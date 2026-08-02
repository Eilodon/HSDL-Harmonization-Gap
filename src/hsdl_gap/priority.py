from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from .conditions import evaluate_condition
from .context import Context
from .model import Policy, TypedDuty


class PriorityState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DETERMINATE = "DETERMINATE"
    PRIORITY_INDETERMINATE = "PRIORITY_INDETERMINATE"


@dataclass(frozen=True, slots=True)
class ConflictResolution:
    conflict_class: str
    normative_slot: str
    state: PriorityState
    active_duty_ids: tuple[str, ...]


def resolve_declared_conflicts(
    policy: Policy,
    context: Context,
    group: str,
) -> tuple[ConflictResolution, ...]:
    mapping = context.as_mapping()
    active_rules = tuple(
        rule
        for rule in policy.rules_for_group(group)
        if evaluate_condition(rule.condition, mapping)
    )
    grouped: dict[str, list[TypedDuty]] = defaultdict(list)
    for rule in active_rules:
        for duty in rule.consequences:
            if duty.conflict_class is not None:
                grouped[duty.conflict_class].append(duty)

    resolutions: list[ConflictResolution] = []
    for conflict_class, duties in sorted(grouped.items()):
        slots = {duty.normative_slot for duty in duties}
        if None in slots or len(slots) != 1:
            raise ValueError(
                f"conflict class {conflict_class!r} spans missing or multiple normative slots: {slots}"
            )
        state = (
            PriorityState.DETERMINATE
            if len(duties) == 1
            else PriorityState.PRIORITY_INDETERMINATE
        )
        resolutions.append(
            ConflictResolution(
                conflict_class=conflict_class,
                normative_slot=next(iter(slots)),
                state=state,
                active_duty_ids=tuple(sorted(duty.id for duty in duties)),
            )
        )
    return tuple(resolutions)
