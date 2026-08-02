from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


QUESTION_DECISIONS = {
    "AGREE",
    "AGREE_WITH_NARROWING",
    "DISAGREE",
    "INSUFFICIENT_SOURCE",
    "OUTSIDE_REVIEWER_SCOPE",
}

OVERALL_DECISIONS = {
    "APPROVE_FOR_REENCODING",
    "APPROVE_WITH_REQUIRED_CHANGES",
    "REQUIRES_FURTHER_SOURCE_WORK",
    "REJECT_CURRENT_CROSSWALK",
}


class ReviewerSignoffError(ValueError):
    """Raised when an independent-review record violates the sign-off contract."""


def _load(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReviewerSignoffError("review document must be a JSON object")
    return payload


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_iso_date(value: Any) -> bool:
    if not _nonempty_string(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_review_template(
    template_path: str | Path,
    provision_audit_path: str | Path,
) -> list[str]:
    template = _load(template_path)
    audit = _load(provision_audit_path)
    errors: list[str] = []

    if template.get("schema_version") != "1.0.0":
        errors.append("unsupported review-template schema_version")
    if template.get("review_status") != "UNASSIGNED_TEMPLATE":
        errors.append("repository template must remain UNASSIGNED_TEMPLATE")
    if template.get("review_id") is not None:
        errors.append("repository template must not contain a review_id")
    if template.get("source_lock_id") != audit.get("source_lock_id"):
        errors.append("review template source_lock_id differs from provision audit")
    if template.get("provision_audit_id") != audit.get("audit_id"):
        errors.append("review template provision_audit_id differs from provision audit")

    questions = template.get("required_questions")
    if not isinstance(questions, list) or not questions:
        errors.append("required_questions must be a non-empty list")
    else:
        ids: list[str] = []
        for index, question in enumerate(questions):
            prefix = f"required_questions[{index}]"
            if not isinstance(question, dict):
                errors.append(f"{prefix} must be an object")
                continue
            question_id = question.get("id")
            if not _nonempty_string(question_id):
                errors.append(f"{prefix}.id must be non-empty")
            else:
                ids.append(question_id)
            if not _nonempty_string(question.get("question")):
                errors.append(f"{prefix}.question must be non-empty")
            if not _nonempty_string(question.get("proposed_answer")):
                errors.append(f"{prefix}.proposed_answer must be non-empty")
            if question.get("reviewer_decision") is not None:
                errors.append(f"{prefix} must not be pre-decided")
            if question.get("reasoning") is not None:
                errors.append(f"{prefix} must not contain prewritten reviewer reasoning")
        if len(set(ids)) != len(ids):
            errors.append("required question IDs must be unique")

    reviewer = template.get("reviewer")
    if not isinstance(reviewer, dict):
        errors.append("reviewer must be an object")
    else:
        populated = [value for value in reviewer.values() if value not in (None, [], "")]
        if populated:
            errors.append("repository template must not contain reviewer identity")

    if template.get("reviewed_on") is not None:
        errors.append("repository template must not contain a review date")
    if template.get("overall_decision") is not None:
        errors.append("repository template must not contain an overall decision")
    if template.get("rule_disposition_review") != []:
        errors.append("repository template rule_disposition_review must begin empty")
    return errors


def validate_completed_review(
    review_path: str | Path,
    template_path: str | Path,
    provision_audit_path: str | Path,
) -> list[str]:
    review = _load(review_path)
    template = _load(template_path)
    audit = _load(provision_audit_path)
    errors: list[str] = []

    if review.get("schema_version") != "1.0.0":
        errors.append("unsupported completed-review schema_version")
    if review.get("review_status") != "COMPLETED":
        errors.append("completed review_status must be COMPLETED")
    if not _nonempty_string(review.get("review_id")):
        errors.append("completed review requires a review_id")
    if review.get("source_lock_id") != template.get("source_lock_id"):
        errors.append("completed review source_lock_id differs from template")
    if review.get("provision_audit_id") != template.get("provision_audit_id"):
        errors.append("completed review provision_audit_id differs from template")

    reviewer = review.get("reviewer")
    if not isinstance(reviewer, dict):
        errors.append("completed review requires reviewer metadata")
        reviewer = {}
    for field in ("full_name", "professional_role"):
        if not _nonempty_string(reviewer.get(field)):
            errors.append(f"reviewer.{field} must be non-empty")
    jurisdictions = reviewer.get("jurisdictions_reviewed")
    if not isinstance(jurisdictions, list) or not jurisdictions or not all(
        _nonempty_string(value) for value in jurisdictions
    ):
        errors.append("reviewer.jurisdictions_reviewed must be a non-empty string list")
    if not _nonempty_string(reviewer.get("conflicts_disclosed")):
        errors.append("reviewer.conflicts_disclosed must be explicit")
    if reviewer.get("independence_attestation") is not True:
        errors.append("reviewer.independence_attestation must be true")
    if not _valid_iso_date(review.get("reviewed_on")):
        errors.append("reviewed_on must be an ISO date")

    expected_questions = template.get("required_questions", [])
    expected_ids = {
        question.get("id")
        for question in expected_questions
        if isinstance(question, dict)
    }
    actual_questions = review.get("required_questions")
    if not isinstance(actual_questions, list):
        errors.append("completed review required_questions must be a list")
        actual_questions = []
    actual_ids: list[str] = []
    for index, question in enumerate(actual_questions):
        prefix = f"required_questions[{index}]"
        if not isinstance(question, dict):
            errors.append(f"{prefix} must be an object")
            continue
        question_id = question.get("id")
        if _nonempty_string(question_id):
            actual_ids.append(question_id)
        decision = question.get("reviewer_decision")
        if decision not in QUESTION_DECISIONS:
            errors.append(f"{prefix}.reviewer_decision is invalid: {decision!r}")
        if not _nonempty_string(question.get("reasoning")):
            errors.append(f"{prefix}.reasoning must be non-empty")
        required_change = question.get("required_change")
        if required_change is not None and not _nonempty_string(required_change):
            errors.append(f"{prefix}.required_change must be null or non-empty")
    if set(actual_ids) != expected_ids:
        errors.append("completed review must answer exactly all required question IDs")
    if len(actual_ids) != len(set(actual_ids)):
        errors.append("completed review contains duplicate question IDs")

    audit_rule_ids = {
        row.get("rule_id")
        for row in audit.get("rules", [])
        if isinstance(row, dict)
    }
    rule_reviews = review.get("rule_disposition_review")
    if not isinstance(rule_reviews, list):
        errors.append("rule_disposition_review must be a list")
        rule_reviews = []
    reviewed_rule_ids: list[str] = []
    for index, item in enumerate(rule_reviews):
        prefix = f"rule_disposition_review[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        rule_id = item.get("rule_id")
        if _nonempty_string(rule_id):
            reviewed_rule_ids.append(rule_id)
        if item.get("reviewer_decision") not in QUESTION_DECISIONS:
            errors.append(f"{prefix}.reviewer_decision is invalid")
        if not _nonempty_string(item.get("reasoning")):
            errors.append(f"{prefix}.reasoning must be non-empty")
    if set(reviewed_rule_ids) != audit_rule_ids:
        errors.append("completed review must cover every provision-audit rule exactly")
    if len(reviewed_rule_ids) != len(set(reviewed_rule_ids)):
        errors.append("completed review contains duplicate rule reviews")

    if review.get("overall_decision") not in OVERALL_DECISIONS:
        errors.append("overall_decision is invalid")
    if not _nonempty_string(review.get("overall_reasoning")):
        errors.append("overall_reasoning must be non-empty")

    signature = review.get("signature")
    if not isinstance(signature, dict):
        errors.append("signature must be an object")
    else:
        if not _nonempty_string(signature.get("method")):
            errors.append("signature.method must be non-empty")
        if signature.get("signed_name") != reviewer.get("full_name"):
            errors.append("signature.signed_name must match reviewer.full_name")
        if signature.get("signed_on") != review.get("reviewed_on"):
            errors.append("signature.signed_on must match reviewed_on")
    return errors


def build_review_readiness_report(
    template_path: str | Path,
    provision_audit_path: str | Path,
) -> dict[str, Any]:
    template = _load(template_path)
    audit = _load(provision_audit_path)
    errors = validate_review_template(template_path, provision_audit_path)
    questions = template.get("required_questions", [])
    audit_rows = audit.get("rules", [])
    return {
        "schema_version": "1.0.0",
        "status": "READY_FOR_ASSIGNMENT" if not errors else "INVALID_TEMPLATE",
        "template_path": str(template_path),
        "source_lock_id": template.get("source_lock_id"),
        "provision_audit_id": template.get("provision_audit_id"),
        "required_question_count": len(questions) if isinstance(questions, list) else 0,
        "required_rule_review_count": len(audit_rows) if isinstance(audit_rows, list) else 0,
        "validation_errors": errors,
        "gate": {
            "independent_reviewer_assigned": False,
            "completed_signoff_present": False,
            "current_law_quantitative_claims": "BLOCKED",
            "manuscript_regeneration": "BLOCKED",
        },
        "notice": (
            "READY_FOR_ASSIGNMENT means the review packet is structurally complete. "
            "It does not mean independent review has occurred."
        ),
    }
