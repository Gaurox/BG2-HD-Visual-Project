"""Explicit acceptance of MultiNew Q3m x2 + installed native playback runtime v2."""
import copy,csv,datetime,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
body=HERE.parent/'q3m-multi-new-frame-stability-20261005-v2'
production=HERE.parent/'q3m-multi-new-full-x2-20261005-v1'
gen=load(body/'current-generation.json');game=get_path('bg2ee_game_root',required=True)
qa_path=ROOT/'sprite/index/qa-decisions/multi-new/2026-10-05-accepted-full-native-playback-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists()
ids=gen['animation_ids'];assert len(ids)==10 and gen['scale']==2 and not gen['SDF']
catalog=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',gen['catalog']['sha256'])
routes=sorted((r for r in catalog['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
shards=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==len(shards)==5155 and sum(s['frame_count'] for s in shards)==519867
# Immutable scoped inventory binds every accepted consumer to its exact leaf SHA.
# Physical hashes were already verified by v2 verify.py; no new global audit.
inventory=HERE/'asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as output:
    writer=csv.writer(output,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
    for route in routes:
        s=catalog['shards'][route['shard_index']]
        writer.writerow([route['animation_id'],route['resref'],s['registry'],s['sha256'],s['frame_count'],route['resource_ordinal']])
baseline=load(body/'baseline.json');expected={r['relative_path']:r['sha256'] for r in baseline['preserved']}
expected['InfinityEngine-Enhancer.dll']=gen['dll']['sha256'];runtime=[]
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha.lower()==expected[name].lower();runtime.append(dict(relative_path=name,sha256=sha))
verification=load(body/'verification.json');assert verification['passed'] and verification['observed_regressions_verified']==10
assert verification['playback']['missing_or_wrong_frames']==0
fixtures=load(production/'creatures.json')['fixtures']
assert len(fixtures)==10
for f in fixtures:assert file_sha(game/f['target']).lower()==f['sha256'].lower()
receipt=load(body/'ingame-installation/active-test.json');assert receipt['dll_sha256']==gen['dll']['sha256'] and receipt['status']=='installed-pending-ingame-qa'
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete',engine_family='multi_new',animation_ids=ids,models=4,colour_variants=10,resources=5155,resource_bindings=5155,unique_native_BAM=1753,frames=519867,original_native_frames=191817,scale=2,SDF=False,source_absent=[]),
    visual_qa=dict(result='pass',authority='user',user_statement='ok tout le lot est validé. committe et met a jour le suivi.\nreste seulement a vérifier la 40ene de créature de la famille précédente. je le fais apres ton committe',individual_scenario_details='not specified by user'),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=5,native_render_owners=['MonsterMulti','MultiNew'],native_palette_kinds=[0],registry_version=7,world_filter='CatmullRom',colour='K6-four-partners-eight-levels/native bank palettes/rule3',SDF=False,native_geometry=True,current_group_metadata_wait=True,native_loop_and_clamp=True,installed_runtime_files=runtime),
    asset_scope=dict(inventory=identity(inventory),ordering='animation_id,resref ascending; UTF-8 CSV LF, header included in SHA256',physical_leaf_count=5155,binding_count=5155,catalogue=gen['catalog'],physical_hash_verification=identity(body/'verification.json')),
    provenance=dict(generation=identity(body/'current-generation.json'),production=gen['production'],runtime=gen['runtime'],installation_snapshot=identity(body/'installation-verification.json'),installation_receipt=identity(body/'ingame-installation/active-test.json'),original_asset_installation_receipt=identity(production/'ingame-installation/active-test.json'),verification=identity(body/'verification.json'),original_verification=identity(production/'verification.json'),fixtures=identity(production/'creatures.json')),
    contextual_seams=load(production/'production.json')['multipart_context'],release=False)
p=ROOT/'sprite/index/q3m-work-tracking.json';track=load(p);totals=track['queue_totals']
assert totals['current_recipe_ingame_accepted_families']==9 and totals['current_recipe_ingame_accepted_animation_ids']==79
other=[copy.deepcopy(f) for f in track['families'] if f['engine_section']!='multi_new']
family=next(f for f in track['families'] if f['engine_section']=='multi_new');assert not family['current_full_production']['qa_ingame']
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
visual=dict(state='accepted-full-family-contextual-V7-native-playback-no-SDF',animation_ids=ids,models=4,colour_variants=10,resources=5155,frames=519867,qa_reference=ref,catalogue_sha256=gen['catalog']['sha256'],SDF=False)
family['current_full_production'].update(state='family-complete-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['current_visual_QA']=visual;family['state']=family['current_full_production']['state']
family['current_installation'].update(state='installed-ingame-accepted',qa_ingame=True,qa_reference=ref)
family['current_colour_witness'].update(state='installed-via-complete-native-palette-family-ingame-accepted',qa_reference=ref)
next(e for e in track['current_recipe_complete_productions'] if e['family']=='multi_new').update(copy.deepcopy(family['current_full_production']))
totals.update(current_recipe_ingame_accepted_families=10,current_recipe_ingame_accepted_animation_ids=89)
track['colour_variants']['state']=track['colour_variants']['state'].replace('MultiNew-V7-contextual-no-SDF-installed-ingame-pending','MultiNew-V7-contextual-native-playback-no-SDF-accepted')
assert other==[f for f in track['families'] if f['engine_section']!='multi_new']
assert totals['current_recipe_installed_animation_ids']==136 and totals['current_recipe_complete_families']==12
write_json(p,track)
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    row['queue_state']='current-recipe-complete-installed-ingame-accepted';row['colour_variant_state']=row['colour_variant_state'].replace('installed-ingame-pending','installed-ingame-accepted')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==ids;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),asset_scope=identity(inventory),accepted_ids=10,accepted_resources=5155,accepted_frames=519867,installed_catalog_sha256=gen['catalog']['sha256'],runtime_files_verified=5,fixtures_verified=10,physical_leaf_hashes_reused_from_v2_verification=5155,accepted_families=10,accepted_recipe_ids=89,installed_families=12,installed_recipe_ids=136,monster_old_qa='pending',monster_old_ids=46,release=False))
print(json.dumps(dict(accepted='multi_new',ids=10,resources=5155,accepted_families=10,accepted_recipe_ids=89,monster_old_pending_ids=46)))
