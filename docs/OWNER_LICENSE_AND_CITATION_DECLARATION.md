# Owner-controlled licence and citation declaration

The repository intentionally does not infer a licence, copyright holder, scholarly author or contributor from a GitHub account name.

`governance/project_identity_declaration.json` is the sole machine-readable owner decision point. Its default state is:

```text
status = PENDING_OWNER_DECLARATION
owner_approval.approved = false
license.spdx_identifier = null
citation.authors = []
```

While the declaration is pending:

- no `LICENSE` or `LICENSE.md` may be introduced;
- no official `CITATION.cff` may be introduced;
- release identity metadata remains blocked;
- the repository owner account is not treated as a scholarly author;
- automation and assistants must not select a licence or invent people.

## Owner decision checklist

An authorised rights holder must provide all of the following in one reviewed change:

1. approval name, timestamp and an issue/decision reference;
2. selected SPDX licence or a declared custom/proprietary choice;
3. copyright holder names and years;
4. confirmation that third-party materials were reviewed for the selected licence scope;
5. author names and, when applicable, ORCID and affiliations;
6. contributor names and roles;
7. release version and release date;
8. DOI or persistent identifier when one exists;
9. corresponding-author, funding and conflict disclosures for publication use.

The generation flags may be switched to `true` only when the declaration validates as `OWNER_APPROVED` with no blockers.

## Citation generator

After approval, the repository can render `CITATION.cff` from the declaration:

```bash
PYTHONPATH=src python -m hsdl_gap.governance_declarations \
  --declaration governance/project_identity_declaration.json \
  --emit-citation > CITATION.cff
```

The generator refuses to run against a pending or incomplete declaration.

## Licence file

The declaration records whether licence-file creation is authorised. The actual canonical licence text must be obtained from the selected licence's authoritative source or supplied by the rights holder for a custom licence. This repository does not synthesize or paraphrase licence terms.
