from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.claim_ledger import (
    ClaimLedgerError,
    build_claim_ledger_report,
    resolve_json_pointer,
)


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "claims" / "model_relative_claims.json"


class ClaimLedgerTests(unittest.TestCase):
    def _write_artifacts(self, root: Path) -> None:
        artifacts = {
            "model-relative-metric-analysis.json": {
                "metrics": [
                    {"numerator": 6, "denominator": 46, "measure_id": "UNWEIGHTED_CATALOG_ROW_SHARE"},
                    {"numerator": 40, "denominator": 46, "measure_id": "UNWEIGHTED_CATALOG_ROW_SHARE"},
                    {"numerator": 690, "denominator": 6440, "unknown_count": 5750},
                    {"numerator": 322, "denominator": 6440, "unknown_count": 5750, "value": None},
                    {"numerator": 5750, "denominator": 6440},
                ],
                "sensitivity": {
                    "changed_evaluation_count": 184,
                    "evaluation_count": 6440,
                    "classification": "ASSUMPTION_SENSITIVE",
                },
            },
            "source-derived-predicate-report.json": {
                "executable_predicate_count": 20,
                "readiness_only_predicate_count": 0,
                "duty_count": 25,
            },
            "eu-article6-context-v2-corpus.json": {
                "context_count": 36,
                "native_route_count": 9,
                "classification_state_counts": {
                    "IN_SCOPE": 18,
                    "OUT_OF_SCOPE": 9,
                    "UNKNOWN": 9,
                },
            },
            "decision33-eu-relation-scenarios.json": {
                "scenario_count": 2,
                "context_count_per_scenario": 322,
                "completeness": {
                    "all_322_contexts_receive_scenario_metadata": True
                },
            },
            "operational-duty-signature-report.json": {
                "exact_cross_jurisdiction_pair_count": 0,
                "same_slot_cross_jurisdiction_pair_count": 0,
            },
            "independent-javascript-oracle-report.json": {
                "projection_hash_match": True,
                "projection_count": 12880,
                "implementation_boundary": {
                    "shared_python_evaluator_code": False
                },
            },
            "source-derived-symbolic-profile-v2-report.json": {
                "symbolically_compiled_rule_count": 20,
                "candidate_rule_count": 20,
                "duty_trigger_expression_count": 5,
                "mismatch_count": 0,
            },
            "candidate-priority-report.json": {
                "edge_count": 9,
                "conditional_edge_count": 2,
                "source_evidenced_edge_count": 9,
                "limitations": {"cross_jurisdiction_priority": "NOT_DECLARED"},
            },
            "engineering-gate-status.json": {
                "p0": {"complete": True, "passed": 7},
                "status": "P0_COMPLETE_P1_CAPABILITIES_READY_COMPLETENESS_BLOCKED",
            },
        }
        for filename, payload in artifacts.items():
            (root / filename).write_text(json.dumps(payload), encoding="utf-8")

    def test_all_declared_claims_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_claim_ledger_report(ledger_path=LEDGER, artifact_dir=root)
        self.assertEqual(report["status"], "CLAIM_LEDGER_VALIDATED")
        self.assertEqual(report["claim_count"], 13)
        self.assertEqual(report["supported_claim_count"], 13)
        self.assertEqual(report["unsupported_claim_count"], 0)
        self.assertEqual(report["evidence_reference_count"], 42)
        self.assertEqual(report["evidence_mismatch_count"], 0)
        self.assertTrue(all(claim["supported"] for claim in report["claims"]))

    def test_artifact_evidence_is_hashed_once_per_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_claim_ledger_report(ledger_path=LEDGER, artifact_dir=root)
        self.assertEqual(len(report["artifact_hashes"]), 9)
        for digest in report["artifact_hashes"].values():
            self.assertRegex(digest, r"^sha256:[0-9a-f]{64}$")

    def test_stale_value_marks_only_affected_claim_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            path = root / "candidate-priority-report.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["edge_count"] = 8
            path.write_text(json.dumps(payload), encoding="utf-8")
            report = build_claim_ledger_report(ledger_path=LEDGER, artifact_dir=root)
        self.assertEqual(report["status"], "CLAIM_LEDGER_STALE")
        self.assertEqual(report["supported_claim_count"], 12)
        self.assertEqual(report["unsupported_claim_count"], 1)
        self.assertEqual(report["evidence_mismatch_count"], 1)
        stale = [claim for claim in report["claims"] if not claim["supported"]]
        self.assertEqual(stale[0]["claim_id"], "CLAIM-PRIORITY-GRAPH-DECLARED")

    def test_json_pointer_supports_arrays_and_escaping(self) -> None:
        document = {"a/b": {"~key": [10, 20]}}
        self.assertEqual(resolve_json_pointer(document, "/a~1b/~0key/1"), 20)
        self.assertEqual(resolve_json_pointer(document, ""), document)

    def test_unresolved_pointer_is_an_error(self) -> None:
        with self.assertRaises(ClaimLedgerError):
            resolve_json_pointer({"a": 1}, "/missing")
        with self.assertRaises(ClaimLedgerError):
            resolve_json_pointer([1], "/2")

    def test_artifact_path_traversal_is_rejected(self) -> None:
        ledger = {
            "schema_version": "1.0.0",
            "ledger_id": "test",
            "claim_class": "MODEL_RELATIVE",
            "legal_validation": "NOT_ASSERTED",
            "claims": [
                {
                    "claim_id": "TEST",
                    "text": "test",
                    "evidence": [
                        {"artifact": "../secret.json", "pointer": "/x", "expected": 1}
                    ],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger_path = root / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaises(ClaimLedgerError):
                build_claim_ledger_report(ledger_path=ledger_path, artifact_dir=root)

    def test_duplicate_claim_ids_are_rejected(self) -> None:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        ledger["claims"].append(dict(ledger["claims"][0]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            ledger_path = root / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            with self.assertRaises(ClaimLedgerError):
                build_claim_ledger_report(ledger_path=ledger_path, artifact_dir=root)

    def test_boundary_does_not_promote_claims(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_artifacts(root)
            report = build_claim_ledger_report(ledger_path=LEDGER, artifact_dir=root)
        boundary = report["boundary"]
        self.assertEqual(boundary["legal_validation"], "NOT_ASSERTED")
        self.assertEqual(boundary["empirical_prevalence"], "NOT_SUPPORTED")
        self.assertEqual(boundary["publication_authorisation"], "NOT_PROVIDED")


if __name__ == "__main__":
    unittest.main()
