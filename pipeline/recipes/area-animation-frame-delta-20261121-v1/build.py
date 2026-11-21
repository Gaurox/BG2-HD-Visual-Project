"""Compare direct-access frame deltas with the tiled area-animation archive."""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import statistics
import struct
from time import perf_counter_ns
from zipfile import ZipFile

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'area-animation-tiles-20261121-v1/build.py'
spec = importlib.util.spec_from_file_location('area_animation_tiles', BASE)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
sharing = base.sharing
PILOT = ('AR3017', 'OH8100', 'AR0516')
DELTA = 'area-animation-frame-delta.index'
DELTA_RECORD = struct.Struct('<IIB')
EDGES = (1, 2, 4, 8)
WINDOW = 6


def grid(width, height, edge):
    return (width+edge-1)//edge, (height+edge-1)//edge


def encode_delta(target, anchor):
    changed = target != anchor
    h, w = changed.shape
    best = None
    best_bytes = target.nbytes
    for edge in EDGES:
        nx, ny = grid(w, h, edge)
        if edge > 1:
            changed = np.logical_or.reduceat(changed, np.arange(0, changed.shape[0], 2), axis=0)
            changed = np.logical_or.reduceat(changed, np.arange(0, changed.shape[1], 2), axis=1)
        columns = np.minimum(edge, w - edge*np.arange(nx))
        rows = np.minimum(edge, h - edge*np.arange(ny))
        count = int((rows @ changed @ columns))
        cost = (nx*ny+7)//8 + count*4
        if cost < best_bytes:
            best_bytes = cost
            best = (edge, changed)
    if best is None:
        return None
    edge, changed = best
    flags = np.packbits(changed, bitorder='little').tobytes()
    occupied = base.tiles.expand_tiles(changed, h, w, edge)
    return edge, flags + target[occupied].tobytes()


class Archive:
    def __init__(self, path):
        self.zip = ZipFile(path)
        self.shared = self.zip.read(sharing.INDEX)
        self.mapping = json.loads(self.shared)
        self.digests = sorted(set(self.mapping['frames'].values()))
        crop = self.zip.read(base.CROP_INDEX)
        self.tiles = self.zip.read(base.TILE_INDEX)
        count = len(self.digests)
        if (base.HEADER.unpack_from(crop) != (b'AAX4CRP1', count, hashlib.sha256(self.shared).digest())
                or base.HEADER.unpack_from(self.tiles) != (b'AAX4TIL1', count, hashlib.sha256(crop).digest())):
            raise ValueError('Index binding mismatch')
        cursor = base.HEADER.size + count
        self.records = {}
        self.deltas = {}
        for i, (digest, shape) in enumerate(zip(
                self.digests, base.GEOMETRY.iter_unpack(crop[base.HEADER.size:]), strict=True)):
            edge = self.tiles[base.HEADER.size+i]
            nx, ny = grid(shape[-2], shape[-1], edge) if edge else (0, 0)
            size = (nx*ny+7)//8
            self.records[digest] = (shape, edge, self.tiles[cursor:cursor+size])
            cursor += size
        if cursor != len(self.tiles):
            raise ValueError('Tile index length mismatch')
        if DELTA in self.zip.namelist():
            index = self.zip.read(DELTA)
            signature, delta_count, binding = base.HEADER.unpack_from(index)
            if signature != b'AAX4DLT1' or binding != hashlib.sha256(self.tiles).digest():
                raise ValueError('Delta index binding mismatch')
            for dest, key, edge in DELTA_RECORD.iter_unpack(index[base.HEADER.size:]):
                digest, anchor = self.digests[dest], self.digests[key]
                if edge not in EDGES or digest in self.deltas or dest == key:
                    raise ValueError('Invalid delta record')
                self.deltas[digest] = (anchor, edge)
            if len(self.deltas) != delta_count or any(key in self.deltas for key, _ in self.deltas.values()):
                raise ValueError('Delta count or reference depth mismatch')

    def frame(self, digest):
        shape, tiled_edge, mask = self.records[digest]
        payload = self.zip.read(sharing.blob_name(digest))
        if digest not in self.deltas:
            return base.tiles.decode_frame(payload, mask, (0, *shape, 0), tiled_edge)
        anchor, edge = self.deltas[digest]
        w, h = shape[:2]
        nx, ny = grid(w, h, edge)
        bits = nx*ny
        flag_bytes = (bits+7)//8
        flags = np.unpackbits(np.frombuffer(payload, dtype='u1', count=flag_bytes), bitorder='little')
        if flags[bits:].any():
            raise ValueError('Nonzero delta padding')
        canvas = np.frombuffer(self.frame(anchor), dtype='<u4').reshape(h, w).copy()
        changed = base.tiles.expand_tiles(flags[:bits].reshape(ny, nx), h, w, edge)
        canvas[changed] = np.frombuffer(payload, dtype='<u4', offset=flag_bytes)
        return canvas.tobytes()

    def payload_bytes(self, digest):
        size = self.zip.getinfo(sharing.blob_name(digest)).file_size
        if digest in self.deltas:
            size += self.payload_bytes(self.deltas[digest][0])
        return size


def survey(source, zones, groups, staging):
    deltas, locked = {}, set()

    @lru_cache(maxsize=WINDOW+1)
    def original(digest):
        w, h = source.records[digest][0][:2]
        raw = sharing.source_bytes(groups[digest][0])
        if sharing.sha(raw) != digest:
            raise ValueError(f'Original source differs: {digest}')
        return np.frombuffer(raw, dtype='<u4').reshape(h, w)

    for area in zones:
        manifest = json.loads(source.zip.read(f'iee-assets/areas/{area}/manifest.json'))
        for resource in manifest['resources']:
            names = [source.mapping['frames'][f'iee-assets/areas/{area}/{f["asset"]}']
                     for f in resource['frames']]
            for cycle in resource['cycles']:
                keys = []
                order = cycle['timeline_frame_indices'] or cycle['native_frame_indices']
                for position, digest in enumerate(dict.fromkeys(names[i] for i in order)):
                    if position % WINDOW == 0:
                        keys.clear()
                    shape, tiled_edge, _ = source.records[digest]
                    if tiled_edge or digest in deltas:
                        continue
                    best = None
                    best_size = source.zip.getinfo(sharing.blob_name(digest)).file_size
                    if digest not in locked:
                        for key in keys:
                            if key == digest or source.records[key][0][:2] != shape[:2]:
                                continue
                            encoded = encode_delta(original(digest), original(key))
                            if encoded and len(encoded[1]) + DELTA_RECORD.size < best_size:
                                best = (key, *encoded)
                                best_size = len(encoded[1]) + DELTA_RECORD.size
                    if best:
                        key, edge, payload = best
                        locked.add(key)
                        deltas[digest] = (key, edge)
                        (staging / digest).write_bytes(payload)
                    else:
                        keys.append(digest)
        print(f'{area} traité, {len(deltas)} deltas retenus au total', flush=True)
    return deltas


def write_archives(source, paths, metadata, staging, run, deltas):
    digests = sorted(set(paths.values()))
    common = json.dumps({**source.mapping, 'frames': paths, 'metadata': metadata},
                        separators=(',', ':'), sort_keys=True).encode()
    crop = base.HEADER.pack(b'AAX4CRP1', len(digests), hashlib.sha256(common).digest())
    crop += b''.join(base.GEOMETRY.pack(*source.records[digest][0]) for digest in digests)
    tiles = base.HEADER.pack(b'AAX4TIL1', len(digests), hashlib.sha256(crop).digest())
    tiles += bytes(source.records[digest][1] for digest in digests)
    tiles += b''.join(source.records[digest][2] for digest in digests)
    ids = {digest: i for i, digest in enumerate(digests)}
    index = base.HEADER.pack(b'AAX4DLT1', len(deltas), hashlib.sha256(tiles).digest())
    index += b''.join(DELTA_RECORD.pack(ids[digest], ids[key], edge)
                      for digest, (key, edge) in sorted(deltas.items()))
    baseline, candidate = run / 'baseline.zip', run / 'area-animations-delta-test.zip'
    with ZipFile(baseline, 'x') as old, ZipFile(candidate, 'x') as new:
        for archive in (old, new):
            for name in metadata:
                sharing.put(archive, name, source.zip.read(name))
            for name, data in ((sharing.INDEX, common), (base.CROP_INDEX, crop), (base.TILE_INDEX, tiles)):
                sharing.put(archive, name, data)
        for digest in digests:
            name = sharing.blob_name(digest)
            payload = source.zip.read(name)
            sharing.put(old, name, payload)
            sharing.put(new, name, (staging/digest).read_bytes() if digest in deltas else payload)
        sharing.put(new, DELTA, index)
    return baseline, candidate, len(index)


def verify_and_measure(before, after, groups, metadata):
    old, new = Archive(before), Archive(after)
    for row in metadata:
        name = row['destination']
        ref = sharing.source_bytes(row)
        if old.zip.read(name) != ref or new.zip.read(name) != ref:
            raise ValueError(f'Metadata differs: {name}')
    verified = 0
    for digest, originals in groups.items():
        frame = new.frame(digest)
        for original in originals:
            if frame != sharing.source_bytes(original):
                raise ValueError(f'Frame differs: {original["destination"]}')
            verified += 1
    print(f'{verified} frames vérifiées octet pour octet', flush=True)
    targets = list(new.deltas)
    metrics = {}
    if targets:
        before_times, after_times = [], []
        rng = random.Random(1320)
        # Alternate reader order on the same random seeks. Each decode starts with
        # an empty frame cache; file data can be cached by the operating system.
        for sample in range(3):
            rng.shuffle(targets)
            for i, digest in enumerate(targets):
                work = [(old, before_times), (new, after_times)]
                if (i+sample)%2:
                    work.reverse()
                for reader, target in work:
                    start = perf_counter_ns()
                    reader.frame(digest)
                    target.append((perf_counter_ns()-start)/1000)
        def summarize(times, archive):
            return {'median_us': round(statistics.median(times), 1),
                    'p95_us': round(float(np.percentile(times, 95)), 1),
                    'mean_payload_bytes': round(statistics.mean(archive.payload_bytes(d) for d in targets)),
                    'max_payload_bytes': max(archive.payload_bytes(d) for d in targets)}
        metrics = {'requests_per_archive': len(before_times), 'baseline': summarize(before_times, old),
                   'delta': summarize(after_times, new)}
    old.zip.close()
    new.zip.close()
    return verified, metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='Extend the experiment to every zone.')
    args = parser.parse_args()
    proof = json.loads((BASE.parent / 'results.json').read_bytes())
    if sharing.file_sha(base.PACK) != proof['tiled_zip_sha256']:
        raise ValueError('Verified baseline archive differs')
    source = Archive(base.PACK)
    zones = sorted({Path(name).parent.name for name in source.mapping['metadata']}) if args.all else PILOT
    run = HERE / 'run' / ('all' if args.all else 'pilot')
    staging = run / 'deltas'
    staging.mkdir(parents=True, exist_ok=False)
    paths = {name: digest for name, digest in source.mapping['frames'].items()
             if Path(name).parent.name in zones}
    metadata = [name for name in source.mapping['metadata'] if Path(name).parent.name in zones]
    original_rows = {row['destination']: row for row in json.loads(sharing.CONTENT.read_bytes())['entries']
                     if row['kind'] == 'area-animation'}
    groups = defaultdict(list)
    for name, digest in paths.items():
        if original_rows[name]['sha256'].lower() != digest:
            raise ValueError(f'Original catalog differs: {name}')
        groups[digest].append(original_rows[name])
    deltas = survey(source, zones, groups, staging)
    before, after, index_size = write_archives(source, paths, metadata, staging, run, deltas)
    verified, metrics = verify_and_measure(before, after, groups, [original_rows[name] for name in metadata])
    sizes = {area: sum(source.zip.getinfo(sharing.blob_name(d)).file_size -
                       (staging/d).stat().st_size - DELTA_RECORD.size
                       for d in {digest for name, digest in paths.items() if Path(name).parent.name == area}
                       if d in deltas) for area in zones}
    old_bytes, new_bytes = before.stat().st_size, after.stat().st_size
    result = {'zones': zones, 'verified_logical_frames': verified, 'verified_unique_frames': len(groups),
              'dense_unique_frames': sum(not source.records[d][1] for d in groups),
              'delta_frames': len(deltas), 'reference_depth': 1 if deltas else 0,
              'delta_index_bytes': index_size, 'delta_bytes_saved_by_zone_before_zip_overhead': sizes,
              'baseline_zip_bytes': old_bytes, 'candidate_zip_bytes': new_bytes,
              'net_savings_bytes': old_bytes-new_bytes,
              'net_savings_pct': round(100*(old_bytes-new_bytes)/old_bytes, 4),
              'candidate_sha256': sharing.file_sha(after), 'random_direct_reads': metrics}
    report = json.dumps(result, indent=2) + '\n'
    (run/'results.json').write_text(report, encoding='utf-8')
    for digest in deltas:
        (staging/digest).unlink()
    staging.rmdir()
    source.zip.close()
    print(report, end='')


if __name__ == '__main__':
    main()
