from __future__ import annotations

from pathlib import Path

from .catalog import load_catalog, validate_catalog

LEGACY_CONTEXT_DIMENSIONS = {
    "risk_tier",
    "sector",
    "system_role",
    "lifecycle_stage",
    "modification_increases_risk",
    "serious_harm_discovered",
    "interacts_with_human",
    "existing_sector_certification",
}

REQUIRED_CATALOG_DIMENSIONS = {
    "catalog_item_id",
    "sector",
    "use_case",
    "decision_effect",
    "automation_level",
    "human_approval_or_review",
    "physical_actuation",
    "biometric_or_sensitive_attribute_use",
    "scale_or_value_threshold",
    "legacy_or_preexisting_certification_status",
    "placed_in_operation_on",
}


def build_decision33_report(catalog_path: str | Path) -> dict[str, object]:
    catalog = load_catalog(catalog_path)
    validation_errors = validate_catalog(catalog)
    missing = sorted(REQUIRED_CATALOG_DIMENSIONS - LEGACY_CONTEXT_DIMENSIONS)
    transport_count = catalog.sector_counts.get("transport", 0)
    unresolved_routes = sum(
        item.assessment_route == "UNRESOLVED_FROM_HTML_TABLE" for item in catalog.items
    )
    return {
        "catalog_id": catalog.id,
        "freeze_date": catalog.freeze_date,
        "legal_status_at_freeze": catalog.legal_status_at_freeze,
        "item_count": len(catalog.items),
        "sector_counts": catalog.sector_counts,
        "transport_share": transport_count / len(catalog.items),
        "unresolved_assessment_routes": unresolved_routes,
        "validation_errors": validation_errors,
        "legacy_schema_compatibility": {
            "status": "NOT_EXACTLY_REPRESENTABLE",
            "missing_dimensions": missing,
            "reason": (
                "The final catalog is use-case and sector specific and repeatedly conditions "
                "coverage on automation, human approval, decision effect, thresholds, physical "
                "actuation, or biometric use. The legacy eight-dimensional context cannot encode "
                "those predicates without information loss."
            ),
        },
        "research_gates": {
            "H7_1_classification_compatibility": "REQUIRES_REPROOF",
            "G2_conformity_assessment": "REQUIRES_REENCODING_AFTER_ROUTE_VERIFICATION",
            "draft_four_group_catalog_claims": "SUPERSEDED_BY_FINAL_SIX_SECTOR_CATALOG",
            "legacy_quantitative_tables": "HISTORICAL_ONLY_UNTIL_CURRENT_PROFILE_EXISTS",
        },
        "transition": catalog.transition,
    }
