"""Derive exact approved soft4 preview and replace only SPDEATH3 runtime bindings."""
from pathlib import Path
from dataclasses import asdict, replace
import argparse
import copy
import importlib.util
import json
import shutil
import struct
import subprocess
import sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import effect_authority as authority
import run_effect_interpolation as interpolation
import install_renderer_candidate as tx
from workspace_paths import get_path
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


base=module('impacts_temporal','pipeline/recipes/effects-lot33-native-impacts-20261017-v1/temporal.py')
builder=module('effects_builder','pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
load,save,rel,digest=base.load,base.save,base.rel,base.digest
sha=workflow.sha256_file
BATCH=ROOT/'effects/batches/spdeath3-bezier-soft4-runtime-20261018-v2'
OUT=ROOT/'effects/installations/spdeath3-bezier-soft4-20261018-v1'
CAND=OUT/'candidate'
PREVIEW=ROOT/'effects/batches/spdeath3-bezier-edgefade-preview-20261018-v1'
PARENT=ROOT/'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'
PREVIOUS_INSTALL=ROOT/'effects/installations/lot33-native-impacts-20261018-v1'
GAME=get_path('bg2ee_game_root',required=True)
PROBE=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
REFS={'SPDEATH3','X33N33'}
PRESERVE=['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','BaldurReal.exe',
          'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
          'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
          'override/Z33T33.vvc','override/Z33B33.vvc','override/Z33N33.vvc',
          'override/Z33P0181.vvc','override/Z33P0182.vvc']
base.BATCH=BATCH


def asset():return load(BATCH/'batch.json')['assets'][0]


def carrier(a,spatial,target):
    raw=read_bam(ROOT/a['source']);frames,pal,tr=decode_bam(raw)
    count,cycles,_=struct.unpack_from('<HBB',raw,8);of,op,ol=struct.unpack_from('<III',raw,12)
    source_cycles=cycle_metadata(raw,count)
    assert source_cycles==a['native_cycles']
    cc=raw[of+count*12:of+count*12+cycles*4]
    lookup_count=max(c['lookup_start']+len(c['frame_indices']) for c in source_cycles)
    lookup=raw[ol:ol+lookup_count*2];palette=raw[op:op+1024]
    cw,ch=spatial['aligned_canvas_size_x1'];pad=5  # preview pad4 + Gaussian pad16, x4
    w,h=cw+2*pad,ch+2*pad
    anchors={tuple(np.asarray(f['canvas_offset_x1'])+np.asarray(f['centre_x1'])) for f in spatial['frames']}
    assert len(anchors)==1
    anchor=next(iter(anchors));centre=[int(anchor[0])+pad,int(anchor[1])+pad]
    nf=24;npal=nf+count*12+cycles*4;nl=npal+1024;cursor=nl+len(lookup)
    table=bytearray();pixels=[]
    for i,(idx,cx,cy,_) in enumerate(frames):
        x,y=np.asarray(spatial['frames'][i]['canvas_offset_x1'])+pad
        image=np.full((h,w),tr,np.uint8);image[y:y+idx.shape[0],x:x+idx.shape[1]]=idx
        assert [int(x)-centre[0],int(y)-centre[1]]==[-cx,-cy]
        table.extend(struct.pack('<HHhhI',w,h,*centre,cursor|0x80000000));pixels.append(image.tobytes());cursor+=w*h
    out=struct.pack('<8sHBBIII',b'BAM V1  ',count,cycles,tr,nf,npal,nl)+table+cc+palette+lookup+b''.join(pixels)
    decoded,pal_after,tr_after=decode_bam(out)
    assert tr_after==tr and np.array_equal(pal_after,pal)
    assert cycle_metadata(out,count)==source_cycles
    checks=[]
    for i,((old,cx,cy,_),(new,ncx,ncy,_)) in enumerate(zip(frames,decoded)):
        x,y=np.asarray(spatial['frames'][i]['canvas_offset_x1'])+pad
        assert np.array_equal(new[y:y+old.shape[0],x:x+old.shape[1]],old)
        blank=new.copy();blank[y:y+old.shape[0],x:x+old.shape[1]]=tr
        assert np.all(blank==tr)
        assert [int(x)-ncx,int(y)-ncy]==[-cx,-cy]
        checks.append({'frame':i,'source_pixels_and_world_positions_exact':True})
    target.parent.mkdir(parents=True);target.write_bytes(out)
    return [w,h],centre,checks


def derive():
    assert not (BATCH/'production.json').exists()
    a=copy.deepcopy(next(a for a in load(PARENT/'batch.json')['assets'] if a['resref']=='SPDEATH3'))
    parent_run=a['interpolation_run']
    a.update(interpolation_run='spdeath3-bezier-soft4-20261018-v2',
             pack='effects/ressources/SPDEATH3/packs/spdeath3-7b-bezier-soft4-apollo30-20261018-v2')
    save(BATCH/'batch.json',{'assets':[a],'parent_interpolation_run':parent_run,
         'authorization':'User chose sigma4 and requested SPDEATH3-only installation and CLUA test',
         'preview':workflow.file_evidence(ROOT,PREVIEW/'result.json')})
    plan=replace(base.make_plan(a),recipe_id='spdeath3-approved-bezier-edge-gaussian4')
    assert not plan.run_root.exists();interpolation.reserve(plan);plan.run_root.mkdir(parents=True)
    snapshot=plan.run_root/'producer-source.py';shutil.copy2(Path(__file__),snapshot)
    old_stage=ROOT/'effects/ressources/SPDEATH3/runs'/parent_run/'02-interpolation'
    old=load(old_stage/'manifest.json');spatial=load(plan.spatial_manifest)
    runtime_carrier=plan.run_root/'runtime-carrier/SPDEATH3.bam'
    size,centre,geometry_checks=carrier(a,spatial,runtime_carrier)
    assert size==[64,104] and centre==[33,60]
    recipe={'schema':interpolation.RECIPE_SCHEMA,'recipe_id':plan.recipe_id,'pipeline_id':interpolation.PIPELINE_ID,
            'scale':4,'target_fps':[30,1],'sigma_x4':4,'core_exact_beyond_x4':16,
            'bezier':'Potrace1.334; original temporal alpha fractions; exact approved preview',
            'alpha_policy':'Gaussian edge-only premultiplied RGBA; straight normal companion; no second premultiplication',
            'new_neural_inference':0,'parent_interpolation':interpolation.evidence(ROOT,'parent-interpolation',old_stage/'manifest.json'),
            'approved_preview':interpolation.evidence(ROOT,'preview',PREVIEW/'result.json'),
            'tools':[interpolation.evidence(ROOT,'producer',snapshot)]}
    save(plan.recipe_path,recipe);created=workflow.utc_now()
    def descriptor(status,sealed,outputs=()):
        d=interpolation.descriptor(plan,recipe,status=status,sealed=sealed,created_at=created,outputs=outputs)
        d['pipeline']['version']='effect-spdeath3-bezier-gaussian4.v1'
        d['provenance']['generator']=rel(Path(__file__))
        d['inputs'].extend([recipe['parent_interpolation'],recipe['approved_preview']]);return d
    save(plan.descriptor_path,descriptor('running',False))
    folder=plan.interpolation_root/'frames-rgba';folder.mkdir(parents=True)
    preview=load(PREVIEW/'result.json');records=[]
    for old_f,p in zip(old['frames'],preview['frames'],strict=True):
        f=copy.deepcopy(old_f);assert p['frame']==f['frame'];v=p['variants']['soft4']
        raw=ROOT/v['premultiplied']['path'];normal=ROOT/v['straight']['path']
        assert workflow.file_evidence(ROOT,raw)==v['premultiplied'] and workflow.file_evidence(ROOT,normal)==v['straight']
        primary=np.fromfile(raw,np.uint8).reshape(416,256,4);straight=np.fromfile(normal,np.uint8).reshape(416,256,4)
        assert np.array_equal(primary[:,:,3],straight[:,:,3]) and np.all(primary[:,:,:3]<=primary[:,:,3:4])
        assert not primary[primary[:,:,3]==0].any() and not straight[straight[:,:,3]==0].any()
        l,t,r,b=old_f['runtime_crop_box_x4'];cx,cy=old_f['centre_x1']
        assert [l+20-centre[0]*4,t+20-centre[1]*4]==[-cx*4,-cy*4]
        stem=f'frame_{f["frame"]:03d}';rp=folder/(stem+'.rgba');rs=folder/(stem+'-straight.rgba');png=folder/(stem+'.png')
        shutil.copy2(raw,rp);shutil.copy2(normal,rs);Image.fromarray(primary).save(png,compress_level=3)
        f.update(logical_size_x1=size,physical_size_x4=[256,416],centre_x1=centre,
                 runtime_crop_box_x4=[0,0,256,416],bytes=256*416*4,
                 raw_rgba_x4='frames-rgba/'+rp.name,raw_rgba_x4_sha256=sha(rp),
                 straight_raw_rgba_x4='frames-rgba/'+rs.name,straight_raw_rgba_x4_sha256=sha(rs),
                 rgba_x4='frames-rgba/'+png.name,rgba_x4_sha256=sha(png),
                 anchored_rgba_sha256=digest(primary.tobytes()),anchored_rgb_sha256=digest(primary[:,:,:3].tobytes()),
                 normal_alpha_policy='approved-bezier-continuous-alpha-gaussian4-edge')
        assert f['raw_rgba_x4_sha256']==v['premultiplied']['sha256'] and f['straight_raw_rgba_x4_sha256']==v['straight']['sha256']
        records.append(f)
    m=copy.deepcopy(old)
    m.update(created_utc=workflow.utc_now(),visual_treatment=recipe,frames=records,
             derived_aligned_canvas_size_x1=size,derived_canvas_origin_in_parent_x4=[-20,-20],
             runtime_carrier={'path':rel(runtime_carrier),'sha256':sha(runtime_carrier),'native_world_pixels_preserved':True})
    for c in m['timing']['cycles']:
        seq=[records[i] for i in c['timeline_frame_indices']]
        assert len({f['anchored_rgb_sha256'] for f in seq})==c['unique_rgb']
        assert len({f['anchored_rgba_sha256'] for f in seq})==c['unique_rgba']
    assert m['timing']==old['timing']
    save(plan.interpolation_root/'manifest.json',m)
    save(plan.descriptor_path,descriptor('completed',True,[
        interpolation.evidence(ROOT,'interpolation-manifest',plan.interpolation_root/'manifest.json'),
        interpolation.evidence(ROOT,'runtime-bam-carrier',runtime_carrier)]))
    report=base.finish(a,plan,spatial)
    save(BATCH/'geometry-verification.json',{'native_frames':geometry_checks,'source_palette_cycles_lookup_preserved':True,
         'size_x1':size,'centre_x1':centre,'native_world_positions_preserved':True,
         'runtime_rgba_exact_sigma4_preview':True,'phases':124,'old_phase_timing_exact':True})
    save(BATCH/'production.json',{'status':'completed','assets':[report],'count':1,'phases':124,
         'source_preview':workflow.file_evidence(ROOT,PREVIEW/'result.json'),'sigma_x4':4,
         'qa':'pending-ingame-user-test','installed':False,'release_changed':False})


def probe(target,name):
    with (OUT/name).open('x',encoding='utf-8') as log:
        subprocess.run([str(PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],
                       stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)


def prepare():
    assert not (OUT/'plan.json').exists()
    CAND.mkdir(parents=True,exist_ok=True)
    a=asset();old_a=next(a for a in load(PARENT/'batch.json')['assets'] if a['resref']=='SPDEATH3')
    active=GAME/'iee-assets/effects';old=load(active/'manifest.json')
    assert sha(active/'manifest.json')==load(PREVIOUS_INSTALL/'installation.json')['manifest_sha256']
    assert [r['resref'] for r in old['resources'][-2:]]==['SPDEATH3','X33N33']
    assert all(f['resref'] not in REFS for f in old['frames'][:-244])
    before={'manifest_sha256':sha(active/'manifest.json'),'registry_sha256':sha(active/'EffectAnimations-X4.registry'),
            'preserved':{n:asdict(tx.snapshot_file(GAME/n)) for n in PRESERVE}}
    save(OUT/'before.json',before)
    manifest=copy.deepcopy(old);files=[];records=[];new_frames=[];contracts=[]
    for line in (PREVIOUS_INSTALL/'runtime-contracts.tsv').read_text(encoding='ascii').splitlines():
        if line.split('\t',1)[0].upper() not in REFS:contracts.append(line)
    def add(name,raw=None,source=None):
        dest=tx.managed_path(CAND,name,create_parents=True)
        if source is not None:
            if dest.exists():assert tx.snapshot_file(dest)==tx.snapshot_file(source)
            else:shutil.copy2(source,dest)
        else:
            if dest.exists():assert dest.read_bytes()==raw
            else:dest.write_bytes(raw)
        files.append({'name':name,**asdict(tx.snapshot_file(dest))})
    old_tails=bytearray()
    for ref,straight in [('SPDEATH3',False),('X33N33',True)]:
        old_raw,old_resource,_,_,_,_=builder.build_resource(old_a,ref,straight);old_tails.extend(old_raw)
        previous=next(r for r in old['resources'] if r['resref']==ref)
        assert old_resource==previous
        raw,resource,frames,copies,checks,m=builder.build_resource(a,ref,straight)
        assert previous['frame_count']==122 and resource['frame_count']==123
        # Padding/continuous alpha may split a formerly shared storage image;
        # temporal phases stay exact, while storage IDs must be regenerated.
        for key in previous['timeline']:
            if key not in {'native_frame_indices_by_cycle','timeline_frame_indices_by_cycle'}:
                assert resource['timeline'][key]==previous['timeline'][key],key
        records.append(raw);contracts.extend(checks)
        i=next(i for i,r in enumerate(manifest['resources']) if r['resref']==ref);manifest['resources'][i]=resource
        for f in frames:f['frame']=len(old['frames'])-244+len(new_frames);new_frames.append(f)
        for source,name in copies:add('iee-assets/effects/'+name,source=source)
        source=ROOT/m['runtime_carrier']['path'];add(f'override/{ref}.bam',source=source)
        i=next(i for i,c in enumerate(manifest['runtime_bam_carriers']) if c['resref']==ref)
        manifest['runtime_bam_carriers'][i].update(sha256=sha(source),bytes=source.stat().st_size,
             policy='uniform64x104 carrier; transparent padding only; native indices/palette/lookup and world positions exact')
    manifest['frames']=old['frames'][:-244]+new_frames
    assert len(new_frames)==246 and len(manifest['frames'])==old['frame_count']+2
    old_registry=(active/'EffectAnimations-X4.registry').read_bytes()
    assert old_registry[-len(old_tails):]==old_tails
    registry=old_registry[:-len(old_tails)]+b''.join(records)
    assert manifest['resources'][:-2]==old['resources'][:-2] and manifest['frames'][:-246]==old['frames'][:-244]
    assert manifest['runtime_vvc_controllers']==old['runtime_vvc_controllers']
    manifest.update(registry_bytes=len(registry),registry_sha256=digest(registry),frame_count=len(manifest['frames']))
    manifest.setdefault('source_packs',[]).append({'resref':'SPDEATH3','pack':a['pack'],
         'manifest_sha256':sha(ROOT/a['pack']/'manifest.json'),'interpolation_run':a['interpolation_run'],
         'variants':{'SPDEATH3':'premultiplied','X33N33':'straight'},'sigma_x4':4})
    add('iee-assets/effects/EffectAnimations-X4.registry',registry)
    add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
    probe(CAND/'iee-assets/effects','candidate-native-loader.log')
    save(OUT/'plan.json',{'files':files,'manifest_sha256':sha(CAND/'iee-assets/effects/manifest.json'),
         'resref':'SPDEATH3','sigma_x4':4,'runtime_resources':322,'backings':43357,'replaced_backings':244,'new_backings':2,
         'other_resources_identical':320,'other_backings_identical':43111,'native_contracts':len(contracts),
         'primary_clua':'C:Eval(\'CreateVisualEffectObject("Z33T33",Player1)\',0)',
         'vvc_controllers_unchanged':True,'size_x1':[64,104],'centre_x1':[33,60],
         'world_positions_preserved':True,'visual_qa':'pending-ingame-user-test','release_changed':False})
    (OUT/'CLUA.md').write_text('# SPDEATH3 — Bézier et fondu sigma4\n\nRelancer via InfinityLoader ; console Ctrl+Espace.\n\n```lua\n-- SPDEATH3 / cycle000-once / normal\nC:Eval(\'CreateVisualEffectObject("Z33T33",Player1)\',0)\n-- Boucle de test bornée\nC:Eval(\'CreateVisualEffectObject("Z33P0182",Player1)\',0)\n```\n\n124phases/2profils ; durée native conservée, même position. Aucun test visuel ingame déduit des contrôles hors jeu.\n',encoding='utf-8')
    print('READY',len(files),'targets;',len(contracts),'contracts; only SPDEATH3+normal companion',flush=True)


def preserved(before):assert all(asdict(tx.snapshot_file(GAME/n))==value for n,value in before['preserved'].items())


def rollback(receipt):
    assert Path(receipt['game_root']).resolve()==GAME.resolve()
    for f in reversed(receipt['files']):
        target=tx.managed_path(GAME,f['name'],create_parents=True)
        current=tx.optional_snapshot(target);expected=tx.FileSnapshot(f['bytes'],f['sha256'])
        old=tx.FileSnapshot(**f['before']) if f['before'] else None
        assert current in (old,expected)
        if current==old:continue
        if old:tx.atomic_copy(OUT/'before'/f['name'],target,old)
        else:tx.safe_unlink(target,expected)
    receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt)


def install():
    assert not (OUT/'transaction.json').exists()
    tx.ensure_game_stopped(tx.running_game_processes)
    (OUT/'before').mkdir(exist_ok=True)
    plan,before=load(OUT/'plan.json'),load(OUT/'before.json');preserved(before)
    assert sha(GAME/'iee-assets/effects/manifest.json')==before['manifest_sha256']
    assert sha(GAME/'iee-assets/effects/EffectAnimations-X4.registry')==before['registry_sha256']
    entries=[]
    for f in plan['files']:
        expected=tx.FileSnapshot(f['bytes'],f['sha256']);assert tx.snapshot_file(CAND/f['name'])==expected
        target=tx.managed_path(GAME,f['name']);old=tx.optional_snapshot(target)
        if old is not None:
            tx.atomic_copy(target,tx.managed_path(OUT/'before',f['name'],create_parents=True),old)
        else:
            assert f['name'] in {'iee-assets/effects/EFX4-SPDEATH3-frame122.rgba',
                                  'iee-assets/effects/EFX4-X33N33-frame122.rgba'}
        entries.append({**f,'before':asdict(old) if old else None})
    receipt={'schema':'bg2-effects-resource-delta-transaction-v1','status':'prepared','game_root':str(GAME),
             'candidate_root':rel(CAND),'created_utc':tx.utc_now(),'files':entries}
    tx.write_json_atomic(OUT/'transaction.json',receipt)
    try:
        tx.ensure_game_stopped(tx.running_game_processes)
        receipt['status']='installing';tx.write_json_atomic(OUT/'transaction.json',receipt)
        for f in entries:
            target=tx.managed_path(GAME,f['name'],create_parents=True)
            assert tx.optional_snapshot(target)==(tx.FileSnapshot(**f['before']) if f['before'] else None)
            tx.atomic_copy(CAND/f['name'],target,tx.FileSnapshot(f['bytes'],f['sha256']))
        for f in entries:assert tx.snapshot_file(GAME/f['name'])==tx.FileSnapshot(f['bytes'],f['sha256'])
        preserved(before);probe(GAME/'iee-assets/effects','installed-native-loader.log')
        receipt['status']='installed';receipt['installed_utc']=tx.utc_now();tx.write_json_atomic(OUT/'transaction.json',receipt)
    except Exception:rollback(receipt);raise
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        save(OUT/'processing-before.json',rows)
        for r in rows:
            if r['asset_key']=='effects:bam:SPDEATH3':
                r.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'installation.json',{k:v for k,v in plan.items() if k!='files'}|{
         'status':'installed-offline-verified','transaction':rel(OUT/'transaction.json'),
         'dll_ini_shaders_character_profile_unchanged':True,'game_and_loader_stopped':True,
         'game_launched':False,'qa_accepted':False,'installed_utc':receipt['installed_utc']})
    print('INSTALLED SPDEATH3 Bezier sigma4; test Z33T33 unchanged',flush=True)


def restore():
    tx.ensure_game_stopped(tx.running_game_processes);rollback(load(OUT/'transaction.json'))
    if (OUT/'processing-before.json').exists():
        previous=next(r for r in load(OUT/'processing-before.json') if r['asset_key']=='effects:bam:SPDEATH3')
        with authority.guard(ROOT,write=True):
            rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
            for r in rows:
                if r['asset_key']=='effects:bam:SPDEATH3' and r['installation_receipt']==rel(OUT/'transaction.json'):
                    r.update({k:previous[k] for k in ['installation_state','installation_receipt']})
            authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'restoration.json',{'status':'restored','transaction':rel(OUT/'transaction.json'),'utc':tx.utc_now()})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['derive','prepare','install','restore']);args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);globals()[args.action]()
