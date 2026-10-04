"""Record targeted SDF override; retain seven-ID base production and immutable QA decisions."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');installation=load(HERE/'installation-verification.json');assert installation['status']=='installed-pending-ingame-qa'
ref=HERE.relative_to(ROOT).as_posix();p=ROOT/'sprite/index/q3m-work-tracking.json';data=load(p)
override=dict(animation_ids=gen['animation_ids'],reference=ref+'/current-generation.json',installation_reference=ref+'/ingame-installation/active-test.json',installation_snapshot=ref+'/installation-verification.json',resources=974,physical_frames=44736,SDF=True,registry_version=9,transparent_native_body=True,state='two-native-guards-SDF-installed-ingame-pending',qa_ingame=False,release=False)
for entry in [next(e for e in data['current_recipe_complete_productions'] if e['family']=='character_old'),next(e for e in data['families'] if e['engine_section']=='character_old')['current_full_production']]:
    entry['per_animation_overrides']=[override];entry['SDF_animation_ids']=gen['animation_ids'];entry['active_catalog_reference']=gen['catalog']['path'];entry['active_runtime_reference']=ref+'/runtime.json';entry['SDF_scope']='only-0x6405-0x6406; other-five-retain-V7'
data['engine_integration']['latest_installation_verification_reference']=ref+'/installation-verification.json';write_json(p,data)
p=ROOT/'sprite/index/q3m-work-items.csv'
with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
for r in rows:
    if r['animation_id'] in gen['animation_ids']:
        r['q3m_v7_full_production_reference']=ref+'/current-generation.json';r['q3m_v7_installation_reference']=ref+'/installation-verification.json';r['colour_variant_state']='v9-full-x2-SDF-installed-ingame-pending'
with p.open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
p=ROOT/'sprite/SUIVI_Q3M.md';s=p.read_text(encoding='utf-8');s+=f'\n## Gardes 6405/6406 : SDF ciblé — 2026-10-04\n\n- Demande SDF sur QCOL6405/QCOL6406 ; **974 BAM/44 736 frames physiques partagés** : 22 MDGU +33 CSHD +919 WPM. V9 profiles8/9 règle3, x2/CatmullRom ; I/F/couleurs/géométries/cycles acquis identiques, zéro nouvelle inférence. Corps natifs936frames entièrement transparents ; SDF ne crée aucun corps.\n- 33 routes CSHD ajoutées par ID : INI `shadow=` vide utilise néanmoins CSHD en jeu ; parent manque deux liaisons CSHDG1, nouveau complet. 952 feuilles partagées clonées pour seuls deux IDs ; cinq autres Character_old et145IDs/routes héritées conservés. Actif6 688ressources/1 686 325frames/55 318routes.\n- [Run/installation](../{ref}/README.md) ; DLL stable16b01e52 +seul support V9 native-kind1 ; hooks/shaders/INI/CRE inchangés. Oracle natif K6×3 toutes frames/slots, compositions avec/sans équipement et40vues GPU passés ; Ankheg V9 préservé. QA utilisateur en attente, aucun nouvel accepted ni release.\n';p.write_text(s,encoding='utf-8')
p=ROOT/'sprite/index/README.md';s=p.read_text(encoding='utf-8');s+=f'\n- Override SDF **6405/6406 seulement** : [run](../../{ref}/README.md), 974 BAM partagés, CSHD ajouté ; corps natifs transparents conservés. Cinq autres Character_old restent V7 sans SDF ; QA ingame en attente.\n';p.write_text(s,encoding='utf-8')
p=ROOT/'.gitattributes';s=p.read_text(encoding='utf-8');s+='\n# Targeted native Doom Guard V9 SDF proofs pin raw bytes.\n'+ref+'/** -text -whitespace\n';p.write_text(s,encoding='utf-8')
print(json.dumps(dict(SDF_ids=gen['animation_ids'],QA=False)))
