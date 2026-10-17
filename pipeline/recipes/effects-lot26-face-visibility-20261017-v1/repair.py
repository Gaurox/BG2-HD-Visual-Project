"""OHRFEAR face-hole repair and offset-only visibility tests for narrow traps."""
from pathlib import Path
from dataclasses import asdict
import argparse
import copy
import importlib.util
import json
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes, distance_transform_edt, label

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import effect_authority as authority
import run_effect_interpolation as interpolation
import install_renderer_candidate as tx
from workspace_paths import get_path
from derive_animation_visual_treatment import smoothstep


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


base = module('lot26_temporal', 'pipeline/recipes/effects-lot26-seedvr7b-apollo30-20261017-v2/temporal.py')
builder = module('lot58_builder', 'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
load, save, rel, digest = base.load, base.save, base.rel, base.digest
sha = workflow.sha256_file
BATCH = ROOT / 'effects/batches/ohrfear-face-fill-20261017-v1'
OUT = ROOT / 'effects/installations/lot26-face-visibility-20261017-v1'
PARENT = ROOT / 'effects/installations/lot26-sdf-no-inset-20261017-v1'
CAND = OUT / 'candidate'
GAME = get_path('bg2ee_game_root', required=True)
base.BATCH = BATCH
PRESERVE = ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini', 'override/fpDraw.glsl',
            'override/fpSprite.glsl', 'override/fpSELECT.glsl',
            'iee-assets/creature-sprites/CreatureSprites-XN.catalog']


def asset():
    return load(BATCH / 'batch.json')['assets'][0]


def derive():
    assert not (BATCH / 'production.json').exists()
    a = copy.deepcopy(next(a for a in load(ROOT / 'effects/batches/lot26-sdf-no-inset-20261017-v1/batch.json')['assets'] if a['resref'] == 'OHRFEAR'))
    old_run = a['interpolation_run']
    a.update(interpolation_run='ohrfear-apollo30-facefill-20261017-v1',
             pack='effects/ressources/OHRFEAR/packs/ohrfear-7b-x4-apollo30-facefill-20261017-v1')
    save(BATCH / 'batch.json', {'assets': [a], 'parent_run': old_run,
         'authorization': 'User: remove transparency in middle of face, effect12 OHRFEAR'})
    plan = base.make_plan(a)
    assert not plan.run_root.exists()
    interpolation.reserve(plan)
    plan.run_root.mkdir(parents=True)
    snapshot = plan.run_root / 'producer-source.py'
    shutil.copy2(Path(__file__), snapshot)
    old_stage = ROOT / 'effects/ressources/OHRFEAR/runs' / old_run / '02-interpolation'
    old = load(old_stage / 'manifest.json')
    spatial = load(plan.spatial_manifest)
    cw, ch = spatial['aligned_canvas_size_x1']
    cache = {}
    source_holes = []
    for f in spatial['frames']:
        alpha = np.array(Image.open(plan.spatial_manifest.parent / f['aligned_rgba_xn']))[:, :, 3]
        mask = alpha > 0
        holes = binary_fill_holes(mask) & ~mask
        labs, count = label(holes)
        chosen = np.zeros_like(mask)
        for k in range(1, count + 1):
            yy, xx = np.where(labs == k)
            # Only small enclosed holes in the central mouth/face region.
            # Keep peripheral holes and all exterior transparency intact.
            if 35*4 <= xx.mean() < 55*4 and 38*4 <= yy.mean() < 58*4 and len(xx) <= 16*16:
                chosen |= labs == k
        fixed = alpha.copy()
        fixed[chosen] = 255
        cache[f['frame']] = (alpha, fixed)
        source_holes.append({'frame': f['frame'], 'filled_pixels_x4': int(chosen.sum())})
    recipe = {'schema': interpolation.RECIPE_SCHEMA, 'recipe_id': 'ohrfear-central-enclosed-hole-fill',
              'pipeline_id': interpolation.PIPELINE_ID, 'scale': 4, 'target_fps': [30, 1],
              'face_roi_x1': [35, 38, 55, 58], 'max_hole_pixels_x4': 256,
              'inner_feather_x4': 12, 'new_neural_inference': 0,
              'policy': 'fill only enclosed central face holes before temporal alpha and feather; preserve exterior and existing straight RGB',
              'parent_interpolation': interpolation.evidence(ROOT, 'parent-interpolation', old_stage / 'manifest.json'),
              'tools': [interpolation.evidence(ROOT, 'producer', snapshot)]}
    save(plan.recipe_path, recipe)
    created = workflow.utc_now()

    def descriptor(status, sealed, outputs=()):
        d = interpolation.descriptor(plan, recipe, status=status, sealed=sealed, created_at=created, outputs=outputs)
        d['pipeline']['version'] = 'effect-ohrfear-facefill.v1'
        d['provenance']['generator'] = rel(Path(__file__))
        d['inputs'].append(recipe['parent_interpolation'])
        return d

    save(plan.descriptor_path, descriptor('running', False))
    stage = plan.interpolation_root
    folder = stage / 'frames-rgba'
    folder.mkdir(parents=True)
    frames, checks, previews = [], [], []
    for old_f in old['frames']:
        f = copy.deepcopy(old_f)
        left, right = f['temporal_source_frames']
        fraction = f['temporal_fraction']
        alpha = np.rint(cache[left][1].astype(np.float32)*(1-fraction) + cache[right][1].astype(np.float32)*fraction).astype(np.uint8)
        original = np.rint(cache[left][0].astype(np.float32)*(1-fraction) + cache[right][0].astype(np.float32)*fraction).astype(np.uint8)
        distance = distance_transform_edt(np.pad(alpha > 0, 1))[1:-1, 1:-1]
        coverage = np.rint(alpha.astype(np.float32)*smoothstep((distance-1.0)/12)).astype(np.uint8)
        original_distance = distance_transform_edt(np.pad(original > 0, 1))[1:-1, 1:-1]
        original_coverage = np.rint(original.astype(np.float32)*smoothstep((original_distance-1.0)/12)).astype(np.uint8)
        l, t, r, b = f['runtime_crop_box_x4']
        w, h = f['physical_size_x4']
        before = np.frombuffer((old_stage / f['straight_raw_rgba_x4']).read_bytes(), np.uint8).reshape(h,w,4).copy()
        assert np.array_equal(before[:,:,3], original_coverage[t:b,l:r])
        fixed = before.copy()
        fixed[:,:,3] = coverage[t:b,l:r]
        assert np.all(fixed[:,:,3] >= before[:,:,3])
        new_pixels = (before[:,:,3] == 0) & (fixed[:,:,3] > 0)
        donors = before[:,:,3] >= 250
        if new_pixels.any():
            _, nearest = distance_transform_edt(~donors, return_indices=True)
            fixed[:,:,:3][new_pixels] = before[nearest[0][new_pixels],nearest[1][new_pixels],:3]
        fixed[fixed[:,:,3] == 0] = 0
        changed = fixed[:,:,3] != before[:,:,3]
        yy, xx = np.where(changed)
        if len(xx):
            assert xx.min() >= 35*4-13 and xx.max() < 55*4+13
            assert yy.min() >= 38*4-13 and yy.max() < 58*4+13
        assert np.array_equal(fixed[:,:,:3][before[:,:,3]>0],before[:,:,:3][before[:,:,3]>0])
        assert np.array_equal(fixed[~changed],before[~changed])
        primary = fixed.copy()
        primary[:,:,:3] = np.rint(fixed[:,:,:3].astype(np.float32)*fixed[:,:,3:4]/255).astype(np.uint8)
        stem = f'frame_{f["frame"]:03d}'
        raw, normal, png = folder/(stem+'.rgba'), folder/(stem+'-straight.rgba'), folder/(stem+'.png')
        raw.write_bytes(primary.tobytes()); normal.write_bytes(fixed.tobytes()); Image.fromarray(primary).save(png)
        canvas = np.zeros((ch*4,cw*4,4),np.uint8);canvas[t:b,l:r]=primary
        f.update(raw_rgba_x4='frames-rgba/'+raw.name,
                 raw_rgba_x4_sha256=digest(primary.tobytes()),straight_raw_rgba_x4='frames-rgba/'+normal.name,
                 straight_raw_rgba_x4_sha256=digest(fixed.tobytes()),rgba_x4='frames-rgba/'+png.name,
                 rgba_x4_sha256=sha(png),anchored_rgba_sha256=digest(canvas.tobytes()),
                 anchored_rgb_sha256=digest(canvas[:,:,:3].tobytes()),normal_alpha_policy='native central-face holes filled before temporal alpha and inner12')
        frames.append(f);checks.append({'frame':f['frame'],'changed_alpha_pixels':int(changed.sum()),'new_coverage_pixels':int(new_pixels.sum())})
        if f['frame'] in (20,45,60): previews.append((f['frame'],before,fixed))
    m = copy.deepcopy(old);m.update(created_utc=workflow.utc_now(),visual_treatment=recipe,frames=frames)
    for cycle in m['timing']['cycles']:
        seq=[frames[i] for i in cycle['timeline_frame_indices']]
        assert len({f['anchored_rgb_sha256'] for f in seq}) == len(seq)
        assert len({f['anchored_rgba_sha256'] for f in seq}) == len(seq)
    assert m['timing']==old['timing']
    carrier=plan.run_root/'runtime-carrier/OHRFEAR.bam';carrier.parent.mkdir();shutil.copy2(ROOT/old['runtime_carrier']['path'],carrier)
    m['runtime_carrier']={**old['runtime_carrier'],'path':rel(carrier)}
    save(stage/'manifest.json',m)
    save(plan.descriptor_path,descriptor('completed',True,[interpolation.evidence(ROOT,'interpolation-manifest',stage/'manifest.json'),interpolation.evidence(ROOT,'runtime-bam-carrier',carrier)]))
    base.finish(a,plan,spatial)
    save(BATCH/'production.json',{'status':'completed','resref':'OHRFEAR','phases':len(frames),'source_holes':source_holes,'phases_checked':checks,
         'existing_visible_rgb_identical':True,'outer_alpha_identical':True,'timing_geometry_carrier_identical':True,'qa':'pending-user-test'})
    sheet=Image.new('RGB',(800,3*430),(90,90,90));draw=ImageDraw.Draw(sheet)
    for row,(n,before,fixed) in enumerate(previews):
        for col,arr in enumerate((before,fixed)):
            im=Image.fromarray(arr);sheet.paste(im,(col*400,row*430+25),im)
            draw.text((col*400+5,row*430+5),f'phase {n}: '+('before' if col==0 else 'filled'),fill='white')
    sheet.save(BATCH/'comparison.png')
    print('OHRFEAR sealed, face hole filled; 90 phases, outer alpha/RGB/timing preserved',flush=True)


def probe(target, logname):
    exe=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
    with (OUT/logname).open('x',encoding='utf-8') as log:
        subprocess.run([str(exe),'--catalogue-only',str(target),str(PARENT/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)


def prepare():
    assert not (OUT/'plan.json').exists()
    OUT.mkdir(parents=True,exist_ok=True);CAND.mkdir(exist_ok=True)
    active=GAME/'iee-assets/effects';old=load(active/'manifest.json')
    assert sha(active/'manifest.json')==load(PARENT/'installation.json')['manifest_sha256']
    before={'manifest_sha256':sha(active/'manifest.json'),'preserved':{n:asdict(tx.snapshot_file(GAME/n)) for n in PRESERVE}}
    save(OUT/'before.json',before)
    files=[]
    def add(name,raw=None,source=None):
        dest=tx.managed_path(CAND,name,create_parents=True)
        assert not dest.exists()
        if source: shutil.copy2(source,dest)
        else: dest.write_bytes(raw)
        files.append({'name':name,**asdict(tx.snapshot_file(dest))})
    a=asset();raw,resource,frames,copies,_,_=builder.build_resource(a,'OHRFEAR',True)
    previous=next(r for r in old['resources'] if r['resref']=='OHRFEAR')
    assert resource['timeline']==previous['timeline'] and resource['frame_count']==previous['frame_count']
    assert resource['cycles']==previous['cycles']
    manifest=copy.deepcopy(old)
    i=manifest['resources'].index(previous);manifest['resources'][i]=resource
    old_frames=[f for f in old['frames'] if f['resref']=='OHRFEAR']
    assert len(old_frames)==len(frames)
    for source,name in copies: add('iee-assets/effects/'+name,source=source)
    for f,p in zip(frames,old_frames):
        assert f['resource_frame']==p['resource_frame'] and f['logical_size_x1']==p['logical_size_x1'] and f['source_centre_x1']==p['source_centre_x1']
        f['frame']=p['frame'];manifest['frames'][p['frame']]=f
    # Two additional controls isolate placement from RGB, alpha and blending.
    for n in (9,26):
        original=(GAME/f'override/Z26T{n:02d}.vvc').read_bytes();v=bytearray(original)
        struct.pack_into('<i',v,0x28,64)
        assert v[:0x28]+v[0x2c:]==original[:0x28]+original[0x2c:]
        name=f'override/Z26V{n:02d}.vvc';add(name,bytes(v))
        manifest['runtime_vvc_controllers'].append({'asset':name,'bam':v[8:16].rstrip(b'\0').decode(),
            'sha256':digest(v),'bytes':len(v),'purpose':'offset-only test 64 units away from actor; original Z26T retained'})
    manifest.setdefault('source_packs',[]).append({'resref':'OHRFEAR','pack':a['pack'],'manifest_sha256':sha(ROOT/a['pack']/'manifest.json'),'interpolation_run':a['interpolation_run'],'rgb_encoding':'straight'})
    assert [r for r in manifest['resources'] if r['resref']!='OHRFEAR']==[r for r in old['resources'] if r['resref']!='OHRFEAR']
    assert [f for f in manifest['frames'] if f['resref']!='OHRFEAR']==[f for f in old['frames'] if f['resref']!='OHRFEAR']
    add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    # Sparse candidate catalogue probe requires only the unchanged registry.
    registry=CAND/'iee-assets/effects/EffectAnimations-X4.registry';shutil.copy2(active/'EffectAnimations-X4.registry',registry)
    probe(CAND/'iee-assets/effects','candidate-native-loader.log')
    save(OUT/'plan.json',{'files':files,'manifest_sha256':sha(CAND/'iee-assets/effects/manifest.json'),
        'registry_unchanged':True,'other_resources_unchanged':252,'face_phases':90,'visibility_controls':['Z26V09','Z26V26'],'visual_qa':'pending-user-test'})
    print('READY',len(files),'targets',flush=True)


def rollback(receipt):
    for f in reversed(receipt['files']):
        dest=tx.managed_path(GAME,f['name'],create_parents=True)
        current=tx.optional_snapshot(dest);old=tx.FileSnapshot(**f['before']) if f['before'] else None
        expected=tx.FileSnapshot(f['bytes'],f['sha256'])
        assert current in (old,expected)
        if current==old: continue
        if old: tx.atomic_copy(OUT/'before'/f['name'],dest,old)
        else: tx.safe_unlink(dest,expected)
    receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt)


def install():
    assert not (OUT/'transaction.json').exists()
    tx.ensure_game_stopped(tx.running_game_processes)
    before,plan=load(OUT/'before.json'),load(OUT/'plan.json')
    assert sha(GAME/'iee-assets/effects/manifest.json')==before['manifest_sha256']
    assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
    (OUT/'before').mkdir(exist_ok=True);entries=[]
    for f in plan['files']:
        expected=tx.FileSnapshot(f['bytes'],f['sha256']);assert tx.snapshot_file(CAND/f['name'])==expected
        target=tx.managed_path(GAME,f['name']);old=tx.optional_snapshot(target)
        if old: tx.atomic_copy(target,tx.managed_path(OUT/'before',f['name'],create_parents=True),old)
        entries.append({**f,'before':asdict(old) if old else None})
    receipt={'status':'prepared','game_root':str(GAME),'files':entries,'created_utc':tx.utc_now()}
    tx.write_json_atomic(OUT/'transaction.json',receipt)
    try:
        for f in entries:
            target=tx.managed_path(GAME,f['name'],create_parents=True)
            assert tx.optional_snapshot(target)==(tx.FileSnapshot(**f['before']) if f['before'] else None)
            tx.atomic_copy(CAND/f['name'],target,tx.FileSnapshot(f['bytes'],f['sha256']))
        assert all(tx.snapshot_file(GAME/f['name'])==tx.FileSnapshot(f['bytes'],f['sha256']) for f in entries)
        assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
        assert sha(GAME/'iee-assets/effects/EffectAnimations-X4.registry')==load(GAME/'iee-assets/effects/manifest.json')['registry_sha256']
        probe(GAME/'iee-assets/effects','installed-native-loader.log')
        receipt['status']='installed';tx.write_json_atomic(OUT/'transaction.json',receipt)
    except Exception:
        rollback(receipt);raise
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        for r in rows:
            if r['asset_key']=='effects:bam:OHRFEAR': r.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'installation.json',{k:v for k,v in plan.items() if k!='files'}|{'status':'installed-offline-verified','qa_accepted':False,'game_launched':False,'dll_ini_character_profile_unchanged':True})
    print('INSTALLED OHRFEAR face fix +2 offset-only visibility controls',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['derive','prepare','install','restore']);args=p.parse_args()
    if args.action=='restore': tx.ensure_game_stopped(tx.running_game_processes);rollback(load(OUT/'transaction.json'))
    else: globals()[args.action]()
