"""Share identical nonzero tiles from the verified area-animation tile grid."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
from zipfile import ZIP_STORED, ZipFile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = HERE / 'run'
WORK = RUN / 'work'
PACK = RUN / 'area-animations-shared-tiles-test.zip'
BASE_PATH = HERE.parent / 'area-animation-tiles-20261121-v1/build.py'
spec = importlib.util.spec_from_file_location('area_animation_tiles', BASE_PATH)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
sharing = base.sharing

HEADER = struct.Struct('<8sII32s')
RECORD = struct.Struct('<QQII')
PIXELS = 'EffectSharedTiles-X4.bin'
EXTRA = {'area-animation-tile-sharing.index': 'EffectSharedTiles-X4.index',
         'area-animation-tile-dictionary.rgba': 'EffectSharedTiles-X4.dictionary.rgba'}


def original_catalog(archive):
    source_manifest = sharing.CONTENT.read_bytes()
    exact_proof = json.loads((Path(sharing.__file__).parent / 'results.json').read_bytes())
    if sharing.sha(source_manifest) != exact_proof['content_manifest_sha256']:
        raise ValueError('Original source catalog differs')
    originals = {row['destination']: row for row in json.loads(source_manifest)['entries']
                 if row['kind'] == 'area-animation'}
    mapping = json.loads(archive.read(sharing.INDEX))
    if mapping['format'] != 'shared-area-animation-frames-v1':
        raise ValueError('Unexpected deduplicated archive format')
    if set(originals) != mapping['frames'].keys() | set(mapping['metadata']):
        raise ValueError('Unexpected archive inventory')
    groups = defaultdict(list)
    for path, digest in mapping['frames'].items():
        source = originals[path]
        if (not sharing.FRAME.fullmatch(path) or not re.fullmatch(r'animations/[A-Za-z0-9_./-]+', source['source'])
                or source['sha256'].lower() != digest):
            raise ValueError(f'Original frame mapping differs: {path}')
        groups[digest].append(source)
    for path in mapping['metadata']:
        if not sharing.METADATA.fullmatch(path) or archive.read(path) != sharing.source_bytes(originals[path]):
            raise ValueError(f'Original metadata differs: {path}')
    return mapping, dict(sorted(groups.items()))


def plan(archive, groups, logical_count):
    crop_data, tile_data = archive.read(base.CROP_INDEX), archive.read(base.TILE_INDEX)
    if base.HEADER.unpack_from(crop_data) != (b'AAX4CRP1', len(groups),
                                               hashlib.sha256(archive.read(sharing.INDEX)).digest()):
        raise ValueError('Crop index binding differs')
    if base.HEADER.unpack_from(tile_data) != (b'AAX4TIL1', len(groups), hashlib.sha256(crop_data).digest()):
        raise ValueError('Tile index binding differs')
    if len(crop_data) != base.HEADER.size + len(groups) * base.GEOMETRY.size:
        raise ValueError('Invalid crop index length')
    tile_hash = hashlib.sha256(tile_data).digest()
    bitmap_path = WORK / base.TILE_INDEX
    bitmap_path.write_bytes(tile_data)
    cursor = base.HEADER.size + len(groups)
    edges = tile_data[base.HEADER.size:cursor]
    with (WORK / 'plan.txt').open('x', encoding='ascii', newline='\n') as out:
        print(tile_hash.hex(), file=out)
        shapes = base.GEOMETRY.iter_unpack(memoryview(crop_data)[base.HEADER.size:])
        for rows, shape, edge in zip(groups.values(), shapes, edges, strict=True):
            width, height, x, y, w, h = shape
            if (not width or not height or x+w > width or y+h > height
                    or (not (w and h) and (x or y or w or h or edge)) or edge not in (0, *base.tiles.EDGES)
                    or any(row['bytes'] != width*height*4 for row in rows)):
                raise ValueError(f'Unexpected tile geometry: {rows[0]["destination"]}')
            size = (((w+edge-1)//edge)*((h+edge-1)//edge)+7)//8 if edge else 0
            print(*shape, edge, cursor, size, *(row['source'] for row in rows), file=out)
            cursor += size
    if cursor != len(tile_data) or sum(map(len, groups.values())) != logical_count:
        raise ValueError('Invalid tile index end or logical count')
    return bitmap_path, tile_hash


def verify_originals(groups):
    def check(item):
        digest, originals = item
        path = ROOT / originals[0]['source']
        if path.stat().st_size != originals[0]['bytes'] or sharing.file_sha(path) != digest:
            raise ValueError(f'Original frame differs: {path}')

    with ThreadPoolExecutor(max_workers=10) as pool:
        for count, _ in enumerate(pool.map(check, groups.items()), 1):
            if count % 2048 == 0:
                print(f'{count}/{len(groups)} sources canoniques confirmées', flush=True)


def write_and_check_archive(source, mapping, groups, data, tile_hash):
    names = [sharing.blob_name(digest) for digest in groups]
    literals = [*mapping['metadata'], sharing.INDEX, base.CROP_INDEX, base.TILE_INDEX]
    index = (data / EXTRA['area-animation-tile-sharing.index']).read_bytes()
    if HEADER.unpack_from(index) != (b'IEETSHR1', len(names), len(mapping['frames']), tile_hash):
        raise ValueError('Invalid sharing index binding')
    record_end = HEADER.size + RECORD.size * len(names)
    offsets = [row[0] for row in RECORD.iter_unpack(index[HEADER.size:record_end])]
    size = (data / PIXELS).stat().st_size
    if not offsets or offsets[0] or offsets != sorted(offsets) or offsets[-1] > size:
        raise ValueError('Invalid sharing stream bounds')
    lengths = [hi - lo for lo, hi in zip(offsets, offsets[1:] + [size])]
    with ZipFile(PACK, 'x') as out, (data / PIXELS).open('rb') as pixels:
        for name, length in zip(names, lengths, strict=True):
            payload = pixels.read(length)
            if len(payload) != length:
                raise ValueError(f'Truncated frame stream: {name}')
            sharing.put(out, name, payload)
        for name in literals:
            sharing.put(out, name, source.read(name))
        for name, filename in EXTRA.items():
            out.write(data / filename, name, compress_type=ZIP_STORED)

    # The worker compared every decoded canvas against its original file.
    # Compare every delivered ZIP member against those exact verified inputs.
    with ZipFile(PACK) as restored, (data / PIXELS).open('rb') as pixels:
        if restored.namelist() != names + literals + list(EXTRA):
            raise ValueError('Unexpected archive members')
        for name, length in zip(names, lengths, strict=True):
            if restored.read(name) != pixels.read(length):
                raise ValueError(f'Archived frame stream differs: {name}')
        for name in literals:
            if restored.read(name) != source.read(name):
                raise ValueError(f'Archived index or metadata differs: {name}')
        for name, filename in EXTRA.items():
            with restored.open(name) as packed:
                if hashlib.file_digest(packed, 'sha256').hexdigest() != sharing.file_sha(data / filename):
                    raise ValueError(f'Archived dictionary or index differs: {name}')


def main():
    proof = json.loads((BASE_PATH.parent / 'results.json').read_bytes())
    if sharing.file_sha(base.PACK) != proof['tiled_zip_sha256']:
        raise ValueError('Verified baseline archive SHA-256 differs')
    WORK.mkdir(parents=True, exist_ok=False)
    data = WORK / 'data'
    data.mkdir()
    counts = WORK / 'counts.txt'
    with ZipFile(base.PACK) as source:
        mapping, groups = original_catalog(source)
        if len(groups) != proof['physical_frames_byte_exact']:
            raise ValueError('Unexpected canonical frame count')
        bitmap, tile_hash = plan(source, groups, proof['original_frames_path_and_bytes_verified'])
        verify_originals(groups)
        worker = RUN / 'build/Release/effect_tile_sharing.exe'
        subprocess.run([worker, 'build', ROOT, bitmap, WORK, data, counts, '--area'], check=True)
        print('Archivage et vérification des octets du pack livré', flush=True)
        write_and_check_archive(source, mapping, groups, data, tile_hash)
    visits, unique, references, original_bytes = map(int, counts.read_text().split())
    index_usage = {name: (data / p).stat().st_size for name, p in EXTRA.items()}
    dict_bytes = index_usage['area-animation-tile-dictionary.rgba']
    raw_savings = proof['tiled_rgba_bytes'] - (data / PIXELS).stat().st_size - dict_bytes
    if original_bytes - dict_bytes - 4*references != raw_savings:
        raise ValueError('Dictionary totals disagree with emitted pixel sizes')
    before, after = base.PACK.stat().st_size, PACK.stat().st_size
    result = {
        'frames_original_paths_and_bytes_verified': len(mapping['frames']),
        'unique_frames_verified': len(groups),
        'original_metadata_files_preserved': len(mapping['metadata']),
        'already_tiled_frames': sum(n for mode, n in proof['modes'].items() if mode != 'dense'),
        'dense_frames': proof['modes']['dense'],
        'occupied_tile_occurrences': visits,
        'dictionary_tiles': unique,
        'dictionary_references': references,
        'dictionary_bytes': dict_bytes,
        'additional_index_bytes': index_usage['area-animation-tile-sharing.index'],
        'payload_savings_including_dictionary_bytes': raw_savings,
        'tiled_zip_bytes': before,
        'shared_tiles_zip_bytes': after,
        'net_savings_bytes': before - after,
        'net_savings_pct': round(100 * (before-after)/before, 4),
        'shared_tiles_zip_sha256': sharing.file_sha(PACK),
    }
    report = json.dumps(result, indent=2) + '\n'
    (HERE / 'results.json').write_text(report, encoding='utf-8', newline='\n')
    for name in (PIXELS, *EXTRA.values()):
        (data / name).unlink()
    data.rmdir()
    print(report, end='')


if __name__ == '__main__':
    main()
