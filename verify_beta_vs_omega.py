"""
AXIOM re-audit: compare bindingness-gap D(VN->EU) vs obligor-gap union using the
SAME per-group-then-union metric the paper actually uses (v10 §7 "Union (>=1 group)").

This corrects verify_bindingness_baseline.py, which wrongly used a GLOBAL regime-beta
(max over ALL rules), letting EU's Art.50 transparency "rescue" EU and yielding a
spurious 30%. The paper's D is per-group-union: G3's tautology-vs-high-risk gap is
NOT cancelled by G5's transparency convergence (different group).

Both metrics computed per encoding, per-group-then-union, so the comparison is
apples-to-apples.
"""
import itertools

risk_tiers = ["Minimal", "Limited", "Medium", "High", "Unacceptable"]
sectors = ["CreditScoring", "Education", "Biometric", "CriticalInfra", "GenAI", "Generic"]
system_roles = ["Provider", "Deployer", "User"]
lifecycle_stages = ["PreMarket", "PostMarket"]
bools = [True, False]
dims = [risk_tiers, sectors, system_roles, lifecycle_stages, bools, bools, bools, bools]
names = ["risk_tier", "sector", "system_role", "lifecycle_stage",
         "modification_increases_risk", "serious_harm_discovered",
         "interacts_with_human", "existing_sector_certification"]
CTX = [dict(zip(names, c)) for c in itertools.product(*dims)]
N = len(CTX); assert N == 2880

PROV = frozenset({"Provider"}); PD = frozenset({"Provider", "Deployer"})
REG = frozenset({"Regulator"}); DEP = frozenset({"Deployer"}); EMPTY = frozenset()

def encs(encoding):
    medium = encoding in ("B1", "B3"); unacc = encoding in ("B2", "B3")
    eu_high = {"High", "Unacceptable"} | ({"Medium"} if medium else set())
    vn_high = {"High"} | ({"Unacceptable"} if unacc else set())
    return eu_high, vn_high

def group_rules(encoding):
    eu_high, vn_high = encs(encoding)
    # (predicate, obligor) per group, EU and VN sides
    EU = {
        "G1": [(lambda c: c["risk_tier"] in eu_high, PROV)],
        "G2": [(lambda c: c["risk_tier"] in eu_high, PROV)],
        "G3": [(lambda c: c["risk_tier"] in eu_high, PD)],
        "G4": [(lambda c: c["risk_tier"] in eu_high, PD)],
        "G5": [(lambda c: c["interacts_with_human"], PROV)],
        "G6": [(lambda c: c["risk_tier"] in eu_high, PROV)],
    }
    VN = {
        "G1": [(lambda c: c["system_role"]=="Provider" and c["lifecycle_stage"]=="PreMarket", PROV),
               (lambda c: c["modification_increases_risk"], PROV),
               (lambda c: c["risk_tier"] in vn_high, REG),
               (lambda c: c["risk_tier"]=="Medium", REG)],
        "G2": [(lambda c: c["risk_tier"] in vn_high, PROV),
               (lambda c: c["risk_tier"] in vn_high and c["existing_sector_certification"], PROV)],
        "G3": [(lambda c: True, EMPTY)],
        "G4": [(lambda c: c["risk_tier"] in {"Medium","High"} and c["lifecycle_stage"]=="PreMarket", PROV),
               (lambda c: c["serious_harm_discovered"], PD)],
        "G5": [(lambda c: c["interacts_with_human"], PROV)],
        "G6": [(lambda c: c["serious_harm_discovered"], DEP)],
    }
    return EU, VN

def fires(c, rules): return any(p(c) for p,_ in rules)
def omega(c, rules):
    o = set()
    for p,ob in rules:
        if p(c): o |= ob
    return frozenset(o)

def analyze(encoding):
    EU, VN = group_rules(encoding)
    vn_gt_eu = 0; obligor = 0
    for c in CTX:
        # bindingness gap (VN strictly stricter): some group VN binds, EU doesn't
        if any(fires(c, VN[g]) and not fires(c, EU[g]) for g in EU):
            vn_gt_eu += 1
        # obligor gap: some group both bind and obligor sets differ
        if any(fires(c, EU[g]) and fires(c, VN[g]) and omega(c, EU[g]) != omega(c, VN[g]) for g in EU):
            obligor += 1
    return vn_gt_eu, obligor

print(f"{'enc':<5}{'D(VN->EU) bindingness':<24}{'ObligorGap union':<20}{'ordering'}")
for enc in ["A", "B1", "B2", "B3"]:
    b, o = analyze(enc)
    order = "bindingness > obligor" if b > o else ("obligor > bindingness" if o > b else "TIE")
    print(f"{enc:<5}{b} ({b/N*100:.1f}%){'':<12}{o} ({o/N*100:.1f}%){'':<7}{order}")

print("\nBoth gaps range 40.0%-60.0% across the 4 encodings and are ANTI-CORRELATED")
print("(obligor 40 / bindingness 60 at A,B2; obligor 60 / bindingness 40 at B1,B3).")
print("Report as ranges per the paper's own §7.4 sensitivity disclosure; the beta-vs-omega")
print("ranking is encoding-dependent, NOT a fixed structural ordering. Invariant: obligor")
print("mismatch present in 4/6 domains under every encoding.")
