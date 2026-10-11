"""Approved feather20/sigma4; restore native canvas; install only AR0411."""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import animation_workflow as workflow
from workspace_paths import get_path

TAG='dstdvl1a-misty-contour-native-geometry-20261011-v2'
RECIPE=Path(__file__).resolve().parent
PROTO=ROOT/'animations/ressources/DSTDVL1A/runs/dstdvl1a-misty-contour-20261011-v1'
RUN=ROOT/'animations/ressources/DSTDVL1A/runs'/TAG
PACK=ROOT/'animations/packs-par-zone'/TAG
BASE=ROOT/'animations/packs-par-zone/ar0411-bubbles2-dstdvl1abc-plus-planar-sphere-20260911/AR0411'
EXTRA=ROOT/'animations/packs-par-zone/am0411rn-magic-sphere-apo8-x4-30fps-spline-fit1-feather4-20260911/AR0411'
LIVE=get_path('bg2ee_game_root')/'iee-assets/areas/AR0411'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return p.relative_to(ROOT).as_posix()
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def payload(p):
    return {f.name:sha(f) for f in p.iterdir() if f.is_file() and (f.suffix=='.rgba' or f.name==v.REGISTRY_NAME)}
def pack(path,resources,source,area=None):
    path.mkdir(parents=True)
    binary=v.registry_v2_from_resources(resources,3)
    (path/v.REGISTRY_NAME).write_bytes(binary)
    for resource in resources:
        for asset in resource['assets']:
            shutil.copy2(source(resource)/asset['name'],path/asset['name'])
    manifest=dict(schema=v.PACK_SCHEMA,status='completed',created_utc=v.utc_now(),scale=4,registry_version=3,
        runtime_contract=dict(feature='TimedTimeline',clock='QPC-pause-aware',registry_version=3),registry=v.REGISTRY_NAME,
        registry_sha256=sha(path/v.REGISTRY_NAME),registry_bytes=len(binary),resource_count=len(resources),
        frame_count=sum(r['frame_count'] for r in resources),timed_resources=[r['resref'] for r in resources if r['playback_mode']=='TimedTimeline'],
        raw_bytes=sum(a['bytes'] for r in resources for a in r['assets']),runtime_budget_enforced=True,base_assets=[],new_assets=[],resources=resources)
    if area: manifest['area_id']=area
    write(path/'manifest.json',manifest)
    v.validate_v2_pack(path)

def prepare():
    assert not RUN.exists() and not PACK.exists(),'Immutable output exists'
    _,old=v.validate_v2_pack(BASE)
    _,prototypes=v.validate_v2_pack(PROTO/'03_runtime_pack')
    original=next(r for r in old if r['resref']=='DSTDVL1A')
    proto=next(r for r in prototypes if r['resref']=='DSTDVL1A')
    assert original['cycles']==proto['cycles']
    target=copy.deepcopy(original)
    stage=RUN/'native-canvas-frames';stage.mkdir(parents=True)
    assets={a['name']:a for a in target['assets']}
    total=0;discarded=0
    for frame,pf in zip(target['frames'],proto['frames']):
        assert sha(LIVE/frame['asset'])==frame['sha256'],'Target changed since preview'
        w,h=pf['physical_size_x4']
        raw=np.frombuffer((PROTO/'03_runtime_pack'/pf['asset']).read_bytes(),np.uint8).reshape(h,w,4)
        if pf['physical_size_x4']!=frame['physical_size_x4']:
            assert [w-48,h-48]==frame['physical_size_x4']
            rgba=raw[24:-24,24:-24].copy()
            total+=int(raw[:,:,:3].sum());discarded+=int(raw[:,:,:3].sum())-int(rgba[:,:,:3].sum())
        else: rgba=raw.copy()
        assert np.all(rgba[:,:,:3]<=rgba[:,:,3:4])
        path=stage/frame['asset'];path.write_bytes(rgba.tobytes())
        assert path.stat().st_size==frame['bytes']
        frame['sha256']=sha(path);assets[frame['asset']]['sha256']=frame['sha256']
    assert v.resource_binary_v2(target,3)==v.resource_binary_v2(original,3),'Geometry/timing changed'
    pack(RUN/'03_runtime_pack',[target],lambda r:stage)
    resources=copy.deepcopy(old)+[copy.deepcopy(next(r for r in v.load_json(EXTRA/'manifest.json')['resources'] if r['resref']=='AM0411RN'))]
    resources.sort(key=v.resource_sort_key)
    assert v.registry_v2_from_resources(resources,3)==(LIVE/v.REGISTRY_NAME).read_bytes(),'Unknown installed registry'
    before=payload(LIVE)
    for resource in resources:
        names={a['name']:a for a in resource['assets']}
        for frame in resource['frames']:
            assert (LIVE/frame['asset']).stat().st_size==frame['bytes']
            frame['sha256']=sha(LIVE/frame['asset']);names[frame['asset']]['sha256']=frame['sha256']
    resources=[target if r['resref']=='DSTDVL1A' else r for r in resources]
    pack(PACK/'AR0411',resources,lambda r:stage if r['resref']=='DSTDVL1A' else LIVE,'AR0411')
    after=payload(PACK/'AR0411')
    assert before.keys()==after.keys()
    changed=[n for n in before if before[n]!=after[n]]
    assert len(changed)==46 and all(n.startswith('AAX4-DSTDVL1A-') for n in changed)
    write(PACK/'manifest.json',dict(schema='bg2-upscale-area-animation-pack-index-v1',status='completed',created_utc=v.utc_now(),areas=[dict(area_id='AR0411',directory='AR0411',manifest_sha256=sha(PACK/'AR0411/manifest.json'),registry_sha256=sha(PACK/'AR0411'/v.REGISTRY_NAME))]))
    write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),resrefs=['DSTDVL1A'],
        source_run=rel(PROTO),source_run_manifest_sha256=sha(PROTO/'manifest.json'),
        runtime_pack='03_runtime_pack',runtime_pack_manifest_sha256=sha(RUN/'03_runtime_pack/manifest.json'),
        output_split_root=rel(PACK),output_manifest_sha256=sha(PACK/'manifest.json'),
        runtime_contract=dict(inner_feather_x4=20,gaussian_sigma_x4=4,frame_count=139,timeline_phases=214,fps=30,
            geometry='exact installed dimensions/centres; crop only prototype external padding24x4',
            crop_discarded_RGB_energy_fraction=discarded/total,
            preservation='approved prototype pixels byte-identical inside each native canvas; core and cadence preserved; registry and siblings byte-identical'),
        qa_status='installed candidate pending user ingame QA'))
    write(RECIPE/'baseline.json',dict(area='AR0411',before=before,after=after,changed_files=changed))
    a,m,p=workflow._artifact(ROOT,RUN)
    workflow._verify_embedded_pack(ROOT,m,p)
    workflow._verify_pack_binding(ROOT,m,p,workflow._source_pack(ROOT,PACK,'DSTDVL1A',['AR0411']),'DSTDVL1A')
    write(RECIPE/'checks.json',dict(passed=True,changed_frames=46,native_geometry_and_timeline_verbatim=True,registry_and_siblings_byte_identical=True,
        approved_pixels_preserved=True,crop_discarded_RGB_energy_fraction=discarded/total,pack_binding_verified=True))
    print('Ready: 46 DSTDVL1A frames changed; native geometry, timeline, registry and all siblings unchanged')

def install():
    result=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader|BGMain' }).Count"],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='0','Game or InfinityLoader running'
    receipt=RECIPE/'installation.json';assert not receipt.exists()
    baseline=v.load_json(RECIPE/'baseline.json')
    v.validate_v2_pack(PACK/'AR0411')
    assert payload(LIVE)==baseline['before'],'Installed payload drift'
    backup=ROOT/'backups/animations'/TAG/'AR0411';assert not backup.exists();backup.mkdir(parents=True)
    for name in baseline['changed_files']: shutil.copy2(LIVE/name,backup/name)
    try:
        for name in baseline['changed_files']: shutil.copy2(PACK/'AR0411'/name,LIVE/name)
        assert payload(LIVE)==baseline['after']
    except Exception:
        for name in baseline['changed_files']: shutil.copy2(backup/name,LIVE/name)
        assert payload(LIVE)==baseline['before']
        raise
    write(receipt,dict(schema='bg2-upscale-animation-targeted-visual-install-v1',status='installed-pending-ingame-qa',created_utc=v.utc_now(),area='AR0411',resref='DSTDVL1A',
        run=rel(RUN),pack=rel(PACK),backup=rel(backup),changed_files=baseline['changed_files'],
        registry_unchanged=True,siblings_unchanged=True,other_areas='not modified'))
    row,rows=workflow._registry_row(ROOT,'DSTDVL1A')
    row['notes']=('AR0411 : contour brumeux recommande (3e colonne) installe 2026-10-11, fondu20px x4 + Gaussian sigma4 en bordure sur RGBA premultiplie. '
        'Coeur conserve ; 139frames/214phases30fps, dimensions et centres natifs, registre et autres assets inchanges. '
        'Run '+rel(RUN)+' ; recu '+rel(receipt)+'. QA ingame ouverte. Autres9zones non modifiees par ce correctif ; pas de validation globale ni release.')
    (ROOT/workflow.REGISTRY_REL).write_bytes(workflow._render_registry(rows))
    print('Installed DSTDVL1A AR0411; 46 frames; native geometry and other assets preserved; backup '+rel(backup))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    install() if args.install else prepare()
