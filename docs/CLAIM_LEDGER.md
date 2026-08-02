# Machine-checked model-relative claim ledger

## Purpose

Generated reports can change while prose remains stale. The claim ledger prevents silent drift by attaching every declared technical claim to one or more generated artifact values through JSON Pointers.

Each evidence reference declares:

- an artifact filename;
- a JSON Pointer;
- an expected value.

The validator reloads freshly reproduced artifacts, resolves every pointer and fails when any actual value differs.

## Current claims

The first ledger covers:

- the 6/46 and 40/46 Decision 33 route composition;
- determinate and indeterminate candidate evaluation counts;
- applicability bounds;
- assumption sensitivity;
- zero exact operational cross-jurisdiction pairs in the declared signatures;
- independent JavaScript/Python oracle equivalence;
- partial symbolic coverage;
- the explicit empty priority graph;
- P0 engineering-gate completion.

## Security and integrity

Artifact references are restricted to plain filenames inside the declared artifact directory. Directory traversal is rejected. Duplicate claim IDs, unresolved JSON Pointers and stale expected values fail validation. Every referenced artifact and the ledger itself are content-hashed.

## CI

The `claim-ledger` workflow performs a clean reproduction, validates the ledger, prints a compact summary and uploads `claim-ledger-report.json`.

## Boundary

A passing claim ledger establishes consistency between declared technical prose and generated values. It does not establish legal validity, empirical prevalence or publication authorisation.
