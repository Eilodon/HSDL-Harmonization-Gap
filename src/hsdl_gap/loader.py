from __future__ import annotations

import json
from pathlib import Path

from .model import ActorRelation, Bindingness, Policy, Rule, TypedDuty


def _load_duty_semantics(path: str | Path | None) -> dict[str, dict[str, object]]:
    if path is None:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return dict(payload.get("duties", {}))


def load_policy_bundle(
    path: str | Path,
    duty_semantics_path: str | Path | None = None,
) -> dict[str, Policy]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    semantics = _load_duty_semantics(duty_semantics_path)
    policies: dict[str, Policy] = {}
    for policy_data in payload["policies"]:
        rules: list[Rule] = []
        for rule_data in policy_data["rules"]:
            duties = []
            for duty in rule_data.get("consequences", []):
                overlay = semantics.get(duty["id"], {})
                duties.append(
                    TypedDuty(
                        id=duty["id"],
                        action=duty["action"],
                        object=duty["object"],
                        obligors=frozenset(duty.get("obligors", [])),
                        actor_relation=ActorRelation(duty.get("actor_relation", "single")),
                        recipient=duty.get("recipient"),
                        timing=duty.get("timing"),
                        alignment_key=overlay.get("alignment_key", duty.get("alignment_key")),
                        normative_slot=overlay.get("normative_slot", duty.get("normative_slot")),
                        conflict_class=overlay.get("conflict_class", duty.get("conflict_class")),
                    )
                )
            rules.append(
                Rule(
                    id=rule_data["id"],
                    jurisdiction=policy_data["jurisdiction"],
                    group=rule_data["group"],
                    instrument=rule_data["instrument"],
                    provision=rule_data["provision"],
                    bindingness=Bindingness[rule_data["bindingness"]],
                    condition=rule_data["condition"],
                    consequences=tuple(duties),
                    source_status=rule_data.get("source_status", "legacy_frozen"),
                    interpretation_status=rule_data.get(
                        "interpretation_status", "author_interpreted"
                    ),
                )
            )
        policy = Policy(
            id=policy_data["id"],
            jurisdiction=policy_data["jurisdiction"],
            version=policy_data["version"],
            rules=tuple(rules),
        )
        policies[policy.jurisdiction] = policy
    return policies
