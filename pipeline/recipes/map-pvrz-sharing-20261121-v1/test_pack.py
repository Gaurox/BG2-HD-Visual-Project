"""Package exact map PVRZ duplicates without changing the release or game."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZIP_STORED, ZipFile, ZipInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTENT = ROOT / 'releases/BG2-HD-Upscale/manifests/content.json'
PACK = HERE / 'run/maps-pvrz-shared-test.zip'
INDEX_NAME = 'pvrz-index.json'
SAFE_NAME = re.compile(r'override/[A-Z0-9_]{1,8}\.PVRZ', re.IGNORECASE | re.ASCII)
HASH_NAME = re.compile(r'[0-9a-f]{64}', re.ASCII)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def path_for(root, name):
    if not SAFE_NAME.fullmatch(name):
        raise ValueError(f'Invalid PVRZ destination: {name}')
    return root / name


def blob_name(digest):
    if not HASH_NAME.fullmatch(digest):
        raise ValueError(f'Invalid PVRZ hash: {digest}')
    return f'pages/{digest}.pvrz'


def put(archive, name, data):
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_STORED
    archive.writestr(entry, data)


def restore(pack, destination):
    with ZipFile(pack) as archive:
        index = json.loads(archive.read(INDEX_NAME))
        if index['format'] != 'map-pvrz-shared-test-v1':
            raise ValueError('Unexpected PVRZ test format')
        groups = defaultdict(list)
        names = index['destinations']
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError('PVRZ destination collision')
        for name, digest in names.items():
            groups[digest].append(path_for(destination, name))
        entries = [INDEX_NAME, *(blob_name(digest) for digest in groups)]
        if sorted(archive.namelist()) != sorted(entries):
            raise ValueError('Unexpected shared archive inventory')
        destination.mkdir(parents=True, exist_ok=False)
        (destination / 'override').mkdir()
        for digest, paths in groups.items():
            data = archive.read(blob_name(digest))
            if sha(data) != digest:
                raise ValueError(f'Shared page bytes differed: {digest}')
            for path in paths:
                with path.open('xb') as output:
                    output.write(data)
    return len(names)


def build():
    content = CONTENT.read_bytes()
    rows = [r for r in json.loads(content)['entries'] if r['kind'] == 'map' and
            Path(r['destination']).suffix.lower() == '.pvrz']
    grouped = defaultdict(list)
    for row in rows:
        path_for(ROOT, row['destination'])
        grouped[row['bytes'], row['sha256'].lower()].append(row)
    groups = {key: items for key, items in grouped.items() if len(items) > 1}
    targets = {r['destination']: digest for (_, digest), items in groups.items() for r in items}
    if len(groups) != 249 or len(targets) != 656 or len({p.casefold() for p in targets}) != 656:
        raise ValueError('The PVRZ inventory differs from the measured 249 groups')
    index = json.dumps({'format': 'map-pvrz-shared-test-v1', 'destinations': targets},
                       sort_keys=True, separators=(',', ':')).encode('ascii')
    PACK.parent.mkdir(exist_ok=False)
    baseline = PACK.parent / 'baseline-test.zip'
    restored = PACK.parent / 'restored'
    with ZipFile(baseline, 'x', allowZip64=True) as plain, ZipFile(PACK, 'x', allowZip64=True) as shared:
        for (size, digest), items in sorted(groups.items()):
            page = (ROOT / items[0]['source']).read_bytes()
            if len(page) != size or sha(page) != digest:
                raise ValueError(f"Source changed: {items[0]['source']}")
            put(shared, blob_name(digest), page)
            for item in sorted(items, key=lambda row: row['destination']):
                original = (ROOT / item['source']).read_bytes()
                if original != page:
                    raise ValueError(f"Source differs from its group: {item['source']}")
                put(plain, item['destination'], original)
        put(shared, INDEX_NAME, index)

    restored_count = restore(PACK, restored)
    expected_names = set(targets)
    real_names = {p.relative_to(restored).as_posix() for p in (restored / 'override').iterdir()}
    if restored_count != len(expected_names) or real_names != expected_names:
        raise ValueError('Restored paths differ from the original destinations')
    for items in groups.values():
        for item in items:
            name = item['destination']
            if path_for(restored, name).read_bytes() != (ROOT / item['source']).read_bytes():
                raise ValueError(f'Restored bytes differ from original: {name}')

    baseline_bytes = baseline.stat().st_size
    pack_bytes = PACK.stat().st_size
    result = {
        'manifest_sha256': sha(content),
        'groups': len(groups),
        'verified_original_paths_and_bytes': restored_count,
        'duplicate_files_removed': restored_count - len(groups),
        'logical_pvrz_bytes': sum(size * len(items) for (size, _), items in groups.items()),
        'unique_pvrz_bytes': sum(size for size, _ in groups),
        'index_bytes': len(index),
        'baseline_zip_bytes': baseline_bytes,
        'shared_zip_bytes': pack_bytes,
        'actual_zip_savings_bytes': baseline_bytes - pack_bytes,
        'actual_zip_savings_pct': round(100 * (baseline_bytes - pack_bytes) / baseline_bytes, 4),
        'shared_zip_sha256': file_sha(PACK),
    }
    report = json.dumps(result, indent=2) + '\n'
    (HERE / 'results.json').write_text(report, encoding='utf-8', newline='\n')
    # Keep only the test archive and its receipt. Remove known scratch files individually.
    for name in sorted(expected_names):
        path_for(restored, name).unlink()
    (restored / 'override').rmdir()
    restored.rmdir()
    baseline.unlink()
    print(report, end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'restore'))
    parser.add_argument('destination', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'build' and args.destination is None:
        build()
    elif args.action == 'restore' and args.destination is not None:
        print(f'{restore(PACK, args.destination)} PVRZ restored.')
    else:
        parser.error('restore requires a new destination directory')
