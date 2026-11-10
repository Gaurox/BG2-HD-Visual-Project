"""Amend current owner disposition from installed residual bridge proof; keep QA."""
from pathlib import Path
from collections import Counter
import copy
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from projectile_tracking import validate_tracking,read_csv
PROOF=ROOT/'projectiles/analysis/residual-four-20261110-v1'
OUT=ROOT/'projectiles/analysis/owner-contracts-residual-four-20261110-v2'
INSTALL=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1'


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))


def main():
    assert not OUT.exists(),'Use a new owner revision'
    game=get_path('bg2ee_game_root',required=True)
    installed=load(INSTALL/'installation.json');before=load(INSTALL/'before.json')
    assert sha(game/'InfinityEngine-Enhancer.dll')==installed['dll']['sha256']
    for n,expected in before['files'].items():assert sha(game/n)==expected['sha256']
    for n,expected in before['source_sha256'].items():
        assert sha(ROOT/'engine/InfinityEngine-Enhancer/source-patchee'/n)==expected
    assert '100% tests passed, 0 tests failed out of 5' in (PROOF/'engine-tests.log').read_text(encoding='utf-8')
    assert 'contracts checked: 31668' in (PROOF/'regression-loader.log').read_text(encoding='utf-8')
    trackpath=ROOT/'projectiles/index/work-tracking.json';tracking=load(trackpath);old=copy.deepcopy(tracking)
    prior=load(ROOT/'projectiles/index/owner-reconciliation-current.json')
    assert prior['actionable_families']==4
    owners=load(ROOT/prior['owners']['path'])
    fixed={109,120,123,126,129,132,135,138,141,142,143,144,145,66}
    colour={120,123,126,129,132,135,138,141,142,143,144}
    OUT.mkdir(parents=True)
    evidence=[ref(INSTALL/'installation.json'),ref(PROOF/'qualification.json'),ref(PROOF/'source-palettes.json'),ref(PROOF/'engine-tests.log'),ref(PROOF/'regression-loader.log')]
    for owner in owners:
        if not owner['owner'].startswith('engine-id:'):continue
        ident=int(owner['owner'].split(':')[1])
        if ident not in fixed:continue
        owner['previous_disposition']=dict(state=owner['state'],errors=owner['errors'])
        owner['state']='qualified-installed-scoped-colour-QA-pending' if ident in colour else 'reconciled-compatible-contracts'
        owner['errors']=[];owner['residual_bridge_evidence']=evidence
        node=tracking['engine_projectiles'].setdefault(str(ident),{})
        integration=node.setdefault('integration',dict(state='technical-reconciliation-recorded'))
        integration['automatic_reconciliation']=dict(state=owner['state'],evidence=(OUT/'owners.json').relative_to(ROOT).as_posix(),
            owner=owner['owner'],reviewed_on='2026-11-10',scope='Technical bridge/palette qualification only; colour QA pending, existing image QA retained.')
        if ident==66:
            integration['residual_four_runtime']=dict(state='qualified-static-installed-prior-image-QA-retained',
                evidence=[e['path'] for e in evidence],scope='Same FLMSTRK source/class/geometry as145;no scanned driver for66;no new live draw claim.')
            node['installation']=dict(state='installed',evidence=[installed['receipt']],scope='Shared FLMSTRK registration;native asset unchanged.')
    assert Counter(o['state'] for o in owners)=={'reconciled-compatible-contracts':302,'qualified-installed-scoped-colour-QA-pending':11,'documented-native-gap-no-static-driver':7}
    write(OUT/'owners.json',owners);write(OUT/'exceptions.json',[])
    summary=dict(schema='bg2-projectile-owner-reconciliation-amendment-v1',date='2026-11-10',
        prior_authority=prior,current_installation=ref(INSTALL/'installation.json'),source_evidence=evidence,
        PROs=243,engine_IDs=77,technical_qualified_owners=313,technical_percentage=97.8125,
        owner_states=dict(Counter(o['state'] for o in owners)),active_exception_families=0,
        pending_manual_colour_checks=2,actual_new_live_HD_draws_claimed=0,
        resolved_active_engine_IDs=13,additional_shared_FLMSTRK_ID=66,deferred_no_driver_owners=7,
        QA_promoted=False,images_changed=False,release_changed=False)
    write(OUT/'summary.json',summary)
    pointer=dict(schema='bg2-projectile-owner-reconciliation-current-v1',date='2026-11-10',
        report=(PROOF/'README.md').relative_to(ROOT).as_posix(),summary=ref(OUT/'summary.json'),
        owners=ref(OUT/'owners.json'),exceptions=ref(OUT/'exceptions.json'),states=summary['owner_states'],
        technical_qualified_owners=313,technical_percentage=97.8125,
        actionable_families=0,actionable_engine_IDs=0,deferred_native_gaps=7,new_manual_tests=2,
        meaning='All four active gaps technically corrected/installed;two representative colour reviews pending;no global visual QA or new live HD claim.')
    tracking['owner_evidence_reconciliation']=pointer
    for ns in ('projectiles','engine_projectiles'):
        for name,record in old[ns].items():
            assert tracking[ns][name].get('qa')==record.get('qa')
            assert tracking[ns][name].get('release')==record.get('release')
    validate_tracking(tracking,{r['resref'] for r in read_csv(ROOT/'projectiles/index/resources.csv')})
    write(trackpath,tracking);write(ROOT/'projectiles/index/owner-reconciliation-current.json',pointer)
    progresspath=ROOT/'projectiles/index/validation-progress-current.json';progress=load(progresspath)
    progress['authorities']['work_tracking_sha256']=sha(trackpath)
    progress['automatic_owner_reconciliation']=pointer
    progress['runtime'].update(dll_sha256=installed['dll']['sha256'],trace_enabled=True)
    progress['scoped_visual_QA']['prepared_manual_tests_pending']=2
    progress['remaining_work']=['Two representative colour reviews:SHWATER6/SPPR207 andSPBOOM67/SPWM110;no systematic alias tests.',
        'After user observations/log capture and game stop,disable only temporary trace;retain installed DLL.',
        'Seven no-driver native gaps preserved;no speculative generation. Position interpolation deferred;release separate.']
    write(progresspath,progress)
    nativepath=ROOT/'projectiles/index/native-contract-review-current.json';native=load(nativepath)
    native['owner_reconciliation']=pointer;native['current_summary']=ref(progresspath)
    native['latest_runtime_installation']=dict(**ref(INSTALL/'installation.json'),state=installed['status'],
        manual_variants=['SHWATER6 red','SPBOOM67 gold'],trace_enabled=True,previous_visual_QA_retained=True)
    write(nativepath,native)
    write(OUT/'publication.json',dict(work_tracking_sha256=sha(trackpath),progress_sha256=sha(progresspath),
        pointer_sha256=sha(ROOT/'projectiles/index/owner-reconciliation-current.json'),QA_states_changed=0,release_changed=False))
    print('313/320 contracts technically qualified;0 active exceptions;2 colour checks pending,7 native no-driver gaps retained.')


if __name__=='__main__':main()
