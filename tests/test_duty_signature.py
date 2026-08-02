from __future__ import annotations

import unittest
from pathlib import Path

from hsdl_gap.candidate_ir import CompiledDuty
from hsdl_gap.duty_signature import (
    DutyRelation,
    OperationalDutySignature,
    build_operational_signature_report,
    compare_operational_signatures,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "policies" / "current_candidate_graph_2026-08-02.json"
BINDINGS = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "engineering_fact_bindings.json"
)


def signature(
    *,
    slot: str = "incident_report",
    actions: tuple[str, ...] = ("submit",),
    object_: str = "incident_report",
    obligors: tuple[str, ...] = ("Provider",),
    actor_relation: str = "primary",
    timing: str = "within_deadline",
) -> OperationalDutySignature:
    return OperationalDutySignature.from_duty(
        CompiledDuty(
            duty_id="synthetic-duty",
            normative_slot=slot,
            actions=actions,
            object=object_,
            obligors=obligors,
            actor_relation=actor_relation,
            timing=timing,
        )
    )


class OperationalDutySignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_operational_signature_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
        )

    def test_candidate_inventory_is_locked(self) -> None:
        self.assertEqual(self.report["duty_count"], 25)
        self.assertEqual(self.report["duties_by_jurisdiction"], {"EU": 8, "VN": 17})
        self.assertEqual(self.report["cross_jurisdiction_pair_count"], 136)

    def test_candidate_names_do_not_establish_cross_jurisdiction_same_slot(self) -> None:
        self.assertEqual(self.report["same_slot_cross_jurisdiction_pair_count"], 0)
        self.assertEqual(self.report["exact_cross_jurisdiction_pair_count"], 0)
        self.assertEqual(self.report["actor_variant_cross_jurisdiction_pair_count"], 0)
        self.assertEqual(
            self.report["cross_jurisdiction_relation_counts"],
            {DutyRelation.INCOMPARABLE_DIFFERENT_SLOT.value: 136},
        )

    def test_exact_requires_all_operational_fields_equal(self) -> None:
        relation, differences = compare_operational_signatures(signature(), signature())
        self.assertEqual(relation, DutyRelation.EXACT_OPERATIONAL_SIGNATURE)
        self.assertEqual(differences, ())

    def test_actor_variant_detects_obligor_and_relation_change(self) -> None:
        relation, differences = compare_operational_signatures(
            signature(),
            signature(obligors=("Deployer",), actor_relation="fallback"),
        )
        self.assertEqual(relation, DutyRelation.ACTOR_VARIANT)
        self.assertEqual(differences, ("obligors", "actor_relation"))

    def test_timing_variant_is_separate(self) -> None:
        relation, differences = compare_operational_signatures(
            signature(), signature(timing="without_undue_delay")
        )
        self.assertEqual(relation, DutyRelation.TIMING_VARIANT)
        self.assertEqual(differences, ("timing",))

    def test_action_variant_is_separate(self) -> None:
        relation, differences = compare_operational_signatures(
            signature(), signature(actions=("notify",))
        )
        self.assertEqual(relation, DutyRelation.ACTION_VARIANT)
        self.assertEqual(differences, ("actions",))

    def test_object_variant_is_separate(self) -> None:
        relation, differences = compare_operational_signatures(
            signature(), signature(object_="incident_record")
        )
        self.assertEqual(relation, DutyRelation.OBJECT_VARIANT)
        self.assertEqual(differences, ("object",))

    def test_multi_dimension_variant_is_not_called_actor_mismatch(self) -> None:
        relation, differences = compare_operational_signatures(
            signature(),
            signature(actions=("notify",), obligors=("Deployer",), timing="immediate"),
        )
        self.assertEqual(relation, DutyRelation.MULTI_DIMENSION_VARIANT)
        self.assertEqual(differences, ("actions", "obligors", "timing"))

    def test_different_slot_is_conservatively_incomparable(self) -> None:
        relation, differences = compare_operational_signatures(
            signature(), signature(slot="technical_remediation")
        )
        self.assertEqual(relation, DutyRelation.INCOMPARABLE_DIFFERENT_SLOT)
        self.assertEqual(differences, ("normative_slot",))

    def test_action_and_obligor_order_are_canonical(self) -> None:
        left = signature(
            actions=("notify", "record", "notify"),
            obligors=("User", "Deployer", "User"),
        )
        right = signature(
            actions=("record", "notify"),
            obligors=("Deployer", "User"),
        )
        self.assertEqual(left, right)
        self.assertEqual(left.signature_hash, right.signature_hash)

    def test_report_does_not_overclaim_crosswalk_identity(self) -> None:
        limitations = self.report["limitations"]
        self.assertEqual(limitations["crosswalk_review"], "NOT_PERFORMED_BY_SIGNATURE_EQUALITY")
        self.assertFalse(limitations["recipient_field_available"])
        self.assertFalse(limitations["modality_field_available"])
        self.assertFalse(limitations["trigger_semantics_in_signature"])
        self.assertEqual(self.report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(self.report["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
