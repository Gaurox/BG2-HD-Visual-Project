"""Final blend-safe runtime bytes -> native/final comparisons and local checks.

Left: native BAM at 15fps. Right: final x4 at 30fps. Same centres, same elapsed time.
Both panels simulate additive Blended rendering on a neutral dark background.
GIF overview x2; cycle MP4s x4. No game or authority writes.
"""
import argparse
import csv
import html
import json
from pathlib import Path
import subprocess
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam
import run_animation_upscale_30fps_v2 as v2
from build_spatial import BATCH

PREVIEWS = BATCH / 'previews'
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
BG = np.array([24, 27, 33], dtype=np.uint8)


def panel(rgb, canvas, offset):
    width, height = canvas
    result = np.zeros((height, width, 3), dtype=np.uint8)
    x, y = offset
    h, w = rgb.shape[:2]
    assert 0 <= x <= width - w and 0 <= y <= height - h
    result[y:y+h, x:x+w] = rgb
    return Image.fromarray(np.minimum(result.astype(np.uint16) + BG, 255).astype(np.uint8))


def render(ref, cycle_number, phase, resource, x1, source_frames, final_pack, cache):
    cycle = resource['cycles'][cycle_number]
    native = cycle['native_frame_indices'][phase // 2]
    output = cycle['timeline_frame_indices'][phase]
    entry = x1['frames'][native]
    idx, _, _, tr = source_frames[native]
    _, palette, _ = cache['source']
    source_rgb = palette[idx].copy()
    source_rgb[idx == tr] = 0
    source_rgb = source_rgb.repeat(4, axis=0).repeat(4, axis=1)
    f = resource['frames'][output]
    width, height = f['physical_size_x4']
    assert f['logical_size_x1'] == entry['source_size']
    assert f['centre_x1'] == entry['centre']
    if output not in cache:
        cache[output] = np.frombuffer((final_pack / f['asset']).read_bytes(), np.uint8).reshape(height, width, 4)
    rgb = cache[output][..., :3]
    canvas = tuple(v * 4 for v in x1['aligned_canvas_size'])
    offset = tuple(v * 4 for v in entry['canvas_offset'])
    left = panel(source_rgb, canvas, offset)
    right = panel(rgb, canvas, offset)
    board = Image.new('RGB', (canvas[0] * 2 + 12, canvas[1] + 66), tuple(BG))
    board.paste(left, (0, 66))
    board.paste(right, (canvas[0] + 12, 66))
    d = ImageDraw.Draw(board)
    d.text((10, 8), f'{ref}  |  cycle {cycle_number}', font=FONT, fill='white')
    d.text((10, 36), 'Source native 15 fps', font=FONT, fill=(190, 200, 215))
    d.text((canvas[0] + 22, 36), 'Resultat x4 / 30 fps', font=FONT, fill=(190, 200, 215))
    return board


def asset_preview(job):
    ref = job['resref']
    folder = PREVIEWS / ref
    folder.mkdir(parents=True, exist_ok=True)
    spatial = ROOT / job['spatial_run']
    split = ROOT / job['final_split']
    split_index = v2.load_json(split / 'manifest.json')
    leaf = split / split_index['areas'][0]['directory']
    final_manifest, resources = v2.validate_v2_pack(leaf)
    resource = next(r for r in resources if r['resref'] == ref)
    source_pack = ROOT / job['temporal_run'] / '03_runtime_pack'
    before = v2.load_json(source_pack / 'manifest.json')['resources'][0]
    native_manifest = v2.load_json(spatial / '03_runtime_pack/manifest.json')['resources'][0]
    assert [c['native_frame_indices'] for c in resource['cycles']] == [c['frame_indices'] for c in native_manifest['cycles']]
    assert resource['native_fps']['numerator'] == 15 and resource['target_fps']['numerator'] == 30
    loss = []
    core_loss = []
    for f, prior in zip(resource['frames'], before['frames'], strict=True):
        assert f['logical_size_x1'] == prior['logical_size_x1'] and f['centre_x1'] == prior['centre_x1']
        w, h = f['physical_size_x4']
        a = np.frombuffer((leaf / f['asset']).read_bytes(), np.uint8).reshape(h, w, 4)
        b = np.frombuffer((source_pack / prior['asset']).read_bytes(), np.uint8).reshape(h, w, 4)
        assert (a[..., 3] <= b[..., 3]).all()
        if job['recipe']['inner_feather_x4'] == 0:
            assert np.array_equal(a[..., 3], b[..., 3])
        expected = np.rint(b[..., :3].astype(np.float32) * (a[..., 3, None] / 255.)).astype(np.uint8)
        assert np.array_equal(a[..., :3], expected), f'{ref}: premultiplication incorrecte'
        assert not a[a[..., 3] == 0, :3].any()
        old = (b[..., :3].astype(float) * (b[..., 3, None] / 255.)) @ np.array([.2126, .7152, .0722])
        new = a[..., :3].astype(float) @ np.array([.2126, .7152, .0722])
        if old.sum() > 0:
            loss.append(float(100 * (1 - new.sum() / old.sum())))
            core = old >= np.percentile(old[old > 0], 95)
            core_loss.append(float(100 * (1 - new[core].sum() / old[core].sum())))
    x1 = v2.load_json(spatial / f'resources/{ref}/01_frames_x1/manifest.json')
    data = (ROOT / f'animations/ressources/{ref}/source.bam').read_bytes()
    if data[:4] == b'BAMC':
        data = zlib.decompress(data[12:])
    source = decode_bam(data)
    cache = {'source': source}
    comparisons = []
    selected = [2] if ref == 'BDFORCEW' else list(range(5)) if ref == 'SPDIMNDR' else [0]
    for cycle in resource['cycles']:
        number = cycle['cycle']
        timeline = cycle['timeline_frame_indices']
        assert len(timeline) == 2 * len(cycle['native_frame_indices'])
        if ref == 'SPDIMNDR' and number in (0, 2, 3, 4):
            assert timeline[-2:] == [cycle['native_frame_indices'][-1]] * 2
        video = folder / f'cycle-{number:02d}-comparison-x4.mp4'
        if not video.exists():
            first = render(ref, number, 0, resource, x1, source[0], leaf, cache)
            w, h = first.size
            cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                   '-video_size', f'{w}x{h}', '-framerate', '30', '-i', '-', '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
                   '-c:v', 'libx264', '-preset', 'fast', '-crf', '12', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)]
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for phase in range(len(timeline)):
                image = first if phase == 0 else render(ref, number, phase, resource, x1, source[0], leaf, cache)
                process.stdin.write(image.tobytes())
                if number in selected:
                    comparisons.append(image.resize((image.width // 2, image.height // 2), Image.Resampling.BOX))
            process.stdin.close()
            assert process.wait() == 0
        elif number in selected:
            for phase in range(len(timeline)):
                image = render(ref, number, phase, resource, x1, source[0], leaf, cache)
                comparisons.append(image.resize((image.width // 2, image.height // 2), Image.Resampling.BOX))
        if number in selected and ref == 'SPDIMNDR':
            gap = Image.new('RGB', comparisons[-1].size, tuple(BG))
            d = ImageDraw.Draw(gap)
            d.text((10, 12), f'SPDIMNDR - fin du cycle {number}', fill='white')
            comparisons.extend([gap] * 9)
        print(f'PREVIEW {ref} cycle {number}', flush=True)
    gif = PREVIEWS / f'{ref}-comparison.gif'
    durations = [round((i + 1) * 100 / 30) * 10 - round(i * 100 / 30) * 10 for i in range(len(comparisons))]
    comparisons[0].save(gif, save_all=True, append_images=comparisons[1:], duration=durations, loop=0, disposal=2)
    poster = PREVIEWS / f'{ref}-poster.png'
    middle_cycle = 1 if ref == 'SPDIMNDR' else selected[0]
    phase = len(resource['cycles'][middle_cycle]['timeline_frame_indices']) // 2
    render(ref, middle_cycle, phase, resource, x1, source[0], leaf, cache).save(poster)
    return {'resref': ref, 'frame_count': resource['frame_count'], 'cycle_slots': [len(c['native_frame_indices']) for c in resource['cycles']],
            'gif': gif.relative_to(ROOT).as_posix(), 'poster': poster.relative_to(ROOT).as_posix(),
            'cycles': [{'cycle': c['cycle'], 'duration_seconds': len(c['timeline_frame_indices']) / 30,
                        'video': (folder / f"cycle-{c['cycle']:02d}-comparison-x4.mp4").relative_to(ROOT).as_posix()} for c in resource['cycles']],
            'checks': {'geometry_and_centres': True, 'native_lookup_and_duration': True,
                       'premultiplied_exactly_once': True, 'zero_rgb_under_zero_alpha': True,
                       'alpha_never_extended': True,
                       'light_loss_mean_pct': round(float(np.mean(loss)), 3),
                       'light_loss_worst_pct': round(max(loss), 3),
                       'core_p95_loss_worst_pct': round(max(core_loss), 3)}}


def main():
    PREVIEWS.mkdir(exist_ok=True)
    batch = v2.load_json(BATCH / 'manifest.json')
    results = [asset_preview(job) for job in batch['resources']]
    v2.write_json(BATCH / 'local-checks.json', {'status': 'completed', 'resources': results, 'installed': False})
    cards = []
    for item in results:
        default = 2 if item['resref'] == 'BDFORCEW' else 0
        choices = ''.join(f'<option {"selected" if c["cycle"] == default else ""} value="{Path(c["video"]).relative_to(PREVIEWS.relative_to(ROOT)).as_posix()}">Cycle {c["cycle"]} — {c["duration_seconds"]:.3f} s</option>' for c in item['cycles'])
        src = Path(item['cycles'][default]['video']).relative_to(PREVIEWS.relative_to(ROOT)).as_posix()
        cards.append(f'<article><h2>{item["resref"]}</h2><p>Gauche : source 15 fps · Droite : résultat x4 / 30 fps</p>'
                     f'<select onchange="const v=this.nextElementSibling;v.src=this.value;v.play()">{choices}</select>'
                     f'<video src="{src}" controls autoplay muted loop playsinline></video></article>')
    page = '<!doctype html><html lang="fr"><meta charset="utf-8"><title>Portails — previews avant installation</title><style>body{background:#181b21;color:#eee;font:16px system-ui;margin:32px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(500px,1fr));gap:24px}article{background:#252931;padding:20px;border-radius:12px}video{display:block;width:100%;margin-top:12px}select{padding:8px;background:#181b21;color:#eee}</style><h1>5 animations — previews avant installation</h1><p>Aucune installation. Comparaison synchronisée sur fond neutre. SPDIMNDR : cycles 0/2/3/4 linéaires, cycle 1 bouclé.</p><main>' + ''.join(cards) + '</main></html>'
    (PREVIEWS / 'index.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    main()
