# P0 engineering foundation changelog

## Added

- Three-valued truth semantics and condition evaluation traces.
- Stable typed identifiers and canonical SHA-256 content hashing.
- Context v2 fixtures with parent/mutation provenance.
- Numeric below/exact/above/unknown boundary generation.
- Measure-aware model-relative experiment envelopes.
- Draft 2020-12 schemas for conditions, contexts, experiment reports and stable IDs.
- Engineering CLI, examples and deterministic demo artifacts.
- Regression tests for the new foundation.

## Changed

- `make reproduce` now runs `make verify` first.
- Package metadata exposes canonical and engineering CLI entry points.
- Canonical README documents the additive engineering lane.

## Unchanged

- Frozen v11 policy/context behavior and golden results.
- Provisional current-law evaluation locks and publication gates.
- Existing HSDL Core 0.1 and finite typed-cover semantics.
