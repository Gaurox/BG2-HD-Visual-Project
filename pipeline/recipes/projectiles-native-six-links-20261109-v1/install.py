"""Install the six secondary registrations transactionally; reuse all image bytes."""
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

OUT = ROOT / 'engine/InfinityEngine-Enhancer/installations/projectiles-native-six-links-20261109-v1'
PROOF = ROOT / 'projectiles/analysis/native-six-links-20261109-v1'
SOURCE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
BUILD = ROOT / 'build/iee-projectile-secondary-links-20261028-v1'
GAME = tx.get_path('bg2ee_game_root', required=True)
NAMES = ['SKYBOLT', 'SPBOOM', 'SPFDEATH', 'SPGENHLA', 'SPGFLSH1', 'SPWRDFLD']


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
               'src/iee/hooks.cpp', 'tests/effect_surface_owner_tests.cpp']
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
    print('Prepared DLL + temporary trace only; 743 resources /72563 backings preserved.')


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
    save(OUT / 'installation.json', dict(status='installed-awaiting-six-HD-runtime-observations',
        installed_utc=tx.utc_now(), receipt=rel(result.receipt_path),
        dll=plan['candidate_dll'], previous_dll=before['runtime_files']['InfinityEngine-Enhancer.dll'],
        ini=plan['candidate_ini'], temporary_trace=True, secondary_resources_added=NAMES,
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
    assert snap(GAME / 'InfinityEngine-Enhancer.dll') == plan['candidate_dll']
    tracking_path = ROOT / 'projectiles/index/work-tracking.json'
    tracking = load(tracking_path)
    assert tracking == before['tracking'], 'Tracking changed during installation; merge before publishing'
    targets = [('projectiles', 'SKYBOLT', 'SKYBOLT'), ('projectiles', 'ICESTORM', 'SPBOOM'),
               ('engine_projectiles', '207', 'SPFDEATH'), ('engine_projectiles', '254', 'SPGENHLA'),
               ('projectiles', 'ENTANG2', 'SPGFLSH1'), ('projectiles', 'PFIELD', 'SPWRDFLD')]
    ev = [rel(OUT / 'installation.json'), rel(PROOF / 'qualification.json')]
    for namespace, name, resource in targets:
        node = tracking[namespace].setdefault(name, {})
        node['integration'] = dict(state='installed-component-route-awaiting-HD-observation',
            evidence=ev, resources=[resource], scope='Actual specialized native FX cell; component only, not full projectile closure.',
            HD_review_state='pending-user-review', previous_visual_QA_retained=True)
        node['installation'] = dict(state='installed', evidence=[installed['receipt']],
            resources=[resource], scope='Secondary-cell registration through DLL; existing image pack untouched.')
    for namespace in ('projectiles', 'engine_projectiles'):
        for name, value in before['tracking'].get(namespace, {}).items():
            assert tracking[namespace][name].get('qa') == value.get('qa')
    tracking.setdefault('runtime_route_installations', {})['native-six-links-20261109-v1'] = dict(
        state='installed-awaiting-HD-observation', resources=NAMES, evidence=ev,
        receipt=installed['receipt'], dll=plan['candidate_dll'], trace_enabled=True,
        unchanged_image_QA=True, open_other_resources=['HLYMITE', 'SHAIR', 'SHEARTH', 'SPSCORIC'])
    validate_tracking(tracking, {r['resref'] for r in read_csv(ROOT / 'projectiles/index/resources.csv')})
    tracking_path.write_text(json.dumps(tracking, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    logs = [dict(path=p.relative_to(GAME).as_posix(), bytes=p.stat().st_size,
                 mtime_ns=p.stat().st_mtime_ns) for p in GAME.glob('*.log')]
    save(OUT / 'log-baseline.json', dict(captured_utc=tx.utc_now(), game_root='config://bg2ee_game_root', logs=logs))
    print('INSTALLED six registrations; transactional DLL/INI backup recorded; HD QA pending.')


def disable_trace():
    tx.ensure_game_stopped(tx.running_game_processes)
    path = GAME / 'InfinityEngine-Enhancer.ini'
    raw = path.read_bytes()
    key = b'EnableEffectStreamingTrace = true'
    assert raw.count(key) == 1
    changed = raw.replace(key, b'EnableEffectStreamingTrace = false')
    tmp = OUT / 'trace-disabled.ini'
    tmp.write_bytes(changed)
    tx.atomic_copy(tmp, path, tx.FileSnapshot(len(changed), tx.sha256_file(tmp)))
    print('Disabled only temporary trace; installed DLL and other settings retained.')


if __name__ == '__main__':
    {'verify': verify, 'prepare': prepare, 'install': install, 'finish': finish,
     'disable-trace': disable_trace}[sys.argv[1]]()
