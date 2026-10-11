"""Package the selected FIRE_3 fade4 preview exactly; AR0202 trial only."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import binary_dilation

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import split_animation_pack_by_area as splitter
from area_pack_state import game_areas_dir

TAG='fire3-aura-fade4-30fps-20261011-v1'
SOURCE=ROOT/'animations/packs-par-zone/fire3-apo8-30fps-ar0202-zero-20261011-v1/AR0202'
PREVIEW=ROOT/'pipeline/recipes/fire3-aura-preview-20261011-v1'
RUN=ROOT/'animations/ressources/FIRE_3/runs'/TAG
PACK=ROOT/'animations/packs-par-zone'/TAG

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def payload(path):
    return {p.name:sha(p) for p in path.iterdir() if p.is_file()
            and (p.suffix=='.rgba' or p.name==v.REGISTRY_NAME)}

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2)
        stream.write('\n')

def main():
    assert not RUN.exists() and not PACK.exists(), 'Immutable output exists'
    live=game_areas_dir()/'AR0202'
    before=payload(live)
    assert before==payload(SOURCE), 'Installed AR0202 drifted from preview source'
    source_manifest,original=v.validate_v2_pack(SOURCE)
    resources=copy.deepcopy(original)
    target=next(r for r in resources if r['resref']=='FIRE_3')
    old=next(r for r in original if r['resref']=='FIRE_3')
    frames=old['frames']
    left=min(-f['centre_x1'][0]*4 for f in frames)
    top=min(-f['centre_x1'][1]*4 for f in frames)
    right=max((f['logical_size_x1'][0]-f['centre_x1'][0])*4 for f in frames)
    bottom=max((f['logical_size_x1'][1]-f['centre_x1'][1])*4 for f in frames)
    original_aligned=[];selected_aligned=[];sources={}
    for resource in resources:
        for asset in resource['assets']:
            sources[asset['name']]=SOURCE/asset['name']
    for f in frames:
        w,h=f['physical_size_x4'];x=-f['centre_x1'][0]*4-left;y=-f['centre_x1'][1]*4-top
        selected=PREVIEW/'variant-1'/f['asset']
        raw=selected.read_bytes()
        assert len(raw)==f['bytes'], 'Selected preview geometry changed'
        pair=[]
        for blob in [(SOURCE/f['asset']).read_bytes(),raw]:
            a=np.frombuffer(blob,np.uint8).reshape(h,w,4)
            canvas=np.zeros((bottom-top,right-left,4),np.uint8)
            canvas[y:y+h,x:x+w]=a
            assert not np.any(a[:,:,:3][a[:,:,3]==0])
            pair.append(canvas)
        original_aligned.append(pair[0]);selected_aligned.append(pair[1])
        sources[f['asset']]=selected
    seed=np.max(np.stack([a[:,:,:3].astype(np.float32).mean(axis=2) for a in original_aligned]),axis=0)>=140
    core=binary_dilation(seed,iterations=2)
    assert all(np.array_equal(a[core],b[core]) for a,b in zip(original_aligned,selected_aligned))
    hashes=[hashlib.sha256(a.tobytes()).hexdigest() for a in selected_aligned]
    assert len(set(hashes))==28, 'Duplicate selected frame'
    timeline=target['cycles'][0]['timeline_frame_indices']
    assert len(timeline)==28 and len(set(timeline))==28
    assert all(not np.array_equal(selected_aligned[i],selected_aligned[timeline[(phase+1)%28]])
               for phase,i in enumerate(timeline))
    by_name={a['name']:a for a in target['assets']}
    for f in target['frames']:
        f['sha256']=sha(sources[f['asset']])
        by_name[f['asset']]['sha256']=f['sha256']
    assert all({k:f[k] for k in ('frame','physical_size_x4','logical_size_x1','centre_x1','asset','bytes')}==
               {k:g[k] for k in ('frame','physical_size_x4','logical_size_x1','centre_x1','asset','bytes')}
               for f,g in zip(target['frames'],old['frames']))
    assert target['cycles']==old['cycles'] and target['native_fps']==old['native_fps']
    assert target['target_fps']=={'numerator':30,'denominator':1}
    splitter.write_area_pack(RUN/'03_runtime_pack',SOURCE,source_manifest,resources,sources,'AR0202')
    splitter.split(RUN/'03_runtime_pack',PACK,
                   ROOT/'pipeline/recipes/fire3-apo8-30fps-20261011-v1/occurrences-ar0202.csv',False)
    after=payload(PACK/'AR0202')
    for name,digest in before.items():
        if name!=v.REGISTRY_NAME and not name.startswith('AAX4-FIRE_3-'):
            assert after[name]==digest, 'Sibling changed: '+name
    assert before[v.REGISTRY_NAME]==after[v.REGISTRY_NAME], 'Temporal registry changed'
    write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',
        created_utc=v.utc_now(),resrefs=['FIRE_3'],source_pack=SOURCE.relative_to(ROOT).as_posix(),
        source_pack_manifest_sha256=sha(SOURCE/'manifest.json'),runtime_pack='03_runtime_pack',
        runtime_pack_manifest_sha256=sha(RUN/'03_runtime_pack/manifest.json'),
        output_split_root=PACK.relative_to(ROOT).as_posix(),output_manifest_sha256=sha(PACK/'manifest.json'),
        visual_treatment=dict(kind='aura-only-inner-fade',inner_feather_x4=4,gaussian_sigma_x4=0,
            selected_preview=PREVIEW.relative_to(ROOT).as_posix()+'/variant-1',
            protected_core='loop-wide meanRGB>=140; dilation2; outer blend4; exact bright core',
            rgb_policy='existing premultiplied RGBA multiplied by fade once',geometry='native unchanged'),
        temporal_contract=dict(fps=30,phases=28,distinct_frames=28,duration_seconds=14/15,registry='unchanged'),
        qa_status='selected-user-preview; pending-explicit-user-ingame-approval'))
    write(HERE/'checks.json',dict(passed=True,selected_variant='Fondu seul 4 px',selected_preview_bytes_exact=True,
        distinct_aligned_frames=28,bright_core_byte_identical=True,geometry_unchanged=True,
        registry_byte_identical=True,siblings_unchanged=True,fps=30,phases=28,duration_seconds=14/15))
    write(HERE/'baseline.json',dict(area='AR0202',before=before,after=after))
    print('Prepared exact fade4 preview: 28 distinct frames; core, native geometry, 30fps registry and siblings preserved')

if __name__=='__main__':
    main()
