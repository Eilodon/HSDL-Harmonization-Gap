from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.candidate_predicates import (
    PredicateProfileError,
    PredicateState,
    build_source_derived_predicate_report,
    compile_source_derived_profile,
    evaluate_executable_rule,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "policies" / "current_candidate_graph_2026-08-02.json"
PROFILE = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "source_derived_predicates.json"
)


class CandidatePredicateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = compile_source_derived_profile(CANDIDATE, PROFILE)
        cls.by_id = {rule.rule_id: rule for rule in cls.rules}
        cls.report = build_source_derived_predicate_report(CANDIDATE, PROFILE)

    def test_all_candidate_rules_and_duties_are_covered(self) -> None:
        self.assertEqual(len(self.rules), 20)
        self.assertEqual(sum(len(rule.duties) for rule in self.rules), 25)
        self.assertEqual(self.report["executable_predicate_count"], 20)
        self.assertEqual(self.report["readiness_only_predicate_count"], 0)

    def test_every_duty_has_modality_recipient_field_and_trigger_signature(self) -> None:
        for rule in self.rules:
            for duty in rule.duties:
                self.assertTrue(duty.modality)
                self.assertIsInstance(duty.recipients, tuple)
                self.assertTrue(duty.trigger_signature)
        self.assertEqual(self.report["duties_with_modality_count"], 25)
        self.assertEqual(self.report["duties_with_recipient_field_count"], 25)
        self.assertEqual(self.report["duties_with_trigger_signature_count"], 25)

    def test_eu_article_50_encodes_polarity_and_exception(self) -> None:
        rule = self.by_id["EU_ART50_DIRECT_INTERACTION_TRANSPARENCY"]
        positive = {
            "system": {
                "intended_direct_interaction": True,
                "interaction_obvious_to_reasonably_informed_person": False,
            },
            "operations": {"authorised_law_exception": False},
        }
        obvious = {
            **positive,
            "system": {
                **positive["system"],
                "interaction_obvious_to_reasonably_informed_person": True,
            },
        }
        exception = {
            **positive,
            "operations": {"authorised_law_exception": True},
        }
        missing = {"system": {"intended_direct_interaction": True}}
        self.assertEqual(
            evaluate_executable_rule(rule, positive).state,
            PredicateState.APPLICABLE,
        )
        self.assertEqual(
            evaluate_executable_rule(rule, obvious).state,
            PredicateState.NOT_APPLICABLE,
        )
        self.assertEqual(
            evaluate_executable_rule(rule, exception).state,
            PredicateState.NOT_APPLICABLE,
        )
        unknown = evaluate_executable_rule(rule, missing)
        self.assertEqual(unknown.state, PredicateState.UNKNOWN)
        self.assertIn(
            "system.interaction_obvious_to_reasonably_informed_person",
            unknown.missing_facts,
        )

    def test_vn_article_10_2_has_distinct_duty_triggers(self) -> None:
        rule = self.by_id["VN_ART10_2_DEPLOYER_RECLASSIFICATION_COORDINATION"]
        ordinary_use = {"actors": {"deployer_role": True}}
        changed = {
            "actors": {"deployer_role": True},
            "operations": {"modification_or_integration_or_function_change": True},
            "classification": {"vn": {"new_or_higher_risk": True}},
        }
        ordinary_result = evaluate_executable_rule(rule, ordinary_use)
        states = {duty.normative_slot: duty.state for duty in ordinary_result.duties}
        self.assertEqual(
            states["deployer_risk_integrity_responsibility"],
            PredicateState.APPLICABLE,
        )
        self.assertEqual(
            states["risk_reclassification_after_change"], PredicateState.UNKNOWN
        )
        changed_result = evaluate_executable_rule(rule, changed)
        self.assertTrue(
            all(duty.state is PredicateState.APPLICABLE for duty in changed_result.duties)
        )

    def test_article_13_routes_require_timing_trigger(self) -> None:
        rule = self.by_id["VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE"]
        base = {
            "classification": {
                "vn": {
                    "listed": True,
                    "assessment_route": "ARTICLE_13_2_A_THIRD_PARTY_CERTIFICATION",
                    "catalog_item_id": "VN_D33_ERA_04",
                }
            }
        }
        self.assertEqual(
            evaluate_executable_rule(rule, base).state, PredicateState.UNKNOWN
        )
        before_use = {
            **base,
            "operations": {"before_use_or_after_significant_change": True},
        }
        self.assertEqual(
            evaluate_executable_rule(rule, before_use).state,
            PredicateState.APPLICABLE,
        )
        outside_event = {
            **base,
            "operations": {"before_use_or_after_significant_change": False},
        }
        self.assertEqual(
            evaluate_executable_rule(rule, outside_event).state,
            PredicateState.NOT_APPLICABLE,
        )

    def test_article_19_reporting_fallback_is_mutually_exclusive(self) -> None:
        rule = self.by_id["VN_ND142_ART19_4_PRELIMINARY_REPORTING"]
        reachable = {
            "operations": {
                "serious_incident": True,
                "reporting_deadline_class": "URGENT_72_HOURS",
                "provider_contact_status": "REACHABLE",
            }
        }
        unreachable = {
            "operations": {
                "serious_incident": True,
                "reporting_deadline_class": "OTHER_5_WORKING_DAYS",
                "provider_contact_status": "UNREACHABLE",
            }
        }
        first = evaluate_executable_rule(rule, reachable)
        first_states = {duty.normative_slot: duty.state for duty in first.duties}
        self.assertEqual(
            first_states["serious_incident_preliminary_report"],
            PredicateState.APPLICABLE,
        )
        self.assertEqual(
            first_states["serious_incident_preliminary_report_fallback"],
            PredicateState.NOT_APPLICABLE,
        )
        second = evaluate_executable_rule(rule, unreachable)
        second_states = {duty.normative_slot: duty.state for duty in second.duties}
        self.assertEqual(
            second_states["serious_incident_preliminary_report"],
            PredicateState.NOT_APPLICABLE,
        )
        self.assertEqual(
            second_states["serious_incident_preliminary_report_fallback"],
            PredicateState.APPLICABLE,
        )

    def test_article_43_notified_body_duty_is_conditional(self) -> None:
        rule = self.by_id["EU_ART43_CONFORMITY_ASSESSMENT"]
        internal = {
            "classification": {
                "eu": {
                    "is_high_risk_ai_system": True,
                    "annex_category": "ANNEX_III_POINTS_2_TO_8",
                    "product_law_route": "NONE",
                    "harmonised_standard_status": "FULLY_APPLIED",
                    "common_specification_status": "NOT_APPLICABLE",
                }
            },
            "operations": {
                "before_placing_on_market_or_putting_into_service": True,
                "substantial_modification": False,
            },
        }
        external = {
            "classification": {
                "eu": {
                    "is_high_risk_ai_system": True,
                    "annex_category": "ANNEX_III_POINT_1",
                    "product_law_route": "NONE",
                    "harmonised_standard_status": "NOT_AVAILABLE",
                    "common_specification_status": "NOT_AVAILABLE",
                }
            },
            "operations": {
                "before_placing_on_market_or_putting_into_service": True,
                "substantial_modification": False,
            },
        }
        internal_result = evaluate_executable_rule(rule, internal)
        internal_states = {duty.normative_slot: duty.state for duty in internal_result.duties}
        self.assertEqual(
            internal_states["conformity_assessment_procedure_selection"],
            PredicateState.APPLICABLE,
        )
        self.assertEqual(
            internal_states["notified_body_participation"],
            PredicateState.NOT_APPLICABLE,
        )
        external_result = evaluate_executable_rule(rule, external)
        self.assertTrue(
            all(duty.state is PredicateState.APPLICABLE for duty in external_result.duties)
        )

    def test_review_boundary_remains_closed(self) -> None:
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")
        self.assertEqual(
            self.report["review_boundary"]["independent_legal_review"], "PENDING"
        )
        self.assertFalse(
            self.report["review_boundary"][
                "quantitative_current_law_claims_allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
