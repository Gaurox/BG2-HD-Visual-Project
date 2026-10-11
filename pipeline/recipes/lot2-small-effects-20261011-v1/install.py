"""Install exactly five prepared lot2 areas; preserve siblings/runtime/WED/ARE."""
from pathlib import Path
import csv
import io
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v
import area_animation_area_test as installer
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
from extract_area_animations import parse_area

TAG = 'lot2-small-effects-20261011-v1'
BATCH = ROOT/'animations/batches'/TAG
PACK = ROOT/'animations/packs-par-zone'/(TAG+'-complete')
GAME = get_path('bg2ee_game_root')
TARGETS = {'AM0504SB': 'AR0504', 'AM4000Z': 'AR4000', 'BUBBLEA': 'AR2903',
           'EYESRED1': 'AR0329', 'WTRBODY1': 'AR0502'}


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def payload(path):
    return {p.name: v.sha256_file(p) for p in sorted(path.iterdir()) if p.is_file()}


def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    baseline = v.load_json(BATCH/'baseline.json')
    receipt_path = BATCH/'installation.json'
    record = v.load_json(receipt_path) if receipt_path.exists() else dict(
        schema='bg2-upscale-animation-batch-installation-v1', status='installing',
        created_utc=v.utc_now(), complete_pack=rel(PACK), areas=[],
        qa_status='pending-ingame', release_status='not-selected')
    completed = {x['area_id'] for x in record['areas']}
    observations = {name: v.sha256_file(GAME/name)
                    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']}
    for area, before in baseline.items():
        live = GAME/'iee-assets/areas'/area
        if area in completed:
            assert payload(live) == before['output_payload'], area + ': installed pack changed'
        else:
            assert live.exists() == before['present'], area + ': presence changed since preparation'
            if live.exists():
                assert payload(live) == before['payload'], area + ': active payload changed since preparation'
            result = installer.install_area_pack(PACK/area, verify_only=True)
            assert not result.dropped

    bifs, entries = load_key()
    are_lookup = {n.upper(): loc for n, t, loc in entries if t == 0x3f2}
    occurrences, originals = [], {}
    for area in sorted(set(TARGETS.values())):
        override = GAME/'override'/(area+'.ARE')
        data = override.read_bytes() if override.exists() else resolve_resource(bifs, are_lookup[area])[0]
        originals[area] = dict(are_sha256=__import__('hashlib').sha256(data).hexdigest(),
                              wed_resref=data[8:16].split(b'\0')[0].decode())
        for row in parse_area(area, data):
            if row['resource_resref'] in TARGETS:
                assert int(row['flags_hex'], 16) & 1, f'{area}: disabled occurrence'
                occurrences.append(row)
    expected = list(csv.DictReader((ROOT/'animations/index/occurrences.csv').open(encoding='utf-8-sig')))
    keys = lambda rows: sorted((r['area_id'], r['resource_resref'], int(r['x']), int(r['y']),
                               int(r['sequence']), int(r['initial_frame']), r['flags_hex']) for r in rows)
    assert keys(occurrences) == keys([r for r in expected if r['resource_resref'] in TARGETS])
    assert len(occurrences) == 21
    record['occurrences'] = occurrences
    record['native_areas'] = originals
    commands = ['# Lot2 — 21 occurrences / 5 cartes', '',
                'Coordonnées logiques x1. `,0` cible le premier portrait. Fermer la console et reprendre le jeu après le saut.', '']
    for ref, area in TARGETS.items():
        commands.extend([f'## {ref} / {area}', '', '```lua', f'C:MoveToArea("{area}")'])
        commands.extend(f"C:Eval('JumpToPoint([{r['x']}.{r['y']}])',0)"
                        for r in occurrences if r['resource_resref'] == ref)
        commands.extend(['```', ''])
    (BATCH/'CLUA.md').write_text('\n'.join(commands), encoding='utf-8')

    for area in sorted(baseline):
        if area in completed:
            continue
        result = installer.install_area_pack(PACK/area, game_root=GAME,
                                             backup_root=ROOT/'backups/animations/area-tests')
        assert payload(GAME/'iee-assets/areas'/area) == baseline[area]['output_payload']
        installer.record_lock(area, PACK/area, GAME)
        record['areas'].append(dict(area_id=area, status=result.status,
                                    receipt=rel(result.receipt_path) if result.receipt_path else None,
                                    incoming_files=result.incoming_files, incoming_bytes=result.incoming_bytes,
                                    pack_manifest_sha256=v.sha256_file(PACK/area/'manifest.json')))
        v.write_json(receipt_path, record)
        print('INSTALLED', area, result.status, flush=True)
    for name, digest in observations.items():
        assert v.sha256_file(GAME/name) == digest, 'Runtime changed: ' + name
    record.update(status='installed', installed_utc=v.utc_now(), runtime_unchanged=observations,
                  all_21_occurrences_installed=True, siblings_preserved=True)
    v.write_json(receipt_path, record)

    with animation_authority_lock(ROOT):
        registry = ROOT/'animations/index/animation_upscale_registry.csv'
        rows = list(csv.DictReader(registry.open(encoding='utf-8-sig', newline='')))
        for row in rows:
            ref = row['resref']
            if ref not in TARGETS:
                continue
            assert row['status'] in ('non-traité', 'à-valider') and not row['qa_decision']
            row.update(status='à-valider', selected_run=f'{ref.lower()}-{TAG}',
                       qa_decision='', qa_date='', correction_id=TAG,
                       notes=f'Lot2 x4 installé le 2026-10-11 sur {TARGETS[ref]}; recette pipeline/recipes/{TAG}/build.py; '
                             f'reçu animations/batches/{TAG}/installation.json; QA ingame en attente; release non sélectionnée.')
        buffer = io.StringIO(newline='')
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        write_atomic(registry, buffer.getvalue())
    print('DONE: 5 assets, 5 maps, 21 occurrences; QA pending; CLUA:', rel(BATCH/'CLUA.md'))


if __name__ == '__main__':
    main()
