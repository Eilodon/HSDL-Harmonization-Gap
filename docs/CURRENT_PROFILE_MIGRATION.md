# Current-profile migration and research gates

## Current verdict

The repository is **execution-ready and publication-blocked**.

Execution-ready means the project now has enough source identity, visual evidence, provision mapping, semantic architecture, regression coverage and migration planning to begin a controlled current-law re-encoding.

Publication-blocked means it does not yet have an independently reviewed current policy model, shared current context universe, current-profile quantitative results or regenerated manuscript claims.

The machine-readable verdict is generated at:

```text
generated/research-gate-status.json
```

## Migration plan

The migration plan is generated from the 23-rule provision audit:

```text
generated/current-profile-migration-plan.json
```

Every legacy rule receives exactly one migration action. The plan separates six workstreams:

1. source validity;
2. ASEAN object typing;
3. obligation-group architecture;
4. rule scope and exceptions;
5. actor relations;
6. typed normative consequences.

The plan does not silently mutate the frozen policy bundle. Replacement rules, retractions and relocations must be added to a separate current profile with implementation evidence and reviewer decisions.

## What may proceed now

The following work is permitted before independent review:

- implement provisional current-profile schemas;
- remove software defects and provable duplicate encodings;
- prepare typed rule graphs whose legal choices remain explicitly provisional;
- add provenance, tests, change logs and reviewer evidence;
- preserve and reproduce the historical model.

A provisional implementation must retain the review dependency. It may not be promoted to a current-law result merely because it executes successfully.

## What remains prohibited

Until every substantive gate passes, the project must not:

- publish current-law directional percentages;
- present the frozen 1,152 flattened gap contexts as exact same-duty actor mismatches;
- reuse H7.1 without a shared EU–Vietnam classification relation and negative cases;
- reuse H7.2 as a single-valued ASEAN harm partition;
- present the finite typed-cover oracle as the symbolic Theorem C implementation;
- claim external HSDL or HolySeed compatibility;
- regenerate final manuscripts as independently reviewed current-law findings.

## Independent review

The packet under `reviews/` contains:

- a human-readable brief;
- an unassigned machine-readable template;
- 11 required legal and policy questions;
- a requirement to review all 23 rule dispositions;
- identity, conflict, independence, date and signature fields.

The repository validates that the template is ready to assign, but the template itself cannot pass as a completed sign-off. A completed record must answer every question and rule disposition.

## Completion sequence

The recommended next sequence is:

1. assign and complete independent review;
2. apply decisions to the migration plan;
3. build the shared current EU–Vietnam classification relation;
4. encode current EU and Vietnam typed policy graphs;
5. add negative and boundary contexts beyond the 46 positive Decision 33 witnesses;
6. run current-profile HSDL differential and typed-cover audits;
7. generate a reason-coded legacy-to-current change log;
8. regenerate results and manuscript claims only after all gates pass.

## Reproduction

Run:

```bash
make reproduce
```

This validates the historical model, source audit, reviewer packet, migration plan and unified gate verdict. It does not download sources; live checksum verification remains a separate command:

```bash
make verify-sources
```
