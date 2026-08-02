from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .context_v2 import ContextV2, FixtureType
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import content_sha256


_MISSING = object()
_SYNTHETIC_TRUTH_TABLE_ROOT = "context:classification-relation:synthetic-root"


class ClassificationState(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN = "UNKNOWN"


class SharedClassificationRelation(str, Enum):
    BOTH_IN_SCOPE_CROSSWALK_REQUIRED = "BOTH_IN_SCOPE_CROSSWALK_REQUIRED"
    EU_ONLY_MODEL_SCOPE = "EU_ONLY_MODEL_SCOPE"
    VN_ONLY_MODEL_SCOPE = "VN_ONLY_MODEL_SCOPE"
    NEITHER_MODEL_SCOPE = "NEITHER_MODEL_SCOPE"
    UNKNOWN_MISSING_FACTS = "UNKNOWN_MISSING_FACTS"


@dataclass(frozen=True, slots=True)
class NativeClassification:
    jurisdiction: str
    state: ClassificationState
    native_route: str | None
    matched_identifiers: tuple[str, ...]
    missing_facts: tuple[str, ...]
    provenance: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "jurisdiction": self.jurisdiction,
            "state": self.state.value,
            "native_route": self.native_route,
            "matched_identifiers": list(self.matched_identifiers),
            "missing_facts": list(self.missing_facts),
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class ClassificationRelationResult:
    context_id: str
    eu: NativeClassification
    vn: NativeClassification
    relation: SharedClassificationRelation
    reason: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "context_id": self.context_id,
            "eu": self.eu.as_mapping(),
            "vn": self.vn.as_mapping(),
            "relation": self.relation.value,
            "reason": self.reason,
        }


def _get_path(payload: Mapping[str, Any], field_path: str) -> Any:
    current: Any = payload
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def classify_eu(facts: Mapping[str, Any]) -> NativeClassification:
    high_risk = _get_path(facts, "classification.eu.is_high_risk_ai_system")
    if high_risk is _MISSING or high_risk is None:
        return NativeClassification(
            jurisdiction="EU",
            state=ClassificationState.UNKNOWN,
            native_route=None,
            matched_identifiers=(),
            missing_facts=("classification.eu.is_high_risk_ai_system",),
            provenance="MISSING_CONTEXT_FACT",
        )
    if not isinstance(high_risk, bool):
        raise ValueError("classification.eu.is_high_risk_ai_system must be boolean")
    if not high_risk:
        return NativeClassification(
            jurisdiction="EU",
            state=ClassificationState.OUT_OF_SCOPE,
            native_route="NOT_HIGH_RISK_IN_CANDIDATE_MODEL",
            matched_identifiers=(),
            missing_facts=(),
            provenance="CONTEXT_DECLARED",
        )
    annex = _get_path(facts, "classification.eu.annex_category")
    product_route = _get_path(facts, "classification.eu.product_law_route")
    identifiers = tuple(
        str(value)
        for value in (annex, product_route)
        if value is not _MISSING and value is not None
    )
    return NativeClassification(
        jurisdiction="EU",
        state=ClassificationState.IN_SCOPE,
        native_route=(
            "HIGH_RISK_PRODUCT_OR_ANNEX_ROUTE"
            if identifiers
            else "HIGH_RISK_ROUTE_UNSPECIFIED"
        ),
        matched_identifiers=identifiers,
        missing_facts=(),
        provenance="CONTEXT_DECLARED",
    )


def classify_vn(facts: Mapping[str, Any]) -> NativeClassification:
    listed = _get_path(facts, "classification.vn.listed")
    if listed is _MISSING or listed is None:
        return NativeClassification(
            jurisdiction="VN",
            state=ClassificationState.UNKNOWN,
            native_route=None,
            matched_identifiers=(),
            missing_facts=("classification.vn.listed",),
            provenance="MISSING_CONTEXT_FACT",
        )
    if not isinstance(listed, bool):
        raise ValueError("classification.vn.listed must be boolean")
    if not listed:
        return NativeClassification(
            jurisdiction="VN",
            state=ClassificationState.OUT_OF_SCOPE,
            native_route="SYNTHETIC_NON_LISTED_CONTROL",
            matched_identifiers=(),
            missing_facts=(),
            provenance="SYNTHETIC_FIXTURE_DECLARED",
        )
    catalog_id = _get_path(facts, "classification.vn.catalog_item_id")
    route = _get_path(facts, "classification.vn.assessment_route")
    missing = tuple(
        field
        for field, value in (
            ("classification.vn.catalog_item_id", catalog_id),
            ("classification.vn.assessment_route", route),
        )
        if value is _MISSING or value is None
    )
    if missing:
        return NativeClassification(
            jurisdiction="VN",
            state=ClassificationState.UNKNOWN,
            native_route=None,
            matched_identifiers=(),
            missing_facts=missing,
            provenance="MISSING_CONTEXT_FACT",
        )
    return NativeClassification(
        jurisdiction="VN",
        state=ClassificationState.IN_SCOPE,
        native_route=str(route),
        matched_identifiers=(str(catalog_id),),
        missing_facts=(),
        provenance="CATALOG_WITNESS_OR_DECLARED_FIXTURE",
    )


def relate_native_classifications(
    eu: NativeClassification,
    vn: NativeClassification,
) -> tuple[SharedClassificationRelation, str]:
    if ClassificationState.UNKNOWN in {eu.state, vn.state}:
        return (
            SharedClassificationRelation.UNKNOWN_MISSING_FACTS,
            "At least one jurisdiction-native classification is unknown; no cross-jurisdiction scope relation is inferred.",
        )
    if eu.state is ClassificationState.IN_SCOPE and vn.state is ClassificationState.IN_SCOPE:
        return (
            SharedClassificationRelation.BOTH_IN_SCOPE_CROSSWALK_REQUIRED,
            "Both native classifiers are in scope, but taxonomy equivalence requires an explicit crosswalk rather than a shared risk-tier shortcut.",
        )
    if eu.state is ClassificationState.IN_SCOPE:
        return (
            SharedClassificationRelation.EU_ONLY_MODEL_SCOPE,
            "The declared facts place the context in the EU candidate scope and outside the Vietnam candidate scope.",
        )
    if vn.state is ClassificationState.IN_SCOPE:
        return (
            SharedClassificationRelation.VN_ONLY_MODEL_SCOPE,
            "The declared facts place the context in the Vietnam candidate scope and outside the EU candidate scope.",
        )
    return (
        SharedClassificationRelation.NEITHER_MODEL_SCOPE,
        "Both jurisdiction-native candidate classifiers are out of scope for the declared facts.",
    )


def classify_context(context: ContextV2) -> ClassificationRelationResult:
    eu = classify_eu(context.facts)
    vn = classify_vn(context.facts)
    relation, reason = relate_native_classifications(eu, vn)
    return ClassificationRelationResult(
        context_id=context.context_id,
        eu=eu,
        vn=vn,
        relation=relation,
        reason=reason,
    )


def _synthetic_relation_cases() -> tuple[ContextV2, ...]:
    base = {
        "time": {"evaluation_date": "2026-08-15"},
        "system": {"sector": "synthetic", "use_case": "relation truth table"},
    }
    cases = (
        (
            "both-in",
            {
                "eu": {"is_high_risk_ai_system": True, "annex_category": "ANNEX_III"},
                "vn": {"listed": True, "catalog_item_id": "SYNTHETIC", "assessment_route": "POINT_B"},
            },
        ),
        (
            "eu-only",
            {
                "eu": {"is_high_risk_ai_system": True},
                "vn": {"listed": False},
            },
        ),
        (
            "vn-only",
            {
                "eu": {"is_high_risk_ai_system": False},
                "vn": {"listed": True, "catalog_item_id": "SYNTHETIC", "assessment_route": "POINT_A"},
            },
        ),
        (
            "neither",
            {
                "eu": {"is_high_risk_ai_system": False},
                "vn": {"listed": False},
            },
        ),
        (
            "unknown",
            {
                "eu": {},
                "vn": {"listed": True, "catalog_item_id": "SYNTHETIC", "assessment_route": "POINT_B"},
            },
        ),
    )
    return tuple(
        ContextV2(
            context_id=f"context:classification-relation:{name}",
            profile_id="profile:classification-relation:truth-table",
            fixture_type=FixtureType.MIXED_FEATURE,
            facts={**base, "classification": classification},
            provenance={
                "status": "SYNTHETIC_FIXTURE",
                "generator": "classification-relation-truth-table-v1",
                "legal_validation": "NOT_ASSERTED",
            },
            parent_context_id=_SYNTHETIC_TRUTH_TABLE_ROOT,
        )
        for name, classification in cases
    )


def build_classification_relation_report(
    catalog_path: str | Path = "catalogs/vn_decision_33_2026.csv",
) -> dict[str, Any]:
    corpus = build_decision33_context_v2_corpus(catalog_path)
    corpus_results = tuple(classify_context(context) for context in corpus)
    synthetic_contexts = _synthetic_relation_cases()
    synthetic_results = tuple(classify_context(context) for context in synthetic_contexts)
    corpus_relations = Counter(item.relation.value for item in corpus_results)
    eu_states = Counter(item.eu.state.value for item in corpus_results)
    vn_states = Counter(item.vn.state.value for item in corpus_results)
    synthetic_relations = Counter(item.relation.value for item in synthetic_results)
    truth_table_complete = set(synthetic_relations) == {
        item.value for item in SharedClassificationRelation
    }
    return {
        "schema_version": "1.0.0",
        "status": "NATIVE_CLASSIFICATION_RELATION_INTERFACE_COMPLETE",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "context_corpus_id": "corpus:VN:decision33-catalog-context-v2",
        "context_count": len(corpus),
        "native_classifier_contract": {
            "shared_factual_context": True,
            "jurisdiction_native_taxonomies_preserved": True,
            "shared_risk_tier_used": False,
            "unknown_is_distinct_from_out_of_scope": True,
        },
        "corpus_eu_state_counts": dict(sorted(eu_states.items())),
        "corpus_vn_state_counts": dict(sorted(vn_states.items())),
        "corpus_relation_counts": dict(sorted(corpus_relations.items())),
        "synthetic_truth_table": {
            "case_count": len(synthetic_results),
            "relation_counts": dict(sorted(synthetic_relations.items())),
            "complete": truth_table_complete,
            "results": [item.as_mapping() for item in synthetic_results],
        },
        "corpus_result_hash": content_sha256(
            [item.as_mapping() for item in corpus_results]
        ),
        "corpus_result_samples": [
            item.as_mapping() for item in corpus_results[:5]
        ],
        "completeness": {
            "interface_executable": True,
            "vn_catalog_classifier_executable": True,
            "eu_high_risk_classifier_interface_executable": True,
            "current_corpus_contains_eu_classification_facts": False,
            "reviewed_eu_vn_crosswalk_available": False,
            "shared_classification_relation_complete": False,
            "notice": (
                "The relation interface is executable and all relation states are tested. "
                "The current Decision 33 corpus lacks EU classification facts, so every "
                "corpus relation remains unknown rather than being forced into a common tier."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="catalogs/vn_decision_33_2026.csv")
    args = parser.parse_args()
    report = build_classification_relation_report(args.catalog)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
