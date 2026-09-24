"""Clone live x4 map pages and repair qualified native liquid composition.

Read-only without --run. WED/ARE/TIS and masks come exclusively from --vanilla-root.
Sentinel entries, unrelated tiles and unselected DXT blocks are retained. A selected
tile sharing a physical atlas slot is isolated on a new page before modification.
No GPU work, WED editing, installation, renderer change or release mutation.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import zlib

import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion

ROOT = Path(__file__).resolve().parents[2]
SENTINEL = 0xFFFFFFFF
Image.MAX_IMAGE_PIXELS = None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def file_digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(part)
    return value.hexdigest().upper()


def resource_name(value):
    value = str(value).upper()
    require(1 <= len(value) <= 8 and value.isascii()
            and all(c.isalnum() or c == '_' for c in value), 'Invalid resource name')
    return value


def resolve_input(value):
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve(strict=True)


def block_mask(mask):
    return np.pad(mask, 4, mode='edge').reshape(66, 4, 66, 4).any((1, 3))


def seam_masks(parsed, slot_groups, full_cells, stock_tile, unique_primary, unique_secondary):
    """World-space masks per group of overlay bits; never cross materials or true banks.
    A group is one slot, or every slot of one tiled family (A-D pavings: neighbouring water
    cells always carry different slots of the same material, AR5000 WT5000A-D)."""
    width, height = parsed['layers'][0]['width'], parsed['layers'][0]['height']
    cells = {(c['x'], c['y']): c for c in parsed['cells']}
    rgb, alpha, coords, interfaces = {}, {}, {}, []
    opposite = {'left': 'right', 'right': 'left', 'top': 'bottom', 'bottom': 'top'}

    def add(store, tile, xy, side, valid, feather):
        mask = store.setdefault(tile, np.zeros((256, 256), np.float32))
        along = np.repeat(valid, 4)
        weights = [1, 1, 1, 1, .75, .5, .25, 0] if feather else [1] * 8
        for distance, weight in enumerate(weights):
            values = along * weight
            if side == 'left': mask[:, distance] = np.maximum(mask[:, distance], values)
            elif side == 'right': mask[:, 255-distance] = np.maximum(mask[:, 255-distance], values)
            elif side == 'top': mask[distance] = np.maximum(mask[distance], values)
            else: mask[255-distance] = np.maximum(mask[255-distance], values)
        coords[tile] = xy

    for group in slot_groups:
        bit = sum(1 << slot for slot in group)
        slot = group[0] if len(group) == 1 else list(group)
        water = np.zeros((height * 64, width * 64), bool)
        for xy, cell in cells.items():
            if not cell['flags'] & bit or cell['count'] != 1:
                continue
            tile = cell['primary'][0]
            if xy in full_cells:
                valid = np.ones((64, 64), bool)
            elif cell['secondary'] != 65535 and tile in unique_primary \
                    and cell['secondary'] in unique_secondary:
                primary_alpha = np.asarray(stock_tile(tile))[:, :, 3]
                secondary_alpha = np.asarray(stock_tile(cell['secondary']))[:, :, 3]
                valid = (primary_alpha == 0) & (secondary_alpha == 255)
            else:
                continue
            x, y = xy
            water[y*64:(y+1)*64, x*64:(x+1)*64] = valid
        safe = binary_erosion(water, structure=np.ones((3, 3), bool), border_value=0)
        for xy, tile in full_cells.items():
            cell = cells[xy]
            if not cell['flags'] & bit:
                continue
            x, y = xy
            own = safe[y*64:(y+1)*64, x*64:(x+1)*64]
            for side, dx, dy in [('left', -1, 0), ('right', 1, 0), ('top', 0, -1), ('bottom', 0, 1)]:
                nx, ny = x + dx, y + dy
                neighbor = cells.get((nx, ny))
                if not neighbor or not neighbor['flags'] & bit or neighbor['count'] != 1 \
                        or neighbor['secondary'] not in unique_secondary:
                    continue
                other = safe[ny*64:(ny+1)*64, nx*64:(nx+1)*64]
                if side == 'left': valid = own[:, :2].all(1) & other[:, -2:].all(1)
                elif side == 'right': valid = own[:, -2:].all(1) & other[:, :2].all(1)
                elif side == 'top': valid = own[:2].all(0) & other[-2:].all(0)
                else: valid = own[-2:].all(0) & other[:2].all(0)
                if not valid.any():
                    continue
                add(rgb, tile, xy, side, valid, True)
                add(alpha, neighbor['secondary'], (nx, ny), opposite[side], valid, False)
                interfaces.append({'slot': slot, 'primary': tile, 'secondary': neighbor['secondary'],
                                   'cell': list(xy), 'neighbor': [nx, ny], 'side': side})
    return rgb, alpha, coords, interfaces


def process_target(target, vanilla, live, destination, write):
    from area_decode import decode_tis_tiles, _pvrz_page_cache
    from bg2lib import resolve_resource, resolve_tileset_resource
    from build_water_route1_batch import parse_wed, parse_standalone_tis, parse_pvr, tile_alpha_constant
    from mos_decode import decode_pvrz_page

    bifs, index, pvr = vanilla
    wed_name = resource_name(target['wed'])
    wed, wed_archive = resolve_resource(bifs, index[wed_name, 0x3E9])
    parsed = parse_wed(wed)
    base = resource_name(parsed['layers'][0]['tis'])
    slots_raw = target.get('slots', [layer['slot'] for layer in parsed['layers'][1:]])
    slots = sorted({int(s['slot'] if isinstance(s, dict) else s) for s in slots_raw})
    require(all(0 < slot < len(parsed['layers']) and slot < 8 for slot in slots), 'Invalid overlay slot')
    bits = sum(1 << slot for slot in slots)
    are_name = resource_name(target.get('area', wed_name[:-1] if wed_name.endswith('N') else wed_name))
    are, are_archive = resolve_resource(bifs, index[are_name, 0x3F2])
    require(are[:8] == b'AREAV1.0' and len(are) > 0x52, 'Unsupported native ARE')
    native_alpha = are[0x52] or 128
    require(int(target.get('native_alpha', native_alpha)) == native_alpha, 'Requested alpha differs from native ARE')
    central_enabled = bool(target.get('restore_central_alpha', True))
    seams_enabled = bool(target.get('repair_rgb_seams', target.get('repair_seams', True)))
    threshold = float(target.get('rgb_difference_threshold', 6.0))
    require(threshold >= 0, 'Negative RGB threshold')
    source_tis, stock_count, stock_size, tis_archive = resolve_tileset_resource(bifs, index[base, 0x3EB])
    require(stock_size == 12, 'Native base must use PVRZ tiles')
    stock_entries = [struct.unpack_from('<3I', source_tis, i * 12) for i in range(stock_count)]
    tis_path = live / (base + '.TIS')
    tis_bytes = tis_path.read_bytes()
    tis = parse_standalone_tis(tis_bytes)
    require(tis['count'] == stock_count, 'Live/native base tile counts differ')
    prefix = base[0] + base[2:]
    physical_uses = Counter(entry for entry in tis['entries'] if entry[0] != SENTINEL)
    physical_unique = {tile for tile, entry in enumerate(tis['entries'])
                       if entry[0] != SENTINEL and physical_uses[entry] == 1}
    primary_uses = defaultdict(list)
    secondary_uses = Counter(c['secondary'] for c in parsed['cells'] if c['secondary'] != 65535)
    for cell in parsed['cells']:
        for tile in cell['primary']:
            primary_uses[tile].append(cell)
    unique_primary = {t for t, uses in primary_uses.items()
                      if len(uses) == 1 and t not in secondary_uses}
    unique_secondary = {t for t, count in secondary_uses.items()
                        if count == 1 and t not in primary_uses and t in physical_unique}
    stock_tile, _ = decode_tis_tiles(bifs, pvr, base, index[base, 0x3EB])
    native_pages = {}
    full_cells, skipped = {}, []
    for tile, uses in primary_uses.items():
        if not all(c['flags'] & bits and c['secondary'] == 65535 and c['count'] == 1 for c in uses):
            continue
        page, x, y = stock_entries[tile]
        if page == SENTINEL or tis['entries'][tile][0] == SENTINEL:
            skipped.append({'tile': tile, 'reason': 'sentinel-preserved'})
            continue
        if tile not in unique_primary:
            skipped.append({'tile': tile, 'reason': 'shared-logical-usage'})
            continue
        if page not in native_pages:
            page_name = resource_name(f'{prefix}{page:02d}')
            packed, _ = resolve_resource(bifs, index[page_name, 0x404])
            native_pages[page] = parse_pvr(packed)
        _, fmt, width, height, _ = native_pages[page]
        if fmt != 7 or x + 64 > width or y + 64 > height:
            skipped.append({'tile': tile, 'reason': 'native-not-opaque-DXT1'})
            continue
        cell = uses[0]
        full_cells[cell['x'], cell['y']] = tile
    central_ids = set(full_cells.values()) if central_enabled else set()
    donor_path = target.get('secondary_master', target.get('secondary_master_x4', target.get('donor')))
    rgb, secondary_alpha, coords, interfaces = ({}, {}, {}, [])
    family = str(target.get('family', ''))
    slot_groups = [slots] if family and ',' not in family else [[slot] for slot in slots]
    if seams_enabled and full_cells:
        require(donor_path is not None, f'{wed_name}: missing secondary master')
        rgb, secondary_alpha, coords, interfaces = seam_masks(
            parsed, slot_groups, full_cells, stock_tile, unique_primary, unique_secondary)
    modified_ids = central_ids | set(rgb) | set(secondary_alpha)
    require(not (set(rgb) & set(secondary_alpha)), 'Primary/secondary repair overlap')
    relocations, relocated_pages, shared_already_conform = [], {}, []
    output_tis = bytearray(tis_bytes)
    header_size = struct.unpack_from('<I', tis_bytes, 16)[0]
    next_page = max(e[0] for e in tis['entries'] if e[0] != SENTINEL) + 1
    for tile in sorted(modified_ids):
        old_entry = tis['entries'][tile]
        page, x, y = old_entry
        if physical_uses[old_entry] == 1:
            continue
        require(tile in unique_primary and tile in full_cells.values(), 'Only qualified central aliases can be isolated')
        source_name = resource_name(f'{prefix}{page:02d}') + '.PVRZ'
        raw, fmt, width, height, offset = parse_pvr((live / source_name).read_bytes())
        require(fmt == 11 and (x % 264, y % 264) == (4, 4)
                and x+260 <= width and y+260 <= height, 'Cannot isolate unproven padded DXT5 tile')
        if tile in central_ids and tile not in rgb and tile_alpha_constant(
                raw, fmt, width, offset, x-4, y-4, 264, native_alpha):
            # An already-correct shared slot needs neither writes nor isolation.
            modified_ids.remove(tile)
            shared_already_conform.append({'tile': tile, 'entry': list(old_entry),
                                          'native_alpha': native_alpha, 'padding_checked': True})
            continue
        resource_name(f'{prefix}{next_page:02d}')
        source_blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height//4, width//4, 16)
        clone = bytearray(raw[:offset]) + bytearray(128*128*16)
        struct.pack_into('<II', clone, 24, 512, 512)
        clone_blocks = np.frombuffer(clone, np.uint8, offset=offset).reshape(128, 128, 16)
        clone_blocks[:66, :66] = source_blocks[(y-4)//4:(y-4)//4+66, (x-4)//4:(x-4)//4+66]
        relocated_pages[next_page] = struct.pack('<I', len(clone)) + zlib.compress(clone, 9)
        tis['entries'][tile] = (next_page, 4, 4)
        struct.pack_into('<3I', output_tis, header_size + tile*12, next_page, 4, 4)
        relocations.append({'tile': tile, 'old_entry': list(old_entry), 'new_entry': [next_page, 4, 4],
                            'reason': 'isolate-selected-primary-from-shared-physical-slot'})
        next_page += 1
    physical_uses = Counter(entry for entry in tis['entries'] if entry[0] != SENTINEL)
    by_page = defaultdict(list)
    for tile in modified_ids:
        page, x, y = tis['entries'][tile]
        require(page != SENTINEL and physical_uses[page, x, y] == 1, 'Selected atlas slot aliased')
        require((x % 264, y % 264) == (4, 4), f'{wed_name}/{tile}: unproven 4px atlas padding')
        by_page[page].append(tile)
    donor = None
    donor_hash = None
    if rgb:
        donor_path = resolve_input(donor_path)
        donor_hash = file_digest(donor_path)
        donor = Image.open(donor_path)
        require(donor.size == (parsed['layers'][0]['width']*256, parsed['layers'][0]['height']*256),
                'Secondary master dimensions differ from WED x4')
    output = destination / 'maps' / wed_name
    if write:
        output.mkdir(parents=True, exist_ok=False)
        (output / (base + '.TIS')).write_bytes(output_tis)
    report = {'wed': wed_name, 'base': base, 'slots': slots, 'native_alpha': native_alpha,
              'central_alpha_enabled': central_enabled, 'qualified_central_tiles': sorted(central_ids),
              'skipped': skipped, 'interfaces': interfaces, 'rgb_difference_threshold': threshold,
              'secondary_master': str(donor_path) if donor else None, 'secondary_master_sha256': donor_hash,
              'source_wed': {'archive': wed_archive, 'sha256': digest(wed)},
              'source_are': {'archive': are_archive, 'sha256': digest(are)},
              'source_tis': {'archive': tis_archive, 'sha256': digest(source_tis)},
              'live_tis_sha256': digest(tis_bytes), 'output_tis_sha256': digest(output_tis),
              'relocations': relocations, 'shared_slots_already_conform': shared_already_conform,
              'pages': [], 'rgb_tiles': []}
    for page in sorted({entry[0] for entry in tis['entries'] if entry[0] != SENTINEL}):
        name = resource_name(f'{prefix}{page:02d}') + '.PVRZ'
        packed = relocated_pages[page] if page in relocated_pages else (live / name).read_bytes()
        result = packed
        rgb_count = alpha_count = 0
        if page in by_page:
            raw, fmt, width, height, offset = parse_pvr(packed)
            require(fmt == 11, f'{name}: selective repair requires existing DXT5')
            original = np.frombuffer(bytes(raw), np.uint8, offset=offset).reshape(height//4, width//4, 16)
            blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height//4, width//4, 16)
            allowed_rgb = np.zeros(blocks.shape[:2], bool)
            allowed_alpha = np.zeros(blocks.shape[:2], bool)
            decoded = decode_pvrz_page(packed) if any(t in rgb for t in by_page[page]) else None
            for tile in sorted(by_page[page]):
                _, x, y = tis['entries'][tile]
                left, top, right, bottom = x-4, y-4, x+260, y+260
                require(left >= 0 and top >= 0 and right <= width and bottom <= height, 'Padding outside page')
                for other_id, (other_page, ox, oy) in enumerate(tis['entries']):
                    if other_page != page or other_id == tile:
                        continue
                    require(max(left, ox-4) >= min(right, ox+260)
                            or max(top, oy-4) >= min(bottom, oy+260), 'Selected padding overlaps another tile')
                bx, by = left//4, top//4
                view = blocks[by:by+66, bx:bx+66]
                if tile in central_ids:
                    view[:, :, :8] = [native_alpha, native_alpha, 0, 0, 0, 0, 0, 0]
                    allowed_alpha[by:by+66, bx:bx+66] = True
                if tile in secondary_alpha:
                    mask = block_mask(secondary_alpha[tile] > 0)
                    view[mask, :8] = [255, 255, 0, 0, 0, 0, 0, 0]
                    allowed_alpha[by:by+66, bx:bx+66] |= mask
                if tile in rgb:
                    cx, cy = coords[tile]
                    core = np.array(decoded.crop((x, y, x+256, y+256)).convert('RGBA'))
                    replacement = np.asarray(donor.crop((cx*256, cy*256, (cx+1)*256, (cy+1)*256)).convert('RGB'))
                    weight = rgb[tile][:, :, None]
                    strong = weight[:, :, 0] == 1
                    difference = float(np.abs(core[:, :, :3][strong].astype(float) - replacement[strong]).mean())
                    do_repair = difference > threshold
                    report['rgb_tiles'].append({'tile': tile, 'mean_absolute_donor_difference': difference,
                                                'repaired': do_repair})
                    if do_repair:
                        core[:, :, :3] = np.rint(core[:, :, :3]*(1-weight) + replacement*weight).clip(0, 255).astype(np.uint8)
                        stream = io.BytesIO()
                        Image.fromarray(np.pad(core, ((4, 4), (4, 4), (0, 0)), mode='edge')).save(
                            stream, format='DDS', pixel_format='DXT5')
                        encoded = stream.getvalue()
                        require(encoded[84:88] == b'DXT5' and len(encoded) == 128+66*66*16,
                                'Pillow did not produce BC3 DDS; use the bundled runtime with DXT5 encoder support')
                        coded = np.frombuffer(encoded, np.uint8, offset=128).reshape(66, 66, 16)
                        mask = block_mask(weight[:, :, 0] > 0)
                        view[mask, 8:] = coded[mask, 8:]
                        allowed_rgb[by:by+66, bx:bx+66] |= mask
            require(np.array_equal(original[~allowed_rgb, 8:], blocks[~allowed_rgb, 8:]), 'RGB outside mask changed')
            require(np.array_equal(original[~allowed_alpha, :8], blocks[~allowed_alpha, :8]), 'Alpha outside mask changed')
            rgb_count = int(np.any(original[:, :, 8:] != blocks[:, :, 8:], axis=2).sum())
            alpha_count = int(np.any(original[:, :, :8] != blocks[:, :, :8], axis=2).sum())
            if rgb_count or alpha_count:
                result = struct.pack('<I', len(raw)) + zlib.compress(raw, 9)
                require(zlib.decompress(result[4:]) == raw, 'PVRZ serialization mismatch')
        if write:
            (output / name).write_bytes(result)
        report['pages'].append({'name': name, 'bytes': len(result), 'sha256': digest(result),
                                'source_sha256': None if page in relocated_pages else digest(packed),
                                'isolated_page': page in relocated_pages, 'rgb_blocks_changed': rgb_count,
                                'alpha_blocks_changed': alpha_count})
    if donor:
        donor.close()
    _pvrz_page_cache.clear()
    report['summary'] = {'central_tiles': len(central_ids), 'interfaces': len(interfaces),
                         'rgb_tiles_repaired': sum(t['repaired'] for t in report['rgb_tiles']),
                         'pages_changed': sum(p['source_sha256'] != p['sha256'] for p in report['pages']),
                         'alpha_blocks_changed': sum(p['alpha_blocks_changed'] for p in report['pages']),
                         'rgb_blocks_changed': sum(p['rgb_blocks_changed'] for p in report['pages']),
                         'tis_byte_exact': not relocations, 'isolated_tiles': len(relocations),
                         'outside_selected_blocks_byte_exact': True}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vanilla-root', type=Path, required=True)
    parser.add_argument('--game-root', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    vanilla_root = args.vanilla_root.resolve(strict=True)
    game_root = args.game_root.resolve(strict=True)
    output = args.output.resolve()
    require(vanilla_root != game_root, 'Vanilla and target game roots must be distinct')
    require((vanilla_root / 'chitin.key').is_file(), 'Vanilla KEY missing')
    require((game_root / 'override').is_dir(), 'Live override missing')
    require(ROOT in output.parents and output != ROOT, 'Output must be a new workspace subdirectory')
    require(not output.exists(), 'Output already exists; use a new trial directory')
    require(not any(part in {'.git', '.agents', '.codex', 'releases'} for part in output.relative_to(ROOT).parts),
            'Output cannot be configuration, Git, agents or release')
    plan_bytes = args.plan.read_bytes()
    plan = json.loads(plan_bytes.decode('utf-8-sig'))
    targets = plan['targets']
    names = [resource_name(t['wed']) for t in targets]
    require(targets and len(names) == len(set(names)), 'Empty or duplicate WED targets')
    os.environ['BG2EE_GAME_ROOT'] = str(vanilla_root)
    import bg2lib
    bg2lib.GAME_DIR = str(vanilla_root)
    bg2lib.KEY_PATH = str(vanilla_root / 'chitin.key')
    bg2lib._bif_cache.clear()
    bifs, resources = bg2lib.load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in resources}
    pvr = {name.upper(): (name, kind, locator) for name, kind, locator in resources if kind == 0x404}
    report = {'schema': 'bg2-liquid-base-x4-trial-v1', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'plan_sha256': digest(plan_bytes), 'producer_sha256': file_digest(Path(__file__)),
              'vanilla_root': str(vanilla_root), 'live_game_root': str(game_root), 'maps': [],
              'status': 'built-pending-ingame-qa' if args.run else 'read-only-plan',
              'installation': 'not-run', 'release': 'not-requested'}
    for target in targets:
        try:
            row = process_target(target, (bifs, index, pvr), game_root / 'override', output, args.run)
        except Exception as error:
            report['status'] = 'failed-partial'
            report['failure'] = {'wed': target['wed'], 'error': str(error)}
            if args.run and output.exists():
                (output / 'base-repair-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            raise
        report['maps'].append(row)
        print(json.dumps({'wed': row['wed'], **row['summary']}), flush=True)
    if args.run:
        (output / 'base-repair-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    else:
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
