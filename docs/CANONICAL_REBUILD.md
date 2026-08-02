# Canonical research spine: first vertical slice

This change set begins the controlled rebuild without altering or deleting the frozen hackathon-era scripts.

## What is canonical in this slice

- `policies/legacy_v11.json` is the single machine-readable source for the reconstructed legacy EU, Vietnam and ASEAN mini-regimes.
- `src/hsdl_gap/` contains a dependency-free Python oracle.
- Duties preserve action, object, obligor, recipient, timing and primary/fallback actor relations.
- Evaluation distinguishes `NO_APPLICABLE_RULE`, `UNSPECIFIED_OBLIGOR`, `DETERMINATE` and the reserved `PRIORITY_INDETERMINATE` state.
- Legacy flattened-obligor metrics remain available solely for exact historical regression.

## What this slice deliberately does not claim

- It is not a current-law legal freeze.
- Decision 33/2026/QĐ-TTg is not yet encoded.
- The ASEAN taxonomy has not yet been rebuilt as a multi-label ontology.
- It is not yet an HSDL/HolySeed execution path.
- The legal annotations have not received independent expert review.

## Reproduction

```bash
make reproduce
```

The command runs regression and semantic tests, then writes `generated/legacy-v11-results.json`.

## Locked legacy results

The test suite locks the 2,880-context space, all six per-group directional-gap tuples, union counts, multi-rule counts, obligor-gap counts, the corrected `ctx*` firing set, and the distinction between regulatory silence and unnamed obligors.

## Next change sets

1. Add official legal-source snapshots, hashes and provision-level annotations.
2. Encode Decision 33 row by row and classify every changed result by reason code.
3. Replace legacy flat obligor comparison with typed-duty alignment and declared conflict classes.
4. Rebuild ASEAN objects as principles, governance practices and multi-label GenAI risks.
5. Add HSDL generation/evaluation and full-space differential testing.
