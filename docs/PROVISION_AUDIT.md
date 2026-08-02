# Provision-level audit

## Purpose

The frozen policy bundle is preserved as a historical reconstruction. It must not be treated as a current-law encoding merely because its aggregate counts reproduce. The provision audit maps every frozen rule to the exact source provision or policy section, records what the source supports, and states whether the rule can be retained, narrowed, retyped, re-encoded or withdrawn.

The canonical audit is:

```text
sources/reviews/legacy_v11_provision_audit.json
```

The generated validation report is:

```text
generated/provision-audit-report.json
```

## Evidence basis

The audit uses the checksum-pinned official-source lock. For Vietnamese scanned instruments, the relevant pages were inspected from derivatives generated only after the downloaded bytes matched the pinned size and SHA-256. For the EU and ASEAN PDFs, the official text layers were used together with exact PDF page locators.

The audit is an author-and-assistant source review. It is not independent legal advice, signature validation or second-reviewer sign-off.

## Coverage contract

Every rule in `policies/legacy_v11.json` must appear exactly once in the audit. CI rejects:

- missing or unknown rule IDs;
- duplicate audit entries;
- empty source locators;
- invalid PDF page numbers;
- unknown dispositions;
- missing findings or required changes;
- inconsistent summary counts;
- a silent claim of independent legal review.

## Dispositions

The audit distinguishes:

- source-confirmed rules that need narrower scope;
- actor, action or typed-consequence re-encoding;
- duplicate cross-group encodings;
- rules unsupported by their cited provision;
- ASEAN principles or policy recommendations that should not be represented as entity-level legal rules.

A source-confirmed provision can still be a publication blocker when the current predicate or consequence is too coarse to support the manuscript claim.

## High-impact findings

The current audit records, among other corrections:

- the duplicate use of EU Article 9 in G1 and G6;
- the provider-only encoding of Vietnam Article 10(2), despite the deployer responsibility and provider-coordination structure;
- the flattening of Vietnam Article 13's point-a and point-b conformity routes;
- the absence of support in Article 13 for automatic reuse of existing sector certification;
- the multi-duty and timed structure of Decree 142 Article 19;
- the absence of support for the generic G6 `control_risk` rule;
- the need to move ASEAN principles and content-provenance recommendations out of the statutory-rule layer.

## Promotion gate

Until the affected rules are re-encoded and independently reviewed:

- legacy numerical outputs are historical-only;
- current-law quantitative outputs remain blocked;
- manuscript regeneration remains blocked.

This is deliberate. Reproducibility of an old model is evidence about that model, not evidence that the model remains legally valid.

## Reproduction

Run:

```bash
make reproduce
```

The command validates the audit and writes `generated/provision-audit-report.json`. An invalid audit exits non-zero.
