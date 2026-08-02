from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from .candidate_ir import (
    CompiledDuty,
    CompiledRule,
    CompilationMode,
    evaluate_compiled_rule,
    compile_candidate_profile,
    load_assumption_sets,
)
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import content_sha256


HEADER = "@hsdl-core 0.2"


class CandidateHSDLError(ValueError):
    """Raised when an HSDL Core 0.2 candidate document is malformed."""


def _json_line(keyword: str, payload: Any) -> str:
    return keyword + " " + json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def emit_candidate_hsdl(
    rules: Iterable[CompiledRule],
    *,
    profile_id: str = "current-candidate-2026-08-02",
) -> str:
    materialised = tuple(rules)
    lines = [
        HEADER,
        _json_line(
            "profile",
            {
                "profile_id": profile_id,
                "claim_class": "MODEL_RELATIVE",
                "legal_validation": "NOT_ASSERTED",
                "rule_count": len(materialised),
            },
        ),
    ]
    for rule in materialised:
        lines.extend(
            [
                _json_line(
                    "rule",
                    {
                        "rule_id": rule.rule_id,
                        "jurisdiction": rule.jurisdiction,
                        "source_id": rule.source_id,
                        "provision": rule.provision,
                        "review_status": rule.review_status,
                        "activation_status": rule.activation_status,
                        "compilation_mode": rule.compilation_mode.value,
                        "required_facts": list(rule.required_facts),
                        "predicate_semantics_complete": (
                            rule.predicate_semantics_complete
                        ),
                    },
                ),
                _json_line("factpaths", dict(rule.fact_paths)),
                _json_line("readiness", dict(rule.readiness_condition)),
                _json_line("structural", dict(rule.structural_condition)),
                _json_line(
                    "uncompiled", list(rule.uncompiled_predicate_facts)
                ),
            ]
        )
        lines.extend(_json_line("duty", duty.as_mapping()) for duty in rule.duties)
        lines.append("endrule")
    lines.append("endprofile")
    return "\n".join(lines) + "\n"


def _decode_payload(line: str, keyword: str, line_number: int) -> Any:
    prefix = keyword + " "
    if not line.startswith(prefix):
        raise CandidateHSDLError(f"line {line_number}: expected {keyword}")
    raw = line[len(prefix) :]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CandidateHSDLError(
            f"line {line_number}: invalid JSON after {keyword}: {exc}"
        ) from exc


def _require_object(value: Any, *, line_number: int, keyword: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CandidateHSDLError(
            f"line {line_number}: {keyword} payload must be an object"
        )
    return value


def _require_string(payload: Mapping[str, Any], field: str, line_number: int) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not value:
        raise CandidateHSDLError(
            f"line {line_number}: {field} must be a non-empty string"
        )
    return value


def _require_string_list(
    payload: Mapping[str, Any], field: str, line_number: int
) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise CandidateHSDLError(
            f"line {line_number}: {field} must be a string array"
        )
    return tuple(value)


def _parse_duty(payload: dict[str, Any], line_number: int) -> CompiledDuty:
    actions = payload.get("actions")
    obligors = payload.get("obligors")
    if not isinstance(actions, list) or not all(
        isinstance(item, str) and item for item in actions
    ):
        raise CandidateHSDLError(
            f"line {line_number}: duty actions must be a string array"
        )
    if not isinstance(obligors, list) or not all(
        isinstance(item, str) and item for item in obligors
    ):
        raise CandidateHSDLError(
            f"line {line_number}: duty obligors must be a string array"
        )
    return CompiledDuty(
        duty_id=_require_string(payload, "duty_id", line_number),
        normative_slot=_require_string(payload, "normative_slot", line_number),
        actions=tuple(actions),
        object=_require_string(payload, "object", line_number),
        obligors=tuple(obligors),
        actor_relation=_require_string(payload, "actor_relation", line_number),
        timing=_require_string(payload, "timing", line_number),
    )


def parse_candidate_hsdl(document: str) -> tuple[str, tuple[CompiledRule, ...]]:
    lines = document.splitlines()
    if not lines or lines[0] != HEADER:
        raise CandidateHSDLError(f"document must begin with {HEADER}")
    if len(lines) < 3:
        raise CandidateHSDLError("candidate document is incomplete")

    profile_payload = _require_object(
        _decode_payload(lines[1], "profile", 2),
        line_number=2,
        keyword="profile",
    )
    profile_id = _require_string(profile_payload, "profile_id", 2)
    if profile_payload.get("claim_class") != "MODEL_RELATIVE":
        raise CandidateHSDLError("line 2: profile claim_class must be MODEL_RELATIVE")
    if profile_payload.get("legal_validation") != "NOT_ASSERTED":
        raise CandidateHSDLError("line 2: profile cannot assert legal validation")
    declared_rule_count = profile_payload.get("rule_count")
    if not isinstance(declared_rule_count, int) or declared_rule_count < 0:
        raise CandidateHSDLError("line 2: rule_count must be a non-negative integer")

    index = 2
    rules: list[CompiledRule] = []
    seen_ids: set[str] = set()
    found_endprofile = False
    while index < len(lines):
        line = lines[index]
        line_number = index + 1
        if line == "endprofile":
            found_endprofile = True
            index += 1
            break
        if not line.startswith("rule "):
            raise CandidateHSDLError(
                f"line {line_number}: expected rule or endprofile"
            )
        rule_payload = _require_object(
            _decode_payload(line, "rule", line_number),
            line_number=line_number,
            keyword="rule",
        )
        rule_id = _require_string(rule_payload, "rule_id", line_number)
        if rule_id in seen_ids:
            raise CandidateHSDLError(f"line {line_number}: duplicate rule ID {rule_id}")
        seen_ids.add(rule_id)
        try:
            mode = CompilationMode(
                _require_string(rule_payload, "compilation_mode", line_number)
            )
        except ValueError as exc:
            raise CandidateHSDLError(
                f"line {line_number}: unsupported compilation mode"
            ) from exc
        required_facts = _require_string_list(
            rule_payload, "required_facts", line_number
        )
        complete = rule_payload.get("predicate_semantics_complete")
        if not isinstance(complete, bool):
            raise CandidateHSDLError(
                f"line {line_number}: predicate_semantics_complete must be boolean"
            )

        index += 1
        expected = ("factpaths", "readiness", "structural", "uncompiled")
        parsed_sections: dict[str, Any] = {}
        for keyword in expected:
            if index >= len(lines):
                raise CandidateHSDLError(f"rule {rule_id} is incomplete")
            section_line_number = index + 1
            parsed_sections[keyword] = _decode_payload(
                lines[index], keyword, section_line_number
            )
            index += 1
        factpaths = _require_object(
            parsed_sections["factpaths"],
            line_number=line_number + 1,
            keyword="factpaths",
        )
        if not all(
            isinstance(key, str)
            and key
            and isinstance(value, str)
            and value
            for key, value in factpaths.items()
        ):
            raise CandidateHSDLError(f"rule {rule_id}: invalid factpaths")
        readiness = _require_object(
            parsed_sections["readiness"],
            line_number=line_number + 2,
            keyword="readiness",
        )
        structural = _require_object(
            parsed_sections["structural"],
            line_number=line_number + 3,
            keyword="structural",
        )
        uncompiled_raw = parsed_sections["uncompiled"]
        if not isinstance(uncompiled_raw, list) or not all(
            isinstance(item, str) and item for item in uncompiled_raw
        ):
            raise CandidateHSDLError(f"rule {rule_id}: uncompiled must be a string array")

        duties: list[CompiledDuty] = []
        duty_ids: set[str] = set()
        while index < len(lines) and lines[index].startswith("duty "):
            duty_line_number = index + 1
            duty_payload = _require_object(
                _decode_payload(lines[index], "duty", duty_line_number),
                line_number=duty_line_number,
                keyword="duty",
            )
            duty = _parse_duty(duty_payload, duty_line_number)
            if duty.duty_id in duty_ids:
                raise CandidateHSDLError(
                    f"line {duty_line_number}: duplicate duty ID {duty.duty_id}"
                )
            duty_ids.add(duty.duty_id)
            duties.append(duty)
            index += 1
        if not duties:
            raise CandidateHSDLError(f"rule {rule_id} must contain at least one duty")
        if index >= len(lines) or lines[index] != "endrule":
            raise CandidateHSDLError(f"rule {rule_id} is missing endrule")
        index += 1

        if set(required_facts) != set(factpaths):
            raise CandidateHSDLError(
                f"rule {rule_id}: required_facts and factpaths differ"
            )
        rules.append(
            CompiledRule(
                rule_id=rule_id,
                jurisdiction=_require_string(rule_payload, "jurisdiction", line_number),
                source_id=_require_string(rule_payload, "source_id", line_number),
                provision=_require_string(rule_payload, "provision", line_number),
                review_status=_require_string(
                    rule_payload, "review_status", line_number
                ),
                activation_status=_require_string(
                    rule_payload, "activation_status", line_number
                ),
                compilation_mode=mode,
                required_facts=required_facts,
                fact_paths=dict(factpaths),
                readiness_condition=readiness,
                structural_condition=structural,
                predicate_semantics_complete=complete,
                uncompiled_predicate_facts=tuple(uncompiled_raw),
                duties=tuple(duties),
            )
        )

    if not found_endprofile:
        raise CandidateHSDLError("candidate document is missing endprofile")
    if index != len(lines):
        raise CandidateHSDLError(
            f"line {index + 1}: content is not allowed after endprofile"
        )
    if len(rules) != declared_rule_count:
        raise CandidateHSDLError(
            f"profile declares {declared_rule_count} rules but contains {len(rules)}"
        )
    return profile_id, tuple(rules)


def _evaluation_projection(evaluation: Any) -> dict[str, Any]:
    return {
        "state": evaluation.state.value,
        "missing_facts": list(evaluation.missing_facts),
        "assumptions_used": list(evaluation.assumptions_used),
        "duties": [duty.as_mapping() for duty in evaluation.duties],
        "structural_trace": evaluation.structural_trace.as_dict(),
        "readiness_trace": evaluation.readiness_trace.as_dict(),
    }


def build_candidate_hsdl_differential_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
    assumptions_path: str | Path,
    catalog_path: str | Path,
) -> dict[str, Any]:
    canonical_rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    document = emit_candidate_hsdl(canonical_rules)
    profile_id, parsed_rules = parse_candidate_hsdl(document)
    contexts = build_decision33_context_v2_corpus(catalog_path)
    assumption_sets = load_assumption_sets(assumptions_path)

    structural_round_trip = [rule.as_mapping() for rule in canonical_rules] == [
        rule.as_mapping() for rule in parsed_rules
    ]
    mismatch_count = 0
    mismatch_samples: list[dict[str, Any]] = []
    scenario_counts: Counter[str] = Counter()
    for assumption_id, assumption in assumption_sets.items():
        values = assumption.get("values", {})
        satisfied = tuple(assumption.get("satisfied_required_facts", ()))
        for canonical, parsed in zip(canonical_rules, parsed_rules, strict=True):
            for context in contexts:
                expected = evaluate_compiled_rule(
                    canonical,
                    context,
                    assumption_values=values,
                    satisfied_required_facts=satisfied,
                )
                actual = evaluate_compiled_rule(
                    parsed,
                    context,
                    assumption_values=values,
                    satisfied_required_facts=satisfied,
                )
                scenario_counts[assumption_id] += 1
                expected_projection = _evaluation_projection(expected)
                actual_projection = _evaluation_projection(actual)
                if expected_projection != actual_projection:
                    mismatch_count += 1
                    if len(mismatch_samples) < 20:
                        mismatch_samples.append(
                            {
                                "assumption_set_id": assumption_id,
                                "rule_id": canonical.rule_id,
                                "context_id": context.context_id,
                                "expected": expected_projection,
                                "actual": actual_projection,
                            }
                        )
    comparison_count = sum(scenario_counts.values())
    return {
        "schema_version": "1.0.0",
        "status": (
            "EQUIVALENT" if structural_round_trip and mismatch_count == 0 else "MISMATCH"
        ),
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "profile_id": profile_id,
        "hsdl_profile": "HSDL_CORE_0_2_REPOSITORY_DEFINED",
        "document_hash": content_sha256(document),
        "document_line_count": len(document.splitlines()),
        "document_byte_count": len(document.encode("utf-8")),
        "rule_count": len(canonical_rules),
        "duty_count": sum(len(rule.duties) for rule in canonical_rules),
        "context_count": len(contexts),
        "assumption_set_count": len(assumption_sets),
        "comparison_count": comparison_count,
        "comparisons_by_assumption_set": dict(sorted(scenario_counts.items())),
        "structural_round_trip_equal": structural_round_trip,
        "mismatch_count": mismatch_count,
        "mismatch_samples": mismatch_samples,
        "compatibility_boundary": {
            "upstream_hsdl_compatibility": "NOT_CLAIMED",
            "independent_implementation": False,
            "current_law_validation": "NOT_ASSERTED",
            "notice": (
                "This differential proves lossless repository-defined HSDL Core 0.2 "
                "round-trip and equal execution through the same Python semantics."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit", action="store_true")
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
    rules = compile_candidate_profile(args.candidate, args.fact_bindings)
    if args.emit:
        print(emit_candidate_hsdl(rules), end="")
        return
    report = build_candidate_hsdl_differential_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
        assumptions_path=args.assumptions,
        catalog_path=args.catalog,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if report["status"] != "EQUIVALENT":
        raise SystemExit(12)


if __name__ == "__main__":
    main()
