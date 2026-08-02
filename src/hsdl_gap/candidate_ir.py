from __future__ import annotations

import argparse
import json
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .conditions_v2 import ConditionTrace, evaluate_condition_v2
from .context_v2 import ContextV2, FixtureType
from .current_candidate import load_current_candidate, validate_current_candidate
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import content_sha256
from .tristate import TruthValue


class CompilationMode(str, Enum):
    UNCONDITIONAL_DECLARED = "UNCONDITIONAL_DECLARED"
    EXPLICIT_CATALOG_ROUTE = "EXPLICIT_CATALOG_ROUTE"
    REQUIRED_FACTS_READINESS_ONLY = "REQUIRED_FACTS_READINESS_ONLY"


class ApplicabilityState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    APPLICABLE_DETERMINATE = "APPLICABLE_DETERMINATE"
    APPLICABLE_UNSPECIFIED_OBLIGOR = "APPLICABLE_UNSPECIFIED_OBLIGOR"
    APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR = (
        "APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR"
    )
    INDETERMINATE_MISSING_FACTS = "INDETERMINATE_MISSING_FACTS"
    INDETERMINATE_PREDICATE_NOT_COMPILED = (
        "INDETERMINATE_PREDICATE_NOT_COMPILED"
    )


class DutyState(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    APPLICABILITY_UNKNOWN = "APPLICABILITY_UNKNOWN"
    APPLICABLE_DETERMINATE = "APPLICABLE_DETERMINATE"
    APPLICABLE_UNSPECIFIED_OBLIGOR = "APPLICABLE_UNSPECIFIED_OBLIGOR"


class CandidateIRError(ValueError):
    """Raised when candidate compilation inputs violate their safety contract."""


@dataclass(frozen=True, slots=True)
class CompiledDuty:
    duty_id: str
    normative_slot: str
    actions: tuple[str, ...]
    object: str
    obligors: tuple[str, ...]
    actor_relation: str
    timing: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "duty_id": self.duty_id,
            "normative_slot": self.normative_slot,
            "actions": list(self.actions),
            "object": self.object,
            "obligors": list(self.obligors),
            "actor_relation": self.actor_relation,
            "timing": self.timing,
        }


@dataclass(frozen=True, slots=True)
class CompiledRule:
    rule_id: str
    jurisdiction: str
    source_id: str
    provision: str
    review_status: str
    activation_status: str
    compilation_mode: CompilationMode
    required_facts: tuple[str, ...]
    fact_paths: Mapping[str, str]
    readiness_condition: Mapping[str, Any]
    structural_condition: Mapping[str, Any]
    predicate_semantics_complete: bool
    uncompiled_predicate_facts: tuple[str, ...]
    duties: tuple[CompiledDuty, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "jurisdiction": self.jurisdiction,
            "source_id": self.source_id,
            "provision": self.provision,
            "review_status": self.review_status,
            "activation_status": self.activation_status,
            "compilation_mode": self.compilation_mode.value,
            "required_facts": list(self.required_facts),
            "fact_paths": dict(self.fact_paths),
            "readiness_condition": dict(self.readiness_condition),
            "structural_condition": dict(self.structural_condition),
            "predicate_semantics_complete": self.predicate_semantics_complete,
            "uncompiled_predicate_facts": list(self.uncompiled_predicate_facts),
            "duties": [duty.as_mapping() for duty in self.duties],
        }


@dataclass(frozen=True, slots=True)
class DutyEvaluation:
    duty_id: str
    normative_slot: str
    state: DutyState
    obligors: tuple[str, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "duty_id": self.duty_id,
            "normative_slot": self.normative_slot,
            "state": self.state.value,
            "obligors": list(self.obligors),
        }


@dataclass(frozen=True, slots=True)
class RuleIREvaluation:
    rule_id: str
    context_id: str
    state: ApplicabilityState
    structural_trace: ConditionTrace
    readiness_trace: ConditionTrace
    missing_facts: tuple[str, ...]
    assumptions_used: tuple[str, ...]
    duties: tuple[DutyEvaluation, ...]
    reason: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "context_id": self.context_id,
            "state": self.state.value,
            "structural_trace": self.structural_trace.as_dict(),
            "readiness_trace": self.readiness_trace.as_dict(),
            "missing_facts": list(self.missing_facts),
            "assumptions_used": list(self.assumptions_used),
            "duties": [duty.as_mapping() for duty in self.duties],
            "reason": self.reason,
        }


def _load_json_object(path: str | Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CandidateIRError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise CandidateIRError(f"{label} must be a JSON object")
    return payload


def _condition_all(parts: list[dict[str, Any]]) -> dict[str, Any]:
    if not parts:
        return {"op": "all", "args": []}
    if len(parts) == 1:
        return parts[0]
    return {"op": "and", "args": parts}


def _known_condition(path: str) -> dict[str, Any]:
    return {"op": "known", "args": [{"field": path}]}


def _eq_condition(path: str, value: Any) -> dict[str, Any]:
    return {
        "op": "eq",
        "args": [{"field": path}, {"literal": value}],
    }


def _in_condition(path: str, values: list[str]) -> dict[str, Any]:
    return {
        "op": "in",
        "args": [{"field": path}, {"literal": values}],
    }


def _not_in_condition(path: str, values: list[str]) -> dict[str, Any]:
    return {
        "op": "not_in",
        "args": [{"field": path}, {"literal": values}],
    }


def _required_fact_inventory(candidate: Mapping[str, Any]) -> set[str]:
    facts: set[str] = set()
    for rule in candidate.get("binding_rule_graph", []):
        if not isinstance(rule, Mapping):
            continue
        activation = rule.get("activation_model", {})
        if isinstance(activation, Mapping):
            required = activation.get("required_facts", [])
            if isinstance(required, list):
                facts.update(item for item in required if isinstance(item, str))
    return facts


def load_fact_bindings(path: str | Path) -> dict[str, str]:
    payload = _load_json_object(path, label="fact bindings")
    if payload.get("legal_validation") != "NOT_ASSERTED":
        raise CandidateIRError("fact bindings must not assert legal validation")
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        raise CandidateIRError("fact bindings must contain a bindings object")
    result: dict[str, str] = {}
    for fact, field_path in bindings.items():
        if not isinstance(fact, str) or not fact:
            raise CandidateIRError("fact binding names must be non-empty strings")
        if not isinstance(field_path, str) or not field_path:
            raise CandidateIRError(f"fact binding {fact!r} must have a field path")
        result[fact] = field_path
    return result


def load_assumption_sets(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = _load_json_object(path, label="engineering assumptions")
    if payload.get("claim_class") != "MODEL_RELATIVE":
        raise CandidateIRError("engineering assumptions must be model-relative")
    if payload.get("legal_validation") != "NOT_ASSERTED":
        raise CandidateIRError("engineering assumptions must not assert legal validation")
    raw_sets = payload.get("assumption_sets")
    if not isinstance(raw_sets, list):
        raise CandidateIRError("engineering assumptions must contain assumption_sets")
    result: dict[str, dict[str, Any]] = {}
    for item in raw_sets:
        if not isinstance(item, dict):
            raise CandidateIRError("assumption sets must be objects")
        assumption_id = item.get("id")
        if not isinstance(assumption_id, str) or not assumption_id:
            raise CandidateIRError("assumption set ID must be non-empty")
        if assumption_id in result:
            raise CandidateIRError(f"duplicate assumption set: {assumption_id}")
        values = item.get("values", {})
        satisfied = item.get("satisfied_required_facts", [])
        if not isinstance(values, dict) or not isinstance(satisfied, list):
            raise CandidateIRError(f"invalid assumption set: {assumption_id}")
        if not all(isinstance(fact, str) and fact for fact in satisfied):
            raise CandidateIRError(
                f"assumption set {assumption_id} has invalid satisfied facts"
            )
        result[assumption_id] = {
            "values": dict(values),
            "satisfied_required_facts": tuple(sorted(set(satisfied))),
            "purpose": item.get("purpose"),
        }
    return result


def compile_candidate_profile(
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
) -> tuple[CompiledRule, ...]:
    candidate = load_current_candidate(candidate_path)
    candidate_errors = validate_current_candidate(candidate_path)
    if candidate_errors:
        raise CandidateIRError(
            "candidate safety validation failed: " + "; ".join(candidate_errors)
        )
    policy = candidate.get("evaluation_policy", {})
    for field in (
        "quantitative_evaluation_allowed",
        "directional_gap_metrics_allowed",
        "actor_mismatch_metrics_allowed",
    ):
        if policy.get(field) is not False:
            raise CandidateIRError(
                f"candidate compiler refuses profile with {field} enabled"
            )

    bindings = load_fact_bindings(fact_bindings_path)
    required_inventory = _required_fact_inventory(candidate)
    missing_bindings = sorted(required_inventory - set(bindings))
    if missing_bindings:
        raise CandidateIRError(f"missing fact bindings: {missing_bindings}")

    point_a_ids: list[str] = []
    for rule in candidate["binding_rule_graph"]:
        activation = rule["activation_model"]
        ids = activation.get("catalog_item_ids")
        if isinstance(ids, list):
            point_a_ids.extend(item for item in ids if isinstance(item, str))
    point_a_ids = sorted(set(point_a_ids))

    compiled: list[CompiledRule] = []
    for rule in candidate["binding_rule_graph"]:
        activation = rule["activation_model"]
        required_facts = tuple(activation.get("required_facts", []))
        fact_paths = {fact: bindings[fact] for fact in required_facts}
        readiness = _condition_all(
            [_known_condition(fact_paths[fact]) for fact in required_facts]
        )

        structural_parts: list[dict[str, Any]] = []
        catalog_route = activation.get("catalog_route")
        if isinstance(catalog_route, str):
            structural_parts.extend(
                (
                    _eq_condition("classification.vn.listed", True),
                    _eq_condition(
                        "classification.vn.assessment_route", catalog_route
                    ),
                )
            )
            item_ids = activation.get("catalog_item_ids")
            item_set = activation.get("catalog_item_set")
            if isinstance(item_ids, list):
                structural_parts.append(
                    _in_condition(
                        "classification.vn.catalog_item_id",
                        [item for item in item_ids if isinstance(item, str)],
                    )
                )
            elif item_set == "ALL_DECISION33_ITEMS_EXCEPT_POINT_A_IDS":
                structural_parts.append(
                    _not_in_condition(
                        "classification.vn.catalog_item_id", point_a_ids
                    )
                )
            mode = CompilationMode.EXPLICIT_CATALOG_ROUTE
            uncompiled = tuple(
                fact for fact in required_facts if fact != "catalog_item_id"
            )
            predicate_complete = not uncompiled
        elif not required_facts:
            mode = CompilationMode.UNCONDITIONAL_DECLARED
            uncompiled = ()
            predicate_complete = True
        else:
            mode = CompilationMode.REQUIRED_FACTS_READINESS_ONLY
            uncompiled = required_facts
            predicate_complete = False

        duties = tuple(
            CompiledDuty(
                duty_id=f"{rule['id']}:{item['normative_slot']}",
                normative_slot=item["normative_slot"],
                actions=tuple(item["actions"]),
                object=item["object"],
                obligors=tuple(item["obligors"]),
                actor_relation=item["actor_relation"],
                timing=item["timing"],
            )
            for item in rule["consequences"]
        )
        compiled.append(
            CompiledRule(
                rule_id=rule["id"],
                jurisdiction=rule["jurisdiction"],
                source_id=rule["source_id"],
                provision=rule["provision"],
                review_status=rule["review_status"],
                activation_status=activation["status"],
                compilation_mode=mode,
                required_facts=required_facts,
                fact_paths=fact_paths,
                readiness_condition=readiness,
                structural_condition=_condition_all(structural_parts),
                predicate_semantics_complete=predicate_complete,
                uncompiled_predicate_facts=uncompiled,
                duties=duties,
            )
        )
    return tuple(compiled)


def _set_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
    parts = field_path.split(".")
    current = payload
    for part in parts[:-1]:
        nested = current.get(part)
        if nested is None:
            nested = {}
            current[part] = nested
        if not isinstance(nested, dict):
            raise CandidateIRError(
                f"cannot apply assumption through non-object path {field_path!r}"
            )
        current = nested
    current[parts[-1]] = value


def _missing_required_facts(
    rule: CompiledRule,
    readiness_trace: ConditionTrace,
) -> tuple[str, ...]:
    missing_paths = set(readiness_trace.missing_facts)
    return tuple(
        sorted(
            fact
            for fact, path in rule.fact_paths.items()
            if path in missing_paths
        )
    )


def _duty_evaluations(
    rule: CompiledRule,
    state: ApplicabilityState,
) -> tuple[DutyEvaluation, ...]:
    if state is ApplicabilityState.NOT_APPLICABLE:
        duty_state = DutyState.NOT_APPLICABLE
        return tuple(
            DutyEvaluation(
                duty_id=duty.duty_id,
                normative_slot=duty.normative_slot,
                state=duty_state,
                obligors=duty.obligors,
            )
            for duty in rule.duties
        )
    if state in {
        ApplicabilityState.INDETERMINATE_MISSING_FACTS,
        ApplicabilityState.INDETERMINATE_PREDICATE_NOT_COMPILED,
    }:
        duty_state = DutyState.APPLICABILITY_UNKNOWN
        return tuple(
            DutyEvaluation(
                duty_id=duty.duty_id,
                normative_slot=duty.normative_slot,
                state=duty_state,
                obligors=duty.obligors,
            )
            for duty in rule.duties
        )
    return tuple(
        DutyEvaluation(
            duty_id=duty.duty_id,
            normative_slot=duty.normative_slot,
            state=(
                DutyState.APPLICABLE_DETERMINATE
                if duty.obligors
                else DutyState.APPLICABLE_UNSPECIFIED_OBLIGOR
            ),
            obligors=duty.obligors,
        )
        for duty in rule.duties
    )


def evaluate_compiled_rule(
    rule: CompiledRule,
    context: ContextV2,
    *,
    assumption_values: Mapping[str, Any] | None = None,
    satisfied_required_facts: tuple[str, ...] = (),
) -> RuleIREvaluation:
    values = dict(assumption_values or {})
    facts = deepcopy(dict(context.facts))
    assumptions_used: list[str] = []
    for fact, value in sorted(values.items()):
        path = rule.fact_paths.get(fact)
        if path is None:
            continue
        _set_path(facts, path, value)
        assumptions_used.append(fact)

    structural = evaluate_condition_v2(rule.structural_condition, facts)
    readiness = evaluate_condition_v2(rule.readiness_condition, facts)
    missing_facts = _missing_required_facts(rule, readiness)

    if structural.value is TruthValue.FALSE:
        state = ApplicabilityState.NOT_APPLICABLE
        reason = "The explicit structural condition is false for this context."
    elif structural.value is TruthValue.UNKNOWN:
        state = ApplicabilityState.INDETERMINATE_MISSING_FACTS
        missing_facts = tuple(
            sorted(set(missing_facts) | set(structural.missing_facts))
        )
        reason = "The explicit structural condition cannot be decided from the context."
    elif rule.compilation_mode is CompilationMode.UNCONDITIONAL_DECLARED:
        state = _applicable_state(rule)
        reason = "The candidate graph declares no activation facts for this rule."
    elif readiness.value is not TruthValue.TRUE:
        state = ApplicabilityState.INDETERMINATE_MISSING_FACTS
        reason = "One or more required activation facts are missing or unknown."
    elif rule.compilation_mode is CompilationMode.REQUIRED_FACTS_READINESS_ONLY:
        state = ApplicabilityState.INDETERMINATE_PREDICATE_NOT_COMPILED
        reason = (
            "The candidate graph names required facts but does not yet encode their "
            "truth conditions, polarity or exceptions."
        )
    else:
        satisfied = set(satisfied_required_facts)
        unresolved = set(rule.uncompiled_predicate_facts) - satisfied
        if unresolved:
            state = ApplicabilityState.INDETERMINATE_PREDICATE_NOT_COMPILED
            reason = (
                "Explicit catalog routing matches, but remaining predicate facts have "
                "not been declared satisfied by this assumption set."
            )
        else:
            state = _applicable_state(rule)
            reason = (
                "Explicit catalog routing matches and every remaining required fact is "
                "declared satisfied by the model-relative assumption set."
            )

    return RuleIREvaluation(
        rule_id=rule.rule_id,
        context_id=context.context_id,
        state=state,
        structural_trace=structural,
        readiness_trace=readiness,
        missing_facts=missing_facts,
        assumptions_used=tuple(assumptions_used),
        duties=_duty_evaluations(rule, state),
        reason=reason,
    )


def _applicable_state(rule: CompiledRule) -> ApplicabilityState:
    empty = sum(not duty.obligors for duty in rule.duties)
    if empty == len(rule.duties):
        return ApplicabilityState.APPLICABLE_UNSPECIFIED_OBLIGOR
    if empty:
        return ApplicabilityState.APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR
    return ApplicabilityState.APPLICABLE_DETERMINATE


def _scenario_summary(
    rules: tuple[CompiledRule, ...],
    contexts: tuple[ContextV2, ...],
    *,
    assumption_id: str,
    assumption: Mapping[str, Any],
) -> dict[str, Any]:
    state_counts: Counter[str] = Counter()
    by_rule: dict[str, dict[str, int]] = {}
    values = assumption.get("values", {})
    satisfied = tuple(assumption.get("satisfied_required_facts", ()))
    for rule in rules:
        counts: Counter[str] = Counter()
        for context in contexts:
            evaluation = evaluate_compiled_rule(
                rule,
                context,
                assumption_values=values,
                satisfied_required_facts=satisfied,
            )
            counts[evaluation.state.value] += 1
            state_counts[evaluation.state.value] += 1
        by_rule[rule.rule_id] = dict(sorted(counts.items()))
    return {
        "assumption_set_id": assumption_id,
        "evaluation_count": len(rules) * len(contexts),
        "state_counts": dict(sorted(state_counts.items())),
        "by_rule": by_rule,
    }


def _route_audit(
    rules: tuple[CompiledRule, ...],
    contexts: tuple[ContextV2, ...],
    assumption_sets: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    positives = tuple(
        context
        for context in contexts
        if context.fixture_type is FixtureType.POSITIVE_WITNESS
    )
    route_rules = tuple(
        rule
        for rule in rules
        if rule.compilation_mode is CompilationMode.EXPLICIT_CATALOG_ROUTE
    )
    result: dict[str, Any] = {}
    for rule in route_rules:
        structural_counts: Counter[str] = Counter()
        structural_matches: list[str] = []
        for context in positives:
            trace = evaluate_condition_v2(rule.structural_condition, context.facts)
            structural_counts[trace.value.value] += 1
            if trace.value is TruthValue.TRUE:
                structural_matches.append(context.context_id)
        scenarios: dict[str, Any] = {}
        for assumption_id, assumption in assumption_sets.items():
            counts: Counter[str] = Counter()
            applicable_contexts: list[str] = []
            for context in positives:
                evaluation = evaluate_compiled_rule(
                    rule,
                    context,
                    assumption_values=assumption.get("values", {}),
                    satisfied_required_facts=tuple(
                        assumption.get("satisfied_required_facts", ())
                    ),
                )
                counts[evaluation.state.value] += 1
                if evaluation.state in {
                    ApplicabilityState.APPLICABLE_DETERMINATE,
                    ApplicabilityState.APPLICABLE_UNSPECIFIED_OBLIGOR,
                    ApplicabilityState.APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR,
                }:
                    applicable_contexts.append(context.context_id)
            scenarios[assumption_id] = {
                "state_counts": dict(sorted(counts.items())),
                "applicable_positive_context_ids": applicable_contexts,
            }
        result[rule.rule_id] = {
            "structural_truth_counts": dict(sorted(structural_counts.items())),
            "structural_match_positive_context_ids": structural_matches,
            "scenarios": scenarios,
        }
    return result


def build_candidate_ir_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
    assumptions_path: str | Path,
    catalog_path: str | Path,
) -> dict[str, Any]:
    rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    contexts = build_decision33_context_v2_corpus(catalog_path)
    assumption_sets = load_assumption_sets(assumptions_path)
    mode_counts = Counter(rule.compilation_mode.value for rule in rules)
    duty_count = sum(len(rule.duties) for rule in rules)
    required_facts = sorted({fact for rule in rules for fact in rule.required_facts})
    scenarios = {
        assumption_id: _scenario_summary(
            rules,
            contexts,
            assumption_id=assumption_id,
            assumption=assumption,
        )
        for assumption_id, assumption in assumption_sets.items()
    }
    return {
        "schema_version": "1.0.0",
        "status": "CANDIDATE_EXECUTABLE_IR_COMPLETE_MODEL_RELATIVE",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "candidate_profile_id": "current-candidate-2026-08-02",
        "candidate_hash": content_sha256(load_current_candidate(candidate_path)),
        "context_corpus_id": "corpus:VN:decision33-catalog-context-v2",
        "context_count": len(contexts),
        "compiled_rule_count": len(rules),
        "compiled_duty_count": duty_count,
        "compilation_mode_counts": dict(sorted(mode_counts.items())),
        "required_fact_count": len(required_facts),
        "required_facts": required_facts,
        "rules": [rule.as_mapping() for rule in rules],
        "assumption_scenarios": scenarios,
        "decision33_route_audit": _route_audit(rules, contexts, assumption_sets),
        "limitations": {
            "required_fact_presence_is_not_predicate_truth": True,
            "generic_rule_predicates_compiled": False,
            "explicit_catalog_route_predicates_compiled": True,
            "priority_and_exception_resolution": "NOT_IMPLEMENTED_IN_THIS_SLICE",
            "quantitative_current_law_claims": "PROHIBITED",
            "notice": (
                "This intermediate representation executes declared structural routing, "
                "missing-fact readiness and explicit synthetic assumptions. It does not "
                "invent legal predicate semantics absent from the candidate graph."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        default="policies/current_candidate_graph_2026-08-02.json",
    )
    parser.add_argument(
        "--fact-bindings",
        default=(
            "profiles/current-candidate-2026-08-02/engineering_fact_bindings.json"
        ),
    )
    parser.add_argument(
        "--assumptions",
        default=(
            "profiles/current-candidate-2026-08-02/engineering_assumptions.json"
        ),
    )
    parser.add_argument(
        "--catalog",
        default="catalogs/vn_decision_33_2026.csv",
    )
    args = parser.parse_args()
    report = build_candidate_ir_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
        assumptions_path=args.assumptions,
        catalog_path=args.catalog,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
