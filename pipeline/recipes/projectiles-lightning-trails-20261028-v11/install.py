"""Two existing LIGHTCHA trails enter the FX/mask route; temporary draw trace."""
from pathlib import Path
from dataclasses import asdict
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'pipeline/scripts'), str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
GAME = tx.get_path('bg2ee_game_root', required=True)
OUT = ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-lightning-trails-20261028-v11'
BUILD = ROOT/'build/iee-projectile-secondary-links-20261028-v1'
PROOF = ROOT/'projectiles/analysis/eclairs-v11-preparation-20261028-v1'
PRESERVE = ['BaldurReal.exe', 'iee-assets/effects/manifest.json',
            'iee-assets/effects/EffectAnimations-X4.registry',
            'override/SPCHLGT1.bam', 'override/SPCHLGT2.bam', 'override/SPCHLGT3.bam',
            'override/XPGREEN.spl']
SOURCE = ROOT/'engine/InfinityEngine-Enhancer/source-patchee'


def js(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def snap(p):
    return asdict(tx.snapshot_file(p))


def save(p, data):
    with p.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def prepare():
    assert not OUT.exists()
    assert '100% tests passed, 0 tests failed out of 3' in (BUILD/'lightning-v11-tests.log').read_text(encoding='utf-8-sig')
    assert 'contracts checked: 824' in (PROOF/'native-contracts.log').read_text(encoding='utf-8-sig')
    old = js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-wall-fog-alpha-20261028-v10/installation.json')
    assert snap(GAME/'InfinityEngine-Enhancer.dll') == old['dll']
    assert snap(GAME/'iee-assets/effects/manifest.json') == old['manifest']
    ini = (GAME/'InfinityEngine-Enhancer.ini').read_bytes()
    key = b'EnableEffectStreamingTrace = false'
    assert ini.count(key) == 1
    traced = ini.replace(key, b'EnableEffectStreamingTrace = true')
    OUT.mkdir(parents=True)
    candidate = OUT/'candidate'
    candidate.mkdir()
    shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll', candidate/'InfinityEngine-Enhancer.dll')
    (candidate/'InfinityEngine-Enhancer.ini').write_bytes(traced)
    shutil.copy2(BUILD/'lightning-v11-tests.log', OUT/'tests.log')
    save(OUT/'before.json', dict(
        files={n: snap(GAME/n) for n in PRESERVE+['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']},
        override_PROs={p.name: snap(p) for p in (GAME/'override').glob('*.pro')},
        source_sha256={str(p.relative_to(ROOT)): tx.sha256_file(p) for p in (
            SOURCE/'src/iee/core/effect_secondary_scope.h',
            SOURCE/'tests/effect_surface_owner_tests.cpp', SOURCE/'src/iee/hooks.cpp')},
        native_contracts=824, proof_sha256=tx.sha256_file(PROOF/'contracts.json'),
        ini_only_change='EnableEffectStreamingTrace=false -> true',
        original_ini_hex=ini.hex()))
    print('Prepared V11: SPCHLGT1/3 FX scope + temporary streaming draw trace; zero image writes')


def install():
    assert not (OUT/'installation.json').exists()
    before = js(OUT/'before.json')
    tx.ensure_game_stopped(tx.running_game_processes)
    for n, old in before['files'].items():
        assert snap(GAME/n) == old, n
    for n, old in before['override_PROs'].items():
        assert snap(GAME/'override'/n) == old, n
    for n, digest in before['source_sha256'].items():
        assert tx.sha256_file(ROOT/n) == digest, n
    assert tx.sha256_file(PROOF/'contracts.json') == before['proof_sha256']
    result = tx.install_candidate(OUT/'candidate', game_root=GAME, backup_root=OUT/'backups')
    tx.verify_transaction(result.receipt_path, game_root=GAME)
    for n, old in before['files'].items():
        if n not in ('InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini'):
            assert snap(GAME/n) == old, n
    for n, old in before['override_PROs'].items():
        assert snap(GAME/'override'/n) == old, n
    original = bytes.fromhex(before['original_ini_hex'])
    assert (GAME/'InfinityEngine-Enhancer.ini').read_bytes() == original.replace(
        b'EnableEffectStreamingTrace = false', b'EnableEffectStreamingTrace = true')
    save(OUT/'installation.json', dict(
        status='installed-awaiting-lightning-and-flight-trace', utc=tx.utc_now(),
        receipt=str(result.receipt_path.relative_to(ROOT)), dll=snap(GAME/'InfinityEngine-Enhancer.dll'),
        previous_dll=before['files']['InfinityEngine-Enhancer.dll'],
        ini=snap(GAME/'InfinityEngine-Enhancer.ini'), temporary_trace=True,
        FX_scope_added=['SPCHLGT1', 'SPCHLGT3'], resources=538, frames=62500,
        native_cycles_checked=27, native_contracts=824, tests='3/3 passed',
        image_files_changed=False, PROs_changed=False, metadata_changed=False,
        movement_changed=False, release_changed=False, ingame_validated=False,
        cleanup='After trace capture and game/loader stop, disable ONLY EnableEffectStreamingTrace; preserve V11 DLL'))
    print('Installed V11; existing LIGHTCHA trails linked, temporary trace on, images/PROs unchanged')


if __name__ == '__main__':
    {'prepare': prepare, 'install': install}[sys.argv[1]]()
