from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .classification_relation import classify_context
from .context_v2 import ContextV2, FixtureType
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import EntityKind, StableId, content_sha256


PROFILE_ID = "profile:EU:article6-annexiii-context-v2"
CORPUS_ID = "corpus:EU:article6-annexiii-context-v2"
_MISSING = object()


class EUContextError(ValueError):
    """Raised when the EU native classification corpus violates its contract."""


class EUClassificationState(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EUClassificationResult:
    state: EUClassificationState
    native_route: str | None
    annex_identifier: str | None
    missing_facts: tuple[str, ...]
    reason: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "native_route": self.native_route,
            "annex_identifier": self.annex_identifier,
            "missing_facts": list(self.missing_facts),
            "reason": self.reason,
        }


def _load_profile(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EUContextError(f"cannot load EU classification profile: {exc}") from exc
    if not isinstance(payload, dict):
        raise EUContextError("EU classification profile must be an object")
    if payload.get("legal_validation") != "NOT_ASSERTED":
        raise EUContextError("EU classification profile must not assert legal validation")
    routes = payload.get("native_routes")
    if not isinstance(routes, list) or not routes:
        raise EUContextError("EU classification profile must contain native routes")
    return payload


def _get_path(payload: Mapping[str, Any], field_path: str) -> Any:
    current: Any = payload
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def classify_eu_article6(facts: Mapping[str, Any]) -> EUClassificationResult:
    route_type = _get_path(facts, "classification.eu.route_type")
    route_id = _get_path(facts, "classification.eu.native_route")
    annex_identifier = _get_path(facts, "classification.eu.annex_identifier")
    missing_identity = tuple(
        path
        for path, value in (
            ("classification.eu.route_type", route_type),
            ("classification.eu.native_route", route_id),
        )
        if value is _MISSING or value is None
    )
    if missing_identity:
        return EUClassificationResult(
            state=EUClassificationState.UNKNOWN,
            native_route=None,
            annex_identifier=None,
            missing_facts=missing_identity,
            reason="EU native route identity is missing.",
        )

    if route_type == "ARTICLE_6_1_PRODUCT":
        safety_component = _get_path(
            facts, "classification.eu.annex_i_product_or_safety_component"
        )
        third_party = _get_path(
            facts,
            "classification.eu.third_party_conformity_assessment_required",
        )
        missing = tuple(
            path
            for path, value in (
                (
                    "classification.eu.annex_i_product_or_safety_component",
                    safety_component,
                ),
                (
                    "classification.eu.third_party_conformity_assessment_required",
                    third_party,
                ),
            )
            if value is _MISSING or value is None
        )
        if missing:
            return EUClassificationResult(
                state=EUClassificationState.UNKNOWN,
                native_route=str(route_id),
                annex_identifier=(
                    None if annex_identifier is _MISSING else str(annex_identifier)
                ),
                missing_facts=missing,
                reason="Article 6(1) requires both product/safety-component and third-party assessment facts.",
            )
        if not isinstance(safety_component, bool) or not isinstance(third_party, bool):
            raise EUContextError("Article 6(1) facts must be boolean")
        in_scope = safety_component and third_party
        return EUClassificationResult(
            state=(
                EUClassificationState.IN_SCOPE
                if in_scope
                else EUClassificationState.OUT_OF_SCOPE
            ),
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=(),
            reason=(
                "Both Article 6(1) cumulative conditions are satisfied."
                if in_scope
                else "At least one cumulative Article 6(1) condition is false."
            ),
        )

    if route_type != "ARTICLE_6_2_ANNEX_III":
        raise EUContextError(f"unsupported EU route type: {route_type!r}")

    listed = _get_path(facts, "classification.eu.annex_iii_listed_use_case")
    if listed is _MISSING or listed is None:
        return EUClassificationResult(
            state=EUClassificationState.UNKNOWN,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=("classification.eu.annex_iii_listed_use_case",),
            reason="Annex III intended-use membership is missing.",
        )
    if not isinstance(listed, bool):
        raise EUContextError("annex_iii_listed_use_case must be boolean")
    if not listed:
        return EUClassificationResult(
            state=EUClassificationState.OUT_OF_SCOPE,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=(),
            reason="The intended use is declared outside the selected Annex III use case.",
        )

    profiling = _get_path(facts, "classification.eu.profiling_natural_persons")
    if profiling is _MISSING or profiling is None:
        return EUClassificationResult(
            state=EUClassificationState.UNKNOWN,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=("classification.eu.profiling_natural_persons",),
            reason="Profiling status is required to apply the Article 6(3) override.",
        )
    if not isinstance(profiling, bool):
        raise EUContextError("profiling_natural_persons must be boolean")
    if profiling:
        return EUClassificationResult(
            state=EUClassificationState.IN_SCOPE,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=(),
            reason="Annex III profiling remains high-risk notwithstanding Article 6(3).",
        )

    exception = _get_path(
        facts, "classification.eu.article6_3_exception_condition"
    )
    if exception is _MISSING or exception is None:
        return EUClassificationResult(
            state=EUClassificationState.UNKNOWN,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=("classification.eu.article6_3_exception_condition",),
            reason="Article 6(3) exception-condition status is missing.",
        )
    if exception == "NONE":
        return EUClassificationResult(
            state=EUClassificationState.IN_SCOPE,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=(),
            reason="The system is an Annex III use case and no Article 6(3) exception condition is declared.",
        )

    significant = _get_path(
        facts, "classification.eu.significant_risk_or_material_influence"
    )
    if significant is _MISSING or significant is None:
        return EUClassificationResult(
            state=EUClassificationState.UNKNOWN,
            native_route=str(route_id),
            annex_identifier=(
                None if annex_identifier is _MISSING else str(annex_identifier)
            ),
            missing_facts=(
                "classification.eu.significant_risk_or_material_influence",
            ),
            reason="The exception condition is declared but significant-risk/material-influence status is missing.",
        )
    if not isinstance(significant, bool):
        raise EUContextError(
            "significant_risk_or_material_influence must be boolean"
        )
    return EUClassificationResult(
        state=(
            EUClassificationState.IN_SCOPE
            if significant
            else EUClassificationState.OUT_OF_SCOPE
        ),
        native_route=str(route_id),
        annex_identifier=(
            None if annex_identifier is _MISSING else str(annex_identifier)
        ),
        missing_facts=(),
        reason=(
            "The declared Annex III use case still poses significant risk or materially influences decision making."
            if significant
            else "The declared Article 6(3) exception condition and no-significant-risk facts are satisfied."
        ),
    )


def _positive_context(route: Mapping[str, Any]) -> ContextV2:
    route_id = str(route["route_id"])
    route_type = str(route["route_type"])
    eu: dict[str, Any] = {
        "route_type": route_type,
        "native_route": route_id,
        "annex_identifier": route["annex_identifier"],
    }
    if route_type == "ARTICLE_6_1_PRODUCT":
        eu.update(
            {
                "annex_i_product_or_safety_component": True,
                "third_party_conformity_assessment_required": True,
            }
        )
    else:
        eu.update(
            {
                "annex_iii_listed_use_case": True,
                "article6_3_exception_condition": "NONE",
                "significant_risk_or_material_influence": True,
                "profiling_natural_persons": False,
            }
        )
    return ContextV2(
        context_id=str(StableId(EntityKind.CONTEXT, "eu-article6", route_id)),
        profile_id=PROFILE_ID,
        fixture_type=FixtureType.POSITIVE_WITNESS,
        facts={
            "classification": {"eu": eu},
            "system": {"use_case": route["label"]},
            "time": {"evaluation_date": "2026-08-02"},
        },
        provenance={
            "status": "SOURCE_DERIVED_SYNTHETIC_ARCHETYPE",
            "source_id": "EU_AI_ACT_2024_1689",
            "source_provision": (
                "Article 6(1)"
                if route_type == "ARTICLE_6_1_PRODUCT"
                else "Article 6(2)-(3) and Annex III"
            ),
            "generator": "eu-article6-context-v2-positive-v1",
            "legal_validation": "NOT_ASSERTED",
        },
    )


def _derived(
    parent: ContextV2,
    *,
    suffix: str,
    fixture_type: FixtureType,
    eu_facts: Mapping[str, Any],
    rationale: str,
) -> ContextV2:
    facts = deepcopy(dict(parent.facts))
    facts["classification"]["eu"] = deepcopy(dict(eu_facts))
    parent_local = StableId.parse(parent.context_id).local_id
    return ContextV2(
        context_id=str(
            StableId(EntityKind.CONTEXT, "eu-article6-derived", f"{parent_local}.{suffix}")
        ),
        profile_id=parent.profile_id,
        fixture_type=fixture_type,
        parent_context_id=parent.context_id,
        mutation_id=suffix,
        facts=facts,
        provenance={
            "status": "SYNTHETIC_FIXTURE",
            "generator": "eu-article6-context-v2-derived-v1",
            "rationale": rationale,
            "legal_validation": "NOT_ASSERTED",
        },
    )


def _route_fixtures(parent: ContextV2) -> tuple[ContextV2, ...]:
    eu = deepcopy(dict(parent.facts["classification"]["eu"]))
    if eu["route_type"] == "ARTICLE_6_1_PRODUCT":
        negative = deepcopy(eu)
        negative["third_party_conformity_assessment_required"] = False
        unknown = deepcopy(eu)
        unknown.pop("third_party_conformity_assessment_required")
        boundary = deepcopy(eu)
        boundary["annex_identifier"] = "ANNEX_I_SECTION_B_LIMITED_APPLICATION"
        return (
            _derived(
                parent,
                suffix="third-party-false",
                fixture_type=FixtureType.SINGLE_FAULT_NEGATIVE,
                eu_facts=negative,
                rationale="Exercise failure of the second cumulative Article 6(1) condition.",
            ),
            _derived(
                parent,
                suffix="third-party-unknown",
                fixture_type=FixtureType.UNKNOWN_FACT,
                eu_facts=unknown,
                rationale="Omit the third-party conformity-assessment fact.",
            ),
            _derived(
                parent,
                suffix="annex-i-section-b-boundary",
                fixture_type=FixtureType.BOUNDARY_EXACT,
                eu_facts=boundary,
                rationale="Exercise the Annex I Section B limited-application boundary without changing Article 6(1) classification.",
            ),
        )

    negative = deepcopy(eu)
    negative.update(
        {
            "article6_3_exception_condition": "NARROW_PROCEDURAL_TASK",
            "significant_risk_or_material_influence": False,
            "profiling_natural_persons": False,
        }
    )
    unknown = deepcopy(negative)
    unknown.pop("significant_risk_or_material_influence")
    boundary = deepcopy(negative)
    boundary["profiling_natural_persons"] = True
    return (
        _derived(
            parent,
            suffix="article6-3-excluded",
            fixture_type=FixtureType.SINGLE_FAULT_NEGATIVE,
            eu_facts=negative,
            rationale="Exercise an Article 6(3) exception condition with no significant risk/material influence.",
        ),
        _derived(
            parent,
            suffix="article6-3-risk-unknown",
            fixture_type=FixtureType.UNKNOWN_FACT,
            eu_facts=unknown,
            rationale="Omit significant-risk/material-influence status while an Article 6(3) condition is asserted.",
        ),
        _derived(
            parent,
            suffix="profiling-override-boundary",
            fixture_type=FixtureType.BOUNDARY_EXACT,
            eu_facts=boundary,
            rationale="Exercise the profiling override that remains high-risk notwithstanding Article 6(3).",
        ),
    )


def build_eu_article6_context_corpus(
    profile_path: str | Path = (
        "profiles/current-candidate-2026-08-02/"
        "eu_native_classification_profile.json"
    ),
) -> tuple[ContextV2, ...]:
    profile = _load_profile(profile_path)
    contexts: list[ContextV2] = []
    for route in profile["native_routes"]:
        if not isinstance(route, Mapping):
            raise EUContextError("native route records must be objects")
        parent = _positive_context(route)
        contexts.append(parent)
        contexts.extend(_route_fixtures(parent))
    return tuple(contexts)


def validate_eu_article6_context_corpus(
    contexts: tuple[ContextV2, ...],
) -> list[str]:
    errors: list[str] = []
    if len(contexts) != 36:
        errors.append(f"EU corpus must contain 36 contexts, got {len(contexts)}")
    ids = [context.context_id for context in contexts]
    if len(ids) != len(set(ids)):
        errors.append("EU context IDs are not unique")
    counts = Counter(context.fixture_type for context in contexts)
    expected = {
        FixtureType.POSITIVE_WITNESS: 9,
        FixtureType.SINGLE_FAULT_NEGATIVE: 9,
        FixtureType.UNKNOWN_FACT: 9,
        FixtureType.BOUNDARY_EXACT: 9,
    }
    if counts != expected:
        errors.append(
            "EU fixture counts differ: "
            + json.dumps(
                {key.value: value for key, value in counts.items()}, sort_keys=True
            )
        )
    parent_ids = {
        context.context_id
        for context in contexts
        if context.fixture_type is FixtureType.POSITIVE_WITNESS
    }
    for context in contexts:
        if context.fixture_type is FixtureType.POSITIVE_WITNESS:
            continue
        if context.parent_context_id not in parent_ids:
            errors.append(f"{context.context_id} has an invalid positive parent")
    state_counts = Counter(
        classify_eu_article6(context.facts).state for context in contexts
    )
    if state_counts[EUClassificationState.IN_SCOPE] != 18:
        errors.append("EU corpus must contain 18 in-scope results")
    if state_counts[EUClassificationState.OUT_OF_SCOPE] != 9:
        errors.append("EU corpus must contain 9 out-of-scope results")
    if state_counts[EUClassificationState.UNKNOWN] != 9:
        errors.append("EU corpus must contain 9 unknown results")
    return errors


def _match_crosswalk_rule(
    profile: Mapping[str, Any],
    context: ContextV2,
) -> Mapping[str, Any] | None:
    features = set(context.facts.get("system", {}).get("source_features", []))
    sector = context.facts.get("system", {}).get("sector")
    for rule in profile.get("decision33_feature_crosswalk_rules", []):
        if not isinstance(rule, Mapping):
            continue
        required_sector = rule.get("sector")
        if required_sector is not None and required_sector != sector:
            continue
        any_features = set(rule.get("any_features", []))
        if any_features and not (features & any_features):
            continue
        return rule
    return None


def overlay_decision33_with_eu_scenario(
    context: ContextV2,
    *,
    profile: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> ContextV2:
    facts = deepcopy(dict(context.facts))
    classification = facts.setdefault("classification", {})
    match = _match_crosswalk_rule(profile, context)
    scenario_id = str(scenario["scenario_id"])
    eu: dict[str, Any] = {
        "assumption_scenario_id": scenario_id,
        "crosswalk_review_status": "PENDING_INDEPENDENT_REVIEW",
    }
    if match is None:
        eu["mapping_status"] = "UNMATCHED"
        if scenario["unmatched_policy"] == "OUT_OF_SCOPE":
            eu["is_high_risk_ai_system"] = False
            eu["native_route"] = "NO_MATCH_UNDER_EXPERIMENTAL_CLOSED_WORLD"
        else:
            eu["native_route"] = None
    else:
        route_by_id = {
            route["route_id"]: route for route in profile["native_routes"]
        }
        route = route_by_id[match["route_id"]]
        eu.update(
            {
                "mapping_status": "MATCHED",
                "mapping_rule_id": match["rule_id"],
                "mapping_strength": match["mapping_strength"],
                "native_route": route["route_id"],
                "annex_category": route["annex_identifier"],
            }
        )
        if route["route_type"] == "ARTICLE_6_2_ANNEX_III":
            eu["is_high_risk_ai_system"] = True
            eu["article6_route"] = "ARTICLE_6_2_ANNEX_III"
        elif (
            scenario["matched_product_route_policy"]
            == "ASSUME_THIRD_PARTY_CONFORMITY_REQUIRED"
        ):
            eu.update(
                {
                    "is_high_risk_ai_system": True,
                    "article6_route": "ARTICLE_6_1_ANNEX_I_PRODUCT",
                    "product_law_route": "ANNEX_I_PRODUCT_ASSUMED",
                    "third_party_conformity_assessment_required": True,
                }
            )
        else:
            eu["article6_route"] = "ARTICLE_6_1_PRODUCT_FACTS_INCOMPLETE"
    classification["eu"] = eu
    provenance = deepcopy(dict(context.provenance))
    provenance["eu_overlay"] = {
        "scenario_id": scenario_id,
        "status": "AUTHOR_DERIVED_CROSSWALK_ASSUMPTION",
        "legal_validation": "NOT_ASSERTED",
        "notice": scenario["notice"],
    }
    return ContextV2(
        context_id=context.context_id,
        profile_id=context.profile_id,
        fixture_type=context.fixture_type,
        facts=facts,
        provenance=provenance,
        parent_context_id=context.parent_context_id,
        mutation_id=context.mutation_id,
    )


def build_decision33_eu_relation_scenario_report(
    profile_path: str | Path = (
        "profiles/current-candidate-2026-08-02/"
        "eu_native_classification_profile.json"
    ),
    catalog_path: str | Path = "catalogs/vn_decision_33_2026.csv",
) -> dict[str, Any]:
    profile = _load_profile(profile_path)
    corpus = build_decision33_context_v2_corpus(catalog_path)
    scenario_reports: list[dict[str, Any]] = []
    for scenario in profile["decision33_overlay_scenarios"]:
        overlaid = tuple(
            overlay_decision33_with_eu_scenario(
                context, profile=profile, scenario=scenario
            )
            for context in corpus
        )
        results = tuple(classify_context(context) for context in overlaid)
        relation_counts = Counter(result.relation.value for result in results)
        eu_state_counts = Counter(result.eu.state.value for result in results)
        mapping_counts = Counter(
            context.facts["classification"]["eu"]["mapping_status"]
            for context in overlaid
        )
        scenario_reports.append(
            {
                "scenario_id": scenario["scenario_id"],
                "context_count": len(overlaid),
                "unmatched_policy": scenario["unmatched_policy"],
                "matched_product_route_policy": scenario[
                    "matched_product_route_policy"
                ],
                "mapping_counts": dict(sorted(mapping_counts.items())),
                "eu_state_counts": dict(sorted(eu_state_counts.items())),
                "relation_counts": dict(sorted(relation_counts.items())),
                "result_hash": content_sha256(
                    [result.as_mapping() for result in results]
                ),
                "notice": scenario["notice"],
            }
        )
    return {
        "schema_version": "1.0.0",
        "status": "DECISION33_EU_RELATION_SCENARIOS_EXECUTED",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "context_count_per_scenario": len(corpus),
        "scenario_count": len(scenario_reports),
        "scenarios": scenario_reports,
        "completeness": {
            "all_322_contexts_receive_scenario_metadata": all(
                report["context_count"] == 322 for report in scenario_reports
            ),
            "open_world_preserves_unknowns": True,
            "closed_world_is_legal_classification": False,
            "reviewed_eu_vn_crosswalk_available": False,
            "notice": (
                "Both scenarios execute the shared relation over every Decision 33 "
                "context. They are engineering assumptions, not reviewed EU–Vietnam "
                "classification equivalence."
            ),
        },
    }


def build_eu_article6_context_report(
    profile_path: str | Path = (
        "profiles/current-candidate-2026-08-02/"
        "eu_native_classification_profile.json"
    ),
) -> dict[str, Any]:
    contexts = build_eu_article6_context_corpus(profile_path)
    errors = validate_eu_article6_context_corpus(contexts)
    results = tuple(classify_eu_article6(context.facts) for context in contexts)
    fixture_counts = Counter(context.fixture_type.value for context in contexts)
    state_counts = Counter(result.state.value for result in results)
    route_counts = Counter(
        result.native_route
        for context, result in zip(contexts, results, strict=True)
        if context.fixture_type is FixtureType.POSITIVE_WITNESS
    )
    return {
        "schema_version": "1.0.0",
        "status": (
            "EU_ARTICLE6_CONTEXT_V2_CORPUS_COMPLETE"
            if not errors
            else "EU_ARTICLE6_CONTEXT_V2_CORPUS_INVALID"
        ),
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "profile_id": PROFILE_ID,
        "corpus_id": CORPUS_ID,
        "context_count": len(contexts),
        "contexts_per_native_route": 4,
        "native_route_count": len(route_counts),
        "fixture_counts": dict(sorted(fixture_counts.items())),
        "classification_state_counts": dict(sorted(state_counts.items())),
        "positive_route_counts": dict(sorted(route_counts.items())),
        "validation_errors": errors,
        "corpus_hash": content_sha256(
            [context.as_mapping() for context in contexts]
        ),
        "coverage_contract": {
            "article_6_1_product_route": True,
            "annex_iii_points_1_to_8": True,
            "article_6_3_exception_negative": True,
            "article_6_3_unknown": True,
            "profiling_override_boundary": True,
            "is_exhaustive_real_world_universe": False,
            "supports_empirical_prevalence_inference": False,
        },
        "contexts": [context.as_mapping() for context in contexts],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        default=(
            "profiles/current-candidate-2026-08-02/"
            "eu_native_classification_profile.json"
        ),
    )
    parser.add_argument("--catalog", default="catalogs/vn_decision_33_2026.csv")
    parser.add_argument(
        "--mode", choices=("corpus", "relation-scenarios"), default="corpus"
    )
    args = parser.parse_args()
    report = (
        build_eu_article6_context_report(args.profile)
        if args.mode == "corpus"
        else build_decision33_eu_relation_scenario_report(
            args.profile, args.catalog
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if report["status"].endswith("INVALID"):
        raise SystemExit(19)


if __name__ == "__main__":
    main()
