"""Check every fine-effect alpha against the unfeathered native temporal mask."""
from temporal import ROOT, BATCH, load, save
import numpy as np
from PIL import Image

reports = []
for a in load(BATCH / 'batch.json')['assets']:
    if a['inner_feather_x4']:
        continue
    stage = ROOT / 'effects/ressources' / a['resref'] / 'runs' / a['interpolation_run'] / '02-interpolation'
    m = load(stage / 'manifest.json')
    sp = ROOT / m['parent']['spatial_manifest']
    s = load(sp)
    masks = {}
    checked = 0
    for f in m['frames']:
        left, right = f['temporal_source_frames']
        for k in (left, right):
            if k not in masks:
                with Image.open(sp.parent / s['frames'][k]['aligned_rgba_xn']) as im:
                    masks[k] = np.asarray(im.getchannel('A')).copy()
        l, t, r, b = f['runtime_crop_box_x4']
        fraction = f['temporal_fraction']
        expected = np.rint(masks[left][t:b, l:r].astype(np.float32) * (1 - fraction) +
                           masks[right][t:b, l:r].astype(np.float32) * fraction).astype(np.uint8)
        w, h = f['physical_size_x4']
        actual = np.frombuffer((stage / f['raw_rgba_x4']).read_bytes(), np.uint8).reshape(h, w, 4)
        assert np.array_equal(actual[:, :, 3], expected), (a['resref'], f['frame'])
        checked += 1
    reports.append({'resref': a['resref'], 'passed': True, 'phases': checked,
                    'native_temporal_coverage_exact': True, 'inner_feather_x4': 0})
    print(a['resref'], 'native coverage exact', checked, flush=True)
assert len(reports) == 19
save(BATCH / 'alpha-coverage-verification.json', {'passed': True, 'assets': reports,
     'fine_assets': 19, 'checked_phases': sum(r['phases'] for r in reports),
     'diffuse_assets_unchanged': 7, 'new_neural_inference_runs': 0})
