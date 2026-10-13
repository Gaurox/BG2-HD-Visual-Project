"""Per-BAM byte, geometry, alpha, native-pose, timing and runtime-pack checks."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1'
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from compose_effect_runtime_packs import validate_pack
from derive_animation_visual_treatment import apply_geometry_preserving_rgb_gaussian, apply_inner_contour_fade
from export_bam_frames import read_bam, cycle_metadata
from bam_export import decode_bam
import effect_workflow as workflow


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def pixels(path, frame, physical_key, raw_key, hash_key):
    raw = (path / frame[raw_key]).read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == frame[hash_key].upper(), ('frame hash', frame['frame'])
    width, height = frame[physical_key]
    assert len(raw) == width * height * 4
    return np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)


def verify(asset):
    name = asset['resref']; resource = ROOT / 'effects/ressources' / name
    checked_inputs = {'pack_manifest_sha256': workflow.sha256_file(ROOT / asset['pack'] / 'manifest.json')}
    for key in ['spatial_run', 'apollo_run', 'treatment_run']:
        checked_inputs[key] = workflow.sha256_file(resource / 'runs' / asset[key] / 'run.json')
    for key, stage in [('spatial_run', 'spatial'), ('apollo_run', 'interpolation'), ('treatment_run', 'interpolation')]:
        check = workflow.verify_run_descriptor(ROOT, resource, name, asset[key], stage=stage,
                                                spatial_run=asset['spatial_run'])
        assert check['ok'], check['errors']
    native_root = resource / 'runs' / asset['spatial_run'] / '00-frames-x1'
    spatial_root = resource / 'runs' / asset['spatial_run'] / '01-spatial-x4'
    apollo_root = resource / 'runs' / asset['apollo_run'] / '02-interpolation'
    final_root = resource / 'runs' / asset['treatment_run'] / '02-interpolation'
    native, spatial, apollo, final = [load(p / 'manifest.json') for p in [native_root, spatial_root, apollo_root, final_root]]
    bam = read_bam(ROOT / asset['source']); decoded, palette, transparent = decode_bam(bam)
    cycles = cycle_metadata(bam, len(decoded))
    assert cycles == native['cycles'] and len(cycles) == 1
    cycle = cycles[0]['frame_indices']
    assert len(spatial['frames']) == len(decoded) == len(native['frames']) == asset['frames']
    source_flux = spatial_flux = 0.0
    source_channels = np.zeros(3); spatial_channels = np.zeros(3)
    for i, (source, scaled) in enumerate(zip(native['frames'], spatial['frames'])):
        indices, cx, cy, tr = decoded[i]
        assert source['source_size'] == [indices.shape[1], indices.shape[0]]
        assert source['centre'] == [cx, cy] == scaled['centre_x1']
        assert scaled['logical_size_x1'] == source['source_size']
        assert scaled['physical_size_xn'] == [v * 4 for v in source['source_size']]
        actual = pixels(spatial_root, scaled, 'physical_size_xn', 'raw_rgba_xn', 'raw_rgba_xn_sha256')
        mask = np.repeat(np.repeat((indices != tr).astype(np.uint8) * 255, 4, axis=0), 4, axis=1)
        assert np.array_equal(actual[:, :, 3], mask), ('source alpha', i)
        if i in cycle:
            native_rgb = palette[indices].astype(float) * (indices != tr)[:, :, None]
            source_channels += native_rgb.sum(axis=(0, 1)) * 16
            spatial_channels += (actual[:, :, :3].astype(float) * (mask > 0)[:, :, None]).sum(axis=(0, 1))
    assert final['timing'] == apollo['timing']
    timing = final['timing']
    assert timing['native_fps'] == [15, 1] and timing['target_fps'] == [30, 1]
    assert timing['native_cycle_slots'] == len(cycle)
    assert timing['timeline_phase_count'] == len(cycle) * 2 == len(final['frames'])
    assert timing['native_frame_indices'] == list(range(0, len(cycle) * 2, 2))
    assert not timing['loop_closed'] and final['rgb_encoding'] == 'premultiplied'
    assert final['visual_treatment']['sigma_x4'] == 1.2 and final['visual_treatment']['inner_feather_x4'] == 12
    assert not final['duplicate_audit'].get('unexpected_visible_duplicates')
    audit = final['duplicate_audit']
    assert audit['exact_visible_duplicates'] == audit.get('native_repeat_duplicates', audit.get('native_hold_duplicates', []))
    checked_final = {}; checked_apollo = {}; visible_phases = 0
    for phase, frame in enumerate(final['frames']):
        assert frame['frame'] == phase
        source_idx = cycle[phase // 2]; scaled = spatial['frames'][source_idx]
        assert frame['geometry_source_frame'] == source_idx == frame['alpha_source_frame']
        assert frame['logical_size_x1'] == scaled['logical_size_x1']
        assert frame['physical_size_x4'] == scaled['physical_size_xn']
        assert frame['centre_x1'] == scaled['centre_x1']
        rawkey = frame['raw_rgba_x4']
        if rawkey not in checked_final:
            actual = pixels(final_root, frame, 'physical_size_x4', 'raw_rgba_x4', 'raw_rgba_x4_sha256')
            af = apollo['frames'][phase]
            original = pixels(apollo_root, af, 'physical_size_x4', 'raw_rgba_x4', 'raw_rgba_x4_sha256')
            blurred = apply_geometry_preserving_rgb_gaussian(original, 1.2)
            expected, _ = apply_inner_contour_fade(blurred, 12, 'premultiplied')
            assert np.array_equal(actual, expected), ('recipe pixels', phase)
            assert np.all(actual[:, :, 3] <= original[:, :, 3])
            assert np.all(actual[:, :, :3] <= actual[:, :, 3:4]), ('premultiplied', phase)
            checked_final[rawkey] = bool(np.any(actual[:, :, :3]))
            source_flux += float(original[:, :, :3].sum()); spatial_flux += float(actual[:, :, :3].sum())
        visible_phases += checked_final[rawkey]
        if phase % 2 == 0:
            anchored = pixels(apollo_root, apollo['frames'][phase], 'physical_size_x4', 'raw_rgba_x4', 'raw_rgba_x4_sha256')
            native_anchor = pixels(spatial_root, scaled, 'physical_size_xn', 'raw_rgba_xn', 'raw_rgba_xn_sha256').copy()
            native_anchor[native_anchor[:, :, 3] == 0] = 0
            assert np.array_equal(anchored, native_anchor), ('native RGB/alpha anchor', phase)
    assert visible_phases > 0, 'effect vanished'
    pack = validate_pack(ROOT / asset['pack'])
    pm = pack.manifest
    assert pack.registry_version == 2 and pack.resource_count == 1 and pm['resref'] == name
    assert pm['cycles'] == cycles
    assert pm['timeline']['phase_count'] == len(cycle) * 2
    for phase, backing in enumerate(pm['timeline']['timeline_frame_indices']):
        pf = pm['frames'][backing]; ff = final['frames'][phase]
        assert pf['sha256'] == ff['raw_rgba_x4_sha256']
        assert pf['logical_size_x1'] == ff['logical_size_x1']
        assert pf['source_centre_x1'] == ff['centre_x1']
    assert pm['timeline']['native_frame_indices'] == pm['timeline']['timeline_frame_indices'][::2]
    chroma_delta = np.max(np.abs(spatial_channels / spatial_channels.sum() - source_channels / source_channels.sum()))
    return {'resref': name, 'passed': True, 'checked_inputs': checked_inputs,
            'native_frames': len(decoded), 'native_slots': len(cycle),
            'phases_30fps': len(final['frames']), 'visible_phases': visible_phases,
            'native_holds': len(final['duplicate_audit'].get('native_hold_duplicates', [])),
            'unexpected_duplicates': 0, 'unique_backings': pm['frame_count'],
            'pack_raw_bytes': sum(f['bytes'] for f in pm['frames']),
            'duration_seconds': len(cycle) / 15,
            'treatment_flux_change_percent': 100 * (spatial_flux / source_flux - 1),
            'source_spatial_chroma_delta': float(chroma_delta),
            'registry_sha256': pm['registry_sha256'], 'visual_qa': 'pending-user'}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--ready-only', action='store_true')
    parser.add_argument('--skip-checked', action='store_true')
    parser.add_argument('--resref', action='append'); args = parser.parse_args()
    assets = load(BATCH / 'batch.json')['assets']; reports = []; failed = []
    for asset in assets:
        if args.resref and asset['resref'] not in args.resref: continue
        if args.ready_only and not (ROOT / asset['pack'] / 'manifest.json').exists(): continue
        try:
            target = BATCH / 'checks' / (asset['resref'] + '.json')
            previous = load(target) if target.exists() else {}
            inputs = {'pack_manifest_sha256': workflow.sha256_file(ROOT / asset['pack'] / 'manifest.json')}
            for key in ['spatial_run', 'apollo_run', 'treatment_run']:
                inputs[key] = workflow.sha256_file(ROOT / 'effects/ressources' / asset['resref'] / 'runs' / asset[key] / 'run.json')
            if args.skip_checked and previous.get('passed') and previous.get('checked_inputs') == inputs:
                result = previous
            else:
                result = verify(asset)
                print(asset['resref'], 'PASS', result['phases_30fps'], 'phases', flush=True)
            reports.append(result)
        except Exception as exc:
            result = {'resref': asset['resref'], 'passed': False, 'error': repr(exc)}
            reports.append(result); failed.append(asset['resref']); print(result, flush=True)
        target = BATCH / 'checks' / (asset['resref'] + '.json'); target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    summary = {'checked': len(reports), 'passed': len(reports) - len(failed), 'failures': failed,
               'total_raw_bytes': sum(r.get('pack_raw_bytes', 0) for r in reports), 'assets': reports}
    (BATCH / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'assets'}))
    return int(bool(failed))


if __name__ == '__main__': raise SystemExit(main())
