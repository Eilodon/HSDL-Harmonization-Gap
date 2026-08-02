from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.alignment import build_typed_alignment_audit, observe_alignment
from hsdl_gap.context import Context
from hsdl_gap.evaluator import evaluate_policy
from hsdl_gap.loader import load_policy_bundle
from hsdl_gap.model import (
    ActorRelation,
    Bindingness,
    Policy,
    Rule,
    TypedDuty,
)
from hsdl_gap.priority import PriorityState, resolve_declared_conflicts

ROOT = Path(__file__).resolve().parents[1]
POLICIES = ROOT / "policies" / "legacy_v11.json"
CROSSWALK = ROOT / "alignments" / "legacy_obligation_crosswalk.json"
SEMANTICS = ROOT / "alignments" / "legacy_duty_semantics.json"


def base_context(**overrides: object) -> Context:
    values = dict(
        risk_tier="High",
        sector="Healthcare",
        system_role="Provider",
        lifecycle_stage="PreMarket",
        modification_increases_risk=False,
        serious_harm_discovered=False,
        interacts_with_human=True,
        existing_sector_certification=False,
    )
    values.update(overrides)
    return Context(**values)


class TypedAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.policies = load_policy_bundle(POLICIES, SEMANTICS)
        cls.audit = build_typed_alignment_audit(
            POLICIES, CROSSWALK, duty_semantics_path=SEMANTICS
        )

    def test_g1_distinct_duties_accumulate_without_priority(self) -> None:
        context = base_context()
        result = evaluate_policy(self.policies["VN"], context, "G1")
        self.assertEqual(
            {duty.normative_slot for duty in result.duties},
            {"risk_governance.classify", "risk_governance.regulatory_inspection"},
        )
        self.assertEqual(resolve_declared_conflicts(self.policies["VN"], context, "G1"), ())

    def test_g1_is_structural_not_exact_actor_mismatch(self) -> None:
        context = base_context()
        eu = evaluate_policy(self.policies["EU"], context, "G1")
        vn = evaluate_policy(self.policies["VN"], context, "G1")
        observation = observe_alignment(eu, vn)
        self.assertEqual(observation.shared_alignment_keys, frozenset({"risk_governance"}))
        self.assertEqual(observation.shared_normative_slots, frozenset())
        self.assertEqual(observation.exact_actor_mismatch_slots, frozenset())
        self.assertTrue(observation.structural_extra_slots_left)
        self.assertTrue(observation.structural_extra_slots_right)

    def test_g5_exact_slot_and_actor_alignment(self) -> None:
        context = base_context(interacts_with_human=True)
        eu = evaluate_policy(self.policies["EU"], context, "G5")
        vn = evaluate_policy(self.policies["VN"], context, "G5")
        observation = observe_alignment(eu, vn)
        self.assertEqual(
            observation.exact_actor_match_slots,
            frozenset({"interaction_transparency.disclose"}),
        )
        self.assertEqual(observation.exact_actor_mismatch_slots, frozenset())

    def test_audit_does_not_promote_flattened_gap_to_exact_mismatch(self) -> None:
        self.assertEqual(self.audit["unions"]["legacy_flattened_obligor_gap_contexts"], 1152)
        self.assertEqual(self.audit["unions"]["typed_exact_actor_mismatch_contexts"], 0)
        self.assertGreater(self.audit["unions"]["contexts_requiring_crosswalk_review"], 0)
        self.assertEqual(
            self.audit["groups"]["G4"]["declared_relation"],
            "cross_functional_bundle",
        )

    def test_declared_same_slot_conflict_is_indeterminate_without_priority_rule(self) -> None:
        duty1 = TypedDuty(
            id="D1",
            action="classify",
            object="system",
            obligors=frozenset({"Provider"}),
            actor_relation=ActorRelation.SINGLE,
            alignment_key="classification",
            normative_slot="classification.perform",
            conflict_class="CLASSIFY_ROUTE",
        )
        duty2 = TypedDuty(
            id="D2",
            action="classify",
            object="system",
            obligors=frozenset({"Regulator"}),
            actor_relation=ActorRelation.SINGLE,
            alignment_key="classification",
            normative_slot="classification.perform",
            conflict_class="CLASSIFY_ROUTE",
        )
        policy = Policy(
            id="SYNTHETIC",
            jurisdiction="X",
            version="test",
            rules=(
                Rule("R1", "X", "G1", "T", "1", Bindingness.BINDING, {"op": "all"}, (duty1,)),
                Rule("R2", "X", "G1", "T", "2", Bindingness.BINDING, {"op": "all"}, (duty2,)),
            ),
        )
        resolutions = resolve_declared_conflicts(policy, base_context(), "G1")
        self.assertEqual(len(resolutions), 1)
        self.assertEqual(resolutions[0].state, PriorityState.PRIORITY_INDETERMINATE)

    def test_conflict_class_cannot_span_normative_slots(self) -> None:
        duty1 = TypedDuty(
            id="D1",
            action="classify",
            object="system",
            obligors=frozenset({"Provider"}),
            alignment_key="classification",
            normative_slot="classification.perform",
            conflict_class="BAD",
        )
        duty2 = TypedDuty(
            id="D2",
            action="inspect",
            object="entity",
            obligors=frozenset({"Regulator"}),
            alignment_key="risk_governance",
            normative_slot="risk_governance.inspect",
            conflict_class="BAD",
        )
        policy = Policy(
            id="SYNTHETIC",
            jurisdiction="X",
            version="test",
            rules=(
                Rule("R1", "X", "G1", "T", "1", Bindingness.BINDING, {"op": "all"}, (duty1,)),
                Rule("R2", "X", "G1", "T", "2", Bindingness.BINDING, {"op": "all"}, (duty2,)),
            ),
        )
        with self.assertRaises(ValueError):
            resolve_declared_conflicts(policy, base_context(), "G1")


if __name__ == "__main__":
    unittest.main()
