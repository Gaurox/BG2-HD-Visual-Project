"""Targeted read-only checks; preserve the earlier exhaustive audit and image jobs."""
from pathlib import Path
import csv, hashlib, json, re, struct, sys
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
GAME = get_path('bg2ee_game_root', required=True)
BASE = ROOT/'projectiles/analysis/audit-complet-243-20261028-v1'
def js(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def rows(p): return list(csv.DictReader(p.open(encoding='utf-8-sig', newline='')))
def save(n, data):
    with (OUT/n).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2); f.write('\n')
if (OUT/'summary.json').exists(): raise SystemExit('Existing evidence: use a new version directory')
bifs, entries = load_key()
key = {(n.upper(), t): loc for n, t, loc in entries}
def read(n, t, ext):
    p = GAME/'override'/f'{n}.{ext}'
    if p.exists(): return p.read_bytes()
    return resolve_resource(bifs, key[n, t])[0] if (n,t) in key else None
manifest = js(GAME/'iee-assets/effects/manifest.json')
catalog = {r['resref']: r for r in manifest['resources']}
baseline = js(BASE/'summary.json')
pro_checks = []
for row in rows(ROOT/'projectiles/index/resources.csv'):
    n = row['resref']; raw = read(n, 1021, 'pro')
    prior = baseline['input_hashes'].get(str(GAME/'override'/f'{n}.pro'),
            baseline['input_hashes'].get(f'KEY://{n}.pro'))
    pro_checks.append(dict(pro=n, matches_full_audit=hashlib.sha256(raw).hexdigest().upper()==prior))
tests = [
    ('SPWI502','CLOUDKIL','Nuage mortel','Nuage persistant, fumée, palette et transparence'),
    ('SPWI313','TRAPSKUL','Piège à crâne','Projectile + ombre native + fragments SKLH/SPSHADOW'),
    ('SPWI118','CHROMORB','Orbe chromatique','Surface composée primaire/ombre ; repli natif connu à diagnostiquer'),
    ('SPPR517','INSEC2','Fléau d’insectes','Vol, anneau/impact, alias et palette déjà installés'),
    ('SPWI404','ICESTORM','Tempête de glace','Explosion native FIREBALL:3 ; ne pas présumer la couverture des fragments'),
    ('SPWI615','LIGHTCHA','Éclairs en chaîne','Traînées SPCHLGT1/2/3 ; cycle9 SPCHLGT3 déjà signalé absent'),
]
usage = rows(ROOT/'projectiles/analysis/20261028-v2/usage.csv')
audit_rows = {r['pro']: r for r in rows(BASE/'projectiles-243.csv')}
components = rows(BASE/'components.csv')
selected = set(); matrix=[]
for spell, pro, label, risk in tests:
    raw = read(spell, 1006, 'spl')
    abilities = [u for u in usage if u['resource']==spell and u['format']=='SPL']
    refs_ok = bool(abilities) and all(u['projectile']==pro and
        hashlib.sha256(raw).hexdigest().upper()==u['source_sha256'] and
        struct.unpack_from('<H',raw,int(u['offset'],16))[0]==int(u['raw_missile_id']) for u in abilities)
    family=set(audit_rows[pro]['closure'].split(';'))
    leaves=[c for c in components if c['pro'] in family and c['activity'] not in ('disabled','metadata')]
    names={c['resource'] for c in leaves if c['resource'] in catalog}
    selected.update(names)
    matrix.append(dict(spell=spell,pro=pro,label=label,risk=risk,ability_references_current=refs_ok,
        runtime_resources=sorted(names),baseline_verdict=audit_rows[pro]['verdict'],
        command=f'C:Eval(\'ForceSpellRES("{spell}",Player2)\',0)',
        result='awaiting-user-test-and-runtime-evidence'))
# Physical samples, not a repeat of the 10 GB exhaustive image check.
samples=[]
for n in sorted(selected):
    frames=[f for f in manifest['frames'] if f['resref']==n]
    for i in sorted({0,len(frames)//2,len(frames)-1}):
        f=frames[i];p=GAME/'iee-assets/effects'/f['asset']
        samples.append(dict(resref=n,asset=f['asset'],bytes=f['bytes'],
            ok=p.is_file() and p.stat().st_size==f['bytes'] and sha(p)==f['sha256'].upper()))
carriers=[]
for c in manifest['runtime_bam_carriers']:
    if c['resref'] not in selected: continue
    p=GAME/c['asset'];carriers.append(dict(resref=c['resref'],ok=p.is_file() and sha(p)==c['sha256'].upper()))
scope=(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/effect_secondary_scope.h').read_text()
whitelist=set(re.findall(r'"([A-Z0-9_]+)"',scope))
summary=dict(scope='243 PRO byte continuity + 6 targeted spell chains + sampled installed images; not global QA',
    manifest_unchanged=sha(GAME/'iee-assets/effects/manifest.json')==baseline['manifest_sha256'],
    registry_sha_matches=sha(GAME/'iee-assets/effects'/manifest['registry'])==manifest['registry_sha256'].upper(),
    dll_matches_v3=sha(GAME/'InfinityEngine-Enhancer.dll')==
        js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-flight-mask-20261028-v3/installation.json')['dll']['sha256'],
    pro_count=len(pro_checks),pro_issues=[r['pro'] for r in pro_checks if not r['matches_full_audit']],
    selected_resources=len(selected),sampled_frames=len(samples),sampled_bytes=sum(r['bytes'] for r in samples),
    frame_issues=[r['asset'] for r in samples if not r['ok']],carriers_checked=len(carriers),
    carrier_issues=[r['resref'] for r in carriers if not r['ok']],
    missing_outputs={n:n not in catalog for n in ('BGLRYU','SPCL236U','SPGLYPHI')},
    LIGHTSTO_MAGMIS_resource_present=read('MAGMIS',1000,'bam') is not None,
    SPCHLGT3_declared_cycles=[c['cycle'] for c in catalog['SPCHLGT3']['cycles']],
    SHAREA_in_secondary_whitelist='SHAREA' in whitelist,
    unverified='Composite surfaces, native children/palettes, per-owner and visual acceptance remain separate')
save('summary.json',summary);save('targeted-tests.json',matrix)
save('physical-samples.json',dict(frames=samples,carriers=carriers,PROs=pro_checks))
print(json.dumps(summary,ensure_ascii=False,indent=2))
