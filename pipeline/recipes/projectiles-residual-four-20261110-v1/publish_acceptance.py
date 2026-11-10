"""Publish the completed colour review/trace cleanup; no new asset or game writes."""
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
ACCEPT=ROOT/'projectiles/analysis/residual-four-colours-accepted-20261110-v1'
OUT=ROOT/'projectiles/analysis/owner-contracts-residual-four-accepted-20261110-v3'
INSTALL=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1'


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def ref(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main():
    assert not OUT.exists(),'Use a new completed revision'
    game=get_path('bg2ee_game_root',required=True);before=load(INSTALL/'before.json');installed=load(INSTALL/'installation.json')
    assert sha(game/'InfinityEngine-Enhancer.dll')==installed['dll']['sha256']
    assert sha(game/'InfinityEngine-Enhancer.ini')==before['runtime_files']['InfinityEngine-Enhancer.ini']['sha256']
    for name,snapshot in before['files'].items():assert sha(game/name)==snapshot['sha256']
    for name,snapshot in before['override_PROs'].items():assert sha(game/'override'/name)==snapshot['sha256']
    write(ACCEPT/'trace-cleanup.json',dict(trace_enabled=False,dll_retained=installed['dll'],
        ini_before_trace_disable=installed['ini'],ini_after_sha256=sha(game/'InfinityEngine-Enhancer.ini'),
        original_ini_exact=True,other_settings_preserved=True,game_and_loader_stopped_at_cleanup=True,
        source_images_PRO_registry_shaders_sprites_preserved=True,release_changed=False))
    prior=load(ROOT/'projectiles/index/owner-reconciliation-current.json');assert prior['new_manual_tests']==2
    owners=load(ROOT/prior['owners']['path']);trackingpath=ROOT/'projectiles/index/work-tracking.json';tracking=load(trackingpath)
    old=copy.deepcopy(tracking);acceptance=ref(ACCEPT/'acceptance.json');evidence=acceptance['path']
    changed=[]
    for owner in owners:
        if owner['state']!='qualified-installed-scoped-colour-QA-pending':continue
        ident=int(owner['owner'].split(':')[1]);owner['state']='reconciled-compatible-contracts'
        owner['shared_colour_evidence']=dict(acceptance=acceptance,observed_for_this_ID=ident in (138,142),
            scope='Exact shared source-specific palette/render contract qualified;visual acceptance stays scoped to138/SHWATER6 and142/MPALETTE67.')
        changed.append(ident)
    assert set(changed)=={120,123,126,129,132,135,138,141,142,143,144}
    assert Counter(o['state'] for o in owners)=={'reconciled-compatible-contracts':313,'documented-native-gap-no-static-driver':7}
    OUT.mkdir(parents=True);write(OUT/'owners.json',owners);write(OUT/'exceptions.json',[])
    summary=dict(schema='bg2-projectile-owner-reconciliation-acceptance-v1',date='2026-11-10',
        prior_authority=prior,acceptance=acceptance,trace_cleanup=ref(ACCEPT/'trace-cleanup.json'),
        owner_states=dict(Counter(o['state'] for o in owners)),technical_qualified_owners=313,total_owners=320,
        technical_percentage=97.8125,active_exception_families=0,pending_manual_checks=0,
        actual_new_HD_colour_resources=['SHWATER','SPBOOM'],observed_native_IDs=[138,142],
        other_variants='Technically qualified/shared compatible evidence;no invented individual visual acceptance',
        FLMSTRK_SPDIMDR_live_draw_claimed=False,release_changed=False)
    write(OUT/'summary.json',summary)
    pointer=dict(schema='bg2-projectile-owner-reconciliation-current-v1',date='2026-11-10',
        report=(ACCEPT/'README.md').relative_to(ROOT).as_posix(),summary=ref(OUT/'summary.json'),
        owners=ref(OUT/'owners.json'),exceptions=ref(OUT/'exceptions.json'),states=summary['owner_states'],
        technical_qualified_owners=313,technical_percentage=97.8125,actionable_families=0,actionable_engine_IDs=0,
        deferred_native_gaps=7,new_manual_tests=0,
        meaning='Four residual families technically qualified/installed,two representative colours visually accepted;no remaining manual tests,no global whole-chain visual claim.')
    tracking['owner_evidence_reconciliation']=pointer
    for ident in changed:
        node=tracking['engine_projectiles'][str(ident)]['integration']['automatic_reconciliation']
        node.update(state='reconciled-compatible-contracts',evidence=pointer['owners']['path'],
            scope='Shared technically qualified native palette/render contract;direct colour approval only138 and142.',acceptance=evidence)
    tracking['runtime_route_installations']['residual-four-20261110-v1'].update(trace_enabled=False,
        trace_cleanup=(ACCEPT/'trace-cleanup.json').relative_to(ROOT).as_posix())
    for ns in ('projectiles','engine_projectiles'):
        for name,record in old[ns].items():
            for field in ('qa','installation','release'):assert record.get(field)==tracking[ns][name].get(field)
    validate_tracking(tracking,{r['resref'] for r in read_csv(ROOT/'projectiles/index/resources.csv')})
    write(trackingpath,tracking);write(ROOT/'projectiles/index/owner-reconciliation-current.json',pointer)
    progresspath=ROOT/'projectiles/index/validation-progress-current.json';progress=load(progresspath)
    progress['latest_user_confirmation']=load(ACCEPT/'acceptance.json')['user_decision']
    progress['authorities']['work_tracking_sha256']=sha(trackingpath)
    progress['automatic_owner_reconciliation']=pointer;progress['runtime'].update(trace_enabled=False,dll_sha256=installed['dll']['sha256'])
    progress['scoped_visual_QA'].update(PRO_observed_components_accepted=sum(n.get('qa',{}).get('state')=='accepted-observed-components' for n in tracking['projectiles'].values()),
        engine_IDs_observed_components_accepted=sum(n.get('qa',{}).get('state')=='accepted-observed-components' for n in tracking['engine_projectiles'].values()),
        prepared_manual_tests_pending=0,residual_colour_variants_accepted=2)
    progress['remaining_work']=['No active residual route/palette correction or manual test remains in this batch.',
        'Seven no-driver native gaps preserved;no speculative production or systematic alias retests.',
        'Position interpolation PROJ-MOTION-001 remains deferred;release separate.']
    write(progresspath,progress)
    nativepath=ROOT/'projectiles/index/native-contract-review-current.json';native=load(nativepath)
    native.update(owner_reconciliation=pointer,current_summary=ref(progresspath),latest_residual_colour_acceptance=acceptance)
    native['latest_runtime_installation'].update(state='four-families-qualified-two-colours-accepted',manual_variants=[],trace_enabled=False)
    write(nativepath,native)
    write(OUT/'publication.json',dict(work_tracking_sha256=sha(trackingpath),progress_sha256=sha(progresspath),
        pointer_sha256=sha(ROOT/'projectiles/index/owner-reconciliation-current.json'),new_visual_approvals=[138,142],
        other_visual_decisions_preserved=True,installation_and_release_states_preserved=True,trace_enabled=False))
    print('Current:313/320 technical contracts;two colours accepted;0 manual tests;trace false,DLL retained.')


if __name__=='__main__':main()
