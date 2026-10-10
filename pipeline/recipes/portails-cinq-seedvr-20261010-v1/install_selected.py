"""User selection: OHRSGATE/SPDIMNDR SeedVR, BDFORCEW Rebout, others xBR.
Prepare seven complete area packs preserving currently installed siblings; install
via the existing transactional installer. No production history/release mutation.
"""
from pathlib import Path
import argparse
import copy
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v2
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
import area_pack_state as state
import area_animation_area_test as installer
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
from extract_area_animations import parse_area

TAG = 'portails-cinq-selection-20261010-v1'
BATCH = ROOT / 'animations/batches' / TAG
PACK = ROOT / 'animations/packs-par-zone' / (TAG + '-complete')

def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()

def payload(leaf):
    manifest, resources = v2.validate_v2_pack(leaf)
    names = [v2.REGISTRY_NAME] + [a['name'] for r in resources for a in r['assets']]
    return {name: v2.sha256_file(leaf / name) for name in names}

def prepare():
    assert not (BATCH / 'selection.json').exists() and not PACK.exists(), 'Selection already exists; use --install'
    BATCH.mkdir(parents=True, exist_ok=True)
    first = v2.load_json(ROOT / 'animations/batches/portails-cinq-20261010-v1/manifest.json')
    seed = v2.load_json(ROOT / 'animations/batches/portails-cinq-seedvr-20261010-v1/manifest.json')
    chosen = {j['resref']: copy.deepcopy(j) for j in first['resources']}
    chosen.update({j['resref']: copy.deepcopy(j) for j in seed['resources'] if j['resref'] in {'OHRSGATE', 'SPDIMNDR'}})
    game = get_path('bg2ee_game_root', required=True)
    lock = state.load_lock()['areas']
    by_area = {}
    for ref, job in chosen.items():
        split = ROOT / job['final_split']
        idx = v2.load_json(split / 'manifest.json')
        job['selected_manifests'] = []
        for a in idx['areas']:
            leaf = split / a['directory']
            by_area.setdefault(a['area_id'], []).append((ref, leaf))
            job['selected_manifests'].append({'path': rel(leaf / 'manifest.json'), 'sha256': v2.sha256_file(leaf / 'manifest.json')})
    roots = []
    checks = []
    for area, additions in sorted(by_area.items()):
        runtime = game / 'iee-assets/areas' / area
        specs = []
        before = {}
        if runtime.exists():
            assert area in lock and lock[area].get('build'), f'{area}: installed base unresolved'
            reconstructed = BATCH / 'base-reconstruction' / area.lower() / area
            base = reconstructed if reconstructed.exists() else state.build_leaf(area, lock[area]['build'], BATCH / 'base-reconstruction')
            before = payload(base)
            actual = {p.name: v2.sha256_file(p) for p in runtime.iterdir() if p.is_file()}
            assert actual == before, f'{area}: base differs from current runtime'
            _, resources = v2.validate_v2_pack(base)
            replacing = {r for r, _ in additions}
            specs.extend(str(base) + '::' + r['resref'] for r in resources if r['resref'] not in replacing)
        specs.extend(str(leaf) + '::' + ref for ref, leaf in additions)
        output = BATCH / 'complete-area-packs' / area
        merge.merge(specs, area, output, output.exists())
        leaf = output / area
        after = payload(leaf)
        kept = {name: sha for name, sha in before.items() if name != v2.REGISTRY_NAME and not any(name.startswith('AAX4-' + ref + '-') for ref, _ in additions)}
        assert all(after.get(name) == sha for name, sha in kept.items()), f'{area}: sibling bytes changed'
        for ref, source in additions:
            _, srcres = v2.validate_v2_pack(source)
            assert all(after[a['name']] == a['sha256'] for r in srcres if r['resref'] == ref for a in r['assets'])
        plan = installer.install_area_pack(leaf, verify_only=True)
        assert not plan.dropped
        roots.append(output)
        checks.append({'area_id': area, 'preserved_frames': len(kept), 'selected_resrefs': [r for r, _ in additions], 'incoming_bytes': plan.incoming_bytes, 'before_payload': before})
        print(f'PREPARED {area}: {len(kept)} sibling frames preserved', flush=True)
    combine.combine(roots, PACK, False)
    bifs, entries = load_key()
    selected_names = set(chosen)
    occurrences = []
    for area in sorted(by_area):
        override = game / 'override' / (area + '.ARE')
        if override.exists():
            data = override.read_bytes()
        else:
            entry = next(e for e in entries if e[0].upper() == area and e[1] == 0x3f2)
            data, _ = resolve_resource(bifs, entry[2])
        for row in parse_area(area, data):
            if row['resource_resref'] in selected_names:
                row['enabled_in_native_area'] = bool(int(row['flags_hex'], 16) & 1)
                occurrences.append(row)
    record = {'schema': 'bg2-upscale-animation-user-selection-v1', 'status': 'prepared', 'created_utc': v2.utc_now(),
              'decision_origin': 'explicit-user-preview-selection', 'decision': 'SeedVR OHRSGATE/SPDIMNDR; ReboutCX BDFORCEW; xBR OHDLPORT/OHHPORT; install ingame',
              'resources': list(chosen.values()), 'complete_pack': rel(PACK), 'complete_manifest_sha256': v2.sha256_file(PACK / 'manifest.json'),
              'area_checks': checks, 'occurrences': occurrences, 'qa_status': 'preview-accepted-pending-ingame', 'release_status': 'not-selected'}
    v2.write_json(BATCH / 'selection.json', record)

def install():
    record = v2.load_json(BATCH / 'selection.json')
    assert v2.sha256_file(PACK / 'manifest.json') == record['complete_manifest_sha256']
    out = BATCH / 'installation.json'
    receipt = v2.load_json(out) if out.exists() else {'schema': 'bg2-upscale-animation-batch-installation-v1', 'status': 'installing', 'created_utc': v2.utc_now(), 'complete_pack': rel(PACK), 'areas': [], 'qa_status': 'pending-ingame', 'release_status': 'not-selected'}
    for check in record['area_checks']:
        area = check['area_id']
        leaf = PACK / area
        if any(a['area_id'] == area for a in receipt['areas']):
            assert payload(leaf) == {p.name: v2.sha256_file(p) for p in (get_path('bg2ee_game_root') / 'iee-assets/areas' / area).iterdir() if p.is_file()}
            continue
        result = installer.install_area_pack(leaf)
        installer.record_lock(area, leaf, installer.DEFAULT_GAME_ROOT)
        receipt['areas'].append({'area_id': area, 'status': result.status, 'receipt': rel(result.receipt_path) if result.receipt_path else None,
                                 'pack_manifest_sha256': v2.sha256_file(leaf / 'manifest.json'), 'preserved_frames': check['preserved_frames']})
        v2.write_json(out, receipt)
        print(f'INSTALLED {area}: {result.status}', flush=True)
    receipt['status'] = 'installed'
    v2.write_json(out, receipt)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    install() if args.install else prepare()
