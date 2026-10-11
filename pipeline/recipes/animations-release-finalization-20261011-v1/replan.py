"""Recheck promotions after repairing acquired QA bindings and WED projection."""
from prepare import *

def main():
    destination=HERE/'promotion-plan-v2.json';assert not destination.exists()
    areas=sorted(state.load_lock()['areas'])
    frozen=[dict(area=area,pack=rel(PACK/area),manifest_sha256=digest(PACK/area/'manifest.json')) for area in areas]
    qa={rel(p):digest(p) for folder in ['qa-decisions','area-qa-decisions','selections']
        for p in (ROOT/'animations/index'/folder).rglob('*.json')}
    cached_validators();plans=[];errors=[]
    with release.workflow_lock():
        assert not release.AUTHORITY_JOURNAL.exists() and not release.PUBLICATION_JOURNAL.exists()
        for index,item in enumerate(frozen,1):
            try:plans.append(release.public_plan(release.build_promotion(item['area'],item['pack'],
                'Finalisation release autorisée le 2026-10-11 ; QA acquises conservées.')))
            except Exception as error:
                errors.append(dict(area=item['area'],error=str(error)))
                print('ERROR',item['area'],str(error),flush=True)
            if index%10==0:print('PLANNED',index,'/',len(areas),flush=True)
    for name,h in qa.items():assert v.sha256_file(ROOT/name)==h,name
    write(destination,dict(schema='bg2-animation-release-finalization-plan-v1',
        status='ready' if not errors else 'requires-repair',areas=frozen,plans=plans,errors=errors,
        preserved_qa_sha256=qa,release_authorized=True,game_mutation=False,new_ingame_QA=False))
    print('READY',len(plans),'ERRORS',len(errors),flush=True)

if __name__=='__main__':main()
