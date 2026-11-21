"""Build and independently verify complete, registry-bound cropped RGBA packs."""
import argparse
import hashlib
import json
import struct
import sys
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from pathlib import Path
from zipfile import ZipFile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RELEASE = ROOT / 'releases/BG2-HD-Upscale'
ARCHIVE = (RELEASE / 'dist-local/alpha10-ui-20261121-v1'
           / 'BG2HD-0.1.0-alpha.10-windows-local-alpha.zip')
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from effect_storage import NAME as SHARED_INDEX, read_map, validate_layout
from workspace_paths import get_path

REGISTRY = 'EffectAnimations-X4.registry'
INDEX = 'EffectCrops-X4.index'
PIXELS = 'EffectCrops-X4.rgba'
MAGIC = b'IEECROP2'
HEADER = struct.Struct('<8sII32s32s')
FRAME = struct.Struct('<I6HQ')


def sha(data):
    return hashlib.sha256(data).digest()


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def selection(kind, live_directory=None):
    archive_inventory = None
    if kind == 'release':
        with ZipFile(ARCHIVE) as archive:
            entries = json.loads(archive.read('bg2hd/manifests/content.json'))['entries']
        archive_inventory = {Path(row['destination']).name: row for row in entries
                             if row['destination'].startswith('iee-assets/effects/')}
        manifest_path = ROOT / archive_inventory['manifest.json']['source']
        directory = manifest_path.parent
    else:
        directory = live_directory or (get_path('bg2ee_game_root') / 'iee-assets/effects')
        manifest_path = directory / 'manifest.json'
    manifest_raw = manifest_path.read_bytes()
    if archive_inventory and sha(manifest_raw).hex() != archive_inventory['manifest.json']['sha256'].lower():
        raise ValueError('Effect production manifest differs from the archived release')
    manifest = json.loads(manifest_raw)
    if manifest['registry'] != REGISTRY:
        raise ValueError('Unexpected registry name')
    registry = (directory / REGISTRY).read_bytes()
    if sha(registry).hex() != manifest['registry_sha256'].lower():
        raise ValueError('Registry hash differs from the source manifest')
    validate_layout(registry, manifest['frames'])
    ids = read_map(directory, manifest, registry)
    shared = (directory / SHARED_INDEX).read_bytes() if manifest.get('storage') else b''
    frames = manifest['frames']
    if archive_inventory:
        expected = set(archive_inventory)
        actual = {REGISTRY, SHARED_INDEX, 'manifest.json'} | {frames[i]['asset'] for i in set(ids)}
        if actual != expected:
            raise ValueError('Physical inventory differs from the archived release')
        for i in set(ids):
            frame = frames[i]
            row = archive_inventory[frame['asset']]
            if frame['bytes'] != row['bytes'] or frame['sha256'].lower() != row['sha256'].lower():
                raise ValueError(f'Archived frame metadata differs: {frame["asset"]}')
    return directory, manifest_raw, frames, ids, registry, shared


def crop(frame, directory):
    raw = (directory / frame['asset']).read_bytes()
    if len(raw) != frame['bytes'] or sha(raw).hex() != frame['sha256'].lower():
        raise ValueError(f'Original frame differs: {frame["asset"]}')
    width, height = frame['physical_size_x4']
    image = np.frombuffer(raw, dtype='<u4').reshape(height, width)
    occupied = image != 0
    ys = np.flatnonzero(occupied.any(axis=1))
    xs = np.flatnonzero(occupied.any(axis=0))
    if not len(ys):
        return width, height, 0, 0, 0, 0, b''
    x, y = int(xs[0]), int(ys[0])
    right, bottom = int(xs[-1]) + 1, int(ys[-1]) + 1
    return width, height, x, y, right - x, bottom - y, image[y:bottom, x:right].tobytes()


def build(inputs, output):
    directory, manifest_raw, frames, ids, registry, shared = inputs
    canonical = sorted(set(ids))
    output.mkdir(parents=True, exist_ok=False)
    with (output / INDEX).open('xb') as index, (output / PIXELS).open('xb') as data:
        index.write(HEADER.pack(MAGIC, len(canonical), len(ids), sha(registry), sha(shared)))
        with ThreadPoolExecutor(max_workers=12) as executor:
            iterator = iter(canonical)
            for done in range(0, len(canonical), 512):
                group = list(islice(iterator, 512))
                rectangles = executor.map(lambda i: crop(frames[i], directory), group)
                for i, (*rectangle, pixels) in zip(group, rectangles, strict=True):
                    index.write(FRAME.pack(i, *rectangle, data.tell()))
                    data.write(pixels)
                if done % 8192 == 0:
                    print(f'{min(done + 512, len(canonical))}/{len(canonical)} rectangles', flush=True)
    (output / REGISTRY).write_bytes(registry)
    if shared:
        (output / SHARED_INDEX).write_bytes(shared)
    (output / 'manifest.json').write_bytes(manifest_raw)


def verify(inputs, output):
    directory, manifest_raw, frames, ids, registry, shared = inputs
    canonical = sorted(set(ids))
    raw_index = (output / INDEX).read_bytes()
    if (len(raw_index) != HEADER.size + FRAME.size * len(canonical)
            or HEADER.unpack_from(raw_index) != (MAGIC, len(canonical), len(ids), sha(registry), sha(shared))):
        raise ValueError('Cropped index does not match the original pack')
    metadata_files = {
        REGISTRY: registry,
        'manifest.json': manifest_raw,
    }
    if shared:
        metadata_files[SHARED_INDEX] = shared
    for name, expected in metadata_files.items():
        if (output / name).read_bytes() != expected:
            raise ValueError(f'Pack metadata differs: {name}')
    rows = list(FRAME.iter_unpack(raw_index[HEADER.size:]))
    offset = 0
    for i, record in zip(canonical, rows, strict=True):
        identifier, width, height, x, y, w, h, start = record
        if (i != identifier or [width, height] != frames[i]['physical_size_x4']
                or start != offset or x + w > width or y + h > height
                or ((not w or not h) and (x or y or w or h))):
            raise ValueError(f'Invalid index row: {i}')
        offset += w * h * 4
    if (output / PIXELS).stat().st_size != offset:
        raise ValueError('Pixel blob size differs from the crop index')

    def check_batch(batch):
        with (output / PIXELS).open('rb') as data:
            for i, width, height, x, y, w, h, start in batch:
                data.seek(start)
                pixels = data.read(w * h * 4)
                canvas = np.zeros((height, width, 4), dtype=np.uint8)
                canvas[y:y + h, x:x + w] = np.frombuffer(pixels, np.uint8).reshape(h, w, 4)
                reference = (directory / frames[i]['asset']).read_bytes()
                if canvas.tobytes() != reference or sha(reference).hex() != frames[i]['sha256'].lower():
                    raise ValueError(f'Non-identical reconstruction: {frames[i]["asset"]}')
        return len(batch)

    checked = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        for count in executor.map(check_batch, (rows[i:i + 64] for i in range(0, len(rows), 64))):
            checked += count
            if checked % 8192 == 0:
                print(f'{checked}/{len(canonical)} frames identical', flush=True)
    original = sum(frames[i]['bytes'] for i in canonical)
    files = {path.name: {'bytes': path.stat().st_size, 'sha256': file_hash(path)}
             for path in output.iterdir() if path.is_file()}
    cropped = files[PIXELS]['bytes'] + files[INDEX]['bytes']
    return {
        'resources': len({frame['resref'] for frame in frames}),
        'logical_frames_verified': len(ids),
        'physical_frames_byte_exact': checked,
        'original_rgba_bytes': original,
        'cropped_rgba_bytes': files[PIXELS]['bytes'],
        'new_index_bytes': files[INDEX]['bytes'],
        'net_savings_bytes': original - cropped,
        'net_savings_pct': round(100 * (original - cropped) / original, 4),
        'files': files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'verify'])
    parser.add_argument('kind', choices=['release', 'live'])
    parser.add_argument('--live-directory', type=Path)
    args = parser.parse_args()
    inputs = selection(args.kind, args.live_directory)
    output = HERE / 'packs' / args.kind
    if args.action == 'build':
        build(inputs, output)
    result = verify(inputs, output)
    report = json.dumps(result, indent=2) + '\n'
    if args.action == 'build':
        (HERE / f'results-{args.kind}.json').write_text(report, encoding='utf-8', newline='\n')
    print(report, end='')


if __name__ == '__main__':
    main()
