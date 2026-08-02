from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from hsdl_gap.reviewer_signoff import (
    QUESTION_DECISIONS,
    build_review_readiness_report,
    validate_completed_review,
    validate_review_template,
)


TEMPLATE = "reviews/independent_legal_review_template.json"
AUDIT = "sources/reviews/legacy_v11_provision_audit.json"


class ReviewerSignoffTests(unittest.TestCase):
    def _completed_review(self) -> dict:
        template = json.loads(Path(TEMPLATE).read_text(encoding="utf-8"))
        audit = json.loads(Path(AUDIT).read_text(encoding="utf-8"))
        reviewer_name = "Independent Reviewer"
        review = copy.deepcopy(template)
        review["review_id"] = "review-001"
        review["review_status"] = "COMPLETED"
        review["reviewer"] = {
            "full_name": reviewer_name,
            "organisation": "Independent",
            "professional_role": "Legal researcher",
            "jurisdictions_reviewed": ["EU", "Vietnam", "ASEAN"],
            "conflicts_disclosed": "No conflicts identified",
            "independence_attestation": True,
        }
        review["reviewed_on"] = "2026-08-03"
        for question in review["required_questions"]:
            question["reviewer_decision"] = "AGREE_WITH_NARROWING"
            question["reasoning"] = "Reviewed against the cited official provision."
            question["required_change"] = "Apply the provision-audit narrowing."
        review["rule_disposition_review"] = [
            {
                "rule_id": row["rule_id"],
                "reviewer_decision": "AGREE_WITH_NARROWING",
                "reasoning": "Disposition reviewed against the cited locator.",
            }
            for row in audit["rules"]
        ]
        review["overall_decision"] = "APPROVE_WITH_REQUIRED_CHANGES"
        review["overall_reasoning"] = "Re-encode before producing current-law results."
        review["signature"] = {
            "method": "typed electronic attestation",
            "signed_name": reviewer_name,
            "signed_on": "2026-08-03",
        }
        return review

    def _validate_payload(self, payload: dict) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "review.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return validate_completed_review(path, TEMPLATE, AUDIT)

    def test_repository_template_is_ready_but_not_signoff(self) -> None:
        self.assertEqual(validate_review_template(TEMPLATE, AUDIT), [])
        report = build_review_readiness_report(TEMPLATE, AUDIT)
        self.assertEqual(report["status"], "READY_FOR_ASSIGNMENT")
        self.assertEqual(report["required_question_count"], 11)
        self.assertEqual(report["required_rule_review_count"], 23)
        self.assertFalse(report["gate"]["completed_signoff_present"])
        self.assertEqual(report["gate"]["current_law_quantitative_claims"], "BLOCKED")

    def test_fully_completed_review_passes_contract(self) -> None:
        self.assertEqual(self._validate_payload(self._completed_review()), [])

    def test_template_itself_cannot_pass_as_completed_review(self) -> None:
        errors = validate_completed_review(TEMPLATE, TEMPLATE, AUDIT)
        self.assertTrue(any("review_status" in error for error in errors))
        self.assertTrue(any("review_id" in error for error in errors))
        self.assertTrue(any("independence_attestation" in error for error in errors))

    def test_missing_question_decision_is_rejected(self) -> None:
        review = self._completed_review()
        review["required_questions"][0]["reviewer_decision"] = None
        errors = self._validate_payload(review)
        self.assertTrue(any("reviewer_decision" in error for error in errors))

    def test_missing_rule_review_is_rejected(self) -> None:
        review = self._completed_review()
        review["rule_disposition_review"].pop()
        errors = self._validate_payload(review)
        self.assertTrue(any("every provision-audit rule" in error for error in errors))

    def test_signature_must_match_reviewer_and_date(self) -> None:
        review = self._completed_review()
        review["signature"]["signed_name"] = "Someone Else"
        review["signature"]["signed_on"] = "2026-08-04"
        errors = self._validate_payload(review)
        self.assertTrue(any("signed_name" in error for error in errors))
        self.assertTrue(any("signed_on" in error for error in errors))

    def test_decision_vocabulary_is_closed(self) -> None:
        self.assertEqual(
            QUESTION_DECISIONS,
            {
                "AGREE",
                "AGREE_WITH_NARROWING",
                "DISAGREE",
                "INSUFFICIENT_SOURCE",
                "OUTSIDE_REVIEWER_SCOPE",
            },
        )


if __name__ == "__main__":
    unittest.main()
