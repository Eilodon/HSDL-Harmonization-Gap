from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.provision_audit import (
    build_provision_audit_report,
    validate_provision_audit,
)


POLICIES = "policies/legacy_v11.json"
AUDIT = "sources/reviews/legacy_v11_provision_audit.json"


class ProvisionAuditTests(unittest.TestCase):
    def test_all_frozen_rules_are_covered(self) -> None:
        self.assertEqual(validate_provision_audit(POLICIES, AUDIT), [])
        report = build_provision_audit_report(POLICIES, AUDIT)
        self.assertEqual(report["status"], "VALIDATED")
        self.assertEqual(report["policy_rule_count"], 23)
        self.assertEqual(report["audited_rule_count"], 23)
        self.assertEqual(report["counts"]["by_jurisdiction"], {"ASEAN": 4, "EU": 8, "VN": 11})

    def test_unsupported_and_duplicate_rules_are_explicit(self) -> None:
        report = build_provision_audit_report(POLICIES, AUDIT)
        self.assertEqual(
            report["unsupported_rule_ids"],
            ["VN_G2_ART13_REUSE", "VN_G6_ND142_EVENT"],
        )
        payload = json.loads(Path(AUDIT).read_text(encoding="utf-8"))
        dispositions = {row["rule_id"]: row["disposition"] for row in payload["rules"]}
        self.assertEqual(
            dispositions["EU_G6_ART9"],
            "DUPLICATE_CROSS_GROUP_ENCODING",
        )

    def test_current_results_and_manuscript_regeneration_remain_blocked(self) -> None:
        report = build_provision_audit_report(POLICIES, AUDIT)
        self.assertEqual(report["promotion_gate"]["legacy_results"], "HISTORICAL_ONLY")
        self.assertEqual(
            report["promotion_gate"]["current_law_results"],
            "BLOCKED_PENDING_REENCODE_AND_INDEPENDENT_REVIEW",
        )
        self.assertEqual(report["promotion_gate"]["manuscript_regeneration"], "BLOCKED")
        self.assertFalse(report["attestation"]["independent_legal_review"])

    def test_missing_rule_is_rejected(self) -> None:
        payload = json.loads(Path(AUDIT).read_text(encoding="utf-8"))
        payload["rules"] = payload["rules"][:-1]
        payload["summary"]["rule_count"] -= 1
        if payload["rules"][-1]["publication_blocker"]:
            payload["summary"]["publication_blocker_count"] -= 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            errors = validate_provision_audit(POLICIES, path)
        self.assertTrue(any("missing from audit" in error for error in errors))

    def test_independent_review_cannot_be_claimed_silently(self) -> None:
        payload = json.loads(Path(AUDIT).read_text(encoding="utf-8"))
        payload["evidence"]["independent_human_legal_reviewer"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            errors = validate_provision_audit(POLICIES, path)
        self.assertTrue(any("must not claim independent legal review" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
