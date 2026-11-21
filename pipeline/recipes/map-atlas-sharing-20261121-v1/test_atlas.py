"""Test canonical x4 map atlases with identical BC1 tile sampling footprints."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
from zipfile import ZipFile
import zlib

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from mos_decode import decode_pvrz_page

spec = importlib.util.spec_from_file_location('pvrz_pack',
    HERE.parent / 'map-pvrz-sharing-20261121-v1/test_pack.py')
pvrz = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pvrz)
FAMILIES = (
    ('AR0334', 'AR0706', 'AR1603', 'AR2001'),
    ('AR0531', 'AR0708', 'AR1612'),
    ('AR0704', 'AR2010'),
)
EMPTY = 0xffffffff
TILE = 256
GUTTER = 4
INDEX = 'atlas-index.json'


def load_map_resources(rows, area):
    resources = {}
    for row in rows:
        if row['area'] != area:
            continue
        data = (ROOT / row['source']).read_bytes()
        if len(data) != row['bytes'] or pvrz.sha(data) != row['sha256'].lower():
            raise ValueError(f"Source changed: {row['source']}")
        resources[row['destination']] = data
    return resources


def atlas(area, files):
    tis = files[f'override/{area}.TIS']
    count, entry_size, offset, tile_px = struct.unpack_from('<4I', tis, 8)
    if tis[:8] != b'TIS V1  ' or (entry_size, offset, tile_px) != (12, 24, TILE) or len(tis) != offset + count * entry_size:
        raise ValueError(f'Unexpected TIS header: {area}')
    entries = tuple(struct.iter_unpack('<3I', tis[offset:]))
    pages = {}
    names = {f'override/{area}.TIS'}
    for page in sorted({p for p, _, _ in entries} - {EMPTY}):
        name = f'override/{area[0]}{area[2:]}{page:02d}.PVRZ'
        names.add(name)
        compressed = files[name]
        raw = zlib.decompress(compressed[4:])
        magic, flags, fmt, upper, color, channel, h, w, depth, surfaces, faces, mips, metadata = struct.unpack_from('<13I', raw)
        if (magic, flags, fmt, upper, color, channel, depth, surfaces, faces, mips) != (0x03525650, 0, 7, 0, 0, 0, 1, 1, 1, 1):
            raise ValueError(f'Unexpected BC1 page format: {name}')
        if (w, h) != (2048, 2048) or len(raw) != 52 + metadata + w * h // 2:
            raise ValueError(f'Unexpected BC1 page size: {name}')
        blocks = np.frombuffer(raw, dtype='<u8', offset=52 + metadata).reshape(h // 4, w // 4)
        pages[page] = (blocks, np.asarray(decode_pvrz_page(compressed)))
    if names != files.keys():
        raise ValueError(f'Unexpected atlas or WED override in the manifest: {area}')
    for page, x, y in entries:
        if page == EMPTY:
            continue
        h, w = pages[page][1].shape[:2]
        if x % 4 or y % 4 or min(x, y, w-x-TILE, h-y-TILE) < GUTTER:
            raise ValueError(f'Missing block-aligned margin: {area} {page} {x} {y}')
    return entries, pages


def compare(original, replacement):
    old_entries, old_pages = original
    new_entries, new_pages = replacement
    checked = different_at_five = 0
    for i, ((p, x, y), (q, u, v)) in enumerate(zip(old_entries, new_entries, strict=True)):
        if p == q == EMPTY:
            continue
        if p == EMPTY or q == EMPTY:
            raise ValueError(f'Blank tile identity differs: {i}')
        blocks_p, rgba_p = old_pages[p]
        blocks_q, rgba_q = new_pages[q]
        last = TILE // 4 + 1
        if not np.array_equal(blocks_p[y//4-1:y//4+last, x//4-1:x//4+last],
                              blocks_q[v//4-1:v//4+last, u//4-1:u//4+last]):
            raise ValueError(f'BC1 tile or four-pixel margin differs: {i}')
        checked += 1

        def footprint(image, left, top):
            xs = np.arange(left-5, left+TILE+5).clip(0, image.shape[1]-1)
            ys = np.arange(top-5, top+TILE+5).clip(0, image.shape[0]-1)
            return image[ys[:, None], xs]

        different_at_five += not np.array_equal(footprint(rgba_p, x, y), footprint(rgba_q, u, v))
    return checked, different_at_five


def check_wed(area, wed, original, replacement):
    layers, doors, overlay, _, door_start, door_cells = struct.unpack_from('<6I', wed, 8)
    w, h, ref, _, _, tilemap, lookup = struct.unpack_from('<HH8sHHII', wed, overlay)
    if wed[:8] != b'WED V1.3' or ref.rstrip(b'\0') != area.encode('ascii'):
        raise ValueError(f'Unexpected WED base tileset for {area}')
    if any(wed[overlay + 24*i + 4:overlay + 24*i + 12].strip(b'\0') for i in range(1, layers)):
        raise ValueError(f'Unexpected secondary overlay resources: {area}')
    primary = secondary = door_refs = 0
    old_count, new_count = len(original[0]), len(replacement[0])
    for cell in range(w * h):
        start, count, alternate, flags = struct.unpack_from('<HHHB', wed, tilemap + 10*cell)
        ids = struct.unpack_from(f'<{count}H', wed, lookup + 2*start)
        if flags & 0xfe or any(index >= min(old_count, new_count) for index in ids):
            raise ValueError(f'Unexpected WED overlay or invalid primary tile: {area}/{cell}')
        primary += count
        if alternate != 0xffff:
            if alternate >= min(old_count, new_count):
                raise ValueError(f'Invalid WED secondary tile: {area}/{cell}')
            secondary += 1
    for i in range(doors):
        first, count = struct.unpack_from('<HH', wed, door_start + 26*i + 10)
        cells = struct.unpack_from(f'<{count}H', wed, door_cells + 2*first)
        if any(cell >= w*h for cell in cells):
            raise ValueError(f'Invalid WED door cells: {area}/{i}')
        door_refs += count
    return dict(sha256=pvrz.sha(wed), cells=w*h, primary_refs=primary, secondary_refs=secondary,
                doors=doors, door_cell_refs=door_refs)


def write_zip(path, files):
    groups = {}
    aliases = {}
    with ZipFile(path, 'x') as out:
        for name, data in sorted(files.items()):
            if name.endswith('.TIS'):
                pvrz.put(out, name, data)
                continue
            digest = pvrz.sha(data)
            aliases[name] = digest
            if digest not in groups:
                groups[digest] = data
                pvrz.put(out, pvrz.blob_name(digest), data)
            elif groups[digest] != data:
                raise ValueError('PVRZ digest collision')
        pvrz.put(out, INDEX, json.dumps(aliases, sort_keys=True, separators=(',', ':')).encode('ascii'))
    return len(groups), sum(map(len, groups.values()))


def build():
    manifest = json.loads(pvrz.CONTENT.read_bytes())
    rows = [r for r in manifest['entries'] if r['kind'] == 'map']
    areas = {a for family in FAMILIES for a in family}
    source = {a: load_map_resources(rows, a) for a in sorted(areas)}
    atlases = {a: atlas(a, files) for a, files in source.items()}
    before = {name: data for files in source.values() for name, data in files.items()}
    if len(before) != sum(map(len, source.values())):
        raise ValueError('Destination collision in the selected zones')
    hashes = {pvrz.sha(data) for name, data in before.items() if name.endswith('.PVRZ')}
    if any(r['area'] not in areas and r['sha256'].lower() in hashes for r in rows
           if r['destination'].upper().endswith('.PVRZ')):
        raise ValueError('Selected pages are also shared outside the experiment')

    bifs, key_entries = load_key()
    wed_key = {name.upper(): loc for name, kind, loc in key_entries if kind == 0x03e9}
    weds = {a: resolve_resource(bifs, wed_key[a])[0] for a in sorted(areas)}
    after = {}
    family_results = []
    for members in FAMILIES:
        kept = min(members, key=lambda a: sum(map(len, source[a].values())))
        checks = {}
        for area in members:
            # Keep each zone's stock WED and TIS name. Copy only the donor's
            # TIS page coordinates and the exact donor pages to its namespace.
            for name, data in source[kept].items():
                dest = (f'override/{area}.TIS' if name.endswith('.TIS') else
                        f'override/{area[0]}{area[2:]}{Path(name).stem[5:]}.PVRZ')
                if dest not in source[area]:
                    raise ValueError(f'Unexpected change of page inventory: {dest}')
                after[dest] = data
            checks[area] = dict(wed=check_wed(area, weds[area], atlases[area], atlases[kept]))
        family_results.append(dict(members=members, atlas=kept, checks=checks))
    if before.keys() != after.keys():
        raise ValueError('The restored names and resource set would differ')

    run = HERE / 'run'
    run.mkdir(exist_ok=False)
    baseline = run / 'baseline-already-deduplicated.zip'
    candidate = run / 'maps-shared-atlas-test.zip'
    before_pages, before_bytes = write_zip(baseline, before)
    after_pages, after_bytes = write_zip(candidate, after)
    restored = run / 'restored'
    (restored / 'override').mkdir(parents=True)
    with ZipFile(candidate) as pack:
        aliases = json.loads(pack.read(INDEX))
        for name, data in after.items():
            entry = name if name.endswith('.TIS') else pvrz.blob_name(aliases[name])
            packed = pack.read(entry)
            if packed != data:
                raise ValueError(f'Archive bytes differ for {name}')
            (restored / name).write_bytes(packed)

    for family in family_results:
        for area, check in family['checks'].items():
            output = atlas(area, {name: (restored / name).read_bytes() for name in source[area]})
            check['wed'] = check_wed(area, weds[area], atlases[area], output)
            checked, changes_at_five = compare(atlases[area], output)
            check.update(textured_tiles_bc1_and_four_pixel_gutter_exact=checked,
                         empty_tiles_unchanged=len(output[0])-checked, tiles_different_at_five_pixels=changes_at_five)
    old_zip = baseline.stat().st_size
    new_zip = candidate.stat().st_size
    measured = dict(
        families=family_results,
        restored_files=len(after),
        pvrz_unique_before=before_pages,
        pvrz_unique_after=after_pages,
        pvrz_additional_saving_bytes=before_bytes-after_bytes,
        deduplicated_baseline_zip_bytes=old_zip,
        shared_atlas_test_zip_bytes=new_zip,
        actual_zip_additional_saving_bytes=old_zip-new_zip,
        shared_atlas_zip_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
    )
    report = json.dumps(measured, indent=2) + '\n'
    (HERE / 'results.json').write_text(report, encoding='utf-8', newline='\n')
    baseline.unlink()
    print(report, end='')


if __name__ == '__main__':
    build()
