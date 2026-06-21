"""
Audit of §7.6 line ~1057 claim:
"syntactic lex specialis would reduce Group 1's contribution to 240 and Group 4's
 to 144 (verified by phase3_omega.py) ... alternatives bounded above by omega_union,
 never enlarge any count."

Compute G4 ObligorGap(EU,VN) under omega_union vs omega_LS_syntactic using the
FINAL obligors from §5.4/§A.6 (NOT phase3_omega.py's PROVISIONAL placeholders).
"""
from itertools import product

RISK = ['Minimal','Limited','Medium','High','Unacceptable']
SEC = ['Healthcare','Finance','Education','PublicSafety','GenAI','Other']
ROLE = ['Provider','Deployer','User']; LIFE=['PreMarket','PostMarket']; B=[True,False]
names = ['risk_tier','sector','system_role','lifecycle_stage',
         'modification_increases_risk','serious_harm_discovered',
         'interacts_with_human','existing_sector_certification']
CTX = [dict(zip(names,c)) for c in product(RISK,SEC,ROLE,LIFE,B,B,B,B)]
N=len(CTX); HU=('High','Unacceptable')

# G4 EU: art12 at risk in {High,Unacceptable} -> {Provider,Deployer}
EU = [(lambda c: c['risk_tier'] in HU, frozenset({'Provider','Deployer'}), 1)]
# G4 VN FINAL (§5.4/§A.6): (pred, obligor, n_dims_constrained)
VN = [
    (lambda c: c['risk_tier'] in ('Medium','High') and c['lifecycle_stage']=='PreMarket',
        frozenset({'Provider'}), 2),                          # art10_kh3: {risk_tier, lifecycle}
    (lambda c: c['serious_harm_discovered']==True,
        frozenset({'Provider','Deployer'}), 1),               # decree142_kh5: {serious_harm}
]

def fires(c, rules): return any(p(c) for p,_,_ in rules)
def omega_union(c, rules):
    o=set()
    for p,ob,_ in rules:
        if p(c): o|=ob
    return frozenset(o)
def omega_syn(c, rules):
    fired=[(ob,d) for p,ob,d in rules if p(c)]
    if not fired: return ('def', frozenset())
    md=max(d for _,d in fired)
    top=[ob for ob,d in fired if d==md]
    if len(top)==1: return ('def', top[0])
    return ('indet', None)

gap_union=0; gap_syn=0; gap_syn_indet=0
for c in CTX:
    if not (fires(c,EU) and fires(c,VN)): continue
    oe = omega_union(c,EU)
    ov_u = omega_union(c,VN)
    if oe != ov_u: gap_union += 1
    st, ov_s = omega_syn(c,VN)
    if st=='indet': gap_syn_indet += 1
    elif oe != ov_s: gap_syn += 1

print("G4 ObligorGap(EU,VN), FINAL obligors:")
print(f"  omega_union:      {gap_union}  (paper table: 144)")
print(f"  omega_LS_syntactic: {gap_syn} ObligorGap, {gap_syn_indet} INDETERMINATE")
print()
print(f"  Paper §7.6 claims syntactic 'reduces G4 to 144'. Actual syntactic = {gap_syn}.")
print(f"  => syntactic {'ENLARGES' if gap_syn>gap_union else 'reduces'} G4 ({gap_union} -> {gap_syn}).")
print(f"  => 'never enlarge any count' is {'FALSE (G4 counterexample)' if gap_syn>gap_union else 'ok'}.")
# all within risk=High region?
syn_ctx=[c for c in CTX if fires(c,EU) and fires(c,VN) and omega_syn(c,VN)[0]=='def'
         and omega_union(c,EU)!=omega_syn(c,VN)[1]]
print(f"  All syntactic-gap ctx have risk_tier=High? {all(c['risk_tier']=='High' for c in syn_ctx)} (⊂ G3's {{High,Unacceptable}})")
