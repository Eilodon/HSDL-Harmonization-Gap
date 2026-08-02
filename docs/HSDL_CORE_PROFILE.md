# HSDL Core 0.1 reference profile

## Purpose

The frozen manuscripts describe the comparative policies using HSDL notation, but the hackathon repository executed independent Python predicates rather than committed HSDL source files. This profile closes that reproducibility gap without claiming compatibility with an unavailable or unverified external implementation.

`HSDL Core 0.1` is a repository-defined, line-oriented executable interchange profile. It serializes the canonical policy and typed-duty model, parses it back into the same domain objects, and evaluates the parsed result through the reference oracle.

## Claim boundary

A successful differential run proves:

- every canonical policy can be serialized into the profile;
- the profile can be parsed without information loss;
- the parsed policies produce the same evaluation state, active rules, bindingness and typed duties across every frozen context, jurisdiction and obligation group.

It does **not** prove:

- compatibility with an external HSDL or HolySeed parser;
- conformance to a third-party language specification;
- current-law validity of the frozen policy encoding;
- correctness of the legal interpretations encoded in the canonical model.

The generated differential report therefore sets `upstream_engine_compatibility` to `NOT_CLAIMED`.

## Grammar

A document begins with:

```text
@hsdl-core 0.1
```

It then contains policy blocks:

```text
policy {JSON metadata}
rule {JSON metadata}
when {JSON condition AST}
duty {JSON typed normative consequence}
endrule
endpolicy
```

JSON objects are emitted with sorted keys and compact separators. The parser rejects unknown statements, nested policies, rules outside policies, duplicate jurisdictions, missing `when` clauses, unknown bindingness values and incomplete blocks.

## Semantic payload

The profile preserves:

- policy identity, jurisdiction and version;
- rule identity, obligation group, instrument and provision;
- bindingness;
- source and interpretation status;
- the complete condition AST;
- duty action and object;
- obligors and actor relation;
- recipient and timing;
- broad alignment key;
- exact normative slot;
- conflict class.

## Reproduction

Run:

```bash
make reproduce
```

The command emits:

- `generated/legacy-v11.hsdl`
- `generated/hsdl-differential-report.json`

The differential gate fails when any canonical and parsed evaluation differs.

## Future compatibility work

External compatibility should be added only after an identifiable implementation and grammar are available. That work must use an adapter and differential tests rather than silently renaming this reference profile as upstream HSDL.
