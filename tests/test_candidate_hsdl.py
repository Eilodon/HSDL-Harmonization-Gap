from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.candidate_hsdl import (
    CandidateHSDLError,
    build_candidate_hsdl_differential_report,
    emit_candidate_hsdl,
    parse_candidate_hsdl,
)
from hsdl_gap.candidate_ir import compile_candidate_profile


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


class CandidateHSDLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = compile_candidate_profile(CANDIDATE, BINDINGS)
        cls.document = emit_candidate_hsdl(cls.rules)
        cls.report = build_candidate_hsdl_differential_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
        )

    def test_round_trip_preserves_every_compiled_rule(self) -> None:
        profile_id, parsed = parse_candidate_hsdl(self.document)
        self.assertEqual(profile_id, "current-candidate-2026-08-02")
        self.assertEqual(
            [rule.as_mapping() for rule in parsed],
            [rule.as_mapping() for rule in self.rules],
        )

    def test_differential_is_equivalent_over_all_scenarios(self) -> None:
        self.assertEqual(self.report["status"], "EQUIVALENT")
        self.assertTrue(self.report["structural_round_trip_equal"])
        self.assertEqual(self.report["mismatch_count"], 0)
        self.assertEqual(self.report["mismatch_samples"], [])
        self.assertEqual(self.report["rule_count"], 20)
        self.assertEqual(self.report["duty_count"], 25)
        self.assertEqual(self.report["context_count"], 322)
        self.assertEqual(self.report["assumption_set_count"], 2)
        self.assertEqual(self.report["comparison_count"], 12880)
        self.assertEqual(
            self.report["comparisons_by_assumption_set"],
            {
                "ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED": 6440,
                "NO_ASSUMPTIONS": 6440,
            },
        )

    def test_document_has_canonical_header_and_shape(self) -> None:
        lines = self.document.splitlines()
        self.assertEqual(lines[0], "@hsdl-core 0.2")
        self.assertTrue(lines[1].startswith("profile "))
        self.assertEqual(lines[-1], "endprofile")
        self.assertEqual(sum(line.startswith("rule ") for line in lines), 20)
        self.assertEqual(sum(line.startswith("duty ") for line in lines), 25)
        self.assertRegex(self.report["document_hash"], r"^sha256:[0-9a-f]{64}$")
        self.assertGreater(self.report["document_byte_count"], 1000)

    def test_missing_header_is_rejected(self) -> None:
        with self.assertRaises(CandidateHSDLError):
            parse_candidate_hsdl(self.document.replace("@hsdl-core 0.2\n", "", 1))

    def test_unknown_statement_is_rejected(self) -> None:
        malformed = self.document.replace("factpaths ", "mystery ", 1)
        with self.assertRaises(CandidateHSDLError):
            parse_candidate_hsdl(malformed)

    def test_missing_endrule_is_rejected(self) -> None:
        malformed = self.document.replace("endrule\n", "", 1)
        with self.assertRaises(CandidateHSDLError):
            parse_candidate_hsdl(malformed)

    def test_content_after_endprofile_is_rejected(self) -> None:
        with self.assertRaises(CandidateHSDLError):
            parse_candidate_hsdl(self.document + "extra\n")

    def test_declared_rule_count_must_match(self) -> None:
        malformed = self.document.replace('"rule_count":20', '"rule_count":19', 1)
        with self.assertRaises(CandidateHSDLError):
            parse_candidate_hsdl(malformed)

    def test_duplicate_rule_id_is_rejected(self) -> None:
        lines = self.document.splitlines()
        rule_indexes = [index for index, line in enumerate(lines) if line.startswith("rule ")]
        first_rule_id_fragment = '"rule_id":"EU_ART9_RISK_MANAGEMENT_SYSTEM"'
        second_line = lines[rule_indexes[1]]
        start = second_line.index('"rule_id":"')
        end = second_line.index('"', start + len('"rule_id":"'))
        original_fragment = second_line[start : end + 1]
        lines[rule_indexes[1]] = second_line.replace(
            original_fragment, first_rule_id_fragment, 1
        )
        with self.assertRaises(CandidateHSDLError):
            parse_candidate_hsdl("\n".join(lines) + "\n")

    def test_compatibility_boundary_is_explicit(self) -> None:
        boundary = self.report["compatibility_boundary"]
        self.assertEqual(boundary["upstream_hsdl_compatibility"], "NOT_CLAIMED")
        self.assertFalse(boundary["independent_implementation"])
        self.assertEqual(boundary["current_law_validation"], "NOT_ASSERTED")
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
