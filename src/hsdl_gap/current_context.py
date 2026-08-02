from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .catalog import CatalogItem, load_catalog, validate_catalog


AXIS_KEYWORDS: dict[str, tuple[str, ...]] = {
    "decision_effect": (
        "decision",
        "approval",
        "allocation",
        "transaction",
        "classification",
        "scoring",
        "ranking",
        "stop",
        "restrict",
        "closure",
        "cancellation",
        "instruction",
        "control",
        "grounding",
        "release",
        "eligibility",
        "interruption",
        "enforcement",
    ),
    "automation_level": (
        "automatic",
        "automated",
        "autonomous",
        "high_automation",
        "direct_execution",
        "direct_intervention",
        "direct_aircraft_control",
        "physical_state_change",
    ),
    "human_approval_or_review": (
        "no_human",
        "no_independent",
        "no_authority",
        "no_direct",
        "no_mandatory",
        "no_operator",
        "no_pilot",
        "no_controller",
        "no_coordinator",
        "no_airport",
        "no_ground",
        "no_certified",
        "no_flight",
        "no_stepwise",
        "without_human",
    ),
    "physical_actuation": (
        "physical_control",
        "physical_state_change",
        "robotic_surgery",
        "treatment_execution",
        "direct_execution",
        "direct_intervention",
        "aircraft_control",
        "vehicle",
        "drone",
        "uav",
        "collision_avoidance",
        "fuel_management",
        "taxi",
        "routing",
        "runway_closure",
        "automatic_stop",
    ),
    "biometric_or_sensitive_attribute_use": (
        "biometric",
        "sensitive_attribute",
        "ethnic",
        "religious",
    ),
    "scale_or_value_threshold": (
        "large_scale",
        "high_value",
        "threshold",
        "large_airport",
        "high_frequency",
    ),
}


@dataclass(frozen=True, slots=True)
class Decision33WitnessContext:
    catalog_item_id: str
    sector: str
    use_case: str
    decision_effect_evidence: tuple[str, ...]
    automation_level_evidence: tuple[str, ...]
    human_approval_or_review_evidence: tuple[str, ...]
    physical_actuation_evidence: tuple[str, ...]
    biometric_or_sensitive_attribute_use_evidence: tuple[str, ...]
    scale_or_value_threshold_evidence: tuple[str, ...]
    legacy_or_preexisting_certification_status: str
    placed_in_operation_on: str | None
    assessment_route: str
    source_features: tuple[str, ...]
    witness_status: str = "AUTHOR_DERIVED_POSITIVE_WITNESS_NOT_EXHAUSTIVE"

    def as_mapping(self) -> dict[str, Any]:
        return asdict(self)


def _axis_evidence(features: tuple[str, ...], axis: str) -> tuple[str, ...]:
    keywords = AXIS_KEYWORDS[axis]
    return tuple(
        sorted(
            feature
            for feature in features
            if any(keyword in feature for keyword in keywords)
        )
    )


def witness_from_catalog_item(item: CatalogItem) -> Decision33WitnessContext:
    features = tuple(sorted(item.activation_features))
    return Decision33WitnessContext(
        catalog_item_id=item.id,
        sector=item.sector,
        use_case=item.name_vi,
        decision_effect_evidence=_axis_evidence(features, "decision_effect"),
        automation_level_evidence=_axis_evidence(features, "automation_level"),
        human_approval_or_review_evidence=_axis_evidence(
            features, "human_approval_or_review"
        ),
        physical_actuation_evidence=_axis_evidence(features, "physical_actuation"),
        biometric_or_sensitive_attribute_use_evidence=_axis_evidence(
            features, "biometric_or_sensitive_attribute_use"
        ),
        scale_or_value_threshold_evidence=_axis_evidence(
            features, "scale_or_value_threshold"
        ),
        legacy_or_preexisting_certification_status=(
            "UNSPECIFIED_BY_INDIVIDUAL_CATALOG_ROW"
        ),
        placed_in_operation_on=None,
        assessment_route=item.assessment_route,
        source_features=features,
    )


def build_decision33_witnesses(
    catalog_path: str | Path,
) -> tuple[Decision33WitnessContext, ...]:
    catalog = load_catalog(catalog_path)
    errors = validate_catalog(catalog)
    if errors:
        raise ValueError("invalid Decision 33 catalog: " + "; ".join(errors))
    return tuple(witness_from_catalog_item(item) for item in catalog.items)


def build_current_context_report(catalog_path: str | Path) -> dict[str, Any]:
    witnesses = build_decision33_witnesses(catalog_path)
    feature_vocabulary = sorted(
        {feature for witness in witnesses for feature in witness.source_features}
    )
    axis_fields = {
        "decision_effect": "decision_effect_evidence",
        "automation_level": "automation_level_evidence",
        "human_approval_or_review": "human_approval_or_review_evidence",
        "physical_actuation": "physical_actuation_evidence",
        "biometric_or_sensitive_attribute_use": (
            "biometric_or_sensitive_attribute_use_evidence"
        ),
        "scale_or_value_threshold": "scale_or_value_threshold_evidence",
    }
    axis_counts: dict[str, int] = {}
    rows_without_axis_evidence: dict[str, list[str]] = {}
    for axis, field_name in axis_fields.items():
        with_evidence = [
            witness
            for witness in witnesses
            if getattr(witness, field_name)
        ]
        axis_counts[axis] = len(with_evidence)
        rows_without_axis_evidence[axis] = [
            witness.catalog_item_id
            for witness in witnesses
            if not getattr(witness, field_name)
        ]

    route_counts: dict[str, int] = {}
    sector_counts: dict[str, int] = {}
    for witness in witnesses:
        route_counts[witness.assessment_route] = (
            route_counts.get(witness.assessment_route, 0) + 1
        )
        sector_counts[witness.sector] = sector_counts.get(witness.sector, 0) + 1

    return {
        "schema_version": "1.0.0",
        "profile_id": "VN_DECISION_33_CATALOG_WITNESS_PROFILE_0_1",
        "status": "CATALOG_DRIVEN_POSITIVE_WITNESSES_COMPLETE",
        "witness_count": len(witnesses),
        "sector_counts": dict(sorted(sector_counts.items())),
        "assessment_route_counts": dict(sorted(route_counts.items())),
        "feature_vocabulary_count": len(feature_vocabulary),
        "feature_vocabulary": feature_vocabulary,
        "axis_evidence_counts": axis_counts,
        "rows_without_axis_evidence": rows_without_axis_evidence,
        "witnesses": [witness.as_mapping() for witness in witnesses],
        "universe_status": {
            "is_cartesian_product": False,
            "is_exhaustive": False,
            "supports_prevalence_inference": False,
            "supports_negative_classification_cases": False,
            "notice": (
                "Each record is one positive catalog witness preserving the row's source "
                "features. The profile does not enumerate non-listed systems or all "
                "combinations of operational facts."
            ),
        },
        "research_gates": {
            "H7_1": "BLOCKED_PENDING_SHARED_EU_VN_CLASSIFICATION_RELATION_AND_NEGATIVE_CASES",
            "current_G2": "ROUTE_STRUCTURE_AVAILABLE_PENDING_CURRENT_POLICY_RULES",
            "uniform_percentage_claims": "PROHIBITED_ON_WITNESS_PROFILE",
            "shared_context_measure": "NOT_DEFINED",
        },
        "derivation_status": {
            "source_features": "CATALOG_TRANSCRIPTION",
            "axis_evidence": "AUTHOR_DERIVED_KEYWORD_GROUPING_REQUIRES_SECOND_REVIEW",
            "legal_signoff": False,
        },
    }
