"""Record only verified Monster production; existing installation/QA retained."""
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    production=load(HERE/'production.json');generation=load(HERE/'current-generation.json')
    verification=load(HERE/'verification.json');previews=load(HERE/'previews.json')
    assert verification['passed'] and previews['animation_ids']==77
    assert all(generation[k] is False for k in ('installation','ingame_QA','release'))
    prefix=HERE.relative_to(ROOT).as_posix()
    record=dict(family='monster',reference=prefix+'/current-generation.json',selection=prefix+'/selection.json',
                animation_ids=generation['animation_ids'],source_absent_animation_ids=generation['source_absent_animation_ids'],
                models=62,colour_variants=77,unique_native_BAM=850,original_native_frames=409599,
                physical_resources=production['pack']['resources'],physical_frames=production['pack']['frames'],
                logical_resource_bindings=1040,bound_frames=496822,
                unique_source_work=102824,unique_encoded_work=102953,stats=production['stats'],
                resume_cache_hits=verification['resume']['encoded_cache_hits'],
                verification_reference=prefix+'/verification.json',previews_reference=prefix+'/previews.json',
                state='family-complete-available-produced-host-verified-installation-ingame-QA-pending',
                registry_version=7,SDF=False,installation=False,qa_ingame=False,release=False)
    path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
    assert not any(r['family']=='monster' for r in tracking['current_recipe_complete_productions'])
    authority_counts={k:v for k,v in tracking['queue_totals'].items() if 'installed' in k or 'ingame' in k}
    family=next(r for r in tracking['families'] if r['engine_section']=='monster')
    assert 'current_full_production' not in family
    family['current_full_production']={k:v for k,v in record.items() if k!='family'}
    tracking['current_recipe_complete_productions'].append(record)
    assert tracking['queue_totals']['current_recipe_complete_animation_ids']==136
    assert tracking['queue_totals']['current_recipe_complete_families']==12
    tracking['queue_totals']['current_recipe_complete_animation_ids']=213
    tracking['queue_totals']['current_recipe_complete_families']=13
    tracking['recorded_on']='2026-10-06'
    assert authority_counts=={k:v for k,v in tracking['queue_totals'].items() if 'installed' in k or 'ingame' in k}
    csvpath=ROOT/'sprite/index/q3m-work-items.csv'
    with csvpath.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream);fields=reader.fieldnames;rows=list(reader)
    witnesses={w['animation_id']:w for w in production['plan']['witnesses']}
    untouched=[r.copy() for r in rows if r['animation_id'] not in witnesses]
    updated=0
    for row in rows:
        if row['animation_id'] not in witnesses:continue
        assert row['engine_family']=='monster' and int(row['source_bam_count'])>0
        assert not row['q3m_v7_installation_reference']
        row['q3m_v7_full_production_reference']=record['reference']
        row['queue_state']='current-recipe-complete-produced-host-verified-installation-ingame-QA-pending'
        row['colour_variant_state']='v7-four-partners-eight-levels-no-SDF-x2-produced-host-verified'
        row['q3m_final_work_count_known']=str(witnesses[row['animation_id']]['encoded_work'])
        updated+=1
    assert updated==77 and untouched==[r for r in rows if r['animation_id'] not in witnesses]
    # The two queue files are mutable pointers, never historical production/QA.
    path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with csvpath.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    summary=ROOT/'sprite/SUIVI_Q3M.md';text=summary.read_text(encoding='utf-8')
    text=text.replace('# Suivi sprites Q3m — 2026-10-05','# Suivi sprites Q3m — 2026-10-06',1)
    lines=text.splitlines()
    matching=[i for i,line in enumerate(lines) if line.startswith('| `monster` |')]
    assert len(matching)==1
    lines[matching[0]]='| `monster` | 77/102 | 3 | **Production disponible complète Q3m V7 x2 améliorée sans SDF, vérifiée sur hôte** : 62 modèles/77 variantes, 850 BAM natifs/409 599 frames ; 102 953 encodages uniques. Installation et QA ingame en attente. 25 IDs sans source exclus. |'
    marker='## Queue / références';position=lines.index(marker)+1
    lines[position:position]=['',f'- Production améliorée complète : **213 IDs /13 familles disponibles** ; Monster ajoute 77 IDs/62 modèles, pack autonome vérifié, non installé. **Installation/QA : 136 IDs /12 familles**, acquis conservés. [Monster](../{prefix}/README.md) ; `{prefix}/current-generation.json`.']
    summary.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(stage='tracking',production_families=13,produced_ids=213,installed_ids=136,ingame_accepted_ids=136,updated_rows=77)),flush=True)

if __name__=='__main__':main()
