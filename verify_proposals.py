"""
Verify claims used by proposals 1-3 against the actual encoding in paper v10.
"""
from itertools import product

# Ctx schema per §3.2
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
print(f"|Ctx| = {len(ctxs)}")  # should be 2880

# --- VN rules per §5 (per-group) ---
# Group 1
def vn_g1_kh1(c):  return c['system_role']=='Provider' and c['lifecycle_stage']=='PreMarket'
def vn_g1_kh2(c):  return c['modification_increases_risk']==True
def vn_g1_kh5a(c): return c['risk_tier']=='High'
def vn_g1_kh5b(c): return c['risk_tier']=='Medium'
G1_VN = [('kh1',vn_g1_kh1,{'Provider'}),
         ('kh2',vn_g1_kh2,{'Provider'}),
         ('kh5a',vn_g1_kh5a,{'Regulator'}),
         ('kh5b',vn_g1_kh5b,{'Regulator'})]

# Group 2
def vn_g2_high(c):  return c['risk_tier']=='High'
def vn_g2_reuse(c): return c['risk_tier']=='High' and c['existing_sector_certification']==True
G2_VN = [('art13_high',vn_g2_high,{'Provider'}),
         ('art13_reuse',vn_g2_reuse,{'Provider'})]

# Group 4
def vn_g4_kh3(c):    return c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket'
def vn_g4_decree(c): return c['serious_harm_discovered']==True
G4_VN = [('art10_kh3',vn_g4_kh3,None),
         ('decree142_kh5',vn_g4_decree,None)]

# --- Helpers ---
def s_of(rule_fn):
    return frozenset(i for i,c in enumerate(ctxs) if rule_fn(c))

def cofiring_pairs(rules):
    """For each pair of rules in this group, return |contexts where both fire|."""
    out = {}
    for i,(n1,f1,_) in enumerate(rules):
        for j,(n2,f2,_) in enumerate(rules):
            if i<j:
                s1, s2 = s_of(f1), s_of(f2)
                out[(n1,n2)] = (len(s1 & s2), s1, s2)
    return out

def subset_relation(s1, s2):
    """Return one of: 'A⊂B', 'B⊂A', 'A=B', 'disjoint', 'incomparable'."""
    if s1 == s2: return 'A=B'
    if s1 < s2:  return 'A⊂B'
    if s2 < s1:  return 'B⊂A'
    if not (s1 & s2): return 'disjoint'
    return 'incomparable'

# === Claim 1: G1 has 816/2880 ctx with ≥2 VN rules co-firing ===
def n_firing(c, rules):
    return sum(1 for _,f,_ in rules if f(c))

g1_multi = sum(1 for c in ctxs if n_firing(c, G1_VN) >= 2)
print(f"\n[Claim] G1: contexts with ≥2 VN rules co-firing = {g1_multi}/2880")
# Per proposal: 816

g2_multi = sum(1 for c in ctxs if n_firing(c, G2_VN) >= 2)
print(f"[Claim] G2: contexts with ≥2 VN rules co-firing = {g2_multi}/2880")
# Per proposal: 288

g4_multi = sum(1 for c in ctxs if n_firing(c, G4_VN) >= 2)
print(f"[Claim] G4: contexts with ≥2 VN rules co-firing = {g4_multi}/2880")
# Per proposal: 288

# === Claim 2: Pairwise subset relations ===
print("\n[G1 VN pairwise relations] (6 pairs)")
pairs_g1 = []
for i,(n1,f1,_) in enumerate(G1_VN):
    for j,(n2,f2,_) in enumerate(G1_VN):
        if i<j:
            r = subset_relation(s_of(f1), s_of(f2))
            print(f"  ({n1}, {n2}): {r}")
            pairs_g1.append((n1,n2,r))

print("\n[G2 VN pairwise relations] (1 pair)")
for i,(n1,f1,_) in enumerate(G2_VN):
    for j,(n2,f2,_) in enumerate(G2_VN):
        if i<j:
            r = subset_relation(s_of(f1), s_of(f2))
            print(f"  ({n1}, {n2}): {r}")

print("\n[G4 VN pairwise relations] (1 pair)")
for i,(n1,f1,_) in enumerate(G4_VN):
    for j,(n2,f2,_) in enumerate(G4_VN):
        if i<j:
            r = subset_relation(s_of(f1), s_of(f2))
            print(f"  ({n1}, {n2}): {r}")

# === Claim 3: Syntactic conjunct count (count of dimensions constrained) ===
# Proposal claims "tie at 2/6 G1 pairs" — verify

# Conjunct counts in G1:
# kh1: system_role + lifecycle_stage = 2 dims
# kh2: modification_increases_risk = 1 dim
# kh5a: risk_tier = 1 dim
# kh5b: risk_tier = 1 dim
syntactic_counts_g1 = {'kh1':2, 'kh2':1, 'kh5a':1, 'kh5b':1}
print("\n[G1 Syntactic conjunct-count comparison] (6 pairs)")
ties_g1 = 0
for n1, n2, _ in pairs_g1:
    c1, c2 = syntactic_counts_g1[n1], syntactic_counts_g1[n2]
    if c1 == c2:
        print(f"  ({n1}={c1}, {n2}={c2}): TIE")
        ties_g1 += 1
    else:
        winner = n1 if c1>c2 else n2
        print(f"  ({n1}={c1}, {n2}={c2}): {winner} more specific")
print(f"  Total ties: {ties_g1}/6")

# === Claim 4: Co-firing pairs with DIFFERENT obligor sets in G1 (relevant for ω-lex-specialis) ===
print("\n[G1: pairs co-firing with DIFFERENT obligor sets]")
diff_pairs = 0
total_cofire_ctxs_with_diff = 0
for i,(n1,f1,o1) in enumerate(G1_VN):
    for j,(n2,f2,o2) in enumerate(G1_VN):
        if i<j:
            s1, s2 = s_of(f1), s_of(f2)
            cofire = s1 & s2
            if o1 != o2 and cofire:
                print(f"  ({n1} {o1}, {n2} {o2}): co-fire in {len(cofire)} ctx")
                diff_pairs += 1
                total_cofire_ctxs_with_diff += len(cofire)
print(f"  Pairs with different ο that co-fire: {diff_pairs}")

# Count contexts where ω_union ≠ ω_lex_specialis_indeterminate would matter
# A context matters when (a) >=2 rules fire, AND (b) those rules have non-identical ο sets
def omega_union(c, rules):
    fired = [(n,o) for n,f,o in rules if f(c)]
    if not fired: return set()
    u = set()
    for _,o in fired: u |= o
    return frozenset(u)

def omega_LS_indeterminate(c, rules):
    """Subset-based lex specialis. Returns (indeterminate?, obligor_set_or_None)."""
    fired = [(n,f,o,s_of(f)) for n,f,o in rules if f(c)]
    if not fired: return (False, frozenset())  # ∅
    # find unique minimal element under S(Ri) ⊆ S(Rj)
    minimal = []
    for i,(n,_,o,si) in enumerate(fired):
        is_min = True
        for j,(_,_,_,sj) in enumerate(fired):
            if i!=j and sj < si:  # someone strictly more specific exists
                is_min = False
                break
        if is_min:
            minimal.append((n,o))
    # if exactly one minimal, OK; otherwise indeterminate
    if len(minimal) == 1:
        return (False, minimal[0][1])
    return (True, None)

# Check G1
diff_union_LS = 0
indeterminate = 0
for c in ctxs:
    ou = omega_union(c, G1_VN)
    ind, ols = omega_LS_indeterminate(c, G1_VN)
    if ind:
        indeterminate += 1
    elif ols != ou:
        diff_union_LS += 1
print(f"\n[G1: ω_union vs ω_lex_specialis (subset-based)]")
print(f"  Contexts where LS is INDETERMINATE: {indeterminate}/2880")
print(f"  Contexts where LS defined but ≠ union: {diff_union_LS}/2880")

# === Claim 5: G4 mechanism attribution (validate 144+720+144=1008 claim from §5.4) ===
def fire_only_kh3(c): return vn_g4_kh3(c) and not vn_g4_decree(c)
def fire_only_decree(c): return vn_g4_decree(c) and not vn_g4_kh3(c)
def fire_both(c): return vn_g4_kh3(c) and vn_g4_decree(c)

# G4 EU: art12 fires risk_tier in [High, Unacceptable]
def eu_g4(c): return c['risk_tier'] in ('High','Unacceptable')

# VN>EU in G4: VN fires (any rule) AND EU doesn't fire
def vn_g4_fires(c): return vn_g4_kh3(c) or vn_g4_decree(c)

vn_gt_eu_g4 = [c for c in ctxs if vn_g4_fires(c) and not eu_g4(c)]
only_kh3 = sum(1 for c in vn_gt_eu_g4 if fire_only_kh3(c))
only_decree = sum(1 for c in vn_gt_eu_g4 if fire_only_decree(c))
both = sum(1 for c in vn_gt_eu_g4 if fire_both(c))
print(f"\n[G4 VN>EU mechanism attribution]")
print(f"  Total VN>EU contexts: {len(vn_gt_eu_g4)}")
print(f"  Only via kh3:    {only_kh3}")
print(f"  Only via decree: {only_decree}")
print(f"  Via both:        {both}")
print(f"  Sum: {only_kh3+only_decree+both}")

# === Claim 6: ASEAN co-firing within groups ===
# G1 ASEAN: 1 rule
# G3 ASEAN: 1 rule
# G4 ASEAN: 1 rule (genai)
# G5 ASEAN: 1 rule
# Nothing co-fires within a group. Confirm by listing.
print("\n[ASEAN]: each per-group mini-regime has at most 1 rule — no co-firing possible per H4 scoping.")
