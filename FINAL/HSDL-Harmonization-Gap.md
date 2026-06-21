## Abstract

> Conventional wisdom holds that the EU sets the global floor for AI regulation and other jurisdictions converge toward it. Formal analysis of Vietnam's new AI Law against the EU AI Act overturns this for an entire risk tier: at minimal risk, Vietnam's universal human-control principle binds where the EU AI Act is silent — Vietnam is the *stricter* regime in formal legal force, not the EU, though we are explicit that bindingness and operational specificity are different axes and this paper measures only the former. We reach this result, and three others — regulatory voids, bindingness gaps, partition incompatibility, and obligor mismatches, four structurally distinct harmonization failure modes in total — by encoding the EU AI Act, Vietnam's Luật 134/2025/QH15 (Southeast Asia's first binding AI law), and the ASEAN AI Governance Guide into HSDL, a formally analyzable policy language, turning a comparison previously done by reading statutes and writing prose into a decidable, brute-force-checkable computation. Across seven obligation pairs, two of the four failure modes — partition incompatibility and obligor mismatch — cannot be resolved by text amendment alone; they require architectural change. This has direct implications for ASEAN's ongoing transition from voluntary guidance toward binding AI governance, which we make concrete for ASEAN, Vietnam, and cross-border deployers in §9.

---

## Introduction

AI governance comparison across jurisdictions is today conducted by reading statutes and writing prose — a method that does not scale, is not independently checkable, and cannot answer a basic operational question with precision: for a given AI system in a given deployment context, which obligations actually differ between two legal regimes, and by how much? This question stops being academic as more jurisdictions move from non-binding guidance to binding law. Vietnam's Luật 134/2025/QH15, effective 1 March 2026, is Southeast Asia's first binding national AI law; its implementing decree, Nghị định 142/2026/NĐ-CP, took effect 30 April 2026. Deployers, regulators, and standard-setters now need this question answered computationally, not narratively.

**The headline result.** Formal analysis shows that for an entire risk tier, Vietnam's AI Law is *stricter* than the EU AI Act — the opposite of the standard "EU sets the floor, others converge toward it" assumption. At minimal risk, Vietnam's Điều 4 Khoản 2 (a universal human-control principle) binds where the EU AI Act's tier-gated Art. 14 is silent. This single reversal (Finding #2, §6) is this paper's central empirical claim; the formal apparatus that follows exists to make this claim — and three others — checkable by re-running code, not asserted in prose. One precision up front, expanded at Finding #2 and §5.3: "stricter" here means stricter in legal force (`β`, Definition H1) — a declaratory principle and a mechanism-specifying design mandate can carry the same legal-force label while differing in operational specificity, an axis this paper flags (Finding #5b) but does not claim to have measured.

**What this paper adds to prior work, up front.** This paper extends the HSDL preprint, a policy language built for AI-agent authorization, not legal-harmonization analysis. *Reused unchanged:* the core machinery that makes any HSDL policy's satisfying-context set decidable and enumerable (Lemma 1, Theorem 2 — §1 gives the full accounting). *New in this paper:* a bindingness-labeling layer, so two regimes' "the same rule" can differ in legal force, not just in scope (Definitions H1–H6); a classification-scheme comparison layer, so two regimes' risk catalogs can be checked for translatability, not just compared value-by-value (Definitions H7–H8); and an obligor dimension that does not exist in the original language at all, so two regimes can be checked for *who* is responsible, not just *how strict* (Definitions H9–H13). None of this is needed to follow the headline result above — it exists to make that result, and the three others, rigorous rather than anecdotal.

This paper encodes the EU AI Act, Vietnam's AI Law, and the ASEAN AI Governance Guide as HSDL policies and applies this machinery to compute — rather than narrate — where these three regimes converge and diverge. Doing so surfaces four structurally distinct kinds of harmonization failure that a prose-only comparison would either miss or conflate:

- **Regulatory voids** (Definition H3.5) — contexts where one regime imposes an obligation and another is entirely silent, not merely lenient.
- **Bindingness gaps** (Definitions H4–H6) — contexts where both regimes address an obligation but at different enforceability levels, exactly quantified and enumerated rather than estimated.
- **Partition and classification-scheme incompatibility** (Definitions H7, H8) — structural mismatches in how two regimes carve up the same regulatory space, which no amount of text alignment alone can resolve because the mismatch is architectural, not textual.
- **Obligor mismatch** (Definition H13, §2.9; §5.1–5.2, Finding #14/#15) — contexts where a numeric gap closes but the underlying obligation-holder differs (state-inspector vs. provider-self-monitor), exposing a distinction the bindingness layer alone cannot express — now formalized as a second output dimension orthogonal to bindingness.

**Table 1** previews these four failure modes with a canonical example each, distinguishing those a text amendment alone can repair from those requiring architectural change — the distinction the Abstract's central claim rests on.

| Failure mode | Defined in | Canonical example (this paper) | Fixable by text amendment alone? |
|---|---|---|---|
| Regulatory Void | Def. H3.5 | G1 (pre-A4): VN silent on the post-market steady-state for High-risk systems while EU mandates continuous risk management | Yes — VN's own Điều 10 Khoản 5 closes it (§5.1) |
| Bindingness Gap | Def. H4 | G3: VN's Điều 4 Khoản 2 binds at `risk_tier=Minimal` where EU is silent — reverses the assumed EU-leads direction | Yes — adjusting either regime's bindingness label resolves it |
| Partition / Cover Incompatibility | Def. H7, H8 | EU's risk-tier-only cover vs. VN's `interacts_with_human`-cutting cover (§2.8) — neither refines the other | **No** — requires re-architecting which dimensions carry obligations, not editing thresholds |
| Obligor Mismatch | Def. H13 (§2.9) | G1 (post-A4) plus three additional instances confirmed in v11's Phase 2: G3 (named-set vs. unnamed-principle, 1,152 ctx), G4 (proper-subset, 144 ctx), G6 (disjoint single-actor, 576 ctx) — four instances spanning three structurally distinct mismatch types; see Finding #18, §7.6, §B.2 | **No** — requires an explicit obligor-allocation decision, not a bindingness-level adjustment |

**A note on reading order.** §2 develops thirteen definitions and five theorems — necessarily dense, and not all of it is required reading. Readers without a formal-methods background (this includes most governance-track readers, by design — the question this paper answers is a governance question, not a theory-of-computation one) can read §2.0's plain-English index, then proceed directly to §3–§8 and treat §2's proofs as reference material to consult only when checking a specific claim. Table 1 above, the Index in §2.0, and §6's Key Findings are written to stand on their own.

The remainder of the paper proceeds as follows. §1 situates the formal apparatus relative to the HSDL preprint and states precisely what is reused versus newly developed. §2 develops the `H1`–`H13` formal framework — bindingness (Definitions H1–H6), classification-scheme and partition incompatibility (Definitions H7–H8), and obligor as a second output dimension (Definitions H9–H13) — together with five supporting theorems (A, A′, B, B′, C). §3–§5 apply the framework to seven obligation pairs across EU, Vietnamese, and ASEAN law. §6–§7 report findings and brute-force-verified quantitative results, including a sensitivity analysis over two ambiguous encoding choices. §8 states limitations and dual-use considerations explicitly — including findings this paper surfaces about the limits of its own evidentiary strength rather than leaving for a reviewer to find: Proposition H7.1's dependency on a still-unsigned legal draft, the EU Signal Homogeneity result, and the partial empirical scope of the new obligor dimension. §9 turns the four failure modes into concrete recommendations for ASEAN, Vietnam, and cross-border deployers. The longest proofs are deferred to Appendix A, in service of keeping §2 itself readable without a formal-methods background (§2.0).

---

## §1 Related Work

### 1.1 EU AI Act Formalization and Computational Compliance

A growing body of work formalizes the EU AI Act itself, rather than comparing it to another regime. Guldimann et al. introduce COMPL-AI, a technical interpretation of the Act's requirements paired with an open benchmarking suite that scores large language models against roughly two dozen compliance-relevant tests — the first systematic attempt to turn the Act's principles into checkable technical criteria. Hernandez, Golpayegani, and Lewis take a complementary, ontology-based approach: an open knowledge graph mapping the Act's requirements onto international standards (ISO/IEC and CEN-CENELEC harmonized standards), surfacing definitional gaps between what the statute demands and what a standard actually certifies. Marino et al.'s Compliance Cards pursue a third strategy, treating compliance as a property tracked across an AI supply chain — providers, component datasets, and pretrained models each carry machine-readable metadata that an automated analysis aggregates into a real-time compliance estimate for the composite system.

These three efforts share a structural commitment this paper also makes — turning legal text into a checkable artifact — but they share a target this paper does not: each evaluates one system, or one supply chain, against one regime (the EU AI Act). None asks whether the Act's own obligations align with another jurisdiction's. This paper's encoding is comparative rather than evaluative: HSDL policies for the EU, Vietnam, and ASEAN are built on a shared context schema precisely so an obligation can be checked *across* regimes, not just checked for compliance *within* one. The two approaches are complementary, not competing — a deployer could in principle use a COMPL-AI-style benchmark to certify a system against one regime's requirements and this paper's `Gap↓` machinery to know which other regime's requirements that certification would, or would not, also satisfy.

### 1.2 Cross-Jurisdiction AI Governance Comparison

Comparative AI governance is itself an active literature, but its center of gravity sits almost entirely on the EU–US–China triangle. Chun, Schroeder de Witt, and Elkins contrast the EU's top-down risk-based model with the US's market-driven, agency-coordinated approach and China's blend of centralized rule-setting with decentralized regional implementation. Al-Maamari's cross-regional study extends the comparison to the UK and evaluates all four jurisdictions' risk-management frameworks against a common set of criteria. Batool, Zowghi, and Bano's systematic literature review of AI governance scholarship more broadly confirms the same pattern: most comparative work treats "global AI governance" as a three- or four-jurisdiction conversation.

Southeast Asia enters this literature, when it does, as a single descriptive aside — voluntary, principle-based, behind the binding-law frontier — rather than as a jurisdiction subjected to the same formal scrutiny as the EU or US. Lu and Tie's comparative analysis of ASEAN and EU AI regulation is a partial exception and the closest existing work to this paper's regional scope: it sets out the EU's centralized, risk-based, binding model against ASEAN's decentralized, voluntary, industry-self-regulation model and the resulting trade-off between compliance burden and innovation flexibility. But that comparison, like the wider literature, proceeds in prose — qualitative description of two governance philosophies — not via a shared formal context checked obligation-by-obligation. Critically, the wider comparative literature also predates the development this paper is built around: Vietnam's Luật 134/2025/QH15, effective 1 March 2026, postdates every work surveyed above, so none of them — nor, by construction, the ASEAN-specific comparison — could register Vietnam's move from ASEAN's voluntary baseline to Southeast Asia's first binding national AI law, or ask the question this paper asks: now that one ASEAN member has crossed that line, where exactly does its binding law sit relative to the EU AI Act and to ASEAN's own voluntary Guide. This paper's three-way EU/Vietnam/ASEAN comparison, and its finding that Vietnam is in places the formally stricter regime, has no precedent in the literature above to confirm or contradict — a gap this paper's HSDL encoding fills with a checkable result rather than a qualitative impression.

### 1.3 Legal Informatics and Policy Language Foundations

This paper's H1–H13 apparatus sits inside a longer legal-informatics tradition of representing norms as machine-checkable rules rather than prose. LegalRuleML, the OASIS rule-interchange standard developed by Palmirani, Governatori, Rotolo, and collaborators, extends the earlier RuleML framework with legal-domain primitives — defeasibility, normative effect, temporal validity, jurisdiction — precisely so statutory and regulatory text can be modeled and exchanged across reasoning systems rather than read once and discarded into prose summaries. The broader defeasible-logic program behind it, including Governatori and Rotolo's formal treatment of legal abrogation, annulment, and norm modification, develops machinery for exactly the kind of priority question — which rule wins when two both apply — that this paper's Definition H3 (*lex strictior*, max-aggregation) sidesteps by construction, and that a companion technical note on lex-specialis aggregation for the obligor dimension takes up directly, citing this tradition by name where this paper does not need to.

This paper's relationship to that tradition is narrower than LegalRuleML's own ambition. LegalRuleML aims at a general-purpose interchange format covering defeasibility, deontic operators, and normative dynamics across arbitrary legal domains. This paper instead inherits a much smaller, purpose-built apparatus — HSDL, a conjunctive attribute-based policy language built originally for dynamic AI-agent authorization, not legal-harmonization analysis (§1.4) — and extends it just far enough (a bindingness-labeled output, a classification-scheme comparison layer, an obligor dimension) to answer one comparative question across three real instruments. Where LegalRuleML and the defeasible-logic tradition pursue expressiveness across the full space of normative phenomena, this paper trades that generality for decidability and brute-force enumerability over a small, closed, three-jurisdiction context — a complementary rather than competing design point: this paper's formal results (Theorems A/A′/B/B′/C) hold *because* the language is deliberately less expressive than LegalRuleML's, not despite it.

### 1.4 Relationship to the HSDL Preprint

This paper extends the HSDL preprint ("HSDL: A Formally Analyzable Policy Language for Dynamic AI Agent Authorization," arXiv preprint v0.1, HolySeed reference implementation, Apache 2.0). The preprint §9 conjectures:

> *"We conjecture this applies to any conjunctive ABAC language over a closed typed context, but leave a full proof of generality as future work."*

This paper instantiates that conjecture in a new domain — legal harmonization — providing cross-domain validation evidence independent of the preprint's acceptance status.

**Carried over (domain-independent):**

| Component | Role |
|---|---|
| **Lemma 1** | S(R) = S_num(R) × S_cat(R) |
| **Theorem 2** | Satisfying(P) = ∪ᵢ S(Rᵢ) |
| **Corollary 1** | Auditability by Construction |
| **Corollary 2** | Polynomial-time contradiction detection |

**Not carried over:** Theorem 1 (dynamic principal/trust trajectory), Theorem 3 (budget cryptographic depth), Z3/TLA+/HolySeed Rust implementation details — these are AI-agent-specific and would introduce domain contamination. Lemma H (§2.5) is new bridging work required because Harmonization Gap needs a labeled-output layer that Theorem 2 alone does not provide.

### 1.5 AI Governance Arbitrage Literature

Corollary H5.1 (§2.3) reads this paper's `Gap↓(A→B)` measure as a formal arbitrage detector. That framing requires an honest disclaimer: the underlying concept — fragmented AI regulation creating exploitable jurisdictional differences in compliance burden — is already named and actively discussed, not introduced here. See, among others: Marwala, "The AI Governance Arbitrage" (UN University, 2026); political-economy work modeling AI regulation as a multilevel government–firm competitive game (*ProMarket*, 2025); and academic treatment of firms shifting operations toward jurisdictions with looser AI requirements (Aloisi & De Stefano, 2023, as cited in subsequent comparative-governance literature). This paper's relationship to that work is additive, not foundational: those treatments are qualitative or game-theoretic at the level of "jurisdictions compete"; this paper computes, per individual rule and exact system configuration, where the differential lies for three real, currently-effective instruments — and Finding #16 (§6) shows that grain of analysis changes which direction the arbitrage incentive actually points, relative to the country-level story that literature typically tells.

---

## §2 Formal Framework

### 2.0 How to Read This Section

This section defines thirteen numbered objects (`H1`–`H13`), five theorems, two bridging lemmas, four propositions, and one observation — the full formal vocabulary the rest of the paper computes with. The table below gives each one a plain-English gloss and its governance payoff, in reading order. **Rows marked "technical plumbing" can be skipped entirely on a first read** — they exist to make the math go through, not to carry an independent governance claim; nothing in §3–§8 requires understanding *how* they work, only trusting *that* they work (and a formal reviewer can check that independently of reading this paper as a whole).

| Item(s) | Plain-English | Governance payoff |
|---|---|---|
| H1 (Bindingness Order) | Four strictness levels — `⊥`/Voluntary/Recommended/Binding — that can be ranked. | Lets the paper say "X is stricter than Y" in a way a computer can check, not just assert. |
| H2 (Regime) | A regime = one jurisdiction's rules, each tagged with a strictness level. | The basic comparable unit — "the EU AI Act" as a single computable object. |
| H3, H3.5 (β, Regulatory Void) | For any real-world scenario, the strictest applicable rule — or an explicit "nothing applies." | Tells *silence* apart from *leniency*; a regime that says nothing isn't the same as one that's lenient. |
| H4, H5 (Gap Set, Total Gap), Cor. H5.1 | Exactly which scenarios put two regimes at different levels, what share of all scenarios that is, and — read the other way — where a compliance-cost-minimizing actor would prefer one regime over the other. | The raw count behind every "X% stricter" claim in this paper, and a formal (not assumed) answer to "where's the arbitrage?" |
| Theorem A | For one scenario, the answer is always computable, quickly. | The findings are checkable by re-running code, not by trusting prose. |
| Lemma H, Lemma H′ | *(technical plumbing)* Bridges this paper's strictness-levels to the math of an earlier paper (Theorem 2) that only handled binary in/out rules. | Skip — only needed if independently verifying Theorem B below. |
| Theorem B | Every gap scenario can be listed completely, not sampled. | Nothing in this paper's gap counts is an estimate or a guess at coverage. |
| H6 (Harmonization Measure) | One percentage score for overall alignment between two regimes. | A single comparable number, instead of requiring a reader to scan every scenario. |
| H7, H7′ (Classification Scheme, Compatibility) | Checks whether one regime's way of *sorting* systems into categories can be translated into another's at all. | Some mismatches are about incompatible categories, not about strictness — a different failure mode entirely. |
| Prop. H7.1, H7.2 | EU's and Vietnam's risk catalogs can't be matched one-to-one; EU's severity levels and ASEAN's harm-type categories are different *kinds* of label. | These specific mismatches can't be fixed by adjusting a threshold — the categories themselves don't line up. |
| H8, Obs. H8.1 (Induced Cover) | Checks whether one regime's rulebook is a "refinement" of another's. | Shows neither regime's structure can be derived from the other's — they cut up the same space along different axes. |
| Theorem C, §7.5 Refinement Matrix *(v11)* | Same check as H8/Obs. H8.1, but run exhaustively across all three policy pairs and both directions, with and without tautologies. | Generalizes the H8 illustrative result to "no non-trivial refinement exists between any pair of regimes in this paper" — a stronger structural-incompatibility claim. Also surfaces and corrects a wording inconsistency in v10's Observation H8.1. |
| Prop. H8.2 (EU Signal Homogeneity, §5.8) | 5 of the EU AI Act's 6 encoded rules in this paper reduce to the same literal condition. | The EU side of this paper's comparison is effectively two independent data points, not six — a scope caveat stated explicitly rather than left for a reviewer to find. |
| H9–H12 (Obligor) | A second output, alongside strictness: not just *how binding*, but *who* must act. | Two regimes can be equally strict on paper while assigning the duty to completely different actors. |
| H13, Theorem A′/B′ | Where the "who" differs even though the "how strict" agrees; the same checkability/completeness guarantees as A/B, extended to "who." | Catches obligor mismatches as rigorously as strictness mismatches — not just flagged in prose. |
| Prop. H13.1 (Dimension Independence) | `β`-equality does not imply `ω`-equality — two regimes can agree completely on strictness and still disagree on who is responsible. | The formal statement behind every "obligor mismatch" finding in §6; one confirmed instance is enough to establish it, and v11 adds three more. |
| Corollary H5.2 *(v11, §5.9)* | β does not vary under the choice of aggregation function in this paper's encoding, because at most one obligation-level ever co-fires. | Stronger than a sensitivity analysis: an algebraic invariance result, not an empirical one. Findings #1, #2, #9, #10, #13, #14, #16 immediate. |

*Five proof/discussion blocks are deferred to the appendices* (Proposition H7.1, Proposition H7.2, Observation H8.1, and Theorem C in Appendix A; Proposition H13.1's extended discussion in Appendix B.1) — the body below states each claim with a short intuition; the full argument is available in the appendices for a reader checking it line by line.

### 2.1 Preliminaries (reused, unchanged)

Let `Ctx` be a closed typed evaluation context — finite set of typed dimensions, numeric/ordinal or categorical, finite vocabulary. For conjunctive rule R over Ctx, `S(R) ⊆ Ctx`. By **Lemma 1**, `S(R) = S_num(R) × S_cat(R)`. A **policy** `P = {R₁,...,Rₙ}` is a finite set of named rules. By **Theorem 2**, `Satisfying(P) = ∪ᵢ S(Rᵢ)`.

### 2.2 Bindingness as Labeled Output

**Definition H1 (Bindingness Order).** `(B, ≤)` finite totally ordered set, minimum `⊥` ("not addressed"):

```
B = { ⊥, Voluntary, Recommended, Binding }
rank: ⊥ → 0, Voluntary → 1, Recommended → 2, Binding → 3
```

Structurally identical to HSDL's `TrustLevel` (§5.1 of the preprint) — no new enumeration machinery required.

**Definition H2 (Regime).** A *regime* is a pair `(P, λ)` where `P` is a policy over shared `Ctx`, `λ: P → B` assigns each rule the bindingness level of the obligation it expresses. (`λ` is metadata on the *consequence*, not a condition in the rule body — `S(Rᵢ)` computes exactly as in Lemma 1, unchanged.)

*Scope note:* `P` need not be "the entire statute" — `P` may be scoped to a single obligation-domain (e.g., rules about risk classification only). This is how §5 is used: 6 obligation-specific "mini-regimes," not one mega-policy. A mega-policy is methodologically wrong here because a tautological rule (e.g., Điều 4 Khoản 2's universal human-control principle) makes `β ≡ Binding` for every context, erasing all domain-specific gaps (verified by code: 2.880/2.880 contexts degenerate).

**Well-formedness:** `λ(Rᵢ) ≠ ⊥` for every `Rᵢ ∈ P`. Named rules always express an obligation strictly above "not addressed"; `⊥` is reserved as `β`'s default output when no rule fires. Without this invariant, the Regulatory Void characterization in §2.3 breaks: a rule with `λ(Rⱼ)=⊥` and `ctx∈S(Rⱼ)` would simultaneously place `ctx` in `∪S(Rᵢ)` and in `S_{=⊥}(P,λ)`, violating the equality. No rule in §5 carries label `⊥`, so all current results hold; this is a proof-completeness requirement, not an empirical correction.

**Definition H3 (Regime Bindingness Function).** For regime `(P,λ)`, define `β_{(P,λ)}: Ctx → B`:

```
β_{(P,λ)}(ctx) = max{ λ(Rᵢ) : Rᵢ ∈ P, ctx ∈ S(Rᵢ) },  or ⊥ if no rule fires
```

*Modeling note:* `max` encodes a *lex strictior* principle — the strictest applicable obligation governs when multiple rules fire. This differs from *lex specialis* (specificity-based priority, which can yield a *less* strict outcome if a specific rule overrides a stricter general rule). *Lex strictior* is the conservative compliance posture appropriate for cross-jurisdictional safety analysis. Alternative aggregation schemes (unanimity, full set of triggered levels) are future work.

**Definition H3.5 (Regulatory Void).** For regime `(P,λ)`, *Regulatory Void*:

```
Void(P,λ) = S_{=⊥}(P,λ) = Ctx \ ∪_{Rᵢ ∈ P} S(Rᵢ)
```

= contexts where no rule in `P` applies (β(ctx)=⊥ by default).

*Directional Void (A toward B):*

```
Void↓(A→B) = { ctx ∈ Ctx : β_A(ctx) > ⊥ ∧ β_B(ctx) = ⊥ }
```

= contexts where regime A has an obligation but regime B is entirely silent — not merely less strict, but unaddressed.

*Relationship to Gap:* `Void↓(A→B) ⊆ Gap↓(A→B)` — every void context is a gap context, but `Gap↓` also covers the case where B has an obligation that is merely weaker. Regulatory Void is the policy-relevant sub-case warranting a distinct label.

### 2.3 Harmonization Gap

**Definition H4 (Gap Set).** Given regimes `A=(P_A,λ_A)`, `B=(P_B,λ_B)` over shared `Ctx`, fixed `(a,b) ∈ B×B`:

```
Gap_{A,B}(a,b) = { ctx ∈ Ctx : β_A(ctx) = a ∧ β_B(ctx) = b }
```

**Definition H5 (Total Gap / Directional Shortfall).**

```
Gap(A,B) = ∪_{a≠b} Gap_{A,B}(a,b)                   // Total divergence
Gap↓(A→B) = ∪_{a>b}  Gap_{A,B}(a,b)                  // A strictly stricter than B
```

`Gap↓(EU→VN/ASEAN)` = every scenario where EU is binding but VN/ASEAN is voluntary/recommended/⊥.

*Corollary H5.1 (Arbitrage interpretation — concept not novel, computation is).* `Gap↓(A→B)` is, by construction, exactly the set of system configurations for which a compliance-cost-minimizing actor would prefer regime `B` over `A`: the obligation is weaker or absent there. This is a formal restatement of *AI regulatory arbitrage* — a concept already named and actively discussed in the AI governance literature (e.g., the United Nations University's 2026 essay "The AI Governance Arbitrage"; political-economy treatments modeling AI regulation as a multilevel government-firm competition; documented concern that firms "shift operations to jurisdictions with looser requirements"). This paper does not claim to introduce that concept. What `Gap↓`/`D` (Definition H6) add to that literature is specificity: prior treatments describe arbitrage qualitatively or model it game-theoretically at the level of "jurisdictions compete"; `Gap↓(A→B)` computes, per individual rule and exact system configuration, *where specifically* — for three real, currently-effective instruments — the differential lies, brute-force-verified rather than assumed. Finding #16 (§6) and §9 make this concrete and, in one respect, surprising.

### 2.4 Theorem A — Gap Membership Decidability

**Theorem A.** *For any fixed `ctx ∈ Ctx`, determining `β_A(ctx)` and `β_B(ctx)` — hence deciding `ctx ∈ Gap_{A,B}(a,b)` for any `(a,b)` — is decidable in time **linear** in `|P_A|+|P_B|` (with constant factor k, the fixed number of `Ctx` dimensions).*

**Proof.** Computing `β_{(P,λ)}(ctx)` requires evaluating `ctx ∈ S(Rᵢ)` for each `Rᵢ ∈ P` — by Lemma 1, each check is a finite conjunction of: halfspace test (`O(1)` per numeric/ordinal dimension) and set-membership test (`O(1)` hash-indexed, or `O(|Σ|)` linear scan, `|Σ|` = max categorical vocabulary size). Max label over `|P|` rules: `O(|P|)`. Total: `O(|P|·k)` with `O(1)` categorical lookup (standard for compiled policy evaluation). For the §5 encoding, the largest vocabulary is `sector` with `|Σ|=6`, so even an unindexed bound is `O(|P|·k·6) = O(|P|·k)` asymptotically. Comparing `β_A` vs `β_B`: `O(1)`. □

### 2.5 Theorem B — Gap Set Enumerability

**Lemma H (Level-Cut Reduction).** This is the bridging step that Theorem 2 alone does not provide — required because Harmonization Gap needs a labeled-max-aggregation layer.

*Base case (v = ⊥):*

```
S_{≥⊥}(P,λ) := Ctx
```

Since `⊥` is the minimum of `B`, `β(ctx) ≥ ⊥` holds for every `ctx ∈ Ctx`. Immediate corollary: `S_{=⊥}(P,λ) = Ctx \ ∪_{Rᵢ ∈ P} S(Rᵢ)` = Regulatory Void (Definition H3.5).

*Inductive case (v > ⊥):*

```
S_{≥v}(P,λ) = { ctx : β(ctx) ≥ v } = ∪_{Rᵢ ∈ P : λ(Rᵢ) ≥ v} S(Rᵢ)
```

*Proof (v > ⊥).* `β(ctx) ≥ v` iff some firing rule has `λ(Rᵢ) ≥ v`. This is exactly Theorem 2's union argument applied to sub-policy `{Rᵢ ∈ P : λ(Rᵢ) ≥ v}` — no new machinery, only a restriction of the rule set before taking the union. □

**Lemma H′ (Exact-Level Set).** `B` finite total order, `v⁺` = next level above `v`:

```
S_{=v}(P,λ) = S_{≥v}(P,λ) \ S_{≥v⁺}(P,λ)
```

*Top-element convention:* when `v = ⊤` (`Binding`, max element of `B`), `v⁺` does not exist — define `S_{≥⊤⁺} := ∅` by convention. Then `S_{=⊤}(P,λ) = S_{≥⊤}(P,λ)`, as expected. (This matters in practice: in this paper's §5 encoding, every named EU/VN rule carries label `Binding` exclusively — `β_EU, β_VN ∈ {⊥, Binding}` throughout, formalized below as the Observation in §5.9 — making `v=⊤` the most-used case throughout §5: every worked example in §5 requires `S_{=Binding}`, so the formula must be well-defined at this point.)

Both operands are finite unions of polytope×finite-set regions (Lemma H inductive case at levels `v` and `v⁺`, both `>⊥`). Since `Ctx` is a finite set (closed-typed finite vocabulary), every subset of `Ctx` is finite. `S_{=v}(P,λ)` is finite and representable as a finite union of polytope×finite-set regions.

*Note on terminology:* "polytope" in standard usage (convex geometry) is a *bounded* intersection of halfspaces. A one-sided constraint (e.g., `scale_affected ≥ 1000`, no upper bound) yields a **polyhedron** (possibly unbounded). When future extensions encode numeric-threshold rules, substitute "polytope" → "polyhedron" or "polyhedral region" unless all numeric dimensions are bounded in both directions.

**Theorem B (Gap Set Enumerability).** *`Gap_{A,B}(a,b) = S_{=a}(P_A,λ_A) ∩ S_{=b}(P_B,λ_B)` is a finite union of polytope×finite-set regions, hence statically enumerable at encoding-time — without executing rules on sampled test inputs. Since `Ctx` is a finite discrete set, enumerability follows directly from finiteness of any subset.*

**Proof.** By Lemma H′, both `S_{=a}(P_A,λ_A)` and `S_{=b}(P_B,λ_B)` are finite unions — write `∪ⱼ Pⱼ^A` and `∪ₖ Pₖ^B`. Distributing intersection: `(∪ⱼ Pⱼ^A) ∩ (∪ₖ Pₖ^B) = ∪_{j,k} (Pⱼ^A ∩ Pₖ^B)`. Each `Pⱼ^A ∩ Pₖ^B` is a polytope×finite-set region: intersection of two convex polytopes is convex (intersection of halfspaces), intersection of two finite sets is finite. Hence `Gap_{A,B}(a,b)` is a finite union of polytope×finite-set regions. Since `Ctx` is finite, `Gap_{A,B}(a,b) ⊆ Ctx` is finite and thus statically enumerable. □

**Corollary H (Total Gap Enumerability).** `Gap(A,B)` and `Gap↓(A→B)` are finite unions (over `|B|²` level-pairs) of enumerable sets from Theorem B, hence enumerable.

### 2.6 Harmonization Measure

**Definition H6 (Harmonization Measure).** Given finite context space `Ctx` (`|Ctx| < ∞`):

```
H(A,B) = 1 - |Gap(A,B)| / |Ctx|  ∈ [0,1]
```

`H(A,B)=1`: perfect harmonization. `H(A,B)=0`: complete divergence.

*Directional Harmonization Shortfall:*

```
D(A→B) = |Gap↓(A→B)| / |Ctx|
```

**Methodological scope of H6/D:** when `P` is scoped per obligation-domain (as in §5), H6/D applies per group. The aggregate "cross-domain incidence" values in §7 answer "does this context show divergence in at least one tracked domain?" — not "does a combined single-β of the full statute differ?" These are composite metrics, not direct instances of H4 on one policy, and must be labeled as such to prevent reviewer misreading (see §7.4).

### 2.7 Classification Scheme Incomparability

**Definition H7 (Classification Scheme).** Let `Attr` be a record type with fields `{sector, use_case, scale_affected, automation_pct, harm_type_flags, …}` — a domain of pre-classification system descriptors examined *before* assigning a value of some `Ctx` dimension `d`. A *classification scheme* for `d` is a total function `τ: Attr → Dom(d)`.

*(Commentary: this layer sits before `Ctx` — Definitions H1–H5 receive `risk_tier` as a given input; H7 unlocks the question "where does that value come from," which H4 cannot address.)*

**Definition H7′ (Scheme Compatibility).** Two schemes `τ_A: Attr → Dom_A`, `τ_B: Attr → Dom_B` are *compatible* iff `∃ h: Dom_A → Dom_B` such that `τ_B = h∘τ_A`, or symmetrically `∃ h': Dom_B → Dom_A` with `τ_A = h'∘τ_B`. **Incomparable** if neither factorization exists.

*Non-triviality.* A candidate `h` (or `h'`) must satisfy its defining equation for *every* `a ∈ Attr`, not merely be total as a function `Dom_A → Dom_B` — totality of the function type and satisfaction of the equation are different conditions. This matters once a codomain has been totalized with a sentinel value (e.g., `N/A`, Proposition H7.2's totality fix): the constant map `h ≡ N/A` is total in the function-existence sense, but it is excluded by the equation itself — not by an added side-condition — whenever some `a ∈ Attr` has `τ_B(a) ≠ N/A`, since then `h(τ_A(a)) = N/A ≠ τ_B(a)`. Consequently, "no `h: Dom_A → Dom_B` exists" in the proofs below is shorthand for "no `h` satisfies the equation"; it is never a literal claim that the type-level mapping `Dom_A → Dom_B` is empty (it never is, for nonempty finite `Dom_A`, `Dom_B` — constant maps always exist).

**Proposition H7.1 (EU/VN incomparability) — status: argued, not proven (verification completed 20/6/2026; see note below).** `τ_EU` (Annex III, extensional enumeration on named use-case categories) and `τ_VN_High` (Danh mục under Điều 13 Khoản 4, also extensional catalog) are incomparable — not because one is extensional and the other intensional (both are extensional), but because the two catalogs are organized along independent axes that cannot factor through each other.

*Intuition.* Annex III lists named use-cases as High regardless of deployment context; VN's Danh mục instead conditions some entries on factors Annex III ignores (e.g. whether a human-approval step exists) and organizes a whole group by harm-scale/reversibility rather than by use-case. Translating either catalog into the other would force one fixed output to stand in for genuinely different real values — impossible for a function. **Full proof: Appendix A.1.**

*Caveat — verification completed, status downgraded.* Re-verified 20/6/2026 against all available public sources: Công văn 1101/BKHCN-CNS&CĐS (03/3/2026, proposal stage); the implementing Nghị định 142/2026/NĐ-CP (effective 30/4/2026), which references the high-risk catalog only generically as "danh mục do Thủ tướng Chính phủ ban hành" without citing a signed Quyết định number or date; and subsequent news coverage through May 2026. No source confirms the Prime Minister has signed the official Quyết định under Điều 13 Khoản 4 — every available source still describes the catalog as "dự thảo" (draft). The catalog-structure mismatch (conditional qualifiers + Nhóm IV's harm-scale organizing axis) is visible in the draft and unlikely to disappear in a final version, but this proposition currently rests on a draft text, not a finalized one. **Status: downgraded from "proven" to "argued, premise corrected — full proof pending confirmation of final Danh mục text."** Re-check immediately before submission in case the Quyết định is signed in the intervening period.

**Proposition H7.2 (EU/ASEAN incomparability — codomain-level, stronger than H7.1).** `τ_EU` and `τ_ASEAN` (6 harm-type categories, Gen AI Guide) are incomparable. The mismatch is at codomain semantics, not merely at values.

*Totality fix:* the original definition of `τ_ASEAN` existed only for `sector=GenAI` — a partial function, inconsistent with Definition H7's "total" requirement. Fix: extend `Dom_ASEAN⁺ = Dom_ASEAN ∪ {N/A}` and redefine `τ_ASEAN: Attr → Dom_ASEAN⁺` as total, with `τ_ASEAN(a) = N/A` whenever `sector(a) ≠ GenAI`.

*Proof sketch.* `Dom_EU = {Minimal, Limited, High, Unacceptable}` (4 levels, an ordered severity scale). `Dom_ASEAN = {Societal, Economic, Environmental, Security, Human Rights, Ethical}` (6 categories, an unordered harm-type partition — orthogonal to severity by the Gen AI Guide's own design: a given harm-type can in principle arise at any severity level, and a single system can raise more than one harm-type concern regardless of its EU tier).

*Intuition.* EU's severity scale and ASEAN's harm-type categories are different *kinds* of label — one is an ordered scale, the other an unordered partition that is orthogonal to severity by the Guide's own design. No single fixed translation value can stand in for harm-type membership that genuinely varies within one severity level, and totalizing the codomain with a sentinel `N/A` doesn't rescue this — the sentinel map fails the same way for any input where the true output isn't `N/A`. **Full proof: Appendix A.2.**

### 2.8 Partition Cover Mismatch

*Terminology note:* `{S(Rᵢ): Rᵢ∈P}` is generally not pairwise-disjoint (e.g., Điều 4 Khoản 2's `S(dieu4kh2_human_control_principle)=Ctx` overlaps every other rule in VN policy), so it does not satisfy the standard partition definition. The correct term is **cover**; the refinement relation applies to covers exactly as to partitions, without requiring disjointness.

**Definition H8 (Induced Cover).** For a policy `P` over `Ctx`, the *cover* induced by `P` is `Π(P) = { S(Rᵢ) : Rᵢ ∈ P }` (a family of subsets of `Ctx`, not generally pairwise-disjoint). A *refinement* relation holds — `Π(P_A)` refines `Π(P_B)` — iff for every `S_A ∈ Π(P_A)`, there exists `S_B ∈ Π(P_B)` such that `S_A ⊆ S_B`.

**Observation H8.1 (Structural Incompatibility — restated v11).** The covers induced by the EU AI Act and the Vietnam AI Law are incompatible *in the non-trivial sense*. Two layers, both reported:

1. **Under Definition H8 as written (positive blocks only, including tautologies):** `Π(EU_AIAct)` IS trivially refined by `Π(VN_AILaw_134_2025)` — because Điều 4 Khoản 2's tautology block `S(dieu4kh2_human_control_principle) = Ctx` contains every EU block. This refinement is uninformative; it reflects that `Ctx` is the trivial upper bound under set inclusion.
2. **After excluding tautological rules (i.e. rules with `S(Rᵢ) = Ctx`):** neither cover refines the other. `Π(EU_AIAct)` is not refined by `Π(VN_AILaw_134_2025 \ {dieu4kh2})` (five of six EU blocks fail to nest); and `Π(VN_AILaw_134_2025)` is not refined by `Π(EU_AIAct)` (six VN blocks fail to nest), regardless of tautology inclusion on the VN side.

The substantive structural-incompatibility claim — that EU's risk-tier-only architecture and VN's multi-axis architecture cut up the regulatory space along genuinely different axes — is established by layer 2. Layer 1 is reported transparently so the reader is not misled by the formal definition's permissiveness toward tautological refinement. **Full proof (by exhaustive subset-check, both layers): Appendix A.3.**

*Why this restatement in v11.* Earlier versions stated "Π(EU) not refined by Π(VN)" without distinguishing the two layers, implicitly using a broader partition definition (rule splits Ctx into S(R) AND its complement) inconsistent with Definition H8's positive-block-only formulation. Theorem C's exhaustive subset-check (added in v11, below) surfaced this inconsistency that prior prose review had not. This is itself an instance of the paper's Finding #11 (formal tool self-certifies its own boundaries) — and direct empirical evidence for the paper's central methodological claim that brute-force-verifiable computation catches structural issues prose comparison misses.

**Theorem C (Partition Refinement Decidability).** *For any two policies `P_A, P_B` over shared `Ctx` (with each `S(Rᵢ)` a polytope × finite-set region per Lemma 1), deciding whether `Π(P_A)` refines `Π(P_B)` is decidable in time `O(|P_A| · |P_B| · k)`, and the complete set of non-nesting `P_A`-blocks is enumerable in the same bound.*

*Intuition.* For each `S_A ∈ Π(P_A)`, check whether any `S_B ∈ Π(P_B)` satisfies `S_A ⊆ S_B`. By Lemma 1, each `S` factors as `S_num × S_cat`; subset reduces to per-dimension interval/set containment, `O(k)`. Total: `O(|P_A| · |P_B| · k)`. Failures are recorded as they occur, yielding the non-nesting list. **Full proof and the Refinement Matrix (12 directional cells, with/without tautology, computed exhaustively for the three §5 policies): Appendix A.4; result table in §7.5.**

### 2.9 Obligor as Second Output Dimension

The Group 1 obligor mismatch (§5.1: VN's Điều 10 Khoản 5 is a regulator-inspects obligation; EU's Art. 9 is a provider-self-monitors obligation, at equal bindingness) shows that `β_A(ctx) = β_B(ctx) = Binding` can co-occur with structurally different obligation-holders. This section formalizes obligor as a second, independent output dimension, decoupled from `β` by design.

**Definition H9 (Obligor Set).**

```
O = { Provider, Deployer, Regulator, ThirdPartyCertifier }
```

`O` is a finite flat set — *flat* meaning `O` carries no natural total order. Obligors cannot be ranked by strictness the way levels in `B` can, which is why `ω` (below) requires a different aggregation from `β`.

*Coverage note:* `Provider` = entity placing the AI system on market (EU Art. 3(3) / VN Điều 5); `Deployer` = entity using it in deployment context; `Regulator` = state supervisory/inspection authority distinct from rulemaking body; `ThirdPartyCertifier` = notified body or recognized certification authority (EU Art. 33; VN Nghị định 142 Điều 13's sector-recognized body). `O` is open for extension.

*Disambiguation from `system_role`.* `O` is an *output* vocabulary — who bears a given obligation — and is distinct from `system_role ∈ {Provider, Deployer, User}`, a `Ctx` *input* dimension (§3.2) describing which role the evaluated AI system occupies. The label overlap (`Provider`, `Deployer`) is intentional shorthand, not identity: a context with `system_role=Provider` can still produce `ω(ctx) = {Regulator}` — e.g. `ctx*` below, where the system under evaluation is provider-operated but the *obligation* names a state authority as the responsible party.

**Definition H10 (Labeled Regime with Obligor).** A *labeled regime with obligor* is a triple `(P, λ, ο)` where `(P, λ)` is a regime (Definition H2) and `ο: P → ℘(O)` assigns each rule the set of obligors named by the obligation it expresses; `ο(Rᵢ) = ∅` if the rule's text does not name a specific obligor. If a rule binds multiple obligors jointly, `|ο(Rᵢ)| > 1`.

**Definition H11 (Obligor Function).** For regime `(P, λ, ο)`:

```
ω_{(P,λ,ο)}(ctx) = ⋃{ ο(Rᵢ) : Rᵢ ∈ P, ctx ∈ S(Rᵢ) }
                   (∅ if no rule fires)
```

`ω` uses *union* aggregation — not *max* — because when multiple rules fire, all named obligors are simultaneously responsible; none dominates.

*Why union, not max:* `β` uses `max` because `B = {⊥, Voluntary, Recommended, Binding}` has a natural total order and the conservative compliance posture selects the strictest applicable level. `O` has no such order: `Regulator` is not "stricter" than `Provider` — they hold categorically distinct obligations. Forcing `O` into a max-aggregation would require an arbitrary total order with no legal basis.

**Definition H12 (Two-Dimensional Output Function).** For labeled regime with obligor `(P, λ, ο)`:

```
Φ_{(P,λ,ο)}: Ctx → B × ℘(O)
Φ_{(P,λ,ο)}(ctx) = ( β_{(P,λ)}(ctx),  ω_{(P,λ,ο)}(ctx) )
```

The two components compute independently: `β` via max-aggregation (Definition H3), `ω` via union-aggregation (Definition H11), both evaluated against the same rule-firing set `{Rᵢ ∈ P : ctx ∈ S(Rᵢ)}`. Independence is not incidental — it reflects that *how binding* an obligation is and *who bears it* are orthogonal statutory questions.

**Proposition H13.1 (Dimension Independence).** `β`-equality does not imply `ω`-equality.

*Proof (Instance 1 — G1, `ctx*` = `risk_tier=High, lifecycle_stage=PostMarket, modification_increases_risk=false`).*

```
β_EU(ctx*) = Binding  (Art. 9: continuous risk management)
β_VN(ctx*) = Binding  (Điều 10 Khoản 5a: mandatory periodic inspection)
ω_EU(ctx*) = { Provider }          // provider operates own risk management system
ω_VN(ctx*) = { Regulator }         // state authority conducts inspection of the entity
```

`β_EU(ctx*) = β_VN(ctx*)` but `ω_EU(ctx*) ≠ ω_VN(ctx*)`. □

*Candidate second instance (Group 2) — considered, not used.* An earlier draft proposed Group 2 as a second instance; external review additionally caught an independent encoding error in this paper's own first-pass `ω_EU`/`ω_VN` annotations for Group 2. **Full discussion of both issues and how each was resolved: Appendix B.1.**

§5.2 is corrected accordingly: `ω_EU = ω_VN = {Provider}` for the dominant case on both sides — Group 2 remains a convergence point, with a different common value than first encoded, and with two exception zones (EU's Annex III point 1; VN's Khoản 2(a) Danh mục) flagged as currently unencodable rather than resolved in either direction. The Proposition's claim does not require a second instance regardless: a single confirmed counterexample (Instance 1) is sufficient to establish that `β`-equality does not in general imply `ω`-equality.

**Definition H13 (Obligor Gap).**

```
ObligorGap(A,B) = { ctx ∈ Ctx : β_A(ctx) > ⊥  ∧
                                 β_B(ctx) > ⊥  ∧
                                 ω_A(ctx) ≠ ω_B(ctx) }
```

= contexts where both regimes impose an obligation (no Regulatory Void in either direction) but on structurally different obligor sets. By construction, `ObligorGap(A,B) ∩ Void↓(A→B) = ∅` and `ObligorGap(A,B) ∩ Void↓(B→A) = ∅` — obligor gaps are a category orthogonal to void gaps, not a sub-case (the three conditions in Definition H13 require both `β_A>⊥` and `β_B>⊥`, while `Void↓(A→B)` requires `β_B=⊥`; these are mutually exclusive on `β_B`, and symmetrically for `Void↓(B→A)` on `β_A`).

**Theorem A′ (Extended Decidability).** Determining `Φ_{(P,λ,ο)}(ctx)` for any fixed `ctx ∈ Ctx` is decidable in time linear in `|P_A|+|P_B|` — the same asymptotic bound as Theorem A.

*Proof.* The `β`-component computation is identical to Theorem A's proof: `O(|P|·k)`. The `ω`-component additionally requires `⋃ο(Rᵢ)` over firing rules. Since `|O|=4`, each `ο(Rᵢ) ∈ ℘(O)` is representable as a 4-bit mask; union is bitwise OR, `O(1)` per rule. Both components can be computed in a single linear scan over `P`. Total: `O(|P|·k)` unchanged. □

**Theorem B′ (Extended Enumerability).** `ObligorGap(A,B)` is a finite, statically enumerable subset of `Ctx`.

*Proof.* `ObligorGap(A,B) ⊆ Ctx`, and `Ctx` is finite (closed-typed finite vocabulary). Every subset of a finite set is finite. For enumeration: a single brute-force pass over all `|Ctx|` contexts, computing `Φ_A(ctx)` and `Φ_B(ctx)` per Theorem A′ and checking the three conditions in Definition H13, suffices. □

*Honesty remark — weaker than Theorem B, not a like-for-like extension.* This proof establishes enumerability by brute-force pass over the (here explicitly finite, `|Ctx|=2.880`) context space. That is **weaker** than Theorem B's *symbolic* enumerability, which avoids executing rules over sampled inputs entirely via the polytope-intersection argument (Lemma H′). A symbolic version of Theorem B′ is plausible in principle — `ω_{(P,λ,ο)}(ctx)` is fully determined by *which subset of `P`'s rules fire* at `ctx`, and each firing condition is itself an `S(Rᵢ)` membership test, so `ObligorGap(A,B)` could in principle be expressed as a finite union of polytope×finite-set regions indexed by rule-firing-subsets — a level-cut-style reduction over rule subsets rather than over `B`-levels (cf. Lemma H). That symbolic strengthening is not carried out here and is left as future work; the brute-force enumerability proved above is sufficient for this paper's explicit, finite `Ctx`, but should not be conflated with Theorem B's stronger scalability guarantee.

### 2.10 Legal Research as Input Pipeline

Rule construction in §5 originates from a manual statutory reading process: cross-referencing a set of legal texts against a set of concepts to track (e.g., "high-risk system," "provider," "human oversight"), then deciding whether each concept is addressed by each text (`true`/`false`/`undefined`). This describes the input-generation process for the formal framework in §2.2–2.8; it is not itself a formal result. Encoding statutory text into conjunctive rules is human legal interpretation — not decidable, not automated. The theorems prove properties of the *formal model*; they do not certify that the model faithfully represents the underlying statute.

### 2.11 Honest Framing

The §9 conjecture of the preprint covers "any conjunctive ABAC language" — true for the core (S(Rᵢ) polytope×finite-set, union property). Harmonization Gap additionally requires **Lemma H** — the bridging step that reduces labeled-max-aggregation to the union form Theorem 2 handles. The correct claim for this paper: *"this confirms the §9 conjecture for the labeled extension, via the level-cut reduction in Lemma H — not as a free corollary of Theorem 2 alone."*

*Scope boundary: H7/H8 vs. the §9 conjecture.* Definition H7 (Classification Scheme, §2.7) and Definition H8 (Induced Cover, §2.8) are **not** instances of Theorem 2's polytope-union machinery. H7's incomparability proofs (Propositions H7.1/H7.2) proceed by direct factorization counterexample over a pre-`Ctx` domain `Attr`; H8's incompatibility proof (Observation H8.1) proceeds by refinement counterexample over `Ctx` itself but does not use the union-of-`S(Rᵢ)` argument of Theorem 2 — it is a structural relation *between* two covers, not a property *of* a single `S(R)`. Theorem C (§2.8, full proof §A.4) extends H8's per-instance check to a per-policy-pair decidability/enumerability result; it proceeds by per-block subset-check (Lemma 1), not by the union argument, and is likewise orthogonal to the §9 conjecture. Accordingly, this paper does not claim H7/H8/C as cross-domain validation evidence for the §9 conjecture, nor does any of them constitute a counterexample: all three are contributions of this paper developed independently of the preprint's apparatus, orthogonal to the generality question §9 raises.

*Scope boundary: H9–H13 vs. the §9 conjecture.* Definitions H9–H13 and Theorems A′/B′ (§2.9) are likewise **not** instances of Theorem 2's polytope-union machinery — `ω`'s union-aggregation over `℘(O)` is a set-union over obligor labels, not a region-union in `Ctx`; and Theorem B′ as proved here is brute-force enumerability, not the symbolic kind Theorem B provides (§2.9's honesty remark). Both are independent contributions of this paper, orthogonal to both the §9 conjecture and to H7/H8/C. (The lex-specialis aggregation question for `ω` — a poset-minimum selection, again not a region-union — is developed in a companion paper and is likewise outside the §9 conjecture's scope.)

---

## §3 Sources & Context Schema

### 3.1 Legal Sources

- **EU AI Act:** Final version, phased into effect 2024–2026.
- **Luật 134/2025/QH15 (Luật Trí tuệ nhân tạo Việt Nam):** Passed by the National Assembly, effective 1 March 2026.
- **Nghị định 142/2026/NĐ-CP:** Implementing decree for the AI Law, effective 30 April 2026.
- **ASEAN AI Governance Guide (2024) and Expanded ASEAN Guide on AI Governance and Ethics — Generative AI (2025):** Guidance documents, non-binding.

### 3.2 Shared Context Schema (`Ctx`)

Dimensions selected based on factors present across all three legal regimes:

| Dimension | Vocabulary | Notes |
|---|---|---|
| `risk_tier` | `{Minimal, Limited, Medium, High, Unacceptable}` | Merge of EU 4-tier and VN 3-tier. **ASSUMED_PARAMETER:** `Medium` maps to `Limited` (conservative) or `High` (liberal) for EU; `Unacceptable` maps to `Cao` or `Bị Cấm` for VN. Tested via sensitivity analysis (§7.4). |
| `sector` | `{Healthcare, Finance, Education, PublicSafety, GenAI, Other}` | |
| `system_role` | `{Provider, Deployer, User}` | |
| `lifecycle_stage` | `{PreMarket, PostMarket}` | |
| `modification_increases_risk` | `{true, false}` | |
| `serious_harm_discovered` | `{true, false}` | |
| `interacts_with_human` | `{true, false}` | |
| `existing_sector_certification` | `{true, false}` | |

```
|Ctx| = 5 × 6 × 3 × 2 × 2 × 2 × 2 × 2 = 2.880 context points
```

Verified by two independent methods: manual arithmetic (5×6×3×2⁵ = 90×32 = 2.880) and brute-force Python enumeration of all combinations — both agree.

**Why these eight dimensions, and not others.** Selection followed three criteria: (1) the dimension is explicitly discriminated by at least one of the three encoded instruments' rule conditions, not merely mentioned in recitals or preambles; (2) statutory text confirms the dimension is legally operative in an obligation-triggering condition, not just descriptive metadata; (3) the dimension has a finite, closed vocabulary, so Lemma 1's `S(R) = S_num(R) × S_cat(R)` factorization applies without modification. Three candidate dimensions were considered and excluded: *harm_scale*/*reversibility* (present in VN's Nhóm IV criteria, but typically expressed as a numeric-continuous scale in the underlying assessment rather than a closed category, so not encodable under criterion 3 without a separate discretization decision this paper does not make); *intended_purpose*/*use_case* (present in EU Annex III's named-use-case enumeration, but with cardinality too large for the kind of exhaustive, closed-vocabulary treatment this paper's decidability results depend on); and *jurisdiction_of_deployer* (relevant to the cross-border scenarios flagged in §9's Future Work, but reserved there rather than encoded here, since doing so properly requires the actor- and jurisdiction-indexed `Ctx` shape that section describes, not a ninth value bolted onto the current schema). One included dimension, `sector`, is load-bearing only for ASEAN's GenAI-specific rule (§5.4) — a future encoding that drops ASEAN could drop `sector` as well without affecting any EU/VN result in this paper.

---

## §4 Seven Obligation Pairs

| # | Domain | EU AI Act anchor | Vietnam anchor | ASEAN anchor | β / divergence type (EU / VN / ASEAN) † |
|---|---|---|---|---|---|
| 1 | Risk classification & reclassification | Art. 9 — continuous lifecycle | Điều 10 Khoản 1 (self-classify pre-market) + Khoản 2 (reclassify on modification) + Khoản 5 (periodic inspection) | Accountability/human-centricity principle | Binding / Binding / Voluntary |
| 2 | Conformity assessment (high-risk) | Art. 11 — pre-market technical documentation | Điều 13 + Nghị định 142 Điều 13 (certification reuse/interoperability) | Not addressed | Binding / Binding (interoperable) / ⊥ |
| 3 | Human oversight scope | Art. 14 — tier-gated (High/Unacceptable only) | Điều 4 Khoản 2 (universal principle, all tiers) | Human-centricity principle | Binding (high-risk only) / Binding (all tiers, principle-level) / Voluntary |
| 4 | Incident reporting / record-keeping | Art. 12 — uniform automatic logging | Điều 12 + Nghị định 142 Điều 12 Khoản 5 (severity-proportional) | Gen AI Guide: disclosure/labelling (recommended) | Binding (uniform) / Binding (severity-scaled) / Recommended |
| 5 | AI-interaction transparency | Art. 50 | Điều 11 Khoản 1 (AI disclosure) | Transparency principle + proportionate explainability | Binding / Binding / Voluntary |
| 6 | Risk-management temporality | Art. 9 — continuous mandate | Nghị định 142 (event-triggered: `serious_harm_discovered`) | Not addressed | Binding (continuous) / Binding (event-triggered) / ⊥ |
| 7 | Risk taxonomy structure | Annex III — fixed categorical catalog | Danh mục under Điều 13 Khoản 4 — also extensional catalog | 6 qualitative harm-type categories (Gen AI) | Incomparable (catalog-structure mismatch, see §5.7) |

† Pairs #1–#6: entries report `β` values per Definition H3 — `β: Ctx → B` is well-defined at these rows. Pair #7: the entry reports a classification-scheme comparison per Definition H7, which operates at the *pre-`Ctx` layer* where `β` is undefined; "Incomparable" is not a `B`-value and should not be read as one. See §5.7.

*Reading by column:* ASEAN is ⊥/Voluntary/Recommended across nearly every row — including obligations Vietnam has already made binding. The largest gap is not EU↔VN (widely studied) but **VN↔ASEAN**: Vietnam is moving faster than its own regional bloc. The AI Law effective 1 March 2026 and Nghị định 142 effective 30 April 2026 make this the most underexplored pairing.

---

## §5 HSDL-Style Encoding

### 5.0 Bindingness & Obligor Types

```
B = { ⊥, Voluntary, Recommended, Binding }
rank: ⊥ → 0, Voluntary → 1, Recommended → 2, Binding → 3

O = { Provider, Deployer, Regulator, ThirdPartyCertifier }   // Definition H9, §2.9 — flat, unranked
```

`obligor:` annotations below populate `ο(Rᵢ) ⊆ O` (Definition H10). **v11 extension:** Groups 3–6 are now annotated on the EU and VN sides (§5.3–§5.6); the ASEAN side carries `ο = ?` (unencoded) for these groups because the ASEAN Guide's principle-level statements do not name specific obligors at the level of detail needed for Definition H10 — a structurally informative finding (cf. §8). Phase 2 of v11 expanded ο-coverage from 2 groups to 6 (EU/VN sides); §B.2 documents the per-group legal research, and Finding #18 reports four new Dimension Independence instances surfaced by this extension.

### 5.1 Group 1 — Risk Classification & Reclassification

```hsdl
policy EU_AIAct {
    rule art9_risk_mgmt_continuous [bindingness: Binding, obligor: {Provider}]:
        risk_tier in [High, Unacceptable];
        // Unconditioned on lifecycle events — obligation holds at every
        // PreMarket/PostMarket instant (continuous by construction).
        // obligor: Provider operates its own continuous risk management system.
}

policy VN_AILaw_134_2025 {
    rule art10_kh1_self_classify [bindingness: Binding, obligor: {Provider}]:
        system_role == Provider &&
        lifecycle_stage == PreMarket;

    rule art10_kh2_reclassify_on_modification [bindingness: Binding, obligor: {Provider}]:
        modification_increases_risk == true;
        // Event-gated — fires only when the triggering condition occurs.

    rule art10_kh5a_supervision_highrisk [bindingness: Binding, obligor: {Regulator}]:
        risk_tier == High;
        // Điều 10 Khoản 5(a): mandatory periodic inspection for High-risk
        // systems. Not gated on lifecycle_stage or modification — closes
        // the post-market steady-state void at ctx* (see worked example).
        // obligor: competent state authority conducts the inspection.

    rule art10_kh5b_supervision_medium [bindingness: Binding, obligor: {Regulator}]:
        risk_tier == Medium;
        // Điều 10 Khoản 5(b): supervision via reports/sample checks for
        // Medium-risk systems. Statutory text uses mandatory language
        // without "may"/"should" qualifiers → Binding. Intensity difference
        // from (a) is an operational specificity distinction (see §8),
        // not a bindingness distinction.

    // risk_tier ∈ {Minimal, Limited}: no rule added.
    // Khoản 5(c) explicitly establishes no periodic obligation at low tiers
    // → Regulatory Void by design (Definition H3.5), not an omission.
}

policy ASEAN_Guide {
    rule accountability_principle [bindingness: Voluntary]:
        true;   // Tautology — S(R) = Ctx
}
```

**Worked Theorem A computation — `ctx*`: `risk_tier=High, system_role=Provider, lifecycle_stage=PostMarket, modification_increases_risk=false`**

*Without Điều 10 Khoản 5 (risk-classification rules Khoản 1/2 only):*

| Regime | Rule firing | β(ctx*) |
|---|---|---|
| EU | `art9_risk_mgmt_continuous` (no lifecycle gate) | **Binding** |
| VN | *No rule fires* — `art10_kh1` requires PreMarket; `art10_kh2` requires modification event | **⊥** |
| ASEAN | `accountability_principle` (tautology) | **Voluntary** |

→ `ctx* ∈ Void↓(EU→VN)` — VN is not merely "less strict" but has no rule addressing this scenario.

*Adding Điều 10 Khoản 5 (statutory text verified against independent sources; see References):*

| Regime | Rule firing | β(ctx*) |
|---|---|---|
| EU | `art9_risk_mgmt_continuous` | **Binding** |
| VN | `art10_kh5a_supervision_highrisk` (`risk_tier==High`, no lifecycle gate) | **Binding** |
| ASEAN | `accountability_principle` | **Voluntary** |

→ `ctx* ∉ Gap↓(EU→VN)` — **void closed**, verified by brute-force code. Robust under all 4 sensitivity encodings (§7.4): `ctx*`'s `risk_tier=High` falls within every `eu_highset`/`vn_highset` variant.

**⚠️ Obligor mismatch — surfaces when the void is closed:** Điều 10 Khoản 5 is an obligation of the **competent state authority** (regulator-side: the state inspects the entity), as confirmed by the immediately following text (inspection/supervision results are the basis for the authority to require reclassification, supplementary documentation, or suspension). EU Art. 9 is an obligation of **the provider** to continuously operate a risk management system (provider-side: self-monitoring). `β: Ctx → B` (Definition H3) measures "what level of obligation applies at ctx," not "who must do what to whom" — so the void closes numerically per the formula, but the claim "VN has an equivalent obligation to EU at ctx*" is an overclaim. The correct framing: *"VN's Điều 10 Khoản 5 closes the apparent regulatory void at the bindingness layer for High-risk post-market systems — but the obligation type differs structurally: EU mandates continuous provider-side risk management; VN mandates periodic regulator-side inspection."* **Formalized (§2.9):** `ω_EU(ctx*) = {Provider}`, `ω_VN(ctx*) = {Regulator}` — `ctx* ∈ ObligorGap(EU,VN)` (Definition H13), the worked Instance 1 of Proposition H13.1.

**Remaining void — `risk_tier=Unacceptable` (240/2.880 contexts):** `art10_kh5a`'s literal `risk_tier==High` does not automatically cover `Unacceptable`. This is a consequence of §3.2's ASSUMED_PARAMETER mapping (`Unacceptable→Cao`), not an encoding error specific to this rule — the same family as Group 2's flag (§5.2). Closes completely under Encodings B2/B3 (§7.4).

### 5.2 Group 2 — Conformity Assessment + Interoperability

```hsdl
policy EU_AIAct {
    rule art11_conformity_assessment [bindingness: Binding,
                                      obligor: {Provider}]:
        risk_tier in [High, Unacceptable];
        // obligor: provider prepares technical documentation and conducts
        // the conformity assessment itself — Art. 43(2): for Annex III
        // points 2-8 (the dominant case), assessment is "based on internal
        // control as referred to in Annex VI, which does not provide for
        // the involvement of a notified body." EXCEPTION (not encodable in
        // current Ctx — no Annex-III-point dimension): Annex III point 1
        // (biometric ID) may instead route through a notified body
        // (Art. 43(1), Annex VII), conditional on harmonised-standards
        // compliance. Annex I product-safety-crossover systems also always
        // require third-party assessment, a separate, unencoded category.
}

policy VN_AILaw_134_2025 {
    rule art13_conformity_assessment_highrisk [bindingness: Binding,
                                               obligor: {Provider}]:
        risk_tier == High;
        // obligor: Điều 13 Khoản 2(b) — for High-risk systems NOT on the
        // mandatory-certification Danh mục, "nhà cung cấp tự đánh giá sự
        // phù hợp HOẶC thuê tổ chức đánh giá" (provider self-assesses OR
        // hires an assessment org) — Provider is the guaranteed obligor;
        // ThirdPartyCertifier is the provider's optional choice, not a
        // named co-obligor of this branch. EXCEPTION (not encodable in
        // current Ctx — no Danh mục-membership dimension): Khoản 2(a)
        // systems on the mandatory-certification Danh mục require a
        // registered/recognized assessment org — {Provider,
        // ThirdPartyCertifier} — and this is the *same* still-draft Danh
        // mục already flagged uncertain in Proposition H7.1.

    rule art13_certification_reuse [bindingness: Binding,
                                    obligor: {Provider}]:
        risk_tier == High &&
        existing_sector_certification == true;
        // Reduces required new evidence; does not reduce bindingness.
        // "Assessment interoperability" ≠ bindingness level —
        // a dimension Definition H1 cannot model (see §8).
        // obligor: read as a variant of the Khoản 2(b) self-assess track
        // with reduced burden via reuse of prior sector certification —
        // Provider guaranteed; whether the prior-certifying body or a
        // Regulator must additionally re-engage to approve the reuse is
        // an OPEN ITEM not resolved by statutory text cited in this paper
        // (§2.9) — left unencoded rather than asserted.
}
```

At `risk_tier=High`: β_EU = β_VN = Binding → no bindingness gap. `ω_EU = ω_VN = {Provider}` for the *dominant case* on both sides — Group 2 is a **convergence point** on both output dimensions (`β` and `ω`), not an `ObligorGap` instance (cf. §2.9), but the convergence holds only because both regimes default to provider self-assessment outside two narrow, currently-unencodable exception zones: EU's Annex III point 1 (biometric ID) and VN's Khoản 2(a) mandatory-certification Danh mục. Whether *those* zones converge or diverge in obligor terms is genuinely unresolved by this paper's `Ctx` schema — not claimed either way. The remaining unmodeled axis at the dominant-case level is *assessment interoperability* (compliance cost / reduced evidentiary burden) — a dimension neither `β` nor `ω` as currently defined captures; see §8.

**⚠️ At `risk_tier=Unacceptable`:** EU fires Binding for all 576/576 contexts of this tier; VN's rule (`risk_tier == High`, excluding Unacceptable) fires for 0/576. The entire `Gap↓(EU→VN)` for Group 2 (576 contexts) falls exactly at this tier. *Interpretation caution:* "Unacceptable risk" under Art. 5 EU means the system is **absolutely prohibited** — the concept of "conformity assessment" (a certification process before market entry) may have no legal meaning for a completely banned product (one does not certify what is prohibited). If so, these 576 contexts reflect an **encoding comparing two structurally incompatible concepts** at that tier, not a genuine regulatory gap on VN's part. Flag explicitly in Discussion.

### 5.3 Group 3 — Human Oversight (tier-gated vs. universal principle)

```hsdl
policy EU_AIAct {
    rule art14_human_oversight [bindingness: Binding,
                                obligor: {Provider, Deployer}]:
        risk_tier in [High, Unacceptable];
        // obligor: Art. 14(3)(a) — Provider builds oversight measures into
        // the system before placing on market; Art. 14(3)(b) + Art. 26(2) —
        // Deployer assigns oversight to natural persons with the necessary
        // competence, training, and authority. Both bear duties jointly;
        // ω uses set union per Definition H11.
        // Web-verified 21/6/2026: artificialintelligenceact.eu/article/14
        // and /article/26, cross-checked against AI Act Service Desk
        // (ai-act-service-desk.ec.europa.eu).
}

policy VN_AILaw_134_2025 {
    rule dieu4kh2_human_control_principle [bindingness: Binding,
                                           obligor: {}]:
        true;   // Điều 4 Khoản 2: AI serves humans, does not replace human
                // authority/responsibility; human control and intervention
                // ability must be maintained over all AI decisions/behavior.
                // Tautology — Binding, unlike ASEAN's Voluntary tautology.
                // obligor: empty per Definition H10 — the provision is a
                // Chương I "nguyên tắc cơ bản" (foundational principle) and
                // does not name a specific actor as duty-bearer. The
                // operative provisions that DO name actors (Điều 10, Điều
                // 11, Điều 13) sit in Chương II (Điều 9–15, "Phân loại và
                // quản lý rủi ro") and govern other domains, whereas this
                // Điều 4 Khoản 2 sits in Chương I; this Khoản 2 is a
                // free-standing principle with
                // ο = ∅ — explicit, not a research gap. Web-verified
                // 21/6/2026: luatvietan.vn/luat-tri-tue-nhan-tao.html
                // (full Điều 4 text) and the official Quốc hội text.
}

policy ASEAN_Guide {
    rule human_centricity_principle [bindingness: Voluntary]:
        true;   // ASEAN AI Governance Guide's human-centricity/human-
                // oversight principle. Tautology — S(R) = Ctx, mirroring
                // G1's accountability_principle and G5's transparency_
                // principle (§5.1, §5.5). Cf. §4 Pair #3's ASEAN anchor
                // ("Human-centricity principle," Voluntary) and §5.9's
                // Observation, both of which already assumed this rule's
                // presence in the encoding — added here so §5.3 matches.
                // Does not change any §7 D/H value already reported:
                // against EU's β∈{⊥,Binding} and VN's β≡Binding, a
                // Voluntary ASEAN floor yields the same Gap↓(EU→ASEAN)
                // and Gap↓(VN→ASEAN) figures as the previously-unencoded
                // (β_ASEAN≡⊥-by-default) state, since Binding > Voluntary
                // > ⊥ either way.
}
```

**Reversal finding:** `ctx'`: `risk_tier = Minimal`.

| Regime | Rule firing | β(ctx') |
|---|---|---|
| EU | *No rule fires* | **⊥** |
| VN | `dieu4kh2_human_control_principle` (tautology) | **Binding** |

→ `ctx' ∈ Gap↑(VN→EU)` — at the lowest risk tier, **VN is stricter than EU**. Formal, computed result reversing the conventional assumption that "EU leads, Global South follows."

**⚠️ Dimension Independence Instance 2 — added v11.** At every `risk_tier ∈ {High, Unacceptable}` context (1,152/2,880 contexts), both `β_EU = β_VN = Binding` (no bindingness gap at this tier), but `ω_EU = {Provider, Deployer}` while `ω_VN = ∅`. By Definition H13, all 1,152 of these contexts are `ObligorGap(EU, VN)` instances. This is a second confirmed instance of Proposition H13.1 (§2.9), structurally distinct from Group 1's `ctx*`: where Group 1 shows two named obligor sets in disagreement (`{Provider}` vs `{Regulator}`), Group 3 shows a *named obligor set vs. unnamed/principled-only* — a categorically different kind of mismatch. The proposition now has both kinds covered, strengthening it from "exists ≥1 instance" to "exists ≥2 instances spanning distinct mismatch types." 

*What ω_VN = ∅ means here, and what it doesn't.* The empty obligor set is a formal `INDETERMINATE`-style sentinel (Definition H10 explicitly provides for it), not a claim that Điều 4 Khoản 2 carries no enforceability. Vietnamese administrative and civil enforcement frameworks can attach to outcome-stated principles via downstream operative provisions and general administrative law; the question this paper measures is narrower — whether *the text of the obligation itself* names a duty-bearer of `O = {Provider, Deployer, Regulator, ThirdPartyCertifier}`. Điều 4 Khoản 2 does not; Art. 14 + Art. 26 do. That difference is what the 1,152 ObligorGap contexts formally record.

**Note on operational specificity (illustrative, not a formal measure).** Both rules are labeled `Binding` by Definition H1's legal-force criterion (mandatory statutory language, no "có thể"/"may" qualifier) — that criterion is about legal force, not about how concretely the obligation's content is specified, and the two can diverge. Điều 4 Khoản 2 states outcomes — AI must serve humans and not displace human authority/responsibility; human control and intervention ability must be maintained over all decisions and behavior of the system; system/data security must be ensured; the development and operation process must be inspectable and supervisable — without enumerating a specific mechanism for any of them. Art. 14(4), where it fires, states comparable outcomes (understand capacities/limitations, avoid automation bias, correctly interpret output, decide not to use/override/reverse the output) but additionally specifies a concrete enabling mechanism for one of them — a stop-button-or-equivalent procedure bringing the system to a safe halt (Art. 14(4)(e), paraphrased) — plus a quantified verification rule for certain biometric systems (two-person sign-off, Art. 14(5)). This is a coarse, manually-read proxy for "operational specificity," not a formal H-definition comparable to bindingness (H1) or obligor (H9–H13) — offered because external review correctly noted this paper flags the specificity gap (Finding #5b, §8) without ever measuring it. A rule stated as an outcome is not automatically less enforceable than one that also names a mechanism — Vietnamese administrative/civil enforcement can act on outcome-stated obligations too — but the *kind* of compliance evidence each obligation calls for differs, and `β` does not capture that difference. **Read Finding #2's "VN stricter" as a claim about formal legal force, verified by code; treat any inference from it to comparative real-world enforceability as a separate, currently unmeasured claim** (restated at Finding #2 itself, §6). The `ω_VN = ∅` finding here is the obligor-dimension analogue of this specificity caveat: the principle-vs-mechanism gap that §5.3 flags informally is now *additionally* measured along an orthogonal formal axis (ο), where the gap shows up as a 1,152-context ObligorGap.

### 5.4 Group 4 — Incident Reporting (uniform vs. severity-proportional vs. recommended)

```hsdl
policy EU_AIAct {
    rule art12_recordkeeping_uniform [bindingness: Binding,
                                      obligor: {Provider, Deployer}]:
        risk_tier in [High, Unacceptable];
        // obligor: Provider's log-design and retention duties arise under
        // Art. 12(1) and Art. 19 ("Providers of high-risk AI systems shall
        // keep the logs..."); Deployer's parallel six-month retention duty
        // arises under Art. 26(6) ("Deployers... shall keep the logs...").
        // Obligor set: {Provider, Deployer}.
        // Web-verified 21/6/2026:
        // artificialintelligenceact.eu/article/12, /article/26, /article/19.
}

policy VN_AILaw_134_2025 {
    rule art10_kh3_notify_classification [bindingness: Binding,
                                          obligor: {Provider}]:
        risk_tier in [Medium, High] &&
        lifecycle_stage == PreMarket;
        // obligor: Điều 10 Khoản 3 — Provider must notify classification
        // result to the AI single-window portal (Cổng thông tin điện tử
        // một cửa) before deployment. The Regulator is the recipient, not
        // a co-obligor (Definition H10 distinguishes duty-bearer from
        // recipient — see §2.9 disambiguation). Web-verified 21/6/2026:
        // wikilegal.vn/quy-dinh-ve-phan-loai..., aplawjapan.com newsletter
        // 20260528 (cites Điều 5 NĐ142 + Điều 10 Khoản 3 Luật).

    rule decree142_art12_kh5_incident_report [bindingness: Binding,
                                              obligor: {Provider, Deployer}]:
        serious_harm_discovered == true;
        // obligor: NĐ142 Điều 19 (provision number correction noted v11 —
        // paper's rule name retains "art12_kh5" for citation continuity
        // with prior versions, but the operative provision in the final
        // Nghị định is Điều 19, not Khoản 5 Điều 12; both reference the
        // same incident-reporting mechanism per Khoản 5 Điều 12 Luật AI).
        // Provider is the primary reporter ("nhà cung cấp ... thực hiện
        // báo cáo sơ bộ"); Deployer is the fallback reporter ("nếu không
        // liên lạc được với nhà cung cấp, bên triển khai có trách nhiệm
        // thực hiện việc báo cáo"). Both are duty-bearers; Definition
        // H11's union aggregation collapses to {Provider, Deployer} on
        // any context where ≥1 of them is obligated, matching the legal
        // intent. Web-verified 21/6/2026: luatvietnam.vn (sample form
        // AI01a citing Điều 19), aplawjapan.com newsletter 20260528.
}

policy ASEAN_Guide {
    rule genai_disclosure_labelling [bindingness: Recommended]:
        sector == GenAI;
        // obligor: ? — the ASEAN Guide states the disclosure principle at
        // a high level without naming a specific actor; "developers and
        // deployers are encouraged to..." appears in some passages but
        // is not consistently scoped to a specific obligation. Left
        // unencoded per Definition H10's escape valve (ο = ?), the same
        // status as Group 2's exception zones and Group 3 VN side ω = ∅.
}
```

At `sector=GenAI, serious_harm_discovered=false`: β_EU=Binding, β_VN=⊥, β_ASEAN=Recommended — three distinct levels on the same context.

**Second reversal instance (cf. Finding #2, Group 3).** At `risk_tier=Medium, lifecycle_stage=PreMarket`: `art10_kh3_notify_classification` fires (β_VN=Binding) while no EU rule in this group fires (β_EU=⊥, since `Medium ∉ {High,Unacceptable}`) — `VN>EU`, independent of `serious_harm_discovered`. This is a mechanism distinct from Group 3's reversal (a risk-tier threshold strictly broader than EU's, not a universal tautology), and is already included within this group's reported `VN>EU=1,008 (35.0%)` figure (§7.1).

*Mechanism-level attribution — resolved, re-verified by brute-force script with mechanism tagging (20/6/2026).* Of the 1,008 `VN>EU` contexts in Group 4: **144** fire *only* via `art10_kh3_notify_classification` (`risk_tier=Medium ∧ lifecycle_stage=PreMarket`, no serious harm discovered); **720** fire *only* via `decree142_art12_kh5_incident_report` (`serious_harm_discovered=true`, outside `Medium ∧ PreMarket`); **144** fire via *both* mechanisms simultaneously. By inclusion–exclusion, `144 + 720 + 144 = 1,008`, matching the reported total exactly — confirming both mechanisms are independently non-empty contributors, not an artifact of overlap. The open item flagged in earlier drafts (re-run with mechanism-level tagging) is closed; the structural claim that the reversal recurs via an independent mechanism holds regardless, and is now additionally quantified.

**⚠️ Dimension Independence Instance 3 — added v11.** At contexts where `risk_tier=High ∧ lifecycle_stage=PreMarket ∧ serious_harm_discovered=false` (144/2,880 contexts): both `β_EU = β_VN = Binding`, but `ω_EU = {Provider, Deployer}` while `ω_VN = {Provider}` — Deployer's log-retention duty (Art. 26(6); Art. 19 imposes the parallel duty on the Provider) has no direct VN counterpart in this group's encoding. By Definition H13, all 144 contexts are `ObligorGap(EU, VN)` instances. This is a *narrower* mismatch than Group 3's (proper-subset rather than disjoint-from-empty), but structurally still on the Dimension Independence side: equal bindingness with different obligor sets. Verified by `phase2_obligor.py`.

### 5.5 Group 5 — Transparency (convergence point)

```hsdl
policy EU_AIAct {
    rule art50_disclosure [bindingness: Binding, obligor: {Provider}]:
        interacts_with_human == true;
        // obligor: Art. 50(1) — "Providers shall ensure that AI systems
        // intended to interact directly with natural persons are designed
        // and developed in such a way that the natural persons concerned
        // are informed that they are interacting with an AI system."
        // Provider is the named duty-bearer; sub-cases for emotion
        // recognition and deepfakes (Art. 50(2)-(4)) add Deployer-side
        // duties that the current Ctx does not distinguish — flagged as
        // an exception zone analogous to §5.2's Annex III point 1 carve-
        // out, but the dominant case for `interacts_with_human=true` is
        // {Provider}. Web-verified 21/6/2026: artificialintelligenceact.eu
        // /article/50.
}

policy VN_AILaw_134_2025 {
    rule art11_kh1_ai_disclosure [bindingness: Binding, obligor: {Provider}]:
        interacts_with_human == true;
        // obligor: Điều 11 Khoản 1 — Provider designs the system with
        // disclosure built in. Same dominant-case obligor as EU Art. 50,
        // hence the convergence finding below.
}

policy ASEAN_Guide {
    rule transparency_principle [bindingness: Voluntary]:
        true;
}
```

β_EU = β_VN = Binding for every context where `interacts_with_human=true` → **convergence point**, no gap. Including this case demonstrates methodological evenhandedness: the formal tool reports alignment where it exists and does not selectively surface only gaps.

**Obligor convergence confirmed (v11).** `ω_EU = ω_VN = {Provider}` for the dominant case (interacts_with_human=true, outside Art. 50(2)-(4) sub-cases). G5 is a convergence point on both `β` and `ω` — Definition H13's `ObligorGap = 0` for this group (verified by `phase2_obligor.py`). G5 is now the *second* obligor-convergence finding alongside G2, both at `ω = {Provider}` for dominant cases.

*Note:* VN Điều 11 aligns with EU Art. 50, not with Art. 11 — the number collision ("Điều 11"/"Art.11") is purely numerical, not legal.

### 5.6 Group 6 — Risk-Management Temporality

```hsdl
policy EU_AIAct {
    rule art9_risk_mgmt_temporality [bindingness: Binding,
                                     obligor: {Provider}]:
        risk_tier in [High, Unacceptable];
        // Continuous obligation — same pattern as Group 1, tracked
        // separately to isolate the temporal dimension specifically.
        // obligor: same as G1 art9_risk_mgmt_continuous — Provider
        // operates the risk-management system, Art. 9(1).
}

policy VN_AILaw_134_2025 {
    rule decree142_event_triggered_control [bindingness: Binding,
                                            obligor: {Deployer}]:
        serious_harm_discovered == true;
        // Nghị định 142: upon discovering serious harm risk, apply
        // control/risk-limitation measures immediately.
        // Event-triggered, not a continuous mandate.
        // obligor: "tổ chức triển khai phải áp dụng ngay biện pháp kiểm
        // soát, hạn chế rủi ro" — "the deploying organization must
        // immediately apply control measures." Deployer is the named
        // duty-bearer; this is the same provision text as the analogous
        // duty in NĐ142's risk-control article. Web-verified 21/6/2026:
        // caa.gov.vn (Vietnam Civil Aviation Authority's official
        // summary), cross-checked against baomoi.com and vnexpress.net.
}

policy ASEAN_Guide {
    // No rule — neither the 2024 Guide nor the 2025 Gen AI Guide
    // addresses risk-management temporality as a standalone obligation.
}
```

At `risk_tier∈{High,Unacceptable}, serious_harm_discovered=false` (steady-state, no harm detected): β_EU=Binding (continuous, not event-gated), β_VN=⊥ (no triggering event), β_ASEAN=⊥ (not addressed). Gap of the same *type* as Group 1's post-market void but a distinct obligation-domain (continuous obligation in general, not risk-classification specifically) — 576 contexts (full slice `{H,U}×serious_harm=false`).

**⚠️ Dimension Independence Instance 4 — added v11.** At contexts where `risk_tier∈{High,Unacceptable} ∧ serious_harm_discovered=true` (576/2,880 contexts), both `β_EU = β_VN = Binding`, but `ω_EU = {Provider}` while `ω_VN = {Deployer}` — the EU's continuous provider self-monitoring and VN's event-triggered deployer control are *disjoint* obligor sets at the same bindingness level. By Definition H13, all 576 contexts are `ObligorGap(EU, VN)` instances. This is structurally the closest analogue to Group 1's `ctx*` (also disjoint single-actor obligor sets), but on a different temporal axis: G1 contrasts Provider-self-monitor vs. Regulator-inspect; G6 contrasts Provider-self-monitor (continuous) vs. Deployer-control (event-triggered) — different sides of the obligation triangle, same kind of structural mismatch. Verified by `phase2_obligor.py`.

### 5.7 Pair #7 — Risk Taxonomy Structure (classification-scheme level)

This pair concerns **classification architecture**, not **bindingness levels on shared contexts**. Definition H4 cannot measure it — not because encoding was not attempted, but because the problem is *at the layer before `Ctx`* (see Definition H7). Formalized in Propositions H7.1/H7.2 (§2.7).

EU/ASEAN (H7.2): proven incomparable by codomain mismatch — unaffected by legal-research corrections.
EU/VN (H7.1): argued incomparable by catalog-structure mismatch; caveat on draft Danh mục status applies (see §2.7).

A full general theorem covering all scheme pairs is future work (Theorem D — distinct from Theorem C, §2.8: Theorem C now generalizes H8's cover-refinement result across regime pairs **(fully proved in v11; Refinement Matrix §7.5, proof §A.4)**; Theorem D would analogously generalize H7's scheme-factorization result across classification-scheme pairs, but remains future work because H7's proofs are codomain-level factorization counterexamples rather than per-block subset checks — a distinct proof technique. The two target different formal objects and should not share a name). The formal tool **correctly certifies its own boundary** — converting a "limitation" into an explicit formal result.

### 5.8 EU Signal Homogeneity

Reading the rule bodies from §5.1–5.6:

| Group | EU rule condition |
|---|---|
| G1 | `risk_tier in [High, Unacceptable]` |
| G2 | `risk_tier in [High, Unacceptable]` |
| G3 | `risk_tier in [High, Unacceptable]` |
| G4 | `risk_tier in [High, Unacceptable]` |
| G6 | `risk_tier in [High, Unacceptable]` |
| G5 | `interacts_with_human == true` *(distinct)* |

**Proposition H8.2 (EU Signal Homogeneity).** 5/6 EU rules in §5 are literally identical conditions — differing only in rule name and article citation. Two derivable consequences (not merely brute-force observations):

1. **Disjointness of `Gap↓(EU→VN)` and `Gap↓(VN→EU)` is a corollary:** for G1, G2, G3, G4, G6, `EU>VN` requires `risk_tier∈{High,Unacceptable}` while `VN>EU` requires `β_EU=⊥`, i.e., `risk_tier∉{High,Unacceptable}` — the two conditions are mutually exclusive on the same variable. G5 is a convergence point and contributes to neither direction.

2. **`D(EU→ASEAN)` reduces to a two-set union:** since no ASEAN rule in §5 carries label `Binding` (only `Voluntary`/`Recommended`/`⊥`), `EU>ASEAN` in every group is equivalent to "EU fires" — so all of `D(EU→ASEAN)` reduces to `|{risk_tier∈{H,U}}| ∪ |{interacts=true}|`, without needing to enumerate 6 groups separately.

The structural diversity in this paper resides entirely on the VN/ASEAN side (event-triggered vs. tautology vs. tier-gated vs. severity-proportional). EU's contribution is one repeated binary signal.

**Symmetry check.** The homogeneity check above is applied to the EU side; for completeness, the same check is applied to VN and ASEAN. VN's 11 rules span 7/8 `Ctx` dimensions — the opposite of EU's pattern. ASEAN's 4 rules show a third pattern: three universal tautologies and one sector-gated. This reflects each instrument's genre: risk-tiered statute, multi-factor decree, principle-based guide.

### 5.9 Observation (Encoding Bindingness Dichotomy)

```
In the §5 encoding, λ(Rᵢ) = Binding for every named rule in every EU and VN
mini-regime (by explicit labeling in §5.1–5.6). By well-formedness
(λ(Rᵢ) ≠ ⊥, Definition H2) and since Binding is the only non-⊥ label used
on either side:

  β_EU(ctx), β_VN(ctx) ∈ {⊥, Binding}   for all ctx ∈ Ctx.

Corollary: Gap↓(EU→VN) = Void↓(EU→VN) exactly (used by Finding #13b, §6).
```

The intermediate levels `Voluntary`/`Recommended` never distinguish EU from VN in this paper's encoding; they do discriminating work only where ASEAN is involved (`β_ASEAN ∈ {⊥, Voluntary, Recommended}`, never `Binding`). This is a derived fact about the §5 encoding — not an additional assumption — stated here, before §6, because Lemma H′ (§2.5) and Finding #13b (§6) both rely on it.

**Corollary H5.2 (Aggregation-Rule Invariance, per-group).** The choice of aggregation function in Definition H3 — `max` (*lex strictior*) as encoded, or alternatives such as *lex specialis*, unanimity, or arbitrary join — does not affect `β` in this paper's §5.1–5.6 encoding. Two structural facts force this:

1. **ASEAN side: at most one rule per mini-regime.** Inspection of §5.1–5.6: each ASEAN mini-regime contains 0 or 1 rule (`accountability_principle` in G1, `dieu4kh2`-counterpart `human-centricity` in G3, `genai_disclosure_labelling` in G4, `transparency_principle` in G5; G2 and G6 have no ASEAN rule). With at most one rule firing, no aggregation is invoked.

2. **EU/VN side: co-firing rules carry identical labels.** By the Observation above, every named rule in every EU and VN mini-regime carries `λ(Rᵢ) = Binding`. Hence for any context `ctx` and any subset `F ⊆ P_EU` (or `P_VN`) of firing rules, `{λ(Rᵢ) : Rᵢ ∈ F}` is either `∅` (β = ⊥) or `{Binding}` (β = Binding). For any aggregation function `agg: ℘(B) → B` satisfying the minimal axiom `agg({v}) = v` (idempotence on singletons — satisfied by `max`, `min`, `lex specialis`, unanimity, and every reasonable candidate), `agg({λ(Rᵢ) : Rᵢ ∈ F}) = Binding` whenever `F ≠ ∅` and `= ⊥` otherwise. The aggregation choice has no observable consequence.

**Hence every Finding in §6 that depends on `β` — #1, #2, #9, #10, #13, #14, #16 — is invariant under the aggregation choice, by construction, without re-running a single computation.** This is a *stronger* robustness result than a sensitivity analysis would produce: sensitivity establishes empirical invariance over a tested set of alternatives; Corollary H5.2 establishes algebraic invariance over the entire class. **This is a different axis from §7.4's encoding sensitivity, and the two must not be conflated: Findings #10 and #16 are invariant to the choice of aggregation function (this Corollary) — but their directional claim, "which regime is laxer," is *not* invariant to §7.4's risk-tier mapping choice (Encoding B1 reverses it; see §7.4's Robustness Summary and §8).** A Finding can be robust on one axis and non-robust on the other simultaneously; #10/#16 are exactly that case. It does **not** extend to `ω` (Definition H11), whose obligor sets `ο(Rᵢ) ⊆ O` are not identical across co-firing rules in general — §5.1's Group 1 contains co-firing rules with `ο = {Provider}` and `ο = {Regulator}` simultaneously, where union-aggregation and lex-specialis-aggregation produce distinct outputs. The ω-side aggregation question — whether lex specialis can replace union aggregation — is treated in a companion paper; see §7.6's methodology caveat for the invariance result that holds regardless of that choice.

---

## §6 Key Findings

Findings are grouped by theme below; numbering reflects the order each was originally surfaced during encoding, not importance or a forced reading order — Finding #2 (the headline reversal) and Finding #18 (the headline obligor result) are flagged ★ regardless of their position in the list below.

### 6.1 Core Empirical Results

1. **Post-market steady-state void (Group 1) — closed by Điều 10 Khoản 5:** EU mandates continuous risk management at every instant; the original VN encoding (Khoản 1/2 only) gated obligations on PreMarket or modification events — a concrete instance of Regulatory Void (Definition H3.5) at post-market steady-state. Text of Điều 10 Khoản 5 verified from statutory sources; new rules encoded; void closed at `ctx*` across all 4 sensitivity encodings. See Finding #14 for accompanying discoveries.

2. ★ **HEADLINE FINDING — Reverse gap recurs via two independent mechanisms (Groups 3 and 4):** VN's Điều 4 Khoản 2 (universal binding principle) is stricter than EU's Art. 14 (tier-gated, High/Unacceptable only) at `risk_tier=Minimal` (Group 3) — a tautology-driven reversal. The same direction of reversal recurs in Group 4 via a structurally distinct mechanism: Điều 10 Khoản 3 fires at `risk_tier∈{Medium,High}`, strictly broader than EU Art. 12's `{High,Unacceptable}` — at `risk_tier=Medium`, VN is Binding while EU is ⊥, contributing to G4's `VN>EU` count independently of any tautology (§5.4). The reversal is therefore a recurring structural feature of how Vietnamese law allocates obligations across risk tiers — confirmed by direct rule inspection via two distinct mechanisms — not an artifact of one tautological rule. Formal, computed result contradicting the standard assumption that the EU always leads on AI regulation. *This is the paper's central empirical claim (see Abstract, Introduction, §9) — numbered #2 here only because of the order in which the encoding work surfaced it, not because of its importance relative to the other 17 findings.* **Caveat — bindingness ≠ operational specificity (§5.3's note; cf. Finding #5b).** "Stricter" here is a claim about legal force (`β`, Definition H1), verified by code. It is not a claim about comparative real-world enforceability: Điều 4 Khoản 2 states outcomes without enumerating a mechanism, where Art. 14(4)/(5) additionally enumerate at least one concrete mechanism and a quantified verification rule. Whether a declaratory outcome-obligation or a mechanism-specified obligation has more practical bite is a separate, currently unmeasured question this paper does not resolve — only flags (Finding #5b, §8) and illustrates (§5.3).

3. **VN↔ASEAN divergence — most novel pairing:** D(VN→ASEAN) = 100% (including Điều 4 Khoản 2) / 93.8% (excluding Điều 4 Khoản 2). Vietnam's AI Law (effective 1 March 2026) and Nghị định 142 (effective 30 April 2026) make this pairing near-certain to be uncharted in prior literature.

4. **Convergence at transparency (Group 5):** EU and VN both at Binding — demonstrates methodological evenhandedness; the formal tool reports alignment, not only gaps.

9. **Quantitative harmonization shortfall (verified by code, post-A4):** D(EU→VN)=30.0%, D(VN→EU)=60.0%, D(EU→ASEAN)=70.0%, D(VN→ASEAN)=100%/93.8%, H(EU,VN)=10.00%. An H(EU,VN) of 10% means that across 6 tracked obligation-domains, the two regimes agree on bindingness in only 1/10 of the context space.

10. **Reverse gap magnitude exceeds forward gap — under the baseline encoding only:** D(VN→EU)=60.0% is exactly 2× D(EU→VN)=30.0% post-A4 (ratio ~1.75× pre-A4) under Encoding A. VN is more frequently *stricter* than EU than the reverse, across the 6 tracked domains — **at baseline**. The post-market void closure (Finding #14) reduced D(EU→VN) without changing D(VN→EU), sharpening this ratio at Encoding A specifically. **This ordering is not robust (§7.4): under Encoding B1 (Medium folded into EU's high-risk set), `D(EU→VN)=50.0%` exceeds `D(VN→EU)=40.0%` — the direction inverts.** B3 is an exact tie (40.0%=40.0%). Unlike Finding #2 (driven by a tautology, robust under all four encodings), this ratio's *direction*, not just its magnitude, depends on a contestable risk-tier mapping choice. The encoding-invariant claim is the weaker one: which regime is laxer is not predictable from country-level reputation, full stop — not "EU is laxer, twice as often."

16. **Read as arbitrage, the direction reverses the conventional fear at baseline — but the reversal itself is not the robust part (cf. Corollary H5.1, §2.3; caveat at Finding #10):** `D(EU→VN)=30.0%` and `D(VN→EU)=60.0%` (Finding #9/#10) are arbitrage-relevant in both directions, not only the popular-narrative direction. `D(EU→VN)=30%` means VN is the laxer destination in 30% of configurations at baseline (the "firms flee strict EU rules" story the literature usually tells). `D(VN→EU)=60%` means **EU is the laxer destination in 60% of configurations at baseline** — twice as often *at this one encoding*. For these six tracked obligation-domains, an arbitrage-seeking actor optimizing purely on bindingness would, under the baseline encoding, more often than not find the EU AI Act — not Vietnam's newer, less internationally scrutinized law — to be the lighter-touch jurisdiction. **As Finding #10 now states explicitly, this direction inverts under Encoding B1** (§7.4) — so the encoding-invariant lesson is not "EU is laxer," it is that country-level "X is the strict one" narratives are the wrong grain for arbitrage analysis full stop: the answer is configuration- *and* encoding-specific, which is exactly what a prose-only comparison cannot deliver and `Gap↓(A→B)` (Definition H5) can, provided the encoding sensitivity is reported alongside the point estimate rather than instead of it. This does not contradict Finding #2 (Vietnam strictly stricter at minimal risk specifically, which *is* tautology-driven and robust).

### 6.2 Structural and Architectural Results

7. **Risk taxonomy architecture (Pair #7) — incomparable, not merely out-of-scope:** Proposition H7.2 (EU/ASEAN, codomain mismatch) is a proven formal result, unaffected by any pending legal verification. Proposition H7.1 (EU/VN, catalog-structure mismatch) is argued on the latest public draft of VN's Danh mục — re-verified 20/6/2026, still unsigned/draft status — so it is reported as "argued, premise corrected," not "proven." Together they still transform a prior "limitation" into explicit, if asymmetrically certain, formal results: the formal tool correctly certifies its own boundary rather than silently failing.

8. **Partition cover mismatch (Definition H8; generalized in v11 via Theorem C, §2.8/§7.5/§A.4):** EU's Art. 14 fires on `risk_tier`; VN's Điều 4 Khoản 2 fires universally (orthogonal); VN's Điều 11 introduces `interacts_with_human` as a distinct axis absent from EU's tier-based architecture. A structural harmonization barrier **independent of bindingness levels** — not detectable by comparing β-values alone (Definition H4 is necessary but not sufficient). *v11 update:* Theorem C's exhaustive Refinement Matrix (§7.5, 12 directional cells across {EU, VN, ASEAN} × with/without tautologies) confirms this result generalizes beyond the three illustrative cells in v10: **no non-trivial cover refinement exists between any pair of regimes**, in either direction. The only nesting that does occur is the `art50`/`art11_kh1` mirror (identical-support convergence noted in §5.5), making partition-cover incompatibility a global property of this paper's encoded policies, not a local illustration (cf. Finding #17).

11. **Formal tool self-certifies its own boundaries:** Proposition H7.2 and Definition H8 convert prior informal limitations into formal results with explicit proofs/observations — shifting from "cannot do X" to "has proven X cannot/should not be done, with formal justification." Proposition H7.1 contributes the same shift at "argued" rather than "proven" strength, pending confirmation of VN's final Danh mục text.

17. **Theorem C generalizes H8: no non-trivial cover refinement exists between any pair of regimes (v11).** §7.5's Refinement Matrix computes all 12 directional refinement cells (6 directional pairs × 2 versions: with/without tautological rules) exhaustively. Result: all 4 of the 6 directional cells that show "with-tautology YES" are trivially driven by tautological universal principles (Điều 4 Khoản 2 on the VN side; `accountability_principle`, `human_centricity_principle`, and `transparency_principle` on the ASEAN side) — removing those tautologies flips all 4 to "NO"; the remaining 2 cells (`VN ⪯ EU`, `ASEAN ⪯ EU`) were already "NO" with tautologies present and are unaffected by removing them. The substantive structural claim: **no non-trivial cover refinement exists between any pair of regimes in this paper, in either direction.** v10's Observation H8.1 illustrated this for the EU↔VN pair on three cells; v11 confirms it generalizes — and, in the process, the exhaustive check surfaced a wording inconsistency in v10's §A.3 (which stated "EU not refined by VN" without distinguishing Definition H8's positive-block-only formulation from the broader split-into-S(R)-and-complement view). v11's §A.3 / §A.4 restate honestly. *This is direct empirical evidence for the paper's central methodological claim: brute-force-verifiable computation catches structural issues prose review misses across revisions* — itself an instance of Finding #11 (formal tool self-certifies its own boundaries).

### 6.3 Obligor Dimension

14. **Post-market void closed — but closing surfaces obligor mismatch and a residual void:** Brute-force code verification: adding `art10_kh5a`/`art10_kh5b` closes `ctx*` across all 4 sensitivity encodings; D(EU→VN) decreases 34.2%→30.0%; H(EU,VN) approximately doubles 5.83%→10.00% (still extremely low; narrative of extreme divergence unchanged). Two accompanying discoveries: (a) **Obligor mismatch** — Điều 10 Khoản 5 is a regulator-side obligation (state inspects entity); EU Art. 9 is a provider-side obligation (continuous self-monitoring) — `β: Ctx → B` cannot distinguish these, so the void closes numerically but "VN has an equivalent obligation" is an overclaim. Formalized in §2.9: `ctx* ∈ ObligorGap(EU,VN)` (Definition H13), the worked instance of Proposition H13.1. (b) **Residual void at Unacceptable tier** (240 contexts) — structurally analogous to Group 2's flag, driven by the same `Unacceptable→Cao` ASSUMED_PARAMETER mapping. See Finding #15 for the formal response to (a).

15. **Obligor formalized as a second output dimension (§2.9) — v10: one confirmed instance; v11: four confirmed instances across three structural types:** Definitions H9–H13 extend the framework's output from `β: Ctx → B` to `Φ = (β, ω): Ctx → B × ℘(O)`, with `ω` aggregating by union over a flat (unranked) obligor set — a different algebra from `β`'s max-aggregation over the ordered `B`, justified because no legal basis exists for ranking `Provider` against `Regulator` by strictness. Theorem A′ preserves Theorem A's linear decidability; Theorem B′ establishes `ObligorGap` enumerability by brute force over the explicit finite `Ctx` — weaker than Theorem B's symbolic enumerability, a limitation stated explicitly rather than left implicit (§2.9). Proposition H13.1 (`β`-equality does not imply `ω`-equality) was proven in v10 by Group 1's `ctx*` (Finding #14a) — one confirmed instance suffices for the existential claim. Group 2 was *not* adopted as a second instance, for two compounding reasons surfaced across two rounds of review: (a) VN's certification-reuse mechanism adding a Regulator-side obligor is unconfirmed by any cited statutory text; (b) external review caught that this paper's own first-pass `ω_EU` annotation for Group 2 (`{Provider, ThirdPartyCertifier}`, citing Art. 33) overclaimed notified-body involvement — Art. 43(2) confirms Annex III points 2–8 (the dominant case) use internal control with no notified body, and the same scrutiny applied to VN's Điều 13 Khoản 2(b) found its "other high-risk systems" branch is also self-assess-*or*-hire, not a guaranteed third party. Corrected: `ω_EU = ω_VN = {Provider}` for the dominant case — Group 2 remains a convergence point, at a different value than first encoded, with two narrow exception zones (EU's Annex III point 1; VN's Khoản 2(a) mandatory-certification Danh mục — the same still-draft instrument Proposition H7.1 already flags) left explicitly unresolved rather than guessed at. **v11 update: `ο`-encoding extended to Groups 1–6 on EU and VN sides (§5.3–§5.6, audit trail §B.2); three additional ObligorGap instances confirmed (Finding #18). Proposition H13.1 now rests on four instances spanning three structurally distinct mismatch types** (disjoint single-actor: G1/G6; proper-subset: G4; named-vs-unnamed: G3). ASEAN-side ο remains unencoded for G3–G6 because the Guide's principle-level statements rarely name a specific actor — itself a finding parallel to G3 VN's `ω = ∅`.

18. ★ **HEADLINE FINDING (v11) — Proposition H13.1 (Dimension Independence) now has 4 confirmed instances spanning three structurally distinct mismatch types.** Phase 2's extension of `ο`-encoding from Groups 1–2 to Groups 1–6 (EU and VN sides; ASEAN side flagged `ο = ?` per §5.0) yields three new ObligorGap instances:

    - **Instance 2 — Group 3 (1,152 contexts):** `ω_EU = {Provider, Deployer}` (Art. 14 + Art. 26) vs. `ω_VN = ∅` (Điều 4 Khoản 2, Chương I principle). *Type: named-set vs. unnamed-principle.*
    - **Instance 3 — Group 4 (144 contexts):** `ω_EU = {Provider, Deployer}` (Art. 12(1) Provider design + Art. 26(6) Deployer log retention) vs. `ω_VN = {Provider}` (Điều 10 Khoản 3 classification notification). *Type: proper-subset mismatch.*
    - **Instance 4 — Group 6 (576 contexts):** `ω_EU = {Provider}` (Art. 9 continuous self-monitor) vs. `ω_VN = {Deployer}` (NĐ142 event-triggered control). *Type: disjoint single-actor mismatch — closest structural analogue to Group 1's `ctx*` but on temporal axis.*

    Together with Group 1's Instance 1 (`{Provider}` vs `{Regulator}`), Proposition H13.1 now rests on **four** confirmed instances across **three** structurally distinct mismatch types: disjoint single-actor (G1, G6), proper-subset (G4), and named-vs-unnamed (G3). The v10 proposition required only ≥1 instance to hold; v11 strengthens it to "exists ≥1 instance of each of three distinct mismatch types." **Total ObligorGap incidence across §5 (distinct-context union): 1,152 contexts — 40.0% of |Ctx|, equal to G3 alone.** The four positive groups' gap-sets are *nested*, not disjoint: each group's EU obligation fires only at `risk_tier ∈ {High, Unacceptable}`, and G3's gap (VN side a tautology with `ω = ∅`) already covers that entire 1,152-context region, so `G1 ⊆ G3`, `G4 ⊆ G3`, `G6 ⊆ G3` (verified by brute-force enumeration). Consequently the per-group counts must **not** be summed. *(The naive per-group sum is 2,448 (85.0%) — not reported because it double-counts contexts appearing in multiple groups. The correct metric, per §7.3's methodological note, is the distinct-context union.)* G3 alone (40.0%) is the largest single-group ObligorGap contributor, exceeding Group 1's contribution by 100% and reframing the obligor dimension from "a flag we attached to one worked example" into "a structural feature co-extensive with the entire high-risk region." Methodology disclosure: Phase 2 obligor annotations are based on web-verified cross-referenced public sources as of 21/6/2026 (per-rule citations in §5.3–§5.6 comments), with no jurisdictional expert review — same caveat strength as Proposition H7.1.

---

### 6.4 Methodological

5. **Two unmodeled dimensions:** (a) Assessment interoperability (Group 2) — VN allows certification reuse; EU has no explicit equivalent mechanism; (b) Operational specificity (Group 3) — VN's principle-level vs EU's concrete design mandate, even at equal bindingness levels.

6. **Cross-anchor mismatch (Group 5):** VN Điều 11 aligns with EU Art. 50, not EU Art. 11 — the matching article cited in the preprint's Theorem 4 compliance table. The number overlap is purely numerical.

12. **Sensitivity analysis: four structural findings robust, but the comparison direction is not:** 4 encoding variants (2×2 design on 2 ASSUMED_PARAMETERS, §7.4) confirm that four structural/qualitative findings — post-market void closure, reverse gap at Minimal, VN↔ASEAN divergence, transparency convergence — hold under every mapping choice. The scalar values `D(EU→VN)` (range 20.0–50.0%) and `D(VN→EU)` (range 40.0–60.0%) vary across encodings — report as ranges, not point estimates. **But this is not the only non-robust element: under Encoding B1, `D(EU→VN)` exceeds `D(VN→EU)`, inverting which regime is laxer (§7.4's Robustness Summary; Findings #10/#16/§9).** That directional/qualitative claim is a separate failure of robustness from the scalar imprecision above, and should not be filed alongside the four genuinely encoding-invariant structural findings.

13. **EU Signal Homogeneity + Gap↓=Void↓ on EU↔VN axis:** (a) The EU side is effectively one repeated binary signal (`risk_tier∈{H,U}`) across 5/6 groups; disjointness of `Gap↓(EU→VN)` and `Gap↓(VN→EU)` follows as a theorem, not just an empirical observation. (b) By the Observation in §5.9 (`β_EU, β_VN ∈ {⊥, Binding}` throughout, derived from the §5.1–5.6 encoding plus well-formedness) — `Gap↓(EU→VN) = Void↓(EU→VN)` exactly. The Regulatory Void concept does discriminating work only in comparisons involving ASEAN, where `Recommended`/`Voluntary` actually appear. (c) The homogeneity check is symmetric, not EU-specific (§5.8): VN's 11 rules span 7/8 `Ctx` dimensions (diverse); ASEAN's 4 rules are either universal tautologies or sector-gated, never risk-tier-gated. Each regime's signal signature reflects its instrument genre — risk-tiered statute, multi-factor decree, principle-based voluntary guide — not an artifact of how the check was applied.

## §7 Quantitative Results

All values below are brute-force verified by Python script (enumerate all 2.880 contexts, compute β for all 3 regimes across 6 groups, compare with manual derivation). Script has no external dependencies beyond standard Python; runtime < 1 second.

*Scope of β values actually used in §5:* as established by the Observation in §5.9, `β_EU, β_VN ∈ {⊥, Binding}` exclusively — the intermediate levels `Voluntary` and `Recommended` never appear in EU↔VN comparisons. `β_ASEAN ∈ {⊥, Voluntary, Recommended}`, never `Binding`. This is a known constraint on the empirical coverage of the full 4-level lattice `B` in this paper.

### 7.1 Per-Group Gap Table (post-A4, verified by code)

| Group | Topic | EU>VN | VN>EU | EU>ASEAN | VN>ASEAN |
|---|---|---|---|---|---|
| G1 | Risk classification | **240 (8.3%)** | **1.248 (43.3%)** | 1.152 (40.0%) | **2.160 (75.0%)** |
| G2 | Conformity assessment | 576 (20.0%) | 0 (0%) | 1.152 (40.0%) | 576 (20.0%) |
| G3 | Human oversight | 0 (0%) | 1.728 (60.0%) | 1.152 (40.0%) | 2.880 (100%) |
| G4 | Incident reporting | 432 (15.0%) | 1.008 (35.0%) | 1.152 (40.0%) | 1.728 (60.0%) |
| G5 | Transparency | 0 (0%) | 0 (0%) | 1.440 (50.0%) | 1.440 (50.0%) |
| G6 | Risk-mgmt temporality | 576 (20.0%) | 864 (30.0%) | 1.152 (40.0%) | 1.440 (50.0%) |
| **Union (≥1 group)** | — | **864 (30.0%)** | **1.728 (60.0%)** | **2.016 (70.0%)** | **2.880 (100%) / 2.700 (93.8%) excl. Điều 4 Khoản 2** |

*(Union EU>VN/EU>ASEAN/VN>EU values hold because the portion of G1 newly closed by A4 was already covered by G3/G6 in the union — verified by code.)*

### 7.2 Summary D/H Table

| Metric | Count | D (post-A4) | D (pre-A4) |
|---|---|---|---|
| `|Ctx|` | — | **2.880** | 2.880 |
| Gap↓(EU→VN) | 864 | **30.0%** | 34.2% |
| Gap↓(VN→EU) — reverse gap | 1.728 | **60.0%** | 60.0% |
| Gap↓(EU→ASEAN) | 2.016 | **70.0%** | 70.0% |
| Gap↓(VN→ASEAN) incl. Điều 4 Khoản 2 | 2.880 | **100%** | 100% |
| Gap↓(VN→ASEAN) excl. Điều 4 Khoản 2 | 2.700 | **93.8%** | 92.5% |
| Gap(EU,VN) total (any divergence) | 2.592 | **90.0%** | 94.2% |
| **H(EU,VN)** | — | **10.00%** | 5.83% |

*Reading:* A4 closes a genuine portion of the void (post-market High-tier, §5.1's ctx*), so D(EU→VN) decreases and H(EU,VN) approximately doubles — but 10% remains extremely low; the "extreme divergence" narrative of Finding #9 is unchanged. D(VN→EU) and D(EU→ASEAN) are unchanged because the newly-closed G1 portion was already inside the G3/G6 union coverage.

Verify: 0 contexts belong simultaneously to Gap↓(EU→VN) and Gap↓(VN→EU) — the two directions are disjoint (EU→VN gap only at `risk_tier∈{High,Unacceptable}`; VN→EU gap only at `risk_tier∈{Minimal,Limited,Medium}`, since at High/Unacceptable EU always reaches Binding).

### 7.3 Methodological Note — Composite Metric

H(A,B)/D(A→B) as computed above is **not** a direct instance of Definition H4 on a single policy combining the full statute. Verified by code: if `β_VN(ctx)` is computed as max over all VN rules combined (merging all 6 groups into one policy), then because Điều 4 Khoản 2 (`dieu4kh2_human_control_principle`) is a tautology with label `Binding`, `β_VN(ctx) ≡ Binding` for all 2.880 contexts — degenerate, erasing all domain-specific gap findings (combined naive `EU>VN` = 0 contexts, meaningless).

This is not a code bug — it is the reason per-group scoping is the methodologically correct choice. Điều 4 Khoản 2 is a general principle on a different subject (human control in general) from the 6 specific obligations under comparison. Mixing a general tautological principle into a max with specific obligations produces a meaningless number.

**Recommended presentation in the paper (two clearly labeled layers):**

1. **Per-domain D values** (§7.1, per Group) — rigorous instances of Definition H3/H4; each Group is a valid regime per Definition H2 (P scoped to one obligation-domain).
2. **Composite Cross-Domain Incidence** (§7.2, Union) — explicitly labeled as "fraction of contexts showing divergence in at least one of N tracked domains," not "harmonization score of the full statute."

### 7.4 Sensitivity Analysis

**Design:** 2×2 on two ASSUMED_PARAMETERS from §3.2:

- **Axis Medium:** EU's high-risk firing set = `{High, Unacceptable}` (Encoding A, conservative) or `{Medium, High, Unacceptable}` (Encoding B1, liberal). Affects EU's rules in G1, G2, G3, G4, G6 (G5 uses `interacts_with_human`, unaffected).
- **Axis Unacceptable:** VN rules with literal `risk_tier == High` (G1's `art10_kh5a`, G2's rules, G4's `art10_kh3`) extended to include `Unacceptable` or not. Encoding A = no extension (literal). Encoding B2 = extension (Cao-tier inclusive, consistent with §3.2's `Unacceptable→Cao` mapping).

4 combinations: **A** (baseline, used throughout §5–7), **B1** (Medium axis only), **B2** (Unacceptable axis only), **B3** (both liberal).

**Results (post-A4, verified by code):**

| Encoding | D(EU→VN) | D(VN→EU) | H(EU,VN) | ctx* ∈ Void↓? | ctx' ∈ Gap↑? | G2 gap@Unacceptable | G1 gap@Unacceptable |
|---|---|---|---|---|---|---|---|
| **A** | **30.0%** | 60.0% | **10.00%** | **False (closed)** | **True** | 576 | 240 |
| **B1** | **50.0%** | 40.0% | **10.00%** | **False (closed)** | **True** | 576 | 240 |
| **B2** | **20.0%** | 60.0% | **20.00%** | **False (closed)** | **True** | 0 | 0 |
| **B3** | **40.0%** | 40.0% | **20.00%** | **False (closed)** | **True** | 0 | 0 |

**Robustness summary:**

| Finding | Robust? |
|---|---|
| Post-market void closure (ctx*, G1) | ✅ Robust — closed in all 4 encodings |
| Reverse gap at Minimal (ctx', G3) | ✅ Robust — Điều 4 Khoản 2 is a tautology, untouched by both axes |
| VN↔ASEAN divergence near-total | ✅ Robust — driven entirely by Điều 4 Khoản 2 tautology |
| Transparency convergence (G5) | ✅ Robust — driven by `interacts_with_human`, unrelated to risk_tier |
| H(EU,VN) qualitatively low (≤20%) | ✅ Robust — always "extreme divergence" regardless of encoding |
| D(EU→VN) precise value | ❌ Not robust — ranges 20.0–50.0% (±15pp) |
| D(VN→EU) precise value | ❌ Not robust — ranges 40.0–60.0% |
| **Directional ordering (which regime is laxer)** | **❌ Not robust — A/B2 show VN-stricter (EU laxer, 2–3×); B1 reverses it (EU-stricter, 50.0% vs 40.0%); B3 is an exact tie. Findings #10/#16/§9 must be read as baseline-encoding-specific, not encoding-invariant.** |
| Group 2 gap@Unacceptable (576 ctx) | Encoding-dependent — closes under B2/B3 |
| Group 1 gap@Unacceptable (240 ctx) | Encoding-dependent — same family as Group 2 |

*Recommended Results/Discussion wording:* "Encoding Điều 10 Khoản 5 closes the post-market steady-state void identified for High-risk systems under Vietnamese law, robust across all four encoding variants. Verifying the statutory text surfaces a new, unmodeled obligor distinction (state-inspection vs. provider-self-monitoring) and leaves a structurally analogous gap at the Unacceptable tier, mirroring the Group 2 finding. Sensitivity analysis confirms that the remaining structural findings — the reverse gap at Minimal tier, the VN↔ASEAN divergence, and the transparency convergence — hold regardless of mapping choice; only the precise scalar percentages vary (D(EU→VN) ranges 20.0–50.0%, D(VN→EU) ranges 40.0–60.0%, H(EU,VN) ranges 10.0–20.0% across encodings), reported here as a transparency measure rather than treating any single encoding's output as ground truth. One ordering is not robust at all: under Encoding B1 specifically, D(EU→VN) (50.0%) exceeds D(VN→EU) (40.0%) — the reverse of the baseline's direction — so 'EU is more often the laxer regime' (Findings #10/#16) should be read as a baseline-encoding finding, not an encoding-invariant one."

### 7.5 Refinement Matrix (Theorem C, exhaustive)

All six directional refinement checks across {EU, VN, ASEAN}, both with and without tautological rules, computed exhaustively by `theorem_c_matrix.py` (~234 subset-checks, runtime < 0.1s). Each cell reports the verdict and, where the refinement fails, the count of non-nesting blocks (full block list in §A.4).

| Direction | With tautologies | Without tautologies |
|---|---|---|
| Π(EU) ⪯ Π(VN) | **YES — trivial** (via Điều 4 Khoản 2 = Ctx) | **NO** — 5 EU blocks fail |
| Π(VN) ⪯ Π(EU) | **NO** — 7 VN blocks fail (incl. tautology itself) | **NO** — 6 VN blocks fail |
| Π(EU) ⪯ Π(ASEAN) | **YES — trivial** (via 3 ASEAN principles = Ctx) | **NO** — 6 EU blocks fail |
| Π(ASEAN) ⪯ Π(EU) | **NO** — 4 ASEAN blocks fail (incl. 3 tautologies) | **NO** — 1 ASEAN block fails (`genai_disclosure_labelling`) |
| Π(VN) ⪯ Π(ASEAN) | **YES — trivial** | **NO** — 10 VN blocks fail |
| Π(ASEAN) ⪯ Π(VN) | **YES — trivial** (via VN's tautology) | **NO** — 1 ASEAN block fails (`genai_disclosure_labelling`) |

**Reading the matrix.**

- *Every "YES" is tautology-driven.* Removing tautological rules (Điều 4 Khoản 2 on VN side; `accountability_principle`, `human_centricity_principle`, and `transparency_principle` on ASEAN side) turns every "YES" into "NO". Four of six cells flip; the other two — `VN ⪯ EU` and `ASEAN ⪯ EU` — were already "NO" with tautologies present and stay "NO".
- *No non-trivial refinement exists between any pair, in any direction.* This is the substantive Theorem C result: the structural incompatibility documented for EU/VN in v10's Observation H8.1 generalizes — once tautological universal principles are set aside — to *every* regime pair examined in this paper.
- *Asymmetric failure modes are informative.* ASEAN → EU fails on only one block (`genai_disclosure_labelling`, sector-gated and orthogonal to EU's risk-tier and `interacts_with_human` axes); whereas VN → ASEAN fails on ten. The asymmetry reflects each instrument's structural diversity: ASEAN's four rules carve a small piece of `Ctx`, easy to fit inside (or fail to fit inside) other covers; VN's eleven rules across seven dimensions almost never fit cleanly under any cover not built on the same axes.
- *The single non-trivial nesting that does occur is the `art50` / `art11_kh1` mirror.* In the Π(EU) ⪯ Π(VN) [no_taut] check, the lone EU block that does refine into Π(VN)' is `art50_disclosure` — because VN's `art11_kh1_ai_disclosure` has identical support (`interacts_with_human = true`). This nesting was already noted in §5.5 as the "convergence point" finding; the Refinement Matrix confirms it is the **only** non-trivial structural alignment across all 12 cells.

This is the result Theorem C (§2.8) certifies as decidable; the proof and exhaustive block-by-block failure analysis are in §A.4.

### 7.6 ObligorGap Incidence Across §5 (v11, after Phase 2 ο-encoding completion)

Phase 2 of v11 extended `ο`-encoding from Groups 1–2 to Groups 1–6 on the EU and VN sides (§B.2 audit trail). Computing `ObligorGap(EU, VN)` per Definition H13 across the six obligation-domains yields:

| Group | Topic | ω_EU (dominant case) | ω_VN (dominant case) | ObligorGap (ctx) | % of \|Ctx\| | Mismatch type |
|---|---|---|---|---|---|---|
| G1 | Risk classification (post-A4) | `{Provider}` (Art. 9) | `{Regulator}` (Điều 10 Khoản 5) | 576 | 20.0% | Disjoint single-actor |
| G2 | Conformity assessment | `{Provider}` (Art. 43(2)) | `{Provider}` (Điều 13 Khoản 2(b)) | **0** | 0.0% | **Convergence** |
| G3 | Human oversight | `{Provider, Deployer}` (Art. 14 + Art. 26) | `∅` (Điều 4 Khoản 2 Chương I) | **1,152** | **40.0%** | Named-set vs. unnamed-principle |
| G4 | Incident reporting | `{Provider, Deployer}` (Art. 12(1) + Art. 26(6)) | `{Provider}` (Điều 10 Khoản 3) | 144 | 5.0% | Proper-subset |
| G5 | Transparency | `{Provider}` (Art. 50) | `{Provider}` (Điều 11 Khoản 1) | **0** | 0.0% | **Convergence** |
| G6 | Risk-mgmt temporality | `{Provider}` (Art. 9) | `{Deployer}` (NĐ142 event-trigger) | 576 | 20.0% | Disjoint single-actor |
| **Union (any group, distinct ctx)** | — | — | — | **1,152** | **40.0%** | = G3 alone (G1/G4/G6 ⊆ G3) |

*Why the union is 1,152, not the per-group sum.* The four positive groups' gap-sets are nested, not disjoint (`G1 ⊆ G3`, `G4 ⊆ G3`, `G6 ⊆ G3`) — see Finding #18 for the full arithmetic.

**Three structural observations from this table.**

1. *Obligor-gap union and bindingness gap each range 40.0%–60.0% and are anti-correlated; neither dominates robustly.* Computed on the **same** per-group-then-union metric across the four §7.4 encodings (`verify_beta_vs_omega.py`):

   | Encoding | `D(VN→EU)` bindingness | ObligorGap union | More frequent |
   |---|---|---|---|
   | A (canonical) | 60.0% | 40.0% | bindingness |
   | B1 | 40.0% | 60.0% | obligor |
   | B2 | 60.0% | 40.0% | bindingness |
   | B3 | 40.0% | 60.0% | obligor |

   The two are **perfectly anti-correlated**: the encodings that move `Medium` into the EU high-risk set (B1, B3) shrink the bindingness gap to 40.0% while enlarging the obligor union to 60.0%, and vice-versa. So **which of `β` or `ω` is the more frequent harmonization failure is encoding-dependent, reported as ranges (both 40.0%–60.0%) rather than a fixed ranking** — exactly as §7.4/Finding #12 reports `D` itself. What *is* invariant under all four encodings: obligor mismatch is present in 4/6 domains (four instances, three mismatch types). The per-group-union figures above are reproduced by `verify_hsdl_harmonization.py`; `verify_bindingness_baseline.py` retains a documented non-standard aggregation as a methodological foil.

2. *Four of six groups are ObligorGap-positive; two are convergence points.* G2 and G5 are convergence points on both `β` and `ω` (a fact §5.2 and §5.5 already report). The other four groups all exhibit ObligorGap, spanning three structurally distinct mismatch types (Finding #18): disjoint single-actor (G1, G6), proper-subset (G4), named-vs-unnamed (G3).

3. *G3 alone (40.0%) is the largest single-group contributor.* G3's 1,152 contexts come from `risk_tier ∈ {High, Unacceptable}` (where EU's Art. 14 fires) with `ω_VN = ∅` for all 1,152 (Điều 4 Khoản 2 fires universally but names no actor). This *quantifies* the "principle-vs-mechanism" gap that v10 flagged informally as "operational specificity" (Finding #5b): the gap shows up as a 40%-of-Ctx ObligorGap along the obligor axis, even though, at High/Unacceptable tiers, `β` reports both regimes as equally Binding.

*Methodology caveat.* As §8 discloses, ω-aggregation choice is consequential — these counts use `ω_union` (Definition H11). An alternative, specificity-based aggregation (lex specialis: the more-specific co-firing rule wins, rather than the union of all co-firing rules' obligors) is examined formally in a companion paper, including conditions under which it is well-defined at all. The G4 case is instructive here: where G4's two VN rules co-fire (`risk_tier=High ∧ lifecycle_stage=PreMarket ∧ serious_harm_discovered=true`), union aggregation rebuilds `{Provider, Deployer} = ω_EU` (no gap), whereas a lex-specialis aggregation that selects only the more-specific rule keeps only `{Provider} ≠ ω_EU`, creating a *fresh* gap. So aggregation choice can move per-group counts in either direction — a per-group count under an alternative aggregation is not bounded above by `ω_union`. What *is* invariant under every aggregation choice examined is the **distinct-context union total (1,152 = 40.0%)**: every per-group ObligorGap lies within `risk_tier ∈ {High, Unacceptable}`, which G3's tautology-driven gap (`ω = ∅` everywhere) already covers in full — so `G1/G4/G6 ⊆ G3` and the union equals G3's 1,152 regardless of aggregation.

### 7.7 Code and Data Availability

All verification scripts referenced in this paper — `verify_proposals.py`, `theorem_c_matrix.py`, `phase2_obligor.py`, `verify_union.py`, `verify_hsdl_harmonization.py`, `verify_beta_vs_omega.py`, `verify_bindingness_baseline.py`, `verify_h8.py`, and `phase3_omega.py` — are pure Python with no external dependencies and are intended for release alongside this paper under an Apache 2.0 license. *(Open item: a public repository URL for this script set is not yet finalized at time of writing; the canonical location will be either a standalone repository or a subfolder of the HSDL reference implementation below, confirmed before submission.)* The HSDL reference implementation is available at https://github.com/Eilodon/HolySeed (Apache 2.0). Legal text sources are cited in-line and in the References; no proprietary data was used in this paper.

---

## §8 Limitations & Dual-Use Considerations

**Limitations:**

- **Shared-schema assumption.** `Ctx` requires EU/VN/ASEAN to be encoded on the same vocabulary. The 5-value `risk_tier` merge (EU 4-tier + VN 3-tier) is not bijective; two mapping choices (`Medium→Limited` or `→High`, `Unacceptable→Cao` or `Bị Cấm`) are ASSUMED_PARAMETERS, not derived. Sensitivity analysis (§7.4) confirms 5 of the 6 tracked structural/qualitative findings — post-market void closure, reverse gap at Minimal, VN↔ASEAN divergence, transparency convergence, and H(EU,VN)'s qualitatively-low reading — are robust under all four encodings. **The sixth is not:** directional ordering — *which* regime is laxer, `D(EU→VN)` vs. `D(VN→EU)` — inverts under Encoding B1 (§7.4's Robustness Summary; Findings #10/#16/§9). This is not reducible to "only scalar D-values are encoding-dependent": a scalar moving within a range is a precision issue, but a comparison flipping which side is larger is a *directional/qualitative* failure of robustness, and should be reported as such rather than folded into the scalar caveat.
- **Legal encoding is human interpretation.** Translating statutory text into conjunctive rules is not decidable or automatable. The theorems prove properties of the formal *model*; they do not certify the model's fidelity to the underlying statute.
- **`max`-aggregation is a modeling choice.** Definition H3 implements *lex strictior* — the strictest applicable obligation governs. This differs from *lex specialis* (specificity-based priority, which may yield a *less* strict outcome).
- **ω-aggregation choice:** unlike β-aggregation (which is algebraically invariant under all reasonable choices by Corollary H5.2, §5.9), ω-aggregation choice can move per-group ObligorGap counts in either direction. The union aggregation (Definition H11) is adopted as canonical because it is the only well-defined choice in cases where no specificity ordering exists between co-firing rules — a structural constraint examined formally in a companion technical note.
- **Two unmodeled dimensions — one formalized since, one still open.** (a) *Assessment interoperability* (Group 2): VN's Nghị định 142 Điều 13 includes a certification reuse mechanism (mutual recognition) that neither `β` (Definition H1) nor `ω` (Definition H11, §2.9) represents — a compliance-cost/evidentiary-burden axis distinct from both. (b) *Operational specificity* (Group 3): EU Art. 14(4)/(5) state outcomes and additionally enumerate at least one concrete mechanism (a stop-button-or-equivalent procedure) and a quantified verification rule for certain biometric systems; VN's Điều 4 Khoản 2 states comparable outcomes without enumerating a mechanism for any of them — see §5.3's illustrative (not formal) comparison, added after external review noted this gap was flagged but never measured. Both groups show identical bindingness (`Binding`) but differ along these unmodeled axes. A third axis, *obligor*, was in this category in earlier drafts but is no longer informal: it is now Definitions H9–H13 (§2.9), a fully formalized second output dimension `ω: Ctx → ℘(O)`. Proposed extension for the two axes that remain informal: a 2D output `(bindingness, specificity)` descriptive metadata layer, to be addressed in a follow-on extension — §5.3's manual proxy is a first step, not that extension.
- **Obligor dimension: formally defined, empirically expanded but not exhaustive (§2.9; updated v11).** `ω: Ctx → ℘(O)` (Definition H11) and `ObligorGap` (Definition H13) are fully defined; Theorems A′/B′ establish decidability and (brute-force, not symbolic — see §2.9's honesty remark) enumerability for `Φ = (β, ω)`. **v11 Phase 2 expanded `ο`-labeling from Groups 1–2 to Groups 1–6 on the EU and VN sides**, surfacing three new ObligorGap instances (G3/G4/G6) whose context-sets are nested inside G3's, for a distinct-context union of 1,152 (40.0% of |Ctx|, equal to G3 alone; Finding #18). Per-rule citations in §5.3–§5.6 cite the operative provisions (Art. 14 + Art. 26 for G3 EU; Điều 4 Khoản 2 for G3 VN; Art. 12(1) Provider + Art. 26(6) Deployer for G4 EU — *not* Art. 19, which imposes the parallel retention duty on the Provider; Điều 10 Khoản 3 and NĐ142 Điều 19 for G4 VN; Art. 50 / Điều 11 Khoản 1 for G5; Art. 9 / NĐ142 event-control for G6). **Methodology disclosure (analogous to Prop. H7.1's status):** all Phase 2 legal research was conducted by web search and cross-referencing of public sources as of 21/6/2026, with no jurisdictional expert review — the same epistemic-strength caveat as Prop. H7.1's "argued, not proven" status. The labeling is *internally consistent* (Phase 2's results were re-run after each group's encoding to catch contradictions, per the protocol in v11's handoff plan) and *cross-referenced* against multiple sources (LuatVietAn, LuatVietnam, AplawJapan, AI Act Service Desk, official ai-act-service-desk.ec.europa.eu, Wiki Legal, baomoi.com, vnexpress.net) — but should be treated by reviewers as "argued and exhaustively cross-checked" rather than "audited by sworn experts." Two open items carry over from v10: EU's Annex III point 1 (biometric ID, G2) and VN's Khoản 2(a) mandatory-certification Danh mục (G2, the same still-draft instrument Prop. H7.1 flags) remain unresolved. **Two new open items from Phase 2:** (a) G4's `decree142_art12_kh5_incident_report` rule label retains its v10 citation despite the operative provision being NĐ142 Điều 19 (the final Nghị định's article numbering differs from the earlier draft the rule was originally named against; the bindingness label and `serious_harm_discovered` predicate are unchanged); (b) the ASEAN side of G3–G6 carries `ο = ?` (unencoded), since the ASEAN Guide's principle-level statements rarely name a specific actor at the precision level Definition H10 requires — itself a finding parallel to G3 VN's `ω = ∅`. *Why Groups 1–2 alone in v10:* see §B.1 for the historical reason (Group 2's two-round correction made the methodology cost vivid). Phase 2 in v11 applied the same per-rule primary-source-check protocol to the remaining four groups; §B.2 documents the audit trail.

  The nested structure of the four positive ObligorGap groups means their distinct-context union (1,152 = G3 alone) cannot be derived by summing per-group counts — see Finding #18 for the full arithmetic. **Reported as a range, per §7.4: the obligor-gap union and the bindingness gap `D(VN→EU)` each span 40.0%–60.0% across the four sensitivity encodings and are anti-correlated** (obligor 40.0% / bindingness 60.0% at encodings A, B2; obligor 60.0% / bindingness 40.0% at B1, B3). Which dimension is the more frequent failure is therefore encoding-dependent and not asserted as a fixed ranking (see §7.6 obs. 1; `verify_beta_vs_omega.py`). Obligor mismatch is a structurally significant *additional* dimension regardless, present in 4/6 domains under every encoding.
- **Lexical vs. systemic obligor scope (G3).** Definition H10 encodes obligors by lexical parsing — if a specific article names no actor, the tool returns `ω = ∅`, reflecting the absence of an explicit designation in that text, not a claim that no systemic reading is available. An alternative systemic reading from Điều 2 (Luật 134/2025's scope article, establishing universal applicability across all AI participants) would yield `ω = O` for Điều 4 Khoản 2 instead of `ω = ∅`. `ObligorGap(EU, VN)` holds under both readings — `∅ ≠ {Provider, Deployer}` (lexical) and `O ≠ {Provider, Deployer}` (systemic) — though the mismatch *type* differs: named-set-vs-unnamed under the lexical reading becomes proper-subset under the systemic reading, since `{Provider, Deployer} ⊂ O`. The finding is robust to this choice; Finding #18's mismatch-type label for G3 is interpretation-dependent.
- **Composite cross-domain incidence is not a direct instance of H4.** Naive single-policy combination degenerates due to Điều 4 Khoản 2's tautology (verified by code). The two-layer presentation (per-domain D values + composite incidence) must be clearly labeled in the paper to prevent misreading.
- **EU Signal Homogeneity limits independence of the "6 obligation-domains" framing.** §5.8 shows 5 of 6 EU rules in §5 reduce to the literally identical condition `risk_tier∈{High,Unacceptable}`; only G5 (`interacts_with_human`) is distinct. This means the comparison contains effectively two independent EU data points, not six — the structural diversity driving the findings is entirely on the VN/ASEAN side. This does not invalidate the per-group D values (each remains a valid Definition H3/H4 instance against a genuinely different VN/ASEAN rule), but it should be stated explicitly rather than left for a reviewer to discover: "7 obligation pairs" should not be read as "7 independent tests of EU's position."
- **Draft Danh mục (Proposition H7.1) — verification completed, downgraded.** The VN High-risk catalog relied upon is the Bộ KHCN draft (Công văn 1101/BKHCN-CNS&CĐS, March 2026). Re-verified 20/6/2026 against all available public sources, including Nghị định 142/2026/NĐ-CP (effective 30/4/2026), which references the catalog generically without citing a signed Quyết định: no confirmation that the Prime Minister has signed the official Quyết định under Điều 13 Khoản 4 was found. **Proposition H7.1 is reported in this paper as "argued, premise corrected — full proof pending confirmation of final Danh mục text," not as "proven."** Re-check immediately before submission in case the Quyết định is signed in the intervening period.
- **Single-researcher verification.** All cross-referencing of statutory text, threshold sourcing, and code verification was performed by one researcher across multiple self-review passes; no external independent reviewer has audited the analysis.

**Dual-Use Considerations:**

A tool that precisely enumerates every context where two regimes differ in bindingness is simultaneously an **advocacy tool** (identifying harmonization needs) and a **regulatory arbitrage tool** (finding jurisdictions where obligations are weaker for a given system configuration). These are technically identical artifacts. Intended use cases and use restrictions should be stated explicitly, not merely listed nominally.

---

## §9 Implications: What Should Change

The four failure modes (Table 1) are not equally actionable. Two are fixable by text amendment alone — Regulatory Void, Bindingness Gap. Two are not — Partition/Cover Incompatibility (§2.8), Obligor Mismatch (§2.9) — they require an architectural or allocational decision, not a threshold edit. What follows is organized by audience and tied explicitly to which failure mode motivates each recommendation, not offered as generic AI-governance advice.

### For ASEAN — transitioning from voluntary Guide toward binding governance

- **Resolve the organizing axis before drafting binding text, not after.** Observation H8.1 shows the EU's risk-tier-only architecture and Vietnam's multi-axis architecture (tier + human-interaction + lifecycle) cannot be reconciled by amending thresholds — they cut up the regulatory space along genuinely different axes, and no text alignment fixes that after the fact. ASEAN's current Guide avoids this choice entirely by being principle-based (§5.8: ASEAN's rules are tautologies or sector-gated, never risk-tier-gated) — but the moment ASEAN moves toward binding rules, it will face exactly this architectural choice. Observation H8.1's refinement check is directly reusable as a pre-drafting design test: before finalizing a binding structure, check whether the candidate cover refines (or is refined by) the structures already binding on ASEAN's largest member economies.
- **Allocate obligor explicitly wherever mutual recognition is intended.** Finding #14a shows two regimes can reach textually "equivalent" bindingness while assigning the duty to different actors (state inspector vs. provider-self-monitor). If ASEAN intends equivalence or mutual-recognition mechanisms with EU- or VN-aligned members, obligor allocation needs its own clause — equal bindingness language does not imply equal obligor — and Definition H13 (`ObligorGap`) gives a checkable test for whether a candidate equivalence claim actually holds, rather than one that looks like it holds because both sides say "Binding."
- **Even ASEAN's own harm-type taxonomy is not severity-reducible (Prop. H7.2).** Any future binding ASEAN instrument that wants to interoperate with EU-style severity tiers will face the same codomain mismatch documented here for the EU pairing — worth resolving by design rather than discovering after adoption.

### For Vietnam

- **The Minimal-risk reversal (★ Finding #2) is a policy choice worth stating explicitly, not an artifact to quietly converge away.** Vietnam's Điều 4 Khoản 2 binds universally where the EU AI Act is silent at the lowest risk tier — this is *more* protective, not a drafting gap. Vietnam can (a) defend this as intentional human-centricity policy distinguishing its approach from the EU's tier-gated model, or (b) if regulatory convergence with the EU is a stated goal, recognize that convergence would require *loosening* Điều 4 Khoản 2's universal bindingness, not tightening VN's other High-risk provisions — a tradeoff the current "VN catching up to EU" framing in public discourse does not surface.
- **Điều 10 Khoản 5's relationship to continuous provider self-monitoring needs one clarifying sentence.** Finding #14a shows VN's regulator-inspection mechanism and the EU's provider-self-monitoring mandate are not the same obligation in different words — they are different obligors entirely, and Vietnam's law does not currently impose a provider-side continuous-monitoring duty at the same post-market steady-state (§5.1). The Khoản 5 supervision requirement should state explicitly whether it *substitutes for* or *supplements* such a duty. This paper's tool surfaces the ambiguity; only a drafting choice resolves it.
- **The mandatory-certification Danh mục (Điều 13 Khoản 4) determines more than Proposition H7.1's classification-comparability — it also determines Group 2's obligor allocation (§5.2, §2.9).** Whichever systems the final Danh mục names will be the systems where `ThirdPartyCertifier` involvement is mandatory rather than optional; this is a second, independent reason to finalize and publish that catalog promptly, beyond the classification-scheme uncertainty already noted.

### For deployers operating across EU/VN/ASEAN

- **"Compliant under regime A" does not transfer to regime B even at equal nominal bindingness.** Group 6's encoding (§5.6) shows that even where both regimes require "Binding" risk-management obligations, *who* performs them can differ structurally: EU mandates continuous provider-side self-monitoring (Art. 9); VN mandates deployer-side event-triggered control (NĐ142). Treat a compliance file built for one jurisdiction as evidence to be re-checked against the obligor dimension specifically when porting to another, not just re-checked against the bindingness level.
- **The HSDL encoding itself — not only this paper's seven reported pairs — is the reusable artifact.** §5's policy encodings are runnable: a deployer with a specific system's `Ctx` values (risk tier, sector, lifecycle stage, etc.) can evaluate `Φ_A(ctx)` and `Φ_B(ctx)` directly (Theorem A′) for their own configuration, rather than waiting for a future paper to cover their specific case. This is a lower-cost, immediately actionable use of the contribution beyond the findings reported here.
- **Reading `Gap↓` as arbitrage (Corollary H5.1) cuts both ways for a deployer, not just a regulator — and the precise ratio is less robust than the underlying advice.** Finding #16's reversal — under the baseline encoding, EU is the laxer jurisdiction in 60% of tracked configurations, not VN — means a deployer who chose VN expecting it to be uniformly the lighter-touch option (or a regulator who assumed the opposite) would often be wrong, for these six obligation-domains. The "twice as often" ratio itself is not robust: §7.4 shows the direction inverts under Encoding B1 (EU becomes the *stricter* regime, 50.0% vs 40.0%). This sharpens rather than undercuts the practical point: a deployer cannot reliably predict which regime is laxer from country reputation, *nor from a single confident point estimate* — the configuration-specific, encoding-range-aware computation is the product; neither the country-level intuition nor an unhedged percentage is a reliable substitute for it.

### Future Work: Multi-Actor, Cross-Border Incident Chains

One natural extension this paper does not attempt: when an AI system's provider, deployer, and affected user sit in three different jurisdictions and a single incident triggers overlapping notification/liability obligations, the relevant question is no longer "which regime governs this system" but "which regime governs *this actor, at this stage, in this jurisdiction*" — a different `Ctx` shape (actor- and jurisdiction-indexed, not single-system) built on top of the Obligor dimension (H9–H13) rather than a direct application of it. Definition H13's `ObligorGap` answers "who's responsible, under one regime" — it does not yet answer "whose notification duty fires first, across regimes, in a single cross-border incident." Scoping that correctly — concrete incident typologies, an explicit notification-chain model, likely a genuinely new Ctx schema rather than an extension of this paper's — is a separate, larger undertaking than the corrections and extensions in this paper's changelog, not a same-session addition.

---

## Appendix A: Full Proofs

The four items below are stated with a short intuition in §2 (per the reading guide in §2.0); this appendix carries the full argument for a reader checking it line by line. Nothing here is new content — it is relocated verbatim from earlier drafts of §2, to keep §2 itself readable for a governance-track audience without a formal-methods background.

### A.1 Proof of Proposition H7.1 (EU/VN Incomparability)

*Proof sketch.*

- *No `h: Dom_EU → Dom_VN`.* Annex III lists named use-cases (e.g., credit-scoring, biometric ID) as High independently of deployment context. VN's Danh mục (Công văn 1101/BKHCN-CNS&CĐS, 4 groups/13 sub-groups) conditions some entries on factors Annex III does not use — e.g., medical-decision-support systems are High-risk only when "the system directly issues decisions/actions without independent human approval." Take `a, a'` both Annex-III-listed (`τ_EU(a)=τ_EU(a')=High`), differing only in whether a human-approval step exists — VN's conditional entry assigns different tiers to `a, a'`. A single `h` cannot output two different values for the same input. Contradiction.
- *No `h': Dom_VN → Dom_EU`.* VN's Danh mục organizes one group by **harm scale/reversibility** (Nhóm IV — "large-scale impact or difficult to reverse") rather than by use-case — an axis Annex III does not use as an independent enumeration criterion. Two systems both in Nhóm IV (same VN input) can differ entirely by use-case, hence may receive different `τ_EU` values depending on use-case. Concrete instance (constructed to illustrate the argument — not itself a claim about an official VN classification ruling):

  ```
  System X: large-scale-harm AI, waste-management use-case
            → Nhóm IV ⟹ τ_VN(X) = Cao
            → waste management is not an Annex III use-case ⟹ τ_EU(X) = Minimal/Limited
  System Y: large-scale-harm AI, biometric-ID use-case
            → Nhóm IV ⟹ τ_VN(Y) = Cao
            → biometric ID IS an Annex III use-case ⟹ τ_EU(Y) = High
  ```

  `τ_VN(X) = τ_VN(Y) = Cao`, but `τ_EU(X) ≠ τ_EU(Y)`. A single `h'(Cao)` cannot output two different values for one input. Contradiction — symmetric to the `h` bullet above.

Hence incomparable by catalog-structure mismatch (conditional qualifiers + non-use-case organizing axis on the VN side). □

### A.2 Proof of Proposition H7.2 (EU/ASEAN Incomparability)

*Proof sketch.* `Dom_EU = {Minimal, Limited, High, Unacceptable}` (4 levels, an ordered severity scale). `Dom_ASEAN = {Societal, Economic, Environmental, Security, Human Rights, Ethical}` (6 categories, an unordered harm-type partition — orthogonal to severity by the Gen AI Guide's own design: a given harm-type can in principle arise at any severity level, and a single system can raise more than one harm-type concern regardless of its EU tier).

*No `h: Dom_EU → Dom_ASEAN⁺` satisfies `τ_ASEAN = h∘τ_EU`.* Restrict attention to `a` with `sector(a)=GenAI`, where `τ_ASEAN(a) ∈ Dom_ASEAN` (a genuine category, never `N/A`, by the totality fix above). `h(High)` would have to equal `τ_ASEAN(a)` simultaneously for *every* such `a` with `τ_EU(a)=High` — but because harm-type is orthogonal to severity, `τ_ASEAN` is not constant on this level-set in general, so a single fixed `h(High)` cannot equal all required outputs without information loss. By the non-triviality clause (Definition H7′), the sentinel constant map `h ≡ N/A` is excluded on the same grounds: it fails the equation for every GenAI-sector `a`, where the required output is a genuine category, not `N/A`. Hence no `h` — sentinel or otherwise — satisfies the equation.

*No `h': Dom_ASEAN → Dom_EU` satisfies `τ_EU = h'∘τ_ASEAN`*, symmetrically: a single harm-type category (e.g. `Societal`) is not confined to one severity level, so `h'(Societal)` cannot equal `τ_EU(a)` for every `a` the category covers.

Mismatch is at typing level (an ordered severity scale vs. an unordered harm-type partition) and survives totalization — extending the codomain with `N/A` fixes *totality of the function type*, not satisfaction of the factorization *equation*, which is the actual compatibility criterion (Definition H7′). □

### A.3 Proof of Observation H8.1 (Partition Cover Incompatibility — restated v11)

*Two-layer proof, exhaustive (computed by `verify_h8.py`; see also §A.4's Refinement Matrix).*

**Layer 1 — Definition H8 as written (positive blocks only).**

- *EU refined by VN — TRIVIALLY TRUE.* Điều 4 Khoản 2's `S(dieu4kh2_human_control_principle) = Ctx`. For every `S_A ∈ Π(EU)`, `S_A ⊆ Ctx = S(dieu4kh2_…)`. The existential in Definition H8 is satisfied by the tautology block alone. This is the **trivial refinement**: any cover whose target contains a tautology is trivially refined, regardless of structural compatibility. Earlier paper versions stated this direction as "not refined" — incorrect under Definition H8's positive-block-only formulation; corrected here.
- *VN not refined by EU — TRUE.* For every EU block `S_B ∈ Π(EU)`, no VN block has the structural shape needed to be contained in it. Concrete witness: VN's `art10_kh1_self_classify` fires on `system_role=Provider ∧ lifecycle_stage=PreMarket` (480 contexts spanning every `risk_tier`). Every EU block in §5 is either driven by `risk_tier ∈ {High, Unacceptable}` (5 of 6 EU rules, by §5.8's homogeneity) or by `interacts_with_human` (Art. 50 alone). `art10_kh1`'s 480 contexts include `risk_tier ∈ {Minimal, Limited, Medium}` configurations (288 contexts), which lie outside every `risk_tier ∈ {H, U}` EU block; and they include `interacts_with_human = false` configurations (240 contexts), which lie outside Art. 50's block. Hence `S(art10_kh1) \ S_B ≠ ∅` for every `S_B ∈ Π(EU)`, and the existential in Definition H8 fails for this VN block. Exhaustively: code confirms six VN blocks (`art10_kh1`, `art10_kh2`, `art10_kh5b`, `art10_kh3`, `decree142_art12_kh5`, `decree142_event_triggered_control`) each fail the existential. □

**Layer 2 — After excluding tautological rules (the substantive structural claim).**

Let `Π(VN)' = Π(VN) \ {S(dieu4kh2_human_control_principle)}`. Layer 1's left direction now reverses:

- *EU not refined by VN' — TRUE.* Exhaustive check (code): five of six EU blocks (`art9_risk_mgmt_continuous`, `art11_conformity_assessment`, `art14_human_oversight`, `art12_recordkeeping_uniform`, `art9_risk_mgmt_temporality` — i.e. the five `risk_tier ∈ {H,U}` blocks by §5.8) fail to nest in any VN' block. Concrete witness: `art14_human_oversight` fires on 1,152 contexts (`risk_tier ∈ {High, Unacceptable}`, all other dimensions free). No single VN' block contains all 1,152 — `art10_kh5a` covers only `risk_tier = High` (576 ctx), missing all 576 Unacceptable contexts; `art10_kh5b` covers `risk_tier = Medium` (disjoint); the other VN' blocks gate on lifecycle/role/event conditions that further restrict their support. Hence no `S_B ∈ Π(VN)'` satisfies `S(art14) ⊆ S_B`. The remaining EU block (`art50_disclosure`, on `interacts_with_human = true`) does nest — `art11_kh1_ai_disclosure` is its mirror image with identical support — so EU's `art50` is the lone EU block that does refine into VN'.
- *VN' not refined by EU — TRUE.* Same six VN blocks as Layer 1 still fail.

Hence the covers are **structurally** incompatible: neither refines the other once tautological rules are excluded, and the only nesting under Definition H8 as written is the uninformative tautology-induced one. This is a harmonization barrier independent of bindingness levels and independent of which side carries a universal principle. □

*Methodological note.* The two-layer presentation is itself a methodological contribution: it separates (a) what Definition H8 mechanically reports from (b) what the reader should treat as substantive structural information. Earlier paper versions conflated these by implicitly using a broader partition definition (rule splits Ctx into S(R) AND its complement, two equivalence classes per rule) that Definition H8 does not formally adopt. The exhaustive Refinement Matrix in §A.4 / §7.5 makes the distinction precise across all 6 directional regime pairs.

### A.4 Proof of Theorem C (Partition Refinement Decidability)

*Statement (recap from §2.8).* For any two policies `P_A, P_B` over shared `Ctx` (with each `S(Rᵢ)` a polytope × finite-set region per Lemma 1), deciding whether `Π(P_A)` refines `Π(P_B)` is decidable in time `O(|P_A| · |P_B| · k)`, and the complete set of non-nesting `P_A`-blocks is enumerable in the same bound.

*Proof.* Refinement (Definition H8) requires: for every `S_A ∈ Π(P_A)`, exists `S_B ∈ Π(P_B)` with `S_A ⊆ S_B`. Algorithm:

```
for each S_A in Π(P_A):                      // |P_A| iterations
  found_container := false
  for each S_B in Π(P_B):                    // |P_B| iterations
    if subset_check(S_A, S_B):               // O(k) per Lemma 1
       found_container := true; break
  if not found_container:
     record S_A as a non-nesting block

return (no non-nesting blocks recorded, list of non-nesting blocks)
```

By Lemma 1, each `S` factors as `S_num × S_cat` (numeric/ordinal × categorical), and `S_A ⊆ S_B` reduces to per-dimension containment: interval containment on numeric/ordinal dimensions (`O(1)` per dimension), set containment on categorical dimensions (`O(|Σ|)` linear scan, or `O(1)` with hash indexing; bounded by `k` total dimensions in either case). Subset-check is thus `O(k)`. The double loop yields `O(|P_A| · |P_B| · k)`. The non-nesting list is built in the same pass — no additional asymptotic cost. □

*Exhaustive computation for this paper's three §5 policies.* The Refinement Matrix in §7.5 records all 12 cells (6 directional × 2 versions). The block-by-block failure analysis below was generated by `theorem_c_matrix.py`:

**Cell-by-cell non-nesting blocks (no-tautology version, the substantive layer):**

```
Π(EU) ⪯ Π(VN)' — 5 of 6 EU blocks fail (the 5 risk-tier-driven blocks):
  art9_risk_mgmt_continuous     (|S|=1152)
  art11_conformity_assessment   (|S|=1152)
  art14_human_oversight         (|S|=1152)
  art12_recordkeeping_uniform   (|S|=1152)
  art9_risk_mgmt_temporality    (|S|=1152)
  [art50_disclosure DOES nest — into art11_kh1_ai_disclosure, identical support]

Π(VN)' ⪯ Π(EU) — 6 of 10 VN blocks fail:
  art10_kh1_self_classify                (|S|=480)
  art10_kh2_reclassify_on_modification   (|S|=1440)
  art10_kh5b_supervision_medium          (|S|=576)
  art10_kh3_notify_classification        (|S|=576)
  decree142_art12_kh5_incident_report    (|S|=1440)
  decree142_event_triggered_control      (|S|=1440)
  [art10_kh5a, art13_*, art11_kh1 DO nest — into art9/art11/art14/art50 EU blocks]

Π(EU) ⪯ Π(ASEAN)' — 6 of 6 EU blocks fail (ASEAN' = only genai_disclosure):
  all six EU blocks fail (none has support ⊆ {sector=GenAI})

Π(ASEAN)' ⪯ Π(EU) — 1 of 1 ASEAN' block fails:
  genai_disclosure_labelling (|S|=480) — sector-gated, orthogonal to EU axes

Π(VN)' ⪯ Π(ASEAN)' — 10 of 10 VN' blocks fail:
  all VN' blocks fail (none has support ⊆ {sector=GenAI})

Π(ASEAN)' ⪯ Π(VN)' — 1 of 1 ASEAN' block fails:
  genai_disclosure_labelling (|S|=480)
```

*Interpretation.* The pattern is consistent across all six directions: outside the lone `art50`/`art11_kh1` mirror nesting, every block driven by `risk_tier`, `lifecycle_stage`, `system_role`, `modification_increases_risk`, `serious_harm_discovered`, or `sector` fails to nest into any cover built on a different axis combination. This is structural-axis incompatibility, not encoding noise. Removing tautologies (the with-taut → no-taut transition in §7.5) reveals it cleanly; with tautologies present, the half-trivial picture in v10's Observation H8.1 obscures it.

*Note on Definition H8's positive-block-only formulation.* Under Definition H8 as written (positive blocks only), one direction (EU ⪯ VN) succeeds trivially due to Điều 4 Khoản 2's tautology. Once tautological rules are removed, both directions fail — making the two-layer presentation in §2.8 essential for correct reading of the result. The Theorem C exhaustive check makes this distinction computable rather than prose-dependent. □

## Appendix B: Methodological Audit Trails

The two items below document the legal-research process behind specific obligor (`ο`) annotations in §5 — not formal proofs, but a record of how those annotations were checked and, in one case, corrected after external review. Relocated here from Appendix A to keep that appendix to proof content only.

### B.1 Group 2 Obligor-Encoding Correction — Full Discussion

An earlier draft of §2.9 proposed Group 2's certification-reuse rule (`art13_certification_reuse`, §5.2) as a second Dimension Independence instance, on the premise that VN's reuse mechanism adds `Regulator` as an obligor absent from EU's scheme. That premise is **not** established by any statutory text cited elsewhere in this paper, and a search for the specific procedural detail did not turn up a confirming source as of 21/6/2026; it is not adopted (§5.2 flags it as an open item instead).

A second, independent problem with this paper's first attempt at Group 2's `ο`-encoding was caught by external review and confirmed by checking Art. 43(2) directly: EU's `art11_conformity_assessment` had been annotated `obligor: {Provider, ThirdPartyCertifier}` unconditionally, citing Art. 33 — but Art. 33 defines *qualification criteria for an organization to act as* a notified body, not a mandate that one is involved in every assessment, and Art. 43(2) states explicitly that Annex III points 2–8 (the dominant case) use internal control "which does not provide for the involvement of a notified body." The same scrutiny applied to VN's side (Điều 13 Khoản 2): the "other high-risk systems" branch (Khoản 2(b), the dominant case outside the mandatory-certification Danh mục) lets the provider self-assess *or* hire an assessor — `ThirdPartyCertifier` is the provider's option, not a guaranteed co-obligor, so the original `{Provider, ThirdPartyCertifier}` annotation on the VN side was an unconditional overclaim by the same standard, just not yet caught.

Both corrections are reflected in §5.2's current encoding (`ω_EU = ω_VN = {Provider}` for the dominant case) and in Finding #15/§8.

### B.2 Phase 2 Obligor-Encoding Audit Trail (v11)

This appendix documents the per-rule legal-research record supporting the obligor annotations added in v11 §5.3–§5.6. Each entry names the operative statutory provision, the assigned `ο ⊆ O`, the primary sources consulted, the date of access (21/6/2026), and any open items.

**G3 — Human Oversight.**

- *EU side: `art14_human_oversight`, `ο = {Provider, Deployer}`.* Operative provisions: Art. 14(1) (design duty on Provider — "High-risk AI systems shall be designed and developed in such a way... that they can be effectively overseen by natural persons"); Art. 14(3)(a) (Provider builds oversight measures); Art. 14(3)(b) (Provider identifies measures appropriate for Deployer to implement); Art. 14(4) (Provider provides the system to Deployer enabling oversight); Art. 26(1)–(2) (Deployer assigns oversight to natural persons with necessary competence, training, authority). Primary sources: artificialintelligenceact.eu/article/14, /article/26; ai-act-service-desk.ec.europa.eu/en/ai-act/article-14; intelligence.dlapiper.com/artificial-intelligence/?t=11-human-oversight (DLA Piper cross-check). No open items — both actors named directly in the operative text.
- *VN side: `dieu4kh2_human_control_principle`, `ο = ∅`.* Operative provision: Điều 4 Khoản 2 Luật Trí tuệ nhân tạo (Luật 134/2025/QH15), Chương I "Những quy định chung," "Nguyên tắc cơ bản trong hoạt động trí tuệ nhân tạo." Text reads "Trí tuệ nhân tạo phục vụ con người, không thay thế thẩm quyền và trách nhiệm của con người. Bảo đảm duy trì sự kiểm soát và khả năng can thiệp của con người đối với mọi quyết định và hành vi của hệ thống trí tuệ nhân tạo..." — no named duty-bearer. Primary sources: luatvietan.vn/luat-tri-tue-nhan-tao.html (full Điều 4 text); thuvienphapluat.vn/phap-luat-nha-dat/toan-van-luat-tri-tue-nhan-tao-2025-luat-so-1342025qh15... (official text). No open items; `∅` is the formal `INDETERMINATE` per Definition H10, not a research gap. Cf. v11 Finding #18's "Type: named-set vs. unnamed-principle."

**G4 — Incident Reporting.**

- *EU side: `art12_recordkeeping_uniform`, `ο = {Provider, Deployer}`.* Operative provisions: Art. 12(1) (Provider designs system for automatic event recording over lifecycle); Art. 26(6) (Deployer keeps logs for at least 6 months). **Correction (audit):** earlier drafts cited the *deployer's* retention duty to Art. 19; verbatim text shows Art. 19 opens "Providers of high-risk AI systems shall keep the logs..." (a **Provider** retention duty parallel to Art. 12), while the deployer's six-month retention duty is Art. 26(6) ("Deployers... shall keep the logs automatically generated by that high-risk AI system... of at least six months"). The `{Provider, Deployer}` obligor set is unchanged — Provider via Art. 12(1)/Art. 19, Deployer via Art. 26(6). Primary sources: artificialintelligenceact.eu/article/12, /article/26, /article/19; ransomleak.com/compliance/eu-ai-act/ (training-focused cross-check noting "log retention for at least six months" as a deployer duty). No open items.
- *VN side rule 1: `art10_kh3_notify_classification`, `ο = {Provider}`.* Operative provision: Luật 134/2025/QH15 Điều 10 Khoản 3 — Provider must notify classification result to AI single-window portal (Cổng thông tin điện tử một cửa, established by NĐ142 Điều 6). Regulator is recipient, not co-obligor (Definition H10 disambiguation). Primary sources: wikilegal.vn/quy-dinh-ve-phan-loai...; aplawjapan.com/en/newsletter/20260528-2 (legal newsletter citing the operative procedure). No open items.
- *VN side rule 2: `decree142_art12_kh5_incident_report`, `ο = {Provider, Deployer}`.* **Provision-number note:** the rule's name retains its v10 citation `art12_kh5` for continuity, but the operative provision in the final NĐ142 is **Điều 19** ("Báo cáo và xử lý sự cố nghiêm trọng"), not Khoản 5 Điều 12. The two refer to the same incident-reporting mechanism via the Luật's Điều 12 Khoản 5 (the parent provision delegating implementation to NĐ142). Operative text: Provider is primary reporter ("nhà cung cấp ... thực hiện báo cáo sơ bộ"); Deployer is fallback reporter ("nếu không liên lạc được với nhà cung cấp, bên triển khai có trách nhiệm thực hiện việc báo cáo"); both must "duy trì, lưu giữ nhật ký hệ thống, dữ liệu và thông tin liên quan đến sự cố." Union aggregation (Definition H11) collapses primary + fallback duty-bearers to `{Provider, Deployer}` at any qualifying context, matching the legal intent. Primary sources: luatvietnam.vn/bieu-mau/mau-bao-cao-su-co-nghiem-trong-cua-he-thong-tri-tue-nhan-tao... (full Điều 19 text and sample form AI01a); aplawjapan.com newsletter 20260528 (legal cross-check). **Open item:** rule name should be reconciled with the final NĐ142 in a future revision; this paper retains the v10 name to avoid renaming in mid-revision.

**G5 — Transparency.**

- *EU side: `art50_disclosure`, `ο = {Provider}`.* Operative provision: Art. 50(1) — "Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system." Provider is the named duty-bearer; Art. 50(2)–(4) add Deployer-side duties for emotion recognition / deepfakes (a Ctx-unencodable sub-case). Primary sources: artificialintelligenceact.eu/article/50. **Open item:** Art. 50(2)–(4) sub-case is structurally similar to G2's Annex III point 1 exception zone — flagged but not separately encoded.
- *VN side: `art11_kh1_ai_disclosure`, `ο = {Provider}`.* Operative provision: Luật 134/2025/QH15 Điều 11 Khoản 1 — Provider designs system with disclosure built in. Primary sources: gvlawyers.com.vn/luat-tri-tue-nhan-tao-viet-nam-2026/ (legal commentary on Điều 11). G5 is a convergence point on both `β` and `ω` (`{Provider} = {Provider}`).

**G6 — Risk-Management Temporality.**

- *EU side: `art9_risk_mgmt_temporality`, `ο = {Provider}`.* Same provision as G1's `art9_risk_mgmt_continuous` (separated only to isolate the temporal dimension); annotation inherited unchanged.
- *VN side: `decree142_event_triggered_control`, `ο = {Deployer}`.* Operative provision: NĐ142, control-measure article. Statutory text reads "Trường hợp phát hiện hệ thống AI có nguy cơ gây ảnh hưởng nghiêm trọng đến tính mạng, sức khỏe, tài sản, an ninh mạng hoặc lợi ích công cộng, **tổ chức triển khai phải áp dụng ngay biện pháp kiểm soát, hạn chế rủi ro** và thực hiện thông báo theo quy định." "Tổ chức triển khai" maps to `Deployer` per the H9 coverage note. Primary sources: caa.gov.vn/pho-bien-phap-luat/hoan-thien-co-so-phap-ly... (Vietnam Civil Aviation Authority's official summary, paraphrasing the Nghị định); baomoi.com/hoan-thien-hanh-lang-phap-ly...; cross-checked against the vietnamplus.vn coverage already in the References. No open items.

**Methodology summary.** Each annotation followed the protocol from the v11 handoff plan: (1) locate the operative obligor-allocating provision (not just the bindingness-establishing one); (2) confirm whether the obligation is unconditional or branches; (3) check both EU and VN sides independently; (4) re-run `phase2_obligor.py` after each group's annotation to catch contradictions. All annotations are based on web-verified public sources as of 21/6/2026; no jurisdictional expert review. This matches Proposition H7.1's epistemic strength ("argued, premise corrected") rather than the stronger "proven" status that would require sworn-expert audit.

**Reproducibility.** The verification scripts used across v11 are available alongside the paper: the four original Phase 1–2 scripts (`verify_proposals.py`, `verify_h8.py`, `theorem_c_matrix.py`, `phase2_obligor.py`), the Phase 3 ω-aggregation script (`phase3_omega.py`), and the audit-cycle additions (`verify_union.py` — distinct-context union; `verify_hsdl_harmonization.py` — independent D/H re-implementation across all 4 sensitivity encodings; `verify_beta_vs_omega.py` — β-gap vs ω-gap on one metric), plus one documented foil retained for the aggregation lesson (`verify_bindingness_baseline.py`). (`verify_g4_lex.py`, used for the G4 lex-specialis counts, is released alongside the companion paper on lex-specialis aggregation rather than with this paper, since that comparison no longer appears here — see §7.6's methodology caveat.) All scripts are pure Python with no external dependencies; combined runtime < 2 seconds. See §7.7 for the availability statement.


---

## References

### Primary Legal Sources

**EU AI Act**

- The Future of Life Institute — *AI Act Explorer*, Article 9 (Risk Management System) — https://artificialintelligenceact.eu/article/9/
- The Future of Life Institute — *AI Act Explorer*, Article 12 (Record-Keeping) — https://artificialintelligenceact.eu/article/12/
- The Future of Life Institute — *AI Act Explorer*, Article 14 (Human Oversight) — https://artificialintelligenceact.eu/article/14/
- The Future of Life Institute — *AI Act Explorer*, Article 19 (Automatically Generated Logs) — https://artificialintelligenceact.eu/article/19/
- The Future of Life Institute — *AI Act Explorer*, Article 26 (Obligations of Deployers) — https://artificialintelligenceact.eu/article/26/
- The Future of Life Institute — *AI Act Explorer*, Article 50 (Transparency for Certain AI Systems) — https://artificialintelligenceact.eu/article/50/
- European Commission — *AI Act Service Desk*, Article 9 — https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-9
- European Commission — *AI Act Service Desk*, Article 14 — https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-14
- DLA Piper — *AI Laws of the World*, "Human oversight in the European Union" — https://intelligence.dlapiper.com/artificial-intelligence/?t=11-human-oversight&c=EU
- A&O Shearman — "Zooming in on AI 10: EU AI Act — Obligations for High-Risk AI Systems" — https://www.aoshearman.com/en/insights/ao-shearman-on-tech/zooming-in-on-ai-10-eu-ai-act-what-are-the-obligations-for-high-risk-ai-systems

**Luật 134/2025/QH15 (Luật Trí tuệ nhân tạo Việt Nam) and Nghị định 142/2026/NĐ-CP**

- VnExpress — "Bốn điểm mới trong Luật Trí tuệ nhân tạo của Việt Nam" — https://vnexpress.net/bon-diem-moi-trong-luat-tri-tue-nhan-tao-cua-viet-nam-5046036.html
- VnExpress — "Phân loại AI rủi ro cao: Phép thử đầu tiên của Luật Trí tuệ nhân tạo" — https://vnexpress.net/phan-loai-ai-rui-ro-cao-phep-thu-dau-tien-cua-luat-tri-tue-nhan-tao-5045115.html
- Duane Morris LLP — "Vietnam – The First Law on Artificial Intelligence" — https://blogs.duanemorris.com/vietnam/2026/03/03/vietnam-the-first-law-on-artificial-intelligence-what-you-must-know/
- VietnamPlus — "Nguyên tắc phân loại và đánh giá sự phù hợp hệ thống trí tuệ nhân tạo" — https://www.vietnamplus.vn/thiet-lap-cong-du-lieu-quoc-gia-ve-ai-tang-giam-sat-he-thong-tri-tue-nhan-tao-post1109165.vnp
- VietnamPlus — "Quy định chi tiết thi hành Luật Trí tuệ nhân tạo mới nhất 2026" — https://www.vietnamplus.vn/quy-dinh-chi-tiet-mot-so-dieu-va-bien-phap-thi-hanh-luat-tri-tue-nhan-tao-post1109436.vnp
- Cục Hàng không Việt Nam — "Hoàn thiện cơ sở pháp lý về quản lý và ứng dụng trí tuệ nhân tạo" — https://caa.gov.vn/pho-bien-phap-luat/hoan-thien-co-so-phap-ly-ve-quan-ly-va-ung-dung-tri-tue-nhan-tao-20260511151935960.htm
- Thư Viện Pháp Luật — "Đã có Nghị định 142/2026/NĐ-CP hướng dẫn Luật Trí tuệ nhân tạo" — https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/111715/da-co-nghi-dinh-142-2026-nd-cp-huong-dan-luat-tri-tue-nhan-tao
- Thư Viện Pháp Luật — "Phân loại hệ thống trí tuệ nhân tạo từ 1/5/2026 (Nghị định 142/2026)" — https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/111767/phan-loai-he-thong-tri-tue-nhan-tao-tu-1-5-2026-nghi-dinh-142-2026
- Wiki Legal — "Quy định về phân loại và đánh giá sự phù hợp hệ thống trí tuệ nhân tạo" — https://wikilegal.vn/quy-dinh-ve-phan-loai-va-danh-gia-su-phu-hop-he-thong-tri-tue-nhan-tao/
- Luật Việt An — "Ra đời Luật Trí tuệ nhân tạo 2025 số 134/2025/QH15" — https://luatvietan.vn/luat-tri-tue-nhan-tao.html
- Thư Viện Pháp Luật — "Toàn văn Luật Trí tuệ nhân tạo 2025" — https://thuvienphapluat.vn/phap-luat-nha-dat/toan-van-luat-tri-tue-nhan-tao-2025-luat-so-1342025qh15--luat-tri-tue-nhan-tao-ai-dau-tien-cua-viet-13396.html
- LuatVietnam — "Mẫu Báo cáo sự cố nghiêm trọng của hệ thống trí tuệ nhân tạo mới nhất" (sample form AI01a citing NĐ142 Điều 19, the operative incident-reporting provision; provision-number reconciliation note in §B.2) — https://luatvietnam.vn/bieu-mau/mau-bao-cao-su-co-nghiem-trong-cua-he-thong-tri-tue-nhan-tao-moi-nhat-571-108879-article.html
- Atsumi & Sakai Tokyo — *Vietnam Legal Update*, "Các điểm mới quan trọng của nghị định hướng dẫn Luật Trí tuệ nhân tạo" (legal newsletter, 28/5/2026; cross-check for Điều 10 Khoản 3 notification mechanism and Điều 19 incident-reporting 72-hour deadline) — https://www.aplawjapan.com/en/newsletter/20260528-2
- GV Lawyers — "Luật trí tuệ nhân tạo Việt Nam 2026: Hướng dẫn chi tiết" (commentary cross-check on Điều 11 Khoản 1 disclosure duty) — https://gvlawyers.com.vn/luat-tri-tue-nhan-tao-viet-nam-2026/
- VnEconomy — "Phân loại rủi ro hệ thống trí tuệ nhân tạo theo Nghị định 142" — https://vneconomy.vn/phan-loai-3-muc-do-rui-ro-cua-he-thong-ai.htm
- Bao Moi (aggregating Báo Kiểm Toán) — "Hoàn thiện hành lang pháp lý cho trí tuệ nhân tạo: Phân loại rủi ro để kiểm soát hệ thống AI" (cross-check for NĐ142 event-triggered control mechanism, naming "tổ chức triển khai" as duty-bearer) — https://baomoi.com/hoan-thien-hanh-lang-phap-ly-cho-tri-tue-nhan-tao-phan-loai-rui-ro-de-kiem-soat-he-thong-ai-c55110580.epi
- Media Chính phủ — "Ban hành Nghị định quy định chi tiết một số điều và biện pháp thi hành Luật Trí tuệ nhân tạo" (official government summary, 30/4/2026) — https://media.chinhphu.vn/ban-hanh-nghi-dinh-quy-dinh-chi-tiet-mot-so-dieu-va-bien-phap-thi-hanh-luat-tri-tue-nhan-tao-102260508162952667.htm
- Thư Viện Pháp Luật — "Từ 1/3/2026, hệ thống trí tuệ nhân tạo có rủi ro thấp được quy định ra sao?" (commentary on Điều 10 Khoản 5 a/b/c bindingness levels) — https://thuvienphapluat.vn/hoi-dap-phap-luat/tu-132026-he-thong-tri-tue-nhan-tao-co-rui-ro-thap-duoc-quy-dinh-ra-sao-138082357.html
- Thư Viện Pháp Luật (van-ban portal) — "Nghị định 142/2026/NĐ-CP hướng dẫn Luật Trí tuệ nhân tạo mới nhất" (full official text reference) — https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Nghi-dinh-142-2026-ND-CP-huong-dan-Luat-Tri-tue-nhan-tao-696080.aspx

*Date of access for all Vietnam-side primary sources used in the v11 obligor-encoding extension: 21/6/2026.* Annotation methodology and epistemic-strength disclaimer in §B.2.

**ASEAN AI Governance Guide (2024) and Expanded ASEAN Guide on AI Governance and Ethics — Generative AI (2025)**

- ASEAN Secretariat — "ASEAN Guide on AI Governance and Ethics" (PDF, 2024) — https://asean.org/wp-content/uploads/2024/02/ASEAN-Guide-on-AI-Governance-and-Ethics_beautified_201223_v2.pdf
- ASEAN Secretariat — "Expanded ASEAN Guide on AI Governance and Ethics — Generative AI" (PDF, 2025) — https://asean.org/wp-content/uploads/2025/01/Expanded-ASEAN-Guide-on-AI-Governance-and-Ethics-Generative-AI.pdf
- Rajah & Tann Asia — "Expanded ASEAN Guide on AI Governance and Ethics" — https://www.rajahtannasia.com/viewpoints/expanded-asean-guide-on-ai-governance-and-ethics/
- Global Compliance News (Baker McKenzie) — "Singapore: Launch of Expanded ASEAN Guide on AI Governance and Ethics — Generative AI" — https://www.globalcompliancenews.com/2025/02/15/
- Modern Diplomacy — "From Soft Law to Hard Rules: Pushing for Binding AI Governance in ASEAN" — https://moderndiplomacy.eu/2026/01/20/from-soft-law-to-hard-rules-pushing-for-binding-ai-governance-in-asean/
- NBR — "Charting ASEAN's Path to AI Governance: Uneven Yet Gaining Ground" — https://www.nbr.org/publication/charting-aseans-path-to-ai-governance-uneven-yet-gaining-ground/
- ISEAS Perspective 2026/13 — Kristina Fong, "What is Shaping Artificial Intelligence (AI) Governance Policies in Southeast Asia?" — https://www.iseas.edu.sg/articles-commentaries/iseas-perspective/2025-13-what-is-shaping-artificial-intelligence-ai-governance-policies-in-southeast-asia-by-kristina-fong/
- International AI Safety Report 2026 (arXiv:2602.21012)
- International AI Safety Report 2025: Second Key Update (arXiv:2511.19863)

### Academic Literature

**HSDL preprint (this paper's base apparatus)**

- "HSDL: A Formally Analyzable Policy Language for Dynamic AI Agent Authorization" — arXiv preprint v0.1, HolySeed reference implementation (Apache 2.0, https://github.com/Eilodon/HolySeed)

**EU AI Act formalization and computational compliance (§1.1)**

- Guldimann, P., Spiridonov, A., Staab, R., et al. — "COMPL-AI Framework: A Technical Interpretation and LLM Benchmarking Suite for the EU Artificial Intelligence Act" — arXiv:2410.07959 (2024)
- Hernandez, J., Golpayegani, D., & Lewis, D. — "An open knowledge graph-based approach for mapping concepts and requirements between the EU AI Act and international standards" — *AI and Ethics*, 5, 4463–4474 (2025) — https://doi.org/10.1007/s43681-025-00708-6
- Marino, B., Chaudhary, Y., Pi, Y., et al. — "Compliance Cards: Automated EU AI Act Compliance Analyses amidst a Complex AI Supply Chain" — arXiv:2406.14758 (2024)

**Cross-jurisdiction AI governance comparison (§1.2)**

- Chun, J., Schroeder de Witt, C., & Elkins, K. — "Comparative Global AI Regulation: Policy Perspectives from the EU, China, and the US" — arXiv:2410.21279 (2024)
- Al-Maamari, A. — "Between Innovation and Oversight: A Cross-Regional Study of AI Risk Management Frameworks in the EU, U.S., UK, and China" — arXiv:2503.05773 (2025)
- Batool, A., Zowghi, D., & Bano, M. — "AI governance: a systematic literature review" — *AI and Ethics* (2025)
- Lu, Y., & Tie, F. H. — "A comparative analysis of artificial intelligence regulation in ASEAN and the European Union" — *Journal of Governance and Regulation*, 14(4, special issue), 401–411 (2025) — https://doi.org/10.22495/jgrv14i4siart16

**Legal informatics and policy language foundations (§1.3)**

- Palmirani, M., Governatori, G., Rotolo, A., Tabet, S., Boley, H., & Paschke, A. — "LegalRuleML: XML-Based Rules and Norms" — *Rule-Based Modeling and Computing on the Semantic Web* (RuleML 2011), LNCS 7018, Springer
- Athan, T., Governatori, G., Palmirani, M., Paschke, A., & Wyner, A. — "LegalRuleML: Design Principles and Foundations" — *Reasoning Web. Web Logic Rules*, 11th International Summer School 2015, Tutorial Lectures, Springer
- Governatori, G., & Rotolo, A. — "Changing legal systems: legal abrogations and annulments in Defeasible Logic" — *Logic Journal of the IGPL*, 18(1), 157–194 (2010)

**AI governance arbitrage literature**

- Marwala, Tshilidzi — "The AI Governance Arbitrage" — United Nations University, March 2026 — https://unu.edu/article/ai-governance-arbitrage
- ProMarket — "The Politics of Fragmentation and Capture in AI Regulation" — July 2025 — https://www.promarket.org/2025/07/07/the-politics-of-fragmentation-and-capture-in-ai-regulation/
- "AI regulation: Competition, arbitrage and regulatory capture" — December 2025 — https://www.researchgate.net/publication/393956309_AI_regulation_Competition_arbitrage_and_regulatory_capture
- "Navigating the AI regulatory landscape: Balancing innovation, ethics, and global governance" (citing Aloisi & De Stefano 2023 on firms shifting to looser-requirement jurisdictions) — Taylor & Francis — https://www.tandfonline.com/doi/full/10.1080/20954816.2025.2569584
- Bloomsbury Intelligence and Security Institute — "Global Fragmentation of AI Governance and Regulation" — February 2026 — https://bisi.org.uk/reports/global-fragmentation-of-ai-governance

### Software and Reproducibility

- HSDL reference implementation — https://github.com/Eilodon/HolySeed (Apache 2.0)
- Verification scripts for this paper's quantitative results (§7.1–§7.6) and proofs (Appendix A) — release details and license in §7.7's Code and Data Availability statement
- Audit-trail scripts for the obligor (`ο`) annotation process (Appendix B) — same release, documented per-script in §B.2's Reproducibility note
