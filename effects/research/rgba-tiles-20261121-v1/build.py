"""Measure lossless sparse RGBA tiles against the alpha.11 cropped effect pack."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rgba_crop',
    HERE.parent / 'rgba-crop-full-20261121-v1/build.py')
crop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crop)
INPUTS = crop.RELEASE / 'release-inputs/effects'
BASE = INPUTS / 'accepted-crop-20261121-v1'
ORIGINAL = INPUTS / 'accepted-20261110-v1'
TILE_INDEX = 'EffectTiles-X4.index'
TILE_PIXELS = 'EffectTiles-X4.rgba'
MAGIC = b'IEETILE1'
HEADER = struct.Struct('<8sII32s')
FRAME = struct.Struct('<QIB3x')  # pixel offset, bitmap offset, tile edge (0 = dense)
EDGES = (4, 8, 16, 32, 64)
METADATA = ('manifest.json', crop.REGISTRY, crop.SHARED_INDEX, crop.INDEX)


def load_inputs(base, original_dir, proof):
    metadata = tuple(name for name in METADATA if name in proof)
    for name in metadata:
        path = base / name
        if path.stat().st_size != proof[name]['bytes'] or crop.file_hash(path) != proof[name]['sha256']:
            raise ValueError(f'Alpha.11 metadata changed: {name}')
    pack = json.loads((base / 'manifest.json').read_bytes())
    original = json.loads((original_dir / 'manifest.json').read_bytes())
    registry = (base / crop.REGISTRY).read_bytes()
    if (pack['frames'] != original['frames'] or pack['resources'] != original['resources']
            or registry != (original_dir / crop.REGISTRY).read_bytes()):
        raise ValueError('Pre-deduplication original frame catalogue differs')
    ids = crop.read_map(base, pack, registry)
    originals = defaultdict(list)
    for i, owner in enumerate(ids):
        originals[owner].append(pack['frames'][i])
    raw_index = (base / crop.INDEX).read_bytes()
    shared = (base / crop.SHARED_INDEX).read_bytes() if crop.SHARED_INDEX in proof else b''
    expected_header = (crop.MAGIC, len(originals), len(ids), crop.sha(registry),
                       crop.sha(shared))
    if crop.HEADER.unpack_from(raw_index) != expected_header:
        raise ValueError('Crop index binding differs')
    rows = tuple(crop.FRAME.iter_unpack(raw_index[crop.HEADER.size:]))
    offset = 0
    for owner, row in zip(sorted(originals), rows, strict=True):
        i, width, height, x, y, w, h, start = row
        if (i != owner or [width, height] != originals[i][0]['physical_size_x4']
                or offset != start or x + w > width or y + h > height
                or ((not w or not h) and (x or y or w or h))):
            raise ValueError(f'Invalid crop row: {i}')
        offset += w * h * 4
    if (base / crop.PIXELS).stat().st_size != offset or offset != proof[crop.PIXELS]['bytes']:
        raise ValueError('Cropped pixel blob length differs')
    return originals, rows, HEADER.pack(MAGIC, len(rows), len(ids), crop.sha(raw_index))


def grid(size, edge):
    return np.arange(0, size, edge)


def tile_bitmap_cost(tiles, row_starts, col_starts, h, w, edge):
    heights = np.minimum(h - row_starts, edge)
    widths = np.minimum(w - col_starts, edge)
    return 4 * int(np.sum((heights[:, None] * widths) * tiles)) + (tiles.size + 7) // 8


def expand_tiles(bitmap, h, w, edge):
    return bitmap.repeat(edge, axis=0).repeat(edge, axis=1)[:h, :w].astype(bool, copy=False)


def encode_frame(item):
    raw, h, w = item
    if not raw:
        return 0, b'', raw
    image = np.frombuffer(raw, dtype='<u4').reshape(h, w)
    occupancy = image != 0
    best_cost, best_edge, best_tiles = len(raw), 0, None
    for edge in EDGES:
        rows, cols = grid(h, edge), grid(w, edge)
        step = edge if edge == EDGES[0] else 2
        occupancy = np.logical_or.reduceat(occupancy, grid(occupancy.shape[0], step), axis=0)
        occupancy = np.logical_or.reduceat(occupancy, grid(occupancy.shape[1], step), axis=1)
        cost = tile_bitmap_cost(occupancy, rows, cols, h, w, edge)
        if cost < best_cost:
            best_cost, best_edge, best_tiles = cost, edge, occupancy
    if best_tiles is None:
        return 0, b'', raw
    bitmap = np.packbits(best_tiles.ravel(), bitorder='little').tobytes()
    pixels = image[expand_tiles(best_tiles, h, w, best_edge)].tobytes()
    if len(pixels) + len(bitmap) != best_cost:
        raise ValueError('Encoded size differs from tile cost')
    return best_edge, bitmap, pixels


def build(output, rows, header, base, proof):
    output.mkdir(exist_ok=False)
    for name in METADATA:
        if name in proof:
            shutil.copyfile(base / name, output / name)
    records, masks = bytearray(), bytearray()
    digest = hashlib.sha256()
    with (base / crop.PIXELS).open('rb') as source, (output / TILE_PIXELS).open('xb') as data, \
            ThreadPoolExecutor(max_workers=10) as pool:
        for start in range(0, len(rows), 48):
            batch = []
            for _, _, _, _, _, w, h, offset in rows[start:start + 48]:
                raw = source.read(w * h * 4)
                if len(raw) != w * h * 4:
                    raise ValueError(f'Truncated crop blob at {offset}')
                digest.update(raw)
                batch.append((raw, h, w))
            for edge, bitmap, pixels in pool.map(encode_frame, batch):
                records.extend(FRAME.pack(data.tell(), len(masks), edge))
                masks.extend(bitmap)
                data.write(pixels)
            if start % 8160 == 0:
                print(f'{min(start + 48, len(rows))}/{len(rows)} frames encoded', flush=True)
    if digest.hexdigest() != proof[crop.PIXELS]['sha256']:
        raise ValueError('Alpha.11 pixel blob differs from the verified release')
    with (output / TILE_INDEX).open('xb') as index:
        for part in (header, records, masks):
            index.write(part)


def decode_frame(pixels, mask, row, edge):
    i, width, height, x, y, w, h, _ = row
    full = np.zeros((height, width), dtype='<u4')
    rectangle = full[y:y + h, x:x + w]
    values = np.frombuffer(pixels, dtype='<u4')
    if not edge:
        rectangle[:] = values.reshape(h, w)
    else:
        ny, nx = (h + edge - 1) // edge, (w + edge - 1) // edge
        bits = np.unpackbits(np.frombuffer(mask, dtype=np.uint8), bitorder='little')
        if bits[ny * nx:].any():
            raise ValueError(f'Nonzero tile padding: {i}')
        rectangle[expand_tiles(bits[:ny * nx].reshape(ny, nx), h, w, edge)] = values
    return full.tobytes()


def verify(output, originals, rows, header, original_dir, proof):
    for name in METADATA:
        if name in proof and crop.file_hash(output / name) != proof[name]['sha256']:
            raise ValueError(f'Output metadata differs: {name}')
    index = (output / TILE_INDEX).read_bytes()
    data_size = (output / TILE_PIXELS).stat().st_size
    if not index.startswith(header) or len(index) < HEADER.size + FRAME.size * len(rows):
        raise ValueError('Invalid tile index header')
    mask_base = HEADER.size + FRAME.size * len(rows)
    records = list(FRAME.iter_unpack(index[HEADER.size:mask_base]))
    next_records = records[1:] + [(data_size, len(index) - mask_base, 0)]
    if records[0][:2] != (0, 0):
        raise ValueError('Tile offsets must start at zero')
    modes = Counter()
    jobs = []
    for row, (start, mask_start, edge), (end, mask_end, _) in zip(rows, records, next_records, strict=True):
        *_, w, h, _ = row
        if edge not in (0, *EDGES) or not 0 <= start <= end <= data_size:
            raise ValueError(f'Invalid tile frame record: {row[0]}')
        expected_mask = (((w + edge - 1) // edge) * ((h + edge - 1) // edge) + 7) // 8 if edge else 0
        if mask_end - mask_start != expected_mask or mask_base + mask_end > len(index):
            raise ValueError(f'Invalid tile bitmap size: {row[0]}')
        jobs.append((row, start, end, index[mask_base + mask_start:mask_base + mask_end], edge))
        modes[str(edge) if edge else 'dense'] += 1

    def check_batch(batch):
        with (output / TILE_PIXELS).open('rb') as data:
            logical = 0
            for row, start, end, mask, edge in batch:
                data.seek(start)
                decoded = decode_frame(data.read(end - start), mask, row, edge)
                for frame in originals[row[0]]:
                    reference = (original_dir / frame['asset']).read_bytes()
                    if decoded != reference or crop.sha(reference).hex() != frame['sha256'].lower():
                        raise ValueError(f"Reconstructed frame differs from original: {frame['asset']}")
                    logical += 1
        return len(batch), logical

    physical_count = logical_count = 0
    with ThreadPoolExecutor(max_workers=10) as pool:
        for physical, logical in pool.map(check_batch, (jobs[i:i + 48] for i in range(0, len(jobs), 48))):
            physical_count += physical
            logical_count += logical
            if physical_count % 8160 == 0:
                print(f'{physical_count}/{len(rows)} backings byte-identical to their originals', flush=True)
    before = proof[crop.PIXELS]['bytes'] + proof[crop.INDEX]['bytes']
    files = {path.name: {'bytes': path.stat().st_size, 'sha256': crop.file_hash(path)}
             for path in output.iterdir() if path.is_file()}
    after = sum(files[name]['bytes'] for name in (TILE_INDEX, TILE_PIXELS, crop.INDEX))
    return {
        'original_pack': (original_dir.relative_to(crop.ROOT).as_posix() if original_dir.is_relative_to(crop.ROOT)
                          else 'config://bg2ee_game_root/iee-assets/effects-before-crop-20261121-v1'),
        'resources': len({f['resref'] for group in originals.values() for f in group}),
        'physical_frames_byte_exact': physical_count,
        'original_logical_frame_files_byte_exact': logical_count,
        'original_alias_files_byte_exact': logical_count - physical_count,
        'cropped_bytes_with_index': before,
        'tiled_bytes_with_both_indexes': after,
        'net_savings_bytes': before - after,
        'net_savings_pct': round(100 * (before - after) / before, 4),
        'mode_counts': dict(sorted(modes.items())),
        'files': files,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify'))
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    kind = 'live' if args.live else 'release'
    proof = json.loads((Path(crop.__file__).parent / f'results-{kind}.json').read_bytes())['files']
    base = Path(crop.__file__).parent / 'packs/live' if args.live else BASE
    original = (crop.get_path('bg2ee_game_root') / 'iee-assets/effects-before-crop-20261121-v1'
                if args.live else ORIGINAL)
    originals, rows, header = load_inputs(base, original, proof)
    final = HERE / ('pack-live' if args.live else 'pack')
    if args.action == 'build' and final.exists():
        raise FileExistsError(final)
    output = final.with_suffix('.partial') if args.action == 'build' else final
    if args.action == 'build':
        build(output, rows, header, base, proof)
    result = verify(output, originals, rows, header, original, proof)
    report = json.dumps(result, indent=2) + '\n'
    if args.action == 'build':
        output.rename(final)
        (HERE / ('results-live.json' if args.live else 'results.json')).write_text(report, encoding='utf-8', newline='\n')
    print(report, end='')


if __name__ == '__main__':
    main()
