from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .stable_id import content_sha256


class EngineeringGateError(ValueError):
    """Raised when required engineering evidence is missing or malformed."""


REQUIRED_ARTIFACTS: dict[str, tuple[str, str]] = {
    "schema_inventory": ("schema-inventory.json", "SCHEMA_INVENTORY_VALID"),
    "decision33_context_v2": (
        "decision33-context-v2-corpus.json",
        "DECISION33_CONTEXT_V2_CORPUS_COMPLETE",
    ),
    "eu_article6_context_v2": (
        "eu-article6-context-v2-corpus.json",
        "EU_ARTICLE6_CONTEXT_V2_CORPUS_COMPLETE",
    ),
    "candidate_ir": (
        "current-candidate-ir-report.json",
        "CANDIDATE_EXECUTABLE_IR_COMPLETE_MODEL_RELATIVE",
    ),
    "source_derived_predicates": (
        "source-derived-predicate-report.json",
        "ALL_CANDIDATE_PREDICATES_EXECUTABLE_PENDING_REVIEW",
    ),
    "eu_vn_relation_scenarios": (
        "decision33-eu-relation-scenarios.json",
        "DECISION33_EU_RELATION_SCENARIOS_EXECUTED",
    ),
    "metric_analysis": (
        "model-relative-metric-analysis.json",
        "MODEL_RELATIVE_METRIC_ANALYSIS_COMPLETE",
    ),
    "operational_signatures": (
        "operational-duty-signature-report.json",
        "OPERATIONAL_DUTY_SIGNATURE_INVENTORY_COMPLETE",
    ),
    "candidate_hsdl_roundtrip": (
        "current-candidate-hsdl-differential-report.json",
        "EQUIVALENT",
    ),
    "python_oracle_projection": (
        "python-oracle-projection-report.json",
        "PYTHON_ORACLE_PROJECTION_COMPLETE",
    ),
    "independent_javascript_oracle": (
        "independent-javascript-oracle-report.json",
        "EQUIVALENT",
    ),
    "symbolic_explicit_routes": (
        "symbolic-catalog-region-report.json",
        "SYMBOLIC_EXPLICIT_ROUTE_ORACLE_EQUIVALENT",
    ),
    "symbolic_full_profile": (
        "source-derived-symbolic-profile-v2-report.json",
        "SOURCE_DERIVED_SYMBOLIC_PROFILE_EQUIVALENT",
    ),
    "priority_engine": (
        "candidate-priority-report.json",
        "CANDIDATE_PRIORITY_GRAPH_EXECUTABLE",
    ),
}


P0_GATES = (
    "schema_inventory",
    "decision33_context_v2",
    "candidate_ir",
    "metric_analysis",
    "candidate_hsdl_roundtrip",
    "python_oracle_projection",
    "independent_javascript_oracle",
)

P1_CAPABILITY_GATES = (
    "source_derived_predicates",
    "eu_article6_context_v2",
    "eu_vn_relation_scenarios",
    "operational_signatures",
    "symbolic_full_profile",
    "priority_engine",
)


def _load_artifact(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EngineeringGateError(f"required artifact is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise EngineeringGateError(f"artifact is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise EngineeringGateError(f"artifact must be a JSON object: {path}")
    return payload


def _artifact_record(
    *, root: Path, filename: str, expected_status: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = root / filename
    payload = _load_artifact(path)
    actual_status = payload.get("status")
    return (
        {
            "artifact": filename,
            "expected_status": expected_status,
            "actual_status": actual_status,
            "passed": actual_status == expected_status,
            "sha256": content_sha256(payload),
        },
        payload,
    )


def build_engineering_gate_status(
    artifact_dir: str | Path = "generated",
) -> dict[str, Any]:
    root = Path(artifact_dir)
    evidence: dict[str, dict[str, Any]] = {}
    payloads: dict[str, dict[str, Any]] = {}
    for gate_id, (filename, expected_status) in REQUIRED_ARTIFACTS.items():
        record, payload = _artifact_record(
            root=root, filename=filename, expected_status=expected_status
        )
        evidence[gate_id] = record
        payloads[gate_id] = payload

    p0 = {gate_id: evidence[gate_id]["passed"] for gate_id in P0_GATES}
    p1 = {
        gate_id: evidence[gate_id]["passed"] for gate_id in P1_CAPABILITY_GATES
    }

    source_predicates = payloads["source_derived_predicates"]
    eu_context = payloads["eu_article6_context_v2"]
    relation = payloads["eu_vn_relation_scenarios"]
    signatures = payloads["operational_signatures"]
    symbolic = payloads["symbolic_full_profile"]
    priority = payloads["priority_engine"]
    independent = payloads["independent_javascript_oracle"]
    candidate_ir = payloads["candidate_ir"]

    completeness = {
        "all_candidate_predicates_executable": (
            source_predicates.get("executable_predicate_count") == 20
            and source_predicates.get("readiness_only_predicate_count") == 0
        ),
        "eu_native_context_corpus_available": (
            eu_context.get("context_count") == 36
            and eu_context.get("native_route_count") == 9
        ),
        "shared_eu_vn_classification_relation_executable": (
            relation.get("scenario_count") == 2
            and relation.get("context_count_per_scenario") == 322
            and relation.get("completeness", {}).get(
                "all_322_contexts_receive_scenario_metadata"
            )
            is True
        ),
        "reviewed_eu_vn_crosswalk_available": relation.get(
            "completeness", {}
        ).get("reviewed_eu_vn_crosswalk_available") is True,
        "same_slot_cross_jurisdiction_crosswalk_available": (
            signatures.get("same_slot_cross_jurisdiction_pair_count", 0) > 0
        ),
        "full_candidate_symbolic_coverage": (
            symbolic.get("symbolic_rule_coverage") == 1.0
            and symbolic.get("mismatch_count") == 0
        ),
        "candidate_priority_edges_declared": (
            priority.get("edge_count", 0) > 0
            and priority.get("conditional_edge_count", 0) > 0
        ),
        "independent_oracle_hash_match": (
            independent.get("projection_hash_match") is True
        ),
        "source_custody_release_package": False,
        "license_and_citation_owner_declarations": False,
        "claim_ledger_and_generated_publication": False,
    }

    p0_complete = all(p0.values())
    p1_ready = all(p1.values())
    fully_complete = p0_complete and p1_ready and all(completeness.values())
    if fully_complete:
        status = "ENGINEERING_COMPLETE"
    elif p0_complete and p1_ready:
        status = "P0_COMPLETE_P1_CAPABILITIES_READY_COMPLETENESS_BLOCKED"
    elif p0_complete:
        status = "P0_COMPLETE_P1_CAPABILITIES_INCOMPLETE"
    else:
        status = "P0_ENGINEERING_INCOMPLETE"

    remaining = [key for key, complete in completeness.items() if not complete]
    return {
        "schema_version": "2.0.0",
        "status": status,
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "artifact_directory": root.as_posix(),
        "evidence": evidence,
        "p0": {
            "gate_count": len(p0),
            "passed": sum(p0.values()),
            "complete": p0_complete,
            "gates": p0,
        },
        "p1_capabilities": {
            "gate_count": len(p1),
            "passed": sum(p1.values()),
            "ready": p1_ready,
            "gates": p1,
        },
        "engineering_completeness": completeness,
        "remaining_engineering_work": remaining,
        "summary": {
            "decision33_context_count": payloads["decision33_context_v2"].get(
                "context_count"
            ),
            "eu_context_count": eu_context.get("context_count"),
            "eu_native_route_count": eu_context.get("native_route_count"),
            "candidate_rule_count": candidate_ir.get("compiled_rule_count"),
            "candidate_duty_count": candidate_ir.get("compiled_duty_count"),
            "source_derived_executable_predicate_count": source_predicates.get(
                "executable_predicate_count"
            ),
            "source_derived_readiness_only_count": source_predicates.get(
                "readiness_only_predicate_count"
            ),
            "independent_projection_count": independent.get("projection_count"),
            "symbolically_compiled_rule_count": symbolic.get(
                "symbolically_compiled_rule_count"
            ),
            "symbolic_rule_coverage": symbolic.get("symbolic_rule_coverage"),
            "priority_edge_count": priority.get("edge_count"),
            "conditional_priority_edge_count": priority.get(
                "conditional_edge_count"
            ),
            "relation_scenario_count": relation.get("scenario_count"),
            "relation_context_count_per_scenario": relation.get(
                "context_count_per_scenario"
            ),
            "same_slot_cross_jurisdiction_pair_count": signatures.get(
                "same_slot_cross_jurisdiction_pair_count"
            ),
        },
        "boundary": {
            "legal_review_gate_included": False,
            "publication_authorisation": "NOT_PROVIDED",
            "notice": (
                "This report tracks software, data, reproducibility and formal-model "
                "completion. Source-derived legal interpretations remain pending "
                "independent review."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", default="generated")
    args = parser.parse_args()
    report = build_engineering_gate_status(args.artifact_dir)
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if not report["p0"]["complete"]:
        raise SystemExit(16)


if __name__ == "__main__":
    main()
