"""Post-treatment water re-check queue (q, rain, night) stored in ingame-map-tracking-v1.json.

    python pipeline/scripts/water_review_queue.py list [--kind q|rain|night] [--all]
    python pipeline/scripts/water_review_queue.py record --wed AR3000 --kind q --state validated --quote "<user message>"
    python pipeline/scripts/water_review_queue.py sync-q          # copy live registry q values into the tracker

Principle (campaign.review): INI WaterOverlayStrength = 1.00; q is set per WED identity in the
route2 registry, so changing a map's q = registry entry + DLL build + Install-WaterRuntime.ps1,
then ``sync-q`` and ``record``. Rain identities stay q0 unless a rain review decides otherwise.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACKING = ROOT / 'pipeline/water/ingame-map-tracking-v1.json'
POINTER = ROOT / 'pipeline/water/route2-registry-current.json'
KINDS = ('q', 'rain', 'night')


def load():
    return json.loads(TRACKING.read_text(encoding='utf-8'))


def save(data):
    data['updated'] = date.today().isoformat()
    TRACKING.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')


def families(item):
    return sorted({o['family'] for o in item['overlays']})


def cmd_list(args):
    data = load()
    kinds = [args.kind] if args.kind else list(KINDS)
    for kind in kinds:
        rows = [m for m in data['maps']
                if m['review'][kind]['state'] == 'pending' or (args.all and m['review'][kind]['state'] != 'not-applicable')]
        print(f'## {kind} ({len(rows)})')
        for m in rows:
            r = m['review'][kind]
            qs = ' '.join(f"{i['overlay']}={i['q']:g}" for i in r.get('current', []))
            extra = {'q': '', 'rain': ' ; C:SetWeather(1), jeu non en pause, ~10 s',
                     'night': ' ; passer la nuit (repos/attente) pour charger la WED nuit'}[kind]
            print(f"{m['wed']:8} {r['state']:10} {','.join(families(m)):22} {qs:40} "
                  f"C:MoveToArea(\"{m['area_id']}\"){extra}")


def cmd_record(args):
    data = load()
    target = next((m for m in data['maps'] if m['wed'] == args.wed.upper()), None)
    if target is None:
        raise SystemExit(f'unknown WED: {args.wed}')
    review = target['review'][args.kind]
    if review['state'] == 'not-applicable':
        raise SystemExit(f'{args.wed} {args.kind}: review not applicable')
    review['state'] = args.state
    if args.quote:
        review['evidence'].append(f"{date.today().isoformat()} user: {args.quote}")
    if args.state == 'validated' and not review['evidence']:
        raise SystemExit('validated review needs --quote')
    save(data)
    print(f"{args.wed} {args.kind} -> {args.state}")


def cmd_sync_q(args):
    pointer = json.loads(POINTER.read_text(encoding='utf-8'))
    entries = json.loads((ROOT / pointer['registry']['path']).read_text(encoding='utf-8'))['entries']
    by_wed = defaultdict(list)
    for e in entries:
        by_wed[e['wed']['resref']].append(e)
    data = load()
    changed = 0
    for m in data['maps']:
        ents = sorted(by_wed.get(m['wed'], []), key=lambda e: (e['overlay']['slot'], e['overlay']['tis_resref']))
        names = {e['overlay']['tis_resref'] for e in ents}
        dry = [e for e in ents if not (e['overlay']['tis_resref'].endswith('R') and e['overlay']['tis_resref'][:-1] in names)]
        rain = [e for e in ents if e not in dry]
        ident = lambda e: {'slot': e['overlay']['slot'], 'overlay': e['overlay']['tis_resref'],
                           'q': float(e['approved_strength'])}
        q_now = [ident(e) for e in dry]
        rain_now = [ident(e) for e in rain] if m['review']['rain']['weather'] else []
        if m['review']['q']['current'] != q_now or m['review']['rain']['current'] != rain_now:
            m['review']['q']['current'], m['review']['rain']['current'] = q_now, rain_now
            changed += 1
    save(data)
    print(f'synced {changed} maps from {pointer["registry"]["path"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('list')
    listing.add_argument('--kind', choices=KINDS)
    listing.add_argument('--all', action='store_true', help='also show already validated reviews')
    record = sub.add_parser('record')
    record.add_argument('--wed', required=True)
    record.add_argument('--kind', choices=KINDS, required=True)
    record.add_argument('--state', choices=('pending', 'validated'), required=True)
    record.add_argument('--quote')
    sub.add_parser('sync-q')
    args = parser.parse_args()
    {'list': cmd_list, 'record': cmd_record, 'sync-q': cmd_sync_q}[args.command](args)


if __name__ == '__main__':
    main()
