"""Record the active SDF candidate without replacing accepted V7 QA or production."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;REF=HERE.relative_to(ROOT).as_posix()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=read(HERE/'ingame-installation/active-test.json');snapshot=read(HERE/'installation-verification.json');production=read(HERE/'production.json');generation=read(HERE/'current-generation.json')
assert receipt['status']=='installed-pending-ingame-qa'
assert sha(HERE/'ingame-installation/active-test.json').upper()==snapshot['installation_receipt_sha256']
game=Path(read(ROOT/'config/workspace-paths.local.json')['paths']['bg2ee_game_root'])
for relative,expected in [(receipt['catalog_relative'],receipt['catalog_sha256']),('InfinityEngine-Enhancer.dll',receipt['dll_sha256'])]+[(i['registry'],i['sha256']) for i in receipt['new_shards']]+[(i['relative_path'],i['sha256']) for i in receipt['preserved_files']]:assert sha(game/relative)==expected.lower(),relative
record=dict(family='monster_large16',reference=f'{REF}/current-generation.json',production_reference=f'{REF}/production.json',installation_reference=f'{REF}/ingame-installation/active-test.json',installation_snapshot=f'{REF}/installation-verification.json',runtime_reference=f'{REF}/runtime.json',scope='complete available Large16 world only; INV remains accepted V7',animation_ids=generation['animation_ids'],resources=18,physical_frames=1688,registry_version=9,colour_profile=8,decode_rule=3,world_filter='CatmullRom',recipe=production['recipe'],stats=production['stats'],state='SDF-trial-metadata-wait-installed-ingame-pending',qa_ingame=False,qa_state='pending',release=False,restore_script=f'{REF}/restore.ps1',original_Q3m_reference='docs/measurements/q3m-monster-large16-full-x2-20261004-v1/current-generation.json',native_Q3m_planes_unchanged=True,metadata_wait=read(HERE/'runtime.json')['capability_delta']['Large16_cold_resolution'])
path=ROOT/'sprite/index/q3m-work-tracking.json';d=read(path);assert not any(t['family']=='monster_large16' for t in d['current_contour_trials'])
d['current_contour_trials'].append(record);next(f for f in d['families'] if f['engine_section']=='monster_large16')['current_contour_trials']=[record]
for key in ['installed_candidate_reference','latest_installation_verification_reference']:d['engine_integration'][key]=record['installation_snapshot']
assert d['queue_totals']['current_recipe_ingame_accepted_families']==3 and d['queue_totals']['current_recipe_ingame_accepted_animation_ids']==9
path.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=ROOT/'sprite/SUIVI_Q3M.md';text=path.read_text(encoding='utf-8')
text=text.replace('catalogue enrichi Large16 **`6fbb2f02…44c80`**','catalogue Large16 SDF **`e23ccdc6…22a43`**')
text=text.replace('DLL `0bdaf3b6…e4d5`, catalogue Large16 SDF',f"DLL `{generation['dll']['sha256'][:8]}…{generation['dll']['sha256'][-4:]}` (base stable + attente Large16), catalogue Large16 SDF")
text=text.replace('autres familles restent NonBlocking. Généralisation', 'Large16 A000/A100/A200 owner11 possède désormais sa propre attente, autres familles restent NonBlocking. Généralisation')
text+=f'\n## Large16 : SDF installé après validation V7\n\n- **V7 sans SDF accepté, commit `9856d78d`** ; QA conservée, trois familles/neuf IDs acceptés.\n- **Actif Large16 : essai V9 SDF x2, QA en attente**, `../{REF}/README.md` ; trois IDs, 18 BAM monde/1 688 frames, deux INV/four frames V7 conservés. Couleurs I/F/deps/profil restaurables V7 byte-identiques.\n- 1 508 masques uniques /180 hits /zéro inférence ou encodage Q3m ; sonde native complète/GPU24vues ; 18/18 premiers accès HD sans miss, attente max96,0796ms.\n- DLL base `16b01e52` + attente Large16 owner11/IDs exacts≤5s ; Character V10 en stock non activé. Shaders/INI/exe/UI/Ankheg/CREblanc/V7 acquis :119fichiers identiques ; toutes50 273routes conservées. Installation et QA restent distinctes.\n- Restore de cet essai → V7 validé, même CREblanc. Mêmes CLUA WYVBAB01/CARCRA01/QMWYVW01 ; gameplay/rotations/mort à tester ingame.\n'
path.write_text(text,encoding='utf-8')
with (ROOT/'sprite/index/README.md').open('a',encoding='utf-8') as out:out.write(f'\n- Large16 SDF actif : `../../{REF}/README.md`, dix-huit feuilles monde/1 688frames, QA en attente. V7 sans SDF reste accepté ; CSV décrit cet acquis V7, essai actif référencé dans `current_contour_trials`.\n')
print(json.dumps(dict(installed_verified=True,SDF=True,preserved=len(receipt['preserved_files']),QA='pending',accepted_V7_commit='9856d78d')))
