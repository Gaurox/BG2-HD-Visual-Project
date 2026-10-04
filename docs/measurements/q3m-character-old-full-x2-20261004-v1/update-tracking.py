"""Record Character_old production/installation only; preserve acquired QA and unrelated edits."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
ref=HERE.relative_to(ROOT).as_posix()
prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');installed=load(HERE/'installation-verification.json');creatures=load(HERE/'creatures.json')
assert installed['status']=='installed-pending-ingame-qa' and installed['catalog_sha256']==gen['catalog']['sha256']
entry=dict(family='character_old',reference=ref+'/current-generation.json',selection=ref+'/selection.json',
    animation_ids=gen['animation_ids'],source_absent_animation_ids=gen['source_absent_animation_ids'],
    models=6,visible_body_models=5,resources=99,physical_frames=4725,logical_resource_bindings=121,logical_bound_frames=5661,
    shared_resource_bindings=22,unique_source_work=3771,unique_encoded_work=3771,
    **prod['stats'],resume_cache_hits=prod['resume']['encoded_cache_hits'],
    transparent_native_guard_ids=['0x6405','0x6406'],transparent_native_guard_physical_frames=936,
    installation_reference=ref+'/ingame-installation/active-test.json',installation_snapshot=ref+'/installation-verification.json',
    state='family-complete-available-produced-installed-ingame-pending',qa_ingame=False,release=False,SDF=False)
p=ROOT/'sprite/index/q3m-work-tracking.json';d=load(p)
family=next(f for f in d['families'] if f['engine_section']=='character_old')
assert 'current_full_production' not in family and not any(x['family']=='character_old' for x in d['current_recipe_complete_productions'])
family['current_full_production']=entry;d['current_recipe_complete_productions'].append(entry)
d['engine_integration']['latest_installation_verification_reference']=entry['installation_snapshot']
d['queue_totals'].update(current_recipe_complete_animation_ids=66,current_recipe_complete_families=8,current_recipe_installed_animation_ids=66)
assert d['queue_totals']['current_recipe_ingame_accepted_families']==6 and d['queue_totals']['current_recipe_ingame_accepted_animation_ids']==58
d['colour_variants']['state']=d['colour_variants']['state'].replace('-other-families-pilot','-Character_old-V7-no-SDF-installed-other-families-pilot')
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
p=ROOT/'sprite/index/q3m-work-items.csv'
with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
work={w['animation_id']:w['encoded_work'] for w in prod['plan']['witnesses']};changed=[]
for r in rows:
    if r['animation_id'] not in gen['animation_ids']:continue
    assert r['engine_family']=='character_old'
    r.update(queue_state='current-recipe-complete-installed-ingame-pending',colour_variant_state='v7-full-x2-no-SDF-installed-ingame-pending',
        q3m_final_work_count_known=str(work[r['animation_id']]),q3m_v7_full_production_reference=entry['reference'],
        q3m_v7_installation_reference=entry['installation_snapshot']);changed.append(r['animation_id'])
assert len(rows)==465 and set(changed)==set(gen['animation_ids'])
with p.open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
p=ROOT/'sprite/SUIVI_Q3M.md';s=p.read_text(encoding='utf-8')
s=s.replace('| `character_old` | 7/8 | — | Avatars anciens/spéciaux, contrat distinct de Character ; Drizzt, Elminster, Sarevok. |',
    '| `character_old` | 7/8 | — | **Famille disponible complète Q3m V7 x2 améliorée sans SDF installée**, sept IDs/six ensembles/99 BAM/4 725 frames ; cinq corps visibles, gardes funestes natifs transparents ; XHFF absent. QA ingame en attente. |')
s=s.replace('59 IDs /7 familles disponibles complètes installées','66 IDs /8 familles disponibles complètes installées')
s+='\n## Character_old : famille complète disponible installée — 2026-10-04\n\n'
s+=f'- Demande utilisateur « go et installe » : **sept IDs/six ensembles/99 BAM/4 725 frames physiques**, Q3m V7 K6 x2/quatre partenaires/huit niveaux, palette améliorée live/CatmullRom, **sans SDF** ; owner6, profils8/9 règle3. Drizzt/Elminster/moine/squelette/Sarevok ; gardes funestes6405/6406 partagent22BAM/936frames transparents source ; 6621/XHFF sans BAM exclu. `../{ref}/current-generation.json`.\n'
s+=f"- 3 771 travaux uniques =288 hits acquis SHA identiques +{prod['stats'].get('new_encoded_work',0)} encodages nouveaux +{prod['stats'].get('special_work',0)} travaux spéciaux ; {prod['stats'].get('new_neural_targets',0)} cibles nouvelles/{prod['stats'].get('target_cache_hits',0)} hits cibles ; reprise3 771 hits sans Torch. 954 répétitions entre BAM distincts ; alias gardes22feuilles partagé, 121bindings/5 661frames liées.\n"
s+=f"- Native monde isolé/combiné :120bindings/5 659frames/{installed['native_combined_test']['native_cycle_slots']}slots, K6 ×trois formats ; CMNKINV auxiliaire/deuxframes/cycle source vide vérifié directement feuille/cache ; couverture totale99BAM/4 725frames physiques, 121bindings/5 661frames liées. Géométries/cycles/profils/représentants conservés, alias exacts, gardes I/F zéro, aucun plan S/M/A. Comparatif six ensembles inspecté ; **QA utilisateur en attente**.\n"
s+=f"- Installation `../{ref}/installation-verification.json` :99feuilles +catalogue +deux témoins QCOL6405/QCOL6406 ; **211 fichiers acquis SHA identiques**, 140IDs/50 356routes/4 670composants hérités identiques ; Ambient accepté/chevalv3/Town_static/Ankheg/Large16/Flying préservés. DLL/shaders/INI inchangés ; actif147IDs/4 769ressources/1 597 856frames/50 477routes, catalogue `{gen['catalog']['sha256']}`.\n"
s+=f"- {creatures['stock_or_override_consumer_count']}CRE consommateurs ; sept CLUA `../{ref}/CLUA-generiques.txt`, deux témoins dérivés ARNMAN01, animation0x28 modifiée et cinq scripts/dialogue vidés ; autres octets conservés. Restore dédié vers le parent Ambient accepté. Huit familles/66 IDs installés, six familles/58 IDs acceptés ; aucune release ni commit à cette étape.\n"
p.write_text(s,encoding='utf-8')
p=ROOT/'sprite/index/README.md';s=p.read_text(encoding='utf-8')
s+=f'\n- Character_old **famille disponible complète produite et installée**, sept IDs/six ensembles/99 BAM/4 725 frames, Q3m V7 K6 x2 amélioré sans SDF ; [production/installation](../../{ref}/README.md), [sept CLUA](../../{ref}/CLUA-generiques.txt). Drizzt/Elminster/moine/squelette/Sarevok et deux gardes partageant un corps natif transparent ; XHFF sans BAM exclu. Huit familles/66 IDs installés ; QA ingame en attente, six familles/58 IDs acceptés conservés.\n'
p.write_text(s,encoding='utf-8')
p=ROOT/'.gitattributes';s=p.read_text(encoding='utf-8');line=ref+'/** -text -whitespace'
if line not in s:p.write_text(s+'\n# Character_old final production/native/installation identities pin raw bytes.\n'+line+'\n',encoding='utf-8')
print(json.dumps(dict(installed_families=8,installed_ids=66,accepted_families=6,accepted_ids=58,csv_changed=changed)))
