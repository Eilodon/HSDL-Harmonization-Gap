from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.context import iter_legacy_contexts
from hsdl_gap.loader import load_policy_bundle
from hsdl_gap.metrics import GROUPS, directional_gap_set, multi_rule_context_count, obligor_gap_set
from hsdl_gap.report import build_legacy_report

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / "policies" / "legacy_v11.json"


class LegacyRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contexts = tuple(iter_legacy_contexts())
        cls.policies = load_policy_bundle(POLICIES)

    def test_context_count(self) -> None:
        self.assertEqual(len(self.contexts), 2880)

    def test_per_group_bindingness_counts(self) -> None:
        expected = {
            "G1": (240, 1248, 1152, 2160),
            "G2": (576, 0, 1152, 576),
            "G3": (0, 1728, 1152, 2880),
            "G4": (432, 1008, 1152, 1728),
            "G5": (0, 0, 1440, 1440),
            "G6": (576, 864, 1152, 1440),
        }
        for group, values in expected.items():
            with self.subTest(group=group):
                actual = (
                    len(directional_gap_set(self.contexts, self.policies["EU"], self.policies["VN"], group)),
                    len(directional_gap_set(self.contexts, self.policies["VN"], self.policies["EU"], group)),
                    len(directional_gap_set(self.contexts, self.policies["EU"], self.policies["ASEAN"], group)),
                    len(directional_gap_set(self.contexts, self.policies["VN"], self.policies["ASEAN"], group)),
                )
                self.assertEqual(actual, values)

    def test_union_counts(self) -> None:
        report = build_legacy_report(POLICIES)
        self.assertEqual(
            report["unions"],
            {
                "EU_gt_ASEAN": 2016,
                "EU_gt_VN": 864,
                "VN_gt_ASEAN": 2880,
                "VN_gt_EU": 1728,
                "obligor_gap_EU_VN": 1152,
            },
        )

    def test_multi_rule_counts(self) -> None:
        self.assertEqual(multi_rule_context_count(self.contexts, self.policies["VN"], "G1"), 816)
        self.assertEqual(multi_rule_context_count(self.contexts, self.policies["VN"], "G2"), 288)
        self.assertEqual(multi_rule_context_count(self.contexts, self.policies["VN"], "G4"), 288)

    def test_obligor_gap_counts(self) -> None:
        expected = {"G1": 576, "G2": 0, "G3": 1152, "G4": 144, "G5": 0, "G6": 576}
        for group in GROUPS:
            with self.subTest(group=group):
                actual = len(obligor_gap_set(self.contexts, self.policies["EU"], self.policies["VN"], group))
                self.assertEqual(actual, expected[group])


if __name__ == "__main__":
    unittest.main()
