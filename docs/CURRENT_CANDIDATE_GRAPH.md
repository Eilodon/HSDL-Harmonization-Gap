# Provisional current-law typed rule graph

## Purpose

`policies/current_candidate_graph_2026-08-02.json` is an implementation scaffold for the current-law rebuild. It applies source-audited structural corrections while keeping every legally review-dependent choice visibly provisional.

It is **not** the current quantitative policy profile.

## Structural corrections already represented

The candidate graph:

- removes the duplicate EU Article 9 rule previously counted in both G1 and G6;
- retracts the unsupported Vietnam Article 13 sector-certification reuse rule;
- retracts the generic Decree 142 G6 event-control abstraction;
- separates EU provider and deployer duties;
- preserves Article 43 procedure and third-party-assessment structure;
- represents Vietnam Article 10(2) as deployer responsibility with provider coordination;
- separates Decision 33 point-a and point-b conformity routes;
- expands Decree 142 Article 19 into record, mitigation, notification, remediation, coordination, reporting and conditional fallback duties;
- moves ASEAN principles and policy recommendations out of the binding entity-rule graph.

## Quantitative prohibition

The graph declares and the validator enforces:

```text
quantitative_evaluation_allowed = false
directional_gap_metrics_allowed = false
actor_mismatch_metrics_allowed = false
```

The graph cannot be used to generate current-law percentages, directional gap counts or actor-mismatch counts. It lacks an independently reviewed shared context universe, negative and boundary cases, a completed current classification relation and reviewed policy predicates.

## Validation contract

`src/hsdl_gap/current_candidate.py` rejects the graph when it:

- enables any prohibited metric;
- reintroduces the frozen `Unacceptable`-tier shortcut;
- reintroduces a removed or ASEAN legacy rule into the binding graph;
- omits typed action, object, obligor relation or timing fields;
- duplicates a normative slot without an explicit conflict model;
- changes the six Decision 33 point-a catalog IDs or the 40 point-b count;
- omits any required Decree 142 Article 19 duty slot;
- promotes an ASEAN principle or recommendation back into a binding rule type;
- claims that independent review or publication gates have passed.

Run:

```bash
make reproduce
```

The command writes:

```text
generated/current-candidate-audit.json
```

A valid result is:

```text
VALIDATED_PROVISIONAL_GRAPH
```

That status proves structural completeness and safety gates only. It is not legal sign-off.

## Review dependency

Every binding candidate rule remains `PENDING_INDEPENDENT_REVIEW`. The review packet under `reviews/` asks the reviewer to confirm or change the disputed actor, scope, route and crosswalk choices.

Reviewer decisions must be applied through the 23-rule migration plan. The candidate graph should then be replaced by a separately versioned reviewed profile rather than silently relabelled as final.

## Promotion requirements

Before the graph can become a current quantitative model, the project must complete:

1. independent legal and policy review;
2. shared current EU–Vietnam classification relation;
3. negative and boundary contexts beyond the 46 positive Decision 33 witnesses;
4. reviewed current predicates and typed consequence graphs;
5. current-profile HSDL round-trip and differential evaluation;
6. current-profile typed-cover audit;
7. reason-coded legacy-to-current change log;
8. manuscript regeneration from the reviewed outputs.
