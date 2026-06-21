"""
RETRACTED METHOD — kept as a documented foil. See verify_beta_vs_omega.py for the
correct comparison.

An earlier AXIOM pass used this file to claim "D(VN->EU) is encoding-dependent:
60% vs 30%, so the obligor-vs-bindingness comparison is unresolved." That 30% was
a METHODOLOGICAL ERROR: it computed a GLOBAL regime-beta (max over ALL of a regime's
rules at once), which lets EU's Art.50 transparency rule lift the global beta_EU to
Binding at low-risk + interacts_with_human contexts, "rescuing" EU and halving the gap.

The paper's D metric is NOT global-beta. It is per-group-then-union (v10 §7,
"Union (>=1 group)"): for each obligation domain G1..G6, compare beta_VN(g) vs
beta_EU(g); a context counts if VN > EU in ANY group. Under that metric, G3's
tautology-vs-high-risk gap is independent of G5's transparency convergence, and
D(VN->EU) = 60% WITH transparency included. This is reproduced exactly by
verify_hsdl_harmonization.py (D(VN->EU)=60.0%, D(EU->VN)=30.0%, H=10.00%).

Below: the two aggregations side by side, to make the lesson explicit. The global
number is shown only to label it NON-STANDARD; do not cite it as the paper's metric.
"""
import itertools

risk = ["Minimal","Limited","Medium","High","Unacceptable"]
sec = ["CreditScoring","Education","Biometric","CriticalInfra","GenAI","Generic"]
role = ["Provider","Deployer","User"]; life = ["PreMarket","PostMarket"]; b = [True,False]
names = ["risk_tier","sector","system_role","lifecycle_stage",
         "modification_increases_risk","serious_harm_discovered",
         "interacts_with_human","existing_sector_certification"]
CTX = [dict(zip(names,c)) for c in itertools.product(risk,sec,role,life,b,b,b,b)]
N = len(CTX); HU = {"High","Unacceptable"}

# Per-group EU/VN firing (encoding A), beta in {0=BOT,1=Binding}
EU = {"G1":lambda c:c["risk_tier"] in HU, "G2":lambda c:c["risk_tier"] in HU,
      "G3":lambda c:c["risk_tier"] in HU, "G4":lambda c:c["risk_tier"] in HU,
      "G5":lambda c:c["interacts_with_human"], "G6":lambda c:c["risk_tier"] in HU}
VN = {"G1":lambda c:(c["system_role"]=="Provider" and c["lifecycle_stage"]=="PreMarket") or c["modification_increases_risk"] or c["risk_tier"] in {"High","Medium"},
      "G2":lambda c:c["risk_tier"]=="High", "G3":lambda c:True,
      "G4":lambda c:(c["risk_tier"] in {"Medium","High"} and c["lifecycle_stage"]=="PreMarket") or c["serious_harm_discovered"],
      "G5":lambda c:c["interacts_with_human"], "G6":lambda c:c["serious_harm_discovered"]}

# CORRECT (paper) metric: per-group then union
per_group_union = sum(any(VN[g](c) and not EU[g](c) for g in EU) for c in CTX)

# WRONG (foil) metric: global regime-beta = max over all rules
def gbeta_eu(c): return any(f(c) for f in EU.values())   # incl. Art.50 transparency
def gbeta_vn(c): return any(f(c) for f in VN.values())   # incl. Dieu4kh2 tautology -> always True
global_beta = sum(gbeta_vn(c) and not gbeta_eu(c) for c in CTX)

print(f"D(VN->EU), per-group-union (PAPER'S metric): {per_group_union}/{N} = {per_group_union/N*100:.1f}%  <- 60.0%, reproducible")
print(f"D(VN->EU), global regime-beta (NON-STANDARD foil): {global_beta}/{N} = {global_beta/N*100:.1f}%  <- 30.0%, NOT the paper's metric")
print()
print("Lesson: the 30% was an aggregation artifact, not a real encoding ambiguity.")
print("For the full obligor-vs-bindingness comparison across all 4 encodings, see")
print("verify_beta_vs_omega.py.")
assert per_group_union == 1728 and global_beta == 864
