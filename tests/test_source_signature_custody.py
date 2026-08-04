from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hsdl_gap.source_signature_custody import (
    SourceCustodyError,
    build_signature_and_deposit_staging_report,
    classify_signature_result,
    parse_pdfsig_output,
    verify_external_deposit_receipt,
)


VALID_TRUSTED = """Digital Signature Info of: sample.pdf
Signature #1:
  - Signature Field Name: Signature1
  - Signer Certificate Common Name: Government Authority
  - Signing Time: Jul 01 2026 10:00:00
  - Signature Validation: Signature is Valid.
  - Certificate Validation: Certificate is Trusted.
"""

VALID_UNTRUSTED = """Digital Signature Info of: sample.pdf
Signature #1:
  - Signature Field Name: Signature1
  - Signer Certificate Common Name: Government Authority
  - Signature Validation: Signature is Valid.
  - Certificate Validation: Certificate issuer isn't Trusted.
"""

INVALID_SIGNATURE = """Digital Signature Info of: sample.pdf
Signature #1:
  - Signature Field Name: Signature1
  - Signature Validation: Signature is Invalid.
  - Certificate Validation: Certificate issuer isn't Trusted.
"""

NO_SIGNATURE = "File 'sample.pdf' does not contain any signatures\n"


class SourceSignatureCustodyTests(unittest.TestCase):
    def test_pdfsig_parser_preserves_integrity_and_trust_separately(self) -> None:
        trusted = parse_pdfsig_output(VALID_TRUSTED)
        self.assertEqual(len(trusted), 1)
        self.assertTrue(trusted[0].cryptographic_integrity_valid)
        self.assertTrue(trusted[0].certificate_trusted)
        untrusted = parse_pdfsig_output(VALID_UNTRUSTED)
        self.assertTrue(untrusted[0].cryptographic_integrity_valid)
        self.assertFalse(untrusted[0].certificate_trusted)
        invalid = parse_pdfsig_output(INVALID_SIGNATURE)
        self.assertFalse(invalid[0].cryptographic_integrity_valid)

    def test_no_signature_output_is_empty_inventory(self) -> None:
        self.assertEqual(parse_pdfsig_output(NO_SIGNATURE), ())

    def test_required_signature_policy_accepts_valid_untrusted_chain(self) -> None:
        report = classify_signature_result(
            signature_profile="government_portal_signed_pdf",
            profile_policy={
                "embedded_signature_expectation": "REQUIRED",
                "notice": "test",
            },
            pdfsig_report={
                "exit_code": 0,
                "signatures": [
                    {
                        "cryptographic_integrity_valid": True,
                        "certificate_trusted": False,
                    }
                ],
            },
        )
        self.assertEqual(
            report["status"],
            "EMBEDDED_SIGNATURE_VALID_TRUST_CHAIN_UNRESOLVED",
        )
        self.assertTrue(report["policy_passed"])
        self.assertTrue(report["trust_chain_resolution_required"])

    def test_required_signature_policy_rejects_missing_or_invalid(self) -> None:
        policy = {"embedded_signature_expectation": "REQUIRED"}
        missing = classify_signature_result(
            signature_profile="government_portal_signed_pdf",
            profile_policy=policy,
            pdfsig_report={"exit_code": 2, "signatures": []},
        )
        self.assertEqual(
            missing["status"], "EXPECTED_EMBEDDED_SIGNATURE_MISSING"
        )
        self.assertFalse(missing["policy_passed"])
        invalid = classify_signature_result(
            signature_profile="government_portal_signed_pdf",
            profile_policy=policy,
            pdfsig_report={
                "exit_code": 1,
                "signatures": [
                    {
                        "cryptographic_integrity_valid": False,
                        "certificate_trusted": False,
                    }
                ],
            },
        )
        self.assertFalse(invalid["policy_passed"])

    def test_non_required_profile_accepts_absent_signature(self) -> None:
        report = classify_signature_result(
            signature_profile="official_journal_pdf",
            profile_policy={"embedded_signature_expectation": "NOT_REQUIRED"},
            pdfsig_report={"exit_code": 2, "signatures": []},
        )
        self.assertEqual(
            report["status"], "NO_EMBEDDED_SIGNATURE_NOT_REQUIRED"
        )
        self.assertTrue(report["policy_passed"])

    def test_staging_builds_six_content_addressed_objects(self) -> None:
        source_ids = [
            "ASEAN_GENAI_GUIDE_2025",
            "ASEAN_GUIDE_2024",
            "EU_AI_ACT_2024_1689",
            "VN_DECISION_33_2026",
            "VN_DECREE_142_2026",
            "VN_LAW_134_2025",
        ]
        pdf_bytes = {
            source_id: f"%PDF-1.7\n{source_id}\n%%EOF\n".encode("ascii")
            for source_id in source_ids
        }
        targets = {
            "schema_version": "1.0.0",
            "freeze_date": "2026-08-02",
            "policy": {
                "transport": "https_only",
                "hash_algorithm": "sha256",
                "maximum_bytes": 1000000,
                "notice": "test fixture",
            },
            "targets": [],
        }
        lock = {
            "schema_version": "1.0.0",
            "lock_id": "test-lock",
            "freeze_date": "2026-08-02",
            "hash_algorithm": "sha256",
            "custody": "HASH_ONLY_NOT_VENDORED",
            "artifacts": [],
        }
        for source_id in source_ids:
            signed = source_id.startswith("VN_")
            signature_profile = (
                "government_portal_signed_pdf"
                if signed
                else "official_journal_pdf"
            )
            source_url = f"https://example.test/{source_id}.pdf"
            targets["targets"].append(
                {
                    "id": source_id,
                    "jurisdiction": "VN" if signed else "OTHER",
                    "instrument": source_id,
                    "official_pdf_url": source_url,
                    "declared_page_count": 1,
                    "signature_profile": signature_profile,
                    "required_for_current_claims": True,
                }
            )
            lock["artifacts"].append(
                {
                    "id": source_id,
                    "official_pdf_url": source_url,
                    "byte_size": len(pdf_bytes[source_id]),
                    "sha256": hashlib.sha256(pdf_bytes[source_id]).hexdigest(),
                    "declared_page_count": 1,
                    "signature_profile": signature_profile,
                }
            )
        policy = {
            "signature_profiles": {
                "government_portal_signed_pdf": {
                    "embedded_signature_expectation": "REQUIRED"
                },
                "official_journal_pdf": {
                    "embedded_signature_expectation": "NOT_REQUIRED"
                },
            },
            "external_deposit": {
                "acceptable_provider_classes": ["ZENODO"],
                "notice": "not deposited",
                "required_receipt_fields": [],
            },
        }

        def fake_fetch(record, **_: object):
            return SimpleNamespace(
                data=pdf_bytes[record["id"]],
                transport_url_used=record["official_pdf_url"],
            )

        def fake_pdfsig(path, **_: object):
            source_id = Path(path).stem
            signatures = (
                [
                    {
                        "signature_number": 1,
                        "cryptographic_integrity_valid": True,
                        "certificate_trusted": False,
                    }
                ]
                if source_id.startswith("VN_")
                else []
            )
            return {
                "exit_code": 0 if signatures else 2,
                "signatures": signatures,
                "signature_count": len(signatures),
                "raw_output": "fixture",
                "raw_output_sha256": hashlib.sha256(b"fixture").hexdigest(),
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            targets_path = root / "targets.json"
            lock_path = root / "lock.json"
            policy_path = root / "policy.json"
            targets_path.write_text(json.dumps(targets), encoding="utf-8")
            lock_path.write_text(json.dumps(lock), encoding="utf-8")
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            with patch(
                "hsdl_gap.source_signature_custody.fetch_declared_pdf",
                side_effect=fake_fetch,
            ), patch(
                "hsdl_gap.source_signature_custody.run_pdfsig",
                side_effect=fake_pdfsig,
            ):
                report = build_signature_and_deposit_staging_report(
                    targets_path=targets_path,
                    lock_path=lock_path,
                    policy_path=policy_path,
                    output_dir=root / "package",
                )
            manifest = json.loads(
                (root / "package" / "deposit-manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            for item in manifest["objects"]:
                self.assertTrue((root / "package" / item["object_path"]).is_file())
        self.assertEqual(
            report["status"],
            "DEPOSIT_PACKAGE_STAGED_SIGNATURE_POLICY_PASSED",
        )
        self.assertEqual(report["verified_source_count"], 6)
        self.assertTrue(report["signature_policy_passed"])
        self.assertEqual(report["external_deposit"]["status"], "READY_FOR_EXTERNAL_DEPOSIT")
        self.assertFalse(report["external_deposit"]["durable_custody_established"])

    def test_receipt_must_match_manifest_and_all_objects(self) -> None:
        manifest = {
            "objects": [
                {"id": "A", "sha256": "a" * 64, "byte_size": 10},
                {"id": "B", "sha256": "b" * 64, "byte_size": 20},
            ]
        }
        policy = {
            "external_deposit": {
                "acceptable_provider_classes": ["ZENODO"],
                "required_receipt_fields": [
                    "provider",
                    "deposit_id",
                    "persistent_identifier",
                    "persistent_url",
                    "submitted_at_utc",
                    "manifest_sha256",
                    "depositor",
                    "object_receipts",
                ],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            policy_path = root / "policy.json"
            receipt_path = root / "receipt.json"
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True), encoding="utf-8"
            )
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            receipt = {
                "provider": "ZENODO",
                "deposit_id": "12345",
                "persistent_identifier": "doi:10.5281/zenodo.12345",
                "persistent_url": "https://doi.org/10.5281/zenodo.12345",
                "submitted_at_utc": "2026-08-02T15:00:00+00:00",
                "manifest_sha256": digest,
                "depositor": "OWNER_DECLARED_NAME",
                "object_receipts": [
                    {"id": "A", "sha256": "a" * 64, "byte_size": 10},
                    {"id": "B", "sha256": "b" * 64, "byte_size": 20},
                ],
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            report = verify_external_deposit_receipt(
                manifest_path=manifest_path,
                receipt_path=receipt_path,
                policy_path=policy_path,
            )
            self.assertEqual(
                report["status"],
                "EXTERNAL_DURABLE_CUSTODY_RECEIPT_VERIFIED",
            )
            self.assertTrue(report["durable_custody_established"])
            receipt["object_receipts"][1]["byte_size"] = 21
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            stale = verify_external_deposit_receipt(
                manifest_path=manifest_path,
                receipt_path=receipt_path,
                policy_path=policy_path,
            )
        self.assertEqual(
            stale["status"], "EXTERNAL_DURABLE_CUSTODY_RECEIPT_MISMATCH"
        )
        self.assertFalse(stale["durable_custody_established"])

    def test_receipt_rejects_non_https_and_unsupported_provider(self) -> None:
        manifest = {"objects": []}
        policy = {
            "external_deposit": {
                "acceptable_provider_classes": ["ZENODO"],
                "required_receipt_fields": [
                    "provider",
                    "deposit_id",
                    "persistent_identifier",
                    "persistent_url",
                    "submitted_at_utc",
                    "manifest_sha256",
                    "depositor",
                    "object_receipts",
                ],
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            policy_path = root / "policy.json"
            receipt_path = root / "receipt.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            receipt = {
                "provider": "UNKNOWN",
                "deposit_id": "x",
                "persistent_identifier": "x",
                "persistent_url": "http://example.test/x",
                "submitted_at_utc": "2026-08-02T15:00:00+00:00",
                "manifest_sha256": hashlib.sha256(
                    manifest_path.read_bytes()
                ).hexdigest(),
                "depositor": "x",
                "object_receipts": [],
            }
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaises(SourceCustodyError):
                verify_external_deposit_receipt(
                    manifest_path=manifest_path,
                    receipt_path=receipt_path,
                    policy_path=policy_path,
                )


if __name__ == "__main__":
    unittest.main()
