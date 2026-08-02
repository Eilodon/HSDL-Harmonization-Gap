from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .candidate_ir import (
    ApplicabilityState,
    CompiledRule,
    CompilationMode,
    compile_candidate_profile,
    evaluate_compiled_rule,
    load_assumption_sets,
)
from .context_v2 import ContextV2
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import content_sha256


_MISSING = object()


class SymbolicRegionError(ValueError):
    """Raised when a condition cannot be represented by the current region algebra."""


def _canonical_value(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _get_path(payload: Mapping[str, Any], field_path: str) -> Any:
    current: Any = payload
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return _MISSING
        current = current[part]
    return current


def _set_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
    parts = field_path.split(".")
    current = payload
    for part in parts[:-1]:
        nested = current.get(part)
        if nested is None:
            nested = {}
            current[part] = nested
        if not isinstance(nested, dict):
            raise SymbolicRegionError(
                f"cannot assign assumption through non-object path {field_path!r}"
            )
        current = nested
    current[parts[-1]] = value


def _set_nested(payload: dict[str, Any], field_path: str, value: Any) -> None:
    _set_path(payload, field_path, value)


@dataclass(frozen=True, slots=True)
class SymbolicDomain:
    values_by_field: Mapping[str, frozenset[str]]
    decoded_values: Mapping[str, Mapping[str, Any]]

    def values(self, field_path: str) -> frozenset[str]:
        if field_path not in self.values_by_field:
            raise SymbolicRegionError(f"no finite domain for field {field_path!r}")
        return self.values_by_field[field_path]

    def decode(self, field_path: str, encoded: str) -> Any:
        return self.decoded_values[field_path][encoded]


@dataclass(frozen=True, slots=True)
class SymbolicRegion:
    region_id: str
    constraints: Mapping[str, frozenset[str]]
    domain: SymbolicDomain

    @property
    def is_empty(self) -> bool:
        return any(not values for values in self.constraints.values())

    def normalised_values(self, field_path: str) -> frozenset[str]:
        return self.constraints.get(field_path, self.domain.values(field_path))

    def matches(self, facts: Mapping[str, Any]) -> bool:
        if self.is_empty:
            return False
        for field_path, allowed in self.constraints.items():
            actual = _get_path(facts, field_path)
            if actual is _MISSING:
                return False
            if _canonical_value(actual) not in allowed:
                return False
        return True

    def subset_of(self, other: "SymbolicRegion") -> bool:
        fields = set(self.domain.values_by_field) | set(other.domain.values_by_field)
        return all(
            self.normalised_values(field) <= other.normalised_values(field)
            for field in fields
        )

    def disjoint_from(self, other: "SymbolicRegion") -> bool:
        fields = set(self.domain.values_by_field) | set(other.domain.values_by_field)
        return any(
            not (self.normalised_values(field) & other.normalised_values(field))
            for field in fields
        )

    def counterexample_not_subset(self, other: "SymbolicRegion") -> dict[str, Any] | None:
        if self.subset_of(other) or self.is_empty:
            return None
        fields = sorted(set(self.domain.values_by_field) | set(other.domain.values_by_field))
        witness: dict[str, Any] = {}
        chosen_difference = False
        for field in fields:
            source_values = self.normalised_values(field)
            target_values = other.normalised_values(field)
            if not source_values:
                return None
            candidates = sorted(source_values, key=str)
            outside = sorted(source_values - target_values, key=str)
            encoded = outside[0] if outside and not chosen_difference else candidates[0]
            if outside and not chosen_difference:
                chosen_difference = True
            _set_nested(witness, field, self.domain.decode(field, encoded))
        return witness if chosen_difference else None

    def as_mapping(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "empty": self.is_empty,
            "constraints": {
                field: [
                    self.domain.decode(field, value)
                    for value in sorted(values, key=str)
                ]
                for field, values in sorted(self.constraints.items())
            },
        }


def _collect_fields(condition: Mapping[str, Any]) -> set[str]:
    op = condition.get("op")
    args = condition.get("args", [])
    if op in {"and", "or", "not"}:
        return {
            field
            for child in args
            for field in _collect_fields(child)
        }
    fields: set[str] = set()
    for operand in args:
        if isinstance(operand, Mapping) and isinstance(operand.get("field"), str):
            fields.add(operand["field"])
    return fields


def _condition_literals(condition: Mapping[str, Any]) -> dict[str, list[Any]]:
    literals: dict[str, list[Any]] = {}
    op = condition.get("op")
    args = condition.get("args", [])
    if op in {"and", "or", "not"}:
        for child in args:
            for field, values in _condition_literals(child).items():
                literals.setdefault(field, []).extend(values)
        return literals
    if len(args) == 2:
        field_operand, literal_operand = args
        if (
            isinstance(field_operand, Mapping)
            and isinstance(field_operand.get("field"), str)
            and isinstance(literal_operand, Mapping)
            and "literal" in literal_operand
        ):
            raw = literal_operand["literal"]
            values = raw if op in {"in", "not_in"} and isinstance(raw, list) else [raw]
            literals.setdefault(field_operand["field"], []).extend(values)
    return literals


def build_symbolic_domain(
    *,
    conditions: Iterable[Mapping[str, Any]],
    contexts: Iterable[Mapping[str, Any]],
) -> SymbolicDomain:
    condition_list = tuple(conditions)
    fields = sorted({field for condition in condition_list for field in _collect_fields(condition)})
    values_by_field: dict[str, frozenset[str]] = {}
    decoded: dict[str, dict[str, Any]] = {}
    literals: dict[str, list[Any]] = {}
    for condition in condition_list:
        for field, values in _condition_literals(condition).items():
            literals.setdefault(field, []).extend(values)
    context_list = tuple(contexts)
    for field in fields:
        mapping: dict[str, Any] = {}
        for facts in context_list:
            value = _get_path(facts, field)
            if value is _MISSING:
                continue
            mapping[_canonical_value(value)] = value
        for value in literals.get(field, []):
            mapping[_canonical_value(value)] = value
        if not mapping:
            raise SymbolicRegionError(f"field {field!r} has no observed or literal domain")
        values_by_field[field] = frozenset(mapping)
        decoded[field] = mapping
    return SymbolicDomain(values_by_field=values_by_field, decoded_values=decoded)


def _intersect_constraints(
    left: dict[str, frozenset[str]],
    right: Mapping[str, frozenset[str]],
    domain: SymbolicDomain,
) -> dict[str, frozenset[str]]:
    result = dict(left)
    for field in set(left) | set(right):
        allowed_left = left.get(field, domain.values(field))
        allowed_right = right.get(field, domain.values(field))
        result[field] = allowed_left & allowed_right
    return result


def compile_condition_region(
    condition: Mapping[str, Any],
    *,
    domain: SymbolicDomain,
    region_id: str,
) -> SymbolicRegion:
    op = condition.get("op")
    args = condition.get("args", [])
    if op == "all":
        if args:
            raise SymbolicRegionError("all requires zero arguments")
        return SymbolicRegion(region_id=region_id, constraints={}, domain=domain)
    if op == "and":
        constraints: dict[str, frozenset[str]] = {}
        for index, child in enumerate(args):
            compiled = compile_condition_region(
                child,
                domain=domain,
                region_id=f"{region_id}.and{index}",
            )
            constraints = _intersect_constraints(
                constraints, compiled.constraints, domain
            )
        return SymbolicRegion(region_id=region_id, constraints=constraints, domain=domain)
    if op == "known":
        if len(args) != 1 or not isinstance(args[0], Mapping) or "field" not in args[0]:
            raise SymbolicRegionError("known requires one field operand")
        field = args[0]["field"]
        allowed = frozenset(
            encoded
            for encoded in domain.values(field)
            if domain.decode(field, encoded) is not None
        )
        return SymbolicRegion(
            region_id=region_id,
            constraints={field: allowed},
            domain=domain,
        )
    if op in {"eq", "in", "not_in"}:
        if len(args) != 2:
            raise SymbolicRegionError(f"{op} requires two operands")
        field_operand, literal_operand = args
        if not isinstance(field_operand, Mapping) or "field" not in field_operand:
            raise SymbolicRegionError(f"{op} left operand must be a field")
        if not isinstance(literal_operand, Mapping) or "literal" not in literal_operand:
            raise SymbolicRegionError(f"{op} right operand must be a literal")
        field = field_operand["field"]
        raw = literal_operand["literal"]
        values = raw if op in {"in", "not_in"} and isinstance(raw, list) else [raw]
        encoded = frozenset(_canonical_value(value) for value in values)
        if op == "not_in":
            allowed = domain.values(field) - encoded
        else:
            allowed = domain.values(field) & encoded
        return SymbolicRegion(
            region_id=region_id,
            constraints={field: allowed},
            domain=domain,
        )
    raise SymbolicRegionError(f"unsupported symbolic condition op: {op!r}")


def _combined_condition(rule: CompiledRule) -> dict[str, Any]:
    return {
        "op": "and",
        "args": [dict(rule.structural_condition), dict(rule.readiness_condition)],
    }


def _apply_assumption(
    rule: CompiledRule,
    context: ContextV2,
    assumption: Mapping[str, Any],
) -> dict[str, Any]:
    facts = deepcopy(dict(context.facts))
    for fact, value in sorted(assumption.get("values", {}).items()):
        path = rule.fact_paths.get(fact)
        if path is not None:
            _set_path(facts, path, value)
    return facts


def build_symbolic_catalog_region_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
    assumptions_path: str | Path,
    catalog_path: str | Path,
) -> dict[str, Any]:
    rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    explicit_rules = tuple(
        rule
        for rule in rules
        if rule.compilation_mode is CompilationMode.EXPLICIT_CATALOG_ROUTE
    )
    if len(explicit_rules) != 2:
        raise SymbolicRegionError("expected exactly two explicit catalog-route rules")
    contexts = build_decision33_context_v2_corpus(catalog_path)
    assumptions = load_assumption_sets(assumptions_path)
    assumption_id = "ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED"
    assumption = assumptions[assumption_id]
    conditions = tuple(_combined_condition(rule) for rule in explicit_rules)
    assumed_facts = tuple(
        _apply_assumption(rule, context, assumption)
        for rule in explicit_rules
        for context in contexts
    )
    domain = build_symbolic_domain(conditions=conditions, contexts=assumed_facts)
    regions = {
        rule.rule_id: compile_condition_region(
            _combined_condition(rule),
            domain=domain,
            region_id=f"region:{rule.rule_id}",
        )
        for rule in explicit_rules
    }

    mismatch_samples: list[dict[str, Any]] = []
    mismatch_count = 0
    comparison_count = 0
    support_counts: Counter[str] = Counter()
    for rule in explicit_rules:
        region = regions[rule.rule_id]
        for context in contexts:
            facts = _apply_assumption(rule, context, assumption)
            symbolic = region.matches(facts)
            evaluated = evaluate_compiled_rule(
                rule,
                context,
                assumption_values=assumption.get("values", {}),
                satisfied_required_facts=tuple(
                    assumption.get("satisfied_required_facts", ())
                ),
            )
            finite = evaluated.state in {
                ApplicabilityState.APPLICABLE_DETERMINATE,
                ApplicabilityState.APPLICABLE_UNSPECIFIED_OBLIGOR,
                ApplicabilityState.APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR,
            }
            comparison_count += 1
            if symbolic:
                support_counts[rule.rule_id] += 1
            if symbolic != finite:
                mismatch_count += 1
                if len(mismatch_samples) < 20:
                    mismatch_samples.append(
                        {
                            "rule_id": rule.rule_id,
                            "context_id": context.context_id,
                            "symbolic": symbolic,
                            "finite": finite,
                            "finite_state": evaluated.state.value,
                        }
                    )

    left, right = explicit_rules
    left_region = regions[left.rule_id]
    right_region = regions[right.rule_id]
    refinements = {
        f"{left.rule_id}->{right.rule_id}": {
            "is_subset": left_region.subset_of(right_region),
            "is_disjoint": left_region.disjoint_from(right_region),
            "counterexample": left_region.counterexample_not_subset(right_region),
        },
        f"{right.rule_id}->{left.rule_id}": {
            "is_subset": right_region.subset_of(left_region),
            "is_disjoint": right_region.disjoint_from(left_region),
            "counterexample": right_region.counterexample_not_subset(left_region),
        },
    }
    domain_mapping = {
        field: [domain.decode(field, value) for value in sorted(values, key=str)]
        for field, values in sorted(domain.values_by_field.items())
    }
    return {
        "schema_version": "1.0.0",
        "status": (
            "SYMBOLIC_EXPLICIT_ROUTE_ORACLE_EQUIVALENT"
            if mismatch_count == 0
            else "SYMBOLIC_EXPLICIT_ROUTE_ORACLE_MISMATCH"
        ),
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "assumption_set_id": assumption_id,
        "candidate_rule_count": len(rules),
        "symbolically_compiled_rule_count": len(explicit_rules),
        "symbolic_rule_coverage": len(explicit_rules) / len(rules),
        "context_count": len(contexts),
        "comparison_count": comparison_count,
        "mismatch_count": mismatch_count,
        "mismatch_samples": mismatch_samples,
        "support_counts": dict(sorted(support_counts.items())),
        "domain_hash": content_sha256(domain_mapping),
        "domain": domain_mapping,
        "regions": {
            rule_id: region.as_mapping()
            for rule_id, region in sorted(regions.items())
        },
        "directed_refinements": refinements,
        "complexity": {
            "region_match": "O(number_of_constrained_fields)",
            "subset": "O(number_of_domain_fields * set_inclusion_cost)",
            "finite_differential": "O(explicit_rules * contexts)",
        },
        "limitations": {
            "supported_condition_ops": ["all", "and", "known", "eq", "in", "not_in"],
            "generic_candidate_rules": "NOT_SYMBOLICALLY_COMPILED",
            "correlated_field_constraints": "NOT_REPRESENTED_BEYOND_CONJUNCTION",
            "symbolic_current_profile_complete": False,
            "notice": (
                "This is a complete symbolic representation only for the two explicit "
                "Decision 33 catalog-route predicates under one declared assumption set."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate", default="policies/current_candidate_graph_2026-08-02.json"
    )
    parser.add_argument(
        "--fact-bindings",
        default="profiles/current-candidate-2026-08-02/engineering_fact_bindings.json",
    )
    parser.add_argument(
        "--assumptions",
        default="profiles/current-candidate-2026-08-02/engineering_assumptions.json",
    )
    parser.add_argument("--catalog", default="catalogs/vn_decision_33_2026.csv")
    args = parser.parse_args()
    report = build_symbolic_catalog_region_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
        assumptions_path=args.assumptions,
        catalog_path=args.catalog,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if report["status"] != "SYMBOLIC_EXPLICIT_ROUTE_ORACLE_EQUIVALENT":
        raise SystemExit(15)


if __name__ == "__main__":
    main()
