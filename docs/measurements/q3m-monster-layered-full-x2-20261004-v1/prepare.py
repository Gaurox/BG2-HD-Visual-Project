"""Append complete layered routes to installed accepted guard parent; reuse Volo pilot bytes."""
import sys,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
game=get_path('bg2ee_game_root',required=True);prior=HERE.parent/'q3m-doom-guard-sdf-ingame-x2-20261004-v1'
previous=load(prior/'current-generation.json');prod=load(HERE/'production.json');isolated=ROOT/prod['pack_directory']
assert not (HERE/'baseline.json').exists()
catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game/catalog_relative)==previous['catalog']['sha256'] and file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
parent=registry.read_sealed_catalog_index(game/catalog_relative,previous['catalog']['sha256'])
new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
assert len(new['animations'])==7 and new['total_resources']==65 and new['total_frames']==6422
assert not {a['animation_id'] for a in parent['animations']}&{a['animation_id'] for a in new['animations']}
pilot_gen=load(HERE.parent/'q3m-families-engine-x2-20261003-v2/current-generation.json')
pilot=registry.read_sealed_catalog_index(ROOT/pilot_gen['catalog']['path'],pilot_gen['catalog']['sha256'])
pilot_routes={r['resref']:r for r in pilot['directory'] if r['animation_id']=='0x2100'}
pilot_preserved=[]
for nr in new['directory']:
    if nr['animation_id']=='0x2100' and nr['resref'] in pilot_routes:
        pr=pilot_routes[nr['resref']]
        assert new['shards'][nr['shard_index']]['sha256']==pilot['shards'][pr['shard_index']]['sha256'],('acquired pilot bytes changed',nr['resref'])
        pilot_preserved.append(nr['resref'])
assert len(pilot_preserved)==4
receipt=load(prior/'ingame-installation/active-test.json');assert receipt['catalog_sha256']==previous['catalog']['sha256']
preserved={r['relative_path']:r for r in load(prior/'baseline.json')['preserved'] if r['relative_path']!='InfinityEngine-Enhancer.dll'}
for s in receipt['new_shards']:preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for r in preserved.values():assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower(),r['relative_path']
canonical=ROOT/previous['generation_dir'];out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']];directory=[dict(r) for r in parent['directory']]
animations={a['animation_id']:dict(a,component_indices=list(a['component_indices'])) for a in parent['animations']}
logical=load(canonical/'pack.json')['catalog']['logical_component_digests'][:]
for s in parent['shards']:
    p=canonical/s['registry'];assert p.stat().st_size==s['registry_bytes'];os.link(p,assets/p.name)
old_routes={(r['animation_id'],r['resref']):r for r in parent['directory']};cmap={};reused=[];new_shards=[]
for nr in new['directory']:
    key=(nr['animation_id'],nr['resref']);ci=nr['component_index'];c=new['components'][ci];s=new['shards'][nr['shard_index']]
    if key in old_routes:
        old=old_routes[key];oc=parent['components'][old['component_index']];os_=parent['shards'][old['shard_index']]
        assert c['digest']==oc['digest'] and s['sha256']==os_['sha256'],('Volo pilot bytes changed',key)
        cmap[ci]=old['component_index'];reused.append(key);continue
    info=leaves.inspect(isolated/Path(s['registry']).name,include_frames=True)
    assert info['version']==7 and info['decode_rule_id']==3 and info['class_profile_id'] in (8,9)
    assert all(not {'S','M','A'}&set(f) for r in info['resources'] for f in r['frames'])
    assert file_sha(isolated/Path(s['registry']).name).upper()==s['sha256']
    newci=len(components);newsi=len(shards);cmap[ci]=newci
    components.append(dict(c,index=newci,shard_start=newsi));logical.append(c['digest'])
    ns=dict(s,index=newsi);shards.append(ns);new_shards.append(ns)
    os.link(isolated/Path(s['registry']).name,assets/Path(s['registry']).name)
    directory.append(dict(nr,component_index=newci,shard_index=newsi))
for a in new['animations']:
    mapped=[cmap[i] for i in a['component_indices']]
    if a['animation_id'] in animations:
        old=animations[a['animation_id']];assert set(old['component_indices'])<=set(mapped);old['component_indices']=mapped
    else:animations[a['animation_id']]=dict(a,component_indices=mapped)
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,list(animations.values()),components,shards,directory,logical,
 dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',delta='V7-complete-monster_layered')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
assert checked['components'][:len(parent['components'])]==parent['components'] and checked['shards'][:len(parent['shards'])]==parent['shards']
cr={(r['animation_id'],r['resref']):r for r in checked['directory']};assert all(cr[k]==v for k,v in old_routes.items())
ca={a['animation_id']:a for a in checked['animations']};assert all(ca[a['animation_id']]==a for a in parent['animations'] if a['animation_id']!='0x2100')
assert len(reused)==0 and len(new_shards)==65 and len(checked['animations'])==154 and checked['total_resources']==6753
source_names={r['resref']+'.BAM' for r in new['directory']}|{a['animation_id'][2:]+'.INI' for a in new['animations']}
assert not source_names&{p.name.upper() for p in (game/'override').iterdir()}
proof=dict(inherited_routes_unchanged=len(parent['directory']),inherited_components_unchanged=len(parent['components']),
 inherited_other_animations_unchanged=147,reused_installed_bindings=reused,acquired_uninstalled_Volo_pilot_leaves_byte_identical=pilot_preserved,new_leaf_files=len(new_shards),new_animation_ids=[a['animation_id'] for a in new['animations']],
 complete_family_animation_ids=[a['animation_id'] for a in new['animations']],active_animations=len(checked['animations']),active_resources=checked['total_resources'],active_frames=checked['total_frames'],active_routes=len(checked['directory']),SDF=False,ingame_QA=False,release=False)
write_json(out/'pack.json',dict(schema='bg2-layered-combined-pack-v1',catalog=combined,new_shards=new_shards,proof=proof))
write_json(HERE/'catalog-proof.json',proof)
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=catalog_relative,parent_catalog_sha256=previous['catalog']['sha256'],dll_sha256=previous['dll']['sha256'],preserved=list(preserved.values()),source_names=sorted(source_names)))
runtime=dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id=HERE.name,base_commit='16b01e52',inherited_runtime=previous['runtime'],
 capability_delta=dict(additional_render_rva='0x32f3b0',additional_vtable_rva='0x5aa840',owner=8,composite=True,hook_count=10,only_family='monster_layered'),
 dll=identity(WORK/'runtime-build/Release/InfinityEngine-Enhancer.dll'),source_provenance=[identity(WORK/'runtime-src'/p) for p in ['src/iee/creature_sprite_x2.cpp','src/iee/creature_sprite_x2.h','src/iee/hooks.cpp','src/iee/game/build_manifest.cpp','src/iee/game/build_manifest.h']],runtime_patch=identity(HERE/'runtime-delta.patch'),ingame_QA=False,release=False)
write_json(HERE/'runtime.json',runtime)
write_json(HERE/'current-generation.json',dict(schema='bg2-layered-Q3m-V7-current-v1',role='production-not-QA-installation-or-release',family='monster_layered',animation_ids=proof['complete_family_animation_ids'],resources=65,frames=6422,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,SDF=False,generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),production=identity(HERE/'production.json'),runtime=identity(HERE/'runtime.json'),dll=runtime['dll'],parent_generation=identity(prior/'current-generation.json'),ingame_QA=False,release=False))
print(json.dumps(proof),flush=True)
