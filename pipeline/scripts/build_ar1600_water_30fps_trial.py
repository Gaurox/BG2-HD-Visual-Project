"""AR1600 only: closed-loop Apollo water interpolation, preserving x4 anchors.

Produces assets and a candidate runtime registry; does not install or update release.
36 phases at 15 Hz + renderer half-steps at 30 Hz retain the authored 2.4 s loop.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw
from build_liquid_periodic_x4_trial import export_tiles, seam_metrics
from mos_decode import decode_pvrz_page
from water_wed import replace_overlay_resref, replace_overlay_timeline, validate_polygons
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
SPATIAL = ROOT / 'maps/water-batches/runs/liquid-families-x4-20260923-v1'
ENGINE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
sys.path.insert(0, str(ENGINE / 'tools'))
from generate_water_route2_registry import load_registry, generate


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


def decode_tiles(tis, folder):
    data = tis.read_bytes()
    count, size, offset, dimension = struct.unpack_from('<4I', data, 8)
    assert size == 12 and dimension == 256
    pages, result = {}, []
    for i in range(count):
        page, x, y = struct.unpack_from('<3I', data, offset + i * 12)
        if page not in pages:
            pages[page] = decode_pvrz_page((folder / f'{tis.stem[0] + tis.stem[2:]}{page:02d}.PVRZ').read_bytes())
        result.append(np.asarray(pages[page].crop((x, y, x + 256, y + 256))).copy())
    return result


def prepare(output, game):
    output.mkdir(parents=True, exist_ok=False)
    override = game / 'override'
    prior = read(SPATIAL / 'override-candidate-v3/manifest.json')['files']
    baseline_names = ['AR1600.WED', 'AR1600.TIS', 'Q9LAKE.TIS', 'QLAKE00.PVRZ',
                      'Q9LAKER.TIS', 'QLAKER00.PVRZ']
    for name in baseline_names:
        if name in prior:
            assert digest(override / name) == prior[name]['sha256'].upper(), name
    before = {name: evidence(override / name) for name in baseline_names}
    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini',
                 'override/fpSEAM.glsl', 'override/fpTone.glsl']:
        before[name] = evidence(game / name)
    assert before['InfinityEngine-Enhancer.dll']['sha256'] == 'C6AA1CFA15083E12F9015F7D9B85A343BEB849CCE80B5EC717EF4FBAB06EE0A6'
    groups = []
    for weather, group, ref, old, new in [('dry', 'lake', 'WTLAKE', 'Q9LAKE', 'QALAK0'),
                                         ('rain', 'lake_rain', 'WTLAKER', 'Q9LAKER', 'QALAK0R')]:
        assert not (override / (new + '.TIS')).exists()
        assert not (override / (new[0] + new[2:] + '00.PVRZ')).exists()
        source = SPATIAL / 'overlays-r2/groups' / group / 'tiles-x4' / ref
        folder = output / weather
        (folder / 'inputs').mkdir(parents=True)
        (folder / 'anchors').mkdir()
        # Retain the actual installed appearance: require source PNGs to encode
        # to the currently selected atlas, then keep these anchors unmodified.
        paths = [source / f'frame_{i:03d}.png' for i in range(6)]
        for i in range(7):
            with Image.open(paths[i % 6]) as image:
                tile = np.array(image.convert('RGBA'))
            assert tile.shape == (256, 256, 4) and np.all(tile[:, :, 3] == 255)
            if i < 6:
                Image.fromarray(tile).save(folder / f'anchors/frame_{i:03d}.png')
            Image.fromarray(np.tile(tile[:, :, :3], (3, 3, 1))).save(folder / f'inputs/frame_{i:03d}.png')
        groups.append({'weather': weather, 'old_alias': old, 'alias': new,
                       'anchors': [evidence(p) for p in paths]})
    save(output / 'plan.json', {'schema': 'bg2-ar1600-water-interpolation-trial-v1',
        'game_root': str(game), 'before': before, 'groups': groups,
        'cycle_seconds': 2.4, 'native_anchor_fps': 2.5, 'stored_phase_fps': 15,
        'display_fps': 30, 'interpolator': 'apo-8', 'procedural_strength': 0,
        'qa': 'pending-user-ingame'})


def interpolate(output):
    ffmpeg = get_path('topaz_video_ffmpeg')
    env = dict(os.environ)
    env['TVAI_MODEL_DIR'] = str(get_path('topaz_video_models'))
    env['TVAI_MODEL_DATA_DIR'] = str(get_path('topaz_video_models'))
    for group in read(output / 'plan.json')['groups']:
        folder = output / group['weather']
        raw = folder / 'apollo'
        raw.mkdir(exist_ok=False)
        command = [str(ffmpeg), '-hide_banner', '-y', '-framerate', '5/2', '-i',
                   str(folder / 'inputs/frame_%03d.png'), '-vf',
                   'tvai_fi=model=apo-8:slowmo=1:rdt=-0.01:fps=15:device=-2',
                   '-fps_mode', 'passthrough', '-pix_fmt', 'rgb24', str(raw / 'out_%06d.png')]
        save(folder / 'apollo-command.json', {'argv': command})
        with (folder / 'apollo.log').open('w', encoding='utf-8') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        files = sorted(raw.glob('out_*.png'))
        if len(files) not in (36, 37):
            raise ValueError(f'Apollo frame count: {len(files)}')
        frames = folder / 'frames'
        frames.mkdir()
        for i in range(36):
            if i % 6 == 0:
                shutil.copy2(folder / f'anchors/frame_{i//6:03d}.png', frames / f'frame_{i:03d}.png')
            else:
                with Image.open(files[i]) as image:
                    assert image.size == (768, 768)
                    image.convert('RGBA').crop((256, 256, 512, 512)).save(frames / f'frame_{i:03d}.png')
        save(folder / 'interpolation.json', {'frames': 36, 'raw_frames': len(files),
             'anchors_restored_exactly': [0, 6, 12, 18, 24, 30], 'closed_loop': True})
        print(group['weather'] + ': Apollo closed loop completed', flush=True)


def build(output):
    plan = read(output / 'plan.json')
    game = Path(plan['game_root'])
    override = game / 'override'
    candidate = output / 'candidate'
    assert not (output / 'build.json').exists() and not (candidate / 'manifest.json').exists()
    candidate.mkdir(exist_ok=True)
    wed = (override / 'AR1600.WED').read_bytes()
    assert digest(override / 'AR1600.WED') == plan['before']['AR1600.WED']['sha256']
    changed = replace_overlay_resref(replace_overlay_timeline(wed, 1, 36, 1), 1, 'QALAK0')
    assert validate_polygons(wed) == validate_polygons(changed)
    (candidate / 'AR1600.WED').write_bytes(changed)
    headers = struct.unpack_from('<I', changed, 16)[0]
    slots = [changed[headers+i*24+4:headers+i*24+12].split(b'\0')[0].decode('ascii')
             for i in range(struct.unpack_from('<I', changed, 8)[0])]
    width, height = struct.unpack_from('<HH', changed, headers)
    tilemap = struct.unpack_from('<I', changed, headers + 16)[0]
    coverage = sum(bool(changed[tilemap+i*10+6] & 2) for i in range(width*height))
    base = override / 'AR1600.TIS'
    base_count = struct.unpack_from('<I', base.read_bytes(), 8)[0]
    parent = ENGINE / 'assets/water-route2/registry-v2.json'
    _, resolved = load_registry(parent)
    entries = copy.deepcopy(resolved['entries'])
    reports = []
    for group in plan['groups']:
        folder = output / group['weather']
        frames = [np.asarray(Image.open(folder / f'frames/frame_{i:03d}.png').convert('RGBA')) for i in range(36)]
        built = export_tiles(frames, group['alias'], candidate)
        decoded = decode_tiles(candidate / (group['alias'] + '.TIS'), candidate)
        old = decode_tiles(override / (group['old_alias'] + '.TIS'), override)
        assert all(np.array_equal(decoded[i*6], old[i]) for i in range(6)), 'Installed anchor pixels changed'
        assert all(np.all(frame[:, :, 3] == 255) for frame in decoded)
        pairs = [{'a': 'water', 'b': 'water', 'axis': axis} for axis in ('x', 'y')]
        reports.append({'weather': group['weather'], 'outputs': built, 'anchors_post_bc3_exact': True,
                        'metrics': [seam_metrics({'water': f}, pairs) for f in decoded]})
        tis, page = [Path(f['path']) for f in built['files']]
        entries.append({'id': 'ar1600-temporal-only-' + group['weather'] + '-20260923-v1',
            'state': 'candidate-installable-pending-qa', 'qa': {'status': 'pending-ingame'},
            'wed': {'resref': 'AR1600', 'sha256': digest(candidate/'AR1600.WED'),
                    'grid': {'width': width, 'height': height}, 'overlay_slots': slots},
            'base_tis': {'resref': 'AR1600', 'tile_count': base_count, 'bytes': base.stat().st_size,
                         'sha256': digest(base), 'pages': []},
            'overlay': {'slot': 1, 'tis_resref': group['alias'], 'tis_sha256': digest(tis),
                        'tis_bytes': tis.stat().st_size, 'tile_count': 36, 'tile_dimension': 256,
                        'pages': [{'resref': page.stem, 'width': 2048, 'height': 2048,
                                   'bytes': page.stat().st_size, 'sha256': digest(page)}]},
            'approved_strength': 0, 'material_id': 1, 'overlay_coverage_cells': coverage,
            'allow_stock_wed_when_override_absent': False,
            'temporal_overlay': {'mode': 'atlas-linear', 'frame_count': 36, 'source_fps': 15,
                'target_fps': 30, 'atlas_columns': 7, 'atlas_stride_pixels': 264, 'atlas_padding_pixels': 4}})
    registry = {'schema': 'bg2-water-route2-registry-v3', 'version': 3,
                'parent': {'path': parent.relative_to(ROOT).as_posix(), 'sha256': digest(parent)},
                'entries': entries}
    save(output / 'registry-v3.json', registry)
    generate(output / 'registry-v3.json')
    save(candidate / 'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1',
         'status': 'completed', 'area': 'AR1600', 'qa': 'pending-user-ingame',
         'files': {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in candidate.iterdir()}})
    save(output / 'build.json', {'status': 'candidate-ready', 'reports': reports,
         'geometry': validate_polygons(changed), 'coverage': coverage,
         'other_registry_entries_preserved_exactly': True, 'producer': evidence(Path(__file__))})
    print('Built AR1600 dry/rain: exact anchors, 36 phases, temporal-only registry', flush=True)


def review(output):
    ffmpeg = Path(shutil.which('ffmpeg') or get_path('topaz_video_ffmpeg'))
    for weather in ('dry', 'rain'):
        folder = output / weather
        frames = decode_tiles(output / 'candidate' / ('QALAK0' + ('R' if weather=='rain' else '') + '.TIS'), output / 'candidate')
        review_dir = folder / 'review'
        review_dir.mkdir(exist_ok=True)
        for i in range(72):
            phase, fraction = divmod(i, 2)
            smooth = Image.blend(Image.fromarray(frames[phase]), Image.fromarray(frames[(phase+1)%36]), fraction/2)
            native = Image.fromarray(frames[(i//12)*6])
            canvas = Image.new('RGB', (1024, 536), (20, 20, 20))
            for k, tile in enumerate((native, smooth)):
                for x in range(2):
                    for y in range(2): canvas.paste(tile, (k*512+x*256, 24+y*256))
            ImageDraw.Draw(canvas).text((8, 5), 'Native cadence 2.5 fps                                      Apollo + 30 fps / unchanged 2.4 s loop', fill='white')
            canvas.save(review_dir / f'frame_{i:03d}.png')
        subprocess.run([str(ffmpeg), '-hide_banner', '-loglevel', 'error', '-y', '-framerate', '30',
                        '-i', str(review_dir/'frame_%03d.png'), '-c:v', 'libx264', '-crf', '16',
                        '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(folder/'comparison-30fps.mp4')], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--stage', choices=['prepare', 'interpolate', 'build', 'review'], required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'maps')
    if args.stage == 'prepare': prepare(output, get_path('bg2ee_game_root'))
    elif args.stage == 'interpolate': interpolate(output)
    elif args.stage == 'build': build(output)
    else: review(output)
