from __future__ import annotations

import json
from pathlib import Path

from .context import iter_legacy_contexts
from .loader import load_policy_bundle
from .metrics import GROUPS, directional_gap_set, obligor_gap_set


def build_legacy_report(policy_path: str | Path) -> dict[str, object]:
    policies = load_policy_bundle(policy_path)
    contexts = tuple(iter_legacy_contexts())
    report: dict[str, object] = {"context_count": len(contexts), "groups": {}}
    unions = {
        "EU_gt_VN": set(),
        "VN_gt_EU": set(),
        "EU_gt_ASEAN": set(),
        "VN_gt_ASEAN": set(),
        "obligor_gap_EU_VN": set(),
    }
    for group in GROUPS:
        eu_vn = directional_gap_set(contexts, policies["EU"], policies["VN"], group)
        vn_eu = directional_gap_set(contexts, policies["VN"], policies["EU"], group)
        eu_as = directional_gap_set(contexts, policies["EU"], policies["ASEAN"], group)
        vn_as = directional_gap_set(contexts, policies["VN"], policies["ASEAN"], group)
        omega = obligor_gap_set(contexts, policies["EU"], policies["VN"], group)
        report["groups"][group] = {
            "EU_gt_VN": len(eu_vn),
            "VN_gt_EU": len(vn_eu),
            "EU_gt_ASEAN": len(eu_as),
            "VN_gt_ASEAN": len(vn_as),
            "obligor_gap_EU_VN": len(omega),
        }
        unions["EU_gt_VN"] |= eu_vn
        unions["VN_gt_EU"] |= vn_eu
        unions["EU_gt_ASEAN"] |= eu_as
        unions["VN_gt_ASEAN"] |= vn_as
        unions["obligor_gap_EU_VN"] |= omega
    report["unions"] = {name: len(values) for name, values in unions.items()}
    return report


def write_legacy_report(policy_path: str | Path, output_path: str | Path) -> None:
    Path(output_path).write_text(
        json.dumps(build_legacy_report(policy_path), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
