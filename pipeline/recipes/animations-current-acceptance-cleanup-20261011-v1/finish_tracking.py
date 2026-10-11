"""Verify the accepted current bytes and publish a new immutable status report."""
from accept_current import *
import subprocess

def main():
    acceptance=load(HERE/'acceptance.json')
    purge=load(HERE/'purge-receipt.json')
    metadata=load(HERE/'artifact-metadata-verification.json')
    checks={}
    for item in acceptance['decisions']:
        ref=item['resref']
        checks[ref]=workflow.check_workspace(ROOT,ref)['errors']
        assert not checks[ref],checks
    for area,record in acceptance['areas'].items():
        assert fresh_payload(state.game_areas_dir()/area)==record['payload_sha256'],area
        assert fresh_payload(path(record['pack']))==record['payload_sha256'],area
    for name,sha in acceptance['all_prior_qa_hashes_preserved'].items():
        assert v.sha256_file(path(name))==sha,name
    status=subprocess.run([sys.executable,str(ROOT/'pipeline/scripts/area_pack_state.py'),'status','-v'],capture_output=True,text=True,encoding='utf-8',errors='replace')
    assert status.returncode==0,status.stdout+status.stderr
    write(HERE/'verification.json',dict(schema='bg2-upscale-current-accepted-cleanup-verification-v1',status='passed',
        created_utc=v.utc_now(),workflow_errors=checks,game_and_snapshot_payload_identical=True,
        prior_qa_preserved_count=len(acceptance['all_prior_qa_hashes_preserved']),
        installation_status=status.stdout.strip(),artifact_metadata=metadata,
        game_mutation=False,release_mutation=False))
    report=copy.deepcopy(load(ROOT/'docs/validation/animations-cleanup-status-20261011-v2.json'))
    report.update(schema='bg2-upscale-animation-cleanup-status-v3',
        scope='Close five current-version QA discrepancies from explicit user ingame acceptance; remove unused animation runs',
        historical_reports=['docs/validation/animations-cleanup-status-20261011-v1.json','docs/validation/animations-cleanup-status-20261011-v2.json'],
        ambiguous_current_versions=[],current_versions_explicitly_accepted=acceptance['decisions'],
        acceptance=rel(HERE/'acceptance.json'),verification=rel(HERE/'verification.json'),
        validation_policy='Existing immutable QA preserved byte for byte; five new exact installed-version decisions explicitly authorized by user; release unchanged',
        next_actions=['Refresh release candidates and final distribution only upon explicit release finalization request'])
    report.pop('historical_report',None)
    report['completed']['five_current_version_discrepancies_closed']=5
    report['BAM']['interpretation']='246 BAM with QA and selection; five known installed-version discrepancies closed by explicit user acceptance'
    report['unused_runs_cleanup']={k:purge[k] for k in ['deleted_runs','deleted_files','freed_bytes','preserved_runs','all_authority_sha256_preserved','diagnostic_recipes_preserved']}
    report['unused_runs_cleanup'].update(receipt=rel(HERE/'purge-receipt.json'),plan=rel(HERE/'purge-plan.json'),
        scope=['animations/runs/*','animations/batches/*','animations/ressources/*/runs/*'],
        retained='Selected versions, immutable QA, installation/release dependencies, native BAMs, technical approvals and their transitive dependencies',
        archived_diagnostic_files=sum(len(r['diagnostic_metadata_preserved']) for r in load(HERE/'delete-verified.json')['records']),
        historical_missing_references_before_cleanup=len(load(HERE/'purge-plan.json')['preexisting_missing_references']),
        historical_missing_references_note='Pre-existing legacy provenance paths recorded in purge-plan; no missing QA/selection artifact manifest after purge')
    write(ROOT/'docs/validation/animations-cleanup-status-20261011-v3.json',report)
    print(status.stdout.strip())
    print('PASS: five accepted versions, prior QA, exact live/snapshot bytes; v3 tracking written')

if __name__=='__main__':main()
