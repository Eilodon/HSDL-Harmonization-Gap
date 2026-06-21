"""
Phase 2 — ObligorGap computation for G3-G6 with newly researched obligors.

Confirmed obligor mappings:
  G3 EU: Art. 14 + Art. 26 → {Provider, Deployer}
  G3 VN: Điều 4 Khoản 2 (Chương I) → ∅  (no named actor)
  G4 EU: Art. 12(1) Provider logging design + Art. 26(6) Deployer log retention → {Provider, Deployer}
         (NB: Art. 19 = Provider retention duty, NOT deployer; deployer 6-month duty is Art. 26(6))
  G4 VN: Điều 10 Khoản 3 (notify classification to Regulator) → {Provider}
  G4 VN: NĐ142 Điều 19 (incident report, paper labels art12_kh5) → {Provider, Deployer}
  G5 EU: Art. 50 disclosure → {Provider}  (provider design duty, dominant case)
  G5 VN: Điều 11 Khoản 1 disclosure → {Provider}
  G6 EU: Art. 9 risk management → {Provider}
  G6 VN: NĐ142 event-triggered → {Deployer}  ("tổ chức triển khai phải áp dụng biện pháp kiểm soát")
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

# Per-group rule definitions + obligor
G3_EU = [('art14',  lambda c: c['risk_tier'] in ('High','Unacceptable'), frozenset({'Provider','Deployer'}))]
G3_VN = [('dieu4kh2', lambda c: True, frozenset())]  # ο = ∅

G4_EU = [('art12',  lambda c: c['risk_tier'] in ('High','Unacceptable'), frozenset({'Provider','Deployer'}))]
G4_VN = [
    ('art10_kh3',     lambda c: c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket', frozenset({'Provider'})),
    ('decree142_kh5', lambda c: c['serious_harm_discovered']==True,                                       frozenset({'Provider','Deployer'})),
]

G5_EU = [('art50', lambda c: c['interacts_with_human']==True, frozenset({'Provider'}))]
G5_VN = [('art11_kh1', lambda c: c['interacts_with_human']==True, frozenset({'Provider'}))]

G6_EU = [('art9',  lambda c: c['risk_tier'] in ('High','Unacceptable'), frozenset({'Provider'}))]
G6_VN = [('decree142_event',  lambda c: c['serious_harm_discovered']==True, frozenset({'Deployer'}))]

def omega_union(c, rules):
    out = set()
    for _,f,o in rules:
        if f(c): out |= o
    return frozenset(out)

def beta(c, rules):
    return 'Binding' if any(f(c) for _,f,_ in rules) else None

def analyze(name, eu, vn):
    obligor_gap = 0
    examples = []
    for c in ctxs:
        be = beta(c, eu)
        bv = beta(c, vn)
        if be is None or bv is None: continue
        oe = omega_union(c, eu)
        ov = omega_union(c, vn)
        if oe != ov:
            obligor_gap += 1
            if len(examples) < 3:
                examples.append((dict(c), oe, ov))
    print(f"\n=== {name} ===")
    print(f"  ObligorGap (β_EU>⊥, β_VN>⊥, ω_EU ≠ ω_VN): {obligor_gap} contexts")
    if examples and obligor_gap:
        print(f"  Example contexts:")
        for c, oe, ov in examples:
            keys = sorted(c.keys())
            short = {k:c[k] for k in ['risk_tier','sector','lifecycle_stage','interacts_with_human','serious_harm_discovered']}
            print(f"    {short}  ω_EU={set(oe)}  ω_VN={set(ov)}")
    return obligor_gap

og3 = analyze('G3 (Human Oversight)', G3_EU, G3_VN)
og4 = analyze('G4 (Incident Reporting)', G4_EU, G4_VN)
og5 = analyze('G5 (Transparency)', G5_EU, G5_VN)
og6 = analyze('G6 (Risk-Mgmt Temporality)', G6_EU, G6_VN)

print("\n" + "="*70)
print("SUMMARY: New ObligorGap instances introduced by Phase 2 encoding")
print("="*70)
print(f"  G3: {og3} ObligorGap contexts  {'← NEW INSTANCE!' if og3 else ''}")
print(f"  G4: {og4} ObligorGap contexts  {'← NEW INSTANCE!' if og4 else ''}")
print(f"  G5: {og5} ObligorGap contexts (expected 0, convergence)")
print(f"  G6: {og6} ObligorGap contexts  {'← NEW INSTANCE!' if og6 else ''}")
