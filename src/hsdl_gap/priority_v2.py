from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping

from .candidate_ir import compile_candidate_profile
from .conditions_v2 import evaluate_condition_v2
from .stable_id import content_sha256
from .tristate import TruthValue


class PriorityRelation(str, Enum):
    ACCUMULATE = "ACCUMULATE"
    PRECEDES = "PRECEDES"
    OVERRIDE = "OVERRIDE"
    EXCEPTION = "EXCEPTION"
    SPECIALISE = "SPECIALISE"
    CONFLICT = "CONFLICT"
    INDEPENDENT = "INDEPENDENT"


class PriorityResolutionState(str, Enum):
    DETERMINATE = "DETERMINATE"
    PRIORITY_INDETERMINATE = "PRIORITY_INDETERMINATE"


SUPPRESSING_RELATIONS = {
    PriorityRelation.OVERRIDE,
    PriorityRelation.EXCEPTION,
    PriorityRelation.SPECIALISE,
}


class PriorityGraphError(ValueError):
    """Raised when a priority graph violates its executable contract."""


@dataclass(frozen=True, slots=True)
class PriorityEdge:
    source_id: str
    target_id: str
    relation: PriorityRelation
    reason_code: str
    condition: Mapping[str, Any] | None = field(default=None, compare=False)
    source_evidence: Mapping[str, Any] | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not self.source_id or not self.target_id:
            raise PriorityGraphError("priority edge IDs must be non-empty")
        if not self.reason_code:
            raise PriorityGraphError("priority edge reason_code must be non-empty")
        if self.source_id == self.target_id and self.relation is not PriorityRelation.INDEPENDENT:
            raise PriorityGraphError("non-independent priority edges cannot be self-referential")
        if self.condition is not None:
            if not isinstance(self.condition, Mapping):
                raise PriorityGraphError("priority edge condition must be an object")
            try:
                evaluate_condition_v2(self.condition, {})
            except ValueError as exc:
                raise PriorityGraphError(f"invalid priority edge condition: {exc}") from exc
        if self.source_evidence is not None and not isinstance(
            self.source_evidence, Mapping
        ):
            raise PriorityGraphError("source_evidence must be an object")

    def as_mapping(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation.value,
            "reason_code": self.reason_code,
            "condition": dict(self.condition) if self.condition is not None else None,
            "source_evidence": (
                dict(self.source_evidence)
                if self.source_evidence is not None
                else None
            ),
        }


def _edge_key(edge: PriorityEdge) -> tuple[str, str, str, str]:
    return edge.source_id, edge.target_id, edge.relation.value, edge.reason_code


@dataclass(frozen=True, slots=True)
class PriorityResolution:
    state: PriorityResolutionState
    active_ids: tuple[str, ...]
    effective_ids: tuple[str, ...]
    suppressed: Mapping[str, tuple[dict[str, str], ...]]
    unresolved_conflicts: tuple[tuple[str, str], ...]
    cycle_components: tuple[tuple[str, ...], ...]
    unknown_edge_conditions: tuple[dict[str, Any], ...]
    inactive_conditional_edges: tuple[dict[str, Any], ...]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "active_ids": list(self.active_ids),
            "effective_ids": list(self.effective_ids),
            "suppressed": {
                target: list(reasons)
                for target, reasons in sorted(self.suppressed.items())
            },
            "unresolved_conflicts": [list(pair) for pair in self.unresolved_conflicts],
            "cycle_components": [list(component) for component in self.cycle_components],
            "unknown_edge_conditions": list(self.unknown_edge_conditions),
            "inactive_conditional_edges": list(self.inactive_conditional_edges),
        }


def load_priority_graph(path: str | Path) -> tuple[str, tuple[PriorityEdge, ...], dict[str, Any]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PriorityGraphError(f"cannot load priority graph: {exc}") from exc
    if not isinstance(payload, dict):
        raise PriorityGraphError("priority graph must be a JSON object")
    if payload.get("claim_class") != "MODEL_RELATIVE":
        raise PriorityGraphError("priority graph must be model-relative")
    if payload.get("legal_validation") != "NOT_ASSERTED":
        raise PriorityGraphError("priority graph must not assert legal validation")
    profile_id = payload.get("profile_id")
    if not isinstance(profile_id, str) or not profile_id:
        raise PriorityGraphError("priority graph profile_id must be non-empty")
    raw_edges = payload.get("edges")
    if not isinstance(raw_edges, list):
        raise PriorityGraphError("priority graph edges must be an array")
    edges: list[PriorityEdge] = []
    seen: set[tuple[str, str, PriorityRelation]] = set()
    for index, raw in enumerate(raw_edges):
        if not isinstance(raw, dict):
            raise PriorityGraphError(f"edges[{index}] must be an object")
        try:
            edge = PriorityEdge(
                source_id=raw["source_id"],
                target_id=raw["target_id"],
                relation=PriorityRelation(raw["relation"]),
                reason_code=raw["reason_code"],
                condition=raw.get("condition"),
                source_evidence=raw.get("source_evidence"),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise PriorityGraphError(f"invalid edges[{index}]") from exc
        key = (edge.source_id, edge.target_id, edge.relation)
        if key in seen:
            raise PriorityGraphError(f"duplicate priority edge: {key}")
        seen.add(key)
        edges.append(edge)
    return profile_id, tuple(edges), payload


def validate_edge_ids(edges: Iterable[PriorityEdge], known_ids: Iterable[str]) -> None:
    known = set(known_ids)
    unknown = sorted(
        {
            identifier
            for edge in edges
            for identifier in (edge.source_id, edge.target_id)
            if identifier not in known
        }
    )
    if unknown:
        raise PriorityGraphError(f"priority graph references unknown IDs: {unknown}")


def _strongly_connected_components(
    nodes: set[str],
    edges: tuple[PriorityEdge, ...],
) -> tuple[tuple[str, ...], ...]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.relation in SUPPRESSING_RELATIONS:
            adjacency[edge.source_id].append(edge.target_id)
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(adjacency.get(node, [])):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == node:
                    break
            if len(component) > 1:
                components.append(tuple(sorted(component)))

    for node in sorted(nodes):
        if node not in indices:
            visit(node)
    return tuple(sorted(components))


def _conditioned_edges(
    active_set: set[str],
    edges: tuple[PriorityEdge, ...],
    facts: Mapping[str, Any],
) -> tuple[tuple[PriorityEdge, ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    enabled: list[PriorityEdge] = []
    unknown: list[dict[str, Any]] = []
    inactive: list[dict[str, Any]] = []
    for edge in edges:
        if edge.source_id not in active_set or edge.target_id not in active_set:
            continue
        if edge.condition is None:
            enabled.append(edge)
            continue
        trace = evaluate_condition_v2(edge.condition, facts)
        record = {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relation": edge.relation.value,
            "reason_code": edge.reason_code,
            "condition_value": trace.value.value,
            "missing_facts": list(trace.missing_facts),
        }
        if trace.value is TruthValue.TRUE:
            enabled.append(edge)
        elif trace.value is TruthValue.FALSE:
            inactive.append(record)
        else:
            unknown.append(record)
    return (
        tuple(sorted(enabled, key=_edge_key)),
        tuple(sorted(unknown, key=lambda item: (item["source_id"], item["target_id"]))),
        tuple(sorted(inactive, key=lambda item: (item["source_id"], item["target_id"]))),
    )


def resolve_priority(
    active_ids: Iterable[str],
    edges: Iterable[PriorityEdge],
    *,
    known_ids: Iterable[str] | None = None,
    facts: Mapping[str, Any] | None = None,
) -> PriorityResolution:
    active = tuple(sorted(set(active_ids)))
    active_set = set(active)
    edge_tuple = tuple(sorted(edges, key=_edge_key))
    if known_ids is not None:
        validate_edge_ids(edge_tuple, known_ids)
    enabled, unknown_conditions, inactive_conditions = _conditioned_edges(
        active_set, edge_tuple, facts or {}
    )
    cycles = _strongly_connected_components(active_set, enabled)
    cycle_members = {member for component in cycles for member in component}

    suppressed_reasons: dict[str, list[dict[str, str]]] = defaultdict(list)
    for edge in enabled:
        if (
            edge.relation in SUPPRESSING_RELATIONS
            and edge.source_id not in cycle_members
            and edge.target_id not in cycle_members
        ):
            suppressed_reasons[edge.target_id].append(
                {
                    "source_id": edge.source_id,
                    "relation": edge.relation.value,
                    "reason_code": edge.reason_code,
                }
            )

    effective = active_set - set(suppressed_reasons) - cycle_members
    conflicts: set[tuple[str, str]] = set()
    for edge in enabled:
        if edge.relation is PriorityRelation.CONFLICT:
            if edge.source_id in effective and edge.target_id in effective:
                conflicts.add(tuple(sorted((edge.source_id, edge.target_id))))

    state = (
        PriorityResolutionState.PRIORITY_INDETERMINATE
        if cycles or conflicts or unknown_conditions
        else PriorityResolutionState.DETERMINATE
    )
    return PriorityResolution(
        state=state,
        active_ids=active,
        effective_ids=tuple(sorted(effective)),
        suppressed={
            target: tuple(
                sorted(
                    reasons,
                    key=lambda item: (
                        item["source_id"], item["relation"], item["reason_code"]
                    ),
                )
            )
            for target, reasons in suppressed_reasons.items()
        },
        unresolved_conflicts=tuple(sorted(conflicts)),
        cycle_components=cycles,
        unknown_edge_conditions=unknown_conditions,
        inactive_conditional_edges=inactive_conditions,
    )


def build_candidate_priority_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
    priority_graph_path: str | Path,
) -> dict[str, Any]:
    rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    duty_ids = tuple(duty.duty_id for rule in rules for duty in rule.duties)
    profile_id, edges, graph_payload = load_priority_graph(priority_graph_path)
    validate_edge_ids(edges, duty_ids)
    all_active = resolve_priority(duty_ids, edges, known_ids=duty_ids)
    reachable = resolve_priority(
        duty_ids,
        edges,
        known_ids=duty_ids,
        facts={"operations": {"provider_contact_status": "REACHABLE"}},
    )
    unreachable = resolve_priority(
        duty_ids,
        edges,
        known_ids=duty_ids,
        facts={"operations": {"provider_contact_status": "UNREACHABLE"}},
    )
    relation_counts = Counter(edge.relation.value for edge in edges)
    conditional_count = sum(edge.condition is not None for edge in edges)
    evidence_count = sum(edge.source_evidence is not None for edge in edges)
    return {
        "schema_version": "2.0.0",
        "status": "CANDIDATE_PRIORITY_GRAPH_EXECUTABLE",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "profile_id": profile_id,
        "priority_graph_hash": content_sha256(graph_payload),
        "duty_count": len(duty_ids),
        "edge_count": len(edges),
        "conditional_edge_count": conditional_count,
        "source_evidenced_edge_count": evidence_count,
        "edge_relation_counts": dict(sorted(relation_counts.items())),
        "graph_status": graph_payload.get("status"),
        "all_duties_active_probe": all_active.as_mapping(),
        "provider_reachable_probe": reachable.as_mapping(),
        "provider_unreachable_probe": unreachable.as_mapping(),
        "semantics": {
            "suppressing_relations": sorted(item.value for item in SUPPRESSING_RELATIONS),
            "accumulate": "retains both active duties",
            "precedes": "records source-derived sequence without suppressing either duty",
            "independent": "retains both active duties",
            "conflict": "marks priority indeterminate when both unsuppressed duties remain",
            "conditional_unknown": "marks priority indeterminate until the edge condition is known",
            "cycles": "marks every active suppressing-cycle member indeterminate",
        },
        "limitations": {
            "candidate_edges_declared": bool(edges),
            "current_candidate_priority_resolution": "DECLARED_SOURCE_DERIVED_EDGES_APPLIED",
            "conditional_priority_edges": "IMPLEMENTED",
            "cross_jurisdiction_priority": "NOT_DECLARED",
            "independent_legal_review": "PENDING",
            "notice": (
                "Declared edges encode coexistence, sequence and fallback within the "
                "same instrument. They do not infer cross-jurisdiction priority."
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
        "--priority-graph",
        default="profiles/current-candidate-2026-08-02/engineering_priority_graph.json",
    )
    args = parser.parse_args()
    report = build_candidate_priority_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
        priority_graph_path=args.priority_graph,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
