"""AR1600 only, v2: interpolate native WTLAKE to 72 phases, then SeedVR x4 as one video.

v1 kept per-image SeedVR anchors whose detail varied 2.7x between frames; Apollo then
warped between them and the shader half-blended again, so the loop still pulsed at
2.5 Hz.  Native WTLAKE is a shimmer, not a coherent translation (DIS flow explains ~25 %
of the frame difference and flips by +-8 native px), so flow interpolators, Apollo
included, warp then jump.  v2 uses periodic band-limited (trigonometric) interpolation of
the six native frames: exact anchors, closed C-infinity loop, 72 phases = true 30 fps over
the native 2.4 s.  SeedVR 7B then upscales the wrapped sequence in one temporal chunk so
detail is consistent.  One 4096 page holds 72 tiles; the shader reads them at 30 Hz
without blending.  Produces assets, registry and review; install is separate.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import numpy as np
from PIL import Image, ImageDraw
from build_liquid_periodic_x4_trial import seam_metrics
from mos_decode import decode_pvrz_page
from run_seedvr_comfyui import ComfyClient
from water_wed import replace_overlay_resref, replace_overlay_timeline, validate_polygons
from workspace_paths import get_path, get_service

ROOT = Path(__file__).resolve().parents[2]
SPATIAL = ROOT / 'maps/water-batches/runs/liquid-families-x4-20260923-v1'
V1 = ROOT / 'maps/water-batches/runs/ar1600-water-30fps-20260923-v1'
ENGINE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
sys.path.insert(0, str(ENGINE / 'tools'))
from generate_water_route2_registry import load_registry, generate

PHASES, NATIVE, STEP = 72, 6, 12          # 72 phases, native anchor every 12
WRAP_HEAD, WRAP_TAIL = 16, 17             # 16 + 72 + 17 = 105 = 4n+1 frames
TILE, PAD, PAGE = 256, 4, 4096
STRIDE = TILE + 2 * PAD
COLUMNS = PAGE // STRIDE                  # 15
GROUPS = [('dry', 'lake', 'WTLAKE', 'QALAK0', 'QBLKV0'),
          ('rain', 'lake_rain', 'WTLAKER', 'QALAK0R', 'QBLKV0R')]
V1_INSTALLED = {'AR1600.WED': 'ACA0EAD43272893AE452FF3E0A615FD9D959EF7E46C586D8374F1BD284AA10C5',
                'QALAK0.TIS': '3DCEDEE67DD4C31B0AB1E1A2CF3DCBBF45C732D8F4FD9C96677B254DB50C4B83',
                'QLAK000.PVRZ': 'E85867C73FA63C6C7AF528445F00264660D675C751C4069164A774BD2CC02103',
                'QLAK0R00.PVRZ': 'DF5984C50B35522C0C2E0C4ED10D341FCDE547EF81A98B1FE08B77706F08CA34',
                'InfinityEngine-Enhancer.dll': 'B5ECAAC5F1A4F46D9CD91ECB770386BCB702ABC93581B451E6A07F7A1BBE8D57'}
SPATIAL_WED = '00140DDF284C592D2ACA8EDB06AA9D6565F838076245567A84EAAFF891E91F60'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def evidence(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def page_name(alias):
    return alias[0] + alias[2:] + '00'


def sharpness(rgb):
    g = rgb[:, :, :3].astype(np.float64).mean(2)
    return float(np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean())


def rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB'))


def prepare(output, game):
    output.mkdir(parents=True, exist_ok=False)
    override = game / 'override'
    for name, sha in V1_INSTALLED.items():
        target = game / name if name.endswith('.dll') else override / name
        assert digest(target) == sha, f'live state differs from v1 receipt: {name}'
    spatial_wed = SPATIAL / 'override-candidate-v3/AR1600.WED'
    assert digest(spatial_wed) == SPATIAL_WED
    groups = []
    for weather, group, ref, old, new in GROUPS:
        for name in (new + '.TIS', page_name(new) + '.PVRZ'):
            assert not (override / name).exists(), name
        folder = output / weather
        (folder / 'native').mkdir(parents=True)
        source = SPATIAL / 'overlays/groups' / group / 'source-native' / ref
        paths = [source / f'frame_{i:03d}.png' for i in range(NATIVE)]
        for i, path in enumerate(paths):
            with Image.open(path) as image:
                tile = np.array(image.convert('RGBA'))
            assert tile.shape == (64, 64, 4) and np.all(tile[:, :, 3] == 255)
            Image.fromarray(tile[:, :, :3]).save(folder / f'native/frame_{i:03d}.png')
        groups.append({'weather': weather, 'source_ref': ref, 'v1_alias': old, 'alias': new,
                       'native': [evidence(p) for p in paths]})
    save(output / 'plan.json', {'schema': 'bg2-ar1600-water-interpolation-trial-v2',
        'game_root': str(game), 'v1_installed': V1_INSTALLED, 'spatial_wed': evidence(spatial_wed),
        'groups': groups, 'cycle_seconds': 2.4, 'phases': PHASES, 'phase_fps': 30,
        'display_fps': 30, 'order': 'interpolate x1 native, then SeedVR x4 one temporal chunk',
        'interpolator': 'periodic band-limited (trigonometric), exact anchors',
        'rejected_interpolator': 'Apollo apo-8: anchors not reproduced, duplicates, jumps on shimmer',
        'seedvr': '7B INT8 convrot, color none, one 105-frame chunk',
        'procedural_strength': 0, 'qa': 'pending-user-ingame'})


def interpolate(output):
    for group in read(output / 'plan.json')['groups']:
        folder = output / group['weather']
        native = np.stack([rgb(folder / f'native/frame_{i:03d}.png').astype(np.float64) for i in range(NATIVE)])
        spectrum = np.fft.fft(native, axis=0)
        padded = np.zeros((PHASES,) + native.shape[1:], complex)
        for k in (1, 2):
            padded[k], padded[PHASES - k] = spectrum[k], spectrum[NATIVE - k]
        padded[0] = spectrum[0]
        padded[3] = padded[PHASES - 3] = spectrum[3] / 2   # split Nyquist: real, symmetric
        phases = np.real(np.fft.ifft(padded, axis=0)) * (PHASES / NATIVE)
        assert np.allclose(phases[::STEP], native, atol=1e-6)
        x1 = folder / 'x1'
        x1.mkdir()
        values = []
        for i in range(PHASES):
            tile = np.clip(np.rint(phases[i]), 0, 255).astype(np.uint8)
            if i % STEP == 0:
                assert np.array_equal(tile, native[i // STEP].astype(np.uint8))
            values.append(sharpness(tile))
            Image.fromarray(np.tile(tile, (3, 3, 1))).save(x1 / f'frame_{i:03d}.png')
        steps = [float(np.abs(phases[(i + 1) % PHASES] - phases[i]).mean()) for i in range(PHASES)]
        save(folder / 'interpolation.json', {'frames': PHASES, 'closed_loop': True,
             'anchor_every': STEP, 'anchors_exact': True, 'x1_sharpness': values, 'x1_step_mae': steps})
        print(f"{group['weather']}: 72 phases, x1 sharpness {min(values):.2f}-{max(values):.2f}, "
              f"step {min(steps):.2f}-{max(steps):.2f}", flush=True)


def seedvr_prompt(directory, prefix):
    return {
        '1': {'class_type': 'VHS_LoadImagesPath', 'inputs': {'directory': str(directory),
              'image_load_cap': 0, 'skip_first_images': 0, 'select_every_nth': 1}},
        '2': {'class_type': 'ResizeImageMaskNode', 'inputs': {'resize_type': 'scale by multiplier',
              'resize_type.multiplier': 4, 'scale_method': 'lanczos', 'input': ['1', 0]}},
        '3': {'class_type': 'SeedVR2Preprocess', 'inputs': {'resized_images': ['2', 0]}},
        '4': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'seedvr2_ema_vae_fp16.safetensors'}},
        '5': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'seedvr2_7b_int8_convrot.safetensors',
              'weight_dtype': 'default'}},
        '6': {'class_type': 'VAEEncodeTiled', 'inputs': {'tile_size': 512, 'overlap': 128,
              'temporal_size': 4096, 'temporal_overlap': 8, 'pixels': ['3', 0], 'vae': ['4', 0]}},
        '7': {'class_type': 'SeedVR2Conditioning', 'inputs': {'model': ['5', 0], 'vae_conditioning': ['6', 0]}},
        '8': {'class_type': 'KSampler', 'inputs': {'seed': 959948902156062, 'steps': 1, 'cfg': 1,
              'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1, 'model': ['5', 0],
              'positive': ['7', 0], 'negative': ['7', 1], 'latent_image': ['6', 0]}},
        '9': {'class_type': 'VAEDecodeTiled', 'inputs': {'tile_size': 512, 'overlap': 128,
              'temporal_size': 4096, 'temporal_overlap': 8, 'samples': ['8', 0], 'vae': ['4', 0]}},
        '10': {'class_type': 'SeedVR2PostProcessing', 'inputs': {'color_correction_method': 'none',
               'images': ['9', 0], 'original_resized_images': ['2', 0]}},
        '11': {'class_type': 'SaveImage', 'inputs': {'filename_prefix': prefix, 'images': ['10', 0]}},
    }


def split_detail(tile, sigma=3.0):
    fy = np.fft.fftfreq(tile.shape[0])[:, None]
    fx = np.fft.fftfreq(tile.shape[1])[None, :]
    gauss = np.exp(-2 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))[..., None]
    low = np.real(np.fft.ifft2(np.fft.fft2(tile, axes=(0, 1)) * gauss, axes=(0, 1)))
    return low, tile - low


def variance_preserving_mix(a, b, w):
    """Linear mix of two renditions of one phase without the mid-fade detail loss."""
    low, detail = split_detail(w * a + (1 - w) * b)
    target = w * split_detail(a)[1].std(axis=(0, 1)) + (1 - w) * split_detail(b)[1].std(axis=(0, 1))
    gain = np.clip(target / np.maximum(detail.std(axis=(0, 1)), 1e-6), 1.0, 1.6)
    return low + detail * gain


def upscale(output):
    client = ComfyClient(get_service('comfyui_url'), 2.0, 3600.0)
    client.preflight()
    for group in read(output / 'plan.json')['groups']:
        folder = output / group['weather']
        wrapped = folder / 'seedvr-in'
        wrapped.mkdir(exist_ok=False)
        order = ([PHASES - WRAP_HEAD + i for i in range(WRAP_HEAD)] + list(range(PHASES)) +
                 list(range(WRAP_TAIL)))
        for k, i in enumerate(order):
            shutil.copy2(folder / f'x1/frame_{i:03d}.png', wrapped / f'frame_{k:03d}.png')
        prompt = seedvr_prompt(wrapped, f"bg2_water/{output.name}-{group['weather']}")
        save(folder / 'seedvr-prompt.json', prompt)
        prompt_id = client.queue(prompt)
        print(f"{group['weather']}: SeedVR prompt {prompt_id} ({len(order)} frames)", flush=True)
        history = client.wait_history(prompt_id)
        images = history['outputs']['11']['images']
        if len(images) != len(order):
            raise ValueError(f'SeedVR frame count: {len(images)}')
        raw = folder / 'seedvr-out'
        for k, info in enumerate(images):
            client.download(info, raw / f'frame_{k:03d}.png')
        # Wrapped output k holds phase order[k].  Phases 0..7 exist twice: after 71 (k=80+)
        # and at the start (k=8+).  Crossfade from the continuation to the start copy so
        # the seam 71 -> 0 and the step 7 -> 8 both stay inside one temporal rendition.
        frames = folder / 'frames'
        frames.mkdir()
        crop = lambda k: rgb(raw / f'frame_{k:03d}.png')[256:512, 256:512].astype(np.float64)
        for phase in range(PHASES):
            tile = crop(WRAP_HEAD + phase)
            if phase < WRAP_HEAD:
                w = (phase + 0.5) / WRAP_HEAD
                tile = variance_preserving_mix(tile, crop(WRAP_HEAD + PHASES + phase), w)
            out = np.dstack([np.clip(np.rint(tile), 0, 255).astype(np.uint8), np.full((TILE, TILE), 255, np.uint8)])
            Image.fromarray(out, 'RGBA').save(frames / f'frame_{phase:03d}.png')
        save(folder / 'seedvr.json', {'prompt_id': prompt_id, 'wrapped_order': order,
             'crossfade_phases': list(range(WRAP_HEAD)), 'crop': [256, 256, 512, 512]})


def write_pvrz(canvas, destination):
    buffer = io.BytesIO()
    canvas.save(buffer, format='DDS', pixel_format='DXT5')
    dds = buffer.getvalue()
    assert dds[84:88] == b'DXT5' and len(dds) == 128 + PAGE * PAGE, 'Pillow cannot encode BC3'
    header = struct.pack('<13I', 0x03525650, 0, 11, 0, 0, 0, PAGE, PAGE, 1, 1, 1, 1, 0)
    pvr = header + dds[128:]
    destination.write_bytes(struct.pack('<I', len(pvr)) + zlib.compress(pvr, 9))


def export_tiles(frames, alias, out):
    canvas = np.zeros((PAGE, PAGE, 4), np.uint8)
    entries = []
    for i, frame in enumerate(frames):
        row, col = divmod(i, COLUMNS)
        x, y = col * STRIDE + PAD, row * STRIDE + PAD
        # Periodic margin: bilinear taps past the tile edge read the opposite edge.
        canvas[y-PAD:y+TILE+PAD, x-PAD:x+TILE+PAD] = np.pad(frame, ((PAD, PAD), (PAD, PAD), (0, 0)), mode='wrap')
        entries.append((0, x, y))
    page = out / (page_name(alias) + '.PVRZ')
    write_pvrz(Image.fromarray(canvas, 'RGBA'), page)
    tis = out / (alias + '.TIS')
    tis.write_bytes(b'TIS V1  ' + struct.pack('<4I', len(frames), 12, 24, TILE) +
                    b''.join(struct.pack('<3I', *e) for e in entries))
    return tis, page


def decode_tiles(tis, folder):
    data = tis.read_bytes()
    count, size, offset, dimension = struct.unpack_from('<4I', data, 8)
    assert size == 12 and dimension == TILE
    page = decode_pvrz_page((folder / (tis.stem[0] + tis.stem[2:] + '00.PVRZ')).read_bytes())
    assert page.size == (PAGE, PAGE)
    out = []
    for i in range(count):
        p, x, y = struct.unpack_from('<3I', data, offset + i * 12)
        assert p == 0
        out.append(np.asarray(page.crop((x, y, x + TILE, y + TILE))).copy())
    return out


def build(output):
    plan = read(output / 'plan.json')
    game = Path(plan['game_root'])
    candidate = output / 'candidate'
    candidate.mkdir(exist_ok=False)
    base_wed = (SPATIAL / 'override-candidate-v3/AR1600.WED').read_bytes()
    dry_alias = plan['groups'][0]['alias']
    changed = replace_overlay_resref(replace_overlay_timeline(base_wed, 1, PHASES, 1), 1, dry_alias)
    assert validate_polygons(base_wed) == validate_polygons(changed)
    (candidate / 'AR1600.WED').write_bytes(changed)
    headers = struct.unpack_from('<I', changed, 16)[0]
    slots = [changed[headers+i*24+4:headers+i*24+12].split(b'\0')[0].decode('ascii')
             for i in range(struct.unpack_from('<I', changed, 8)[0])]
    width, height = struct.unpack_from('<HH', changed, headers)
    tilemap = struct.unpack_from('<I', changed, headers + 16)[0]
    coverage = sum(bool(changed[tilemap+i*10+6] & 2) for i in range(width*height))
    base = game / 'override/AR1600.TIS'
    base_count = struct.unpack_from('<I', base.read_bytes(), 8)[0]
    parent = ENGINE / 'assets/water-route2/registry-v2.json'
    _, resolved = load_registry(parent)
    entries = copy.deepcopy(resolved['entries'])
    reports = []
    for group in plan['groups']:
        folder = output / group['weather']
        frames = [np.asarray(Image.open(folder / f'frames/frame_{i:03d}.png').convert('RGBA')) for i in range(PHASES)]
        tis, page = export_tiles(frames, group['alias'], candidate)
        decoded = decode_tiles(tis, candidate)
        assert len(decoded) == PHASES and all(np.all(f[:, :, 3] == 255) for f in decoded)
        sharp = [sharpness(f) for f in decoded]
        steps = [float(np.abs(decoded[(i+1) % PHASES][:, :, :3].astype(float) - decoded[i][:, :, :3]).mean())
                 for i in range(PHASES)]
        pairs = [{'a': 'water', 'b': 'water', 'axis': axis} for axis in ('x', 'y')]
        reports.append({'weather': group['weather'], 'alias': group['alias'],
                        'files': [evidence(tis), evidence(page)],
                        'post_bc3_sharpness': sharp, 'post_bc3_step_mae': steps,
                        'sharpness_ratio_max_min': max(sharp) / min(sharp),
                        'step_ratio_max_median': max(steps) / float(np.median(steps)),
                        'seams': [seam_metrics({'water': f}, pairs) for f in decoded]})
        entries.append({'id': 'ar1600-temporal-only-' + group['weather'] + '-20260923-v2',
            'state': 'candidate-installable-pending-qa', 'qa': {'status': 'pending-ingame'},
            'wed': {'resref': 'AR1600', 'sha256': digest(candidate / 'AR1600.WED'),
                    'grid': {'width': width, 'height': height}, 'overlay_slots': slots},
            'base_tis': {'resref': 'AR1600', 'tile_count': base_count, 'bytes': base.stat().st_size,
                         'sha256': digest(base), 'pages': []},
            'overlay': {'slot': 1, 'tis_resref': group['alias'], 'tis_sha256': digest(tis),
                        'tis_bytes': tis.stat().st_size, 'tile_count': PHASES, 'tile_dimension': TILE,
                        'pages': [{'resref': page.stem, 'width': PAGE, 'height': PAGE,
                                   'bytes': page.stat().st_size, 'sha256': digest(page)}]},
            'approved_strength': 0, 'material_id': 1, 'overlay_coverage_cells': coverage,
            'allow_stock_wed_when_override_absent': False,
            'temporal_overlay': {'mode': 'atlas-linear', 'frame_count': PHASES, 'source_fps': 30,
                'target_fps': 30, 'atlas_columns': COLUMNS, 'atlas_stride_pixels': STRIDE,
                'atlas_padding_pixels': PAD}})
    registry = {'schema': 'bg2-water-route2-registry-v3', 'version': 3,
                'parent': {'path': parent.relative_to(ROOT).as_posix(), 'sha256': digest(parent)},
                'entries': entries}
    save(output / 'registry-v3.json', registry)
    generate(output / 'registry-v3.json')
    save(candidate / 'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1',
         'status': 'completed', 'area': 'AR1600', 'qa': 'pending-user-ingame',
         'files': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                   for p in sorted(candidate.iterdir()) if p.name != 'manifest.json'}})
    save(output / 'build.json', {'status': 'candidate-ready', 'reports': reports,
         'geometry': validate_polygons(changed), 'coverage': coverage, 'wed_speed': 1,
         'wed_fallback_seconds': PHASES / 15, 'producer': evidence(Path(__file__))})
    for r in reports:
        print(f"{r['weather']}: sharpness {min(r['post_bc3_sharpness']):.2f}-{max(r['post_bc3_sharpness']):.2f}"
              f" step {min(r['post_bc3_step_mae']):.2f}-{max(r['post_bc3_step_mae']):.2f}", flush=True)


def review(output):
    ffmpeg = Path(shutil.which('ffmpeg') or get_path('topaz_video_ffmpeg'))
    for group in read(output / 'plan.json')['groups']:
        folder = output / group['weather']
        new = decode_tiles(output / 'candidate' / (group['alias'] + '.TIS'), output / 'candidate')
        v1 =[np.asarray(Image.open(V1 / group['weather'] / f'frames/frame_{i:03d}.png').convert('RGB')) for i in range(36)]
        review_dir = folder / 'review'
        review_dir.mkdir()
        for i in range(PHASES):
            phase, half = divmod(i, 2)
            left = Image.blend(Image.fromarray(v1[phase]), Image.fromarray(v1[(phase+1) % 36]), half / 2)
            right = Image.fromarray(new[i][:, :, :3])
            canvas = Image.new('RGB', (1024, 536), (20, 20, 20))
            for k, tile in enumerate((left, right)):
                for x in range(2):
                    for y in range(2): canvas.paste(tile, (k*512+x*256, 24+y*256))
            ImageDraw.Draw(canvas).text((8, 5), 'v1 installed (36 + shader half-steps)                     v2 candidate (72 phases, video SeedVR)', fill='white')
            canvas.save(review_dir / f'frame_{i:03d}.png')
        subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-stream_loop', '3',
                        '-framerate', '30', '-i', str(review_dir / 'frame_%03d.png'), '-c:v', 'libx264',
                        '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        str(folder / 'comparison-v1-v2-30fps.mp4')], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=['prepare', 'interpolate', 'upscale', 'build', 'review'], required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'maps')
    stage = args.stage
    if stage == 'prepare': prepare(output, get_path('bg2ee_game_root'))
    elif stage == 'interpolate': interpolate(output)
    elif stage == 'upscale': upscale(output)
    elif stage == 'build': build(output)
    else: review(output)
