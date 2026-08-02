# Typed finite cover oracle

## Problem repaired

The frozen refinement analysis compared unlabeled support sets. Equal or nested supports could therefore be interpreted across unrelated obligation domains, and the implementation retained duplicate rule blocks even though the manuscript notation used an ordinary set that would collapse equal supports.

The typed finite cover oracle separates those concerns explicitly.

## Block identity

Each indexed block represents one rule-duty pair:

```text
(rule id, duty id, group, semantic label, support)
```

The support is the set of frozen context indices in which the rule fires. A block is never compared with a block from another obligation group or semantic label.

Two label modes are reported:

- `exact`: group plus `normative_slot`;
- `broad`: group plus `alignment_key`.

The broad mode is an issue-spotting view. It must not be presented as proof that the duties are legally equivalent.

## Indexed and quotient covers

The indexed cover preserves every rule-duty identity, including two distinct rules with equal support.

The quotient cover collapses blocks only when all three values are equal:

1. obligation group;
2. semantic label;
3. support set.

The output reports the number of duplicate support-label blocks collapsed for every jurisdiction and label mode.

## Directed refinement

A source cover refines a target cover only when every source block has at least one target witness satisfying:

```text
same group
same semantic label
source support is a subset of target support
```

The report records a witness for every covered block and diagnostics for every uncovered block.

## Complexity and claim boundary

This implementation is deliberately a finite oracle over the 2,880 frozen contexts:

- support construction: `O(|Ctx| * |Rules|)`;
- worst-case pairwise refinement: `O(|Blocks_A| * |Blocks_B| * |Ctx|)`.

It uses Python `frozenset` inclusion. It does not implement the symbolic per-dimension algorithm claimed by the frozen Theorem C and therefore does not claim the manuscript's `O(|P_A||P_B|k)` bound.

## Theorem disposition

The generated report gates the old statements as follows:

- H8: withdraw and replace with a labeled typed-cover definition;
- Theorem C implementation claim: not implemented by this finite oracle;
- replacement finite claim: directed refinement on the frozen context space is decidable by label-preserving support inclusion over indexed or quotient typed blocks.

A later symbolic implementation may recover a parameterized complexity result, but it must operate on typed symbolic regions and be differential-tested against this finite oracle.

## Reproduction

Run:

```bash
make reproduce
```

The command emits `generated/typed-cover-audit.json`.

## Legal limitation

A failed refinement may result from genuine architectural divergence, an incomplete legal crosswalk or a mistaken semantic label. The matrix is a formal diagnostic, not independent legal sign-off.
