from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from .tristate import TruthValue, tri_and, tri_not, tri_or


_MISSING = object()


class ConditionV2Error(ValueError):
    """Raised when a condition document is structurally invalid."""


@dataclass(frozen=True, slots=True)
class ConditionTrace:
    op: str
    value: TruthValue
    path: str
    detail: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["ConditionTrace", ...] = field(default_factory=tuple)
    missing_facts: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "op": self.op,
            "value": self.value.value,
            "path": self.path,
            "detail": dict(self.detail),
            "missing_facts": list(self.missing_facts),
            "children": [child.as_dict() for child in self.children],
        }


def _get_path(context: Mapping[str, Any], field_path: str) -> Any:
    current: Any = context
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _require_mapping(value: Any, *, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConditionV2Error(f"{path} must be an object")
    return value


def _require_args(
    condition: Mapping[str, Any],
    *,
    path: str,
    exact: int | None = None,
    minimum: int | None = None,
) -> list[Any]:
    args = condition.get("args", [])
    if not isinstance(args, list):
        raise ConditionV2Error(f"{path}.args must be an array")
    if exact is not None and len(args) != exact:
        raise ConditionV2Error(f"{path}.args must contain exactly {exact} items")
    if minimum is not None and len(args) < minimum:
        raise ConditionV2Error(f"{path}.args must contain at least {minimum} items")
    return args


def _operand(
    node: Any,
    context: Mapping[str, Any],
    *,
    path: str,
) -> tuple[Any, tuple[str, ...], Mapping[str, Any]]:
    operand = _require_mapping(node, path=path)
    keys = set(operand)
    if keys == {"field"}:
        field_name = operand["field"]
        if not isinstance(field_name, str) or not field_name:
            raise ConditionV2Error(f"{path}.field must be a non-empty string")
        value = _get_path(context, field_name)
        if value is _MISSING:
            return _MISSING, (field_name,), {"kind": "field", "field": field_name}
        return value, (), {"kind": "field", "field": field_name, "actual": value}
    if keys == {"literal"}:
        return operand["literal"], (), {"kind": "literal", "literal": operand["literal"]}
    raise ConditionV2Error(
        f"{path} must contain exactly one of 'field' or 'literal'"
    )


def _merge_missing(children: Sequence[ConditionTrace]) -> tuple[str, ...]:
    return tuple(sorted({fact for child in children for fact in child.missing_facts}))


def _parse_date(value: Any, *, path: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ConditionV2Error(f"{path} must be an ISO-8601 date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ConditionV2Error(f"{path} must be an ISO-8601 date string") from exc


def _binary_values(
    condition: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    path: str,
) -> tuple[Any, Any, tuple[str, ...], Mapping[str, Any]]:
    args = _require_args(condition, path=path, exact=2)
    left, left_missing, left_detail = _operand(args[0], context, path=f"{path}.args[0]")
    right, right_missing, right_detail = _operand(
        args[1], context, path=f"{path}.args[1]"
    )
    return (
        left,
        right,
        tuple(sorted(set(left_missing + right_missing))),
        {"left": left_detail, "right": right_detail},
    )


def evaluate_condition_v2(
    condition: Mapping[str, Any],
    context: Mapping[str, Any],
    *,
    path: str = "$",
) -> ConditionTrace:
    condition = _require_mapping(condition, path=path)
    op = condition.get("op")
    if not isinstance(op, str) or not op:
        raise ConditionV2Error(f"{path}.op must be a non-empty string")

    if op == "all":
        _require_args(condition, path=path, exact=0)
        return ConditionTrace(op=op, value=TruthValue.TRUE, path=path)

    if op in {"and", "or"}:
        args = _require_args(condition, path=path, minimum=1)
        children = tuple(
            evaluate_condition_v2(
                _require_mapping(item, path=f"{path}.args[{index}]"),
                context,
                path=f"{path}.args[{index}]",
            )
            for index, item in enumerate(args)
        )
        value = tri_and(child.value for child in children) if op == "and" else tri_or(
            child.value for child in children
        )
        return ConditionTrace(
            op=op,
            value=value,
            path=path,
            children=children,
            missing_facts=_merge_missing(children),
        )

    if op == "not":
        args = _require_args(condition, path=path, exact=1)
        child = evaluate_condition_v2(
            _require_mapping(args[0], path=f"{path}.args[0]"),
            context,
            path=f"{path}.args[0]",
        )
        return ConditionTrace(
            op=op,
            value=tri_not(child.value),
            path=path,
            children=(child,),
            missing_facts=child.missing_facts,
        )

    if op in {"exists", "missing", "known"}:
        args = _require_args(condition, path=path, exact=1)
        operand = _require_mapping(args[0], path=f"{path}.args[0]")
        if set(operand) != {"field"}:
            raise ConditionV2Error(f"{path}.args[0] must be a field operand")
        field_name = operand["field"]
        if not isinstance(field_name, str) or not field_name:
            raise ConditionV2Error(f"{path}.args[0].field must be a non-empty string")
        value = _get_path(context, field_name)
        present = value is not _MISSING
        if op == "exists":
            result = present
        elif op == "missing":
            result = not present
        else:
            result = present and value is not None
        return ConditionTrace(
            op=op,
            value=TruthValue.from_bool(result),
            path=path,
            detail={
                "field": field_name,
                "present": present,
                "actual": None if not present else value,
            },
            missing_facts=(field_name,) if op == "known" and not result else (),
        )

    if op in {
        "eq",
        "ne",
        "in",
        "not_in",
        "lt",
        "lte",
        "gt",
        "gte",
        "contains",
        "contains_any",
        "contains_all",
        "overlaps",
        "before",
        "on_or_before",
        "after",
        "on_or_after",
    }:
        left, right, missing, detail = _binary_values(
            condition, context, path=path
        )
        if missing:
            return ConditionTrace(
                op=op,
                value=TruthValue.UNKNOWN,
                path=path,
                detail=detail,
                missing_facts=missing,
            )

        try:
            if op == "eq":
                result = left == right
            elif op == "ne":
                result = left != right
            elif op == "in":
                result = left in right
            elif op == "not_in":
                result = left not in right
            elif op == "lt":
                result = left < right
            elif op == "lte":
                result = left <= right
            elif op == "gt":
                result = left > right
            elif op == "gte":
                result = left >= right
            elif op == "contains":
                result = right in left
            elif op == "contains_any":
                result = bool(set(left) & set(right))
            elif op == "contains_all":
                result = set(right) <= set(left)
            elif op == "overlaps":
                result = bool(set(left) & set(right))
            else:
                left_date = _parse_date(left, path=f"{path}.args[0]")
                right_date = _parse_date(right, path=f"{path}.args[1]")
                if op == "before":
                    result = left_date < right_date
                elif op == "on_or_before":
                    result = left_date <= right_date
                elif op == "after":
                    result = left_date > right_date
                else:
                    result = left_date >= right_date
        except (TypeError, ValueError) as exc:
            raise ConditionV2Error(f"{path} operands are incompatible for {op}") from exc
        return ConditionTrace(
            op=op,
            value=TruthValue.from_bool(result),
            path=path,
            detail=detail,
        )

    if op == "between":
        args = _require_args(condition, path=path, exact=3)
        value, value_missing, value_detail = _operand(
            args[0], context, path=f"{path}.args[0]"
        )
        lower, lower_missing, lower_detail = _operand(
            args[1], context, path=f"{path}.args[1]"
        )
        upper, upper_missing, upper_detail = _operand(
            args[2], context, path=f"{path}.args[2]"
        )
        missing = tuple(sorted(set(value_missing + lower_missing + upper_missing)))
        detail = {
            "value": value_detail,
            "lower": lower_detail,
            "upper": upper_detail,
        }
        if missing:
            return ConditionTrace(
                op=op,
                value=TruthValue.UNKNOWN,
                path=path,
                detail=detail,
                missing_facts=missing,
            )
        try:
            result = lower <= value <= upper
        except TypeError as exc:
            raise ConditionV2Error(f"{path} operands are incompatible for between") from exc
        return ConditionTrace(
            op=op,
            value=TruthValue.from_bool(result),
            path=path,
            detail=detail,
        )

    raise ConditionV2Error(f"Unsupported condition v2 op: {op!r}")
