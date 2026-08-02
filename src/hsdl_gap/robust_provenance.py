from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .provenance import (
    DEFAULT_MAXIMUM_BYTES,
    load_source_lock,
    load_source_targets,
    verify_provenance_report_against_lock,
)
from .source_transport import SourceTransportError, fetch_declared_pdf


def _artifact_record(target: dict[str, Any], result: Any) -> dict[str, Any]:
    data = result.data
    return {
        "id": target["id"],
        "jurisdiction": target["jurisdiction"],
        "instrument": target["instrument"],
        "requested_url": target["official_pdf_url"],
        "transport_url_used": result.transport_url_used,
        "final_url": result.final_url,
        "transport_attempt_number": result.attempt_number,
        "http_status": result.http_status,
        "content_type": result.content_type,
        "declared_page_count": target["declared_page_count"],
        "page_count_evidence": "DECLARED_FROM_OFFICIAL_PDF_ENDPOINT_DISCOVERY_NOT_RECOUNTED",
        "signature_profile": target["signature_profile"],
        "required_for_current_claims": target["required_for_current_claims"],
        "artifact_custody": "HASH_ONLY_NOT_VENDORED",
        "visual_review_status": "NOT_PERFORMED_BY_ACQUISITION_RUNNER",
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "pdf_magic_verified": True,
    }


def build_source_provenance_report(
    targets_path: str | Path,
    *,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    payload = load_source_targets(targets_path)
    maximum_bytes = int(
        payload["policy"].get("maximum_bytes", DEFAULT_MAXIMUM_BYTES)
    )
    artifacts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for target in payload["targets"]:
        try:
            result = fetch_declared_pdf(
                target,
                timeout_seconds=timeout_seconds,
                maximum_bytes=maximum_bytes,
            )
            artifacts.append(_artifact_record(target, result))
        except (OSError, SourceTransportError) as exc:
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
            "transport_fallbacks_change_identity": False,
            "legal_review": "NOT_PERFORMED",
            "notice": payload["policy"]["notice"],
        },
    }


def build_source_verification_report(
    targets_path: str | Path,
    lock_path: str | Path,
    *,
    timeout_seconds: int = 90,
) -> dict[str, Any]:
    targets = load_source_targets(targets_path)
    lock = load_source_lock(lock_path)
    locked = {artifact["id"]: artifact for artifact in lock["artifacts"]}
    maximum_bytes = int(
        targets["policy"].get("maximum_bytes", DEFAULT_MAXIMUM_BYTES)
    )
    artifacts: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for target in targets["targets"]:
        expected = locked.get(target["id"])
        if expected is None:
            errors.append(
                {
                    "id": target["id"],
                    "error_type": "SourceTransportError",
                    "message": "target is absent from source lock",
                }
            )
            continue
        transport_record = dict(target)
        if "alternate_official_pdf_urls" not in transport_record:
            transport_record["alternate_official_pdf_urls"] = expected.get(
                "alternate_official_pdf_urls", []
            )
        try:
            result = fetch_declared_pdf(
                transport_record,
                timeout_seconds=timeout_seconds,
                maximum_bytes=maximum_bytes,
                expected_sha256=expected["sha256"],
                expected_byte_size=expected["byte_size"],
            )
            artifacts.append(_artifact_record(target, result))
        except (OSError, SourceTransportError) as exc:
            errors.append(
                {
                    "id": target["id"],
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    required_ids = {
        target["id"]
        for target in targets["targets"]
        if target["required_for_current_claims"]
    }
    acquired_ids = {artifact["id"] for artifact in artifacts}
    acquisition = {
        "schema_version": "1.0.0",
        "freeze_date": targets["freeze_date"],
        "retrieved_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "status": (
            "COMPLETE"
            if not errors and required_ids <= acquired_ids
            else "INCOMPLETE"
        ),
        "target_count": len(targets["targets"]),
        "acquired_count": len(artifacts),
        "required_count": len(required_ids),
        "missing_required_ids": sorted(required_ids - acquired_ids),
        "artifacts": sorted(artifacts, key=lambda item: item["id"]),
        "errors": sorted(errors, key=lambda item: item["id"]),
        "attestation": {
            "hash_algorithm": "sha256",
            "artifact_custody": "HASH_ONLY_NOT_VENDORED",
            "transport_fallbacks_change_identity": False,
            "identity_enforced_during_fetch": True,
            "legal_review": "NOT_PERFORMED",
            "notice": targets["policy"]["notice"],
        },
    }
    verification = verify_provenance_report_against_lock(acquisition, lock)
    return {
        "schema_version": "1.0.0",
        "status": verification["status"],
        "verification": verification,
        "acquisition": acquisition,
    }
