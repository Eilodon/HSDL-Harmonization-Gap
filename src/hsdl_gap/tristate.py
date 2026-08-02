from __future__ import annotations

from enum import Enum
from typing import Iterable


class TruthValue(str, Enum):
    """Three-valued truth used when a context may omit material facts."""

    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_bool(cls, value: bool) -> "TruthValue":
        return cls.TRUE if value else cls.FALSE

    def __bool__(self) -> bool:
        raise TypeError(
            "TruthValue has no implicit boolean conversion; compare it explicitly"
        )


def tri_not(value: TruthValue) -> TruthValue:
    if value is TruthValue.TRUE:
        return TruthValue.FALSE
    if value is TruthValue.FALSE:
        return TruthValue.TRUE
    return TruthValue.UNKNOWN


def tri_and(values: Iterable[TruthValue]) -> TruthValue:
    saw_unknown = False
    for value in values:
        if value is TruthValue.FALSE:
            return TruthValue.FALSE
        if value is TruthValue.UNKNOWN:
            saw_unknown = True
    return TruthValue.UNKNOWN if saw_unknown else TruthValue.TRUE


def tri_or(values: Iterable[TruthValue]) -> TruthValue:
    saw_unknown = False
    for value in values:
        if value is TruthValue.TRUE:
            return TruthValue.TRUE
        if value is TruthValue.UNKNOWN:
            saw_unknown = True
    return TruthValue.UNKNOWN if saw_unknown else TruthValue.FALSE
