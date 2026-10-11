"""Reinstall the existing AM0504SB ReboutCX trial; no new inference."""
from pathlib import Path
import csv
import io
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v
import area_animation_area_test as installer
import area_pack_state as state
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from workspace_paths import get_path

SOURCE = ROOT/'animations/packs-par-zone/lot2-small-effects-20261011-v1-complete/AR0504'
OUT = ROOT/'animations/batches/lot2-purple-reboutcx-trial-20261011-v1'
GAME = get_path('bg2ee_game_root')


def payload(path):
    return {p.name: v.sha256_file(p) for p in sorted(path.iterdir())
            if p.is_file() and p.name != 'manifest.json'}


def main():
    installer.ensure_game_stopped(installer.running_game_processes)
    v.validate_v2_pack(SOURCE)
    expected = payload(SOURCE)
    live = GAME/'iee-assets/areas/AR0504'
    before = payload(live)
    assert expected.keys() == before.keys()
    assert all(expected[n] == digest for n, digest in before.items()
               if not n.startswith('AAX4-AM0504SB-'))
    other_areas = {a: v.sha256_file(GAME/'iee-assets/areas'/a/v.REGISTRY_NAME)
                   for a in ['AR4000', 'AR0329', 'AR2903', 'AR0502']}
    OUT.mkdir(parents=True, exist_ok=False)
    v.write_json(OUT/'baseline.json', dict(area='AR0504', before=before, after=expected,
        source_pack=SOURCE.relative_to(ROOT).as_posix(), other_area_registries=other_areas))
    result = installer.install_area_pack(SOURCE, game_root=GAME)
    assert payload(live) == expected
    for a, digest in other_areas.items():
        assert v.sha256_file(GAME/'iee-assets/areas'/a/v.REGISTRY_NAME) == digest
    for attempt in range(3):
        try:
            state.record_zone('AR0504', GAME/'iee-assets/areas', leaf=SOURCE)
            break
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(.25)
    assert state.zone_signatures(live) == state.load_lock()['areas']['AR0504']['resources']
    v.write_json(OUT/'installation.json', dict(schema='bg2-upscale-animation-batch-installation-v1',
        status='installed', installed_utc=v.utc_now(), resrefs=['AM0504SB'], areas=['AR0504'],
        occurrences=6, source_pack=SOURCE.relative_to(ROOT).as_posix(),
        source_manifest_sha256=v.sha256_file(SOURCE/'manifest.json'),
        receipt=result.receipt_path.relative_to(ROOT).as_posix() if result.receipt_path else None,
        recipe='ReboutCX x4 -> Apollo8 30 FPS -> inner12 -> premultiply once',
        siblings_and_other_choices_preserved=True, qa_status='pending-ingame', release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry = ROOT/'animations/index/animation_upscale_registry.csv'
        rows = list(csv.DictReader(registry.open(encoding='utf-8-sig', newline='')))
        row = next(r for r in rows if r['resref'] == 'AM0504SB')
        assert row['status'] == 'à-valider' and not row['qa_decision']
        row.update(selected_run='am0504sb-lot2-small-effects-20261011-v1',
            correction_id='lot2-small-effects-20261011-v1',
            notes='Lot2: retour en ReboutCX x4/Apollo8 30 FPS/inner12 demandé et installé le 2026-10-11 '
                  'sur les 6 occurrences AR0504; reçu animations/batches/lot2-purple-reboutcx-trial-20261011-v1/installation.json; '
                  'QA ingame en attente; autres choix du lot2 conservés; release non sélectionnée.')
        buf = io.StringIO(newline='')
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        write_atomic(registry, buf.getvalue())
    print('INSTALLED: AM0504SB ReboutCX on all 6 AR0504 occurrences; other choices preserved')


if __name__ == '__main__':
    main()
