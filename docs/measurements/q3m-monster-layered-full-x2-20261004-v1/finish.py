"""Record installed pending QA scope; keep all unrelated tracking/history bytes."""
import sys,json,csv,io,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');prod=load(HERE/'production.json');verification=load(HERE/'verification.json');proof=load(HERE/'catalog-proof.json');install=load(HERE/'installation-verification.json')
receipt=load(HERE/'ingame-installation/active-test.json');assert install['status']==receipt['status']=='installed-pending-ingame-qa'
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256'] and file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
baseline=load(HERE/'baseline.json')
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower()
for s in receipt['new_shards']:assert file_sha(game/s['registry']).upper()==s['sha256']
for f in receipt['fixtures']:assert file_sha(game/f['target'])==f['sha256']
# Re-run complete compositions through actual installed leaves/catalogue.
if '--resume-installed' in sys.argv:
    verified=load(HERE/'installed-native-verification.json');assert verified['passed'] and verified['catalog_sha256']==gen['catalog']['sha256'] and verified['dll_sha256']==gen['dll']['sha256'];installed_native=verified['native_composite']
else:
    p=subprocess.run([str(HERE/'composite_probe.exe'),str(game/'iee-assets/creature-sprites'),str(HERE/'work/composite.oracle')],capture_output=True,text=True,encoding='utf-8')
    (HERE/'native-installed.log').write_text(p.stdout+p.stderr,encoding='utf-8');assert p.returncode==0,(p.stdout[-1000:],p.stderr)
    installed_native=json.loads(next(s for s in reversed(p.stdout.splitlines()) if s.startswith('{')))
assert installed_native==verification['native_composite']
write_json(HERE/'installed-native-verification.json',dict(passed=True,native_composite=installed_native,catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],preserved_files=len(baseline['preserved']),new_shards=len(receipt['new_shards']),fixtures=len(receipt['fixtures']),ingame_QA=False,release=False))
reference=genpath='docs/measurements/'+HERE.name+'/current-generation.json';snapshot='docs/measurements/'+HERE.name+'/installation-verification.json'
track_path=ROOT/'sprite/index/q3m-work-tracking.json';track=load(track_path);family=next(f for f in track['families'] if f['engine_section']=='monster_layered')
summary_before=dict(track['queue_totals']);assert summary_before['current_recipe_complete_families']==8 and summary_before['current_recipe_complete_animation_ids']==66 and summary_before['current_recipe_ingame_accepted_animation_ids']==65
family['current_colour_witness']['state']='installed-via-complete-family-ingame-pending'
family['current_colour_witness']['installation_reference']=snapshot
family['source_dedup']['remaining_gpu_work']=0
family['current_full_production']=dict(reference=reference,selection='docs/measurements/'+HERE.name+'/selection.json',animation_ids=gen['animation_ids'],native_kinds=[0,1],bams=[r for w in prod['plan']['witnesses'] for r in w['refs']],physical_resources=65,physical_frames=6422,unique_source_work=prod['plan']['unique_source_work'],unique_encoded_work=prod['plan']['unique_encoded_work'],encoded_cache_hits=prod['stats']['encoded_cache_hits'],new_encoded_work=prod['stats']['new_encoded_work'],special_work=prod['stats']['special_work'],new_neural_targets=prod['stats']['new_neural_targets'],resume_cache_hits=verification['resume']['encoded_cache_hits'],scope='complete-native-world-body-each-weapon-all-cycles-directions; native uncycled auxiliary preserved; MSIRG2BE orphan excluded',excluded_non_native_refs=['MSIRG2BE'],runtime_reference=gen['runtime']['path'],installation_reference='docs/measurements/'+HERE.name+'/ingame-installation/active-test.json',installation_snapshot=snapshot,state='family-complete-produced-installed-ingame-QA-pending',registry_version=7,SDF=False,qa_ingame=False,release=False)
family['state']='family-complete-produced-installed-ingame-QA-pending'
family['current_installation']=dict(state='installed-ingame-pending',reference=snapshot,receipt=family['current_full_production']['installation_reference'],catalogue_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],animation_ids=gen['animation_ids'],SDF=False,qa_ingame=False)
track['queue_totals'].update(current_recipe_complete_families=9,current_recipe_complete_animation_ids=73,current_recipe_installed_animation_ids=73)
track['engine_integration']['installed_candidate_reference']=reference
track['engine_integration']['latest_installation_verification_reference']=snapshot
track['colour_variants']['state']+='-Monster_layered-V7-no-SDF-installed-ingame-pending'
write_json(track_path,track)
csv_path=ROOT/'sprite/index/q3m-work-items.csv';lines=csv_path.read_bytes().decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));output=[lines[0]];byid={w['animation_id']:w for w in prod['plan']['witnesses']};changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in byid:output.append(line);continue
    row.update(queue_state='q3m-v7-full-produced-installed-ingame-pending',colour_variant_state='v7-full-layered-no-SDF-x2-installed-ingame-pending',q3m_v7_full_production_reference=reference,q3m_v7_installation_reference=family['current_full_production']['installation_reference'],q3m_final_work_count_known=str(byid[row['animation_id']]['encoded_work']))
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n');writer.writerow(row);output.append(stream.getvalue());changed.append(row['animation_id'])
assert len(changed)==7;raw=csv_path.read_bytes();prefix=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'';csv_path.write_bytes(prefix+''.join(output).encode('utf-8'))
p=ROOT/'sprite/SUIVI_Q3M.md';t=p.read_text(encoding='utf-8');t=t.replace('| `monster_layered` | 7/7 | — | Corps et armes superposées ; sous-types `2000` et `8000` à conserver séparément. Sirines, ogres mages, gnolls, hobgobelins, kobolds. |','| `monster_layered` | 7/7 | — | **Famille complète Q3m V7 x2 palette améliorée sans SDF installée, QA en attente** ; 65 BAM utiles/6 422 frames, sept modèles, corps/armes, deux chemins natifs. MSIRG2BE orphelin exclu. |')
t=t.replace('66 IDs /8 familles disponibles complètes installées','73 IDs /9 familles disponibles complètes installées')
t+='\n- Monster_layered **complet installé, QA ingame en attente** : `../docs/measurements/'+HERE.name+'/README.md`, sept IDs/modèles, 65 BAM/6 422 frames ; 5 757 encodages uniques, 276 hits acquis, 5 479 nouveaux +deux spéciaux. Quatre feuilles Volo identiques au pilote local acquis ; 65 feuilles ajoutées au catalogue installé, où le pilote était absent. MSIRG2BE orphelin conservé hors runtime, aucun BAM source modifié. Hook ajouté au type2000 (`5aa840/32f3b0`), type8000 (`5aa650/32ee90`) déjà couvert ; association de la proposition corrigée par fabrique native. Neuf familles/73 IDs complets installés ; sept familles/65 IDs acceptés conservés.\n'
p.write_text(t,encoding='utf-8')
p=ROOT/'sprite/index/README.md';t=p.read_text(encoding='utf-8');t+='\n- Monster_layered **complet produit/installé, QA ingame en attente** : [run](../../docs/measurements/'+HERE.name+'/README.md), [sept CLUA](../../docs/measurements/'+HERE.name+'/CLUA.txt). Sept modèles, 65 BAM/6 422 frames Q3m V7 x2 palette améliorée sans SDF ; 65 feuilles ajoutées au catalogue, dont quatre Volo identiques au pilote local acquis. Sirine MSIRG2BE orphelin exclu ; hook type2000 ajouté, type8000 déjà couvert. Neuf familles/73 IDs complets installés, sept familles/65 IDs acceptés inchangés.\n';p.write_text(t,encoding='utf-8')
readme=f'''# Monster_layered complet — Q3m x2 palette améliorée, sans SDF

- État : **produit/installé ; QA ingame en attente**, pas de release. Sept IDs/modèles2000/2100/2200/2300/8000/8100/8200 ; toutes frames/cycles/centres, corps +chaque arme.
- Source utile : **65 BAM/6 422frames/5 757identités**. Cache276 ; nouveaux5 479encodages +deux spéciaux sans inférence ; cibles neuves{prod['stats']['new_neural_targets']}. Aucun modèle partagé ; UVOLMG2/MG2E doublon de pixels, deux bindings conservés.
- `MSIRG2BE` : orphelin90frames, dont30 hauteur0. Native EquipWeapon=`prefix+weapon[0]+G1/G2/G1E/G2E` →MSIRBG2E ; pas MSIRG2BE. Source inchangée ; aucun pixel/geometrie inventé. `native-routes.json`, `weapon-bindings.asm`.
- Correction de l'association dans la proposition : fabrique330DD4/type2000→ctor3119A0/vtable5AA840/render32F3B0 ; type8000→ctor311300/vtable5AA650/render32EE90, déjà couvert. Nouveau hook owner8/composite +tableaux10. `factory-native.asm`, `runtime-delta.patch` ; préfixe32octets pinné.
- DLL : base installée16b01e52 +acquis V9 kind1 +seul delta hook. CPP lecteur410acf6a…569b0 identique au parent ; aucun Character V10 en stock activé, shaders/INI inchangés.
- Catalogue : parent147IDs/6 688ressources/1 686 325frames ; actif{proof['active_animations']}IDs/{proof['active_resources']}ressources/{proof['active_frames']}frames/{proof['active_routes']}routes. Quatre Volo SHA identiques au pilote local acquis, absent du parent installé ; **65feuilles ajoutées**, anciens composants/routes préservés.
- Tests : toutes6 422frames feuilles/cache/profils/référents/géométrie/cycles sans SDF ; native K6×3encodages, isolé/combiné ; {verification['native_composite']['native_composites']}compositions/{verification['native_composite']['resolved_layers']}couches, zéro couche absente ; Ankheg V9 hérité ; mêmes compositions relues au chemin installé. Auxiliaires non cyclés : {verification['auxiliary_uncycled_resources']}, {verification['auxiliary_frames_cache_verified']}frames cache vérifiées.
- Installation : {len(receipt['new_shards'])}feuilles +catalogue +DLL +Volo QLYR2100 dérivé ENDVOLO sans scripts/dialogue. **{len(baseline['preserved'])}fichiers acquis SHA préservés**, sauvegardes `work/before`. Jeu/InfinityLoader fermés ; sources BAM/INI et CRE stock conservés. `install.ps1`, `restore.ps1`.
- Autorités distinctes : `current-generation.json`, `production.json`, `verification.json`, `runtime.json`, `ingame-installation/active-test.json`, `installation-verification.json`, `installed-native-verification.json`. Validation utilisateur non déduite. Comparatif `comparison.png`, tests `CLUA.txt`, consommateurs stock `creatures.json`.

```powershell
& 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe' docs/measurements/{HERE.name}/verify.py
```
'''
(HERE/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps(dict(installed=True,changed_CSV_ids=changed,accepted_families=7,accepted_ids=65,complete_families=9,complete_ids=73,preserved=len(baseline['preserved']))),flush=True)
