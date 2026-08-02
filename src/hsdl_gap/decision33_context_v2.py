from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping

from .catalog import CatalogItem, RegulatoryCatalog, load_catalog, validate_catalog
from .context_v2 import ContextV2, FixtureType
from .current_context import Decision33WitnessContext, build_decision33_witnesses
from .stable_id import EntityKind, StableId, content_sha256


PROFILE_ID = "profile:VN:decision33-catalog-context-v2"
CORPUS_ID = "corpus:VN:decision33-catalog-context-v2"
ROUTE_A = "ARTICLE_13_2_A_THIRD_PARTY_CERTIFICATION"
ROUTE_B = "ARTICLE_13_2_B_PROVIDER_SELF_OR_THIRD_PARTY"


class Decision33ContextV2Error(ValueError):
    """Raised when the generated Decision 33 corpus violates its contract."""


def _catalog_payload(catalog: RegulatoryCatalog) -> dict[str, Any]:
    return {
        "id": catalog.id,
        "issued_on": catalog.issued_on,
        "effective_from": catalog.effective_from,
        "freeze_date": catalog.freeze_date,
        "legal_status_at_freeze": catalog.legal_status_at_freeze,
        "transition": catalog.transition,
        "items": [asdict(item) for item in catalog.items],
    }


def _positive_context(
    catalog: RegulatoryCatalog,
    item: CatalogItem,
    witness: Decision33WitnessContext,
) -> ContextV2:
    context_id = str(StableId(EntityKind.CONTEXT, "decision33", item.id))
    return ContextV2(
        context_id=context_id,
        profile_id=PROFILE_ID,
        fixture_type=FixtureType.POSITIVE_WITNESS,
        facts={
            "time": {
                "issued_on": catalog.issued_on,
                "effective_from": catalog.effective_from,
                "evaluation_date": catalog.freeze_date,
                "placed_in_operation_on": witness.placed_in_operation_on,
            },
            "system": {
                "sector": witness.sector,
                "use_case": witness.use_case,
                "source_features": list(witness.source_features),
            },
            "classification": {
                "vn": {
                    "listed": True,
                    "catalog_item_id": witness.catalog_item_id,
                    "assessment_route": witness.assessment_route,
                    "assessment_route_evidence": item.assessment_route_evidence,
                    "legacy_or_preexisting_certification_status": (
                        witness.legacy_or_preexisting_certification_status
                    ),
                }
            },
            "evidence": {
                "decision_effect": list(witness.decision_effect_evidence),
                "automation_level": list(witness.automation_level_evidence),
                "human_approval_or_review": list(
                    witness.human_approval_or_review_evidence
                ),
                "physical_actuation": list(witness.physical_actuation_evidence),
                "biometric_or_sensitive_attribute_use": list(
                    witness.biometric_or_sensitive_attribute_use_evidence
                ),
                "scale_or_value_threshold": list(
                    witness.scale_or_value_threshold_evidence
                ),
            },
        },
        provenance={
            "status": "SOURCE_DERIVED",
            "source_catalog_id": catalog.id,
            "catalog_item_id": item.id,
            "source_features_status": "CATALOG_TRANSCRIPTION",
            "axis_evidence_status": (
                "AUTHOR_DERIVED_KEYWORD_GROUPING_REQUIRES_SECOND_REVIEW"
            ),
            "generator": "decision33-context-v2-positive-v1",
            "legal_validation": "NOT_ASSERTED",
        },
    )


def _derived_context(
    parent: ContextV2,
    *,
    suffix: str,
    fixture_type: FixtureType,
    facts: Mapping[str, Any],
    mutation: Mapping[str, Any],
) -> ContextV2:
    parent_local = StableId.parse(parent.context_id).local_id
    return ContextV2(
        context_id=str(
            StableId(
                EntityKind.CONTEXT,
                "decision33-derived",
                f"{parent_local}.{suffix}",
            )
        ),
        profile_id=parent.profile_id,
        fixture_type=fixture_type,
        parent_context_id=parent.context_id,
        mutation_id=suffix,
        facts=facts,
        provenance={
            "status": "SYNTHETIC_FIXTURE",
            "generator": "decision33-context-v2-derived-v1",
            "mutation": dict(mutation),
            "legal_validation": "NOT_ASSERTED",
        },
    )


def _negative_nonlisted(parent: ContextV2) -> ContextV2:
    facts = deepcopy(dict(parent.facts))
    vn = facts["classification"]["vn"]
    vn["listed"] = False
    vn["catalog_item_id"] = None
    vn["assessment_route"] = None
    return _derived_context(
        parent,
        suffix="nonlisted-control",
        fixture_type=FixtureType.SINGLE_FAULT_NEGATIVE,
        facts=facts,
        mutation={
            "concept": "catalog_membership",
            "from": "LISTED_POSITIVE_WITNESS",
            "to": "SYNTHETIC_NON_LISTED_CONTROL",
            "rationale": (
                "Exercise the non-listed branch without asserting that this textual use "
                "case is legally outside the catalog."
            ),
        },
    )


def _unknown_catalog_id(parent: ContextV2) -> ContextV2:
    facts = deepcopy(dict(parent.facts))
    facts["classification"]["vn"].pop("catalog_item_id")
    return _derived_context(
        parent,
        suffix="missing-catalog-id",
        fixture_type=FixtureType.UNKNOWN_FACT,
        facts=facts,
        mutation={
            "field": "classification.vn.catalog_item_id",
            "operation": "DELETE",
            "rationale": "Exercise unknown classification identity.",
        },
    )


def _unknown_route(parent: ContextV2) -> ContextV2:
    facts = deepcopy(dict(parent.facts))
    facts["classification"]["vn"].pop("assessment_route")
    return _derived_context(
        parent,
        suffix="missing-assessment-route",
        fixture_type=FixtureType.UNKNOWN_FACT,
        facts=facts,
        mutation={
            "field": "classification.vn.assessment_route",
            "operation": "DELETE",
            "rationale": "Exercise unknown Article 13 assessment route.",
        },
    )


def _temporal_boundary(
    parent: ContextV2,
    *,
    effective_from: str,
    offset_days: int,
    suffix: str,
    fixture_type: FixtureType,
) -> ContextV2:
    boundary_date = date.fromisoformat(effective_from) + timedelta(days=offset_days)
    facts = deepcopy(dict(parent.facts))
    previous = facts["time"]["evaluation_date"]
    facts["time"]["evaluation_date"] = boundary_date.isoformat()
    return _derived_context(
        parent,
        suffix=suffix,
        fixture_type=fixture_type,
        facts=facts,
        mutation={
            "field": "time.evaluation_date",
            "from": previous,
            "to": boundary_date.isoformat(),
            "boundary": "effective_from",
            "offset_days": offset_days,
        },
    )


def build_decision33_context_v2_corpus(
    catalog_path: str | Path,
) -> tuple[ContextV2, ...]:
    catalog = load_catalog(catalog_path)
    errors = validate_catalog(catalog)
    if errors:
        raise Decision33ContextV2Error(
            "invalid Decision 33 catalog: " + "; ".join(errors)
        )
    witnesses = build_decision33_witnesses(catalog_path)
    witness_by_id = {witness.catalog_item_id: witness for witness in witnesses}
    if set(witness_by_id) != {item.id for item in catalog.items}:
        raise Decision33ContextV2Error(
            "catalog rows and current positive witnesses do not have identical IDs"
        )

    contexts: list[ContextV2] = []
    for item in catalog.items:
        parent = _positive_context(catalog, item, witness_by_id[item.id])
        contexts.extend(
            (
                parent,
                _negative_nonlisted(parent),
                _unknown_catalog_id(parent),
                _unknown_route(parent),
                _temporal_boundary(
                    parent,
                    effective_from=catalog.effective_from,
                    offset_days=-1,
                    suffix="effective-date-below",
                    fixture_type=FixtureType.BOUNDARY_BELOW,
                ),
                _temporal_boundary(
                    parent,
                    effective_from=catalog.effective_from,
                    offset_days=0,
                    suffix="effective-date-exact",
                    fixture_type=FixtureType.BOUNDARY_EXACT,
                ),
                _temporal_boundary(
                    parent,
                    effective_from=catalog.effective_from,
                    offset_days=1,
                    suffix="effective-date-above",
                    fixture_type=FixtureType.BOUNDARY_ABOVE,
                ),
            )
        )
    return tuple(contexts)


def validate_decision33_context_v2_corpus(
    catalog: RegulatoryCatalog,
    contexts: tuple[ContextV2, ...],
) -> list[str]:
    errors: list[str] = []
    ids = [context.context_id for context in contexts]
    if len(ids) != len(set(ids)):
        errors.append("context IDs are not unique")

    positives = [
        context
        for context in contexts
        if context.fixture_type is FixtureType.POSITIVE_WITNESS
    ]
    if len(positives) != len(catalog.items):
        errors.append("positive witness count does not match catalog item count")

    positive_ids = {context.context_id for context in positives}
    expected_positive_ids = {
        str(StableId(EntityKind.CONTEXT, "decision33", item.id))
        for item in catalog.items
    }
    if positive_ids != expected_positive_ids:
        errors.append("positive context IDs do not match every catalog row exactly")

    children_by_parent: Counter[str] = Counter()
    for context in contexts:
        if context.fixture_type is FixtureType.POSITIVE_WITNESS:
            continue
        if context.parent_context_id not in positive_ids:
            errors.append(f"{context.context_id} references a non-positive parent")
        else:
            children_by_parent[context.parent_context_id] += 1
    for positive_id in sorted(positive_ids):
        if children_by_parent[positive_id] != 6:
            errors.append(
                f"{positive_id} must have exactly six deterministic derived fixtures"
            )

    expected_fixture_counts = {
        FixtureType.POSITIVE_WITNESS: 46,
        FixtureType.SINGLE_FAULT_NEGATIVE: 46,
        FixtureType.UNKNOWN_FACT: 92,
        FixtureType.BOUNDARY_BELOW: 46,
        FixtureType.BOUNDARY_EXACT: 46,
        FixtureType.BOUNDARY_ABOVE: 46,
    }
    counts = Counter(context.fixture_type for context in contexts)
    for fixture_type, expected in expected_fixture_counts.items():
        if counts[fixture_type] != expected:
            errors.append(
                f"{fixture_type.value} count must be {expected}, got {counts[fixture_type]}"
            )
    unexpected_types = set(counts) - set(expected_fixture_counts)
    if unexpected_types:
        errors.append(
            "unexpected fixture types: "
            + ", ".join(sorted(item.value for item in unexpected_types))
        )

    for context in contexts:
        if context.fixture_type in {
            FixtureType.BOUNDARY_BELOW,
            FixtureType.BOUNDARY_EXACT,
            FixtureType.BOUNDARY_ABOVE,
        }:
            expected_offset = {
                FixtureType.BOUNDARY_BELOW: -1,
                FixtureType.BOUNDARY_EXACT: 0,
                FixtureType.BOUNDARY_ABOVE: 1,
            }[context.fixture_type]
            expected_date = (
                date.fromisoformat(catalog.effective_from)
                + timedelta(days=expected_offset)
            ).isoformat()
            if context.facts["time"]["evaluation_date"] != expected_date:
                errors.append(f"{context.context_id} has an invalid effective-date boundary")
    return errors


def build_decision33_context_v2_report(
    catalog_path: str | Path,
) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    contexts = build_decision33_context_v2_corpus(catalog_path)
    validation_errors = validate_decision33_context_v2_corpus(catalog, contexts)
    fixture_counts = Counter(context.fixture_type.value for context in contexts)
    positives = [
        context
        for context in contexts
        if context.fixture_type is FixtureType.POSITIVE_WITNESS
    ]
    route_counts = Counter(
        context.facts["classification"]["vn"]["assessment_route"]
        for context in positives
    )
    sector_counts = Counter(context.facts["system"]["sector"] for context in positives)
    return {
        "schema_version": "1.0.0",
        "status": (
            "DECISION33_CONTEXT_V2_CORPUS_COMPLETE"
            if not validation_errors
            else "DECISION33_CONTEXT_V2_CORPUS_INVALID"
        ),
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "profile_id": PROFILE_ID,
        "corpus_id": CORPUS_ID,
        "catalog": {
            "catalog_id": catalog.id,
            "catalog_hash": content_sha256(_catalog_payload(catalog)),
            "issued_on": catalog.issued_on,
            "effective_from": catalog.effective_from,
            "freeze_date": catalog.freeze_date,
            "legal_status_at_freeze": catalog.legal_status_at_freeze,
        },
        "context_count": len(contexts),
        "positive_witness_count": len(positives),
        "derived_fixture_count": len(contexts) - len(positives),
        "contexts_per_catalog_row": 7,
        "fixture_counts": dict(sorted(fixture_counts.items())),
        "positive_assessment_route_counts": dict(sorted(route_counts.items())),
        "positive_sector_counts": dict(sorted(sector_counts.items())),
        "validation_errors": validation_errors,
        "coverage_contract": {
            "every_catalog_row_has_positive_witness": True,
            "every_catalog_row_has_nonlisted_control": True,
            "every_catalog_row_has_missing_catalog_identity": True,
            "every_catalog_row_has_missing_assessment_route": True,
            "every_catalog_row_has_effective_date_below_exact_above": True,
            "is_exhaustive_real_world_universe": False,
            "supports_empirical_prevalence_inference": False,
            "notice": (
                "The derived fixtures exercise declared model branches and temporal "
                "boundaries. They do not establish that any synthetic control is a legal "
                "classification of a real system."
            ),
        },
        "contexts": [context.as_mapping() for context in contexts],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        default="catalogs/vn_decision_33_2026.csv",
    )
    args = parser.parse_args()
    report = build_decision33_context_v2_report(args.catalog)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if report["status"] != "DECISION33_CONTEXT_V2_CORPUS_COMPLETE":
        raise SystemExit(11)


if __name__ == "__main__":
    main()
