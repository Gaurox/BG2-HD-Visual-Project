"""Record installed MultiNew, keep MonsterOld/visual QA pending, no release."""
import csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');prod=load(HERE/'production.json');verification=load(HERE/'verification.json');receipt=load(HERE/'ingame-installation/active-test.json');baseline=load(HERE/'baseline.json')
assert receipt['status']=='installed-pending-ingame-qa' and verification['passed']
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower()
for s in receipt['new_shards']:assert file_sha(game/s['registry']).upper()==s['sha256']
for f in receipt['fixtures']:assert file_sha(game/f['target'])==f['sha256']
write_json(HERE/'installed-native-verification.json',dict(passed=True,catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],DLL_unchanged=True,preserved_files=len(baseline['preserved']),resources=gen['resources'],frames=gen['frames'],logical_resource_bindings=5155,bound_frames=519867,fixtures=10,native_world=verification['native_world']['combined'],native_composite=verification['native_composite'],ingame_QA=False,release=False))
reference='docs/measurements/'+HERE.name+'/current-generation.json';snapshot='docs/measurements/'+HERE.name+'/installation-verification.json';receiptref='docs/measurements/'+HERE.name+'/ingame-installation/active-test.json'
p=ROOT/'sprite/index/q3m-work-tracking.json';track=load(p);family=next(f for f in track['families'] if f['engine_section']=='multi_new');totals=track['queue_totals']
assert totals['current_recipe_complete_families']==11 and totals['current_recipe_installed_animation_ids']==126 and totals['current_recipe_ingame_accepted_animation_ids']==79
family['current_colour_witness'].update(state='installed-via-complete-native-palette-family-ingame-pending',installation_reference=snapshot)
family['source_dedup']['remaining_gpu_work']=0
family['current_full_production']=dict(reference=reference,selection='docs/measurements/'+HERE.name+'/selection.json',animation_ids=gen['animation_ids'],source_absent_animation_ids=[],models=4,colour_variants=10,physical_resources=gen['resources'],physical_frames=gen['frames'],logical_resource_bindings=5155,bound_frames=519867,unique_native_BAM=1753,original_native_frames=191817,unique_original_source_work=17103,unique_source_work=prod['plan']['unique_source_work'],unique_encoded_work=42772,stats=prod['stats'],multipart_context=prod['multipart_context'],resume_cache_hits=42772,runtime_reference=gen['runtime']['path'],installation_reference=receiptref,installation_snapshot=snapshot,state='family-complete-produced-installed-ingame-QA-pending',registry_version=7,SDF=False,qa_ingame=False,release=False)
family['current_full_production']['cumulative_stats']=prod['cumulative_stats']
family['current_full_production']['encode_workers']=prod['encode_workers']
family['current_full_production']['palette_acceleration']=prod['palette_acceleration']
family['state']=family['current_full_production']['state'];family['current_installation']=dict(state='installed-ingame-pending',reference=snapshot,receipt=receiptref,catalogue_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],animation_ids=gen['animation_ids'],SDF=False,qa_ingame=False)
assert not any(e['family']=='multi_new' for e in track['current_recipe_complete_productions'])
track['current_recipe_complete_productions'].append(dict(family='multi_new',**family['current_full_production']))
totals.update(current_recipe_complete_families=12,current_recipe_complete_animation_ids=136,current_recipe_installed_animation_ids=136)
assert totals['current_recipe_ingame_accepted_families']==9 and totals['current_recipe_ingame_accepted_animation_ids']==79
track['engine_integration'].update(installed_candidate_reference=reference,latest_installation_verification_reference=snapshot)
track['colour_variants']['state']+='-MultiNew-V7-contextual-no-SDF-installed-ingame-pending';track['recorded_on']='2026-10-05';write_json(p,track)
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];byid={w['animation_id']:w for w in prod['plan']['witnesses']};changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in byid:out.append(line);continue
    row.update(queue_state='q3m-v7-full-produced-installed-ingame-pending',colour_variant_state='v7-full-native-bank-palettes-contextual-no-SDF-x2-installed-ingame-pending',q3m_v7_full_production_reference=reference,q3m_v7_installation_reference=receiptref,q3m_final_work_count_known=str(byid[row['animation_id']]['encoded_work']))
    text=io.StringIO(newline='');csv.DictWriter(text,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(text.getvalue());changed.append(row['animation_id'])
assert len(changed)==10;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
p=ROOT/'sprite/SUIVI_Q3M.md';t=p.read_text(encoding='utf-8');t=t.replace('126 IDs /11 familles disponibles complètes installées','136 IDs /12 familles disponibles complètes installées')
t=t.replace('| `multi_new` | 10/10 | — | Grands composites, quadrants et BAM divisés selon l\'INI ; dragons, Démogorgon. |','| `multi_new` | 10/10 | — | **Complète installée, QA en attente** : neuf dragons (trois modèles, sept palettes MDR1) et Démogorgon ; Q3m K6 x2 amélioré, raccords contextuels quatre/neuf parties, sans SDF. |')
description=f"- 10 IDs/4 modèles : MDR1 rouge/vert/aqua/bleu/brun/multicolore/violet ; MDR2 noir, MDR3 argent, MDEM Démogorgon. 1 753 BAM/191 817 frames natives ; {gen['resources']} feuilles/{gen['frames']} frames physiques, 5 155 liaisons/519 867 frames liées.\n- 17 103 sources originales -> 42 772 travaux compatibles, 30 palettes BMP natives par banque ; 5 411 assemblages contextuels, zéro changement hors bande. Q3m V7 K6 x2 amélioré/CatmullRom sans SDF.\n- DLL/INI/shaders acquis inchangés ; 10 CRE tests QMUL neutres. Douze familles/136 IDs installés ; neuf familles/79 IDs acceptés inchangés. **Monster_old et MultiNew : QA en attente** ; aucune release déduite.\n"
t+='\n## MultiNew : complet installé — 2026-10-05\n\n'+description+'- [Run et CLUA](../docs/measurements/'+HERE.name+'/README.md).\n';p.write_text(t,encoding='utf-8')
p=ROOT/'sprite/index/README.md';t=p.read_text(encoding='utf-8');t+='\n- MultiNew complet installé, QA en attente : [run](../../docs/measurements/'+HERE.name+'/README.md), [10 CLUA](../../docs/measurements/'+HERE.name+'/CLUA.txt). Quatre modèles/10 IDs, 30 palettes par banque, contextes natifs quatre/neuf parties ; douze familles/136 IDs installés, neuf familles/79 IDs acceptés conservés.\n';p.write_text(t,encoding='utf-8')
(HERE/'README.md').write_text('# MultiNew complet — Q3m amélioré x2 installé\n\n'+description+f"- Décodeur natif K6×3formats : 519 867 frames/cycles liés ; assemblage ordonné des cellules natives quatre/neuf parties : {verification['native_composite']['native_composites']} cas. Contrat palettes/géométrie/indices spéciaux/représentants vérifié.\n- Vérification cache-only : 42 772 encodages de base et 5 411 checkpoints relus sans import Torch ; aucune inférence durant ces contrôles. Production reprise : 1 823 contextes acquis conservés, 3 588 terminés, 21 348 nouvelles cibles contextuelles. Statistiques exactes `production.json`, recettes/contextes `multipart_context`.\n- Anciennes 207 animations/7 102 composants/55 733 routes et {len(baseline['preserved'])} fichiers acquis préservés. Catalogue actif : `catalog-proof.json`. Aucun BAM/INI/BMP natif remplacé.\n- Autorités : `current-generation.json`, `production.json`, `verification.json`, `runtime-route.json`, `installation-verification.json`, `installed-native-verification.json`, reçu local `ingame-installation/active-test.json`.\n- Essais : `CLUA.txt`/`creatures.json`, dix créatures neutres sans scripts/effets/équipement. Trois comparatifs `comparison*.png`, assemblages complets natif x2/Q3m. Aucun test ingame réalisé par l'agent.\n- Restauration : `restore.ps1`, jeu et InfinityLoader fermés ; parent catalogue conservé hors git `work/before`. Caches/assets locaux sous `sprite/.work/{HERE.name}` ; sources et manifests de production versionnés, payload/release inchangés.\n",encoding='utf-8')
with (HERE/'README.md').open('a',encoding='utf-8') as stream:
    stream.write(f"- Calculs GPU de base cumulés : {prod['cumulative_stats']['new_neural_targets']} cibles uniques ; les reprises CPU n'en génèrent aucune. Encodage : {prod['encode_workers']} threads/BLAS1 ; mesure synthétique `encode-scheduling.json`, SHA serial/parallèle identiques.\n")
    stream.write(f"- Accélération palette : `{prod['palette_acceleration']['mode']}`, source/compteurs `production.json`, mesures réelles `acceleration-benchmark.json`, comparaison CPU acquise et ROIs `acceleration-validation.json`. Les encodages CPU acquis sont conservés octet pour octet ; les ambiguïtés GPU sont recalculées par blocs CPU originaux.\n")
print(json.dumps(dict(installed=True,family='multi_new',animation_ids=10,resources=gen['resources'],frames=gen['frames'],accepted_ids=79)))
