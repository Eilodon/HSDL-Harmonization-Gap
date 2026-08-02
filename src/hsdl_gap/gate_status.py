from __future__ import annotations

from pathlib import Path
from typing import Any

from .current_context import build_current_context_report
from .current_report import build_decision33_report
from .hsdl_core import build_hsdl_differential_report
from .migration_plan import build_migration_plan
from .provision_audit import build_provision_audit_report
from .reviewer_signoff import build_review_readiness_report
from .typed_cover import build_typed_cover_audit


def build_research_gate_status(
    *,
    policy_path: str | Path,
    duty_semantics_path: str | Path,
    catalog_path: str | Path,
    provision_audit_path: str | Path,
    review_template_path: str | Path,
) -> dict[str, Any]:
    decision33 = build_decision33_report(catalog_path)
    current_context = build_current_context_report(catalog_path)
    hsdl = build_hsdl_differential_report(policy_path, duty_semantics_path)
    cover = build_typed_cover_audit(policy_path, duty_semantics_path)
    provision = build_provision_audit_report(policy_path, provision_audit_path)
    review = build_review_readiness_report(
        review_template_path,
        provision_audit_path,
    )
    migration = build_migration_plan(provision_audit_path)

    technical_gates = {
        "decision33_route_visual_review": (
            decision33["assessment_route_visual_review"]["status"]
            == "VISUALLY_VERIFIED_AGAINST_CHECKSUM_PINNED_PDF"
        ),
        "decision33_catalog_validation": not decision33["validation_errors"],
        "current_context_witness_profile": (
            current_context["status"]
            == "CATALOG_DRIVEN_POSITIVE_WITNESSES_COMPLETE"
        ),
        "legacy_hsdl_roundtrip": hsdl["status"] == "EQUIVALENT",
        "typed_cover_finite_oracle": (
            cover["status"] == "FINITE_TYPED_COVER_ORACLE_COMPLETE"
        ),
        "provision_audit_coverage": provision["status"] == "VALIDATED",
        "independent_review_packet": review["status"] == "READY_FOR_ASSIGNMENT",
        "migration_plan": migration["status"] == "READY_FOR_REVIEWED_REENCODING",
    }
    technical_ready = all(technical_gates.values())

    substantive_gates = {
        "independent_legal_review": False,
        "current_eu_vn_rule_reencoding": False,
        "shared_current_classification_relation": False,
        "negative_and_boundary_contexts": False,
        "current_profile_hsdl_differential": False,
        "current_profile_typed_cover": False,
        "legacy_to_current_change_log": False,
        "durable_source_custody": False,
        "cryptographic_signature_validation": False,
        "manuscript_claim_regeneration": False,
    }

    allowed_actions = [
        "Preserve and reproduce the frozen historical model.",
        "Implement provisional current-profile schemas and typed rules.",
        "Apply corrections that do not depend on disputed legal interpretation.",
        "Prepare and assign the independent review packet.",
        "Add tests, provenance, change logs and reviewer evidence.",
    ]
    prohibited_actions = [
        "Publish current-law directional percentages.",
        "Present the 1,152 legacy flattened gaps as exact actor mismatches.",
        "Reuse H7.1 without a shared current classification relation and negative cases.",
        "Reuse H7.2 as a single-valued ASEAN harm partition.",
        "Present the finite typed-cover oracle as the symbolic theorem implementation.",
        "Regenerate final manuscripts as legally reviewed current-law results.",
        "Claim external HSDL or HolySeed compatibility.",
    ]

    return {
        "schema_version": "1.0.0",
        "status": (
            "EXECUTION_READY_PUBLICATION_BLOCKED"
            if technical_ready and not all(substantive_gates.values())
            else "TECHNICAL_GATES_INCOMPLETE"
        ),
        "technical_gate_count": len(technical_gates),
        "technical_gates_passed": sum(technical_gates.values()),
        "technical_gates": technical_gates,
        "substantive_gate_count": len(substantive_gates),
        "substantive_gates_passed": sum(substantive_gates.values()),
        "substantive_gates": substantive_gates,
        "evidence_summary": {
            "decision33_catalog_items": decision33["item_count"],
            "decision33_point_a_routes": decision33["assessment_route_counts"].get(
                "ARTICLE_13_2_A_THIRD_PARTY_CERTIFICATION", 0
            ),
            "decision33_point_b_routes": decision33["assessment_route_counts"].get(
                "ARTICLE_13_2_B_PROVIDER_SELF_OR_THIRD_PARTY", 0
            ),
            "current_positive_witnesses": current_context["witness_count"],
            "legacy_hsdl_comparisons": hsdl["comparison_count"],
            "legacy_hsdl_mismatches": hsdl["mismatch_count"],
            "provision_audited_rules": provision["audited_rule_count"],
            "publication_blocker_rules": provision["counts"][
                "publication_blockers"
            ],
            "independent_review_questions": review["required_question_count"],
            "independent_rule_reviews_required": review[
                "required_rule_review_count"
            ],
            "migration_workstreams": len(migration["workstreams"]),
        },
        "allowed_actions": allowed_actions,
        "prohibited_actions": prohibited_actions,
        "next_gate_sequence": [
            "Assign and complete independent legal/policy review.",
            "Apply reviewer decisions to the 23-rule migration plan.",
            "Implement the shared current EU–Vietnam classification relation.",
            "Encode current EU and Vietnam typed policy graphs.",
            "Generate negative and boundary contexts, not only positive catalog witnesses.",
            "Run current-profile HSDL differential and typed-cover audits.",
            "Generate a reason-coded legacy-to-current change log.",
            "Regenerate quantitative and manuscript claims only after all gates pass.",
        ],
        "attestation": {
            "independent_review_completed": False,
            "current_law_quantitative_results_exist": False,
            "publication_ready": False,
            "notice": (
                "Technical readiness means the project can proceed with a controlled "
                "re-encoding. It does not mean the legal analysis or manuscripts are ready "
                "for publication."
            ),
        },
    }
