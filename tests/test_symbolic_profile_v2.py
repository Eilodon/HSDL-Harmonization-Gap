from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.symbolic_profile_v2 import (
    SymbolicProfileError,
    build_symbolic_profile_v2_report,
    collect_domains,
    symbolic_evaluate,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "policies" / "current_candidate_graph_2026-08-02.json"
PROFILE = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "source_derived_predicates.json"
)


class SymbolicProfileV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_symbolic_profile_v2_report(CANDIDATE, PROFILE)

    def test_all_twenty_rule_predicates_are_symbolically_compiled(self) -> None:
        self.assertEqual(self.report["candidate_rule_count"], 20)
        self.assertEqual(self.report["symbolically_compiled_rule_count"], 20)
        self.assertEqual(self.report["symbolic_rule_coverage"], 1.0)

    def test_all_conditional_duty_triggers_are_compiled(self) -> None:
        self.assertEqual(self.report["duty_trigger_expression_count"], 5)
        self.assertEqual(self.report["expression_count"], 25)
        trigger_ids = {
            item["expression_id"]
            for item in self.report["expressions"]
            if item["expression_kind"] == "DUTY_TRIGGER"
        }
        self.assertIn(
            "duty-trigger:VN_ND142_ART19_4_PRELIMINARY_REPORTING:serious_incident_preliminary_report_fallback",
            trigger_ids,
        )
        self.assertIn(
            "duty-trigger:EU_ART43_CONFORMITY_ASSESSMENT:notified_body_participation",
            trigger_ids,
        )

    def test_independent_symbolic_evaluator_matches_canonical(self) -> None:
        self.assertEqual(
            self.report["status"],
            "SOURCE_DERIVED_SYMBOLIC_PROFILE_EQUIVALENT",
        )
        self.assertEqual(self.report["mismatch_count"], 0)
        self.assertEqual(self.report["mismatch_samples"], [])
        self.assertGreater(self.report["comparison_count"], 100)
        self.assertTrue(
            all(item["mismatch_count"] == 0 for item in self.report["expressions"])
        )

    def test_every_nonconstant_expression_has_missing_fact_probes(self) -> None:
        for item in self.report["expressions"]:
            if item["field_count"] == 0:
                self.assertEqual(item["missing_probe_count"], 0)
            else:
                self.assertEqual(
                    item["missing_probe_count"], item["field_count"]
                )
                self.assertGreater(item["unknown_probe_count"], 0)

    def test_or_and_not_in_semantics_are_supported(self) -> None:
        condition = {
            "op": "and",
            "args": [
                {
                    "op": "or",
                    "args": [
                        {
                            "op": "eq",
                            "args": [{"field": "x"}, {"literal": "a"}],
                        },
                        {
                            "op": "eq",
                            "args": [{"field": "x"}, {"literal": "b"}],
                        },
                    ],
                },
                {
                    "op": "not_in",
                    "args": [{"field": "y"}, {"literal": ["blocked"]}],
                },
            ],
        }
        domains = collect_domains(condition)
        self.assertEqual(set(domains), {"x", "y"})
        self.assertEqual(symbolic_evaluate(condition, {"x": "a", "y": "ok"})[0], "TRUE")
        self.assertEqual(symbolic_evaluate(condition, {"x": "z", "y": "ok"})[0], "FALSE")
        unknown = symbolic_evaluate(condition, {"x": "a"})
        self.assertEqual(unknown[0], "UNKNOWN")
        self.assertEqual(unknown[1], ("y",))

    def test_unsupported_future_operator_fails_closed(self) -> None:
        condition = {
            "op": "gte",
            "args": [{"field": "score"}, {"literal": 1}],
        }
        with self.assertRaises(SymbolicProfileError):
            collect_domains(condition)
        with self.assertRaises(SymbolicProfileError):
            symbolic_evaluate(condition, {"score": 2})

    def test_symbolic_claim_boundary_is_explicit(self) -> None:
        self.assertTrue(self.report["limitations"]["finite_domain"])
        self.assertEqual(
            self.report["limitations"]["unbounded_symbolic_theorem"],
            "NOT_CLAIMED",
        )
        self.assertEqual(
            self.report["limitations"]["independent_legal_review"], "PENDING"
        )
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
