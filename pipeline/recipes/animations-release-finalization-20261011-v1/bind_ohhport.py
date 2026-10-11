from prepare import *
ref='OHHPORT';area='AR0811'
selection=ROOT/'animations/index/selections'/('OHHPORT.json')
old=load(selection);qa=load(path(old['qa_decision']['path']))
shutil.copyfile(selection,HERE/'ohhport-selection-before.json')
source=path(old['source_pack']['areas'][0]['path'])
rr=resources(PACK/area,ref);assert release.equivalent_resource_groups(resources(source),rr,ref)
assert qa['status']=='accepted' and qa['tested_areas']==[area] and qa['decision_date']=='2026-10-10'
oldqa={rel(p):digest(p) for p in (ROOT/'animations/index/qa-decisions').glob('*/*.json')}
run=ROOT/'animations/ressources/OHHPORT/runs/ohhport-acquired-canonical-binding-20261011-v1'
write(run/'manifest.json',dict(schema='bg2-upscale-historical-qa-binding-run-v1',status='completed',created_utc=v.utc_now(),
    resrefs=[ref],output_split_root=rel(PACK),output_manifest_sha256=digest(PACK/'manifest.json'),
    operation='canonical path wrapper for unchanged explicitly accepted OHHPORT',
    prior_qa_decision=old['qa_decision'],prior_selected_run=old['selected_run'],resources=rr,
    acquired_qa_date=qa['decision_date'],new_ingame_qa=False,game_mutation=False,graphical_reprocessing=False))
outcome=workflow.finalize(ROOT,ref,run,PACK,[area],'accepted',qa['decision_date'],
    'Rattachement canonique de la QA acquise le 2026-10-10, octets et contrat identiques. Aucune nouvelle visite ingame. Source : '+old['qa_decision']['path']+'. '+qa['decision'],
    decision_id='2026-10-11-preserved-ohhport-canonical-v1',recipe_id=old.get('recipe_id'),correction_id=old.get('correction_id'),apply=True)
check=workflow.check_workspace(ROOT,ref,selected_only=True);assert not check['errors'],check
for name,h in oldqa.items():assert v.sha256_file(ROOT/name)==h,name
write(HERE/'ohhport-canonical-binding.json',dict(outcome=outcome,source_qa=old['qa_decision'],
    acquired_qa_date=qa['decision_date'],old_qa_unchanged=True,new_ingame_qa=False,game_mutation=False))
print('OHHPORT CANONICAL; QA DATE PRESERVED',qa['decision_date'])
