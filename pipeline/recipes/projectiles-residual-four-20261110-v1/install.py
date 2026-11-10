"""Install the four secondary registrations transactionally; reuse all image bytes."""
from pathlib import Path
from dataclasses import asdict
import copy
import json
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'pipeline/scripts'),
               str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
from projectile_tracking import validate_tracking, read_csv

OUT = ROOT / 'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1'
PROOF = ROOT / 'projectiles/analysis/residual-four-20261110-v1'
SOURCE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
BUILD = ROOT / 'build/iee-projectile-secondary-links-20261028-v1'
GAME = tx.get_path('bg2ee_game_root', required=True)
NAMES = ['SHWATER', 'FLMSTRK', 'SPDIMDR1', 'SPDIMDR2', 'SPBOOM']


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def snap(p):
    return asdict(tx.snapshot_file(p))


def save(p, data):
    assert not p.exists(), 'Use a new completed version'
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rel(p):
    return p.relative_to(ROOT).as_posix()


def verify():
    assert not (PROOF / 'engine-tests.log').exists()
    pattern = '^(iee_effect_surface_owner_tests|iee_effect_occlusion_tests|iee_tests|iee_effect_animation_x4_registry_tests|iee_effect_texture_cache_tests)$'
    with (PROOF / 'engine-tests.log').open('w', encoding='utf-8') as f:
        subprocess.run(['ctest', '--test-dir', str(BUILD), '-C', 'Release', '-R', pattern,
                        '--output-on-failure'], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                       check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert '100% tests passed, 0 tests failed out of 5' in (PROOF / 'engine-tests.log').read_text(encoding='utf-8')
    probe('before-install-native-loader.log')
    print('Five engine suites PASS; native loader contracts PASS.')


def probe(log):
    assert not (PROOF / log).exists()
    with (PROOF / log).open('w', encoding='utf-8') as f:
        subprocess.run([str(BUILD / 'Release/iee_effect_animation_x4_registry_tests.exe'),
                        '--metadata-mib', '64', '--catalogue-only', str(GAME / 'iee-assets/effects'),
                        str(PROOF / 'runtime-contracts.tsv')], cwd=ROOT, stdout=f,
                       stderr=subprocess.STDOUT, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    expected = load(PROOF / 'qualification.json')['contracts']
    assert f'contracts checked: {expected}' in (PROOF / log).read_text(encoding='utf-8')


def prepare():
    assert not OUT.exists()
    qualified = load(PROOF / 'qualification.json')
    assert qualified['resources'] == NAMES
    assert tx.sha256_file(GAME / 'iee-assets/effects/manifest.json') == qualified['manifest_sha256']
    assert tx.sha256_file(GAME / 'InfinityEngine-Enhancer.dll') == qualified['installed_dll_sha256']
    assert '100% tests passed, 0 tests failed out of 5' in (PROOF / 'engine-tests.log').read_text(encoding='utf-8')
    preserve = ['BaldurReal.exe', 'iee-assets/effects/manifest.json',
                'iee-assets/effects/EffectAnimations-X4.registry',
                'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
                'override/fpDraw.glsl', 'override/fpSprite.glsl', 'override/fpSELECT.glsl']
    for name in NAMES:
        for ext in ('bam', 'vvc'):
            path = GAME / 'override' / (name + '.' + ext)
            if path.exists():
                preserve.append(path.relative_to(GAME).as_posix())
    sources = ['src/iee/core/effect_secondary_scope.h', 'src/iee/core/effect_texture_alias.h',
               'src/iee/hooks.cpp', 'src/iee/core/effect_indexed_palette.h',
               'src/iee/core/effect_native_projectile_palettes.h',
               'tests/effect_native_projectile_palette_fixtures.h',
               'tests/effect_texture_cache_tests.cpp', 'tests/effect_surface_owner_tests.cpp',
               'src/iee/core/effect_residual_projectile_palettes.h',
               'tests/effect_residual_projectile_palette_fixtures.h']
    ini = (GAME / 'InfinityEngine-Enhancer.ini').read_bytes()
    key = b'EnableEffectStreamingTrace = false'
    assert ini.count(key) == 1
    candidate = OUT / 'candidate'
    candidate.mkdir(parents=True)
    shutil.copy2(BUILD / 'Release/InfinityEngine-Enhancer.dll', candidate / 'InfinityEngine-Enhancer.dll')
    (candidate / 'InfinityEngine-Enhancer.ini').write_bytes(ini.replace(key, b'EnableEffectStreamingTrace = true'))
    save(OUT / 'before.json', dict(files={name: snap(GAME / name) for name in preserve},
        runtime_files={name: snap(GAME / name) for name in ('InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini')},
        override_PROs={p.name: snap(p) for p in (GAME / 'override').glob('*.pro')},
        tracking=load(ROOT / 'projectiles/index/work-tracking.json'),
        source_sha256={name: tx.sha256_file(SOURCE / name) for name in sources},
        proof_manifest=tx.sha256_file(PROOF / 'qualification.json')))
    save(OUT / 'plan.json', dict(resources=NAMES,
        candidate_dll=snap(candidate / 'InfinityEngine-Enhancer.dll'),
        candidate_ini=snap(candidate / 'InfinityEngine-Enhancer.ini'),
        managed_files=['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini'],
        ini_delta='EnableEffectStreamingTrace=false -> true only',
        image_files_changed=0, native_PRO_changes=0, additional_inference=0))
    print('Prepared DLL + temporary trace only; 743 resources /72563 backings preserved; five raster names/four families.')


def preserved(before):
    for name, value in before['files'].items():
        assert snap(GAME / name) == value, name
    for name, value in before['override_PROs'].items():
        assert snap(GAME / 'override' / name) == value, name


def install():
    assert not (OUT / 'installation.json').exists()
    before = load(OUT / 'before.json')
    plan = load(OUT / 'plan.json')
    tx.ensure_game_stopped(tx.running_game_processes)
    preserved(before)
    for name, value in before['runtime_files'].items():
        assert snap(GAME / name) == value
    for name, value in before['source_sha256'].items():
        assert tx.sha256_file(SOURCE / name) == value
    result = tx.install_candidate(OUT / 'candidate', game_root=GAME, backup_root=OUT / 'backups')
    tx.verify_transaction(result.receipt_path, game_root=GAME)
    preserved(before)
    assert snap(GAME / 'InfinityEngine-Enhancer.dll') == plan['candidate_dll']
    assert snap(GAME / 'InfinityEngine-Enhancer.ini') == plan['candidate_ini']
    try:
        probe('installed-native-loader.log')
    except Exception:
        tx.restore_from_receipt(result.receipt_path, game_root=GAME)
        raise
    save(OUT / 'installation.json', dict(status='installed-awaiting-two-representative-colours',
        installed_utc=tx.utc_now(), receipt=rel(result.receipt_path),
        dll=plan['candidate_dll'], previous_dll=before['runtime_files']['InfinityEngine-Enhancer.dll'],
        ini=plan['candidate_ini'], temporary_trace=True, secondary_resources_added=[n for n in NAMES if n != 'SPBOOM'],
        palette_resources_updated=['SHWATER','SPBOOM'],
        native_contracts=load(PROOF / 'qualification.json')['contracts'], engine_tests='5/5 passed',
        resources=743, backings=72563, image_files_changed=False, PROs_changed=False,
        metadata_changed=False, native_geometry_changed=False, release_changed=False,
        inference_jobs=0, ingame_validated=False, game_launched=False,
        cleanup='After user tests/log analysis and game/loader stop, disable ONLY EnableEffectStreamingTrace; retain DLL.'))
    finish()


def finish():
    before = load(OUT / 'before.json')
    plan = load(OUT / 'plan.json')
    installed = load(OUT / 'installation.json')
    tx.verify_transaction(ROOT / installed['receipt'], game_root=GAME)
    preserved(before)
    tracking_path = ROOT / 'projectiles/index/work-tracking.json'
    tracking = load(tracking_path)
    assert tracking == before['tracking'], 'Tracking changed during installation'
    evidence = [rel(OUT / 'installation.json'), rel(PROOF / 'qualification.json'), rel(PROOF / 'source-palettes.json')]
    ids = [109,120,123,126,129,132,135,138,141,142,143,144,145]
    for ident in ids:
        node = tracking['engine_projectiles'].setdefault(str(ident), {})
        integration = node.setdefault('integration', dict(state='technical-reconciliation-recorded'))
        integration['residual_four_runtime'] = dict(state='qualified-installed-colour-QA-pending' if ident in [120,123,126,129,132,135,138,141,142,143,144] else 'qualified-static-installed-prior-image-QA-retained',
            evidence=evidence, previous_visual_QA_retained=True, live_HD_draw_observed=False,
            scope='Current DLL source/pack/palette/native geometry/cycles qualification, not live draw or global visual approval')
        node['installation'] = dict(state='installed', evidence=[installed['receipt']],
            scope='DLL bridge/palette changes only; existing images and native PROs unchanged.')
    for ns in ('projectiles','engine_projectiles'):
        for name, previous in before['tracking'][ns].items():
            assert tracking[ns][name].get('qa') == previous.get('qa')
            assert tracking[ns][name].get('release') == previous.get('release')
    tracking.setdefault('runtime_route_installations', {})['residual-four-20261110-v1'] = dict(
        state='four-families-qualified-installed-two-colour-checks-pending', resources=NAMES,
        evidence=evidence, receipt=installed['receipt'], dll=plan['candidate_dll'], trace_enabled=True,
        manual_review_scope=['SHWATER6 red via SPPR207','SPBOOM67 gold via SPWM110'],
        automated_other_variants=['SHWATER1..7 native214 used knots each','SPBOOM67/65/69 twelve used knots each',
            'normal/additive upload cache separation','FLMSTRK neutral and SPDIMDR1/2 2->1->2 native resource transitions'],
        new_images=0, neutral_visual_retests_requested=False)
    validate_tracking(tracking, {r['resref'] for r in read_csv(ROOT / 'projectiles/index/resources.csv')})
    tracking_path.write_text(json.dumps(tracking, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(OUT / 'log-baseline.json', dict(captured_utc=tx.utc_now(), game_root='config://bg2ee_game_root',
        logs=[dict(path=p.relative_to(GAME).as_posix(), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns) for p in GAME.glob('*.log')]))
    print('Installed four residual families; two representative colour checks pending, existing QA retained.')


def disable_trace():
    tx.ensure_game_stopped(tx.running_game_processes)
    path = GAME / 'InfinityEngine-Enhancer.ini'
    raw = path.read_bytes()
    key = b'EnableEffectStreamingTrace = true'
    assert raw.count(key) == 1
    changed = raw.replace(key, b'EnableEffectStreamingTrace = false')
    tmp = ROOT / '.tmp/projectiles-residual-four-trace-disabled.ini'
    tmp.write_bytes(changed)
    tx.atomic_copy(tmp, path, tx.FileSnapshot(len(changed), tx.sha256_file(tmp)))
    print('Disabled only temporary trace; installed DLL and other settings retained.')


if __name__ == '__main__':
    {'verify': verify, 'prepare': prepare, 'install': install, 'finish': finish,
     'disable-trace': disable_trace}[sys.argv[1]]()
