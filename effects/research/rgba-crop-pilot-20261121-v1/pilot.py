"""Store raw RGBA rectangles and verify every reconstructed frame."""
import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RELEASE = ROOT / 'releases/BG2-HD-Upscale'
ARCHIVE = (RELEASE / 'dist-local/alpha10-ui-20261121-v1'
           / 'BG2HD-0.1.0-alpha.10-windows-local-alpha.zip')
PACK = HERE / 'pack'
SCOPE = frozenset({'SPRDRABU', 'Y31N058', 'Y31N059', 'Y31P059', 'BDFORCEW'})

sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from effect_storage import read_map

MAGIC = b'IEECROP1'
HEADER = struct.Struct('<8sII32s32s')
FRAME = struct.Struct('<I6HQ')
LINK = struct.Struct('<II')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_selection():
    with ZipFile(ARCHIVE) as archive:
        content = json.loads(archive.read('bg2hd/manifests/content.json'))['entries']
    packaged = {
        Path(entry['destination']).name: entry for entry in content
        if entry['destination'].startswith('iee-assets/effects/')
    }
    manifest_path = ROOT / packaged['manifest.json']['source']
    manifest_data = manifest_path.read_bytes()
    if hashlib.sha256(manifest_data).hexdigest() != packaged['manifest.json']['sha256'].lower():
        raise ValueError('Effect manifest differs from the archive')
    manifest = json.loads(manifest_data)
    registry = (manifest_path.parent / manifest['registry']).read_bytes()
    registry_hash = hashlib.sha256(registry).digest()
    storage_hash = bytes.fromhex(manifest['storage']['sha256'])
    if registry_hash.hex() != packaged[manifest['registry']]['sha256'].lower():
        raise ValueError('Registry differs from the archive')
    if storage_hash.hex() != packaged[manifest['storage']['index']]['sha256'].lower():
        raise ValueError('Storage map differs from the archive')
    ids = read_map(manifest_path.parent, manifest, registry)
    frames = manifest['frames']
    aliases = {i: ids[i] for i, frame in enumerate(frames) if frame['resref'] in SCOPE}
    if {frames[i]['resref'] for i in aliases} != SCOPE:
        raise ValueError('Incomplete effect selection')
    physical = {i: packaged[frames[i]['asset']] for i in sorted(set(aliases.values()))}
    for i, entry in physical.items():
        frame = frames[i]
        if (entry['sha256'].upper(), entry['bytes']) != (frame['sha256'].upper(), frame['bytes']):
            raise ValueError(f'Frame inventory differs from the archive: {frame["asset"]}')
    return frames, aliases, physical, registry_hash, storage_hash


def build(selection):
    frames, aliases, physical, registry_hash, storage_hash = selection
    PACK.mkdir()
    with (PACK / 'frames.index').open('xb') as index, (PACK / 'pixels.rgba').open('xb') as pixels:
        index.write(HEADER.pack(MAGIC, len(physical), len(aliases), registry_hash, storage_hash))
        for i, entry in physical.items():
            native = (ROOT / entry['source']).read_bytes()
            width, height = frames[i]['physical_size_x4']
            image = np.frombuffer(native, dtype='<u4').reshape(height, width)
            occupied = image != 0
            ys = np.flatnonzero(occupied.any(axis=1))
            xs = np.flatnonzero(occupied.any(axis=0))
            if len(ys):
                x, y = int(xs[0]), int(ys[0])
                w, h = int(xs[-1]) + 1 - x, int(ys[-1]) + 1 - y
            else:
                x = y = w = h = 0
            index.write(FRAME.pack(i, width, height, x, y, w, h, pixels.tell()))
            pixels.write(image[y:y + h, x:x + w].tobytes())
        for logical, canonical in aliases.items():
            index.write(LINK.pack(logical, canonical))


def verify(selection):
    frames, aliases, physical, registry_hash, storage_hash = selection
    index_path = PACK / 'frames.index'
    pixels_path = PACK / 'pixels.rgba'
    raw_index = index_path.read_bytes()
    binding = (MAGIC, len(physical), len(aliases), registry_hash, storage_hash)
    records_end = HEADER.size + FRAME.size * len(physical)
    if (len(raw_index) != records_end + LINK.size * len(aliases)
            or HEADER.unpack_from(raw_index) != binding):
        raise ValueError('Invalid pilot index size or binding')
    if list(LINK.iter_unpack(raw_index[records_end:])) != list(aliases.items()):
        raise ValueError('Logical frame mapping differs')

    original_by_effect = Counter()
    cropped_by_effect = Counter()
    changed_by_effect = Counter()
    checked = {}
    with pixels_path.open('rb') as pixels:
        entries = FRAME.iter_unpack(raw_index[HEADER.size:records_end])
        for expected, (i, width, height, x, y, w, h, offset) in zip(physical, entries, strict=True):
            if (i != expected or [width, height] != frames[i]['physical_size_x4']
                    or offset != pixels.tell() or x + w > width or y + h > height
                    or (not w or not h) and (x or y or w or h)):
                raise ValueError(f'Invalid geometry or position for frame {expected}')
            stored_bytes = w * h * 4
            stored = pixels.read(stored_bytes)
            if len(stored) != stored_bytes:
                raise ValueError(f'Truncated pixel data for frame {i}')
            frame = np.zeros((height, width, 4), dtype=np.uint8)
            frame[y:y + h, x:x + w] = np.frombuffer(stored, dtype=np.uint8).reshape(h, w, 4)
            reconstructed = frame.tobytes()
            reference = (ROOT / physical[i]['source']).read_bytes()
            sha = hashlib.sha256(reference).hexdigest().upper()
            if reconstructed != reference or sha != physical[i]['sha256'].upper():
                raise ValueError(f'Byte mismatch for {frames[i]["asset"]}')
            checked[i] = sha
            effect = frames[i]['resref']
            original_by_effect[effect] += len(reference)
            cropped_by_effect[effect] += stored_bytes
            changed_by_effect[effect] += stored_bytes < len(reference)
        if pixels.read(1):
            raise ValueError('Trailing pixel data')
    for logical, canonical in aliases.items():
        if frames[logical]['sha256'].upper() != checked[canonical]:
            raise ValueError(f'Logical frame differs after reconstruction: {logical}')

    original = sum(original_by_effect.values())
    cropped = pixels_path.stat().st_size
    metadata = index_path.stat().st_size
    return {
        'archive': ARCHIVE.relative_to(ROOT).as_posix(),
        'resources': sorted(SCOPE),
        'physical_frames_byte_exact': len(checked),
        'logical_frames_verified': len(aliases),
        'existing_shared_references': len(aliases) - len(physical),
        'original_rgba_bytes': original,
        'cropped_rgba_bytes': cropped,
        'runtime_index_bytes': metadata,
        'pilot_bytes': cropped + metadata,
        'net_savings_bytes': original - cropped - metadata,
        'net_savings_pct': round(100 * (original - cropped - metadata) / original, 4),
        'files': {path.name: {'bytes': path.stat().st_size, 'sha256': digest(path)}
                  for path in (index_path, pixels_path)},
        'resources_by_physical_owner': {
            effect: {'original_bytes': original_by_effect[effect], 'cropped_bytes': cropped_by_effect[effect],
                     'cropped_frames': changed_by_effect[effect]}
            for effect in sorted(original_by_effect)
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['build', 'verify'])
    args = parser.parse_args()
    selection = load_selection()
    if args.action == 'build':
        build(selection)
    print(json.dumps(verify(selection), indent=2))


if __name__ == '__main__':
    main()
