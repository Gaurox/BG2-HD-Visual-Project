"""Record completed installed town_static; QA/release remain independent."""
import csv,io,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prefix=HERE.relative_to(ROOT).as_posix()
production=load(HERE/'production.json');plan=production['plan'];stats=production['stats']
installation=load(HERE/'installation-verification.json')
assert installation['status']=='installed-pending-ingame-qa' and not installation['ingame_QA']
entry=dict(family='town_static',reference=prefix+'/current-generation.json',selection=prefix+'/selection.json',
    animation_ids=[w['animation_id'] for w in plan['witnesses']],source_absent_animation_ids=['0x4001'],
    physical_frames=1543,unique_source_work=1542,unique_encoded_work=1542,
    encoded_cache_hits=stats['encoded_cache_hits'],new_encoded_work=stats['new_encoded_work'],
    new_neural_targets=stats['new_neural_targets'],resume_cache_hits=production['resume']['encoded_cache_hits'],
    installation_reference=prefix+'/ingame-installation/active-test.json',
    installation_snapshot=prefix+'/installation-verification.json',
    state='family-complete-available-produced-installed-ingame-QA-pending',qa_ingame=False,release=False,SDF=False)
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
assert not any(r['family']=='town_static' for r in tracking['current_recipe_complete_productions'])
tracking['current_recipe_complete_productions'].append(entry)
family=next(f for f in tracking['families'] if f['engine_section']=='town_static')
family['current_full_production']=entry
totals=tracking['queue_totals']
assert totals['current_recipe_complete_families']==5 and totals['current_recipe_complete_animation_ids']==23
totals.update(current_recipe_complete_families=6,current_recipe_complete_animation_ids=41,current_recipe_installed_animation_ids=41)
assert totals['current_recipe_ingame_accepted_families']==4 and totals['current_recipe_ingame_accepted_animation_ids']==22
tracking['engine_integration']['latest_installation_verification_reference']=prefix+'/installation-verification.json'
path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=ROOT/'sprite/index/q3m-work-items.csv';rows=path.read_text(encoding='utf-8-sig').splitlines(keepends=True)
fields=next(csv.reader([rows[0]]));by_id={w['animation_id']:w for w in plan['witnesses']};changed=0
for i,line in enumerate(rows[1:],1):
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in by_id:continue
    assert row['engine_family']=='town_static'
    row.update(queue_state='current-recipe-complete-installed-QA-pending',
        colour_variant_state='v7-full-x2-no-SDF-installed-ingame-QA-pending',
        q3m_final_work_count_known=str(by_id[row['animation_id']]['encoded_work']),
        q3m_v7_full_production_reference=prefix+'/current-generation.json',
        q3m_v7_installation_reference=prefix+'/installation-verification.json')
    out=io.StringIO(newline='');writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');writer.writerow(row)
    rows[i]=out.getvalue();changed+=1
assert changed==18
path.write_text(''.join(rows),encoding='utf-8')
print('Recorded town_static installed: 6 complete families/41 IDs; 4 families/22 IDs accepted unchanged.')
