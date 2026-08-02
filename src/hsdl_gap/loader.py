from __future__ import annotations

import json
from pathlib import Path

from .model import ActorRelation, Bindingness, Policy, Rule, TypedDuty


def load_policy_bundle(path: str | Path) -> dict[str, Policy]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    policies: dict[str, Policy] = {}
    for policy_data in payload["policies"]:
        rules: list[Rule] = []
        for rule_data in policy_data["rules"]:
            duties = tuple(
                TypedDuty(
                    id=duty["id"],
                    action=duty["action"],
                    object=duty["object"],
                    obligors=frozenset(duty.get("obligors", [])),
                    actor_relation=ActorRelation(duty.get("actor_relation", "single")),
                    recipient=duty.get("recipient"),
                    timing=duty.get("timing"),
                    conflict_class=duty.get("conflict_class"),
                )
                for duty in rule_data.get("consequences", [])
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
                    consequences=duties,
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
