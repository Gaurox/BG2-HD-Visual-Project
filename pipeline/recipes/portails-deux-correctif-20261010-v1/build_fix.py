"""Two authorized repairs; original runs immutable, no game/release writes."""
from pathlib import Path
import argparse, copy, json, shutil, subprocess, sys
import numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
import run_animation_small_subject_xbr2 as xbr
import split_animation_pack_by_area as split
import build_blended_rgb_neutral_pack as neutral
TAG = 'portails-deux-correctif-20261010-v1'
BATCH = ROOT / 'animations/batches' / TAG

def run(args):
    subprocess.run([str(a) for a in args], cwd=ROOT, check=True)

def ohh():
    old = ROOT / 'animations/ressources/OHHPORT/runs/ohhport-xbr-spatial-20261010-v1'
    new = ROOT / 'animations/ressources/OHHPORT/runs/ohhport-xbr-backgroundfix-20261010-v1'
    if not new.exists():
        new.mkdir(parents=True)
        src = old / 'resources/OHHPORT'
        dst = new / 'resources/OHHPORT'
        for folder in ['00_source', '01_frames_x1']:
            shutil.copytree(src / folder, dst / folder)
        m = v2.load_json(old / 'manifest.json')
        m.update(status='prepared', run=new.name, created_utc=v2.utc_now(), updated_utc=v2.utc_now())
        m.pop('completed_utc', None)
        resource = m['resources'][0]
        resource.update(status='prepared', preview=None)
        for key in ['upscale', 'upscale_manifest_sha256', 'completed_utc']:
            resource.pop(key, None)
        authoring = dst / '01_frames_x1'
        fm = v2.load_json(authoring / 'manifest.json')
        fm['source'] = str(dst / '00_source/OHHPORT.bam')
        entry = next(f for f in fm['frames'] if f['frame'] == 2)
        rgba = np.asarray(Image.open(authoring / 'rgba' / entry['file']).convert('RGBA')).copy()
        remove = (rgba[:, :, :3].max(axis=2) == 0) & (rgba[:, :, 3] != 0)
        assert remove.sum() == 15007
        rgba[remove, 3] = 0
        rgba[rgba[:, :, 3] == 0, :3] = 0
        assert (rgba[:, :, 3] != 0).sum() == 1376
        for folder, pixels, key in [('rgba', rgba, 'rgba_sha256'), ('rgb', rgba[:, :, :3], 'rgb_sha256'), ('alpha', rgba[:, :, 3], 'alpha_sha256')]:
            file = authoring / folder / entry['file']
            Image.fromarray(pixels).save(file)
            entry[key] = v2.sha256_file(file)
        fm['authoring_override'] = {'native_frame': 2, 'rule': 'exact-black opaque background -> alpha zero; original transparent index retained', 'removed_pixels': 15007, 'foreground_pixels': 1376, 'canonical_source_unchanged': True}
        v2.write_json(authoring / 'manifest.json', fm)
        resource['frame_manifest_sha256'] = v2.sha256_file(authoring / 'manifest.json')
        m['authoring_override'] = fm['authoring_override']
        v2.write_json(new / 'manifest.json', m)
    if not (new / '03_runtime_pack/manifest.json').exists():
        xbr.build(new, 'OHHPORT', 'node', True, 'nearest', True)
        run([sys.executable, '-B', ROOT / 'pipeline/scripts/build_animation_runtime_pack.py', new])
    temporal = ROOT / 'animations/ressources/OHHPORT/runs/ohhport-apo8-backgroundfix-20261010-v1'
    base = new / '03_runtime_pack'
    plan = v2.build_plan(new, base, ['OHHPORT'], model='apo-8', transparent_rgb_mode='nearest-opaque-dilate')
    v2.write_json(BATCH / 'OHHPORT-plan.json', plan)
    v2.build_run(new, base, temporal, ['OHHPORT'], plan['plan_sha256'], v2.DEFAULT_TVAI_FFMPEG, v2.DEFAULT_TVAI_MODEL_DIR, 'apo-8', v2.DEFAULT_DEVICE, 'ffmpeg', True, transparent_rgb_mode='nearest-opaque-dilate')
    source = BATCH / 'artifacts/OHHPORT-source-split'
    final = BATCH / 'artifacts/OHHPORT-final-split'
    split.split(temporal / '03_runtime_pack', source, ROOT / 'animations/index/occurrences.csv', source.exists())
    neutral.build(source, final, {'OHHPORT'}, final.exists(), 'premultiply', None, 0)
    v2.write_json(BATCH / 'OHHPORT-job.json', dict(resref='OHHPORT', spatial_run=new.relative_to(ROOT).as_posix(), temporal_run=temporal.relative_to(ROOT).as_posix(), final_split=final.relative_to(ROOT).as_posix(), recipe=dict(spatial='xBR2 blend -> nearest2', temporal='Apollo8 15->30', native_frame_2_background='transparent', rgb_policy='premultiply-once', inner_feather_x4=0)))

def bdf():
    source = ROOT / 'animations/ressources/BDFORCEW/runs/bdforcew-apo8-portails-20261010-v1'
    output = ROOT / 'animations/ressources/BDFORCEW/runs/bdforcew-splinefit1-20261010-v1'
    if not output.exists():
        run([sys.executable, '-B', ROOT / 'pipeline/scripts/build_per_frame_spline_alpha_30fps_v2.py', '--temporal-run', source, '--resref', 'BDFORCEW', '--run', output.name, '--fit-error', '1', '--sample-spacing', '1.5', '--supersample', '4', '--padding-x4', '32', '--inner-feather-x4', '16', '--rgb-policy', 'premultiplied'])
    final = BATCH / 'artifacts/BDFORCEW-final-split'
    split.split(output / '03_runtime_pack', final, ROOT / 'animations/index/occurrences.csv', final.exists())
    v2.write_json(BATCH / 'BDFORCEW-job.json', dict(resref='BDFORCEW', spatial_run='animations/ressources/BDFORCEW/runs/bdforcew-rebout-spatial-20261010-v1', temporal_run=source.relative_to(ROOT).as_posix(), final_split=final.relative_to(ROOT).as_posix(), spline_run=output.relative_to(ROOT).as_posix(), recipe=dict(spatial='ReboutCX retained', temporal='Apollo8 retained 15->30', alpha='SplineFit1', fit_error_x4=1, inner_feather_x4=16, rgb_policy='premultiply-once')))

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('asset', choices=['OHHPORT','BDFORCEW']); args=p.parse_args()
    BATCH.mkdir(parents=True, exist_ok=True)
    ohh() if args.asset == 'OHHPORT' else bdf()
