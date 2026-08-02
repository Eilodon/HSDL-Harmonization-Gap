from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .context import iter_legacy_contexts
from .evaluator import evaluate_policy
from .loader import load_policy_bundle
from .model import ActorRelation, Bindingness, Policy, Rule, TypedDuty


HEADER = "@hsdl-core 0.1"
PROFILE_ID = "HSDL_CORE_REFERENCE_0_1"


class HSDLCoreError(ValueError):
    """Raised when an HSDL Core 0.1 document violates the reference grammar."""


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _duty_payload(duty: TypedDuty) -> dict[str, Any]:
    return {
        "id": duty.id,
        "action": duty.action,
        "object": duty.object,
        "obligors": sorted(duty.obligors),
        "actor_relation": duty.actor_relation.value,
        "recipient": duty.recipient,
        "timing": duty.timing,
        "alignment_key": duty.alignment_key,
        "normative_slot": duty.normative_slot,
        "conflict_class": duty.conflict_class,
    }


def serialize_policy_bundle(policies: dict[str, Policy]) -> str:
    """Serialize canonical policies into the line-oriented HSDL Core 0.1 profile."""
    lines = [HEADER]
    for jurisdiction in sorted(policies):
        policy = policies[jurisdiction]
        lines.append(
            "policy "
            + _json(
                {
                    "id": policy.id,
                    "jurisdiction": policy.jurisdiction,
                    "version": policy.version,
                }
            )
        )
        for rule in policy.rules:
            lines.append(
                "rule "
                + _json(
                    {
                        "id": rule.id,
                        "jurisdiction": rule.jurisdiction,
                        "group": rule.group,
                        "instrument": rule.instrument,
                        "provision": rule.provision,
                        "bindingness": rule.bindingness.name,
                        "source_status": rule.source_status,
                        "interpretation_status": rule.interpretation_status,
                    }
                )
            )
            lines.append("when " + _json(rule.condition))
            for duty in rule.consequences:
                lines.append("duty " + _json(_duty_payload(duty)))
            lines.append("endrule")
        lines.append("endpolicy")
    return "\n".join(lines) + "\n"


def _decode_payload(line: str, keyword: str, line_number: int) -> dict[str, Any]:
    prefix = keyword + " "
    if not line.startswith(prefix):
        raise HSDLCoreError(f"line {line_number}: expected {keyword!r}")
    try:
        payload = json.loads(line[len(prefix) :])
    except json.JSONDecodeError as exc:
        raise HSDLCoreError(
            f"line {line_number}: invalid JSON after {keyword}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise HSDLCoreError(f"line {line_number}: {keyword} payload must be an object")
    return payload


def parse_policy_bundle(text: str) -> dict[str, Policy]:
    """Parse the repository's explicit HSDL Core 0.1 reference profile."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != HEADER:
        raise HSDLCoreError(f"document must begin with {HEADER!r}")

    policies: dict[str, Policy] = {}
    current_policy: dict[str, Any] | None = None
    current_rules: list[Rule] = []
    current_rule: dict[str, Any] | None = None
    current_condition: dict[str, Any] | None = None
    current_duties: list[TypedDuty] = []

    for line_number, line in enumerate(lines[1:], start=2):
        if line.startswith("policy "):
            if current_policy is not None or current_rule is not None:
                raise HSDLCoreError(f"line {line_number}: nested policy is not allowed")
            current_policy = _decode_payload(line, "policy", line_number)
            required = {"id", "jurisdiction", "version"}
            if set(current_policy) != required:
                raise HSDLCoreError(
                    f"line {line_number}: policy fields must be {sorted(required)}"
                )
            current_rules = []
            continue

        if line.startswith("rule "):
            if current_policy is None or current_rule is not None:
                raise HSDLCoreError(f"line {line_number}: rule is outside a policy")
            current_rule = _decode_payload(line, "rule", line_number)
            required = {
                "id",
                "jurisdiction",
                "group",
                "instrument",
                "provision",
                "bindingness",
                "source_status",
                "interpretation_status",
            }
            if set(current_rule) != required:
                raise HSDLCoreError(
                    f"line {line_number}: rule fields must be {sorted(required)}"
                )
            if current_rule["jurisdiction"] != current_policy["jurisdiction"]:
                raise HSDLCoreError(
                    f"line {line_number}: rule jurisdiction differs from policy"
                )
            current_condition = None
            current_duties = []
            continue

        if line.startswith("when "):
            if current_rule is None or current_condition is not None:
                raise HSDLCoreError(
                    f"line {line_number}: exactly one when clause is required per rule"
                )
            current_condition = _decode_payload(line, "when", line_number)
            continue

        if line.startswith("duty "):
            if current_rule is None or current_condition is None:
                raise HSDLCoreError(
                    f"line {line_number}: duty must follow a rule's when clause"
                )
            payload = _decode_payload(line, "duty", line_number)
            required = {
                "id",
                "action",
                "object",
                "obligors",
                "actor_relation",
                "recipient",
                "timing",
                "alignment_key",
                "normative_slot",
                "conflict_class",
            }
            if set(payload) != required:
                raise HSDLCoreError(
                    f"line {line_number}: duty fields must be {sorted(required)}"
                )
            obligors = payload["obligors"]
            if not isinstance(obligors, list) or not all(
                isinstance(actor, str) for actor in obligors
            ):
                raise HSDLCoreError(
                    f"line {line_number}: duty obligors must be a string list"
                )
            current_duties.append(
                TypedDuty(
                    id=payload["id"],
                    action=payload["action"],
                    object=payload["object"],
                    obligors=frozenset(obligors),
                    actor_relation=ActorRelation(payload["actor_relation"]),
                    recipient=payload["recipient"],
                    timing=payload["timing"],
                    alignment_key=payload["alignment_key"],
                    normative_slot=payload["normative_slot"],
                    conflict_class=payload["conflict_class"],
                )
            )
            continue

        if line == "endrule":
            if current_rule is None or current_condition is None:
                raise HSDLCoreError(
                    f"line {line_number}: endrule requires a complete rule"
                )
            try:
                bindingness = Bindingness[current_rule["bindingness"]]
            except KeyError as exc:
                raise HSDLCoreError(
                    f"line {line_number}: unknown bindingness {current_rule['bindingness']!r}"
                ) from exc
            current_rules.append(
                Rule(
                    id=current_rule["id"],
                    jurisdiction=current_rule["jurisdiction"],
                    group=current_rule["group"],
                    instrument=current_rule["instrument"],
                    provision=current_rule["provision"],
                    bindingness=bindingness,
                    condition=current_condition,
                    consequences=tuple(current_duties),
                    source_status=current_rule["source_status"],
                    interpretation_status=current_rule["interpretation_status"],
                )
            )
            current_rule = None
            current_condition = None
            current_duties = []
            continue

        if line == "endpolicy":
            if current_policy is None or current_rule is not None:
                raise HSDLCoreError(
                    f"line {line_number}: endpolicy requires a complete policy"
                )
            jurisdiction = current_policy["jurisdiction"]
            if jurisdiction in policies:
                raise HSDLCoreError(
                    f"line {line_number}: duplicate jurisdiction {jurisdiction!r}"
                )
            policy = Policy(
                id=current_policy["id"],
                jurisdiction=jurisdiction,
                version=current_policy["version"],
                rules=tuple(current_rules),
            )
            policies[jurisdiction] = policy
            current_policy = None
            current_rules = []
            continue

        raise HSDLCoreError(f"line {line_number}: unknown statement {line!r}")

    if current_policy is not None or current_rule is not None:
        raise HSDLCoreError("document ended before the current block was closed")
    if not policies:
        raise HSDLCoreError("document contains no policies")
    return policies


def emit_hsdl_core(
    policy_path: str | Path,
    duty_semantics_path: str | Path | None = None,
) -> str:
    policies = load_policy_bundle(policy_path, duty_semantics_path)
    return serialize_policy_bundle(policies)


def _evaluation_payload(evaluation: Any) -> dict[str, Any]:
    return {
        "state": evaluation.state.value,
        "active_rule_ids": list(evaluation.active_rule_ids),
        "bindingness": evaluation.bindingness.name,
        "duties": [_duty_payload(duty) for duty in evaluation.duties],
    }


def build_hsdl_differential_report(
    policy_path: str | Path,
    duty_semantics_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compare canonical JSON evaluation with parsed HSDL Core evaluation."""
    canonical = load_policy_bundle(policy_path, duty_semantics_path)
    document = serialize_policy_bundle(canonical)
    parsed = parse_policy_bundle(document)
    jurisdictions = sorted(canonical)
    groups = sorted(
        {rule.group for policy in canonical.values() for rule in policy.rules}
    )

    mismatch_examples: list[dict[str, Any]] = []
    comparison_count = 0
    context_count = 0
    for context_index, context in enumerate(iter_legacy_contexts()):
        context_count += 1
        for jurisdiction in jurisdictions:
            for group in groups:
                comparison_count += 1
                left = evaluate_policy(canonical[jurisdiction], context, group)
                right = evaluate_policy(parsed[jurisdiction], context, group)
                if left != right and len(mismatch_examples) < 20:
                    mismatch_examples.append(
                        {
                            "context_index": context_index,
                            "context": context.as_mapping(),
                            "jurisdiction": jurisdiction,
                            "group": group,
                            "canonical": _evaluation_payload(left),
                            "hsdl_core": _evaluation_payload(right),
                        }
                    )

    return {
        "schema_version": "1.0.0",
        "profile_id": PROFILE_ID,
        "status": "EQUIVALENT" if not mismatch_examples else "MISMATCH",
        "upstream_engine_compatibility": "NOT_CLAIMED",
        "source_policy_path": str(policy_path),
        "duty_semantics_path": (
            str(duty_semantics_path) if duty_semantics_path is not None else None
        ),
        "document_sha256": hashlib.sha256(document.encode("utf-8")).hexdigest(),
        "document_line_count": len(document.splitlines()),
        "document_byte_size": len(document.encode("utf-8")),
        "jurisdictions": jurisdictions,
        "groups": groups,
        "context_count": context_count,
        "comparison_count": comparison_count,
        "mismatch_count": len(mismatch_examples),
        "mismatch_examples": mismatch_examples,
        "attestation": {
            "canonical_format": "JSON policy bundle plus semantic overlay",
            "executable_format": "repository-defined HSDL Core 0.1 reference profile",
            "comparison_scope": "all legacy contexts, jurisdictions, and groups",
            "notice": (
                "This proves semantic round-trip equivalence for the repository's explicit "
                "reference profile. It does not establish compatibility with an external "
                "HSDL or HolySeed implementation."
            ),
        },
    }
