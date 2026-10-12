"""Read-only reconciliation: accepted domain sources, installed witness, legacy package."""
import csv, hashlib, json, os, struct, sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path
OUT = ROOT / '.tmp/maps-release-finalization-20261012-v1'
OUT.mkdir(exist_ok=True)

def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.file_digest(p.open('rb'), 'sha256').hexdigest().upper()
def names(tis):
    data=tis.read_bytes(); n,size,off,dim=struct.unpack_from('<4I',data,8)
    assert data[:8]==b'TIS V1  ' and size==12 and dim==256, str(tis)
    prefix=tis.stem[0]+tis.stem[2:]
    pages=sorted({struct.unpack_from('<I',data,off+i*size)[0] for i in range(n)}-{0xffffffff})
    return [tis.name]+[f'{prefix}{p:02d}.PVRZ' for p in pages]
def overlays(wed):
    data=wed.read_bytes(); count=struct.unpack_from('<I',data,8)[0]; off=struct.unpack_from('<I',data,16)[0]
    return [data[off+i*24+4:off+i*24+12].split(b'\0')[0].decode('ascii') for i in range(count)]

game=get_path('bg2ee_game_root',required=True)/'override'
old=read(ROOT/'releases/BG2-HD-Upscale/manifests/content.json')
by=defaultdict(list)
for e in old['entries']:
    if e['kind']=='map': by[e['area']].append(e)
tracking=read(ROOT/'pipeline/water/ingame-map-tracking-v1.json')
water={m['wed']:m for m in tracking['maps'] if m['qa_state']=='validated-ingame'}
protected=read(ROOT/'maps/cleanup-candidates-20261012-v1.json')['protected_roots']
file_index=defaultdict(list)
for item in protected:
    for base,dirs,files in os.walk(ROOT/item['path']):
        dirs[:]=[d for d in dirs if d not in ('runtime-src','runtime-build','.git')]
        for name in files:
            p=Path(base)/name
            if p.suffix.upper() in ('.PVRZ','.TIS','.WED'):
                file_index[(name.upper(),p.stat().st_size)].append(p)
cache={}; missing=[]; variants=[];changed=[]
for i,(area,entries) in enumerate(sorted(by.items()),1):
    tis=game/(area+'.TIS')
    if not tis.exists(): missing.append({'area':area,'missing_tis':str(tis)});continue
    wanted=names(tis)
    if area in water:
        wed=game/(area+'.WED');wanted.append(wed.name)
        for overlay in overlays(wed)[1:]:
            if overlay and (game/(overlay+'.TIS')).exists():
                wanted+=names(game/(overlay+'.TIS'))
    existing={Path(e['source']).name.upper():e for e in entries}
    selected=[]
    for name in sorted(set(wanted)):
        p=game/name
        h=sha(p); candidates=file_index.get((name.upper(),p.stat().st_size),[])
        # Current release source first, then canonical override candidates; witness is never copied.
        candidates=sorted(candidates,key=lambda q:(0 if name.upper() in existing and q==ROOT/existing[name.upper()]['source'] else 1, 0 if 'override-candidate' in q.parts else 1, len(q.parts), q.as_posix()))
        match=None
        for q in candidates:
            st=q.stat();key=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
            if key not in cache:cache[key]=sha(q)
            if cache[key]==h:match=q;break
        if match is None:
            # Sources already packaged but outside the cleanup-root inventory (AR0516 WED).
            e=existing.get(name.upper())
            if e and (ROOT/e['source']).is_file() and sha(ROOT/e['source'])==h:match=ROOT/e['source']
        if match is None:missing.append({'area':area,'name':name,'sha256':h,'candidate_count':len(candidates)})
        selected.append({'name':name,'bytes':p.stat().st_size,'sha256':h,'source':match.relative_to(ROOT).as_posix() if match else None})
    delta=[x['name'] for x in selected if x['name'].upper() not in existing or existing[x['name'].upper()]['sha256'].upper()!=x['sha256']]
    dropped=sorted(set(existing)-{x['name'].upper() for x in selected})
    v={'area':area,'component_id':entries[0]['component_id'],'catalog_source_path':next(e['source_run'] for e in entries if e['source'].upper().endswith('.TIS')),'files':selected,'changed':delta,'dropped':dropped,'water':area in water,'qa_evidence_ids':water.get(area,{}).get('qa_evidence_ids',[])}
    variants.append(v)
    if delta or dropped:changed.append({'area':area,'changed':len(delta),'dropped':dropped,'water':area in water})
    if i%50==0:print('Reconciled',i,'/',len(by),flush=True)
result={'variants':variants,'missing':missing,'changed':changed,'game_reference':'config://bg2ee_game_root/override','hashes_computed':len(cache)}
(OUT/'probe.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'variants':len(variants),'water':len(water),'changed':changed,'missing':missing,'hashes_computed':len(cache)},indent=2),flush=True)
