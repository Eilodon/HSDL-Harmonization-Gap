from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.classification_relation import (
    ClassificationState,
    NativeClassification,
    SharedClassificationRelation,
    build_classification_relation_report,
    classify_eu,
    classify_vn,
    relate_native_classifications,
)


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalogs" / "vn_decision_33_2026.csv"


class ClassificationRelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_classification_relation_report(CATALOG)

    def test_interface_preserves_native_taxonomies(self) -> None:
        contract = self.report["native_classifier_contract"]
        self.assertTrue(contract["shared_factual_context"])
        self.assertTrue(contract["jurisdiction_native_taxonomies_preserved"])
        self.assertFalse(contract["shared_risk_tier_used"])
        self.assertTrue(contract["unknown_is_distinct_from_out_of_scope"])

    def test_current_corpus_refuses_to_infer_missing_eu_classification(self) -> None:
        self.assertEqual(self.report["context_count"], 322)
        self.assertEqual(self.report["corpus_eu_state_counts"], {"UNKNOWN": 322})
        self.assertEqual(
            self.report["corpus_relation_counts"],
            {"UNKNOWN_MISSING_FACTS": 322},
        )
        self.assertFalse(
            self.report["completeness"]["current_corpus_contains_eu_classification_facts"]
        )

    def test_vietnam_classifier_preserves_positive_negative_and_unknown_fixtures(self) -> None:
        self.assertEqual(
            self.report["corpus_vn_state_counts"],
            {"IN_SCOPE": 184, "OUT_OF_SCOPE": 46, "UNKNOWN": 92},
        )

    def test_synthetic_truth_table_covers_every_relation(self) -> None:
        truth_table = self.report["synthetic_truth_table"]
        self.assertTrue(truth_table["complete"])
        self.assertEqual(truth_table["case_count"], 5)
        self.assertEqual(
            truth_table["relation_counts"],
            {relation.value: 1 for relation in SharedClassificationRelation},
        )

    def test_both_in_scope_requires_crosswalk_not_equivalence(self) -> None:
        eu = NativeClassification(
            "EU", ClassificationState.IN_SCOPE, "EU_ROUTE", (), (), "TEST"
        )
        vn = NativeClassification(
            "VN", ClassificationState.IN_SCOPE, "VN_ROUTE", (), (), "TEST"
        )
        relation, reason = relate_native_classifications(eu, vn)
        self.assertEqual(
            relation,
            SharedClassificationRelation.BOTH_IN_SCOPE_CROSSWALK_REQUIRED,
        )
        self.assertIn("crosswalk", reason)

    def test_unknown_dominates_scope_relation(self) -> None:
        unknown = NativeClassification(
            "EU",
            ClassificationState.UNKNOWN,
            None,
            (),
            ("missing",),
            "TEST",
        )
        known = NativeClassification(
            "VN", ClassificationState.IN_SCOPE, "VN_ROUTE", (), (), "TEST"
        )
        relation, _ = relate_native_classifications(unknown, known)
        self.assertEqual(
            relation, SharedClassificationRelation.UNKNOWN_MISSING_FACTS
        )

    def test_eu_classifier_distinguishes_unknown_false_and_true(self) -> None:
        unknown = classify_eu({"classification": {"eu": {}}})
        outside = classify_eu(
            {"classification": {"eu": {"is_high_risk_ai_system": False}}}
        )
        inside = classify_eu(
            {
                "classification": {
                    "eu": {
                        "is_high_risk_ai_system": True,
                        "annex_category": "ANNEX_III",
                    }
                }
            }
        )
        self.assertEqual(unknown.state, ClassificationState.UNKNOWN)
        self.assertEqual(outside.state, ClassificationState.OUT_OF_SCOPE)
        self.assertEqual(inside.state, ClassificationState.IN_SCOPE)
        self.assertEqual(inside.matched_identifiers, ("ANNEX_III",))

    def test_vn_listed_context_requires_identity_and_route(self) -> None:
        unknown = classify_vn(
            {"classification": {"vn": {"listed": True}}}
        )
        outside = classify_vn(
            {"classification": {"vn": {"listed": False}}}
        )
        inside = classify_vn(
            {
                "classification": {
                    "vn": {
                        "listed": True,
                        "catalog_item_id": "VN_D33_ERA_04",
                        "assessment_route": "POINT_A",
                    }
                }
            }
        )
        self.assertEqual(unknown.state, ClassificationState.UNKNOWN)
        self.assertEqual(
            unknown.missing_facts,
            (
                "classification.vn.catalog_item_id",
                "classification.vn.assessment_route",
            ),
        )
        self.assertEqual(outside.state, ClassificationState.OUT_OF_SCOPE)
        self.assertEqual(inside.state, ClassificationState.IN_SCOPE)

    def test_non_boolean_scope_flags_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            classify_eu(
                {"classification": {"eu": {"is_high_risk_ai_system": "yes"}}}
            )
        with self.assertRaises(ValueError):
            classify_vn({"classification": {"vn": {"listed": 1}}})

    def test_report_is_hashed_and_does_not_overclaim_completeness(self) -> None:
        self.assertEqual(
            self.report["status"],
            "NATIVE_CLASSIFICATION_RELATION_INTERFACE_COMPLETE",
        )
        self.assertRegex(
            self.report["corpus_result_hash"], r"^sha256:[0-9a-f]{64}$"
        )
        completeness = self.report["completeness"]
        self.assertTrue(completeness["interface_executable"])
        self.assertFalse(completeness["reviewed_eu_vn_crosswalk_available"])
        self.assertFalse(completeness["shared_classification_relation_complete"])
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
