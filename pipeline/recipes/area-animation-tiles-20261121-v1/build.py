"""Crop and tile the unique RGBA frames in the local area animation test archive."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
from pathlib import Path
import struct
from zipfile import ZipFile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load_script(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sharing = load_script('area_animation_sharing', HERE.parent / 'area-animation-sharing-20261121-v1/build.py')
tiles = load_script('effect_tile_encoder', ROOT / 'effects/research/rgba-tiles-20261121-v1/build.py')
RUN = HERE / 'run'
PACK = RUN / 'area-animations-tiled-test.zip'
CROP_INDEX = 'area-animation-crop.index'
TILE_INDEX = 'area-animation-tiles.index'
HEADER = struct.Struct('<8sI32s')
GEOMETRY = struct.Struct('<6I')


def inventory(selection):
    manifests = {}
    geometry = {}
    paths = {}
    for row in selection:
        name, digest = row['destination'], row['sha256'].lower()
        if not sharing.FRAME.fullmatch(name):
            continue
        path = ROOT / row['source']
        if path.parent not in manifests:
            manifest = json.loads((path.parent / 'manifest.json').read_bytes())
            manifests[path.parent] = {f['asset']: f for r in manifest['resources'] for f in r['frames']}
        frame = manifests[path.parent][path.name]
        dims = tuple(frame['physical_size_x4'])
        if frame['sha256'].lower() != digest or dims[0]*dims[1]*4 != row['bytes']:
            raise ValueError(f'Original dimensions or hash differ: {name}')
        if geometry.setdefault(digest, dims) != dims:
            raise ValueError(f'Inconsistent geometry for a shared frame: {name}')
        paths[name] = digest
    return geometry, paths


def encode(item):
    digest, raw, (width, height) = item
    if len(raw) != width*height*4 or sharing.sha(raw) != digest:
        raise ValueError(f'Unexpected deduplicated RGBA data: {digest}')
    image = np.frombuffer(raw, dtype='<u4').reshape(height, width)
    nonzero = image != 0
    yy = np.flatnonzero(nonzero.any(axis=1))
    xx = np.flatnonzero(nonzero.any(axis=0))
    if yy.size:
        x, y = int(xx[0]), int(yy[0])
        w, h = int(xx[-1])+1-x, int(yy[-1])+1-y
        pixels = image[y:y+h, x:x+w].tobytes()
    else:
        x = y = w = h = 0
        pixels = b''
    row = (width, height, x, y, w, h)
    edge, bitmap, packed = tiles.encode_frame((pixels, h, w))
    return row, pixels, edge, bitmap, packed


def write_archives(source, shared_index, index, dimensions, digests, cropped_path):
    geometry = bytearray()
    modes = bytearray()
    bitmaps = bytearray()
    counts = Counter()
    crop_bytes = tile_bytes = 0
    with ZipFile(cropped_path, 'x') as crop_zip, ZipFile(PACK, 'x') as tile_zip, ThreadPoolExecutor(max_workers=8) as pool:
        for start in range(0, len(digests), 48):
            names = digests[start:start+48]
            batch = [(digest, source.read(sharing.blob_name(digest)), dimensions[digest]) for digest in names]
            for digest, (row, cropped, edge, bitmap, packed) in zip(names, pool.map(encode, batch), strict=True):
                geometry.extend(GEOMETRY.pack(*row))
                modes.append(edge)
                bitmaps.extend(bitmap)
                counts[str(edge) if edge else 'dense'] += 1
                name = sharing.blob_name(digest)
                sharing.put(crop_zip, name, cropped)
                sharing.put(tile_zip, name, packed)
                crop_bytes += len(cropped)
                tile_bytes += len(packed)
            if start % 2016 == 0:
                print(f'{min(start+48,len(digests))}/{len(digests)} frames rognées et tuilées', flush=True)
        for name in index['metadata']:
            raw = source.read(name)
            sharing.put(crop_zip, name, raw)
            sharing.put(tile_zip, name, raw)
        crop_data = HEADER.pack(b'AAX4CRP1', len(digests), tiles.crop.sha(shared_index)) + bytes(geometry)
        tile_data = HEADER.pack(b'AAX4TIL1', len(digests), tiles.crop.sha(crop_data)) + bytes(modes) + bytes(bitmaps)
        for archive in (crop_zip, tile_zip):
            sharing.put(archive, sharing.INDEX, shared_index)
            sharing.put(archive, CROP_INDEX, crop_data)
        sharing.put(tile_zip, TILE_INDEX, tile_data)
    return crop_bytes, tile_bytes, len(crop_data), len(tile_data), dict(counts)


def restore(pack, destination):
    with ZipFile(pack) as archive:
        shared_raw = archive.read(sharing.INDEX)
        original = json.loads(shared_raw)
        if original['format'] != 'shared-area-animation-frames-v1':
            raise ValueError('Unexpected frame mapping format')
        groups = defaultdict(list)
        for name, digest in original['frames'].items():
            if not sharing.FRAME.fullmatch(name):
                raise ValueError(f'Invalid frame path: {name}')
            groups[digest].append(name)
        digests = sorted(groups)
        meta = original['metadata']
        if not all(sharing.METADATA.fullmatch(name) for name in meta):
            raise ValueError('Invalid registry or manifest name')
        expected = [sharing.INDEX, CROP_INDEX, TILE_INDEX, *meta, *(sharing.blob_name(d) for d in digests)]
        if sorted(archive.namelist()) != sorted(expected):
            raise ValueError('Invalid tiled archive inventory')
        count = len(digests)
        crop_data, tile_data = archive.read(CROP_INDEX), archive.read(TILE_INDEX)
        if (len(crop_data) != HEADER.size + GEOMETRY.size*count
                or HEADER.unpack_from(crop_data) != (b'AAX4CRP1', count, tiles.crop.sha(shared_raw))
                or len(tile_data) < HEADER.size+count
                or HEADER.unpack_from(tile_data) != (b'AAX4TIL1', count, tiles.crop.sha(crop_data))):
            raise ValueError('Crop or tile index binding differs')
        cursor = HEADER.size+count
        destination.mkdir(parents=True, exist_ok=False)
        rows = GEOMETRY.iter_unpack(crop_data[HEADER.size:])
        edges = tile_data[HEADER.size:cursor]
        for i, (digest, row, edge) in enumerate(zip(digests, rows, edges, strict=True)):
            width, height, x, y, w, h = row
            if (not width or not height or x+w > width or y+h > height
                    or ((not w or not h) and (x or y or w or h or edge)) or edge not in (0, *tiles.EDGES)):
                raise ValueError(f'Unexpected tiled frame geometry: {digest}')
            mask_size = (((w+edge-1)//edge)*((h+edge-1)//edge)+7)//8 if edge else 0
            if cursor+mask_size > len(tile_data):
                raise ValueError('Truncated tile bitmap')
            mask = tile_data[cursor:cursor+mask_size]
            cursor += mask_size
            pixels = archive.read(sharing.blob_name(digest))
            raw = tiles.decode_frame(pixels, mask, (i, *row, 0), edge)
            if sharing.sha(raw) != digest:
                raise ValueError(f'Canvas reconstruction changed: {digest}')
            for name in groups[digest]:
                sharing.write_original_path(destination, name, raw)
            if (i+1) % 2048 == 0:
                print(f'{i+1}/{count} canevas restitués', flush=True)
        if cursor != len(tile_data):
            raise ValueError('Unexpected trailing tile masks')
        for name in meta:
            sharing.write_original_path(destination, name, archive.read(name))


def build():
    proof = json.loads((Path(sharing.__file__).parent / 'results.json').read_bytes())
    manifest = sharing.CONTENT.read_bytes()
    if sharing.sha(manifest) != proof['content_manifest_sha256'] or sharing.file_sha(sharing.PACK) != proof['shared_zip_sha256']:
        raise ValueError('The verified deduplicated baseline has changed')
    selection = [r for r in json.loads(manifest)['entries'] if r['kind'] == 'area-animation']
    dimensions, paths = inventory(selection)
    RUN.mkdir(exist_ok=False)
    cropped = RUN / 'area-animations-cropped-intermediate.zip'
    with ZipFile(sharing.PACK) as baseline:
        shared_raw = baseline.read(sharing.INDEX)
        index = json.loads(shared_raw)
        if (index['frames'] != paths or len(dimensions) != proof['physical_frames']
                or sorted(index['metadata']) != sorted(r['destination'] for r in selection if r['destination'] not in paths)):
            raise ValueError('Original catalog and shared archive differ')
        crop_data, tile_data, crop_index, tile_index, modes = write_archives(
            baseline, shared_raw, index, dimensions, sorted(dimensions), cropped)

    restored = RUN / 'restored'
    restore(PACK, restored)
    expected = {r['destination'] for r in selection}
    actual = {p.relative_to(restored).as_posix() for p in restored.rglob('*') if p.is_file()}
    if actual != expected:
        raise ValueError('Restored original paths differ')

    def compare(row):
        if (restored/row['destination']).read_bytes() != sharing.source_bytes(row):
            raise ValueError(f"Restored bytes differ: {row['destination']}")

    with ThreadPoolExecutor(max_workers=10) as pool:
        for count, _ in enumerate(pool.map(compare, selection), 1):
            if count % 4096 == 0:
                print(f'{count}/{len(selection)} fichiers comparés à leurs originaux', flush=True)
    baseline_bytes = sharing.PACK.stat().st_size
    cropped_bytes, packed_bytes = cropped.stat().st_size, PACK.stat().st_size
    result = dict(
        original_frames_path_and_bytes_verified=len(paths), physical_frames_byte_exact=len(dimensions),
        original_registries_and_manifests_path_and_bytes_verified=len(selection)-len(paths),
        deduplicated_zip_bytes=baseline_bytes, cropped_zip_bytes=cropped_bytes, tiled_zip_bytes=packed_bytes,
        crop_index_bytes=crop_index, tile_index_bytes=tile_index, sharing_index_bytes=len(shared_raw),
        cropped_rgba_bytes=crop_data, tiled_rgba_bytes=tile_data, modes=modes,
        crop_zip_savings_bytes=baseline_bytes-cropped_bytes, tiles_additional_zip_savings_bytes=cropped_bytes-packed_bytes,
        additional_zip_savings_bytes=baseline_bytes-packed_bytes,
        additional_zip_savings_pct=round(100*(baseline_bytes-packed_bytes)/baseline_bytes, 4),
        total_savings_vs_original_zip_bytes=proof['baseline_zip_bytes']-packed_bytes,
        tiled_zip_sha256=sharing.file_sha(PACK),
    )
    report = json.dumps(result, indent=2) + '\n'
    (HERE/'results.json').write_text(report, encoding='utf-8', newline='\n')
    for name in actual:
        (restored/name).unlink()
    for zone in (restored/'iee-assets/areas').iterdir():
        zone.rmdir()
    (restored/'iee-assets/areas').rmdir()
    (restored/'iee-assets').rmdir()
    restored.rmdir()
    cropped.unlink()
    print(report, end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'restore'))
    parser.add_argument('destination', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'build' and args.destination is None:
        build()
    elif args.action == 'restore' and args.destination is not None:
        restore(PACK, args.destination)
    else:
        parser.error('restore requires a new destination directory')
