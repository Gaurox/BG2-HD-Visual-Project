"""Five requested SeedVR alternatives: identical timing/finishing, no installation."""
from pathlib import Path
import json
import subprocess
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import split_animation_pack_by_area as split
import build_blended_rgb_neutral_pack as neutral
from bam_export import decode_bam
from workspace_paths import get_path

TAG = 'lot2-seedvr-comparison-20261011-v1'
OUT = ROOT/'animations/batches'/TAG
SPATIAL = ROOT/'animations/batches/lot2-seedvr7b-lab-x4-20261011-v1'
TEMPORAL = ROOT/'animations/batches/lot2-seedvr-apo8-20261011-v1'
CURRENT = ROOT/'animations/packs-par-zone/lot2-small-effects-20261011-v1-final-assets'
ORIGINAL = ROOT/'animations/batches/lot2-reboutcx-xbr-x4-20261011-v1'
JOBS = [('AM0504SB', 'AR0504', 'ReboutCX', 12), ('AM4000Z', 'AR4000', 'ReboutCX', 0),
        ('BUBBLEA', 'AR2903', 'xBR2 blend + nearest2', 0),
        ('EYESRED1', 'AR0329', 'xBR2 + nearest2', 0),
        ('WTRBODY1', 'AR0502', 'xBR2 + nearest2', 0)]
BG = (34, 34, 34)
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 21)
SMALL = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def sha(path):
    return v.sha256_file(path)


def finish():
    OUT.mkdir(parents=True, exist_ok=True)
    assert v.load_json(SPATIAL/'manifest.json')['status'] == 'completed'
    targets = ['AM0504SB', 'AM4000Z', 'BUBBLEA']
    base = SPATIAL/'03_runtime_pack'
    plan = v.build_plan(SPATIAL, base, targets, 'apo-8', preserve_segmented_holds=True,
                        transparent_rgb_mode='nearest-opaque-dilate')
    v.write_json(OUT/'temporal-plan.json', plan)
    v.build_run(SPATIAL, base, TEMPORAL, targets, plan['plan_sha256'],
                v.DEFAULT_TVAI_FFMPEG, v.DEFAULT_TVAI_MODEL_DIR, 'apo-8',
                v.DEFAULT_DEVICE, 'ffmpeg', True, preserve_segmented_holds=True,
                transparent_rgb_mode='nearest-opaque-dilate')
    raw = OUT/'artifacts/source-split'
    purple = OUT/'artifacts/purple-inner12'
    final = OUT/'artifacts/final-split'
    split.split(TEMPORAL/'03_runtime_pack', raw, ROOT/'animations/index/occurrences.csv', raw.exists())
    neutral.build(raw, purple, {'AM0504SB'}, purple.exists(), 'premultiply', None, 12)
    neutral.build(purple, final, {j[0] for j in JOBS}-{'AM0504SB'}, final.exists(), 'premultiply', None, 0)
    return final


def contexts(final):
    result = []
    for ref, area, method, radius in JOBS:
        old_pack, new_pack = CURRENT/area, final/area
        _, old = v.validate_v2_pack(old_pack)
        _, new = v.validate_v2_pack(new_pack)
        old = next(r for r in old if r['resref'] == ref)
        new = next(r for r in new if r['resref'] == ref)
        assert v.resource_binary_v2(old, 3) == v.resource_binary_v2(new, 3), ref + ': timing/geometry differs'
        x1 = v.load_json(SPATIAL/f'resources/{ref}/01_frames_x1/manifest.json')
        before = v.load_json(ORIGINAL/f'resources/{ref}/01_frames_x1/manifest.json')
        assert x1['source_sha256'] == before['source_sha256']
        assert x1['aligned_canvas_size'] == before['aligned_canvas_size']
        assert [(f['source_size'], f['centre'], f['canvas_offset']) for f in x1['frames']] == [
            (f['source_size'], f['centre'], f['canvas_offset']) for f in before['frames']]
        data = (ROOT/f'animations/ressources/{ref}/source.bam').read_bytes()
        if data[:4] == b'BAMC':
            data = zlib.decompress(data[12:])
        source = decode_bam(data)
        for frame in new['frames']:
            w, h = frame['physical_size_x4']
            rgba = np.frombuffer((new_pack/frame['asset']).read_bytes(), np.uint8).reshape(h, w, 4)
            assert not rgba[rgba[..., 3] == 0, :3].any()
            assert np.all(rgba[..., :3] <= rgba[..., 3, None])
        result.append(dict(ref=ref, area=area, method=method, radius=radius,
                           old_pack=old_pack, new_pack=new_pack, old=old, new=new,
                           x1=x1, source=source, cache={},
                           canvas=tuple(n*4 for n in x1['aligned_canvas_size']),
                           zoom=3 if ref == 'EYESRED1' else 1))
    return result


def panels(ctx, cycle_number, phase):
    cycle = ctx['old']['cycles'][cycle_number]
    sequence = cycle['timeline_frame_indices']
    native_sequence = cycle['native_frame_indices']
    count = len(sequence) if sequence else len(native_sequence)*2
    phase %= count
    native = native_sequence[phase//2]
    output = sequence[phase] if sequence else native
    frame_x1 = ctx['x1']['frames'][native]
    offset = [n*4 for n in frame_x1['canvas_offset']]
    idx, _, _, transparent = ctx['source'][0][native]
    rgb = ctx['source'][1][idx].copy()
    rgb[idx == transparent] = 0
    images = []
    for kind in ('native', 'old', 'new'):
        if kind == 'native':
            pixels = rgb.repeat(4, 0).repeat(4, 1)
        else:
            key = kind, output
            if key not in ctx['cache']:
                frame = ctx[kind]['frames'][output]
                w, h = frame['physical_size_x4']
                ctx['cache'][key] = np.frombuffer((ctx[kind+'_pack']/frame['asset']).read_bytes(),
                                                 np.uint8).reshape(h, w, 4)[..., :3]
            pixels = ctx['cache'][key]
        w, h = ctx['canvas']
        canvas = np.zeros((h, w, 3), np.uint16)
        x, y = offset
        fh, fw = pixels.shape[:2]
        canvas[y:y+fh, x:x+fw] = pixels
        image = Image.fromarray(np.minimum(canvas + np.array(BG), 255).astype(np.uint8))
        if ctx['zoom'] != 1:
            image = image.resize((w*ctx['zoom'], h*ctx['zoom']), Image.Resampling.NEAREST)
        images.append(image)
    return images


def board(items, master_phase=None, one_cycle=None):
    width = 1080
    heights = [max(110, c['canvas'][1]*c['zoom'])+54 for c in items]
    sheet = Image.new('RGB', (width, sum(heights)+70), BG)
    draw = ImageDraw.Draw(sheet)
    for col, title in enumerate(['NATIF', 'VERSION ACTUELLE', 'SEEDVR2 7B / LAB']):
        draw.text((col*360+18, 14), title, font=FONT, fill='white')
    draw.text((18, 45), 'Memes instants, centres et durees. Rendu additif sur fond neutre; hors jeu.', font=SMALL, fill='#bbbbbb')
    top = 70
    for ctx, height in zip(items, heights):
        cycle_number = one_cycle if one_cycle is not None else 0
        cycle = ctx['old']['cycles'][cycle_number]
        count = len(cycle['timeline_frame_indices']) or len(cycle['native_frame_indices'])*2
        selected = 24 if ctx['ref'] == 'BUBBLEA' else count//2
        phase = selected if master_phase is None else master_phase % count
        zoom = ' / zoom affichage x3' if ctx['zoom'] != 1 else ''
        draw.text((18, top+8), ctx['ref']+zoom, font=SMALL, fill='white')
        draw.text((378, top+8), ctx['method'], font=SMALL, fill='#cccccc')
        draw.text((738, top+8), f'Cycle {cycle_number} / phase {phase}', font=SMALL, fill='#cccccc')
        for col, image in enumerate(panels(ctx, cycle_number, phase)):
            sheet.paste(image, (col*360+(360-image.width)//2, top+39))
        top += height
        draw.line((15, top-1, width-15, top-1), fill='#555555')
    return sheet


def encoder(path, size):
    return subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
        '-pixel_format', 'rgb24', '-video_size', f'{size[0]}x{size[1]}', '-framerate', '30', '-i', '-',
        '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-c:v', 'libx264', '-preset', 'fast', '-crf', '12',
        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)], stdin=subprocess.PIPE)


def compare(items):
    folder = OUT/'comparisons'
    folder.mkdir(exist_ok=True)
    still = board(items)
    still.save(folder/'comparatif-natif-actuel-seedvr.png')
    movie = folder/'comparatif-natif-actuel-seedvr-30fps.mp4'
    process = encoder(movie, still.size)
    gif = []
    for phase in range(120):
        image = board(items, phase)
        process.stdin.write(image.tobytes())
        if phase % 3 == 0:
            gif.append(image.quantize(colors=192))
    process.stdin.close()
    assert process.wait() == 0
    gif[0].save(folder/'comparatif-anime.gif', save_all=True, append_images=gif[1:],
                duration=100, loop=0, optimize=False)
    cards = []
    videos = [(movie, 120)]
    for ctx in items:
        choices = []
        for cycle in ctx['old']['cycles']:
            number = cycle['cycle']
            count = len(cycle['timeline_frame_indices']) or len(cycle['native_frame_indices'])*2
            path = folder/f'{ctx["ref"]}-cycle{number}.mp4'
            first = board([ctx], 0, number)
            process = encoder(path, first.size)
            for phase in range(count):
                process.stdin.write(board([ctx], phase, number).tobytes())
            process.stdin.close()
            assert process.wait() == 0
            videos.append((path, count))
            choices.append(f'<option value="{path.name}">Cycle {number} ({count/30:.3f} s)</option>')
        first_path = f'{ctx["ref"]}-cycle0.mp4'
        cards.append(f'<article><h2>{ctx["ref"]}</h2><select onchange="const v=this.nextElementSibling;v.src=this.value;v.play()">'
                     + ''.join(choices)+f'</select><video src="{first_path}" controls autoplay muted loop playsinline></video></article>')
    html = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Lot2 — actuel / SeedVR</title>
<style>body{background:#222;color:#eee;font:17px system-ui;max-width:1280px;margin:24px auto;padding:0 16px}video,img{width:100%;display:block}article{border:1px solid #555;padding:16px;margin:24px 0}select{padding:8px;margin-bottom:12px}</style>
<h1>Lot2 — natif / version actuelle / SeedVR2 7B LAB</h1><p>Colonnes synchronisees. Versions actuelles installees; SeedVR non installe. Yeux et WTRBODY1: cadence native. Flammes et BUBBLEA: Apollo8 30 FPS. BUBBLEA: pauses exactes.</p>
<video src="comparatif-natif-actuel-seedvr-30fps.mp4" controls autoplay muted loop playsinline></video>'''
    (folder/'index.html').write_text(html + ''.join(cards)+'</html>', encoding='utf-8')
    for path, count in videos:
        data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
            'stream=nb_frames,r_frame_rate', '-show_entries', 'format=duration', '-of', 'json', str(path)]))
        assert data['streams'][0]['r_frame_rate'] == '30/1'
        assert int(data['streams'][0]['nb_frames']) == count
        assert abs(float(data['format']['duration']) - count/30) < .002
    return folder, videos


def main():
    game = get_path('bg2ee_game_root')
    installed = v.load_json(ROOT/'animations/batches/lot2-small-effects-20261011-v1/baseline.json')
    final = finish()
    items = contexts(final)
    folder, videos = compare(items)
    for area, entry in installed.items():
        actual = {p.name: sha(p) for p in (game/'iee-assets/areas'/area).iterdir() if p.is_file()}
        assert actual == entry['output_payload'], area + ': current installation changed'
    v.write_json(OUT/'manifest.json', dict(schema='bg2-upscale-animation-comparison-v1',
        status='completed', created_utc=v.utc_now(), resrefs=[j[0] for j in JOBS],
        user_request='Explicit SeedVR alternative for each lot2 asset, including tiny subjects',
        spatial_run=rel(SPATIAL), temporal_run=rel(TEMPORAL), final_split=rel(final),
        comparison=rel(folder), preview=rel(folder/'comparatif-natif-actuel-seedvr.png'),
        videos=[dict(path=rel(p), frames=n, sha256=sha(p)) for p, n in videos],
        geometry_and_timing_match=True, installed=False, current_installation_preserved=True,
        qa_status='pending-user-choice', release_status='not-selected'))
    print('COMPLETED', rel(folder), flush=True)


if __name__ == '__main__':
    main()
