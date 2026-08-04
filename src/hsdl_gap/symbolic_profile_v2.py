from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .candidate_predicates import compile_source_derived_profile
from .conditions_v2 import evaluate_condition_v2
from .stable_id import content_sha256


MISSING = object()
OTHER = "__SYMBOLIC_OTHER__"
SUPPORTED_OPS = frozenset({"all", "and", "or", "eq", "in", "not_in"})


class SymbolicProfileError(ValueError):
    pass


def get_path(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return MISSING
        current = current[part]
    return current


def set_path(payload: dict[str, Any], path: str, value: Any) -> None:
    current = payload
    parts = path.split(".")
    for part in parts[:-1]:
        child = current.setdefault(part, {})
        if not isinstance(child, dict):
            raise SymbolicProfileError(f"cannot set {path!r}")
        current = child
    current[parts[-1]] = value


def tri_and(values: Iterable[str]) -> str:
    values = tuple(values)
    if "FALSE" in values:
        return "FALSE"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    return "TRUE"


def tri_or(values: Iterable[str]) -> str:
    values = tuple(values)
    if "TRUE" in values:
        return "TRUE"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    return "FALSE"


def operand(node: Any, facts: Mapping[str, Any]) -> tuple[Any, set[str]]:
    if not isinstance(node, Mapping):
        raise SymbolicProfileError("operand must be an object")
    if set(node) == {"field"}:
        path = node["field"]
        if not isinstance(path, str) or not path:
            raise SymbolicProfileError("field must be non-empty")
        value = get_path(facts, path)
        return (value, {path}) if value is MISSING else (value, set())
    if set(node) == {"literal"}:
        return node["literal"], set()
    raise SymbolicProfileError("operand must contain field or literal")


def symbolic_evaluate(
    condition: Mapping[str, Any], facts: Mapping[str, Any]
) -> tuple[str, tuple[str, ...]]:
    if not isinstance(condition, Mapping):
        raise SymbolicProfileError("condition must be an object")
    op = condition.get("op")
    args = condition.get("args", [])
    if op not in SUPPORTED_OPS or not isinstance(args, list):
        raise SymbolicProfileError(f"unsupported symbolic condition: {op!r}")
    if op == "all":
        if args:
            raise SymbolicProfileError("all takes no arguments")
        return "TRUE", ()
    if op in {"and", "or"}:
        if not args:
            raise SymbolicProfileError(f"{op} requires arguments")
        children = [symbolic_evaluate(child, facts) for child in args]
        value = tri_and(item[0] for item in children) if op == "and" else tri_or(
            item[0] for item in children
        )
        missing = tuple(sorted({fact for item in children for fact in item[1]}))
        return value, missing
    if len(args) != 2:
        raise SymbolicProfileError(f"{op} requires two arguments")
    left, left_missing = operand(args[0], facts)
    right, right_missing = operand(args[1], facts)
    missing = tuple(sorted(left_missing | right_missing))
    if missing:
        return "UNKNOWN", missing
    try:
        result = left == right if op == "eq" else left in right if op == "in" else left not in right
    except TypeError as exc:
        raise SymbolicProfileError(f"incompatible operands for {op}") from exc
    return ("TRUE" if result else "FALSE"), ()


def add_literal(domains: dict[str, set[Any]], field: str, value: Any) -> None:
    domain = domains.setdefault(field, set())
    if isinstance(value, bool):
        domain.update((True, False))
    elif isinstance(value, str):
        domain.update((value, OTHER))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        domain.update((value - 1, value, value + 1))
    else:
        raise SymbolicProfileError(f"unsupported literal: {value!r}")


def collect_domains(condition: Mapping[str, Any]) -> dict[str, tuple[Any, ...]]:
    domains: dict[str, set[Any]] = {}

    def visit(node: Any) -> None:
        if not isinstance(node, Mapping):
            raise SymbolicProfileError("condition node must be an object")
        op = node.get("op")
        args = node.get("args", [])
        if op not in SUPPORTED_OPS or not isinstance(args, list):
            raise SymbolicProfileError(f"unsupported operator: {op!r}")
        if op == "all":
            if args:
                raise SymbolicProfileError("all takes no arguments")
            return
        if op in {"and", "or"}:
            if not args:
                raise SymbolicProfileError(f"{op} requires arguments")
            for child in args:
                visit(child)
            return
        if len(args) != 2:
            raise SymbolicProfileError(f"{op} requires two arguments")
        left, right = args
        if not isinstance(left, Mapping) or set(left) != {"field"}:
            raise SymbolicProfileError("first operand must be a field")
        if not isinstance(right, Mapping) or set(right) != {"literal"}:
            raise SymbolicProfileError("second operand must be a literal")
        field = left["field"]
        literal = right["literal"]
        if op in {"in", "not_in"}:
            if not isinstance(literal, list) or not literal:
                raise SymbolicProfileError(f"{op} requires a literal list")
            for value in literal:
                add_literal(domains, field, value)
        else:
            add_literal(domains, field, literal)

    visit(condition)
    return {
        field: tuple(
            sorted(values, key=lambda value: (type(value).__name__, repr(value)))
        )
        for field, values in sorted(domains.items())
    }


def assignments(domains: Mapping[str, tuple[Any, ...]]) -> tuple[dict[str, Any], ...]:
    fields = tuple(domains)
    if not fields:
        return ({},)
    result = []
    for values in itertools.product(*(domains[field] for field in fields)):
        facts: dict[str, Any] = {}
        for field, value in zip(fields, values, strict=True):
            set_path(facts, field, value)
        result.append(facts)
    return tuple(result)


def missing_probes(
    domains: Mapping[str, tuple[Any, ...]], complete: tuple[dict[str, Any], ...]
) -> tuple[dict[str, Any], ...]:
    if not domains:
        return ()
    baseline = complete[0]
    result = []
    for omitted in domains:
        facts: dict[str, Any] = {}
        for field in domains:
            if field != omitted:
                set_path(facts, field, get_path(baseline, field))
        result.append(facts)
    return tuple(result)


def canonical_projection(
    condition: Mapping[str, Any], facts: Mapping[str, Any]
) -> tuple[str, tuple[str, ...]]:
    trace = evaluate_condition_v2(condition, facts)
    return trace.value.value, tuple(sorted(set(trace.missing_facts)))


def expression_inventory(rules: tuple[Any, ...]) -> tuple[dict[str, Any], ...]:
    result = []
    for rule in rules:
        result.append(
            {
                "expression_id": f"rule:{rule.rule_id}",
                "rule_id": rule.rule_id,
                "kind": "RULE_PREDICATE",
                "condition": rule.predicate,
            }
        )
        for duty in rule.duties:
            if duty.trigger_condition is not None:
                result.append(
                    {
                        "expression_id": f"duty-trigger:{duty.duty_id}",
                        "rule_id": rule.rule_id,
                        "kind": "DUTY_TRIGGER",
                        "condition": duty.trigger_condition,
                    }
                )
    return tuple(result)


def build_symbolic_profile_v2_report(
    candidate_path: str | Path = "policies/current_candidate_graph_2026-08-02.json",
    predicate_profile_path: str | Path = "profiles/current-candidate-2026-08-02/source_derived_predicates.json",
) -> dict[str, Any]:
    rules = compile_source_derived_profile(candidate_path, predicate_profile_path)
    expressions = expression_inventory(rules)
    reports = []
    mismatches = []
    comparisons = 0
    for expression in expressions:
        condition = expression["condition"]
        domains = collect_domains(condition)
        complete = assignments(domains)
        probes = missing_probes(domains, complete)
        support = []
        false_count = 0
        unknown_count = 0
        local_mismatch = 0
        for facts in complete + probes:
            actual = symbolic_evaluate(condition, facts)
            expected = canonical_projection(condition, facts)
            comparisons += 1
            if actual != expected:
                local_mismatch += 1
                if len(mismatches) < 20:
                    mismatches.append(
                        {
                            "expression_id": expression["expression_id"],
                            "facts": facts,
                            "symbolic": {"value": actual[0], "missing_facts": list(actual[1])},
                            "canonical": {"value": expected[0], "missing_facts": list(expected[1])},
                        }
                    )
            if facts in complete:
                if actual[0] == "TRUE":
                    support.append(facts)
                elif actual[0] == "FALSE":
                    false_count += 1
            elif actual[0] == "UNKNOWN":
                unknown_count += 1
        reports.append(
            {
                "expression_id": expression["expression_id"],
                "rule_id": expression["rule_id"],
                "expression_kind": expression["kind"],
                "field_count": len(domains),
                "domains": {field: list(values) for field, values in domains.items()},
                "complete_assignment_count": len(complete),
                "missing_probe_count": len(probes),
                "support_count": len(support),
                "false_count": false_count,
                "unknown_probe_count": unknown_count,
                "mismatch_count": local_mismatch,
                "support_hash": content_sha256(support),
                "support_sample": support[0] if support else None,
            }
        )
    rule_count = sum(item["kind"] == "RULE_PREDICATE" for item in expressions)
    mismatch_count = sum(item["mismatch_count"] for item in reports)
    return {
        "schema_version": "1.0.0",
        "status": "SOURCE_DERIVED_SYMBOLIC_PROFILE_EQUIVALENT" if mismatch_count == 0 else "SOURCE_DERIVED_SYMBOLIC_PROFILE_MISMATCH",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "supported_operators": sorted(SUPPORTED_OPS),
        "candidate_rule_count": len(rules),
        "symbolically_compiled_rule_count": rule_count,
        "symbolic_rule_coverage": rule_count / len(rules),
        "duty_trigger_expression_count": len(expressions) - rule_count,
        "expression_count": len(expressions),
        "comparison_count": comparisons,
        "mismatch_count": mismatch_count,
        "mismatch_samples": mismatches,
        "expressions": reports,
        "profile_hash": content_sha256([item["condition"] for item in expressions]),
        "limitations": {
            "finite_domain": True,
            "unbounded_symbolic_theorem": "NOT_CLAIMED",
            "independent_legal_review": "PENDING",
            "operator_scope": sorted(SUPPORTED_OPS),
            "notice": "All current source-derived expressions are compiled over finite literal domains. Future unsupported operators fail closed."
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", default="policies/current_candidate_graph_2026-08-02.json")
    parser.add_argument("--predicate-profile", default="profiles/current-candidate-2026-08-02/source_derived_predicates.json")
    args = parser.parse_args()
    report = build_symbolic_profile_v2_report(args.candidate, args.predicate_profile)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if report["mismatch_count"]:
        raise SystemExit(23)


if __name__ == "__main__":
    main()
