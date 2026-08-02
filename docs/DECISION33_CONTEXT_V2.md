# Decision 33 context v2 corpus

## Purpose

The original current-context report preserves 46 positive catalog witnesses. This slice migrates those witnesses into the typed context-v2 model and adds deterministic controls for branches that a positive-only catalog cannot exercise.

The corpus remains model-relative. It is a test corpus, not an estimate of the number or proportion of deployed AI systems covered by Decision 33.

## Corpus contract

Every one of the 46 catalog rows produces exactly seven contexts:

1. the source-derived positive witness;
2. a synthetic non-listed control;
3. a fixture with the catalog-item identity omitted;
4. a fixture with the Article 13 assessment route omitted;
5. an evaluation one day before the effective date;
6. an evaluation exactly on the effective date;
7. an evaluation one day after the effective date.

The resulting corpus contains 322 contexts:

- 46 positive witnesses;
- 46 single-fault negative controls;
- 92 unknown-fact fixtures;
- 46 below-boundary fixtures;
- 46 exact-boundary fixtures;
- 46 above-boundary fixtures.

The positive witnesses preserve the visually verified Article 13 route split:

- 6 point-a third-party-certification rows;
- 40 point-b provider-self-or-third-party rows.

## Provenance

Positive contexts distinguish catalog transcription from author-derived keyword grouping. Every generated fixture records:

- its positive parent context;
- a stable mutation ID;
- the exact mutation operation;
- `SYNTHETIC_FIXTURE` provenance;
- `legal_validation = NOT_ASSERTED`.

The non-listed controls are deliberately described as test controls. They do not assert that the named real-world use case is legally outside the catalog.

## Reproduction

```bash
PYTHONPATH=src python -m hsdl_gap.decision33_context_v2 \
  --catalog catalogs/vn_decision_33_2026.csv
```

`make reproduce` writes the report to:

```text
generated/decision33-context-v2-corpus.json
```

## Downstream use

This corpus provides inputs for the next slices:

- compiling candidate activation metadata into executable conditions;
- testing unknown propagation;
- testing effective-date applicability;
- implementing jurisdiction-native classifiers;
- differential testing JSON and HSDL execution;
- producing measure-aware model-relative metrics.

It does not close the shared EU–Vietnam classification gate by itself.
