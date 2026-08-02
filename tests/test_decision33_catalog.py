from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.catalog import load_catalog, validate_catalog
from hsdl_gap.current_report import ROUTE_A, ROUTE_B, ROUTE_EVIDENCE, build_decision33_report

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalogs" / "vn_decision_33_2026.csv"


class Decision33CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog(CATALOG)
        cls.report = build_decision33_report(CATALOG)

    def test_catalog_inventory(self) -> None:
        self.assertEqual(len(self.catalog.items), 46)
        self.assertEqual(
            self.catalog.sector_counts,
            {
                "banking": 2,
                "education": 3,
                "ethnic_and_religious_affairs": 7,
                "healthcare": 2,
                "proceedings": 1,
                "transport": 31,
            },
        )
        self.assertEqual(validate_catalog(self.catalog), [])

    def test_freeze_status_and_transition(self) -> None:
        self.assertEqual(self.catalog.legal_status_at_freeze, "ISSUED_NOT_YET_EFFECTIVE")
        self.assertEqual(self.catalog.effective_from, "2026-08-15")
        self.assertEqual(
            self.catalog.transition["pre_effective_health_education_finance_deadline"],
            "2027-09-01",
        )
        self.assertEqual(
            self.catalog.transition["pre_effective_other_sectors_deadline"],
            "2027-03-01",
        )

    def test_legacy_schema_is_blocked_from_lossy_reuse(self) -> None:
        compatibility = self.report["legacy_schema_compatibility"]
        self.assertEqual(compatibility["status"], "NOT_EXACTLY_REPRESENTABLE")
        self.assertIn("human_approval_or_review", compatibility["missing_dimensions"])
        self.assertIn("catalog_item_id", compatibility["missing_dimensions"])
        self.assertEqual(
            self.report["research_gates"]["H7_1_classification_compatibility"],
            "REQUIRES_REPROOF",
        )

    def test_assessment_routes_are_encoded_but_not_legally_signed_off(self) -> None:
        self.assertEqual(
            self.report["assessment_route_counts"],
            {ROUTE_A: 6, ROUTE_B: 40},
        )
        self.assertEqual(self.report["unresolved_assessment_routes"], 0)
        self.assertEqual(
            self.report["assessment_route_evidence_statuses"],
            [ROUTE_EVIDENCE],
        )
        self.assertEqual(
            self.report["research_gates"]["G2_conformity_assessment"],
            "ROUTES_INGESTED_PENDING_SIGNED_PDF_VISUAL_AND_RULE_ENCODING",
        )


if __name__ == "__main__":
    unittest.main()
