"""Install V12 DLL/temporary trace and two exclusive QA files, with rollback."""
from pathlib import Path
from dataclasses import asdict
import json
import os
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
GAME=tx.get_path('bg2ee_game_root',required=True)
BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'
OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-mask-capture-20261028-v12'
PROOF=ROOT/'projectiles/analysis/masque-capture-v12-20261028-v1'
QA=['XQTARG.cre','XQSEED.spl']
PRESERVE=['BaldurReal.exe','iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry',
          'override/SPFIRSE2.bam','override/SPCHLGT1.bam',
          'override/SPCHLGT2.bam','override/SPCHLGT3.bam']


def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def snap(p):return asdict(tx.snapshot_file(p))
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')


def prepare():
    if OUT.exists():
        assert {p.name for p in OUT.iterdir()} <= {'candidate','tests.log'}, 'Sealed preparation exists'
    assert '100% tests passed, 0 tests failed out of 4' in (BUILD/'mask-v12-tests.log').read_text(encoding='utf-8-sig')
    assert 'contracts checked: 1048' in (PROOF/'native-contracts.log').read_text(encoding='utf-8-sig')
    old=js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-lightning-trails-20261028-v11/installation.json')
    assert snap(GAME/'InfinityEngine-Enhancer.dll')==old['dll']
    off=js(ROOT/'projectiles/analysis/validations-manuelles-consolidees-20261028-v1/trace-disabled.json')
    assert tx.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==off['after_sha256']
    plan=js(PROOF/'prepare.json')
    for name in QA:
        assert not (GAME/'override'/name).exists()
        assert snap(PROOF/'qa'/name)==plan['QA_resources'][name]
    protected={n:snap(GAME/n) for n in PRESERVE+['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini']}
    OUT.mkdir(parents=True,exist_ok=True)
    candidate=OUT/'candidate';candidate.mkdir(exist_ok=True)
    shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',candidate/'InfinityEngine-Enhancer.dll')
    ini=(GAME/'InfinityEngine-Enhancer.ini').read_bytes()
    assert ini.count(b'EnableEffectStreamingTrace = false')==1
    (candidate/'InfinityEngine-Enhancer.ini').write_bytes(ini.replace(b'EnableEffectStreamingTrace = false',b'EnableEffectStreamingTrace = true'))
    shutil.copy2(BUILD/'mask-v12-tests.log',OUT/'tests.log')
    save(OUT/'before.json',dict(files=protected,
        PROs={p.name:snap(p) for p in (GAME/'override').glob('*.pro')},
        qa_source={n:snap(PROOF/'qa'/n) for n in QA},
        source_sha256={n:tx.sha256_file(ROOT/n) for n in [
            'engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/effect_secondary_scope.h',
            'engine/InfinityEngine-Enhancer/source-patchee/tests/effect_occlusion_tests.cpp',
            'engine/InfinityEngine-Enhancer/source-patchee/tests/effect_surface_owner_tests.cpp']},
        tracking_sha256=tx.sha256_file(ROOT/'projectiles/index/work-tracking.json')))
    print('Prepared V12: SPMAGMIS per-FX scope, two new QA files, temporary trace only')


def install():
    assert not (OUT/'installation.json').exists()
    before=js(OUT/'before.json')
    tx.ensure_game_stopped(tx.running_game_processes)
    for n,s in before['files'].items():assert snap(GAME/n)==s,n
    for n,s in before['PROs'].items():assert snap(GAME/'override'/n)==s,n
    for n,h in before['source_sha256'].items():assert tx.sha256_file(ROOT/n)==h,n
    assert tx.sha256_file(ROOT/'projectiles/index/work-tracking.json')==before['tracking_sha256']
    for n in QA:
        target=GAME/'override'/n
        assert target.resolve().parent==(GAME/'override').resolve() and not target.exists()
        assert snap(PROOF/'qa'/n)==before['qa_source'][n]
    save(OUT/'qa-transaction.json',dict(status='prepared',before={n:None for n in QA},files=before['qa_source']))
    created=[];result=None
    try:
        for n in QA:
            data=(PROOF/'qa'/n).read_bytes()
            with (GAME/'override'/n).open('xb') as f:
                created.append(n)
                f.write(data);f.flush();os.fsync(f.fileno())
            assert snap(GAME/'override'/n)==before['qa_source'][n]
        result=tx.install_candidate(OUT/'candidate',game_root=GAME,backup_root=OUT/'backups')
        tx.verify_transaction(result.receipt_path,game_root=GAME)
        for n,s in before['files'].items():
            if n not in ['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini']:assert snap(GAME/n)==s,n
        for n,s in before['PROs'].items():assert snap(GAME/'override'/n)==s,n
    except Exception:
        if result:tx.restore_from_receipt(result.receipt_path,game_root=GAME)
        for n in created:
            p=GAME/'override'/n
            assert snap(p)==before['qa_source'][n], 'Divergent QA file; preserve for manual recovery'
            p.unlink()
        raise
    save(OUT/'installation.json',dict(status='installed-awaiting-technical-capture',utc=tx.utc_now(),
        receipt=str(result.receipt_path.relative_to(ROOT)),dll=snap(GAME/'InfinityEngine-Enhancer.dll'),
        previous_dll=before['files']['InfinityEngine-Enhancer.dll'],ini=snap(GAME/'InfinityEngine-Enhancer.ini'),
        scope_added=['SPMAGMIS'],temporary_trace=True,new_QA_files={n:snap(GAME/'override'/n) for n in QA},
        existing_QA_or_gameplay_resources_replaced=0,images_reprocessed=0,PROs_changed=False,
        manifest_and_registry_changed=False,movement_changed=False,release_changed=False,
        tests='4/4 passed',native_contracts=1048,ingame_validated=False,
        cleanup='After capture and game/loader stop: disable only streaming trace; remove only the two new SHA-matched QA files if no longer needed'))
    print('Installed V12 + XQTARG/XQSEED; images/PROs/catalogue unchanged, temporary trace active')


if __name__=='__main__':{'prepare':prepare,'install':install}[sys.argv[1]]()
