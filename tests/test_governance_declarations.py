from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from hsdl_gap.governance_declarations import (
    GovernanceDeclarationError,
    build_governance_readiness_report,
    render_citation_cff,
    validate_governance_declaration,
)


ROOT = Path(__file__).resolve().parents[1]
DECLARATION = ROOT / "governance" / "project_identity_declaration.json"


class GovernanceDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.approved = json.loads(DECLARATION.read_text(encoding="utf-8"))

    def _pending(self) -> dict:
        payload = deepcopy(self.approved)
        payload["status"] = "PENDING_OWNER_DECLARATION"
        payload["owner_approval"] = {
            "approved": False,
            "approved_by": None,
            "approved_at_utc": None,
            "approval_reference": None,
        }
        payload["license"].update(
            {
                "spdx_identifier": None,
                "copyright_holders": [],
                "copyright_years": [],
                "third_party_material_reviewed": False,
            }
        )
        payload["citation"].update(
            {
                "version": None,
                "release_date": None,
                "authors": [],
                "contributors": [],
            }
        )
        payload["generation_policy"] = {
            "license_file_allowed": False,
            "citation_cff_allowed": False,
            "release_metadata_allowed": False,
            "fail_closed_on_missing_owner_approval": True,
        }
        return payload

    def test_repository_declaration_is_owner_approved(self) -> None:
        report = build_governance_readiness_report(DECLARATION, ROOT)
        self.assertEqual(
            report["status"], "OWNER_GOVERNANCE_APPROVED_GENERATION_READY"
        )
        self.assertTrue(report["owner_approved"])
        self.assertEqual(report["identity_counts"]["declared_author_count"], 1)
        self.assertEqual(report["blockers"], [])
        self.assertTrue(report["generation_readiness"]["license_file_allowed"])
        self.assertTrue(report["generation_readiness"]["citation_cff_allowed"])
        self.assertTrue(report["official_files_present"]["LICENSE"])
        self.assertTrue(report["official_files_present"]["CITATION.cff"])

    def test_repository_account_does_not_imply_scholarly_authorship(self) -> None:
        report = build_governance_readiness_report(DECLARATION, ROOT)
        self.assertEqual(report["repository_owner_account"], "Eilodon")
        self.assertFalse(
            report["boundary"]["repository_account_implies_authorship"]
        )
        self.assertFalse(report["boundary"]["assistant_may_invent_authors"])
        self.assertFalse(report["boundary"]["assistant_may_select_license"])

    def test_approved_declaration_can_emit_citation(self) -> None:
        citation = render_citation_cff(self.approved)
        self.assertIn("cff-version: 1.2.0", citation)
        self.assertIn('family-names: "Ngo"', citation)
        self.assertIn('given-names: "Bao Thai"', citation)
        self.assertIn('email: "bao.nt.1992@gmail.com"', citation)
        self.assertIn('orcid: "https://orcid.org/0009-0003-9693-4077"', citation)
        self.assertIn("license: Apache-2.0", citation)
        self.assertIn('version: "1.0.0"', citation)
        self.assertNotIn("Eilodon\n", citation)

    def test_pending_declaration_cannot_emit_citation(self) -> None:
        with self.assertRaises(GovernanceDeclarationError):
            render_citation_cff(self._pending())

    def test_pending_declaration_rejects_official_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            declaration = root / "declaration.json"
            declaration.write_text(
                json.dumps(self._pending()), encoding="utf-8"
            )
            (root / "LICENSE").write_text("unapproved", encoding="utf-8")
            with self.assertRaises(GovernanceDeclarationError):
                build_governance_readiness_report(declaration, root)

    def test_approved_declaration_requires_authors_and_rights_holders(self) -> None:
        approved = deepcopy(self.approved)
        approved["citation"]["authors"] = []
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(approved)
        approved = deepcopy(self.approved)
        approved["license"]["copyright_holders"] = []
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(approved)

    def test_pending_declaration_cannot_enable_generation_flags(self) -> None:
        pending = self._pending()
        pending["generation_policy"]["citation_cff_allowed"] = True
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(pending)

    def test_selected_license_must_be_an_owner_allowed_choice(self) -> None:
        approved = deepcopy(self.approved)
        approved["license"]["spdx_identifier"] = "UNDECLARED-LICENSE"
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(approved)


if __name__ == "__main__":
    unittest.main()
