from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .conditions_v2 import evaluate_condition_v2
from .experiment import (
    MetricDefinition,
    UnknownPolicy,
    build_experiment_envelope,
    compute_corpus_share,
)
from .schema_inventory import build_schema_inventory
from .tristate import TruthValue


def _load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _parse_observation(value: Any) -> TruthValue:
    if value is True:
        return TruthValue.TRUE
    if value is False:
        return TruthValue.FALSE
    if isinstance(value, str):
        try:
            return TruthValue(value.upper())
        except ValueError as exc:
            raise ValueError(f"invalid observation: {value!r}") from exc
    raise ValueError(f"invalid observation: {value!r}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hsdl-gap-engineering",
        description=(
            "Engineering-only utilities. Outputs are model-relative and do not assert "
            "independently validated legal conclusions."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inventory = subparsers.add_parser("schema-inventory")
    inventory.add_argument("--schema-dir", default="schemas")

    evaluate = subparsers.add_parser("evaluate-condition")
    evaluate.add_argument("--condition", required=True)
    evaluate.add_argument("--context", required=True)

    experiment = subparsers.add_parser("experiment-report")
    experiment.add_argument("--profile", required=True)
    experiment.add_argument("--corpus", required=True)
    experiment.add_argument("--observations", required=True)
    experiment.add_argument("--metric-id", required=True)
    experiment.add_argument("--measure-id", default="UNWEIGHTED_CORPUS_SHARE")
    experiment.add_argument(
        "--unknown-policy",
        choices=tuple(policy.value for policy in UnknownPolicy),
        default=UnknownPolicy.COUNT_AS_SEPARATE_CATEGORY.value,
    )
    experiment.add_argument("--assumption", action="append", default=[])

    args = parser.parse_args()
    if args.command == "schema-inventory":
        result = build_schema_inventory(args.schema_dir)
    elif args.command == "evaluate-condition":
        condition = _load_json(args.condition)
        context = _load_json(args.context)
        result = evaluate_condition_v2(condition, context).as_dict()
    else:
        profile = _load_json(args.profile)
        corpus = _load_json(args.corpus)
        observations_payload = _load_json(args.observations)
        if not isinstance(observations_payload, list):
            raise ValueError("observations must be a JSON array")
        definition = MetricDefinition(
            metric_id=args.metric_id,
            measure_id=args.measure_id,
            numerator_definition="observations equal TRUE",
            denominator_definition="all declared corpus observations",
            unknown_policy=UnknownPolicy(args.unknown_policy),
        )
        metric = compute_corpus_share(
            definition,
            (_parse_observation(value) for value in observations_payload),
        )
        result = build_experiment_envelope(
            profile_id=str(profile.get("profile_id", "unspecified-profile")),
            profile_payload=profile,
            corpus_id=str(corpus.get("corpus_id", "unspecified-corpus")),
            corpus_payload=corpus,
            assumptions=args.assumption,
            metric_definition=definition,
            metric_result=metric,
        )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
