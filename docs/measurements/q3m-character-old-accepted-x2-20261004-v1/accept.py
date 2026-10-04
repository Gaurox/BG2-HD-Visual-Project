"""Explicit full-family user QA on installed mixed V7/V9; keep historical proofs immutable."""
import datetime,json,sys,csv,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
qa_path=ROOT/'sprite/index/qa-decisions/character_old/2026-10-04-accepted-full-character-old-q3m-v7-v9-guards-sdf-x2-catmullrom-v1.json'
assert not qa_path.exists()
body=ROOT/'docs/measurements/q3m-character-old-full-x2-20261004-v1'
fixed=ROOT/'docs/measurements/q3m-character-old-runtime-fix-x2-20261004-v1'
sdf=ROOT/'docs/measurements/q3m-doom-guard-sdf-ingame-x2-20261004-v1'
gen=load(sdf/'current-generation.json');game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
catalog=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',gen['catalog']['sha256'])
ids=[f'0x{x:04X}' for x in range(0x6400,0x6407)];sdf_ids=gen['animation_ids'];assert sdf_ids==ids[-2:]
routes=[r for r in catalog['directory'] if r['animation_id'] in ids]
resources=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
refs={r['resref'] for r in routes};frames=sum(s['frame_count'] for s in resources);bound_frames=sum(catalog['shards'][r['shard_index']]['frame_count'] for r in routes)
assert len(routes)==4962 and len(resources)==2018 and len(refs)==1066 and frames==93194
headers={}
for s in resources:
    path=game/s['registry'];assert file_sha(path).upper()==s['sha256']
    with path.open('rb') as f:headers[s['index']]=struct.unpack('<8s6I',f.read(32))
byid={aid:[r for r in routes if r['animation_id']==aid] for aid in ids}
for aid,rr in byid.items():
    versions={headers[r['shard_index']][1] for r in rr}
    assert versions==({9} if aid in sdf_ids else {7})
    assert all(headers[r['shard_index']][5] in (8,9) and headers[r['shard_index']][6]==3 for r in rr)
runtime=[]
expected={r['relative_path']:r['sha256'] for r in load(sdf/'baseline.json')['preserved']}
expected['InfinityEngine-Enhancer.dll']=gen['dll']['sha256']
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha.lower()==expected[name].lower();runtime.append(dict(relative_path=name,sha256=sha))
assert load(fixed/'installed-composition.json')['native_composite']['passed']
assert load(sdf/'installed-composition.json')['native_composite']['passed'] and load(sdf/'gpu-verification.json')['passed']
fixtures=load(body/'ingame-installation/active-test.json')['fixtures']
for f in fixtures:assert file_sha(game/f['target']).lower()==f['sha256'].lower()
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete-available',engine_family='character_old',animation_ids=ids,excluded_animation_ids=['0x6621'],source_absent=[dict(animation_id='0x6621',symbol='FIGHTER_FEMALE_HUMAN_BG1',resref='XHFF')],variant_id='q3m-v7-v9-K6-x2-catmullrom-guards-only-SDF',scale=2,models=6,visible_body_models=5,resources=len(resources),unique_native_BAM=len(refs),frames=frames,logical_resource_bindings=len(routes),logical_bound_frames=bound_frames,body_resources=99,body_frames=4725,SDF_animation_ids=sdf_ids,transparent_native_guard_frames=936,resource_counting='2018 installed variant leaves /1066 distinct native resrefs; cloned equipment/shadows counted once per variant'),
    visual_qa=dict(result='pass',authority='user',user_statement='bien on valide toute la famille. met a jour le suivi et committe',individual_scenario_details='not specified by user'),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],ini_sha256=expected['InfinityEngine-Enhancer.ini'],catalogue_sha256=gen['catalog']['sha256'],owner=6,world_filter='CatmullRom',colour='K6-four-partners-eight-levels/live native palettes/rule3',registry_versions=[7,9],SDF_scope=dict(enabled_animation_ids=sdf_ids,disabled_animation_ids=ids[:5],mode=1,shadow_alpha=127),native_geometry=True,installed_runtime_files=runtime),
    provenance=dict(body_generation=identity(body/'current-generation.json'),native_dependency_generation=identity(fixed/'current-generation.json'),guard_SDF_generation=identity(sdf/'current-generation.json'),productions=[identity(r/'production.json') for r in (body,fixed,sdf)],installation_snapshots=[identity(r/'installation-verification.json') for r in (body,fixed,sdf)],verifications=[identity(r/'verification.json') for r in (body,fixed,sdf)],installed_composition=identity(sdf/'installed-composition.json'),fixtures=fixtures),resources=resources,resource_bindings=routes,release=False)
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
p=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(p);totals=tracking['queue_totals'];assert totals['current_recipe_ingame_accepted_families']==6 and totals['current_recipe_ingame_accepted_animation_ids']==58
totals.update(current_recipe_ingame_accepted_families=7,current_recipe_ingame_accepted_animation_ids=65)
visual=dict(state='accepted-full-available-mixed-V7-V9',animation_ids=ids,models=6,resources=2018,unique_native_BAM=1066,frames=93194,qa_reference=ref,catalogue_sha256=gen['catalog']['sha256'],SDF_animation_ids=sdf_ids)
family=next(f for f in tracking['families'] if f['engine_section']=='character_old');entry=next(f for f in tracking['current_recipe_complete_productions'] if f['family']=='character_old')
for e in (family['current_full_production'],entry):
    e.update(state='family-complete-available-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual,accepted_installed_resources=2018,accepted_installed_frames=93194,accepted_logical_resource_bindings=4962,accepted_logical_bound_frames=bound_frames)
    for o in e['per_animation_overrides']:o.update(state='two-native-guards-SDF-installed-ingame-accepted',qa_ingame=True,qa_reference=ref)
family['current_visual_QA']=visual
tracking['colour_variants']['state']=tracking['colour_variants']['state'].replace('Character_old-V7-no-SDF-installed','Character_old-V7-V9-guards-SDF-accepted');write_json(p,tracking)
p=ROOT/'sprite/index/q3m-work-items.csv'
with p.open(encoding='utf-8-sig',newline='') as f:reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
for r in rows:
    if r['animation_id'] in ids:
        r['queue_state']='current-recipe-complete-installed-ingame-accepted';r['colour_variant_state']=r['colour_variant_state'].replace('installed-ingame-pending','installed-ingame-accepted')
with p.open('w',encoding='utf-8',newline='') as f:writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),accepted_ids=7,unique_native_BAM=1066,accepted_variant_leaves=2018,accepted_frames=93194,SDF_animation_ids=sdf_ids,installed_catalog_sha256=gen['catalog']['sha256'],runtime_files_verified=5,resource_files_verified=2018,accepted_families=7,accepted_recipe_ids=65,release=False))
p=ROOT/'sprite/SUIVI_Q3M.md';s=p.read_text(encoding='utf-8')
lines=s.splitlines()
for i,line in enumerate(lines):
    if line.startswith('| `character_old` |'):lines[i]='| `character_old` | 7/8 | 7 | **Famille disponible complète validée**, Q3m x2 palette améliorée/CatmullRom ; cinq IDs V7 sans SDF +gardes6405/6406 V9 SDF. 1 066 BAM natifs/2 018 feuilles variantes installées ; corps des gardes natifs transparents, XHFF6621 absent. |'
    if line.startswith('- Historique V6 :'):
        lines[i]=line.replace('58 IDs /6 familles validées','65 IDs /7 familles validées').replace('`ambient` V7 sans SDF)','`ambient` V7 sans SDF, `character_old` V7/V9 SDF gardes seulement)')
s='\n'.join(lines)+'\n';s+=f'\n## Character_old : famille complète validée — 2026-10-04\n\n- Validation explicite utilisateur : « bien on valide toute la famille » ; **sept IDs/six ensembles**, cinq corps visibles +gardes6405/6406 transparents natifs. Q3m x2/CatmullRom/palette améliorée ; V7 sans SDF pour6400–6404, V9 SDF pour6405/6406. XHFF6621 sans source exclu.\n- QA immuable `{ref}` : **2 018 feuilles variantes/93 194frames physiques installées**, 1 066 BAM natifs distincts, 4 962bindings/{bound_frames}frames liées ;952 dépendances clonées pour isoler SDF. SHA2018feuilles +DLL/INI/trois shaders +deuxCREtémoin vérifiés, aucune production/installation historique réécrite.\n- [Décision/suivi](../docs/measurements/{HERE.name}/README.md) ; totaux **sept familles/65 IDs acceptés**, huit familles/66 IDs installés. Ogre reste QA en attente ; aucune modification ingame/release.\n';p.write_text(s,encoding='utf-8')
p=ROOT/'sprite/index/README.md';s=p.read_text(encoding='utf-8');s+=f'\n- Character_old complet **accepté ingame**, sept IDs, Q3m V7 sans SDF6400–6404 +V9 SDF6405/6406 : [QA/décision](../../docs/measurements/{HERE.name}/README.md). 1 066 BAM natifs/2 018 feuilles variantes ; XHFF6621 absent.\n';p.write_text(s,encoding='utf-8')
p=ROOT/'.gitattributes';s=p.read_text(encoding='utf-8');s+='\n# Character_old mixed V7/V9 accepted identities pin raw bytes.\ndocs/measurements/'+HERE.name+'/** -text -whitespace\nsprite/index/qa-decisions/character_old/*.json -text -whitespace\n';p.write_text(s,encoding='utf-8')
print(json.dumps(dict(accepted='character_old',ids=7,resources=2018,frames=93194,SDF_ids=sdf_ids,accepted_families=7,accepted_recipe_ids=65)))
