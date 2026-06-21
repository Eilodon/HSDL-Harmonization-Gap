"""
Carefully verify H8.1 direction logic.

Definition H8: 'Π(P_A) refines Π(P_B)' iff for EVERY S_A ∈ Π(P_A),
EXISTS S_B ∈ Π(P_B) with S_A ⊆ S_B.

So "EU refined by VN" means: for every EU block, exists a VN block containing it.
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

def s_of(rule_fn):
    return frozenset(i for i,c in enumerate(ctxs) if rule_fn(c))

# Build complete EU and VN policies from §5
# EU rules (from §5.1, §5.2, §5.3, §5.4, §5.5, §5.6)
EU_rules = {
    'art9_risk_mgmt_continuous':     lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art11_conformity_assessment':   lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art14_human_oversight':         lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art12_recordkeeping_uniform':   lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art50_disclosure':              lambda c: c['interacts_with_human']==True,
    'art9_risk_mgmt_temporality':    lambda c: c['risk_tier'] in ('High','Unacceptable'),
}

VN_rules = {
    'art10_kh1_self_classify':              lambda c: c['system_role']=='Provider' and c['lifecycle_stage']=='PreMarket',
    'art10_kh2_reclassify_on_modification': lambda c: c['modification_increases_risk']==True,
    'art10_kh5a_supervision_highrisk':      lambda c: c['risk_tier']=='High',
    'art10_kh5b_supervision_medium':        lambda c: c['risk_tier']=='Medium',
    'art13_conformity_assessment_highrisk': lambda c: c['risk_tier']=='High',
    'art13_certification_reuse':            lambda c: c['risk_tier']=='High' and c['existing_sector_certification']==True,
    'dieu4kh2_human_control_principle':     lambda c: True,  # tautology
    'art10_kh3_notify_classification':      lambda c: c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket',
    'decree142_art12_kh5_incident_report':  lambda c: c['serious_harm_discovered']==True,
    'art11_kh1_ai_disclosure':              lambda c: c['interacts_with_human']==True,
    'decree142_event_triggered_control':    lambda c: c['serious_harm_discovered']==True,
}

PI_EU = {n: s_of(f) for n,f in EU_rules.items()}
PI_VN = {n: s_of(f) for n,f in VN_rules.items()}

def refines(piA, piB):
    """piA refines piB iff every block in piA is contained in some block in piB."""
    fails = []
    for nA, sA in piA.items():
        found = False
        for nB, sB in piB.items():
            if sA <= sB:
                found = True
                break
        if not found:
            fails.append(nA)
    return (len(fails)==0, fails)

print("=== EU refined by VN? (Every EU block nests in some VN block) ===")
ok, fails = refines(PI_EU, PI_VN)
if ok:
    print("YES — Π(EU) refines Π(VN).")
    print("Why: Điều 4 Khoản 2 is tautology (Ctx), so every EU block ⊆ Ctx.")
else:
    print("NO. Failing EU blocks:")
    for n in fails:
        print(f"  {n} — no VN block ⊇ this")

print()
print("=== VN refined by EU? (Every VN block nests in some EU block) ===")
ok, fails = refines(PI_VN, PI_EU)
if ok:
    print("YES")
else:
    print("NO. Failing VN blocks:")
    for n in fails:
        print(f"  {n} — no EU block ⊇ S({n})")
        sA = PI_VN[n]
        print(f"    |S({n})| = {len(sA)}")
        # Show which EU blocks come close
        for nB, sB in PI_EU.items():
            print(f"    EU.{nB}: |∩|={len(sA & sB)}, |S_A \\ S_B|={len(sA - sB)}")
        break  # just show one

print()
print("=== After removing tautologies (Điều 4 Khoản 2): ===")
PI_VN_no_taut = {n:s for n,s in PI_VN.items() if n != 'dieu4kh2_human_control_principle'}
ok, fails = refines(PI_EU, PI_VN_no_taut)
if ok:
    print("EU refined by VN (no taut)? YES")
else:
    print(f"EU refined by VN (no taut)? NO — {len(fails)} blocks fail: {fails}")
ok, fails = refines(PI_VN_no_taut, PI_EU)
if ok:
    print("VN (no taut) refined by EU? YES")
else:
    print(f"VN (no taut) refined by EU? NO — {len(fails)} blocks fail: {fails}")
