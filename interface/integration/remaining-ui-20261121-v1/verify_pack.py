"""Verify every installed resource's dimensions, coverage, center, and cycles before install."""
import hashlib
import json
import struct
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'interface/experiments/remaining-ui-seedvr7b-x4-20261121-v1'
PACK = HERE / 'pack'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def blocks(data, offset, first, count):
    return [struct.unpack_from('<7I', data, offset + 28 * i) for i in range(first, first + count)]


def verify_frame(frame, rendered_blocks, pages, verify_alpha):
    width, height = frame['native_size']
    coverage = np.zeros((height, width), dtype=np.uint8)
    source_alpha = np.asarray(Image.open(RUN / 'sources' / f"{frame['key']}-x1.png").getchannel('A'))
    for page, sx, sy, w, h, dx, dy in rendered_blocks:
        atlas_width, atlas_height, dxt = pages[page]
        assert w and h and sx + w <= atlas_width and sy + h <= atlas_height
        assert dx + w <= width and dy + h <= height
        coverage[dy:dy+h, dx:dx+w] += 1
        if verify_alpha and frame['alpha_native_preserved']:
            actual = dxt[sy:sy+h, sx:sx+w, :8]
            alpha = source_alpha[dy:dy+h, dx:dx+w]
            assert np.array_equal(actual[:, :, 0], alpha) and np.array_equal(actual[:, :, 1], alpha)
            assert not np.any(actual[:, :, 2:])
    assert np.all(coverage == 1), frame['key']


def main():
    manifest = read(HERE / 'pack.json')
    results = read(RUN / 'results.json')
    by_name = defaultdict(list)
    by_key = {}
    for frame in results['results']:
        by_name[frame['resref']].append(frame)
        by_key[frame['key']] = frame
    for name in by_name:
        by_name[name].sort(key=lambda frame: frame['frame'])
    assert set(manifest['resources']) == set(by_name)
    assert {item['key'] for item in manifest['gallery']} == set(by_key)
    for filename, digest in manifest['files'].items():
        assert hashlib.sha256((PACK / filename).read_bytes()).hexdigest() == digest, filename
    fixtures = HERE / 'verification-fixtures'
    fixtures.mkdir(exist_ok=True)
    pages = {}
    for row in manifest['pages']:
        name = f"MOS{row['page']:04}"
        compressed = (PACK / f'override/{name}.PVRZ').read_bytes()
        pvr = zlib.decompress(compressed[4:])
        assert len(pvr) == struct.unpack_from('<I', compressed)[0]
        signature, _, pixel_format, _, _, _, height, width, _, _, _, mips, metadata = struct.unpack_from('<13I', pvr)
        assert signature == 0x03525650 and pixel_format == 11 and mips == 1
        assert (width, height) == (row['width'], row['height'])
        native_dxt = pvr[52+metadata:]
        assert len(native_dxt) == width * height
        (fixtures / f'{name}.dxt5').write_bytes(native_dxt)
        tiles = np.memmap(PACK / f'iee-assets/UIREVIEW-{name}-x4.dxt5', np.uint8, 'r', shape=(height, width, 16))
        pages[row['page']] = (width, height, tiles)

    converted = 0
    for name, row in manifest['resources'].items():
        native = by_name[name]
        data = (PACK / row['path']).read_bytes()
        if row['source_format'].endswith('V1'):
            converted += 1
        if row['installed_format'] == 'MOS V2':
            assert len(native) == 1 and data[:8] == b'MOS V2  '
            width, height, count, offset = struct.unpack_from('<4I', data, 8)
            assert [width, height] == native[0]['native_size'] and len(data) == offset + count * 28
            verify_frame(native[0], blocks(data, offset, 0, count), pages, True)
            continue
        assert data[:8] == b'BAM V2  '
        fc, cc, bc, fo, co, bo = struct.unpack_from('<6I', data, 8)
        assert (fo, co, bo, len(data)) == (32, 32+fc*12, 32+fc*12+cc*4, 32+fc*12+cc*4+bc*28)
        entries = [struct.unpack_from('<HHhhHH', data, fo + i * 12) for i in range(fc)]
        for frame, entry in zip(native, entries):
            w, h, cx, cy, first, count = entry
            assert [w, h] == frame['native_size'] and [cx, cy] == frame['center_native']
            verify_frame(frame, blocks(data, bo, first, count), pages, True)
        assert cc == len(native[0]['cycles'])
        for index, sequence in enumerate(native[0]['cycles']):
            count, first = struct.unpack_from('<HH', data, co + index * 4)
            assert entries[first:first + count] == [entries[i] for i in sequence]
    for item in manifest['gallery']:
        if item['mosaic'].startswith('BGQ'):
            frame = by_key[item['key']]
            data = (PACK / f"override/{item['mosaic']}.MOS").read_bytes()
            width, height, count, offset = struct.unpack_from('<4I', data, 8)
            assert [width, height] == frame['native_size']
            verify_frame(frame, blocks(data, offset, 0, count), pages, False)
    assert converted == 39
    print(f'{len(by_name)} resources, {len(by_key)} frames, {converted} V1 conversions, '
          f'{len(pages)} atlases: geometry, alpha, cycles and hashes verified.')


if __name__ == '__main__':
    main()
