"""AR1600 whole map: x4 RGB matte contours on every qualified water pair.

Recipe validated ingame on the ship zone (``build_water_contour_matte_trial.py``);
same functions, no local transition ramp.  Windows of 8x8 WED cells with a one-cell
halo keep every neighbourhood operation continuous across tiles.  Source pages are
pre-Astra for the pages the earlier trials changed, live otherwise.
prepare: SciPy/NumPy/Pillow; encode: Pillow 12 BC3.  Installation is separate.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, defaultdict
import json
from pathlib import Path
import struct
import zlib

import numpy as np
from PIL import Image

import bg2lib
from area_decode import decode_tis_tiles
from build_water_contour_matte_trial import (composite, edge_rgb, extend_colours, read, require,
                                             silhouette, sha, source_pages, write)
from build_water_contour_trial import alpha_block_exact_endpoints, blocks_encode
from build_water_route1_batch import parse_wed, parse_standalone_tis, parse_pvr
from mos_decode import decode_pvrz_page
from workspace_paths import ROOT, get_path

AREA, WINDOW = 'AR1600', 8


def door_cells(wed):
    count, offset, tiles = (struct.unpack_from('<I', wed, o)[0] for o in (0x0C, 0x18, 0x1C))
    cells = set()
    for i in range(count):
        first, n = struct.unpack_from('<HH', wed, offset + i * 26 + 10)
        cells.update(struct.unpack_from(f'<{n}H', wed, tiles + first * 2))
    return cells


def prepare(args):
    output = args.output.resolve()
    output.relative_to(ROOT / 'maps')
    require(not output.exists(), 'Refusing to overwrite an existing run')
    game = get_path('bg2ee_game_root', required=True)
    live = game / 'override'
    originals, _ = source_pages(live)
    bg2lib.GAME_DIR = str(args.vanilla_root)
    bg2lib.KEY_PATH = str(args.vanilla_root / 'chitin.key')
    bifs, resources = bg2lib.load_key()
    lookup = {(n.upper(), k): loc for n, k, loc in resources}
    pvr = {n.upper(): (n, k, loc) for n, k, loc in resources if k == 0x404}
    native_wed, _ = bg2lib.resolve_resource(bifs, lookup[AREA, 0x3e9])
    parsed = parse_wed(native_wed)
    require(parsed['cells'] == parse_wed((live / (AREA + '.WED')).read_bytes())['cells'], 'WED base geometry changed')
    base = parsed['layers'][0]
    prefix = base['tis'][0] + base['tis'][2:]
    tis = parse_standalone_tis((live / (base['tis'] + '.TIS')).read_bytes())
    stock, _ = decode_tis_tiles(bifs, pvr, base['tis'], lookup[base['tis'], 0x3eb])
    are, _ = bg2lib.resolve_resource(bifs, lookup[AREA, 0x3f2])
    water_alpha = are[0x52] or 128
    require(water_alpha == 128, 'Unexpected WATER_ALPHA contract')
    doors = door_cells(native_wed)
    physical = Counter(tis['entries'])
    logical = Counter(t for c in parsed['cells'] for t in c['primary'])
    logical.update(c['secondary'] for c in parsed['cells'] if c['secondary'] != 65535)
    grid = {(c['x'], c['y']): c for c in parsed['cells']}
    qualified, skipped = {}, Counter()
    for i, c in enumerate(parsed['cells']):
        if not c['flags'] & 2 or c['secondary'] == 65535:
            continue
        p, s = c['primary'][0], c['secondary']
        reason = ('animated' if c['count'] != 1 else 'door' if i in doors else
                  'shared' if max(logical[p], logical[s], physical[tis['entries'][p]],
                                  physical[tis['entries'][s]]) != 1 else None)
        if reason is None and not np.all(np.asarray(stock(p))[:, :, 3].astype(int)
                                         + np.asarray(stock(s))[:, :, 3] == 255):
            reason = 'non-complementary'
        if reason:
            skipped[reason] += 1
        else:
            qualified[(c['x'], c['y'])] = c
    cache, hashes = OrderedDict(), {}

    def tile(index):
        page, px, py = tis['entries'][index]
        name = f'{prefix}{page:02d}.PVRZ'
        if page not in cache:
            data = originals.get(name) or (live / name).read_bytes()
            hashes[name] = sha(data)
            cache[page] = decode_pvrz_page(data)
            if len(cache) > 12:
                cache.popitem(last=False)
        return np.array(cache[page].crop((px, py, px + 256, py + 256)))

    output.mkdir(parents=True)
    (output / 'tiles').mkdir()
    records, colour = [], Counter()
    a = water_alpha / 255
    windows = sorted({(x // WINDOW, y // WINDOW) for x, y in qualified})
    for n, (wx, wy) in enumerate(windows, 1):
        x0, y0, size = wx * WINDOW - 1, wy * WINDOW - 1, WINDOW + 2
        shape = (size * 256, size * 256)
        primary, secondary = [np.zeros((*shape, 4), np.uint8) for _ in range(2)]
        native = np.zeros(shape, bool)
        cell_slice = lambda cx, cy: np.s_[(cy - y0) * 256:(cy - y0 + 1) * 256, (cx - x0) * 256:(cx - x0 + 1) * 256]
        for cy in range(y0, y0 + size):
            for cx in range(x0, x0 + size):
                c = grid.get((cx, cy))
                if c is None or c['count'] != 1 or tis['entries'][c['primary'][0]][0] == 0xffffffff:
                    continue
                sl = cell_slice(cx, cy)
                primary[sl] = tile(c['primary'][0])
                native[sl] = (np.asarray(stock(c['primary'][0]))[:, :, 3] > 127).repeat(4, 0).repeat(4, 1)
                if (cx, cy) in qualified:
                    secondary[sl] = tile(c['secondary'])
        obj, coverage = silhouette(primary[:, :, :3], native)
        rgb_p, report = edge_rgb(primary[:, :, :3], obj)
        colour.update(report)
        rgb_s = extend_colours(secondary[:, :, :3], secondary[:, :, 3] > 127)
        p_alpha = np.where(coverage > 0, coverage / (1 - a * (1 - coverage)), 0.0)
        for (cx, cy), c in qualified.items():
            if (cx // WINDOW, cy // WINDOW) != (wx, wy):
                continue
            sl = cell_slice(cx, cy)
            for role, old, rgb, alpha, index in [('primary', primary, rgb_p, p_alpha, c['primary'][0]),
                                                  ('secondary', secondary, rgb_s, 1 - coverage, c['secondary'])]:
                target = old[sl].copy()
                target[:, :, :3] = rgb[sl]
                target[:, :, 3] = np.rint(alpha[sl] * 255).clip(0, 255).astype(np.uint8)
                if not np.any(target != old[sl]):
                    continue
                Image.fromarray(target).save(output / 'tiles' / f'{index}-{role}.png')
                records.append({'tile': index, 'role': role, 'cell': [cx, cy],
                                'entry': list(tis['entries'][index]), 'png': f'tiles/{index}-{role}.png'})
        print(f'window {n}/{len(windows)} ({wx},{wy})', flush=True)
    write(output / 'prepare.json', {
        'schema': 'bg2-water-contour-matte-map-v1', 'area': AREA, 'scope': 'whole map, qualified water pairs',
        'water_alpha': water_alpha, 'qualified_pairs': len(qualified), 'skipped': dict(skipped),
        'recipe': 'build_water_contour_matte_trial.py silhouette/edge_rgb/extend_colours, no transition ramp',
        'composition': 'U -> P -> a*S; S=1-M; P=M/(1-a*(1-M))', 'window_cells': WINDOW, 'halo_cells': 1,
        'colour': dict(colour), 'source_pages': hashes, 'astra_restored_pages': sorted(originals),
        'tiles': records, 'producer_sha256': sha(Path(__file__).read_bytes()), 'installation': 'not performed'})
    print(json.dumps({'qualified_pairs': len(qualified), 'skipped': dict(skipped), 'tiles': len(records)}), flush=True)


def encode(args):
    run = args.output.resolve(strict=True)
    run.relative_to(ROOT / 'maps')
    plan = read(run / 'prepare.json')
    candidate = run / 'override-candidate'
    require(not candidate.exists(), 'Candidate already exists')
    live = get_path('bg2ee_game_root', required=True) / 'override'
    originals, _ = source_pages(live)
    for name, digest in plan['source_pages'].items():
        require(sha(originals.get(name) or (live / name).read_bytes()) == digest, 'Source page drift: ' + name)
    candidate.mkdir()
    groups = defaultdict(list)
    for t in plan['tiles']:
        groups[t['entry'][0]].append(t)
    files, pages_report, finals = {}, [], {}
    for page, tiles in sorted(groups.items()):
        name = f'A1600{page:02d}.PVRZ'
        packed = originals.get(name) or (live / name).read_bytes()
        raw, fmt, width, height, offset = parse_pvr(packed)
        require(fmt == 11, 'Expected existing BC3 page')
        original = np.frombuffer(bytes(raw), np.uint8, offset=offset).reshape(height // 4, width // 4, 16)
        blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height // 4, width // 4, 16)
        allowed_a, allowed_rgb = [np.zeros(blocks.shape[:2], bool) for _ in range(2)]
        decoded = np.asarray(decode_pvrz_page(packed))
        for t in tiles:
            _, px, py = t['entry']
            require((px % 264, py % 264) == (4, 4), 'Unqualified atlas padding')
            current = decoded[py - 4:py + 260, px - 4:px + 260]
            core = np.asarray(Image.open(run / t['png']))
            target = np.pad(core, ((4, 4), (4, 4), (0, 0)), mode='edge')
            changed = np.pad(core != decoded[py:py + 256, px:px + 256], ((4, 4), (4, 4), (0, 0)), mode='edge')
            target = np.where(changed, target, current)
            ma = changed[:, :, 3].reshape(66, 4, 66, 4).any((1, 3))
            mr = changed[:, :, :3].any(2).reshape(66, 4, 66, 4).any((1, 3))
            coded = blocks_encode(target).copy()
            alpha_blocks = target[:, :, 3].reshape(66, 4, 66, 4).transpose(0, 2, 1, 3).reshape(66, 66, 16)
            for iy, ix in zip(*np.nonzero(ma)):
                coded[iy, ix, :8] = np.frombuffer(alpha_block_exact_endpoints(alpha_blocks[iy, ix].tobytes()), np.uint8)
            bx, by = (px - 4) // 4, (py - 4) // 4
            view = blocks[by:by + 66, bx:bx + 66]
            view[ma, :8] = coded[ma, :8]
            view[mr, 8:] = coded[mr, 8:]
            allowed_a[by:by + 66, bx:bx + 66] |= ma
            allowed_rgb[by:by + 66, bx:bx + 66] |= mr
        require(np.array_equal(original[~allowed_a, :8], blocks[~allowed_a, :8]), 'Unrelated alpha block changed')
        require(np.array_equal(original[~allowed_rgb, 8:], blocks[~allowed_rgb, 8:]), 'Unrelated RGB block changed')
        data = struct.pack('<I', len(raw)) + zlib.compress(raw, 9)
        (candidate / name).write_bytes(data)
        final = np.asarray(decode_pvrz_page(data))
        for t in tiles:
            _, px, py = t['entry']
            finals[(t['role'], tuple(t['cell']))] = final[py:py + 256, px:px + 256].copy()
        files[name] = {'sha256': sha(data), 'bytes': len(data)}
        pages_report.append({'name': name, 'before_sha256': sha(packed), 'after_sha256': sha(data),
                             'alpha_blocks_changed': int(np.any(original[:, :, :8] != blocks[:, :, :8], 2).sum()),
                             'rgb_blocks_changed': int(np.any(original[:, :, 8:] != blocks[:, :, 8:], 2).sum())})
        print('Encoded ' + name, flush=True)
    for name, data in originals.items():          # earlier trial pages without changes: pre-Astra bytes
        if name not in files:
            (candidate / name).write_bytes(data)
            files[name] = {'sha256': sha(data), 'bytes': len(data)}
            pages_report.append({'name': name, 'restored_pre_astra': True})
    a = plan['water_alpha'] / 255
    pngs = {(t['role'], tuple(t['cell'])): t['png'] for t in plan['tiles']}
    errors = []
    for cell in {c for _, c in pngs}:
        if ('primary', cell) not in finals or ('secondary', cell) not in finals:
            continue
        dp, ds = [np.asarray(Image.open(run / pngs[(r, cell)]))[:, :, 3] / 255. for r in ('primary', 'secondary')]
        intended = dp * (1 - a * ds)
        effective = finals[('primary', cell)][:, :, 3] / 255. * (1 - a * finals[('secondary', cell)][:, :, 3] / 255.)
        edge = (intended > 0) & (intended < 1)
        errors.append(np.abs(effective - intended)[edge])
    err = np.concatenate(errors)
    require(len(err) > 0 and float(err.mean()) < .03, 'Excessive BC3 coverage error')
    write(candidate / 'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1', 'status': 'completed',
          'area': AREA, 'scope': 'whole-map water contours (x4 RGB matte)', 'files': files})
    write(run / 'build.json', {'schema': 'bg2-water-contour-matte-map-build-v1', 'area': AREA, 'pages': pages_report,
          'tiles': len(plan['tiles']), 'bc3_edge_effective_coverage_error': {
              'mean': float(err.mean()), 'p99': float(np.percentile(err, 99)), 'max': float(err.max()), 'samples': len(err)},
          'outside_selected_blocks': 'byte-exact vs source pages', 'temporal_water': 'no WED/TIS/overlay/DLL change',
          'prepare_sha256': sha((run / 'prepare.json').read_bytes()), 'producer_sha256': sha(Path(__file__).read_bytes()),
          'installation': 'not performed', 'qa': 'pending-user-ingame'})
    print(json.dumps({'pages': len(files), 'tiles': len(plan['tiles']), 'coverage_mean_error': float(err.mean())}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stage', choices=['prepare', 'encode'])
    parser.add_argument('--vanilla-root', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.stage == 'prepare':
        require(args.vanilla_root is not None, 'Missing --vanilla-root')
        prepare(args)
    else:
        encode(args)


if __name__ == '__main__':
    main()
