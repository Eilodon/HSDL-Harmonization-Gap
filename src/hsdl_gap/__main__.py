from __future__ import annotations

import argparse
import json

from .alignment import build_typed_alignment_audit
from .asean import build_asean_ontology_audit
from .current_context import build_current_context_report
from .current_report import build_decision33_report
from .gate_status import build_research_gate_status
from .hsdl_core import build_hsdl_differential_report, emit_hsdl_core
from .migration_plan import build_migration_plan
from .provision_audit import build_provision_audit_report
from .report import build_legacy_report
from .review_bundle import build_visual_review_bundle
from .reviewer_signoff import build_review_readiness_report
from .robust_provenance import (
    build_source_provenance_report,
    build_source_verification_report,
)
from .typed_cover import build_typed_cover_audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "legacy",
            "decision33",
            "current-context",
            "typed-alignment",
            "asean-ontology",
            "typed-cover",
            "provision-audit",
            "review-readiness",
            "migration-plan",
            "gate-status",
            "emit-hsdl",
            "hsdl-differential",
            "acquire-sources",
            "verify-sources",
            "build-review-bundle",
        ),
        default="legacy",
    )
    parser.add_argument("--policies", default="policies/legacy_v11.json")
    parser.add_argument("--catalog", default="catalogs/vn_decision_33_2026.csv")
    parser.add_argument("--asean-ontology", default="asean/guide_ontology_2024_2025.json")
    parser.add_argument(
        "--provision-audit",
        default="sources/reviews/legacy_v11_provision_audit.json",
    )
    parser.add_argument(
        "--review-template",
        default="reviews/independent_legal_review_template.json",
    )
    parser.add_argument(
        "--targets",
        default="sources/official_pdf_targets.json",
    )
    parser.add_argument(
        "--lock",
        default="sources/official_pdf_lock_2026-08-02.json",
    )
    parser.add_argument(
        "--output-dir",
        default="generated/source-review-bundle",
    )
    parser.add_argument(
        "--crosswalk",
        default="alignments/legacy_obligation_crosswalk.json",
    )
    parser.add_argument(
        "--semantics",
        default="alignments/legacy_duty_semantics.json",
    )
    args = parser.parse_args()

    if args.mode == "emit-hsdl":
        print(emit_hsdl_core(args.policies, args.semantics), end="")
        return
    if args.mode == "decision33":
        report = build_decision33_report(args.catalog)
    elif args.mode == "current-context":
        report = build_current_context_report(args.catalog)
    elif args.mode == "asean-ontology":
        report = build_asean_ontology_audit(args.asean_ontology)
    elif args.mode == "typed-cover":
        report = build_typed_cover_audit(args.policies, args.semantics)
    elif args.mode == "provision-audit":
        report = build_provision_audit_report(args.policies, args.provision_audit)
    elif args.mode == "review-readiness":
        report = build_review_readiness_report(
            args.review_template,
            args.provision_audit,
        )
    elif args.mode == "migration-plan":
        report = build_migration_plan(args.provision_audit)
    elif args.mode == "gate-status":
        report = build_research_gate_status(
            policy_path=args.policies,
            duty_semantics_path=args.semantics,
            catalog_path=args.catalog,
            provision_audit_path=args.provision_audit,
            review_template_path=args.review_template,
        )
    elif args.mode == "hsdl-differential":
        report = build_hsdl_differential_report(args.policies, args.semantics)
    elif args.mode == "acquire-sources":
        report = build_source_provenance_report(args.targets)
    elif args.mode == "verify-sources":
        report = build_source_verification_report(args.targets, args.lock)
    elif args.mode == "build-review-bundle":
        report = build_visual_review_bundle(args.lock, args.output_dir)
    elif args.mode == "typed-alignment":
        report = build_typed_alignment_audit(
            args.policies, args.crosswalk, duty_semantics_path=args.semantics
        )
    else:
        report = build_legacy_report(args.policies)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if args.mode == "acquire-sources" and report["status"] != "COMPLETE":
        raise SystemExit(2)
    if args.mode == "verify-sources" and report["status"] != "VERIFIED":
        raise SystemExit(3)
    if (
        args.mode == "build-review-bundle"
        and report["status"] != "CHECKSUM_VERIFIED_AND_RENDERED"
    ):
        raise SystemExit(4)
    if args.mode == "hsdl-differential" and report["status"] != "EQUIVALENT":
        raise SystemExit(5)
    if args.mode == "provision-audit" and report["status"] != "VALIDATED":
        raise SystemExit(6)
    if args.mode == "review-readiness" and report["status"] != "READY_FOR_ASSIGNMENT":
        raise SystemExit(7)
    if args.mode == "migration-plan" and report["status"] != "READY_FOR_REVIEWED_REENCODING":
        raise SystemExit(8)
    if args.mode == "gate-status" and report["status"] != "EXECUTION_READY_PUBLICATION_BLOCKED":
        raise SystemExit(9)


if __name__ == "__main__":
    main()
