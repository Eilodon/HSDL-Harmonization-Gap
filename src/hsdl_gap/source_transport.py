from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PDF_MAGIC = b"%PDF-"
DEFAULT_MAXIMUM_BYTES = 150_000_000
USER_AGENT = "HSDL-Harmonization-Gap/1.0 official-source-transport"


class SourceTransportError(RuntimeError):
    """Raised when no declared official transport yields an acceptable PDF."""


@dataclass(frozen=True, slots=True)
class FetchResult:
    data: bytes
    canonical_url: str
    transport_url_used: str
    final_url: str
    http_status: int
    content_type: str
    attempt_number: int


def declared_transport_urls(record: dict[str, Any]) -> tuple[str, ...]:
    canonical = record["official_pdf_url"]
    alternates = record.get("alternate_official_pdf_urls", [])
    if not isinstance(alternates, list) or not all(
        isinstance(url, str) and url.startswith("https://") for url in alternates
    ):
        raise SourceTransportError(
            f"{record.get('id', '<unknown>')}: alternate_official_pdf_urls must be an HTTPS string list"
        )
    ordered: list[str] = []
    for url in (canonical, *alternates):
        if url not in ordered:
            ordered.append(url)
    return tuple(ordered)


def _read_response_limited(response: Any, maximum_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > maximum_bytes:
            raise SourceTransportError(
                f"artifact exceeds maximum_bytes={maximum_bytes}"
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _identity_error(
    data: bytes,
    *,
    expected_sha256: str | None,
    expected_byte_size: int | None,
) -> str | None:
    if not data.startswith(PDF_MAGIC):
        return "payload does not begin with PDF magic bytes"
    if expected_byte_size is not None and len(data) != expected_byte_size:
        return f"byte-size mismatch: {len(data)} != {expected_byte_size}"
    if expected_sha256 is not None:
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected_sha256:
            return f"SHA-256 mismatch: {digest} != {expected_sha256}"
    return None


def fetch_declared_pdf(
    record: dict[str, Any],
    *,
    timeout_seconds: int = 90,
    maximum_bytes: int = DEFAULT_MAXIMUM_BYTES,
    attempts_per_url: int = 3,
    expected_sha256: str | None = None,
    expected_byte_size: int | None = None,
) -> FetchResult:
    """Fetch a PDF through declared official transports and optionally enforce identity.

    The canonical URL remains the source identifier. Alternate URLs are transport-only
    fallbacks. When expected identity is supplied, no transport is accepted unless the
    bytes exactly match the pinned size and SHA-256.
    """
    if attempts_per_url <= 0:
        raise ValueError("attempts_per_url must be positive")

    errors: list[str] = []
    canonical = record["official_pdf_url"]
    attempt_number = 0
    for transport_url in declared_transport_urls(record):
        for local_attempt in range(1, attempts_per_url + 1):
            attempt_number += 1
            request = Request(
                transport_url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.1",
                    "Cache-Control": "no-cache",
                    "Pragma": "no-cache",
                    "Referer": "https://eur-lex.europa.eu/" if "eur-lex.europa.eu" in transport_url else transport_url,
                },
            )
            try:
                with urlopen(request, timeout=timeout_seconds) as response:
                    data = _read_response_limited(response, maximum_bytes)
                    identity_error = _identity_error(
                        data,
                        expected_sha256=expected_sha256,
                        expected_byte_size=expected_byte_size,
                    )
                    if identity_error is None:
                        return FetchResult(
                            data=data,
                            canonical_url=canonical,
                            transport_url_used=transport_url,
                            final_url=response.geturl(),
                            http_status=getattr(response, "status", 200),
                            content_type=response.headers.get_content_type(),
                            attempt_number=attempt_number,
                        )
                    errors.append(
                        f"{transport_url} attempt {local_attempt}: {identity_error}"
                    )
            except (HTTPError, URLError, OSError, SourceTransportError) as exc:
                errors.append(
                    f"{transport_url} attempt {local_attempt}: {type(exc).__name__}: {exc}"
                )
            if local_attempt < attempts_per_url:
                time.sleep(min(1.5 * local_attempt, 4.0))

    source_id = record.get("id", "<unknown>")
    detail = " | ".join(errors[-12:])
    raise SourceTransportError(
        f"{source_id}: no declared official transport produced acceptable bytes; {detail}"
    )
