"""Install the checked 33-effect 7B batch; preserve all 64 existing effects and character settings."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot33-seedvr7b-apollo30-20261014-v1'
OUT = ROOT / 'effects/installations/lot33-seedvr7b-apollo30-nearest-20261014-v1'
BUILD = ROOT / 'build/iee-effects97-cap4g-nearest-20261014-v1'
CANDIDATE = OUT / 'candidate'
BEFORE = OUT / 'installed-before'
PRESERVED = (
    'InfinityEngine-Enhancer.ini', 'override/fpDraw.glsl',
    'override/fpSprite.glsl', 'override/fpSELECT.glsl',
    'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
)
sys.path[:0] = [str(ROOT / 'pipeline/scripts'),
               str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools')]
from workspace_paths import get_path
from compose_effect_runtime_packs import validate_pack, compose, write_pack, sha256_file
import install_renderer_candidate as installer
import effect_workflow as workflow
import effect_authority as authority


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def relative(path):
    return path.relative_to(ROOT).as_posix()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(workflow.json_bytes(data))


def preserved_hashes(game):
    return {name: sha256_file(game / name) for name in PRESERVED}


def check_pack(pack, old, assets):
    """Bind every installed resource and backing to its exact checked input."""
    assert pack.resource_count == 97 and old.resource_count == 64
    expected_resources = {r['resref']: r for r in old.resources}
    expected_frames = {f['asset']: f['sha256'] for f in old.frames}
    names = []
    for asset in assets:
        unit = validate_pack(ROOT / asset['pack'])
        check = load(BATCH / 'checks' / (asset['resref'] + '.json'))
        assert check['passed'] and not check['unexpected_duplicates']
        assert unit.manifest_sha256 == check['checked_inputs']['pack_manifest_sha256']
        assert unit.manifest['registry_sha256'] == check['registry_sha256']
        assert unit.resource_count == 1
        resource = unit.resources[0]
        name = resource['resref']
        assert name == asset['resref'] and name not in expected_resources
        assert resource['source']['spatial_run'] == asset['spatial_run']
        assert resource['source']['interpolation_run'] == asset['treatment_run']
        assert resource['timeline']['target_fps'] == [30, 1]
        expected_resources[name] = resource
        expected_frames.update({f['asset']: f['sha256'] for f in unit.frames})
        names.append(name)
    assert len(set(names)) == 33
    assert {r['resref']: r for r in pack.resources} == expected_resources
    assert {f['asset']: f['sha256'] for f in pack.frames} == expected_frames
    assert sum(f['bytes'] for f in pack.frames) == 3428013696
    assert sum(f['bytes'] for f in pack.frames) < 4096 * 1024 * 1024
    return names


def compose_candidate():
    assert not (OUT / 'installation-result.json').exists(), 'Use a new installation version'
    verification = load(BATCH / 'verification.json')
    assert verification['checked'] == verification['passed'] == 33 and not verification['failures']
    game = get_path('bg2ee_game_root', required=True)
    OUT.mkdir(parents=True, exist_ok=True)
    BEFORE.mkdir(exist_ok=True)
    snapshot = OUT / 'before.json'
    current = {'preserved_sha256': preserved_hashes(game),
               'dll_sha256': sha256_file(game / 'InfinityEngine-Enhancer.dll'),
               'manifest_sha256': sha256_file(game / 'iee-assets/effects/manifest.json')}
    if snapshot.exists():
        assert load(snapshot) == current, 'Active installation changed; use a new version'
    else:
        save(snapshot, current)
    for name in ('InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini'):
        target = BEFORE / name
        if not target.exists():
            shutil.copy2(game / name, target)
        assert sha256_file(target) == sha256_file(game / name)
    old_root = BEFORE / 'effects'
    if not old_root.exists():
        shutil.copytree(game / 'iee-assets/effects', old_root)
    old = validate_pack(old_root)
    assert old.manifest_sha256 == current['manifest_sha256']
    assets = load(BATCH / 'batch.json')['assets']
    packs = [old, *(validate_pack(ROOT / a['pack']) for a in assets)]
    effect_root = CANDIDATE / 'iee-assets/effects'
    if not (effect_root / 'manifest.json').exists():
        registry, manifest, copies = compose(packs)
        write_pack(effect_root, registry, manifest, copies)
    candidate = validate_pack(effect_root)
    check_pack(candidate, old, assets)
    print(f'Composed {candidate.resource_count} effects, {len(candidate.frames)} backings, '
          '3428013696 raw bytes; all 64 previous effects preserved', flush=True)


def prepare():
    assert not (OUT / 'installation-result.json').exists()
    before = load(OUT / 'before.json')
    game = get_path('bg2ee_game_root', required=True)
    assert preserved_hashes(game) == before['preserved_sha256']
    assert sha256_file(game / 'InfinityEngine-Enhancer.dll') == before['dll_sha256']
    assert sha256_file(game / 'iee-assets/effects/manifest.json') == before['manifest_sha256']
    pack = validate_pack(CANDIDATE / 'iee-assets/effects')
    names = check_pack(pack, validate_pack(BEFORE / 'effects'), load(BATCH / 'batch.json')['assets'])
    header = 'generated/iee/water_route2_registry.generated.h'
    assert sha256_file(BUILD / header) == sha256_file(
        ROOT / 'build/iee-effects-nearest-20261013-v1' / header)
    shutil.copy2(BUILD / 'Release/InfinityEngine-Enhancer.dll', CANDIDATE / 'InfinityEngine-Enhancer.dll')
    shutil.copy2(BEFORE / 'InfinityEngine-Enhancer.ini', CANDIDATE / 'InfinityEngine-Enhancer.ini')
    with (OUT / 'native-runtime-pack-check.log').open('w', encoding='utf-8') as log:
        subprocess.run([str(BUILD / 'Release/iee_effect_animation_x4_registry_tests.exe'),
                        str(pack.root)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    plan = {'schema': 'bg2-effects-install-plan-v1', 'resrefs': names,
            'resource_count': pack.resource_count, 'frame_count': len(pack.frames),
            'raw_bytes': 3428013696, 'runtime_raw_limit_bytes': 4294967296,
            'effect_filter': 'NEAREST', 'target_fps': [30, 1], 'scale': 4,
            'gpu_texture_capacity': 64, 'character_profile': 'NearestRGB-SilhouetteAlphaAA',
            'manifest_sha256': pack.manifest_sha256,
            'registry_sha256': pack.manifest['registry_sha256'],
            'dll_sha256': sha256_file(CANDIDATE / 'InfinityEngine-Enhancer.dll'),
            'preserved_sha256': before['preserved_sha256'],
            'water_registry_header_sha256': sha256_file(BUILD / header),
            'native_runtime_pack_loaded': True, 'previous_effects_preserved': 64,
            'candidate': relative(CANDIDATE), 'build': relative(BUILD)}
    installer.install_candidate(CANDIDATE, game_root=game, backup_root=OUT / 'backups', verify_only=True)
    save(OUT / 'install-plan.json', plan)
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)


def install():
    assert not (OUT / 'installation-result.json').exists(), 'Installation already recorded'
    game = get_path('bg2ee_game_root', required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    before = load(OUT / 'before.json')
    plan = load(OUT / 'install-plan.json')
    assert preserved_hashes(game) == before['preserved_sha256']
    assert sha256_file(game / 'InfinityEngine-Enhancer.dll') == before['dll_sha256']
    assert validate_pack(game / 'iee-assets/effects').manifest_sha256 == before['manifest_sha256']
    assert sha256_file(CANDIDATE / 'InfinityEngine-Enhancer.dll') == plan['dll_sha256']
    assert validate_pack(CANDIDATE / 'iee-assets/effects').manifest_sha256 == plan['manifest_sha256']
    result = installer.install_candidate(CANDIDATE, game_root=game, backup_root=OUT / 'backups')
    assert result.status == 'installed' and result.receipt_path
    installer.verify_transaction(result.receipt_path, game_root=game)
    installed = validate_pack(game / 'iee-assets/effects')
    assert installed.manifest_sha256 == plan['manifest_sha256']
    check_pack(installed, validate_pack(BEFORE / 'effects'), load(BATCH / 'batch.json')['assets'])
    assert sha256_file(game / 'InfinityEngine-Enhancer.dll') == plan['dll_sha256']
    assert preserved_hashes(game) == before['preserved_sha256']
    receipt = relative(result.receipt_path)
    with authority.guard(ROOT, write=True):
        rows = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
        save(OUT / 'processing-before.json', rows)
        expected = json.loads(json.dumps(rows))
        count = 0
        for row in expected:
            if row['asset_key'].rsplit(':', 1)[-1] in plan['resrefs']:
                row['installation_state'] = 'installed'
                row['installation_receipt'] = receipt
                count += 1
        assert count == 33
        authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(expected)})
        assert workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS) == expected
    final = {**plan, 'schema': 'bg2-effects-installation-result-v1', 'status': 'installed-verified',
             'receipt': receipt, 'new_effects_installed': 33, 'model': 'seedvr2_7b_int8_convrot.safetensors',
             'character_files_byte_identical': True, 'other_processing_rows_unchanged': True,
             'qa_and_selections_unchanged': True, 'release_mutation': False,
             'visual_qa': 'pending-user-ingame'}
    save(OUT / 'installation-result.json', final)
    save(BATCH / 'installation.json', final)
    clua = load(BATCH / 'clua.json')
    assert [item['resref'] for item in clua] == plan['resrefs']
    commands = ['# Lot33 installé — SeedVR2 7B x4 / NEAREST / 30 FPS', '',
                'Démarrer avec InfinityLoader. Ctrl+Espace ; une commande puis fermer la console et reprendre le jeu.',
                'Personnages : NearestRGB-SilhouetteAlphaAA conservé. QA ingame en attente.', '']
    for item in clua:
        commands.extend([f"## {item['resref']} → {item['vvc']}", '',
                         '```lua', item['command'], '```', ''])
    (OUT / 'CLUA.md').write_text('\n'.join(commands), encoding='utf-8')
    print(json.dumps(final, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['compose', 'prepare', 'install'])
    action = parser.parse_args().action
    {'compose': compose_candidate, 'prepare': prepare, 'install': install}[action]()
