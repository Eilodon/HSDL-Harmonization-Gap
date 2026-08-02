from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class ConditionError(ValueError):
    pass


def evaluate_condition(condition: Mapping[str, Any], context: Mapping[str, object]) -> bool:
    op = condition.get("op")
    args = condition.get("args", [])

    if op == "all":
        return True
    if op == "and":
        return all(evaluate_condition(item, context) for item in args)
    if op == "or":
        return any(evaluate_condition(item, context) for item in args)
    if op == "not":
        if len(args) != 1:
            raise ConditionError("not expects exactly one argument")
        return not evaluate_condition(args[0], context)
    if op == "eq":
        field, expected = args
        return context[field] == expected
    if op == "in":
        field, expected = args
        return context[field] in expected

    raise ConditionError(f"Unsupported condition op: {op!r}")
