from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.engineering_gates import (
    EngineeringGateError,
    REQUIRED_ARTIFACTS,
    build_engineering_gate_status,
)


class EngineeringGateTests(unittest.TestCase):
    def _write_artifacts(self, root: Path) -> None:
        payloads = {
            "schema_inventory": {"status": "SCHEMA_INVENTORY_VALID"},
            "decision33_context_v2": {
                "status": "DECISION33_CONTEXT_V2_CORPUS_COMPLETE",
                "context_count": 322,
            },
            "candidate_ir": {
                "status": "CANDIDATE_EXECUTABLE_IR_COMPLETE_MODEL_RELATIVE",
                "compiled_rule_count": 20,
                "compiled_duty_count": 25,
                "compilation_mode_counts": {
                    "REQUIRED_FACTS_READINESS_ONLY": 17
                },
            },
            "metric_analysis": {
                "status": "MODEL_RELATIVE_METRIC_ANALYSIS_COMPLETE"
            },
            "operational_signatures": {
                "status": "OPERATIONAL_DUTY_SIGNATURE_INVENTORY_COMPLETE",
                "same_slot_cross_jurisdiction_pair_count": 0,
            },
            "candidate_hsdl_roundtrip": {"status": "EQUIVALENT"},
            "python_oracle_projection": {
                "status": "PYTHON_ORACLE_PROJECTION_COMPLETE"
            },
            "independent_javascript_oracle": {
                "status": "EQUIVALENT",
                "projection_hash_match": True,
                "projection_count": 12880,
            },
            "symbolic_explicit_routes": {
                "status": "SYMBOLIC_EXPLICIT_ROUTE_ORACLE_EQUIVALENT",
                "symbolically_compiled_rule_count": 2,
                "symbolic_rule_coverage": 0.1,
            },
            "priority_engine": {
                "status": "CANDIDATE_PRIORITY_GRAPH_EXECUTABLE",
                "edge_count": 0,
            },
        }
        for gate_id, (filename, _) in REQUIRED_ARTIFACTS.items():
            (root / filename).write_text(
                json.dumps(payloads[gate_id]), encoding="utf-8"
            )

    def test_current_engineering_state_is_p0_complete_and_p1_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_engineering_gate_status(root)
        self.assertEqual(
            report["status"],
            "P0_COMPLETE_P1_CAPABILITIES_READY_COMPLETENESS_BLOCKED",
        )
        self.assertTrue(report["p0"]["complete"])
        self.assertEqual(report["p0"]["passed"], 7)
        self.assertTrue(report["p1_capabilities"]["ready"])
        self.assertEqual(report["p1_capabilities"]["passed"], 3)
        self.assertTrue(
            report["engineering_completeness"]["independent_oracle_hash_match"]
        )
        self.assertFalse(
            report["engineering_completeness"]["all_candidate_predicates_executable"]
        )
        self.assertFalse(
            report["engineering_completeness"]["full_candidate_symbolic_coverage"]
        )

    def test_remaining_work_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_engineering_gate_status(root)
        remaining = set(report["remaining_engineering_work"])
        self.assertEqual(
            remaining,
            {
                "all_candidate_predicates_executable",
                "shared_eu_vn_classification_relation",
                "same_slot_cross_jurisdiction_crosswalk_available",
                "full_candidate_symbolic_coverage",
                "candidate_priority_edges_declared",
                "source_custody_release_package",
                "claim_ledger_and_generated_publication",
            },
        )

    def test_summary_preserves_key_inventory_counts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_engineering_gate_status(root)
        self.assertEqual(
            report["summary"],
            {
                "context_count": 322,
                "candidate_rule_count": 20,
                "candidate_duty_count": 25,
                "candidate_readiness_only_rule_count": 17,
                "independent_projection_count": 12880,
                "symbolically_compiled_rule_count": 2,
                "symbolic_rule_coverage": 0.1,
                "priority_edge_count": 0,
                "same_slot_cross_jurisdiction_pair_count": 0,
            },
        )

    def test_missing_artifact_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(EngineeringGateError):
                build_engineering_gate_status(directory)

    def test_wrong_status_fails_only_the_relevant_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            filename = REQUIRED_ARTIFACTS["candidate_ir"][0]
            path = root / filename
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["status"] = "BROKEN"
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = build_engineering_gate_status(root)
        self.assertFalse(report["p0"]["complete"])
        self.assertFalse(report["p0"]["gates"]["candidate_ir"])
        self.assertEqual(report["p0"]["passed"], 6)
        self.assertEqual(report["status"], "P0_ENGINEERING_INCOMPLETE")

    def test_gate_evidence_is_content_hashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_engineering_gate_status(root)
        for evidence in report["evidence"].values():
            self.assertRegex(evidence["sha256"], r"^sha256:[0-9a-f]{64}$")
            self.assertTrue(evidence["passed"])

    def test_boundary_explicitly_excludes_legal_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_engineering_gate_status(root)
        self.assertFalse(report["boundary"]["legal_review_gate_included"])
        self.assertEqual(
            report["boundary"]["publication_authorisation"], "NOT_PROVIDED"
        )
        self.assertEqual(report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(report["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
