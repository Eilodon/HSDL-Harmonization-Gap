from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .source_transport import SourceTransportError, fetch_declared_pdf


class ReviewBundleError(RuntimeError):
    """Raised when a visual-review artifact cannot be built safely."""


RENDER_PROFILES: dict[str, dict[str, Any]] = {
    "VN_DECISION_33_2026": {
        "directory": "decision33-pages",
        "dpi": 120,
        "purpose": "catalog route and transition visual review",
    },
    "VN_LAW_134_2025": {
        "directory": "law134-pages",
        "dpi": 110,
        "purpose": "provision locator and source interpretation review",
    },
    "VN_DECREE_142_2026": {
        "directory": "decree142-pages",
        "dpi": 90,
        "purpose": "provision locator and source interpretation review",
    },
}


def verify_locked_pdf_bytes(data: bytes, artifact: dict[str, Any]) -> None:
    """Compatibility helper retained for unit-level identity tests."""
    transport_record = dict(artifact)
    transport_record.setdefault("official_pdf_url", "https://example.invalid/source.pdf")
    if not data.startswith(b"%PDF-"):
        raise ReviewBundleError(f"{artifact['id']}: downloaded payload is not a PDF")
    if len(data) != artifact["byte_size"]:
        raise ReviewBundleError(
            f"{artifact['id']}: byte-size drift: {len(data)} != {artifact['byte_size']}"
        )
    import hashlib

    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_hash != artifact["sha256"]:
        raise ReviewBundleError(
            f"{artifact['id']}: SHA-256 drift: {actual_hash} != {artifact['sha256']}"
        )


def parse_pdfinfo_page_count(output: str) -> int:
    for line in output.splitlines():
        if line.startswith("Pages:"):
            value = line.split(":", 1)[1].strip()
            try:
                pages = int(value)
            except ValueError as exc:
                raise ReviewBundleError(f"invalid pdfinfo page count: {value!r}") from exc
            if pages <= 0:
                raise ReviewBundleError("pdfinfo returned a non-positive page count")
            return pages
    raise ReviewBundleError("pdfinfo output did not contain a Pages field")


def _require_executable(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise ReviewBundleError(f"required executable is missing: {name}")
    return path


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


def _render_pdf(
    pdftoppm: str,
    pdf_path: Path,
    image_dir: Path,
    *,
    dpi: int,
    expected_pages: int,
) -> int:
    image_dir.mkdir(parents=True, exist_ok=True)
    prefix = image_dir / "page"
    _run(
        [
            pdftoppm,
            "-png",
            "-r",
            str(dpi),
            str(pdf_path),
            str(prefix),
        ]
    )
    rendered_pages = len(list(image_dir.glob("page-*.png")))
    if rendered_pages != expected_pages:
        raise ReviewBundleError(
            f"{pdf_path.stem}: rendered {rendered_pages} pages, expected {expected_pages}"
        )
    return rendered_pages


def build_visual_review_bundle(
    lock_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    pdfinfo = _require_executable("pdfinfo")
    pdftotext = _require_executable("pdftotext")
    pdftoppm = _require_executable("pdftoppm")

    lock = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    artifacts = lock.get("artifacts")
    if lock.get("schema_version") != "1.0.0" or not isinstance(artifacts, list):
        raise ReviewBundleError("unsupported or malformed source lock")

    root = Path(output_dir)
    text_dir = root / "text"
    text_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="hsdl-source-review-") as temp_name:
        temp_root = Path(temp_name)
        for artifact in artifacts:
            try:
                fetch = fetch_declared_pdf(
                    artifact,
                    expected_sha256=artifact["sha256"],
                    expected_byte_size=artifact["byte_size"],
                )
            except SourceTransportError as exc:
                raise ReviewBundleError(str(exc)) from exc
            data = fetch.data

            pdf_path = temp_root / f"{artifact['id']}.pdf"
            pdf_path.write_bytes(data)
            info_output = _run([pdfinfo, str(pdf_path)])
            actual_pages = parse_pdfinfo_page_count(info_output)
            declared_pages = artifact["declared_page_count"]
            if actual_pages != declared_pages:
                raise ReviewBundleError(
                    f"{artifact['id']}: page-count drift: {actual_pages} != {declared_pages}"
                )

            text_path = text_dir / f"{artifact['id']}.txt"
            _run([pdftotext, "-layout", str(pdf_path), str(text_path)])

            rendered_pages = 0
            rendered_image_dir: str | None = None
            render_dpi: int | None = None
            render_purpose: str | None = None
            profile = RENDER_PROFILES.get(artifact["id"])
            if profile is not None:
                image_dir = root / profile["directory"]
                rendered_pages = _render_pdf(
                    pdftoppm,
                    pdf_path,
                    image_dir,
                    dpi=profile["dpi"],
                    expected_pages=actual_pages,
                )
                rendered_image_dir = str(image_dir.relative_to(root))
                render_dpi = profile["dpi"]
                render_purpose = profile["purpose"]

            records.append(
                {
                    "id": artifact["id"],
                    "official_pdf_url": artifact["official_pdf_url"],
                    "transport_url_used": fetch.transport_url_used,
                    "transport_attempt_number": fetch.attempt_number,
                    "sha256": artifact["sha256"],
                    "byte_size": artifact["byte_size"],
                    "declared_page_count": declared_pages,
                    "recounted_page_count": actual_pages,
                    "text_path": str(text_path.relative_to(root)),
                    "rendered_image_dir": rendered_image_dir,
                    "rendered_page_count": rendered_pages,
                    "render_dpi": render_dpi,
                    "render_purpose": render_purpose,
                    "visual_review_status": "EVIDENCE_BUNDLE_GENERATED_NOT_REVIEWED",
                }
            )

    records.sort(key=lambda item: item["id"])
    report = {
        "schema_version": "1.1.0",
        "lock_id": lock["lock_id"],
        "status": "CHECKSUM_VERIFIED_AND_RENDERED",
        "artifact_count": len(records),
        "rendered_source_count": sum(
            record["rendered_page_count"] > 0 for record in records
        ),
        "rendered_page_count": sum(
            record["rendered_page_count"] for record in records
        ),
        "records": records,
        "attestation": {
            "pdf_bytes_retained": False,
            "extracted_text_is_derivative_evidence": True,
            "rendered_images_are_derivative_evidence": True,
            "transport_fallbacks_change_identity": False,
            "legal_review_performed": False,
            "notice": (
                "Every derivative was generated only after one declared official transport "
                "reproduced the pinned byte size and SHA-256. Generation is not legal sign-off."
            ),
        },
    }
    (root / "index.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
