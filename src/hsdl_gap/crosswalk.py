from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class PairRelation(str, Enum):
    EQUIVALENT = "equivalent"
    EQUIVALENT_WITH_EXTENSION = "equivalent_with_extension"
    ANALOGOUS = "analogous"
    CROSS_FUNCTIONAL_BUNDLE = "cross_functional_bundle"


@dataclass(frozen=True, slots=True)
class GroupCrosswalk:
    group: str
    relation: PairRelation
    shared_alignment_keys: tuple[str, ...]
    rationale: str
    review_status: str


def load_group_crosswalk(
    path: str | Path,
    left: str = "EU",
    right: str = "VN",
) -> dict[str, GroupCrosswalk]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    for comparison in payload["comparisons"]:
        if comparison["left"] == left and comparison["right"] == right:
            return {
                group: GroupCrosswalk(
                    group=group,
                    relation=PairRelation(data["relation"]),
                    shared_alignment_keys=tuple(data.get("shared_alignment_keys", [])),
                    rationale=data["rationale"],
                    review_status=data["review_status"],
                )
                for group, data in comparison["groups"].items()
            }
    raise KeyError(f"no crosswalk for {left}->{right}")
