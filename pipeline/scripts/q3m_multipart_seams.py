"""Q3m x2 contextual tile seams. Invoked automatically by q3m_family_witnesses.

Fixed palettes/native ramps K6: assemble before RGB fill/inference; preserve
native draws and guides; encode only body pixels within four native pixels.
Historical witness producers remain immutable; this module owns new caches.
"""
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
os.environ.setdefault('OMP_NUM_THREADS', '4')
import numpy as np


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def context_plan(resources, selection):
    source = {(r['witness']['animation_id'], r['resref']): r for r in resources}
    contexts, bindings = {}, {}
    for witness in selection['witnesses']:
        if witness['family'] not in ('monster_quadrant', 'multi_new') and not witness.get('multipart_groups'):
            continue
        groups = witness.get('multipart_groups')
        if not groups and witness['family'] == 'monster_quadrant':
            # Legacy four-part pilot selection; preserve its source bytes.
            grouped = {}
            for ref in witness['refs']:
                stem = ref[:-1] if not ref.endswith('E') else ref[:-2]
                grouped.setdefault((stem, ref.endswith('E')), []).append(ref)
            groups = [sorted(refs) for refs in grouped.values()]
            if any(len(refs) != 4 or
                   {ref[-2] if ref.endswith('E') else ref[-1] for ref in refs} != set('1234')
                   for refs in groups):
                raise ValueError('Quadrant group does not contain native parts 1..4')
        if not groups:
            raise ValueError('Tiled sprite requires explicit native multipart_groups')
        for refs in groups:
            if len(refs) < 2 or len(set(refs)) != len(refs):
                raise ValueError('Invalid native tile group')
            parts = [source[(witness['animation_id'], ref)] for ref in refs]
            if any(r['profile'].kind not in (0, 1) or len(r['profile'].fitting) != 6 for r in parts):
                raise ValueError('Contextual seams require compatible native K6 palettes')
            if any(not np.array_equal(r['profile'].fitting, parts[0]['profile'].fitting) for r in parts):
                raise ValueError('Different native tile palettes require a new contextual contract')
            for seq in range(min(len(r['cycles']) for r in parts)):
                for slot in range(min(len(r['cycles'][seq]) for r in parts)):
                    indices = [r['cycles'][seq][slot] for r in parts]
                    if any(i >= len(r['frames']) for r, i in zip(parts, indices)):
                        continue
                    rows = [r['frames'][i] for r, i in zip(parts, indices)]
                    key = digest([(row['key'], row['geometry']) for row in rows])
                    contexts.setdefault(key, dict(nodes=list(zip(parts, rows)),
                        geometry=[row['geometry'] for row in rows]))
                    for part, (resource, row) in enumerate(zip(parts, rows)):
                        binding = (witness['animation_id'], resource['resref'], row['frame_index'])
                        if binding in bindings and bindings[binding] != (key, part):
                            raise ValueError('Frame aliases different neighbours; split frame/cycle bindings before encoding')
                        bindings[binding] = (key, part)
    return contexts, bindings


def strength(a, geometry):
    """Exact validated feather: clip((4-distance)/3, 0, 1), x2 pixel centres."""
    h, w = a[1]*2, a[0]*2
    yy, xx = np.mgrid[:h, :w]
    wx, wy = -a[2]+(xx+.5)/2, -a[3]+(yy+.5)/2
    distance = np.full((h, w), np.inf)
    for b in geometry:
        if b is a or not b[0]*b[1]:
            continue
        bx, by = -b[2], -b[3]
        br, bt = bx+b[0], by+b[1]
        if -a[2]+a[0] == bx or br == -a[2]:
            cut = bx if -a[2]+a[0] == bx else br
            overlap = (wy >= max(-a[3], by)) & (wy < min(-a[3]+a[1], bt))
            distance = np.minimum(distance, np.where(overlap, abs(wx-cut), np.inf))
        if -a[3]+a[1] == by or bt == -a[3]:
            cut = by if -a[3]+a[1] == by else bt
            overlap = (wx >= max(-a[2], bx)) & (wx < min(-a[2]+a[0], br))
            distance = np.minimum(distance, np.where(overlap, abs(wy-cut), np.inf))
    return np.clip((4-distance)/3, 0, 1)


def repair_part(args):
    """Independent native cell, exact feather/codec; writes its own context key."""
    from palette_work_plan import file_sha
    from q3m_family_witnesses import save, validate_encoded
    item, context = args
    part, r, row, old, weight, roi = item
    targets, left, top, recipe_key, ck, work, works, old_targets = context
    node = dict(parent_key=row['key'], encoded_key=row['key'], changed_pixels=0)
    if roi.any():
        a = row['geometry']; x, y = -a[2]-left, -a[3]-top
        crop = targets[:, y*2:y*2+a[1]*2, x*2:x*2+a[0]*2][:, roi, :]
        blend = (old_targets(works[row['key']], roi)*(1-weight[roi][None, :, None])+
            crop*weight[roi][None, :, None]).astype(np.float32)
        from q3m_guarded_gpu_encode import encode
        encoded = encode(r['profile'],old['guide'][roi][None, :], blend[:, None, :, :])
        result = {k: v.copy() for k, v in old.items()}
        result['I'][roi], result['F'][roi] = encoded['I'][0], encoded['F'][0]
        result['dep'] = r['profile'].dependencies(result['I'], result['F'])
        validate_encoded(r['profile'], result['I'], result['F'], result['guide'], result['dep'])
        assert np.array_equal(result['I'][~roi], old['I'][~roi])
        assert np.array_equal(result['F'][~roi], old['F'][~roi])
        node['changed_pixels'] = int(((result['I'] != old['I']) | (result['F'] != old['F'])).sum())
        if node['changed_pixels']:
            key = digest([recipe_key, ck, part, row['key']]); dest = work/'encoded'/(key+'.npz')
            if dest.exists():
                with np.load(dest, allow_pickle=False) as z:
                    assert all(np.array_equal(z[k], v) for k, v in result.items())
            else:
                save(dest, **result)
            node.update(encoded_key=key, encoded_sha256=file_sha(dest))
    return node


def apply_context(resources, works, selection_path, cache, mode='run'):
    """plan=CPU, run=resume/infer missing contexts, bind=read sealed checkpoints.

    Parent encoded/targets remain read-only. New keys include full ordered
    context, geometry, recipe/backend/profile; orphan frames stay acquired.
    """
    from palette_work_plan import file_sha, write_json
    from q3m_family_witnesses import save, validate_encoded, load_model
    from workspace_paths import get_path
    cache = Path(cache)
    contexts, bindings = context_plan(resources, load(selection_path))
    report = dict(contexts=len(contexts), referenced_native_frames=len(bindings),
        unreferenced_native_frames=sum(len(r['frames']) for r in resources
            if r['witness']['family'] in ('monster_quadrant', 'multi_new') or
            r['witness'].get('multipart_groups'))-len(bindings),
        context_cache_hits=0, new_neural_targets=0, changed_encoded_pixels=0,
        changed_outside_band=0, band_native_pixels=4, scale=2, SDF=False)
    if not contexts or mode == 'plan':
        return report
    backend = load(cache/'backend.json')
    backend_key = bytes.fromhex(digest(backend))
    encoder = file_sha(Path(__file__).with_name('palette_q3m_partners.py'))
    recipe = dict(schema='bg2-q3m-multipart-contextual-seams-v1',
        selection_sha256=file_sha(selection_path), producer_sha256=file_sha(Path(__file__)),
        backend=backend, encoder_sha256=encoder, band_native_pixels=4,
        scale=2, neural_batch=6, fp16=True, reduce='Box x4 to x2', SDF=False)
    accelerated_mode = os.environ.get('Q3M_PALETTE_ENCODER', 'cpu')
    if accelerated_mode != 'cpu':
        recipe['palette_acceleration'] = dict(mode=accelerated_mode,
            sha256=file_sha(Path(__file__).with_name('q3m_guarded_gpu_encode.py')))
    recipe_key = digest(recipe)
    work = cache/'multipart-seams'/recipe_key
    if mode == 'run':
        for sub in ('contexts', 'encoded'):
            (work/sub).mkdir(parents=True, exist_ok=True)
        write_json(work/'recipe.json', recipe)
    elif mode != 'bind':
        raise ValueError('Unknown contextual production mode')
    parent = cache/'encoded'/encoder

    @lru_cache(maxsize=128)
    def arrays(key):
        with np.load(parent/(key+'.npz'), allow_pickle=False) as z:
            return {n: z[n].copy() for n in z.files}

    def old_targets(item, roi):
        used = np.unique(item['frame'].indices[item['frame'].indices != 0])
        targets = []
        for palette in item['profile'].fitting:
            key = hashlib.sha256(backend_key+bytes.fromhex(item['input_key'])+
                used.tobytes()+palette[used].tobytes()).hexdigest()
            with np.load(cache/'targets'/key[:2]/(key+'.npz'), allow_pickle=False) as z:
                targets.append(z['target'][roi].copy())
        return np.stack(targets)

    encode_workers = int(os.environ.get('Q3M_CONTEXT_ENCODE_WORKERS','1'))
    if not 1 <= encode_workers <= 16:
        raise ValueError('Context encode worker count outside 1..16')
    trim_cuda = os.environ.get('Q3M_TRIM_CUDA_CACHE','0') == '1'
    report['context_encode_workers'] = encode_workers
    model, records = None, {}
    for done, (ck, context) in enumerate(sorted(contexts.items()), 1):
        checkpoint = work/'contexts'/(ck+'.json')
        if checkpoint.exists():
            record = load(checkpoint)
            if record['recipe_key'] != recipe_key:
                raise ValueError('Context recipe differs')
            if len(record['nodes']) != len(context['nodes']) or any(
                    n['parent_key'] != row['key'] for n, (_, row) in
                    zip(record['nodes'], context['nodes'])):
                raise ValueError('Context frame bindings differ')
            for node in record['nodes']:
                if node['encoded_key'] != node['parent_key']:
                    if file_sha(work/'encoded'/(node['encoded_key']+'.npz')) != node['encoded_sha256']:
                        raise ValueError('Context payload identity differs')
            report['context_cache_hits'] += 1
        else:
            if mode != 'run':
                raise ValueError('Missing contextual checkpoint; run production before packing')
            prepared = []
            for r, row in context['nodes']:
                old = arrays(row['key'])
                validate_encoded(r['profile'], old['I'], old['F'], old['guide'], old['dep'])
                weight = strength(row['geometry'], context['geometry'])
                roi = (weight > 0) & (r['profile'].classes[old['guide']] >= (3 if r['profile'].kind == 0 else 4))
                prepared.append((r, row, old, weight, roi))
            targets, left, top = None, 0, 0
            if any(roi.any() for _, _, _, _, roi in prepared):
                from scipy.ndimage import distance_transform_edt
                from reboutcx_batch_p10 import pack_normalized
                from chainner_ext import resize, ResizeFilter
                import torch
                if model is None:
                    from reboutcx_multipal import inference_context
                    if inference_context() != backend:
                        raise ValueError('GPU backend differs from pinned source targets')
                    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
                    torch.set_num_threads(4)
                    torch.backends.cudnn.deterministic = True
                    torch.use_deterministic_algorithms(True)
                    model, _ = load_model(get_path('reboutcx_model', required=True), device='cuda:0', fp16=True)
                positive = [a for a in context['geometry'] if a[0]*a[1]]
                left, top = min(-a[2] for a in positive), min(-a[3] for a in positive)
                right, bottom = max(a[0]-a[2] for a in positive), max(a[1]-a[3] for a in positive)
                W, H = right-left, bottom-top
                rgb, mask = np.zeros((6, H, W, 3), np.uint8), np.zeros((H, W), bool)
                for r, row in context['nodes']:
                    a = row['geometry']; x, y = -a[2]-left, -a[3]-top
                    if not a[0]*a[1]:
                        continue
                    indices = works[row['key']]['frame'].indices; m = indices != 0
                    for k in range(6):
                        rgb[k, y:y+a[1], x:x+a[0]][m] = r['profile'].fitting[k][indices][m]
                    mask[y:y+a[1], x:x+a[0]] |= m
                nearest = distance_transform_edt(~mask, return_distances=False, return_indices=True)
                inputs = [np.ascontiguousarray(im[tuple(nearest)]) for im in rgb]
                canvas = (((H+31)//32)*32, ((W+31)//32)*32)
                tensor = torch.from_numpy(pack_normalized(inputs, *canvas).transpose(0, 3, 1, 2)).cuda().half()
                with torch.inference_mode():
                    prediction = model(tensor)
                if tuple(prediction.shape) != (6, 3, canvas[0]*4, canvas[1]*4):
                    raise ValueError('Contextual model output differs')
                output = prediction.float().clamp(0, 1).cpu().numpy()
                if trim_cuda and not report['new_neural_targets']:
                    del prediction
                    torch.cuda.empty_cache()
                    with torch.inference_mode():
                        prediction = model(tensor)
                    if not np.array_equal(output, prediction.float().clamp(0, 1).cpu().numpy()):
                        raise ValueError('CUDA cache trim changed contextual neural output')
                    report['cuda_trim_exact_output_checks'] = 6
                targets = np.stack([np.ascontiguousarray(np.clip(resize(
                    o[:, :H*4, :W*4].transpose(1, 2, 0), (W*2, H*2), ResizeFilter.Box, False),
                    0, 1), dtype=np.float32) for o in output])
                del tensor, prediction, output
                if trim_cuda:
                    torch.cuda.empty_cache()
                report['new_neural_targets'] += 6
            shared = (targets, left, top, recipe_key, ck, work, works, old_targets)
            jobs = [((part, *item), shared) for part, item in enumerate(prepared)]
            if encode_workers == 1:
                nodes = list(map(repair_part,jobs))
            else:
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=encode_workers) as pool:
                    nodes = list(pool.map(repair_part,jobs))
            record = dict(recipe_key=recipe_key, nodes=nodes, changed_outside_band=0)
            write_json(checkpoint, record)
        records[ck] = record
        report['changed_encoded_pixels'] += sum(n['changed_pixels'] for n in record['nodes'])
        if done % 16 == 0 or done == len(contexts):
            print(json.dumps(dict(stage='multipart-context', done=done, total=len(contexts))), flush=True)
    for r in resources:
        for row in r['frames']:
            binding = (r['witness']['animation_id'], r['resref'], row['frame_index'])
            if binding not in bindings:
                continue
            ck, part = bindings[binding]; node = records[ck]['nodes'][part]
            old, new = row['key'], node['encoded_key']
            if old != new:
                works.setdefault(new, dict(works[old], encoded_path=work/'encoded'/(new+'.npz')))
                row['key'] = new
    report['recipe_key'] = recipe_key
    return report
