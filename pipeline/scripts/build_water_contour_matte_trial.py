"""AR1600 local trial: foreground-over-water contours taken from the x4 RGB silhouette.

The installed x4 base RGB draws each object (ropes, mast, sail, pier) with a hard,
straight edge on a black background, inside the native x1 mask; the installed alpha,
derived from x1, is thicker and stepped and exposes that black as a dark fringe.
Recipe:
  coverage M = non-black x4 RGB within 4 px x4 of the native edge, closed 3x3,
               specks removed, light anti-aliasing (gaussian 0.8, ramp 0.35);
               deeper than 4 px inside the native mask stays opaque (dark detail kept);
  RGB        = SeedVR light rim recoloured from the object's own interior
               (2 px when local width > 8 px x4, 1 px from the axis for 4-8 px ropes,
               untouched below), then carried 5 px outward so filtering never meets black;
  water art  = secondary colours extended into the object side (S = 1 - M);
  passes     = Astra's pair contract: S = 1 - M, P = M / (1 - a (1 - M)), a = 128/255.
Same ROI, rim transition and selective BC3 as ``build_water_contour_trial.py``; the
source is the pre-Astra page set, so the candidate replaces Astra's trial entirely.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, defaultdict
import hashlib
import json
from pathlib import Path
import struct
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

import bg2lib
from area_decode import decode_tis_tiles
from build_water_contour_trial import alpha_block_exact_endpoints, blocks_encode, composite
from build_water_route1_batch import parse_wed, parse_standalone_tis, parse_pvr
from mos_decode import decode_pvrz_page
from workspace_paths import ROOT, get_path

ASTRA_RUN = ROOT / 'maps/water-batches/runs/ar1600-contour-colour-trial-20260923-v2'
ASTRA_RECEIPT = ROOT / 'pipeline/water/manifests/ar1600-contour-installed-20260923-v1.json'
PREVIEW = ROOT / 'maps/water-batches/runs/ar1600-contour-mask-preview-20260923-v2'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


# --- recipe ------------------------------------------------------------------------

def norm_conv(values, weights, sigma):
    num = np.stack([ndi.gaussian_filter(values[..., c] * weights, sigma)
                    for c in range(values.shape[-1])], -1)
    den = ndi.gaussian_filter(weights, sigma)[..., None]
    return num / np.maximum(den, 1e-6), den[..., 0]


def silhouette(rgb, native, band=4, black=20, aa_sigma=0.8, aa_ramp=0.35, min_speck=12):
    d_in = ndi.distance_transform_edt(native)
    near = ndi.distance_transform_edt(~native) <= band
    lit = (rgb.max(-1) > black) & near
    obj = ndi.binary_closing(lit, np.ones((3, 3)), border_value=0) | lit
    deep = native & (d_in > band)
    obj |= deep
    labels, n = ndi.label(obj, np.ones((3, 3)))
    index = range(1, n + 1)
    sizes = ndi.sum(np.ones_like(labels), labels, index)
    anchored = ndi.maximum(deep, labels, index) > 0
    obj = np.r_[False, (sizes >= min_speck) | anchored][labels]
    blur = ndi.gaussian_filter(obj.astype(np.float64), aa_sigma)
    coverage = np.clip((blur - 0.5) / aa_ramp + 0.5, 0, 1)
    coverage[deep] = 1.0
    coverage[~near & ~native] = 0.0
    return obj, coverage


def edge_rgb(rgb, obj, sigma=2.0, reach=5):
    rgb = rgb.astype(np.float64)
    d = ndi.distance_transform_edt(obj)
    width = 2 * ndi.maximum_filter(d, size=9)
    out = rgb.copy()
    report = {}
    for name, sel, rim, core_min, s in [('wide', width > 8, 2.0, 3.5, sigma),
                                        ('thin', (width > 4) & (width <= 8), 1.0, 1.5, 1.2)]:
        interior, den = norm_conv(rgb, (obj & (d >= core_min)).astype(np.float64), s)
        ok = obj & sel & (d <= rim) & (den > 1e-3)
        out[ok] = interior[ok]
        report[name + '_rim_px'] = int(ok.sum())
    ext, den = norm_conv(out, obj.astype(np.float64), sigma)
    outside = ~obj & (ndi.distance_transform_edt(~obj) <= reach) & (den > 1e-4)
    out[outside] = ext[outside]
    report['extended_px'] = int(outside.sum())
    return np.clip(np.rint(out), 0, 255).astype(np.uint8), report


def extend_colours(rgb, valid, sigma=2.0, iterations=4):
    out = rgb.astype(np.float64).copy()
    weight = valid.astype(np.float64)
    for _ in range(iterations):
        fill, den = norm_conv(out, weight, sigma)
        new = (weight == 0) & (den > 1e-3)
        out[new] = fill[new]
        weight[new] = 1.0
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


# --- stages -----------------------------------------------------------------------

ZONE_RECEIPT = ROOT / 'pipeline/water/manifests/ar1600-contour-matte-installed-20260923-v1.json'


def source_pages(live):
    """Pre-Astra bytes for the pages Astra's installed trial changed; live otherwise.

    Accepted live states for those pages: Astra's trial, or this recipe's zone trial."""
    receipt = read(ASTRA_RECEIPT)
    zone = read(ZONE_RECEIPT)['files'] if ZONE_RECEIPT.is_file() else {}
    backup = ROOT / Path(receipt['backup_receipt']).parent
    pages = {}
    for name, row in receipt['files'].items():
        live_hash = sha((live / name).read_bytes())
        require(live_hash in (row['after_sha256'], zone.get(name, {}).get('sha256')),
                f'{name}: live page is neither Astra nor the matte zone trial')
        data = (backup / name).read_bytes()
        require(sha(data) == row['before_sha256'], f'{name}: Astra backup drift')
        pages[name] = data
    return pages, {n: r['after_sha256'] for n, r in receipt['files'].items()}


def prepare(args):
    output = args.output.resolve()
    output.relative_to(ROOT / 'maps')
    require(not output.exists(), 'Refusing to overwrite an existing run')
    evidence = read(PREVIEW / 'report.json')
    area = evidence['area']
    game = get_path('bg2ee_game_root', required=True)
    live = game / 'override'
    originals, astra_live = source_pages(live)
    bg2lib.GAME_DIR = str(args.vanilla_root)
    bg2lib.KEY_PATH = str(args.vanilla_root / 'chitin.key')
    bifs, resources = bg2lib.load_key()
    lookup = {(n.upper(), k): loc for n, k, loc in resources}
    pvr = {n.upper(): (n, k, loc) for n, k, loc in resources if k == 0x404}
    native_wed, _ = bg2lib.resolve_resource(bifs, lookup[area, 0x3e9])
    require(sha(native_wed) == evidence['source_wed_sha256'], 'Native WED drift')
    parsed = parse_wed(native_wed)
    live_wed = parse_wed((live / (area + '.WED')).read_bytes())
    require(parsed['cells'] == live_wed['cells'], 'WED base geometry changed')
    base = parsed['layers'][0]
    prefix = base['tis'][0] + base['tis'][2:]
    tis_data = (live / (base['tis'] + '.TIS')).read_bytes()
    require(sha(tis_data) == evidence['installed_tis_sha256'], 'Installed TIS drift')
    tis = parse_standalone_tis(tis_data)
    stock, _ = decode_tis_tiles(bifs, pvr, base['tis'], lookup[base['tis'], 0x3eb])
    are, _ = bg2lib.resolve_resource(bifs, lookup[area, 0x3f2])
    water_alpha = are[0x52] or 128
    require(water_alpha == 128, 'Unexpected WATER_ALPHA contract')
    x, y, w, h = evidence['rect_x1']
    left, top, right, bottom = x - 64, y - 64, x + w + 64, y + h + 64
    shape = ((bottom - top) * 4, (right - left) * 4)
    primary, secondary = [np.zeros((*shape, 4), np.uint8) for _ in range(2)]
    native = np.zeros(shape, bool)
    pair_region = np.zeros(shape, bool)
    cache, hashes = OrderedDict(), {}
    physical = Counter(tis['entries'])
    logical = Counter(t for c in parsed['cells'] for t in c['primary'])
    logical.update(c['secondary'] for c in parsed['cells'] if c['secondary'] != 65535)

    def tile(index):
        page, px, py = tis['entries'][index]
        require(page != 0xffffffff, 'Sentinel tile in trial')
        name = f'{prefix}{page:02d}.PVRZ'
        if page not in cache:
            data = originals.get(name) or (live / name).read_bytes()
            hashes[name] = sha(data)
            if name in evidence['installed_pages']:
                require(hashes[name] == evidence['installed_pages'][name], 'Pre-Astra page drift: ' + name)
            cache[page] = decode_pvrz_page(data)
            if len(cache) > 6:
                cache.popitem(last=False)
        return np.array(cache[page].crop((px, py, px + 256, py + 256)))

    cells = []
    for c in parsed['cells']:
        cx, cy = c['x'] * 64, c['y'] * 64
        if not (left <= cx < right and top <= cy < bottom):
            continue
        require(c['count'] == 1, 'Animated base is outside the contract')
        p, s = c['primary'][0], c['secondary']
        ax, ay = (cx - left) * 4, (cy - top) * 4
        sl = np.s_[ay:ay + 256, ax:ax + 256]
        pa = np.asarray(stock(p))[:, :, 3]
        primary[sl] = tile(p)
        native[sl] = (pa > 127).repeat(4, 0).repeat(4, 1)
        qualified = s != 65535 and bool(c['flags'] & 2)
        if qualified:
            sa = np.asarray(stock(s))[:, :, 3]
            require(bool(np.all(pa.astype(int) + sa == 255)), 'Non-complementary native pair')
            secondary[sl] = tile(s)
            pair_region[sl] = True
        if x <= cx < x + w and y <= cy < y + h and qualified:
            for index in (p, s):
                require(logical[index] == 1 and physical[tis['entries'][index]] == 1,
                        'Shared tile needs explicit isolation: ' + str(index))
            cells.append({'x': c['x'], 'y': c['y'], 'primary': p, 'secondary': s, 'ax': ax, 'ay': ay})
    roi = np.s_[256:256 + h * 4, 256:256 + w * 4]
    # Same experimental patch as Astra: exact 4 px perimeter, 12 px ramp to existing art.
    yy, xx = np.indices((h * 4, w * 4))
    rim = np.minimum.reduce([xx, yy, w * 4 - 1 - xx, h * 4 - 1 - yy])
    mix = np.zeros(shape, np.float32)
    mix[roi] = np.clip((rim - 4) / 12, 0, 1)
    mix *= pair_region
    print('Silhouette from x4 RGB', flush=True)
    obj, coverage = silhouette(primary[:, :, :3], native)
    rgb_p, report_p = edge_rgb(primary[:, :, :3], obj)
    rgb_s = extend_colours(secondary[:, :, :3], secondary[:, :, 3] > 127)
    a = water_alpha / 255
    p_alpha = np.where(coverage > 0, coverage / (1 - a * (1 - coverage)), 0.0)
    desired_p, desired_s = primary.copy(), secondary.copy()
    for old, new, rgb, alpha in [(primary, desired_p, rgb_p, p_alpha), (secondary, desired_s, rgb_s, 1 - coverage)]:
        new[:, :, :3] = np.rint(old[:, :, :3] * (1 - mix[:, :, None]) + rgb * mix[:, :, None]).astype(np.uint8)
        new[:, :, 3] = np.rint(old[:, :, 3] * (1 - mix) + alpha * 255 * mix).clip(0, 255).astype(np.uint8)
    output.mkdir(parents=True)
    (output / 'tiles').mkdir()
    tile_records = []
    for c in cells:
        ax, ay = c['ax'], c['ay']
        for role, old, new in [('primary', primary, desired_p), ('secondary', secondary, desired_s)]:
            index = c[role]
            target = new[ay:ay + 256, ax:ax + 256]
            if not np.any(old[ay:ay + 256, ax:ax + 256] != target):
                continue
            Image.fromarray(target).save(output / 'tiles' / f'{index}-{role}.png')
            tile_records.append({'tile': index, 'role': role, 'cell': [c['x'], c['y']],
                                 'entry': list(tis['entries'][index]), 'png': f'tiles/{index}-{role}.png'})
    overlay_name = live_wed['layers'][1]['tis']
    ot = parse_standalone_tis((live / (overlay_name + '.TIS')).read_bytes())
    op, ox, oy = ot['entries'][0]
    overlay = np.asarray(decode_pvrz_page((live / f'{overlay_name[0] + overlay_name[2:]}{op:02d}.PVRZ').read_bytes()))
    underlay = np.tile(overlay[oy:oy + 256, ox:ox + 256, :3], (h // 64, w // 64, 1))
    np.savez_compressed(output / 'canvas.npz', primary=primary[roi], secondary=secondary[roi],
                        desired_primary=desired_p[roi], desired_secondary=desired_s[roi],
                        coverage=np.rint(coverage[roi] * 255).astype(np.uint8), mix=mix[roi],
                        underlay=underlay, native=native[roi])
    write(output / 'prepare.json', {
        'schema': 'bg2-water-contour-matte-trial-v1', 'area': area, 'rect_x1': [x, y, w, h],
        'water_alpha': water_alpha, 'geometry': 'x4 RGB silhouette (non-black >20, band 4 px x4, closing 3x3, '
        'specks <12 px removed, AA gaussian 0.8 ramp 0.35); deeper native interior opaque',
        'colour': report_p, 'composition': 'U -> P -> a*S; S=1-M; P=M/(1-a*(1-M))',
        'roi_rim': '4px x4 exact perimeter, then 12px transition to pre-Astra art',
        'source_pages': hashes, 'astra_live_pages': astra_live,
        'astra_restored_pages': sorted(originals), 'tiles': tile_records,
        'producer_sha256': sha(Path(__file__).read_bytes()), 'installation': 'not performed'})
    print(json.dumps({'prepared_tiles': len(tile_records), 'colour': report_p}), flush=True)


def panels3(images, labels, path, crop=None):
    if crop:
        images = [im.crop(crop).resize((640, 512), Image.Resampling.NEAREST) for im in images]
    else:
        size = (640, round(images[0].height * 640 / images[0].width))
        images = [im.resize(size, Image.Resampling.LANCZOS) for im in images]
    w, h = images[0].size
    canvas = Image.new('RGB', (w * 3 + 48, h + 90), (24, 28, 33))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 21)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 16)
    for i, (im, label) in enumerate(zip(images, labels)):
        draw.text((12 + i * (w + 12), 10), label, font=font, fill='white')
        canvas.paste(im.convert('RGB'), (12 + i * (w + 12), 44))
    draw.text((12, h + 56), 'Simulation des couches, BC3 décodé — pas une capture ingame', font=small, fill=(175, 185, 195))
    canvas.save(path)


def encode(args):
    run = args.output.resolve(strict=True)
    run.relative_to(ROOT / 'maps')
    plan = read(run / 'prepare.json')
    candidate = run / 'override-candidate'
    require(not candidate.exists(), 'Candidate already exists')
    game = get_path('bg2ee_game_root', required=True)
    live = game / 'override'
    originals, _ = source_pages(live)
    for name, digest in plan['source_pages'].items():
        data = originals.get(name) or (live / name).read_bytes()
        require(sha(data) == digest, 'Source page drift: ' + name)
    candidate.mkdir()
    groups = defaultdict(list)
    for t in plan['tiles']:
        groups[t['entry'][0]].append(t)
    canv = np.load(run / 'canvas.npz')
    p, s = canv['primary'].copy(), canv['secondary'].copy()
    x, y, w, h = plan['rect_x1']
    files, pages_report = {}, []
    tis = parse_standalone_tis((live / 'AR1600.TIS').read_bytes())
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
            ax, ay = (t['cell'][0] * 64 - x) * 4, (t['cell'][1] * 64 - y) * 4
            (p if t['role'] == 'primary' else s)[ay:ay + 256, ax:ax + 256] = final[py:py + 256, px:px + 256]
        files[name] = {'sha256': sha(data), 'bytes': len(data)}
        pages_report.append({'name': name, 'before_sha256': sha(packed), 'after_sha256': sha(data),
                             'alpha_blocks_changed': int(np.any(original[:, :, :8] != blocks[:, :, :8], 2).sum()),
                             'rgb_blocks_changed': int(np.any(original[:, :, 8:] != blocks[:, :, 8:], 2).sum())})
        print('Encoded ' + name, flush=True)
    # Astra pages this trial does not touch go back to their pre-Astra bytes.
    for name, data in originals.items():
        if name not in files:
            (candidate / name).write_bytes(data)
            files[name] = {'sha256': sha(data), 'bytes': len(data)}
            pages_report.append({'name': name, 'restored_pre_astra': True})
    a = plan['water_alpha'] / 255
    before = composite(canv['primary'], canv['secondary'], canv['underlay'], a)
    after = composite(p, s, canv['underlay'], a)
    to_image = lambda c: Image.fromarray(np.rint(c).clip(0, 255).astype(np.uint8))
    b, f = to_image(before), to_image(after)
    astra = Image.open(ASTRA_RUN / 'composite-after-bc3.png').convert('RGB')
    b.save(run / 'composite-before.png')
    f.save(run / 'composite-after-bc3.png')
    labels = ['AVANT (HD installé)', 'ASTRA (installé)', 'MATTE RGB x4 (candidat)']
    panels3([b, astra, f], labels, run / 'comparison-3-full.png')
    for name, crop in [('rigging', (400, 256, 720, 512)), ('sail-pier', (0, 120, 320, 376)),
                       ('deck', (300, 700, 620, 956))]:
        panels3([b, astra, f], labels, run / f'comparison-3-{name}.png', crop)
    effective = p[:, :, 3] / 255. * (1 - a * s[:, :, 3] / 255.)
    intended = canv['desired_primary'][:, :, 3] / 255. * (1 - a * canv['desired_secondary'][:, :, 3] / 255.)
    edge = (canv['mix'] == 1) & (canv['coverage'] > 0) & (canv['coverage'] < 255)
    err = np.abs(effective - intended)[edge]
    require(len(err) > 0 and float(err.mean()) < .03, 'Excessive BC3 coverage error')
    write(candidate / 'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1',
          'status': 'completed', 'area': 'AR1600', 'scope': 'local ship contour trial (x4 RGB matte)', 'files': files})
    write(run / 'build.json', {'schema': 'bg2-water-contour-matte-build-v1', 'area': 'AR1600', 'pages': pages_report,
          'tiles': len(plan['tiles']), 'bc3_edge_effective_coverage_error': {
              'mean': float(err.mean()), 'p99': float(np.percentile(err, 99)), 'max': float(err.max()), 'samples': len(err)},
          'outside_selected_blocks': 'byte-exact vs pre-Astra pages', 'temporal_water': 'no WED/TIS/overlay/DLL change',
          'prepare_sha256': sha((run / 'prepare.json').read_bytes()), 'producer_sha256': sha(Path(__file__).read_bytes()),
          'installation': 'not performed', 'qa': 'pending-user-ingame'})
    print(json.dumps({'pages': len(files), 'coverage_mean_error': float(err.mean())}), flush=True)


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
