"""Compose the 54 checked packs with the active pack; transactional installation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot54-seedvr3b-apollo30-20261013-v1'
INSTALL = ROOT / 'effects/installations/lot54-seedvr3b-apollo30-gauss12-feather12-20261013-v1'
BUILD = ROOT / 'build/iee-effects-lot54-2g-20261013'
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
    batch = load(BATCH / 'batch.json'); verification = load(BATCH / 'verification.json')
    assert verification['checked'] == verification['passed'] == 54 and not verification['failures']
    assert (BATCH / 'preview/index.html').is_file()
    assert len(load(BATCH / 'preview/preview.json')['assets']) == 54
    game = get_path('bg2ee_game_root', required=True)
    INSTALL.mkdir(parents=True, exist_ok=True)
    before = INSTALL / 'installed-before'; before.mkdir(exist_ok=True)
    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']:
        if not (before / name).exists(): shutil.copy2(game / name, before / name)
        assert sha256_file(before / name) == sha256_file(game / name), 'Active renderer changed; prepare a new installation version'
    old_pack = before / 'effects'
    if not old_pack.exists(): shutil.copytree(game / 'iee-assets/effects', old_pack)
    old = validate_pack(old_pack); active = validate_pack(game / 'iee-assets/effects')
    assert old.manifest_sha256 == active.manifest_sha256
    packs = [validate_pack(ROOT / a['pack']) for a in batch['assets']]
    for asset, pack in zip(batch['assets'], packs):
        check = load(BATCH / 'checks' / (asset['resref']+'.json'))
        assert check['passed'] and check['registry_sha256'] == pack.manifest['registry_sha256']
    candidate = INSTALL / 'candidate'; candidate.mkdir(exist_ok=True)
    effect_root = candidate / 'iee-assets/effects'
    if not (effect_root / 'manifest.json').is_file():
        registry, manifest, copies = compose([old, *packs]); write_pack(effect_root, registry, manifest, copies)
    result = validate_pack(effect_root)
    assert result.resource_count == old.resource_count + 54
    old_frames = {f['asset']: f['sha256'] for f in old.frames}
    new_frames = {f['asset']: f['sha256'] for f in result.frames}
    assert all(new_frames.get(n) == digest for n, digest in old_frames.items())
    raw_bytes = sum(f['bytes'] for f in result.frames)
    assert raw_bytes <= 2048 * 1024 * 1024
    shutil.copy2(BUILD / 'Release/InfinityEngine-Enhancer.dll', candidate / 'InfinityEngine-Enhancer.dll')
    shutil.copy2(before / 'InfinityEngine-Enhancer.ini', candidate / 'InfinityEngine-Enhancer.ini')
    with (INSTALL / 'native-runtime-pack-check.log').open('w', encoding='utf-8') as log:
        subprocess.run([str(BUILD / 'Release/iee_effect_animation_x4_registry_tests.exe'), str(effect_root)],
                       cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    plan = {'schema': 'bg2-effects-install-plan-v1', 'resrefs': [a['resref'] for a in batch['assets']],
            'candidate': relative(candidate), 'new_packs': [a['pack'] for a in batch['assets']],
            'existing_pack_snapshot': relative(old_pack), 'registry_version': 2,
            'resource_count': result.resource_count, 'frame_count': result.manifest['frame_count'],
            'raw_bytes': raw_bytes, 'runtime_raw_limit_bytes': 2048*1024*1024,
            'registry_sha256': result.manifest['registry_sha256'],
            'previous_dll_sha256': sha256_file(before / 'InfinityEngine-Enhancer.dll'),
            'dll_sha256': sha256_file(candidate / 'InfinityEngine-Enhancer.dll'),
            'ini_sha256': sha256_file(candidate / 'InfinityEngine-Enhancer.ini'),
            'previous_payloads_preserved': True, 'native_runtime_pack_loaded': True,
            'visual_qa': 'pending-user-ingame', 'preview': relative(BATCH / 'preview/index.html'),
            'clua': relative(BATCH / 'CLUA.md')}
    save(INSTALL / 'install-plan.json', plan)
    installer.install_candidate(candidate, game_root=game, backup_root=INSTALL / 'backups', verify_only=True)
    print(json.dumps(plan, indent=2), flush=True)


def install():
    plan = load(INSTALL / 'install-plan.json'); game = get_path('bg2ee_game_root', required=True)
    candidate = ROOT / plan['candidate']; before = INSTALL / 'installed-before'
    installer.ensure_game_stopped(installer.running_game_processes)
    for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']:
        assert sha256_file(game / name) == sha256_file(before / name), 'Active renderer changed since preparation'
    assert validate_pack(game / 'iee-assets/effects').manifest_sha256 == validate_pack(before / 'effects').manifest_sha256
    result = installer.install_candidate(candidate, game_root=game, backup_root=INSTALL / 'backups')
    assert result.status == 'installed' and result.receipt_path
    installer.verify_transaction(result.receipt_path, game_root=game)
    installed = validate_pack(game / 'iee-assets/effects')
    assert installed.manifest['registry_sha256'] == plan['registry_sha256']
    assert sha256_file(game / 'InfinityEngine-Enhancer.dll') == plan['dll_sha256']
    assert sha256_file(game / 'InfinityEngine-Enhancer.ini') == plan['ini_sha256']
    receipt = relative(result.receipt_path)
    with authority.guard(ROOT, write=True):
        processing = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
        selected = set(plan['resrefs']); updated = 0
        for row in processing:
            if row['asset_key'].rsplit(':', 1)[-1] in selected:
                row['installation_state'] = 'installed'; row['installation_receipt'] = receipt; updated += 1
        assert updated == 54
        authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(processing)})
    final = {'schema': 'bg2-effects-installation-result-v1', 'status': 'installed', 'resrefs': plan['resrefs'],
             'receipt': receipt, 'registry_sha256': plan['registry_sha256'], 'resource_count': plan['resource_count'],
             'new_packs': plan['new_packs'], 'dll_sha256': plan['dll_sha256'], 'ini_unchanged': True,
             'previous_effects_preserved': True, 'raw_bytes': plan['raw_bytes'], 'visual_qa': 'pending-user-ingame'}
    save(INSTALL / 'installation-result.json', final); save(BATCH / 'installation.json', final)
    print(json.dumps(final, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['prepare', 'install'])
    action = parser.parse_args().action
    prepare() if action == 'prepare' else install()
