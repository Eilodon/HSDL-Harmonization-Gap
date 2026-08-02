from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from .conditions import evaluate_condition
from .context import iter_legacy_contexts
from .loader import load_policy_bundle
from .model import Policy, TypedDuty


LabelMode = Literal["exact", "broad"]
CoverMode = Literal["indexed", "quotient"]


@dataclass(frozen=True, slots=True)
class CoverBlock:
    id: str
    jurisdiction: str
    group: str
    label_mode: LabelMode
    label: str
    support: frozenset[int]
    member_ids: tuple[str, ...]

    @property
    def typed_label(self) -> str:
        return f"{self.group}::{self.label}"


def duty_label(duty: TypedDuty, label_mode: LabelMode) -> str | None:
    if label_mode == "exact":
        return duty.normative_slot
    if label_mode == "broad":
        return duty.alignment_key
    raise ValueError(f"unsupported label_mode: {label_mode!r}")


def build_indexed_cover(
    policy: Policy,
    *,
    label_mode: LabelMode,
) -> tuple[list[CoverBlock], list[str]]:
    contexts = tuple(iter_legacy_contexts())
    blocks: list[CoverBlock] = []
    unlabeled: list[str] = []
    for rule in policy.rules:
        support = frozenset(
            index
            for index, context in enumerate(contexts)
            if evaluate_condition(rule.condition, context.as_mapping())
        )
        for duty in rule.consequences:
            label = duty_label(duty, label_mode)
            member_id = f"{rule.id}:{duty.id}"
            if not label:
                unlabeled.append(member_id)
                continue
            blocks.append(
                CoverBlock(
                    id=member_id,
                    jurisdiction=policy.jurisdiction,
                    group=rule.group,
                    label_mode=label_mode,
                    label=label,
                    support=support,
                    member_ids=(member_id,),
                )
            )
    return blocks, sorted(unlabeled)


def quotient_cover(blocks: Iterable[CoverBlock]) -> list[CoverBlock]:
    grouped: dict[tuple[str, str, frozenset[int]], list[CoverBlock]] = {}
    for block in blocks:
        key = (block.group, block.label, block.support)
        grouped.setdefault(key, []).append(block)

    quotient: list[CoverBlock] = []
    for (group, label, support), members in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1], sorted(item[0][2])),
    ):
        all_member_ids = tuple(
            sorted(member_id for member in members for member_id in member.member_ids)
        )
        jurisdiction = members[0].jurisdiction
        label_mode = members[0].label_mode
        quotient.append(
            CoverBlock(
                id="Q[" + ",".join(all_member_ids) + "]",
                jurisdiction=jurisdiction,
                group=group,
                label_mode=label_mode,
                label=label,
                support=support,
                member_ids=all_member_ids,
            )
        )
    return quotient


def refinement_result(
    source_blocks: Iterable[CoverBlock],
    target_blocks: Iterable[CoverBlock],
) -> dict[str, Any]:
    source = list(source_blocks)
    target = list(target_blocks)
    uncovered: list[dict[str, Any]] = []
    witnesses: list[dict[str, Any]] = []
    for block in source:
        compatible = [
            candidate
            for candidate in target
            if candidate.group == block.group
            and candidate.label == block.label
            and block.support <= candidate.support
        ]
        if compatible:
            compatible.sort(key=lambda candidate: (len(candidate.support), candidate.id))
            witness = compatible[0]
            witnesses.append(
                {
                    "source_block": block.id,
                    "target_block": witness.id,
                    "group": block.group,
                    "label": block.label,
                    "source_support_size": len(block.support),
                    "target_support_size": len(witness.support),
                }
            )
        else:
            same_label = [
                candidate
                for candidate in target
                if candidate.group == block.group and candidate.label == block.label
            ]
            uncovered.append(
                {
                    "source_block": block.id,
                    "member_ids": list(block.member_ids),
                    "group": block.group,
                    "label": block.label,
                    "support_size": len(block.support),
                    "same_label_target_count": len(same_label),
                    "largest_same_label_intersection": max(
                        (len(block.support & candidate.support) for candidate in same_label),
                        default=0,
                    ),
                }
            )
    return {
        "is_refinement": not uncovered,
        "source_block_count": len(source),
        "target_block_count": len(target),
        "covered_source_block_count": len(source) - len(uncovered),
        "uncovered_source_block_count": len(uncovered),
        "uncovered": uncovered,
        "witnesses": witnesses,
    }


def _select_cover(
    indexed: list[CoverBlock],
    cover_mode: CoverMode,
) -> list[CoverBlock]:
    if cover_mode == "indexed":
        return indexed
    if cover_mode == "quotient":
        return quotient_cover(indexed)
    raise ValueError(f"unsupported cover_mode: {cover_mode!r}")


def _cover_inventory(blocks: list[CoverBlock], unlabeled: list[str]) -> dict[str, Any]:
    by_group: dict[str, int] = {}
    by_label: dict[str, int] = {}
    for block in blocks:
        by_group[block.group] = by_group.get(block.group, 0) + 1
        by_label[block.typed_label] = by_label.get(block.typed_label, 0) + 1
    quotient = quotient_cover(blocks)
    return {
        "indexed_block_count": len(blocks),
        "quotient_block_count": len(quotient),
        "duplicate_support_label_blocks_collapsed": len(blocks) - len(quotient),
        "unlabeled_duty_count": len(unlabeled),
        "unlabeled_duty_ids": unlabeled,
        "indexed_blocks_by_group": dict(sorted(by_group.items())),
        "indexed_blocks_by_typed_label": dict(sorted(by_label.items())),
    }


def build_typed_cover_audit(
    policy_path: str | Path,
    duty_semantics_path: str | Path | None = None,
) -> dict[str, Any]:
    policies = load_policy_bundle(policy_path, duty_semantics_path)
    jurisdictions = sorted(policies)
    covers: dict[str, dict[str, list[CoverBlock]]] = {}
    inventories: dict[str, dict[str, Any]] = {}

    for label_mode in ("exact", "broad"):
        covers[label_mode] = {}
        inventories[label_mode] = {}
        for jurisdiction in jurisdictions:
            blocks, unlabeled = build_indexed_cover(
                policies[jurisdiction], label_mode=label_mode
            )
            covers[label_mode][jurisdiction] = blocks
            inventories[label_mode][jurisdiction] = _cover_inventory(blocks, unlabeled)

    matrices: dict[str, Any] = {}
    for label_mode in ("exact", "broad"):
        matrices[label_mode] = {}
        for cover_mode in ("indexed", "quotient"):
            directed: dict[str, Any] = {}
            for source_jurisdiction in jurisdictions:
                for target_jurisdiction in jurisdictions:
                    if source_jurisdiction == target_jurisdiction:
                        continue
                    source_blocks = _select_cover(
                        covers[label_mode][source_jurisdiction], cover_mode
                    )
                    target_blocks = _select_cover(
                        covers[label_mode][target_jurisdiction], cover_mode
                    )
                    key = f"{source_jurisdiction}->{target_jurisdiction}"
                    directed[key] = refinement_result(source_blocks, target_blocks)
            matrices[label_mode][cover_mode] = directed

    exact_results = matrices["exact"]["quotient"].values()
    exact_true = sum(result["is_refinement"] for result in exact_results)
    return {
        "schema_version": "1.0.0",
        "status": "FINITE_TYPED_COVER_ORACLE_COMPLETE",
        "context_count": 2880,
        "jurisdictions": jurisdictions,
        "label_modes": {
            "exact": "group plus normative_slot",
            "broad": "group plus alignment_key",
        },
        "cover_modes": {
            "indexed": "preserves every rule-duty identity, including equal supports",
            "quotient": "collapses blocks only when group, label, and support are equal",
        },
        "inventories": inventories,
        "matrices": matrices,
        "summary": {
            "directed_pair_count_per_matrix": len(jurisdictions) * (len(jurisdictions) - 1),
            "exact_quotient_refinements_true": exact_true,
            "exact_quotient_refinements_false": (
                len(jurisdictions) * (len(jurisdictions) - 1) - exact_true
            ),
        },
        "theorem_gate": {
            "legacy_H8": "WITHDRAW_AND_REPLACE_WITH_LABELED_TYPED_COVER",
            "legacy_Theorem_C_implementation_claim": (
                "NOT_IMPLEMENTED_BY_THIS_FINITE_ORACLE"
            ),
            "replacement_claim": (
                "For the finite frozen context space, directed refinement is decided by "
                "label-preserving support inclusion over indexed or quotient typed blocks."
            ),
        },
        "complexity": {
            "support_construction": "O(|Ctx| * |Rules|)",
            "refinement_worst_case": "O(|Blocks_A| * |Blocks_B| * |Ctx|)",
            "implementation_note": (
                "Python frozenset inclusion is used as a finite oracle. No symbolic "
                "O(|P_A||P_B|k) implementation is claimed."
            ),
        },
        "limitations": {
            "legal_label_review": "PENDING_INDEPENDENT_REVIEW",
            "current_law_profile": "NOT_YET_ENCODED",
            "symbolic_region_algorithm": "NOT_IMPLEMENTED",
            "notice": (
                "A false refinement may reflect real architectural divergence, an "
                "unresolved legal crosswalk, or incomplete labels. It is not by itself "
                "a legal conclusion."
            ),
        },
    }
