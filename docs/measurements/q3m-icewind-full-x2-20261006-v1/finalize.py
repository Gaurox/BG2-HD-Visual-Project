"""Record verified Icewind production only; preserve installed/QA/release states."""
import csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');verification=load(HERE/'verification.json')
    runtime=load(HERE/'runtime.json');runtimecheck=load(HERE/'runtime-verification.json');previews=load(HERE/'previews.json')
    assert verification['passed'] and runtimecheck['passed'] and previews['animation_ids']==40
    gen.update(runtime=dict(path=(HERE/'runtime.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'runtime.json')),
        dll=runtime['dll'],verification=dict(path=(HERE/'verification.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'verification.json')),
        runtime_verification=dict(path=(HERE/'runtime-verification.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'runtime-verification.json')))
    write_json(HERE/'current-generation.json',gen);prefix=HERE.relative_to(ROOT).as_posix();reference=prefix+'/current-generation.json'
    record=dict(family='monster_icewind',reference=reference,selection=prefix+'/selection.json',animation_ids=gen['animation_ids'],models=36,colour_variants=40,
        source_absent_animation_ids=gen['source_absent_animation_ids'],native_source_absent_animation_ids=gen['native_source_absent_animation_ids'],
        unique_native_BAM=1051,original_native_frames=71072,physical_resources=1115,physical_frames=75176,logical_resource_bindings=1140,bound_frames=76955,
        unique_source_work=70871,unique_encoded_work=70871,stats=prod['stats'],resume_cache_hits=verification['resume']['encoded_cache_hits'],
        verification_reference=prefix+'/verification.json',runtime_reference=prefix+'/runtime.json',runtime_verification_reference=prefix+'/runtime-verification.json',
        previews_reference=prefix+'/previews.json',state='family-complete-native-available-produced-host-verified-installation-ingame-QA-pending',
        registry_version=7,SDF=False,installation=False,qa_ingame=False,release=False)
    path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
    assert not any(r['family']=='monster_icewind' for r in tracking['current_recipe_complete_productions'])
    preserved={k:v for k,v in tracking['queue_totals'].items() if 'installed' in k or 'ingame' in k}
    family=next(f for f in tracking['families'] if f['engine_section']=='monster_icewind');assert 'current_full_production' not in family
    family['current_full_production']={k:v for k,v in record.items() if k!='family'}
    family['native_available_scope']=dict(animation_ids=40,models=36,native_source_absent_animation_ids=gen['native_source_absent_animation_ids'],reference=prefix+'/selection.json',raw_source_inventory_unchanged=True)
    tracking['current_recipe_complete_productions'].append(record)
    assert tracking['queue_totals']['current_recipe_complete_animation_ids']==213
    tracking['queue_totals']['current_recipe_complete_animation_ids']=253;tracking['queue_totals']['current_recipe_complete_families']=14
    tracking['remaining_full_production_families']=[];tracking['recorded_on']='2026-10-06'
    assert preserved=={k:v for k,v in tracking['queue_totals'].items() if 'installed' in k or 'ingame' in k}
    csvpath=ROOT/'sprite/index/q3m-work-items.csv';raw=csvpath.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=0
    witnesses={w['animation_id']:w for w in prod['plan']['witnesses']}
    for line in lines[1:]:
        row=dict(zip(fields,next(csv.reader([line]))))
        if row['animation_id'] not in witnesses:out.append(line);continue
        assert row['engine_family']=='monster_icewind' and not row['q3m_v7_installation_reference']
        row.update(q3m_v7_full_production_reference=reference,queue_state='current-recipe-complete-native-produced-host-verified-installation-ingame-QA-pending',
            colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-produced-host-verified',q3m_final_work_count_known=str(witnesses[row['animation_id']]['encoded_work']))
        stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed+=1
    assert changed==40
    csvpath.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'));write_json(path,tracking)
    summary=ROOT/'sprite/SUIVI_Q3M.md';text=summary.read_text(encoding='utf-8');lines=text.splitlines()
    for i,line in enumerate(lines):
        if line.startswith('| `monster_icewind` |'):
            lines[i]='| `monster_icewind` | 40/132 natifs ; 44 avec préfixe | — | **Production native disponible complète V7 x2 améliorée sans SDF vérifiée sur hôte** : 36 modèles/40 IDs, 1 051 BAM/71 072 frames ; 70 871 encodages uniques. DLL candidate owner2 chargement/cycles ; installation/QA en attente. 88 absents +4 IDs au layout Monster exclus. |'
        elif line.startswith('- Character : **78 IDs V6 complets'):
            lines[i]=line.replace('291 IDs/14 familles produites','331 IDs/15 familles produites').replace('Monster reste production seule','Monster et Icewind restent production seule').replace('**Seul lot complet à produire : Icewind**, 40 modèles de base/44 IDs disponibles ; 88 IDs sans source exclus.','**Aucun lot natif disponible complet restant à produire.** Icewind : 36 modèles/40 IDs ; 88 absents et quatre IDs sans layout Icewind exclus.')
    position=lines.index('## Queue / références')+1
    lines[position:position]=['',f'- Icewind : **40 IDs/36 modèles produits**, 2 632 encodages acquis conservés, 64 511 guides historiques importés ; nouveaux calculs limités aux clés manquantes. [Production](../{prefix}/README.md). Total amélioré **253 IDs/14 familles**, recettes retenues Character V6 inclus **331 IDs/15 familles** ; installation/QA acquises inchangées.']
    summary.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(stage='tracking-complete',improved_ids=253,improved_families=14,selected_recipe_ids=331,selected_recipe_families=15,installed_or_QA_counts_unchanged=True,updated_rows=40)),flush=True)

if __name__=='__main__':main()
