"""Paired primary-texture / secondary-draw opacity for one standard-chain water map.

Generalises the AR0300N 160/160 experiment (build_water_art_opacity_candidate.py) to any WED whose
central liquid tiles were written by build_liquid_base_x4_trial.py: every central slot listed in
its base report goes from the native alpha to --alpha (sentinel redirects sharing a slot are
covered once), and every registry entry of the WED gets the matching ``local_art_opacity`` so the
DLL draws the exclusive water secondaries at the same alpha. RGB and every other block stay
byte-identical; installation, DLL build and QA stay separate.

    python pipeline/scripts/build_paired_art_opacity_candidate.py --area AR0413 --alpha 64 \
        --base-report <run>/bases/base-repair-report.json --registry <cumulative registry-v3.json> \
        --output maps/water-batches/runs/ar0413-oil-opacity64-<date>-v1
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import zlib

import numpy as np

from bg2lib import load_key, resolve_resource
from build_water_route1_batch import ROOT, parse_pvr, parse_standalone_tis, parse_wed
from workspace_paths import get_path

SENTINEL = 0xFFFFFFFF


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def liquid_secondary_ids(wed: bytes) -> list[int]:
    """Secondary tiles of every liquid overlay slot (A-D pavings use slots 1-4), exclusive to
    liquid cells; build_water_art_opacity_candidate.secondary_ids only covers slot 1 (AR0300N)."""
    parsed = parse_wed(wed)
    bits = sum(1 << layer['slot'] for layer in parsed['layers'][1:] if layer['tis'])
    water = {c['secondary'] for c in parsed['cells'] if c['flags'] & bits and c['secondary'] != 65535}
    other = {c['secondary'] for c in parsed['cells'] if not c['flags'] & bits and c['secondary'] != 65535}
    primaries = {i for c in parsed['cells'] for i in c['primary']}
    require(not water & (other | primaries), 'ambiguous secondary roles')
    return sorted(water)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--area', required=True)
    parser.add_argument('--alpha', type=int, required=True)
    parser.add_argument('--base-report', type=Path, required=True)
    parser.add_argument('--registry', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    area = args.area.upper()
    require(1 <= args.alpha <= 255, 'alpha outside 1..255')
    output = args.output.resolve()
    require(ROOT in output.parents and not output.exists(), 'output must be a new workspace folder')
    live = Path(get_path('bg2ee_game_root')) / 'override'

    report = json.loads(args.base_report.read_text(encoding='utf-8'))
    target = next(m for m in report['maps'] if m['wed'] == area)
    native = int(target['native_alpha'])
    central = sorted(target['qualified_central_tiles'])
    bifs, resources = load_key()
    lookup = {(n.upper(), k): loc for n, k, loc in resources}
    stock_wed, _ = resolve_resource(bifs, lookup[area, 0x3E9])
    secondaries = liquid_secondary_ids(stock_wed)

    base = target['base']
    prefix = base[0] + base[2:]
    tis = parse_standalone_tis((live / f'{base}.TIS').read_bytes())
    slots = {}
    for tile in central:
        entry = tis['entries'][tile]
        require(entry[0] != SENTINEL and (entry[1] % 264, entry[2] % 264) == (4, 4), f'{tile}: unproven slot')
        slots.setdefault(entry, []).append(tile)
    users = {}
    for tile, entry in enumerate(tis['entries']):
        users.setdefault(entry, []).append(tile)
    for entry, tiles in slots.items():
        extra = set(users[entry]) - set(tiles)
        proven = target.get('shared_uniform_slots', {})
        require(not extra or any(set(proven.get(str(t), ())) == extra for t in tiles),
                f'{entry}: slot shared outside the proven uniform sentinel redirects')

    candidate = output / 'override-candidate'
    candidate.mkdir(parents=True)
    files, changed = {}, 0
    for page in sorted({e[0] for e in slots}):
        name = f'{prefix}{page:02d}.PVRZ'
        packed = (live / name).read_bytes()
        raw, fmt, width, height, offset = parse_pvr(packed)
        require(fmt == 11, f'{name}: DXT5 required')
        blocks = np.frombuffer(raw, np.uint8, offset=offset).reshape(height // 4, width // 4, 16)
        before = blocks.copy()
        allowed = np.zeros(blocks.shape[:2], bool)
        for (p, x, y) in [e for e in slots if e[0] == page]:
            bx, by = (x - 4) // 4, (y - 4) // 4
            view = blocks[by:by + 66, bx:bx + 66]
            require(np.all(view[:, :, :8] == [native, native, 0, 0, 0, 0, 0, 0]), f'{name}: native alpha parent required')
            view[:, :, :8] = [args.alpha, args.alpha, 0, 0, 0, 0, 0, 0]
            allowed[by:by + 66, bx:bx + 66] = True
        require(np.array_equal(before[:, :, 8:], blocks[:, :, 8:]), 'central RGB modified')
        require(np.array_equal(before[~allowed], blocks[~allowed]), 'alpha outside central slots modified')
        changed += int(np.any(before != blocks, axis=2).sum())
        data = struct.pack('<I', len(raw)) + zlib.compress(bytes(raw), 9)
        (candidate / name).write_bytes(data)
        files[name] = {'bytes': len(data), 'sha256': digest(data), 'before_sha256': digest(packed)}
    (candidate / 'manifest.json').write_text(json.dumps({
        'schema': 'bg2-upscale-area-animation-override-assets-v1', 'status': 'completed', 'area': area,
        'files': {n: {'bytes': f['bytes'], 'sha256': f['sha256']} for n, f in files.items()}}, indent=2) + '\n',
        encoding='utf-8', newline='\n')

    registry = json.loads(args.registry.read_text(encoding='utf-8'))
    art = {'mode': 'paired-primary-texture-secondary-draw', 'source_draw_alpha': native,
           'target_draw_alpha': args.alpha, 'primary_texture_alpha': args.alpha,
           'secondary_tile_ids': secondaries,
           'scope': f'exact {area} WED/TIS and exclusive water secondary roles; preserve RGB and other alpha'}
    touched = 0
    for entry in registry['entries']:
        if entry['wed']['resref'] == area:
            entry['local_art_opacity'] = copy.deepcopy(art)
            entry['state'] = 'candidate-installable-pending-qa'
            entry['qa'] = {'status': 'pending-ingame'}
            touched += 1
    require(touched, f'no registry entry for {area}')
    (output / 'registry-v3.json').write_text(json.dumps(registry, indent=2) + '\n', encoding='utf-8', newline='\n')
    summary = {'area': area, 'native_alpha': native, 'alpha': args.alpha, 'central_tiles': len(central),
               'slots': len(slots), 'secondary_tiles': len(secondaries), 'pages': files,
               'alpha_blocks_changed': changed, 'registry_entries': touched,
               'base_report': args.base_report.resolve().relative_to(ROOT).as_posix(),
               'parent_registry': args.registry.resolve().relative_to(ROOT).as_posix()}
    (output / 'report.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'pages'}))


if __name__ == '__main__':
    main()
