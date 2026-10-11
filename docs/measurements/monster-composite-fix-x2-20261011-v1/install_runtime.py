"""Install the tested DLL transactionally; preserve the current INI and assets."""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from workspace_paths import get_path
import install_renderer_candidate as renderer

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert not (HERE / 'installation.json').exists(), 'installation already recorded'
runtime = json.loads((HERE / 'runtime.json').read_text(encoding='utf-8'))
assert runtime['native_tests_passed'] and runtime['unrelated_source_files_identical']
game = get_path('bg2ee_game_root', required=True)
candidate = (ROOT / runtime['dll']['path']).parent
assert sha(game / 'InfinityEngine-Enhancer.dll') == runtime['baseline_dll']['sha256'], 'active renderer changed'
assert sha(game / 'InfinityEngine-Enhancer.ini') == runtime['ini']['sha256'], 'active INI changed'
assert sha(candidate / 'InfinityEngine-Enhancer.dll') == runtime['dll']['sha256']
catalog = game / 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
catalog_before = sha(catalog)
result = renderer.install_candidate(candidate, game_root=game)
try:
    assert sha(game / 'InfinityEngine-Enhancer.dll') == runtime['dll']['sha256']
    assert sha(game / 'InfinityEngine-Enhancer.ini') == runtime['ini']['sha256']
    assert sha(catalog) == catalog_before
except Exception:
    renderer.restore_from_receipt(result.receipt_path, game_root=game)
    raise
report = dict(schema='bg2-monster-composite-runtime-install-v1', status='installed-pending-ingame-QA',
    game_root='config://bg2ee_game_root', runtime_reference=(HERE/'runtime.json').relative_to(ROOT).as_posix(),
    renderer_receipt=result.receipt_path.relative_to(ROOT).as_posix(),
    parent_dll_sha256=runtime['baseline_dll']['sha256'], dll_sha256=runtime['dll']['sha256'],
    ini_preserved=True, catalog_preserved=True, changed_files=['InfinityEngine-Enhancer.dll'],
    capability_scope='all registered Monster owner3; composite only when native extra layers active',
    ingame_QA=False, release=False)
(HERE / 'installation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report), flush=True)
