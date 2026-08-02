from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .context import Context, iter_legacy_contexts
from .crosswalk import GroupCrosswalk, load_group_crosswalk
from .evaluator import evaluate_policy
from .loader import load_policy_bundle
from .metrics import GROUPS, obligor_gap_set
from .model import PolicyEvaluation, TypedDuty


@dataclass(frozen=True, slots=True)
class AlignmentObservation:
    shared_alignment_keys: frozenset[str]
    shared_normative_slots: frozenset[str]
    exact_actor_mismatch_slots: frozenset[str]
    exact_actor_match_slots: frozenset[str]
    structural_extra_slots_left: frozenset[str]
    structural_extra_slots_right: frozenset[str]
    has_unspecified_obligor_left: bool
    has_unspecified_obligor_right: bool


def _duties_by_slot(evaluation: PolicyEvaluation) -> dict[str, tuple[TypedDuty, ...]]:
    grouped: dict[str, list[TypedDuty]] = defaultdict(list)
    for duty in evaluation.duties:
        if duty.normative_slot:
            grouped[duty.normative_slot].append(duty)
    return {slot: tuple(duties) for slot, duties in grouped.items()}


def _alignment_keys(evaluation: PolicyEvaluation) -> frozenset[str]:
    return frozenset(
        duty.alignment_key for duty in evaluation.duties if duty.alignment_key is not None
    )


def _slot_actors(duties: Iterable[TypedDuty]) -> frozenset[str]:
    actors: set[str] = set()
    for duty in duties:
        actors.update(duty.obligors)
    return frozenset(actors)


def observe_alignment(left: PolicyEvaluation, right: PolicyEvaluation) -> AlignmentObservation:
    left_slots = _duties_by_slot(left)
    right_slots = _duties_by_slot(right)
    shared_slots = frozenset(left_slots) & frozenset(right_slots)
    actor_mismatch: set[str] = set()
    actor_match: set[str] = set()
    for slot in shared_slots:
        if _slot_actors(left_slots[slot]) == _slot_actors(right_slots[slot]):
            actor_match.add(slot)
        else:
            actor_mismatch.add(slot)
    return AlignmentObservation(
        shared_alignment_keys=_alignment_keys(left) & _alignment_keys(right),
        shared_normative_slots=shared_slots,
        exact_actor_mismatch_slots=frozenset(actor_mismatch),
        exact_actor_match_slots=frozenset(actor_match),
        structural_extra_slots_left=frozenset(left_slots) - shared_slots,
        structural_extra_slots_right=frozenset(right_slots) - shared_slots,
        has_unspecified_obligor_left=any(not duty.obligors for duty in left.duties),
        has_unspecified_obligor_right=any(not duty.obligors for duty in right.duties),
    )


def build_typed_alignment_audit(
    policy_path: str | Path,
    crosswalk_path: str | Path,
    contexts: tuple[Context, ...] | None = None,
    duty_semantics_path: str | Path | None = None,
) -> dict[str, object]:
    policies = load_policy_bundle(policy_path, duty_semantics_path)
    crosswalk = load_group_crosswalk(crosswalk_path)
    contexts = contexts or tuple(iter_legacy_contexts())
    groups: dict[str, object] = {}
    typed_mismatch_union: set[int] = set()
    review_union: set[int] = set()
    legacy_gap_union: set[int] = set()

    for group in GROUPS:
        entry: GroupCrosswalk = crosswalk[group]
        counts = {
            "both_active_contexts": 0,
            "left_only_contexts": 0,
            "right_only_contexts": 0,
            "both_silent_contexts": 0,
            "exact_slot_actor_mismatch_contexts": 0,
            "exact_slot_actor_match_contexts": 0,
            "structural_duty_mismatch_contexts": 0,
            "cross_functional_contexts": 0,
            "unspecified_obligor_contexts": 0,
            "contexts_requiring_crosswalk_review": 0,
        }
        observed_shared_slots: set[str] = set()
        observed_alignment_keys: set[str] = set()
        for index, context in enumerate(contexts):
            left = evaluate_policy(policies["EU"], context, group)
            right = evaluate_policy(policies["VN"], context, group)
            left_active = bool(left.active_rule_ids)
            right_active = bool(right.active_rule_ids)
            if left_active and right_active:
                counts["both_active_contexts"] += 1
            elif left_active:
                counts["left_only_contexts"] += 1
                continue
            elif right_active:
                counts["right_only_contexts"] += 1
                continue
            else:
                counts["both_silent_contexts"] += 1
                continue

            observation = observe_alignment(left, right)
            observed_shared_slots.update(observation.shared_normative_slots)
            observed_alignment_keys.update(observation.shared_alignment_keys)
            if observation.has_unspecified_obligor_left or observation.has_unspecified_obligor_right:
                counts["unspecified_obligor_contexts"] += 1

            if observation.exact_actor_mismatch_slots:
                counts["exact_slot_actor_mismatch_contexts"] += 1
                typed_mismatch_union.add(index)
            if observation.exact_actor_match_slots:
                counts["exact_slot_actor_match_contexts"] += 1

            has_structural_extras = bool(
                observation.structural_extra_slots_left
                or observation.structural_extra_slots_right
            )
            if observation.shared_alignment_keys and has_structural_extras:
                counts["structural_duty_mismatch_contexts"] += 1
                counts["contexts_requiring_crosswalk_review"] += 1
                review_union.add(index)
            elif not observation.shared_alignment_keys:
                counts["cross_functional_contexts"] += 1
                counts["contexts_requiring_crosswalk_review"] += 1
                review_union.add(index)

        legacy_gap = obligor_gap_set(
            contexts, policies["EU"], policies["VN"], group
        )
        legacy_gap_union |= legacy_gap
        groups[group] = {
            "declared_relation": entry.relation.value,
            "declared_shared_alignment_keys": list(entry.shared_alignment_keys),
            "review_status": entry.review_status,
            "rationale": entry.rationale,
            "observed_shared_alignment_keys": sorted(observed_alignment_keys),
            "observed_shared_normative_slots": sorted(observed_shared_slots),
            "legacy_flattened_obligor_gap_contexts": len(legacy_gap),
            **counts,
        }

    return {
        "context_count": len(contexts),
        "method": {
            "exact_actor_mismatch": (
                "Actors differ within the same explicit normative_slot."
            ),
            "structural_duty_mismatch": (
                "The regimes share a broad alignment_key but activate different normative_slots."
            ),
            "cross_functional": (
                "Both regimes are active in the legacy group but no broad alignment_key is shared."
            ),
            "warning": (
                "The crosswalk is an author-interpreted audit artifact and is not independent legal sign-off."
            ),
        },
        "groups": groups,
        "unions": {
            "legacy_flattened_obligor_gap_contexts": len(legacy_gap_union),
            "typed_exact_actor_mismatch_contexts": len(typed_mismatch_union),
            "contexts_requiring_crosswalk_review": len(review_union),
        },
    }
