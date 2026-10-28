"""Read-only live route audit; writes only beside this script."""
from pathlib import Path
import csv, hashlib, json, sys
from collections import Counter
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from projectile_tracking import parse_pro
OUT=Path(__file__).parent
GAME=get_path('bg2ee_game_root',required=True)
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest().upper()
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def ref(b,o):return b[o:o+8].split(b'\0')[0].decode('ascii').upper()
m=load(GAME/'iee-assets/effects/manifest.json'); resources={r['resref']:r for r in m['resources']}
routes={r['owner']:r for r in load(ROOT/'effects/installations/lot31-latest-20261019-v1/palette-routes.json')}
carriers={r['resref']:r for r in m['runtime_bam_carriers']}
contexts=load(OUT/'contexts.json'); direct={}
for c in contexts.values():
    for u in c['uses']:
        if u['role']=='travel-animation' and not u.get('via'):direct.setdefault(u['projectile'],[]).append(c)
records=[]
for s in rows(ROOT/'projectiles/index/resources.csv'):
    n=s['resref']; stock=(ROOT/s['extracted_path']).read_bytes(); over=GAME/'override'/f'{n}.pro'
    live=over.read_bytes() if over.exists() else stock
    p=parse_pro(live); target=ref(live,0x104) if len(live)>=512 else ''
    src=ref(stock,0x104) if len(stock)>=512 else ''
    route=routes.get(n); r=resources.get(target)
    expected=bytearray(stock)
    if route:expected[0x104:0x10c]=route['runtime_bam'].encode().ljust(8,b'\0')
    cs=direct.get(n,[])
    records.append({'pro':n,'source_travel':src,'live_travel':target,'override':over.exists(),
      'catalogue':bool(r),'production_bam':r.get('production_bam',target) if r else '',
      'palette_job':r.get('palette_job','') if r else '',
      'lot31_route':bool(route),'route_matches':live==bytes(expected) if route else None,
      'palette_job_matches':r.get('palette_job')==route['palette_job'] if route and r else None,
      'encoding_matches':r.get('rgb_encoding')==route['encoding'] if route and r else None,
      'native_other_bytes_preserved':live[:0x104]+live[0x10c:]==stock[:0x104]+stock[0x10c:],
      'coverage':';'.join(sorted({c['coverage_level'] for c in cs})),
      'source_context_jobs':';'.join(sorted({x.get('job_id','') for c in cs for x in c['candidates'] if x.get('job_id')})),
      'geometry_cycle_declared':any(c['cycle']==p.get('travel_cycle') for c in r.get('cycles',[])) if r else False})
selection=load(ROOT/'projectiles/previews/selection-animee-50-20261028-v1/selection.json')
names={x['bam'] for x in selection}|{x['live_travel'] for x in records if x['catalogue']}
frame_issues=[];checked=0;total_bytes=0
for f in m['frames']:
    if f['resref'] not in names:continue
    path=GAME/'iee-assets/effects'/f['asset'];checked+=1
    if not path.is_file():frame_issues.append({'asset':f['asset'],'reason':'missing'});continue
    total_bytes+=path.stat().st_size
    if path.stat().st_size!=f['bytes'] or sha(path)!=f['sha256'].upper():frame_issues.append({'asset':f['asset'],'reason':'size-or-sha'})
print('Backings checked',checked,'bytes',total_bytes,flush=True)
carrier_issues=[];carrier_checked=0
for n in sorted(names):
    if n not in carriers:continue
    c=carriers[n];p=GAME/c['asset'];carrier_checked+=1
    if not p.is_file() or sha(p)!=c['sha256'].upper():carrier_issues.append(n)
selected=[]
for s in selection:
    pro_records=[x for x in records if x['source_travel']==s['bam']]
    selected.append({'number':s['n'],'bam':s['bam'],'catalogue':s['bam'] in resources,
      'source_owners':len(pro_records),'owners_with_live_catalogue':sum(x['catalogue'] for x in pro_records),
      'owners_lot31_verified':sum(x['lot31_route'] and x['route_matches'] and x['palette_job_matches'] and x['encoding_matches'] for x in pro_records),
      'contexts':sorted({c['coverage_level'] for c in contexts.values() if s['bam'] in c['bam_names']})})
summary={'scope':'243 stock PRO active overrides + selection50; static checks, no current ingame observation',
 'manifest_sha256':sha(GAME/'iee-assets/effects/manifest.json'),
 'registry_sha_matches':sha(GAME/'iee-assets/effects'/m['registry'])==m['registry_sha256'].upper(),
 'active_catalogue':len(resources),'stock_pro':len(records),
 'direct_travel_nonempty':sum(bool(x['live_travel']) for x in records),
 'direct_travel_catalogue':sum(x['catalogue'] for x in records),
 'direct_travel_no_catalogue':[x['pro'] for x in records if x['live_travel'] and not x['catalogue']],
 'lot31_routes':sum(x['lot31_route'] for x in records),
 'lot31_route_issues':[x for x in records if x['lot31_route'] and not all(x[k] for k in ('route_matches','palette_job_matches','encoding_matches'))],
 'nonroute_changed_pro':[x['pro'] for x in records if not x['lot31_route'] and not x['native_other_bytes_preserved']],
 'cycle_issues':[x for x in records if x['catalogue'] and not x['geometry_cycle_declared']],
 'selection_catalogue':sum(s['catalogue'] for s in selected),
 'backings_sha_checked':checked,'backings_bytes':total_bytes,'backing_issues':frame_issues,
 'carrier_sha_checked':carrier_checked,'carrier_issues':carrier_issues,
 'selection':selected,'remaining_limits':['No full per-owner ingame draw validation','Smoke/fragments/explosions engine routes unresolved','Default non-lot31 palette and blend require owner contract review']}
(OUT/'live-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (OUT/'live-pro-routes.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
print(json.dumps({k:v for k,v in summary.items() if k not in ('selection','remaining_limits')},indent=2))
