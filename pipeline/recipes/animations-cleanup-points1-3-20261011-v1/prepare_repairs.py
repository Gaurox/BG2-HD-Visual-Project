"""Two authorized installations and four metadata-only lock reconstructions."""
from common import *
INSTALL=['AR3021','AR5000']
LOCK_ONLY=['AR0307','AR0411','AR6001','AR6005']

def main():
    assert not REPAIR.exists() and not (HERE/'repair-baseline.json').exists()
    jobs={}
    for area in INSTALL+LOCK_ONLY:
        live=state.game_areas_dir()/area;before=payload(live)
        if area=='AR3021':
            rr=[];sources={}
            for ref in ['AM3021D','AM3021E','AM3021F']:
                leaf=qa_leaf(ref,area);target=resources(leaf,ref);verify_assets(leaf,target)
                rr+=copy.deepcopy(target);sources.update(source_assets(leaf,target))
            assert state.zone_resource_names(live)==set(r['resref'] for r in rr),'AR3021 unexpected sibling'
            version=registry_version(live)
        else:
            rr,sources,version,_=reconstruct(area)
            if area=='AR5000':
                for ref in ['FISH1L','FISH2L','FISH2S','FISH3S']:
                    leaf=qa_leaf(ref,area);target=resources(leaf,ref);verify_assets(leaf,target)
                    assert not any(r['resref']==ref for r in rr)
                    rr+=copy.deepcopy(target);sources.update(source_assets(leaf,target))
        write_leaf(REPAIR/area,area,rr,sources,version,dict(operation='restore accepted resources' if area=='AR3021' else
            ('add four already accepted fish; exact siblings preserved' if area=='AR5000' else 'metadata-only exact installed reconstruction'),
            qa_policy='existing immutable decisions retained; no new ingame acceptance',game_root='config://bg2ee_game_root'))
        after=payload(REPAIR/area)
        if area in LOCK_ONLY:assert before==after,area
        if area=='AR5000':assert all(after.get(n)==h for n,h in before.items() if n!=v.REGISTRY_NAME),area
        jobs[area]=dict(before=before,after=after,operation='install' if area in INSTALL else 'lock-only',
                       old_lock=state.load_lock()['areas'][area])
        print('PREPARED',area,jobs[area]['operation'],flush=True)
    write_index(REPAIR,INSTALL+LOCK_ONLY,'two complete-area installations; four exact snapshots for lock repairs only')
    write(HERE/'repair-baseline.json',dict(areas=jobs,game_mutation_scope=INSTALL,lock_only_areas=LOCK_ONLY))

if __name__=='__main__':main()
