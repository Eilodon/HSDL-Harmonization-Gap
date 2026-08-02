from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .conditions_v2 import ConditionTrace, evaluate_condition_v2
from .current_candidate import load_current_candidate, validate_current_candidate
from .stable_id import content_sha256
from .tristate import TruthValue


class PredicateProfileError(ValueError):
    """Raised when the source-derived predicate profile violates its contract."""


class PredicateState(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ExecutableDutyV2:
    duty_id: str
    normative_slot: str
    actions: tuple[str, ...]
    object: str
    obligors: tuple[str, ...]
    actor_relation: str
    timing: str
    modality: str
    recipients: tuple[str, ...]
    trigger_condition: Mapping[str, Any] | None
    trigger_signature: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "duty_id": self.duty_id,
            "normative_slot": self.normative_slot,
            "actions": list(self.actions),
            "object": self.object,
            "obligors": list(self.obligors),
            "actor_relation": self.actor_relation,
            "timing": self.timing,
            "modality": self.modality,
            "recipients": list(self.recipients),
            "trigger_condition": (
                dict(self.trigger_condition)
                if self.trigger_condition is not None
                else None
            ),
            "trigger_signature": self.trigger_signature,
        }


@dataclass(frozen=True, slots=True)
class ExecutableRuleV2:
    rule_id: str
    jurisdiction: str
    source_id: str
    provision: str
    review_status: str
    source_evidence: Mapping[str, Any]
    predicate: Mapping[str, Any]
    duties: tuple[ExecutableDutyV2, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "jurisdiction": self.jurisdiction,
            "source_id": self.source_id,
            "provision": self.provision,
            "review_status": self.review_status,
            "source_evidence": dict(self.source_evidence),
            "predicate": dict(self.predicate),
            "predicate_semantics_complete": True,
            "duties": [duty.as_mapping() for duty in self.duties],
        }


@dataclass(frozen=True, slots=True)
class DutyPredicateEvaluation:
    duty_id: str
    normative_slot: str
    state: PredicateState
    trace: ConditionTrace
    missing_facts: tuple[str, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "duty_id": self.duty_id,
            "normative_slot": self.normative_slot,
            "state": self.state.value,
            "trace": self.trace.as_dict(),
            "missing_facts": list(self.missing_facts),
        }


@dataclass(frozen=True, slots=True)
class RulePredicateEvaluation:
    rule_id: str
    state: PredicateState
    trace: ConditionTrace
    missing_facts: tuple[str, ...]
    duties: tuple[DutyPredicateEvaluation, ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "state": self.state.value,
            "trace": self.trace.as_dict(),
            "missing_facts": list(self.missing_facts),
            "duties": [duty.as_mapping() for duty in self.duties],
        }


def _load_json_object(path: str | Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PredicateProfileError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PredicateProfileError(f"{label} must be a JSON object")
    return payload


def _require_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PredicateProfileError(f"{label} must be a non-empty string")
    return value


def _require_condition(value: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PredicateProfileError(f"{label} must be a condition object")
    try:
        evaluate_condition_v2(value, {})
    except ValueError as exc:
        raise PredicateProfileError(f"invalid {label}: {exc}") from exc
    return value


def _state_from_truth(value: TruthValue) -> PredicateState:
    if value is TruthValue.TRUE:
        return PredicateState.APPLICABLE
    if value is TruthValue.FALSE:
        return PredicateState.NOT_APPLICABLE
    return PredicateState.UNKNOWN


def compile_source_derived_profile(
    candidate_path: str | Path,
    predicate_profile_path: str | Path,
) -> tuple[ExecutableRuleV2, ...]:
    candidate_errors = validate_current_candidate(candidate_path)
    if candidate_errors:
        raise PredicateProfileError(
            "candidate safety validation failed: " + "; ".join(candidate_errors)
        )
    candidate = load_current_candidate(candidate_path)
    profile = _load_json_object(predicate_profile_path, label="predicate profile")
    if profile.get("candidate_profile_id") != candidate.get("profile_id"):
        raise PredicateProfileError("predicate profile targets a different candidate")
    if profile.get("legal_validation") != "NOT_ASSERTED":
        raise PredicateProfileError("predicate profile must not assert legal validation")
    if profile.get("claim_class") != "MODEL_RELATIVE":
        raise PredicateProfileError("predicate profile must be model-relative")

    candidate_rules = {
        rule["id"]: rule for rule in candidate.get("binding_rule_graph", [])
    }
    raw_rules = profile.get("rules")
    if not isinstance(raw_rules, list):
        raise PredicateProfileError("predicate profile must contain a rules array")
    profile_rules: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw_rules):
        if not isinstance(item, dict):
            raise PredicateProfileError(f"rules[{index}] must be an object")
        rule_id = _require_string(item.get("rule_id"), label=f"rules[{index}].rule_id")
        if rule_id in profile_rules:
            raise PredicateProfileError(f"duplicate predicate rule: {rule_id}")
        profile_rules[rule_id] = item

    missing = sorted(set(candidate_rules) - set(profile_rules))
    extra = sorted(set(profile_rules) - set(candidate_rules))
    if missing or extra:
        raise PredicateProfileError(
            f"predicate coverage mismatch; missing={missing}, extra={extra}"
        )

    compiled: list[ExecutableRuleV2] = []
    seen_duty_ids: set[str] = set()
    for rule_id, candidate_rule in candidate_rules.items():
        spec = profile_rules[rule_id]
        predicate = _require_condition(
            spec.get("predicate"), label=f"{rule_id}.predicate"
        )
        evidence = spec.get("source_evidence")
        if not isinstance(evidence, dict):
            raise PredicateProfileError(f"{rule_id}.source_evidence must be an object")
        if evidence.get("source_id") not in {
            candidate_rule["source_id"],
            "VN_LAW_134_2025_AND_DECISION_33_2026",
        }:
            raise PredicateProfileError(f"{rule_id} source evidence does not match rule")
        raw_duties = spec.get("duties")
        if not isinstance(raw_duties, dict):
            raise PredicateProfileError(f"{rule_id}.duties must be an object")
        candidate_slots = {
            consequence["normative_slot"]: consequence
            for consequence in candidate_rule["consequences"]
        }
        if set(raw_duties) != set(candidate_slots):
            raise PredicateProfileError(
                f"{rule_id} duty coverage differs from candidate consequences"
            )
        duties: list[ExecutableDutyV2] = []
        for slot, consequence in candidate_slots.items():
            semantics = raw_duties[slot]
            if not isinstance(semantics, dict):
                raise PredicateProfileError(f"{rule_id}.{slot} semantics must be an object")
            modality = _require_string(
                semantics.get("modality"), label=f"{rule_id}.{slot}.modality"
            )
            recipients = semantics.get("recipients")
            if not isinstance(recipients, list) or not all(
                isinstance(item, str) and item for item in recipients
            ):
                raise PredicateProfileError(
                    f"{rule_id}.{slot}.recipients must be a string array"
                )
            trigger_raw = semantics.get("trigger")
            trigger = (
                None
                if trigger_raw is None
                else _require_condition(
                    trigger_raw, label=f"{rule_id}.{slot}.trigger"
                )
            )
            trigger_signature = _require_string(
                semantics.get("trigger_signature"),
                label=f"{rule_id}.{slot}.trigger_signature",
            )
            duty_id = f"{rule_id}:{slot}"
            if duty_id in seen_duty_ids:
                raise PredicateProfileError(f"duplicate duty ID: {duty_id}")
            seen_duty_ids.add(duty_id)
            duties.append(
                ExecutableDutyV2(
                    duty_id=duty_id,
                    normative_slot=slot,
                    actions=tuple(consequence["actions"]),
                    object=consequence["object"],
                    obligors=tuple(consequence["obligors"]),
                    actor_relation=consequence["actor_relation"],
                    timing=consequence["timing"],
                    modality=modality,
                    recipients=tuple(recipients),
                    trigger_condition=trigger,
                    trigger_signature=trigger_signature,
                )
            )
        compiled.append(
            ExecutableRuleV2(
                rule_id=rule_id,
                jurisdiction=candidate_rule["jurisdiction"],
                source_id=candidate_rule["source_id"],
                provision=candidate_rule["provision"],
                review_status=candidate_rule["review_status"],
                source_evidence=evidence,
                predicate=predicate,
                duties=tuple(duties),
            )
        )
    return tuple(compiled)


def evaluate_executable_rule(
    rule: ExecutableRuleV2,
    facts: Mapping[str, Any],
) -> RulePredicateEvaluation:
    rule_trace = evaluate_condition_v2(rule.predicate, facts)
    rule_state = _state_from_truth(rule_trace.value)
    duty_results: list[DutyPredicateEvaluation] = []
    for duty in rule.duties:
        if rule_state is PredicateState.NOT_APPLICABLE:
            trace = rule_trace
            duty_state = PredicateState.NOT_APPLICABLE
        elif rule_state is PredicateState.UNKNOWN:
            trace = rule_trace
            duty_state = PredicateState.UNKNOWN
        elif duty.trigger_condition is None:
            trace = rule_trace
            duty_state = PredicateState.APPLICABLE
        else:
            trace = evaluate_condition_v2(duty.trigger_condition, facts)
            duty_state = _state_from_truth(trace.value)
        duty_results.append(
            DutyPredicateEvaluation(
                duty_id=duty.duty_id,
                normative_slot=duty.normative_slot,
                state=duty_state,
                trace=trace,
                missing_facts=tuple(sorted(set(trace.missing_facts))),
            )
        )
    return RulePredicateEvaluation(
        rule_id=rule.rule_id,
        state=rule_state,
        trace=rule_trace,
        missing_facts=tuple(sorted(set(rule_trace.missing_facts))),
        duties=tuple(duty_results),
    )


def build_source_derived_predicate_report(
    candidate_path: str | Path = "policies/current_candidate_graph_2026-08-02.json",
    predicate_profile_path: str | Path = (
        "profiles/current-candidate-2026-08-02/source_derived_predicates.json"
    ),
) -> dict[str, Any]:
    rules = compile_source_derived_profile(candidate_path, predicate_profile_path)
    duties = tuple(duty for rule in rules for duty in rule.duties)
    modality_counts = Counter(duty.modality for duty in duties)
    jurisdiction_counts = Counter(rule.jurisdiction for rule in rules)
    source_counts = Counter(rule.source_id for rule in rules)
    return {
        "schema_version": "1.0.0",
        "status": "ALL_CANDIDATE_PREDICATES_EXECUTABLE_PENDING_REVIEW",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "candidate_rule_count": len(rules),
        "executable_predicate_count": len(rules),
        "readiness_only_predicate_count": 0,
        "duty_count": len(duties),
        "duties_with_modality_count": sum(bool(duty.modality) for duty in duties),
        "duties_with_trigger_signature_count": sum(
            bool(duty.trigger_signature) for duty in duties
        ),
        "duties_with_recipient_field_count": len(duties),
        "modality_counts": dict(sorted(modality_counts.items())),
        "jurisdiction_rule_counts": dict(sorted(jurisdiction_counts.items())),
        "source_rule_counts": dict(sorted(source_counts.items())),
        "profile_hash": content_sha256([rule.as_mapping() for rule in rules]),
        "rules": [rule.as_mapping() for rule in rules],
        "review_boundary": {
            "source_text_checked": True,
            "independent_legal_review": "PENDING",
            "quantitative_current_law_claims_allowed": False,
            "notice": (
                "Executable source-derived predicates remove the engineering "
                "readiness-only state. They do not close independent legal review."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate", default="policies/current_candidate_graph_2026-08-02.json"
    )
    parser.add_argument(
        "--predicate-profile",
        default=(
            "profiles/current-candidate-2026-08-02/"
            "source_derived_predicates.json"
        ),
    )
    args = parser.parse_args()
    report = build_source_derived_predicate_report(
        args.candidate, args.predicate_profile
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
