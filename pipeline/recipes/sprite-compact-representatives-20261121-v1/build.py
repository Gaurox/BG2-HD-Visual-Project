"""Pack native palette-representative tables losslessly for ZIP distribution."""
import argparse
from array import array
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
from zipfile import ZIP_STORED, ZipFile, ZipInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CONTENT = ROOT / 'releases/BG2-HD-Upscale/manifests/content.json'
RUN = HERE / 'run'
PACK = RUN / 'sprite-compact-representatives-test.zip'
MAGIC = b'IEEREP1\0'
TABLE_BYTES = 512
SENTINEL = 0xFFFF
BITMAP, RUNS, RAW = 0xFE, 0xFD, 0xFF
ASSET = re.compile(r'iee-assets/creature-sprites/CreatureSprites-XN(?:-[A-F0-9]{64}\.registry|\.catalog)')
INDEX = 'sprite-representatives-pack.json'


def encode_table(table):
    values = array('H', table)
    if len(values) != 256:
        raise ValueError('Truncated representative table')
    slots, kept = [], array('H')
    for i, value in enumerate(values):
        if value != SENTINEL:
            slots.append(i)
            kept.append(value)
    count = len(slots)
    runs = []
    for slot in slots:
        if runs and slot == runs[-1][0] + runs[-1][1]:
            runs[-1][1] += 1
        else:
            runs.append([slot, 1])
    costs = (1 + 3*count if count < RUNS else float('inf'),
             2 + 2*len(runs) + 2*count, 33 + 2*count, 513)
    choice = min(range(len(costs)), key=costs.__getitem__)
    if choice == 0:
        return bytes([count, *slots]) + kept.tobytes(), 'slots'
    if choice == 1:
        return bytes([RUNS, len(runs), *(n for start, size in runs for n in (start, size-1))]) + kept.tobytes(), 'runs'
    if choice == 2:
        mask = bytearray(32)
        for i in slots:
            mask[i//8] |= 1 << (i%8)
        return bytes([BITMAP]) + mask + kept.tobytes(), 'bitmap'
    return bytes([RAW]) + table, 'raw'


def decode_table(data, start):
    mode, = struct.unpack_from('<B', data, start)
    offset = start + 1
    if mode == RAW:
        if offset + TABLE_BYTES > len(data):
            raise ValueError('Truncated raw table')
        return data[offset:offset+TABLE_BYTES], offset + TABLE_BYTES, 'raw'
    if mode == BITMAP:
        if offset + 32 > len(data):
            raise ValueError('Truncated slot bitmap')
        mask = int.from_bytes(data[offset:offset+32], 'little')
        slots = []
        while mask:
            low = mask & -mask
            slots.append(low.bit_length()-1)
            mask ^= low
        offset += 32
        name = 'bitmap'
    elif mode == RUNS:
        count, = struct.unpack_from('<B', data, offset)
        offset += 1
        slots = []
        for _ in range(count):
            first, last = struct.unpack_from('<BB', data, offset)
            slots.extend(range(first, first+last+1))
            offset += 2
        name = 'runs'
    else:
        slots = list(data[offset:offset+mode])
        if len(slots) != mode:
            raise ValueError('Truncated slot list')
        offset += mode
        name = 'slots'
    if (slots and slots[-1] > 255) or any(b <= a for a, b in zip(slots, slots[1:])):
        raise ValueError('Invalid representative slot order')
    end = offset + len(slots)*2
    values = array('H', data[offset:end])
    if len(values) != len(slots) or SENTINEL in values:
        raise ValueError('Invalid representative values')
    table = array('H', [SENTINEL]) * 256
    for slot, value in zip(slots, values, strict=True):
        table[slot] = value
    return table.tobytes(), end, name


def transform(data, restore=False):
    prefix = 12 if restore else 0
    if restore and data[:8] != MAGIC:
        raise ValueError('Missing compact table signature')
    magic, version, scale, resources, marker = struct.unpack_from('<8s4I', data, prefix)
    if magic != b'IEECSXN\0' or version not in (6, 7, 9) or scale != 2 or marker != 65535:
        raise ValueError('Unsupported sprite shard header')
    output = bytearray() if restore else bytearray(MAGIC + struct.pack('<I', len(data)))
    previous, offset = prefix, prefix + 32
    modes = Counter()
    before_bytes, after_bytes = 0, 0
    for _ in range(resources):
        frames, cycles = struct.unpack_from('<II', data, offset+40)
        offset += 48 + (2052 if version in (7, 9) else 0)
        for _ in range(frames):
            index_bytes, = struct.unpack_from('<I', data, offset+12)
            start = offset + 16
            if restore:
                table, end, mode = decode_table(data, start)
                before_bytes += TABLE_BYTES
                after_bytes += end-start
            else:
                end = start + TABLE_BYTES
                table, mode = encode_table(data[start:end])
                before_bytes += TABLE_BYTES
                after_bytes += len(table)
            modes[mode] += 1
            output.extend(data[previous:start])
            output.extend(table)
            previous = end
            fraction_bytes, = struct.unpack_from('<I', data, end+32)
            offset = end + 40
            stored = index_bytes + fraction_bytes
            if version == 9:
                for _ in range(2):
                    size, = struct.unpack_from('<I', data, offset)
                    offset += 8
                    stored += size
            offset += stored
        for _ in range(cycles):
            slots, = struct.unpack_from('<I', data, offset)
            offset += 4 + 4*slots
    if offset != len(data):
        raise ValueError('Unexpected shard length')
    output.extend(data[previous:offset])
    if restore and len(output) != struct.unpack_from('<I', data, 8)[0]:
        raise ValueError('Restored shard length differs')
    return output, modes, before_bytes, after_bytes


def originals():
    selected = {}
    for entry in json.loads(CONTENT.read_bytes())['entries']:
        if entry['kind'] != 'sprite':
            continue
        name = entry['destination']
        if not ASSET.fullmatch(name) or name in selected:
            raise ValueError(f'Unexpected sprite asset path: {name}')
        selected[name] = entry
    return selected


def put(archive, name, data):
    entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = ZIP_STORED
    archive.writestr(entry, data)


def check(data, expected, name):
    if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256'].lower():
        raise ValueError(f'Asset differs: {name}')


def verify(selected=None, destination=None):
    count, frames = 0, 0
    with ZipFile(PACK) as archive:
        expected = json.loads(archive.read(INDEX))
        names = archive.namelist()
        if (len(names) != len(expected)+1 or set(names) != set(expected) | {INDEX}
                or not all(ASSET.fullmatch(name) for name in expected)):
            raise ValueError('Unexpected pack inventory')
        if selected is not None and set(expected) != set(selected):
            raise ValueError('Source and packed inventories differ')
        if destination is not None:
            destination.mkdir(parents=True, exist_ok=False)
        for name, row in expected.items():
            compact = archive.read(name)
            if name.endswith('.registry'):
                try:
                    data, modes, _, _ = transform(compact, restore=True)
                except (ValueError, struct.error) as error:
                    raise ValueError(f'Cannot reconstruct sprite registry {name}') from error
                frames += sum(modes.values())
            else:
                data = compact
            check(data, row, name)
            if selected is not None:
                source = selected[name]
                check(data, source, name)
                if data != (ROOT/source['source']).read_bytes():
                    raise ValueError(f'Original and reconstructed bytes differ: {name}')
            if destination is not None:
                path = destination / name
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as out:
                    out.write(data)
            count += 1
            if count % 3000 == 0:
                print(f'{count}/{len(expected)} fichiers reconstruits', flush=True)
    return count, frames


def build():
    selected = originals()
    RUN.mkdir(exist_ok=False)
    baseline = RUN / 'baseline.zip'
    modes = Counter()
    native_tables = compact_tables = 0
    inventory = {name: {key: row[key] for key in ('sha256', 'bytes')} for name, row in selected.items()}
    with ZipFile(baseline, 'x') as old, ZipFile(PACK, 'x') as new:
        for i, (name, row) in enumerate(selected.items(), 1):
            original = (ROOT / row['source']).read_bytes()
            check(original, row, name)
            if name.endswith('.registry'):
                compact, codecs, raw_size, packed_size = transform(original)
                modes.update(codecs)
                native_tables += raw_size
                compact_tables += packed_size
            else:
                compact = original
            put(old, name, original)
            put(new, name, compact)
            if i % 3000 == 0:
                print(f'{i}/{len(selected)} fichiers traités', flush=True)
        put(new, INDEX, json.dumps(inventory, separators=(',', ':')).encode())
    verified, frames = verify(selected)
    assert frames == sum(modes.values())
    old_bytes, new_bytes = baseline.stat().st_size, PACK.stat().st_size
    with PACK.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    results = {
        'verified_registries': verified-1,
        'verified_catalogs': 1,
        'verified_frame_tables': frames,
        'table_modes': dict(modes),
        'original_table_bytes': native_tables,
        'compact_table_bytes': compact_tables,
        'table_savings_bytes': native_tables-compact_tables,
        'baseline_zip_bytes': old_bytes,
        'compact_zip_bytes': new_bytes,
        'net_zip_savings_bytes': old_bytes-new_bytes,
        'net_zip_savings_pct': round(100*(old_bytes-new_bytes)/old_bytes, 4),
        'compact_zip_sha256': digest,
    }
    report = json.dumps(results, indent=2) + '\n'
    (HERE/'results.json').write_text(report, encoding='utf-8')
    baseline.unlink()
    print(report, end='')


if __name__ == '__main__':
    if sys.byteorder != 'little':
        raise RuntimeError('Representative codec requires little-endian arrays')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('build', 'verify', 'restore'))
    parser.add_argument('destination', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'build' and args.destination is None:
        build()
    elif args.action == 'verify' and args.destination is None:
        print(verify(originals()))
    elif args.action == 'restore' and args.destination is not None:
        print(verify(destination=args.destination))
    else:
        parser.error('restore requires a new output directory')
