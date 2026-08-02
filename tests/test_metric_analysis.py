from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.metric_analysis import (
    MetricAnalysisError,
    build_metric_analysis_report,
    load_metric_registry,
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
REGISTRY = ROOT / "metrics" / "model_relative_registry.json"


class MetricAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_metric_analysis_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
            registry_path=REGISTRY,
        )
        cls.metrics = {
            metric["metric_id"]: metric for metric in cls.report["metrics"]
        }

    def test_report_is_hashed_and_model_relative(self) -> None:
        self.assertEqual(
            self.report["status"], "MODEL_RELATIVE_METRIC_ANALYSIS_COMPLETE"
        )
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")
        self.assertRegex(
            self.report["registry"]["registry_hash"], r"^sha256:[0-9a-f]{64}$"
        )
        self.assertRegex(
            self.report["candidate"]["profile_hash"], r"^sha256:[0-9a-f]{64}$"
        )
        self.assertRegex(
            self.report["corpus"]["corpus_hash"], r"^sha256:[0-9a-f]{64}$"
        )

    def test_route_metrics_are_catalog_row_shares(self) -> None:
        point_a = self.metrics["metric:decision33:point-a-positive-catalog-share"]
        point_b = self.metrics["metric:decision33:point-b-positive-catalog-share"]
        self.assertEqual((point_a["numerator"], point_a["denominator"]), (6, 46))
        self.assertEqual((point_b["numerator"], point_b["denominator"]), (40, 46))
        self.assertAlmostEqual(point_a["value"], 6 / 46)
        self.assertAlmostEqual(point_b["value"], 40 / 46)
        self.assertEqual(point_a["measure_id"], "UNWEIGHTED_CATALOG_ROW_SHARE")
        self.assertIn("not share of deployed AI systems", point_a["interpretation"])

    def test_determinate_metric_uses_all_6440_rule_context_evaluations(self) -> None:
        metric = self.metrics["metric:candidate:determinate-outcome-share"]
        self.assertEqual(metric["denominator"], 6440)
        self.assertEqual(metric["numerator"], 690)
        self.assertEqual(metric["unknown_count"], 5750)
        self.assertAlmostEqual(metric["value"], 690 / 6440)
        self.assertEqual(
            metric["measure_id"], "UNWEIGHTED_RULE_CONTEXT_EVALUATION_SHARE"
        )

    def test_applicability_metric_reports_bounds_instead_of_filling_unknowns(self) -> None:
        metric = self.metrics["metric:candidate:applicable-outcome-bounds"]
        self.assertIsNone(metric["value"])
        self.assertEqual(metric["numerator"], 322)
        self.assertEqual(metric["unknown_count"], 5750)
        self.assertEqual(metric["denominator"], 6440)
        self.assertAlmostEqual(metric["lower_bound"], 322 / 6440)
        self.assertAlmostEqual(metric["upper_bound"], (322 + 5750) / 6440)

    def test_indeterminate_share_is_explicit(self) -> None:
        metric = self.metrics["metric:candidate:indeterminate-outcome-share"]
        self.assertEqual(metric["numerator"], 5750)
        self.assertEqual(metric["denominator"], 6440)
        self.assertAlmostEqual(metric["value"], 5750 / 6440)

    def test_sensitivity_identifies_only_the_route_assumption_transitions(self) -> None:
        sensitivity = self.report["sensitivity"]
        self.assertEqual(sensitivity["evaluation_count"], 6440)
        self.assertEqual(sensitivity["changed_evaluation_count"], 184)
        self.assertAlmostEqual(sensitivity["changed_evaluation_share"], 184 / 6440)
        self.assertEqual(sensitivity["classification"], "ASSUMPTION_SENSITIVE")
        self.assertEqual(
            sensitivity["transition_counts"],
            {"INDETERMINATE_MISSING_FACTS->APPLICABLE_DETERMINATE": 184},
        )
        changed_rules = {
            item["rule_id"] for item in sensitivity["changed_evaluations"]
        }
        self.assertEqual(
            changed_rules,
            {
                "VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE",
                "VN_ART13_2B_PROVIDER_OPTION_ROUTE",
            },
        )

    def test_claim_boundary_rejects_prevalence_language(self) -> None:
        boundary = self.report["claim_boundary"]
        self.assertEqual(boundary["empirical_prevalence"], "NOT_SUPPORTED")
        self.assertEqual(
            boundary["independent_legal_conclusion"], "NOT_ASSERTED"
        )
        self.assertEqual(
            boundary["uniform_model_space_percentage"], "NOT_USED"
        )

    def test_registry_rejects_overlapping_numerator_and_unknown_states(self) -> None:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        payload["metrics"][0]["unknown_states"].append("APPLICABLE_DETERMINATE")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(MetricAnalysisError):
                load_metric_registry(path)

    def test_registry_rejects_duplicate_metric_ids(self) -> None:
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        payload["metrics"].append(dict(payload["metrics"][0]))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(MetricAnalysisError):
                load_metric_registry(path)


if __name__ == "__main__":
    unittest.main()
