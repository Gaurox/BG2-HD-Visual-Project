"""Remove consecutive native holds, Apollo-retime over the unchanged duration.

Runtime BAM carriers only add transparent padding. This lets the retimed poses
use their own native bounds even while the original slot was a 1x1 blank.
No native pixels, palette, lookup slots, world placement or FPS are changed.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
from fractions import Fraction

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_effect_interpolation as interpolation
import effect_workflow as workflow
from export_bam_frames import read_bam, cycle_metadata
from bam_export import decode_bam
from derive_animation_visual_treatment import apply_geometry_preserving_rgb_gaussian, apply_inner_contour_fade
from build_effect_runtime_pack import build_interpolated_pack_record, write_pack
from compose_effect_runtime_packs import validate_pack

TAG = 'lot33-retimed-20261014-v2'
BATCH = ROOT / 'effects/batches' / TAG
ORIGINAL = ROOT / 'effects/batches/lot33-seedvr7b-apollo30-20261014-v1/batch.json'


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, j):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(j, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rel(p):
    return p.relative_to(ROOT).as_posix()


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def prepare_geometry(a, spatial):
    raw = read_bam(ROOT / a['source'])
    dec, palette, tr = decode_bam(raw)
    cycles = cycle_metadata(raw, len(dec))
    cycle = cycles[0]['frame_indices']
    cw, ch = spatial['aligned_canvas_size_x1']
    identities = []
    for i, (idx, cx, cy, _) in enumerate(dec):
        aligned = np.full((ch, cw), tr, np.uint8)
        x, y = spatial['frames'][i]['canvas_offset_x1']
        aligned[y:y+idx.shape[0], x:x+idx.shape[1]] = idx
        # Identity is the native visible appearance at its world anchor.
        rgba = np.dstack((palette[aligned], (aligned != tr).astype(np.uint8)*255))
        rgba[rgba[:, :, 3] == 0] = 0
        identities.append(digest(rgba.tobytes()))
    keys = []
    for idx in cycle:
        if not keys or identities[idx] != identities[keys[-1]]:
            keys.append(idx)
    # SPIMPFR starts with 24 completely empty native records. Remove that
    # empty pre-roll as well: feathering its interpolation otherwise yields
    # two visually black output phases despite distinct alpha bytes.
    if a['resref']=='SPIMPFR':
        while keys and not np.any(dec[keys[0]][0]!=tr):keys.pop(0)
    assert len(keys) >= 2
    n = len(cycle)*2
    originals = [list(f['runtime_crop_box_xn']) for f in spatial['frames']]
    rects = copy.deepcopy(originals)
    phase_keys = []
    for phase in range(n):
        numer = phase*(len(keys)-1)
        left, rem = divmod(numer, n-1)
        right = min(left+1, len(keys)-1)
        phase_keys.append((keys[left], keys[right], rem/(n-1)))
        current = cycle[phase//2]
        for k in {keys[left], keys[right]}:
            r = originals[k]; box = rects[current]
            rects[current] = [min(box[0],r[0]), min(box[1],r[1]), max(box[2],r[2]), max(box[3],r[3])]
    # Rebuild BAM V1 without requantizing/replacing any source pixels.
    count, cc, _ = struct.unpack_from('<HBB', raw, 8)
    off_frames, off_palette, off_lookup = struct.unpack_from('<III', raw, 12)
    cycle_table = raw[off_frames+count*12:off_frames+count*12+cc*4]
    lookup_count = max(c['lookup_start']+len(c['frame_indices']) for c in cycles)
    lookup = raw[off_lookup:off_lookup+lookup_count*2]
    pal = raw[off_palette:off_palette+1024]
    of = 24; op = of+count*12+cc*4; ol = op+1024; cursor = ol+len(lookup)
    table = bytearray(); payload = []; runtime_centres = []
    for i, (idx, cx, cy, _) in enumerate(dec):
        l,t,r,b = [v//4 for v in rects[i]]
        ox,oy = spatial['frames'][i]['canvas_offset_x1']
        new = np.full((b-t,r-l), tr, np.uint8)
        x,y = ox-l,oy-t
        new[y:y+idx.shape[0],x:x+idx.shape[1]] = idx
        ncx,ncy = cx+x,cy+y
        runtime_centres.append([ncx,ncy])
        table.extend(struct.pack('<HHhhI',r-l,b-t,ncx,ncy,cursor|0x80000000))
        data = new.tobytes(); payload.append(data); cursor += len(data)
        # Prove world-space native fallback is byte-identical inside the common canvas.
        check = np.full((ch,cw), tr, np.uint8)
        check[t:b,l:r] = new
        expected = np.full((ch,cw),tr,np.uint8)
        expected[oy:oy+idx.shape[0],ox:ox+idx.shape[1]] = idx
        assert np.array_equal(check,expected), (a['resref'],i,'native pixels moved')
        assert [l+ncx,t+ncy] == [ox+cx,oy+cy]
    header = struct.pack('<8sHBBIII',b'BAM V1  ',count,cc,tr,of,op,ol)
    carrier = header+bytes(table)+cycle_table+pal+lookup+b''.join(payload)
    assert cycle_metadata(carrier,count) == cycles
    return keys, cycle, phase_keys, rects, runtime_centres, carrier


def produce(a):
    name = a['resref']; run_id = name.lower()+'-interpolation-apollo30-retimed-20261014-v2'
    resource = ROOT/'effects/ressources'/name
    destination = resource/'runs'/run_id
    pack_root = resource/'packs'/(name.lower()+'-7b-x4-apollo30-retimed-20261014-v2')
    report_path = BATCH/'checks'/(name+'.json')
    if report_path.exists():
        report = load(report_path)
        assert report['passed'] and validate_pack(pack_root).manifest_sha256 == report['pack_manifest_sha256']
        return report
    plan = interpolation.build_plan(ROOT,name,a['spatial_run'],run_id,'apollo8-native-holds-removed-duration-preserved',
        15,30,interpolation.DEFAULT_TVAI_FFMPEG,interpolation.DEFAULT_TVAI_MODEL_DIR,'apo-8','-2',loop_closed=False)
    spatial = interpolation.validate_spatial_manifest(plan)
    if plan.descriptor_path.exists() and load(plan.descriptor_path).get('result',{}).get('sealed'):
        return finish(a,plan,spatial)
    keys,cycle,phase_keys,rects,centres,carrier = prepare_geometry(a,spatial)
    n = len(cycle)*2
    rate = Fraction((len(keys)-1)*30,n-1)
    created = workflow.utc_now()
    recipe = interpolation.recipe_snapshot(plan)
    recipe.update(rgb_policy='Retained SeedVR7B x4 poses; Apollo8 on consecutive distinct native poses only',
        alpha_policy='Linear temporal coverage of aligned native masks; no generated alpha or spatial scaling',
        native_anchor_policy='Distinct poses span first to last output phase; native slot duration unchanged',
        input_fps=[rate.numerator,rate.denominator],keyframes=keys,
        sigma_x4=1.2,inner_feather_x4=12,rgb_encoding='premultiplied',
        runtime_bam_policy='Transparent padding only; original palette, pixels, centres in world space and cycles preserved',
        tools=[interpolation.evidence(ROOT,'producer',Path(__file__))])
    if not destination.exists():
        interpolation.reserve(plan)
    else:
        assert not load(plan.descriptor_path).get('result',{}).get('sealed'), 'Sealed run immutable'
    save(plan.recipe_path,recipe)
    def descriptor(status,sealed,outputs=(),notes=None):
        d=interpolation.descriptor(plan,recipe,status=status,sealed=sealed,created_at=created,outputs=outputs,notes=notes)
        d['pipeline']['version']='effect-retimed-holds-removed.v1'
        d['provenance']['generator']=rel(Path(__file__))
        return d
    save(plan.descriptor_path,descriptor('running',False))
    stage=destination/'02-interpolation'; inputs=stage/'input-rgb'; apollo=stage/'apollo-raw'; frames_root=stage/'frames-rgba'
    for p in (inputs,apollo,frames_root): p.mkdir(parents=True,exist_ok=True)
    images={}
    for k in set(keys):
        with Image.open(plan.spatial_manifest.parent/spatial['frames'][k]['aligned_rgba_xn']) as img:
            images[k]=np.asarray(img.convert('RGBA')).copy()
    for p in inputs.glob('in_*.png'):p.unlink()  # current unsealed working run only
    for i,k in enumerate(keys):
        Image.fromarray(images[k][:,:,:3]).save(inputs/f'in_{i:03d}.png')
    # Extra terminal input is discarded; the desired last phase lands on the real endpoint.
    Image.fromarray(images[keys[-1]][:,:,:3]).save(inputs/f'in_{len(keys):03d}.png')
    command=[str(plan.tvai_ffmpeg),'-hide_banner','-loglevel','error','-y','-framerate',str(rate),
        '-i',str(inputs/'in_%03d.png'),'-vf','tvai_fi=model=apo-8:fps=30:rdt=-0.01:device=-2',
        '-pix_fmt','rgb24',str(apollo/'out_%04d.png')]
    command_path=destination/'apollo-command.json'
    cached=command_path.exists() and load(command_path)=={'command':command}
    save(command_path,{'command':command})
    env=dict(os.environ,TVAI_MODEL_DIR=str(plan.tvai_model_dir),TVAI_MODEL_DATA_DIR=str(plan.tvai_model_dir))
    log=destination/'apollo.log'
    if not cached or not (destination/'apollo-completed.json').exists():
        for p in apollo.glob('out_*.png'):p.unlink()  # discard the unsealed attempt's temporal outputs
        with log.open('w',encoding='utf-8') as out:
            subprocess.run(command,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
        save(destination/'apollo-completed.json',{'completed_utc':workflow.utc_now()})
    produced=interpolation.parse_numbered_pngs(apollo)
    assert len(produced)>=n,(name,len(produced),n)
    records=[]; visible={}; duplicates=[]; empty=[]; flux=[]
    canvas=tuple(v*4 for v in spatial['aligned_canvas_size_x1'])
    for phase in range(n):
        left,right,fraction=phase_keys[phase]; g=cycle[phase//2]
        with Image.open(produced[phase]) as img: rgb=np.asarray(img.convert('RGB')).copy()
        if fraction==0: rgb=images[left][:,:,:3].copy()
        alpha=np.rint(images[left][:,:,3].astype(float)*(1-fraction)+images[right][:,:,3].astype(float)*fraction).astype(np.uint8)
        rgba=np.dstack((rgb,alpha)); rgba[alpha==0]=0
        # The treatment helper expects premultiplied RGB (native masks were binary historically).
        rgba[:,:,:3]=np.rint(rgba[:,:,:3].astype(float)*(alpha[:,:,None]/255)).astype(np.uint8)
        blurred=apply_geometry_preserving_rgb_gaussian(rgba,1.2)
        final,_=apply_inner_contour_fade(blurred,12,'premultiplied')
        final[final[:,:,3]==0]=0
        assert np.all(final[:,:,:3]<=final[:,:,3:4])
        l,t,r,b=rects[g]; crop=final[t:b,l:r].copy()
        outside=final.copy(); outside[t:b,l:r]=0
        assert not outside.any(),(name,phase,'temporal pixels clipped')
        image=Image.fromarray(crop); ph=frames_root/f'frame_{phase:03d}'
        image.save(ph.with_suffix('.png'),compress_level=3); data=crop.tobytes(); ph.with_suffix('.rgba').write_bytes(data)
        world_hash=digest(final.tobytes())
        if world_hash in visible: duplicates.append([visible[world_hash],phase])
        else: visible[world_hash]=phase
        if not np.any(final[:,:,:3]): empty.append(phase)
        flux.append(int(final[:,:,:3].sum()))
        records.append({'frame':phase,'alpha_source_frame':g,'geometry_source_frame':g,
            'temporal_source_frames':[left,right],'temporal_fraction':fraction,
            'logical_size_x1':[(r-l)//4,(b-t)//4],'physical_size_x4':[r-l,b-t],
            'centre_x1':centres[g],'runtime_crop_box_x4':[l,t,r,b],
            'rgba_x4':f'frames-rgba/{ph.name}.png','rgba_x4_sha256':workflow.sha256_file(ph.with_suffix('.png')),
            'raw_rgba_x4':f'frames-rgba/{ph.name}.rgba','raw_rgba_x4_sha256':digest(data),'bytes':len(data)})
    assert not duplicates,(name,'duplicate visible/world RGBA',duplicates)
    assert len(empty)<=1,(name,'repeated empty poses',empty)
    carrier_path=destination/'runtime-carrier'/f'{name}.bam';carrier_path.parent.mkdir(exist_ok=True);carrier_path.write_bytes(carrier)
    audit={'method':'SHA256 of complete anchored premultiplied RGBA, including blank phases; no exemptions',
        'exact_visible_duplicates':[],'unexpected_visible_duplicates':[],'native_hold_duplicates':[],
        'visible_phase_count':n-len(empty),'empty_phase_count':len(empty),'unique_rgba_frame_count':n,'stored_rgba_frame_count':n}
    manifest={'schema':interpolation.INTERPOLATION_SCHEMA,'status':'completed','created_utc':workflow.utc_now(),
        'resref':name,'scale':4,'rgb_encoding':'premultiplied','visual_treatment':recipe,
        'parent':{'spatial_run':a['spatial_run'],'run_descriptor':rel(plan.parent_descriptor),
          'run_descriptor_sha256':workflow.sha256_file(plan.parent_descriptor),'spatial_manifest':rel(plan.spatial_manifest),
          'spatial_manifest_sha256':workflow.sha256_file(plan.spatial_manifest)},
        'timing':{'native_fps':[15,1],'target_fps':[30,1],'native_cycle_slots':len(cycle),'timeline_phase_count':n,
          'native_frame_indices':list(range(0,n,2)),'timeline_frame_indices':list(range(n)),'loop_closed':False},
        'alpha_policy':recipe['alpha_policy'],'native_anchor_policy':recipe['native_anchor_policy'],
        'duplicate_audit':audit,'retiming':{'keyframes':keys,'removed_consecutive_native_holds':len(cycle)-len(keys),
          'input_fps':[rate.numerator,rate.denominator],'duration_seconds':len(cycle)/15,
          'endpoint':'last genuine pose at last presentation phase; no repeated terminal half-frame'},
        'runtime_carrier':{'path':rel(carrier_path),'sha256':digest(carrier),'native_world_pixels_preserved':True},'frames':records}
    save(stage/'manifest.json',manifest)
    outputs=[interpolation.evidence(ROOT,'interpolation-manifest',stage/'manifest.json'),
             interpolation.evidence(ROOT,'runtime-bam-carrier',carrier_path)]
    save(plan.descriptor_path,descriptor('completed',True,outputs))
    return finish(a,plan,spatial)


def finish(a,plan,spatial):
    name=a['resref']; stage=plan.interpolation_root; manifest=load(stage/'manifest.json')
    run_id=plan.run_id; n=len(manifest['frames']); keys=manifest['retiming']['keyframes']
    carrier_path=ROOT/manifest['runtime_carrier']['path']; carrier=carrier_path.read_bytes()
    pack_root=ROOT/'effects/ressources'/name/'packs'/(name.lower()+'-7b-x4-apollo30-retimed-20261014-v2')
    report_path=BATCH/'checks'/(name+'.json')
    registry,assets,timeline=build_interpolated_pack_record(name,manifest,stage)
    native=load(ROOT/spatial['source']['frame_manifest']); sd=load(plan.parent_descriptor)
    pack=write_pack(pack_root,b'IEEEFX4\0'+struct.pack('<IIII',2,4,1,0)+registry,assets,sd,native,spatial,
        registry_version=2,timeline=timeline,interpolation_descriptor=load(plan.descriptor_path))
    checked=validate_pack(pack_root)
    empty=[]; flux=[]
    for f in manifest['frames']:
        arr=np.frombuffer((stage/f['raw_rgba_x4']).read_bytes(),np.uint8).reshape(-1,4)
        value=int(arr[:,:3].sum());flux.append(value)
        if value==0:empty.append(f['frame'])
    slots=manifest['timing']['native_cycle_slots']
    report={'resref':name,'passed':True,'spatial_run':a['spatial_run'],'interpolation_run':run_id,'pack':rel(pack_root),
        'pack_manifest_sha256':checked.manifest_sha256,'runtime_bam':rel(carrier_path),'runtime_bam_sha256':digest(carrier),
        'native_cycle_slots':slots,'distinct_consecutive_keyframes':len(keys),'phases':n,'unique_anchored_rgba':n,
        'duration_seconds':slots/15,'duplicates':[],'empty_phases':empty,'native_world_pixels_preserved':True,
        'raw_bytes':sum(f['bytes'] for f in checked.frames),'minimum_rgb_flux':min(flux),'maximum_rgb_flux':max(flux)}
    save(report_path,report)
    workflow.register_run(ROOT,name,'interpolation',run_id,write=True)
    print(name,'PASS',n,'distinct phases,',slots-len(keys),'holds removed',flush=True)
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resref',action='append');args=parser.parse_args()
    batch=load(ORIGINAL);selected=[a for a in batch['assets'] if not args.resref or a['resref'] in args.resref]
    reports=[]
    for i,a in enumerate(selected,1):
        print(i,'/',len(selected),a['resref'],flush=True)
        reports.append(produce(a))
    save(BATCH/'production.json',{'schema':'bg2-effects-retimed-production-v1','reports':reports,'count':len(reports)})


if __name__=='__main__':main()
