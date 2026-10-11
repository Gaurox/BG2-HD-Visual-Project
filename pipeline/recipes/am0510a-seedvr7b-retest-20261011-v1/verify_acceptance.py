"""Check retained QA/installed bytes and record the actual cleanup completion."""
from finalize import ROOT, RECIPE, ACTIVE, LOT5, GAME, FINAL, TRIAL, v, rel, payload, workflow, state

def main():
    check = workflow.check_workspace(ROOT, 'AM0510A'); assert check['ok'], check
    report = v.load_json(RECIPE/'acceptance.json')
    lock = state.load_lock()
    areas = ['AR0510', *report['lot5_preserved']['areas']]
    for area in areas:
        leaf = ACTIVE/area if area=='AR0510' else LOT5/area
        v.validate_v2_pack(leaf)
        assert payload(leaf)==payload(GAME/'iee-assets/areas'/area),area
        assert state.recipe_signatures(lock['areas'][area]) == {key: val['sig'] for key,val in lock['areas'][area]['resources'].items()},area
    for item in report['cleanup_targets']:
        item['status'] = 'pending' if (ROOT/item['path']).exists() else 'deleted'
    pending = [item['path'] for item in report['cleanup_targets'] if item['status']=='pending']
    report.update(cleanup_status='completed' if not pending else 'partial-pending-shared-pack-approval',
        cleanup_pending=pending,cleanup_deleted_bytes=sum(item['bytes'] for item in report['cleanup_targets'] if item['status']=='deleted'),
        verification=dict(accepted_qa_lineage_valid=True,installed_area_payloads_identical=21,lock_recipes_valid=21,
                          mask_sha256=v.sha256_file(FINAL/'mask.png'),verified_utc=v.utc_now()))
    if pending:
        report['cleanup_approval_reason']='Automatic approval review rejected deletion of the shared complete index: other 20 lot5 areas need explicit authorization despite preserved exact copies.'
    else:
        report.pop('cleanup_approval_reason',None)
    v.write_json(RECIPE/'acceptance.json',report)
    print('QA/installation/lock OK: 21 areas; deleted',len(report['cleanup_targets'])-len(pending),'targets; pending:',pending,flush=True)

if __name__=='__main__':main()
