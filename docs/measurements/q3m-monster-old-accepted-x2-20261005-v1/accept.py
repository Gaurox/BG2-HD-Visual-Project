"""Record explicit full available Monster_old acceptance, with current installed runtime."""
import copy,csv,datetime,hashlib,io,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
def committed_identity(p):
    relative=p.relative_to(ROOT).as_posix();raw=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
    assert p.read_bytes().replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n')
    return dict(path=relative,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),serialization='Git HEAD blob; working copy equivalent modulo CRLF')
production=HERE.parent/'q3m-monster-old-full-x2-20261004-v1'
runtime=HERE.parent/'q3m-multi-new-frame-stability-20261005-v2'
analysis=HERE.parent/'q3m-monster-old-7001-7b06-analysis-20261005-v1'
gen=load(production/'current-generation.json');current=load(runtime/'current-generation.json')
game=get_path('bg2ee_game_root',required=True);ids=gen['animation_ids']
qa_path=ROOT/'sprite/index/qa-decisions/monster_old/2026-10-05-accepted-full-available-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists() and len(ids)==46 and gen['scale']==2 and not gen['SDF']
catalog=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',current['catalog']['sha256'])
selected=registry.read_sealed_catalog_index(ROOT/gen['catalog']['path'],gen['catalog']['sha256'])
routes=sorted((r for r in catalog['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
assert routes==sorted((r for r in selected['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
shards=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==218 and len(shards)==217 and sum(s['frame_count'] for s in shards)==17752
assert sum(catalog['shards'][r['shard_index']]['frame_count'] for r in routes)==17754
for s in shards:assert file_sha(game/s['registry']).lower()==s['sha256'].lower()
fixtures=load(production/'creatures.json')['fixtures'];assert len(fixtures)==46
for f in fixtures:assert file_sha(game/f['target']).lower()==f['sha256'].lower()
baseline=load(runtime/'baseline.json');expected={r['relative_path']:r['sha256'] for r in baseline['preserved']}
expected['InfinityEngine-Enhancer.dll']=current['dll']['sha256'];runtime_files=[]
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha.lower()==expected[name].lower();runtime_files.append(dict(relative_path=name,sha256=sha))
assert load(production/'verification.json')['passed']
inventory=HERE/'asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as output:
    writer=csv.writer(output,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
    for r in routes:
        s=catalog['shards'][r['shard_index']]
        writer.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],s['frame_count'],r['resource_ordinal']])
absent=load(production/'selection.json')['source_absent_animation_ids'];assert len(absent)==8
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete-available',engine_family='monster_old',animation_ids=ids,models=18,colour_variants=46,resources=217,resource_bindings=218,unique_native_BAM=79,frames=17752,bound_frames=17754,original_native_frames=6917,scale=2,SDF=False,source_absent=absent),
    visual_qa=dict(result='pass',authority='user',user_statement='ok je valide les 2.\ntu peux valider tout ce pack de monstres.\nmet a jour le suivi et committe',individual_scenario_details='not specified by user',explicitly_confirmed=['QOLD7001','QOLD7B06'],accepted_as_installed=True,analysis=identity(analysis/'analysis.json'),analysis_notes=identity(analysis/'README.md'),proposed_ogrillon_and_wolf_retouches_applied=False),
    runtime_contract=dict(runtime=current['runtime'],dll=current['dll'],catalogue_sha256=current['catalog']['sha256'],owner=7,native_render_owners=['MonsterOld'],native_palette_kinds=[0,1],registry_version=7,world_filter='CatmullRom',colour='K6-four-partners-eight-levels/native replacement palettes/rule3',SDF=False,native_geometry=True,installed_runtime_files=runtime_files),
    asset_scope=dict(inventory=identity(inventory),ordering='animation_id,resref ascending; UTF-8 CSV LF, header included in SHA256',physical_leaf_count=217,binding_count=218,catalogue=current['catalog'],physical_leaf_hashes_verified=217,selected_routes_unchanged=True),
    provenance=dict(generation=identity(production/'current-generation.json'),production=gen['production'],original_runtime=gen['runtime'],current_runtime_generation=identity(runtime/'current-generation.json'),current_runtime_installation_snapshot=committed_identity(runtime/'installation-verification.json'),original_asset_installation_snapshot=identity(production/'installation-verification.json'),original_asset_installation_receipt=identity(production/'ingame-installation/active-test.json'),verification=identity(production/'verification.json'),fixtures=identity(production/'creatures.json')),release=False)
p=ROOT/'sprite/index/q3m-work-tracking.json';track=load(p);totals=track['queue_totals']
assert totals['current_recipe_ingame_accepted_families']==10 and totals['current_recipe_ingame_accepted_animation_ids']==89
other=[copy.deepcopy(f) for f in track['families'] if f['engine_section']!='monster_old']
family=next(f for f in track['families'] if f['engine_section']=='monster_old');assert not family['current_full_production']['qa_ingame']
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
visual=dict(state='accepted-full-available-family-V7-no-SDF-as-installed',animation_ids=ids,models=18,colour_variants=46,resources=217,frames=17752,resource_bindings=218,bound_frames=17754,qa_reference=ref,catalogue_sha256=current['catalog']['sha256'],dll_sha256=current['dll']['sha256'],SDF=False)
family['current_full_production'].update(state='family-complete-available-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['current_visual_QA']=visual;family['state']=family['current_full_production']['state']
family['current_installation'].update(state='installed-ingame-accepted',qa_ingame=True,qa_reference=ref)
family['current_colour_witness'].update(state='installed-via-complete-native-palette-family-ingame-accepted',qa_reference=ref)
next(e for e in track['current_recipe_complete_productions'] if e['family']=='monster_old').update(copy.deepcopy(family['current_full_production']))
totals.update(current_recipe_ingame_accepted_families=11,current_recipe_ingame_accepted_animation_ids=135)
track['colour_variants']['state']=track['colour_variants']['state'].replace('Monster_old-V7-no-SDF-installed-ingame-pending','Monster_old-V7-no-SDF-accepted')
assert other==[f for f in track['families'] if f['engine_section']!='monster_old']
assert totals['current_recipe_installed_animation_ids']==136 and totals['current_recipe_complete_families']==12
write_json(p,track)
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    row['queue_state']='current-recipe-complete-installed-ingame-accepted';row['colour_variant_state']=row['colour_variant_state'].replace('installed-ingame-pending','installed-ingame-accepted')
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==ids;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),asset_scope=identity(inventory),accepted_ids=46,accepted_resources=217,accepted_frames=17752,binding_count=218,bound_frames=17754,installed_catalog_sha256=current['catalog']['sha256'],runtime_files_verified=5,fixtures_verified=46,physical_leaf_hashes_verified=217,accepted_families=11,accepted_recipe_ids=135,installed_families=12,installed_recipe_ids=136,retouches_applied=False,release=False))
print(json.dumps(dict(accepted='monster_old',ids=46,resources=217,accepted_families=11,accepted_recipe_ids=135)))
