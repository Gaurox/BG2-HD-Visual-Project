"""Freeze complete installed-area packs, then plan promotions against acquired QA."""
from pathlib import Path
import sys,functools,json,shutil
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/recipes/animations-cleanup-points1-3-20261011-v1'))
from common import *
HERE=Path(__file__).resolve().parent
PACK=ROOT/'animations/packs-par-zone/animations-release-20261011-v1'
import animation_release as release
import merge_area_pack_resources as merger

def reconstruct_for_release(area):
    build=state.load_lock()['areas'][area]['build']
    if 'leaf' in build:return reconstruct(area)
    loaded=[]
    for spec in build['merged_from']:
        items,_=merger.load_area_pack(spec);loaded.extend(items)
    groups={}
    for resource,sources in loaded:groups.setdefault(resource['resref'],[]).append((resource,sources))
    rr=[];sources={}
    for ref,variants in sorted(groups.items()):
        variants.sort(key=lambda pair:(v.resource_position(pair[0]) is not None,v.resource_position(pair[0]) or (0,0)))
        for index,(resource,resource_sources) in enumerate(variants):
            sources.update(merger.retarget_variant(resource,index,resource_sources));rr.append(resource)
    live=state.game_areas_dir()/area;version=registry_version(live);before=fresh_payload(live)
    assert v.registry_v2_from_resources(sorted(rr,key=v.resource_sort_key),version)==(live/v.REGISTRY_NAME).read_bytes(),area+': reconstructed routing differs'
    assert {v.REGISTRY_NAME,*sources}==set(before),area
    assert all(before[a['name']]==a['sha256'].lower() for r in rr for a in r['assets']),area
    return rr,sources,version,before

def cached_validators():
    release.validate_pack=functools.lru_cache(None)(release.validate_pack)
    release.validate_workflow_resref=functools.lru_cache(None)(release.validate_workflow_resref)
    original_load=release.load_json;cache={}
    def load_static(p):
        if p==release.CANDIDATES:return original_load(p)
        if p not in cache:cache[p]=original_load(p)
        return cache[p]
    release.load_json=load_static
    release.sha256_file=functools.lru_cache(None)(release.sha256_file)

def main():
    assert not (HERE/'promotion-plan.json').exists()
    qa={rel(p):digest(p) for folder in ['qa-decisions','area-qa-decisions','selections'] for p in (ROOT/'animations/index'/folder).rglob('*.json')}
    before=HERE/'animation-release-candidates-before.json'
    if not before.exists():shutil.copyfile(release.CANDIDATES,before)
    areas=sorted(state.load_lock()['areas']);frozen=[]
    for index,area in enumerate(areas,1):
        leaf=PACK/area
        if not (leaf/'manifest.json').exists():
            rr,sources,version,installed=reconstruct_for_release(area)
            write_leaf(leaf,area,rr,sources,version,dict(operation='release snapshot, exact installed bytes, QA checked separately',
                source_lock='animations/index/area-pack-lock.json',game_mutation=False))
            assert fresh_payload(leaf)==installed,area
        else:assert fresh_payload(leaf)==fresh_payload(state.game_areas_dir()/area),area
        frozen.append(dict(area=area,pack=rel(leaf),manifest_sha256=digest(leaf/'manifest.json')))
        if index%10==0:print('FROZEN',index,'/',len(areas),flush=True)
    if not (PACK/'manifest.json').exists():write_index(PACK,areas,'Complete installed-area snapshots for explicit release finalization; QA remains separate')
    cached_validators();plans=[];errors=[]
    with release.workflow_lock():
        assert not release.AUTHORITY_JOURNAL.exists() and not release.PUBLICATION_JOURNAL.exists()
        for index,area in enumerate(areas,1):
            try:
                plan=release.build_promotion(area,rel(PACK/area),'Finalisation release demandée par l’utilisateur le2026-10-11 ; QA acquises conservées, composition exacte vérifiée sans nouvelle validation ingame.')
                plans.append(release.public_plan(plan))
            except Exception as error:
                errors.append(dict(area=area,error=str(error)));print('PROMOTION ERROR',area,str(error),flush=True)
            if index%10==0:print('PLANNED',index,'/',len(areas),flush=True)
    for name,h in qa.items():assert v.sha256_file(ROOT/name)==h,name
    write(HERE/'promotion-plan.json',dict(schema='bg2-animation-release-finalization-plan-v1',status='ready' if not errors else 'requires-repair',
        source_candidates=rel(before),source_candidates_sha256=digest(before),areas=frozen,plans=plans,errors=errors,
        preserved_qa_sha256=qa,release_authorized=True,game_mutation=False,new_ingame_QA=False))
    print('PLAN',len(plans),'ready;',len(errors),'errors',flush=True)

if __name__=='__main__':main()
