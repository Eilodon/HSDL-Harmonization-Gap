from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.release_package import (
    ReleasePackageError,
    build_release_package,
    verify_release_package,
)


class ReleasePackageTests(unittest.TestCase):
    def _write_fixture_repo(self, root: Path) -> Path:
        (root / "generated").mkdir()
        (root / "schemas").mkdir()
        (root / "sources").mkdir()
        (root / "profiles").mkdir()
        (root / "generated" / "a.json").write_text(
            json.dumps({"status": "A"}), encoding="utf-8"
        )
        (root / "generated" / "b.hsdl").write_text(
            "@hsdl-core 0.2\nendprofile\n", encoding="utf-8"
        )
        (root / "schemas" / "x.schema.json").write_text(
            json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema"}),
            encoding="utf-8",
        )
        (root / "sources" / "official_pdf_lock_2026-08-02.json").write_text(
            json.dumps({"custody": "HASH_ONLY_NOT_VENDORED"}), encoding="utf-8"
        )
        (root / "profiles" / "profile.json").write_text(
            json.dumps({"profile_id": "test"}), encoding="utf-8"
        )
        (root / "README.md").write_text("fixture\n", encoding="utf-8")
        spec = {
            "schema_version": "1.0.0",
            "release_id": "test-preview",
            "release_class": "ENGINEERING_PREVIEW",
            "claim_class": "MODEL_RELATIVE",
            "legal_validation": "NOT_ASSERTED",
            "include": [
                "README.md",
                "generated/*.json",
                "generated/*.hsdl",
                "schemas/*.schema.json",
                "sources/official_pdf_lock_2026-08-02.json",
                "profiles/*.json",
            ],
            "required_generated_artifacts": ["generated/a.json"],
            "publication_blockers": [
                "DURABLE_PDF_CUSTODY_NOT_ESTABLISHED",
                "LICENSE_FILE_NOT_DECLARED",
            ],
            "notice": "test engineering preview",
        }
        spec_path = root / "spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        return spec_path

    def test_builds_and_self_verifies_content_addressed_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            report = build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/package",
            )
            verification = verify_release_package(root / "out" / "package")
        self.assertEqual(
            report["status"], "ENGINEERING_RELEASE_PREVIEW_COMPLETE_BLOCKED"
        )
        self.assertEqual(verification["status"], "RELEASE_PACKAGE_VERIFIED")
        self.assertEqual(report["entry_count"], 6)
        self.assertEqual(report["unique_object_count"], 6)
        self.assertRegex(report["zip_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(report["custody_boundary"]["content_addressed_local_package"])
        self.assertFalse(report["custody_boundary"]["durable_external_deposit"])
        self.assertFalse(report["custody_boundary"]["official_pdf_bytes_included"])
        self.assertTrue(report["custody_boundary"]["official_pdf_lock_included"])

    def test_zip_is_deterministic_for_identical_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            first = build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/first",
            )
            second = build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/second",
            )
        self.assertEqual(first["manifest_hash"], second["manifest_hash"])
        self.assertEqual(first["zip_sha256"], second["zip_sha256"])
        self.assertEqual(first["zip_byte_size"], second["zip_byte_size"])

    def test_manifest_preserves_original_paths_and_object_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/package",
            )
            manifest = json.loads(
                (root / "out" / "package" / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
        paths = [entry["path"] for entry in manifest["entries"]]
        self.assertEqual(paths, sorted(paths))
        self.assertIn("generated/a.json", paths)
        for entry in manifest["entries"]:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(entry["object_path"].startswith("objects/sha256/"))

    def test_ro_crate_metadata_references_every_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/package",
            )
            crate = json.loads(
                (root / "out" / "package" / "ro-crate-metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            manifest = json.loads(
                (root / "out" / "package" / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
        ids = {item["@id"] for item in crate["@graph"]}
        for entry in manifest["entries"]:
            self.assertIn(entry["path"], ids)

    def test_tampered_object_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/package",
            )
            manifest = json.loads(
                (root / "out" / "package" / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            object_path = root / "out" / "package" / manifest["entries"][0]["object_path"]
            object_path.write_bytes(b"tampered")
            verification = verify_release_package(root / "out" / "package")
        self.assertEqual(verification["status"], "RELEASE_PACKAGE_INVALID")
        self.assertGreaterEqual(verification["error_count"], 1)
        self.assertTrue(any("mismatch" in error for error in verification["errors"]))

    def test_missing_required_generated_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            (root / "generated" / "a.json").unlink()
            with self.assertRaises(ReleasePackageError):
                build_release_package(
                    repository_root=root,
                    spec_path=spec,
                    output_dir="out/package",
                )

    def test_unsafe_include_pattern_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec_path = self._write_fixture_repo(root)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["include"] = ["../outside.json"]
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(ReleasePackageError):
                build_release_package(
                    repository_root=root,
                    spec_path=spec_path,
                    output_dir="out/package",
                )

    def test_publication_blockers_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self._write_fixture_repo(root)
            report = build_release_package(
                repository_root=root,
                spec_path=spec,
                output_dir="out/package",
            )
        self.assertEqual(
            report["publication_blockers"],
            [
                "DURABLE_PDF_CUSTODY_NOT_ESTABLISHED",
                "LICENSE_FILE_NOT_DECLARED",
            ],
        )
        self.assertEqual(report["claim_class"], "MODEL_RELATIVE")
        self.assertEqual(report["legal_validation"], "NOT_ASSERTED")


if __name__ == "__main__":
    unittest.main()
