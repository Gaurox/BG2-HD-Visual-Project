"""Repair the rejected WTSWAM pilot from exact inputs; plan-only without --run."""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import build_wtswam_route2_pilot as pilot
import build_wtsew_route2_pilot as common
import repair_water_map_batch as seams
from build_water_route1_batch import eligible_primary_ids, parse_pvr, parse_standalone_tis, parse_wed

ROOT = pilot.ROOT
PARENT = ROOT / 'maps/technical-overlays/WTSWAM/runs/seedvr2-none-apollo8-x4-15hz-route2-render30-q070-ar1607-ar1800-20260912'
PARENT_SHA = 'B37AC8176CDFAB633790FCFF9271C70EDDB5CA9D303F1026D52A48432ADB3222'
ARE_ALPHA = {'AR1607': 100, 'AR1800': 128}


def correct_central_alpha(area, wed, source, destination, value):
    """Copy only proven primary DXT5 alpha blocks, including their owned padding."""
    parsed = parse_wed(wed)
    ids = eligible_primary_ids(parsed, 1)
    tis = parse_standalone_tis((source / f'{area}.TIS').read_bytes())
    by_page = {}
    for tile in sorted(ids):
        page, x, y = tis['entries'][tile]
        common.require(page != 0xffffffff and (x % 264, y % 264) == (4, 4), 'unproven central slot')
        by_page.setdefault(page, []).append((x, y))
    changed = 0
    for page, slots in by_page.items():
        path = destination / f'{area[0]+area[2:]}{page:02d}.PVRZ'
        raw, fmt, width, height, offset = parse_pvr(path.read_bytes())
        common.require(fmt == 11, 'central repair requires DXT5')
        blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height//4, width//4, 16)
        before = blocks.copy()
        allowed = np.zeros(blocks.shape[:2], bool)
        for x, y in slots:
            bx, by = (x-4)//4, (y-4)//4
            common.require(x+260 <= width and y+260 <= height, 'padding out of bounds')
            view = blocks[by:by+66, bx:bx+66]
            common.require(np.all(view[:, :, :8] == [128, 128, 0, 0, 0, 0, 0, 0]), 'alpha128 parent required')
            view[:, :, :8] = [value, value, 0, 0, 0, 0, 0, 0]
            allowed[by:by+66, bx:bx+66] = True
        common.require(np.array_equal(before[:, :, 8:], blocks[:, :, 8:]), 'central RGB modified')
        common.require(np.array_equal(before[~allowed], blocks[~allowed]), 'alpha outside central slots modified')
        changed += int(np.any(before != blocks, axis=2).sum())
        if not np.array_equal(before, blocks):
            path.write_bytes(struct.pack('<I', len(raw)) + zlib.compress(raw, 9))
            common.require(zlib.decompress(path.read_bytes()[4:]) == raw, 'alpha serialization drift')
    return {'tiles': len(ids), 'effective_native_alpha': value, 'alpha_blocks_changed': changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    common.require(ROOT in output.parents and not output.exists(), 'output must be new within workspace')
    common.require(common.sha256_file(PARENT/'registry-v3.json') == PARENT_SHA, 'parent registry drift')
    original = json.loads((PARENT/'registry-v3.json').read_text(encoding='utf-8'))
    checked = common.verify_live_registry(original)
    registry = copy.deepcopy(original)
    bifs, resources = seams.load_key()
    lookup = {(n.upper(), k): loc for n, k, loc in resources}
    pvr = {n.upper(): (n, k, loc) for n, k, loc in resources if k == 0x404}
    reports = []
    if args.run:
        output.mkdir(parents=True)
        (output/'override-candidate').mkdir()
    for area, alpha in ARE_ALPHA.items():
        wed, _ = seams.resolve_resource(bifs, lookup[area, 0x3e9])
        are, archive = seams.resolve_resource(bifs, lookup[area, 0x3f2])
        # BG2EE copies the ARE header after its eight-byte signature. Header+0x4a
        # becomes CGameArea::m_waterAlpha; zero selects native default 128.
        common.require(are[:8] == b'AREAV1.0' and (are[0x52] or 128) == alpha, 'native ARE alpha drift')
        common.require(not (common.get_path('bg2ee_game_root')/'override'/f'{area}.ARE').exists(), 'ARE override requires a new audit')
        source = pilot.BASE_ROOT / area
        entry = next(e for e in registry['entries'] if e['wed']['resref'] == area)
        common.require(seams.tis_metadata(area, source)[0] == entry['base_tis'], 'base source mismatch')
        donor = ROOT/f'maps/{area}/runs/seedvr2-7b-int8-lab-grid-2x2-x4/tuiles-secondaires/03_assemble/{area}-tuiles-secondaires-x4-seedvr2-7b-int8-lab-overlap.png'
        destination = output/'maps'/area
        report = seams.inspect_or_patch(area, wed, source, donor, bifs, lookup, pvr,
                                       destination if args.run else None)
        report['are_source'] = {'archive': archive, 'sha256': common.sha256_bytes(are), 'water_alpha': alpha}
        if args.run:
            report['central_alpha'] = correct_central_alpha(area, wed, source, destination, alpha)
            report['final_pages'] = {p.name: common.sha256_file(p) for p in sorted(destination.glob('*.PVRZ'))}
            entry['base_tis'] = seams.tis_metadata(area, destination)[0]
            entry['qa'] = {'status': 'pending-ingame', 'reference': common.relative(output/f'{area}-repair-report.json')}
            common.write_json(output/f'{area}-repair-report.json', report)
        reports.append(seams.summary(report) | {'water_alpha': alpha})
    plan = {'parent_registry': common.relative(PARENT/'registry-v3.json'), 'parent_sha256': PARENT_SHA,
            'verified_live_files': checked, 'reports': reports, 'tests': 'not-run-user-choice'}
    print(json.dumps(plan, ensure_ascii=False), flush=True)
    if not args.run:
        return
    common.require(registry['entries'][:15] == original['entries'][:15], 'unrelated registry changes')
    registry['experiment'] = {'scope': list(ARE_ALPHA), 'parent': common.relative(PARENT),
                              'reason': 'user-rejected-tiling-transparency-motion', 'qa': 'pending-ingame'}
    common.write_json(output/'registry-v3.json', registry)
    files = {}
    before = {}
    live = common.get_path('bg2ee_game_root')/'override'
    for area in ARE_ALPHA:
        for path in sorted((output/'maps'/area).glob('*.PVRZ')):
            digest = common.sha256_file(path)
            live_sha = common.sha256_file(live/path.name)
            if digest != live_sha:
                shutil.copy2(path, output/'override-candidate'/path.name)
                files[path.name] = {'bytes': path.stat().st_size, 'sha256': digest}
                before[path.name] = live_sha
    common.write_json(output/'override-candidate/manifest.json', {
        'schema': 'bg2-upscale-area-animation-override-assets-v1', 'status': 'completed',
        'area': 'AR1607-AR1800', 'files': files, 'qa_status': 'pending-ingame'})
    common.write_json(output/'live-before.json', before)
    common.write_json(output/'run.json', plan | {
        'schema': 'bg2-wtswam-repair-run-v1', 'asset_ids': ['maps:AR1607:day', 'maps:AR1800:day'],
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'producer_sha256': common.sha256_file(Path(__file__)),
        'registry_sha256': common.sha256_file(output/'registry-v3.json'),
        'installation': 'not-run', 'qa': 'pending-ingame', 'release': 'not-requested'})


if __name__ == '__main__':
    main()
