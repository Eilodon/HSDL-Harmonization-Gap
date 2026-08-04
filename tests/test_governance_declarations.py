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
        cls.pending = json.loads(DECLARATION.read_text(encoding="utf-8"))

    def test_repository_declaration_remains_pending(self) -> None:
        report = build_governance_readiness_report(DECLARATION, ROOT)
        self.assertEqual(
            report["status"], "OWNER_GOVERNANCE_DECLARATION_PENDING"
        )
        self.assertFalse(report["owner_approved"])
        self.assertEqual(report["identity_counts"]["declared_author_count"], 0)
        self.assertIn("OWNER_APPROVAL_MISSING", report["blockers"])
        self.assertIn("SPDX_LICENSE_NOT_SELECTED", report["blockers"])
        self.assertFalse(
            report["generation_readiness"]["license_file_allowed"]
        )
        self.assertFalse(
            report["generation_readiness"]["citation_cff_allowed"]
        )

    def test_repository_account_does_not_imply_scholarly_authorship(self) -> None:
        report = build_governance_readiness_report(DECLARATION, ROOT)
        self.assertEqual(report["repository_owner_account"], "Eilodon")
        self.assertFalse(
            report["boundary"]["repository_account_implies_authorship"]
        )
        self.assertFalse(report["boundary"]["assistant_may_invent_authors"])
        self.assertFalse(report["boundary"]["assistant_may_select_license"])

    def test_pending_declaration_cannot_emit_citation(self) -> None:
        with self.assertRaises(GovernanceDeclarationError):
            render_citation_cff(self.pending)

    def test_pending_declaration_rejects_official_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("unapproved", encoding="utf-8")
            with self.assertRaises(GovernanceDeclarationError):
                build_governance_readiness_report(DECLARATION, root)

    def _approved(self) -> dict:
        payload = deepcopy(self.pending)
        payload["status"] = "OWNER_APPROVED"
        payload["owner_approval"] = {
            "approved": True,
            "approved_by": "Authorised Rights Holder",
            "approved_at_utc": "2026-08-02T16:00:00+00:00",
            "approval_reference": "https://github.com/Eilodon/HSDL-Harmonization-Gap/issues/OWNER_DECISION",
        }
        payload["license"].update(
            {
                "spdx_identifier": "Apache-2.0",
                "copyright_holders": ["Authorised Rights Holder"],
                "copyright_years": [2026],
                "third_party_material_reviewed": True,
            }
        )
        payload["citation"].update(
            {
                "version": "1.0.0",
                "release_date": "2026-08-02",
                "authors": [
                    {
                        "name": "Authorised Rights Holder",
                        "given_names": "Authorised",
                        "family_names": "Rights Holder",
                        "orcid": "https://orcid.org/0000-0000-0000-0000",
                        "affiliation": "Declared Institution",
                        "roles": ["Conceptualization", "Software"],
                    }
                ],
                "contributors": [
                    {
                        "name": "Declared Contributor",
                        "roles": ["Validation"],
                    }
                ],
            }
        )
        payload["generation_policy"] = {
            "license_file_allowed": True,
            "citation_cff_allowed": True,
            "release_metadata_allowed": True,
            "fail_closed_on_missing_owner_approval": True,
        }
        return payload

    def test_complete_owner_approval_unlocks_generation(self) -> None:
        approved = self._approved()
        validation = validate_governance_declaration(approved)
        self.assertTrue(validation["approved"])
        self.assertEqual(validation["blockers"], [])
        self.assertTrue(validation["license_file_allowed"])
        self.assertTrue(validation["citation_cff_allowed"])
        citation = render_citation_cff(approved)
        self.assertIn("cff-version: 1.2.0", citation)
        self.assertIn("Authorised Rights Holder", citation)
        self.assertIn("version: \"1.0.0\"", citation)
        self.assertNotIn("Eilodon\n", citation)

    def test_approved_declaration_requires_authors_and_rights_holders(self) -> None:
        approved = self._approved()
        approved["citation"]["authors"] = []
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(approved)
        approved = self._approved()
        approved["license"]["copyright_holders"] = []
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(approved)

    def test_pending_declaration_cannot_enable_generation_flags(self) -> None:
        pending = deepcopy(self.pending)
        pending["generation_policy"]["citation_cff_allowed"] = True
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(pending)

    def test_selected_license_must_be_an_owner_allowed_choice(self) -> None:
        approved = self._approved()
        approved["license"]["spdx_identifier"] = "UNDECLARED-LICENSE"
        with self.assertRaises(GovernanceDeclarationError):
            validate_governance_declaration(approved)


if __name__ == "__main__":
    unittest.main()
