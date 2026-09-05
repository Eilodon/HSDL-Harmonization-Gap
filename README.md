> **Current research status.** This README preserves the frozen v11 Sprint baseline. For the source-audited current-law rebuild, typed engineering lane, and present claim boundaries, start with [`README_CANONICAL.md`](README_CANONICAL.md). Current-law quantitative gap and actor-mismatch metrics remain blocked pending the required independent legal/policy review and reviewed crosswalks.

# HSDL Harmonization Gap v11 — Final Package

**Date**: 21/6/2026
**Version**: v11 (from v10, +361 lines)

## What's in this package

### Main deliverable
- `HSDL-Harmonization-Gap-v11.md` — full paper, ~1,307 lines

### Verification scripts (Python 3, no external deps; combined runtime <1s)
- `verify_proposals.py` — initial fact-check on co-firing counts, pairwise relations, syntactic tie counts, G4 mechanism attribution
- `verify_h8.py` — confirms §A.3 bug fix: Π(EU) IS trivially refined by Π(VN) via tautology; §A.3 restated honestly
- `theorem_c_matrix.py` — Phase 1: exhaustive 12-cell Refinement Matrix (Theorem C, §7.5, §A.5)
- `phase3_omega.py` — Phase 3: ω-LS sensitivity (Observation H14.1, Definitions H14/H14′/H15)
- `phase2_obligor.py` — Phase 2: ObligorGap counts for G3/G4/G5/G6 with newly-encoded obligors (Finding #18, §7.6, §A.6)

### Reference
- `HSDL-Harmonization-Gap-v10.md` — previous version, for diff/comparison

## v11 Major Additions

| Item | Section | Source |
|---|---|---|
| Corollary H5.2 (β aggregation invariance) | §5.9 | Phase 0 |
| Theorem C (full proof) | §2.8, §A.5 | Phase 1 |
| §7.5 Refinement Matrix (12 cells) | §7.5 | Phase 1 |
| §A.3 restated (Path C bug fix) | §A.3 | Discovered by Phase 1 |
| Definitions H14, H14′, H15 + Theorem A″ | §2.9 | Phase 3 |
| Observation H14.1 (subset-LS vacuity G1) | §2.9 | Phase 3 |
| Obligor annotations G3–G6 (EU + VN sides) | §5.3–§5.6 | Phase 2 |
| §7.6 ObligorGap Incidence table | §7.6 | Phase 2 |
| §A.6 Phase 2 audit trail | §A.6 | Phase 2 |
| Findings #17, #18 ★, #19 | §6 | Phases 1/2/3 |
| v11 Changelog | §1.1 | Wrap-up |

## How to reproduce all results

```bash
python3 verify_proposals.py    # G1/G2/G4 co-firing + relations
python3 verify_h8.py            # §A.3 bug fix verification
python3 theorem_c_matrix.py     # 12-cell Refinement Matrix
python3 phase3_omega.py         # ω-LS sensitivity G1/G2/G4
python3 phase2_obligor.py       # ObligorGap counts G3/G4/G5/G6
python3 verify_union.py         # per-group counts + TRUE distinct-context union (1,152)
python3 verify_hsdl_harmonization.py    # independent reimpl: D/H, all 4 sensitivity encodings
python3 verify_beta_vs_omega.py         # β-gap vs ω-gap, same per-group-union metric, per encoding
python3 verify_g4_lex.py                # G4 ObligorGap: ω_union=144 vs syntactic-LS=288 (enlarges)
python3 verify_bindingness_baseline.py  # FOIL: why global-β (30%) ≠ paper's per-group-union (60%)
```

All scripts use only Python 3 stdlib (no pip install needed). Each outputs verification text that matches the numbers in the v11 paper.

## v11 Headline Findings

★ **Finding #18 (★ headline of v11)**: Dimension Independence proposition now rests on **4 instances spanning 3 mismatch types** (vs. 1 instance in v10). Total ObligorGap (distinct-context **union**) = **1,152 contexts (40.0% of |Ctx|)**, equal to G3 alone — the four positive groups' gap-sets are nested (G1/G4/G6 ⊆ G3, since each fires only at `risk_tier ∈ {High, Unacceptable}`, which G3 covers entirely), so the per-group counts (576/1,152/144/576) must **not** be summed. Reported as **ranges** (per §7.4): on the same per-group-then-union metric, the obligor-gap union and the bindingness gap `D(VN→EU)` each span **40.0%–60.0%** across the four sensitivity encodings and are **anti-correlated** — obligor 40% / bindingness 60% at encodings A, B2; obligor 60% / bindingness 40% at B1, B3 (`verify_beta_vs_omega.py`, `verify_hsdl_harmonization.py`). So which dimension is the more frequent failure is encoding-dependent; the paper asserts no fixed ranking. *(Revision history: an early draft reported "1,872 (65.0%) > 60.0%" — a nested-set double-count, withdrawn. A side-investigation that obtained "D=30%" had used a non-standard global regime-β aggregation, not the paper's per-group-union metric — kept as a documented foil in `verify_bindingness_baseline.py`. The 40% obligor union and the 40–60% range are both solid; only the β-vs-ω ranking is encoding-sensitive.)*

**Finding #17**: Theorem C's exhaustive 12-cell Refinement Matrix shows no non-trivial cover refinement exists between any pair of regimes — and *surfaced a wording inconsistency in v10's §A.3* that prose review had missed across revisions. Direct empirical evidence for the paper's central methodological claim.

**Finding #19**: β-aggregation is algebraically invariant (Corollary H5.2); ω-aggregation is consequential (Observation H14.1). Asymmetry documented as a formal result.

## Methodology Disclosure (v11)

All Phase 2 legal research was conducted via web search and cross-referencing of public sources as of 21/6/2026. No jurisdictional expert review. Same epistemic-strength caveat as Proposition H7.1 ("argued, premise corrected"). Per-rule citations in §5.3–§5.6 comments and §A.6 audit trail.

## Watch-Outs (preserved from handoff plan)

1. §A.3 bug fix is the only v10 statement materially restated; cf. §A.3's "Why this restatement in v11" note.
2. ω-LS Definitions H14/H14′/H15 were pre-committed before computation (avoids researcher degrees of freedom).
3. Brute-force script re-run after each group's annotation (avoids G4-style mechanism attribution issues).
4. G3 VN ω=∅ framed positively as Instance 2 (not "honest negative").
5. Disjoint vs incomparable distinguished explicitly in Observation H14.1.
6. Corollary H5.2 scope: "≤1 rule per ASEAN mini-regime" justification (not just "Binding-only").
7. Theorem naming: A″ (not A‴) — consistency with A, A′.
8. Methodology disclosure explicit at annotation time, not added as caveat after.
