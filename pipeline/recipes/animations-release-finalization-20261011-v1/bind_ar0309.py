"""Formalize the occurrence contract explicitly accepted in the 2026-09-21 QA."""
from prepare import *

def main():
    baseline={rel(p):digest(p) for folder in ['qa-decisions','area-qa-decisions','selections']
        for p in (ROOT/'animations/index'/folder).rglob('*.json')}
    write(HERE/'qa-authorities-before.json',baseline)
    old_selection=ROOT/'animations/index/selections/AM0309A.json'
    shutil.copyfile(old_selection,HERE/'am0309a-selection-before.json')
    old=load(old_selection);old_qa=load(path(old['qa_decision']['path']))
    assert '945,763' in old_qa['decision'] and old_qa['decision_date']=='2026-09-21'
    old_rr=resources(path(old['source_pack']['areas'][0]['path']),'AM0309A')
    new_rr=resources(PACK/'AR0309','AM0309A')
    assert len(old_rr)==len(new_rr)==1
    normalized=copy.deepcopy(new_rr[0]);assert normalized.pop('position')==[945,763]
    normalized.pop('variant_index',None);assert normalized==old_rr[0]
    assert same_live(PACK/'AR0309',new_rr,'AR0309')
    tag='am0309a-acquired-occurrence-bound-20261011-v1'
    run=ROOT/'animations/ressources/AM0309A/runs'/tag
    write(run/'manifest.json',dict(schema='bg2-upscale-historical-qa-binding-run-v1',status='completed',
        created_utc=v.utc_now(),resrefs=['AM0309A'],output_split_root=rel(PACK),
        output_manifest_sha256=digest(PACK/'manifest.json'),
        operation='formalize the occurrence position explicitly described by existing acquired QA',
        acquired_qa_date=old_qa['decision_date'],prior_qa_decision=old['qa_decision'],
        prior_selected_run=old['selected_run'],resources=new_rr,
        new_ingame_qa=False,game_mutation=False,graphical_reprocessing=False))
    decision_id='2026-10-11-preserved-am0309a-occurrence-945-763-v1'
    text='Formalisation du contrat déjà accepté le 2026-09-21, occurrence ARE945,763 ; textures, géométrie, cadence et masque identiques. Aucune nouvelle visite ingame. Source immuable : '+old['qa_decision']['path']+'. '+old_qa['decision']
    outcome=workflow.finalize(ROOT,'AM0309A',run,PACK,['AR0309'],'accepted',old_qa['decision_date'],text,
        decision_id=decision_id,recipe_id=old.get('recipe_id'),correction_id=old.get('correction_id'),apply=True)
    checked=workflow.check_workspace(ROOT,'AM0309A');assert not checked['errors'],checked
    changed_selection=rel(old_selection)
    for name,sha in baseline.items():
        if name!=changed_selection:assert v.sha256_file(ROOT/name)==sha,name
    write(HERE/'ar0309-occurrence-binding.json',dict(outcome=outcome,source_qa=old['qa_decision'],
        modified_current_selection=changed_selection,all_prior_qa_preserved=True,new_ingame_qa=False,game_mutation=False))
    print('AR0309 ACQUIRED QA BOUND; DATE',old_qa['decision_date'])

if __name__=='__main__':main()
