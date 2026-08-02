# Candidate executable intermediate representation

## Purpose

The provisional current candidate graph contains typed consequences and activation metadata, but most activation models list required fact names rather than executable legal predicates. This slice converts that graph into a model-relative intermediate representation without inventing missing truth conditions.

## Three compilation modes

### `UNCONDITIONAL_DECLARED`

The candidate rule declares no required activation facts. The intermediate representation preserves that declaration and can evaluate the rule directly. The current graph contains one such rule: the general Vietnam human-control principle, whose source does not identify an obligor in the encoded consequence.

### `EXPLICIT_CATALOG_ROUTE`

The candidate graph explicitly identifies a Decision 33 route and, where relevant, the exact point-a catalog IDs. The compiler can therefore execute the structural catalog-routing predicate:

- listed status;
- route identity;
- point-a membership or point-b exclusion.

Other required facts, such as the before-use/significant-change timing trigger, remain uncompiled unless an explicit model-relative assumption set declares them satisfied.

### `REQUIRED_FACTS_READINESS_ONLY`

The candidate graph names facts that a future predicate needs, but it does not yet encode their polarity, combinations, exceptions or truth conditions. The compiler creates a missing-fact readiness check and returns `INDETERMINATE_PREDICATE_NOT_COMPILED` even when fixture values are supplied. Presence is not treated as predicate truth.

## Evaluation states

```text
NOT_APPLICABLE
APPLICABLE_DETERMINATE
APPLICABLE_UNSPECIFIED_OBLIGOR
APPLICABLE_PARTIALLY_UNSPECIFIED_OBLIGOR
INDETERMINATE_MISSING_FACTS
INDETERMINATE_PREDICATE_NOT_COMPILED
```

Duty evaluations preserve a separate state so an applicable rule with an unnamed obligor cannot be confused with a rule that does not apply.

## Fact bindings

`profiles/current-candidate-2026-08-02/engineering_fact_bindings.json` maps every required-fact name to a typed context-v2 path. These are schema bindings only. They do not define legal meaning or assert that a fact is satisfied.

## Assumption sets

`engineering_assumptions.json` contains two scenarios:

- `NO_ASSUMPTIONS` exposes missing data and uncompiled predicates;
- `ASSUME_ARTICLE13_TIMING_TRIGGER_SATISFIED` exercises the already declared point-a/point-b route split under one explicit synthetic timing assumption.

Under the second scenario, the positive witnesses produce exactly six applicable point-a routes and forty applicable point-b routes. Opposite-route witnesses remain not applicable.

## Reproduction

```bash
PYTHONPATH=src python -m hsdl_gap.candidate_ir
```

`make reproduce` writes:

```text
generated/current-candidate-ir-report.json
```

## Claim boundary

This intermediate representation is an engineering artifact. It proves that declared routing, fact readiness, unknown propagation, duties and assumptions can be executed deterministically. It does not promote the candidate graph, complete generic legal predicates, resolve priority, or authorise current-law percentages.
