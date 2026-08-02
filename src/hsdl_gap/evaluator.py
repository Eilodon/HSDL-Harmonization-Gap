from __future__ import annotations

from .conditions import evaluate_condition
from .context import Context
from .model import Bindingness, EvaluationState, Policy, PolicyEvaluation


def evaluate_policy(policy: Policy, context: Context, group: str) -> PolicyEvaluation:
    mapping = context.as_mapping()
    active = [
        rule
        for rule in policy.rules_for_group(group)
        if evaluate_condition(rule.condition, mapping)
    ]
    if not active:
        return PolicyEvaluation(state=EvaluationState.NO_APPLICABLE_RULE)

    bindingness = max(rule.bindingness for rule in active)
    duties = tuple(duty for rule in active for duty in rule.consequences)
    state = (
        EvaluationState.UNSPECIFIED_OBLIGOR
        if duties and all(not duty.obligors for duty in duties)
        else EvaluationState.DETERMINATE
    )
    return PolicyEvaluation(
        state=state,
        active_rule_ids=tuple(rule.id for rule in active),
        bindingness=Bindingness(bindingness),
        duties=duties,
    )
