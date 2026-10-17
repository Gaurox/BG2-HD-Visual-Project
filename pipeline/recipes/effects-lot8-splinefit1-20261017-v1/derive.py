"""Eight requested alpha-only SplineFit1 derivatives; neural RGB/timing reused."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import shutil
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import build_per_frame_spline_alpha_30fps_v2 as spline
import effect_workflow as workflow
import run_effect_interpolation as interpolation

SPEC = importlib.util.spec_from_file_location('effects26_parent', ROOT / 'pipeline/recipes/effects-lot26-seedvr7b-apollo30-20261017-v2/temporal.py')
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
BATCH = ROOT / 'effects/batches/lot26-seedvr7b-apollo30-20261017-v3'
base.BATCH = BATCH
load, save, digest, rel = base.load, base.save, base.digest, base.rel


def derive(a):
    name = a['resref']
    if (BATCH / 'checks' / f'{name}.json').exists():
        return load(BATCH / 'spline-verification' / f'{name}.json')
    parent = ROOT / 'effects/ressources' / name / 'runs' / a['spline_parent_run']
    old_path = parent / '02-interpolation/manifest.json'
    old = load(old_path)
    plan = base.make_plan(a)
    assert not plan.run_root.exists(), 'Never overwrite an existing derivative'
    interpolation.reserve(plan)
    plan.run_root.mkdir(parents=True)
    snapshot = plan.run_root / 'producer-source.py'
    snapshot.write_bytes(Path(__file__).read_bytes())
    recipe = {'schema': interpolation.RECIPE_SCHEMA, 'recipe_id': 'spline-fit1-alpha-only',
              'pipeline_id': interpolation.PIPELINE_ID, 'scale': 4, 'target_fps': [30, 1],
              'fit_error_x4': 1.0, 'sample_spacing_x4': 1.5, 'supersample': 4,
              'padding_x4': 32, 'threshold': 0, 'inner_feather_x4': 0,
              'normal_rgb': 'byte-identical straight RGB',
              'primary_rgb': 'existing premultiplied RGB scaled once by new_alpha/old_alpha',
              'alpha': 'per-frame periodic cubic spline, fit tolerance1 x4; inward coverage; holes and small islands retained',
              'parent_interpolation': interpolation.evidence(ROOT, 'parent-interpolation-manifest', old_path),
              'tools': [interpolation.evidence(ROOT, 'producer', snapshot),
                        interpolation.evidence(ROOT, 'spline-fitter', ROOT / 'pipeline/scripts/build_per_frame_spline_alpha_30fps_v2.py')],
              'neural_inference_runs': 0}
    save(plan.recipe_path, recipe)
    created = workflow.utc_now()

    def descriptor(status, sealed, outputs=()):
        value = interpolation.descriptor(plan, recipe, status=status, sealed=sealed,
                                          created_at=created, outputs=outputs)
        value['pipeline']['version'] = 'effect-splinefit1-alpha-only.v1'
        value['provenance']['generator'] = rel(Path(__file__))
        value['inputs'].append(interpolation.evidence(ROOT, 'parent-interpolation-manifest', old_path))
        return value

    save(plan.descriptor_path, descriptor('running', False))
    stage = plan.interpolation_root
    frames_root = stage / 'frames-rgba'
    frames_root.mkdir(parents=True)
    spatial = load(plan.spatial_manifest)
    cw, ch = spatial['aligned_canvas_size_x1']
    records, checks, cache = [], [], {}
    for f in old['frames']:
        w, h = f['physical_size_x4']
        raw = (old_path.parent / f['raw_rgba_x4']).read_bytes()
        straight_raw = (old_path.parent / f['straight_raw_rgba_x4']).read_bytes()
        assert digest(raw) == f['raw_rgba_x4_sha256']
        assert digest(straight_raw) == f['straight_raw_rgba_x4_sha256']
        pixels = np.frombuffer(raw, np.uint8).reshape(h, w, 4)
        straight = np.frombuffer(straight_raw, np.uint8).reshape(h, w, 4)
        assert np.array_equal(pixels[:, :, 3], straight[:, :, 3])
        alpha = pixels[:, :, 3]
        key = (w, h, digest(alpha.tobytes()))
        if key not in cache:
            smoothed, stats = spline.spline_alpha(alpha, threshold=0, fit_error=1.0,
                spacing=1.5, supersample=4, padding=32, inner_feather=0, protected_core=0)
            # Never remove a small island solely because its fitted raster vanishes.
            labels, count = ndimage.label(alpha > 0, structure=np.ones((3, 3)))
            masses = np.bincount(labels.ravel(), weights=smoothed.ravel(), minlength=count + 1)
            missing = np.flatnonzero(masses[1:] == 0) + 1
            for label in missing:
                smoothed[labels == label] = alpha[labels == label]
            stats['preserved_collapsed_islands'] = len(missing)
            cache[key] = smoothed, stats
        smoothed, stats = cache[key]
        assert np.all(smoothed <= alpha) and not smoothed[alpha == 0].any()
        out_straight = straight.copy()
        out_straight[:, :, 3] = smoothed
        assert np.array_equal(out_straight[:, :, :3], straight[:, :, :3])
        ratio = np.divide(smoothed.astype(np.float32), alpha, out=np.zeros(alpha.shape, np.float32), where=alpha > 0)
        out = pixels.copy()
        out[:, :, :3] = np.rint(pixels[:, :, :3].astype(np.float32) * ratio[:, :, None]).astype(np.uint8)
        out[:, :, 3] = smoothed
        assert np.all(out[:, :, :3] <= out[:, :, 3:4])
        stem = f'frame_{f["frame"]:03d}'
        png, path, normal_path = (frames_root / (stem + suffix) for suffix in ('.png', '.rgba', '-straight.rgba'))
        Image.fromarray(out).save(png, compress_level=3)
        path.write_bytes(out.tobytes())
        normal_path.write_bytes(out_straight.tobytes())
        l, t, r, b = f['runtime_crop_box_x4']
        canvas = np.zeros((ch * 4, cw * 4, 4), np.uint8)
        canvas[t:b, l:r] = out
        record = copy.deepcopy(f)
        record.update(rgba_x4='frames-rgba/' + png.name, rgba_x4_sha256=workflow.sha256_file(png),
                      raw_rgba_x4='frames-rgba/' + path.name, raw_rgba_x4_sha256=digest(out.tobytes()),
                      straight_raw_rgba_x4='frames-rgba/' + normal_path.name,
                      straight_raw_rgba_x4_sha256=digest(out_straight.tobytes()),
                      anchored_rgba_sha256=digest(canvas.tobytes()),
                      anchored_rgb_sha256=digest(canvas[:, :, :3].tobytes()),
                      normal_alpha_policy='SplineFit1-x4-SS4-inner0-native-palette-inward')
        records.append(record)
        checks.append({'frame': f['frame'], 'straight_rgb_identical': True,
                       'alpha_never_increased': True, 'transparent_holes_preserved': True,
                       'changed_alpha_pixels': int(np.count_nonzero(smoothed != alpha)),
                       'alpha_mass_retained': float(smoothed.sum()) / float(alpha.sum()) if alpha.any() else 1.0,
                       'fit': stats})
    result = copy.deepcopy(old)
    result.update(created_utc=workflow.utc_now(), frames=records, visual_treatment=recipe,
                  alpha_derivation={'method': 'SplineFit1', 'parent': recipe['parent_interpolation']})
    # Exact timing/phase identity is retained; only content hashes change.
    for cycle in result['timing']['cycles']:
        seq = [records[i] for i in cycle['timeline_frame_indices']]
        rgb = [f['anchored_rgb_sha256'] for f in seq]
        rgba = [f['anchored_rgba_sha256'] for f in seq]
        adjacent = [i for i in range(1, len(rgb)) if rgb[i] == rgb[i - 1]]
        seam = bool(cycle['loop_closed'] and rgb[0] == rgb[-1])
        if not cycle['constant_native_cycle']:
            assert len(set(rgb)) == len(rgb) and len(set(rgba)) == len(rgba), (name, cycle['id'])
            assert not adjacent and not seam
        cycle.update(unique_rgb=len(set(rgb)), unique_rgba=len(set(rgba)),
                     adjacent_rgb_duplicates=adjacent, loop_seam_duplicate=seam)
    carrier = plan.run_root / 'runtime-carrier' / (name + '.bam')
    carrier.parent.mkdir()
    shutil.copy2(ROOT / old['runtime_carrier']['path'], carrier)
    result['runtime_carrier'] = {**old['runtime_carrier'], 'path': rel(carrier)}
    save(stage / 'manifest.json', result)
    save(plan.descriptor_path, descriptor('completed', True, [
        interpolation.evidence(ROOT, 'interpolation-manifest', stage / 'manifest.json'),
        interpolation.evidence(ROOT, 'runtime-bam-carrier', carrier)]))
    base.finish(a, plan, spatial)
    report = {'resref': name, 'passed': True, 'phases': len(records), 'frames': checks,
              'source': workflow.file_evidence(ROOT, old_path),
              'output': workflow.file_evidence(ROOT, stage / 'manifest.json'),
              'fit_error_x4': 1, 'inner_feather_x4': 0, 'straight_rgb_byte_identical': True,
              'dimensions_centres_cycles_timing_unchanged': True, 'new_neural_inference_runs': 0}
    save(BATCH / 'spline-verification' / f'{name}.json', report)
    print(name, 'SplineFit1 verified', len(records), 'phases', flush=True)
    return report


def main():
    reports = [derive(a) for a in load(BATCH / 'batch.json')['assets'] if a['splinefit1_requested']]
    assert len(reports) == 8
    save(BATCH / 'spline-verification.json', {'passed': True, 'count': 8,
         'phases': sum(r['phases'] for r in reports), 'assets': reports,
         'other_18_productions_unchanged': True, 'installed': False, 'qa': 'pending-user-review'})


if __name__ == '__main__':
    main()
