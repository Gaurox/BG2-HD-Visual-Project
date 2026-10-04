"""Runtime-only patch: capture baseline, verify native build, record installation."""
import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUN = Path(__file__).resolve().parent
OLD = ROOT / 'docs/measurements/q3m-ankheg-sdf-ingame-x2-20261004-v1'
BUILD = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/build-q3m-sdf-stable-20261004-v1'
SOURCE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    assert not path.exists(), f'Immutable run file already exists: {path}'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def identity(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def json_result(path):
    return json.loads([line for line in path.read_text(encoding='utf-8-sig').splitlines()
                       if line.startswith('{')][-1])


def native(name, executable, args=(), cwd=ROOT):
    log = RUN / f'{name}.log'
    assert not log.exists(), f'Already tested: {name}'
    with log.open('wb') as out:
        process = subprocess.run([str(executable), *map(str, args)], cwd=cwd,
                                 stdout=out, stderr=subprocess.STDOUT, check=True)
    return dict(exit_code=process.returncode, log=identity(log))


mode = sys.argv[1]
if mode == 'baseline':
    old_runtime = read(OLD / 'runtime.json')
    old_baseline = read(OLD / 'baseline.json')
    old_generation = read(OLD / 'current-generation.json')
    game = Path(read(ROOT / 'config/workspace-paths.local.json')['paths']['bg2ee_game_root'])
    pack = read(ROOT / old_generation['generation_dir'] / 'pack.json')
    assets = {item['relative_path']: item['sha256'] for item in old_baseline['unchanged_assets']}
    assets.update({item['target']: item['sha256'] for item in old_runtime['shaders']})
    assets.update({item['registry']: item['sha256'] for item in pack['new_shards']})
    assets[old_baseline['catalog_relative']] = old_generation['catalog']['sha256']
    assets['InfinityEngine-Enhancer.ini'] = old_baseline['ini_sha256']
    assets['BaldurReal.exe'] = old_baseline['executable_sha256']
    for relative, expected in assets.items():
        assert sha(game / relative) == expected.lower(), relative
    assert sha(game / 'InfinityEngine-Enhancer.dll') == old_runtime['dll']['sha256']
    write(RUN / 'baseline.json', dict(
        game_root='config://bg2ee_game_root', dll_sha256=old_runtime['dll']['sha256'],
        unchanged_assets=[dict(relative_path=relative, sha256=expected.lower())
                          for relative, expected in sorted(assets.items())],
        parent_runtime=identity(OLD / 'runtime.json'),
        parent_installation=identity(OLD / 'installation-verification.json')))
    probe = (ROOT / 'docs/measurements/q3m-ankheg-sdf-stability-analysis-20261004-v1/work/proposed_lookup_probe.cpp').read_text()
    probe = probe.replace('Explicitly request existing Character wait: owner=9 still disallows it.',
                          'Wait for authenticated owner-9 metadata before the first HD draw.')
    (RUN / 'cold_lookup_probe.cpp').write_text(probe, encoding='utf-8')
    build_probe = (ROOT / 'docs/measurements/q3m-ankheg-sdf-stability-analysis-20261004-v1/build_probe.cmd').read_text()
    build_probe = build_probe.replace('build-q3m-sdf-20261004-v1', BUILD.name)
    build_probe = build_probe.replace('q3m-ankheg-sdf-stability-analysis-20261004-v1', RUN.name)
    (RUN / 'build_probe.cmd').write_text(build_probe, encoding='utf-8')
    print(f'Baseline: {len(assets)} preserved files, old DLL confirmed.')
elif mode == 'native':
    # The cold probe links the actual new build's resolver objects, not a patched copy.
    probe_build = native('probe-build', 'cmd.exe', ('/d', '/c', RUN / 'build_probe.cmd'))
    isolated = ROOT / 'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated'
    core = native('core', BUILD / 'Release/iee_tests.exe', cwd=SOURCE)
    cold = native('cold-lookup', RUN / 'cold_lookup_probe.exe', (isolated,))
    cold_result = json_result(RUN / 'cold-lookup.log')
    assert cold_result['cold_misses'] == 0 and cold_result['warm_hits'] == 12
    latencies = [float(x) for x in re.findall(r'ready_ms=([\d.]+)', (RUN / 'cold-lookup.log').read_text())]
    cold_result.update(maximum_wait_ms=max(latencies), total_wait_ms=sum(latencies))
    sdf = native('sdf', BUILD / 'Release/iee_palette_partner_tests.exe',
                 (isolated, isolated / 'witnesses.oracle', isolated / 'sdf-composite.oracle'))
    sdf_result = json_result(RUN / 'sdf.log')
    assert sdf_result['passed'] and sdf_result['resources'] == 12 and sdf_result['frames'] == 516
    assert 'SDF composite golden cases passed: 48' in (RUN / 'sdf.log').read_text()
    dll = identity(BUILD / 'Release/InfinityEngine-Enhancer.dll')
    sources = [identity(SOURCE / f'src/iee/{name}')
               for name in ('creature_sprite_x2.h', 'creature_sprite_x2.cpp', 'hooks.cpp')]
    # Render contract remains covered by the original GPU proof and unchanged shaders.
    old_runtime = read(OLD / 'runtime.json')
    for shader in old_runtime['shaders']:
        assert sha(ROOT / shader['path']) == shader['sha256']
    write(RUN / 'verification.json', dict(
        schema='bg2-ankheg-sdf-metadata-wait-native-verification-v1',
        passed=True, core=core, cold_lookup=dict(**cold, **cold_result),
        SDF=dict(**sdf, **sdf_result, composite_cases=48), probe_build=probe_build,
        probe_source=identity(RUN / 'cold_lookup_probe.cpp'), dll=dll, source_provenance=sources,
        original_SDF_verification=identity(OLD / 'verification.json'),
        original_GPU_verification=identity(OLD / 'gpu-verification.json'),
        shaders_byte_identical=True, ingame_QA=False, release=False))
    wait = dict(catalog_versions=[2], owner=9, animation_id='0x3000',
                mode='WaitForAnkhegMetadata', maximum_wait_ms=5000,
                timeout_policy='component-quarantine-and-native-fallback', payloads='lazy',
                other_monster_families='NonBlocking', Character='existing owner-1 wait retained')
    write(RUN / 'runtime.json', dict(
        schema='bg2-upscale-runtime-capabilities-delta-v1', status='development-candidate',
        runtime_id='iee-q3m-v9-ankheg-sdf-stable-x2-20261004-v1',
        inherited_runtime=identity(OLD / 'runtime.json'),
        capability_delta=dict(ankheg_cold_resolution=wait), dll=dll,
        source_provenance=sources, verification=identity(RUN / 'verification.json'),
        shaders=old_runtime['shaders'], assets='unchanged; no regeneration',
        ingame_QA=False, release=False))
    generation = copy.deepcopy(read(OLD / 'current-generation.json'))
    generation.update(schema='bg2-ankheg-Q3m-SDF-runtime-patch-current-v1',
                      role='runtime-patch-over-unchanged-production',
                      runtime=identity(RUN / 'runtime.json'), dll=dll,
                      host_verification=identity(RUN / 'verification.json'),
                      parent_generation=identity(OLD / 'current-generation.json'),
                      metadata_wait=wait, state='host-verified-ready-to-install')
    write(RUN / 'current-generation.json', generation)
    print(json.dumps(dict(cold_lookup=cold_result, SDF=sdf_result, core_passed=True, dll=dll)))
elif mode == 'track':
    installed = read(RUN / 'installation-verification.json')
    assert installed['status'] == 'installed-pending-ingame-qa'
    tracking_path = ROOT / 'sprite/index/q3m-work-tracking.json'
    tracking = read(tracking_path)
    old_trial = next(x for x in tracking['current_contour_trials'] if x['family'] == 'monster_ankheg')
    assert old_trial['runtime_reference'] == (OLD / 'runtime.json').relative_to(ROOT).as_posix()
    history = copy.deepcopy(old_trial)
    history.update(state='superseded-runtime-by-metadata-wait-patch', installation_state='superseded',
                   user_feedback='resultat magnifique; instability with temporary vanilla x1 frames',
                   stability_analysis='docs/measurements/q3m-ankheg-sdf-stability-analysis-20261004-v1/README.md')
    tracking['historical_contour_trials'].append(history)
    trial = copy.deepcopy(old_trial)
    rel = RUN.relative_to(ROOT).as_posix()
    trial.update(reference=f'{rel}/current-generation.json', runtime_reference=f'{rel}/runtime.json',
                 installation_reference=f'{rel}/ingame-installation/active-test.json',
                 installation_snapshot=f'{rel}/installation-verification.json',
                 restore_script=f'{rel}/restore.ps1',
                 state='SDF-trial-metadata-wait-installed-ingame-QA-pending',
                 metadata_wait=read(RUN / 'current-generation.json')['metadata_wait'])
    tracking['current_contour_trials'] = [trial if x['family'] == 'monster_ankheg' else x
                                         for x in tracking['current_contour_trials']]
    family = next(x for x in tracking['families'] if x['engine_section'] == 'monster_ankheg')
    family['current_contour_trial'] = copy.deepcopy(trial)
    tracking['engine_integration']['installed_candidate_reference'] = f'{rel}/installation-verification.json'
    tracking_path.write_text(json.dumps(tracking, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    csv_path = ROOT / 'sprite/index/q3m-work-items.csv'
    csv = csv_path.read_text(encoding='utf-8')
    assert csv.count('v7-colours-with-v9-sdf-trial-installed-QA-pending') == 1
    csv = csv.replace('v7-colours-with-v9-sdf-trial-installed-QA-pending',
                      'v7-colours-with-v9-sdf-stable-runtime-installed-QA-pending')
    csv_path.write_text(csv, encoding='utf-8', newline='')
    print('Tracking: new runtime/installation only; production and QA decisions retained.')
else:
    raise ValueError(mode)
