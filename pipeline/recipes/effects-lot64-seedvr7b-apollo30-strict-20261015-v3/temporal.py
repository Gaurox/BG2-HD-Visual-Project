"""Apollo retiming per native cycle/mode; world geometry and durations retained.

No installation. Registry-v2 unused phase-table tails are padding, never extra
playback time: the native slot remains authoritative. Alternate playback modes
are retained explicitly when consumers use the same cycle both ways.
"""
from pathlib import Path
import argparse
import collections
import copy
from fractions import Fraction
import hashlib
import json
import os
import struct
import subprocess
import sys
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow
import run_effect_interpolation as interpolation
from bam_export import decode_bam
from export_bam_frames import read_bam, cycle_metadata
from derive_animation_visual_treatment import apply_geometry_preserving_rgb_gaussian, apply_inner_contour_fade
from build_effect_runtime_pack import write_pack
from compose_effect_runtime_packs import validate_pack

BATCH = ROOT / 'effects/batches/lot64-seedvr7b-apollo30-strict-20261015-v3'
HERE = Path(__file__).resolve().parent


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    workflow.atomic_write(p, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))


def rel(p):
    return p.relative_to(ROOT).as_posix()


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def distinct_keys(slots, identities, blank, closed):
    keys = [];seen=set()
    for g in slots:
        if identities[g] not in seen:
            keys.append(g)
            seen.add(identities[g])
    # Blank endpoint padding is removed with holds and its duration redistributed.
    # A wholly transparent control cycle is retained, not given invented motion.
    if any(not blank[k] for k in keys):
        while keys and blank[keys[0]]:
            keys.pop(0)
        while keys and blank[keys[-1]]:
            keys.pop()
    elif keys:
        keys=keys[:1]
    if closed and len(keys) > 1 and identities[keys[0]] == identities[keys[-1]]:
        keys.pop()
    return keys


def phase_sources(keys, count, closed):
    if len(keys) == 1:
        return [(keys[0], keys[0], 0.0)] * count
    denominator = count if closed else count - 1
    distance = len(keys) if closed else len(keys) - 1
    result = []
    for phase in range(count):
        left, rem = divmod(phase * distance, denominator)
        right = (left + 1) % len(keys) if closed else min(left + 1, len(keys) - 1)
        result.append((keys[left], keys[right], rem / denominator))
    return result


def cycle_modes(asset):
    """Resolve VVC onset/hold/release references; retain conflicting modes.

    VVC references are normally one-based, zeros select the implicit cycle0
    when no phases are supplied. Legacy all-three-phase zero-based controllers
    are normalized together. Orientation-based consumers cover all directions.
    Sources: IESDP VVC-v1; GemRB ScriptedAnimation phase interpretation.
    """
    count = len(asset['native_cycles'])
    modes = [set() for _ in range(count)]
    roles = [[] for _ in range(count)]
    for c in asset['consumers']:
        if c['owner_route'] != 'vvc':
            continue
        loop = c['loop'] == '1'
        raw = [int(v) for v in c['cycles'].split(';')]
        refs = [(v if v < 2**31 else v - 2**32) - 1 for v in raw]
        if refs[1] < 0 and refs[2] < 0:
            refs = [-1, max(refs[0], 0), -1]
        elif refs[2] >= 0:
            shift = max(0, -refs[0], -refs[1])
            refs = [v + shift for v in refs]
        oriented = int(c.get('orientations') or 0) > 1
        for role, g in zip(('introduction', 'duration', 'ending'), refs):
            if g < 0:
                continue
            targets = range(count) if oriented else [g]
            for k in targets:
                if 0 <= k < count:
                    value = loop and role == 'duration'
                    modes[k].add(value)
                    roles[k].append({'consumer': c['consumer_key'], 'role': role, 'closed': value})
    # Unreferenced BAM cycles remain autonomous, not concatenated or discarded.
    for k in range(count):
        if not modes[k]:
            modes[k].add(asset['playback'] == 'loop')
            roles[k].append({'consumer': 'unreferenced-native-cycle', 'role': 'retained', 'closed': asset['playback'] == 'loop'})
    return modes, roles


def geometry(asset, spatial):
    raw = read_bam(ROOT / asset['source'])
    dec, palette, tr = decode_bam(raw)
    cycles = cycle_metadata(raw, len(dec))
    assert cycles == asset['native_cycles']
    cw, ch = spatial['aligned_canvas_size_x1']
    identities, blank = [], []
    for i, (idx, _, _, _) in enumerate(dec):
        rgba = np.zeros((ch, cw, 4), np.uint8)
        x, y = spatial['frames'][i]['canvas_offset_x1']
        rgba[y:y+idx.shape[0], x:x+idx.shape[1], :3] = palette[idx]
        rgba[y:y+idx.shape[0], x:x+idx.shape[1], 3] = (idx != tr).astype(np.uint8) * 255
        rgba[rgba[:, :, 3] == 0] = 0
        identities.append(digest(rgba.tobytes()))
        blank.append(not np.any(rgba[:, :, :3]))
    rects = [list(f['runtime_crop_box_xn']) for f in spatial['frames']]
    originals = copy.deepcopy(rects)
    modes, roles = cycle_modes(asset)
    variants = []
    for cycle in cycles:
        c = cycle['cycle']; slots = cycle['frame_indices']; count = len(slots) * 2
        assert count > 0
        for closed in sorted(modes[c]):
            keys = distinct_keys(slots, identities, blank, closed)
            assert keys
            sources = phase_sources(keys, count, closed)
            name = f'cycle{c:03d}-' + ('loop' if closed else 'once')
            variants.append({'id': name, 'cycle': c, 'loop_closed': closed,
                             'native_slots': slots, 'phase_count': count,
                             'keyframes': keys, 'phase_sources': sources,
                             'native_roles': roles[c], 'constant_native_cycle': len(keys) == 1,
                             'transparent_native_cycle': all(blank[k] for k in keys),
                             'removed_native_slots': len(slots) - len(keys)})
            for phase, (left, right, _) in enumerate(sources):
                g = slots[phase // 2]
                for k in (left, right):
                    r = originals[k]; b = rects[g]
                    rects[g] = [min(b[0], r[0]), min(b[1], r[1]), max(b[2], r[2]), max(b[3], r[3])]
    # Transparent padding only, exactly as the accepted lot33 carrier policy.
    count, cc, _ = struct.unpack_from('<HBB', raw, 8)
    of, op, ol = struct.unpack_from('<III', raw, 12)
    cycle_table = raw[of+count*12:of+count*12+cc*4]
    lookup_count = max(c['lookup_start'] + len(c['frame_indices']) for c in cycles)
    lookup = raw[ol:ol+lookup_count*2]
    palette_bytes = raw[op:op+1024]
    nf = 24; npal = nf+count*12+cc*4; nl = npal+1024; cursor = nl+len(lookup)
    table = bytearray(); payload = []; centres = []
    for i, (idx, cx, cy, _) in enumerate(dec):
        l, t, r, b = [v//4 for v in rects[i]]
        ox, oy = spatial['frames'][i]['canvas_offset_x1']
        x, y = ox-l, oy-t
        padded = np.full((b-t, r-l), tr, np.uint8)
        padded[y:y+idx.shape[0], x:x+idx.shape[1]] = idx
        centres.append([cx+x, cy+y])
        table.extend(struct.pack('<HHhhI', r-l, b-t, cx+x, cy+y, cursor|0x80000000))
        data = padded.tobytes(); payload.append(data); cursor += len(data)
        expected = np.full((ch,cw), tr, np.uint8); expected[oy:oy+idx.shape[0],ox:ox+idx.shape[1]] = idx
        actual = np.full((ch,cw), tr, np.uint8); actual[t:b,l:r] = padded
        assert np.array_equal(expected, actual)
        assert [l+cx+x,t+cy+y] == [ox+cx,oy+cy]
    carrier = struct.pack('<8sHBBIII', b'BAM V1  ', count, cc, tr, nf, npal, nl) + bytes(table) + cycle_table + palette_bytes + lookup + b''.join(payload)
    assert cycle_metadata(carrier, count) == cycles
    return variants, rects, centres, carrier


def make_plan(a):
    # Reuse the generic descriptor authority, not its mono-cycle pixel path.
    resource = ROOT / 'effects/ressources' / a['resref']
    parent = resource / 'runs' / a['spatial_run'] / 'run.json'
    sd = load(parent)
    po = next(f for f in sd['outputs'] if f['role'] == 'spatial-manifest')
    return interpolation.InterpolationPlan(ROOT, a['resref'], {}, a['spatial_run'],
        a['interpolation_run'], resource / 'runs' / a['interpolation_run'], parent, po,
        ROOT / po['path'], 'apollo8-cycle-retimed-duration-preserved', 15, 30,
        interpolation.DEFAULT_TVAI_FFMPEG, interpolation.DEFAULT_TVAI_MODEL_DIR,
        'apo-8', '-2')


def apollo(plan, variant, images):
    folder = plan.interpolation_root / variant['id']
    inputs = folder / 'input-rgb'; outputs = folder / 'apollo-raw'
    for p in (inputs, outputs): p.mkdir(parents=True, exist_ok=True)
    keys = variant['keyframes']; count = variant['phase_count']
    if len(keys) == 1:
        return None
    closed = variant['loop_closed']
    rate = Fraction((len(keys) if closed else len(keys)-1)*30, count if closed else count-1)
    padded_keys = keys + (keys[:2] if closed else [keys[-1]])
    for i, k in enumerate(padded_keys):
        path = inputs / f'in_{i:03d}.png'
        if not path.exists(): Image.fromarray(images[k][:,:,:3]).save(path)
    command = [str(plan.tvai_ffmpeg), '-hide_banner', '-loglevel', 'error', '-y',
               '-framerate', str(rate), '-i', str(inputs/'in_%03d.png'),
               '-vf', 'tvai_fi=model=apo-8:fps=30:rdt=-0.01:device=-2',
               '-pix_fmt', 'rgb24', str(outputs/'out_%04d.png')]
    command_path = folder / 'apollo-command.json'
    if not (folder/'completed.json').exists():
        save(command_path, {'command':command,'input_fps':[rate.numerator,rate.denominator]})
        env = dict(os.environ, TVAI_MODEL_DIR=str(plan.tvai_model_dir), TVAI_MODEL_DATA_DIR=str(plan.tvai_model_dir))
        with (folder/'apollo.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        save(folder/'completed.json',{'completed_utc':workflow.utc_now()})
    else:
        assert load(command_path)['command'] == command
    files = interpolation.parse_numbered_pngs(outputs)
    assert len(files) >= count, (variant['id'],len(files),count)
    return files


def produce(a):
    report_path = BATCH/'checks'/(a['resref']+'.json')
    if report_path.exists(): return load(report_path)
    plan = make_plan(a); spatial = load(plan.spatial_manifest)
    if plan.descriptor_path.exists() and load(plan.descriptor_path).get('result',{}).get('sealed'):
        return finish(a,plan,spatial)
    variants, rects, centres, carrier = geometry(a,spatial)
    reservation=workflow.reservation_path(plan.run_root.parent.parent,plan.run_id)
    if not plan.descriptor_path.exists() and not reservation.exists(): interpolation.reserve(plan)
    if reservation.exists():
        assert load(reservation)['asset_id']=='effects:bam:'+a['resref']
    plan.run_root.mkdir(parents=True,exist_ok=True)
    created = workflow.utc_now()
    snapshot = plan.run_root / 'producer-source.py'
    if not snapshot.exists(): snapshot.write_bytes(Path(__file__).read_bytes())
    recipe = {'schema':interpolation.RECIPE_SCHEMA,'recipe_id':plan.recipe_id,'pipeline_id':interpolation.PIPELINE_ID,
              'model':'apo-8','spatial_model':'seedvr2_7b_int8_convrot.safetensors','scale':4,
              'native_fps':[15,1],'target_fps':[30,1],'sigma_x4':1.2,'inner_feather_x4':12,
              'rgb_encoding':'premultiplied','filter':'NEAREST',
              'alpha_policy':'linear temporal blend of nearest-enlarged aligned native masks; no generated coverage',
              'retiming':'all exact repeated native poses removed within each cycle, including nonconsecutive repeats; distinct poses stretched over unchanged native cycle duration; loop closing endpoint not emitted twice',
              'runtime_carrier':'transparent padding only; palette, world indices/pixels, native lookup and centres preserved',
              'native_control_exception':'wholly constant/transparent native cycle keeps its true content and duration',
              'tools':[interpolation.evidence(ROOT,'producer',snapshot)]}
    if plan.recipe_path.exists(): recipe = load(plan.recipe_path)
    else: save(plan.recipe_path,recipe)
    def descriptor(status,sealed,outputs=()):
        d=interpolation.descriptor(plan,recipe,status=status,sealed=sealed,created_at=created,outputs=outputs)
        d['pipeline']['version']='effect-multicycle-retimed-strict.v2';d['provenance']['generator']=rel(Path(__file__))
        return d
    save(plan.descriptor_path,descriptor('running',False))
    stage=plan.interpolation_root;frames_root=stage/'frames-rgba';frames_root.mkdir(parents=True,exist_ok=True)
    records=[];results=[]
    for v in variants:
        print(a['resref'],v['id'],len(v['keyframes']),'poses ->',v['phase_count'],'phases',flush=True)
        images={}
        for k in set(v['keyframes']):
            with Image.open(plan.spatial_manifest.parent/spatial['frames'][k]['aligned_rgba_xn']) as im: images[k]=np.asarray(im.convert('RGBA')).copy()
        files=apollo(plan,v,images)
        hashes=[];rgb_hashes=[];empty=[];indices=[]
        for phase,(left,right,fraction) in enumerate(v['phase_sources']):
            g=v['native_slots'][phase//2];l,t,r,b=rects[g]
            if fraction==0: rgb=images[left][:,:,:3].copy()
            else:
                with Image.open(files[phase]) as im:rgb=np.asarray(im.convert('RGB')).copy()
            alpha=np.rint(images[left][:,:,3].astype(np.float32)*(1-fraction)+images[right][:,:,3].astype(np.float32)*fraction).astype(np.uint8)
            rgba=np.dstack((rgb,alpha));rgba[alpha==0]=0
            rgba[:,:,:3]=np.rint(rgba[:,:,:3].astype(np.float32)*(alpha[:,:,None]/255)).astype(np.uint8)
            final,_=apply_inner_contour_fade(apply_geometry_preserving_rgb_gaussian(rgba,1.2),12,'premultiplied')
            final[final[:,:,3]==0]=0
            assert np.all(final[:,:,:3]<=final[:,:,3:4])
            assert not final[:t].any() and not final[b:].any() and not final[t:b,:l].any() and not final[t:b,r:].any()
            hashes.append(digest(final.tobytes()));rgb_hashes.append(digest(final[:,:,:3].tobytes()))
            if not final[:,:,:3].any():empty.append(phase)
            index=len(records);indices.append(index);crop=final[t:b,l:r].copy()
            stem=f'frame_{index:03d}';png=frames_root/(stem+'.png');raw=frames_root/(stem+'.rgba')
            Image.fromarray(crop).save(png,compress_level=3);raw.write_bytes(crop.tobytes())
            records.append({'frame':index,'cycle':v['cycle'],'mode':'loop' if v['loop_closed'] else 'once','phase':phase,
                'alpha_source_frame':g,'geometry_source_frame':g,'temporal_source_frames':[left,right],'temporal_fraction':fraction,
                'logical_size_x1':[(r-l)//4,(b-t)//4],'physical_size_x4':[r-l,b-t],
                'centre_x1':centres[g],'runtime_crop_box_x4':[l,t,r,b],
                'rgba_x4':'frames-rgba/'+png.name,'rgba_x4_sha256':workflow.sha256_file(png),
                'raw_rgba_x4':'frames-rgba/'+raw.name,'raw_rgba_x4_sha256':workflow.sha256_file(raw),'bytes':raw.stat().st_size,
                'anchored_rgba_sha256':hashes[-1],'anchored_rgb_sha256':rgb_hashes[-1]})
        adjacent=[i for i in range(1,len(hashes)) if rgb_hashes[i]==rgb_hashes[i-1]]
        seam=v['loop_closed'] and rgb_hashes[-1]==rgb_hashes[0]
        if not v['constant_native_cycle']:
            assert not adjacent,(a['resref'],v['id'],'adjacent visible duplicates',adjacent)
            assert not seam,(a['resref'],v['id'],'duplicate loop seam')
            assert len(empty)<=1,(a['resref'],v['id'],'blank visible phases',empty)
            assert len(set(rgb_hashes))==len(rgb_hashes),(a['resref'],v['id'],'repeated RGB pose anywhere in cycle',len(rgb_hashes)-len(set(rgb_hashes)))
            assert len(set(hashes))==len(hashes),(a['resref'],v['id'],'repeated RGBA pose anywhere in cycle')
        result={k:value for k,value in v.items() if k!='phase_sources'}
        result.update(timeline_frame_indices=indices,native_frame_indices=indices[::2],duration_seconds=len(v['native_slots'])/15,
                      unique_rgba=len(set(hashes)),unique_rgb=len(set(rgb_hashes)),adjacent_rgb_duplicates=adjacent,
                      loop_seam_duplicate=bool(seam),empty_phases=empty)
        results.append(result)
        save(stage/v['id']/'verification.json',result)
    carrier_path=plan.run_root/'runtime-carrier'/(a['resref']+'.bam');carrier_path.parent.mkdir(exist_ok=True);carrier_path.write_bytes(carrier)
    manifest={'schema':interpolation.INTERPOLATION_SCHEMA,'status':'completed','created_utc':workflow.utc_now(),
              'resref':a['resref'],'scale':4,'rgb_encoding':'premultiplied','visual_treatment':recipe,
              'parent':{'spatial_run':a['spatial_run'],'run_descriptor':rel(plan.parent_descriptor),
                        'run_descriptor_sha256':workflow.sha256_file(plan.parent_descriptor),'spatial_manifest':rel(plan.spatial_manifest),'spatial_manifest_sha256':workflow.sha256_file(plan.spatial_manifest)},
              'timing':{'native_fps':[15,1],'target_fps':[30,1],'preserve_native_cycles':True,'cycles':results},
              'runtime_carrier':{'path':rel(carrier_path),'sha256':digest(carrier),'native_world_pixels_preserved':True},'frames':records}
    save(stage/'manifest.json',manifest)
    outputs=[interpolation.evidence(ROOT,'interpolation-manifest',stage/'manifest.json'),interpolation.evidence(ROOT,'runtime-bam-carrier',carrier_path)]
    save(plan.descriptor_path,descriptor('completed',True,outputs))
    return finish(a,plan,spatial)


def finish(a,plan,spatial):
    stage=plan.interpolation_root;m=load(stage/'manifest.json');variants=m['timing']['cycles']
    primary=[];alternates=[]
    for c in a['native_cycles']:
        options=[v for v in variants if v['cycle']==c['cycle']]
        chosen=max(options,key=lambda v:v['loop_closed']);primary.append(chosen)
        alternates.extend(v['id'] for v in options if v is not chosen)
    # Deduplicate storage across cycles/modes only; each real cycle retains its
    # own exact 2*S playback phases. Registry tails are unreachable at S slots.
    assets=[];identities={};mapping=[]
    for f in m['frames']:
        identity=(f['raw_rgba_x4_sha256'],tuple(f['physical_size_x4']))
        if identity not in identities:
            index=len(assets);assert index<1000
            identities[identity]=index
            assets.append({'frame':index,'asset':f'EFX4-{a["resref"]}-frame{index:03d}.rgba',
                           'source':rel(stage/f['raw_rgba_x4']),'source_sha256':f['raw_rgba_x4_sha256'],
                           'sha256':f['raw_rgba_x4_sha256'],'bytes':f['bytes'],
                           'logical_size_x1':f['logical_size_x1'],'physical_size_x4':f['physical_size_x4'],
                           'source_centre_x1':f['centre_x1']})
        mapping.append(identities[identity])
    native=[[mapping[i] for i in v['native_frame_indices']] for v in primary]
    timeline=[[mapping[i] for i in v['timeline_frame_indices']] for v in primary]
    maximum=max(map(len,timeline));registry=bytearray(a['resref'].encode('ascii').ljust(8,b'\0'))
    registry.extend(struct.pack('<II',len(assets),len(native)))
    for f in assets:registry.extend(struct.pack('<II',*f['logical_size_x1']))
    for cycle in native:registry.extend(struct.pack(f'<I{len(cycle)}I',len(cycle),*cycle))
    registry.extend(struct.pack('<IIIII',15,1,30,1,maximum))
    for cycle in timeline:
        padded=cycle+[cycle[-1]]*(maximum-len(cycle));registry.extend(struct.pack(f'<{maximum}I',*padded))
    timing={'native_fps':[15,1],'target_fps':[30,1],'phase_count':maximum,
            'native_frame_indices_by_cycle':native,'timeline_frame_indices_by_cycle':timeline,
            'actual_phase_counts_by_cycle':list(map(len,timeline)),
            'cycle_profiles':[v['id'] for v in primary],'alternate_profiles':alternates,
            'unreachable_tail_policy':'v2 equal-width tables padded only beyond native slot count; no extra presented phase or duration'}
    pack_root=ROOT/a['pack']
    if not (pack_root/'manifest.json').exists():
        write_pack(pack_root,b'IEEEFX4\0'+struct.pack('<IIII',2,4,1,0)+bytes(registry),assets,
                   load(plan.parent_descriptor),load(ROOT/spatial['source']['frame_manifest']),spatial,
                   registry_version=2,timeline=timing,interpolation_descriptor=load(plan.descriptor_path))
    checked=validate_pack(pack_root)
    workflow.register_run(ROOT,a['resref'],'interpolation',a['interpolation_run'],write=True)
    report={'resref':a['resref'],'passed':True,'spatial_run':a['spatial_run'],'interpolation_run':a['interpolation_run'],
            'pack':a['pack'],'pack_manifest_sha256':checked.manifest_sha256,'native_cycles':len(a['native_cycles']),
            'cycle_mode_variants':len(variants),'phases':len(m['frames']),'backings':len(assets),
            'native_durations_preserved':True,'native_world_geometry_preserved':True,
            'visible_adjacent_duplicates':0,'alternate_playback_profiles':alternates,
            'transparent_control_cycles':[v['id'] for v in variants if v['transparent_native_cycle']],
            'runtime_carrier':m['runtime_carrier'],'raw_bytes':sum(f['bytes'] for f in assets)}
    save(BATCH/'checks'/(a['resref']+'.json'),report)
    print(a['resref'],'PASS',len(m['frames']),'phases',len(variants),'cycle/mode variants',flush=True)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--resref',action='append');p.add_argument('--wait-spatial',action='store_true');args=p.parse_args()
    assets=[a for a in load(BATCH/'batch.json')['assets'] if not args.resref or a['resref'] in args.resref]
    progress=load(BATCH/'temporal-progress.json') if (BATCH/'temporal-progress.json').exists() else {}
    failures=[]
    for i,a in enumerate(assets,1):
        print('temporal',i,'/',len(assets),a['resref'],flush=True)
        progress[a['resref']]={'state':'running','started_utc':workflow.utc_now()};save(BATCH/'temporal-progress.json',progress)
        try:
            if args.wait_spatial:
                deadline=time.monotonic()+21600
                parent=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'run.json'
                while not (parent.exists() and load(parent).get('result',{}).get('sealed')):
                    spatial_progress=ROOT/load(BATCH/'batch.json')['spatial_batch']/'spatial-progress.json'
                    state=load(spatial_progress).get(a['resref'],{}) if spatial_progress.exists() else {}
                    if state.get('state')=='failed':raise RuntimeError('spatial failed: '+state.get('error',''))
                    if time.monotonic()>deadline:raise RuntimeError('spatial wait exceeded six hours')
                    time.sleep(3)
            produce(a);progress[a['resref']]['state']='completed'
        except Exception as exc:
            failures.append(a['resref']);progress[a['resref']].update(state='failed',error=str(exc))
            print('FAILED',a['resref'],repr(exc),flush=True)
        save(BATCH/'temporal-progress.json',progress)
    print('Temporal failures:',failures,flush=True)
    return int(bool(failures))


if __name__=='__main__':raise SystemExit(main())
