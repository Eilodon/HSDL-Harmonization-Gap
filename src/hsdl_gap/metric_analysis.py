from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .candidate_ir import (
    ApplicabilityState,
    CompiledRule,
    RuleIREvaluation,
    compile_candidate_profile,
    evaluate_compiled_rule,
    load_assumption_sets,
)
from .context_v2 import ContextV2, FixtureType
from .current_candidate import load_current_candidate
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import content_sha256


class MetricUnknownPolicy(str, Enum):
    COUNT_AS_SEPARATE_CATEGORY = "COUNT_AS_SEPARATE_CATEGORY"
    EXCLUDE_AND_REPORT = "EXCLUDE_AND_REPORT"
    LOWER_UPPER_BOUND = "LOWER_UPPER_BOUND"


class MetricAnalysisError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MetricSpec:
    metric_id: str
    scenario_id: str
    measure_id: str
    population: str
    rule_ids: tuple[str, ...]
    numerator_states: tuple[ApplicabilityState, ...]
    unknown_states: tuple[ApplicabilityState, ...]
    unknown_policy: MetricUnknownPolicy
    numerator_definition: str
    denominator_definition: str
    interpretation: str


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_id: str
    scenario_id: str
    measure_id: str
    population: str
    numerator: int
    denominator: int
    unknown_count: int
    excluded_count: int
    value: float | None
    lower_bound: float | None
    upper_bound: float | None
    numerator_definition: str
    denominator_definition: str
    interpretation: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "scenario_id": self.scenario_id,
            "measure_id": self.measure_id,
            "population": self.population,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "unknown_count": self.unknown_count,
            "excluded_count": self.excluded_count,
            "value": self.value,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "numerator_definition": self.numerator_definition,
            "denominator_definition": self.denominator_definition,
            "interpretation": self.interpretation,
        }


def _load_json_object(path: str | Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetricAnalysisError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise MetricAnalysisError(f"{label} must be a JSON object")
    return payload


def load_metric_registry(path: str | Path) -> tuple[str, tuple[MetricSpec, ...], dict[str, Any]]:
    payload = _load_json_object(path, label="metric registry")
    if payload.get("claim_class") != "MODEL_RELATIVE":
        raise MetricAnalysisError("metric registry must be model-relative")
    if payload.get("legal_validation") != "NOT_ASSERTED":
        raise MetricAnalysisError("metric registry must not assert legal validation")
    registry_id = payload.get("registry_id")
    if not isinstance(registry_id, str) or not registry_id:
        raise MetricAnalysisError("metric registry ID must be non-empty")
    raw_metrics = payload.get("metrics")
    if not isinstance(raw_metrics, list) or not raw_metrics:
        raise MetricAnalysisError("metric registry must contain metrics")

    seen: set[str] = set()
    specs: list[MetricSpec] = []
    for raw in raw_metrics:
        if not isinstance(raw, dict):
            raise MetricAnalysisError("metric definitions must be objects")
        metric_id = raw.get("metric_id")
        if not isinstance(metric_id, str) or not metric_id:
            raise MetricAnalysisError("metric_id must be non-empty")
        if metric_id in seen:
            raise MetricAnalysisError(f"duplicate metric_id: {metric_id}")
        seen.add(metric_id)
        try:
            numerator_states = tuple(
                ApplicabilityState(value) for value in raw.get("numerator_states", [])
            )
            unknown_states = tuple(
                ApplicabilityState(value) for value in raw.get("unknown_states", [])
            )
            unknown_policy = MetricUnknownPolicy(raw["unknown_policy"])
        except (KeyError, ValueError) as exc:
            raise MetricAnalysisError(f"invalid state/policy in {metric_id}") from exc
        if set(numerator_states) & set(unknown_states):
            raise MetricAnalysisError(
                f"{metric_id} numerator and unknown states must be disjoint"
            )
        rule_ids = raw.get("rule_ids", [])
        if not isinstance(rule_ids, list) or not all(
            isinstance(rule_id, str) and rule_id for rule_id in rule_ids
        ):
            raise MetricAnalysisError(f"{metric_id} has invalid rule_ids")
        string_fields = (
            "scenario_id",
            "measure_id",
            "population",
            "numerator_definition",
            "denominator_definition",
            "interpretation",
        )
        for field in string_fields:
            if not isinstance(raw.get(field), str) or not raw[field]:
                raise MetricAnalysisError(f"{metric_id}.{field} must be non-empty")
        specs.append(
            MetricSpec(
                metric_id=metric_id,
                scenario_id=raw["scenario_id"],
                measure_id=raw["measure_id"],
                population=raw["population"],
                rule_ids=tuple(rule_ids),
                numerator_states=numerator_states,
                unknown_states=unknown_states,
                unknown_policy=unknown_policy,
                numerator_definition=raw["numerator_definition"],
                denominator_definition=raw["denominator_definition"],
                interpretation=raw["interpretation"],
            )
        )
    return registry_id, tuple(specs), payload


def _evaluate_scenario(
    rules: tuple[CompiledRule, ...],
    contexts: tuple[ContextV2, ...],
    assumption: Mapping[str, Any],
) -> dict[tuple[str, str], RuleIREvaluation]:
    values = assumption.get("values", {})
    satisfied = tuple(assumption.get("satisfied_required_facts", ()))
    return {
        (rule.rule_id, context.context_id): evaluate_compiled_rule(
            rule,
            context,
            assumption_values=values,
            satisfied_required_facts=satisfied,
        )
        for rule in rules
        for context in contexts
    }


def _select_contexts(
    population: str,
    contexts: tuple[ContextV2, ...],
) -> tuple[ContextV2, ...]:
    if population == "ALL_CANDIDATE_RULE_CONTEXT_EVALUATIONS":
        return contexts
    if population == "POSITIVE_DECISION33_WITNESSES":
        return tuple(
            context
            for context in contexts
            if context.fixture_type is FixtureType.POSITIVE_WITNESS
        )
    raise MetricAnalysisError(f"unsupported metric population: {population}")


def compute_metric(
    spec: MetricSpec,
    *,
    rules: tuple[CompiledRule, ...],
    contexts: tuple[ContextV2, ...],
    evaluations: Mapping[tuple[str, str], RuleIREvaluation],
) -> MetricResult:
    rule_by_id = {rule.rule_id: rule for rule in rules}
    if spec.rule_ids:
        missing = sorted(set(spec.rule_ids) - set(rule_by_id))
        if missing:
            raise MetricAnalysisError(
                f"{spec.metric_id} references unknown rules: {missing}"
            )
        selected_rules = tuple(rule_by_id[rule_id] for rule_id in spec.rule_ids)
    else:
        selected_rules = rules
    selected_contexts = _select_contexts(spec.population, contexts)
    states = [
        evaluations[(rule.rule_id, context.context_id)].state
        for rule in selected_rules
        for context in selected_contexts
    ]
    numerator = sum(state in spec.numerator_states for state in states)
    unknown_count = sum(state in spec.unknown_states for state in states)

    if spec.unknown_policy is MetricUnknownPolicy.EXCLUDE_AND_REPORT:
        denominator = len(states) - unknown_count
        excluded = unknown_count
        value = numerator / denominator if denominator else None
        lower = upper = value
    elif spec.unknown_policy is MetricUnknownPolicy.LOWER_UPPER_BOUND:
        denominator = len(states)
        excluded = 0
        value = None
        lower = numerator / denominator if denominator else None
        upper = (
            (numerator + unknown_count) / denominator if denominator else None
        )
    else:
        denominator = len(states)
        excluded = 0
        value = numerator / denominator if denominator else None
        lower = upper = value

    return MetricResult(
        metric_id=spec.metric_id,
        scenario_id=spec.scenario_id,
        measure_id=spec.measure_id,
        population=spec.population,
        numerator=numerator,
        denominator=denominator,
        unknown_count=unknown_count,
        excluded_count=excluded,
        value=value,
        lower_bound=lower,
        upper_bound=upper,
        numerator_definition=spec.numerator_definition,
        denominator_definition=spec.denominator_definition,
        interpretation=spec.interpretation,
    )


def compare_scenarios(
    baseline_id: str,
    baseline: Mapping[tuple[str, str], RuleIREvaluation],
    alternative_id: str,
    alternative: Mapping[tuple[str, str], RuleIREvaluation],
) -> dict[str, Any]:
    if set(baseline) != set(alternative):
        raise MetricAnalysisError("scenario evaluation universes differ")
    transitions: Counter[str] = Counter()
    changed_keys: list[dict[str, str]] = []
    for key in sorted(baseline):
        before = baseline[key].state
        after = alternative[key].state
        if before is after:
            continue
        transition = f"{before.value}->{after.value}"
        transitions[transition] += 1
        changed_keys.append(
            {
                "rule_id": key[0],
                "context_id": key[1],
                "from": before.value,
                "to": after.value,
            }
        )
    total = len(baseline)
    changed_count = len(changed_keys)
    return {
        "baseline_scenario_id": baseline_id,
        "alternative_scenario_id": alternative_id,
        "evaluation_count": total,
        "changed_evaluation_count": changed_count,
        "changed_evaluation_share": changed_count / total if total else None,
        "classification": (
            "ASSUMPTION_SENSITIVE" if changed_count else "ASSUMPTION_STABLE"
        ),
        "transition_counts": dict(sorted(transitions.items())),
        "changed_evaluations": changed_keys,
    }


def build_metric_analysis_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
    assumptions_path: str | Path,
    catalog_path: str | Path,
    registry_path: str | Path,
) -> dict[str, Any]:
    rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    contexts = build_decision33_context_v2_corpus(catalog_path)
    assumption_sets = load_assumption_sets(assumptions_path)
    registry_id, specs, registry_payload = load_metric_registry(registry_path)

    unknown_scenarios = sorted(
        {spec.scenario_id for spec in specs} - set(assumption_sets)
    )
    if unknown_scenarios:
        raise MetricAnalysisError(
            f"metrics reference unknown assumption scenarios: {unknown_scenarios}"
        )
    evaluations = {
        scenario_id: _evaluate_scenario(rules, contexts, assumption)
        for scenario_id, assumption in assumption_sets.items()
    }
    results = [
        compute_metric(
            spec,
            rules=rules,
            contexts=contexts,
            evaluations=evaluations[spec.scenario_id],
        )
        for spec in specs
    ]
    baseline_id = "NO_ASSUMPTIONS"
    alternative_id = "ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED"
    sensitivity = compare_scenarios(
        baseline_id,
        evaluations[baseline_id],
        alternative_id,
        evaluations[alternative_id],
    )
    corpus_payload = {
        "corpus_id": "corpus:VN:decision33-catalog-context-v2",
        "contexts": [context.as_mapping() for context in contexts],
    }
    return {
        "schema_version": "1.0.0",
        "status": "MODEL_RELATIVE_METRIC_ANALYSIS_COMPLETE",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "registry": {
            "registry_id": registry_id,
            "registry_hash": content_sha256(registry_payload),
        },
        "candidate": {
            "profile_id": "current-candidate-2026-08-02",
            "profile_hash": content_sha256(load_current_candidate(candidate_path)),
        },
        "corpus": {
            "corpus_id": "corpus:VN:decision33-catalog-context-v2",
            "corpus_hash": content_sha256(corpus_payload),
            "context_count": len(contexts),
        },
        "rule_count": len(rules),
        "evaluation_count_per_scenario": len(rules) * len(contexts),
        "metrics": [result.as_mapping() for result in results],
        "sensitivity": sensitivity,
        "claim_boundary": {
            "empirical_prevalence": "NOT_SUPPORTED",
            "independent_legal_conclusion": "NOT_ASSERTED",
            "uniform_model_space_percentage": "NOT_USED",
            "notice": (
                "Each result describes one declared finite population, profile and "
                "assumption scenario. Catalog-row shares and rule-context evaluation "
                "shares are not interchangeable."
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
        default="profiles/current-candidate-2026-08-02/engineering_fact_bindings.json",
    )
    parser.add_argument(
        "--assumptions",
        default="profiles/current-candidate-2026-08-02/engineering_assumptions.json",
    )
    parser.add_argument(
        "--catalog", default="catalogs/vn_decision_33_2026.csv"
    )
    parser.add_argument(
        "--registry", default="metrics/model_relative_registry.json"
    )
    args = parser.parse_args()
    report = build_metric_analysis_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
        assumptions_path=args.assumptions,
        catalog_path=args.catalog,
        registry_path=args.registry,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
