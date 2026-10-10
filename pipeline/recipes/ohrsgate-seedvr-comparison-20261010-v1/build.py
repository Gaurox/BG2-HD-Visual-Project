"""OHRSGATE-only SeedVR7B INT8/LAB alternative; Apollo8 + inner16 identical to Rebout.

Outputs are new runs/previews. No edits to previous batch, game, QA authority or release.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'pipeline/recipes/portails-cinq-20261010-v1'))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as splitter
import build_blended_rgb_neutral_pack as neutral
import build_previews as preview

REF = 'OHRSGATE'
TAG = 'ohrsgate-seedvr-comparison-20261010-v1'
BATCH = ROOT / 'animations/batches' / TAG
SPATIAL = ROOT / 'animations/ressources/OHRSGATE/runs/ohrsgate-seedvr7b-spatial-20261010-v1'
TEMPORAL = ROOT / 'animations/ressources/OHRSGATE/runs/ohrsgate-seedvr7b-apo8-20261010-v1'
FINAL = ROOT / 'animations/ressources/OHRSGATE/runs/ohrsgate-seedvr7b-inner16-final-20261010-v1'


def spatial():
    if (SPATIAL / '03_runtime_pack/manifest.json').exists():
        return
    args = [sys.executable, '-B', str(ROOT / 'pipeline/scripts/run_animation_upscale.py'),
            '--resref', REF, '--run', SPATIAL.name, '--seed', '4220', '--pad', '32', '--resume']
    print('SEEDVR SPATIAL START', flush=True)
    with (BATCH / 'seedvr-spatial.log').open('a', encoding='utf-8') as stream:
        subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True)
    print('SEEDVR SPATIAL COMPLETED', flush=True)


def main():
    BATCH.mkdir(parents=True, exist_ok=True)
    spatial()
    base = SPATIAL / '03_runtime_pack'
    plan = v2.build_plan(SPATIAL, base, [REF], model='apo-8', transparent_rgb_mode='nearest-opaque-dilate')
    v2.write_json(BATCH / 'temporal-plan.json', plan)
    print('APOLLO8 START', flush=True)
    v2.build_run(SPATIAL, base, TEMPORAL, [REF], plan['plan_sha256'],
                 v2.DEFAULT_TVAI_FFMPEG, v2.DEFAULT_TVAI_MODEL_DIR, 'apo-8',
                 v2.DEFAULT_DEVICE, 'ffmpeg', True,
                 transparent_rgb_mode='nearest-opaque-dilate')
    print('APOLLO8 COMPLETED', flush=True)
    source_split = BATCH / 'artifacts/OHRSGATE-source-split'
    final_split = BATCH / 'artifacts/OHRSGATE-final-split'
    splitter.split(TEMPORAL / '03_runtime_pack', source_split,
                   ROOT / 'animations/index/occurrences.csv', source_split.exists())
    neutral.build(source_split, final_split, {REF}, final_split.exists(), 'premultiply', None, 16)
    FINAL.mkdir(parents=True, exist_ok=True)
    job = {'resref': REF, 'spatial_run': SPATIAL.relative_to(ROOT).as_posix(),
           'temporal_run': TEMPORAL.relative_to(ROOT).as_posix(),
           'final_run': FINAL.relative_to(ROOT).as_posix(),
           'final_split': final_split.relative_to(ROOT).as_posix(),
           'recipe': {'spatial': 'SeedVR2 7B INT8 / LAB', 'seed': 4220,
                      'temporal': 'Apollo8 15->30 nearest-opaque-dilate',
                      'inner_feather_x4': 16, 'rgb_policy': 'premultiply-once'}}
    record = {'schema': 'bg2-upscale-animation-visual-treatment-v1', 'status': 'completed',
              'created_utc': v2.utc_now(), 'resref': REF, 'source_run': job['temporal_run'],
              'source_run_manifest_sha256': v2.sha256_file(TEMPORAL / 'manifest.json'),
              'output_split_root': job['final_split'],
              'output_manifest_sha256': v2.sha256_file(final_split / 'manifest.json'),
              'recipe': job['recipe'], 'qa_status': 'pending-user-preview', 'installed': False,
              'recipe_script': Path(__file__).relative_to(ROOT).as_posix()}
    v2.write_json(FINAL / 'manifest.json', record)
    preview.PREVIEWS = BATCH / 'previews'
    preview.PREVIEWS.mkdir(exist_ok=True)
    checks = preview.asset_preview(job)
    v2.write_json(BATCH / 'local-checks.json', {'status': 'completed', 'resources': [checks], 'installed': False})
    compare_ab(final_split, preview.PREVIEWS)
    v2.write_json(BATCH / 'manifest.json', {'schema': 'bg2-upscale-animation-batch-production-v1',
                  'status': 'completed', 'created_utc': v2.utc_now(), 'resources': [job],
                  'qa_status': 'pending-user-preview', 'installed': False,
                  'previous_variant': 'animations/ressources/OHRSGATE/runs/ohrsgate-portails-final-20261010-v1'})
    print('SEEDVR FINAL + COMPARISON COMPLETED', flush=True)


def compare_ab(final_split, out):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    old = ROOT / 'animations/batches/portails-cinq-20261010-v1/artifacts/OHRSGATE-final-split/OH4220'
    new = final_split / 'OH4220'
    _, old_resources = v2.validate_v2_pack(old)
    _, new_resources = v2.validate_v2_pack(new)
    left, right = old_resources[0], new_resources[0]
    assert left['cycles'] == right['cycles']
    x1 = v2.load_json(SPATIAL / 'resources/OHRSGATE/01_frames_x1/manifest.json')
    canvas = [v * 4 for v in x1['aligned_canvas_size']]
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
    width, height = canvas[0] * 2 + 12, canvas[1] + 66
    mp4 = out / 'OHRSGATE-ReboutCX-vs-SeedVR-x4.mp4'
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
               '-video_size', f'{width}x{height}', '-framerate', '30', '-i', '-',
               '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-preset', 'fast',
               '-crf', '12', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(mp4)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    images = []
    timeline = right['cycles'][0]['timeline_frame_indices']
    for phase, number in enumerate(timeline):
        native = right['cycles'][0]['native_frame_indices'][phase // 2]
        offset = [v * 4 for v in x1['frames'][native]['canvas_offset']]
        board = Image.new('RGB', (width, height), tuple(preview.BG))
        for pack, resource, xpos in [(old, left, 0), (new, right, canvas[0] + 12)]:
            frame = resource['frames'][number]
            w, h = frame['physical_size_x4']
            pixels = np.frombuffer((pack / frame['asset']).read_bytes(), np.uint8).reshape(h, w, 4)
            other = (right if resource is left else left)['frames'][number]
            assert frame['logical_size_x1'] == other['logical_size_x1']
            assert frame['centre_x1'] == other['centre_x1']
            other_pack = new if pack == old else old
            other_pixels = np.frombuffer((other_pack / other['asset']).read_bytes(), np.uint8).reshape(h, w, 4)
            assert np.array_equal(pixels[..., 3], other_pixels[..., 3]), 'alpha A/B divergent'
            board.paste(preview.panel(pixels[..., :3], canvas, offset), (xpos, 66))
        draw = ImageDraw.Draw(board)
        draw.text((10, 8), 'OHRSGATE - meme alpha / meme cadence / meme fondu16', font=font, fill='white')
        draw.text((10, 36), 'ReboutCX x4 / Apollo8', font=font, fill=(190, 200, 215))
        draw.text((canvas[0] + 22, 36), 'SeedVR2 7B LAB x4 / Apollo8', font=font, fill=(190, 200, 215))
        process.stdin.write(board.tobytes())
        images.append(board.resize((width // 2, height // 2), Image.Resampling.BOX))
        if phase == len(timeline) // 2:
            board.save(out / 'OHRSGATE-ReboutCX-vs-SeedVR-poster.png')
    process.stdin.close()
    assert process.wait() == 0
    durations = [round((i+1)*100/30)*10 - round(i*100/30)*10 for i in range(len(images))]
    images[0].save(out / 'OHRSGATE-ReboutCX-vs-SeedVR.gif', save_all=True,
                   append_images=images[1:], duration=durations, loop=0, disposal=2)
    v2.write_json(out / 'ab-contract.json', {'same_alpha_all_60_frames': True,
                  'same_timeline_and_duration': True, 'same_geometry_and_centres': True,
                  'left': str(old), 'right': str(new), 'installed': False})


if __name__ == '__main__':
    main()
