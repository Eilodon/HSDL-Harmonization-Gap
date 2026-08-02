from __future__ import annotations

import hashlib
import unittest
from unittest.mock import patch

from hsdl_gap.source_transport import (
    SourceTransportError,
    declared_transport_urls,
    fetch_declared_pdf,
)


class _Headers:
    def __init__(self, content_type: str) -> None:
        self._content_type = content_type

    def get_content_type(self) -> str:
        return self._content_type


class _Response:
    def __init__(self, data: bytes, url: str, content_type: str) -> None:
        self._data = data
        self._offset = 0
        self._url = url
        self.status = 200
        self.headers = _Headers(content_type)

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self._data) - self._offset
        chunk = self._data[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class SourceTransportTests(unittest.TestCase):
    def test_fallback_is_used_only_when_it_matches_pinned_identity(self) -> None:
        primary = "https://official.example/primary.pdf"
        fallback = "https://official.example/fallback.pdf"
        pdf = b"%PDF-1.7\nlocked artifact\n%%EOF\n"
        target = {
            "id": "SOURCE_A",
            "official_pdf_url": primary,
            "alternate_official_pdf_urls": [fallback],
        }

        def fake_urlopen(request, timeout):
            url = request.full_url
            if url == primary:
                return _Response(b"<html>landing page</html>", url, "text/html")
            if url == fallback:
                return _Response(pdf, url, "application/pdf")
            raise AssertionError(f"unexpected URL: {url}")

        with patch("hsdl_gap.source_transport.urlopen", side_effect=fake_urlopen):
            result = fetch_declared_pdf(
                target,
                attempts_per_url=1,
                expected_sha256=hashlib.sha256(pdf).hexdigest(),
                expected_byte_size=len(pdf),
            )

        self.assertEqual(result.canonical_url, primary)
        self.assertEqual(result.transport_url_used, fallback)
        self.assertEqual(result.data, pdf)
        self.assertEqual(result.attempt_number, 2)

    def test_fallback_with_wrong_pdf_identity_is_rejected(self) -> None:
        primary = "https://official.example/primary.pdf"
        fallback = "https://official.example/fallback.pdf"
        expected = b"%PDF-1.7\nexpected\n%%EOF\n"
        wrong = b"%PDF-1.7\nwrong\n%%EOF\n"
        target = {
            "id": "SOURCE_A",
            "official_pdf_url": primary,
            "alternate_official_pdf_urls": [fallback],
        }

        def fake_urlopen(request, timeout):
            return _Response(wrong, request.full_url, "application/pdf")

        with patch("hsdl_gap.source_transport.urlopen", side_effect=fake_urlopen):
            with self.assertRaisesRegex(SourceTransportError, "no declared official transport"):
                fetch_declared_pdf(
                    target,
                    attempts_per_url=1,
                    expected_sha256=hashlib.sha256(expected).hexdigest(),
                    expected_byte_size=len(expected),
                )

    def test_transport_urls_are_deduplicated_in_declared_order(self) -> None:
        target = {
            "id": "SOURCE_A",
            "official_pdf_url": "https://official.example/a.pdf",
            "alternate_official_pdf_urls": [
                "https://official.example/a.pdf",
                "https://official.example/b.pdf",
            ],
        }
        self.assertEqual(
            declared_transport_urls(target),
            (
                "https://official.example/a.pdf",
                "https://official.example/b.pdf",
            ),
        )

    def test_non_https_alternate_is_rejected(self) -> None:
        target = {
            "id": "SOURCE_A",
            "official_pdf_url": "https://official.example/a.pdf",
            "alternate_official_pdf_urls": ["http://official.example/b.pdf"],
        }
        with self.assertRaisesRegex(SourceTransportError, "HTTPS string list"):
            declared_transport_urls(target)


if __name__ == "__main__":
    unittest.main()
