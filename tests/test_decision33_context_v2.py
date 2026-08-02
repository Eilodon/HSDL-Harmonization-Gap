from __future__ import annotations

import unittest
from collections import Counter, defaultdict
from pathlib import Path

from hsdl_gap.context_v2 import FixtureType
from hsdl_gap.decision33_context_v2 import (
    ROUTE_A,
    ROUTE_B,
    build_decision33_context_v2_corpus,
    build_decision33_context_v2_report,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalogs" / "vn_decision_33_2026.csv"


class Decision33ContextV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contexts = build_decision33_context_v2_corpus(CATALOG)
        cls.report = build_decision33_context_v2_report(CATALOG)

    def test_report_is_complete_and_model_relative(self) -> None:
        self.assertEqual(
            self.report["status"], "DECISION33_CONTEXT_V2_CORPUS_COMPLETE"
        )
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")
        self.assertEqual(self.report["validation_errors"], [])

    def test_every_catalog_row_has_seven_contexts(self) -> None:
        self.assertEqual(len(self.contexts), 322)
        self.assertEqual(self.report["positive_witness_count"], 46)
        self.assertEqual(self.report["derived_fixture_count"], 276)
        self.assertEqual(self.report["contexts_per_catalog_row"], 7)

        grouped: dict[str, list[object]] = defaultdict(list)
        for context in self.contexts:
            parent = context.parent_context_id or context.context_id
            grouped[parent].append(context)
        self.assertEqual(len(grouped), 46)
        self.assertTrue(all(len(group) == 7 for group in grouped.values()))

    def test_fixture_counts_are_locked(self) -> None:
        counts = Counter(context.fixture_type for context in self.contexts)
        self.assertEqual(counts[FixtureType.POSITIVE_WITNESS], 46)
        self.assertEqual(counts[FixtureType.SINGLE_FAULT_NEGATIVE], 46)
        self.assertEqual(counts[FixtureType.UNKNOWN_FACT], 92)
        self.assertEqual(counts[FixtureType.BOUNDARY_BELOW], 46)
        self.assertEqual(counts[FixtureType.BOUNDARY_EXACT], 46)
        self.assertEqual(counts[FixtureType.BOUNDARY_ABOVE], 46)

    def test_positive_routes_preserve_six_forty_split(self) -> None:
        self.assertEqual(
            self.report["positive_assessment_route_counts"],
            {ROUTE_A: 6, ROUTE_B: 40},
        )

    def test_nonlisted_controls_remove_identity_and_route(self) -> None:
        controls = [
            context
            for context in self.contexts
            if context.fixture_type is FixtureType.SINGLE_FAULT_NEGATIVE
        ]
        self.assertEqual(len(controls), 46)
        for context in controls:
            vn = context.facts["classification"]["vn"]
            self.assertFalse(vn["listed"])
            self.assertIsNone(vn["catalog_item_id"])
            self.assertIsNone(vn["assessment_route"])
            self.assertEqual(context.provenance["status"], "SYNTHETIC_FIXTURE")
            self.assertEqual(context.provenance["legal_validation"], "NOT_ASSERTED")

    def test_unknown_fixtures_omit_exactly_one_material_fact(self) -> None:
        unknowns = [
            context
            for context in self.contexts
            if context.fixture_type is FixtureType.UNKNOWN_FACT
        ]
        suffix_counts = Counter(context.mutation_id for context in unknowns)
        self.assertEqual(suffix_counts["missing-catalog-id"], 46)
        self.assertEqual(suffix_counts["missing-assessment-route"], 46)
        for context in unknowns:
            vn = context.facts["classification"]["vn"]
            if context.mutation_id == "missing-catalog-id":
                self.assertNotIn("catalog_item_id", vn)
                self.assertIn("assessment_route", vn)
            else:
                self.assertNotIn("assessment_route", vn)
                self.assertIn("catalog_item_id", vn)

    def test_effective_date_boundaries_are_before_exact_after(self) -> None:
        expected = {
            FixtureType.BOUNDARY_BELOW: "2026-08-14",
            FixtureType.BOUNDARY_EXACT: "2026-08-15",
            FixtureType.BOUNDARY_ABOVE: "2026-08-16",
        }
        counts: Counter[FixtureType] = Counter()
        for context in self.contexts:
            if context.fixture_type in expected:
                counts[context.fixture_type] += 1
                self.assertEqual(
                    context.facts["time"]["evaluation_date"],
                    expected[context.fixture_type],
                )
        for fixture_type in expected:
            self.assertEqual(counts[fixture_type], 46)

    def test_all_derived_contexts_reference_positive_parent(self) -> None:
        positive_ids = {
            context.context_id
            for context in self.contexts
            if context.fixture_type is FixtureType.POSITIVE_WITNESS
        }
        for context in self.contexts:
            if context.fixture_type is FixtureType.POSITIVE_WITNESS:
                self.assertIsNone(context.parent_context_id)
            else:
                self.assertIn(context.parent_context_id, positive_ids)

    def test_corpus_explicitly_disclaims_exhaustiveness_and_prevalence(self) -> None:
        contract = self.report["coverage_contract"]
        self.assertFalse(contract["is_exhaustive_real_world_universe"])
        self.assertFalse(contract["supports_empirical_prevalence_inference"])
        self.assertTrue(contract["every_catalog_row_has_positive_witness"])
        self.assertTrue(
            contract["every_catalog_row_has_effective_date_below_exact_above"]
        )

    def test_ids_and_catalog_hash_are_deterministic(self) -> None:
        ids = [context.context_id for context in self.contexts]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertRegex(
            self.report["catalog"]["catalog_hash"], r"^sha256:[0-9a-f]{64}$"
        )
        rebuilt = build_decision33_context_v2_report(CATALOG)
        self.assertEqual(
            rebuilt["catalog"]["catalog_hash"],
            self.report["catalog"]["catalog_hash"],
        )
        self.assertEqual(
            [item["context_id"] for item in rebuilt["contexts"]],
            [item["context_id"] for item in self.report["contexts"]],
        )


if __name__ == "__main__":
    unittest.main()
