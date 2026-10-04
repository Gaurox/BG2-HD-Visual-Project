"""Explicit user acceptance of installed contextual Quadrant; immutable old runs."""
import copy,csv,datetime,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
body=HERE.parent/'q3m-monster-quadrant-seam-fixed-x2-20261004-v1'
gen=load(body/'current-generation.json');game=get_path('bg2ee_game_root',required=True)
qa_path=ROOT/'sprite/index/qa-decisions/monster_quadrant/2026-10-04-accepted-full-quadrant-contextual-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists()
ids=gen['animation_ids'];assert len(ids)==7
catalog_path=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(catalog_path)==gen['catalog']['sha256']
catalog=registry.read_sealed_catalog_index(catalog_path,gen['catalog']['sha256'])
routes=[r for r in catalog['directory'] if r['animation_id'] in ids]
resources=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==len(resources)==132 and sum(s['frame_count'] for s in resources)==12928
for s in resources:assert file_sha(game/s['registry']).upper()==s['sha256']
baseline=load(body/'baseline.json');expected={r['relative_path']:r['sha256'] for r in baseline['preserved']}
runtime=[]
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha.lower()==expected[name].lower();runtime.append(dict(relative_path=name,sha256=sha))
verification=load(body/'verification.json');assert verification['passed'] and verification['changed_outside_band']==0
assert load(body/'installed-native-verification.json')['passed']
fixtures=load(body/'ingame-installation/active-test.json')['fixtures']
for f in fixtures:assert file_sha(game/f['target']).lower()==f['sha256'].lower()
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete',engine_family='monster_quadrant',animation_ids=ids,models=2,colour_variants=7,resources=132,unique_native_BAM=36,frames=12928,scale=2,SDF=False,source_absent=['0x1101','0x1105'],excluded_non_native_BAM_count=33),
    visual_qa=dict(result='pass',authority='user',user_statement='valide la famille. met a jour le suivi. mémorise la nouvelle methodo dans un pipeline a utiliser systematiquement sur les gros sprites a plusieurs tuiles. met a jour la doc en conséquence et committe tout',individual_scenario_details='not specified by user'),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=4,native_palette_kinds=[0],registry_version=7,world_filter='CatmullRom',colour='K6-four-partners-eight-levels/live native palettes/rule3',SDF=False,native_geometry=True,installed_runtime_files=runtime),
    provenance=dict(generation=identity(body/'current-generation.json'),production=identity(body/'production.json'),runtime=gen['runtime'],recipe=identity(body/'recipe.json'),installation_snapshot=identity(body/'installation-verification.json'),installation_receipt=identity(body/'ingame-installation/active-test.json'),verification=identity(body/'verification.json'),installed_verification=identity(body/'installed-native-verification.json'),fixtures=fixtures),
    contextual_seams=dict(contexts=3144,new_neural_targets=18552,band_native_pixels=4,changed_encoded_pixels=6010622,changed_outside_band=0,unreferenced_frames_preserved=272,native_empty_declarations=65),resources=resources,resource_bindings=routes,release=False)
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
p=ROOT/'sprite/index/q3m-work-tracking.json';track=load(p);totals=track['queue_totals']
assert totals['current_recipe_ingame_accepted_families']==8 and totals['current_recipe_ingame_accepted_animation_ids']==72
totals.update(current_recipe_ingame_accepted_families=9,current_recipe_ingame_accepted_animation_ids=79)
family=next(f for f in track['families'] if f['engine_section']=='monster_quadrant')
visual=dict(state='accepted-full-family-contextual-V7-no-SDF',animation_ids=ids,models=2,colour_variants=7,resources=132,frames=12928,qa_reference=ref,catalogue_sha256=gen['catalog']['sha256'],SDF=False)
family['current_full_production'].update(state='family-complete-seam-corrected-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['current_visual_QA']=visual;family['state']=family['current_full_production']['state']
family['current_installation'].update(state='installed-ingame-accepted',qa_ingame=True,qa_reference=ref)
family['current_colour_witness'].update(state='installed-via-seam-corrected-complete-family-ingame-accepted',qa_reference=ref)
entry=next(e for e in track['current_recipe_complete_productions'] if e['family']=='monster_quadrant');entry.update(copy.deepcopy(family['current_full_production']))
track['colour_variants']['state']=track['colour_variants']['state'].replace('Monster_quadrant-V7-no-SDF-installed-ingame-pending','Monster_quadrant-contextual-V7-no-SDF-accepted')
track['multipart_production_method']=dict(reference='pipeline/SPRITES_Q3M_MULTIPART.md',producer='pipeline/scripts/q3m_multipart_seams.py',policy='systematic for native spatial tile groups',accepted_reference=ref)
write_json(p,track)
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    row['queue_state']='current-recipe-complete-installed-ingame-accepted';row['colour_variant_state']=row['colour_variant_state'].replace('installed-ingame-pending','installed-ingame-accepted')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==ids;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),accepted_ids=7,accepted_resources=132,accepted_frames=12928,installed_catalog_sha256=gen['catalog']['sha256'],runtime_files_verified=5,resource_files_verified=132,accepted_families=9,accepted_recipe_ids=79,installed_families=10,installed_recipe_ids=80,release=False))
(HERE/'README.md').write_text('# Monster_quadrant — accepté ingame, 2026-10-04\n\n- QA immuable : `'+ref+'` ; autorité utilisateur « valide la famille », version installée avec raccords contextuels.\n- Deux modèles/sept palettes, 36 BAM natifs/132 feuilles/12 928 frames ; Q3m V7 K6 x2 amélioré/CatmullRom sans SDF ; MWDR1101/1105 sans source, 33 BAM hors constructeur exclus.\n- 3 144 contextes/18 552 cibles ; 6 010 622 pixels encodés modifiés, zéro hors bandes4px natifs. 272 frames non référencées/65 déclarations0×0 préservées.\n- 132 feuilles +DLL/INI/trois shaders/7 fixtures installés SHA vérifiés. Historique production/installation inchangé.\n- Méthode systématique : [pipeline réutilisable](../../../pipeline/SPRITES_Q3M_MULTIPART.md), appels automatiques plan/run/pack.\n- Suivi : dix familles/80 IDs installés ; neuf familles/79 IDs acceptés. Ogre reste QA en attente. Aucun payload/release modifié.\n',encoding='utf-8')
print(json.dumps(dict(accepted='monster_quadrant',ids=7,resources=132,frames=12928,accepted_families=9,accepted_recipe_ids=79)))
