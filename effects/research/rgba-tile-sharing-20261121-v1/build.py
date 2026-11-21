"""Build and verify shared nonzero RGBA tile packs from original frame files."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rgba_tiles', HERE.parent / 'rgba-tiles-20261121-v1/build.py')
tiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tiles)
crop = tiles.crop
SHARED_INDEX = 'EffectSharedTiles-X4.index'
SHARED_PIXELS = 'EffectSharedTiles-X4.bin'
DICTIONARY = 'EffectSharedTiles-X4.dictionary.rgba'


def plan(work, tiled, tiled_proof, known):
    originals, rows, header = known
    index = (tiled / tiles.TILE_INDEX).read_bytes()
    digest = crop.sha(index).hex()
    if digest != tiled_proof['files'][tiles.TILE_INDEX]['sha256'] or not index.startswith(header):
        raise ValueError('The tiled frame index differs from the verified pack')
    pixel_bytes = (tiled / tiles.TILE_PIXELS).stat().st_size
    if pixel_bytes != tiled_proof['files'][tiles.TILE_PIXELS]['bytes']:
        raise ValueError('The tiled baseline length differs from its receipt')
    start = tiles.HEADER.size + tiles.FRAME.size * len(rows)
    records = list(tiles.FRAME.iter_unpack(index[tiles.HEADER.size:start]))
    successors = records[1:] + [(pixel_bytes, len(index) - start, 0)]
    if records[0][:2] != (0, 0):
        raise ValueError('Invalid tile index start')
    with (work / 'plan.txt').open('w', encoding='ascii', newline='\n') as out:
        print(digest, file=out)
        for row, record, successor in zip(rows, records, successors, strict=True):
            i, width, height, x, y, w, h, _ = row
            pixels, flags, edge = record
            pixels_end, flags_end, _ = successor
            if not (0 <= pixels <= pixels_end <= pixel_bytes and 0 <= flags <= flags_end <= len(index) - start
                    and edge in (0, *tiles.EDGES)):
                raise ValueError(f'Invalid tile frame offsets: {i}')
            flags_size = flags_end - flags
            names = [f['asset'] for f in originals[i]]
            print(width, height, x, y, w, h, edge, start + flags, flags_size, *names, file=out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify'))
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    kind = 'live' if args.live else 'release'
    crop_proof = json.loads((Path(crop.__file__).parent / f'results-{kind}.json').read_bytes())['files']
    tiled_dir = Path(tiles.__file__).parent
    tiled_proof = json.loads((tiled_dir / ('results-live.json' if args.live else 'results.json')).read_bytes())
    tiled_pack = tiled_dir / ('pack-live' if args.live else 'pack')
    base = Path(crop.__file__).parent / 'packs/live' if args.live else tiles.BASE
    original = (crop.get_path('bg2ee_game_root') / 'iee-assets/effects-before-crop-20261121-v1'
                if args.live else tiles.ORIGINAL)
    final = HERE / f'pack-{kind}'
    output = final.with_suffix('.partial') if args.action == 'build' else final
    work = HERE / f'work-{kind}'
    if args.action == 'build':
        if final.exists() or output.exists() or work.exists():
            raise FileExistsError(f'The {kind} run already exists')
        work.mkdir()
        output.mkdir()
    known = tiles.load_inputs(base, original, crop_proof)
    plan(work, tiled_pack, tiled_proof, known)
    counts = work / 'counts.txt'
    worker = HERE / 'build-parallel/Release/effect_tile_sharing.exe'
    subprocess.run([worker, args.action, original, tiled_pack, work, output, counts], check=True)
    if args.action == 'verify':
        record = json.loads((HERE / f'results-{kind}.json').read_bytes())
        for name, entry in record['files'].items():
            path = output / name
            if path.stat().st_size != entry['bytes'] or crop.file_hash(path) != entry['sha256']:
                raise ValueError(f'Output changed: {name}')
        return
    for name in (*tiles.METADATA, tiles.TILE_INDEX):
        if name in tiled_proof['files']:
            source = tiled_pack / name
            if crop.file_hash(source) != tiled_proof['files'][name]['sha256']:
                raise ValueError(f'Tile pack metadata differs: {name}')
            shutil.copyfile(source, output / name)
    active_tiles, shared_groups, references, original_bytes = map(int, counts.read_text().split())
    files = {path.name: {'bytes': path.stat().st_size, 'sha256': crop.file_hash(path)}
             for path in output.iterdir() if path.is_file()}
    new_bytes = sum(files[n]['bytes'] for n in (SHARED_INDEX, SHARED_PIXELS, DICTIONARY))
    index_names = (crop.SHARED_INDEX, crop.INDEX, tiles.TILE_INDEX)
    before = sum(tiled_proof['files'][name]['bytes'] for name in (*index_names, tiles.TILE_PIXELS)
                 if name in tiled_proof['files'])
    after = sum(files[name]['bytes'] for name in index_names if name in files) + new_bytes
    if original_bytes - files[DICTIONARY]['bytes'] - 4*references != (
            tiled_proof['files'][tiles.TILE_PIXELS]['bytes'] - files[SHARED_PIXELS]['bytes'] - files[DICTIONARY]['bytes']):
        raise ValueError('Dictionary occurrence totals differ from the actual output size')
    result = {
        'original_pack': tiled_proof['original_pack'],
        'canonical_frames_byte_exact': tiled_proof['physical_frames_byte_exact'],
        'original_frame_files_byte_exact': tiled_proof['original_logical_frame_files_byte_exact'],
        'original_alias_files_byte_exact': tiled_proof['original_alias_files_byte_exact'],
        'active_tiles': active_tiles,
        'shared_groups': shared_groups,
        'dictionary_references': references,
        'original_bytes_of_shared_tiles': original_bytes,
        'tiled_bytes_with_indexes': before,
        'shared_tile_bytes_with_indexes': after,
        'net_savings_bytes': before - after,
        'net_savings_pct': round(100 * (before - after) / before, 4),
        'files': files,
    }
    output.rename(final)
    report = json.dumps(result, indent=2) + '\n'
    (HERE / f'results-{kind}.json').write_text(report, encoding='utf-8', newline='\n')
    print(report, end='')


if __name__ == '__main__':
    main()
