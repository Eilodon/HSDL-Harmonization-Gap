from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.candidate_ir import (
    ApplicabilityState,
    CompilationMode,
    DutyState,
    build_candidate_ir_report,
    compile_candidate_profile,
    evaluate_compiled_rule,
    load_assumption_sets,
)
from hsdl_gap.context_v2 import FixtureType
from hsdl_gap.decision33_context_v2 import ROUTE_A, ROUTE_B, build_decision33_context_v2_corpus


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


class CandidateIRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = compile_candidate_profile(CANDIDATE, BINDINGS)
        cls.rule_by_id = {rule.rule_id: rule for rule in cls.rules}
        cls.contexts = build_decision33_context_v2_corpus(CATALOG)
        cls.positives = tuple(
            context
            for context in cls.contexts
            if context.fixture_type is FixtureType.POSITIVE_WITNESS
        )
        cls.assumptions = load_assumption_sets(ASSUMPTIONS)
        cls.report = build_candidate_ir_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            assumptions_path=ASSUMPTIONS,
            catalog_path=CATALOG,
        )

    def test_all_candidate_rules_and_duties_compile(self) -> None:
        self.assertEqual(len(self.rules), 20)
        self.assertEqual(sum(len(rule.duties) for rule in self.rules), 25)
        self.assertEqual(len(self.rule_by_id), len(self.rules))

    def test_compilation_modes_do_not_overstate_predicate_semantics(self) -> None:
        counts = self.report["compilation_mode_counts"]
        self.assertEqual(counts[CompilationMode.UNCONDITIONAL_DECLARED.value], 1)
        self.assertEqual(counts[CompilationMode.EXPLICIT_CATALOG_ROUTE.value], 2)
        self.assertEqual(
            counts[CompilationMode.REQUIRED_FACTS_READINESS_ONLY.value], 17
        )
        readiness_rules = [
            rule
            for rule in self.rules
            if rule.compilation_mode
            is CompilationMode.REQUIRED_FACTS_READINESS_ONLY
        ]
        self.assertTrue(
            all(not rule.predicate_semantics_complete for rule in readiness_rules)
        )

    def test_every_declared_required_fact_has_context_path_binding(self) -> None:
        for rule in self.rules:
            self.assertEqual(set(rule.required_facts), set(rule.fact_paths))
            self.assertTrue(all(rule.fact_paths.values()))

    def test_article13_structural_routing_preserves_six_forty_split(self) -> None:
        audit_a = self.report["decision33_route_audit"][
            "VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"
        ]
        audit_b = self.report["decision33_route_audit"][
            "VN_ART13_2B_PROVIDER_OPTION_ROUTE"
        ]
        self.assertEqual(audit_a["structural_truth_counts"], {"FALSE": 40, "TRUE": 6})
        self.assertEqual(audit_b["structural_truth_counts"], {"FALSE": 6, "TRUE": 40})

    def test_article13_without_timing_assumption_remains_indeterminate(self) -> None:
        rule = self.rule_by_id["VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"]
        point_a = next(
            context
            for context in self.positives
            if context.facts["classification"]["vn"]["assessment_route"] == ROUTE_A
        )
        result = evaluate_compiled_rule(rule, point_a)
        self.assertEqual(result.state, ApplicabilityState.INDETERMINATE_MISSING_FACTS)
        self.assertTrue(
            all(duty.state is DutyState.APPLICABILITY_UNKNOWN for duty in result.duties)
        )

    def test_explicit_timing_assumption_executes_only_matching_route(self) -> None:
        assumption = self.assumptions["ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED"]
        rule_a = self.rule_by_id["VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"]
        rule_b = self.rule_by_id["VN_ART13_2B_PROVIDER_OPTION_ROUTE"]
        point_a = next(
            context
            for context in self.positives
            if context.facts["classification"]["vn"]["assessment_route"] == ROUTE_A
        )
        point_b = next(
            context
            for context in self.positives
            if context.facts["classification"]["vn"]["assessment_route"] == ROUTE_B
        )
        kwargs = {
            "assumption_values": assumption["values"],
            "satisfied_required_facts": assumption["satisfied_required_facts"],
        }
        self.assertEqual(
            evaluate_compiled_rule(rule_a, point_a, **kwargs).state,
            ApplicabilityState.APPLICABLE_DETERMINATE,
        )
        self.assertEqual(
            evaluate_compiled_rule(rule_b, point_b, **kwargs).state,
            ApplicabilityState.APPLICABLE_DETERMINATE,
        )
        self.assertEqual(
            evaluate_compiled_rule(rule_a, point_b, **kwargs).state,
            ApplicabilityState.NOT_APPLICABLE,
        )
        self.assertEqual(
            evaluate_compiled_rule(rule_b, point_a, **kwargs).state,
            ApplicabilityState.NOT_APPLICABLE,
        )

    def test_timing_assumption_produces_six_and_forty_applicable_positives(self) -> None:
        scenario_id = "ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED"
        audit_a = self.report["decision33_route_audit"][
            "VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"
        ]["scenarios"][scenario_id]
        audit_b = self.report["decision33_route_audit"][
            "VN_ART13_2B_PROVIDER_OPTION_ROUTE"
        ]["scenarios"][scenario_id]
        self.assertEqual(
            audit_a["state_counts"],
            {"APPLICABLE_DETERMINATE": 6, "NOT_APPLICABLE": 40},
        )
        self.assertEqual(
            audit_b["state_counts"],
            {"APPLICABLE_DETERMINATE": 40, "NOT_APPLICABLE": 6},
        )

    def test_general_principle_preserves_unspecified_obligor_state(self) -> None:
        rule = self.rule_by_id["VN_ART4_2_HUMAN_CONTROL_PRINCIPLE"]
        result = evaluate_compiled_rule(rule, self.positives[0])
        self.assertEqual(
            result.state, ApplicabilityState.APPLICABLE_UNSPECIFIED_OBLIGOR
        )
        self.assertEqual(len(result.duties), 1)
        self.assertEqual(
            result.duties[0].state,
            DutyState.APPLICABLE_UNSPECIFIED_OBLIGOR,
        )

    def test_generic_required_fact_rule_is_never_silently_promoted(self) -> None:
        rule = self.rule_by_id["EU_ART9_RISK_MANAGEMENT_SYSTEM"]
        result = evaluate_compiled_rule(
            rule,
            self.positives[0],
            assumption_values={
                "is_high_risk_ai_system": True,
                "lifecycle_stage": "POST_MARKET",
            },
            satisfied_required_facts=(
                "is_high_risk_ai_system",
                "lifecycle_stage",
            ),
        )
        self.assertEqual(
            result.state,
            ApplicabilityState.INDETERMINATE_PREDICATE_NOT_COMPILED,
        )

    def test_report_is_model_relative_and_quantitative_claims_remain_prohibited(self) -> None:
        self.assertEqual(
            self.report["status"],
            "CANDIDATE_EXECUTABLE_IR_COMPLETE_MODEL_RELATIVE",
        )
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")
        limitations = self.report["limitations"]
        self.assertTrue(limitations["required_fact_presence_is_not_predicate_truth"])
        self.assertFalse(limitations["generic_rule_predicates_compiled"])
        self.assertEqual(
            limitations["quantitative_current_law_claims"], "PROHIBITED"
        )


if __name__ == "__main__":
    unittest.main()
