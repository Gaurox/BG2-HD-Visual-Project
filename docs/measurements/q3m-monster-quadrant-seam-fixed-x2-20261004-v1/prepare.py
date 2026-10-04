"""Replace only the existing seven Quadrant components, preserve native runtime."""
from common import *
from workspace_paths import get_path
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
game=get_path('bg2ee_game_root',required=True);prod=load(HERE/'production.json');oldroot=ROOT/GEN['generation_dir']
catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game/catalog_relative)==GEN['catalog']['sha256'] and file_sha(game/'InfinityEngine-Enhancer.dll')==GEN['dll']['sha256']
parent=registry.read_sealed_catalog_index(game/catalog_relative,GEN['catalog']['sha256']);isolated=ROOT/prod['pack_directory']
delta=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
assert delta['total_resources']==132 and delta['total_frames']==12928 and len(delta['animations'])==7
ids={a['animation_id'] for a in delta['animations']};assert ids==set(GEN['animation_ids'])
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']];directory=[dict(d) for d in parent['directory']];animations=[dict(a) for a in parent['animations']]
logical=load(oldroot/'pack.json')['catalog']['logical_component_digests'][:]
out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
routes={(r['animation_id'],r['resref']):r for r in parent['directory']};replaced=set();delta_shards=[]
for d in delta['directory']:
    key=(d['animation_id'],d['resref']);old=routes[key];ci=old['component_index'];si=old['shard_index']
    c=dict(delta['components'][d['component_index']],index=ci,shard_start=si)
    s=dict(delta['shards'][d['shard_index']],index=si)
    assert all(old[k]==d[k] for k in ('resource_ordinal',))
    p=isolated/Path(s['registry']).name;assert file_sha(p).upper()==s['sha256'];info=leaves.inspect(p,include_frames=False)
    assert info['version']==7 and info['class_profile_id']==8 and info['decode_rule_id']==3
    dest=assets/p.name
    if not dest.exists():os.link(p,dest)
    components[ci]=c;shards[si]=s;logical[ci]=c['digest'];replaced.add(ci);delta_shards.append(s)
for s in parent['shards']:
    if s['index'] in replaced:continue
    p=oldroot/s['registry'];assert p.stat().st_size==s['registry_bytes'];dest=assets/p.name
    if not dest.exists():os.link(p,dest)
assert len(replaced)==132
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',delta='V7-contextual-four-native-pixel-seam-repair')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
assert checked['directory']==parent['directory'] and checked['animations']==parent['animations']
assert all(checked['components'][i]==c and checked['shards'][i]==parent['shards'][i] for i,c in enumerate(parent['components']) if i not in replaced)
assert len(checked['animations'])==161 and checked['total_resources']==6885 and checked['total_frames']==1705675 and len(checked['directory'])==55515
receipt=load(PARENT/'ingame-installation/active-test.json');preserved={r['relative_path']:r for r in receipt['preserved_files']}
for s in receipt['new_shards']:preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for f in receipt['fixtures']:preserved[f['target']]=dict(relative_path=f['target'],sha256=f['sha256'])
preserved['InfinityEngine-Enhancer.dll']=dict(relative_path='InfinityEngine-Enhancer.dll',sha256=GEN['dll']['sha256'])
for r in preserved.values():assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower(),r['relative_path']
proof=dict(replaced_quadrant_components=132,inherited_other_components_unchanged=6753,all_routes_unchanged=55515,all_animation_memberships_unchanged=161,active_resources=6885,active_frames=1705675,animation_ids=GEN['animation_ids'],DLL_unchanged=True,shader_INI_unchanged=True,SDF=False,ingame_QA=False,release=False)
write_json(out/'pack.json',dict(schema='bg2-quadrant-seam-combined-pack-v1',catalog=combined,new_shards=delta_shards,proof=proof));write_json(HERE/'catalog-proof.json',proof)
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=catalog_relative,parent_catalog_sha256=GEN['catalog']['sha256'],dll_sha256=GEN['dll']['sha256'],preserved=list(preserved.values()),source_names=load(PARENT/'baseline.json')['source_names']))
gen=dict(GEN,schema='bg2-quadrant-Q3m-V7-seam-current-v1',generation_dir=relative(out),catalog=identity(assets/'CreatureSprites-XN.catalog'),production=identity(HERE/'production.json'),parent_generation=identity(PARENT/'current-generation.json'),seam_repair=identity(HERE/'recipe.json'),ingame_QA=False,release=False)
write_json(HERE/'current-generation.json',gen);write_json(HERE/'creatures.json',load(PARENT/'creatures.json'))
(HERE/'CLUA.txt').write_bytes((PARENT/'CLUA.txt').read_bytes());print(json.dumps(proof),flush=True)
