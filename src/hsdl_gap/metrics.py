from __future__ import annotations

from collections.abc import Iterable

from .context import Context
from .evaluator import evaluate_policy
from .model import Bindingness, Policy

GROUPS = ("G1", "G2", "G3", "G4", "G5", "G6")


def directional_gap_set(
    contexts: Iterable[Context],
    stricter: Policy,
    laxer: Policy,
    group: str,
) -> set[int]:
    out: set[int] = set()
    for index, context in enumerate(contexts):
        left = evaluate_policy(stricter, context, group)
        right = evaluate_policy(laxer, context, group)
        if left.bindingness > right.bindingness:
            out.add(index)
    return out


def obligor_gap_set(
    contexts: Iterable[Context],
    left_policy: Policy,
    right_policy: Policy,
    group: str,
) -> set[int]:
    out: set[int] = set()
    for index, context in enumerate(contexts):
        left = evaluate_policy(left_policy, context, group)
        right = evaluate_policy(right_policy, context, group)
        if (
            left.bindingness > Bindingness.NOT_ADDRESSED
            and right.bindingness > Bindingness.NOT_ADDRESSED
            and left.flattened_obligors != right.flattened_obligors
        ):
            out.add(index)
    return out


def multi_rule_context_count(
    contexts: Iterable[Context], policy: Policy, group: str
) -> int:
    return sum(
        len(evaluate_policy(policy, context, group).active_rule_ids) >= 2
        for context in contexts
    )
