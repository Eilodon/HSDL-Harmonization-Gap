# ADR 0001: Separate model-relative experiments from current-law claims

- Status: Accepted
- Date: 2026-08-02

## Context

The provisional current candidate graph correctly disables current-law percentages and actor-mismatch metrics while independent review, a shared classification relation and negative/boundary contexts remain incomplete. Engineering work nevertheless needs an executable lane for validating schemas, conditions, fixture generators, measures and reports.

Changing the existing safety flags would conflate two different questions:

1. Does the software execute a declared model reproducibly?
2. Is that model an independently validated statement of current law?

The repository can answer the first question before it can answer the second.

## Decision

Create a separate model-relative experiment lane. It must never mutate or promote the candidate graph's legal-review status.

Every experiment artifact records profile and corpus hashes, assumptions, measure definitions, unknown handling and a non-legal claim boundary. The only permitted claim class in this lane is `MODEL_RELATIVE`; legal validation is always `NOT_ASSERTED`.

## Consequences

- Candidate models and synthetic corpora can be executed and regression-tested now.
- Quantitative engineering outputs can be compared across commits without being presented as empirical prevalence or legal conclusions.
- Legal-review gates remain intact.
- Later reviewed profiles may reuse the same execution machinery while changing only their attestation and source-review records.
