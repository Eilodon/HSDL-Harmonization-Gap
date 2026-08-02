from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class NamedObject:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class AseanGuideOntology:
    id: str
    freeze_date: str
    status: str
    guiding_principles: tuple[NamedObject, ...]
    governance_framework_areas: tuple[NamedObject, ...]
    genai_risks: tuple[NamedObject, ...]
    genai_policy_dimensions: tuple[NamedObject, ...]
    risk_representation: str
    risk_codomain: str
    risks_mutually_exclusive: bool
    source_claims_exhaustive_partition: bool
    legacy_labels: tuple[str, ...]
    legacy_taxonomy_status: str

    @property
    def risk_ids(self) -> frozenset[str]:
        return frozenset(item.id for item in self.genai_risks)

    def validate_risk_flags(self, flags: Iterable[str]) -> frozenset[str]:
        selected = frozenset(flags)
        unknown = selected - self.risk_ids
        if unknown:
            raise ValueError(f"unknown ASEAN GenAI risk flags: {sorted(unknown)}")
        return selected


def _objects(values: list[dict[str, str]]) -> tuple[NamedObject, ...]:
    return tuple(NamedObject(id=value["id"], name=value["name"]) for value in values)


def load_asean_ontology(path: str | Path) -> AseanGuideOntology:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    risks = payload["genai_risk_objects"]
    legacy = payload["legacy_taxonomy_audit"]
    return AseanGuideOntology(
        id=payload["ontology_id"],
        freeze_date=payload["freeze_date"],
        status=payload["status"],
        guiding_principles=_objects(payload["guiding_principles"]),
        governance_framework_areas=_objects(payload["governance_framework_areas"]),
        genai_risks=_objects(risks["items"]),
        genai_policy_dimensions=_objects(payload["genai_policy_dimensions"]),
        risk_representation=risks["research_representation"],
        risk_codomain=risks["codomain"],
        risks_mutually_exclusive=bool(risks["mutually_exclusive"]),
        source_claims_exhaustive_partition=bool(risks["exhaustive_partition_claimed_by_source"]),
        legacy_labels=tuple(legacy["legacy_labels"]),
        legacy_taxonomy_status=legacy["status"],
    )


def validate_asean_ontology(ontology: AseanGuideOntology) -> list[str]:
    errors: list[str] = []
    expected_counts = {
        "guiding_principles": (ontology.guiding_principles, 7),
        "governance_framework_areas": (ontology.governance_framework_areas, 4),
        "genai_risks": (ontology.genai_risks, 6),
        "genai_policy_dimensions": (ontology.genai_policy_dimensions, 9),
    }
    for label, (objects, expected) in expected_counts.items():
        if len(objects) != expected:
            errors.append(f"{label} expected {expected}, got {len(objects)}")
        ids = [obj.id for obj in objects]
        if len(ids) != len(set(ids)):
            errors.append(f"{label} contains duplicate IDs")
    if ontology.risk_representation != "multi_label_flags":
        errors.append("GenAI risks must use multi_label_flags")
    if ontology.risk_codomain != "power_set":
        errors.append("GenAI risk codomain must be power_set")
    if ontology.risks_mutually_exclusive:
        errors.append("official GenAI risks must not be modeled as mutually exclusive")
    if ontology.source_claims_exhaustive_partition:
        errors.append("source must not be represented as claiming an exhaustive partition")
    return errors


def build_asean_ontology_audit(path: str | Path) -> dict[str, object]:
    ontology = load_asean_ontology(path)
    errors = validate_asean_ontology(ontology)
    example_overlap = ontology.validate_risk_flags(
        {"inaccurate_responses_disinformation", "embedded_biases", "privacy_confidentiality"}
    )
    return {
        "ontology_id": ontology.id,
        "freeze_date": ontology.freeze_date,
        "status": ontology.status,
        "counts": {
            "guiding_principles": len(ontology.guiding_principles),
            "governance_framework_areas": len(ontology.governance_framework_areas),
            "genai_risk_objects": len(ontology.genai_risks),
            "genai_policy_dimensions": len(ontology.genai_policy_dimensions),
        },
        "risk_model": {
            "representation": ontology.risk_representation,
            "codomain": ontology.risk_codomain,
            "mutually_exclusive": ontology.risks_mutually_exclusive,
            "source_claims_exhaustive_partition": ontology.source_claims_exhaustive_partition,
            "overlap_example": sorted(example_overlap),
        },
        "legacy_taxonomy": {
            "labels": list(ontology.legacy_labels),
            "status": ontology.legacy_taxonomy_status,
            "h7_2_gate": "RETRACT_OR_REFORMULATE_AS_TYPED_MULTI_LABEL_COMPARISON",
        },
        "validation_errors": errors,
    }
