# Model-relative metrics and sensitivity

## Rule: no percentage without a declared population

Every metric in this repository must declare:

- profile and corpus identity;
- assumption scenario;
- finite population;
- numerator states;
- denominator definition;
- unknown states and handling policy;
- interpretation boundary.

A number such as `6 / 46` is a share of Decision 33 catalog rows in the positive-witness inventory. It is not a share of deployed AI systems. A number such as `690 / 6,440` is a share of candidate rule-context evaluations. The two populations are not interchangeable.

## Registry

`metrics/model_relative_registry.json` is the source of truth for metric definitions. The loader rejects duplicate IDs and any metric that places the same evaluation state in both its numerator and unknown categories.

The first registry includes:

- point-a positive catalog-row share;
- point-b positive catalog-row share;
- determinate candidate rule-context outcome share;
- lower/upper bounds for candidate applicability when indeterminate evaluations remain unresolved;
- indeterminate candidate rule-context outcome share.

## Unknown handling

Supported policies are:

- `COUNT_AS_SEPARATE_CATEGORY`;
- `EXCLUDE_AND_REPORT`;
- `LOWER_UPPER_BOUND`.

The applicability metric uses bounds rather than silently treating every unknown as false. Its lower bound counts only currently determined applicable evaluations. Its upper bound additionally treats every indeterminate evaluation as potentially applicable.

## Current finite populations

### Positive Decision 33 witnesses

Population size: 46 catalog-row witnesses.

Under the explicit synthetic timing assumption:

- point-a route: 6 / 46;
- point-b route: 40 / 46.

These are source-inventory composition measures.

### Candidate rule-context evaluations

Population size:

```text
20 compiled rules × 322 contexts = 6,440 evaluations
```

Under `NO_ASSUMPTIONS`, the partial IR produces:

- 690 determinate outcomes;
- 5,750 indeterminate outcomes;
- 322 currently applicable outcomes;
- applicability lower bound `322 / 6,440`;
- applicability upper bound `(322 + 5,750) / 6,440`.

These values measure engineering completeness of this IR, not legal certainty or real-world frequency.

## Sensitivity

The report compares `NO_ASSUMPTIONS` with `ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED` over the same 6,440 evaluation keys.

Exactly 184 evaluations change:

```text
INDETERMINATE_MISSING_FACTS → APPLICABLE_DETERMINATE
```

All changes belong to the two explicitly compiled Article 13 catalog routes. The remaining rules are unaffected because the alternative assumption set does not fill or define their predicates.

## Reproduction

```bash
PYTHONPATH=src python -m hsdl_gap.metric_analysis
```

`make reproduce` writes:

```text
generated/model-relative-metric-analysis.json
```

## Claim boundary

The report always sets:

```text
claim_class = MODEL_RELATIVE
legal_validation = NOT_ASSERTED
empirical_prevalence = NOT_SUPPORTED
```

The metric layer cannot promote the candidate graph or authorise current-law comparative claims.
