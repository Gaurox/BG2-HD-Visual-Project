"""Propagate the accepted FIRE_3 bytes; preserve each installed area's siblings."""
from pathlib import Path
import copy, hashlib, json, shutil, struct, sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import area_pack_state as state
import split_animation_pack_by_area as split

TAG='fire3-aura-fade4-all-areas-20261011-v1'
PACK=ROOT/'animations/packs-par-zone'/TAG
RUN=ROOT/'animations/ressources/FIRE_3/runs'/TAG
SOURCE=ROOT/'animations/packs-par-zone/fire3-aura-fade4-30fps-20261011-v1/AR0202'
AREAS=['AR0331','AR0500','AR0526','AR0906','AR3001','AR5000','OH4200','OH4210','OH4220']

def rel(p):
    return p.resolve().relative_to(ROOT).as_posix()

def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as out:
        json.dump(data,out,ensure_ascii=False,indent=2);out.write('\n')

def payload(p):
    return {f.name:v.sha256_file(f) for f in p.iterdir() if f.is_file() and f.name!='manifest.json'}

def installed_resources(area,entry):
    live=state.game_areas_dir()/area
    before=payload(live)
    assert state.zone_signatures(live)==entry['resources'], area+': installation differs from lock'
    version=struct.unpack_from('<I',(live/v.REGISTRY_NAME).read_bytes(),len(v.REGISTRY_MAGIC))[0]
    registry=(live/v.REGISTRY_NAME).read_bytes()
    candidates=[]
    for name in state.recipe_sources(entry):
        leaf=Path(name)
        if not leaf.is_absolute():leaf=ROOT/leaf
        _,resources=v.validate_v2_pack(leaf)
        candidates.extend((r,leaf) for r in resources)
    chosen=[];sources={}
    for key,signature in sorted(entry['resources'].items()):
        found=None
        for resource,leaf in candidates:
            assets=resource['assets']
            if state.resource_key(assets[0]['name'])!=key:continue
            hashes=[(a['name'],a['sha256'].lower()) for a in assets]
            if state.group_signature(hashes)!=signature['sig']:continue
            if not all(before.get(name)==digest for name,digest in hashes):continue
            if v.resource_binary_v2(resource,version) not in registry:continue
            found=(resource,leaf);break
        assert found, area+': no exact installed source for '+key
        resource,leaf=found
        chosen.append(copy.deepcopy(resource))
        for asset in resource['assets']:sources[asset['name']]=leaf/asset['name']
    assert v.registry_v2_from_resources(chosen,version)==registry, area+': reconstructed contract differs'
    assert set(before)=={v.REGISTRY_NAME,*sources}, area+': unaccounted installed files'
    return chosen,sources,before,version

def main():
    assert not PACK.exists() and not RUN.exists() and not (HERE/'baseline.json').exists()
    _,resources=v.validate_v2_pack(SOURCE)
    selected=next(r for r in resources if r['resref']=='FIRE_3')
    assert selected['frame_count']==28 and selected['target_fps']==dict(numerator=30,denominator=1)
    timeline=selected['cycles'][0]['timeline_frame_indices']
    assert len(set(timeline))==len(timeline)==28
    # Compare all frames after alignment to their native centres, including loop seam.
    import numpy as np
    frames=selected['frames']
    left=min(-f['centre_x1'][0]*4 for f in frames);top=min(-f['centre_x1'][1]*4 for f in frames)
    right=max((f['logical_size_x1'][0]-f['centre_x1'][0])*4 for f in frames)
    bottom=max((f['logical_size_x1'][1]-f['centre_x1'][1])*4 for f in frames)
    hashes=[]
    for f in frames:
        width,height=f['physical_size_x4']
        a=np.frombuffer((SOURCE/f['asset']).read_bytes(),np.uint8).reshape(height,width,4)
        assert not np.any(a[:,:,:3][a[:,:,3]==0])
        canvas=np.zeros((bottom-top,right-left,4),np.uint8)
        x=-f['centre_x1'][0]*4-left;y=-f['centre_x1'][1]*4-top
        canvas[y:y+height,x:x+width]=a
        hashes.append(hashlib.sha256(canvas.tobytes()).hexdigest())
    assert len(set(hashes))==28
    lock=state.load_lock();jobs={}
    for area in AREAS:
        jobs[area]=installed_resources(area,lock['areas'][area])
    baseline={};entries=[]
    for area,(old,sources,before,version) in jobs.items():
        target=next(r for r in old if r['resref']=='FIRE_3')
        assert len([r for r in old if r['resref']=='FIRE_3'])==1
        assert v.resource_position(target) is None and v.resource_variant_index(target)==0
        assert target['cycles'][0]['native_frame_indices']==selected['cycles'][0]['native_frame_indices']
        for index in target['cycles'][0]['native_frame_indices']:
            a,b=target['frames'][index],selected['frames'][index]
            assert all(a[k]==b[k] for k in ['frame','physical_size_x4','logical_size_x1','centre_x1']),area
        output_resources=[r for r in old if r['resref']!='FIRE_3']+[copy.deepcopy(selected)]
        output_resources.sort(key=v.resource_sort_key)
        leaf=PACK/area;leaf.mkdir(parents=True)
        registry=v.registry_v2_from_resources(output_resources,version)
        (leaf/v.REGISTRY_NAME).write_bytes(registry)
        for resource in output_resources:
            for asset in resource['assets']:
                src=SOURCE/asset['name'] if resource['resref']=='FIRE_3' else sources[asset['name']]
                shutil.copyfile(src,leaf/asset['name'])
        raw=sum(a['bytes'] for r in output_resources for a in r['assets']);assert raw<=v.MAX_RAW_BYTES
        manifest=dict(schema=v.PACK_SCHEMA,status='completed',created_utc=v.utc_now(),scale=4,registry_version=version,
            runtime_contract=dict(feature='TimedTimeline',clock='QPC-pause-aware',registry_version=version),
            registry=v.REGISTRY_NAME,registry_sha256=v.sha256_file(leaf/v.REGISTRY_NAME),registry_bytes=len(registry),
            resource_count=len(output_resources),frame_count=sum(r['frame_count'] for r in output_resources),
            timed_resources=sorted({r['resref'] for r in output_resources if r.get('playback_mode')=='TimedTimeline'}),
            area_id=area,raw_bytes=raw,runtime_budget_enforced=True,base_assets=[],new_assets=[],resources=output_resources,
            replacement=dict(resref='FIRE_3',source=rel(SOURCE),source_manifest_sha256=v.sha256_file(SOURCE/'manifest.json'),
                previous_registry_sha256=before[v.REGISTRY_NAME],siblings='exact installed bytes and binary entries preserved'))
        write(leaf/'manifest.json',manifest);v.validate_v2_pack(leaf)
        after=payload(leaf)
        before_siblings={n:h for n,h in before.items() if n!=v.REGISTRY_NAME and not n.startswith('AAX4-FIRE_3-')}
        after_siblings={n:h for n,h in after.items() if n!=v.REGISTRY_NAME and not n.startswith('AAX4-FIRE_3-')}
        assert before_siblings==after_siblings,area
        assert all(v.resource_binary_v2(r,version) in registry for r in old if r['resref']!='FIRE_3'),area
        baseline[area]=dict(before=before,after=after,siblings_byte_identical=True,sibling_runtime_entries_identical=True,
            registry_version_preserved=version,original_lock=lock['areas'][area])
        entries.append(dict(area_id=area,directory=area,resrefs=sorted({r['resref'] for r in output_resources}),
            resource_count=len(output_resources),frame_count=manifest['frame_count'],raw_bytes=raw,
            registry_sha256=manifest['registry_sha256'],manifest_sha256=v.sha256_file(leaf/'manifest.json'),over_runtime_budget=False))
        print('PREPARED',area,'siblings exact; FIRE_3 28 distinct phases',flush=True)
    write(PACK/'manifest.json',dict(schema=split.INDEX_SCHEMA,status='completed',created_utc=v.utc_now(),
        runtime_budget_bytes=v.MAX_RAW_BYTES,area_count=len(entries),areas=entries,
        largest_area_raw_bytes=max(e['raw_bytes'] for e in entries),total_raw_bytes=sum(e['raw_bytes'] for e in entries),
        areas_over_budget=[],resrefs_without_area=[]))
    source_run=ROOT/'animations/ressources/FIRE_3/runs/fire3-aura-fade4-30fps-20261011-v1'
    write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-propagation-v1',status='completed',created_utc=v.utc_now(),
        resrefs=['FIRE_3'],source_run=rel(source_run),source_run_manifest_sha256=v.sha256_file(source_run/'manifest.json'),
        output_split_root=rel(PACK),output_manifest_sha256=v.sha256_file(PACK/'manifest.json'),areas=AREAS,
        fps=30,distinct_phases=28,duration_seconds=14/15,inner_fade_x4=4,gaussian_sigma_x4=0,
        qa_reference='animations/index/area-qa-decisions/FIRE_3/2026-10-11-accepted-fire3-ar0202-fade4-30fps-v1.json',
        qa_scope='AR0202 accepted; byte-identical asset propagated; no new ingame visits inferred',release_status='not-selected'))
    write(HERE/'baseline.json',dict(areas=baseline,reference_ar0202_payload=payload(SOURCE),
        reference_assets=v.sha256_file(SOURCE/'manifest.json'),distinct_aligned_frame_count=28,
        cycle_duration_seconds=14/15,selection_qa_unchanged=True,release_unchanged=True))

if __name__=='__main__':main()
