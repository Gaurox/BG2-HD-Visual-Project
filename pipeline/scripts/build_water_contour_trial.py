"""Complete an approved, local water-mask preview as a reversible BC3 candidate.

prepare: SciPy/NumPy/Pillow; encode: Pillow >= 11 with DDS DXT5 support.
Only a new workspace run is written. Installation is a separate explicit action.
The current contract is static, unique WED primary/secondary pairs at x4.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict, defaultdict
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import struct
import zlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import bg2lib
from area_decode import decode_tis_tiles
from build_water_route1_batch import parse_wed, parse_standalone_tis, parse_pvr
from mos_decode import decode_pvrz_page
from workspace_paths import ROOT, get_path


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def clean_edge_rgb(rgb, support, valid, repair_region):
    """Local interior donors, region-labelled; preserve narrow-ridge colours.

    No colour threshold: legitimate black detail is not used as a cutout mask.
    Donors stay within six x4 pixels and the nearest native connected region.
    """
    from scipy import ndimage as ndi
    support = support & valid
    distance = ndi.distance_transform_edt(support)
    outside, nearest = ndi.distance_transform_edt(~support, return_indices=True)
    labels, _ = ndi.label(support, structure=np.ones((3, 3)))
    region = labels[tuple(nearest)]
    region[support] = labels[support]
    # A thin cord may have no 3px core. Its local medial ridge is still valid art.
    ridges = support & (distance >= ndi.maximum_filter(distance, size=3))
    donors = (distance >= 3) | ridges
    target = valid & repair_region & (((distance > 0) & (distance < 3)) |
                                      ((~support) & (outside <= 3)))
    yy, xx = np.nonzero(target)
    weights = np.zeros(len(yy), np.float32)
    total = np.zeros((len(yy), 3), np.float32)
    min_d2 = np.full(len(yy), 999, np.int32)
    offsets = sorted((dy*dy+dx*dx, dy, dx) for dy in range(-6, 7)
                     for dx in range(-6, 7) if dy*dy+dx*dx <= 36)
    for d2, dy, dx in offsets:
        sy, sx = np.clip(yy+dy, 0, rgb.shape[0]-1), np.clip(xx+dx, 0, rgb.shape[1]-1)
        eligible = donors[sy, sx] & (labels[sy, sx] == region[yy, xx])
        eligible &= d2 <= min_d2 + 2
        if not eligible.any():
            continue
        min_d2[eligible] = np.minimum(min_d2[eligible], d2)
        weight = eligible.astype(np.float32) / (1+d2)
        total += rgb[sy, sx] * weight[:, None]
        weights += weight
    # The medial ridge supplies at least one local donor for every thin feature.
    require(bool(np.all(weights > 0)), 'No reliable colour donor in the local region')
    result = rgb.copy()
    result[yy, xx] = np.rint(total/weights[:, None]).clip(0, 255).astype(np.uint8)
    return result, {'pixels': len(yy), 'max_donor_radius_x4': 6,
                    'unresolved': int(np.count_nonzero(weights == 0))}


def panels(left, right, path, title, crop=None):
    if crop:
        left, right = [im.crop(crop).resize((800, 640), Image.Resampling.NEAREST)
                       for im in (left, right)]
    else:
        size = (768, round(left.height*768/left.width))
        left, right = [im.resize(size, Image.Resampling.LANCZOS) for im in (left, right)]
    w, h = left.size
    canvas = Image.new('RGB', (w*2+36, h+112), (24, 28, 33))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 22)
    small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 17)
    for x, label, im in [(12, 'AVANT', left), (w+24, 'APRÈS', right)]:
        draw.text((x, 12), label, font=font, fill='white')
        canvas.paste(im.convert('RGB'), (x, 50))
    draw.text((12, h+65), title, font=small, fill='white')
    draw.text((12, h+88), 'Simulation des couches — pas une capture ingame', font=small,
              fill=(175, 185, 195))
    canvas.save(path)


def prepare(args):
    from scipy import ndimage as ndi
    preview = args.preview.resolve(strict=True)
    output = args.output.resolve()
    output.relative_to(ROOT/'maps')
    require(not output.exists(), 'Refusing to overwrite an existing run')
    evidence = read(preview/'report.json')
    area = evidence['area']
    require(area == 'AR1600', 'This composition contract is qualified only for AR1600')
    require(evidence['topology_counts_preserved'], 'Preview topology was rejected')
    game = get_path('bg2ee_game_root', required=True)
    live = game/'override'
    bg2lib.GAME_DIR = str(args.vanilla_root)
    bg2lib.KEY_PATH = str(args.vanilla_root/'chitin.key')
    bifs, resources = bg2lib.load_key()
    lookup = {(n.upper(), k): loc for n, k, loc in resources}
    pvr = {n.upper(): (n, k, loc) for n, k, loc in resources if k == 0x404}
    native_wed, _ = bg2lib.resolve_resource(bifs, lookup[area, 0x3e9])
    require(sha(native_wed) == evidence['source_wed_sha256'], 'Native WED drift')
    parsed = parse_wed(native_wed)
    live_wed = parse_wed((live/(area+'.WED')).read_bytes())
    require(parsed['cells'] == live_wed['cells'], 'WED base geometry changed')
    base = parsed['layers'][0]
    prefix = base['tis'][0]+base['tis'][2:]
    tis_data = (live/(base['tis']+'.TIS')).read_bytes()
    require(sha(tis_data) == evidence['installed_tis_sha256'], 'Installed TIS drift')
    tis = parse_standalone_tis(tis_data)
    stock, _ = decode_tis_tiles(bifs, pvr, base['tis'], lookup[base['tis'], 0x3eb])
    are, _ = bg2lib.resolve_resource(bifs, lookup[area, 0x3f2])
    require(not (live/(area+'.ARE')).exists(), 'Custom ARE needs explicit alpha qualification')
    water_alpha = are[0x52] or 128
    require(water_alpha == 128, 'Unexpected WATER_ALPHA contract')
    x, y, w, h = evidence['rect_x1']
    require(all(v % 64 == 0 for v in (x, y, w, h)), 'Non tile-aligned ROI')
    left, top, right, bottom = x-64, y-64, x+w+64, y+h+64
    require(left >= 0 and top >= 0 and right <= base['width']*64 and bottom <= base['height']*64,
            'This local trial requires one full context tile')
    shape = ((bottom-top)*4, (right-left)*4)
    primary, secondary = [np.zeros((*shape, 4), np.uint8) for _ in range(2)]
    geometry = np.zeros(shape, bool)
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
            data = (live/name).read_bytes()
            hashes[name] = sha(data)
            if name in evidence['installed_pages']:
                require(hashes[name] == evidence['installed_pages'][name], 'Preview page drift: '+name)
            cache[page] = decode_pvrz_page(data)
            if len(cache) > 6:
                cache.popitem(last=False)
        return np.array(cache[page].crop((px, py, px+256, py+256)))

    cells = []
    for c in parsed['cells']:
        cx, cy = c['x']*64, c['y']*64
        if not (left <= cx < right and top <= cy < bottom):
            continue
        require(c['count'] == 1, 'Animated base is outside the contract')
        p, s = c['primary'][0], c['secondary']
        ax, ay = (cx-left)*4, (cy-top)*4
        sl = np.s_[ay:ay+256, ax:ax+256]
        pa = np.asarray(stock(p))[:, :, 3]
        primary[sl] = tile(p)
        geometry[sl] = (pa > 127).repeat(4, 0).repeat(4, 1)
        qualified = s != 65535 and bool(c['flags'] & 2)
        if qualified:
            sa = np.asarray(stock(s))[:, :, 3]
            require(bool(np.all(pa.astype(int)+sa == 255)), 'Non-complementary native pair')
            secondary[sl] = tile(s)
            pair_region[sl] = True
        if x <= cx < x+w and y <= cy < y+h and qualified:
            for index in (p, s):
                require(logical[index] == 1 and physical[tis['entries'][index]] == 1,
                        'Shared tile needs explicit isolation: '+str(index))
            cells.append({'x': c['x'], 'y': c['y'], 'primary': p, 'secondary': s,
                          'ax': ax, 'ay': ay})
    roi = np.s_[256:256+h*4, 256:256+w*4]
    approved = np.asarray(Image.open(preview/'mask-after.png'))
    require(approved.shape == (h*4, w*4), 'Preview dimensions differ')
    m = primary[:, :, 3].astype(np.float32)/255
    m[roi] = approved.astype(np.float32)/255
    # Fade the experimental patch into the untouched map, leaving its perimeter exact.
    yy, xx = np.indices((h*4, w*4))
    rim = np.minimum.reduce([xx, yy, w*4-1-xx, h*4-1-yy])
    mix = np.zeros(shape, np.float32)
    mix[roi] = np.clip((rim-4)/12, 0, 1)
    mix *= pair_region
    repair = ndi.binary_dilation(ndi.binary_dilation(geometry) ^ ndi.binary_erosion(geometry),
                                iterations=3) & (mix > 0)
    print('Reconstructing foreground edge colours', flush=True)
    rgb_p, report_p = clean_edge_rgb(primary[:, :, :3], geometry,
                                    np.ones(shape, bool), repair)
    print('Reconstructing water-art edge colours', flush=True)
    rgb_s, report_s = clean_edge_rgb(secondary[:, :, :3], ~geometry, pair_region, repair)
    desired_p, desired_s = primary.copy(), secondary.copy()
    a = water_alpha/255
    p_alpha = m/(1-a*(1-m))
    for old, new, rgb, alpha in [(primary, desired_p, rgb_p, p_alpha),
                                 (secondary, desired_s, rgb_s, 1-m)]:
        new[:, :, :3] = np.rint(old[:, :, :3]*(1-mix[:, :, None])+rgb*mix[:, :, None]).astype(np.uint8)
        new[:, :, 3] = np.rint(old[:, :, 3]*(1-mix)+alpha*255*mix).clip(0, 255).astype(np.uint8)
    output.mkdir(parents=True)
    (output/'tiles').mkdir()
    tile_records = []
    for c in cells:
        ax, ay = c['ax'], c['ay']
        for role, old, new in [('primary', primary, desired_p), ('secondary', secondary, desired_s)]:
            index = c[role]
            original = old[ay:ay+256, ax:ax+256]
            target = new[ay:ay+256, ax:ax+256]
            if not np.any(original != target):
                continue
            Image.fromarray(target).save(output/'tiles'/f'{index}-{role}.png')
            tile_records.append({'tile': index, 'role': role, 'cell': [c['x'], c['y']],
                                 'entry': list(tis['entries'][index]),
                                 'png': f'tiles/{index}-{role}.png'})
    overlay_name = live_wed['layers'][1]['tis']
    ot = parse_standalone_tis((live/(overlay_name+'.TIS')).read_bytes())
    op, ox, oy = ot['entries'][0]
    overlay = np.asarray(decode_pvrz_page((live/f'{overlay_name[0]+overlay_name[2:]}{op:02d}.PVRZ').read_bytes()))
    overlay = overlay[oy:oy+256, ox:ox+256, :3]
    underlay = np.tile(overlay, (h//64, w//64, 1))
    np.savez_compressed(output/'canvas.npz', primary=primary[roi], secondary=secondary[roi],
                        desired_primary=desired_p[roi], desired_secondary=desired_s[roi],
                        coverage=approved, mix=mix[roi], underlay=underlay)
    protected_names = ['AR1600.TIS', 'AR1600.WED', 'QALAK0.TIS', 'QALAK0R.TIS',
                       'QLAK000.PVRZ', 'QLAK0R00.PVRZ', 'fpSEAM.glsl', 'fpTone.glsl']
    protected = {str(Path('override')/n): sha((live/n).read_bytes()) for n in protected_names}
    protected.update({n: sha((game/n).read_bytes()) for n in
                      ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']})
    temporal = read(ROOT/'pipeline/water/manifests/ar1600-water-30fps-installed-20260923-v1.json')
    for n, row in temporal['installed_override'].items():
        require(protected[str(Path('override')/n)] == row['sha256'], '30 FPS baseline drift: '+n)
    require(protected['InfinityEngine-Enhancer.dll'] == temporal['runtime']['installed_sha256'],
            '30 FPS DLL drift')
    plan = {'schema': 'bg2-water-contour-trial-v1', 'area': area, 'rect_x1': [x, y, w, h],
            'preview': str(preview.relative_to(ROOT)), 'preview_report_sha256': sha((preview/'report.json').read_bytes()),
            'preview_mask_sha256': sha((preview/'mask-after.png').read_bytes()),
            'water_alpha': water_alpha, 'composition': 'U -> P -> a*S; S=1-M; P=M/(1-a*(1-M))',
            'roi_rim': '4px x4 exact perimeter, then 12px transition to existing art',
            'colour_foreground': report_p, 'colour_water_art': report_s,
            'source_pages': hashes, 'protected': protected, 'tiles': tile_records,
            'producer_sha256': sha(Path(__file__).read_bytes()), 'installation': 'not performed'}
    write(output/'prepare.json', plan)
    print(json.dumps({'prepared_tiles': len(tile_records), 'output': str(output)}), flush=True)


def blocks_encode(rgba):
    stream = io.BytesIO()
    Image.fromarray(rgba).save(stream, format='DDS', pixel_format='DXT5')
    data = stream.getvalue()
    h, w = rgba.shape[:2]
    require(data[84:88] == b'DXT5' and len(data) == 128+w*h, 'Pillow BC3 encoder unavailable')
    return np.frombuffer(data, np.uint8, offset=128).reshape(h//4, w//4, 16)


@lru_cache(maxsize=65536)
def alpha_block_exact_endpoints(values):
    """Fit BC3's two alpha palette modes; preserve authored 0/255 exactly.

    Endpoint candidates come from the block's actual values. This retains sparse
    subpixel coverage much better than an extrema-only 8-entry ramp.
    """
    data = np.frombuffer(values, np.uint8).astype(np.int32)
    endpoints = np.unique(np.r_[data, 0, 255])
    lo, hi = np.meshgrid(endpoints, endpoints)
    a0, a1 = lo.ravel(), hi.ravel()
    eight = a0 > a1
    palette = np.empty((len(a0), 8), np.int32)
    palette[:, 0], palette[:, 1] = a0, a1
    for k in range(1, 7):
        palette[:, k+1] = np.where(eight, ((7-k)*a0+k*a1)//7,
                                   ((5-k)*a0+k*a1)//5 if k <= 4 else (0 if k == 5 else 255))
    valid = np.ones(len(a0), bool)
    if 0 in data:
        valid &= np.any(palette == 0, axis=1)
    if 255 in data:
        valid &= np.any(palette == 255, axis=1)
    palette, a0, a1 = palette[valid], a0[valid], a1[valid]
    errors = (data[None, :, None]-palette[:, None, :])**2
    indices = errors.argmin(2)
    best = np.take_along_axis(errors, indices[:, :, None], axis=2)[:, :, 0].sum(1).argmin()
    bits = sum(int(idx) << (3*i) for i, idx in enumerate(indices[best]))
    return bytes([int(a0[best]), int(a1[best])])+bits.to_bytes(6, 'little')


def composite(p, s, u, a):
    pa, sa = p[:, :, 3:4]/255., s[:, :, 3:4]/255.*a
    return s[:, :, :3]*sa+(1-sa)*(p[:, :, :3]*pa+(1-pa)*u)


def encode(args):
    run = args.output.resolve(strict=True)
    run.relative_to(ROOT/'maps')
    plan = read(run/'prepare.json')
    require(not (run/'override-candidate').exists(), 'Candidate already exists')
    game = get_path('bg2ee_game_root', required=True)
    live = game/'override'
    for name, digest in plan['protected'].items():
        require(sha((game/name).read_bytes()) == digest, 'Protected live drift: '+name)
    for name, digest in plan['source_pages'].items():
        require(sha((live/name).read_bytes()) == digest, 'Source page drift: '+name)
    candidate = run/'override-candidate'
    candidate.mkdir()
    groups = defaultdict(list)
    for t in plan['tiles']:
        groups[t['entry'][0]].append(t)
    canv = np.load(run/'canvas.npz')
    p, s = canv['primary'].copy(), canv['secondary'].copy()
    x, y, w, h = plan['rect_x1']
    files, pages_report = {}, []
    tis = parse_standalone_tis((live/'AR1600.TIS').read_bytes())
    for page, tiles in sorted(groups.items()):
        name = f'A1600{page:02d}.PVRZ'
        packed = (live/name).read_bytes()
        raw, fmt, width, height, offset = parse_pvr(packed)
        require(fmt == 11, 'Expected existing BC3 page')
        original = np.frombuffer(bytes(raw), np.uint8, offset=offset).reshape(height//4, width//4, 16)
        blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height//4, width//4, 16)
        allowed_a, allowed_rgb = [np.zeros(blocks.shape[:2], bool) for _ in range(2)]
        decoded = np.asarray(decode_pvrz_page(packed))
        for t in tiles:
            _, px, py = t['entry']
            require((px % 264, py % 264) == (4, 4), 'Unqualified atlas padding')
            require(px+260 <= width and py+260 <= height, 'Padding outside atlas')
            for idx, (op, ox, oy) in enumerate(tis['entries']):
                if op == page and idx != t['tile']:
                    require(max(px-4, ox-4) >= min(px+260, ox+260) or
                            max(py-4, oy-4) >= min(py+260, oy+260), 'Overlapping atlas tiles')
            current = decoded[py-4:py+260, px-4:px+260]
            core = np.asarray(Image.open(run/t['png']))
            target = np.pad(core, ((4, 4), (4, 4), (0, 0)), mode='edge')
            # Do not regenerate unrelated padding. Only extend each changed core channel.
            old_core = decoded[py:py+256, px:px+256]
            changed = np.pad(core != old_core, ((4, 4), (4, 4), (0, 0)), mode='edge')
            target = np.where(changed, target, current)
            ma = changed[:, :, 3].reshape(66, 4, 66, 4).any((1, 3))
            mr = changed[:, :, :3].any(2).reshape(66, 4, 66, 4).any((1, 3))
            coded = blocks_encode(target).copy()
            alpha_blocks = target[:, :, 3].reshape(66, 4, 66, 4).transpose(0, 2, 1, 3).reshape(66, 66, 16)
            for iy, ix in zip(*np.nonzero(ma)):
                coded[iy, ix, :8] = np.frombuffer(alpha_block_exact_endpoints(alpha_blocks[iy, ix].tobytes()), np.uint8)
            bx, by = (px-4)//4, (py-4)//4
            view = blocks[by:by+66, bx:bx+66]
            view[ma, :8] = coded[ma, :8]
            view[mr, 8:] = coded[mr, 8:]
            allowed_a[by:by+66, bx:bx+66] |= ma
            allowed_rgb[by:by+66, bx:bx+66] |= mr
        require(np.array_equal(original[~allowed_a, :8], blocks[~allowed_a, :8]), 'Unrelated alpha block changed')
        require(np.array_equal(original[~allowed_rgb, 8:], blocks[~allowed_rgb, 8:]), 'Unrelated RGB block changed')
        data = struct.pack('<I', len(raw))+zlib.compress(raw, 9)
        (candidate/name).write_bytes(data)
        final = np.asarray(decode_pvrz_page(data))
        for t in tiles:
            _, px, py = t['entry']
            ax, ay = (t['cell'][0]*64-x)*4, (t['cell'][1]*64-y)*4
            canvas = p if t['role'] == 'primary' else s
            canvas[ay:ay+256, ax:ax+256] = final[py:py+256, px:px+256]
        files[name] = {'sha256': sha(data), 'bytes': len(data)}
        pages_report.append({'name': name, 'before_sha256': sha(packed), 'after_sha256': sha(data),
            'alpha_blocks_changed': int(np.any(original[:, :, :8] != blocks[:, :, :8], 2).sum()),
            'rgb_blocks_changed': int(np.any(original[:, :, 8:] != blocks[:, :, 8:], 2).sum()),
            'unselected_blocks_byte_exact': True})
        print('Encoded '+name, flush=True)
    a = plan['water_alpha']/255
    before = composite(canv['primary'], canv['secondary'], canv['underlay'], a)
    after = composite(p, s, canv['underlay'], a)
    b, f = [Image.fromarray(np.rint(c).clip(0, 255).astype(np.uint8)) for c in (before, after)]
    b.save(run/'composite-before.png')
    f.save(run/'composite-after-bc3.png')
    panels(b, f, run/'comparison-colour-bc3.png', 'Masque + couleurs de bord + composition des deux couches ; BC3 décodé')
    panels(b, f, run/'comparison-colour-detail-bc3.png', 'Contours du gréement ; BC3 décodé', (400, 256, 720, 512))
    effective = p[:, :, 3]/255.*(1-a*s[:, :, 3]/255.)
    intended = canv['desired_primary'][:, :, 3]/255.*(1-a*canv['desired_secondary'][:, :, 3]/255.)
    edge = (canv['mix'] == 1) & (canv['coverage'] > 0) & (canv['coverage'] < 255)
    err = np.abs(effective-intended)[edge]
    require(len(err) > 0 and float(err.mean()) < .03, 'Excessive BC3 coverage error')
    Image.fromarray(np.rint(effective*255).astype(np.uint8)).save(run/'effective-coverage-bc3.png')
    write(candidate/'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1',
        'status': 'completed', 'area': 'AR1600', 'scope': 'local ship contour trial', 'files': files})
    write(run/'build.json', {'schema': 'bg2-water-contour-build-v1', 'area': 'AR1600',
        'pages': pages_report, 'tiles': len(plan['tiles']), 'protected': plan['protected'],
        'bc3_edge_effective_coverage_error': {'mean': float(err.mean()), 'p99': float(np.percentile(err, 99)),
                                             'max': float(err.max()), 'samples': len(err)},
        'outside_selected_blocks': 'byte-exact, RGB/alpha channels verified separately',
        'temporal_water': 'no WED/TIS/overlay/shader/DLL/INI changes',
        'prepare_sha256': sha((run/'prepare.json').read_bytes()),
        'producer_sha256': sha(Path(__file__).read_bytes()),
        'installation': 'not performed', 'qa': 'pending-user-ingame'})
    print(json.dumps({'pages': len(files), 'tiles': len(plan['tiles']),
                      'coverage_mean_error': float(err.mean()), 'output': str(run)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'encode'])
    parser.add_argument('--preview', type=Path)
    parser.add_argument('--vanilla-root', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.stage == 'prepare':
        require(args.preview is not None and args.vanilla_root is not None, 'Missing preparation inputs')
        prepare(args)
    else:
        encode(args)


if __name__ == '__main__':
    main()
