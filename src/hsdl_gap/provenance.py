from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MAXIMUM_BYTES = 150_000_000
PDF_MAGIC = b"%PDF-"
USER_AGENT = "HSDL-Harmonization-Gap/1.0 source-provenance"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ProvenanceError(ValueError):
    """Raised when a source target or acquired artifact violates the contract."""


def load_source_targets(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_source_targets(payload)
    return payload


def load_source_lock(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_source_lock(payload)
    return payload


def validate_source_targets(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ProvenanceError("unsupported source-target schema_version")

    policy = payload.get("policy")
    if not isinstance(policy, dict):
        raise ProvenanceError("policy must be an object")
    if policy.get("transport") != "https_only":
        raise ProvenanceError("only https_only transport is supported")
    if policy.get("hash_algorithm") != "sha256":
        raise ProvenanceError("only sha256 is supported")

    targets = payload.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ProvenanceError("targets must be a non-empty list")

    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    required_fields = {
        "id",
        "jurisdiction",
        "instrument",
        "official_pdf_url",
        "declared_page_count",
        "signature_profile",
        "required_for_current_claims",
    }
    for target in targets:
        if not isinstance(target, dict):
            raise ProvenanceError("each target must be an object")
        missing = sorted(required_fields - target.keys())
        if missing:
            raise ProvenanceError(
                f"target {target.get('id', '<unknown>')} missing fields: {missing}"
            )
        source_id = target["id"]
        url = target["official_pdf_url"]
        if not isinstance(source_id, str) or not source_id:
            raise ProvenanceError("target id must be a non-empty string")
        if source_id in seen_ids:
            raise ProvenanceError(f"duplicate target id: {source_id}")
        seen_ids.add(source_id)
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ProvenanceError(f"target {source_id} must use an https URL")
        if url in seen_urls:
            raise ProvenanceError(f"duplicate target URL: {url}")
        seen_urls.add(url)
        page_count = target["declared_page_count"]
        if not isinstance(page_count, int) or page_count <= 0:
            raise ProvenanceError(
                f"target {source_id} declared_page_count must be positive"
            )
        if not isinstance(target["required_for_current_claims"], bool):
            raise ProvenanceError(
                f"target {source_id} required_for_current_claims must be boolean"
            )


def validate_source_lock(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != "1.0.0":
        raise ProvenanceError("unsupported source-lock schema_version")
    if payload.get("hash_algorithm") != "sha256":
        raise ProvenanceError("source lock must use sha256")
    if payload.get("custody") != "HASH_ONLY_NOT_VENDORED":
        raise ProvenanceError("unsupported source-lock custody state")

    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ProvenanceError("source lock artifacts must be a non-empty list")

    required_fields = {
        "id",
        "official_pdf_url",
        "byte_size",
        "sha256",
        "declared_page_count",
        "signature_profile",
    }
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ProvenanceError("each locked artifact must be an object")
        missing = sorted(required_fields - artifact.keys())
        if missing:
            raise ProvenanceError(
                f"locked artifact {artifact.get('id', '<unknown>')} missing fields: {missing}"
            )
        source_id = artifact["id"]
        url = artifact["official_pdf_url"]
        if not isinstance(source_id, str) or not source_id:
            raise ProvenanceError("locked artifact id must be a non-empty string")
        if source_id in seen_ids:
            raise ProvenanceError(f"duplicate locked artifact id: {source_id}")
        seen_ids.add(source_id)
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ProvenanceError(
                f"locked artifact {source_id} must use an https URL"
            )
        if url in seen_urls:
            raise ProvenanceError(f"duplicate locked artifact URL: {url}")
        seen_urls.add(url)
        if not isinstance(artifact["byte_size"], int) or artifact["byte_size"] <= 0:
            raise ProvenanceError(
                f"locked artifact {source_id} byte_size must be positive"
            )
        digest = artifact["sha256"]
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            raise ProvenanceError(
                f"locked artifact {source_id} sha256 must be 64 lowercase hex characters"
            )
        if (
            not isinstance(artifact["declared_page_count"], int)
            or artifact["declared_page_count"] <= 0
        ):
            raise ProvenanceError(
                f"locked artifact {source_id} declared_page_count must be positive"
            )


def fingerprint_pdf_bytes(data: bytes) -> dict[str, Any]:
    if not data.startswith(PDF_MAGIC):
        raise ProvenanceError("artifact does not begin with PDF magic bytes")
    return {
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pdf_magic_verified": True,
    }


def _read_response_limited(response: Any, maximum_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > maximum_bytes:
            raise ProvenanceError(
                f"artifact exceeds maximum_bytes={maximum_bytes}"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def acquire_source(
    target: dict[str, Any], *, timeout_seconds: int, maximum_bytes: int
) -> dict[str, Any]:
    request = Request(
        target["official_pdf_url"],
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*;q=0.1",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        data = _read_response_limited(response, maximum_bytes)
        fingerprint = fingerprint_pdf_bytes(data)
        content_type = response.headers.get_content_type()
        return {
            "id": target["id"],
            "jurisdiction": target["jurisdiction"],
            "instrument": target["instrument"],
            "requested_url": target["official_pdf_url"],
            "final_url": response.geturl(),
            "http_status": getattr(response, "status", 200),
            "content_type": content_type,
            "declared_page_count": target["declared_page_count"],
            "page_count_evidence": "DECLARED_FROM_OFFICIAL_PDF_ENDPOINT_DISCOVERY_NOT_RECOUNTED",
            "signature_profile": target["signature_profile"],
            "required_for_current_claims": target["required_for_current_claims"],
            "artifact_custody": "HASH_ONLY_NOT_VENDORED",
            "visual_review_status": "NOT_PERFORMED_BY_ACQUISITION_RUNNER",
            **fingerprint,
        }


def build_source_provenance_report(
    targets_path: str | Path,
    *,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    payload = load_source_targets(targets_path)
    policy = payload["policy"]
    maximum_bytes = int(policy.get("maximum_bytes", DEFAULT_MAXIMUM_BYTES))
    artifacts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for target in payload["targets"]:
        try:
            artifacts.append(
                acquire_source(
                    target,
                    timeout_seconds=timeout_seconds,
                    maximum_bytes=maximum_bytes,
                )
            )
        except (HTTPError, URLError, OSError, ProvenanceError) as exc:
            errors.append(
                {
                    "id": str(target.get("id", "<unknown>")),
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    artifacts.sort(key=lambda item: item["id"])
    errors.sort(key=lambda item: item["id"])
    required_ids = {
        target["id"]
        for target in payload["targets"]
        if target["required_for_current_claims"]
    }
    acquired_ids = {artifact["id"] for artifact in artifacts}
    missing_required = sorted(required_ids - acquired_ids)

    return {
        "schema_version": "1.0.0",
        "freeze_date": payload["freeze_date"],
        "retrieved_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "status": "COMPLETE" if not errors and not missing_required else "INCOMPLETE",
        "target_count": len(payload["targets"]),
        "acquired_count": len(artifacts),
        "required_count": len(required_ids),
        "missing_required_ids": missing_required,
        "artifacts": artifacts,
        "errors": errors,
        "attestation": {
            "hash_algorithm": "sha256",
            "artifact_custody": "HASH_ONLY_NOT_VENDORED",
            "legal_review": "NOT_PERFORMED",
            "notice": policy["notice"],
        },
    }


def verify_provenance_report_against_lock(
    acquisition: dict[str, Any], lock: dict[str, Any]
) -> dict[str, Any]:
    validate_source_lock(lock)
    observed = {item["id"]: item for item in acquisition.get("artifacts", [])}
    expected = {item["id"]: item for item in lock["artifacts"]}
    artifact_results: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []

    for source_id in sorted(expected):
        locked = expected[source_id]
        actual = observed.get(source_id)
        if actual is None:
            mismatches.append(
                {"id": source_id, "field": "artifact", "expected": "present", "observed": "missing"}
            )
            artifact_results.append({"id": source_id, "status": "MISSING"})
            continue

        source_mismatches: list[dict[str, Any]] = []
        comparisons = {
            "official_pdf_url": (
                locked["official_pdf_url"],
                actual.get("requested_url"),
            ),
            "byte_size": (locked["byte_size"], actual.get("byte_size")),
            "sha256": (locked["sha256"], actual.get("sha256")),
            "declared_page_count": (
                locked["declared_page_count"],
                actual.get("declared_page_count"),
            ),
            "signature_profile": (
                locked["signature_profile"],
                actual.get("signature_profile"),
            ),
        }
        for field, (expected_value, observed_value) in comparisons.items():
            if expected_value != observed_value:
                mismatch = {
                    "id": source_id,
                    "field": field,
                    "expected": expected_value,
                    "observed": observed_value,
                }
                source_mismatches.append(mismatch)
                mismatches.append(mismatch)
        artifact_results.append(
            {
                "id": source_id,
                "status": "VERIFIED" if not source_mismatches else "DRIFT",
                "sha256": actual.get("sha256"),
                "byte_size": actual.get("byte_size"),
                "mismatches": source_mismatches,
            }
        )

    unexpected_ids = sorted(set(observed) - set(expected))
    for source_id in unexpected_ids:
        mismatches.append(
            {
                "id": source_id,
                "field": "artifact",
                "expected": "not present in lock",
                "observed": "unexpected acquired artifact",
            }
        )

    acquisition_errors = acquisition.get("errors", [])
    verified = (
        acquisition.get("status") == "COMPLETE"
        and not acquisition_errors
        and not mismatches
    )
    return {
        "schema_version": "1.0.0",
        "lock_id": lock["lock_id"],
        "lock_freeze_date": lock["freeze_date"],
        "verified_at_utc": acquisition.get("retrieved_at_utc"),
        "status": "VERIFIED" if verified else "FAILED",
        "locked_artifact_count": len(expected),
        "observed_artifact_count": len(observed),
        "artifact_results": artifact_results,
        "unexpected_ids": unexpected_ids,
        "mismatches": mismatches,
        "acquisition_errors": acquisition_errors,
        "custody": lock["custody"],
        "review_gates": lock["review_gates"],
        "notice": lock["notice"],
    }


def build_source_verification_report(
    targets_path: str | Path,
    lock_path: str | Path,
    *,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    acquisition = build_source_provenance_report(
        targets_path, timeout_seconds=timeout_seconds
    )
    lock = load_source_lock(lock_path)
    verification = verify_provenance_report_against_lock(acquisition, lock)
    return {
        "schema_version": "1.0.0",
        "status": verification["status"],
        "verification": verification,
        "acquisition": acquisition,
    }
