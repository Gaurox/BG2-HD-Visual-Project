"""Produce the fifteen scoped Q3m x2/V7 witnesses from the acquired exact source plans."""
from __future__ import annotations
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
os.environ.setdefault('OMP_NUM_THREADS', '4')
import argparse
import csv
from collections import defaultdict, Counter
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import runpy
import struct
import time
import zlib
import numpy as np
from analyze_sprite_frame_dedup import ROOT, ro
from analyze_playable_frame_dedup import identities
from palette_q3m_partners import Profile
from palette_partner_registry import write as write_leaf, inspect as inspect_leaf
from palette_work_plan import file_sha, write_json
from run_creature_sprite_x2 import SourceFrame, run_xbr, direct_upscale_contract, map_output, xbr_provenance_indices
from reboutcx_batch import prepare_inference_rgb, load_model
from reboutcx_batch_p12 import infer_float_crops
from workspace_paths import get_path

SELECTION = ROOT/'sprite/index/q3m-family-witnesses.json'


def require(ok, message):
    if not ok: raise ValueError(message)


def save(path, **arrays):
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix('.part')
    with temporary.open('wb') as stream: np.savez_compressed(stream, **arrays)
    temporary.replace(path)


@contextmanager
def exclusive(root):
    import msvcrt
    root.mkdir(parents=True, exist_ok=True); lock = (root/'.writer.lock').open('a+b')
    lock.seek(0,2)
    if not lock.tell(): lock.write(b'\0'); lock.flush()
    lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    try: yield
    finally: lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1); lock.close()


def validate_selection(selection, complete_family=None):
    from analyze_native_sprite_families import KNOWN
    witnesses = selection['witnesses']
    if complete_family is None:
        require(len(witnesses) == len(KNOWN) and {w['family'] for w in witnesses} == set(KNOWN), 'one witness per native family required')
    else:
        require(complete_family in KNOWN and {w['family'] for w in witnesses} == {complete_family}, 'complete family scope differs')
    require(len({w['animation_id'] for w in witnesses}) == len(witnesses), 'duplicate witness animation')
    with (ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig',newline='') as stream:
        inventory = {r['animation_id']:r for r in csv.DictReader(stream)}
    if complete_family:
        expected = {aid for aid,row in inventory.items() if row['engine_section'] == complete_family}
        require({w['animation_id'] for w in witnesses} == expected, 'complete family animation coverage differs')
        with (ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig',newline='') as stream:
            source_items = {r['animation_id']:r for r in csv.DictReader(stream)}
        for witness in witnesses:
            refs = source_items[witness['animation_id']]['bam_resrefs'].split(';')
            require(refs != [''] and len(witness['refs']) == len(set(refs)) and set(witness['refs']) == set(refs), 'complete family BAM coverage differs')
    for witness in witnesses:
        native = inventory[witness['animation_id']]
        require(native['engine_section'] == witness['family'] and KNOWN[witness['family']][0] == witness['owner'], 'witness owner/family differs from source')
        require(native['false_color'] == '' or int(native['false_color']) == witness['native_kind'], 'witness palette kind differs from INI')
        if witness['family'] == 'multi_new':
            # Stock dragon resrefs: prefix + bank + PART(1..9) + chunk + direction.
            # Nine direction suffixes of part 1 are not a nine-part native draw.
            groups = witness.get('multipart_groups',[])
            require(groups and set(witness['refs']) == {ref for group in groups for ref in group}, 'missing multipart groups')
            for group in groups:
                require(len(group) == 9 and len(set(group)) == 9 and all(len(ref) == 8 for ref in group), 'dragon needs nine distinct parts')
                require({ref[5] for ref in group} == set('123456789') and len({ref[:5]+ref[6:] for ref in group}) == 1, 'dragon part/bank/chunk/direction group differs')
    return witnesses


def source_plan(selection_path=SELECTION, complete_family=None):
    selection_path = Path(selection_path)
    selection = json.loads(selection_path.read_text(encoding='utf-8'))
    witnesses = validate_selection(selection,complete_family)
    pointers = {name:json.loads((ROOT/path).read_text()) for name,path in (
        ('character','sprite/index/palette-work-plan.json'),('other','sprite/index/q3m-source-work-plan.json'))}
    databases = {}
    for name, pointer in pointers.items():
        path = ROOT/pointer['path']; require(path.stat().st_size == pointer['bytes'] and file_sha(path).lower() == pointer['sha256'].lower(), 'source plan identity changed')
        databases[name] = ro(path)
    character_fits = np.stack([np.frombuffer(r['rgb_u8_256x3'],np.uint8).reshape(256,3) for r in databases['character'].execute('SELECT * FROM profile_palettes ORDER BY palette_ordinal')])
    # Reuse the pinned native arithmetic oracle, with fresh input/output only.
    oracle_module = runpy.run_path(str(ROOT/'docs/measurements/q3m-monster-contract-x2-20261002-v1/build_contract.py'))
    exe = (get_path('bg2ee_game_root',required=True)/'BaldurReal.exe').read_bytes()
    oracle = oracle_module['NativeFixed'](exe)
    profiles, works, resources, source_keys = {}, {}, [], set()
    for witness in selection['witnesses']:
        char = witness['family'] == 'character'; db = databases['character' if char else 'other']
        for ref in witness['refs']:
            resource = db.execute('SELECT * FROM resources WHERE resref=?',(ref,)).fetchone(); require(resource is not None, 'missing source '+ref)
            rid = resource['resource_id']; p = np.frombuffer(resource['palette_bgra'],np.uint8).reshape(256,4)
            if char:
                membership = db.execute('SELECT 1 FROM model_resources JOIN models USING(model_id) WHERE resource_id=? AND animation_id=?',(rid,witness['animation_id'])).fetchone()
            else: membership = db.execute('SELECT 1 FROM animation_resources WHERE resource_id=? AND animation_id=?',(rid,witness['animation_id'])).fetchone()
            require(membership is not None, 'source is outside witness animation '+ref)
            key = (witness['native_kind'],p.tobytes())
            if key not in profiles:
                if witness['native_kind'] == 1: fits = character_fits
                else:
                    fits_list = []
                    for _,flags,tint in oracle_module['FITS']:
                        actual = oracle.realize(p,flags,tint)
                        expected = oracle_module['expected_palette'](p,flags,tint)
                        require(np.array_equal(actual,expected), 'native fixed palette oracle differs')
                        fits_list.append(actual[:,:3])
                    fits = np.stack(fits_list)
                profiles[key] = Profile(witness['native_kind'],p,fits)
            profile = profiles[key]
            queue = 'processing_queue' if char else 'source_work_queue'
            frames = []
            for row in db.execute(f'SELECT f.*,q.* FROM frames f JOIN {queue} q USING(work_id) WHERE f.resource_id=? ORDER BY f.frame_index',(rid,)):
                w,h = row['width'],row['height']; require(0 < w*h < 65535 and row['transparent_index'] == 0, 'source geometry contract')
                indices = np.frombuffer(zlib.decompress(row['indices_zlib']),np.uint8).reshape(h,w).copy()
                rgb = p[:,[2,1,0]].copy(); rgba = np.dstack((rgb[indices],np.where(indices == 0,0,255).astype(np.uint8))).tobytes()
                frame = SourceFrame(ref,row['frame_index'],w,h,row['center_x'],row['center_y'],0,indices,rgb,rgba)
                input_key, source_key, _, _, _ = identities(indices,rgb,0)
                expected_key = row['work_key'] if char else bytes.fromhex(row['source_work_key'])
                if isinstance(expected_key,str): expected_key = bytes.fromhex(expected_key)
                require(source_key == expected_key, f'source work identity differs {ref}/{row["frame_index"]}: {source_key.hex()} vs {expected_key.hex()}')
                source_keys.add(source_key.hex())
                encoded_key = hashlib.sha256(bytes.fromhex(profile.identity)+source_key).hexdigest()
                if encoded_key in works:
                    old = works[encoded_key]['frame']
                    require(np.array_equal(old.indices,indices) and np.array_equal(old.palette[indices],rgb[indices]), 'source hash collision')
                else: works[encoded_key] = dict(frame=frame,profile=profile,input_key=input_key.hex(),source_key=source_key.hex())
                frames.append(dict(key=encoded_key,geometry=(w,h,row['center_x'],row['center_y'],0),frame_index=row['frame_index']))
            cycles = [list(struct.unpack(f"<{c['slot_count']}H",c['frame_indices_le_u16'])) for c in db.execute('SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index',(rid,))]
            require(len(frames) == resource['frame_count'] and len(cycles) == resource['cycle_count'], 'native coverage incomplete')
            resources.append(dict(witness=witness,resref=ref,source_sha256=resource['canonical_sha256'],frames=frames,cycles=cycles,profile=profile))
    for db in databases.values(): db.close()
    witness_summary = []
    for witness in witnesses:
        keys = {f['key'] for r in resources if r['witness'] is witness for f in r['frames']}
        witness_summary.append(dict(witness,physical_frames=sum(len(r['frames']) for r in resources if r['witness'] is witness),
                                    source_work=len({works[k]['source_key'] for k in keys}),encoded_work=len(keys)))
    summary = dict(schema='bg2-q3m-family-witness-work-plan-v1',selection_sha256=file_sha(selection_path),families=len({w['family'] for w in witnesses}),resources=len(resources),physical_frames=sum(len(r['frames']) for r in resources),unique_source_work=len(source_keys),unique_encoded_work=len(works),native_oracle='pinned CVidPalette type0 Realize; K6 byte comparison; type1 acquired Character K6',witnesses=witness_summary,source_plans=pointers)
    if complete_family: summary['complete_family'] = complete_family
    return resources,works,summary


def produce(resources, works, root):
    from reboutcx_multipal import inference_context
    backend_path = root/'backend.json'
    if backend_path.exists():
        backend = json.loads(backend_path.read_text()); require(file_sha(get_path('reboutcx_model',required=True)) == backend['model_sha256'], 'model changed')
        import importlib.metadata
        for name,version in backend['dependencies'].items(): require(importlib.metadata.version(name) == version,'backend dependency changed')
        for name,digest in backend['kernels'].items(): require(file_sha(ROOT/'pipeline/scripts'/name) == digest,'inference kernel changed')
        require(importlib.metadata.version('torch') == backend['torch'], 'Torch changed')
    else: backend = inference_context(); write_json(backend_path,backend)
    backend_key = hashlib.sha256(json.dumps(backend,sort_keys=True).encode()).digest()
    encoder_key = file_sha(Path(__file__).with_name('palette_q3m_partners.py'))
    directory = root/'encoded'/encoder_key; directory.mkdir(parents=True,exist_ok=True)
    scalepix = get_path('mmpx_scalepix',required=True)
    guide_namespace = hashlib.sha256((file_sha(scalepix)+file_sha(ROOT/'pipeline/scripts/xbr2x_batch.js')+file_sha(ROOT/'pipeline/scripts/run_creature_sprite_x2.py')).encode()).hexdigest()
    guide_dir = root/'guides'/guide_namespace
    stats = Counter(); missing_guides = {}
    for key,work in works.items():
        path = directory/(key+'.npz'); work['encoded_path'] = path
        if path.exists():
            with np.load(path,allow_pickle=False) as data:
                require(set(data.files) == {'guide','I','F','dep'},'encoded members differ')
                arrays = {n:data[n].copy() for n in data.files}
            shape = (work['frame'].height*2,work['frame'].width*2)
            require(all(arrays[n].dtype == np.uint8 and arrays[n].shape == shape for n in ('guide','I','F')),'cached planes differ')
            work['profile'].validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep']); stats['encoded_cache_hits'] += 1
        else:
            guide = guide_dir/(work['source_key']+'.npz'); work['guide_path'] = guide
            if not guide.exists(): missing_guides.setdefault(work['source_key'],work['frame'])
    keys = list(missing_guides)
    for start in range(0,len(keys),64):
        batch_keys = keys[start:start+64]; frames = [missing_guides[k] for k in batch_keys]
        # xBR is only a semantic index guide; it is never a final sprite treatment.
        outputs = run_xbr(frames,scalepix,'node',direct_upscale_contract(2))
        for key,frame,output in zip(batch_keys,frames,outputs,strict=True):
            indices,_ = map_output(frame,output[2],xbr_provenance_indices(frame,2))
            save(guide_dir/(key+'.npz'),guide=indices.reshape(frame.height*2,frame.width*2)); stats['new_guides'] += 1
        print(json.dumps(dict(stage='guides',done=min(start+64,len(keys)),total=len(keys))),flush=True)
    requests, pending = {}, []
    for key,work in works.items():
        if work['encoded_path'].exists(): continue
        with np.load(work['guide_path'],allow_pickle=False) as data: guide = data['guide'].copy()
        frame = work['frame']; require(np.isin(guide,np.unique(frame.indices)).all(),'guide uses absent source index')
        profile = work['profile']; work['guide'] = guide
        if not np.any(profile.classes[guide] >= (3 if profile.kind == 0 else 4)):
            f = np.zeros_like(guide); save(work['encoded_path'],guide=guide,I=guide.copy(),F=f,dep=profile.dependencies(guide,f)); stats['special_work'] += 1; continue
        work['targets'] = []; pending.append(work)
        used = np.unique(frame.indices[frame.indices != 0])
        for palette in profile.fitting:
            # Byte-exact source indices/mask and only RGB entries affecting this input.
            target_key = hashlib.sha256(backend_key+bytes.fromhex(work['input_key'])+used.tobytes()+palette[used].tobytes()).hexdigest()
            path = root/'targets'/target_key[:2]/(target_key+'.npz'); work['targets'].append(path)
            if not path.exists():
                old = requests.setdefault(target_key,(path,frame,palette))
                require(np.array_equal(old[1].indices,frame.indices) and np.array_equal(old[2][used],palette[used]),'neural input hash collision')
            else: stats['target_cache_hits'] += 1
    if requests:
        # No Torch/processor/model construction occurs on an all-hit resume.
        import torch
        from chainner_ext import resize, ResizeFilter
        require(inference_context() == backend,'GPU backend changed')
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8'); torch.set_num_threads(4)
        torch.backends.cudnn.deterministic = True; torch.use_deterministic_algorithms(True)
        descriptor,_ = load_model(get_path('reboutcx_model',required=True),device='cuda:0',fp16=True)
        groups = defaultdict(list)
        for request in requests.values():
            frame = request[1]; canvas = (((frame.height+31)//32)*32,((frame.width+31)//32)*32)
            groups[canvas].append(request)
        done = 0
        for canvas,group in sorted(groups.items()):
            for start in range(0,len(group),86):
                batch = group[start:start+86]; images = [prepare_inference_rgb(frame,palette) for _,frame,palette in batch]
                require(all(image is not None for image in images),'transparent model work')
                crops,_ = infer_float_crops(descriptor,images,canvas=canvas,fp16=True)
                for (path,frame,_),crop in zip(batch,crops,strict=True):
                    target = np.ascontiguousarray(np.clip(resize(crop,(frame.width*2,frame.height*2),ResizeFilter.Box,False),0,1),dtype=np.float32)
                    save(path,target=target)
                done += len(batch); stats['new_neural_targets'] += len(batch)
                print(json.dumps(dict(stage='neural-targets',done=done,total=len(requests))),flush=True)
        del descriptor
    from concurrent.futures import ThreadPoolExecutor
    def encode(work):
        targets = []
        for path in work['targets']:
            with np.load(path,allow_pickle=False) as data: target = data['target'].copy()
            require(target.dtype == np.float32 and target.shape == (*work['guide'].shape,3),'target cache differs'); targets.append(target)
        arrays = work['profile'].encode(work['guide'],np.stack(targets)); save(work['encoded_path'],**arrays)
        return 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        for done,_ in enumerate(pool.map(encode,pending),1):
            stats['new_encoded_work'] += 1
            if done % 32 == 0 or done == len(pending): print(json.dumps(dict(stage='encoding',done=done,total=len(pending))),flush=True)
    return dict(stats),directory


def pack(resources,works,output):
    from run_creature_sprite_x2 import catalog_shard_filename,catalog_shard_entry_bytes,catalog_component_digest,catalog_directory_digest
    require(not output.exists(),'fresh immutable pack destination required'); output.mkdir(parents=True)
    infos,components,directory,animations = [],[],[],{}
    oracle = bytearray(struct.pack('<8sI',b'IEEQP7\0\0',len(resources)))
    for ordinal,resource in enumerate(resources):
        material = dict(resref=resource['resref'],source_sha256=resource['source_sha256'],frames=[],cycles=resource['cycles'])
        profile = resource['profile']; witness = resource['witness']; aid = int(witness['animation_id'],16)
        palettes = []
        for rgb in profile.fitting:
            alpha = np.full(256,255,np.uint8); alpha[0] = 0; alpha[1] = 127
            palette = np.column_stack((rgb,alpha))
            # CVidCell clears the entire transparent entry after Realize.
            # Pixel oracle is at the draw boundary, not the Realize return.
            palette[0] = 0
            palettes.append(palette)
        oracle.extend(struct.pack('<II8sII',aid,witness['owner'],resource['resref'].encode().ljust(8,b'\0'),len(resource['frames']),len(resource['cycles'])))
        for palette in palettes: oracle.extend(palette.tobytes())
        oracle.extend(profile.metadata())
        for cycle in resource['cycles']: oracle.extend(struct.pack('<I',len(cycle))+struct.pack(f'<{len(cycle)}I',*cycle))
        for row in resource['frames']:
            work = works[row['key']]
            with np.load(work['encoded_path'],allow_pickle=False) as data: arrays = {name:data[name].copy() for name in data.files}
            profile.validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep'])
            reps = np.full(256,0xffff,np.uint16); values,offsets = np.unique(work['frame'].indices,return_index=True); reps[values] = offsets
            material['frames'].append(dict(geometry=row['geometry'],representatives=reps,**arrays))
            w,h,cx,cy,_ = row['geometry']; oracle.extend(struct.pack('<IIii',w,h,cx,cy))
            for palette in palettes: oracle.extend(hashlib.sha256(profile.decode(arrays['I'],arrays['F'],palette).tobytes()).digest())
        leaf = output/(resource['resref']+'.registry'); info = write_leaf(leaf,[material],profile)
        sealed = output/catalog_shard_filename(info['sha256']); leaf.replace(sealed); infos.append(info)
        entry = catalog_shard_entry_bytes(info,output); digest = catalog_component_digest(2,[entry])
        components.append(dict(index=ordinal,digest=digest,shard_start=ordinal,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=info['registry_bytes']))
        animations.setdefault(aid,dict(owner=witness['owner'],components=[]))['components'].append(ordinal)
        directory.append((aid,resource['resref'],ordinal,ordinal,0))
    memberships, animation_raw = [],bytearray()
    for aid,animation in sorted(animations.items()):
        start = len(memberships); memberships.extend(animation['components']); animation_raw.extend(struct.pack('<4I',aid,animation['owner'],start,len(animation['components'])))
    directory_raw = b''.join(struct.pack('<I8sIII',a,r.encode().ljust(8,b'\0'),c,s,o) for a,r,c,s,o in sorted(directory))
    totals = [sum(i[n] for i in infos) for n in ('resource_count','frame_count','index_bytes','registry_bytes')]
    raw = bytearray(struct.pack('<8s6I4Q',b'IEECSNC\0',2,2,len(animations),len(components),len(memberships),len(infos),*totals))
    raw.extend(struct.pack('<II32s',len(directory),24,bytes.fromhex(catalog_directory_digest(2,directory_raw))))
    raw.extend(animation_raw); raw.extend(struct.pack(f'<{len(memberships)}I',*memberships))
    for component in components:
        raw.extend(struct.pack('<32s4I3Q',bytes.fromhex(component['digest']),component['shard_start'],1,1,0,component['frame_count'],component['index_bytes'],component['registry_bytes']))
    for info in infos: raw.extend(catalog_shard_entry_bytes(info,output))
    raw.extend(directory_raw); (output/'CreatureSprites-XN.catalog').write_bytes(raw); (output/'witnesses.oracle').write_bytes(oracle)
    report = dict(schema='bg2-q3m-family-witness-pack-v1',scale=2,registry_version=7,catalog_version=2,animation_count=len(animations),resources=totals[0],frames=totals[1],index_bytes=totals[2],registry_bytes=totals[3],catalog_sha256=hashlib.sha256(raw).hexdigest(),oracle_sha256=hashlib.sha256(oracle).hexdigest(),oracle_palette_stage='post-CVidCell-transparent-entry-clear',leaves=infos,ingame_validated=False)
    write_json(output/'pack.json',report); return report


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=('plan','run','pack')); parser.add_argument('--cache',type=Path,required=True); parser.add_argument('--output',type=Path)
    parser.add_argument('--selection',type=Path,default=SELECTION); parser.add_argument('--complete-family')
    args = parser.parse_args(); args.cache = args.cache.resolve(); args.cache.mkdir(parents=True,exist_ok=True)
    if args.output: args.output = args.output.resolve()
    resources,works,summary = source_plan(args.selection,args.complete_family); print(json.dumps(dict(stage='plan',**{k:summary[k] for k in ('families','resources','physical_frames','unique_source_work','unique_encoded_work')})),flush=True)
    with exclusive(args.cache):
        if args.command == 'plan':
            if args.output: write_json(args.output,summary)
        elif args.command == 'run':
            stats,directory = produce(resources,works,args.cache); write_json(args.cache/'production.json',dict(plan=summary,stats=stats,encoded_directory=str(directory.relative_to(ROOT)))); print(json.dumps(stats),flush=True)
        else:
            require(args.output is not None,'--output required')
            directory = args.cache/'encoded'/file_sha(Path(__file__).with_name('palette_q3m_partners.py'))
            for key,work in works.items(): work['encoded_path'] = directory/(key+'.npz')
            print(json.dumps(pack(resources,works,args.output)),flush=True)


if __name__ == '__main__': main()
