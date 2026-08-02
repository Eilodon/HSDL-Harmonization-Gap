from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any


class Bindingness(IntEnum):
    NOT_ADDRESSED = 0
    VOLUNTARY = 1
    RECOMMENDED = 2
    BINDING = 3


class EvaluationState(str, Enum):
    NO_APPLICABLE_RULE = "NO_APPLICABLE_RULE"
    DETERMINATE = "DETERMINATE"
    UNSPECIFIED_OBLIGOR = "UNSPECIFIED_OBLIGOR"
    PRIORITY_INDETERMINATE = "PRIORITY_INDETERMINATE"


class ActorRelation(str, Enum):
    SINGLE = "single"
    CONCURRENT = "concurrent"
    JOINT = "joint"
    PRIMARY = "primary"
    FALLBACK = "fallback"
    UNSPECIFIED = "unspecified"


@dataclass(frozen=True, slots=True)
class TypedDuty:
    id: str
    action: str
    object: str
    obligors: frozenset[str]
    actor_relation: ActorRelation = ActorRelation.SINGLE
    recipient: str | None = None
    timing: str | None = None
    conflict_class: str | None = None


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    jurisdiction: str
    group: str
    instrument: str
    provision: str
    bindingness: Bindingness
    condition: dict[str, Any]
    consequences: tuple[TypedDuty, ...]
    source_status: str = "legacy_frozen"
    interpretation_status: str = "author_interpreted"


@dataclass(frozen=True, slots=True)
class Policy:
    id: str
    jurisdiction: str
    version: str
    rules: tuple[Rule, ...]

    def rules_for_group(self, group: str) -> tuple[Rule, ...]:
        return tuple(rule for rule in self.rules if rule.group == group)


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule: Rule
    duties: tuple[TypedDuty, ...]


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    state: EvaluationState
    active_rule_ids: tuple[str, ...] = field(default_factory=tuple)
    bindingness: Bindingness = Bindingness.NOT_ADDRESSED
    duties: tuple[TypedDuty, ...] = field(default_factory=tuple)

    @property
    def flattened_obligors(self) -> frozenset[str]:
        actors: set[str] = set()
        for duty in self.duties:
            actors.update(duty.obligors)
        return frozenset(actors)
