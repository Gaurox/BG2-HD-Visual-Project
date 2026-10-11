from prepare import *
baseline=load(HERE/'promotion-plan-v2.json');assert {e['area'] for e in baseline['errors']}=={'AR0309','AR0516','AR0811'}
cached_validators();plans={p['area']:p for p in baseline['plans']}
with release.workflow_lock():
    for error in baseline['errors']:
        area=error['area']
        plans[area]=release.public_plan(release.build_promotion(area,rel(PACK/area),'QA acquises conservées ; contrats exacts rattachés pour release.'))
        print('REPAIRED',area,flush=True)
qa={rel(p):digest(p) for folder in ['qa-decisions','area-qa-decisions','selections']
    for p in (ROOT/'animations/index'/folder).rglob('*.json')}
old=load(HERE/'qa-authorities-before.json')
mutable={'animations/index/selections/AM0309A.json','animations/index/selections/OHHPORT.json'}
for name,sha in old.items():
    if name not in mutable:assert v.sha256_file(ROOT/name)==sha,name
write(HERE/'promotion-plan-v3.json',dict(**{k:value for k,value in baseline.items() if k not in {'status','plans','errors','preserved_qa_sha256'}},
    status='ready',plans=[plans[a['area']] for a in baseline['areas']],errors=[],preserved_qa_sha256=qa,
    historical_qa_authorities_preserved=True,repaired_current_selections=sorted(mutable)))
write(HERE/'ohhport-canonical-binding.json',dict(source_qa=load(HERE/'ohhport-selection-before.json')['qa_decision'],
    current_selection='animations/index/selections/OHHPORT.json',acquired_qa_date='2026-10-10',old_qa_unchanged=True,
    new_ingame_qa=False,game_mutation=False,historical_malformed_decision_retained=True))
write(HERE/'runtime-and-wed-freeze.json',dict(bundle_id='iee-0.1.0-alpha.9',
    source_inventory=rel(HERE/'renderer-source-inventory.json'),
    current_dll_sha256=load(ROOT/'pipeline/recipes/trees-night-color-20261011-v2/runtime.json')['dll_sha256'],
    source_acceptance='pipeline/recipes/trees-night-color-20261011-v2/acceptance.json',
    ar0516_first_promotion=plans['AR0516'],new_wed_spec='maps/wed-corrections/AR0516/lower-sphinct-cover-acquired-20261011-v2.json',
    evidence='engine/InfinityEngine-Enhancer/source-patchee/docs/validation/ar0516-acquired-release-binding-20261011-v1.md',
    game_mutation=False,new_ingame_qa=False))
print('ALL 234 READY',flush=True)
