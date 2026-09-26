"""Foreground-over-water contours from the x4 RGB silhouette, any water WED (one map per run).

Recipe validated ingame on AR1600 (ship zone, then whole map, 2026-09-23); functions are
imported unchanged from ``build_water_contour_matte_trial.py``:
  coverage M = non-black x4 RGB within 4 px x4 of the native edge, closed 3x3, specks
               < 12 px removed, AA gaussian 0.8 / ramp 0.35; native interior > 4 px opaque;
  RGB        = light SeedVR rim recoloured from the object's interior (2 px if local width
               > 8 px x4, 1 px from the axis for 4-8 px), then carried 5 px outward;
  water art  = secondary colours extended into the object side;
  passes     = S = 1 - M, P = M / (1 - a (1 - M)), a = ARE WATER_ALPHA (0 -> 128).
Scope: WED cells whose base has a secondary tile and any liquid overlay bit; cells without
secondary, doors, animated, shared or non-complementary tiles are skipped and reported.

Stages:
  survey   read-only preconditions (black background, BC3 pages, atlas padding, pairs);
  prepare  windows of 8x8 cells + one-cell halo -> desired tiles;
  encode   selective BC3 blocks -> candidate pages + manifest (installation is separate).
The x4 RGB must be the untreated base: a page already treated by this recipe carries
object colours outside the native edge and is refused (pass --source-backup folders instead).
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
from build_water_contour_matte_trial import (edge_rgb, extend_colours, read, require, silhouette,
                                             sha, write)
from build_water_contour_trial import alpha_block_exact_endpoints, blocks_encode
from build_water_route1_batch import parse_wed, parse_standalone_tis, parse_pvr
from mos_decode import decode_pvrz_page
from workspace_paths import ROOT, get_path

WINDOW = 8
STANDARD = ROOT / 'pipeline/water/liquid-family-standard-v1.json'


def contour_spline_fit(area, explicit=None, standard_path=STANDARD):
    """Spline fit of the matte contour: --spline-fit (0 = off) > per-map exception of the family
    standard (``contour_map_overrides``) > standard default (spline fit 1.0, validated on every
    family 2026-09-25).  Exceptions belong to maps, never to families (AR0408, AR0703)."""
    if explicit is not None:
        return explicit or None
    standard = json.loads(Path(standard_path).read_text(encoding='utf-8'))
    override = standard.get('contour_map_overrides', {}).get(area.upper(), {})
    value = override.get('spline_fit', standard['defaults']['contour'].get('spline_fit'))
    return value or None


def spline_coverage(obj, native, fit_error=1.0, spacing=1.5, supersample=2, band=4, aa_sigma=None, aa_ramp=0.35):
    """Coverage of the x4 silhouette whose contour (holes and islands kept) is refitted by a
    periodic spline (SPLINE_ALPHA_MASK_PIPELINE, fit 1.0 validated on AR0900 water) and
    rasterised by area, instead of the gaussian AA of ``silhouette``.  Same bounds: native
    interior > band stays opaque, nothing appears beyond band px of the native mask."""
    from scipy import ndimage as ndi
    from build_spline_map_alpha import spline_mask
    if not obj.any():
        return np.zeros(obj.shape, np.float64), {'rings': 0}
    fitted, report = spline_mask(Image.fromarray(np.where(obj, 255, 0).astype(np.uint8)),
                                 fit_error, spacing, supersample)
    coverage = np.asarray(fitted, np.float64) / 255.0
    if aa_sigma:                  # same soft edge as ``silhouette`` on the refitted trajectory
        blur = ndi.gaussian_filter((coverage > 0.5).astype(np.float64), aa_sigma)
        coverage = np.clip((blur - 0.5) / aa_ramp + 0.5, 0, 1)
    deep = native & (ndi.distance_transform_edt(native) > band)
    near = ndi.distance_transform_edt(~native) <= band
    coverage[deep] = 1.0
    coverage[~near & ~native] = 0.0
    return coverage, report
LIQUID_BITS = 0x1E          # overlay slots 1-4
BLACK, MAX_OUTSIDE_LIT = 20, 0.15       # per tile: skip the cell above this lit share
TREATED_MEDIAN, TREATED_TILES = 0.05, 0.05  # map level: refuse (already treated / no matte)


def door_cells(wed):
    count, offset, tiles = (struct.unpack_from('<I', wed, o)[0] for o in (0x0C, 0x18, 0x1C))
    cells = set()
    for i in range(count):
        first, n = struct.unpack_from('<HH', wed, offset + i * 26 + 10)
        cells.update(struct.unpack_from(f'<{n}H', wed, tiles + first * 2))
    return cells


class Area:
    """Native WED/TIS/ARE from the vanilla KEY, x4 pages from override (or a backup)."""

    def __init__(self, area, vanilla, source_backup=None):
        self.area = area.upper()
        self.live = get_path('bg2ee_game_root', required=True) / 'override'
        self.backups = [Path(b).resolve() for b in (source_backup or [])]
        bg2lib.GAME_DIR = str(vanilla)
        bg2lib.KEY_PATH = str(Path(vanilla) / 'chitin.key')
        bifs, resources = bg2lib.load_key()
        lookup = {(n.upper(), k): loc for n, k, loc in resources}
        pvr = {n.upper(): (n, k, loc) for n, k, loc in resources if k == 0x404}
        self.wed_bytes, _ = bg2lib.resolve_resource(bifs, lookup[self.area, 0x3e9])
        self.wed = parse_wed(self.wed_bytes)
        live_wed = self.live / f'{self.area}.WED'
        if live_wed.is_file():
            require(parse_wed(live_wed.read_bytes())['cells'] == self.wed['cells'], 'Installed WED base geometry differs')
        base = self.wed['layers'][0]
        self.tis_name = base['tis']
        self.prefix = base['tis'][0] + base['tis'][2:]
        tis_path = self.live / f'{self.tis_name}.TIS'
        require(tis_path.is_file(), f'{tis_path.name}: no installed x4 base')
        self.tis = parse_standalone_tis(tis_path.read_bytes())
        self.stock, _ = decode_tis_tiles(bifs, pvr, base['tis'], lookup[base['tis'], 0x3eb])
        # Night WEDs (ARxxxxN) have no ARE of their own: the day ARE carries WATER_ALPHA.
        are_name = self.area if (self.area, 0x3f2) in lookup else self.area.rstrip('N')
        are, _ = bg2lib.resolve_resource(bifs, lookup[are_name, 0x3f2])
        self.water_alpha = are[0x52] or 128
        self.grid = {(c['x'], c['y']): c for c in self.wed['cells']}
        self.cache, self.page_hashes = OrderedDict(), {}

    def page_bytes(self, name):
        for backup in self.backups:        # first folder holding the page wins
            if (backup / name).is_file():
                return (backup / name).read_bytes()
        return (self.live / name).read_bytes()

    def tile(self, index):
        page, px, py = self.tis['entries'][index]
        name = f'{self.prefix}{page:02d}.PVRZ'
        if page not in self.cache:
            data = self.page_bytes(name)
            self.page_hashes[name] = sha(data)
            self.cache[page] = decode_pvrz_page(data)
            if len(self.cache) > 12:
                self.cache.popitem(last=False)
        return np.array(self.cache[page].crop((px, py, px + 256, py + 256)))

    def native(self, index):
        return (np.asarray(self.stock(index))[:, :, 3] > 127).repeat(4, 0).repeat(4, 1)

    def outside_lit(self, index):
        """Share of x4 RGB pixels brighter than black outside the native mask of a primary."""
        outside = ~self.native(index)
        return float((self.tile(index)[:, :, :3].max(-1)[outside] > BLACK).mean()) if outside.any() else 0.0

    def qualify(self):
        doors = door_cells(self.wed_bytes)
        physical = Counter(self.tis['entries'])
        logical = Counter(t for c in self.wed['cells'] for t in c['primary'])
        logical.update(c['secondary'] for c in self.wed['cells'] if c['secondary'] != 65535)
        qualified, skipped = {}, Counter()
        for i, c in enumerate(self.wed['cells']):
            if not c['flags'] & LIQUID_BITS:
                continue
            if c['secondary'] == 65535:
                skipped['no-secondary'] += 1
                continue
            p, s = c['primary'][0], c['secondary']
            reason = ('animated' if c['count'] != 1 else 'door' if i in doors else
                      'sentinel' if 0xffffffff in (self.tis['entries'][p][0], self.tis['entries'][s][0]) else
                      'shared' if max(logical[p], logical[s], physical[self.tis['entries'][p]],
                                      physical[self.tis['entries'][s]]) != 1 else None)
            if reason is None and not np.all(np.asarray(self.stock(p))[:, :, 3].astype(int)
                                             + np.asarray(self.stock(s))[:, :, 3] == 255):
                reason = 'non-complementary'
            if reason is None and self.outside_lit(p) > MAX_OUTSIDE_LIT:
                reason = 'non-black-background'
            if reason:
                skipped[reason] += 1
            else:
                qualified[(c['x'], c['y'])] = c
        return qualified, skipped


def survey(area):
    """Read-only preconditions; returns a report dict."""
    qualified, skipped = area.qualify()
    formats, padding = Counter(), Counter()
    lit = [area.outside_lit(c['primary'][0]) for c in qualified.values()]
    for c in qualified.values():
        for index in (c['primary'][0], c['secondary']):
            page, px, py = area.tis['entries'][index]
            padding['ok' if (px % 264, py % 264) == (4, 4) else 'other'] += 1
    for name in sorted(area.page_hashes):
        formats[parse_pvr(area.page_bytes(name))[1]] += 1
    # Map-level signature of an already treated base: many pairs lose the black matte.
    everything = np.array(lit + [MAX_OUTSIDE_LIT + 1] * skipped.get('non-black-background', 0)) if (lit or skipped) else np.zeros(1)
    over = float((everything > MAX_OUTSIDE_LIT).mean()) if everything.size else 0.0
    report = {'area': area.area, 'water_alpha': area.water_alpha, 'qualified_pairs': len(qualified),
              'skipped': dict(skipped), 'pvr_formats': {str(k): v for k, v in formats.items()},
              'atlas_padding': dict(padding),
              'outside_native_lit_share': {'median': float(np.median(everything)) if everything.size else 0.0,
                                           'tiles_over_limit_share': over}}
    problems = []
    if not qualified:
        problems.append('no qualified water pair')
    if set(formats) - {11}:
        problems.append('non-BC3 pages (format 11 required)')
    if padding.get('other'):
        problems.append('atlas padding other than 4 px x4 / pitch 264')
    # A single painted/non-matte pair is a local exception, not evidence that the
    # whole base was already contour-treated.  This matters on the small seven/
    # eight-pair pool maps where one legitimate exception otherwise exceeds 5%.
    non_black = skipped.get('non-black-background', 0)
    if report['outside_native_lit_share']['median'] > TREATED_MEDIAN or (over > TREATED_TILES and non_black >= 2):
        problems.append('x4 RGB not black outside the native mask: already treated, or no matte background')
    report['ready'] = not problems
    report['problems'] = problems
    return report


def prepare(area, output, central_water=False, spline_fit=None, spline_aa=None):
    """``central_water``: liquid cells without secondary (fully water, alpha restored by the
    spatial stage) join the matte as water instead of an opaque object; otherwise their
    coverage bleeds 1-4 px into the neighbouring pair and draws a line (AR5000)."""
    report = survey(area)
    require(report['ready'], 'Survey failed: ' + '; '.join(report['problems']))
    qualified, skipped = area.qualify()
    output.mkdir(parents=True)
    (output / 'tiles').mkdir()
    records, colour = [], Counter()
    a = area.water_alpha / 255
    windows = sorted({(x // WINDOW, y // WINDOW) for x, y in qualified})
    for n, (wx, wy) in enumerate(windows, 1):
        x0, y0, size = wx * WINDOW - 1, wy * WINDOW - 1, WINDOW + 2
        shape = (size * 256, size * 256)
        primary, secondary = [np.zeros((*shape, 4), np.uint8) for _ in range(2)]
        native = np.zeros(shape, bool)
        cell = lambda cx, cy: np.s_[(cy - y0) * 256:(cy - y0 + 1) * 256, (cx - x0) * 256:(cx - x0 + 1) * 256]
        for cy in range(y0, y0 + size):
            for cx in range(x0, x0 + size):
                c = area.grid.get((cx, cy))
                if c is None or c['count'] != 1 or area.tis['entries'][c['primary'][0]][0] == 0xffffffff:
                    continue
                if central_water and c['flags'] & LIQUID_BITS and c['secondary'] == 65535:
                    continue                  # water: black RGB, empty native mask
                primary[cell(cx, cy)] = area.tile(c['primary'][0])
                native[cell(cx, cy)] = area.native(c['primary'][0])
                if (cx, cy) in qualified:
                    secondary[cell(cx, cy)] = area.tile(c['secondary'])
        obj, coverage = silhouette(primary[:, :, :3], native)
        if spline_fit:
            # Alpha only: pixels the spline adds lie within the 5 px colour extension of the
            # original silhouette; using the refitted mask as RGB donor spread black notches.
            coverage, _ = spline_coverage(obj, native, spline_fit, aa_sigma=spline_aa)
        rgb_p, rep = edge_rgb(primary[:, :, :3], obj)
        colour.update(rep)
        rgb_s = extend_colours(secondary[:, :, :3], secondary[:, :, 3] > 127)
        p_alpha = np.where(coverage > 0, coverage / (1 - a * (1 - coverage)), 0.0)
        for (cx, cy), c in qualified.items():
            if (cx // WINDOW, cy // WINDOW) != (wx, wy):
                continue
            sl = cell(cx, cy)
            for role, old, rgb, alpha, index in [('primary', primary, rgb_p, p_alpha, c['primary'][0]),
                                                  ('secondary', secondary, rgb_s, 1 - coverage, c['secondary'])]:
                target = old[sl].copy()
                target[:, :, :3] = rgb[sl]
                target[:, :, 3] = np.rint(alpha[sl] * 255).clip(0, 255).astype(np.uint8)
                if not np.any(target != old[sl]):
                    continue
                Image.fromarray(target).save(output / 'tiles' / f'{index}-{role}.png')
                records.append({'tile': index, 'role': role, 'cell': [cx, cy],
                                'entry': list(area.tis['entries'][index]), 'png': f'tiles/{index}-{role}.png'})
        print(f'window {n}/{len(windows)} ({wx},{wy})', flush=True)
    write(output / 'prepare.json', {
        'schema': 'bg2-water-contour-matte-v1', 'area': area.area, 'survey': report,
        'water_alpha': area.water_alpha, 'qualified_pairs': len(qualified), 'skipped': dict(skipped),
        'recipe': 'build_water_contour_matte_trial.py silhouette/edge_rgb/extend_colours (validated AR1600)',
        'composition': 'U -> P -> a*S; S=1-M; P=M/(1-a*(1-M))', 'window_cells': WINDOW, 'halo_cells': 1,
        'central_water': central_water, 'spline_fit': spline_fit, 'spline_aa_sigma': spline_aa,
        'colour': dict(colour), 'source_backups': [str(b) for b in area.backups],
        'source_pages': dict(area.page_hashes), 'tiles': records,
        'producer_sha256': sha(Path(__file__).read_bytes()), 'installation': 'not performed'})
    print(json.dumps({'qualified_pairs': len(qualified), 'skipped': dict(skipped), 'tiles': len(records)}), flush=True)


def encode(area, run):
    plan = read(run / 'prepare.json')
    require(plan['area'] == area.area, 'Run belongs to another area')
    candidate = run / 'override-candidate'
    require(not candidate.exists(), 'Candidate already exists')
    for name, digest in plan['source_pages'].items():
        require(sha(area.page_bytes(name)) == digest, 'Source page drift: ' + name)
    candidate.mkdir()
    groups = defaultdict(list)
    for t in plan['tiles']:
        groups[t['entry'][0]].append(t)
    files, pages_report, finals = {}, [], {}
    for page, tiles in sorted(groups.items()):
        name = f'{area.prefix}{page:02d}.PVRZ'
        packed = area.page_bytes(name)
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
    err = np.concatenate(errors) if errors else np.zeros(1)
    require(float(err.mean()) < .03, 'Excessive BC3 coverage error')
    write(candidate / 'manifest.json', {'schema': 'bg2-upscale-area-animation-override-assets-v1', 'status': 'completed',
          'area': area.area, 'scope': 'whole-map water contours (x4 RGB matte)', 'files': files})
    write(run / 'build.json', {'schema': 'bg2-water-contour-matte-build-v1', 'area': area.area, 'pages': pages_report,
          'tiles': len(plan['tiles']), 'bc3_edge_effective_coverage_error': {
              'mean': float(err.mean()), 'p99': float(np.percentile(err, 99)), 'max': float(err.max()), 'samples': len(err)},
          'outside_selected_blocks': 'byte-exact vs source pages', 'temporal_water': 'no WED/TIS/overlay/DLL change',
          'prepare_sha256': sha((run / 'prepare.json').read_bytes()), 'producer_sha256': sha(Path(__file__).read_bytes()),
          'installation': 'not performed', 'qa': 'pending-user-ingame'})
    print(json.dumps({'pages': len(files), 'tiles': len(plan['tiles']), 'coverage_mean_error': float(err.mean())}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('stage', choices=['survey', 'prepare', 'encode'])
    parser.add_argument('--area', required=True, nargs='+', help='survey accepts several areas')
    parser.add_argument('--vanilla-root', type=Path, required=True)
    parser.add_argument('--source-backup', type=Path, action='append',
                        help='install-backup folder holding untreated pages; repeatable, first match wins')
    parser.add_argument('--output', type=Path, help='prepare/encode: run folder under maps/')
    parser.add_argument('--spline-fit', type=float,
                        help='prepare: periodic spline error (x4 px) refitting the silhouette contour; '
                             'default from the family standard (1.0, per-map exceptions); 0 = gaussian '
                             'matte only (historical)')
    parser.add_argument('--spline-aa', type=float,
                        help='prepare with --spline-fit: gaussian AA sigma (x4 px) applied to the refitted '
                             'mask, as in the default matte (0.8)')
    parser.add_argument('--no-central-water', dest='central_water', action='store_false',
                        help='prepare: historical matte (runs before 2026-09-25): liquid cells without '
                             'secondary count as opaque objects and bleed into the neighbouring pair')
    args = parser.parse_args()
    if args.stage == 'survey':
        reports = []
        for name in args.area:
            try:
                reports.append(survey(Area(name, args.vanilla_root, args.source_backup)))
            except (RuntimeError, KeyError) as error:
                reports.append({'area': name.upper(), 'ready': False, 'problems': [str(error)]})
            print(json.dumps(reports[-1], ensure_ascii=False), flush=True)
        return
    require(len(args.area) == 1 and args.output is not None, 'prepare/encode: one --area and --output')
    output = args.output.resolve()
    output.relative_to(ROOT / 'maps')
    area = Area(args.area[0], args.vanilla_root, args.source_backup)
    if args.stage == 'prepare':
        require(not output.exists(), 'Refusing to overwrite an existing run')
        prepare(area, output, args.central_water, contour_spline_fit(args.area[0], args.spline_fit),
                args.spline_aa)
    else:
        encode(area, output)


if __name__ == '__main__':
    main()
