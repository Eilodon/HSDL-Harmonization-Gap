from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping

from .stable_id import content_sha256
from .tristate import TruthValue


class ClaimClass(str, Enum):
    MODEL_RELATIVE = "MODEL_RELATIVE"


class UnknownPolicy(str, Enum):
    EXCLUDE_AND_REPORT = "EXCLUDE_AND_REPORT"
    COUNT_AS_FALSE = "COUNT_AS_FALSE"
    COUNT_AS_SEPARATE_CATEGORY = "COUNT_AS_SEPARATE_CATEGORY"
    LOWER_UPPER_BOUND = "LOWER_UPPER_BOUND"


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    measure_id: str
    numerator_definition: str
    denominator_definition: str
    unknown_policy: UnknownPolicy = UnknownPolicy.COUNT_AS_SEPARATE_CATEGORY


@dataclass(frozen=True, slots=True)
class MetricResult:
    metric_id: str
    measure_id: str
    numerator: int
    denominator: int
    unknown_count: int
    value: float | None
    lower_bound: float | None = None
    upper_bound: float | None = None

    def as_mapping(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_truth(value: bool | TruthValue) -> TruthValue:
    if isinstance(value, TruthValue):
        return value
    if isinstance(value, bool):
        return TruthValue.from_bool(value)
    raise TypeError("metric observations must be bool or TruthValue")


def compute_corpus_share(
    definition: MetricDefinition,
    observations: Iterable[bool | TruthValue],
) -> MetricResult:
    values = tuple(_coerce_truth(value) for value in observations)
    true_count = sum(value is TruthValue.TRUE for value in values)
    false_count = sum(value is TruthValue.FALSE for value in values)
    unknown_count = sum(value is TruthValue.UNKNOWN for value in values)

    if definition.unknown_policy is UnknownPolicy.EXCLUDE_AND_REPORT:
        denominator = true_count + false_count
        value = true_count / denominator if denominator else None
        return MetricResult(
            metric_id=definition.metric_id,
            measure_id=definition.measure_id,
            numerator=true_count,
            denominator=denominator,
            unknown_count=unknown_count,
            value=value,
        )

    denominator = len(values)
    if definition.unknown_policy is UnknownPolicy.COUNT_AS_FALSE:
        value = true_count / denominator if denominator else None
        return MetricResult(
            metric_id=definition.metric_id,
            measure_id=definition.measure_id,
            numerator=true_count,
            denominator=denominator,
            unknown_count=unknown_count,
            value=value,
        )

    if definition.unknown_policy is UnknownPolicy.COUNT_AS_SEPARATE_CATEGORY:
        value = true_count / denominator if denominator else None
        return MetricResult(
            metric_id=definition.metric_id,
            measure_id=definition.measure_id,
            numerator=true_count,
            denominator=denominator,
            unknown_count=unknown_count,
            value=value,
        )

    lower = true_count / denominator if denominator else None
    upper = (true_count + unknown_count) / denominator if denominator else None
    return MetricResult(
        metric_id=definition.metric_id,
        measure_id=definition.measure_id,
        numerator=true_count,
        denominator=denominator,
        unknown_count=unknown_count,
        value=None,
        lower_bound=lower,
        upper_bound=upper,
    )


def build_experiment_envelope(
    *,
    profile_id: str,
    profile_payload: Mapping[str, Any],
    corpus_id: str,
    corpus_payload: Mapping[str, Any],
    assumptions: Iterable[str],
    metric_definition: MetricDefinition,
    metric_result: MetricResult,
) -> dict[str, Any]:
    if metric_definition.metric_id != metric_result.metric_id:
        raise ValueError("metric definition/result IDs differ")
    if metric_definition.measure_id != metric_result.measure_id:
        raise ValueError("metric definition/result measure IDs differ")
    return {
        "schema_version": "1.0.0",
        "claim_class": ClaimClass.MODEL_RELATIVE.value,
        "legal_validation": "NOT_ASSERTED",
        "profile": {
            "profile_id": profile_id,
            "profile_hash": content_sha256(profile_payload),
        },
        "corpus": {
            "corpus_id": corpus_id,
            "corpus_hash": content_sha256(corpus_payload),
        },
        "assumptions": sorted(set(assumptions)),
        "metric_definition": {
            "metric_id": metric_definition.metric_id,
            "measure_id": metric_definition.measure_id,
            "numerator_definition": metric_definition.numerator_definition,
            "denominator_definition": metric_definition.denominator_definition,
            "unknown_policy": metric_definition.unknown_policy.value,
        },
        "metric_result": metric_result.as_mapping(),
        "claim_boundary": (
            "This result describes the declared executable profile and corpus only. "
            "It is not a claim about empirical prevalence or independently validated law."
        ),
    }
