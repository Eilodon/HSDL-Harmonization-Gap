from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CatalogItem:
    id: str
    sector: str
    sector_ordinal: int
    name_vi: str
    activation_features: tuple[str, ...]
    assessment_route: str
    assessment_route_evidence: str


@dataclass(frozen=True, slots=True)
class RegulatoryCatalog:
    id: str
    issued_on: str
    effective_from: str
    freeze_date: str
    legal_status_at_freeze: str
    transition: dict[str, Any]
    items: tuple[CatalogItem, ...]

    @property
    def sector_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.sector for item in self.items).items()))

    @property
    def assessment_route_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(item.assessment_route for item in self.items).items()))


def load_catalog(csv_path: str | Path, meta_path: str | Path | None = None) -> RegulatoryCatalog:
    csv_path = Path(csv_path)
    if meta_path is None:
        meta_path = csv_path.with_suffix(".meta.json")
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = tuple(csv.DictReader(handle))
    items = tuple(
        CatalogItem(
            id=row["id"],
            sector=row["sector"],
            sector_ordinal=int(row["sector_ordinal"]),
            name_vi=row["name_vi"],
            activation_features=tuple(filter(None, row["activation_features"].split("|"))),
            assessment_route=row["assessment_route"],
            assessment_route_evidence=row["assessment_route_evidence"],
        )
        for row in rows
    )
    return RegulatoryCatalog(
        id=meta["catalog_id"],
        issued_on=meta["issued_on"],
        effective_from=meta["effective_from"],
        freeze_date=meta["freeze_date"],
        legal_status_at_freeze=meta["legal_status_at_freeze"],
        transition=dict(meta["transition"]),
        items=items,
    )


def validate_catalog(catalog: RegulatoryCatalog) -> list[str]:
    errors: list[str] = []
    ids = [item.id for item in catalog.items]
    if len(ids) != len(set(ids)):
        errors.append("catalog item IDs are not unique")
    per_sector: dict[str, list[int]] = {}
    for item in catalog.items:
        per_sector.setdefault(item.sector, []).append(item.sector_ordinal)
        if not item.activation_features:
            errors.append(f"{item.id} has no activation features")
        if not item.assessment_route_evidence:
            errors.append(f"{item.id} has no assessment-route evidence status")
    for sector, ordinals in per_sector.items():
        expected = list(range(1, len(ordinals) + 1))
        if sorted(ordinals) != expected:
            errors.append(f"{sector} ordinals are not contiguous")
    return errors
