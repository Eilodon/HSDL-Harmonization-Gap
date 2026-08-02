from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .stable_id import content_sha256


class ClaimLedgerError(ValueError):
    """Raised when a claim ledger or evidence reference is invalid."""


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClaimLedgerError(f"{label} is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ClaimLedgerError(f"{label} is invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ClaimLedgerError(f"{label} must be a JSON object: {path}")
    return payload


def resolve_json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ClaimLedgerError(f"JSON Pointer must begin with '/': {pointer!r}")
    current = document
    for raw_token in pointer.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                raise ClaimLedgerError(
                    f"JSON Pointer {pointer!r} does not resolve: missing key {token!r}"
                )
            current = current[token]
        elif isinstance(current, list):
            if token == "-":
                raise ClaimLedgerError("'-' is not valid for read-only JSON Pointer")
            try:
                index = int(token)
            except ValueError as exc:
                raise ClaimLedgerError(
                    f"JSON Pointer {pointer!r} has non-integer array token {token!r}"
                ) from exc
            if index < 0 or index >= len(current):
                raise ClaimLedgerError(
                    f"JSON Pointer {pointer!r} array index is out of range"
                )
            current = current[index]
        else:
            raise ClaimLedgerError(
                f"JSON Pointer {pointer!r} descends through a scalar value"
            )
    return current


def _safe_artifact_path(root: Path, filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise ClaimLedgerError(
            f"artifact names must be plain filenames without directories: {filename!r}"
        )
    return root / filename


def build_claim_ledger_report(
    *,
    ledger_path: str | Path = "claims/model_relative_claims.json",
    artifact_dir: str | Path = "generated",
) -> dict[str, Any]:
    ledger_file = Path(ledger_path)
    artifact_root = Path(artifact_dir)
    ledger = _load_json_object(ledger_file, label="claim ledger")
    if ledger.get("claim_class") != "MODEL_RELATIVE":
        raise ClaimLedgerError("claim ledger must use MODEL_RELATIVE claim class")
    if ledger.get("legal_validation") != "NOT_ASSERTED":
        raise ClaimLedgerError("claim ledger must not assert legal validation")
    ledger_id = ledger.get("ledger_id")
    if not isinstance(ledger_id, str) or not ledger_id:
        raise ClaimLedgerError("claim ledger ID must be non-empty")
    raw_claims = ledger.get("claims")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ClaimLedgerError("claim ledger must contain at least one claim")

    seen_claim_ids: set[str] = set()
    artifact_cache: dict[str, dict[str, Any]] = {}
    evidence_hashes: dict[str, str] = {}
    claim_results: list[dict[str, Any]] = []
    mismatch_count = 0
    evidence_count = 0

    for claim_index, raw_claim in enumerate(raw_claims):
        if not isinstance(raw_claim, dict):
            raise ClaimLedgerError(f"claims[{claim_index}] must be an object")
        claim_id = raw_claim.get("claim_id")
        text = raw_claim.get("text")
        evidence = raw_claim.get("evidence")
        if not isinstance(claim_id, str) or not claim_id:
            raise ClaimLedgerError(f"claims[{claim_index}].claim_id must be non-empty")
        if claim_id in seen_claim_ids:
            raise ClaimLedgerError(f"duplicate claim ID: {claim_id}")
        seen_claim_ids.add(claim_id)
        if not isinstance(text, str) or not text:
            raise ClaimLedgerError(f"claim {claim_id} text must be non-empty")
        if not isinstance(evidence, list) or not evidence:
            raise ClaimLedgerError(f"claim {claim_id} must contain evidence")

        evidence_results: list[dict[str, Any]] = []
        for evidence_index, raw_item in enumerate(evidence):
            if not isinstance(raw_item, dict):
                raise ClaimLedgerError(
                    f"claim {claim_id} evidence[{evidence_index}] must be an object"
                )
            artifact = raw_item.get("artifact")
            pointer = raw_item.get("pointer")
            if not isinstance(artifact, str):
                raise ClaimLedgerError(
                    f"claim {claim_id} evidence[{evidence_index}].artifact must be a string"
                )
            if not isinstance(pointer, str):
                raise ClaimLedgerError(
                    f"claim {claim_id} evidence[{evidence_index}].pointer must be a string"
                )
            if "expected" not in raw_item:
                raise ClaimLedgerError(
                    f"claim {claim_id} evidence[{evidence_index}] must declare expected"
                )
            if artifact not in artifact_cache:
                path = _safe_artifact_path(artifact_root, artifact)
                artifact_cache[artifact] = _load_json_object(
                    path, label=f"evidence artifact {artifact}"
                )
                evidence_hashes[artifact] = content_sha256(artifact_cache[artifact])
            actual = resolve_json_pointer(artifact_cache[artifact], pointer)
            expected = raw_item["expected"]
            matches = actual == expected
            evidence_count += 1
            if not matches:
                mismatch_count += 1
            evidence_results.append(
                {
                    "artifact": artifact,
                    "artifact_sha256": evidence_hashes[artifact],
                    "pointer": pointer,
                    "expected": expected,
                    "actual": actual,
                    "matches": matches,
                }
            )
        claim_results.append(
            {
                "claim_id": claim_id,
                "text": text,
                "supported": all(item["matches"] for item in evidence_results),
                "evidence": evidence_results,
            }
        )

    supported_count = sum(item["supported"] for item in claim_results)
    return {
        "schema_version": "1.0.0",
        "status": (
            "CLAIM_LEDGER_VALIDATED" if mismatch_count == 0 else "CLAIM_LEDGER_STALE"
        ),
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "ledger_id": ledger_id,
        "ledger_hash": content_sha256(ledger),
        "artifact_directory": artifact_root.as_posix(),
        "claim_count": len(claim_results),
        "supported_claim_count": supported_count,
        "unsupported_claim_count": len(claim_results) - supported_count,
        "evidence_reference_count": evidence_count,
        "evidence_mismatch_count": mismatch_count,
        "artifact_hashes": dict(sorted(evidence_hashes.items())),
        "claims": claim_results,
        "boundary": {
            "legal_validation": "NOT_ASSERTED",
            "empirical_prevalence": "NOT_SUPPORTED",
            "publication_authorisation": "NOT_PROVIDED",
            "notice": (
                "A validated ledger proves that claim text is consistent with declared "
                "artifact values. It does not establish legal validity or empirical scope."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="claims/model_relative_claims.json")
    parser.add_argument("--artifact-dir", default="generated")
    args = parser.parse_args()
    report = build_claim_ledger_report(
        ledger_path=args.ledger,
        artifact_dir=args.artifact_dir,
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if report["status"] != "CLAIM_LEDGER_VALIDATED":
        raise SystemExit(17)


if __name__ == "__main__":
    main()
