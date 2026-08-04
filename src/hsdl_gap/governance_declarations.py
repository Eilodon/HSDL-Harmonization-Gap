from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .stable_id import content_sha256


class GovernanceDeclarationError(ValueError):
    """Raised when owner-controlled project identity data is invalid."""


def load_governance_declaration(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GovernanceDeclarationError(f"cannot load governance declaration: {exc}") from exc
    if not isinstance(payload, dict):
        raise GovernanceDeclarationError("governance declaration must be an object")
    return payload


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernanceDeclarationError(f"{label} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise GovernanceDeclarationError(f"{label} must be a string array")
    if not allow_empty and not value:
        raise GovernanceDeclarationError(f"{label} must not be empty")
    return [item.strip() for item in value]


def _people(value: Any, label: str, *, allow_empty: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise GovernanceDeclarationError(f"{label} must be an array")
    if not allow_empty and not value:
        raise GovernanceDeclarationError(f"{label} must not be empty")
    result: list[dict[str, Any]] = []
    for index, person in enumerate(value):
        if not isinstance(person, dict):
            raise GovernanceDeclarationError(f"{label}[{index}] must be an object")
        name = _nonempty_string(person.get("name"), f"{label}[{index}].name")
        record = {"name": name}
        for field in ("given_names", "family_names", "orcid", "affiliation", "email"):
            item = person.get(field)
            if item is not None:
                record[field] = _nonempty_string(item, f"{label}[{index}].{field}")
        roles = person.get("roles", [])
        record["roles"] = _string_list(
            roles, f"{label}[{index}].roles", allow_empty=True
        )
        result.append(record)
    return result


def validate_governance_declaration(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != "1.0.0":
        raise GovernanceDeclarationError("unsupported governance schema_version")
    status = payload.get("status")
    if status not in {"PENDING_OWNER_DECLARATION", "OWNER_APPROVED"}:
        raise GovernanceDeclarationError("unsupported governance declaration status")
    repository = _nonempty_string(payload.get("repository"), "repository")
    owner_account = _nonempty_string(
        payload.get("repository_owner_account"), "repository_owner_account"
    )
    approval = payload.get("owner_approval")
    license_record = payload.get("license")
    citation = payload.get("citation")
    generation = payload.get("generation_policy")
    if not all(isinstance(item, dict) for item in (approval, license_record, citation, generation)):
        raise GovernanceDeclarationError(
            "owner_approval, license, citation and generation_policy must be objects"
        )
    approved = approval.get("approved")
    if not isinstance(approved, bool):
        raise GovernanceDeclarationError("owner_approval.approved must be boolean")
    if approved != (status == "OWNER_APPROVED"):
        raise GovernanceDeclarationError("status and owner approval disagree")

    allowed_choices = _string_list(
        license_record.get("allowed_owner_choices"),
        "license.allowed_owner_choices",
        allow_empty=False,
    )
    title = _nonempty_string(citation.get("title"), "citation.title")
    repository_url = _nonempty_string(
        citation.get("repository_url"), "citation.repository_url"
    )
    preferred_type = _nonempty_string(
        citation.get("preferred_citation_type"),
        "citation.preferred_citation_type",
    )

    blockers: list[str] = []
    authors: list[dict[str, Any]] = []
    contributors: list[dict[str, Any]] = []
    if not approved:
        blockers.extend(
            [
                "OWNER_APPROVAL_MISSING",
                "SPDX_LICENSE_NOT_SELECTED",
                "COPYRIGHT_HOLDERS_NOT_DECLARED",
                "AUTHOR_IDENTITIES_NOT_DECLARED",
                "RELEASE_VERSION_NOT_DECLARED",
            ]
        )
    else:
        _nonempty_string(approval.get("approved_by"), "owner_approval.approved_by")
        _nonempty_string(
            approval.get("approved_at_utc"), "owner_approval.approved_at_utc"
        )
        _nonempty_string(
            approval.get("approval_reference"),
            "owner_approval.approval_reference",
        )
        spdx = _nonempty_string(
            license_record.get("spdx_identifier"), "license.spdx_identifier"
        )
        if spdx not in allowed_choices:
            raise GovernanceDeclarationError(
                "selected SPDX/custom licence is absent from allowed_owner_choices"
            )
        _string_list(
            license_record.get("copyright_holders"),
            "license.copyright_holders",
            allow_empty=False,
        )
        years = license_record.get("copyright_years")
        if not isinstance(years, list) or not years or not all(
            isinstance(year, int) and 1900 <= year <= 2200 for year in years
        ):
            raise GovernanceDeclarationError(
                "license.copyright_years must contain valid integer years"
            )
        if license_record.get("third_party_material_reviewed") is not True:
            blockers.append("THIRD_PARTY_MATERIAL_REVIEW_NOT_CONFIRMED")
        authors = _people(citation.get("authors"), "citation.authors", allow_empty=False)
        contributors = _people(
            citation.get("contributors", []),
            "citation.contributors",
            allow_empty=True,
        )
        _nonempty_string(citation.get("version"), "citation.version")
        _nonempty_string(citation.get("release_date"), "citation.release_date")

    license_allowed = approved and not blockers
    citation_allowed = approved and not blockers
    declared_generation = {
        "license_file_allowed": generation.get("license_file_allowed"),
        "citation_cff_allowed": generation.get("citation_cff_allowed"),
        "release_metadata_allowed": generation.get("release_metadata_allowed"),
    }
    if not all(isinstance(value, bool) for value in declared_generation.values()):
        raise GovernanceDeclarationError("generation policy flags must be boolean")
    if not approved and any(declared_generation.values()):
        raise GovernanceDeclarationError(
            "pending owner declaration cannot enable artifact generation"
        )
    if approved and (
        declared_generation["license_file_allowed"] != license_allowed
        or declared_generation["citation_cff_allowed"] != citation_allowed
        or declared_generation["release_metadata_allowed"] != citation_allowed
    ):
        raise GovernanceDeclarationError(
            "approved generation policy must match validated readiness"
        )

    return {
        "repository": repository,
        "repository_owner_account": owner_account,
        "approved": approved,
        "title": title,
        "repository_url": repository_url,
        "preferred_citation_type": preferred_type,
        "authors": authors,
        "contributors": contributors,
        "blockers": blockers,
        "license_file_allowed": license_allowed,
        "citation_cff_allowed": citation_allowed,
        "release_metadata_allowed": citation_allowed,
    }


def _cff_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_citation_cff(payload: Mapping[str, Any]) -> str:
    validation = validate_governance_declaration(payload)
    if not validation["citation_cff_allowed"]:
        raise GovernanceDeclarationError(
            "CITATION.cff generation is blocked pending owner declaration"
        )
    citation = payload["citation"]
    lines = [
        "cff-version: 1.2.0",
        f"message: {_cff_quote(citation.get('message') or 'Please cite this software.')}",
        f"title: {_cff_quote(citation['title'])}",
        f"type: {citation['preferred_citation_type']}",
        f"version: {_cff_quote(citation['version'])}",
        f"date-released: {_cff_quote(citation['release_date'])}",
        f"repository-code: {_cff_quote(citation['repository_url'])}",
        "authors:",
    ]
    for person in validation["authors"]:
        lines.append(f"  - name: {_cff_quote(person['name'])}")
        if person.get("orcid"):
            lines.append(f"    orcid: {_cff_quote(person['orcid'])}")
        if person.get("affiliation"):
            lines.append(f"    affiliation: {_cff_quote(person['affiliation'])}")
    doi = citation.get("doi")
    if doi:
        lines.append(f"doi: {_cff_quote(doi)}")
    return "\n".join(lines) + "\n"


def build_governance_readiness_report(
    declaration_path: str | Path = "governance/project_identity_declaration.json",
    repository_root: str | Path = ".",
) -> dict[str, Any]:
    payload = load_governance_declaration(declaration_path)
    validation = validate_governance_declaration(payload)
    root = Path(repository_root)
    official_files = {
        "LICENSE": (root / "LICENSE").is_file(),
        "LICENSE.md": (root / "LICENSE.md").is_file(),
        "CITATION.cff": (root / "CITATION.cff").is_file(),
    }
    if not validation["approved"] and any(official_files.values()):
        raise GovernanceDeclarationError(
            "official licence or citation file exists without owner approval"
        )
    return {
        "schema_version": "1.0.0",
        "status": (
            "OWNER_GOVERNANCE_APPROVED_GENERATION_READY"
            if validation["approved"] and not validation["blockers"]
            else "OWNER_GOVERNANCE_DECLARATION_PENDING"
        ),
        "repository": validation["repository"],
        "repository_owner_account": validation["repository_owner_account"],
        "owner_approved": validation["approved"],
        "blockers": validation["blockers"],
        "official_files_present": official_files,
        "generation_readiness": {
            "license_file_allowed": validation["license_file_allowed"],
            "citation_cff_allowed": validation["citation_cff_allowed"],
            "release_metadata_allowed": validation["release_metadata_allowed"],
        },
        "identity_counts": {
            "declared_author_count": len(validation["authors"]),
            "declared_contributor_count": len(validation["contributors"]),
        },
        "declaration_hash": content_sha256(payload),
        "boundary": {
            "repository_account_implies_authorship": False,
            "assistant_may_select_license": False,
            "assistant_may_invent_authors": False,
            "notice": (
                "Only an authorised rights holder may approve licence, copyright "
                "and scholarly identity metadata."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--declaration", default="governance/project_identity_declaration.json"
    )
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--emit-citation", action="store_true")
    args = parser.parse_args()
    payload = load_governance_declaration(args.declaration)
    if args.emit_citation:
        print(render_citation_cff(payload), end="")
        return
    report = build_governance_readiness_report(
        args.declaration, args.repository_root
    )
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
