"""Apply approved DSTDVL1A edge recipe to its four siblings, AR0411 only."""
import argparse
import copy
import importlib.util
import sys
import shutil
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import animation_workflow as workflow
from workspace_paths import get_path

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

h=module('native_pack_helpers',ROOT/'pipeline/recipes/dstdvl1a-misty-contour-native-geometry-20261011-v2/install.py')
blur=module('approved_misty_recipe',ROOT/'pipeline/recipes/dstdvl1a-misty-contour-20261011-v1/build.py')
TAG='ar0411-dstdvl-family-misty-contour-20261011-v1'
RECIPE=Path(__file__).resolve().parent
RUN=ROOT/'animations/batches'/TAG
PACK=ROOT/'animations/packs-par-zone'/TAG
BASE=ROOT/'animations/packs-par-zone/dstdvl1a-misty-contour-native-geometry-20261011-v2/AR0411'
LIVE=get_path('bg2ee_game_root')/'iee-assets/areas/AR0411'
TARGETS=['DSTDVL1B','DSTDVL1C','DSTDVL2B','DSTDVL2C']

def prepare():
    assert not RUN.exists() and not PACK.exists(),'Immutable output exists'
    _,resources=v.validate_v2_pack(BASE)
    before=h.payload(LIVE)
    assert before==h.payload(BASE),'Live pack changed since DSTDVL1A installation'
    assert v.registry_v2_from_resources(resources,3)==(LIVE/v.REGISTRY_NAME).read_bytes()
    resources=copy.deepcopy(resources)
    originals={r['resref']:copy.deepcopy(r) for r in resources if r['resref'] in TARGETS}
    stage=RUN/'frames';stage.mkdir(parents=True)
    metrics={};samples={}
    for resource in resources:
        name=resource['resref']
        if name not in TARGETS: continue
        assets={a['name']:a for a in resource['assets']}
        changed=0;core_pixels=0;best=-1
        for frame in resource['frames']:
            w,height=frame['physical_size_x4']
            source=np.frombuffer((LIVE/frame['asset']).read_bytes(),np.uint8).reshape(height,w,4)
            assert np.all(source[:,:,:3]<=source[:,:,3:4])
            padded,core=blur.treat(source,20,4)
            if source[:,:,3].any():
                result=padded[24:-24,24:-24].copy();core=core[24:-24,24:-24]
            else: result=padded
            assert result.shape==source.shape
            assert np.array_equal(result[core],source[core]),'Core changed'
            assert np.all(result[:,:,:3]<=result[:,:,3:4])
            core_pixels+=int(core.sum())
            changed+=int(not np.array_equal(source,result))
            path=stage/frame['asset'];path.write_bytes(result.tobytes())
            assert path.stat().st_size==frame['bytes']
            frame['sha256']=h.sha(path);assets[frame['asset']]['sha256']=frame['sha256']
            score=int(source[:,:,:3].sum()) if frame['frame']<18 else -1
            if score>best:
                best=score;samples[name]=(source.copy(),result.copy(),frame['frame'])
        assert v.resource_binary_v2(resource,3)==v.resource_binary_v2(originals[name],3),name+' geometry/timing changed'
        metrics[name]=dict(frame_count=resource['frame_count'],changed_frames=changed,core_pixels_byte_identical=core_pixels,
            timeline_phases=[len(c['timeline_frame_indices']) for c in resource['cycles']],geometry_and_timeline_verbatim=True)
    targets=[r for r in resources if r['resref'] in TARGETS]
    h.pack(RUN/'03_runtime_pack',targets,lambda r:stage)
    h.pack(PACK/'AR0411',resources,lambda r:stage if r['resref'] in TARGETS else LIVE,'AR0411')
    after=h.payload(PACK/'AR0411')
    assert before.keys()==after.keys()
    changed=[n for n in before if before[n]!=after[n]]
    assert len(changed)==sum(m['changed_frames'] for m in metrics.values())
    assert all(any(n.startswith('AAX4-'+r+'-') for r in TARGETS) for n in changed)
    assert before[v.REGISTRY_NAME]==after[v.REGISTRY_NAME]
    h.write(PACK/'manifest.json',dict(schema='bg2-upscale-area-animation-pack-index-v1',status='completed',created_utc=v.utc_now(),areas=[dict(area_id='AR0411',directory='AR0411',manifest_sha256=h.sha(PACK/'AR0411/manifest.json'),registry_sha256=h.sha(PACK/'AR0411'/v.REGISTRY_NAME))]))
    h.write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),resrefs=TARGETS,
        source_pack=h.rel(BASE),source_pack_manifest_sha256=h.sha(BASE/'manifest.json'),
        runtime_pack='03_runtime_pack',runtime_pack_manifest_sha256=h.sha(RUN/'03_runtime_pack/manifest.json'),
        output_split_root=h.rel(PACK),output_manifest_sha256=h.sha(PACK/'manifest.json'),
        visual_treatment=dict(recipe='DSTDVL1A approved third column',inner_feather_x4=20,gaussian_sigma_x4=4,
            formula='identical approved edge-only premultiplied RGBA feather/Gaussian; native-canvas crop; core distance>=36 unchanged',
            reference_recipe=h.rel(blur.RECIPE) if hasattr(blur,'RECIPE') else 'pipeline/recipes/dstdvl1a-misty-contour-20261011-v1/build.py',
            timing='current installed cycles and rates unchanged; transparent holds retained',scope='AR0411 only'),
        metrics=metrics,qa_status='pending-user-ingame-QA'))
    h.write(RECIPE/'baseline.json',dict(area='AR0411',before=before,after=after,changed_files=changed))
    a,m,p=workflow._artifact(ROOT,RUN);workflow._verify_embedded_pack(ROOT,m,p)
    for name in TARGETS:
        workflow._verify_pack_binding(ROOT,m,p,workflow._source_pack(ROOT,PACK,name,['AR0411']),name)
    board=Image.new('RGB',(1940,1100),(25,25,25));d=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    for i,name in enumerate(TARGETS):
        src,dst,idx=samples[name];x=(i%2)*970;y=(i//2)*550
        d.text((x+8,y+5),name+' / frame'+str(idx)+' : actuel -> contour brumeux',font=font,fill='white')
        for col,rgba in enumerate([src,dst]):
            height,w=rgba.shape[:2];yy,xx=np.indices((height,w));bg=30+((xx//24+yy//24)%2)*8
            rgb=np.clip(rgba[:,:,:3].astype(np.int16)+bg[:,:,None],0,255).astype(np.uint8)
            im=Image.fromarray(rgb);im.thumbnail((465,485))
            board.paste(im,(x+col*480+(470-im.width)//2,y+42+(485-im.height)//2))
    board.save(RUN/'DSTDVL-family-before-after.png')
    h.write(RECIPE/'checks.json',dict(passed=True,metrics=metrics,changed_frames=len(changed),registry_and_non_targets_byte_identical=True,
        DSTDVL1A_unchanged=True,pack_bindings_verified=True,preview=h.rel(RUN/'DSTDVL-family-before-after.png')))
    print('Prepared '+','.join(TARGETS)+'; '+str(len(changed))+' changed frames; native geometry/timing and DSTDVL1A preserved')

def install():
    result=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader|BGMain' }).Count"],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='0','Game or InfinityLoader running'
    receipt=RECIPE/'installation.json';assert not receipt.exists()
    baseline=v.load_json(RECIPE/'baseline.json');v.validate_v2_pack(PACK/'AR0411')
    assert h.payload(LIVE)==baseline['before'],'Live pack drift'
    backup=ROOT/'backups/animations'/TAG/'AR0411';assert not backup.exists();backup.mkdir(parents=True)
    for name in baseline['changed_files']:shutil.copy2(LIVE/name,backup/name)
    try:
        for name in baseline['changed_files']:shutil.copy2(PACK/'AR0411'/name,LIVE/name)
        assert h.payload(LIVE)==baseline['after']
    except Exception:
        for name in baseline['changed_files']:shutil.copy2(backup/name,LIVE/name)
        assert h.payload(LIVE)==baseline['before']
        raise
    h.write(receipt,dict(schema='bg2-upscale-animation-targeted-visual-install-v1',status='installed-pending-ingame-qa',created_utc=v.utc_now(),area='AR0411',resrefs=TARGETS,
        run=h.rel(RUN),pack=h.rel(PACK),backup=h.rel(backup),changed_files=baseline['changed_files'],registry_unchanged=True,
        non_targets_unchanged=True,other_areas='not modified'))
    _,rows=workflow._registry_row(ROOT,TARGETS[0])
    for row in rows:
        if row['resref'] in TARGETS:
            row['notes']=('AR0411 : meme contour brumeux que DSTDVL1A installe 2026-10-11, fondu20px x4 + Gaussian sigma4 en bordure sur RGBA premultiplie. '
                'Coeur, dimensions/centres, timeline et cadence conserves. Run '+h.rel(RUN)+' ; recu '+h.rel(receipt)+'. QA ingame ouverte ; autres zones non modifiees ; aucune release.')
        elif row['resref']=='DSTDVL1A':
            row['notes']=row['notes'].replace('QA ingame ouverte.','QA utilisateur AR0411 rendu et mouvement acceptee 2026-10-11.').replace('Autres9zones non modifiees par ce correctif','Autres9zones non modifiees par ce correctif')
    (ROOT/workflow.REGISTRY_REL).write_bytes(workflow._render_registry(rows))
    print('Installed four DSTDVL siblings on AR0411; registry and DSTDVL1A unchanged; backup '+h.rel(backup))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    install() if args.install else prepare()
