"""Synchronized final 3B/7B renders; native anchors/timing and common alpha."""
from pathlib import Path
import json
import html
import shutil
import subprocess
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1'
OUT = BATCH / 'preview'
FFMPEG, FFPROBE = shutil.which('ffmpeg'), shutil.which('ffprobe')
FONT = 'C:/Windows/Fonts/consola.ttf'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def poses(asset, variant):
    runs = ROOT / 'effects/ressources' / asset['resref'] / 'runs'
    spatial = load(runs / variant['spatial_run'] / '01-spatial-x4/manifest.json')
    final_root = runs / variant['treatment_run'] / '02-interpolation'
    final = load(final_root / 'manifest.json')
    assert final['rgb_encoding'] == 'premultiplied'
    size = tuple(v * 4 for v in spatial['aligned_canvas_size_x1'])
    cache = {}
    for frame in final['frames']:
        key = (frame['rgba_x4'], tuple(frame['runtime_crop_box_x4']))
        if key not in cache:
            rgba = Image.open(final_root / frame['rgba_x4']).convert('RGBA')
            canvas = Image.new('RGBA', size, (0, 0, 0, 0))
            crop = frame['runtime_crop_box_x4']
            canvas.paste(rgba, (crop[0], crop[1]))
            cache[key] = canvas
        yield cache[key]


def encoder(path, size):
    log = path.with_suffix('.encode.log').open('w', encoding='utf-8')
    process = subprocess.Popen([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y',
        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{size[0]}x{size[1]}', '-r', '30',
        '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)],
        stdin=subprocess.PIPE, stdout=log, stderr=log)
    return process, log


def finish(process, log):
    process.stdin.close()
    assert process.wait() == 0
    log.close()


def probe(path, phases):
    result = json.loads(subprocess.check_output([FFPROBE, '-v', 'error',
        '-show_streams', '-of', 'json', str(path)]))
    video = next(s for s in result['streams'] if s['codec_type'] == 'video')
    assert video['avg_frame_rate'] == '30/1' and int(video['nb_frames']) == phases
    return {'path': path.relative_to(BATCH).as_posix(), 'phases': phases, 'fps': 30,
            'size': [video['width'], video['height']], 'bytes': path.stat().st_size}


def main():
    OUT.mkdir(exist_ok=True)
    videos = OUT / 'videos'; videos.mkdir(exist_ok=True)
    assets = load(BATCH / 'batch.json')['assets']
    grid_cache, reports, figures, posters = [], [], [], []
    font = ImageFont.truetype(FONT, 24)
    small_font = ImageFont.truetype(FONT, 18)
    for asset in assets:
        assert load(BATCH / 'checks' / (asset['resref'] + '.json'))['passed']
        run_root = ROOT / 'effects/ressources' / asset['resref'] / 'runs'
        spatial_a = load(run_root / asset['baseline_3b']['spatial_run'] / '01-spatial-x4/manifest.json')
        spatial_b = load(run_root / asset['spatial_run'] / '01-spatial-x4/manifest.json')
        assert spatial_a['parameters']['model'] == 'seedvr2_3b_int8_convrot.safetensors'
        assert spatial_b['parameters']['model'] == 'seedvr2_7b_int8_convrot.safetensors'
        assert {k:v for k,v in spatial_a['parameters'].items() if k != 'model'} == {
            k:v for k,v in spatial_b['parameters'].items() if k != 'model'}
        for a_frame, b_frame in zip(spatial_a['frames'], spatial_b['frames'], strict=True):
            for key in ['frame', 'source_rgb_sha256', 'source_alpha_sha256', 'centre_x1',
                        'logical_size_x1', 'physical_size_xn', 'runtime_crop_box_xn']:
                assert a_frame[key] == b_frame[key], (asset['resref'], key)
        path = videos / (asset['resref'] + '-3B-7B.mp4')
        left = poses(asset, asset['baseline_3b']); right = poses(asset, asset)
        thumbs, phases, delta, visible, differing = [], 0, 0, 0, 0
        process = log = None
        for a, b in zip(left, right, strict=True):
            assert a.size == b.size
            arr_a = np.asarray(a); arr_b = np.asarray(b)
            assert np.array_equal(arr_a[:, :, 3], arr_b[:, :, 3]), asset['resref']
            mask = arr_a[:, :, 3] > 0
            diff = np.abs(arr_a[:, :, :3].astype(np.int16) - arr_b[:, :, :3].astype(np.int16))
            delta += int(diff[mask].sum()); visible += int(mask.sum())
            differing += int(np.count_nonzero(np.any(diff > 0, axis=2) & mask))
            canvas = Image.new('RGB', (a.width * 2, a.height + 48), (8, 8, 12))
            draw = ImageDraw.Draw(canvas)
            draw.text((10, 10), asset['resref'] + ' / 3B', fill='white', font=font)
            draw.text((a.width + 10, 10), asset['resref'] + ' / 7B', fill='white', font=font)
            # These RGB bytes are premultiplied already; do not apply alpha again.
            canvas.paste(a.convert('RGB'), (0, 48)); canvas.paste(b.convert('RGB'), (a.width, 48))
            if process is None: process, log = encoder(path, canvas.size)
            process.stdin.write(canvas.tobytes())
            tile = Image.new('RGB', (352, 208), 'black')
            for image, x in [(a, 0), (b, 176)]:
                thumb = image.convert('RGB'); thumb.thumbnail((172, 208), Image.Resampling.LANCZOS)
                tile.paste(thumb, (x + (176 - thumb.width)//2, (208 - thumb.height)//2))
            thumbs.append(tile); phases += 1
        finish(process, log)
        metadata = probe(path, phases)
        reports.append({'resref': asset['resref'], 'video': metadata,
            'same_alpha_every_phase': True, 'same_anchors_and_geometry': True,
            'same_inputs_and_parameters_except_model': True,
            'rgb_visible_mean_abs_delta_255': delta / (3 * visible),
            'visible_pixels_different_percent': 100 * differing / visible,
            'metric_interpretation': 'difference only; no model quality ranking'})
        grid_cache.append(thumbs)
        posters.append(max(thumbs, key=lambda im: np.asarray(im).astype(np.uint64).sum()))
        figures.append(f'<figure><video src="videos/{html.escape(path.name)}" autoplay loop muted playsinline preload="auto"></video><figcaption>{asset["resref"]} · 3B à gauche / 7B à droite</figcaption></figure>')
        print(asset['resref'], 'comparison verified', phases, flush=True)
    assert len(assets) == 10
    cell_w, cell_h = 360, 266
    size = (cell_w * 5, cell_h * 2)
    base = Image.new('RGB', size, (13, 13, 17)); draw = ImageDraw.Draw(base)
    for i, asset in enumerate(assets):
        x, y = i % 5 * cell_w, i // 5 * cell_h
        draw.text((x+8, y+216), asset['resref'], font=small_font, fill='white')
        draw.text((x+8, y+241), '3B', font=small_font, fill='#8bc9ff')
        draw.text((x+184, y+241), '7B', font=small_font, fill='#d7a7ff')
    poster = base.copy()
    for i, tile in enumerate(posters): poster.paste(tile, (i%5*cell_w+4, i//5*cell_h+4))
    poster.save(OUT / 'comparison-poster.png')
    phases = max(len(p) for p in grid_cache) + 30
    path = OUT / 'comparison-animated-30fps.mp4'; process, log = encoder(path, size)
    for phase in range(phases):
        canvas = base.copy()
        for i, tiles in enumerate(grid_cache):
            index = phase % (len(tiles) + 15)
            if index < len(tiles): canvas.paste(tiles[index], (i%5*cell_w+4, i//5*cell_h+4))
        process.stdin.write(canvas.tobytes())
    finish(process, log); grid = probe(path, phases)
    subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', str(path),
        '-filter_complex', '[0:v]fps=12,scale=1200:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer',
        '-loop', '0', str(OUT / 'comparison-animated.gif')], check=True)
    (OUT / 'comparison.json').write_text(json.dumps({'assets': reports, 'grid': grid,
        'encoding': 'premultiplied RGB over black, alpha applied once upstream',
        'installed_variant': '3B unchanged', 'visual_qa': 'pending-user'}, indent=2)+'\n', encoding='utf-8')
    template = (Path(__file__).parent / 'gallery.html').read_text(encoding='utf-8')
    (OUT / 'index.html').write_text(template.replace('<!-- PAIRS -->', '\n'.join(figures)), encoding='utf-8')
    print('10 synchronized comparisons and animated sheet ready', flush=True)


if __name__ == '__main__': main()
