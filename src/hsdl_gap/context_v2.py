from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .stable_id import EntityKind, StableId, content_sha256


class FixtureType(str, Enum):
    POSITIVE_WITNESS = "POSITIVE_WITNESS"
    SINGLE_FAULT_NEGATIVE = "SINGLE_FAULT_NEGATIVE"
    BOUNDARY_BELOW = "BOUNDARY_BELOW"
    BOUNDARY_EXACT = "BOUNDARY_EXACT"
    BOUNDARY_ABOVE = "BOUNDARY_ABOVE"
    UNKNOWN_FACT = "UNKNOWN_FACT"
    MIXED_FEATURE = "MIXED_FEATURE"
    MULTI_RULE_OVERLAP = "MULTI_RULE_OVERLAP"
    PRIORITY_CONFLICT = "PRIORITY_CONFLICT"
    TEMPORAL_TRANSITION = "TEMPORAL_TRANSITION"
    ADVERSARIAL = "ADVERSARIAL"


@dataclass(frozen=True, slots=True)
class ContextV2:
    context_id: str
    profile_id: str
    fixture_type: FixtureType
    facts: Mapping[str, Any]
    provenance: Mapping[str, Any]
    parent_context_id: str | None = None
    mutation_id: str | None = None

    def __post_init__(self) -> None:
        parsed = StableId.parse(self.context_id)
        if parsed.kind is not EntityKind.CONTEXT:
            raise ValueError("context_id must use the context stable-ID kind")
        if not self.profile_id:
            raise ValueError("profile_id must be non-empty")
        if not isinstance(self.facts, Mapping):
            raise TypeError("facts must be a mapping")
        if not isinstance(self.provenance, Mapping):
            raise TypeError("provenance must be a mapping")
        if self.fixture_type is not FixtureType.POSITIVE_WITNESS and not self.parent_context_id:
            raise ValueError("derived fixtures must record parent_context_id")

    def as_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "2.0.0",
            "context_id": self.context_id,
            "profile_id": self.profile_id,
            "fixture_type": self.fixture_type.value,
            "parent_context_id": self.parent_context_id,
            "mutation_id": self.mutation_id,
            "facts": deepcopy(dict(self.facts)),
            "provenance": deepcopy(dict(self.provenance)),
        }

    @property
    def content_hash(self) -> str:
        return content_sha256(self.as_mapping())


def _set_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
    parts = field_path.split(".")
    current = payload
    for part in parts[:-1]:
        nested = current.get(part)
        if nested is None:
            nested = {}
            current[part] = nested
        if not isinstance(nested, dict):
            raise ValueError(f"cannot descend into non-object field {part!r}")
        current = nested
    current[parts[-1]] = value


def _delete_path(payload: dict[str, Any], field_path: str) -> None:
    parts = field_path.split(".")
    current: Any = payload
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


@dataclass(frozen=True, slots=True)
class MutationSpec:
    mutation_id: str
    field_path: str
    replacement: Any = None
    delete_field: bool = False
    fixture_type: FixtureType = FixtureType.SINGLE_FAULT_NEGATIVE
    rationale: str = "single-fault mutation"


def generate_single_fault_contexts(
    base: ContextV2,
    mutations: Sequence[MutationSpec],
) -> tuple[ContextV2, ...]:
    generated: list[ContextV2] = []
    seen_ids: set[str] = set()
    parent_local = StableId.parse(base.context_id).local_id
    for mutation in mutations:
        if mutation.mutation_id in seen_ids:
            raise ValueError(f"duplicate mutation_id: {mutation.mutation_id}")
        seen_ids.add(mutation.mutation_id)
        facts = deepcopy(dict(base.facts))
        if mutation.delete_field:
            _delete_path(facts, mutation.field_path)
        else:
            _set_path(facts, mutation.field_path, mutation.replacement)
        context_id = str(
            StableId(
                EntityKind.CONTEXT,
                "generated",
                f"{parent_local}.{mutation.mutation_id}",
            )
        )
        generated.append(
            ContextV2(
                context_id=context_id,
                profile_id=base.profile_id,
                fixture_type=mutation.fixture_type,
                parent_context_id=base.context_id,
                mutation_id=mutation.mutation_id,
                facts=facts,
                provenance={
                    "status": "SYNTHETIC_FIXTURE",
                    "generator": "single-fault-v1",
                    "field_path": mutation.field_path,
                    "delete_field": mutation.delete_field,
                    "rationale": mutation.rationale,
                },
            )
        )
    return tuple(generated)


def numeric_boundary_mutations(
    *,
    mutation_prefix: str,
    field_path: str,
    threshold: int | float,
    step: int | float = 1,
) -> tuple[MutationSpec, MutationSpec, MutationSpec, MutationSpec]:
    if step <= 0:
        raise ValueError("step must be positive")
    return (
        MutationSpec(
            mutation_id=f"{mutation_prefix}.below",
            field_path=field_path,
            replacement=threshold - step,
            fixture_type=FixtureType.BOUNDARY_BELOW,
            rationale="value immediately below threshold",
        ),
        MutationSpec(
            mutation_id=f"{mutation_prefix}.exact",
            field_path=field_path,
            replacement=threshold,
            fixture_type=FixtureType.BOUNDARY_EXACT,
            rationale="value exactly at threshold",
        ),
        MutationSpec(
            mutation_id=f"{mutation_prefix}.above",
            field_path=field_path,
            replacement=threshold + step,
            fixture_type=FixtureType.BOUNDARY_ABOVE,
            rationale="value immediately above threshold",
        ),
        MutationSpec(
            mutation_id=f"{mutation_prefix}.unknown",
            field_path=field_path,
            delete_field=True,
            fixture_type=FixtureType.UNKNOWN_FACT,
            rationale="threshold fact omitted to exercise unknown semantics",
        ),
    )
