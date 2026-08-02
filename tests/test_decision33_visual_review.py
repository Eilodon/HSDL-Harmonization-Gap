from __future__ import annotations

import json
import unittest

from hsdl_gap.current_report import build_decision33_report


class Decision33VisualReviewTests(unittest.TestCase):
    def test_visual_overlay_closes_pdf_route_gate(self) -> None:
        report = build_decision33_report("catalogs/vn_decision_33_2026.csv")
        review = report["assessment_route_visual_review"]
        self.assertEqual(
            review["status"],
            "VISUALLY_VERIFIED_AGAINST_CHECKSUM_PINNED_PDF",
        )
        self.assertEqual(review["validation_errors"], [])
        self.assertFalse(review["independent_legal_signoff"])
        self.assertEqual(
            report["research_gates"]["G2_conformity_assessment"],
            "ROUTES_VISUALLY_VERIFIED_PENDING_CURRENT_RULE_ENCODING_AND_SECOND_REVIEW",
        )

    def test_visual_overlay_identifies_six_point_a_rows(self) -> None:
        payload = json.loads(
            open(
                "sources/reviews/vn_decision_33_2026.visual.json",
                encoding="utf-8",
            ).read()
        )
        findings = payload["findings"]
        self.assertEqual(findings["route_a_count"], 6)
        self.assertEqual(findings["route_b_count"], 40)
        self.assertEqual(findings["total_catalog_rows"], 46)
        self.assertEqual(
            set(findings["route_a_ids"]),
            {
                "VN_D33_ERA_04",
                "VN_D33_ERA_05",
                "VN_D33_ERA_06",
                "VN_D33_ERA_07",
                "VN_D33_HLT_02",
                "VN_D33_PRC_01",
            },
        )

    def test_missing_overlay_reopens_gate(self) -> None:
        report = build_decision33_report(
            "catalogs/vn_decision_33_2026.csv",
            visual_review_path=None,
        )
        self.assertEqual(
            report["assessment_route_visual_review"]["status"],
            "PENDING_OR_INVALID",
        )
        self.assertTrue(report["validation_errors"])


if __name__ == "__main__":
    unittest.main()
