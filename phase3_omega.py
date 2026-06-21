"""
Phase 3 — ω-aggregation sensitivity analysis.

Compare ω_union (current Definition H11) vs ω_lex_specialis (Definition H15)
under two candidate specificity orders (H14 subset-based, H14' syntactic).
Run across G1, G2, G4 (the only groups with multi-rule co-firing on VN side).
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

def s_of(f):
    return frozenset(i for i,c in enumerate(ctxs) if f(c))

# Each rule = (name, predicate, obligor_set, n_dims_constrained)
G1_VN = [
    ('art10_kh1',  lambda c: c['system_role']=='Provider' and c['lifecycle_stage']=='PreMarket', frozenset({'Provider'}), 2),
    ('art10_kh2',  lambda c: c['modification_increases_risk']==True,                            frozenset({'Provider'}), 1),
    ('art10_kh5a', lambda c: c['risk_tier']=='High',                                            frozenset({'Regulator'}), 1),
    ('art10_kh5b', lambda c: c['risk_tier']=='Medium',                                          frozenset({'Regulator'}), 1),
]
G2_VN = [
    ('art13_high',  lambda c: c['risk_tier']=='High',                                            frozenset({'Provider'}), 1),
    ('art13_reuse', lambda c: c['risk_tier']=='High' and c['existing_sector_certification']==True, frozenset({'Provider'}), 2),
]
G4_VN = [
    # G4 obligor encoding is currently empty in §5.4 (Phase 2 will fill). For Phase 3,
    # use placeholder obligors based on most-likely encoding per Phase 2 plan:
    #   art10_kh3 = notification of classification → likely {Regulator}
    #   decree142_kh5 = incident report → likely {Regulator, Provider}
    # Marked as PROVISIONAL until Phase 2 confirms.
    ('art10_kh3',     lambda c: c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket', frozenset({'Regulator'}), 2),
    ('decree142_kh5', lambda c: c['serious_harm_discovered']==True,                                       frozenset({'Regulator','Provider'}), 1),
]

# ω_union (Definition H11)
def omega_union(ctx, rules):
    out = set()
    for n,f,o,_ in rules:
        if f(ctx): out |= o
    return frozenset(out)

# ω_LS subset-based (Definition H14 / H15)
def omega_LS_subset(ctx, rules, s_cache):
    fired = [(n,o,s_cache[n]) for n,f,o,_ in rules if f(ctx)]
    if not fired: return ('defined', frozenset())
    # Find minimal elements: R_i is minimal if no other firing R_j has S(R_j) ⊂ S(R_i)
    minimal = []
    for i,(ni,oi,si) in enumerate(fired):
        is_min = True
        for j,(nj,oj,sj) in enumerate(fired):
            if i!=j and sj < si:  # strict subset
                is_min = False
                break
        if is_min:
            minimal.append((ni, oi))
    if len(minimal) == 1:
        return ('defined', minimal[0][1])
    return ('indeterminate', None)

# ω_LS syntactic (Definition H14' / H15)
def omega_LS_syntactic(ctx, rules):
    fired = [(n,o,d) for n,f,o,d in rules if f(ctx)]
    if not fired: return ('defined', frozenset())
    max_d = max(d for _,_,d in fired)
    most_specific = [(n,o) for n,o,d in fired if d==max_d]
    if len(most_specific) == 1:
        return ('defined', most_specific[0][1])
    return ('indeterminate', None)

def analyze(group_name, rules):
    s_cache = {n: s_of(f) for n,f,_,_ in rules}
    
    n_fire_any = 0
    n_multi_fire = 0
    n_union_ne_subset = 0
    n_subset_indet = 0
    n_union_ne_syntactic = 0
    n_syntactic_indet = 0
    
    breakdown_subset = {'taut_agree':0, 'taut_disagree':0, 'indet':0}
    breakdown_syntactic = {'taut_agree':0, 'taut_disagree':0, 'indet':0}
    
    for c in ctxs:
        firing = [n for n,f,_,_ in rules if f(c)]
        if firing: n_fire_any += 1
        if len(firing) >= 2: n_multi_fire += 1
        
        ou = omega_union(c, rules)
        st_sub, ols_sub = omega_LS_subset(c, rules, s_cache)
        st_syn, ols_syn = omega_LS_syntactic(c, rules)
        
        # Subset LS
        if st_sub == 'indeterminate':
            n_subset_indet += 1
        elif ols_sub != ou:
            n_union_ne_subset += 1
        
        # Syntactic LS
        if st_syn == 'indeterminate':
            n_syntactic_indet += 1
        elif ols_syn != ou:
            n_union_ne_syntactic += 1
    
    print(f"\n=== {group_name} ===")
    print(f"  Contexts where any rule fires:           {n_fire_any}/2880")
    print(f"  Contexts where ≥2 rules co-fire:         {n_multi_fire}/2880")
    print()
    print(f"  [Subset-based H14]")
    print(f"    INDETERMINATE:                          {n_subset_indet}/2880  ({n_subset_indet*100/2880:.1f}%)")
    print(f"    Defined and ≠ ω_union:                  {n_union_ne_subset}/2880")
    print(f"    → ω_union and ω_LS_subset give SAME output everywhere else.")
    print()
    print(f"  [Syntactic H14']")
    print(f"    INDETERMINATE:                          {n_syntactic_indet}/2880  ({n_syntactic_indet*100/2880:.1f}%)")
    print(f"    Defined and ≠ ω_union:                  {n_union_ne_syntactic}/2880")

# Run
analyze('G1', G1_VN)
analyze('G2', G2_VN)
analyze('G4 (provisional obligors)', G4_VN)

# Special: count ObligorGap instances under each ω choice for G1
# G1 EU: art9 fires at risk in [High,Unacceptable] with ο={Provider}
print("\n" + "="*70)
print("G1: ObligorGap incidence under union vs subset-LS vs syntactic-LS")
print("="*70)

def beta_eu_g1(c): return 'Binding' if c['risk_tier'] in ('High','Unacceptable') else None
def omega_eu_g1(c): return frozenset({'Provider'}) if beta_eu_g1(c) else frozenset()

s_cache_g1 = {n: s_of(f) for n,f,_,_ in G1_VN}

gap_union = 0
gap_subset_strict = 0   # only count ctx where subset-LS is DEFINED (else exclude)
gap_subset_indet = 0    # count ctx where subset-LS is INDETERMINATE
gap_syn_strict = 0
gap_syn_indet = 0

for c in ctxs:
    be = beta_eu_g1(c)
    bv_fire = any(f(c) for _,f,_,_ in G1_VN)
    if not (be and bv_fire): continue  # ObligorGap requires both β > ⊥
    
    oe = omega_eu_g1(c)
    
    # union
    ov_u = omega_union(c, G1_VN)
    if oe != ov_u: gap_union += 1
    
    # subset-LS
    st, ov_sub = omega_LS_subset(c, G1_VN, s_cache_g1)
    if st == 'indeterminate':
        gap_subset_indet += 1
    elif oe != ov_sub:
        gap_subset_strict += 1
    
    # syntactic-LS
    st2, ov_syn = omega_LS_syntactic(c, G1_VN)
    if st2 == 'indeterminate':
        gap_syn_indet += 1
    elif oe != ov_syn:
        gap_syn_strict += 1

print(f"\n  ObligorGap(EU,VN) count under each ω choice (G1, β_EU and β_VN both > ⊥):")
print(f"    ω_union (current):           {gap_union} ObligorGap contexts")
print(f"    ω_LS_subset (defined only):  {gap_subset_strict} ObligorGap, {gap_subset_indet} INDETERMINATE")
print(f"    ω_LS_syntactic (defined only): {gap_syn_strict} ObligorGap, {gap_syn_indet} INDETERMINATE")
