"""Render exact premultiplied RGB over black; native anchors and 30 FPS retained."""
from __future__ import annotations
import argparse
import html
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot33-seedvr7b-apollo30-20261014-v1'
OUT = BATCH / 'preview'
FFMPEG = shutil.which('ffmpeg')
FFPROBE = shutil.which('ffprobe')


def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))


def encoder(path, size):
    log = path.with_suffix('.encode.log').open('w', encoding='utf-8')
    command = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
               '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', '30', '-i', '-',
               '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt',
               'yuv420p', '-movflags', '+faststart', str(path)]
    return subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log, stderr=log), log


def frames(asset):
    root = ROOT / 'effects/ressources' / asset['resref'] / 'runs'
    final_root = root / asset['treatment_run'] / '02-interpolation'
    final = load(final_root / 'manifest.json')
    spatial = load(root / asset['spatial_run'] / '01-spatial-x4/manifest.json')
    assert final['rgb_encoding'] == 'premultiplied'
    size = tuple(v * 4 for v in spatial['aligned_canvas_size_x1'])
    cached = {}
    for frame in final['frames']:
        key = (frame['rgba_x4'], tuple(frame['runtime_crop_box_x4']))
        if key not in cached:
            with Image.open(final_root / frame['rgba_x4']) as image:
                image = image.convert('RGB')  # Already premultiplied: never apply alpha again.
            canvas = Image.new('RGB', size, 'black')
            crop = frame['runtime_crop_box_x4']; canvas.paste(image, (crop[0], crop[1]))
            cached[key] = canvas
        yield cached[key]


def probe(path, expected):
    data = json.loads(subprocess.check_output([FFPROBE, '-v', 'error', '-show_streams', '-of', 'json', str(path)]))
    video = next(s for s in data['streams'] if s['codec_type'] == 'video')
    assert video['avg_frame_rate'] == '30/1' and int(video['nb_frames']) == expected
    return {'path': path.relative_to(BATCH).as_posix(), 'frames': expected,
            'fps': 30, 'size': [video['width'], video['height']], 'bytes': path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--ready-only', action='store_true')
    parser.add_argument('--resref', action='append')
    args = parser.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    batch = load(BATCH / 'batch.json'); assets = batch['assets']; ready = []
    if args.resref:
        assert args.ready_only
        assets = [a for a in assets if a['resref'] in args.resref]
    videos = OUT / 'videos'; videos.mkdir(exist_ok=True)
    for asset in assets:
        check_path = BATCH / 'checks' / (asset['resref'] + '.json')
        if not check_path.exists():
            if args.ready_only: continue
            raise RuntimeError('Missing per-asset verification: ' + asset['resref'])
        assert load(check_path)['passed']
        final_path = ROOT / 'effects/ressources' / asset['resref'] / 'runs' / asset['treatment_run'] / '02-interpolation/manifest.json'
        phase_count = len(load(final_path)['frames']); path = videos / (asset['resref'] + '.mp4')
        if not path.exists():
            iterator = frames(asset); first = next(iterator); process, log = encoder(path, first.size)
            process.stdin.write(first.tobytes())
            for image in iterator: process.stdin.write(image.tobytes())
            process.stdin.close(); assert process.wait() == 0; log.close()
        asset['video'] = probe(path, phase_count); ready.append(asset)
        print(asset['resref'], 'video verified', phase_count, flush=True)
    if args.ready_only:
        return
    assert len(ready) == 33
    width, height = 1296, 1140; font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 20)
    cache = []; posters = []; cell_w, cell_h = 216, 190
    for asset in assets:
        poses = []
        for image in frames(asset):
            thumb = image.copy(); thumb.thumbnail((202, 148), Image.Resampling.NEAREST)
            tile = Image.new('RGB', (202, 148), 'black'); tile.paste(thumb, ((202-thumb.width)//2, (148-thumb.height)//2))
            poses.append(tile)
        cache.append(poses); posters.append(max(poses, key=lambda im: np.asarray(im).astype(np.uint64).sum()))
    total = max(len(f) for f in cache) + 30
    path = OUT / 'lot33-animated-30fps.mp4'; process, log = encoder(path, (width, height))
    base = Image.new('RGB', (width, height), (13, 13, 17)); draw = ImageDraw.Draw(base)
    for i, asset in enumerate(assets):
        x, y = (i % 6)*cell_w, (i // 6)*cell_h
        draw.text((x+8, y+163), asset['resref'], font=font, fill=(238, 238, 243))
    poster = base.copy()
    for i, thumb in enumerate(posters): poster.paste(thumb, ((i%6)*cell_w+7, (i//6)*cell_h+6))
    poster.save(OUT / 'lot33-poster.png')
    for phase in range(total):
        canvas = base.copy()
        for i, poses in enumerate(cache):
            position = phase % (len(poses) + 15)
            if position < len(poses): canvas.paste(poses[position], ((i%6)*cell_w+7, (i//6)*cell_h+6))
        process.stdin.write(canvas.tobytes())
    process.stdin.close(); assert process.wait() == 0; log.close()
    grid_video = probe(path, total)
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(path),
                    '-filter_complex', '[0:v]fps=12,scale=864:-1:flags=neighbor,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer',
                    '-loop', '0', str(OUT / 'lot33-animated.gif')], check=True)
    (OUT / 'preview.json').write_text(json.dumps({'assets': ready, 'grid_video': grid_video,
         'rgb_display': 'premultiplied RGB displayed directly over black',
         'grid_restart_gap_seconds': 0.5, 'gif_preview_fps': 12}, indent=2)+'\n', encoding='utf-8')
    tiles = '\n'.join(f'<figure><video src="videos/{a["resref"]}.mp4" autoplay loop muted playsinline preload="auto"></video><figcaption>{a["resref"]}</figcaption></figure>' for a in assets)
    template = (Path(__file__).parent / 'gallery.html').read_text(encoding='utf-8')
    (OUT / 'index.html').write_text(template.replace('<!-- EFFECTS -->', tiles), encoding='utf-8')
    print('33 videos + animated sheet + gallery complete', flush=True)


if __name__ == '__main__': main()
