"""Install only DLL + identical INI; keep all effects, characters and map assets."""
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'engine/InfinityEngine-Enhancer/installations/renderer-startup-barrier-20261014-v1'
BUILD = ROOT / 'build/iee-map-first-frame-refresh-20261014-v1'
sys.path[:0] = [str(ROOT / 'pipeline/scripts'),
               str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as installer
from compose_effect_runtime_packs import validate_pack
from workspace_paths import get_path


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    game = get_path('bg2ee_game_root', required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    baseline = load(ROOT / 'engine/InfinityEngine-Enhancer/installations/hooks-startup-repair-20261014-v1/corrected-v1/installation.json')['preserved_sha256']
    preserved = {name: installer.sha256_file(game / name) for name in baseline}
    assert preserved == baseline, 'Effects or character profile changed since diagnosis'
    pack = validate_pack(game / 'iee-assets/effects')
    batch = load(ROOT / 'effects/batches/lot33-seedvr7b-apollo30-20261014-v1/batch.json')
    assert pack.resource_count == 97
    resources = {r['resref']: r for r in pack.resources}
    for asset in batch['assets']:
        resource = resources[asset['resref']]
        assert resource['source']['spatial_run'] == asset['spatial_run']
        assert resource['source']['interpolation_run'] == asset['treatment_run']
        assert resource['timeline']['target_fps'] == [30, 1]
    header = 'generated/iee/water_route2_registry.generated.h'
    assert installer.sha256_file(BUILD / header) == installer.sha256_file(
        ROOT / 'build/iee-effects-nearest-20261013-v1' / header)
    OUT.mkdir(parents=True, exist_ok=False)
    candidate = OUT / 'candidate'
    candidate.mkdir()
    shutil.copy2(BUILD / 'Release/InfinityEngine-Enhancer.dll', candidate / 'InfinityEngine-Enhancer.dll')
    shutil.copy2(game / 'InfinityEngine-Enhancer.ini', candidate / 'InfinityEngine-Enhancer.ini')
    save(OUT / 'before.json', {'preserved_sha256': preserved,
                             'dll_sha256': installer.sha256_file(game / 'InfinityEngine-Enhancer.dll')})
    result = installer.install_candidate(candidate, game_root=game, backup_root=OUT / 'backups')
    installer.verify_transaction(result.receipt_path, game_root=game)
    assert {name: installer.sha256_file(game / name) for name in preserved} == preserved
    assert set(result.files) == {'InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini'}
    save(OUT / 'installation.json', {
        'schema': 'bg2-renderer-host-startup-barrier-install-v1',
        'status': 'installed-awaiting-user-controlled-no-zoom-check',
        'receipt': result.receipt_path.relative_to(ROOT).as_posix(),
        'dll_sha256': installer.sha256_file(game / 'InfinityEngine-Enhancer.dll'),
        'preserved_sha256': preserved, 'effect_resources': 97,
        'lot33_model': 'seedvr2_7b_int8_convrot.safetensors',
        'lot33_scale': 4, 'lot33_target_fps': [30, 1], 'effect_filter': 'NEAREST',
        'character_profile': 'NearestRGB-SilhouetteAlphaAA',
        'native_raw_limit_bytes': 4294967296, 'gpu_effect_cache_slots': 64,
        'map_assets_changed': False, 'release_changed': False,
    })
    print('Corrected DLL installed; INI, shaders, character catalog and all 97 effects preserved. '
          'Awaiting user-controlled runtime verification.', flush=True)


if __name__ == '__main__':
    main()
