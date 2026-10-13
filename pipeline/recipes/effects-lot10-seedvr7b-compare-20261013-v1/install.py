"""Replace only the ten compared effects; retain the current stable renderer."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1'
INSTALL = ROOT / 'effects/installations/lot10-seedvr7b-apollo30-20261013-v1'
BUILD = ROOT / 'build/iee-character-stable-effect-cache64-20261013-v1'
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from workspace_paths import get_path
from compose_effect_runtime_packs import validate_pack, compose, write_pack, sha256_file
import effect_workflow as workflow
import effect_authority as authority
import install_renderer_candidate as installer


def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def relative(path): return path.relative_to(ROOT).as_posix()
def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare():
    batch = load(BATCH / 'batch.json'); checks = load(BATCH / 'verification.json')
    assert checks['checked'] == checks['passed'] == 10 and not checks['failures']
    assert len(load(BATCH / 'preview/comparison.json')['assets']) == 10
    game = get_path('bg2ee_game_root', required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    selected = {a['resref']: a for a in batch['assets']}
    old = validate_pack(game / 'iee-assets/effects')
    stable = load(ROOT / 'docs/measurements/character-stable-cache64-20261013-v1/installation.json')
    assert sha256_file(game / 'InfinityEngine-Enhancer.dll') == stable['dll_sha256']
    for path, digest in stable['preserved_sha256'].items():
        assert sha256_file(game / path) == digest, path
    INSTALL.mkdir(parents=True, exist_ok=False)
    before = INSTALL / 'installed-before'; before.mkdir()
    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']:
        shutil.copy2(game / name, before / name)
    for name in ['manifest.json', 'EffectAnimations-X4.registry']:
        shutil.copy2(game / 'iee-assets/effects' / name, before / name)
    shutil.copy2(ROOT / 'effects/index/processing.csv', before / 'processing.csv')
    packs, replaced = [], set()
    for source in old.manifest['source_packs']:
        original = validate_pack(ROOT / source['path'])
        assert original.manifest_sha256 == source['manifest_sha256']
        names = {r['resref'] for r in original.resources}
        overlap = names & selected.keys()
        if overlap:
            assert len(names) == len(overlap) == 1, 'replacement must be a unit pack'
            name = next(iter(overlap)); asset = selected[name]
            replacement = validate_pack(ROOT / asset['pack'])
            checked = load(BATCH / 'checks' / (name+'.json'))
            assert checked['passed']
            assert replacement.manifest_sha256 == checked['checked_inputs']['pack_manifest_sha256']
            assert replacement.manifest['registry_sha256'] == checked['registry_sha256']
            spatial = load(ROOT / 'effects/ressources' / name / 'runs' / asset['spatial_run'] / '01-spatial-x4/manifest.json')
            assert spatial['scale'] == 4 and spatial['parameters']['scale'] == 4
            assert spatial['parameters']['model'] == 'seedvr2_7b_int8_convrot.safetensors'
            timing = replacement.resources[0]['timeline']
            assert replacement.registry_version == 2 and timing['native_fps'] == [15, 1]
            assert timing['target_fps'] == [30, 1]
            assert timing['phase_count'] == checked['native_slots'] * 2
            for frame in replacement.frames:
                assert frame['physical_size_x4'] == [v * 4 for v in frame['logical_size_x1']]
            packs.append(replacement); replaced.add(name)
        else:
            packs.append(original)
    assert replaced == selected.keys()
    candidate = INSTALL / 'candidate'; candidate.mkdir()
    registry, manifest, copies = compose(packs)
    write_pack(candidate / 'iee-assets/effects', registry, manifest, copies)
    combined = validate_pack(candidate / 'iee-assets/effects')
    assert combined.resource_count == old.resource_count == 64
    assert {r['resref'] for r in combined.resources} == {r['resref'] for r in old.resources}
    kept_frames = {f['asset']: f['sha256'] for f in old.frames if f['resref'] not in selected}
    after_frames = {f['asset']: f['sha256'] for f in combined.frames}
    assert all(after_frames.get(name) == digest for name, digest in kept_frames.items())
    old_resources = {r['resref']: r for r in old.resources}
    assert all(r == old_resources[r['resref']] for r in combined.resources if r['resref'] not in selected)
    raw_bytes = sum(f['bytes'] for f in combined.frames)
    assert raw_bytes <= 2048 * 1024 * 1024
    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']:
        shutil.copy2(before / name, candidate / name)
    with (INSTALL / 'native-runtime-pack-check.log').open('w', encoding='utf-8') as log:
        subprocess.run([str(BUILD / 'Release/iee_effect_animation_x4_registry_tests.exe'),
                        str(candidate / 'iee-assets/effects')], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    plan = {'schema': 'bg2-effects-7b-install-plan-v1', 'resrefs': list(selected),
        'candidate': relative(candidate), 'new_packs': [a['pack'] for a in batch['assets']],
        'active_before_manifest_sha256': old.manifest_sha256,
        'registry_version': 2, 'scale': 4, 'target_fps': [30, 1],
        'resource_count': 64, 'replaced_resources': 10, 'preserved_resources': 54,
        'frames': len(combined.frames), 'raw_bytes': raw_bytes,
        'registry_sha256': manifest['registry_sha256'],
        'manifest_sha256': combined.manifest_sha256,
        'dll_sha256': sha256_file(candidate / 'InfinityEngine-Enhancer.dll'),
        'ini_sha256': sha256_file(candidate / 'InfinityEngine-Enhancer.ini'),
        'preserved_runtime_sha256': stable['preserved_sha256'],
        'native_pack_load_passed': True, 'visual_qa': 'pending-user-ingame'}
    save(INSTALL / 'install-plan.json', plan)
    installer.install_candidate(candidate, game_root=game, backup_root=INSTALL / 'backups', verify_only=True)
    print(json.dumps(plan, indent=2), flush=True)


def install():
    plan = load(INSTALL / 'install-plan.json'); game = get_path('bg2ee_game_root', required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']:
        assert sha256_file(game / name) == sha256_file(INSTALL / 'installed-before' / name)
    assert validate_pack(game / 'iee-assets/effects').manifest_sha256 == plan['active_before_manifest_sha256']
    before_rows = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
    result = installer.install_candidate(ROOT / plan['candidate'], game_root=game, backup_root=INSTALL / 'backups')
    installer.verify_transaction(result.receipt_path, game_root=game)
    installed = validate_pack(game / 'iee-assets/effects')
    assert installed.manifest['registry_sha256'] == plan['registry_sha256']
    assert installed.manifest_sha256 == plan['manifest_sha256']
    assert sha256_file(game / 'InfinityEngine-Enhancer.dll') == plan['dll_sha256']
    for path, digest in plan['preserved_runtime_sha256'].items():
        if path != 'iee-assets/effects/EffectAnimations-X4.registry':
            assert sha256_file(game / path) == digest, path
    receipt = relative(result.receipt_path)
    assets = load(BATCH / 'batch.json')['assets']
    by_resref = {r['resref']: r for r in installed.resources}
    old_manifest = load(INSTALL / 'installed-before/manifest.json')
    old_hashes = {f['asset']: f['sha256'] for f in old_manifest['frames']}
    payload_checks = []
    for asset in assets:
        name = asset['resref']; resource = by_resref[name]
        assert resource['source']['spatial_run'] == asset['spatial_run']
        assert resource['source']['interpolation_run'] == asset['treatment_run']
        unit = validate_pack(ROOT / asset['pack'])
        actual = {f['asset']: f['sha256'] for f in installed.frames if f['resref'] == name}
        assert actual == {f['asset']: f['sha256'] for f in unit.frames}
        changed = sum(digest != old_hashes.get(filename) for filename, digest in actual.items())
        assert changed > 0, 'must contain real 7B pixels rather than only relabel a 3B pack'
        payload_checks.append({'resref': name, 'scale': 4, 'target_fps': [30,1],
            'phase_count': resource['timeline']['phase_count'], 'changed_backings': changed,
            'all_installed_pixels_match_7b_pack': True,
            'spatial_run': asset['spatial_run'], 'interpolation_run': asset['treatment_run']})
    for asset in assets:
        workflow.register_run(ROOT, asset['resref'], 'spatial', asset['spatial_run'], write=True)
        workflow.register_run(ROOT, asset['resref'], 'interpolation', asset['treatment_run'], write=True)
    with authority.guard(ROOT, write=True):
        processing = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
        selected = set(plan['resrefs']); changed = 0
        originals = {r['asset_key']: r for r in before_rows}
        for row in processing:
            if row['asset_key'].rsplit(':', 1)[-1] in selected:
                row['installation_state'] = 'installed'; row['installation_receipt'] = receipt; changed += 1
                assert all(row[k] == originals[row['asset_key']][k] for k in
                           ['selected_run','qa_state','qa_evidence','release_state','release_candidate'])
            else:
                assert row == originals[row['asset_key']], row['asset_key']
        assert changed == 10
        authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(processing)})
    final = {'schema': 'bg2-effects-7b-installation-v1', 'status': 'installed-verified',
        'resrefs': plan['resrefs'], 'model': 'seedvr2_7b_int8_convrot.safetensors',
        'scale': 4, 'target_fps': [30,1], 'registry_version': 2,
        'receipt': receipt, 'registry_sha256': plan['registry_sha256'],
        'manifest_sha256': installed.manifest_sha256, 'payload_checks': payload_checks,
        'resource_count': 64, 'preserved_resources': 54, 'raw_bytes': plan['raw_bytes'],
        'dll_sha256': plan['dll_sha256'], 'renderer_and_character_profile_preserved': True,
        'per_asset_technical_checks': '10/10 passed; input hashes bound to installed packs',
        'visual_qa': 'pending-user-ingame'}
    save(INSTALL / 'installation-result.json', final)
    save(BATCH / 'installation.json', final)
    print(json.dumps(final, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare','install'])
    args = parser.parse_args(); prepare() if args.action == 'prepare' else install()
