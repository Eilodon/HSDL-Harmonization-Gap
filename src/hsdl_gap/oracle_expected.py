from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .candidate_ir import (
    compile_candidate_profile,
    evaluate_compiled_rule,
    load_assumption_sets,
)
from .decision33_context_v2 import build_decision33_context_v2_corpus
from .stable_id import content_sha256


def evaluation_projection(evaluation: Any) -> dict[str, Any]:
    return {
        "state": evaluation.state.value,
        "missing_facts": list(evaluation.missing_facts),
        "assumptions_used": list(evaluation.assumptions_used),
        "duties": [duty.as_mapping() for duty in evaluation.duties],
        "structural_trace": evaluation.structural_trace.as_dict(),
        "readiness_trace": evaluation.readiness_trace.as_dict(),
    }


def build_expected_oracle_report(
    *,
    candidate_path: str | Path,
    fact_bindings_path: str | Path,
    assumptions_path: str | Path,
    catalog_path: str | Path,
) -> dict[str, Any]:
    rules = compile_candidate_profile(candidate_path, fact_bindings_path)
    contexts = build_decision33_context_v2_corpus(catalog_path)
    assumption_sets = load_assumption_sets(assumptions_path)
    projections: list[dict[str, Any]] = []
    state_counts: Counter[str] = Counter()
    by_assumption: Counter[str] = Counter()
    for assumption_id in sorted(assumption_sets):
        assumption = assumption_sets[assumption_id]
        values = assumption.get("values", {})
        satisfied = tuple(assumption.get("satisfied_required_facts", ()))
        for rule in rules:
            for context in contexts:
                evaluation = evaluate_compiled_rule(
                    rule,
                    context,
                    assumption_values=values,
                    satisfied_required_facts=satisfied,
                )
                projection = evaluation_projection(evaluation)
                projections.append(
                    {
                        "assumption_set_id": assumption_id,
                        "rule_id": rule.rule_id,
                        "context_id": context.context_id,
                        "evaluation": projection,
                    }
                )
                state_counts[projection["state"]] += 1
                by_assumption[assumption_id] += 1
    return {
        "schema_version": "1.0.0",
        "status": "PYTHON_ORACLE_PROJECTION_COMPLETE",
        "projection_contract": "CANDIDATE_IR_EVALUATION_PROJECTION_V1",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "rule_count": len(rules),
        "context_count": len(contexts),
        "assumption_set_count": len(assumption_sets),
        "projection_count": len(projections),
        "projection_hash": content_sha256(projections),
        "state_counts": dict(sorted(state_counts.items())),
        "projections_by_assumption_set": dict(sorted(by_assumption.items())),
        "projection_samples": projections[:3],
        "notice": (
            "The hash commits to every projected Python evaluation in deterministic "
            "assumption, rule and context order. Independent engines must reproduce it."
        ),
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
        "--assumptions",
        default="profiles/current-candidate-2026-08-02/engineering_assumptions.json",
    )
    parser.add_argument("--catalog", default="catalogs/vn_decision_33_2026.csv")
    args = parser.parse_args()
    report = build_expected_oracle_report(
        candidate_path=args.candidate,
        fact_bindings_path=args.fact_bindings,
        assumptions_path=args.assumptions,
        catalog_path=args.catalog,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
