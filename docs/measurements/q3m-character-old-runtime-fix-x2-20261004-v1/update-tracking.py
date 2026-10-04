"""Point only Character_old production/installation to the dependency correction; no QA acceptance."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');installed=load(HERE/'installation-verification.json');verified=load(HERE/'verification.json');prod=load(HERE/'production.json')
assert installed['status']=='installed-pending-ingame-qa' and installed['catalog_sha256']==gen['catalog']['sha256']
ref=HERE.relative_to(ROOT).as_posix();p=ROOT/'sprite/index/q3m-work-tracking.json';data=load(p)
entry=next(x for x in data['current_recipe_complete_productions'] if x['family']=='character_old')
old=dict(entry);entry.update(reference=ref+'/current-generation.json',body_production_reference=old['reference'],
    native_dependencies_reference=ref+'/dependencies.json',installation_reference=ref+'/ingame-installation/active-test.json',installation_snapshot=ref+'/installation-verification.json',
    body_resources=99,body_physical_frames=4725,resources=1066,physical_frames=49394,additional_resources=967,additional_frames=44669,
    logical_resource_bindings=121+verified['registered_dependency_bindings'],logical_bound_frames=5661+verified['logical_dependency_bound_frames'],shared_resource_bindings=121+verified['registered_dependency_bindings']-1066,body_shared_resource_bindings=22,unique_source_work=verified['unique_source_work_complete_family'],unique_encoded_work=verified['unique_encoded_work_complete_family'],
    dependency_unique_encoded_work=18576,dependency_production_stats=prod['stats'],runtime_fix='native-shadow-and-equipment-registered',
    state='family-complete-with-native-dependencies-installed-ingame-pending',qa_ingame=False,release=False,SDF=False)
family=next(f for f in data['families'] if f['engine_section']=='character_old');family['current_full_production']=entry
data['engine_integration']['latest_installation_verification_reference']=entry['installation_snapshot'];write_json(p,data)
p=ROOT/'sprite/index/q3m-work-items.csv'
with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
for r in rows:
    if r['animation_id'] in gen['animation_ids']:
        r['q3m_v7_full_production_reference']=entry['reference'];r['q3m_v7_installation_reference']=entry['installation_snapshot']
        r['q3m_final_work_count_known']=str(verified['unique_encoded_work_by_animation'][r['animation_id']])
with p.open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
p=ROOT/'sprite/SUIVI_Q3M.md';s=p.read_text(encoding='utf-8')
s=s.replace('sept IDs/six ensembles/99 BAM/4 725 frames ; cinq corps visibles, gardes funestes natifs transparents ; XHFF absent. QA ingame en attente.',
    'sept IDs/six ensembles/99 BAM corps/4 725 frames, **967 BAM dépendances natives ajoutés** (ombres + équipement ancien) ; cinq corps visibles, gardes natifs transparents ; XHFF absent. Correction du fallback vanilla installée, QA ingame en attente.')
s+=f'\n## Character_old : correction des dépendances natives — 2026-10-04\n\n- Symptôme confirmé : session 16:19:52–16:20:23, `CSHDG1` absent → composition incomplète → vanilla pour 6400/6401/6403. Première installation non validée ; corps acquis conservés.\n- Delta : 33 CSHD +15 SSHD +919 WPM =967 BAM/44 669 frames/18 576 travaux encodés uniques, Q3m V7 K6 x2, sans SDF ; 4 775 liaisons ajoutées aux seuls sept IDs. Corps 99 BAM/4 725 frames inchangés. Famille : 1 066 BAM/49 394 frames physiques.\n- [Production/installation corrective](../{ref}/README.md), `verification.json` : oracle natif toutes frames nouvelles + compositions corps/ombre/arme/bouclier/casque, séquence16/slot31 et voisins. DLL/INI/shaders/autres familles conservés. QA ingame en attente ; compte accepted inchangé ; release inchangée.\n'
p.write_text(s,encoding='utf-8')
p=ROOT/'sprite/index/README.md';s=p.read_text(encoding='utf-8');s+=f'\n- Character_old : [correction du fallback vanilla](../../{ref}/README.md), ombres/équipements natifs Q3m V7 x2 ajoutés ; référence courante `{ref}/current-generation.json`. Corps conservés ; QA ingame en attente.\n';p.write_text(s,encoding='utf-8')
p=ROOT/'.gitattributes';s=p.read_text(encoding='utf-8');line=ref+'/** -text';s+='\n# Character_old dependency correction proofs pin raw bytes.\n'+line+'\n';p.write_text(s,encoding='utf-8')
print(json.dumps(dict(state=entry['state'],catalog=gen['catalog']['sha256'],qa_ingame=False)))
