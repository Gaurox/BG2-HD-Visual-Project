"""Finish per-pass SPMAGMIS masking while preserving its existing padded canvas."""
from pathlib import Path
from dataclasses import asdict
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
GAME=tx.get_path('bg2ee_game_root',required=True)
OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v14'
OLD=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v13'
PROOF=ROOT/'projectiles/analysis/masque-capture-v14-20261028-v1'
BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'

def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def snap(p):return asdict(tx.snapshot_file(p))
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')

def prepare():
    assert not OUT.exists()
    assert '100% tests passed, 0 tests failed out of 5' in (BUILD/'mask-v14-final-tests.log').read_text(encoding='utf-8-sig')
    previous=js(OLD/'installation.json');assert snap(GAME/'InfinityEngine-Enhancer.dll')==previous['dll']
    assert snap(GAME/'InfinityEngine-Enhancer.ini')==js(OLD/'before.json')['protected']['InfinityEngine-Enhancer.ini']
    proof=js(PROOF/'geometry-proof.json');assert proof['source_images_reprocessed'] is False
    old_before=js(OLD/'before.json')
    protected={n:snap(GAME/n) for n in old_before['protected'] if n!='InfinityEngine-Enhancer.dll'}
    for n,expected in old_before['protected'].items():
        if n not in ['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini']:assert protected[n]==expected,n
    for n,h in js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-mask-capture-20261028-v12/installation.json')['new_QA_files'].items():
        assert snap(GAME/'override'/n)==h
        protected['override/'+n]=h
    OUT.mkdir(parents=True);candidate=OUT/'candidate';candidate.mkdir()
    shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',candidate/'InfinityEngine-Enhancer.dll')
    shutil.copy2(GAME/'InfinityEngine-Enhancer.ini',candidate/'InfinityEngine-Enhancer.ini')
    shutil.copy2(BUILD/'mask-v14-final-tests.log',OUT/'tests.log')
    names=['src/iee/core/effect_surface_owner.h','src/iee/core/effect_secondary_scope.h',
           'src/iee/hooks.cpp','src/iee/effect_animation_x4_registry.cpp','src/iee/effect_animation_x4_registry.h',
           'tests/effect_surface_owner_tests.cpp','tests/effect_occlusion_tests.cpp','tests/effect_texture_cache_tests.cpp']
    save(OUT/'before.json',dict(protected=protected,previous_dll=previous['dll'],PROs=old_before['PROs'],
        source_sha256={n:tx.sha256_file(ROOT/'engine/InfinityEngine-Enhancer/source-patchee'/n) for n in names},
        geometry_proof_sha256=tx.sha256_file(PROOF/'geometry-proof.json')))
    print('Prepared V14: crop source to native variable canvas; same QA files/INI/images/PROs')

def install():
    assert not (OUT/'installation.json').exists()
    b=js(OUT/'before.json');tx.ensure_game_stopped(tx.running_game_processes)
    assert snap(GAME/'InfinityEngine-Enhancer.dll')==b['previous_dll']
    for n,h in b['protected'].items():assert snap(GAME/n)==h,n
    for n,h in b['PROs'].items():assert snap(GAME/'override'/n)==h,n
    for n,h in b['source_sha256'].items():assert tx.sha256_file(ROOT/'engine/InfinityEngine-Enhancer/source-patchee'/n)==h,n
    result=tx.install_candidate(OUT/'candidate',game_root=GAME,backup_root=OUT/'backups')
    tx.verify_transaction(result.receipt_path,game_root=GAME)
    for n,h in b['protected'].items():assert snap(GAME/n)==h,n
    for n,h in b['PROs'].items():assert snap(GAME/'override'/n)==h,n
    save(OUT/'installation.json',dict(status='installed-awaiting-one-magic-missile-capture',utc=tx.utc_now(),
        receipt=str(result.receipt_path.relative_to(ROOT)),dll=snap(GAME/'InfinityEngine-Enhancer.dll'),
        previous_dll=b['previous_dll'],ini_unchanged=True,temporary_trace=True,SPMAGMIS_source_crop=dict(lookup=[64,78],content=[64,64],top=7,bottom=7,destination='native-variable-canvas'),
        scope_added_since_V11=['SPMAGMIS'],new_QA_files_since_V11=['XQTARG.cre','XQSEED.spl'],
        images_reprocessed=0,existing_gameplay_resources_changed=False,PROs_changed=False,
        catalogue_changed=False,movement_changed=False,release_changed=False,tests='5/5 passed',
        loader_contracts_retained=1048,ingame_validated=False))
    print('Installed final V14: per-pass mask and dynamic native canvas, existing source cropped in memory; no image writes')

if __name__=='__main__':{'prepare':prepare,'install':install}[sys.argv[1]]()
