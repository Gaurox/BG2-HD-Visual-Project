"""Standard plans for the water chain of one map, from the vanilla WED and the family standard.

    python pipeline/scripts/plan_water_map.py inventory --vanilla-root <vanilla>
    python pipeline/scripts/plan_water_map.py plan --area AR0404 --vanilla-root <vanilla> --output maps/water-batches/runs/ar0404-water-x4-<date>-v1

``inventory`` lists every WED with an active liquid overlay, its family and its install state.
``plan`` writes, in a new run folder, the inputs of the existing producers:
  request.json        -> build_liquid_base_x4_trial.py, assemble_liquid_family_x4_trial.py
  overlays-plan.json  -> build_liquid_periodic_x4_trial.py
  temporal-plan.json  -> build_liquid_temporal_30fps.py (families not blocked only)
  plan-report.json    -> choices, refusals, decisions still owed to the user
Family parameters come from pipeline/water/liquid-family-standard-v1.json; nothing is guessed
for an unknown overlay, an ambiguous secondary master or a blocked temporal family.
Aliases are deterministic 6-character names (Y + kind S/F + 4 base36), rain = alias + R, with
page names checked against the KEY, the override and each other.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import sys

import bg2lib
from build_water_route1_batch import parse_wed
from workspace_paths import ROOT, get_path

STANDARD = ROOT / 'pipeline/water/liquid-family-standard-v1.json'
DIGITS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
STANDARD_ALIAS = re.compile(r'^Y[SF][0-9A-Z]{4}R?$')   # prefix unused by earlier water work


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def page_name(alias):
    return alias[0] + alias[2:] + '00'


def temporal_plan_group(family_id, aliases, temporal, rain_of=None):
    group = {'id': family_id, 'aliases': aliases, 'material_id': temporal['material_id']}
    if rain_of:
        group['rain_of'] = rain_of     # rain = fpTone pass: the runtime keeps it timing-only (q0)
        return group
    if 'cycle_seconds' in temporal:
        group['cycle_seconds'] = temporal['cycle_seconds']
    if 'approved_strength' in temporal:
        group['approved_strength'] = temporal['approved_strength']
    return group


class Vanilla:
    def __init__(self, root):
        bg2lib.GAME_DIR = str(root)
        bg2lib.KEY_PATH = str(Path(root) / 'chitin.key')
        bg2lib._bif_cache.clear()
        self.bifs, resources = bg2lib.load_key()
        self.index = {(n.upper(), k): loc for n, k, loc in resources}
        self.names = {n.upper() for n, _, _ in resources}

    def wed(self, area):
        data, _ = bg2lib.resolve_resource(self.bifs, self.index[area, 0x3E9])
        return data

    def has_tis(self, name):
        return (name, 0x3EB) in self.index


def family_index(standard):
    index = {}
    for family in standard['families']:
        for ref in family['overlays']:
            index[ref] = family
    return index


def liquid_slots(wed):
    parsed = parse_wed(wed)
    slots = []
    for layer in parsed['layers'][1:]:
        if not layer['tis']:
            continue
        bit = 1 << layer['slot']
        active = any(c['flags'] & bit for c in parsed['cells'])
        slots.append({'slot': layer['slot'], 'source': layer['tis'], 'active': active})
    return parsed, slots


def live_overlay_names(override, area):
    path = override / f'{area}.WED'
    if not path.is_file():
        return None
    return [layer['tis'] for layer in parse_wed(path.read_bytes())['layers'][1:]]


def prior_state(area, parsed, active, override, vanilla):
    """Water treatments already installed on this WED; replacing any of them is the user's call."""
    names = live_overlay_names(override, area) or []
    if any(STANDARD_ALIAS.match(n) for n in names):
        return [f'standard chain already installed on {area} ({names}): restore before re-planning']
    found = []
    live_wed = override / f'{area}.WED'
    if live_wed.is_file():
        live_bytes = live_wed.read_bytes()
        live = parse_wed(live_bytes)
        found += [f"slot {a['slot']}: {a['tis']} -> {b['tis']}"
                  for a, b in zip(parsed['layers'][1:], live['layers'][1:]) if a['tis'] != b['tis']]
        vanilla_wed = vanilla.wed(area)

        def count(data, slot):
            header = struct.unpack_from('<I', data, 16)[0] + slot * 24
            return struct.unpack_from('<H', data, struct.unpack_from('<I', data, header + 16)[0] + 2)[0]
        for s in active:
            if count(vanilla_wed, s['slot']) != count(live_bytes, s['slot']):
                found.append(f"slot {s['slot']}: lookup {count(vanilla_wed, s['slot'])} -> {count(live_bytes, s['slot'])}")
    result = [f'earlier water treatment installed on {area} ({"; ".join(found)}): replacing it is a user decision'] if found else []
    pointer = ROOT / 'pipeline/water/route2-registry-current.json'
    if pointer.is_file() and any(i['wed'] == area for i in read(pointer)['identities']):
        result.append(f'{area} has a route2 identity in the installed DLL registry: user decision')
    return result


def inventory(args):
    vanilla = Vanilla(args.vanilla_root)
    families = family_index(read(STANDARD))
    override = get_path('bg2ee_game_root', required=True) / 'override'
    rows = []
    for area in sorted(n for n, k in vanilla.index if k == 0x3E9):
        try:
            parsed, slots = liquid_slots(vanilla.wed(area))
        except Exception as error:          # corrupt or non-standard WED: report, do not stop
            rows.append({'area': area, 'error': str(error)})
            continue
        active = [s for s in slots if s['active']]
        if not active:
            continue
        base = parsed['layers'][0]['tis']
        base_tis = override / f'{base}.TIS'
        x4 = base_tis.is_file() and struct.unpack_from('<I', base_tis.read_bytes(), 20)[0] == 256
        prior = prior_state(area, parsed, active, override, vanilla)
        shared = sorted({s['source'] for s in active if (override / f"{s['source']}.TIS").is_file()})
        rows.append({'area': area,
                     'families': sorted({families[s['source']]['id'] if s['source'] in families else 'UNKNOWN:' + s['source']
                                         for s in active}),
                     'slots': [f"{s['slot']}:{s['source']}" for s in active],
                     'x4_base_installed': bool(x4),
                     'state': 'ready' if not prior else 'user-decision',
                     'prior_treatment': prior,
                     'shared_overlay_overridden': shared})
    if args.output:
        write(Path(args.output), {'schema': 'bg2-water-inventory-v1', 'areas': rows})
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))


def make_alias(area, key, kind, taken):
    salt = 0
    while True:
        value = int(hashlib.sha1(f'{area}|{key}|{kind}|{salt}'.encode()).hexdigest(), 16) % 36 ** 4
        code = ''.join(DIGITS[(value // 36 ** i) % 36] for i in range(3, -1, -1))
        alias = f'Y{kind}{code}'
        names = {alias, alias + 'R', page_name(alias), page_name(alias + 'R')}
        if not names & taken:
            taken.update(names)
            return alias
        salt += 1


def secondary_master(area, explicit):
    if explicit:
        path = Path(explicit)
        return (path if path.is_absolute() else ROOT / path), []
    base = area.rstrip('N') if area.endswith('N') else area
    found = sorted((ROOT / 'maps' / base / 'runs').glob('*/tuiles-secondaires/03_assemble/*.png'))
    night = [p for p in found if any(w in p.as_posix().lower() for w in ('nuit', 'night'))]
    found = night if area.endswith('N') else [p for p in found if p not in night]
    return (found[0] if len(found) == 1 else None), found


def plan(args):
    output = Path(args.output).resolve()
    output.relative_to(ROOT / 'maps')
    if output.exists():
        raise SystemExit('Refusing to overwrite an existing run')
    area = args.area.upper()
    standard = read(STANDARD)
    families = family_index(standard)
    vanilla = Vanilla(args.vanilla_root)
    game = get_path('bg2ee_game_root', required=True)
    override = game / 'override'
    parsed, slots = liquid_slots(vanilla.wed(area))
    active = [s for s in slots if s['active']]
    stops = []
    if not active:
        stops.append('no active liquid overlay in this WED')
    unknown = sorted({s['source'] for s in active if s['source'] not in families})
    if unknown:
        stops.append(f'unknown liquid overlay(s) {unknown}: not in liquid-family-standard-v1.json')
    stops += prior_state(area, parsed, active, override, vanilla)
    base = parsed['layers'][0]['tis']
    base_tis = override / f'{base}.TIS'
    if not base_tis.is_file() or struct.unpack_from('<I', base_tis.read_bytes(), 20)[0] != 256:
        stops.append(f'{base}.TIS: no installed x4 map base (upscale the map first)')
    master, candidates = secondary_master(area, args.secondary_master)
    if master is None or not master.is_file():
        stops.append('secondary master x4 not found or ambiguous; pass --secondary-master. Candidates: '
                     + str([p.relative_to(ROOT).as_posix() for p in candidates]))
    report = {'schema': 'bg2-water-map-plan-v1', 'area': area, 'standard': str(STANDARD.relative_to(ROOT)),
              'active_slots': active, 'stops': stops, 'decisions_owed': [],
              'notes': [f"{s['source']}.TIS is overridden (shared by other maps); this WED moves to an isolated "
                        f"alias and leaves the shared resource untouched" for s in active
                        if (override / f"{s['source']}.TIS").is_file()]}
    if stops:
        print(json.dumps(report, indent=2, ensure_ascii=False))
        raise SystemExit('STOP: ' + ' | '.join(stops))
    taken = set(vanilla.names) | {p.stem.upper() for p in override.iterdir()}
    groups, temporal_groups, target_slots = [], [], []
    by_family = {}
    for s in active:
        by_family.setdefault(families[s['source']]['id'], []).append(s)
    for family_id, members in by_family.items():
        family = next(f for f in standard['families'] if f['id'] == family_id)
        slot_of = {m['source']: m['slot'] for m in members}
        refs = family['overlays']
        missing = [r for r in refs if not vanilla.has_tis(r)]
        if missing:
            raise SystemExit(f'STOP: family {family_id} resources missing from KEY: {missing}')
        spatial = {r: make_alias(area, slot_of.get(r, f'm{i}'), 'S', taken) for i, r in enumerate(refs)}
        rain = all(vanilla.has_tis(r + 'R') for r in refs)
        for weather in ('dry', 'rain') if rain else ('dry',):
            suffix = 'R' if weather == 'rain' else ''
            groups.append({'id': family_id + ('_rain' if suffix else ''), 'wed': area,
                           'resrefs': [r + suffix for r in refs],
                           'aliases': {r + suffix: spatial[r] + suffix for r in refs},
                           'method': family['spatial_method'],
                           'layout': [[r + suffix for r in row] for row in family['layout']],
                           'seam_mode': 'compatible', 'weather': weather, 'source_wed_resrefs': refs})
        for r in refs:
            if r in slot_of:
                target_slots.append({'slot': slot_of[r], 'source': r, 'alias': spatial[r],
                                     'rain_alias': spatial[r] + 'R'})
        if not rain:
            report['decisions_owed'].append(f'{family_id}: no rain variant in KEY; dry only')
        temporal = family['temporal']
        if temporal['status'] == 'blocked':
            report['decisions_owed'].append(f"{family_id} 30 fps: {temporal['why']}")
            continue
        fps = {r: make_alias(area, slot_of.get(r, f'm{i}'), 'F', taken) for i, r in enumerate(refs)}
        temporal_groups.append(temporal_plan_group(family_id, fps, temporal))
        if rain:
            temporal_groups.append(temporal_plan_group(
                family_id + '_rain', {r + 'R': fps[r] + 'R' for r in refs}, temporal, family_id))
    output.mkdir(parents=True)
    write(output / 'request.json', {
        'schema': 'bg2-liquid-family-x4-trial-request-v1', 'standard': report['standard'],
        'source_vanilla': str(args.vanilla_root), 'destination': 'config://bg2ee_game_root',
        'runtime': {'dll': 'preserve-installed', 'mode': 'native-composition-alias-unregistered-route2-q0',
                    'timeline': 'preserve-vanilla-lookup-and-speed'},
        'targets': [{'wed': area, 'family': ','.join(by_family), 'slots': target_slots,
                     'secondary_master': master.relative_to(ROOT).as_posix(),
                     'composition': 'native', 'repair_seams': True}],
        'user_qa': 'pending', 'release': 'not-requested'})
    write(output / 'overlays-plan.json', {'schema': 'bg2-liquid-periodic-x4-trial-plan-v1',
                                          'color_correction_method': 'none', 'native_timeline': True,
                                          'groups': groups})
    if temporal_groups:
        write(output / 'temporal-plan.json', {
            'spatial_run': output.relative_to(ROOT).as_posix(), 'wed': area,
            'selection': (output / 'selection.json').relative_to(ROOT).as_posix(),
            'source_wed': (output / 'override-candidate' / f'{area}.WED').relative_to(ROOT).as_posix(),
            'groups': temporal_groups})
    report.update({'families': list(by_family), 'groups': [g['id'] for g in groups],
                   'temporal_groups': [g['id'] for g in temporal_groups],
                   'secondary_master': master.relative_to(ROOT).as_posix()})
    write(output / 'plan-report.json', report)
    print(json.dumps(report, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    i = sub.add_parser('inventory')
    i.add_argument('--vanilla-root', type=Path, required=True)
    i.add_argument('--output', type=Path)
    p = sub.add_parser('plan')
    p.add_argument('--area', required=True)
    p.add_argument('--vanilla-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--secondary-master', help='x4 secondary-tile master PNG when discovery is ambiguous')
    args = parser.parse_args()
    inventory(args) if args.command == 'inventory' else plan(args)


if __name__ == '__main__':
    main()
