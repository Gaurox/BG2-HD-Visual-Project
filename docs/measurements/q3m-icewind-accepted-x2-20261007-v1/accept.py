"""Record user's complete Icewind acceptance; bind installed bytes/runtime."""
import copy,csv,datetime,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
PROD=HERE.parent/'q3m-icewind-full-x2-20261006-v1';INSTALL=HERE.parent/'q3m-icewind-ingame-x2-20261006-v1'
gen=load(INSTALL/'current-generation.json');production=load(PROD/'current-generation.json');ids=gen['animation_ids']
qa_path=ROOT/'sprite/index/qa-decisions/monster-icewind/2026-10-07-accepted-full-native-icewind-q3m-v7-x2-nearest-v1.json'
assert not qa_path.exists() and len(ids)==40 and gen['scale']==2 and not gen['SDF']
receipt=load(INSTALL/'ingame-installation/active-test.json');assert receipt['status']=='installed-pending-ingame-qa'
assert load(INSTALL/'verification.json')['passed'] and load(INSTALL/'installed-native-verification.json')['passed']
game=get_path('bg2ee_game_root',required=True)
catalog_path=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(catalog_path)==gen['catalog']['sha256']
cat=registry.read_sealed_catalog_index(catalog_path,gen['catalog']['sha256'])
selected=registry.read_sealed_catalog_index(ROOT/production['catalog']['path'],production['catalog']['sha256'])
routes=sorted((r for r in cat['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
signature=lambda c,rs:[(r['animation_id'],r['resref'],r['resource_ordinal'],c['shards'][r['shard_index']]['sha256']) for r in rs]
original=sorted(selected['directory'],key=lambda r:(r['animation_id'],r['resref']))
assert signature(cat,routes)==signature(selected,original)
shards=[cat['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==1140 and len(shards)==1115 and sum(s['frame_count'] for s in shards)==75176
assert sum(cat['shards'][r['shard_index']]['frame_count'] for r in routes)==76955
for s in shards:assert file_sha(game/s['registry']).upper()==s['sha256']
fixtures=load(INSTALL/'creatures.json')['fixtures'];assert len(fixtures)==40
for f in fixtures:assert file_sha(game/f['target'])==f['sha256']
baseline=load(INSTALL/'baseline.json');expected={r['relative_path']:r['sha256'] for r in baseline['preserved']}
expected['InfinityEngine-Enhancer.dll']=gen['dll']['sha256'];runtime_files=[]
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha==expected[name];runtime_files.append(dict(relative_path=name,sha256=sha))
ini=(game/'InfinityEngine-Enhancer.ini').read_text(encoding='utf-8-sig')
settings=registry.parse_animation_ini(ini.encode('cp1252'))
filters=[v['creaturespritefilter'] for v in settings.values() if 'creaturespritefilter' in v]
assert filters==['Nearest'],filters
inventory=HERE/'asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as output:
    writer=csv.writer(output,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
    for r in routes:
        s=cat['shards'][r['shard_index']];writer.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],s['frame_count'],r['resource_ordinal']])
selection=load(PROD/'selection.json')
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),recorded_on='2026-10-07',timezone='Europe/Paris',
    scope=dict(kind='installed-native-family-complete-available',engine_family='monster_icewind',animation_ids=ids,models=36,colour_variants=40,
        resources=1115,resource_bindings=1140,unique_native_BAM=1051,frames=75176,bound_frames=76955,original_native_frames=71072,
        scale=2,SDF=False,source_absent=selection['source_absent_animation_ids'],native_source_absent=selection['native_source_absent_animation_ids']),
    visual_qa=dict(result='pass',authority='user',user_statement='bien, tous les mobs sont vérifiés ingame et validés. valide le lot, mets a jour le suivi et committe',
        individual_scenario_details='not specified by user',accepted_as_installed=True,full_lot_explicitly_confirmed=True),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=2,native_render_owners=['MonsterIcewind'],
        native_palette_kinds=[0],registry_version=7,world_filter='Nearest',colour='K6-four-partners-eight-levels/native fixed and alternate palettes/rule3',
        SDF=False,native_geometry=True,body_and_weapon_metadata_wait=True,native_loop_and_clamp=True,installed_runtime_files=runtime_files),
    asset_scope=dict(inventory=identity(inventory),ordering='animation_id,resref ascending; UTF-8 CSV LF, header included in SHA256',
        physical_leaf_count=1115,binding_count=1140,catalogue=gen['catalog'],physical_leaf_hashes_verified=1115,selected_routes_unchanged=True),
    provenance=dict(generation=identity(PROD/'current-generation.json'),production=production['production'],recipe=production['recipe'],
        installed_generation=identity(INSTALL/'current-generation.json'),installation_snapshot=identity(INSTALL/'installation-verification.json'),
        installation_receipt=identity(INSTALL/'ingame-installation/active-test.json'),verification=identity(INSTALL/'verification.json'),
        installed_native_verification=identity(INSTALL/'installed-native-verification.json'),fixtures=identity(INSTALL/'creatures.json')),release=False)
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path);totals=tracking['queue_totals']
assert totals['current_recipe_ingame_accepted_animation_ids']==136 and totals['current_recipe_ingame_accepted_families']==12
assert totals['current_recipe_installed_animation_ids']==176 and totals['current_recipe_complete_animation_ids']==253
other=copy.deepcopy([f for f in tracking['families'] if f['engine_section']!='monster_icewind'])
family=next(f for f in tracking['families'] if f['engine_section']=='monster_icewind');assert not family['current_full_production']['qa_ingame']
ref=qa_path.relative_to(ROOT).as_posix();visual=dict(state='accepted-full-native-available-family-V7-no-SDF-as-installed',animation_ids=ids,
    models=36,colour_variants=40,resources=1115,frames=75176,resource_bindings=1140,bound_frames=76955,qa_reference=ref,
    catalogue_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],SDF=False,world_filter='Nearest')
state='family-complete-native-available-produced-installed-ingame-accepted'
family['current_full_production'].update(state=state,qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['state']=state;family['current_visual_QA']=visual
family['current_installation'].update(state='installed-ingame-accepted',qa_ingame=True,qa_reference=ref)
family['current_colour_witness'].update(state='installed-via-complete-native-family-ingame-accepted',qa_reference=ref)
next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster_icewind').update(copy.deepcopy(family['current_full_production']))
totals.update(current_recipe_ingame_accepted_families=13,current_recipe_ingame_accepted_animation_ids=176)
tracking['recorded_on']='2026-10-07'
assert other==[f for f in tracking['families'] if f['engine_section']!='monster_icewind']
write_json(qa_path,qa);write_json(path,tracking)
path=ROOT/'sprite/index/q3m-work-items.csv';raw=path.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True)
fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    assert row['q3m_v7_installation_reference'].endswith('q3m-icewind-ingame-x2-20261006-v1/ingame-installation/active-test.json')
    row['queue_state']='current-recipe-complete-native-installed-ingame-accepted'
    row['colour_variant_state']='v7-four-partners-eight-levels-no-SDF-x2-installed-ingame-accepted'
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row)
    out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==ids;path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),asset_scope=identity(inventory),accepted_ids=40,models=36,accepted_resources=1115,accepted_frames=75176,
    binding_count=1140,bound_frames=76955,installed_catalog_sha256=gen['catalog']['sha256'],runtime_files_verified=5,fixtures_verified=40,physical_leaf_hashes_verified=1115,
    accepted_improved_families=13,accepted_improved_ids=176,accepted_selected_recipe_families=14,accepted_selected_recipe_ids=254,
    remaining_produced_uninstalled_family='monster',remaining_produced_uninstalled_ids=77,release=False))
print(json.dumps(dict(accepted='monster_icewind',ids=40,models=36,resources=1115,accepted_improved_ids=176,accepted_with_character_v6_ids=254)),flush=True)
