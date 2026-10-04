"""Append Ambient to the installed accepted Town parent; preserve horse-v3 and every acquired leaf."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
assert not (HERE/'baseline.json').exists()
game=get_path('bg2ee_game_root',required=True)
prior=ROOT/'docs/measurements/q3m-town-static-full-x2-20261004-v1'
previous=load(prior/'current-generation.json'); previous_baseline=load(prior/'baseline.json')
production=load(HERE/'production.json'); isolated=ROOT/production['pack_directory']
out=isolated.parent/'combined'; assets=out/'iee-assets/creature-sprites'
catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game/catalog_relative)==previous['catalog']['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
parent=registry.read_sealed_catalog_index(game/catalog_relative,previous['catalog']['sha256'])
new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
assert len(new['animations'])==18 and new['total_resources']==34 and new['total_frames']==2580
assert not {a['animation_id'] for a in parent['animations']} & {a['animation_id'] for a in new['animations']}
selection=load(HERE/'selection.json'); refs={r for w in selection['witnesses'] for r in w['refs']}
source_names={r+'.BAM' for r in refs}|{w['animation_id'][2:]+'.INI' for w in selection['witnesses']}
assert not source_names & {p.name.upper() for p in (game/'override').iterdir()}
receipt=load(prior/'ingame-installation/active-test.json')
assert receipt['status']=='installed-pending-ingame-qa'
preserved={r['relative_path']:r for r in previous_baseline['preserved']}
for s in receipt['new_shards']:
    preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for f in receipt['fixtures']:
    preserved[f['target']]=dict(relative_path=f['target'],sha256=f['sha256'])
qa=ROOT/'sprite/index/qa-decisions/town_static/2026-10-04-accepted-full-available-town-static-q3m-v7-x2-catmullrom-v1.json'
accepted=load(qa)
assert accepted['status']=='accepted' and accepted['runtime_contract']['catalogue_sha256']==previous['catalog']['sha256']
for s in accepted['resources']:
    preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for r in preserved.values():assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower(),r['relative_path']
canonical=ROOT/previous['generation_dir']; assets.mkdir(parents=True)
for s in parent['shards']:
    source=canonical/s['registry']; assert source.is_file() and source.stat().st_size==s['registry_bytes']
    os.link(source,assets/source.name)
ci,si=len(parent['components']),len(parent['shards'])
components=[dict(c) for c in parent['components']]; shards=[dict(s) for s in parent['shards']]
animations=[dict(a) for a in parent['animations']]; directory=[dict(r) for r in parent['directory']]
for s in new['shards']:
    source=isolated/Path(s['registry']).name; assert file_sha(source).upper()==s['sha256']
    info=leaves.inspect(source,include_frames=True)
    assert info['version']==7 and info['decode_rule_id']==3 and info['class_profile_id'] in (8,9)
    assert all(not ({'S','M','A'} & set(f)) for r in info['resources'] for f in r['frames'])
    os.link(source,assets/source.name)
    shards.append(dict(s,index=si+s['index']))
components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components'])
animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in new['animations'])
directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in new['directory'])
logical=load(canonical/'pack.json')['catalog']['logical_component_digests']+[c['digest'] for c in new['components']]
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
    dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',delta='V7-complete-ambient')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
assert checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards']
checked_animations={a['animation_id']:a for a in checked['animations']}
assert all(checked_animations[a['animation_id']]==a for a in parent['animations'])
old_routes={(r['animation_id'],r['resref']):r for r in parent['directory']}
checked_routes={(r['animation_id'],r['resref']):r for r in checked['directory']}
assert all(checked_routes[k]==v for k,v in old_routes.items())
assert len(checked['animations'])==140 and checked['total_resources']==4670 and checked['total_frames']==1593131 and len(checked['directory'])==50356
proof=dict(inherited_animations_unchanged=len(parent['animations']),inherited_routes_unchanged=len(parent['directory']),
    inherited_components_and_shards_unchanged=ci,new_animation_ids=[a['animation_id'] for a in new['animations']],
    new_owner=12,new_resources=34,new_frames=2580,logical_resource_bindings=39,shared_resource_bindings=5,source_absent_animation_ids=selection['source_absent_animation_ids'],
    active_animations=len(checked['animations']),active_resources=checked['total_resources'],active_frames=checked['total_frames'],
    active_routes=len(checked['directory']),accepted_town_static_resources_preserved=18,accepted_QA=identity(qa),
    SDF=False,ingame_QA=False,release=False)
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=catalog_relative,
    parent_catalog_sha256=previous['catalog']['sha256'],dll_sha256=previous['dll']['sha256'],
    ini_sha256=file_sha(game/'InfinityEngine-Enhancer.ini'),preserved=list(preserved.values()),source_names=sorted(source_names),accepted_QA=identity(qa)))
write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(schema='bg2-ambient-mixed-pack-v1',catalog=combined,new_shards=shards[si:],proof=proof))
write_json(HERE/'current-generation.json',dict(schema='bg2-ambient-Q3m-V7-current-v1',
    role='production-not-QA-installation-or-release',family='ambient',animation_ids=proof['new_animation_ids'],
    resources=34,frames=2580,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,SDF=False,
    source_absent_animation_ids=selection['source_absent_animation_ids'],generation_dir=out.relative_to(ROOT).as_posix(),
    catalog=identity(assets/'CreatureSprites-XN.catalog'),production=identity(HERE/'production.json'),
    runtime=previous['runtime'],dll=previous['dll'],parent_generation=identity(prior/'current-generation.json'),
    ingame_QA=False,release=False))
print(json.dumps(dict(**proof,preserved_installed_files=len(preserved))))
