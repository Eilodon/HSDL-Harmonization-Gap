from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DISPOSITION_ACTIONS: dict[str, dict[str, str]] = {
    "CONFIRMED_MINOR_SCOPE_REENCODE": {
        "migration_action": "NARROW_SCOPE_AND_REENCODE",
        "workstream": "RULE_SCOPE_AND_EXCEPTIONS",
    },
    "CONFIRMED_ACTOR_REENCODE": {
        "migration_action": "SPLIT_OR_REASSIGN_TYPED_ACTORS",
        "workstream": "ACTOR_RELATIONS",
    },
    "CONFIRMED_ACTION_REENCODE": {
        "migration_action": "REWRITE_TYPED_ACTION_GRAPH",
        "workstream": "NORMATIVE_CONSEQUENCES",
    },
    "CONFIRMED_TYPED_REENCODE": {
        "migration_action": "EXPAND_TYPED_RULE_GRAPH",
        "workstream": "NORMATIVE_CONSEQUENCES",
    },
    "DUPLICATE_CROSS_GROUP_ENCODING": {
        "migration_action": "REMOVE_DUPLICATE_AND_DERIVE_PROJECTION",
        "workstream": "GROUP_ARCHITECTURE",
    },
    "UNSUPPORTED_BY_CITED_PROVISION": {
        "migration_action": "RETRACT_UNLESS_NEW_SOURCE_IDENTIFIED",
        "workstream": "SOURCE_VALIDITY",
    },
    "POLICY_PRINCIPLE_NOT_ENTITY_RULE": {
        "migration_action": "MOVE_TO_PRINCIPLE_LAYER",
        "workstream": "ASEAN_OBJECT_TYPING",
    },
    "POLICY_RECOMMENDATION_NOT_ENTITY_RULE": {
        "migration_action": "MOVE_TO_RECOMMENDATION_LAYER",
        "workstream": "ASEAN_OBJECT_TYPING",
    },
}

WORKSTREAM_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "SOURCE_VALIDITY": (
        "CHECKSUM_PINNED_SOURCE",
        "PROVISION_LOCATOR",
        "INDEPENDENT_REVIEW",
    ),
    "ACTOR_RELATIONS": (
        "PROVISION_AUDIT",
        "INDEPENDENT_REVIEW",
        "TYPED_DUTY_SCHEMA",
    ),
    "NORMATIVE_CONSEQUENCES": (
        "PROVISION_AUDIT",
        "INDEPENDENT_REVIEW",
        "TYPED_DUTY_SCHEMA",
    ),
    "RULE_SCOPE_AND_EXCEPTIONS": (
        "CURRENT_CLASSIFICATION_SCHEMA",
        "PROVISION_AUDIT",
        "INDEPENDENT_REVIEW",
    ),
    "GROUP_ARCHITECTURE": (
        "TYPED_DUTY_SCHEMA",
        "CONFLICT_CLASS_GATE",
        "MANUSCRIPT_METRIC_REDESIGN",
    ),
    "ASEAN_OBJECT_TYPING": (
        "ASEAN_TYPED_ONTOLOGY",
        "INDEPENDENT_POLICY_REVIEW",
        "CROSS_LAYER_COMPARISON_PROTOCOL",
    ),
}

WORKSTREAM_ACCEPTANCE: dict[str, tuple[str, ...]] = {
    "SOURCE_VALIDITY": (
        "No current rule is unsupported by its cited source.",
        "Every replacement source has a checksum-pinned locator.",
    ),
    "ACTOR_RELATIONS": (
        "Primary, fallback, coordinated and recipient roles are represented separately.",
        "No actor set is inferred by flattening unrelated duties.",
    ),
    "NORMATIVE_CONSEQUENCES": (
        "Every rule emits typed action, object, actor relation, timing and source.",
        "Distinct duties accumulate unless an explicit same-slot conflict exists.",
    ),
    "RULE_SCOPE_AND_EXCEPTIONS": (
        "Predicates implement current classification and procedure conditions.",
        "Exceptions, timing and category-specific branches are explicit.",
    ),
    "GROUP_ARCHITECTURE": (
        "No source norm is double-counted as an independent obligation group.",
        "Temporal projections are derived views rather than duplicate duties.",
    ),
    "ASEAN_OBJECT_TYPING": (
        "Principles, governance practices, risks and recommendations remain separate layers.",
        "No voluntary policy object is silently promoted into a statutory entity rule.",
    ),
}


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("migration-plan input must be a JSON object")
    return payload


def build_migration_plan(audit_path: str | Path) -> dict[str, Any]:
    audit = _load(audit_path)
    rows = audit.get("rules")
    if not isinstance(rows, list) or not rows:
        raise ValueError("provision audit must contain rule rows")

    items: list[dict[str, Any]] = []
    disposition_counts: Counter[str] = Counter()
    workstream_counts: Counter[str] = Counter()
    workstream_rule_ids: defaultdict[str, list[str]] = defaultdict(list)
    blocker_ids: list[str] = []

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("every provision-audit row must be an object")
        rule_id = row.get("rule_id")
        disposition = row.get("disposition")
        if not isinstance(rule_id, str) or not rule_id:
            raise ValueError("every provision-audit row needs a rule_id")
        if disposition not in DISPOSITION_ACTIONS:
            raise ValueError(f"unsupported audit disposition: {disposition!r}")
        mapping = DISPOSITION_ACTIONS[disposition]
        workstream = mapping["workstream"]
        is_blocker = row.get("publication_blocker") is True
        if is_blocker:
            blocker_ids.append(rule_id)
        disposition_counts[disposition] += 1
        workstream_counts[workstream] += 1
        workstream_rule_ids[workstream].append(rule_id)
        items.append(
            {
                "legacy_rule_id": rule_id,
                "source_id": row.get("source_id"),
                "source_locator": row.get("locator"),
                "audit_disposition": disposition,
                "migration_action": mapping["migration_action"],
                "workstream": workstream,
                "publication_blocker": is_blocker,
                "required_change": row.get("required_change"),
                "dependencies": list(WORKSTREAM_DEPENDENCIES[workstream]),
                "target_status": "NOT_STARTED",
                "replacement_rule_ids": [],
                "implementation_evidence": [],
                "independent_review_decision": None,
            }
        )

    workstreams: list[dict[str, Any]] = []
    ordered_workstreams = (
        "SOURCE_VALIDITY",
        "ASEAN_OBJECT_TYPING",
        "GROUP_ARCHITECTURE",
        "RULE_SCOPE_AND_EXCEPTIONS",
        "ACTOR_RELATIONS",
        "NORMATIVE_CONSEQUENCES",
    )
    for sequence, workstream in enumerate(ordered_workstreams, start=1):
        rule_ids = sorted(workstream_rule_ids.get(workstream, []))
        workstreams.append(
            {
                "sequence": sequence,
                "id": workstream,
                "rule_count": len(rule_ids),
                "rule_ids": rule_ids,
                "dependencies": list(WORKSTREAM_DEPENDENCIES[workstream]),
                "acceptance_criteria": list(WORKSTREAM_ACCEPTANCE[workstream]),
                "status": "NOT_STARTED",
            }
        )

    return {
        "schema_version": "1.0.0",
        "plan_id": "current-profile-migration-plan-2026-08-02",
        "source_audit_id": audit.get("audit_id"),
        "status": "READY_FOR_REVIEWED_REENCODING",
        "legacy_rule_count": len(items),
        "publication_blocker_count": len(blocker_ids),
        "publication_blocker_rule_ids": sorted(blocker_ids),
        "counts": {
            "by_disposition": dict(sorted(disposition_counts.items())),
            "by_workstream": dict(sorted(workstream_counts.items())),
        },
        "workstreams": workstreams,
        "rule_migrations": sorted(items, key=lambda item: item["legacy_rule_id"]),
        "new_current_profile_components": [
            {
                "id": "VN_DECISION33_CLASSIFICATION_RELATION",
                "status": "POSITIVE_WITNESS_PROFILE_EXISTS_NEGATIVE_CASES_PENDING",
                "dependencies": [
                    "INDEPENDENT_REVIEW",
                    "SHARED_EU_VN_CLASSIFICATION_SCHEMA",
                ],
            },
            {
                "id": "VN_ARTICLE13_ROUTE_GRAPH",
                "status": "ROUTE_TABLE_VISUALLY_VERIFIED_RULE_GRAPH_PENDING",
                "dependencies": ["INDEPENDENT_REVIEW"],
            },
            {
                "id": "VN_DECREE142_ARTICLE19_DUTY_GRAPH",
                "status": "PROVISION_AUDITED_TYPED_RULE_GRAPH_PENDING",
                "dependencies": ["INDEPENDENT_REVIEW"],
            },
            {
                "id": "EU_CURRENT_HIGH_RISK_RELATION",
                "status": "PENDING_CURRENT_SCOPE_ENCODING",
                "dependencies": ["SHARED_EU_VN_CLASSIFICATION_SCHEMA"],
            },
            {
                "id": "ASEAN_PRINCIPLE_AND_RECOMMENDATION_LAYERS",
                "status": "ONTOLOGY_EXISTS_EXECUTABLE_POLICY_LAYER_PENDING",
                "dependencies": ["INDEPENDENT_POLICY_REVIEW"],
            },
        ],
        "promotion_gate": {
            "implementation_may_begin_before_review": True,
            "review_dependent_choices_must_remain_provisional": True,
            "current_quantitative_results": "BLOCKED",
            "manuscript_regeneration": "BLOCKED",
            "release_candidate": "BLOCKED",
        },
        "completion_contract": {
            "all_rule_migrations_have_replacement_or_retraction": True,
            "all_publication_blockers_closed": True,
            "independent_review_applied": True,
            "current_profile_tests_pass": True,
            "hsdl_differential_passes": True,
            "typed_cover_audit_regenerated": True,
            "legacy_to_current_change_log_generated": True,
        },
        "notice": (
            "This plan authorises implementation scaffolding and provisional re-encoding. "
            "It does not authorise current-law numerical or manuscript claims before "
            "independent review and all completion gates pass."
        ),
    }
