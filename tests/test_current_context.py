from __future__ import annotations

import unittest

from hsdl_gap.current_context import (
    build_current_context_report,
    build_decision33_witnesses,
)


class CurrentContextTests(unittest.TestCase):
    def test_one_positive_witness_per_catalog_row(self) -> None:
        witnesses = build_decision33_witnesses("catalogs/vn_decision_33_2026.csv")
        self.assertEqual(len(witnesses), 46)
        self.assertEqual(len({w.catalog_item_id for w in witnesses}), 46)
        self.assertTrue(all(w.source_features for w in witnesses))

    def test_profile_is_explicitly_non_exhaustive(self) -> None:
        report = build_current_context_report("catalogs/vn_decision_33_2026.csv")
        self.assertEqual(
            report["status"],
            "CATALOG_DRIVEN_POSITIVE_WITNESSES_COMPLETE",
        )
        self.assertFalse(report["universe_status"]["is_cartesian_product"])
        self.assertFalse(report["universe_status"]["is_exhaustive"])
        self.assertFalse(report["universe_status"]["supports_prevalence_inference"])
        self.assertEqual(
            report["research_gates"]["uniform_percentage_claims"],
            "PROHIBITED_ON_WITNESS_PROFILE",
        )

    def test_h7_1_remains_blocked(self) -> None:
        report = build_current_context_report("catalogs/vn_decision_33_2026.csv")
        self.assertEqual(
            report["research_gates"]["H7_1"],
            "BLOCKED_PENDING_SHARED_EU_VN_CLASSIFICATION_RELATION_AND_NEGATIVE_CASES",
        )
        self.assertEqual(
            report["assessment_route_counts"],
            {
                "ARTICLE_13_2_A_THIRD_PARTY_CERTIFICATION": 6,
                "ARTICLE_13_2_B_PROVIDER_SELF_OR_THIRD_PARTY": 40,
            },
        )

    def test_axis_evidence_is_traceable_to_source_features(self) -> None:
        witnesses = build_decision33_witnesses("catalogs/vn_decision_33_2026.csv")
        for witness in witnesses:
            source = set(witness.source_features)
            evidence_fields = (
                witness.decision_effect_evidence,
                witness.automation_level_evidence,
                witness.human_approval_or_review_evidence,
                witness.physical_actuation_evidence,
                witness.biometric_or_sensitive_attribute_use_evidence,
                witness.scale_or_value_threshold_evidence,
            )
            for evidence in evidence_fields:
                self.assertTrue(set(evidence) <= source)


if __name__ == "__main__":
    unittest.main()
