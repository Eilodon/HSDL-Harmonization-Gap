from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


PDF_MAGIC = b"%PDF-"
USER_AGENT = "HSDL-Harmonization-Gap/1.0 visual-review"
DEFAULT_MAXIMUM_BYTES = 150_000_000


class ReviewBundleError(RuntimeError):
    """Raised when a visual-review artifact cannot be built safely."""


def verify_locked_pdf_bytes(data: bytes, artifact: dict[str, Any]) -> None:
    if not data.startswith(PDF_MAGIC):
        raise ReviewBundleError(f"{artifact['id']}: downloaded payload is not a PDF")
    actual_size = len(data)
    actual_hash = hashlib.sha256(data).hexdigest()
    if actual_size != artifact["byte_size"]:
        raise ReviewBundleError(
            f"{artifact['id']}: byte-size drift: {actual_size} != {artifact['byte_size']}"
        )
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


def _download(url: str, *, maximum_bytes: int = DEFAULT_MAXIMUM_BYTES) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/pdf,*/*;q=0.1",
        },
    )
    chunks: list[bytes] = []
    total = 0
    with urlopen(request, timeout=90) as response:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > maximum_bytes:
                raise ReviewBundleError(
                    f"artifact exceeds maximum_bytes={maximum_bytes}"
                )
            chunks.append(chunk)
    return b"".join(chunks)


def _run(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout


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
    image_dir = root / "decision33-pages"
    text_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="hsdl-source-review-") as temp_name:
        temp_root = Path(temp_name)
        for artifact in artifacts:
            data = _download(artifact["official_pdf_url"])
            verify_locked_pdf_bytes(data, artifact)

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
            if artifact["id"] == "VN_DECISION_33_2026":
                prefix = image_dir / "page"
                _run(
                    [
                        pdftoppm,
                        "-png",
                        "-r",
                        "120",
                        str(pdf_path),
                        str(prefix),
                    ]
                )
                rendered_pages = len(list(image_dir.glob("page-*.png")))
                if rendered_pages != actual_pages:
                    raise ReviewBundleError(
                        "Decision 33 render did not produce one image per PDF page"
                    )

            records.append(
                {
                    "id": artifact["id"],
                    "official_pdf_url": artifact["official_pdf_url"],
                    "sha256": artifact["sha256"],
                    "byte_size": artifact["byte_size"],
                    "declared_page_count": declared_pages,
                    "recounted_page_count": actual_pages,
                    "text_path": str(text_path.relative_to(root)),
                    "rendered_page_count": rendered_pages,
                    "visual_review_status": "EVIDENCE_BUNDLE_GENERATED_NOT_REVIEWED",
                }
            )

    records.sort(key=lambda item: item["id"])
    report = {
        "schema_version": "1.0.0",
        "lock_id": lock["lock_id"],
        "status": "CHECKSUM_VERIFIED_AND_RENDERED",
        "artifact_count": len(records),
        "records": records,
        "attestation": {
            "pdf_bytes_retained": False,
            "extracted_text_is_derivative_evidence": True,
            "rendered_images_are_derivative_evidence": True,
            "legal_review_performed": False,
            "notice": (
                "Every derivative was generated only after the downloaded PDF matched "
                "the pinned byte size and SHA-256. Generation is not legal sign-off."
            ),
        },
    }
    (root / "index.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report
