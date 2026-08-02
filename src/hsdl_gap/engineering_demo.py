from __future__ import annotations

from .conditions_v2 import evaluate_condition_v2
from .experiment import (
    MetricDefinition,
    UnknownPolicy,
    build_experiment_envelope,
    compute_corpus_share,
)
from .tristate import TruthValue


def build_engineering_demo() -> dict[str, object]:
    condition = {
        "op": "and",
        "args": [
            {
                "op": "eq",
                "args": [
                    {"field": "system.direct_human_interaction"},
                    {"literal": True},
                ],
            },
            {
                "op": "on_or_after",
                "args": [
                    {"field": "time.evaluation_date"},
                    {"literal": "2026-08-15"},
                ],
            },
        ],
    }
    contexts = [
        {
            "system": {"direct_human_interaction": True},
            "time": {"evaluation_date": "2026-08-14"},
        },
        {
            "system": {"direct_human_interaction": True},
            "time": {"evaluation_date": "2026-08-15"},
        },
        {
            "system": {"direct_human_interaction": True},
            "time": {},
        },
    ]
    traces = [evaluate_condition_v2(condition, context) for context in contexts]
    definition = MetricDefinition(
        metric_id="metric:engineering:demo-applicability-share",
        measure_id="UNWEIGHTED_DEMO_CORPUS_SHARE",
        numerator_definition="demo contexts where the condition evaluates TRUE",
        denominator_definition="all three declared demo contexts",
        unknown_policy=UnknownPolicy.LOWER_UPPER_BOUND,
    )
    metric = compute_corpus_share(definition, (trace.value for trace in traces))
    envelope = build_experiment_envelope(
        profile_id="profile:engineering:demo-v1",
        profile_payload={"profile_id": "profile:engineering:demo-v1", "condition": condition},
        corpus_id="corpus:engineering:demo-v1",
        corpus_payload={"corpus_id": "corpus:engineering:demo-v1", "contexts": contexts},
        assumptions=["ASSUME_DEMO_EFFECTIVE_DATE_2026_08_15"],
        metric_definition=definition,
        metric_result=metric,
    )
    return {
        "schema_version": "1.0.0",
        "status": "ENGINEERING_DEMO_COMPLETE",
        "condition_traces": [trace.as_dict() for trace in traces],
        "experiment": envelope,
        "expected_truth_values": [
            TruthValue.FALSE.value,
            TruthValue.TRUE.value,
            TruthValue.UNKNOWN.value,
        ],
    }


def main() -> None:
    import json

    print(json.dumps(build_engineering_demo(), indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
