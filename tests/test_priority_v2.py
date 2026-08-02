from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.priority_v2 import (
    PriorityEdge,
    PriorityGraphError,
    PriorityRelation,
    PriorityResolutionState,
    build_candidate_priority_report,
    load_priority_graph,
    resolve_priority,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "policies" / "current_candidate_graph_2026-08-02.json"
BINDINGS = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "engineering_fact_bindings.json"
)
GRAPH = (
    ROOT
    / "profiles"
    / "current-candidate-2026-08-02"
    / "engineering_priority_graph.json"
)


def edge(
    source: str,
    target: str,
    relation: PriorityRelation,
    reason: str = "TEST",
    condition: dict | None = None,
) -> PriorityEdge:
    return PriorityEdge(source, target, relation, reason, condition=condition)


class PriorityV2Tests(unittest.TestCase):
    def test_candidate_uses_declared_source_graph(self) -> None:
        report = build_candidate_priority_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            priority_graph_path=GRAPH,
        )
        self.assertEqual(report["status"], "CANDIDATE_PRIORITY_GRAPH_EXECUTABLE")
        self.assertEqual(report["schema_version"], "2.0.0")
        self.assertEqual(report["duty_count"], 25)
        self.assertEqual(report["edge_count"], 9)
        self.assertEqual(report["conditional_edge_count"], 2)
        self.assertEqual(report["source_evidenced_edge_count"], 9)
        self.assertEqual(
            report["edge_relation_counts"],
            {
                "ACCUMULATE": 3,
                "EXCEPTION": 1,
                "OVERRIDE": 1,
                "PRECEDES": 4,
            },
        )
        self.assertEqual(
            report["graph_status"],
            "SOURCE_DERIVED_DECLARED_PRIORITY_GRAPH_PENDING_REVIEW",
        )
        self.assertEqual(
            report["limitations"]["current_candidate_priority_resolution"],
            "DECLARED_SOURCE_DERIVED_EDGES_APPLIED",
        )
        self.assertEqual(
            report["limitations"]["conditional_priority_edges"], "IMPLEMENTED"
        )
        self.assertEqual(
            report["limitations"]["cross_jurisdiction_priority"],
            "NOT_DECLARED",
        )

    def test_unknown_fallback_condition_is_indeterminate(self) -> None:
        report = build_candidate_priority_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            priority_graph_path=GRAPH,
        )
        probe = report["all_duties_active_probe"]
        self.assertEqual(probe["state"], "PRIORITY_INDETERMINATE")
        self.assertEqual(len(probe["unknown_edge_conditions"]), 2)
        self.assertEqual(len(probe["effective_ids"]), 25)

    def test_provider_reachable_and_unreachable_probes_are_determinate(self) -> None:
        report = build_candidate_priority_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            priority_graph_path=GRAPH,
        )
        provider = (
            "VN_ND142_ART19_4_PRELIMINARY_REPORTING:"
            "serious_incident_preliminary_report"
        )
        fallback = (
            "VN_ND142_ART19_4_PRELIMINARY_REPORTING:"
            "serious_incident_preliminary_report_fallback"
        )
        reachable = report["provider_reachable_probe"]
        self.assertEqual(reachable["state"], "DETERMINATE")
        self.assertIn(fallback, reachable["suppressed"])
        self.assertNotIn(fallback, reachable["effective_ids"])
        self.assertIn(provider, reachable["effective_ids"])
        unreachable = report["provider_unreachable_probe"]
        self.assertEqual(unreachable["state"], "DETERMINATE")
        self.assertIn(provider, unreachable["suppressed"])
        self.assertNotIn(provider, unreachable["effective_ids"])
        self.assertIn(fallback, unreachable["effective_ids"])

    def test_override_suppresses_target(self) -> None:
        result = resolve_priority(
            ["A", "B"],
            [edge("A", "B", PriorityRelation.OVERRIDE)],
            known_ids=["A", "B"],
        )
        self.assertEqual(result.state, PriorityResolutionState.DETERMINATE)
        self.assertEqual(result.effective_ids, ("A",))
        self.assertEqual(result.suppressed["B"][0]["relation"], "OVERRIDE")

    def test_conditional_override_tracks_false_and_unknown(self) -> None:
        conditional = edge(
            "A",
            "B",
            PriorityRelation.OVERRIDE,
            condition={
                "op": "eq",
                "args": [{"field": "facts.ready"}, {"literal": True}],
            },
        )
        unknown = resolve_priority(
            ["A", "B"], [conditional], known_ids=["A", "B"]
        )
        self.assertEqual(
            unknown.state, PriorityResolutionState.PRIORITY_INDETERMINATE
        )
        self.assertEqual(len(unknown.unknown_edge_conditions), 1)
        inactive = resolve_priority(
            ["A", "B"],
            [conditional],
            known_ids=["A", "B"],
            facts={"facts": {"ready": False}},
        )
        self.assertEqual(inactive.state, PriorityResolutionState.DETERMINATE)
        self.assertEqual(inactive.effective_ids, ("A", "B"))
        self.assertEqual(len(inactive.inactive_conditional_edges), 1)
        enabled = resolve_priority(
            ["A", "B"],
            [conditional],
            known_ids=["A", "B"],
            facts={"facts": {"ready": True}},
        )
        self.assertEqual(enabled.effective_ids, ("A",))

    def test_exception_and_specialisation_are_suppressing(self) -> None:
        for relation in (PriorityRelation.EXCEPTION, PriorityRelation.SPECIALISE):
            with self.subTest(relation=relation):
                result = resolve_priority(
                    ["general", "specific"],
                    [edge("specific", "general", relation)],
                    known_ids=["general", "specific"],
                )
                self.assertEqual(result.effective_ids, ("specific",))

    def test_accumulate_precedes_and_independent_retain_both(self) -> None:
        for relation in (
            PriorityRelation.ACCUMULATE,
            PriorityRelation.PRECEDES,
            PriorityRelation.INDEPENDENT,
        ):
            with self.subTest(relation=relation):
                result = resolve_priority(
                    ["A", "B"],
                    [edge("A", "B", relation)],
                    known_ids=["A", "B"],
                )
                self.assertEqual(result.state, PriorityResolutionState.DETERMINATE)
                self.assertEqual(result.effective_ids, ("A", "B"))

    def test_unsuppressed_conflict_is_indeterminate(self) -> None:
        result = resolve_priority(
            ["A", "B"],
            [edge("A", "B", PriorityRelation.CONFLICT)],
            known_ids=["A", "B"],
        )
        self.assertEqual(result.state, PriorityResolutionState.PRIORITY_INDETERMINATE)
        self.assertEqual(result.unresolved_conflicts, (("A", "B"),))

    def test_suppression_can_remove_a_conflict_party(self) -> None:
        result = resolve_priority(
            ["A", "B", "C"],
            [
                edge("A", "B", PriorityRelation.OVERRIDE),
                edge("B", "C", PriorityRelation.CONFLICT),
            ],
            known_ids=["A", "B", "C"],
        )
        self.assertEqual(result.state, PriorityResolutionState.DETERMINATE)
        self.assertEqual(result.effective_ids, ("A", "C"))
        self.assertEqual(result.unresolved_conflicts, ())

    def test_suppressing_cycle_is_indeterminate(self) -> None:
        result = resolve_priority(
            ["A", "B", "C"],
            [
                edge("A", "B", PriorityRelation.OVERRIDE),
                edge("B", "A", PriorityRelation.EXCEPTION),
            ],
            known_ids=["A", "B", "C"],
        )
        self.assertEqual(result.state, PriorityResolutionState.PRIORITY_INDETERMINATE)
        self.assertEqual(result.cycle_components, (("A", "B"),))
        self.assertEqual(result.effective_ids, ("C",))

    def test_unknown_edge_identifier_is_rejected(self) -> None:
        with self.assertRaises(PriorityGraphError):
            resolve_priority(
                ["A"],
                [edge("A", "missing", PriorityRelation.OVERRIDE)],
                known_ids=["A"],
            )

    def test_non_independent_self_edge_is_rejected(self) -> None:
        with self.assertRaises(PriorityGraphError):
            edge("A", "A", PriorityRelation.OVERRIDE)

    def test_duplicate_graph_edge_is_rejected(self) -> None:
        payload = {
            "schema_version": "2.0.0",
            "profile_id": "test",
            "claim_class": "MODEL_RELATIVE",
            "legal_validation": "NOT_ASSERTED",
            "edges": [
                {
                    "source_id": "A",
                    "target_id": "B",
                    "relation": "OVERRIDE",
                    "reason_code": "X",
                },
                {
                    "source_id": "A",
                    "target_id": "B",
                    "relation": "OVERRIDE",
                    "reason_code": "Y",
                },
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "priority.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(PriorityGraphError):
                load_priority_graph(path)


if __name__ == "__main__":
    unittest.main()
