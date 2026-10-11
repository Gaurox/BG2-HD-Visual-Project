"""AR3000: repair witnessed RGB fringes only; keep every BC3 alpha byte intact.

python -B pipeline/recipes/ar3000-rgb-edge-fix-20261011-v1/build.py --vanilla <native-root>
Output is immutable, installation is separate.
"""
import argparse
import hashlib
import json
import struct
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import bg2lib
from area_decode import decode_tis_tiles
from bc3_refined import encode_bc3
from build_liquid_base_x4_trial import block_mask, rgb_seam_difference, seam_masks
from build_water_route1_batch import parse_pvr, parse_standalone_tis, parse_wed
from mos_decode import decode_pvrz_page
from workspace_paths import get_path

Image.MAX_IMAGE_PIXELS = None
RUN = ROOT / 'maps/water-batches/runs/ar3000-rgb-edge-fix-20261011-v1'
BASELINE = ROOT / 'maps/water-batches/runs/ar3000-contour-matte-20260929-v2/override-candidate/A300010.PVRZ'
DONOR = ROOT / ('maps/AR3000/runs/seedvr2-7b-int8-lab-x4-primary-secondary-grid3x2/'
                'tuiles-secondaires/03_assemble/AR3000-tuiles-secondaires-x4-seedvr2-7b-int8-lab-overlap.png')
SELECTED = {(491, 'right'), (533, 'bottom')}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vanilla', type=Path, required=True)
    args = parser.parse_args()
    live = get_path('bg2ee_game_root', required=True) / 'override'
    source = (live / 'A300010.PVRZ').read_bytes()
    assert source == BASELINE.read_bytes(), 'Live page differs from the diagnosed contour baseline'
    tis_bytes = (live / 'AR3000.TIS').read_bytes()
    tis = parse_standalone_tis(tis_bytes)
    bg2lib.GAME_DIR = str(args.vanilla.resolve(strict=True))
    bg2lib.KEY_PATH = str(Path(bg2lib.GAME_DIR) / 'chitin.key')
    bifs, resources = bg2lib.load_key()
    index = {(name, kind): loc for name, kind, loc in resources}
    pvr = {name: (name, kind, loc) for name, kind, loc in resources if kind == 0x404}
    wed_bytes, _ = bg2lib.resolve_resource(bifs, index['AR3000', 0x3E9])
    parsed = parse_wed(wed_bytes)
    assert parsed['layers'][0]['tis'] == 'AR3000'
    stock_tile, _ = decode_tis_tiles(bifs, pvr, 'AR3000', index['AR3000', 0x3EB])
    physical = Counter(tis['entries'])
    primary = defaultdict(list)
    secondary = Counter(c['secondary'] for c in parsed['cells'] if c['secondary'] != 65535)
    for cell in parsed['cells']:
        for tile in cell['primary']:
            primary[tile].append(cell)
    unique_primary = {tile for tile, uses in primary.items() if len(uses) == 1 and tile not in secondary}
    unique_secondary = {tile for tile, count in secondary.items()
                        if count == 1 and tile not in primary and physical[tis['entries'][tile]] == 1}
    full_cells = {}
    for tile in unique_primary:
        cell = primary[tile][0]
        if cell['count'] == 1 and cell['secondary'] == 65535 and cell['flags'] & 30:
            if np.all(np.asarray(stock_tile(tile))[:, :, 3] == 255):
                full_cells[cell['x'], cell['y']] = tile
    masks, _, coords, interfaces = seam_masks(parsed, [[1, 2, 3, 4]], full_cells,
        stock_tile, unique_primary, unique_secondary, selected_interfaces=SELECTED)
    assert {(i['primary'], i['side']) for i in interfaces} == SELECTED
    assert {t: coords[t] for t in masks} == {491: (29, 11), 533: (29, 12)}
    raw, fmt, width, height, offset = parse_pvr(source)
    assert fmt == 11
    original = np.frombuffer(bytes(raw), np.uint8, offset=offset).reshape(height//4, width//4, 16)
    blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(original.shape)
    allowed = np.zeros(blocks.shape[:2], bool)
    before = decode_pvrz_page(source).convert('RGBA')
    reports = []
    previews = []
    with Image.open(DONOR) as donor:
        assert donor.size == (parsed['layers'][0]['width']*256, parsed['layers'][0]['height']*256)
        for tile in sorted(masks):
            page, x, y = tis['entries'][tile]
            assert page == 10 and physical[page, x, y] == 1
            assert (x % 264, y % 264) == (4, 4)
            assert 0 <= x-4 < x+260 <= width and 0 <= y-4 < y+260 <= height
            for other, (op, ox, oy) in enumerate(tis['entries']):
                if op == page and other != tile:
                    assert max(x-4, ox-4) >= min(x+260, ox+260) or max(y-4, oy-4) >= min(y+260, oy+260)
            cx, cy = coords[tile]
            core = np.array(before.crop((x, y, x+256, y+256)))
            assert np.all(core[:, :, 3] == 160)
            replacement = np.array(donor.crop((cx*256, cy*256, (cx+1)*256, (cy+1)*256)).convert('RGB'))
            metrics = rgb_seam_difference(core, replacement, masks[tile])
            assert max(metrics.values()) > 6
            weight = masks[tile][:, :, None]
            core[:, :, :3] = np.rint(core[:, :, :3]*(1-weight) + replacement*weight).clip(0,255).astype(np.uint8)
            coded = np.frombuffer(encode_bc3(np.pad(core, ((4,4),(4,4),(0,0)), mode='edge')),
                                  np.uint8).reshape(66,66,16)
            mask = block_mask(masks[tile] > 0)
            bx, by = (x-4)//4, (y-4)//4
            view = blocks[by:by+66, bx:bx+66]
            view[mask, 8:] = coded[mask, 8:]
            allowed[by:by+66, bx:bx+66] |= mask
            reports.append({'tile': tile, 'cell': [cx,cy], 'side': next(s for t,s in SELECTED if t==tile),
                            'before_donor_difference': metrics, 'allowed_rgb_blocks': int(mask.sum())})
            previews.append((tile, x, y, replacement))
    assert np.array_equal(original[:, :, :8], blocks[:, :, :8]), 'Alpha changed'
    assert np.array_equal(original[~allowed, 8:], blocks[~allowed, 8:]), 'RGB outside footprint changed'
    assert raw[:offset] == parse_pvr(source)[0][:offset]
    result = struct.pack('<I', len(raw)) + zlib.compress(raw, 9)
    after = decode_pvrz_page(result).convert('RGBA')
    assert np.array_equal(np.asarray(before)[:, :, 3], np.asarray(after)[:, :, 3])
    # BC3 writes cover entire 4x4 blocks. Assert decoded pixels outside that footprint stay exact.
    pixel_allowed = allowed.repeat(4, 0).repeat(4, 1)
    assert np.array_equal(np.asarray(before)[~pixel_allowed], np.asarray(after)[~pixel_allowed])
    for report, (tile, x, y, replacement) in zip(reports, previews):
        fixed = np.array(after.crop((x,y,x+256,y+256)))
        metrics = rgb_seam_difference(fixed, replacement, masks[tile])
        report['after_donor_difference'] = metrics
        side = report['side']
        assert metrics[side] < 4 and metrics[side] < report['before_donor_difference'][side]/4
    RUN.mkdir(parents=True, exist_ok=False)
    candidate = RUN / 'override-candidate'
    candidate.mkdir()
    (candidate / 'A300010.PVRZ').write_bytes(result)
    write_json(candidate / 'manifest.json', {'schema':'bg2-upscale-area-animation-override-assets-v1',
        'status':'completed','area':'AR3000','files':{'A300010.PVRZ':{'bytes':len(result),'sha256':sha(result)}}})
    for tile,x,y,_ in previews:
        preview = Image.new('RGBA',(528,264))
        preview.paste(before.crop((x-4,y-4,x+260,y+260)),(0,0))
        preview.paste(after.crop((x-4,y-4,x+260,y+260)),(264,0))
        preview.convert('RGB').save(RUN / f'tile-{tile}-before-after.png')
    write_json(RUN / 'build.json', {'schema':'bg2-water-rgb-edge-repair-v1','area':'AR3000',
        'source':'config://bg2ee_game_root/override/A300010.PVRZ', 'source_sha256':sha(source),
        'output_sha256':sha(result),'tis_sha256':sha(tis_bytes),'wed_sha256':sha(wed_bytes),
        'donor':DONOR.relative_to(ROOT).as_posix(),'donor_sha256':sha(DONOR.read_bytes()),
        'encoder':'bc3_refined.encode_bc3; selective RGB blocks only; 4px replicated padding',
        'tiles':reports,'rgb_blocks_changed':int(np.any(original[:,:,8:] != blocks[:,:,8:],axis=2).sum()),
        'alpha_blocks_changed':0, 'outside_footprint_byte_exact':True,
        'decoded_alpha_byte_exact':True,'qa':'pending-ingame','installation':'separate receipt'})
    print(json.dumps({'run':str(RUN),'tiles':reports,'output_sha256':sha(result)}, indent=2))


if __name__ == '__main__':
    main()
