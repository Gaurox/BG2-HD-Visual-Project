"""Local WED foreground-mask trial; writes PNG previews only, never game assets.

Native geometry -> bounded Potrace curves -> supersampled x4 coverage.
The before mask uses installed primary alpha at real contours. Fully-water
cells are normalized to zero geometry, independently of their art opacity.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
# The locally available Potrace port is pure Python. Keep the interpreter's
# already imported NumPy rather than loading a different vendored NumPy ABI.
sys.path.append(str(ROOT / '.tools/potracer'))
import potrace
import bg2lib
from area_decode import decode_tis_tiles
from build_water_route1_batch import parse_wed
from mos_decode import decode_pvrz_page
from workspace_paths import get_path


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def components(binary, diagonal=False):
    """Count connected components by unioning horizontal runs, including border contact."""
    parents, areas, border = [], [], []
    previous = []
    height, width = binary.shape

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for y, row in enumerate(binary):
        diff = np.diff(np.pad(row.astype(np.int8), (1, 1)))
        starts, ends = np.flatnonzero(diff == 1), np.flatnonzero(diff == -1)
        current = []
        cursor = 0
        for x0, x1 in zip(starts, ends):
            i = len(parents)
            parents.append(i)
            areas.append(int(x1 - x0))
            border.append(y in (0, height - 1) or x0 == 0 or x1 == width)
            margin = int(diagonal)
            while cursor < len(previous) and previous[cursor][1] + margin <= x0:
                cursor += 1
            j = cursor
            while j < len(previous) and previous[j][0] < x1 + margin:
                p = root(previous[j][2])
                r = root(i)
                if p != r:
                    parents[p] = r
                    areas[r] += areas[p]
                    border[r] |= border[p]
                j += 1
            current.append((int(x0), int(x1), i))
        previous = current
    roots = [i for i in range(len(parents)) if parents[i] == i]
    return {'count': len(roots), 'enclosed': sum(not border[i] for i in roots),
            'areas': sorted(areas[i] for i in roots)}


def topology(mask):
    solid = mask >= 128
    return {'foreground_8': components(solid, True),
            'background_4': components(~solid, False)}


def edge_band(binary, radius):
    padded = np.pad(binary, radius, mode='edge')
    band = np.zeros_like(binary)
    h, w = binary.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy <= radius * radius:
                band |= binary != padded[radius+dy:radius+dy+h, radius+dx:radius+dx+w]
    return band


def trace_mask(native, alphamax, supersample):
    scale = 4 * supersample
    h, w = native.shape
    paths = potrace.Bitmap(~native).trace(turdsize=0, alphamax=alphamax,
                                         turnpolicy=potrace.POTRACE_TURNPOLICY_BLACK,
                                         opticurve=True, opttolerance=0.1)
    merged = Image.new('1', (w*scale, h*scale))
    rings = 0
    for curve in paths:
        current = np.array([curve.start_point.x, curve.start_point.y])
        points = [current]
        for segment in curve.segments:
            end = np.array([segment.end_point.x, segment.end_point.y])
            if segment.is_corner:
                points.extend([np.array([segment.c.x, segment.c.y]), end])
            else:
                c1 = np.array([segment.c1.x, segment.c1.y])
                c2 = np.array([segment.c2.x, segment.c2.y])
                length = np.linalg.norm(c1-current)+np.linalg.norm(c2-c1)+np.linalg.norm(end-c2)
                t = np.linspace(0, 1, max(4, int(np.ceil(length*scale)))+1)[1:, None]
                points.extend((1-t)**3*current + 3*(1-t)**2*t*c1 + 3*(1-t)*t*t*c2 + t**3*end)
            current = end
        layer = Image.new('1', merged.size)
        ImageDraw.Draw(layer).polygon([tuple(p*scale) for p in points], fill=1)
        merged = ImageChops.logical_xor(merged, layer)
        rings += 1
    high = np.asarray(merged, dtype=np.uint8).reshape(h*4, supersample, w*4, supersample)
    return np.rint(high.mean(axis=(1, 3))*255).astype(np.uint8), rings


def comparison(before, after, output, zoom=None):
    if zoom is not None:
        before, after = before.crop(zoom), after.crop(zoom)
        size = (before.width*2, before.height*2)
        before, after = [i.resize(size, Image.Resampling.NEAREST) for i in (before, after)]
    else:
        size = (768, round(before.height*768/before.width))
        before, after = [i.resize(size, Image.Resampling.LANCZOS) for i in (before, after)]
    width, height = before.size
    canvas = Image.new('RGB', (width*2+36, height+120), (24, 28, 33))
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 23)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 17)
    draw = ImageDraw.Draw(canvas)
    for x, title, image in [(12, 'AVANT — masque HD installé', before),
                            (width+24, 'APRÈS — contour vectorisé', after)]:
        draw.text((x, 12), title, font=font, fill='white')
        canvas.paste(image.convert('RGB'), (x, 55))
    draw.text((12, height+72), 'Blanc : décor devant l’eau   •   Noir : eau   •   Gris : couverture partielle',
              font=small, fill=(220, 225, 230))
    draw.text((12, height+96), 'Essai de masque uniquement — hors jeu, avant compression BC3',
              font=small, fill=(175, 185, 195))
    canvas.save(output)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--area', default='AR1600')
    ap.add_argument('--vanilla-root', type=Path, required=True)
    ap.add_argument('--rect-x1', type=int, nargs=4, required=True, metavar=('X', 'Y', 'W', 'H'))
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--alphamax', type=float, default=0.8)
    args = ap.parse_args()
    area = args.area.upper()
    x, y, w, h = args.rect_x1
    if any(v % 64 for v in (x, y, w, h)) or min(x, y) < 0 or min(w, h) <= 0:
        raise ValueError('Use a positive, tile-aligned rectangle')
    output = args.output.resolve()
    output.relative_to(ROOT/'maps')
    if output.exists():
        raise FileExistsError(output)
    bg2lib.GAME_DIR = str(args.vanilla_root)
    bg2lib.KEY_PATH = str(args.vanilla_root/'chitin.key')
    bifs, resources = bg2lib.load_key()
    lookup = {(n.upper(), k): locator for n, k, locator in resources}
    pvr = {n.upper(): (n, k, locator) for n, k, locator in resources if k == 0x404}
    wed, archive = bg2lib.resolve_resource(bifs, lookup[area, 0x3e9])
    parsed = parse_wed(wed)
    base = parsed['layers'][0]
    if any(c['count'] != 1 for c in parsed['cells']):
        raise ValueError('Animated base geometry is outside this mask-only trial')
    if x+w > base['width']*64 or y+h > base['height']*64:
        raise ValueError('ROI outside WED')
    stock, _ = decode_tis_tiles(bifs, pvr, base['tis'], lookup[base['tis'], 0x3eb])
    game = get_path('bg2ee_game_root')
    tis_path = game/'override'/(base['tis']+'.TIS')
    tis = tis_path.read_bytes()
    count, entry, start, size = struct.unpack_from('<4I', tis, 8)
    if entry != 12 or size != 256:
        raise ValueError('Expected installed x4 TIS')
    # Full tile of context on every side avoids processing the cropped silhouette.
    left, top = max(0, x-64), max(0, y-64)
    right, bottom = min(base['width']*64, x+w+64), min(base['height']*64, y+h+64)
    nw, nh = right-left, bottom-top
    native = np.zeros((nh, nw), bool)
    before = np.zeros((nh*4, nw*4), np.uint8)
    art = Image.new('RGB', (nw*4, nh*4))
    pages = OrderedDict()
    hashes, cells_report = {}, []
    bitmask = sum(1 << l['slot'] for l in parsed['layers'][1:] if l['tis'].startswith(('WT', 'YS')))
    for cell in parsed['cells']:
        cx, cy = cell['x']*64, cell['y']*64
        if not (left <= cx < right and top <= cy < bottom):
            continue
        index = cell['primary'][0]
        source = np.asarray(stock(index))[:, :, 3]
        page, px, py = struct.unpack_from('<3I', tis, start+index*12)
        if page == 0xffffffff:
            image = Image.new('RGBA', (256, 256), (0, 0, 0, 255))
        else:
            name = f'{base["tis"][0]+base["tis"][2:]}{page:02d}.PVRZ'
            if page not in pages:
                data = (game/'override'/name).read_bytes()
                hashes[name] = sha(data)
                if len(pages) >= 6:
                    pages.popitem(last=False)
                pages[page] = decode_pvrz_page(data)
            image = pages[page].crop((px, py, px+256, py+256))
        alpha = np.array(image.getchannel('A'))
        full_water = bool(cell['flags'] & bitmask) and cell['secondary'] == 65535 and bool(np.all(source == 255))
        if full_water:
            source = np.zeros_like(source)
            alpha[:] = 0
        ix, iy = cx-left, cy-top
        native[iy:iy+64, ix:ix+64] = source > 127
        before[iy*4:iy*4+256, ix*4:ix*4+256] = alpha
        art.paste(image.convert('RGB'), (ix*4, iy*4))
        cells_report.append({'cell': [cell['x'], cell['y']], 'primary': index,
                             'secondary': cell['secondary'], 'normalized_full_water': full_water})
    traced, rings = trace_mask(native, args.alphamax, 4)
    source4 = native.repeat(4, 0).repeat(4, 1)
    band = edge_band(source4, 2)
    after = np.where(band, traced, before).astype(np.uint8)
    rect = ((x-left)*4, (y-top)*4, (x+w-left)*4, (y+h-top)*4)
    crop = lambda a: a[rect[1]:rect[3], rect[0]:rect[2]]
    old, new = crop(before), crop(after)
    old_top, new_top = topology(old), topology(new)
    native_top = topology(crop(source4).astype(np.uint8)*255)
    valid = all(native_top[k]['count'] == new_top[k]['count'] and
                native_top[k]['enclosed'] == new_top[k]['enclosed'] for k in native_top)
    output.mkdir(parents=True)
    before_im, after_im = Image.fromarray(old), Image.fromarray(new)
    before_im.save(output/'mask-before.png')
    after_im.save(output/'mask-after.png')
    Image.fromarray(crop(source4).astype(np.uint8)*255).save(output/'mask-native-nearest.png')
    art.crop(rect).save(output/'foreground-rgb-reference.png')
    comparison(before_im, after_im, output/'comparison.png')
    report = {'schema': 'bg2-water-contour-mask-preview-v1', 'area': area,
              'rect_x1': args.rect_x1, 'context_x1': 64, 'source_wed_archive': archive,
              'source_wed_sha256': sha(wed), 'installed_tis_sha256': sha(tis),
              'installed_pages': hashes, 'cells': cells_report,
              'method': 'native Potrace curves, supersampled area coverage x4',
              'parameters': {'alphamax': args.alphamax, 'opttolerance': 0.1, 'turdsize': 0,
                             'turnpolicy': 'black: foreground-8/background-4',
                             'supersample_final': 4, 'change_band_radius_x4': 2},
              'rings': rings, 'changed_pixels': int(np.count_nonzero(old != new)),
              'before_topology': old_top, 'after_topology': new_top,
              'native_topology': native_top,
              'topology_counts_preserved': valid,
              'outside_band_unchanged': bool(np.array_equal(after[~band], before[~band])),
              'before_is': 'installed foreground alpha; full-water art opacity normalized to zero geometry',
              'after_is': 'geometric coverage only; not paired-pass compensated or BC3 encoded',
              'rgb_modified': False, 'installation': 'not performed',
              'producer_sha256': sha(Path(__file__).read_bytes())}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['area', 'rect_x1', 'changed_pixels',
                     'topology_counts_preserved', 'outside_band_unchanged', 'installation']}))


if __name__ == '__main__':
    main()
