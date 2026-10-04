"""Append dependencies, extend only the seven old-character memberships; preserve all parent routes/leaves."""
import copy,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
game=get_path('bg2ee_game_root',required=True);prior=ROOT/'docs/measurements/q3m-character-old-full-x2-20261004-v1'
previous=load(prior/'current-generation.json');production=load(HERE/'production.json');delta=ROOT/production['pack_directory']
assert not (HERE/'current-generation.json').exists()
parent_root=ROOT/previous['generation_dir'];out=delta.parent/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
parent=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',previous['catalog']['sha256'])
new=registry.read_sealed_catalog_index(delta/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
ci,si=len(parent['components']),len(parent['shards']);components=copy.deepcopy(parent['components']);shards=copy.deepcopy(parent['shards'])
for shard in parent['shards']:
    source=parent_root/shard['registry'];assert source.stat().st_size==shard['registry_bytes'];os.link(source,assets/source.name)
for shard in new['shards']:
    source=delta/Path(shard['registry']).name;assert file_sha(source).upper()==shard['sha256']
    os.link(source,assets/source.name);shards.append(dict(shard,index=si+shard['index']))
components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components'])
animations=copy.deepcopy(parent['animations']);directory=copy.deepcopy(parent['directory']);byref={r['resref']:r for r in new['directory']}
byid={a['animation_id']:a for a in animations};consumers=production['plan']['consumers']
for aid,refs in consumers.items():
    for ref in refs:
        r=byref[ref];directory.append(dict(r,animation_id=aid,component_index=ci+r['component_index'],shard_index=si+r['shard_index']))
    byid[aid]['component_indices']=sorted(set(byid[aid]['component_indices'])|{ci+byref[r]['component_index'] for r in refs})
logical=load(parent_root/'pack.json')['catalog']['logical_component_digests']+[c['digest'] for c in new['components']]
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
    dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',delta='V7-character-old-native-dependencies')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
assert checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards']
routes={(r['animation_id'],r['resref']):r for r in checked['directory']}
assert all(routes[(r['animation_id'],r['resref'])]==r for r in parent['directory'])
assert all(next(a for a in checked['animations'] if a['animation_id']==old['animation_id'])==old for old in parent['animations'] if old['animation_id'] not in consumers)
assert len(checked['animations'])==147 and checked['total_resources']==5736 and checked['total_frames']==1642525
preserved={r['relative_path']:r for r in load(prior/'baseline.json')['preserved']}
receipt=load(prior/'ingame-installation/active-test.json');assert receipt['catalog_sha256']==previous['catalog']['sha256']
for s in receipt['new_shards']:preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for f in receipt['fixtures']:preserved[f['target']]=dict(relative_path=f['target'],sha256=f['sha256'])
for r in preserved.values():assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
proof=dict(parent_routes_unchanged=len(parent['directory']),parent_components_unchanged=ci,unaffected_animations_unchanged=140,
    body_resources_unchanged=99,body_frames_unchanged=4725,additional_resources=len(new['shards']),additional_frames=new['total_frames'],
    additional_bindings=sum(map(len,consumers.values())),active_animations=147,active_resources=checked['total_resources'],
    active_frames=checked['total_frames'],active_routes=len(checked['directory']),SDF=False,ingame_QA=False,release=False)
source_names=load(prior/'baseline.json')['source_names']+[r+'.BAM' for r in byref]
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog',parent_catalog_sha256=previous['catalog']['sha256'],preserved=list(preserved.values()),source_names=sorted(set(source_names))))
write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(schema='bg2-character-old-native-dependencies-pack-v1',catalog=combined,new_shards=shards[si:],proof=proof))
write_json(HERE/'current-generation.json',dict(previous,schema='bg2-character-old-Q3m-V7-dependencies-current-v1',resources=1066,frames=49394,body_resources=99,body_frames=4725,generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),parent_generation=identity(prior/'current-generation.json'),body_production=previous['production'],production=identity(HERE/'production.json'),additional_resources=967,additional_frames=44669,additional_bindings=proof['additional_bindings'],runtime_fix='native-shadow-and-equipment-registered',ingame_QA=False,release=False))
print(json.dumps(proof))
