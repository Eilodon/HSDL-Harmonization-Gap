from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_MAXIMUM_BYTES = 150_000_000
PDF_MAGIC = b"%PDF-"
USER_AGENT = "HSDL-Harmonization-Gap/1.0 source-provenance"


class ProvenanceError(ValueError):
    """Raised when a source target or acquired artifact violates the contract."""


def load_source_targets(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_source_targets(payload)
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
