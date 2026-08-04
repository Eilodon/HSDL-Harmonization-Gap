# Generated model-relative technical preview

The generated preview is a technical evidence artifact, not a manuscript.

Its inputs are:

- the model-relative claim ledger;
- freshly reproduced JSON evidence artifacts;
- the section-placement specification;
- the owner governance readiness declaration.

Generation proceeds only when every claim is supported and every ledger claim appears in exactly one section. The rendered Markdown includes each claim's artifact filename, JSON Pointer, actual value and content hash.

## Build

```bash
make reproduce
PYTHONPATH=src python -m hsdl_gap.claim_ledger \
  --ledger claims/model_relative_claims.json \
  --artifact-dir generated \
  > generated/claim-ledger-report.json
PYTHONPATH=src python -m hsdl_gap.generated_publication \
  --spec publication/model_relative_technical_preview_spec.json \
  --ledger claims/model_relative_claims.json \
  --artifact-dir generated \
  --governance-declaration governance/project_identity_declaration.json \
  --repository-root . \
  --markdown-output generated/model-relative-technical-preview.md \
  > generated/generated-publication-preview-report.json
```

## Fail-closed conditions

Generation fails when:

- any evidence value drifts from the claim ledger;
- a claim is unsupported;
- a ledger claim is omitted from the preview specification;
- a claim appears in multiple sections;
- the preview spec asserts legal validation;
- the preview spec authorises publication;
- pending owner governance is bypassed.

## Mandatory banner

Every generated Markdown preview begins with:

```text
NOT AUTHORISED FOR PUBLICATION
```

The preview retains explicit blockers for independent legal review, reviewed crosswalks, durable external custody, owner licence/citation declarations and publication authorisation.

This pipeline eliminates manual copying of technical numbers. It does not replace legal analysis, peer review, author approval or manuscript editing.
