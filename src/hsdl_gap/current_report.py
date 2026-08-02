from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
DEFAULT_VISUAL_REVIEW = Path("sources/reviews/vn_decision_33_2026.visual.json")


def _load_visual_review(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    review_path = Path(path)
    if not review_path.exists():
        return None
    return json.loads(review_path.read_text(encoding="utf-8"))


def _validate_visual_review(
    review: dict[str, Any] | None,
    catalog_ids: set[str],
    route_a_ids: set[str],
) -> list[str]:
    if review is None:
        return ["Decision 33 visual-review overlay is unavailable"]
    errors: list[str] = []
    if review.get("schema_version") != "1.0.0":
        errors.append("unsupported Decision 33 visual-review schema")
    if review.get("source_id") != "VN_DECISION_33_2026":
        errors.append("Decision 33 visual-review source_id mismatch")
    findings = review.get("findings", {})
    reviewed_a = set(findings.get("route_a_ids", []))
    if reviewed_a != route_a_ids:
        errors.append("visually reviewed point-a rows do not match catalog routes")
    if not reviewed_a <= catalog_ids:
        errors.append("visual review references unknown catalog IDs")
    if findings.get("route_a_count") != len(route_a_ids):
        errors.append("visual review point-a count mismatch")
    if findings.get("route_b_count") != len(catalog_ids - route_a_ids):
        errors.append("visual review point-b count mismatch")
    if findings.get("total_catalog_rows") != len(catalog_ids):
        errors.append("visual review total-row count mismatch")
    column_order = findings.get("route_column_order", {})
    if column_order.get("left") != ROUTE_B or column_order.get("right") != ROUTE_A:
        errors.append("visual review route-column order mismatch")
    if not column_order.get("header_visually_confirmed"):
        errors.append("visual review did not confirm the table header")
    if review.get("review_status") != "VISUALLY_VERIFIED_AGAINST_CHECKSUM_PINNED_PDF":
        errors.append("visual review has not reached the expected status")
    return errors


def build_decision33_report(
    catalog_path: str | Path,
    visual_review_path: str | Path | None = DEFAULT_VISUAL_REVIEW,
) -> dict[str, object]:
    catalog = load_catalog(catalog_path)
    validation_errors = validate_catalog(catalog)
    catalog_ids = {item.id for item in catalog.items}
    route_a_ids = {
        item.id for item in catalog.items if item.assessment_route == ROUTE_A
    }
    visual_review = _load_visual_review(visual_review_path)
    visual_errors = _validate_visual_review(visual_review, catalog_ids, route_a_ids)
    validation_errors.extend(visual_errors)
    visual_verified = not visual_errors

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
        "assessment_route_visual_review": {
            "status": (
                "VISUALLY_VERIFIED_AGAINST_CHECKSUM_PINNED_PDF"
                if visual_verified
                else "PENDING_OR_INVALID"
            ),
            "overlay_path": str(visual_review_path) if visual_review_path else None,
            "validation_errors": visual_errors,
            "independent_legal_signoff": False,
        },
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
            "G2_conformity_assessment": (
                "ROUTES_VISUALLY_VERIFIED_PENDING_CURRENT_RULE_ENCODING_AND_SECOND_REVIEW"
                if visual_verified
                else "ROUTES_INGESTED_PENDING_SIGNED_PDF_VISUAL_AND_RULE_ENCODING"
            ),
            "draft_four_group_catalog_claims": "SUPERSEDED_BY_FINAL_SIX_SECTOR_CATALOG",
            "legacy_quantitative_tables": "HISTORICAL_ONLY_UNTIL_CURRENT_PROFILE_EXISTS",
        },
        "transition": catalog.transition,
    }
