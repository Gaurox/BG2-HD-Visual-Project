"""Share x4 map decor by original x1 identity, keeping each zone's geometry and alpha."""
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import struct
import sys
from zipfile import ZipFile
import zlib

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import bg2lib
from mos_decode import decode_pvrz_page

spec = importlib.util.spec_from_file_location('atlas_trial', HERE.parent / 'map-atlas-sharing-20261121-v1/test_atlas.py')
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
pvrz = trial.pvrz
RELEASE = ROOT / 'releases/BG2-HD-Upscale/manifests'
WATER = ROOT / 'pipeline/water/requests/ar6300-water-30fps-20260929-v4/registry-v3.json'
RUN = HERE / 'run'
ZIP = RUN / 'shared-original-maps-test.zip'
INDEX = 'map-sharing-index.json'
EMPTY = 0xffffffff


def sha(data):
    return hashlib.sha256(data).hexdigest()


def resref(data):
    return data.rstrip(b'\0').decode('ascii').upper()


def page_name(tileset, index):
    return f'{tileset[0]}{tileset[2:]}{index:02}.PVRZ'


def wed_layout(wed):
    if wed[:8] != b'WED V1.3':
        raise ValueError('Unexpected WED header')
    count, _, start = struct.unpack_from('<3I', wed, 8)
    w, h, name, _, _, tilemap, lookup = struct.unpack_from('<HH8sHHII', wed, start)
    overlays = tuple(resref(wed[start+24*i+4:start+24*i+12]) for i in range(1, count))
    cells = []
    for cell in range(w*h):
        slot, n, secondary, *flags = struct.unpack_from('<HHHBBBB', wed, tilemap + 10*cell)
        primary = struct.unpack_from(f'<{n}H', wed, lookup+2*slot)
        cells.append((primary, secondary, bytes(flags)))
    return resref(name), w, h, overlays, cells


def original_families():
    bifs, resources = bg2lib.load_key()
    keys = {(name.upper(), kind): loc for name, kind, loc in resources}

    @lru_cache(maxsize=32)
    def original(name, kind):
        return bg2lib.resolve_resource(bifs, keys[name, kind])[0]

    @lru_cache(maxsize=None)
    def tile_hashes(name):
        data, count, size, _ = bg2lib.resolve_tileset_resource(bifs, keys[name, 0x03eb])
        if size != 12 or len(data) != count * size:
            raise ValueError(f'Unexpected x1 TIS: {name}')
        positions = defaultdict(list)
        for i, (page, x, y) in enumerate(struct.iter_unpack('<3I', data)):
            positions[page].append((i, x, y))
        result = [b'\0'*32] * count
        for page, coords in positions.items():
            if page == EMPTY:
                continue
            pixels = np.asarray(decode_pvrz_page(original(page_name(name, page)[:-5], 0x0404)))
            seen = {}
            for i, x, y in coords:
                if (x, y) not in seen:
                    tile = pixels[y:y+64, x:x+64]
                    if tile.shape != (64, 64, 4):
                        raise ValueError(f'x1 tile outside its atlas: {name}/{i}')
                    seen[x, y] = hashlib.sha256(np.ascontiguousarray(tile)).digest()
                result[i] = seen[x, y]
        return tuple(result)

    groups = defaultdict(list)
    records = {}
    for area in sorted(name for name, kind in keys if kind == 0x03e9):
        raw = original(area, 0x03e9)
        ref, w, h, overlays, cells = wed_layout(raw)
        tile = tile_hashes(ref)
        identity = hashlib.sha256(b''.join(tile))
        grid = hashlib.sha256(struct.pack('<HH', w, h))
        grid.update(json.dumps(overlays).encode('ascii'))
        for primary, alternate, flags in cells:
            # The stock renderer reuses primary art for out-of-range alternates.
            grid.update(struct.pack('<H', len(primary)) + b''.join(tile[i] for i in primary))
            grid.update(b'\0' if alternate >= len(tile) else b'\1'+tile[alternate])
            grid.update(flags)
        signature = (identity.hexdigest(), grid.hexdigest())
        groups[signature].append(area)
        records[area] = dict(tis=ref, tiles=len(tile), wed_sha256=sha(raw), original_signature=signature)
    aliases = {}
    for area, kind in keys:
        if kind == 0x03f2:
            wed = resref(original(area, kind)[8:16])
            if area != wed:
                aliases[area] = wed
    bg2lib._bif_cache.clear()
    return [g for g in groups.values() if len(g) > 1], records, dict(sorted(aliases.items())), original


def read_validated(row):
    raw = (ROOT / row['source']).read_bytes()
    if len(raw) != row['bytes'] or sha(raw) != row['sha256'].lower():
        raise ValueError(f"Approved file differs: {row['source']}")
    return raw


def split_page(data):
    raw = zlib.decompress(data[4:])
    header = struct.unpack_from('<13I', raw)
    magic, _, fmt, _, _, _, h, w, depth, surfaces, faces, mip, meta = header
    block_size = {7: 8, 11: 16}[fmt]
    start = 52+meta
    if magic != 0x03525650 or (depth, surfaces, faces, mip) != (1, 1, 1, 1) or w%4 or h%4:
        raise ValueError('Unexpected x4 PVR header')
    if len(raw) != start + (w//4)*(h//4)*block_size:
        raise ValueError('Unexpected x4 PVR payload')
    blocks = np.frombuffer(raw, offset=start, dtype=np.uint8).reshape(-1, block_size)
    return raw[:start], blocks[:, -8:].tobytes(), (blocks[:, :8].tobytes() if fmt == 11 else None)


def join_page(header, rgb, alpha):
    if len(rgb) != len(alpha) or len(rgb) % 8:
        raise ValueError('Invalid BC3 planes')
    blocks = np.empty((len(rgb)//8, 16), dtype=np.uint8)
    blocks[:, :8] = np.frombuffer(alpha, dtype=np.uint8).reshape(-1,8)
    blocks[:, 8:] = np.frombuffer(rgb, dtype=np.uint8).reshape(-1,8)
    raw = header + blocks.tobytes()
    return struct.pack('<I', len(raw)) + zlib.compress(raw, 6)


def base_resources(area, inventory):
    row = inventory[f'{area}.TIS']
    tis = read_validated(row)
    n, size, start, edge = struct.unpack_from('<4I', tis, 8)
    if (size, start, edge, len(tis)) != (12, 24, 256, 24+n*12):
        raise ValueError(f'Unexpected x4 TIS: {area}')
    entries = tuple(struct.iter_unpack('<3I', tis[start:]))
    pages = {p: inventory[page_name(area,p)] for p in sorted({p for p,x,y in entries}-{EMPTY})}
    return tis, entries, pages


def check_active_layout(area, wed, count):
    ref, _, _, overlays, cells = wed_layout(wed)
    if ref != area or any(i>=count for primary, secondary, flags in cells for i in primary) or any(
        secondary>=count and secondary!=65535 for _,secondary,_ in cells):
        raise ValueError(f'Invalid delivered WED/TIS references: {area}')
    return dict(sha256=sha(wed), cells=len(cells), overlays=[r for r in overlays if r])


def write_archives(inventory, selected, stored):
    # Stored ZIP on both sides. Account for a blob still needed by a zone
    # outside the families by leaving one copy of it in the measurement.
    before_hashes = {inventory[name]['sha256'].lower() for name in selected}
    external = {r['sha256'].lower(): r for name,r in inventory.items() if name.endswith('.PVRZ') and
                name not in selected and r['sha256'].lower() in before_hashes}
    baseline = RUN / 'baseline.zip'
    with ZipFile(baseline, 'x') as out:
        names = {name: inventory[name]['sha256'].lower() for name in selected}
        unique = {names[name]: inventory[name] for name in selected}
        for digest, row in sorted(unique.items()):
            pvrz.put(out, f'objects/{digest}', read_validated(row))
        pvrz.put(out, INDEX, json.dumps(names, separators=(',', ':'), sort_keys=True).encode('ascii'))
    with ZipFile(ZIP, 'x') as out:
        objects = dict(stored)
        for digest, row in external.items():
            objects.setdefault(digest, read_validated(row))
        for digest, data in sorted(objects.items()):
            pvrz.put(out, f'objects/{digest}', data)
        pvrz.put(out, INDEX, json.dumps(selected, separators=(',', ':'), sort_keys=True).encode('ascii'))
    size = baseline.stat().st_size
    baseline.unlink()
    return size, len(external)


def retrieve(archive, recipe):
    def obj(key):
        payload = archive.read(f'objects/{recipe[key]}')
        if sha(payload) != recipe[key]:
            raise ValueError('Archive object checksum mismatch')
        return payload
    if 'pvrz' in recipe:
        return obj('pvrz')
    return join_page(bytes.fromhex(recipe['pvr_header']), zlib.decompress(obj('rgb')), zlib.decompress(obj('alpha')))


def build():
    families, originals, area_aliases, original = original_families()
    manifest = json.loads(pvrz.CONTENT.read_bytes())
    inventory = {Path(r['destination']).name.upper():r for r in manifest['entries'] if r['kind']=='map'}
    release_areas = {r['area'] for r in csv.DictReader((RELEASE/'map-release-candidates.csv').open(encoding='utf-8-sig'))}
    if set(originals) != release_areas | {'OH6460'}:
        raise ValueError('Unexpected WED coverage relative to the selected catalog')
    water = defaultdict(list)
    for entry in json.loads(WATER.read_bytes())['entries']:
        water[entry['wed']['resref']].append(entry)
    already = {frozenset(group): donor for group,donor in zip(trial.FAMILIES, ('AR0706','AR0708','AR0704'), strict=True)}
    objects, recipes, output, checks, layout = {}, {}, {}, {}, []
    for group in families:
        if len({originals[a]['tis'] for a in group}) == 1:
            layout.append(dict(areas=group, donor=originals[group[0]]['tis'], status='native-shared-tileset'))
            continue
        info = {a:base_resources(a,inventory) for a in group}
        # Prefer the exact variant already used by the most areas, then the smaller accepted build.
        page_signatures = {a:tuple(r['sha256'] for r in info[a][2].values()) for a in group}
        counts = Counter(page_signatures.values())
        donor = already.get(frozenset(group)) or min(group, key=lambda a: (
            -counts[page_signatures[a]], sum(r['bytes'] for r in info[a][2].values()), a))
        donor_tis, entries, donor_pages = info[donor]
        for area, (tis, own_entries, own_pages) in info.items():
            if tis != donor_tis or own_pages.keys() != donor_pages.keys():
                raise ValueError(f'Current x4 tile layout differs: {area} / {donor}')
            wed_row = inventory.get(f'{area}.WED')
            wed = read_validated(wed_row) if wed_row else original(area, 0x03e9)
            checks[area] = check_active_layout(area, wed, len(entries))
            checks[area]['tis_sha256'] = sha(tis)
            for binding in water[area]:
                if binding['base_tis']['sha256'].lower() != sha(tis):
                    raise ValueError(f'Water TIS binding differs: {area}')
            checks[area]['water_contracts'] = len(water[area])

        split_pages = 0
        for p, donor_row in donor_pages.items():
            donor_pvrz = read_validated(donor_row)
            head, rgb, alpha = split_page(donor_pvrz)
            sources = {a:read_validated(info[a][2][p]) for a in group}
            planes = {a:split_page(data) for a,data in sources.items()}
            use_split = alpha is not None and any(parts[2] != alpha for parts in planes.values())
            split_pages += use_split
            for area,(own_head,own_rgb,own_alpha) in planes.items():
                if (own_alpha is None) != (alpha is None) or own_head != head:
                    raise ValueError(f'PVR formats or dimensions differ: {area}/{p}')
                name = page_name(area,p)
                if use_split:
                    crgb, ca = zlib.compress(rgb, 6), zlib.compress(own_alpha, 6)
                    recipe = dict(rgb=sha(crgb), alpha=sha(ca), pvr_header=head.hex())
                    objects.setdefault(recipe['rgb'], crgb)
                    objects.setdefault(recipe['alpha'], ca)
                    prepared = join_page(head, rgb, own_alpha)
                else:
                    prepared = donor_pvrz
                    recipe = dict(pvrz=sha(prepared))
                    objects.setdefault(recipe['pvrz'], prepared)
                    # BC1 alpha is encoded jointly with RGB. Confirm that there is no mask drift.
                    if alpha is None and sources[area] != prepared:
                        old_opacity = np.asarray(decode_pvrz_page(sources[area]))[:,:,3]
                        new_opacity = np.asarray(decode_pvrz_page(prepared))[:,:,3]
                        for page,x,y in entries:
                            if page == p and not np.array_equal(old_opacity[y-4:y+260,x-4:x+260],
                                                                 new_opacity[y-4:y+260,x-4:x+260]):
                                raise ValueError(f'BC1 tile alpha differs: {area}/{p}')
                for binding in water[area]:
                    for page in binding['base_tis'].get('pages', []):
                        if page['resref'].upper()+'.PVRZ' == name and page['sha256'].lower() != sha(prepared):
                            raise ValueError(f'Water page hash would change: {name}')
                if split_page(prepared) != (head,rgb,own_alpha):
                    raise ValueError(f'Colour or alpha verification failed: {name}')
                recipes[name] = recipe
                output[name] = dict(sha256=sha(prepared), bytes=len(prepared), baseline_sha256=sha(sources[area]))
        layout.append(dict(areas=group, donor=donor, status='local-candidate', shared_page_count=len(donor_pages),
                           bc3_private_alpha_pages=split_pages))

    RUN.mkdir(exist_ok=False)
    old_size, external = write_archives(inventory, recipes, objects)
    restored = RUN/'restored'/'override'
    restored.mkdir(parents=True)
    with ZipFile(ZIP) as archive:
        actual = json.loads(archive.read(INDEX))
        if actual != recipes:
            raise ValueError('Archive destination inventory differs')
        for name, recipe in actual.items():
            (restored/name).write_bytes(retrieve(archive, recipe))
    for name, proof in output.items():
        if pvrz.file_sha(restored/name) != proof['sha256'] or (restored/name).stat().st_size != proof['bytes']:
            raise ValueError(f'Restored file differs: {name}')
    measured = dict(
        original_wed_variants=len(originals), native_are_aliases=area_aliases, families=layout,
        original_signatures={a:originals[a] for group in families for a in group},
        wed_and_tis_checks=checks, files=output, shared_objects=len(objects), external_overlap_pages=external,
        original_deduplicated_test_zip_bytes=old_size, shared_test_zip_bytes=ZIP.stat().st_size,
        marginal_zip_saving_bytes=old_size-ZIP.stat().st_size, pack_sha256=pvrz.file_sha(ZIP),
    )
    (HERE/'results.json').write_text(json.dumps(measured,indent=2)+'\n', encoding='utf-8', newline='\n')
    print(len(families),'families',sum(map(len,families)), 'variants;',len(area_aliases),'native ARE aliases;',
          len(output),'verified PVRZ;', measured['marginal_zip_saving_bytes'],'net bytes',flush=True)


if __name__ == '__main__':
    build()
