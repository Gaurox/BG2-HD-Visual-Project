"""True 30 fps WED liquid overlays for one map, any family (recipe validated on AR1600 v2).

Input: groups already prepared by ``build_liquid_periodic_x4_trial.py`` (x1 periodic
3x3 contexts, native alpha, WED playback, adjacencies) and their selected spatial build
(method seedvr/bilinear, edge collar decision).  One run = one WED, dry groups plus
their rain twins.

Recipe (AR1600 v2, validated ingame 2026-09-23):
1. Periodic band-limited (trigonometric) interpolation of the native keyframes, in
   lookup order, on the x1 context: exact anchors, closed smooth loop.  No flow
   interpolator: native liquids shimmer, Apollo warps then jumps.
2. x4: ``seedvr`` = SeedVR 7B on the whole wrapped sequence as one temporal chunk
   (consistent detail), loop seam = variance-preserving crossfade of the two renditions;
   ``bilinear`` = periodic bilinear x4 per phase.  Same edge collar as the spatial build.
3. One 4096 BC3 page per resource, WED slot -> isolated alias, sequential lookup of the
   phases, speed 1; registry timeline source 30 = target 30 (no shader blend).
Produces a candidate and a registry; DLL build and installation stay separate.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import numpy as np
from PIL import Image
from build_liquid_periodic_x4_trial import compatible_edges, seam_metrics, split_context
from mos_decode import decode_pvrz_page
from run_seedvr_comfyui import ComfyClient
from water_wed import replace_overlay_resref, replace_overlay_timeline, validate_polygons
from workspace_paths import get_path, get_service

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
sys.path.insert(0, str(ENGINE / 'tools'))
from generate_water_route2_registry import load_registry, generate

TILE, PAD, PAGE = 256, 4, 4096
STRIDE = TILE + 2 * PAD
COLUMNS = PAGE // STRIDE                   # 15 -> 225 phases per page
DISPLAY_FPS, WED_HZ = 30, 15
LOOP_CROSSFADE = 16
CURRENT_REGISTRY = ROOT / 'pipeline/water/route2-registry-current.json'
SEEDVR_SEED = 959948902156062


# --- pure recipe ---------------------------------------------------------------

def phase_count(keyframes: int, cycle_seconds: float) -> int:
    """Phases at 30 fps, rounded to a multiple of the keyframes so anchors stay exact."""
    per_key = max(1, round(cycle_seconds * DISPLAY_FPS / keyframes))
    phases = keyframes * per_key
    if phases > COLUMNS * COLUMNS:
        raise ValueError(f'{phases} phases exceed one {PAGE} page')
    return phases


def native_cycle(playback: list[dict]) -> float | None:
    """WED loop length when every slot of the group agrees; None when ambiguous."""
    values = {(len(p['lookup']), p['speed_divisor']) for p in playback}
    if len(values) != 1:
        return None
    count, speed = values.pop()
    return count * speed / WED_HZ if speed > 0 else None


def trig_interpolate(keys: np.ndarray, phases: int) -> np.ndarray:
    """Periodic band-limited interpolation along axis 0; exact at every phases/N step."""
    n = keys.shape[0]
    if phases % n:
        raise ValueError('phases must be a multiple of the keyframes')
    spectrum = np.fft.fft(keys.astype(np.float64), axis=0)
    padded = np.zeros((phases,) + keys.shape[1:], complex)
    half = n // 2
    for k in range(-((n - 1) // 2), (n - 1) // 2 + 1):
        padded[k % phases] = spectrum[k % n]
    if n % 2 == 0:                         # split Nyquist: stays real and symmetric
        padded[half] += spectrum[half] / 2
        padded[phases - half] += spectrum[half] / 2
    return np.real(np.fft.ifft(padded, axis=0)) * (phases / n)


def wrap_order(phases: int, head: int = LOOP_CROSSFADE) -> list[int]:
    """Phase order for one SeedVR chunk: tail + loop + head, total 4n+1 frames."""
    head = min(head, phases)
    tail = head + 1
    while (head + phases + tail - 1) % 4:
        tail += 1
    return [phases - head + i for i in range(head)] + list(range(phases)) + [i % phases for i in range(tail)]


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


def sharpness(image):
    g = image[:, :, :3].astype(np.float64).mean(2)
    return float(np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean())


def page_name(alias):
    return alias[0] + alias[2:] + '00'


def write_pvrz(canvas, destination):
    buffer = io.BytesIO()
    canvas.save(buffer, format='DDS', pixel_format='DXT5')
    dds = buffer.getvalue()
    if dds[84:88] != b'DXT5' or len(dds) != 128 + PAGE * PAGE:
        raise RuntimeError(f'Pillow {Image.__version__} cannot encode BC3; use Pillow 12+')
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


# --- run plumbing ----------------------------------------------------------------

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def evidence(path):
    path = Path(path)
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def rgb(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGB'))


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def prepare(plan_path, output, game):
    """Plan: {spatial_run, wed, base_registry?, selection?, source_wed?, groups: [{id, aliases,
    material_id, cycle_seconds?}]}.  Rain groups name an earlier dry group in ``rain_of``.
    Without ``base_registry`` the registry compiled into the installed DLL is used
    (``route2-registry-current.json``); its DLL hash must match the live DLL."""
    plan = read(plan_path)
    current = read(CURRENT_REGISTRY)
    live_dll = digest(game / 'InfinityEngine-Enhancer.dll')
    if live_dll != current['dll_sha256']:
        raise ValueError(f'installed DLL {live_dll} is not the one recorded in {CURRENT_REGISTRY.name}; '
                         'find which registry it carries before building on it')
    plan.setdefault('base_registry', current['registry']['path'])
    spatial = resolve(plan['spatial_run'])
    selection_path = resolve(plan.get('selection', spatial / 'overlays-selected-v3/selection.json'))
    source_wed = resolve(plan.get('source_wed', spatial / 'override-candidate-v3' / f"{plan['wed']}.WED"))
    selection = {g['id']: g for g in read(selection_path)['groups']}
    if not source_wed.is_file() or not (game / 'override' / f"{plan['wed']}.TIS").is_file():
        raise ValueError('source WED and installed x4 base TIS are both required')
    pages = [page_name(a) for e in plan['groups'] for a in e['aliases'].values()]
    if len(pages) != len(set(pages)):
        raise ValueError(f'page names collide inside the plan: {pages}')
    output.mkdir(parents=True, exist_ok=False)
    override = game / 'override'
    records, cycles = [], {}
    for entry in plan['groups']:
        gid = entry['id']
        prepared = read(spatial / 'overlays/groups' / gid / 'prepare.json')
        group = prepared['contract']['group']
        selected = read(resolve(selection[gid]['build_manifest']))
        if group['wed'] != plan['wed']:
            raise ValueError(f'{gid}: one run = one WED')
        aliases = entry['aliases']
        for ref in group['resrefs']:
            alias = aliases[ref]
            if len(alias) > 8 or len(page_name(alias)) > 8:
                raise ValueError(f'{alias}: resref or page name over 8 bytes')
            for name in (alias + '.TIS', page_name(alias) + '.PVRZ'):
                if (override / name).exists():
                    raise ValueError(f'{name} already installed: choose a new alias')
        playback = [p for w in prepared['topology']['weds'] for p in w['playback']]
        lookups = {tuple(p['lookup']) for p in playback}
        if len(lookups) != 1:
            raise ValueError(f'{gid}: members use different lookups; not supported')
        lookup = list(lookups.pop())
        dry = entry.get('rain_of')
        if dry:
            if dry not in cycles:
                raise ValueError(f'{gid}: list its dry group {dry} first')
            cycle = cycles[dry]
            dry_aliases = next(e['aliases'] for e in plan['groups'] if e['id'] == dry)
            dry_group = read(spatial / 'overlays/groups' / dry / 'prepare.json')['contract']['group']
            dry_by_source = dict(zip(dry_group['source_wed_resrefs'], dry_group['resrefs']))
            for ref, src in zip(group['resrefs'], group['source_wed_resrefs']):
                if aliases[ref] != dry_aliases[dry_by_source[src]] + 'R':
                    raise ValueError(f'{ref}: rain alias must be the dry alias + R (native routing)')
        else:
            cycle = entry.get('cycle_seconds') or native_cycle(playback)
            if not cycle:
                raise ValueError(f'{gid}: WED speeds disagree {[p["speed_divisor"] for p in playback]}; '
                                 'set cycle_seconds explicitly and validate it ingame')
        cycles[gid] = cycle
        phases = phase_count(len(lookup), cycle)
        folder = output / gid
        (folder / 'keys').mkdir(parents=True)
        alphas = []
        for k, index in enumerate(lookup):
            shutil.copy2(spatial / 'overlays/groups' / gid / f'inputs/rgb/frame_{index:03d}.png', folder / f'keys/frame_{k:03d}.png')
            alphas.append(np.asarray(Image.open(spatial / 'overlays/groups' / gid / f'inputs/alpha/frame_{index:03d}.png')))
        if not all(np.array_equal(alphas[0], a) for a in alphas):
            raise ValueError(f'{gid}: alpha changes between keyframes; not supported')
        Image.fromarray(alphas[0]).save(folder / 'alpha.png')
        method = selected['group']['method']
        collar = any(m.get('correction_applied') for m in selected['metrics'])
        records.append({'id': gid, 'rain_of': dry, 'group': group, 'aliases': aliases,
                        'material_id': entry.get('material_id', 1), 'lookup': lookup,
                        'playback': playback, 'cycle_seconds': cycle, 'phases': phases,
                        'method': method, 'edge_collar': collar,
                        'seam_width_x4': int(group.get('seam_width_x4', 8)),
                        'adjacencies': prepared['topology']['adjacencies'],
                        'selected_build': evidence(resolve(selection[gid]['build_manifest']))})
    save(output / 'plan.json', {'schema': 'bg2-liquid-temporal-30fps-v1', 'source_plan': evidence(plan_path),
         'game_root': str(game), 'wed': plan['wed'], 'spatial_run': str(spatial),
         'selection': evidence(selection_path), 'source_wed': evidence(source_wed),
         'base_registry': str(resolve(plan['base_registry'])), 'groups': records,
         'display_fps': DISPLAY_FPS, 'qa': 'pending-user-ingame'})
    for r in records:
        print(f"{r['id']}: {len(r['lookup'])} keys -> {r['phases']} phases, {r['cycle_seconds']:.3f} s, {r['method']}", flush=True)


def interpolate(output):
    for group in read(output / 'plan.json')['groups']:
        folder = output / group['id']
        keys = np.stack([rgb(folder / f'keys/frame_{k:03d}.png') for k in range(len(group['lookup']))])
        phases = trig_interpolate(keys, group['phases'])
        step = group['phases'] // len(group['lookup'])
        assert np.allclose(phases[::step], keys, atol=1e-6)
        x1 = folder / 'x1'
        x1.mkdir()
        for i, frame in enumerate(phases):
            Image.fromarray(np.clip(np.rint(frame), 0, 255).astype(np.uint8)).save(x1 / f'frame_{i:03d}.png')
        steps = [float(np.abs(phases[(i + 1) % len(phases)] - phases[i]).mean()) for i in range(len(phases))]
        save(folder / 'interpolation.json', {'phases': group['phases'], 'anchor_every': step,
             'anchors_exact': True, 'closed_loop': True, 'x1_step_mae': steps})
        print(f"{group['id']}: x1 step {min(steps):.2f}-{max(steps):.2f}", flush=True)


def seedvr_prompt(directory, prefix, frames_per_chunk=None, overlap=0):
    """Default: the whole wrapped loop in one temporal chunk (validated).  A manual chunk
    size is a VRAM fallback; chunk borders may reintroduce detail steps."""
    prompt = {
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
        '12': {'class_type': 'SeedVR2TemporalChunk', 'inputs': {'latent': ['6', 0], 'temporal_overlap': overlap,
               'chunking_mode': 'manual', 'chunking_mode.frames_per_chunk': frames_per_chunk}},
        '7': {'class_type': 'SeedVR2Conditioning', 'inputs': {'model': ['5', 0], 'vae_conditioning': ['12', 0]}},
        '8': {'class_type': 'KSampler', 'inputs': {'seed': SEEDVR_SEED, 'steps': 1, 'cfg': 1,
              'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1, 'model': ['5', 0],
              'positive': ['7', 0], 'negative': ['7', 1], 'latent_image': ['12', 0]}},
        '13': {'class_type': 'SeedVR2TemporalMerge', 'inputs': {'latents': ['8', 0], 'temporal_overlap': ['12', 1]}},
        '9': {'class_type': 'VAEDecodeTiled', 'inputs': {'tile_size': 512, 'overlap': 128,
              'temporal_size': 4096, 'temporal_overlap': 8, 'samples': ['13', 0], 'vae': ['4', 0]}},
        '10': {'class_type': 'SeedVR2PostProcessing', 'inputs': {'color_correction_method': 'none',
               'images': ['9', 0], 'original_resized_images': ['2', 0]}},
        '11': {'class_type': 'SaveImage', 'inputs': {'filename_prefix': prefix, 'images': ['10', 0]}},
    }
    if not frames_per_chunk:
        del prompt['12'], prompt['13']
        prompt['7']['inputs']['vae_conditioning'] = ['6', 0]
        prompt['8']['inputs']['latent_image'] = ['6', 0]
        prompt['9']['inputs']['samples'] = ['8', 0]
    return prompt


def upscale(output, frames_per_chunk=None, overlap=0):
    plan = read(output / 'plan.json')
    client = None
    for group in plan['groups']:
        folder = output / group['id']
        phases, g = group['phases'], group['group']
        side = 64 * len(g['layout']) * 4
        center = (slice(side, 2 * side), slice(side, 2 * side))
        alpha = Image.open(folder / 'alpha.png')
        alpha_x4 = np.asarray(alpha.resize((alpha.width * 4, alpha.height * 4), Image.Resampling.NEAREST))
        contexts = {}
        if group['method'] == 'seedvr':
            client = client or ComfyClient(get_service('comfyui_url'), 2.0, 7200.0)
            client.preflight()
            order = wrap_order(phases)
            wrapped = folder / 'seedvr-in'
            wrapped.mkdir()
            for k, i in enumerate(order):
                shutil.copy2(folder / f'x1/frame_{i:03d}.png', wrapped / f'frame_{k:03d}.png')
            prompt = seedvr_prompt(wrapped, f"bg2_water/{output.name}-{group['id']}", frames_per_chunk, overlap)
            save(folder / 'seedvr-prompt.json', prompt)
            prompt_id = client.queue(prompt)
            print(f"{group['id']}: SeedVR {prompt_id} ({len(order)} frames)", flush=True)
            images = client.wait_history(prompt_id)['outputs']['11']['images']
            if len(images) != len(order):
                raise ValueError(f'SeedVR frame count: {len(images)}')
            raw = folder / 'seedvr-out'
            for k, info in enumerate(images):
                client.download(info, raw / f'frame_{k:03d}.png')
            head = order.index(0)
            crop = lambda k: rgb(raw / f'frame_{k:03d}.png')[center].astype(np.float64)
            for phase in range(phases):
                tile = crop(head + phase)
                if phase < head:
                    w = (phase + 0.5) / head
                    tile = variance_preserving_mix(tile, crop(head + phases + phase), w)
                contexts[phase] = tile
            save(folder / 'seedvr.json', {'prompt_id': prompt_id, 'wrapped_order': order,
                 'crossfade_phases': head, 'frames_per_chunk': frames_per_chunk, 'overlap': overlap})
        elif group['method'] == 'bilinear':
            for phase in range(phases):
                with Image.open(folder / f'x1/frame_{phase:03d}.png') as image:
                    up = image.convert('RGB').resize((image.width * 4, image.height * 4), Image.Resampling.BILINEAR)
                contexts[phase] = np.asarray(up)[center].astype(np.float64)
        else:
            raise ValueError(f"unsupported spatial method {group['method']}")
        tiles = folder / 'tiles'
        for phase in range(phases):
            full = np.zeros((side * 3, side * 3, 4), np.uint8)
            full[center[0], center[1], :3] = np.clip(np.rint(contexts[phase]), 0, 255).astype(np.uint8)
            full[:, :, 3] = alpha_x4
            frames = split_context(Image.fromarray(full, 'RGBA'), g)
            if group['edge_collar']:
                frames = compatible_edges(frames, group['adjacencies'], group['seam_width_x4'])
            for ref, array in frames.items():
                (tiles / ref).mkdir(parents=True, exist_ok=True)
                Image.fromarray(array, 'RGBA').save(tiles / ref / f'frame_{phase:03d}.png')


def build(output):
    plan = read(output / 'plan.json')
    game = Path(plan['game_root'])
    candidate = output / 'candidate'
    candidate.mkdir(exist_ok=False)
    wed_name = plan['wed']
    source_wed = Path(plan['source_wed']['path'])
    if digest(source_wed) != plan['source_wed']['sha256']:
        raise ValueError('source WED changed since prepare')
    wed = source_wed.read_bytes()
    base_geometry = validate_polygons(wed)
    headers = struct.unpack_from('<I', wed, 16)[0]
    layers = struct.unpack_from('<I', wed, 8)[0]
    reports, identities = [], []
    for group in plan['groups']:
        folder = output / group['id']
        g = group['group']
        for ref, source_ref in zip(g['resrefs'], g['source_wed_resrefs']):
            alias = group['aliases'][ref]
            frames = [np.asarray(Image.open(folder / f'tiles/{ref}/frame_{i:03d}.png').convert('RGBA'))
                      for i in range(group['phases'])]
            tis, page = export_tiles(frames, alias, candidate)
            decoded = decode_tiles(tis, candidate)
            if not all(np.array_equal(d[:, :, 3], f[:, :, 3]) for d, f in zip(decoded, frames)):
                raise ValueError('BC3 changed the native binary alpha')
            sharp = [sharpness(f) for f in decoded]
            steps = [float(np.abs(decoded[(i+1) % len(decoded)][:, :, :3].astype(float) - decoded[i][:, :, :3]).mean())
                     for i in range(len(decoded))]
            reports.append({'group': group['id'], 'resref': ref, 'alias': alias,
                            'files': [evidence(tis), evidence(page)],
                            'sharpness_ratio_max_min': max(sharp) / min(sharp),
                            'step_ratio_max_median': max(steps) / float(np.median(steps)),
                            'post_bc3_sharpness': sharp, 'post_bc3_step_mae': steps})
            slot = [p['slot'] for p in group['playback'] if p['wed_resref'] == source_ref]
            if len(slot) != 1:
                raise ValueError(f'{source_ref}: slot not found')
            slot = slot[0]
            if not group['rain_of']:       # rain TIS is routed natively from dry alias + R
                wed = replace_overlay_resref(replace_overlay_timeline(
                    wed, slot, group['phases'], 1, require_sequential=False), slot, alias)
            identities.append((group, ref, alias, slot, tis, page))
    if validate_polygons(wed) != base_geometry:
        raise ValueError('WED geometry changed')
    (candidate / f'{wed_name}.WED').write_bytes(wed)
    headers = struct.unpack_from('<I', wed, 16)[0]
    slots = [wed[headers+i*24+4:headers+i*24+12].split(b'\0')[0].decode('ascii') for i in range(layers)]
    width, height = struct.unpack_from('<HH', wed, headers)
    tilemap = struct.unpack_from('<I', wed, headers + 16)[0]
    base = game / 'override' / f'{wed_name}.TIS'
    base_count = struct.unpack_from('<I', base.read_bytes(), 8)[0]
    base_registry = Path(plan['base_registry'])
    child, resolved = load_registry(base_registry)
    entries = [e for e in copy.deepcopy(resolved['entries']) if e['wed']['resref'] != wed_name]
    for group, ref, alias, slot, tis, page in identities:
        coverage = sum(bool(wed[tilemap+i*10+6] & (1 << slot)) for i in range(width*height))
        entries.append({'id': f"{wed_name.lower()}-temporal-{alias.lower()}-{output.name}",
            'state': 'candidate-installable-pending-qa', 'qa': {'status': 'pending-ingame'},
            'wed': {'resref': wed_name, 'sha256': digest(candidate / f'{wed_name}.WED'),
                    'grid': {'width': width, 'height': height}, 'overlay_slots': slots},
            'base_tis': {'resref': wed_name, 'tile_count': base_count, 'bytes': base.stat().st_size,
                         'sha256': digest(base), 'pages': []},
            'overlay': {'slot': slot, 'tis_resref': alias, 'tis_sha256': digest(tis),
                        'tis_bytes': tis.stat().st_size, 'tile_count': group['phases'], 'tile_dimension': TILE,
                        'pages': [{'resref': page.stem, 'width': PAGE, 'height': PAGE,
                                   'bytes': page.stat().st_size, 'sha256': digest(page)}]},
            'approved_strength': 0, 'material_id': group['material_id'], 'overlay_coverage_cells': coverage,
            'allow_stock_wed_when_override_absent': False,
            'temporal_overlay': {'mode': 'atlas-linear', 'frame_count': group['phases'],
                'source_fps': DISPLAY_FPS, 'target_fps': DISPLAY_FPS, 'atlas_columns': COLUMNS,
                'atlas_stride_pixels': STRIDE, 'atlas_padding_pixels': PAD}})
    registry = {'schema': 'bg2-water-route2-registry-v3', 'version': 3,
                'parent': child['parent'], 'entries': entries}
    save(output / 'registry-v3.json', registry)
    generate(output / 'registry-v3.json')
    save(candidate / 'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1',
         'status': 'completed', 'area': wed_name, 'qa': 'pending-user-ingame',
         'files': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)}
                   for p in sorted(candidate.iterdir()) if p.name != 'manifest.json'}})
    save(output / 'build.json', {'status': 'candidate-ready', 'source_wed': evidence(source_wed),
         'geometry': base_geometry, 'reports': reports, 'base_registry': evidence(base_registry),
         'producer': evidence(Path(__file__))})
    for r in reports:
        print(f"{r['group']}/{r['resref']} -> {r['alias']}: sharpness x{r['sharpness_ratio_max_min']:.2f}, "
              f"step max/med {r['step_ratio_max_median']:.2f}", flush=True)


def review(output):
    ffmpeg = Path(shutil.which('ffmpeg') or get_path('topaz_video_ffmpeg'))
    plan = read(output / 'plan.json')
    for group in plan['groups']:
        g = group['group']
        dim = len(g['layout'])
        decoded = {ref: decode_tiles(output / 'candidate' / (group['aliases'][ref] + '.TIS'), output / 'candidate')
                   for ref in g['resrefs']}
        review_dir = output / group['id'] / 'review'
        review_dir.mkdir()
        for i in range(group['phases']):
            canvas = Image.new('RGB', (TILE * dim * 2, TILE * dim * 2))
            for y, row in enumerate(g['layout']):
                for x, ref in enumerate(row):
                    tile = Image.fromarray(decoded[ref][i][:, :, :3])
                    for oy in range(2):
                        for ox in range(2):
                            canvas.paste(tile, ((ox * dim + x) * TILE, (oy * dim + y) * TILE))
            canvas.save(review_dir / f'frame_{i:03d}.png')
        subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-stream_loop', '3',
                        '-framerate', str(DISPLAY_FPS), '-i', str(review_dir / 'frame_%03d.png'),
                        '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        str(output / group['id'] / 'review-30fps.mp4')], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=['prepare', 'interpolate', 'upscale', 'build', 'review'], required=True)
    parser.add_argument('--plan', type=Path, help='prepare only')
    parser.add_argument('--frames-per-chunk', type=int, help='SeedVR manual chunk (4n+1) when one chunk exceeds VRAM')
    parser.add_argument('--chunk-overlap', type=int, default=0)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'maps')
    if args.stage == 'prepare':
        prepare(args.plan.resolve(), output, get_path('bg2ee_game_root'))
    elif args.stage == 'interpolate':
        interpolate(output)
    elif args.stage == 'upscale':
        upscale(output, args.frames_per_chunk, args.chunk_overlap)
    elif args.stage == 'build':
        build(output)
    else:
        review(output)
