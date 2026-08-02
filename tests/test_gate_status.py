from __future__ import annotations

import unittest

from hsdl_gap.gate_status import build_research_gate_status


class GateStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_research_gate_status(
            policy_path="policies/legacy_v11.json",
            duty_semantics_path="alignments/legacy_duty_semantics.json",
            catalog_path="catalogs/vn_decision_33_2026.csv",
            current_candidate_path="policies/current_candidate_graph_2026-08-02.json",
            provision_audit_path="sources/reviews/legacy_v11_provision_audit.json",
            review_template_path="reviews/independent_legal_review_template.json",
        )

    def test_technical_execution_is_ready(self) -> None:
        self.assertEqual(
            self.report["status"],
            "EXECUTION_READY_PUBLICATION_BLOCKED",
        )
        self.assertEqual(self.report["technical_gate_count"], 9)
        self.assertEqual(
            self.report["technical_gates_passed"],
            self.report["technical_gate_count"],
        )
        self.assertTrue(all(self.report["technical_gates"].values()))
        self.assertTrue(
            self.report["technical_gates"]["provisional_current_rule_graph"]
        )

    def test_substantive_publication_gates_remain_closed(self) -> None:
        self.assertEqual(self.report["substantive_gates_passed"], 0)
        self.assertFalse(any(self.report["substantive_gates"].values()))
        self.assertFalse(self.report["attestation"]["publication_ready"])
        self.assertFalse(
            self.report["attestation"]["independent_review_completed"]
        )
        self.assertTrue(
            self.report["attestation"]["provisional_current_graph_exists"]
        )
        self.assertFalse(
            self.report["attestation"]["current_law_quantitative_results_exist"]
        )

    def test_evidence_summary_matches_locked_results(self) -> None:
        evidence = self.report["evidence_summary"]
        self.assertEqual(evidence["decision33_catalog_items"], 46)
        self.assertEqual(evidence["decision33_point_a_routes"], 6)
        self.assertEqual(evidence["decision33_point_b_routes"], 40)
        self.assertEqual(evidence["current_positive_witnesses"], 46)
        self.assertGreater(evidence["provisional_current_binding_rules"], 0)
        self.assertGreater(evidence["provisional_current_normative_slots"], 0)
        self.assertEqual(evidence["provisional_non_binding_policy_objects"], 4)
        self.assertEqual(evidence["legacy_hsdl_comparisons"], 51840)
        self.assertEqual(evidence["legacy_hsdl_mismatches"], 0)
        self.assertEqual(evidence["provision_audited_rules"], 23)
        self.assertEqual(evidence["publication_blocker_rules"], 21)
        self.assertEqual(evidence["independent_review_questions"], 11)
        self.assertEqual(evidence["independent_rule_reviews_required"], 23)
        self.assertEqual(evidence["migration_workstreams"], 6)

    def test_prohibited_claims_are_explicit(self) -> None:
        forbidden = " ".join(self.report["prohibited_actions"])
        self.assertIn("directional percentages", forbidden)
        self.assertIn("1,152", forbidden)
        self.assertIn("H7.1", forbidden)
        self.assertIn("H7.2", forbidden)
        self.assertIn("provisional current rule graph", forbidden)
        self.assertIn("external HSDL", forbidden)


if __name__ == "__main__":
    unittest.main()
