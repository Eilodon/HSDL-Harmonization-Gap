from __future__ import annotations

import unittest
from collections import Counter
from pathlib import Path

from hsdl_gap.context_v2 import FixtureType
from hsdl_gap.decision33_context_v2 import build_decision33_context_v2_corpus
from hsdl_gap.eu_context_v2 import (
    EUClassificationState,
    build_decision33_eu_relation_scenario_report,
    build_eu_article6_context_corpus,
    build_eu_article6_context_report,
    classify_eu_article6,
    overlay_decision33_with_eu_scenario,
    _load_profile,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "eu_native_classification_profile.json"
)
CATALOG = ROOT / "catalogs" / "vn_decision_33_2026.csv"


class EUContextV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = _load_profile(PROFILE)
        cls.contexts = build_eu_article6_context_corpus(PROFILE)
        cls.report = build_eu_article6_context_report(PROFILE)
        cls.relation_report = build_decision33_eu_relation_scenario_report(
            PROFILE, CATALOG
        )

    def test_nine_native_routes_have_four_fixtures_each(self) -> None:
        self.assertEqual(len(self.contexts), 36)
        self.assertEqual(self.report["native_route_count"], 9)
        self.assertEqual(self.report["contexts_per_native_route"], 4)
        self.assertEqual(
            self.report["fixture_counts"],
            {
                "BOUNDARY_EXACT": 9,
                "POSITIVE_WITNESS": 9,
                "SINGLE_FAULT_NEGATIVE": 9,
                "UNKNOWN_FACT": 9,
            },
        )

    def test_native_corpus_exercises_in_out_and_unknown(self) -> None:
        self.assertEqual(
            self.report["classification_state_counts"],
            {"IN_SCOPE": 18, "OUT_OF_SCOPE": 9, "UNKNOWN": 9},
        )
        self.assertEqual(
            self.report["status"], "EU_ARTICLE6_CONTEXT_V2_CORPUS_COMPLETE"
        )
        self.assertEqual(self.report["validation_errors"], [])

    def test_article_6_1_requires_both_cumulative_conditions(self) -> None:
        product = next(
            context
            for context in self.contexts
            if context.fixture_type is FixtureType.POSITIVE_WITNESS
            and context.facts["classification"]["eu"]["route_type"]
            == "ARTICLE_6_1_PRODUCT"
        )
        children = [
            context
            for context in self.contexts
            if context.parent_context_id == product.context_id
        ]
        states = {
            child.fixture_type: classify_eu_article6(child.facts).state
            for child in children
        }
        self.assertEqual(
            classify_eu_article6(product.facts).state,
            EUClassificationState.IN_SCOPE,
        )
        self.assertEqual(
            states[FixtureType.SINGLE_FAULT_NEGATIVE],
            EUClassificationState.OUT_OF_SCOPE,
        )
        self.assertEqual(
            states[FixtureType.UNKNOWN_FACT], EUClassificationState.UNKNOWN
        )
        self.assertEqual(
            states[FixtureType.BOUNDARY_EXACT], EUClassificationState.IN_SCOPE
        )

    def test_profiling_overrides_article_6_3_exception(self) -> None:
        boundaries = [
            context
            for context in self.contexts
            if context.fixture_type is FixtureType.BOUNDARY_EXACT
            and context.facts["classification"]["eu"]["route_type"]
            == "ARTICLE_6_2_ANNEX_III"
        ]
        self.assertEqual(len(boundaries), 8)
        for context in boundaries:
            eu = context.facts["classification"]["eu"]
            self.assertTrue(eu["profiling_natural_persons"])
            self.assertFalse(eu["significant_risk_or_material_influence"])
            result = classify_eu_article6(context.facts)
            self.assertEqual(result.state, EUClassificationState.IN_SCOPE)

    def test_article_6_3_negative_is_not_treated_as_unknown(self) -> None:
        negatives = [
            context
            for context in self.contexts
            if context.fixture_type is FixtureType.SINGLE_FAULT_NEGATIVE
            and context.facts["classification"]["eu"]["route_type"]
            == "ARTICLE_6_2_ANNEX_III"
        ]
        self.assertEqual(len(negatives), 8)
        self.assertTrue(
            all(
                classify_eu_article6(context.facts).state
                is EUClassificationState.OUT_OF_SCOPE
                for context in negatives
            )
        )

    def test_both_relation_scenarios_execute_all_322_contexts(self) -> None:
        self.assertEqual(self.relation_report["scenario_count"], 2)
        self.assertEqual(self.relation_report["context_count_per_scenario"], 322)
        for scenario in self.relation_report["scenarios"]:
            self.assertEqual(scenario["context_count"], 322)
            self.assertEqual(sum(scenario["mapping_counts"].values()), 322)
            self.assertEqual(sum(scenario["eu_state_counts"].values()), 322)
            self.assertEqual(sum(scenario["relation_counts"].values()), 322)

    def test_open_world_preserves_unknown_and_closed_world_fills_eu_state(self) -> None:
        scenarios = {
            item["scenario_id"]: item for item in self.relation_report["scenarios"]
        }
        open_world = scenarios["EU_SOURCE_ANCHORED_OPEN_WORLD"]
        closed_world = scenarios["EU_EXPERIMENTAL_CLOSED_WORLD"]
        self.assertGreater(open_world["eu_state_counts"].get("IN_SCOPE", 0), 0)
        self.assertGreater(open_world["eu_state_counts"].get("UNKNOWN", 0), 0)
        self.assertEqual(closed_world["eu_state_counts"].get("UNKNOWN", 0), 0)
        self.assertEqual(
            sum(closed_world["eu_state_counts"].values()), 322
        )
        self.assertFalse(
            self.relation_report["completeness"][
                "closed_world_is_legal_classification"
            ]
        )

    def test_vn_fixture_mutations_do_not_silently_change_eu_mapping(self) -> None:
        corpus = build_decision33_context_v2_corpus(CATALOG)
        scenario = next(
            item
            for item in self.profile["decision33_overlay_scenarios"]
            if item["scenario_id"] == "EU_SOURCE_ANCHORED_OPEN_WORLD"
        )
        overlaid = {
            context.context_id: overlay_decision33_with_eu_scenario(
                context, profile=self.profile, scenario=scenario
            )
            for context in corpus
        }
        positive_by_id = {
            context.context_id: context
            for context in corpus
            if context.fixture_type is FixtureType.POSITIVE_WITNESS
        }
        checked = 0
        for context in corpus:
            if context.parent_context_id not in positive_by_id:
                continue
            parent_eu = overlaid[context.parent_context_id].facts["classification"]["eu"]
            child_eu = overlaid[context.context_id].facts["classification"]["eu"]
            self.assertEqual(parent_eu, child_eu)
            checked += 1
        self.assertEqual(checked, 276)

    def test_crosswalk_profile_has_no_shared_risk_tier(self) -> None:
        serialized = str(self.profile).lower()
        self.assertNotIn("shared_risk_tier", serialized)
        self.assertEqual(self.profile["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
