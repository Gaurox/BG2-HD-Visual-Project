"""Exact-resource reconstruction and immutable snapshots for animation cleanup."""
from pathlib import Path
import ast, copy, csv, json, shutil, struct, sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import animation_workflow as workflow
import area_pack_state as state
import run_animation_upscale_30fps_v2 as v
import split_animation_pack_by_area as splitter
TAG='animations-cleanup-points1-3-20261011-v1'
REPAIR=ROOT/'animations/packs-par-zone'/TAG
_json={};_hash={}

def rel(p):return p.resolve().relative_to(ROOT).as_posix()
def path(s):
    p=Path(s);return p if p.is_absolute() else ROOT/p
def load(p):
    p=Path(p)
    if p not in _json:_json[p]=json.loads(p.read_text(encoding='utf-8-sig'))
    return _json[p]
def digest(p):
    p=Path(p)
    if p not in _hash:_hash[p]=v.sha256_file(p)
    return _hash[p]
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as out:out.write((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
def payload(p):return {f.name:digest(f) for f in p.iterdir() if f.is_file() and f.name!='manifest.json'}
def fresh_payload(p):return {f.name:v.sha256_file(f) for f in p.iterdir() if f.is_file() and f.name!='manifest.json'}
def rows():return list(csv.DictReader((ROOT/'animations/index/animation_upscale_registry.csv').open(encoding='utf-8')))
def resources(leaf,ref=None):
    rr=load(leaf/'manifest.json')['resources']
    return [r for r in rr if ref is None or r['resref']==ref]
def source_assets(leaf,rr):return {a['name']:leaf/a['name'] for r in rr for a in r['assets']}
def verify_assets(leaf,rr):
    for r in rr:
        for a in r['assets']:
            p=leaf/a['name'];assert p.stat().st_size==a['bytes'] and digest(p)==a['sha256'].lower(),p
def registry_version(live):return struct.unpack_from('<I',(live/v.REGISTRY_NAME).read_bytes(),len(v.REGISTRY_MAGIC))[0]
def same_live(leaf,rr,area):
    live=state.game_areas_dir()/area;version=registry_version(live);registry=(live/v.REGISTRY_NAME).read_bytes()
    return all(v.resource_binary_v2(r,version) in registry and all((live/a['name']).exists() and
        digest(live/a['name'])==a['sha256'].lower() for a in r['assets']) for r in rr)
def qa_leaf(ref,area):
    sel=load(ROOT/'animations/index/selections'/(ref+'.json'))
    return path(next(a['path'] for a in sel['source_pack']['areas'] if a['area']==area))
def lock_leaves(area,entry):
    build=entry['build'];out=[]
    if 'leaf' in build:return [path(build['leaf'])]
    for spec in build.get('merged_from',[]):
        if spec.startswith('{'):
            metadata=ast.literal_eval(spec)
            if metadata['area_id']==area:out.append(path(metadata['source_split_root'])/area)
        else:out.append(path(spec.split('::')[0]))
    return out
def reconstruct(area):
    live=state.game_areas_dir()/area;before=payload(live);version=registry_version(live)
    registry=(live/v.REGISTRY_NAME).read_bytes();entry=state.load_lock()['areas'][area]
    keys=state.zone_resource_names(live);leaves=lock_leaves(area,entry)
    for ref in {state.base_resref(k) for k in keys}:
        try:leaves.append(qa_leaf(ref,area))
        except (FileNotFoundError,StopIteration,KeyError):pass
    candidates=[(r,leaf) for leaf in dict.fromkeys(leaves) if (leaf/'manifest.json').is_file() for r in resources(leaf)]
    found=[];sources={}
    for key in sorted(keys):
        match=None
        for r,leaf in candidates:
            if state.resource_key(r['assets'][0]['name'])!=key:continue
            if not all(before.get(a['name'])==a['sha256'].lower() for a in r['assets']):continue
            if v.resource_binary_v2(r,version) not in registry:continue
            verify_assets(leaf,[r]);match=(r,leaf);break
        assert match,area+': cannot reconstruct exact installed resource '+key
        r,leaf=match;found.append(copy.deepcopy(r));sources.update(source_assets(leaf,[r]))
    assert v.registry_v2_from_resources(found,version)==registry,area+': contract reconstruction differs'
    assert {v.REGISTRY_NAME,*sources}==set(before),area+': unexplained installed files'
    return found,sources,version,before
def write_leaf(leaf,area,rr,sources,version,provenance):
    assert not leaf.exists(),leaf
    rr=sorted(copy.deepcopy(rr),key=v.resource_sort_key);raw=sum(a['bytes'] for r in rr for a in r['assets'])
    assert raw<=v.MAX_RAW_BYTES
    leaf.mkdir(parents=True);registry=v.registry_v2_from_resources(rr,version);(leaf/v.REGISTRY_NAME).write_bytes(registry)
    for r in rr:
        for a in r['assets']:
            shutil.copyfile(sources[a['name']],leaf/a['name'])
    write(leaf/'manifest.json',dict(schema=v.PACK_SCHEMA,status='completed',created_utc=v.utc_now(),scale=4,
        registry_version=version,runtime_contract=dict(feature='TimedTimeline',clock='QPC-pause-aware',registry_version=version),
        registry=v.REGISTRY_NAME,registry_sha256=digest(leaf/v.REGISTRY_NAME),registry_bytes=len(registry),
        area_id=area,resource_count=len(rr),frame_count=sum(r['frame_count'] for r in rr),raw_bytes=raw,
        runtime_budget_enforced=True,base_assets=[],new_assets=[],resources=rr,
        timed_resources=sorted({r['resref'] for r in rr if r.get('playback_mode')=='TimedTimeline'}),provenance=provenance))
    v.validate_v2_pack(leaf)
def write_index(root,areas,purpose):
    entries=[]
    for area in sorted(areas):
        m=load(root/area/'manifest.json');entries.append(dict(area_id=area,directory=area,resrefs=sorted({r['resref'] for r in m['resources']}),
            resource_count=m['resource_count'],frame_count=m['frame_count'],raw_bytes=m['raw_bytes'],
            registry_sha256=m['registry_sha256'],manifest_sha256=digest(root/area/'manifest.json'),over_runtime_budget=False))
    write(root/'manifest.json',dict(schema=splitter.INDEX_SCHEMA,status='completed',created_utc=v.utc_now(),purpose=purpose,
        areas=entries,area_count=len(entries),runtime_budget_bytes=v.MAX_RAW_BYTES,
        largest_area_raw_bytes=max(x['raw_bytes'] for x in entries),total_raw_bytes=sum(x['raw_bytes'] for x in entries),
        areas_over_budget=[],resrefs_without_area=[]))
