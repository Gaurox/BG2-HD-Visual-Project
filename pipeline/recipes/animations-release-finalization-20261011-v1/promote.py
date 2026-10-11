"""Publish the authorized area candidates with the standard durable transaction."""
from prepare import *

def main():
    plan_path=HERE/'promotion-plan-v3.json'
    if not plan_path.exists():plan_path=HERE/'promotion-plan-v2.json'
    if not plan_path.exists():plan_path=HERE/'promotion-plan.json'
    baseline=load(plan_path)
    assert baseline['status']=='ready',baseline.get('errors')
    receipt_path=HERE/'promotion-receipt.json'
    assert not receipt_path.exists()
    cached_validators();promoted=[]
    with release.workflow_lock():
        assert not release.AUTHORITY_JOURNAL.exists()
        assert not release.PUBLICATION_JOURNAL.exists()
        for index,item in enumerate(baseline['areas'],1):
            area=item['area'];pack=item['pack']
            assert digest(ROOT/pack/'manifest.json')==item['manifest_sha256']
            # Rebuild against the current registry: each new component ID must be unique.
            plan=release.build_promotion(area,pack,
                'Finalisation release autorisée le 2026-10-11 ; QA acquises conservées, composition exacte vérifiée sans nouvelle validation ingame.')
            changed=release.apply_acceptance(plan)
            promoted.append(dict(**release.public_plan(plan),changed=changed))
            if index%10==0:print('PROMOTED',index,'/',len(baseline['areas']),flush=True)
    for name,sha in baseline['preserved_qa_sha256'].items():
        assert v.sha256_file(ROOT/name)==sha,name
    candidates=json.loads(release.CANDIDATES.read_text(encoding='utf-8-sig'))['candidates']
    assert len(candidates)==len(baseline['areas'])==234
    assert len({c['component_id'] for c in candidates})==234
    assert {c['area'] for c in candidates}=={a['area'] for a in baseline['areas']}
    assert all(c['approval_status']=='approved-for-release' for c in candidates)
    write(receipt_path,dict(schema='bg2-animation-release-finalization-receipt-v1',
        areas=promoted,area_count=len(promoted),candidates_sha256=v.sha256_file(release.CANDIDATES),
        plan=rel(plan_path),plan_sha256=digest(plan_path),game_mutation=False,new_ingame_QA=False,
        preserved_qa_sha256=baseline['preserved_qa_sha256']))
    print('PROMOTED ALL',len(promoted),flush=True)

if __name__=='__main__':main()
