from __future__ import annotations

import hashlib
import unittest

from hsdl_gap.review_bundle import (
    ReviewBundleError,
    parse_pdfinfo_page_count,
    verify_locked_pdf_bytes,
)


class ReviewBundleTests(unittest.TestCase):
    def _artifact(self, data: bytes) -> dict:
        return {
            "id": "TEST_PDF",
            "byte_size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def test_locked_pdf_bytes_verify(self) -> None:
        data = b"%PDF-1.7\nfixture\n%%EOF\n"
        verify_locked_pdf_bytes(data, self._artifact(data))

    def test_checksum_drift_is_rejected(self) -> None:
        data = b"%PDF-1.7\nfixture\n%%EOF\n"
        artifact = self._artifact(data)
        artifact["sha256"] = "0" * 64
        with self.assertRaisesRegex(ReviewBundleError, "SHA-256 drift"):
            verify_locked_pdf_bytes(data, artifact)

    def test_non_pdf_is_rejected_before_rendering(self) -> None:
        data = b"not a pdf"
        with self.assertRaisesRegex(ReviewBundleError, "not a PDF"):
            verify_locked_pdf_bytes(data, self._artifact(data))

    def test_pdfinfo_page_count_is_parsed(self) -> None:
        output = "Title: Example\nPages:          16\nEncrypted: no\n"
        self.assertEqual(parse_pdfinfo_page_count(output), 16)

    def test_missing_pdfinfo_pages_is_rejected(self) -> None:
        with self.assertRaisesRegex(ReviewBundleError, "did not contain"):
            parse_pdfinfo_page_count("Title: Example\n")


if __name__ == "__main__":
    unittest.main()
