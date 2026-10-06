"""Record the verified Icewind installation; preserve all acquired QA decisions."""
import csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');baseline=load(HERE/'baseline.json');receipt=load(HERE/'ingame-installation/active-test.json')
verification=load(HERE/'verification.json');assert receipt['status']=='installed-pending-ingame-qa' and verification['passed']
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/receipt['catalog_relative'])==gen['catalog']['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
for r in baseline['preserved']:assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower()
for s in receipt['new_shards']:assert file_sha(game/s['registry']).upper()==s['sha256'].upper()
for f in receipt['fixtures']:assert file_sha(game/f['target'])==f['sha256']
installed=registry.read_sealed_catalog_index(game/receipt['catalog_relative'],gen['catalog']['sha256'])
assert len(installed['animations'])==257
ids={a['animation_id'] for a in installed['animations'] if a['owner']==2}
assert ids==set(gen['animation_ids'])
write_json(HERE/'installed-native-verification.json',dict(passed=True,installed_animations=257,icewind_ids=40,resources=1115,frames=75176,
    catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],preserved_files=len(baseline['preserved']),fixtures=40,
    inherited_routes_unchanged=60888,new_leaf_sha256_verified=1115,native_world=verification['native_world'],playback=verification['playback'],ingame_QA=False,release=False))
prefix=HERE.relative_to(ROOT).as_posix();reference=prefix+'/current-generation.json';snapshot=prefix+'/installation-verification.json';receiptref=prefix+'/ingame-installation/active-test.json'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path);totals=tracking['queue_totals']
assert totals['current_recipe_installed_animation_ids']==136
qa={k:v for k,v in totals.items() if 'accepted' in k}
family=next(f for f in tracking['families'] if f['engine_section']=='monster_icewind')
record=next(f for f in tracking['current_recipe_complete_productions'] if f['family']=='monster_icewind')
state='family-complete-native-available-produced-installed-host-verified-ingame-QA-pending'
for item in (family['current_full_production'],record):
    item.update(installation=True,installation_reference=receiptref,installation_snapshot=snapshot,installation_generation_reference=reference,state=state)
family['state']=state;family['current_installation']=dict(state='installed-ingame-pending',reference=snapshot,receipt=receiptref,
    generation_reference=reference,catalogue_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],animation_ids=gen['animation_ids'],SDF=False,qa_ingame=False)
family['current_colour_witness'].update(state='installed-via-complete-native-family-ingame-QA-pending',installation_reference=snapshot)
totals['current_recipe_installed_animation_ids']=176
assert totals['current_recipe_complete_animation_ids']==253 and qa=={k:v for k,v in totals.items() if 'accepted' in k}
tracking['engine_integration'].update(installed_candidate_reference=reference,latest_installation_verification_reference=snapshot)
tracking['recorded_on']='2026-10-07'
write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True)
fields=next(csv.reader([lines[0]]));out=[lines[0]];selected=set(gen['animation_ids']);changed=0
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in selected:out.append(line);continue
    assert row['engine_family']=='monster_icewind' and not row['q3m_v7_installation_reference']
    row.update(q3m_v7_installation_reference=receiptref,queue_state='current-recipe-complete-native-installed-ingame-QA-pending',colour_variant_state='v7-four-partners-eight-levels-no-SDF-x2-installed-ingame-QA-pending')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row)
    out.append(stream.getvalue());changed+=1
assert changed==40;path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
path=ROOT/'sprite/SUIVI_Q3M.md';text=path.read_text(encoding='utf-8');lines=text.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| `monster_icewind` |'):
        lines[i]='| `monster_icewind` | 40/132 natifs ; 44 avec préfixe | — | **Famille native disponible complète V7 x2 améliorée sans SDF installée, QA ingame en attente** : 36 modèles/40 IDs, 1 051 BAM/71 072 frames natives, 1 115 feuilles/75 176 frames physiques. DLL owner2 chargement/cycles ; 40 CRE QICE neutres. 88 absents +4 IDs au layout Monster exclus. |'
    elif line.startswith('- Production améliorée complète : **253 IDs'):
        lines[i]=line.replace('packs autonomes vérifiés, non installés','packs autonomes vérifiés ; Icewind installé, Monster non installé').replace('**Installation/QA : 136 IDs /12 familles**, acquis conservés','**Installation : 176 IDs/13 familles ; QA : 136 IDs/12 familles**, acquis conservés')
    elif line.startswith('- Character : **78 IDs V6 complets'):
        lines[i]=line.replace('214 IDs/13 familles installés et acceptés ; Monster et Icewind restent production seule','254 IDs/14 familles installés, 214 IDs/13 familles acceptés ; Monster reste production seule, Icewind attend sa QA')
lines[0]=lines[0].replace('2026-10-06','2026-10-07')
lines.extend(['','## Icewind installé — 2026-10-07','',
    '- 40 IDs/36 modèles ; Q3m V7 K6/quatre partenaires/huit niveaux/x2 sans SDF, filtre Nearest conservé. Catalogue combiné 257 IDs/13 372 feuilles/2 318 470 frames ; 217 IDs/60 888 routes parents préservés.',
    f'- [Installation/CLUA](../{prefix}/README.md), reçu `{prefix}/ingame-installation/active-test.json`. 40 CRE QICE neutres, dont trois palettes alternatives et alias E020. DLL candidate owner2 installée ; INI/shaders/exécutable natif inchangés. Sauvegarde/restauration disponibles.',
    '- Installation améliorée 176 IDs/13 familles ; avec Character V6 acquis : 254 IDs/14 familles. QA inchangée 136 IDs/12 familles (+Character : 214/13). Icewind QA ingame en attente, aucune release déduite.'])
path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(installed=True,icewind_ids=40,active_ids=257,installed_improved_ids=176,installed_selected_recipe_ids=254,ingame_accepted_ids_unchanged=136,QA_pending=True,release=False)),flush=True)
