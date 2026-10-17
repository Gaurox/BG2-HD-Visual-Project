"""Seal the exact eight SDF previews, zero inward offset, for runtime installation."""
from pathlib import Path
import copy
import importlib.util
import shutil
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow
import run_effect_interpolation as interpolation


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


base = module('effects26_base', 'pipeline/recipes/effects-lot26-seedvr7b-apollo30-20261017-v2/temporal.py')
sdf = module('effects8_sdf', 'pipeline/recipes/effects-lot8-sdf-ankheg-preview-20261017-v1/preview.py')
BATCH = ROOT / 'effects/batches/lot26-sdf-no-inset-20261017-v1'
base.BATCH = BATCH
load, save, rel, digest = base.load, base.save, base.rel, base.digest


def produce(a):
    name = a['resref']
    if (BATCH / 'checks' / f'{name}.json').exists():
        return load(BATCH / 'checks' / f'{name}.json')
    parent = ROOT / 'effects/ressources' / name / 'runs' / a['sdf_parent_run']
    old = load(parent / '02-interpolation/manifest.json')
    preview = load(sdf.OUT / 'assets' / f'{name}.json')
    hashes = {f['frame']: f['candidate_rgba_sha256'] for f in preview['frames']}
    plan = base.make_plan(a)
    assert not plan.run_root.exists(), 'Sealed or partial existing run must be preserved'
    interpolation.reserve(plan)
    plan.run_root.mkdir(parents=True)
    snapshot = plan.run_root / 'producer-source.py'
    snapshot.write_bytes(Path(__file__).read_bytes())
    recipe = {'schema': interpolation.RECIPE_SCHEMA, 'recipe_id': 'ankheg-sdf-raster-x4-zero-inset',
              'pipeline_id': interpolation.PIPELINE_ID, 'scale': 4, 'target_fps': [30, 1],
              'inset_x4': 0, 'sigma_x4': 4, 'bias_limit_x4': 2, 'area_supersampling': 8,
              'alpha_policy': 'exact SDF preview without inset; bounded reconstruction and nearest foreground material',
              'parent_interpolation': interpolation.evidence(ROOT, 'parent-interpolation-manifest', parent / '02-interpolation/manifest.json'),
              'preview': interpolation.evidence(ROOT, 'preview-verification', sdf.OUT / 'assets' / f'{name}.json'),
              'tools': [interpolation.evidence(ROOT, 'producer', snapshot),
                        interpolation.evidence(ROOT, 'preview-producer', ROOT / 'pipeline/recipes/effects-lot8-sdf-ankheg-preview-20261017-v1/preview.py'),
                        interpolation.evidence(ROOT, 'validated-sdf', sdf.REFERENCE)],
              'new_neural_inference': 0}
    save(plan.recipe_path, recipe)
    created = workflow.utc_now()

    def descriptor(status, sealed, outputs=()):
        d = interpolation.descriptor(plan, recipe, status=status, sealed=sealed, created_at=created, outputs=outputs)
        d['pipeline']['version'] = 'effects-sdf-raster-zero-inset.v1'
        d['provenance']['generator'] = rel(Path(__file__))
        d['inputs'].append(recipe['parent_interpolation'])
        return d

    save(plan.descriptor_path, descriptor('running', False))
    stage = plan.interpolation_root
    folder = stage / 'frames-rgba'
    folder.mkdir(parents=True)
    spatial = load(plan.spatial_manifest)
    cw, ch = spatial['aligned_canvas_size_x1']
    cache, records = {}, []
    for old_frame in old['frames']:
        f = copy.deepcopy(old_frame)
        straight = sdf.frame(parent / '02-interpolation', old_frame)
        pixels, checked = sdf.smooth_rgba(straight, cache)
        assert digest(pixels.tobytes()) == hashes[f['frame']], (name, f['frame'], 'preview mismatch')
        primary = pixels.copy()
        primary[:, :, :3] = np.rint(pixels[:, :, :3].astype(np.float32) * pixels[:, :, 3:4] / 255).astype(np.uint8)
        primary[primary[:, :, 3] == 0] = 0
        stem = f'frame_{f["frame"]:03d}'
        raw = folder / (stem + '.rgba')
        normal = folder / (stem + '-straight.rgba')
        png = folder / (stem + '.png')
        raw.write_bytes(primary.tobytes())
        normal.write_bytes(pixels.tobytes())
        Image.fromarray(primary).save(png, compress_level=3)
        canvas = np.zeros((ch * 4, cw * 4, 4), np.uint8)
        l, t, r, b = f['runtime_crop_box_x4']
        canvas[t:b, l:r] = primary
        f.update(raw_rgba_x4='frames-rgba/' + raw.name, raw_rgba_x4_sha256=digest(primary.tobytes()),
                 straight_raw_rgba_x4='frames-rgba/' + normal.name, straight_raw_rgba_x4_sha256=digest(pixels.tobytes()),
                 rgba_x4='frames-rgba/' + png.name, rgba_x4_sha256=workflow.sha256_file(png),
                 anchored_rgba_sha256=digest(canvas.tobytes()), anchored_rgb_sha256=digest(canvas[:, :, :3].tobytes()),
                 normal_alpha_policy='ankheg-SDF-x4-zero-inset-coverage8x8')
        records.append(f)
    manifest = copy.deepcopy(old)
    manifest.update(created_utc=workflow.utc_now(), visual_treatment=recipe, frames=records)
    for cycle in manifest['timing']['cycles']:
        sequence = [records[i] for i in cycle['timeline_frame_indices']]
        rgb = [f['anchored_rgb_sha256'] for f in sequence]
        rgba = [f['anchored_rgba_sha256'] for f in sequence]
        if not cycle['constant_native_cycle']:
            assert len(set(rgb)) == len(rgb) and len(set(rgba)) == len(rgba), (name, cycle['id'])
        cycle.update(unique_rgb=len(set(rgb)), unique_rgba=len(set(rgba)),
                     adjacent_rgb_duplicates=[i for i in range(1, len(rgb)) if rgb[i] == rgb[i - 1]],
                     loop_seam_duplicate=bool(cycle['loop_closed'] and rgb[0] == rgb[-1]))
    assert manifest['timing'] == old['timing'], 'Timing/profile contents must remain exact'
    carrier = plan.run_root / 'runtime-carrier' / (name + '.bam')
    carrier.parent.mkdir()
    shutil.copy2(ROOT / old['runtime_carrier']['path'], carrier)
    manifest['runtime_carrier'] = {**old['runtime_carrier'], 'path': rel(carrier)}
    save(stage / 'manifest.json', manifest)
    save(plan.descriptor_path, descriptor('completed', True, [
        interpolation.evidence(ROOT, 'interpolation-manifest', stage / 'manifest.json'),
        interpolation.evidence(ROOT, 'runtime-bam-carrier', carrier)]))
    result = base.finish(a, plan, spatial)
    save(BATCH / 'sdf-verification' / f'{name}.json', {
        'passed': True, 'resref': name, 'phases': len(records), 'sdf_inset_x4': 0,
        'straight_rgba_exact_preview': True, 'premultiplication_exact': True,
        'timing_geometry_carrier_preserved': True, 'new_neural_inference': 0,
        'manifest': workflow.file_evidence(ROOT, stage / 'manifest.json')})
    print(name, 'SDF without inset sealed', len(records), flush=True)
    return result


def main():
    parent = ROOT / 'effects/batches/lot26-seedvr7b-apollo30-20261017-v2'
    assets = load(BATCH / 'batch.json')['assets']
    for a in assets:
        if a.get('sdf_parent_run'):
            produce(a)
        else:
            target = BATCH / 'checks' / f'{a["resref"]}.json'
            target.parent.mkdir(exist_ok=True)
            if not target.exists():
                shutil.copy2(parent / 'checks' / target.name, target)
    save(BATCH / 'production.json', {'status': 'completed', 'count': 26,
         'sdf_without_inset': load(BATCH / 'batch.json')['sdf_assets'], 'sdf_phases': 404,
         'other_assets_v2_unchanged': 18, 'qa': 'pending-ingame-user-test', 'installed': False,
         'assets': [load(BATCH / 'checks' / f'{a["resref"]}.json') for a in assets]})


if __name__ == '__main__':
    main()
