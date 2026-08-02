from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .stable_id import canonical_json_bytes


class ReleasePackageError(ValueError):
    """Raised when a release package spec, build, or verification is invalid."""


_MEDIA_TYPES = {
    ".json": "application/json",
    ".hsdl": "text/plain",
    ".md": "text/markdown",
    ".csv": "text/csv",
    ".toml": "application/toml",
}

_ZIP_FIXED_DATE_TIME = (1980, 1, 1, 0, 0, 0)


def _media_type(path: Path) -> str:
    return _MEDIA_TYPES.get(path.suffix, "application/octet-stream")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_path(root: Path, value: str | Path) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else root / candidate


def _load_spec(spec_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleasePackageError(f"release spec is missing: {spec_path}") from exc
    except json.JSONDecodeError as exc:
        raise ReleasePackageError(
            f"release spec is invalid JSON: {spec_path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ReleasePackageError(f"release spec must be a JSON object: {spec_path}")
    return payload


def _check_safe_pattern(pattern: Any) -> None:
    if not isinstance(pattern, str) or not pattern:
        raise ReleasePackageError(
            f"include pattern must be a non-empty string: {pattern!r}"
        )
    pattern_path = Path(pattern)
    if pattern_path.is_absolute() or ".." in pattern_path.parts:
        raise ReleasePackageError(f"unsafe include pattern: {pattern!r}")


def _resolve_includes(repository_root: Path, patterns: list[Any]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for pattern in patterns:
        _check_safe_pattern(pattern)
        matches = [p for p in sorted(repository_root.glob(pattern)) if p.is_file()]
        for file_path in matches:
            rel = file_path.relative_to(repository_root).as_posix()
            resolved[rel] = file_path
    return resolved


def _check_required_artifacts(repository_root: Path, required: list[Any]) -> None:
    for rel in required:
        if not isinstance(rel, str) or not rel:
            raise ReleasePackageError(
                f"required generated artifact must be a non-empty string: {rel!r}"
            )
        if not (repository_root / rel).is_file():
            raise ReleasePackageError(f"required generated artifact is missing: {rel}")


def _build_ro_crate(release_id: str, entries: list[dict[str, Any]]) -> dict[str, Any]:
    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": release_id,
            "hasPart": [{"@id": entry["path"]} for entry in entries],
        },
    ]
    for entry in entries:
        graph.append(
            {
                "@id": entry["path"],
                "@type": "File",
                "sha256": entry["sha256"],
                "contentSize": entry["byte_size"],
                "encodingFormat": entry["media_type"],
            }
        )
    return {"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": graph}


def _write_deterministic_zip(zip_path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo(filename=name, date_time=_ZIP_FIXED_DATE_TIME)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])


def build_release_package(
    *,
    repository_root: str | Path,
    spec_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    root = Path(repository_root)
    spec = _load_spec(_resolve_path(root, spec_path))

    release_id = spec.get("release_id")
    claim_class = spec.get("claim_class")
    legal_validation = spec.get("legal_validation")
    include_patterns = spec.get("include")
    required_artifacts = spec.get("required_generated_artifacts", [])
    publication_blockers = spec.get("publication_blockers")

    if not isinstance(release_id, str) or not release_id:
        raise ReleasePackageError("release spec release_id must be non-empty")
    if claim_class != "MODEL_RELATIVE":
        raise ReleasePackageError("release spec must use MODEL_RELATIVE claim class")
    if legal_validation != "NOT_ASSERTED":
        raise ReleasePackageError("release spec must not assert legal validation")
    if not isinstance(include_patterns, list) or not include_patterns:
        raise ReleasePackageError(
            "release spec must declare at least one include pattern"
        )
    if not isinstance(publication_blockers, list) or not publication_blockers:
        raise ReleasePackageError(
            "release spec must declare at least one publication blocker"
        )
    if not isinstance(required_artifacts, list):
        raise ReleasePackageError("required_generated_artifacts must be a list")

    _check_required_artifacts(root, required_artifacts)
    included = _resolve_includes(root, include_patterns)
    if not included:
        raise ReleasePackageError("release spec include patterns matched no files")

    entries: list[dict[str, Any]] = []
    unique_objects: dict[str, Path] = {}
    for rel_path in sorted(included):
        file_path = included[rel_path]
        digest = _file_sha256(file_path)
        object_path = f"objects/sha256/{digest[:2]}/{digest[2:]}"
        entries.append(
            {
                "path": rel_path,
                "sha256": digest,
                "byte_size": file_path.stat().st_size,
                "media_type": _media_type(file_path),
                "object_path": object_path,
            }
        )
        unique_objects.setdefault(object_path, file_path)

    manifest = {
        "schema_version": "1.0.0",
        "release_id": release_id,
        "entries": entries,
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False).encode(
            "utf-8"
        )
        + b"\n"
    )
    manifest_hash = "sha256:" + hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()

    ro_crate_bytes = (
        json.dumps(
            _build_ro_crate(release_id, entries),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )

    output_root = _resolve_path(root, output_dir)
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)
    (output_root / "manifest.json").write_bytes(manifest_bytes)
    (output_root / "ro-crate-metadata.json").write_bytes(ro_crate_bytes)
    for object_path, file_path in unique_objects.items():
        destination = output_root / object_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(file_path.read_bytes())

    zip_path = output_root.parent / f"{output_root.name}.zip"
    zip_files = {
        "manifest.json": manifest_bytes,
        "ro-crate-metadata.json": ro_crate_bytes,
        **{
            object_path: file_path.read_bytes()
            for object_path, file_path in sorted(unique_objects.items())
        },
    }
    _write_deterministic_zip(zip_path, zip_files)
    zip_bytes = zip_path.read_bytes()

    verification = verify_release_package(output_root)

    official_pdf_bytes_included = any(
        entry["path"].lower().endswith(".pdf") for entry in entries
    )
    official_pdf_lock_included = any(
        "official_pdf_lock" in entry["path"] for entry in entries
    )

    return {
        "schema_version": "1.0.0",
        "status": "ENGINEERING_RELEASE_PREVIEW_COMPLETE_BLOCKED",
        "claim_class": "MODEL_RELATIVE",
        "legal_validation": "NOT_ASSERTED",
        "release_id": release_id,
        "output_directory": output_root.as_posix(),
        "zip_path": zip_path.as_posix(),
        "zip_sha256": hashlib.sha256(zip_bytes).hexdigest(),
        "zip_byte_size": len(zip_bytes),
        "manifest_hash": manifest_hash,
        "entry_count": len(entries),
        "unique_object_count": len(unique_objects),
        "publication_blockers": list(publication_blockers),
        "verification": verification,
        "custody_boundary": {
            "content_addressed_local_package": True,
            "durable_external_deposit": False,
            "official_pdf_bytes_included": official_pdf_bytes_included,
            "official_pdf_lock_included": official_pdf_lock_included,
            "notice": (
                "This package is a local content-addressed engineering artifact. "
                "It is not a durable institutional deposit and does not authorise "
                "publication."
            ),
        },
    }


def verify_release_package(package_dir: str | Path) -> dict[str, Any]:
    package_root = Path(package_dir)
    manifest_path = package_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "schema_version": "1.0.0",
            "status": "RELEASE_PACKAGE_INVALID",
            "entry_count": 0,
            "error_count": 1,
            "errors": [f"manifest is missing: {manifest_path}"],
            "manifest_hash": None,
        }
    except json.JSONDecodeError as exc:
        return {
            "schema_version": "1.0.0",
            "status": "RELEASE_PACKAGE_INVALID",
            "entry_count": 0,
            "error_count": 1,
            "errors": [f"manifest is invalid JSON: {exc}"],
            "manifest_hash": None,
        }

    entries = manifest.get("entries", [])
    recomputed_hash = "sha256:" + hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()

    errors: list[str] = []
    if not (package_root / "ro-crate-metadata.json").is_file():
        errors.append("ro-crate-metadata.json is missing")

    for entry in entries:
        object_path = package_root / entry["object_path"]
        if not object_path.is_file():
            errors.append(f"object is missing: {entry['object_path']}")
            continue
        actual_digest = _file_sha256(object_path)
        if actual_digest != entry["sha256"]:
            errors.append(
                f"object content hash mismatch for {entry['path']}: "
                f"expected {entry['sha256']}, got {actual_digest}"
            )
        actual_size = object_path.stat().st_size
        if actual_size != entry["byte_size"]:
            errors.append(
                f"object byte size mismatch for {entry['path']}: "
                f"expected {entry['byte_size']}, got {actual_size}"
            )

    status = "RELEASE_PACKAGE_VERIFIED" if not errors else "RELEASE_PACKAGE_INVALID"
    return {
        "schema_version": "1.0.0",
        "status": status,
        "entry_count": len(entries),
        "error_count": len(errors),
        "errors": errors,
        "manifest_hash": recomputed_hash,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--root", default=".")
    build_parser.add_argument("--spec", required=True)
    build_parser.add_argument("--output", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--package", required=True)

    args = parser.parse_args(argv)

    if args.command == "build":
        report = build_release_package(
            repository_root=args.root,
            spec_path=args.spec,
            output_dir=args.output,
        )
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        if report["verification"]["status"] != "RELEASE_PACKAGE_VERIFIED":
            raise SystemExit(17)
    else:
        report = verify_release_package(args.package)
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        if report["status"] != "RELEASE_PACKAGE_VERIFIED":
            raise SystemExit(17)


if __name__ == "__main__":
    main()
