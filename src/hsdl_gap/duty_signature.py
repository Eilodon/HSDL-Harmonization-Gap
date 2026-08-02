from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any, Iterable

from .candidate_ir import CompiledDuty, CompiledRule, compile_candidate_profile
from .stable_id import content_sha256


class DutyRelation(str, Enum):
    EXACT_OPERATIONAL_SIGNATURE = "EXACT_OPERATIONAL_SIGNATURE"
    ACTOR_VARIANT = "ACTOR_VARIANT"
    TIMING_VARIANT = "TIMING_VARIANT"
    ACTION_VARIANT = "ACTION_VARIANT"
    OBJECT_VARIANT = "OBJECT_VARIANT"
    MULTI_DIMENSION_VARIANT = "MULTI_DIMENSION_VARIANT"
    INCOMPARABLE_DIFFERENT_SLOT = "INCOMPARABLE_DIFFERENT_SLOT"


@dataclass(frozen=True, slots=True)
class OperationalDutySignature:
    normative_slot: str
    actions: tuple[str, ...]
    object: str
    obligors: tuple[str, ...]
    actor_relation: str
    timing: str

    @classmethod
    def from_duty(cls, duty: CompiledDuty) -> "OperationalDutySignature":
        return cls(
            normative_slot=duty.normative_slot,
            actions=tuple(sorted(set(duty.actions))),
            object=duty.object,
            obligors=tuple(sorted(set(duty.obligors))),
            actor_relation=duty.actor_relation,
            timing=duty.timing,
        )

    def as_mapping(self) -> dict[str, Any]:
        return {
            "normative_slot": self.normative_slot,
            "actions": list(self.actions),
            "object": self.object,
            "obligors": list(self.obligors),
            "actor_relation": self.actor_relation,
            "timing": self.timing,
        }

    @property
    def signature_hash(self) -> str:
        return content_sha256(self.as_mapping())


@dataclass(frozen=True, slots=True)
class DutyRecord:
    jurisdiction: str
    rule_id: str
    duty_id: str
    signature: OperationalDutySignature

    def as_mapping(self) -> dict[str, Any]:
        return {
            "jurisdiction": self.jurisdiction,
            "rule_id": self.rule_id,
            "duty_id": self.duty_id,
            "signature": self.signature.as_mapping(),
            "signature_hash": self.signature.signature_hash,
        }


@dataclass(frozen=True, slots=True)
class DutyComparison:
    source_duty_id: str
    target_duty_id: str
    relation: DutyRelation
    differing_dimensions: tuple[str, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "source_duty_id": self.source_duty_id,
            "target_duty_id": self.target_duty_id,
            "relation": self.relation.value,
            "differing_dimensions": list(self.differing_dimensions),
        }


def compare_operational_signatures(
    source: OperationalDutySignature,
    target: OperationalDutySignature,
) -> tuple[DutyRelation, tuple[str, ...]]:
    if source.normative_slot != target.normative_slot:
        return DutyRelation.INCOMPARABLE_DIFFERENT_SLOT, ("normative_slot",)

    differences: list[str] = []
    if source.actions != target.actions:
        differences.append("actions")
    if source.object != target.object:
        differences.append("object")
    if source.obligors != target.obligors:
        differences.append("obligors")
    if source.actor_relation != target.actor_relation:
        differences.append("actor_relation")
    if source.timing != target.timing:
        differences.append("timing")

    if not differences:
        return DutyRelation.EXACT_OPERATIONAL_SIGNATURE, ()
    difference_set = set(differences)
    if difference_set <= {"obligors", "actor_relation"}:
        return DutyRelation.ACTOR_VARIANT, tuple(differences)
    if difference_set == {"timing"}:
        return DutyRelation.TIMING_VARIANT, tuple(differences)
    if difference_set == {"actions"}:
        return DutyRelation.ACTION_VARIANT, tuple(differences)
    if difference_set == {"object"}:
        return DutyRelation.OBJECT_VARIANT, tuple(differences)
    return DutyRelation.MULTI_DIMENSION_VARIANT, tuple(differences)


def build_duty_inventory(rules: Iterable[CompiledRule]) -> tuple[DutyRecord, ...]:
    records: list[DutyRecord] = []
    for rule in rules:
        for duty in rule.duties:
            records.append(
                DutyRecord(
                    jurisdiction=rule.jurisdiction,
                    rule_id=rule.rule_id,
                    duty_id=duty.duty_id,
                    signature=OperationalDutySignature.from_duty(duty),
                )
            )
    return tuple(records)


def compare_duty_records(
    source: DutyRecord,
    target: DutyRecord,
) -> DutyComparison:
    relation, differences = compare_operational_signatures(
        source.signature, target.signature
    )
    return DutyComparison(
        source_duty_id=source.duty_id,
        target_duty_id=target.duty_id,
        relation=relation,
        differing_dimensions=differences,
    )


def build_operational_signature_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
) -> dict[str, Any]:
    rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    inventory = build_duty_inventory(rules)
    by_jurisdiction: dict[str, tuple[DutyRecord, ...]] = {
        jurisdiction: tuple(
            record for record in inventory if record.jurisdiction == jurisdiction
        )
        for jurisdiction in sorted({record.jurisdiction for record in inventory})
    }
    if set(by_jurisdiction) != {"EU", "VN"}:
        raise ValueError("candidate duty inventory must contain EU and VN duties")

    comparisons = tuple(
        compare_duty_records(source, target)
        for source, target in product(by_jurisdiction["EU"], by_jurisdiction["VN"])
    )
    relation_counts = Counter(item.relation.value for item in comparisons)
    duplicate_hashes = {
        signature_hash: sorted(record.duty_id for record in records)
        for signature_hash, records in _group_by_signature_hash(inventory).items()
        if len(records) > 1
    }
    slot_counts = Counter(record.signature.normative_slot for record in inventory)
    duplicate_slots = {
        slot: count for slot, count in sorted(slot_counts.items()) if count > 1
    }
    same_slot_pairs = [
        item
        for item in comparisons
        if item.relation is not DutyRelation.INCOMPARABLE_DIFFERENT_SLOT
    ]
    exact_pairs = [
        item
        for item in comparisons
        if item.relation is DutyRelation.EXACT_OPERATIONAL_SIGNATURE
    ]
    actor_variant_pairs = [
        item for item in comparisons if item.relation is DutyRelation.ACTOR_VARIANT
    ]
    return {
        "schema_version": "1.0.0",
        "status": "OPERATIONAL_DUTY_SIGNATURE_INVENTORY_COMPLETE",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "candidate_profile_id": "current-candidate-2026-08-02",
        "signature_definition": {
            "fields": [
                "normative_slot",
                "actions",
                "object",
                "obligors",
                "actor_relation",
                "timing",
            ],
            "exact_requires_all_fields_equal": True,
            "action_and_obligor_order": "CANONICAL_SORTED_SET",
        },
        "duty_count": len(inventory),
        "duties_by_jurisdiction": {
            jurisdiction: len(records)
            for jurisdiction, records in by_jurisdiction.items()
        },
        "cross_jurisdiction_pair_count": len(comparisons),
        "cross_jurisdiction_relation_counts": dict(sorted(relation_counts.items())),
        "same_slot_cross_jurisdiction_pair_count": len(same_slot_pairs),
        "exact_cross_jurisdiction_pair_count": len(exact_pairs),
        "actor_variant_cross_jurisdiction_pair_count": len(actor_variant_pairs),
        "duplicate_signature_hashes": duplicate_hashes,
        "duplicate_normative_slots": duplicate_slots,
        "inventory": [record.as_mapping() for record in inventory],
        "same_slot_comparisons": [item.as_mapping() for item in same_slot_pairs],
        "limitations": {
            "recipient_field_available": False,
            "modality_field_available": False,
            "trigger_semantics_in_signature": False,
            "crosswalk_review": "NOT_PERFORMED_BY_SIGNATURE_EQUALITY",
            "notice": (
                "Different normative slots are conservatively incomparable. Zero exact "
                "pairs means the candidate naming/signature layer does not establish an "
                "exact cross-jurisdiction identity; it does not prove that no reviewed "
                "legal crosswalk could exist."
            ),
        },
    }


def _group_by_signature_hash(
    inventory: Iterable[DutyRecord],
) -> dict[str, list[DutyRecord]]:
    grouped: dict[str, list[DutyRecord]] = {}
    for record in inventory:
        grouped.setdefault(record.signature.signature_hash, []).append(record)
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        default="policies/current_candidate_graph_2026-08-02.json",
    )
    parser.add_argument(
        "--fact-bindings",
        default="profiles/current-candidate-2026-08-02/engineering_fact_bindings.json",
    )
    args = parser.parse_args()
    report = build_operational_signature_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
