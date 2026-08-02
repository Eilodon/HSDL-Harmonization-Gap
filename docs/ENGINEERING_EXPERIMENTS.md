# Model-relative engineering experiments

## Purpose

This track allows the repository to execute candidate policy models, generate boundary fixtures and calculate declared corpus metrics without changing the legal-review gates on the current-law candidate profile.

The track is deliberately separate from publication claims. Every experiment report must contain:

- `claim_class = MODEL_RELATIVE`;
- `legal_validation = NOT_ASSERTED`;
- a content hash for the profile;
- a content hash for the corpus;
- the complete assumption-ID set;
- an explicit numerator, denominator and unknown-value policy;
- a claim-boundary notice.

A model-relative result may say:

> Under profile P, corpus C and assumptions A, 12 of 310 declared fixtures meet metric M.

It may not silently become a statement about empirical prevalence, legal validity or the population of deployed AI systems.

## New foundations

### Three-valued conditions

`hsdl_gap.conditions_v2` evaluates conditions as `TRUE`, `FALSE` or `UNKNOWN`. Missing facts are not treated as false. Every result includes an evaluation trace and the set of missing facts.

### Typed fixture corpus

`hsdl_gap.context_v2` distinguishes positive witnesses from generated negative, boundary, unknown, overlap, conflict, temporal and adversarial fixtures. Derived fixtures retain their parent context and mutation provenance.

### Stable identifiers and hashes

`hsdl_gap.stable_id` provides stable typed IDs and canonical SHA-256 hashing for profiles, corpora and generated reports.

### Measure-aware metrics

`hsdl_gap.experiment` requires a metric definition and makes unknown handling explicit. It supports separate-category reporting, exclusion with disclosure, counting unknown as false, and lower/upper bounds.

## Commands

Validate the schema inventory:

```bash
PYTHONPATH=src python -m hsdl_gap.engineering_cli schema-inventory
```

Evaluate one v2 condition against a context:

```bash
PYTHONPATH=src python -m hsdl_gap.engineering_cli evaluate-condition \
  --condition examples/engineering/condition.json \
  --context examples/engineering/context.json
```

Build a model-relative experiment report:

```bash
PYTHONPATH=src python -m hsdl_gap.engineering_cli experiment-report \
  --profile examples/engineering/profile.json \
  --corpus examples/engineering/corpus.json \
  --observations examples/engineering/observations.json \
  --metric-id metric:engineering:example-share \
  --assumption ASSUME_EXAMPLE_EFFECTIVE_DATE
```

Run the full foundation checks and regenerate the demonstration artifact:

```bash
make verify
make reproduce
```

## Compatibility boundary

This foundation does not modify the frozen v11 context model or the canonical legacy evaluator. It is an additive execution lane for later current-profile compilation, per-duty evaluation, differential engines and symbolic cover work.
