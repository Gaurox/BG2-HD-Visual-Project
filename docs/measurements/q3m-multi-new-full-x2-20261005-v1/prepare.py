"""Append all ten MultiNew IDs to installed MonsterOld, preserving acquired bytes."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
game=get_path('bg2ee_game_root',required=True);prior=HERE.parent/'q3m-monster-old-full-x2-20261004-v1';previous=load(prior/'current-generation.json')
assert load(HERE/'runtime-route.json')['passed'] and not (HERE/'baseline.json').exists()
catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game/catalog_relative)==previous['catalog']['sha256'] and file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
prod=load(HERE/'production.json');isolated=ROOT/prod['pack_directory']
parent=registry.read_sealed_catalog_index(game/catalog_relative,previous['catalog']['sha256'])
new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
assert len(new['animations'])==10 and len(new['directory'])==5155 and prod['pack']['logical_resource_bindings']==5155
assert not {a['animation_id'] for a in parent['animations']}&{a['animation_id'] for a in new['animations']}
preserved={r['relative_path']:r for r in load(prior/'baseline.json')['preserved']}
receipt=load(prior/'ingame-installation/active-test.json')
for s in receipt['new_shards']:preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for f in receipt['fixtures']:preserved[f['target']]=dict(relative_path=f['target'],sha256=f['sha256'])
for r in preserved.values():assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower(),r['relative_path']
canonical=ROOT/previous['generation_dir'];out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']];directory=[dict(r) for r in parent['directory']];animations=[dict(a) for a in parent['animations']]
logical=load(canonical/'pack.json')['catalog']['logical_component_digests'][:]
for s in parent['shards']:
    p=canonical/s['registry'];assert p.stat().st_size==s['registry_bytes'];os.link(p,assets/p.name)
ci,si=len(components),len(shards);new_shards=[]
for s in new['shards']:
    p=isolated/Path(s['registry']).name;assert file_sha(p).upper()==s['sha256'];info=leaves.inspect(p,include_frames=True)
    assert info['version']==7 and info['class_profile_id']==8 and info['decode_rule_id']==3
    assert all(not {'S','M','A'}&set(f) for r in info['resources'] for f in r['frames'])
    os.link(p,assets/p.name);ns=dict(s,index=si+s['index']);shards.append(ns);new_shards.append(ns)
components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components']);logical.extend(c['digest'] for c in new['components'])
animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in new['animations'])
directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in new['directory'])
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',delta='V7-complete-native-multi_new-contextual')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
assert checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards']
rr={(r['animation_id'],r['resref']):r for r in checked['directory']};assert all(rr[(r['animation_id'],r['resref'])]==r for r in parent['directory'])
aa={a['animation_id']:a for a in checked['animations']};assert all(aa[a['animation_id']]==a for a in parent['animations'])
assert len(checked['animations'])==217 and len(checked['directory'])==60888
selection=load(HERE/'selection.json');source_names={r['resref']+'.BAM' for r in new['directory']}|{a['animation_id'][2:]+'.INI' for a in new['animations']}|{o['resref']+'.BMP' for w in selection['witnesses'] for o in w.get('palette_overrides_by_bank',{}).values()}
assert not source_names&{p.name.upper() for p in (game/'override').iterdir()}
proof=dict(inherited_routes_unchanged=len(parent['directory']),inherited_components_unchanged=ci,inherited_other_animations_unchanged=len(parent['animations']),new_leaf_files=new['total_resources'],logical_resource_bindings=5155,bound_frames=519867,shared_resource_bindings=prod['pack']['shared_resource_bindings'],new_animation_ids=[a['animation_id'] for a in new['animations']],complete_family_animation_ids=[a['animation_id'] for a in new['animations']],source_absent_animation_ids=[],active_animations=217,active_resources=checked['total_resources'],active_frames=checked['total_frames'],active_routes=60888,SDF=False,ingame_QA=False,release=False)
write_json(out/'pack.json',dict(schema='bg2-multi-new-combined-pack-v1',catalog=combined,new_shards=new_shards,proof=proof));write_json(HERE/'catalog-proof.json',proof)
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=catalog_relative,parent_catalog_sha256=previous['catalog']['sha256'],dll_sha256=previous['dll']['sha256'],preserved=list(preserved.values()),source_names=sorted(source_names)))
write_json(HERE/'current-generation.json',dict(schema='bg2-multi-new-Q3m-V7-current-v1',role='production-not-QA-installation-or-release',family='multi_new',animation_ids=proof['complete_family_animation_ids'],resources=new['total_resources'],logical_resource_bindings=5155,bound_frames=519867,unique_native_BAM=1753,frames=new['total_frames'],original_native_frames=191817,models=4,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,SDF=False,generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),production=identity(HERE/'production.json'),runtime=previous['runtime'],runtime_route=identity(HERE/'runtime-route.json'),dll=previous['dll'],parent_generation=identity(prior/'current-generation.json'),DLL_unchanged=True,ingame_QA=False,release=False))
print(json.dumps(proof),flush=True)
