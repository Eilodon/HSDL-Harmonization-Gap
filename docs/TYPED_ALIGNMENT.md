# Typed-duty alignment and conflict-class gate

This audit separates three questions that the frozen `omega` set collapsed:

1. Do two rules address the same broad regulatory function (`alignment_key`)?
2. Do they impose the same concrete normative duty (`normative_slot`)?
3. Only when the normative slot is the same, do the responsible actors differ?

A provider classification duty and a regulator inspection duty may coexist in the
same risk-governance bundle. They are not competing actor assignments for one duty,
so `lex specialis` is not applicable and their actor sets must not be compared as
though one replaces the other.

## Conflict classes

Priority resolution is now opt-in. A duty participates only when it declares a
non-null `conflict_class`, and every duty in that class must share exactly one
`normative_slot`. Multiple active duties in a declared class remain
`PRIORITY_INDETERMINATE` until an explicit legal priority rule is encoded.
Syntactic condition count is not treated as legal priority.

## Legacy audit result

The frozen flattened metric still reproduces 1,152 distinct EU–Vietnam obligor-gap
contexts. Under exact typed comparison, no context currently contains an actor
mismatch within the same explicit normative slot. The same 1,152-context union
requires crosswalk review because it contains structural duty differences,
analogies, cross-functional bundles, or an unnamed obligor.

This is not yet a final legal conclusion. The crosswalk is author-interpreted and
must receive a second legal review. Its purpose is to prevent the implementation
from silently upgrading analogical comparisons into exact actor mismatches.
