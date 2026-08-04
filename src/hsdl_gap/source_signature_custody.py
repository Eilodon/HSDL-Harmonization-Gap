from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from .provenance import DEFAULT_MAXIMUM_BYTES, load_source_lock, load_source_targets
from .source_transport import SourceTransportError, fetch_declared_pdf
from .stable_id import content_sha256


class SourceCustodyError(ValueError):
    """Raised when signature or custody evidence violates its contract."""


@dataclass(frozen=True, slots=True)
class ParsedPDFSignature:
    signature_number: int
    field_name: str | None
    signer_common_name: str | None
    signing_time: str | None
    signature_validation: str | None
    certificate_validation: str | None

    @property
    def cryptographic_integrity_valid(self) -> bool | None:
        if self.signature_validation is None:
            return None
        normalized = self.signature_validation.lower()
        if "signature is valid" in normalized:
            return True
        if "signature is invalid" in normalized or "digest mismatch" in normalized:
            return False
        return None

    @property
    def certificate_trusted(self) -> bool | None:
        if self.certificate_validation is None:
            return None
        normalized = self.certificate_validation.lower()
        if "certificate is trusted" in normalized:
            return True
        if "isn't trusted" in normalized or "not trusted" in normalized:
            return False
        return None

    def as_mapping(self) -> dict[str, Any]:
        return {
            "signature_number": self.signature_number,
            "field_name": self.field_name,
            "signer_common_name": self.signer_common_name,
            "signing_time": self.signing_time,
            "signature_validation": self.signature_validation,
            "certificate_validation": self.certificate_validation,
            "cryptographic_integrity_valid": self.cryptographic_integrity_valid,
            "certificate_trusted": self.certificate_trusted,
        }


def _load_json(path: str | Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceCustodyError(f"cannot load {label}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceCustodyError(f"{label} must be a JSON object")
    return payload


def _clean_pdfsig_value(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("-") or ":" not in stripped:
        return None
    key, value = stripped[1:].split(":", 1)
    return key.strip(), value.strip()


def parse_pdfsig_output(output: str) -> tuple[ParsedPDFSignature, ...]:
    """Parse the stable human-readable fields emitted by Poppler's pdfsig.

    Unknown fields are ignored. Absence of a ``Signature #N`` heading means the PDF
    contains no embedded signatures, including pdfsig's explicit no-signature message.
    """
    signatures: list[ParsedPDFSignature] = []
    current_number: int | None = None
    current: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_number, current
        if current_number is None:
            return
        signatures.append(
            ParsedPDFSignature(
                signature_number=current_number,
                field_name=current.get("Signature Field Name"),
                signer_common_name=current.get("Signer Certificate Common Name"),
                signing_time=current.get("Signing Time"),
                signature_validation=current.get("Signature Validation"),
                certificate_validation=current.get("Certificate Validation"),
            )
        )
        current_number = None
        current = {}

    for raw_line in output.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("Signature #") and stripped.endswith(":"):
            flush()
            raw_number = stripped[len("Signature #") : -1]
            try:
                current_number = int(raw_number)
            except ValueError as exc:
                raise SourceCustodyError(
                    f"invalid pdfsig signature heading: {stripped!r}"
                ) from exc
            continue
        item = _clean_pdfsig_value(raw_line)
        if item is not None and current_number is not None:
            key, value = item
            current[key] = value
    flush()
    return tuple(signatures)


def run_pdfsig(pdf_path: str | Path, *, executable: str = "pdfsig") -> dict[str, Any]:
    resolved = shutil.which(executable)
    if resolved is None:
        raise SourceCustodyError(f"pdfsig executable is unavailable: {executable}")
    completed = subprocess.run(
        [resolved, str(pdf_path)],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    combined = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    )
    signatures = parse_pdfsig_output(combined)
    return {
        "tool": "pdfsig",
        "tool_path": resolved,
        "exit_code": completed.returncode,
        "signature_count": len(signatures),
        "signatures": [signature.as_mapping() for signature in signatures],
        "raw_output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "raw_output": combined,
    }


def classify_signature_result(
    *,
    signature_profile: str,
    profile_policy: Mapping[str, Any],
    pdfsig_report: Mapping[str, Any],
) -> dict[str, Any]:
    expectation = profile_policy.get("embedded_signature_expectation")
    if expectation not in {"REQUIRED", "NOT_REQUIRED"}:
        raise SourceCustodyError(
            f"unsupported embedded signature expectation for {signature_profile}"
        )
    signatures = pdfsig_report.get("signatures")
    if not isinstance(signatures, list):
        raise SourceCustodyError("pdfsig report signatures must be an array")
    count = len(signatures)
    integrity_values = [item.get("cryptographic_integrity_valid") for item in signatures]
    trust_values = [item.get("certificate_trusted") for item in signatures]

    if pdfsig_report.get("exit_code") not in {0, 2}:
        status = "PDFSIG_TOOL_ERROR"
    elif count == 0 and expectation == "REQUIRED":
        status = "EXPECTED_EMBEDDED_SIGNATURE_MISSING"
    elif count == 0:
        status = "NO_EMBEDDED_SIGNATURE_NOT_REQUIRED"
    elif False in integrity_values:
        status = "EMBEDDED_SIGNATURE_INVALID"
    elif all(value is True for value in integrity_values):
        status = (
            "EMBEDDED_SIGNATURE_VALID_TRUSTED"
            if all(value is True for value in trust_values)
            else "EMBEDDED_SIGNATURE_VALID_TRUST_CHAIN_UNRESOLVED"
        )
    else:
        status = "EMBEDDED_SIGNATURE_PRESENT_INTEGRITY_UNRESOLVED"

    policy_passed = status in {
        "NO_EMBEDDED_SIGNATURE_NOT_REQUIRED",
        "EMBEDDED_SIGNATURE_VALID_TRUSTED",
        "EMBEDDED_SIGNATURE_VALID_TRUST_CHAIN_UNRESOLVED",
    }
    return {
        "signature_profile": signature_profile,
        "embedded_signature_expectation": expectation,
        "status": status,
        "policy_passed": policy_passed,
        "signature_count": count,
        "all_integrity_valid": bool(signatures) and all(
            value is True for value in integrity_values
        ),
        "all_certificate_chains_trusted": bool(signatures) and all(
            value is True for value in trust_values
        ),
        "trust_chain_resolution_required": bool(signatures)
        and not all(value is True for value in trust_values),
        "notice": profile_policy.get("notice"),
    }


def _safe_filename(source_id: str) -> str:
    if not source_id or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for character in source_id):
        raise SourceCustodyError(f"unsafe source ID: {source_id!r}")
    return f"{source_id}.pdf"


def _write_content_addressed_object(
    object_root: Path, data: bytes, expected_sha256: str
) -> str:
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha256:
        raise SourceCustodyError(
            f"content-addressed object hash mismatch: {digest} != {expected_sha256}"
        )
    relative = Path("objects") / "sha256" / digest[:2] / digest
    destination = object_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return relative.as_posix()


def build_signature_and_deposit_staging_report(
    *,
    targets_path: str | Path,
    lock_path: str | Path,
    policy_path: str | Path,
    output_dir: str | Path,
    timeout_seconds: int = 90,
    pdfsig_executable: str = "pdfsig",
) -> dict[str, Any]:
    targets = load_source_targets(targets_path)
    lock = load_source_lock(lock_path)
    policy = _load_json(policy_path, label="signature and deposit policy")
    profile_policies = policy.get("signature_profiles")
    if not isinstance(profile_policies, dict):
        raise SourceCustodyError("signature_profiles must be an object")
    locked = {item["id"]: item for item in lock["artifacts"]}
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict[str, Any]] = []
    source_reports: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    maximum_bytes = int(
        targets["policy"].get("maximum_bytes", DEFAULT_MAXIMUM_BYTES)
    )

    with tempfile.TemporaryDirectory(prefix="hsdl-source-signature-") as temp_dir:
        temp_root = Path(temp_dir)
        for target in targets["targets"]:
            source_id = target["id"]
            expected = locked.get(source_id)
            if expected is None:
                errors.append(
                    {
                        "id": source_id,
                        "error_type": "SOURCE_LOCK_MISSING",
                        "message": "source target is absent from the pinned lock",
                    }
                )
                continue
            signature_profile = target["signature_profile"]
            profile_policy = profile_policies.get(signature_profile)
            if not isinstance(profile_policy, dict):
                errors.append(
                    {
                        "id": source_id,
                        "error_type": "SIGNATURE_PROFILE_POLICY_MISSING",
                        "message": f"no policy for {signature_profile}",
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
                pdf_path = temp_root / _safe_filename(source_id)
                pdf_path.write_bytes(result.data)
                pdfsig_report = run_pdfsig(
                    pdf_path, executable=pdfsig_executable
                )
                classification = classify_signature_result(
                    signature_profile=signature_profile,
                    profile_policy=profile_policy,
                    pdfsig_report=pdfsig_report,
                )
                object_path = _write_content_addressed_object(
                    root, result.data, expected["sha256"]
                )
                manifest_entries.append(
                    {
                        "id": source_id,
                        "object_path": object_path,
                        "sha256": expected["sha256"],
                        "byte_size": expected["byte_size"],
                        "media_type": "application/pdf",
                        "canonical_url": target["official_pdf_url"],
                        "transport_url_used": result.transport_url_used,
                        "signature_profile": signature_profile,
                    }
                )
                source_reports.append(
                    {
                        "id": source_id,
                        "instrument": target["instrument"],
                        "jurisdiction": target["jurisdiction"],
                        "source_identity_verified": True,
                        "sha256": expected["sha256"],
                        "byte_size": expected["byte_size"],
                        "signature_classification": classification,
                        "pdfsig": pdfsig_report,
                    }
                )
            except (OSError, SourceTransportError, SourceCustodyError) as exc:
                errors.append(
                    {
                        "id": source_id,
                        "error_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )

    manifest_entries.sort(key=lambda item: item["id"])
    source_reports.sort(key=lambda item: item["id"])
    errors.sort(key=lambda item: item["id"])
    manifest = {
        "schema_version": "1.0.0",
        "manifest_id": "official-source-deposit-staging-2026-08-02",
        "source_lock_id": lock["lock_id"],
        "object_count": len(manifest_entries),
        "objects": manifest_entries,
        "source_lock_sha256": content_sha256(lock),
        "signature_policy_sha256": content_sha256(policy),
    }
    manifest_path = root / "deposit-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    signature_policy_passed = bool(source_reports) and all(
        item["signature_classification"]["policy_passed"]
        for item in source_reports
    )
    complete = (
        len(source_reports) == len(targets["targets"])
        and not errors
        and signature_policy_passed
    )
    return {
        "schema_version": "1.0.0",
        "status": (
            "DEPOSIT_PACKAGE_STAGED_SIGNATURE_POLICY_PASSED"
            if complete
            else "DEPOSIT_PACKAGE_STAGING_INCOMPLETE"
        ),
        "claim_class": "SOURCE_IDENTITY_AND_CUSTODY",
        "legal_validation": "NOT_ASSERTED",
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "target_count": len(targets["targets"]),
        "verified_source_count": len(source_reports),
        "manifest_sha256": manifest_sha256,
        "manifest_path": manifest_path.as_posix(),
        "sources": source_reports,
        "errors": errors,
        "signature_policy_passed": signature_policy_passed,
        "external_deposit": {
            "status": "READY_FOR_EXTERNAL_DEPOSIT" if complete else "NOT_READY",
            "receipt_verified": False,
            "durable_custody_established": False,
            "acceptable_provider_classes": policy["external_deposit"][
                "acceptable_provider_classes"
            ],
            "notice": policy["external_deposit"]["notice"],
        },
    }


def _validate_persistent_url(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise SourceCustodyError("persistent_url must be a non-empty string")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SourceCustodyError("persistent_url must be an absolute HTTPS URL")
    return value


def verify_external_deposit_receipt(
    *,
    manifest_path: str | Path,
    receipt_path: str | Path,
    policy_path: str | Path,
) -> dict[str, Any]:
    manifest = _load_json(manifest_path, label="deposit manifest")
    receipt = _load_json(receipt_path, label="external deposit receipt")
    policy = _load_json(policy_path, label="signature and deposit policy")
    required = policy["external_deposit"]["required_receipt_fields"]
    missing = [field for field in required if field not in receipt]
    if missing:
        raise SourceCustodyError(f"deposit receipt is missing fields: {missing}")
    provider = receipt["provider"]
    if provider not in policy["external_deposit"]["acceptable_provider_classes"]:
        raise SourceCustodyError(f"unsupported external deposit provider: {provider}")
    _validate_persistent_url(receipt["persistent_url"])
    manifest_digest = hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()
    if receipt["manifest_sha256"] != manifest_digest:
        raise SourceCustodyError("deposit receipt manifest hash does not match")
    object_receipts = receipt["object_receipts"]
    if not isinstance(object_receipts, list):
        raise SourceCustodyError("object_receipts must be an array")
    receipt_by_id = {
        item.get("id"): item for item in object_receipts if isinstance(item, dict)
    }
    mismatches: list[dict[str, Any]] = []
    for expected in manifest.get("objects", []):
        actual = receipt_by_id.get(expected["id"])
        if actual is None:
            mismatches.append(
                {"id": expected["id"], "reason": "OBJECT_RECEIPT_MISSING"}
            )
            continue
        for field in ("sha256", "byte_size"):
            if actual.get(field) != expected[field]:
                mismatches.append(
                    {
                        "id": expected["id"],
                        "reason": f"{field.upper()}_MISMATCH",
                        "expected": expected[field],
                        "actual": actual.get(field),
                    }
                )
    return {
        "schema_version": "1.0.0",
        "status": (
            "EXTERNAL_DURABLE_CUSTODY_RECEIPT_VERIFIED"
            if not mismatches
            else "EXTERNAL_DURABLE_CUSTODY_RECEIPT_MISMATCH"
        ),
        "provider": provider,
        "deposit_id": receipt["deposit_id"],
        "persistent_identifier": receipt["persistent_identifier"],
        "persistent_url": receipt["persistent_url"],
        "manifest_sha256": manifest_digest,
        "object_count": len(manifest.get("objects", [])),
        "object_receipt_count": len(object_receipts),
        "mismatches": mismatches,
        "durable_custody_established": not mismatches,
        "receipt_hash": content_sha256(receipt),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("stage", "verify-receipt"), default="stage"
    )
    parser.add_argument("--targets", default="sources/official_pdf_targets.json")
    parser.add_argument(
        "--lock", default="sources/official_pdf_lock_2026-08-02.json"
    )
    parser.add_argument(
        "--policy", default="sources/custody/signature_and_deposit_policy.json"
    )
    parser.add_argument(
        "--output-dir", default="generated/source-custody-staging"
    )
    parser.add_argument("--manifest")
    parser.add_argument("--receipt")
    args = parser.parse_args()
    if args.mode == "stage":
        report = build_signature_and_deposit_staging_report(
            targets_path=args.targets,
            lock_path=args.lock,
            policy_path=args.policy,
            output_dir=args.output_dir,
        )
    else:
        if not args.manifest or not args.receipt:
            parser.error("verify-receipt requires --manifest and --receipt")
        report = verify_external_deposit_receipt(
            manifest_path=args.manifest,
            receipt_path=args.receipt,
            policy_path=args.policy,
        )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if args.mode == "verify-receipt" and not report["durable_custody_established"]:
        raise SystemExit(31)


if __name__ == "__main__":
    main()
