# Next implementation slices

After this foundation PR is green, continue with independent pull requests:

1. Migrate all 46 Decision 33 witnesses to context v2 and generate rule-linked negative/boundary fixtures.
2. Compile provisional activation metadata into executable condition ASTs under explicit assumption IDs.
3. Add per-duty applicability, partial/unknown states, exception and priority semantics.
4. Implement jurisdiction-native EU and Vietnam classifiers over a shared factual context.
5. Add full operational duty signatures and alignment relation invariants.
6. Implement HSDL Core 0.2 plus an independent TypeScript differential oracle.
7. Implement symbolic region cover with finite-oracle differential tests and counterexamples.
8. Add metric registry, sensitivity analysis and profile-to-profile impact reports.
9. Add source custody/signature records, provenance graph and reproducible release crates.
10. Package an executable computational-policy benchmark.

Each slice must preserve legacy golden results and declare machine-checkable acceptance criteria before downstream work depends on it.
