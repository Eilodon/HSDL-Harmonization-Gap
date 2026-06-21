"""
Independent verification of the §7.6 ObligorGap union claim in HSDL v11.
Reconstructs all 6 groups' EU/VN rules from §5.1-§5.6 and computes:
  - per-group ObligorGap counts
  - naive sum
  - TRUE union of distinct contexts (dedup)
"""
from itertools import product

RISK_TIERS = ['Minimal', 'Limited', 'Medium', 'High', 'Unacceptable']
SECTORS = ['Healthcare', 'Finance', 'Education', 'PublicSafety', 'GenAI', 'Other']
ROLES = ['Provider', 'Deployer', 'User']
LIFECYCLES = ['PreMarket', 'PostMarket']
BOOL = [True, False]

def all_contexts():
    for rt, sc, rl, lf, mr, sh, ih, ec in product(
        RISK_TIERS, SECTORS, ROLES, LIFECYCLES, BOOL, BOOL, BOOL, BOOL):
        yield dict(risk_tier=rt, sector=sc, system_role=rl, lifecycle_stage=lf,
                   modification_increases_risk=mr, serious_harm_discovered=sh,
                   interacts_with_human=ih, existing_sector_certification=ec)
ctxs = list(all_contexts())
assert len(ctxs) == 2880, len(ctxs)

HU = ('High', 'Unacceptable')

# ---- Group rule definitions (name, predicate, obligor_set) ----
# G1 (§5.1)
G1_EU = [('art9', lambda c: c['risk_tier'] in HU, frozenset({'Provider'}))]
G1_VN = [
    ('art10_kh1',  lambda c: c['system_role']=='Provider' and c['lifecycle_stage']=='PreMarket', frozenset({'Provider'})),
    ('art10_kh2',  lambda c: c['modification_increases_risk']==True, frozenset({'Provider'})),
    ('art10_kh5a', lambda c: c['risk_tier']=='High',  frozenset({'Regulator'})),
    ('art10_kh5b', lambda c: c['risk_tier']=='Medium',frozenset({'Regulator'})),
]
# G2 (§5.2) — conformity assessment; both sides {Provider} dominant case -> convergence
G2_EU = [('art43', lambda c: c['risk_tier'] in HU, frozenset({'Provider'}))]
G2_VN = [
    ('art13_high',  lambda c: c['risk_tier']=='High', frozenset({'Provider'})),
    ('art13_reuse', lambda c: c['risk_tier']=='High' and c['existing_sector_certification']==True, frozenset({'Provider'})),
]
# G3 (§5.3)
G3_EU = [('art14', lambda c: c['risk_tier'] in HU, frozenset({'Provider','Deployer'}))]
G3_VN = [('dieu4kh2', lambda c: True, frozenset())]
# G4 (§5.4)
G4_EU = [('art12', lambda c: c['risk_tier'] in HU, frozenset({'Provider','Deployer'}))]
G4_VN = [
    ('art10_kh3',     lambda c: c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket', frozenset({'Provider'})),
    ('decree142_kh5', lambda c: c['serious_harm_discovered']==True, frozenset({'Provider','Deployer'})),
]
# G5 (§5.5)
G5_EU = [('art50', lambda c: c['interacts_with_human']==True, frozenset({'Provider'}))]
G5_VN = [('art11_kh1', lambda c: c['interacts_with_human']==True, frozenset({'Provider'}))]
# G6 (§5.6)
G6_EU = [('art9', lambda c: c['risk_tier'] in HU, frozenset({'Provider'}))]
G6_VN = [('decree142_event', lambda c: c['serious_harm_discovered']==True, frozenset({'Deployer'}))]

def omega_union(c, rules):
    out = set()
    for _, f, o in rules:
        if f(c): out |= o
    return frozenset(out)

def beta_fires(c, rules):
    return any(f(c) for _, f, _ in rules)

def obligor_gap_set(eu, vn):
    s = set()
    for i, c in enumerate(ctxs):
        if beta_fires(c, eu) and beta_fires(c, vn):
            if omega_union(c, eu) != omega_union(c, vn):
                s.add(i)
    return s

groups = {
    'G1': (G1_EU, G1_VN),
    'G2': (G2_EU, G2_VN),
    'G3': (G3_EU, G3_VN),
    'G4': (G4_EU, G4_VN),
    'G5': (G5_EU, G5_VN),
    'G6': (G6_EU, G6_VN),
}

sets = {}
naive = 0
for g, (eu, vn) in groups.items():
    s = obligor_gap_set(eu, vn)
    sets[g] = s
    naive += len(s)
    pct = len(s)*100/2880
    print(f"  {g}: ObligorGap = {len(s):5d} ctx  ({pct:4.1f}%)")

print()
print(f"  Naive sum (all 6 groups):        {naive}  ({naive*100/2880:.1f}%)")

only_g3g4g6 = len(sets['G3']) + len(sets['G4']) + len(sets['G6'])
print(f"  G3+G4+G6 only (no G1):           {only_g3g4g6}  ({only_g3g4g6*100/2880:.1f}%)  <- the paper's '1,872'?")

union = set()
for g in groups:
    union |= sets[g]
print(f"  TRUE UNION (distinct ctx, dedup):{len(union)}  ({len(union)*100/2880:.1f}%)")

# Check subset claims
print()
print("  Subset checks (is each group's gap ⊆ G3's gap?):")
for g in ('G1','G4','G6'):
    print(f"    {g} ⊆ G3 : {sets[g] <= sets['G3']}")
# all gap contexts have risk_tier in {High,Unacceptable}?
all_hu = all(ctxs[i]['risk_tier'] in HU for i in union)
print(f"  Every union ctx has risk_tier ∈ {{High,Unacceptable}}: {all_hu}")
print(f"  |{{ctx: risk_tier ∈ HU}}| = {sum(1 for c in ctxs if c['risk_tier'] in HU)}")

print()
print("  Bindingness comparison:")
print(f"    ObligorGap union incidence: {len(union)*100/2880:.1f}%  (robust, reproducible)")
print(f"    Bindingness-gap D(VN->EU) @ encoding A (per-group-union): 60.0% > obligor 40.0%")
print(f"    => ranking is ASSUMED_PARAMETER-sensitive (reverses under B1/B3); see")
print(f"       verify_beta_vs_omega.py and verify_hsdl_harmonization.py")
