"""
Theorem C — Refinement Matrix.
Computes Π(P_A) refines Π(P_B) for all 6 directional pairs:
  EU↔VN, EU↔ASEAN, VN↔ASEAN
× 2 versions: with tautologies, without tautologies (i.e. excluding rules where S(R)=Ctx).

For each cell: report YES/NO and list of non-nesting blocks (with sizes).
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
assert len(ctxs) == 2880

def s_of(f):
    return frozenset(i for i,c in enumerate(ctxs) if f(c))

EU = {
    'art9_risk_mgmt_continuous':    lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art11_conformity_assessment':  lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art14_human_oversight':        lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art12_recordkeeping_uniform':  lambda c: c['risk_tier'] in ('High','Unacceptable'),
    'art50_disclosure':             lambda c: c['interacts_with_human']==True,
    'art9_risk_mgmt_temporality':   lambda c: c['risk_tier'] in ('High','Unacceptable'),
}

VN = {
    'art10_kh1_self_classify':               lambda c: c['system_role']=='Provider' and c['lifecycle_stage']=='PreMarket',
    'art10_kh2_reclassify_on_modification':  lambda c: c['modification_increases_risk']==True,
    'art10_kh5a_supervision_highrisk':       lambda c: c['risk_tier']=='High',
    'art10_kh5b_supervision_medium':         lambda c: c['risk_tier']=='Medium',
    'art13_conformity_assessment_highrisk':  lambda c: c['risk_tier']=='High',
    'art13_certification_reuse':             lambda c: c['risk_tier']=='High' and c['existing_sector_certification']==True,
    'dieu4kh2_human_control_principle':      lambda c: True,                    # TAUT
    'art10_kh3_notify_classification':       lambda c: c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket',
    'decree142_art12_kh5_incident_report':   lambda c: c['serious_harm_discovered']==True,
    'art11_kh1_ai_disclosure':               lambda c: c['interacts_with_human']==True,
    'decree142_event_triggered_control':     lambda c: c['serious_harm_discovered']==True,
}

ASEAN = {
    'accountability_principle':    lambda c: True,                  # TAUT
    'transparency_principle':      lambda c: True,                  # TAUT
    'genai_disclosure_labelling':  lambda c: c['sector']=='GenAI',
}

# Compute Π
def cover(policy):
    return {n: s_of(f) for n,f in policy.items()}

PI = {'EU': cover(EU), 'VN': cover(VN), 'ASEAN': cover(ASEAN)}

# Find tautologies
def find_tauts(pi):
    full = frozenset(range(2880))
    return [n for n,s in pi.items() if s == full]

for nm in PI:
    print(f"Tautologies in {nm}: {find_tauts(PI[nm])}")

# Build without-tautology versions
PI_NT = {nm: {k:v for k,v in pi.items() if v != frozenset(range(2880))} for nm,pi in PI.items()}

# Refinement check
def refines(piA, piB):
    fails = []
    for nA, sA in piA.items():
        if not any(sA <= sB for sB in piB.values()):
            fails.append((nA, len(sA)))
    return (len(fails)==0, fails)

# Compute 12 cells (6 directional × 2 versions)
print("\n" + "="*78)
print("REFINEMENT MATRIX — Π(P_A) refines Π(P_B)?")
print("="*78)

pairs = [('EU','VN'), ('VN','EU'), ('EU','ASEAN'), ('ASEAN','EU'), ('VN','ASEAN'), ('ASEAN','VN')]
results = {}
for A,B in pairs:
    for ver, src in [('with_taut', PI), ('no_taut', PI_NT)]:
        ok, fails = refines(src[A], src[B])
        results[(A,B,ver)] = (ok, fails)
        verdict = "YES (trivial)" if ok and any(len(s)==2880 for s in src[B].values()) else ("YES" if ok else "NO")
        print(f"\n[{ver}]  Π({A}) refines Π({B})?  {verdict}")
        if not ok:
            print(f"   {len(fails)} block(s) fail to nest:")
            for n, sz in fails:
                print(f"     - {n}  (|S|={sz})")

# Sanity: per-direction summary
print("\n" + "="*78)
print("SUMMARY")
print("="*78)
for A,B in pairs:
    wt = results[(A,B,'with_taut')][0]
    nt = results[(A,B,'no_taut')][0]
    print(f"  {A} → {B}:  with_taut={'Y' if wt else 'N'},  no_taut={'Y' if nt else 'N'}")
