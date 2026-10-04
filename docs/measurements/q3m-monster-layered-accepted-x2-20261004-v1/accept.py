"""Explicit user QA; new decision, historical production/installation unchanged."""
import copy,csv,datetime,io,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
body=HERE.parent/'q3m-monster-layered-full-x2-20261004-v1'
diagnostic=HERE.parent/'q3m-monster-layered-visibility-analysis-20261004-v1'
gen=load(body/'current-generation.json');game=get_path('bg2ee_game_root',required=True)
qa_path=ROOT/'sprite/index/qa-decisions/monster_layered/2026-10-04-accepted-full-layered-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists()
ids=gen['animation_ids'];assert len(ids)==7
catalog_path=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(catalog_path)==gen['catalog']['sha256']
catalog=registry.read_sealed_catalog_index(catalog_path,gen['catalog']['sha256'])
routes=[r for r in catalog['directory'] if r['animation_id'] in ids]
resources=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==len(resources)==65 and sum(s['frame_count'] for s in resources)==6422
for s in resources:
    p=game/s['registry'];assert file_sha(p).upper()==s['sha256']
    with p.open('rb') as f:header=struct.unpack('<8s6I',f.read(32))
    assert header[1]==7 and header[5] in (8,9) and header[6]==3
baseline=load(body/'baseline.json');expected={r['relative_path']:r['sha256'] for r in baseline['preserved']}
expected['InfinityEngine-Enhancer.dll']=gen['dll']['sha256']
runtime=[]
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha.lower()==expected[name].lower();runtime.append(dict(relative_path=name,sha256=sha))
assert load(body/'installed-native-verification.json')['passed']
fixtures=load(body/'ingame-installation/active-test.json')['fixtures']
for f in fixtures:assert file_sha(game/f['target']).lower()==f['sha256'].lower()
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete',engine_family='monster_layered',animation_ids=ids,models=7,resources=65,frames=6422,scale=2,SDF=False,excluded_non_native_refs=['MSIRG2BE'],source_absent=[]),
    visual_qa=dict(result='pass',authority='user',user_statement="ok c'est bo tout validé. met a jour le suivi et committe. puis identifie une nouvelle famille à traiter",individual_scenario_details='not specified by user',Volo='Acceptance follows diagnosis and stock SARVOLO test suggestion; no assumption about exact spawn command used.'),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=8,native_palette_kinds=[0,1],registry_version=7,world_filter='CatmullRom',colour='K6-four-partners-eight-levels/live native palettes/rule3',SDF=False,native_geometry=True,installed_runtime_files=runtime),
    provenance=dict(generation=identity(body/'current-generation.json'),production=identity(body/'production.json'),runtime=identity(body/'runtime.json'),installation_snapshot=identity(body/'installation-verification.json'),installation_receipt=identity(body/'ingame-installation/active-test.json'),verification=identity(body/'verification.json'),installed_verification=identity(body/'installed-native-verification.json'),visibility_diagnosis=identity(diagnostic/'analysis.json'),fixtures=fixtures),
    test_fixture_warning='QLYR2100 inherits ENDVOLO permanent Avatar Removal opcode271; unsuitable for visible tests. Use stock SARVOLO (same 2100 animation, no CRE effects). Ogre mage OGREMA01 equips native MAGE01 opcode20 invisibility.',resources=resources,resource_bindings=routes,release=False)
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
p=ROOT/'sprite/index/q3m-work-tracking.json';track=load(p);totals=track['queue_totals']
assert totals['current_recipe_ingame_accepted_families']==7 and totals['current_recipe_ingame_accepted_animation_ids']==65
totals.update(current_recipe_ingame_accepted_families=8,current_recipe_ingame_accepted_animation_ids=72)
family=next(f for f in track['families'] if f['engine_section']=='monster_layered')
visual=dict(state='accepted-full-family-V7-no-SDF',animation_ids=ids,models=7,resources=65,frames=6422,qa_reference=ref,catalogue_sha256=gen['catalog']['sha256'],SDF=False)
family['current_full_production'].update(state='family-complete-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['current_visual_QA']=visual;family['state']='family-complete-produced-installed-ingame-accepted'
# Queue state records QA separately from unchanged installation receipts.
family['current_installation'].update(state='installed-ingame-accepted',qa_ingame=True,qa_reference=ref)
family['current_colour_witness'].update(state='installed-via-complete-family-ingame-accepted',qa_reference=ref)
assert not any(e['family']=='monster_layered' for e in track['current_recipe_complete_productions'])
track['current_recipe_complete_productions'].append(dict(family='monster_layered',**copy.deepcopy(family['current_full_production'])))
track['colour_variants']['state']=track['colour_variants']['state'].replace('Monster_layered-V7-no-SDF-installed-ingame-pending','Monster_layered-V7-no-SDF-accepted')
write_json(p,track)
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();text=raw.decode('utf-8-sig');lines=text.splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    row['queue_state']='current-recipe-complete-installed-ingame-accepted';row['colour_variant_state']=row['colour_variant_state'].replace('installed-ingame-pending','installed-ingame-accepted')
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n');writer.writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==ids;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
p=ROOT/'sprite/SUIVI_Q3M.md';t=p.read_text(encoding='utf-8');t=t.replace('**Famille complète Q3m V7 x2 palette améliorée sans SDF installée, QA en attente**','**Famille complète Q3m V7 x2 palette améliorée sans SDF installée et validée ingame**')
t=t.replace('65 IDs /7 familles validées','72 IDs /8 familles validées').replace('`character_old` V7/V9 SDF gardes seulement)','`character_old` V7/V9 SDF gardes seulement, `monster_layered` V7 sans SDF)')
t+='\n## Monster_layered : famille complète validée — 2026-10-04\n\n- Utilisateur « tout validé » : **sept IDs/sept modèles/65 BAM/6 422 frames**, Q3m V7 K6 x2 palette améliorée/CatmullRom sans SDF. MSIRG2BE orphelin exclu ; source inchangée.\n- QA immuable `'+ref+'` : 65 feuilles et DLL/INI/trois shaders installés SHA vérifiés ; provenance production/native/installation et diagnostic visibilité conservée. Volo : `C:CreateCreature("SARVOLO")`; QLYR2100 hérite du masquage finaliste ENDVOLO/opcode271 et ne convient pas au test visible. Ogre mage : invisibilité native MAGE01/opcode20, rendu HD confirmé.\n- [Décision](../docs/measurements/'+HERE.name+'/README.md) ; **neuf familles/73 IDs installés, huit familles/72 IDs acceptés** ; Ogre reste QA en attente. Aucune installation/release modifiée.\n'
p.write_text(t,encoding='utf-8')
p=ROOT/'sprite/index/README.md';t=p.read_text(encoding='utf-8');t+='\n- Monster_layered complet **validé ingame**, sept modèles/65 BAM/6 422 frames Q3m V7 x2 palette améliorée/CatmullRom sans SDF : [QA/décision](../../docs/measurements/'+HERE.name+'/README.md). Volo visible : `SARVOLO`; fixture QLYR2100 masquée nativement, à éviter. Huit familles/72 IDs acceptés ; neuf familles/73 IDs installés.\n';p.write_text(t,encoding='utf-8')
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),accepted_ids=7,accepted_resources=65,accepted_frames=6422,installed_catalog_sha256=gen['catalog']['sha256'],runtime_files_verified=5,resource_files_verified=65,accepted_families=8,accepted_recipe_ids=72,release=False))
(HERE/'README.md').write_text('# Monster_layered — accepté ingame, 2026-10-04\n\n- QA : `'+ref+'`. Autorité : utilisateur « tout validé », après diagnostic Volo/ogre mage.\n- Sept IDs/sept modèles, 65 BAM/6 422 frames ; Q3m V7 K6 x2 palette améliorée/CatmullRom, sans SDF ; MSIRG2BE orphelin exclu.\n- 65 feuilles et cinq fichiers runtime installés SHA vérifiés ; production/installation et diagnostic historiques inchangés. Catalogue '+gen['catalog']['sha256']+' ; DLL '+gen['dll']['sha256']+'.\n- Volo : SARVOLO partage 2100 sans masquage CRE ; QLYR2100 conserve ENDVOLO/opcode271 et ne convient pas au test visible. Aucun CRE stock/fixture installé réécrit. Ogre mage : MAGE01/opcode20 natif.\n- Suivi : neuf familles/73 IDs installés ; huit familles/72 IDs acceptés. Ogre QA en attente ; release inchangée.\n',encoding='utf-8')
print(json.dumps(dict(accepted='monster_layered',ids=7,resources=65,frames=6422,accepted_families=8,accepted_recipe_ids=72)))
