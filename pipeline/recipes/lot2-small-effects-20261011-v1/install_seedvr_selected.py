"""User choice: SeedVR AM0504SB/AM4000Z/EYESRED1; preserve the other two."""
from pathlib import Path
import argparse
import csv
import io
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
import area_pack_state as state
import area_animation_area_test as installer
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from workspace_paths import get_path

TAG = 'lot2-seedvr-selected-20261011-v1'
BATCH = ROOT/'animations/batches'/TAG
PACK = ROOT/'animations/packs-par-zone'/(TAG+'-complete')
SEED = ROOT/'animations/batches/lot2-seedvr-comparison-20261011-v1/artifacts/final-split'
GAME = get_path('bg2ee_game_root')
JOBS = {'AM0504SB': 'AR0504', 'AM4000Z': 'AR4000', 'EYESRED1': 'AR0329'}
KEEP = ['AR2903', 'AR0502']


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def payload(path):
    return {p.name: v.sha256_file(p) for p in sorted(path.iterdir())
            if p.is_file() and p.name != 'manifest.json'}


def prepare():
    BATCH.mkdir(parents=True, exist_ok=False)
    lock = state.load_lock()
    bases, roots = {}, []
    for ref, area in JOBS.items():
        live = GAME/'iee-assets/areas'/area
        base = ROOT/lock['areas'][area]['build']['leaf']
        _, old = v.validate_v2_pack(base)
        assert payload(base) == payload(live), area + ': active baseline differs'
        _, new = v.validate_v2_pack(SEED/area)
        target = next(r for r in new if r['resref'] == ref)
        previous = next(r for r in old if r['resref'] == ref)
        assert v.resource_binary_v2(previous, 3) == v.resource_binary_v2(target, 3)
        specs = [str(base)+'::'+r['resref'] for r in old if r['resref'] != ref]
        specs.append(str(SEED/area)+'::'+ref)
        destination = ROOT/'animations/packs-par-zone'/(TAG+'-'+area)
        merge.merge(specs, area, destination, False)
        before, after = payload(live), payload(destination/area)
        assert before[v.REGISTRY_NAME] == after[v.REGISTRY_NAME]
        for name, digest in before.items():
            if not name.startswith('AAX4-'+ref+'-'):
                assert after[name] == digest, area + ': sibling changed ' + name
        assert all(after[a['name']] == a['sha256'].lower() for a in target['assets'])
        roots.append(destination)
        bases[area] = dict(resref=ref, before=before, after=after)
    combine.combine(roots, PACK, False)
    for area in KEEP:
        bases[area] = dict(before=payload(GAME/'iee-assets/areas'/area), preserved=True)
    v.write_json(BATCH/'baseline.json', bases)
    v.write_json(BATCH/'manifest.json', dict(schema='bg2-upscale-animation-user-selection-v1',
        status='prepared', created_utc=v.utc_now(), resrefs=list(JOBS),
        decision_origin='explicit-user-preview-choice',
        decision='SeedVR AM0504SB/AM4000Z/EYESRED1; keep BUBBLEA/WTRBODY1 current recipes',
        complete_pack=rel(PACK), complete_manifest_sha256=v.sha256_file(PACK/'manifest.json'),
        qa_status='preview-selected-pending-ingame', release_status='not-selected'))
    print('PREPARED: 3 SeedVR assets / 3 maps / 17 occurrences; other two preserved')


def install():
    installer.ensure_game_stopped(installer.running_game_processes)
    baseline = v.load_json(BATCH/'baseline.json')
    choice = v.load_json(BATCH/'manifest.json')
    assert v.sha256_file(PACK/'manifest.json') == choice['complete_manifest_sha256']
    runtime = {n: v.sha256_file(GAME/n) for n in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']}
    path = BATCH/'installation.json'
    record = v.load_json(path) if path.exists() else dict(
        schema='bg2-upscale-animation-batch-installation-v1', status='installing',
        created_utc=v.utc_now(), complete_pack=rel(PACK), areas=[],
        qa_status='pending-ingame', release_status='not-selected')
    done = {r['area_id'] for r in record['areas']}
    for area, row in baseline.items():
        actual = payload(GAME/'iee-assets/areas'/area)
        assert actual == row['after' if area in done else 'before'], area + ': live payload changed'
        if not row.get('preserved') and area not in done:
            plan = installer.install_area_pack(PACK/area, verify_only=True)
            assert not plan.dropped
    for area in sorted(JOBS.values()):
        if area not in done:
            result = installer.install_area_pack(PACK/area, game_root=GAME)
            record['areas'].append(dict(area_id=area, status=result.status,
                receipt=rel(result.receipt_path) if result.receipt_path else None,
                incoming_files=result.incoming_files, incoming_bytes=result.incoming_bytes,
                pack_manifest_sha256=v.sha256_file(PACK/area/'manifest.json')))
            v.write_json(path, record)
        assert payload(GAME/'iee-assets/areas'/area) == baseline[area]['after']
        for attempt in range(3):
            try:
                state.record_zone(area, GAME/'iee-assets/areas', leaf=(PACK/area).resolve())
                break
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(.25)
        print('INSTALLED', area, flush=True)
    for area in KEEP:
        assert payload(GAME/'iee-assets/areas'/area) == baseline[area]['before']
    for name, digest in runtime.items():
        assert v.sha256_file(GAME/name) == digest
    lock = state.load_lock()
    for area in JOBS.values():
        assert state.zone_signatures(GAME/'iee-assets/areas'/area) == lock['areas'][area]['resources']
    record.update(status='installed', installed_utc=v.utc_now(),
        selected_assets=list(JOBS), selected_occurrences=17,
        kept_assets=['BUBBLEA', 'WTRBODY1'], siblings_preserved=True, runtime_unchanged=runtime)
    v.write_json(path, record)
    for ref, area in JOBS.items():
        wrapper = ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-{TAG}'
        wrapper.mkdir(parents=True, exist_ok=True)
        if not (wrapper/'manifest.json').exists():
            v.write_json(wrapper/'manifest.json', dict(schema='bg2-upscale-animation-visual-treatment-v1',
                status='completed', created_utc=v.utc_now(), resref=ref, resrefs=[ref],
                source_run='animations/batches/lot2-seedvr7b-lab-x4-20261011-v1',
                output_split_root=rel(PACK), source_pack=rel(PACK/area),
                source_pack_manifest_sha256=v.sha256_file(PACK/area/'manifest.json'),
                recipe=dict(spatial='SeedVR2 7B INT8/LAB x4', seed=20261011,
                    inner_feather_x4=12 if ref == 'AM0504SB' else 0,
                    playback='Native' if ref == 'EYESRED1' else 'Apollo8 30 FPS',
                    rgb='premultiply once'),
                installation=rel(path), qa_status='preview-selected-pending-ingame', release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry = ROOT/'animations/index/animation_upscale_registry.csv'
        rows = list(csv.DictReader(registry.open(encoding='utf-8-sig', newline='')))
        for row in rows:
            ref = row['resref']
            if ref not in JOBS:
                continue
            assert row['status'] == 'à-valider' and not row['qa_decision']
            row.update(selected_run=f'{ref.lower()}-{TAG}', correction_id=TAG,
                notes=f'Lot2: variante SeedVR2 7B INT8/LAB choisie en comparatif et installée le 2026-10-11 sur {JOBS[ref]}; '
                      f'reçu animations/batches/{TAG}/installation.json; QA ingame en attente; release non sélectionnée.')
        out = io.StringIO(newline='')
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        write_atomic(registry, out.getvalue())
    print('DONE: SeedVR installed on all 17 selected occurrences; BUBBLEA/WTRBODY1 unchanged')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    install() if args.install else prepare()
