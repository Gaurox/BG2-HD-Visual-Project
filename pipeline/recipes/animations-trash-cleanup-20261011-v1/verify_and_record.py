"""Verify deletion/quarantine and record physical locations without changing QA."""
from prepare import *
import subprocess,copy,sys

def main():
    plan=load(HERE/'operation-plan.json');progress=load(HERE/'operation-progress.json')
    assert progress['status']=='completed' and progress['plan_sha256']==sha(HERE/'operation-plan.json')
    assert len(progress['deleted'])==43 and len(progress['moved'])==51
    for item in plan['deletes']:
        assert not (ROOT/item['path']).exists(),item['path']
        for record in item['diagnostics']:assert sha(ROOT/record['archive'])==record['sha256']
    for item in plan['moves']:
        assert not (ROOT/item['source']).exists()
        dest=ROOT/item['destination'];assert dest.is_dir()
        actual={p.relative_to(dest).as_posix():sha(p) for p in dest.rglob('*') if p.is_file()}
        assert actual==item['payload_sha256'],item['source']
    marker_by_source={r['source']:r for r in plan['reservation_moves']}
    for item in plan['reservation_moves']:
        assert not (ROOT/item['source']).exists() and sha(ROOT/item['destination'])==item['sha256']
    for name,h in plan['authority_sha256'].items():
        p=ROOT/(marker_by_source[name]['destination'] if name in marker_by_source else name)
        assert sha(p)==h,name
    for name in plan['retained_roots']:assert (ROOT/name).is_dir(),name
    roots=[p for p in [*(ROOT/'animations/runs').glob('*'),*(ROOT/'animations/batches').glob('*'),*(ROOT/'animations/ressources').glob('*/runs/*')] if p.is_dir()]
    assert len(roots)==665,len(roots)
    contracts={}
    def scan(obj):
        if isinstance(obj,dict):
            if isinstance(obj.get('manifest_path'),str) and isinstance(obj.get('manifest_sha256'),str):
                contracts[obj['manifest_path']]=obj['manifest_sha256'].lower()
            for value in obj.values():scan(value)
        elif isinstance(obj,list):
            for value in obj:scan(value)
    for base in ['qa-decisions','area-qa-decisions','selections']:
        for p in (ROOT/'animations/index'/base).rglob('*.json'):scan(load(p))
    for name,h in contracts.items():assert sha(ROOT/name)==h,name
    assert len(contracts)==1265
    review=load(AUDIT/'reviewed-audit.json')
    for item in review['removable']:
        for bam in item['bam_duplicate_verification']:
            assert any(sha(ROOT/name)==bam['sha256'] for name in bam['identical_canonical_sources'])
    status=subprocess.run([sys.executable,str(ROOT/'pipeline/scripts/area_pack_state.py'),'status','-v'],
        capture_output=True,text=True,encoding='utf-8',env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    assert status.returncode==0,status.stdout+status.stderr
    manifest=dict(schema='bg2-animation-local-trash-manifest-v1',status='quarantined-not-validated',
        created_utc=datetime.now(timezone.utc).isoformat(),operation_plan=rel(HERE/'operation-plan.json'),
        operation_plan_sha256=sha(HERE/'operation-plan.json'),original_root=str(ROOT),
        moved_runs=plan['moves'],reservation_markers=plan['reservation_moves'],
        restore_policy='Verify payload hashes; move destination to source only when source is free; restore associated reservation too. Original manifests remain unchanged.',
        disk_space_freed_by_quarantine=0,QA_mutation=False,installation_mutation=False,release_mutation=False)
    write(TRASH/'manifest.json',manifest)
    index=dict(schema='bg2-animation-local-run-quarantine-locations-v1',
        authority_policy='Physical locations only; never changes production, QA, selection, installation or release status.',
        manifest=rel(TRASH/'manifest.json'),manifest_sha256=sha(TRASH/'manifest.json'),
        migrations=[dict(source=r['source'],destination=r['destination']) for r in plan['moves']+plan['reservation_moves']])
    write(ROOT/'animations/index/run-quarantine-20261011-v1.json',index)
    receipt=dict(schema='bg2-animation-runs-trash-cleanup-receipt-v1',status='completed',
        created_utc=datetime.now(timezone.utc).isoformat(),operation_plan=rel(HERE/'operation-plan.json'),
        operation_plan_sha256=sha(HERE/'operation-plan.json'),deleted_runs=43,quarantined_runs=29,
        quarantined_reservations=22,retained_runs=665,gross_deleted_bytes=plan['gross_deleted_bytes'],
        diagnostics_archived_bytes=plan['diagnostics_archived_bytes'],estimated_net_freed_bytes=plan['estimated_net_freed_bytes'],
        quarantined_bytes=plan['quarantined_bytes'],trash_manifest=rel(TRASH/'manifest.json'),
        trash_manifest_sha256=sha(TRASH/'manifest.json'),
        verification=dict(all_quarantined_payload_hashes_identical=True,authority_files_unchanged_or_moved_exactly=len(plan['authority_sha256']),
            qa_selection_manifests_present_hash_identical=len(contracts),installation_status=status.stdout.strip(),native_sources_preserved=True),
        game_mutation=False,QA_mutation=False,release_mutation=False)
    write(HERE/'receipt.json',receipt)
    report=copy.deepcopy(load(ROOT/'docs/validation/animations-cleanup-status-20261011-v3.json'))
    report.update(schema='bg2-upscale-animation-cleanup-status-v4',
        scope='Acquired QA preserved; additional43 unused runs deleted,29 uncertain runs reversibly quarantined',
        verification=rel(HERE/'receipt.json'))
    report['historical_reports'].append('docs/validation/animations-cleanup-status-20261011-v3.json')
    report['additional_unused_runs_cleanup']=dict(deleted_runs=43,estimated_net_freed_bytes=plan['estimated_net_freed_bytes'],
        quarantined_runs=29,quarantined_reservations=22,remaining_active_tree_runs=665,
        quarantine_is_not_validation=True,trash=rel(TRASH),physical_migrations=rel(ROOT/'animations/index/run-quarantine-20261011-v1.json'),
        receipt=rel(HERE/'receipt.json'))
    report['next_actions'].insert(0,'Keep29 quarantined runs until explicit decision; no ingame recheck implied by physical reservations/history')
    write(ROOT/'docs/validation/animations-cleanup-status-20261011-v4.json',report)
    print(status.stdout.strip())
    print('PASS:43 deleted;29+22 quarantined byte-identical;665 retained;1265 QA manifests intact; tracking v4')

if __name__=='__main__':main()
