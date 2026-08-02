from __future__ import annotations

import hashlib
import unittest

from hsdl_gap.provenance import (
    ProvenanceError,
    fingerprint_pdf_bytes,
    validate_source_targets,
)


class SourceProvenanceTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "schema_version": "1.0.0",
            "freeze_date": "2026-08-02",
            "policy": {
                "transport": "https_only",
                "hash_algorithm": "sha256",
                "maximum_bytes": 1000,
                "notice": "test",
            },
            "targets": [
                {
                    "id": "SOURCE_A",
                    "jurisdiction": "TEST",
                    "instrument": "Instrument A",
                    "official_pdf_url": "https://example.test/a.pdf",
                    "declared_page_count": 1,
                    "signature_profile": "test_pdf",
                    "required_for_current_claims": True,
                }
            ],
        }

    def test_valid_target_bundle(self) -> None:
        validate_source_targets(self._payload())

    def test_duplicate_ids_are_rejected(self) -> None:
        payload = self._payload()
        payload["targets"].append(dict(payload["targets"][0]))
        payload["targets"][1]["official_pdf_url"] = "https://example.test/b.pdf"
        with self.assertRaisesRegex(ProvenanceError, "duplicate target id"):
            validate_source_targets(payload)

    def test_non_https_target_is_rejected(self) -> None:
        payload = self._payload()
        payload["targets"][0]["official_pdf_url"] = "http://example.test/a.pdf"
        with self.assertRaisesRegex(ProvenanceError, "must use an https URL"):
            validate_source_targets(payload)

    def test_pdf_fingerprint_is_deterministic(self) -> None:
        data = b"%PDF-1.7\nsource provenance fixture\n%%EOF\n"
        result = fingerprint_pdf_bytes(data)
        self.assertEqual(result["byte_size"], len(data))
        self.assertEqual(result["sha256"], hashlib.sha256(data).hexdigest())
        self.assertTrue(result["pdf_magic_verified"])

    def test_non_pdf_artifact_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProvenanceError, "PDF magic"):
            fingerprint_pdf_bytes(b"not a pdf")


if __name__ == "__main__":
    unittest.main()
