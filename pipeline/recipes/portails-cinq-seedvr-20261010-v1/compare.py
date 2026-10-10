"""Native / first recipe / SeedVR: 5-row sheet, animated sheet and all-cycle videos.

Only reads completed variants. Original comparison batches are never rewritten.
"""
import argparse
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
sys.path.insert(0, str(ROOT / 'pipeline/recipes/portails-cinq-20261010-v1'))
import run_animation_upscale_30fps_v2 as v2
import build_previews as preview
from bam_export import decode_bam

BATCH = ROOT / 'animations/batches/portails-cinq-seedvr-20261010-v1'
FIRST = ROOT / 'animations/batches/portails-cinq-20261010-v1'
OUT = BATCH / 'comparisons'
ORDER = ['BDFORCEW', 'OHDLPORT', 'OHHPORT', 'OHRSGATE', 'SPDIMNDR']
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 22)
SMALL = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)


def leaf(job):
    split = ROOT / job['final_split']
    index = v2.load_json(split / 'manifest.json')
    pack = split / index['areas'][0]['directory']
    _, resources = v2.validate_v2_pack(pack)
    return pack, resources[0]


def context(old, new):
    ref = new['resref']
    old_pack, old_resource = leaf(old)
    new_pack, new_resource = leaf(new)
    assert old_resource['cycles'] == new_resource['cycles']
    assert old_resource['frame_count'] == new_resource['frame_count']
    assert [(f['logical_size_x1'], f['centre_x1']) for f in old_resource['frames']] == [(f['logical_size_x1'], f['centre_x1']) for f in new_resource['frames']]
    x1 = v2.load_json(ROOT / new['spatial_run'] / f'resources/{ref}/01_frames_x1/manifest.json')
    old_x1 = v2.load_json(ROOT / old['spatial_run'] / f'resources/{ref}/01_frames_x1/manifest.json')
    assert x1['source_sha256'] == old_x1['source_sha256']
    assert x1['aligned_canvas_size'] == old_x1['aligned_canvas_size']
    data = (ROOT / f'animations/ressources/{ref}/source.bam').read_bytes()
    if data[:4] == b'BAMC':
        data = zlib.decompress(data[12:])
    source = decode_bam(data)
    first_method = 'xBR2 + nearest2' if ref in ('OHDLPORT', 'OHHPORT') else 'ReboutCX'
    return {'ref': ref, 'old_pack': old_pack, 'old': old_resource,
            'new_pack': new_pack, 'new': new_resource, 'x1': x1,
            'source': source, 'cache': {}, 'method': first_method,
            'canvas': [v * 4 for v in x1['aligned_canvas_size']],
            'selected_cycle': 2 if ref == 'BDFORCEW' else 1 if ref == 'SPDIMNDR' else 0}


def panels(ctx, cycle_number, phase):
    cycle = ctx['new']['cycles'][cycle_number]
    native = cycle['native_frame_indices'][phase // 2]
    output = cycle['timeline_frame_indices'][phase]
    entry = ctx['x1']['frames'][native]
    offset = [v * 4 for v in entry['canvas_offset']]
    frames, palette, _ = ctx['source']
    idx, _, _, tr = frames[native]
    rgb = palette[idx].copy()
    rgb[idx == tr] = 0
    images = [preview.panel(rgb.repeat(4, 0).repeat(4, 1), ctx['canvas'], offset)]
    for name in ('old', 'new'):
        key = name, output
        if key not in ctx['cache']:
            f = ctx[name]['frames'][output]
            w, h = f['physical_size_x4']
            ctx['cache'][key] = np.frombuffer((ctx[name + '_pack'] / f['asset']).read_bytes(), np.uint8).reshape(h, w, 4)
        images.append(preview.panel(ctx['cache'][key][..., :3], ctx['canvas'], offset))
    return images


def triple(ctx, number, phase):
    w, h = ctx['canvas']
    image = Image.new('RGB', (w * 3 + 24, h + 70), tuple(preview.BG))
    d = ImageDraw.Draw(image)
    d.text((10, 7), f"{ctx['ref']} | cycle {number}", font=FONT, fill='white')
    titles = ['Native 15 fps', ctx['method'] + ' x4 / 30 fps', 'SeedVR2 7B LAB x4 / 30 fps']
    for i, panel in enumerate(panels(ctx, number, phase)):
        x = i * (w + 12)
        image.paste(panel, (x, 70))
        d.text((x + 10, 37), titles[i], font=FONT, fill=(190, 200, 215))
    return image


def encoder(path, size):
    w, h = size
    return subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
        '-pixel_format', 'rgb24', '-video_size', f'{w}x{h}', '-framerate', '30', '-i', '-',
        '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-preset', 'fast', '-crf', '12',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)


def asset_movies(ctx):
    folder = OUT / ctx['ref']
    folder.mkdir(exist_ok=True)
    for c in ctx['new']['cycles']:
        number = c['cycle']
        path = folder / f'cycle-{number:02d}-all-versions-x4.mp4'
        if path.exists():
            continue
        first = triple(ctx, number, 0)
        process = encoder(path, first.size)
        for phase in range(len(c['timeline_frame_indices'])):
            image = first if phase == 0 else triple(ctx, number, phase)
            process.stdin.write(image.tobytes())
        process.stdin.close()
        assert process.wait() == 0
        print(f"COMPARISON {ctx['ref']} cycle {number}", flush=True)


def sheet(contexts, master_phase=None):
    cell_w = 370
    left = 20
    top = 72
    heights = [ctx['canvas'][1] // 2 + 45 for ctx in contexts]
    board = Image.new('RGB', (cell_w * 3 + 40, sum(heights) + top + 20), tuple(preview.BG))
    d = ImageDraw.Draw(board)
    for i, title in enumerate(['NATIVE', 'PREMIERE RECETTE', 'SEEDVR2 7B INT8 / LAB']):
        d.text((left + i * cell_w + 8, 17), title, font=FONT, fill='white')
    d.text((28, 47), 'Memes centres et durees - aucune installation - apercu x2', font=SMALL, fill=(180, 193, 213))
    for ctx, row_h in zip(contexts, heights):
        cycle = ctx['selected_cycle']
        count = len(ctx['new']['cycles'][cycle]['timeline_frame_indices'])
        phase = count // 2 if master_phase is None else master_phase % count
        d.text((left + 8, top + 5), f"{ctx['ref']} - cycle {cycle}", font=FONT, fill='white')
        d.text((left + cell_w + 8, top + 5), ctx['method'], font=FONT, fill=(196, 205, 224))
        for i, image in enumerate(panels(ctx, cycle, phase)):
            im = image.resize((image.width // 2, image.height // 2), Image.Resampling.BOX)
            assert im.width <= cell_w
            x = left + i * cell_w + (cell_w - im.width) // 2
            board.paste(im, (x, top + 38))
        top += row_h
        d.line((left, top - 1, board.width - left, top - 1), fill=(62, 69, 82))
    return board


def report(contexts, complete):
    cards = []
    for ctx in contexts:
        default = ctx['selected_cycle']
        choices = ''.join(f'<option {"selected" if c["cycle"] == default else ""} value="{ctx["ref"]}/cycle-{c["cycle"]:02d}-all-versions-x4.mp4">Cycle {c["cycle"]} — {len(c["timeline_frame_indices"])/30:.3f} s</option>' for c in ctx['new']['cycles'])
        src = f"{ctx['ref']}/cycle-{default:02d}-all-versions-x4.mp4"
        cards.append(f'<article><h2>{ctx["ref"]}</h2><p>Native · {ctx["method"]} · SeedVR2 7B LAB</p>'
            f'<select onchange="const v=this.nextElementSibling;v.src=this.value;v.play()">{choices}</select>'
            f'<video controls autoplay muted loop playsinline src="{src}"></video></article>')
    page = '<!doctype html><html lang="fr"><meta charset="utf-8"><title>5 animations — toutes les versions</title><style>body{background:#181b21;color:#eee;font:16px system-ui;margin:32px}article{background:#252931;padding:20px;margin:24px 0;border-radius:12px}video{display:block;width:100%;margin-top:12px}select{padding:8px;background:#181b21;color:#eee}img{max-width:100%}</style><h1>5 animations — toutes les versions</h1><p>Colonnes : native 15 fps · première recette x4/30 fps · SeedVR2 7B LAB x4/30 fps. Aucune installation. SPDIMNDR : cycles 0/2/3/4 linéaires, cycle 1 bouclé.</p>'
    if complete:
        page += '<p><a href="planche-toutes-versions.png">Planche fixe x2</a> · <a href="planche-toutes-versions-30fps.mp4">Planche animée 30 fps</a></p>'
    page += ''.join(cards) + '</html>'
    (OUT / 'index.html').write_text(page, encoding='utf-8')


def verify_movie(path, expected_frames):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
        'stream=codec_name,nb_frames,r_frame_rate', '-show_entries', 'format=duration',
        '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    stream = info['streams'][0]
    assert stream['codec_name'] == 'h264' and stream['r_frame_rate'] == '30/1'
    assert int(stream['nb_frames']) == expected_frames
    assert abs(float(info['format']['duration']) - expected_frames / 30) < .002


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--available', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    first = {j['resref']: j for j in v2.load_json(FIRST / 'manifest.json')['resources']}
    current = v2.load_json(BATCH / 'manifest.json')
    new = {j['resref']: j for j in current['resources']}
    if not args.available:
        assert current['status'] == 'completed' and set(new) == set(ORDER)
    contexts = []
    for ref in ORDER:
        if ref not in new:
            continue
        ctx = context(first[ref], new[ref])
        contexts.append(ctx)
        if ref != 'OHRSGATE' and not (BATCH / f'{ref}-local-checks.json').exists():
            preview.PREVIEWS = BATCH / 'previews'
            preview.PREVIEWS.mkdir(exist_ok=True)
            result = preview.asset_preview(new[ref])
            v2.write_json(BATCH / f'{ref}-local-checks.json', result)
        asset_movies(ctx)
    complete = len(contexts) == 5
    if complete:
        sheet(contexts).save(OUT / 'planche-toutes-versions.png')
        path = OUT / 'planche-toutes-versions-30fps.mp4'
        if not path.exists():
            first_board = sheet(contexts, 0)
            process = encoder(path, first_board.size)
            for phase in range(180):
                process.stdin.write((first_board if phase == 0 else sheet(contexts, phase)).tobytes())
            process.stdin.close()
            assert process.wait() == 0
        verify_movie(path, 180)
        for ctx in contexts:
            for cycle in ctx['new']['cycles']:
                verify_movie(OUT / ctx['ref'] / f"cycle-{cycle['cycle']:02d}-all-versions-x4.mp4",
                             len(cycle['timeline_frame_indices']))
        v2.write_json(OUT / 'comparison-contract.json', {'status': 'completed', 'assets': ORDER,
            'columns': ['native', 'first-recipe', 'seedvr7b-lab'], 'same_geometry_and_centres': True,
            'same_native_lookup_and_duration': True, 'cycles_in_reader': sum(len(c['new']['cycles']) for c in contexts),
            'movie_frame_counts_and_durations': True, 'installed': False})
    report(contexts, complete)
    print('COMPARISON REPORT COMPLETED', flush=True)


if __name__ == '__main__':
    main()
