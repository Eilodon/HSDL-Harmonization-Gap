from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class EntityKind(str, Enum):
    SOURCE = "source"
    PROVISION = "provision"
    POLICY = "policy"
    RULE = "rule"
    DUTY = "duty"
    CONTEXT = "context"
    CORPUS = "corpus"
    METRIC = "metric"
    PROFILE = "profile"
    ASSUMPTION = "assumption"


@dataclass(frozen=True, slots=True, order=True)
class StableId:
    kind: EntityKind
    namespace: str
    local_id: str

    def __post_init__(self) -> None:
        for label, value in (
            ("namespace", self.namespace),
            ("local_id", self.local_id),
        ):
            if not _COMPONENT.fullmatch(value):
                raise ValueError(
                    f"{label} must match {_COMPONENT.pattern!r}: {value!r}"
                )

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.namespace}:{self.local_id}"

    @classmethod
    def parse(cls, value: str) -> "StableId":
        parts = value.split(":", 2)
        if len(parts) != 3:
            raise ValueError("stable IDs must have kind:namespace:local_id")
        kind_raw, namespace, local_id = parts
        try:
            kind = EntityKind(kind_raw)
        except ValueError as exc:
            raise ValueError(f"unsupported stable ID kind: {kind_raw!r}") from exc
        return cls(kind=kind, namespace=namespace, local_id=local_id)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def content_sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()
