"""Build and verify a local ZIP of shared, byte-identical area animation RGBA frames."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZIP_STORED, ZipFile, ZipInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTENT = ROOT / 'releases/BG2-HD-Upscale/manifests/content.json'
PACK = HERE / 'run/area-animations-shared-test.zip'
INDEX = 'area-animation-frames.json'
BASE = r'iee-assets/areas/(?:AR|OH)[0-9]{4}/'
FRAME = re.compile(BASE + r'AAX4-[A-Z0-9_]{1,8}(?:-v[0-9]+)?-frame[0-9]{3,4}\.rgba', re.ASCII)
METADATA = re.compile(BASE + r'(?:AreaAnimations-X4\.registry|manifest\.json)', re.ASCII)
DIGEST = re.compile('[0-9a-f]{64}', re.ASCII)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def blob_name(digest):
    if not DIGEST.fullmatch(digest):
        raise ValueError(f'Invalid SHA-256: {digest}')
    return f'frames/{digest}.rgba'


def put(archive, name, data):
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_STORED
    archive.writestr(entry, data)


def source_bytes(row):
    path = (ROOT / row['source']).resolve(strict=True)
    if not path.is_relative_to(ROOT):
        raise ValueError(f'Source outside workspace: {path}')
    return path.read_bytes()


def validate(row, data):
    if len(data) != row['bytes'] or sha(data) != row['sha256'].lower():
        raise ValueError(f"Source differs from manifest: {row['source']}")


def compare_group(group):
    rows = group[1]
    data = source_bytes(rows[0])
    validate(rows[0], data)
    for row in rows[1:]:
        if source_bytes(row) != data:
            raise ValueError(f"Original RGBA does not match its group: {row['source']}")
    return data


def write_original_path(destination, name, data):
    path = destination / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def restore(pack, destination):
    with ZipFile(pack) as archive:
        index = json.loads(archive.read(INDEX))
        if index['format'] != 'shared-area-animation-frames-v1':
            raise ValueError('Unexpected test format')
        groups = defaultdict(list)
        for name, digest in index['frames'].items():
            if not FRAME.fullmatch(name):
                raise ValueError(f'Invalid frame path: {name}')
            groups[digest].append(name)
        metadata = index['metadata']
        if not all(METADATA.fullmatch(name) for name in metadata):
            raise ValueError('Invalid registry or manifest path')
        names = [*index['frames'], *metadata]
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError('Destination collision')
        expected = [INDEX, *metadata, *(blob_name(key) for key in groups)]
        if sorted(archive.namelist()) != sorted(expected):
            raise ValueError('Archive inventory mismatch')
        destination.mkdir(parents=True, exist_ok=False)
        for count, (digest, paths) in enumerate(groups.items(), 1):
            data = archive.read(blob_name(digest))
            if sha(data) != digest:
                raise ValueError(f'Changed shared RGBA: {digest}')
            for name in paths:
                write_original_path(destination, name, data)
            if count % 2048 == 0:
                print(f'{count}/{len(groups)} shared frames restored', flush=True)
        for name in metadata:
            write_original_path(destination, name, archive.read(name))
    return len(index['frames']), len(metadata)


def build():
    raw_manifest = CONTENT.read_bytes()
    selection = [r for r in json.loads(raw_manifest)['entries'] if r['kind'] == 'area-animation']
    expected = {r['destination'] for r in selection}
    if not selection or len({name.casefold() for name in expected}) != len(selection):
        raise ValueError('Empty or ambiguous area animation selection')
    frames, metadata = defaultdict(list), []
    for row in selection:
        name = row['destination']
        if FRAME.fullmatch(name):
            digest = row['sha256'].lower()
            blob_name(digest)
            frames[digest].append(row)
        elif METADATA.fullmatch(name):
            metadata.append(row)
        else:
            raise ValueError(f'Unexpected area animation payload: {name}')
    index = json.dumps({
        'format': 'shared-area-animation-frames-v1',
        'frames': {row['destination']: digest for digest, rows in frames.items() for row in rows},
        'metadata': sorted(row['destination'] for row in metadata),
    }, sort_keys=True, separators=(',', ':')).encode('ascii')

    PACK.parent.mkdir(exist_ok=False)
    baseline = PACK.parent / 'baseline.zip'
    groups = sorted(frames.items())
    with ZipFile(baseline, 'x') as direct, ZipFile(PACK, 'x') as shared, ThreadPoolExecutor(max_workers=8) as pool:
        for start in range(0, len(groups), 128):
            batch = groups[start:start+128]
            for (digest, originals), data in zip(batch, pool.map(compare_group, batch), strict=True):
                put(shared, blob_name(digest), data)
                for row in originals:
                    put(direct, row['destination'], data)
            if start % 2048 == 0:
                print(f'{min(start+128,len(groups))}/{len(groups)} shared frames written', flush=True)
        for row in metadata:
            data = source_bytes(row)
            validate(row, data)
            put(direct, row['destination'], data)
            put(shared, row['destination'], data)
        put(shared, INDEX, index)

    restored = PACK.parent / 'restored'
    frame_count, metadata_count = restore(PACK, restored)
    actual = {p.relative_to(restored).as_posix() for p in restored.rglob('*') if p.is_file()}
    if actual != expected or frame_count+metadata_count != len(expected):
        raise ValueError('Restored names differ from the original destinations')

    def compare_restored(row):
        if (restored / row['destination']).read_bytes() != source_bytes(row):
            raise ValueError(f"Restored bytes differ: {row['destination']}")

    with ThreadPoolExecutor(max_workers=10) as pool:
        for count, _ in enumerate(pool.map(compare_restored, selection), 1):
            if count % 4096 == 0:
                print(f'{count}/{len(selection)} paths and original bytes verified', flush=True)

    direct_bytes = baseline.stat().st_size
    archive_bytes = PACK.stat().st_size
    logical_bytes = sum(r['bytes'] for rows in frames.values() for r in rows)
    unique_bytes = sum(rows[0]['bytes'] for rows in frames.values())
    report = {
        'content_manifest_sha256': sha(raw_manifest),
        'zones': len({row['area'] for row in selection}),
        'original_frames_path_and_bytes_verified': frame_count,
        'original_registries_and_manifests_path_and_bytes_verified': metadata_count,
        'physical_frames': len(frames),
        'duplicate_files_removed': frame_count - len(frames),
        'logical_rgba_bytes': logical_bytes,
        'unique_rgba_bytes': unique_bytes,
        'sharing_index_bytes': len(index),
        'storage_savings_index_included_bytes': logical_bytes - unique_bytes - len(index),
        'baseline_zip_bytes': direct_bytes,
        'shared_zip_bytes': archive_bytes,
        'actual_zip_savings_bytes': direct_bytes - archive_bytes,
        'actual_zip_savings_pct': round(100 * (direct_bytes - archive_bytes) / direct_bytes, 4),
        'shared_zip_sha256': file_sha(PACK),
    }
    result = json.dumps(report, indent=2) + '\n'
    (HERE / 'results.json').write_text(result, encoding='utf-8', newline='\n')
    for name in actual:
        (restored / name).unlink()
    for zone in (restored / 'iee-assets/areas').iterdir():
        zone.rmdir()
    (restored / 'iee-assets/areas').rmdir()
    (restored / 'iee-assets').rmdir()
    restored.rmdir()
    baseline.unlink()
    print(result, end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'restore'))
    parser.add_argument('destination', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'build' and args.destination is None:
        build()
    elif args.action == 'restore' and args.destination is not None:
        frames, metadata = restore(PACK, args.destination)
        print(f'{frames} frames et {metadata} fichiers de métadonnées restaurés.')
    else:
        parser.error('restore requires a new destination directory')
