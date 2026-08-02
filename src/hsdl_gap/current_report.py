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

ROUTE_A = "ARTICLE_13_2_A_THIRD_PARTY_CERTIFICATION"
ROUTE_B = "ARTICLE_13_2_B_PROVIDER_SELF_OR_THIRD_PARTY"
ROUTE_EVIDENCE = "TWO_HTML_TRANSCRIPTIONS_MATCH_PENDING_SIGNED_PDF_VISUAL"


def build_decision33_report(catalog_path: str | Path) -> dict[str, object]:
    catalog = load_catalog(catalog_path)
    validation_errors = validate_catalog(catalog)
    missing = sorted(REQUIRED_CATALOG_DIMENSIONS - LEGACY_CONTEXT_DIMENSIONS)
    transport_count = catalog.sector_counts.get("transport", 0)
    unresolved_routes = sum(
        item.assessment_route not in {ROUTE_A, ROUTE_B} for item in catalog.items
    )
    route_evidence_statuses = sorted({item.assessment_route_evidence for item in catalog.items})
    return {
        "catalog_id": catalog.id,
        "freeze_date": catalog.freeze_date,
        "legal_status_at_freeze": catalog.legal_status_at_freeze,
        "item_count": len(catalog.items),
        "sector_counts": catalog.sector_counts,
        "transport_share": transport_count / len(catalog.items),
        "assessment_route_counts": catalog.assessment_route_counts,
        "assessment_route_evidence_statuses": route_evidence_statuses,
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
            "G2_conformity_assessment": "ROUTES_INGESTED_PENDING_SIGNED_PDF_VISUAL_AND_RULE_ENCODING",
            "draft_four_group_catalog_claims": "SUPERSEDED_BY_FINAL_SIX_SECTOR_CATALOG",
            "legacy_quantitative_tables": "HISTORICAL_ONLY_UNTIL_CURRENT_PROFILE_EXISTS",
        },
        "transition": catalog.transition,
    }
