"""Complete immutable selection input; no domain asset or game mutation."""
import hashlib, json, os, sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'.tmp/maps-release-finalization-20261012-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().upper()
def ref(p):return p.relative_to(ROOT).as_posix()

game=get_path('bg2ee_game_root',required=True)/'override'
plan=read(OUT/'probe.json');by={v['area']:v for v in plan['variants']}
old=read(ROOT/'releases/BG2-HD-Upscale/manifests/content.json')
registry_path=read(ROOT/'pipeline/water/route2-registry-current.json')['registry']['path']
registry=read(ROOT/registry_path)
required={}
for e in registry['entries']:
    area=e['wed']['resref'];o=e['overlay']
    required[(area,o['tis_resref']+'.TIS')]=(o['tis_bytes'],o['tis_sha256'].upper())
    for p in o['pages']:required[(area,p['resref']+'.PVRZ')]=(p['bytes'],p['sha256'].upper())
protected=read(ROOT/'maps/cleanup-candidates-20261012-v1.json')['protected_roots']
index=defaultdict(list);wanted={n for _,n in required}
for item in protected:
    for base,dirs,files in os.walk(ROOT/item['path']):
        dirs[:]=[d for d in dirs if d not in ('runtime-src','runtime-build','.git')]
        for n in files:
            if n.upper() in wanted:index[n.upper()].append(Path(base)/n)
errors=[];cache={}
for (area,n),(size,h) in required.items():
    v=by[area];existing=next((x for x in v['files'] if x['name']==n),None)
    if existing:
        if existing['bytes']!=size or existing['sha256']!=h:errors.append('registry mismatch '+area+'/'+n)
        continue
    live=game/n
    if not live.is_file() or live.stat().st_size!=size or sha(live)!=h:errors.append('live registry mismatch '+area+'/'+n);continue
    candidates=sorted(index[n],key=lambda p:(0 if 'override-candidate' in p.parts else 1,len(p.parts),p.as_posix()))
    match=None
    for p in candidates:
        st=p.stat()
        if st.st_size!=size:continue
        key=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
        if key not in cache:cache[key]=sha(p)
        if cache[key]==h:match=p;break
    if not match:errors.append('missing source '+area+'/'+n);continue
    v['files'].append(dict(name=n,bytes=size,sha256=h,source=ref(match)))
for e in old['entries']:
    if e['kind']=='map' and e['source'].upper().endswith('.WED') and not by[e['area']]['water']:
        p=ROOT/e['source'];assert sha(p)==e['sha256']==sha(game/p.name)
        by[e['area']]['files'].append(dict(name=p.name,bytes=p.stat().st_size,sha256=e['sha256'],source=e['source'],animation_owned=True))
ar3003_receipt=ROOT/'backups/maps/AR3003-20260906T213541736829Z-783bd7c5/install-backup.json'
r=read(ar3003_receipt);installed={e['name']:e['installed'] for e in r['files']}
for f in by['AR3003']['files']:
    if not f['source']:
        p=ROOT/'output/map-patch-compositor/ar3003-four-portals-20260906/05_build/x4-four-portals-patched-test'/f['name']
        assert sha(p)==f['sha256']==installed[f['name']]['sha256']
        f['source']=ref(p)
        f['binding_receipt']=ref(ar3003_receipt)
for v in plan['variants']:
    v['files'].sort(key=lambda f:f['name'])
    existing={Path(e['source']).name.upper():e for e in old['entries'] if e['kind']=='map' and e['area']==v['area']}
    v['changed']=[x['name'] for x in v['files'] if x['name'].upper() not in existing or existing[x['name'].upper()]['sha256']!=x['sha256']]
    v['dropped']=sorted(set(existing)-{f['name'].upper() for f in v['files']})
    assert not v['dropped']
    for f in v['files']:
        if not f['source']:errors.append('unresolved '+v['area']+'/'+f['name'])
    for e in (e for e in registry['entries'] if e['wed']['resref']==v['area']):
        files={f['name']:f for f in v['files']}
        for n,h in [(e['wed']['resref']+'.WED',e['wed']['sha256']),(e['base_tis']['resref']+'.TIS',e['base_tis']['sha256'])]:
            if files[n]['sha256']!=h.upper():errors.append('runtime guard mismatch '+n)
        for p in e['base_tis'].get('pages',[]):
            if files[p['resref']+'.PVRZ']['sha256']!=p['sha256'].upper():errors.append('runtime base guard mismatch '+p['resref'])
bundle=ROOT/'releases/BG2-HD-Upscale/bg2hd/renderer/InfinityEngine-Enhancer.dll'
binary=bundle.read_bytes()
markers=[]
for e in registry['entries']:
    if e['overlay']['tis_resref'].encode('ascii')+b'\0' not in binary:markers.append(e['overlay']['tis_resref'])
if markers:errors.append('DLL lacks registry overlays '+str(markers))
plan['missing']=errors
plan['runtime']={'registry':registry_path,'registry_sha256':sha(ROOT/registry_path),'entries':len(registry['entries']),'dll_sha256':sha(bundle),'overlay_resrefs_in_dll':not markers,'owned_ini_keys':{'EnableWaterEffect':'true','EnableWaterOverlayRoute2':'true','WaterOverlayStrength':'1.00'}}
plan['changed']=[{'area':v['area'],'changed':len(v['changed'])} for v in plan['variants'] if v['changed']]
with (OUT/'complete-plan.json').open('w',encoding='utf-8') as f:json.dump(plan,f,indent=2);f.write('\n')
print(json.dumps({'variants':len(by),'changed_variants':len(plan['changed']),'files':sum(len(v['files']) for v in plan['variants']),'runtime':plan['runtime'],'errors':errors},indent=2))
if errors:raise SystemExit(1)
