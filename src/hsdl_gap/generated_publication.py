from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .claim_ledger import build_claim_ledger_report
from .governance_declarations import build_governance_readiness_report
from .stable_id import content_sha256


class GeneratedPublicationError(ValueError):
    """Raised when a claim-led preview cannot be generated safely."""


def _load_json(path: str | Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GeneratedPublicationError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GeneratedPublicationError(f"{label} must be a JSON object")
    return payload


def _validate_spec(spec: Mapping[str, Any]) -> None:
    if spec.get("schema_version") != "1.0.0":
        raise GeneratedPublicationError("unsupported publication preview spec")
    if spec.get("status") != "NOT_AUTHORISED_FOR_PUBLICATION":
        raise GeneratedPublicationError("preview spec must remain publication-blocked")
    if spec.get("claim_class") != "MODEL_RELATIVE":
        raise GeneratedPublicationError("preview spec must be model-relative")
    if spec.get("legal_validation") != "NOT_ASSERTED":
        raise GeneratedPublicationError("preview spec must not assert legal validation")
    sections = spec.get("sections")
    boundaries = spec.get("required_boundaries")
    if not isinstance(sections, list) or not sections:
        raise GeneratedPublicationError("preview spec requires sections")
    if not isinstance(boundaries, list) or not boundaries or not all(
        isinstance(item, str) and item for item in boundaries
    ):
        raise GeneratedPublicationError("preview spec requires boundary statements")
    seen_sections: set[str] = set()
    seen_claims: set[str] = set()
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            raise GeneratedPublicationError(f"sections[{index}] must be an object")
        section_id = section.get("section_id")
        heading = section.get("heading")
        claim_ids = section.get("claim_ids")
        if not isinstance(section_id, str) or not section_id:
            raise GeneratedPublicationError(f"sections[{index}].section_id invalid")
        if section_id in seen_sections:
            raise GeneratedPublicationError(f"duplicate section ID: {section_id}")
        seen_sections.add(section_id)
        if not isinstance(heading, str) or not heading:
            raise GeneratedPublicationError(f"sections[{index}].heading invalid")
        if not isinstance(claim_ids, list) or not claim_ids:
            raise GeneratedPublicationError(f"sections[{index}] needs claim IDs")
        for claim_id in claim_ids:
            if not isinstance(claim_id, str) or not claim_id:
                raise GeneratedPublicationError("claim IDs must be non-empty strings")
            if claim_id in seen_claims:
                raise GeneratedPublicationError(
                    f"claim appears in more than one section: {claim_id}"
                )
            seen_claims.add(claim_id)


def _format_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return "`" + json.dumps(value, sort_keys=True, ensure_ascii=False) + "`"
    if value is None:
        return "`null`"
    if isinstance(value, bool):
        return "`true`" if value else "`false`"
    return f"`{value}`"


def _render_markdown(
    *,
    spec: Mapping[str, Any],
    ledger_report: Mapping[str, Any],
    governance_report: Mapping[str, Any],
) -> str:
    claims = {item["claim_id"]: item for item in ledger_report["claims"]}
    lines = [
        f"# {spec['title']}",
        "",
        "> **NOT AUTHORISED FOR PUBLICATION.** This file is a deterministic engineering preview generated from machine-checked evidence.",
        "",
        "## Scope and boundaries",
        "",
    ]
    lines.extend(f"- {statement}" for statement in spec["required_boundaries"])
    lines.extend(
        [
            f"- Governance status: `{governance_report['status']}`.",
            f"- Claim ledger: `{ledger_report['ledger_id']}` with `{ledger_report['claim_count']}` supported claims.",
            "",
        ]
    )
    for section in spec["sections"]:
        lines.extend([f"## {section['heading']}", ""])
        for claim_id in section["claim_ids"]:
            claim = claims[claim_id]
            lines.extend(
                [
                    f"### `{claim_id}`",
                    "",
                    claim["text"],
                    "",
                    "Evidence:",
                    "",
                ]
            )
            for evidence in claim["evidence"]:
                lines.append(
                    "- "
                    f"`{evidence['artifact']}{evidence['pointer']}` = "
                    f"{_format_value(evidence['actual'])}; artifact hash "
                    f"`{evidence['artifact_sha256']}`."
                )
            lines.append("")
    lines.extend(
        [
            "## Promotion blockers",
            "",
            "- Independent legal review is not included in this preview.",
            "- A reviewed EU–Vietnam crosswalk and reviewed same-slot duty relation remain separate gates.",
            "- External durable custody requires a verified persistent deposit receipt.",
            "- Licence, copyright, author and contributor metadata require owner approval.",
            "- This preview must not replace or silently update a manuscript.",
            "",
        ]
    )
    return "\n".join(lines)


def build_generated_publication_preview(
    *,
    spec_path: str | Path,
    ledger_path: str | Path,
    artifact_dir: str | Path,
    governance_declaration_path: str | Path,
    repository_root: str | Path,
    markdown_output_path: str | Path | None = None,
) -> dict[str, Any]:
    spec = _load_json(spec_path, label="publication preview spec")
    _validate_spec(spec)
    ledger_report = build_claim_ledger_report(
        ledger_path=ledger_path, artifact_dir=artifact_dir
    )
    if ledger_report["status"] != "CLAIM_LEDGER_VALIDATED":
        raise GeneratedPublicationError(
            "publication preview requires a fully validated claim ledger"
        )
    if ledger_report["unsupported_claim_count"] != 0:
        raise GeneratedPublicationError(
            "publication preview refuses unsupported claims"
        )
    governance_report = build_governance_readiness_report(
        governance_declaration_path, repository_root
    )
    report_claims = {item["claim_id"] for item in ledger_report["claims"]}
    spec_claims = {
        claim_id
        for section in spec["sections"]
        for claim_id in section["claim_ids"]
    }
    missing = sorted(spec_claims - report_claims)
    unplaced = sorted(report_claims - spec_claims)
    if missing or unplaced:
        raise GeneratedPublicationError(
            f"preview claim placement mismatch; missing={missing}, unplaced={unplaced}"
        )
    markdown = _render_markdown(
        spec=spec,
        ledger_report=ledger_report,
        governance_report=governance_report,
    )
    if markdown_output_path is not None:
        output = Path(markdown_output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(markdown, encoding="utf-8")
    return {
        "schema_version": "1.0.0",
        "status": "TECHNICAL_PUBLICATION_PREVIEW_GENERATED_NOT_AUTHORISED",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "publication_authorisation": "NOT_PROVIDED",
        "preview_id": spec["preview_id"],
        "title": spec["title"],
        "section_count": len(spec["sections"]),
        "claim_count": ledger_report["claim_count"],
        "evidence_reference_count": ledger_report["evidence_reference_count"],
        "claim_ledger_hash": ledger_report["ledger_hash"],
        "artifact_hashes": ledger_report["artifact_hashes"],
        "governance_status": governance_report["status"],
        "owner_approved": governance_report["owner_approved"],
        "spec_hash": content_sha256(spec),
        "markdown_sha256": content_sha256(markdown),
        "markdown_line_count": len(markdown.splitlines()),
        "markdown_output_path": (
            Path(markdown_output_path).as_posix()
            if markdown_output_path is not None
            else None
        ),
        "boundaries": list(spec["required_boundaries"]),
        "promotion_blockers": [
            "INDEPENDENT_LEGAL_REVIEW_PENDING",
            "REVIEWED_EU_VN_CROSSWALK_PENDING",
            "REVIEWED_SAME_SLOT_DUTY_RELATION_PENDING",
            "EXTERNAL_DURABLE_CUSTODY_RECEIPT_PENDING",
            "OWNER_LICENSE_AND_CITATION_DECLARATION_PENDING",
            "PUBLICATION_AUTHORISATION_NOT_PROVIDED",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spec",
        default="publication/model_relative_technical_preview_spec.json",
    )
    parser.add_argument("--ledger", default="claims/model_relative_claims.json")
    parser.add_argument("--artifact-dir", default="generated")
    parser.add_argument(
        "--governance-declaration",
        default="governance/project_identity_declaration.json",
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument(
        "--markdown-output",
        default="generated/model-relative-technical-preview.md",
    )
    args = parser.parse_args()
    report = build_generated_publication_preview(
        spec_path=args.spec,
        ledger_path=args.ledger,
        artifact_dir=args.artifact_dir,
        governance_declaration_path=args.governance_declaration,
        repository_root=args.repository_root,
        markdown_output_path=args.markdown_output,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
