"""Scoped non-generative alternatives after visual observation of SeedVR inventions."""
import copy
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_effect_spatial as spatial
from run_creature_sprite_x2 import run_xbr,direct_upscale_contract,XBR_ADAPTER
from workspace_paths import get_path
from upscale_animation_frames import make_contact_sheet

BASE=ROOT/'effects/batches/lot50-seedvr7b-apollo30-20261108-v1'
OUT=ROOT/'effects/batches/lot50-xbr-small-20261108-v1'

def prepare():
    original=json.loads((BASE/'batch.json').read_text(encoding='utf-8'))
    names={a['resref'] for a in original['assets'] if a['profile'] in {'F','G'}}|{'FIRE_4G2','SPFBSMAL','SPFIRE'}
    assets=[]
    for old in original['assets']:
        if old['resref'] not in names:continue
        a=copy.deepcopy(old);n=a['resref'];a.update(seedvr_spatial_run=a['spatial_run'],seedvr_interpolation_run=a['interpolation_run'],
            spatial_run=f'{n.lower()}-xbr4x-nativealpha-20261108-v1',interpolation_run=f'{n.lower()}-xbr4x-apollo30-native-20261108-v1',
            pack=f'effects/ressources/{n}/packs/{n.lower()}-xbr4x-apollo30-initial-20261108-v1',sigma_x4=0)
        assets.append(a)
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/'batch.json').exists():(OUT/'batch.json').write_text(json.dumps(dict(schema='bg2-effects-production-batch-v1',assets=assets,
        reason='SeedVR visual inspection: invented symbolic/engraved shapes on tiny flames and white particles. Preserve original SeedVR runs and add xBR4X alternatives.',
        source_batch=BASE.relative_to(ROOT).as_posix(),assets_count=len(assets)),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    substitutions=[('temporal.py','temporal_xbr.py'),('verify.py','verify_xbr.py'),('runtime_profiles.py','runtime_profiles_xbr.py')]
    for source,target in substitutions:
        p=HERE/target
        if p.exists():continue
        text=(HERE/source).read_text(encoding='utf-8')
        text=text.replace("effects/batches/lot50-seedvr7b-apollo30-20261108-v1","effects/batches/lot50-xbr-small-20261108-v1")
        text=text.replace('from temporal import','from temporal_xbr import')
        text=text.replace('seedvr2_7b_int8_convrot.safetensors','XBR/xbr4X')
        text=text.replace("s['parameters']['color_correction_method']=='lab'","s['parameters']['color_correction_method']=='native'")
        text=text.replace("f'{name.lower()}-7b-x4-apollo30-native-profiles-20261108-v2'","f'{name.lower()}-xbr4x-apollo30-native-profiles-20261108-v1'")
        p.write_text(text,encoding='utf-8')
    return json.loads((OUT/'batch.json').read_text(encoding='utf-8'))['assets']

def produce_spatial(a):
    n=a['resref'];plan=spatial.build_plan(ROOT,n,a['spatial_run'],'xbr4x-nativealpha',Path('pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json'),server='http://127.0.0.1:8188',pad=0,poll_seconds=.2,timeout_seconds=1800,upload_folder='unused',color_correction_method='lab')
    if plan.descriptor_path.exists() and spatial.load_json(plan.descriptor_path).get('result',{}).get('sealed'):return
    spatial.reserve_plan(plan);plan.run_root.mkdir(parents=True,exist_ok=True)
    source=spatial._ensure_source(plan)
    r=dict(schema=spatial.RECIPE_SCHEMA,pipeline_id=spatial.PIPELINE_ID,recipe_id='xbr4x-nativealpha',scale=4,algorithm='XBR/xbr4X',blend_colors=False,
           alpha_policy='native nearest4; explicit inherited green-index derivation for3assets',
           tools=[spatial.file_evidence(ROOT,'producer',Path(__file__)),spatial.file_evidence(ROOT,'adapter',XBR_ADAPTER)],
           tool=dict(path='config://mmpx_scalepix',sha256=spatial.workflow.sha256_file(get_path('mmpx_scalepix',required=True))))
    spatial.write_json(plan.recipe_path,r)
    seed=ROOT/'effects/ressources'/n/'runs'/a['seedvr_spatial_run']
    if not plan.frame_root.exists():shutil.copytree(seed/'00-frames-x1',plan.frame_root)
    fm=spatial.load_json(plan.frame_root/'manifest.json')
    m=spatial.load_json(seed/'01-spatial-x4/manifest.json');m=copy.deepcopy(m)
    inputs=[]
    for f in fm['frames']:
        rgb=np.array(Image.open(plan.frame_root/'rgb'/f['file']).convert('RGB'))
        filled=np.dstack((rgb,np.full(rgb.shape[:2],255,np.uint8)))
        inputs.append(SimpleNamespace(width=rgb.shape[1],height=rgb.shape[0],rgba=filled.tobytes()))
    outputs=run_xbr(inputs,get_path('mmpx_scalepix',required=True),shutil.which('node'),direct_upscale_contract(4))
    stage=plan.spatial_root;stage.mkdir(parents=True,exist_ok=True)
    records=[];runtime=[]
    for meta,template,(w,h,data) in zip(fm['frames'],m['frames'],outputs):
        rgba=np.frombuffer(data,np.uint8).reshape(h,w,4).copy();alpha=np.array(Image.open(plan.frame_root/'alpha'/meta['file'])).repeat(4,0).repeat(4,1)
        assert rgba.shape[:2]==alpha.shape
        rgba[:,:,3]=alpha;aligned=Image.fromarray(rgba)
        crop=aligned.crop(tuple(template['runtime_crop_box_xn']));row=copy.deepcopy(template)
        for key in ('prompt_id','comfy_padded_xn','padded_x1'):row.pop(key,None)
        for key,image in [('aligned_rgba_xn',aligned),('rgba_xn',crop),('rgb_xn',crop.convert('RGB')),('alpha_xn',crop.getchannel('A'))]:
            p=stage/row[key];p.parent.mkdir(exist_ok=True);image.save(p);row[key+'_sha256']=spatial.workflow.sha256_file(p)
        p=stage/row['raw_rgba_xn'];p.parent.mkdir(exist_ok=True);p.write_bytes(crop.tobytes());row['raw_rgba_xn_sha256']=spatial.workflow.sha256_file(p)
        runtime.append(stage/row['rgba_xn']);records.append(row)
    preview=stage/'preview/contact.png';make_contact_sheet(runtime,preview)
    m.update(parameters=dict(model='XBR/xbr4X',scale=4,color_correction_method='native',blend_colors=False),frames=records,
             source=dict(frame_manifest=spatial.workflow.relative_path(ROOT,plan.frame_root/'manifest.json'),frame_manifest_sha256=spatial.workflow.sha256_file(plan.frame_root/'manifest.json')),
             preview='preview/contact.png',preview_sha256=spatial.workflow.sha256_file(preview),algorithm='XBR/xbr4X')
    m.pop('comfyui',None);m.pop('workflow',None)
    spatial.write_json(stage/'manifest.json',m)
    spatial.validate_frame_stage(ROOT,plan.frame_root,source);spatial.validate_spatial_stage(ROOT,stage,fm)
    outputs=[spatial.file_evidence(ROOT,'frames-manifest',plan.frame_root/'manifest.json'),spatial.file_evidence(ROOT,'spatial-manifest',stage/'manifest.json'),spatial.file_evidence(ROOT,'spatial-preview',preview)]
    d=spatial.build_descriptor(plan,r,source,status='completed',sealed=True,created_at_utc=spatial.workflow.utc_now(),outputs=outputs)
    d['provenance']['generator']=spatial.workflow.relative_path(ROOT,Path(__file__));d['provenance']['command']=['xbr_variants.py',n]
    spatial.write_json(plan.descriptor_path,d)
    spatial.workflow.register_run(ROOT,n,'spatial',a['spatial_run'],write=True)

def main():
    assets=prepare()
    import temporal_xbr as temporal
    import verify_xbr as verification
    import runtime_profiles_xbr as runtime
    from run_temporal import save
    temporal.save=verification.save=runtime.save=save
    progress={}
    for a in assets:
        n=a['resref']
        try:
            produce_spatial(a);temporal.produce(a);verification.verify(a);runtime.build(a)
            progress[n]={'state':'completed'}
        except Exception as exc:
            import traceback
            traceback.print_exc();progress[n]={'state':'failed','error':repr(exc)}
        save(OUT/'progress.json',progress)
    return any(r['state']=='failed' for r in progress.values())

if __name__=='__main__':raise SystemExit(main())
