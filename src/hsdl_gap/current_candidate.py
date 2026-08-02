from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


EXPECTED_STATUS = "PROVISIONAL_REVIEW_DEPENDENT_NO_QUANTITATIVE_EVALUATION"
EXPECTED_REMOVED_LEGACY_RULES = {
    "EU_G6_ART9",
    "VN_G2_ART13_REUSE",
    "VN_G6_ND142_EVENT",
}
EXPECTED_ASEAN_FORMER_RULES = {
    "ASEAN_G1_ACCOUNTABILITY",
    "ASEAN_G3_HUMAN_CENTRICITY",
    "ASEAN_G4_GENAI_LABEL",
    "ASEAN_G5_TRANSPARENCY",
}
EXPECTED_POINT_A_IDS = {
    "VN_D33_ERA_04",
    "VN_D33_ERA_05",
    "VN_D33_ERA_06",
    "VN_D33_ERA_07",
    "VN_D33_HLT_02",
    "VN_D33_PRC_01",
}
REQUIRED_ART19_SLOTS = {
    "serious_incident_record_and_initial_mitigation",
    "provider_serious_incident_technical_remediation",
    "serious_incident_information_and_response_coordination",
    "serious_incident_preliminary_report",
    "serious_incident_preliminary_report_fallback",
}
ALLOWED_POLICY_OBJECT_TYPES = {
    "VOLUNTARY_GUIDING_PRINCIPLE",
    "POLICY_RECOMMENDATION_DIMENSION",
}
FORBIDDEN_LEGACY_RULE_IDS_IN_BINDING_GRAPH = (
    EXPECTED_REMOVED_LEGACY_RULES | EXPECTED_ASEAN_FORMER_RULES
)


class CurrentCandidateError(ValueError):
    """Raised when the provisional current rule graph violates its safety contract."""


def load_current_candidate(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CurrentCandidateError("current candidate must be a JSON object")
    return payload


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _contains_forbidden_unacceptable(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() == "unacceptable"
    if isinstance(value, dict):
        return any(
            _contains_forbidden_unacceptable(key)
            or _contains_forbidden_unacceptable(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_unacceptable(item) for item in value)
    return False


def _validate_consequence(
    consequence: Any,
    *,
    prefix: str,
    errors: list[str],
) -> str | None:
    if not isinstance(consequence, dict):
        errors.append(f"{prefix} must be an object")
        return None
    required = {
        "normative_slot",
        "actions",
        "object",
        "obligors",
        "actor_relation",
        "timing",
    }
    missing = sorted(required - consequence.keys())
    if missing:
        errors.append(f"{prefix} missing fields: {missing}")
    slot = consequence.get("normative_slot")
    if not _nonempty_string(slot):
        errors.append(f"{prefix}.normative_slot must be non-empty")
        slot = None
    actions = consequence.get("actions")
    if not isinstance(actions, list) or not actions or not all(
        _nonempty_string(action) for action in actions
    ):
        errors.append(f"{prefix}.actions must be a non-empty string list")
    if not _nonempty_string(consequence.get("object")):
        errors.append(f"{prefix}.object must be non-empty")
    obligors = consequence.get("obligors")
    if not isinstance(obligors, list) or not all(
        _nonempty_string(actor) for actor in obligors
    ):
        errors.append(f"{prefix}.obligors must be a string list")
    if not _nonempty_string(consequence.get("actor_relation")):
        errors.append(f"{prefix}.actor_relation must be non-empty")
    if not _nonempty_string(consequence.get("timing")):
        errors.append(f"{prefix}.timing must be non-empty")
    return slot


def _iter_rule_slots(rules: Iterable[dict[str, Any]]) -> Iterable[tuple[str, str]]:
    for rule in rules:
        rule_id = rule.get("id", "<unknown>")
        for consequence in rule.get("consequences", []):
            if isinstance(consequence, dict) and _nonempty_string(
                consequence.get("normative_slot")
            ):
                yield rule_id, consequence["normative_slot"]


def validate_current_candidate(
    candidate_path: str | Path,
    *,
    decision33_visual_path: str | Path = "sources/reviews/vn_decision_33_2026.visual.json",
) -> list[str]:
    payload = load_current_candidate(candidate_path)
    errors: list[str] = []

    if payload.get("schema_version") != "1.0.0":
        errors.append("unsupported current-candidate schema_version")
    if payload.get("status") != EXPECTED_STATUS:
        errors.append("current-candidate status does not preserve the provisional gate")
    if not _nonempty_string(payload.get("profile_id")):
        errors.append("profile_id must be non-empty")
    if not _nonempty_string(payload.get("source_lock_id")):
        errors.append("source_lock_id must be non-empty")
    if not _nonempty_string(payload.get("provision_audit_id")):
        errors.append("provision_audit_id must be non-empty")

    evaluation = payload.get("evaluation_policy")
    if not isinstance(evaluation, dict):
        errors.append("evaluation_policy must be an object")
    else:
        for field in (
            "quantitative_evaluation_allowed",
            "directional_gap_metrics_allowed",
            "actor_mismatch_metrics_allowed",
        ):
            if evaluation.get(field) is not False:
                errors.append(f"evaluation_policy.{field} must remain false")
        if evaluation.get("typed_rule_graph_validation_allowed") is not True:
            errors.append(
                "evaluation_policy.typed_rule_graph_validation_allowed must be true"
            )
        if not _nonempty_string(evaluation.get("reason")):
            errors.append("evaluation_policy.reason must be non-empty")

    removed = payload.get("removed_legacy_rules")
    removed_ids: list[str] = []
    if not isinstance(removed, list):
        errors.append("removed_legacy_rules must be a list")
    else:
        for index, item in enumerate(removed):
            prefix = f"removed_legacy_rules[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{prefix} must be an object")
                continue
            rule_id = item.get("legacy_rule_id")
            if not _nonempty_string(rule_id):
                errors.append(f"{prefix}.legacy_rule_id must be non-empty")
            else:
                removed_ids.append(rule_id)
            if not _nonempty_string(item.get("disposition")):
                errors.append(f"{prefix}.disposition must be non-empty")
            if not _nonempty_string(item.get("reason")):
                errors.append(f"{prefix}.reason must be non-empty")
        if set(removed_ids) != EXPECTED_REMOVED_LEGACY_RULES:
            errors.append(
                "removed legacy rule set must contain exactly the duplicate and unsupported rules"
            )
        if len(removed_ids) != len(set(removed_ids)):
            errors.append("removed_legacy_rules contains duplicate IDs")

    rules = payload.get("binding_rule_graph")
    binding_rule_ids: list[str] = []
    all_slots: list[str] = []
    if not isinstance(rules, list) or not rules:
        errors.append("binding_rule_graph must be a non-empty list")
        rules = []
    for index, rule in enumerate(rules):
        prefix = f"binding_rule_graph[{index}]"
        if not isinstance(rule, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rule_id = rule.get("id")
        if not _nonempty_string(rule_id):
            errors.append(f"{prefix}.id must be non-empty")
            rule_id = f"<invalid-{index}>"
        binding_rule_ids.append(rule_id)
        if rule_id in FORBIDDEN_LEGACY_RULE_IDS_IN_BINDING_GRAPH:
            errors.append(f"{prefix} silently reintroduces removed legacy rule {rule_id}")
        if rule.get("jurisdiction") not in {"EU", "VN"}:
            errors.append(f"{prefix}.jurisdiction must be EU or VN")
        for field in ("source_id", "provision", "review_status"):
            if not _nonempty_string(rule.get(field)):
                errors.append(f"{prefix}.{field} must be non-empty")
        if rule.get("review_status") != "PENDING_INDEPENDENT_REVIEW":
            errors.append(f"{prefix} must remain pending independent review")
        activation = rule.get("activation_model")
        if not isinstance(activation, dict):
            errors.append(f"{prefix}.activation_model must be an object")
        else:
            if not _nonempty_string(activation.get("status")):
                errors.append(f"{prefix}.activation_model.status must be non-empty")
            required_facts = activation.get("required_facts")
            if not isinstance(required_facts, list) or not all(
                _nonempty_string(fact) for fact in required_facts
            ):
                errors.append(
                    f"{prefix}.activation_model.required_facts must be a string list"
                )
            if _contains_forbidden_unacceptable(activation):
                errors.append(
                    f"{prefix}.activation_model reintroduces the forbidden Unacceptable-tier shortcut"
                )
        consequences = rule.get("consequences")
        if not isinstance(consequences, list) or not consequences:
            errors.append(f"{prefix}.consequences must be a non-empty list")
        else:
            for consequence_index, consequence in enumerate(consequences):
                slot = _validate_consequence(
                    consequence,
                    prefix=f"{prefix}.consequences[{consequence_index}]",
                    errors=errors,
                )
                if slot:
                    all_slots.append(slot)

    duplicate_rule_ids = sorted(
        rule_id
        for rule_id, count in Counter(binding_rule_ids).items()
        if count > 1
    )
    if duplicate_rule_ids:
        errors.append(f"duplicate binding rule IDs: {duplicate_rule_ids}")
    duplicate_slots = sorted(
        slot for slot, count in Counter(all_slots).items() if count > 1
    )
    if duplicate_slots:
        errors.append(
            f"duplicate normative slots require explicit conflict-class semantics: {duplicate_slots}"
        )

    rule_by_id = {
        rule.get("id"): rule
        for rule in rules
        if isinstance(rule, dict) and _nonempty_string(rule.get("id"))
    }
    point_a = rule_by_id.get("VN_ART13_2A_THIRD_PARTY_CERTIFICATION_ROUTE")
    point_b = rule_by_id.get("VN_ART13_2B_PROVIDER_OPTION_ROUTE")
    if point_a is None or point_b is None:
        errors.append("both typed Article 13 point-a and point-b routes are required")
    else:
        visual = json.loads(Path(decision33_visual_path).read_text(encoding="utf-8"))
        visual_ids = set(visual.get("findings", {}).get("route_a_ids", []))
        candidate_a_ids = set(
            point_a.get("activation_model", {}).get("catalog_item_ids", [])
        )
        if candidate_a_ids != EXPECTED_POINT_A_IDS or candidate_a_ids != visual_ids:
            errors.append(
                "point-a catalog IDs must match the checksum-verified Decision 33 visual review"
            )
        if point_b.get("activation_model", {}).get("catalog_item_count") != 40:
            errors.append("point-b route must retain the visually verified count of 40")
        if point_a.get("activation_model", {}).get("catalog_route") != (
            "ARTICLE_13_2_A_THIRD_PARTY_CERTIFICATION"
        ):
            errors.append("point-a route identifier is invalid")
        if point_b.get("activation_model", {}).get("catalog_route") != (
            "ARTICLE_13_2_B_PROVIDER_SELF_OR_THIRD_PARTY"
        ):
            errors.append("point-b route identifier is invalid")

    art19_slots = {
        slot
        for rule_id, slot in _iter_rule_slots(rules)
        if rule_id.startswith("VN_ND142_ART19_")
    }
    missing_art19 = sorted(REQUIRED_ART19_SLOTS - art19_slots)
    if missing_art19:
        errors.append(f"Article 19 typed duty graph is missing slots: {missing_art19}")

    policy_objects = payload.get("non_binding_policy_objects")
    object_ids: list[str] = []
    former_ids: list[str] = []
    if not isinstance(policy_objects, list):
        errors.append("non_binding_policy_objects must be a list")
        policy_objects = []
    for index, item in enumerate(policy_objects):
        prefix = f"non_binding_policy_objects[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        object_id = item.get("id")
        former_id = item.get("former_legacy_rule_id")
        if not _nonempty_string(object_id):
            errors.append(f"{prefix}.id must be non-empty")
        else:
            object_ids.append(object_id)
        if not _nonempty_string(former_id):
            errors.append(f"{prefix}.former_legacy_rule_id must be non-empty")
        else:
            former_ids.append(former_id)
        if not _nonempty_string(item.get("source_id")):
            errors.append(f"{prefix}.source_id must be non-empty")
        if not _nonempty_string(item.get("section")):
            errors.append(f"{prefix}.section must be non-empty")
        if item.get("object_type") not in ALLOWED_POLICY_OBJECT_TYPES:
            errors.append(f"{prefix}.object_type is not a non-binding policy layer")
    if len(object_ids) != len(set(object_ids)):
        errors.append("non_binding_policy_objects contains duplicate IDs")
    if set(former_ids) != EXPECTED_ASEAN_FORMER_RULES:
        errors.append("all four frozen ASEAN rules must move to non-binding layers")

    gates = payload.get("research_gates")
    if not isinstance(gates, dict):
        errors.append("research_gates must be an object")
    else:
        for field in (
            "independent_review",
            "shared_current_context",
            "negative_and_boundary_cases",
            "current_hsdl_profile",
            "current_typed_cover",
        ):
            if gates.get(field) != "PENDING":
                errors.append(f"research_gates.{field} must remain PENDING")
        for field in ("current_quantitative_results", "manuscript_regeneration"):
            if gates.get(field) != "BLOCKED":
                errors.append(f"research_gates.{field} must remain BLOCKED")
    if not _nonempty_string(payload.get("notice")):
        errors.append("notice must be non-empty")
    return errors


def build_current_candidate_report(
    candidate_path: str | Path,
    *,
    decision33_visual_path: str | Path = "sources/reviews/vn_decision_33_2026.visual.json",
) -> dict[str, Any]:
    payload = load_current_candidate(candidate_path)
    errors = validate_current_candidate(
        candidate_path,
        decision33_visual_path=decision33_visual_path,
    )
    rules = payload.get("binding_rule_graph", [])
    policy_objects = payload.get("non_binding_policy_objects", [])
    slots = [slot for _, slot in _iter_rule_slots(rules if isinstance(rules, list) else [])]
    jurisdiction_counts = Counter(
        rule.get("jurisdiction")
        for rule in rules
        if isinstance(rule, dict) and rule.get("jurisdiction") in {"EU", "VN"}
    )
    actor_relations = Counter(
        consequence.get("actor_relation")
        for rule in rules
        if isinstance(rule, dict)
        for consequence in rule.get("consequences", [])
        if isinstance(consequence, dict) and _nonempty_string(consequence.get("actor_relation"))
    )
    return {
        "schema_version": "1.0.0",
        "profile_id": payload.get("profile_id"),
        "status": "VALIDATED_PROVISIONAL_GRAPH" if not errors else "INVALID",
        "validation_errors": errors,
        "binding_rule_count": len(rules) if isinstance(rules, list) else 0,
        "binding_rules_by_jurisdiction": dict(sorted(jurisdiction_counts.items())),
        "typed_normative_slot_count": len(slots),
        "actor_relations": dict(sorted(actor_relations.items())),
        "removed_legacy_rule_count": len(payload.get("removed_legacy_rules", [])),
        "non_binding_policy_object_count": (
            len(policy_objects) if isinstance(policy_objects, list) else 0
        ),
        "article13_route_gate": {
            "point_a_count": 6,
            "point_b_count": 40,
            "visual_overlay_required": True,
        },
        "article19_required_slot_count": len(REQUIRED_ART19_SLOTS),
        "evaluation_gate": {
            "typed_graph_validation": "ALLOWED",
            "quantitative_evaluation": "BLOCKED",
            "directional_gap_metrics": "BLOCKED",
            "actor_mismatch_metrics": "BLOCKED",
            "manuscript_regeneration": "BLOCKED",
        },
        "attestation": {
            "independent_review_completed": False,
            "current_context_complete": False,
            "current_quantitative_results_exist": False,
            "notice": (
                "Validation proves structural completeness and safety gates for the "
                "provisional graph. It is not legal sign-off or a quantitative result."
            ),
        },
    }
