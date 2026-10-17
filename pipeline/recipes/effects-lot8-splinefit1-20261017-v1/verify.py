"""Re-read the eight derivatives and verify the limited alpha-only contract."""
import copy
import numpy as np
from derive import ROOT, BATCH, load, save, digest, workflow, base

reports = []
for a in load(BATCH / 'batch.json')['assets']:
    ref = a['resref']
    if not a['splinefit1_requested']:
        reports.append(load(BATCH / 'verification' / f'{ref}.json'))
        continue
    parent = ROOT / 'effects/ressources' / ref / 'runs' / a['spline_parent_run'] / '02-interpolation'
    stage = ROOT / 'effects/ressources' / ref / 'runs' / a['interpolation_run'] / '02-interpolation'
    before, after = load(parent / 'manifest.json'), load(stage / 'manifest.json')
    assert before['timing'] == after['timing']
    assert len(before['frames']) == len(after['frames'])
    assert workflow.sha256_file(ROOT / before['runtime_carrier']['path']) == workflow.sha256_file(ROOT / after['runtime_carrier']['path'])
    retained, changed, partial = [], 0, 0
    for old, new in zip(before['frames'], after['frames'], strict=True):
        for key in ('frame', 'cycle', 'mode', 'phase', 'temporal_source_frames', 'temporal_fraction',
                    'logical_size_x1', 'physical_size_x4', 'centre_x1', 'runtime_crop_box_x4'):
            assert old[key] == new[key], (ref, key)
        w, h = old['physical_size_x4']
        rgb_before = np.frombuffer((parent / old['straight_raw_rgba_x4']).read_bytes(), np.uint8).reshape(h, w, 4)
        normal_raw = (stage / new['straight_raw_rgba_x4']).read_bytes()
        raw = (stage / new['raw_rgba_x4']).read_bytes()
        assert digest(normal_raw) == new['straight_raw_rgba_x4_sha256']
        assert digest(raw) == new['raw_rgba_x4_sha256']
        normal = np.frombuffer(normal_raw, np.uint8).reshape(h, w, 4)
        primary = np.frombuffer(raw, np.uint8).reshape(h, w, 4)
        assert np.array_equal(normal[:, :, :3], rgb_before[:, :, :3])
        assert np.array_equal(normal[:, :, 3], primary[:, :, 3])
        assert np.all(normal[:, :, 3] <= rgb_before[:, :, 3])
        assert not normal[:, :, 3][rgb_before[:, :, 3] == 0].any()
        expected = np.rint(normal[:, :, :3].astype(np.float32) * normal[:, :, 3:4] / 255).astype(np.uint8)
        assert np.max(np.abs(expected.astype(np.int16) - primary[:, :, :3].astype(np.int16))) <= 1
        changed += int(np.count_nonzero(normal[:, :, 3] != rgb_before[:, :, 3]))
        partial += int(np.count_nonzero((normal[:, :, 3] > 0) & (normal[:, :, 3] < 255)))
        if rgb_before[:, :, 3].any():
            retained.append(float(normal[:, :, 3].sum()) / float(rgb_before[:, :, 3].sum()))
    check = load(BATCH / 'checks' / f'{ref}.json')
    report = {'resref': ref, 'passed': True, 'phases': len(after['frames']),
              'source_model': 'seedvr2_7b_int8_convrot.safetensors', 'scale': 4, 'target_fps': [30, 1],
              'alpha_method': 'SplineFit1 / fit_error1 x4 / SS4 / inner0',
              'straight_rgb_byte_identical': True, 'premultiplied_consistency_max_error': 1,
              'geometry_centres_carrier_timing_byte_identical': True,
              'alpha_never_increased': True, 'transparent_holes_preserved': True,
              'changed_alpha_pixels': changed, 'partial_alpha_pixels': partial,
              'min_alpha_mass_retained': min(retained), 'mean_alpha_mass_retained': float(np.mean(retained)),
              'pack_manifest_sha256': check['pack_manifest_sha256'],
              'cycle_mode_variants': check['cycle_mode_variants'], 'raw_bytes': check['raw_bytes'],
              'qa': 'pending-user-review', 'installed': False}
    save(BATCH / 'verification' / f'{ref}.json', report)
    reports.append(report)
    print(ref, 'independent alpha-only PASS', len(after['frames']), 'phases; min mass', round(min(retained), 3), flush=True)
assert len(reports) == 26
save(BATCH / 'verification.json', {'passed': 26, 'failures': [], 'splinefit1_assets': 8,
     'other_productions_unchanged': 18, 'assets': reports,
     'phases': sum(r['phases'] for r in reports),
     'cycle_mode_variants': sum(r['cycle_mode_variants'] for r in reports),
     'qa': 'pending-user-review', 'installed': False})
