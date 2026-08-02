# Jurisdiction-native classification relation

## Purpose

The EU and Vietnam candidate regimes should not be forced into one shared `risk_tier` field. This interface classifies the same factual context independently under each jurisdiction-native model and relates the two outputs only after both are known.

## Native states

Each classifier returns:

```text
IN_SCOPE
OUT_OF_SCOPE
UNKNOWN
```

`UNKNOWN` is distinct from `OUT_OF_SCOPE`. Missing facts never become a negative classification.

## Current native classifiers

### Vietnam

A listed context requires:

- `classification.vn.listed = true`;
- a catalog-item ID;
- an Article 13 assessment route.

Synthetic non-listed controls are out of scope only within the declared fixture model.

### EU

The current interface requires `classification.eu.is_high_risk_ai_system`. When the field is absent, the result is unknown. When true, native Annex/product-route identifiers are preserved when available.

## Cross-jurisdiction relations

The interface reports:

- both in scope, crosswalk required;
- EU-only model scope;
- Vietnam-only model scope;
- neither model scope;
- unknown because at least one native classification lacks facts.

Both-in-scope does not mean equivalent. It explicitly requires a crosswalk.

## Current corpus result

The 322-context Decision 33 corpus contains no EU classification facts. Therefore all 322 cross-jurisdiction relations remain `UNKNOWN_MISSING_FACTS`.

The Vietnam side remains informative:

- 184 in-scope fixtures;
- 46 synthetic out-of-scope controls;
- 92 unknown fixtures missing catalog identity or route.

A five-case synthetic truth table exercises every relation state without promoting those fixtures to legal examples.

## Boundary

The executable interface is complete, but the shared relation is not. Completing it requires EU factual witnesses and an explicit crosswalk; the engine refuses to substitute a common risk-tier shortcut.
