"""Accept the complete Ogre world family on explicit user authority; no install."""
import copy,csv,datetime,hashlib,io,json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
def committed_identity(p):
    relative=p.relative_to(ROOT).as_posix();raw=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
    assert p.read_bytes().replace(b'\r\n',b'\n')==raw.replace(b'\r\n',b'\n')
    return dict(path=relative,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),serialization='Git HEAD blob; working copy equivalent modulo CRLF')
production=HERE.parent/'q3m-monster-large-full-x2-20261003-v1'
runtime=HERE.parent/'q3m-multi-new-frame-stability-20261005-v2'
gen=load(production/'current-generation.json');current=load(runtime/'current-generation.json');game=get_path('bg2ee_game_root',required=True)
ids=gen['animation_ids'];assert ids==['0x9000'] and gen['scale']==2
qa_path=ROOT/'sprite/index/qa-decisions/monster_large/2026-10-05-accepted-full-ogre-q3m-v7-x2-catmullrom-v1.json'
assert not qa_path.exists()
catalog=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',current['catalog']['sha256'])
selected=registry.read_sealed_catalog_index(ROOT/gen['catalog']['path'],gen['catalog']['sha256'])
routes=sorted((r for r in catalog['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
assert routes==sorted((r for r in selected['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
shards=[catalog['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
assert len(routes)==len(shards)==7 and sum(s['frame_count'] for s in shards)==434
for s in shards:
    p=game/s['registry'];assert file_sha(p).lower()==s['sha256'].lower()
    d=leaves.inspect(p,include_frames=True);assert d['version']==7 and d['class_profile_id']==9 and all(not {'S','M','A'}&set(f) for r in d['resources'] for f in r['frames'])
creatures=load(production/'creatures.json')['creatures'];assert len(creatures)==22
index=registry.KeyIndex(game);entries=index.resource_map(1009)
for c in creatures:
    p=game/'override'/(c['resref']+'.cre');raw=p.read_bytes() if p.exists() else index.resolve(entries[c['resref']])[0]
    assert hashlib.sha256(raw).hexdigest()==c['sha256'] and struct.unpack_from('<I',raw,0x28)[0]==0x9000
baseline=load(runtime/'baseline.json');expected={r['relative_path']:r['sha256'] for r in baseline['preserved']}
expected['InfinityEngine-Enhancer.dll']=current['dll']['sha256'];runtime_files=[]
for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):
    sha=file_sha(game/name);assert sha.lower()==expected[name].lower();runtime_files.append(dict(relative_path=name,sha256=sha))
assert all(r['passed'] for r in load(production/'installation-verification.json')['native_tests'].values())
inventory=HERE/'asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as output:
    writer=csv.writer(output,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
    for r in routes:
        s=catalog['shards'][r['shard_index']];writer.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],s['frame_count'],r['resource_ordinal']])
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    scope=dict(kind='installed-native-family-complete-world',engine_family='monster_large',animation_ids=ids,models=1,creature_consumers=22,resources=7,resource_bindings=7,frames=434,scale=2,SDF=False,source_absent=[],inventory_resource='MOGRINV produced; dedicated UI QA not claimed'),
    visual_qa=dict(result='pass',authority='user',user_statement="l'ogre est validé? il est indiqué toujours en attente de QA ! je veux toute la famille validée QA si c'est pas déja le cas",individual_scenario_details='not specified by user',individual_creature_spawn_tests='not claimed; 22 consumers share one accepted avatar',accepted_as_installed=True),
    runtime_contract=dict(runtime=committed_identity(ROOT/current['runtime']['path']),dll=current['dll'],catalogue_sha256=current['catalog']['sha256'],owner=10,native_render_owners=['MonsterLarge'],native_palette_kinds=[1],registry_version=7,world_filter='CatmullRom',colour='K6-four-partners-eight-levels/rule3',SDF=False,native_geometry=True,installed_runtime_files=runtime_files),
    asset_scope=dict(inventory=identity(inventory),ordering='animation_id,resref ascending; UTF-8 CSV LF, header included in SHA256',physical_leaf_count=7,binding_count=7,catalogue=current['catalog'],physical_leaf_hashes_verified=7,selected_routes_unchanged=True),
    provenance=dict(generation=committed_identity(production/'current-generation.json'),production=committed_identity(ROOT/gen['production']['path']),original_runtime=committed_identity(ROOT/gen['runtime']['path']),current_runtime_generation=committed_identity(runtime/'current-generation.json'),current_runtime_installation_snapshot=committed_identity(runtime/'installation-verification.json'),original_asset_installation_snapshot=committed_identity(production/'installation-verification.json'),original_asset_installation_receipt=identity(production/'ingame-installation/active-test.json'),host_tests=committed_identity(production/'host-tests.json'),creatures=committed_identity(production/'creatures.json')),release=False)
p=ROOT/'sprite/index/q3m-work-tracking.json';track=load(p);totals=track['queue_totals']
assert totals['current_recipe_ingame_accepted_families']==11 and totals['current_recipe_ingame_accepted_animation_ids']==135
other=[copy.deepcopy(f) for f in track['families'] if f['engine_section']!='monster_large']
family=next(f for f in track['families'] if f['engine_section']=='monster_large');assert not family['current_full_production']['qa_ingame']
write_json(qa_path,qa);ref=qa_path.relative_to(ROOT).as_posix()
visual=dict(state='accepted-full-family-world-V7-no-SDF-as-installed',animation_ids=ids,models=1,creature_consumers=22,resources=7,frames=434,qa_reference=ref,catalogue_sha256=current['catalog']['sha256'],dll_sha256=current['dll']['sha256'],SDF=False)
family['current_full_production'].update(state='family-complete-produced-installed-ingame-accepted',qa_ingame=True,qa_reference=ref,visual_QA=visual)
family['current_visual_QA']=visual;family['state']=family['current_full_production']['state']
family['current_installation']=dict(state='installed-ingame-accepted',reference=family['current_full_production']['installation_snapshot'],receipt=family['current_full_production']['installation_reference'],animation_ids=ids,qa_ingame=True,qa_reference=ref,SDF=False)
family['current_colour_witness'].update(state='installed-via-complete-native-palette-family-ingame-accepted',qa_reference=ref)
next(e for e in track['current_recipe_complete_productions'] if e['family']=='monster_large').update(copy.deepcopy(family['current_full_production']))
totals.update(current_recipe_ingame_accepted_families=12,current_recipe_ingame_accepted_animation_ids=136)
track['colour_variants']['state']=track['colour_variants']['state'].replace('Ogre-installed','Ogre-V7-no-SDF-accepted')
assert other==[f for f in track['families'] if f['engine_section']!='monster_large']
assert totals['current_recipe_installed_animation_ids']==136 and totals['current_recipe_complete_families']==12
write_json(p,track)
p=ROOT/'sprite/index/q3m-work-items.csv';raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines(keepends=True);fields=next(csv.reader([lines[0]]));out=[lines[0]];changed=[]
for line in lines[1:]:
    row=dict(zip(fields,next(csv.reader([line]))))
    if row['animation_id'] not in ids:out.append(line);continue
    row['queue_state']='current-recipe-complete-installed-ingame-accepted';row['colour_variant_state']='v7-family-complete-installed-ingame-accepted'
    stream=io.StringIO(newline='');csv.DictWriter(stream,fields,lineterminator='\r\n' if line.endswith('\r\n') else '\n').writerow(row);out.append(stream.getvalue());changed.append(row['animation_id'])
assert changed==ids;p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(out).encode('utf-8'))
write_json(HERE/'acceptance-summary.json',dict(qa=identity(qa_path),asset_scope=identity(inventory),accepted_ids=1,creature_consumers=22,accepted_resources=7,accepted_frames=434,installed_catalog_sha256=current['catalog']['sha256'],runtime_files_verified=5,creature_identities_verified=22,physical_leaf_hashes_verified=7,accepted_families=12,accepted_recipe_ids=136,installed_families=12,installed_recipe_ids=136,release=False))
print(json.dumps(dict(accepted='monster_large',ids=1,creatures=22,resources=7,accepted_families=12,accepted_recipe_ids=136)))
