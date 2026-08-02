from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .loader import load_policy_bundle


class ProvisionAuditError(ValueError):
    """Raised when a provision audit is incomplete or internally inconsistent."""


def load_provision_audit(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProvisionAuditError("provision audit must be a JSON object")
    return payload


def _policy_rules(policy_path: str | Path) -> dict[str, dict[str, str]]:
    policies = load_policy_bundle(policy_path)
    rows: dict[str, dict[str, str]] = {}
    for jurisdiction, policy in policies.items():
        for rule in policy.rules:
            if rule.id in rows:
                raise ProvisionAuditError(f"duplicate policy rule id: {rule.id}")
            rows[rule.id] = {
                "jurisdiction": jurisdiction,
                "group": rule.group,
                "instrument": rule.instrument,
                "provision": rule.provision,
            }
    return rows


def validate_provision_audit(
    policy_path: str | Path,
    audit_path: str | Path,
) -> list[str]:
    policy_rules = _policy_rules(policy_path)
    payload = load_provision_audit(audit_path)
    errors: list[str] = []

    if payload.get("schema_version") != "1.0.0":
        errors.append("unsupported provision-audit schema_version")
    allowed = payload.get("allowed_dispositions")
    if not isinstance(allowed, list) or not allowed or not all(
        isinstance(value, str) and value for value in allowed
    ):
        errors.append("allowed_dispositions must be a non-empty string list")
        allowed_set: set[str] = set()
    else:
        allowed_set = set(allowed)
        if len(allowed_set) != len(allowed):
            errors.append("allowed_dispositions contains duplicates")

    rows = payload.get("rules")
    if not isinstance(rows, list):
        return errors + ["rules must be a list"]

    audited_ids: list[str] = []
    blocker_count = 0
    for index, row in enumerate(rows):
        prefix = f"rules[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rule_id = row.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id:
            errors.append(f"{prefix}.rule_id must be a non-empty string")
            continue
        audited_ids.append(rule_id)
        if rule_id not in policy_rules:
            errors.append(f"{prefix} references unknown policy rule: {rule_id}")
        source_id = row.get("source_id")
        if not isinstance(source_id, str) or not source_id:
            errors.append(f"{prefix}.source_id must be a non-empty string")
        locator = row.get("locator")
        if not isinstance(locator, dict) or not locator:
            errors.append(f"{prefix}.locator must be a non-empty object")
        else:
            pages = locator.get("pdf_pages")
            if not isinstance(pages, list) or not pages or not all(
                isinstance(page, int) and page > 0 for page in pages
            ):
                errors.append(f"{prefix}.locator.pdf_pages must contain positive integers")
            if not any(
                isinstance(locator.get(key), str) and locator.get(key)
                for key in ("provision", "section")
            ):
                errors.append(f"{prefix}.locator needs a provision or section string")
        disposition = row.get("disposition")
        if disposition not in allowed_set:
            errors.append(f"{prefix}.disposition is not allowed: {disposition!r}")
        blocker = row.get("publication_blocker")
        if not isinstance(blocker, bool):
            errors.append(f"{prefix}.publication_blocker must be boolean")
        elif blocker:
            blocker_count += 1
        findings = row.get("findings")
        if not isinstance(findings, list) or not findings or not all(
            isinstance(finding, str) and finding for finding in findings
        ):
            errors.append(f"{prefix}.findings must be a non-empty string list")
        required_change = row.get("required_change")
        if not isinstance(required_change, str) or not required_change:
            errors.append(f"{prefix}.required_change must be a non-empty string")

    duplicates = sorted(
        rule_id for rule_id, count in Counter(audited_ids).items() if count > 1
    )
    if duplicates:
        errors.append(f"duplicate audited rule ids: {duplicates}")

    audited_set = set(audited_ids)
    missing = sorted(set(policy_rules) - audited_set)
    unexpected = sorted(audited_set - set(policy_rules))
    if missing:
        errors.append(f"policy rules missing from audit: {missing}")
    if unexpected:
        errors.append(f"audit contains unknown rules: {unexpected}")

    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
    else:
        if summary.get("rule_count") != len(rows):
            errors.append("summary.rule_count does not match audited rows")
        if summary.get("publication_blocker_count") != blocker_count:
            errors.append(
                "summary.publication_blocker_count does not match audited rows"
            )
        if summary.get("current_quantitative_reuse") != "BLOCKED":
            errors.append("summary must block current quantitative reuse")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
    elif evidence.get("independent_human_legal_reviewer") is not False:
        errors.append(
            "this audit must not claim independent legal review before sign-off"
        )
    return errors


def build_provision_audit_report(
    policy_path: str | Path,
    audit_path: str | Path,
) -> dict[str, Any]:
    policy_rules = _policy_rules(policy_path)
    payload = load_provision_audit(audit_path)
    errors = validate_provision_audit(policy_path, audit_path)
    rows = payload.get("rules", []) if isinstance(payload.get("rules"), list) else []

    disposition_counts = Counter()
    jurisdiction_counts = Counter()
    group_counts = Counter()
    blocker_ids: list[str] = []
    unsupported_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or row.get("rule_id") not in policy_rules:
            continue
        rule_id = row["rule_id"]
        metadata = policy_rules[rule_id]
        disposition = row.get("disposition", "<missing>")
        disposition_counts[disposition] += 1
        jurisdiction_counts[metadata["jurisdiction"]] += 1
        group_counts[metadata["group"]] += 1
        if row.get("publication_blocker") is True:
            blocker_ids.append(rule_id)
        if disposition == "UNSUPPORTED_BY_CITED_PROVISION":
            unsupported_ids.append(rule_id)

    return {
        "schema_version": "1.0.0",
        "audit_id": payload.get("audit_id"),
        "status": "VALIDATED" if not errors else "INVALID",
        "policy_rule_count": len(policy_rules),
        "audited_rule_count": len(rows),
        "validation_errors": errors,
        "counts": {
            "by_disposition": dict(sorted(disposition_counts.items())),
            "by_jurisdiction": dict(sorted(jurisdiction_counts.items())),
            "by_group": dict(sorted(group_counts.items())),
            "publication_blockers": len(blocker_ids),
            "unsupported_by_cited_provision": len(unsupported_ids),
        },
        "publication_blocker_rule_ids": sorted(blocker_ids),
        "unsupported_rule_ids": sorted(unsupported_ids),
        "promotion_gate": {
            "legacy_results": "HISTORICAL_ONLY",
            "current_law_results": (
                "BLOCKED_PENDING_REENCODE_AND_INDEPENDENT_REVIEW"
            ),
            "manuscript_regeneration": "BLOCKED",
        },
        "attestation": {
            "independent_legal_review": False,
            "source_identity": "CHECKSUM_PINNED",
            "provision_review": "AUTHOR_AND_ASSISTANT_SOURCE_AUDIT",
        },
    }
