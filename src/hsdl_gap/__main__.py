from __future__ import annotations

import argparse
import json

from .alignment import build_typed_alignment_audit
from .asean import build_asean_ontology_audit
from .current_report import build_decision33_report
from .provenance import build_source_provenance_report
from .report import build_legacy_report


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
    elif args.mode == "typed-alignment":
        report = build_typed_alignment_audit(
            args.policies, args.crosswalk, duty_semantics_path=args.semantics
        )
    else:
        report = build_legacy_report(args.policies)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if args.mode == "acquire-sources" and report["status"] != "COMPLETE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
