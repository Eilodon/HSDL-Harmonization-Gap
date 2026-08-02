from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.candidate_hsdl import emit_candidate_hsdl
from hsdl_gap.candidate_ir import compile_candidate_profile
from hsdl_gap.decision33_context_v2 import build_decision33_context_v2_report
from hsdl_gap.oracle_expected import build_expected_oracle_report


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
ORACLE = ROOT / "reference-engines" / "javascript" / "candidate_oracle.mjs"


class IndependentJavaScriptOracleTests(unittest.TestCase):
    def test_failed_known_condition_records_missing_fact(self) -> None:
        from hsdl_gap.conditions_v2 import evaluate_condition_v2
        from hsdl_gap.tristate import TruthValue

        trace = evaluate_condition_v2(
            {"op": "known", "args": [{"field": "classification.eu.high_risk"}]},
            {"classification": {"eu": {}}},
        )
        self.assertEqual(trace.value, TruthValue.FALSE)
        self.assertEqual(trace.missing_facts, ("classification.eu.high_risk",))

    def test_expected_projection_contract_is_complete(self) -> None:
        report = build_expected_oracle_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
        )
        self.assertEqual(report["status"], "PYTHON_ORACLE_PROJECTION_COMPLETE")
        self.assertEqual(report["projection_count"], 12880)
        self.assertEqual(report["rule_count"], 20)
        self.assertEqual(report["context_count"], 322)
        self.assertEqual(report["assumption_set_count"], 2)
        self.assertRegex(report["projection_hash"], r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(
            report["projections_by_assumption_set"],
            {
                "ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED": 6440,
                "NO_ASSUMPTIONS": 6440,
            },
        )

    @unittest.skipUnless(shutil.which("node"), "Node.js is required")
    def test_independent_javascript_oracle_matches_python_projection_hash(self) -> None:
        rules = compile_candidate_profile(CANDIDATE, BINDINGS)
        hsdl = emit_candidate_hsdl(rules)
        corpus = build_decision33_context_v2_report(CATALOG)
        expected = build_expected_oracle_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hsdl_path = root / "candidate.hsdl"
            corpus_path = root / "corpus.json"
            expected_path = root / "expected.json"
            hsdl_path.write_text(hsdl, encoding="utf-8")
            corpus_path.write_text(
                json.dumps(corpus, ensure_ascii=False), encoding="utf-8"
            )
            expected_path.write_text(
                json.dumps(expected, ensure_ascii=False), encoding="utf-8"
            )
            completed = subprocess.run(
                [
                    "node",
                    str(ORACLE),
                    "--hsdl",
                    str(hsdl_path),
                    "--corpus",
                    str(corpus_path),
                    "--assumptions",
                    str(ASSUMPTIONS),
                    "--expected",
                    str(expected_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["status"], "EQUIVALENT")
        self.assertTrue(report["projection_hash_match"])
        self.assertEqual(report["projection_count"], 12880)
        self.assertEqual(
            report["actual_projection_hash"], expected["projection_hash"]
        )
        boundary = report["implementation_boundary"]
        self.assertFalse(boundary["shared_python_evaluator_code"])
        self.assertTrue(boundary["shared_hsdl_document"])
        self.assertEqual(boundary["upstream_hsdl_compatibility"], "NOT_CLAIMED")

    @unittest.skipUnless(shutil.which("node"), "Node.js is required")
    def test_independent_oracle_rejects_malformed_hsdl(self) -> None:
        expected = build_expected_oracle_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
        )
        corpus = build_decision33_context_v2_report(CATALOG)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hsdl_path = root / "candidate.hsdl"
            corpus_path = root / "corpus.json"
            expected_path = root / "expected.json"
            hsdl_path.write_text("not-hsdl\n", encoding="utf-8")
            corpus_path.write_text(json.dumps(corpus), encoding="utf-8")
            expected_path.write_text(json.dumps(expected), encoding="utf-8")
            completed = subprocess.run(
                [
                    "node",
                    str(ORACLE),
                    "--hsdl",
                    str(hsdl_path),
                    "--corpus",
                    str(corpus_path),
                    "--assumptions",
                    str(ASSUMPTIONS),
                    "--expected",
                    str(expected_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("@hsdl-core 0.2", completed.stderr)


if __name__ == "__main__":
    unittest.main()
