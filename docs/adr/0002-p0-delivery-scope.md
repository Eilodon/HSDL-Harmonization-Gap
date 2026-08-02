# ADR 0002: Deliver P0 as additive foundation slices

- Status: Accepted
- Date: 2026-08-02

## Decision

The engineering roadmap will be delivered as small, reviewable pull requests rather than another all-in-one canonical rebuild commit.

This first slice establishes schema contracts, stable IDs, three-valued conditions, typed fixtures, measure-aware experiment envelopes and integration with the existing reproduction command. It intentionally does not compile the current candidate graph, replace the legacy evaluator or implement symbolic typed cover.

Subsequent slices will build on these stable interfaces in this order:

1. current-context migration and generated negative/boundary corpus;
2. candidate-profile compiler and per-duty evaluator;
3. EU–Vietnam classification relation;
4. HSDL Core 0.2 and independent differential engine;
5. typed alignment v2, symbolic cover and measure registry;
6. provenance, release packaging and benchmark layers.

## Consequences

Each pull request can preserve legacy golden outputs, publish explicit acceptance criteria and use CI evidence before the next layer depends on it.
