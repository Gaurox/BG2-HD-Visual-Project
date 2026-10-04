"""Replace only the two horse leaf bindings; preserve every other catalogue entry."""
import json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as reg
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
game=get_path('bg2ee_game_root',required=True);base=ROOT/'docs/measurements/q3m-ambient-static-full-x2-20261004-v1'
old=load(base/'current-generation.json');production=load(HERE/'production.json');oldpack=ROOT/old['generation_dir'];isolated=ROOT/production['pack_directory']
catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game/catalog_relative)==old['catalog']['sha256']
parent=reg.read_sealed_catalog_index(game/catalog_relative,old['catalog']['sha256'])
new=reg.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
assert len(new['directory'])==2 and {r['resref'] for r in new['directory']}=={'AHRSG1','AHRSG1E'}
out=isolated.parent/'combined';assets=out/'iee-assets/creature-sprites';assert not out.exists();assets.mkdir(parents=True)
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']]
animations=[dict(a) for a in parent['animations']];directory=[dict(r) for r in parent['directory']]
new_shards=[];replaced=[]
for route in new['directory']:
 target=next(r for r in directory if r['animation_id']=='0xB100' and r['resref']==route['resref'])
 ci,si=target['component_index'],target['shard_index'];assert target['resource_ordinal']==0
 s=dict(new['shards'][route['shard_index']],index=si);c=dict(new['components'][route['component_index']],index=ci,shard_start=si)
 assert s['frame_count']==parent['shards'][si]['frame_count']
 shards[si]=s;components[ci]=c;new_shards.append(s);replaced.append(dict(resref=route['resref'],component_index=ci,shard_index=si,old_sha256=parent['shards'][si]['sha256'],new_sha256=s['sha256']))
for s in shards:
 source=(isolated/Path(s['registry']).name) if s in new_shards else oldpack/s['registry']
 assert source.is_file() and source.stat().st_size==s['registry_bytes'];os.link(source,assets/source.name)
logical=[c['digest'] for c in components]
combined=reg.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
 dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',horse='V7-native-eye-I-F0-local-v1')))
checked=reg.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
assert checked['directory']==parent['directory'] and checked['animations']==parent['animations']
assert all(checked['shards'][i]==s for i,s in enumerate(parent['shards']) if i not in {r['shard_index'] for r in replaced})
assert all(checked['components'][i]==c for i,c in enumerate(parent['components']) if i not in {r['component_index'] for r in replaced})
oldbase=load(base/'baseline.json');receipt=load(base/'ingame-installation/active-test.json')
preserved={r['relative_path']:r for r in oldbase['preserved']}
for s in receipt['new_shards']:
 if s['sha256'] not in {r['old_sha256'] for r in replaced}:preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for f in receipt['fixtures']:preserved[f['target']]=dict(relative_path=f['target'],sha256=f['sha256'])
for r in preserved.values():assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower()
qa=ROOT/'sprite/index/qa-decisions/ambient_static/2026-10-04-accepted-12-models-except-horse-q3m-v7-x2-catmullrom-v1.json'
proof=dict(inherited_animations_unchanged=104,inherited_routes_unchanged=50299,replaced_resources=replaced,new_resources=2,new_frames=44,active_animations=104,active_resources=4618,active_frames=1589008,active_routes=50299,unchanged_other_shards=4616,accepted_ambient_static_resources_preserved=24,accepted_ambient_static_QA=identity(qa),SDF=False,ingame_QA=False,release=False)
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=catalog_relative,parent_catalog_sha256=old['catalog']['sha256'],dll_sha256=oldbase['dll_sha256'],ini_sha256=oldbase['ini_sha256'],preserved=list(preserved.values()),source_names=['B100.INI','AHRSG1.BAM','AHRSG1E.BAM'],accepted_QA=identity(qa)))
write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(catalog=combined,new_shards=new_shards,proof=proof))
write_json(HERE/'current-generation.json',dict(schema='bg2-horse-native-eye-Q3m-V7-v1',role='production-not-QA-installation-or-release',family='ambient_static',animation_ids=['0xB100'],resources=2,frames=44,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,SDF=False,recipe='native-eye-2x2-I-exact-F0-local-v1',generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),production=identity(HERE/'production.json'),runtime=old['runtime'],dll=old['dll'],ingame_QA=False,release=False))
write_json(HERE/'creatures.json',dict(fixtures=[],representatives=[dict(resref='HORSE',animation_id='0xB100',clua='C:CreateCreature("HORSE")')]))
print(json.dumps(proof))
