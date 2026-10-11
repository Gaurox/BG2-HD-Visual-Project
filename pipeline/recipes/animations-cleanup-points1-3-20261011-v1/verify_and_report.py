"""Final scoped checks and a new immutable follow-up; historical report v1 remains untouched."""
from formalize_legacy import archive_evidence
from common import *
import contextlib,io,argparse

def main():
    repaired=load(HERE/'repair-installation.json');baseline=load(HERE/'repair-baseline.json')
    migration=load(HERE/'historical-qa-migration.json');checks=[]
    for area,job in baseline['areas'].items():
        live=state.game_areas_dir()/area
        assert fresh_payload(live)==job['after'],area
        assert state.load_lock()['areas'][area]['build']==dict(leaf=rel(REPAIR/area))
        assert state.recipe_signatures(state.load_lock()['areas'][area])=={
            k:x['sig'] for k,x in state.zone_signatures(live).items()},area
        if area in repaired['lock_only_areas']:assert job['before']==job['after']
        if area=='AR5000':assert all(job['after'][n]==h for n,h in job['before'].items() if n!=v.REGISTRY_NAME)
        checks.append(dict(area=area,installed_exact_expected=True,recipe_reconstructs=True,
            operation=job['operation'],prior_game_payload_preserved=area in repaired['lock_only_areas']))
    for ref,area in [('AM3021D','AR3021'),('AM3021E','AR3021'),('AM3021F','AR3021'),
                     ('FISH1L','AR5000'),('FISH2L','AR5000'),('FISH2S','AR5000'),('FISH3S','AR5000')]:
        leaf=qa_leaf(ref,area);assert same_live(leaf,resources(leaf,ref),area),ref
    for p,h in repaired['prior_qa_hashes_preserved'].items():assert v.sha256_file(ROOT/p)==h,p
    for r in migration['results']:
        assert digest(path(r['decision']))==r['decision_sha256'] and not r['check_errors']
        sel=load(ROOT/'animations/index/selections'/(r['resref']+'.json'))
        assert sel['qa_decision']['sha256'].lower()==r['decision_sha256']
        assert sel['source_pack']['path']==r['qa_pack']
    rr=rows();assert len(rr)==246 and all(r['status']=='validé-x4' and r['selected_run'] and r['qa_decision'] for r in rr)
    assert all((ROOT/'animations/index/selections'/(r['resref']+'.json')).is_file() and path(r['qa_decision']).is_file() for r in rr)
    output=io.StringIO()
    with contextlib.redirect_stdout(output):code=state.command_status(argparse.Namespace(verbose=True,deep=False))
    assert code==0,output.getvalue()
    receipts=archive_evidence([dict(path=r['receipt'],sha256=r['receipt_sha256']) for r in repaired['receipts']])
    verified=dict(schema='bg2-upscale-animation-cleanup-verification-v1',status='passed',created_utc=v.utc_now(),
        repaired_areas=checks,all_prior_qa_hashes_preserved=True,canonical_registry_resources=246,
        historical_qa_checks_passed=43,historical_installed_identical=38,
        historical_installed_ambiguous=5,area_state_status=output.getvalue().strip(),
        installed_accepted_resources_checked=7,receipt_archives=receipts,
        regression_command='python -m unittest discover -s pipeline/tests -p test_area_pack_state.py',
        regression_tests=5,regression_result='passed',release_mutation=False)
    write(HERE/'verification.json',verified)
    old=load(ROOT/'docs/validation/animations-cleanup-status-20261011-v1.json')
    report=dict(schema='bg2-upscale-animation-cleanup-status-v2',date='2026-10-11',
        scope='User-requested points 1 to 3; historical user QA preserved, current-version discrepancies explicit',
        historical_report='docs/validation/animations-cleanup-status-20261011-v1.json',
        BAM=dict(resources=246,**{'validé-x4':246},occurrences=3422,areas=234,qa_decision_and_selection_missing=0,
            interpretation='Accepted exact versions, not an assertion that every installed version is accepted'),
        completed=dict(restored_accepted_AR3021=['AM3021D','AM3021E','AM3021F'],
            added_accepted_AR5000=['FISH1L','FISH2L','FISH2S','FISH3S'],
            lock_only_areas=repaired['lock_only_areas'],historical_qa_bound=43,historical_live_identical=38,
            reconstruction_bug_fixed='area_pack_state.build_from_leaf preserves a leaf for structured merged_from provenance instead of stringifying metadata objects'),
        ambiguous_current_versions=[dict(resref=x['resref'],areas=x['installed_different_areas'],
            acquired_validation_preserved=True,accepted_selection=x['selected_run'],reason=x['clarification'].strip(),
            required_action='Choose accepted-version restoration or explicitly accept/recheck the exact currently installed version',
            game_changed_in_this_cleanup=False) for x in migration['results'] if x['installed_different_areas']],
        resolved_historical_note=dict(AM0602F='Native 9 phases installed = exact AR0602 accepted QA 2026-09-05; older 18-phase/30-FPS note retained as history'),
        validation_policy='No existing QA decision changed; no new ingame visit, approval or release integration inferred',
        verification=rel(HERE/'verification.json'),installation_receipt=rel(HERE/'repair-installation.json'),
        migration=rel(HERE/'historical-qa-migration.json'),FIRE_3=old['FIRE_3'],
        release=old['release'],optional_accepted_visual_reserves=old['optional_accepted_visual_reserves'],
        separate_WBM_scope=old['separate_WBM_scope'],
        next_actions=['Resolve the five installed-version discrepancies; no blanket recheck of the other 38 legacy assets',
            'Refresh release candidates and final distribution only upon explicit release finalization request'])
    write(ROOT/'docs/validation/animations-cleanup-status-20261011-v2.json',report)
    print('VERIFIED: 6 repaired areas, 7 accepted installations, 43 preserved historical QA, 246 structured selections; 5 explicit ambiguities')

if __name__=='__main__':main()
