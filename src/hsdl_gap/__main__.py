from __future__ import annotations

import argparse
import json

from .alignment import build_typed_alignment_audit
from .asean import build_asean_ontology_audit
from .current_report import build_decision33_report
from .provenance import (
    build_source_provenance_report,
    build_source_verification_report,
)
from .report import build_legacy_report
from .review_bundle import build_visual_review_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "legacy",
            "decision33",
            "typed-alignment",
            "asean-ontology",
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
    if args.mode == "decision33":
        report = build_decision33_report(args.catalog)
    elif args.mode == "asean-ontology":
        report = build_asean_ontology_audit(args.asean_ontology)
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


if __name__ == "__main__":
    main()
