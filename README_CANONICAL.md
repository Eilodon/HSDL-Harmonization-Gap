# Canonical rebuild and engineering experiment lane

The original v11 scripts and manuscripts remain the frozen historical baseline. The canonical research spine provides:

- machine-readable policy bundles;
- typed normative duties;
- explicit evaluation states;
- a dependency-free Python oracle;
- golden regression tests;
- one-command reproduction and CI artifacts.

The additive engineering lane now also provides:

- JSON Schema Draft 2020-12 contracts for stable IDs, conditions, contexts and experiment reports;
- three-valued condition evaluation (`TRUE`, `FALSE`, `UNKNOWN`);
- traceable positive, negative, boundary and unknown fixtures;
- canonical content hashes for profiles and corpora;
- model-relative metrics with explicit measures and unknown handling;
- an experiment report that cannot assert legal validation.

Run:

```bash
make verify
make reproduce
```

The original current-law publication gates remain unchanged. Engineering experiment outputs describe only their declared profile, corpus and assumptions.

See:

- [`docs/CANONICAL_REBUILD.md`](docs/CANONICAL_REBUILD.md)
- [`docs/ENGINEERING_EXPERIMENTS.md`](docs/ENGINEERING_EXPERIMENTS.md)
- [`docs/adr/0001-model-relative-experiment-lane.md`](docs/adr/0001-model-relative-experiment-lane.md)
