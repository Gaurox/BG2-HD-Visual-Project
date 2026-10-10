"""Four new SeedVR7B/LAB runs + existing OHRSGATE SeedVR variant; no installation.

Preserve recipe radii 16/0/0/16/2 and the SPDIMNDR linear-cycle adaptation.
The first batch and OHRSGATE comparison remain read-only inputs.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'pipeline/recipes/portails-cinq-20261010-v1'))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as splitter
import build_blended_rgb_neutral_pack as neutral
import build_previews as preview
from build_temporal import adapted_plan, interpolate_progress

TAG = 'portails-cinq-seedvr-20261010-v1'
BATCH = ROOT / 'animations/batches' / TAG
JOBS = [('OHDLPORT', 5400, 0), ('OHHPORT', 811, 0),
        ('BDFORCEW', 8100, 16), ('SPDIMNDR', 6108, 2)]


def build_asset(ref, seed, radius):
    spatial = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-seedvr7b-spatial-20261010-v1'
    temporal = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-seedvr7b-apo8-20261010-v1'
    final = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-seedvr7b-inner{radius}-final-20261010-v1'
    if not (spatial / '03_runtime_pack/manifest.json').exists():
        print(f'SEEDVR START {ref}', flush=True)
        args = [sys.executable, '-B', str(ROOT / 'pipeline/scripts/run_animation_upscale.py'),
                '--resref', ref, '--run', spatial.name, '--seed', str(seed), '--pad', '32', '--resume']
        with (BATCH / f'{ref}-seedvr.log').open('a', encoding='utf-8') as stream:
            subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
    print(f'SEEDVR COMPLETED {ref}', flush=True)
    base = spatial / '03_runtime_pack'
    plan = adapted_plan(spatial, base, [ref], model='apo-8', transparent_rgb_mode='nearest-opaque-dilate')
    if ref == 'SPDIMNDR':
        assert [c['timeline_phases'] for c in plan['targets'][0]['cycles']] == [58, 60, 16, 58, 136]
    v2.write_json(BATCH / f'{ref}-temporal-plan.json', plan)
    v2.build_run(spatial, base, temporal, [ref], plan['plan_sha256'],
                 v2.DEFAULT_TVAI_FFMPEG, v2.DEFAULT_TVAI_MODEL_DIR, 'apo-8',
                 v2.DEFAULT_DEVICE, 'ffmpeg', True,
                 transparent_rgb_mode='nearest-opaque-dilate')
    source_split = BATCH / f'artifacts/{ref}-source-split'
    final_split = BATCH / f'artifacts/{ref}-final-split'
    splitter.split(temporal / '03_runtime_pack', source_split,
                   ROOT / 'animations/index/occurrences.csv', source_split.exists())
    neutral.build(source_split, final_split, {ref}, final_split.exists(), 'premultiply', None, radius)
    final.mkdir(parents=True, exist_ok=True)
    job = {'resref': ref, 'spatial_run': spatial.relative_to(ROOT).as_posix(),
           'temporal_run': temporal.relative_to(ROOT).as_posix(),
           'final_run': final.relative_to(ROOT).as_posix(),
           'final_split': final_split.relative_to(ROOT).as_posix(),
           'recipe': {'spatial': 'SeedVR2 7B INT8 / LAB', 'seed': seed,
                      'temporal': 'Apollo8 15->30 nearest-opaque-dilate',
                      'inner_feather_x4': radius, 'rgb_policy': 'premultiply-once',
                      'linear_cycles': [0, 2, 3, 4] if ref == 'SPDIMNDR' else []}}
    if not (final / 'manifest.json').exists():
        v2.write_json(final / 'manifest.json', {
            'schema': 'bg2-upscale-animation-visual-treatment-v1', 'status': 'completed',
            'created_utc': v2.utc_now(), 'resref': ref, 'source_run': job['temporal_run'],
            'source_run_manifest_sha256': v2.sha256_file(temporal / 'manifest.json'),
            'output_split_root': job['final_split'],
            'output_manifest_sha256': v2.sha256_file(final_split / 'manifest.json'),
            'recipe': job['recipe'], 'qa_status': 'pending-user-preview', 'installed': False,
            'recipe_script': Path(__file__).relative_to(ROOT).as_posix()})
    print(f'FINAL COMPLETED {ref}', flush=True)
    return job


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    v2.build_plan = adapted_plan
    v2.interpolate_cycle = interpolate_progress
    ohr = v2.load_json(ROOT / 'animations/batches/ohrsgate-seedvr-comparison-20261010-v1/manifest.json')['resources'][0]
    batch = {'schema': 'bg2-upscale-animation-batch-production-v1', 'status': 'working',
             'created_utc': v2.utc_now(), 'resources': [ohr], 'installed': False,
             'qa_status': 'pending-user-preview', 'release_status': 'not-selected'}
    v2.write_json(BATCH / 'manifest.json', batch)
    for ref, seed, radius in JOBS:
        job = build_asset(ref, seed, radius)
        batch['resources'].append(job)
        v2.write_json(BATCH / 'manifest.json', batch)
    batch['status'] = 'completed'
    v2.write_json(BATCH / 'manifest.json', batch)
    print('ALL FIVE SEEDVR VARIANTS COMPLETED', flush=True)


if __name__ == '__main__':
    main()
