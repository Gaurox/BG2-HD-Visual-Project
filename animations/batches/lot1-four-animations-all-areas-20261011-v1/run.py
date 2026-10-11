"""Prepare/verify or transactionally install the four existing lot-1 results."""
import argparse
import csv
import dataclasses
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'pipeline/area-animation-area-test'))
import area_pack_state as state
import merge_area_pack_resources as merger
import area_animation_area_test as installer

SOURCES = {
    'AM5204C': 'am5204c-reboutcx-apo8-x4-30fps-v2-aura16-20260922',
    'AM5204D': 'am5204d-seedvr7b-apo8-x4-30fps-v2-innerfeather16-premul-20260922',
    'AM5508C': 'am5508c-reboutcx-apo8-x4-30fps-v2-innerfeather16-premul-20260922',
    'AM5508D': 'am5508d-reboutcx-apo8-x4-30fps-v2-innerfeather16-premul-20260922',
}
AREAS = ['AR5204', 'OH4210', 'AR5201', 'AR5502', 'AR5501', 'AR5506', 'AR5507', 'AR5508']


def save(name, value):
    path = BATCH / name
    temporary = path.with_suffix(path.suffix + '.part')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def prepare():
    assert not (BATCH / 'manifest.json').exists(), 'Preparation already completed'
    installer.ensure_game_stopped(installer.running_game_processes)
    lock = state.load_lock()
    with (ROOT / 'animations/index/occurrences.csv').open(encoding='utf-8-sig') as stream:
        occurrences = list(csv.DictReader(stream))
    plan = []
    for area in AREAS:
        target = state.game_areas_dir() / area
        before = state.zone_signatures(target) if target.exists() else {}
        entry = lock['areas'].get(area, {})
        assert before == entry.get('resources', {}), (area, 'installation differs from lock')
        inputs = []
        if before:
            base = state.build_leaf(area, entry['build'], BATCH / 'preserved-sources')
            assert state.leaf_signatures(base) == before, (area, 'reconstruction differs')
            manifest = json.loads((base / 'manifest.json').read_text(encoding='utf-8'))
            for resource in manifest['resources']:
                if resource['resref'] not in SOURCES:
                    assert resource.get('position') is None, 'position binding requires explicit handling'
                    inputs.append(state.rel(base) + '::' + resource['resref'])
        lot_resources = sorted({row['resource_resref'] for row in occurrences
                                if row['area_id'] == area and row['resource_resref'] in SOURCES})
        expected = {key: value for key, value in before.items() if state.base_resref(key) not in SOURCES}
        for resref in lot_resources:
            source = ROOT / 'animations/packs-par-zone' / SOURCES[resref] / area
            inputs.append(state.rel(source))
            expected.update(state.leaf_signatures(source))
        output = ROOT / 'animations/packs-par-zone' / BATCH.name / area.lower()
        merger.merge(inputs, area, output, False)
        leaf = output / area
        assert state.leaf_signatures(leaf) == expected, (area, 'resource bytes changed')
        result = installer.install_area_pack(leaf, verify_only=True)
        assert not result.dropped, (area, result.dropped)
        plan.append({'area': area, 'pack': state.rel(leaf), 'before': before, 'expected': expected,
                     'lot_resources': lot_resources, 'files': result.incoming_files,
                     'bytes': result.incoming_bytes,
                     'manifest_sha256': state.sha256_file(leaf / 'manifest.json')})
        print(area, 'verified', ','.join(expected), round(result.incoming_bytes / 1048576, 2), 'MiB', flush=True)
    save('manifest.json', {'schema': 'bg2-upscale-animation-installed-lot-v1', 'status': 'completed',
                          'created_utc': state.utc_now(), 'qa_status': 'pending',
                          'game_root': 'config://bg2ee_game_root', 'resrefs': sorted(SOURCES),
                          'source_recipe': 'Existing 20260922 x4/30fps results, unchanged bytes; complete per-area merge',
                          'areas': plan})
    save('local-checks.json', {'status': 'passed', 'areas': AREAS,
                              'checks': ['source packs validated by merger', 'installation matches lock',
                                         'preserved and target frame signatures unchanged',
                                         'runtime budget enforced', 'VerifyOnly: no resources dropped']})


def install():
    assert not (BATCH / 'installation.json').exists(), 'Installation receipt already exists'
    manifest = json.loads((BATCH / 'manifest.json').read_text(encoding='utf-8'))
    results = []
    for item in manifest['areas']:
        area = item['area']
        leaf = ROOT / item['pack']
        target = state.game_areas_dir() / area
        actual = state.zone_signatures(target) if target.exists() else {}
        assert actual == item['before'], (area, 'installation changed since preparation')
        assert state.sha256_file(leaf / 'manifest.json') == item['manifest_sha256']
        result = installer.install_area_pack(leaf)
        installer.record_lock(area, leaf, installer.DEFAULT_GAME_ROOT)
        assert state.zone_signatures(target) == item['expected'], (area, 'installed bytes differ')
        assert state.load_lock()['areas'][area]['resources'] == item['expected'], (area, 'lock not recorded')
        value = dataclasses.asdict(result)
        value['receipt_path'] = str(result.receipt_path) if result.receipt_path else None
        results.append(value)
        save('installation.json', {'status': 'completed' if len(results) == len(AREAS) else 'installing',
                                   'updated_utc': state.utc_now(), 'game_root': 'config://bg2ee_game_root',
                                   'qa_status': 'pending', 'areas': results})
        print(area, result.status, 'verified exact bytes; no resource dropped', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'install'])
    args = parser.parse_args()
    prepare() if args.mode == 'prepare' else install()
