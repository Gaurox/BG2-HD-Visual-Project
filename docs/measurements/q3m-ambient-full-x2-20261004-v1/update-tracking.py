"""Record only the new Ambient production/installation; user QA remains pending."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
ref=HERE.relative_to(ROOT).as_posix()
prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');installed=load(HERE/'installation-verification.json')
assert installed['status']=='installed-pending-ingame-qa' and installed['catalog_sha256']==gen['catalog']['sha256']
entry=dict(family='ambient',reference=ref+'/current-generation.json',selection=ref+'/selection.json',
    animation_ids=gen['animation_ids'],source_absent_animation_ids=gen['source_absent_animation_ids'],
    models=16,resources=34,physical_frames=2580,logical_resource_bindings=39,logical_bound_frames=2734,
    shared_resource_bindings=5,unique_source_work=2406,unique_encoded_work=2406,
    **prod['stats'],resume_cache_hits=prod['resume']['encoded_cache_hits'],
    installation_reference=ref+'/ingame-installation/active-test.json',installation_snapshot=ref+'/installation-verification.json',
    state='family-complete-available-produced-installed-ingame-pending',qa_ingame=False,release=False,SDF=False)
p=ROOT/'sprite/index/q3m-work-tracking.json';d=load(p)
family=next(f for f in d['families'] if f['engine_section']=='ambient')
assert 'current_full_production' not in family and not any(x['family']=='ambient' for x in d['current_recipe_complete_productions'])
family['current_full_production']=entry;d['current_recipe_complete_productions'].append(entry)
d['engine_integration']['latest_installation_verification_reference']=entry['installation_snapshot']
d['queue_totals'].update(current_recipe_complete_animation_ids=59,current_recipe_complete_families=7,current_recipe_installed_animation_ids=59)
assert d['queue_totals']['current_recipe_ingame_accepted_families']==5 and d['queue_totals']['current_recipe_ingame_accepted_animation_ids']==40
d['colour_variants']['state']=d['colour_variants']['state'].replace('-other-families-pilot','-Ambient-V7-no-SDF-installed-other-families-pilot')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'sprite/index/q3m-work-items.csv'
with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
work={w['animation_id']:w['encoded_work'] for w in prod['plan']['witnesses']};changed=[]
for r in rows:
    if r['animation_id'] not in gen['animation_ids']:continue
    assert r['engine_family']=='ambient'
    r.update(queue_state='current-recipe-complete-installed-ingame-pending',colour_variant_state='v7-full-x2-no-SDF-installed-ingame-pending',
        q3m_final_work_count_known=str(work[r['animation_id']]),q3m_v7_full_production_reference=entry['reference'],
        q3m_v7_installation_reference=entry['installation_snapshot']);changed.append(r['animation_id'])
assert len(rows)==465 and set(changed)==set(gen['animation_ids'])
with p.open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
p=ROOT/'sprite/SUIVI_Q3M.md';s=p.read_text(encoding='utf-8')
s=s.replace('| `ambient` | 18/21 | — | Animations ambiantes mobiles ; chats, rats, poules, écureuils, figurants. |',
    '| `ambient` | 18/21 | — | **Famille disponible complète Q3m V7 x2 améliorée sans SDF installée**, 18 IDs/16 modèles/34 BAM/2 580 frames ; QA ingame en attente. KEG1/2/3 sans BAM. |')
s=s.replace('41 IDs /6 familles disponibles complètes installées','59 IDs /7 familles disponibles complètes installées')
s+='\n## Ambient : famille complète disponible installée — 2026-10-04\n\n'
s+=f'- Demande utilisateur « ok go » : **18 IDs/16 modèles/34 BAM/2 580 frames physiques distinctes**, Q3m V7 K6 x2/quatre partenaires/huit niveaux, palettes améliorées live, CatmullRom, **sans SDF** ; owner12, profils8/9 règle3. KEG1/2/3 (CC00/CC01/CC02) sans BAM, exclus. `../{ref}/current-generation.json`.\n'
s+=f"- Travail réel : 2 406 encodages uniques =1 024 hits acquis SHA identiques +{prod['stats'].get('new_encoded_work',0)} nouveaux encodages +{prod['stats'].get('special_work',0)} frame spéciale ; {prod['stats'].get('new_neural_targets',0)} cibles ; reprise 2 406 hits sans Torch. Chauve-souris C000/C500 et rat C300/CC04 partagent cinq feuilles : 39 bindings/2 734 frames liées, aucune duplication physique ; 174 répétitions entre BAM distincts.\n"
s+=f"- Tests natifs isolé/combiné : 39 bindings/2 734 frames/{installed['native_combined_test']['native_cycle_slots']} slots, K6 ×trois formats ; cycles/centres/profils/représentants source préservés, alias exacts, plans S/M/A absents ; comparatif16modèles inspecté, aucune QA ingame déduite.\n"
s+=f"- Installation `../{ref}/installation-verification.json` : 34 feuilles +catalogue +un CRE témoin QAMBCC04 ; **176 fichiers acquis préservés SHA**, 122 IDs/50 317 routes/4 636 composants hérités identiques ; Town_static accepté, cheval v3, Ankheg/Large16/Flying conservés. DLL/shaders/INI inchangés ; actif140IDs/4 670ressources/1 593 131frames/50 356routes, SHA catalogue `{gen['catalog']['sha256']}`.\n"
s+=f'- 571 CRE consommateurs ; 18 commandes `../{ref}/CLUA-generiques.txt`, témoins/census `creatures.json` ; restauration dédiée vers le parent Town_static accepté. **QA utilisateur en attente** ; sept familles/59 IDs installés, cinq familles/40 IDs acceptés ; aucune release ni commit à cette étape.\n'
p.write_text(s,encoding='utf-8')
p=ROOT/'sprite/index/README.md';s=p.read_text(encoding='utf-8')
s+=f'\n- Ambient **famille disponible complète produite et installée**, 18 IDs/16 modèles/34 BAM/2 580 frames physiques, Q3m V7 K6 x2 amélioré sans SDF ; [production/installation](../../{ref}/README.md), [18 CLUA](../../{ref}/CLUA-generiques.txt). Chauve-souris/rat intérieur et extérieur partagés ; 1 024 hits acquis, 1 382 nouveaux travaux dont une frame spéciale. Sept familles/59 IDs installés ; QA ingame en attente, cinq familles/40 IDs acceptés conservés.\n'
p.write_text(s,encoding='utf-8')
p=ROOT/'.gitattributes';s=p.read_text(encoding='utf-8');line=ref+'/** -text -whitespace'
if line not in s:p.write_text(s+'\n# Ambient native/production/installation identities pin raw evidence bytes.\n'+line+'\n',encoding='utf-8')
print(json.dumps(dict(installed_families=7,installed_ids=59,accepted_families=5,accepted_ids=40,csv_changed=changed)))
