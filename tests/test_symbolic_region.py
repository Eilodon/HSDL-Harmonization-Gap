from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.symbolic_region import (
    SymbolicRegionError,
    build_symbolic_catalog_region_report,
    build_symbolic_domain,
    compile_condition_region,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "policies" / "current_candidate_graph_2026-08-02.json"
BINDINGS = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "engineering_fact_bindings.json"
)
ASSUMPTIONS = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "engineering_assumptions.json"
)
CATALOG = ROOT / "catalogs" / "vn_decision_33_2026.csv"
POINT_A = "VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"
POINT_B = "VN_ART13_2B_PROVIDER_OPTION_ROUTE"


class SymbolicRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_symbolic_catalog_region_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
        )

    def test_symbolic_and_finite_oracles_are_equivalent(self) -> None:
        self.assertEqual(
            self.report["status"], "SYMBOLIC_EXPLICIT_ROUTE_ORACLE_EQUIVALENT"
        )
        self.assertEqual(self.report["comparison_count"], 644)
        self.assertEqual(self.report["mismatch_count"], 0)
        self.assertEqual(self.report["mismatch_samples"], [])

    def test_scope_is_explicitly_partial(self) -> None:
        self.assertEqual(self.report["candidate_rule_count"], 20)
        self.assertEqual(self.report["symbolically_compiled_rule_count"], 2)
        self.assertEqual(self.report["symbolic_rule_coverage"], 0.1)
        self.assertFalse(
            self.report["limitations"]["symbolic_current_profile_complete"]
        )
        self.assertEqual(
            self.report["limitations"]["generic_candidate_rules"],
            "NOT_SYMBOLICALLY_COMPILED",
        )

    def test_symbolic_support_counts_lock_route_boundaries(self) -> None:
        self.assertEqual(
            self.report["support_counts"],
            {POINT_A: 24, POINT_B: 160},
        )

    def test_routes_are_disjoint_and_neither_refines_the_other(self) -> None:
        forward = self.report["directed_refinements"][f"{POINT_A}->{POINT_B}"]
        reverse = self.report["directed_refinements"][f"{POINT_B}->{POINT_A}"]
        for result in (forward, reverse):
            self.assertFalse(result["is_subset"])
            self.assertTrue(result["is_disjoint"])
            self.assertIsInstance(result["counterexample"], dict)
            self.assertTrue(result["counterexample"])

    def test_region_constraints_include_known_catalog_identity(self) -> None:
        for rule_id in (POINT_A, POINT_B):
            constraints = self.report["regions"][rule_id]["constraints"]
            self.assertIn("classification.vn.catalog_item_id", constraints)
            self.assertNotIn(None, constraints["classification.vn.catalog_item_id"])
            self.assertEqual(
                constraints["operations.before_use_or_after_significant_change"],
                [True],
            )

    def test_domain_and_report_are_hashed_and_model_relative(self) -> None:
        self.assertRegex(self.report["domain_hash"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")
        self.assertEqual(
            self.report["assumption_set_id"],
            "ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED",
        )

    def test_simple_region_subset_and_counterexample(self) -> None:
        source_condition = {
            "op": "eq",
            "args": [{"field": "x"}, {"literal": "a"}],
        }
        target_condition = {
            "op": "in",
            "args": [{"field": "x"}, {"literal": ["a", "b"]}],
        }
        contexts = ({"x": "a"}, {"x": "b"}, {"x": "c"})
        domain = build_symbolic_domain(
            conditions=(source_condition, target_condition), contexts=contexts
        )
        source = compile_condition_region(
            source_condition, domain=domain, region_id="source"
        )
        target = compile_condition_region(
            target_condition, domain=domain, region_id="target"
        )
        self.assertTrue(source.subset_of(target))
        self.assertFalse(target.subset_of(source))
        self.assertEqual(target.counterexample_not_subset(source), {"x": "b"})

    def test_unsupported_or_is_rejected_instead_of_approximated(self) -> None:
        condition = {
            "op": "or",
            "args": [
                {"op": "eq", "args": [{"field": "x"}, {"literal": "a"}]},
                {"op": "eq", "args": [{"field": "x"}, {"literal": "b"}]},
            ],
        }
        domain = build_symbolic_domain(
            conditions=(condition,), contexts=({"x": "a"}, {"x": "b"})
        )
        with self.assertRaises(SymbolicRegionError):
            compile_condition_region(condition, domain=domain, region_id="unsupported")


if __name__ == "__main__":
    unittest.main()
