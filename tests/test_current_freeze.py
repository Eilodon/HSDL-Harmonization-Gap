from __future__ import annotations

import json
import unittest
from pathlib import Path

from hsdl_gap.current_candidate import build_current_candidate_report
from hsdl_gap.provision_audit import build_provision_audit_report


FREEZE = Path("sources/current_freeze_2026-08-02.json")
LOCK = Path("sources/official_pdf_lock_2026-08-02.json")
VISUAL = Path("sources/reviews/vn_decision_33_2026.visual.json")
AUDIT = "sources/reviews/legacy_v11_provision_audit.json"
POLICIES = "policies/legacy_v11.json"
CANDIDATE = "policies/current_candidate_graph_2026-08-02.json"


class CurrentFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
        cls.lock = json.loads(LOCK.read_text(encoding="utf-8"))
        cls.visual = json.loads(VISUAL.read_text(encoding="utf-8"))

    def test_freeze_status_is_execution_ready_but_publication_blocked(self) -> None:
        self.assertEqual(self.freeze["schema_version"], "0.4.0")
        self.assertEqual(
            self.freeze["status"],
            "EXECUTION_READY_PARTIAL_LEGAL_FREEZE_PUBLICATION_BLOCKED",
        )
        attestation = self.freeze["attestation"]
        self.assertTrue(attestation["technical_execution_ready"])
        self.assertFalse(attestation["independent_review_completed"])
        self.assertFalse(attestation["current_law_quantitative_results_exist"])
        self.assertFalse(attestation["publication_ready"])

    def test_source_identities_match_pinned_lock(self) -> None:
        freeze_sources = {source["id"]: source for source in self.freeze["sources"]}
        lock_sources = {source["id"]: source for source in self.lock["artifacts"]}
        self.assertEqual(set(freeze_sources), set(lock_sources))
        self.assertEqual(len(freeze_sources), 6)
        for source_id, locked in lock_sources.items():
            frozen = freeze_sources[source_id]
            self.assertEqual(frozen["official_pdf_url"], locked["official_pdf_url"])
            self.assertEqual(frozen["declared_page_count"], locked["declared_page_count"])
            self.assertEqual(frozen["byte_size"], locked["byte_size"])
            self.assertEqual(frozen["sha256"], locked["sha256"])
            self.assertEqual(len(frozen["sha256"]), 64)

    def test_decision33_internal_visual_status_matches_overlay(self) -> None:
        review = self.freeze["internal_review"]["decision33_visual_overlay"]
        findings = self.visual["findings"]
        self.assertEqual(review["status"], "COMPLETE_AGAINST_CHECKSUM_PINNED_PDF")
        self.assertEqual(review["point_a_routes"], findings["route_a_count"])
        self.assertEqual(review["point_b_routes"], findings["route_b_count"])
        self.assertFalse(review["independent_legal_signoff"])

    def test_provision_audit_summary_matches_validated_report(self) -> None:
        report = build_provision_audit_report(POLICIES, AUDIT)
        review = self.freeze["internal_review"]["legacy_rule_provision_audit"]
        self.assertEqual(report["status"], "VALIDATED")
        self.assertEqual(review["status"], "VALIDATED_23_OF_23_RULES")
        self.assertEqual(report["audited_rule_count"], 23)
        self.assertEqual(
            review["publication_blocker_rules"],
            report["counts"]["publication_blockers"],
        )
        self.assertEqual(
            set(review["unsupported_rule_ids"]),
            set(report["unsupported_rule_ids"]),
        )
        self.assertFalse(review["independent_legal_signoff"])

    def test_provisional_graph_status_matches_validator(self) -> None:
        report = build_current_candidate_report(CANDIDATE)
        review = self.freeze["internal_review"]["provisional_current_graph"]
        self.assertEqual(report["status"], "VALIDATED_PROVISIONAL_GRAPH")
        self.assertEqual(review["status"], report["status"])
        self.assertFalse(review["quantitative_evaluation_allowed"])
        self.assertFalse(review["directional_gap_metrics_allowed"])
        self.assertFalse(review["actor_mismatch_metrics_allowed"])
        self.assertFalse(review["independent_legal_signoff"])

    def test_publication_gates_remain_blocked(self) -> None:
        gates = self.freeze["gates"]
        self.assertEqual(gates["official_pdf_endpoint"], "COMPLETE")
        self.assertEqual(gates["sha256_identity"], "COMPLETE_AND_REVERIFIED")
        self.assertEqual(gates["decision33_route_table_visual_review"], "COMPLETE_INTERNAL_REVIEW")
        self.assertEqual(gates["legacy_rule_provision_audit"], "COMPLETE_INTERNAL_REVIEW")
        self.assertEqual(gates["independent_legal_policy_review"], "PENDING")
        self.assertEqual(gates["shared_current_classification_relation"], "PENDING")
        self.assertEqual(gates["current_law_quantitative_claims"], "BLOCKED")
        self.assertEqual(gates["manuscript_regeneration"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
