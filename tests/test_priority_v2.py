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
) -> PriorityEdge:
    return PriorityEdge(source, target, relation, reason)


class PriorityV2Tests(unittest.TestCase):
    def test_candidate_uses_explicit_empty_graph(self) -> None:
        report = build_candidate_priority_report(
            candidate_path=CANDIDATE,
            fact_bindings_path=BINDINGS,
            priority_graph_path=GRAPH,
        )
        self.assertEqual(report["status"], "CANDIDATE_PRIORITY_GRAPH_EXECUTABLE")
        self.assertEqual(report["duty_count"], 25)
        self.assertEqual(report["edge_count"], 0)
        self.assertEqual(report["edge_relation_counts"], {})
        probe = report["all_duties_active_probe"]
        self.assertEqual(probe["state"], "DETERMINATE")
        self.assertEqual(len(probe["effective_ids"]), 25)
        self.assertEqual(probe["suppressed"], {})
        self.assertEqual(
            report["limitations"]["current_candidate_priority_resolution"],
            "NO_EDGES_DECLARED_NO_IMPLICIT_PRIORITY",
        )

    def test_override_suppresses_target(self) -> None:
        result = resolve_priority(
            ["A", "B"],
            [edge("A", "B", PriorityRelation.OVERRIDE)],
            known_ids=["A", "B"],
        )
        self.assertEqual(result.state, PriorityResolutionState.DETERMINATE)
        self.assertEqual(result.effective_ids, ("A",))
        self.assertEqual(result.suppressed["B"][0]["relation"], "OVERRIDE")

    def test_exception_and_specialisation_are_suppressing(self) -> None:
        for relation in (PriorityRelation.EXCEPTION, PriorityRelation.SPECIALISE):
            with self.subTest(relation=relation):
                result = resolve_priority(
                    ["general", "specific"],
                    [edge("specific", "general", relation)],
                    known_ids=["general", "specific"],
                )
                self.assertEqual(result.effective_ids, ("specific",))

    def test_accumulate_and_independent_retain_both(self) -> None:
        for relation in (PriorityRelation.ACCUMULATE, PriorityRelation.INDEPENDENT):
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
            "schema_version": "1.0.0",
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
