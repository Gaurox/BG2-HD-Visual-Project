"""Append complete Ankheg to the installed flying catalog; preserve keyed native routes."""
import configparser,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
def require(ok,message):
    if not ok:raise ValueError(message)
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
def result(path):return next(json.loads(line) for line in reversed(path.read_text(encoding='utf-8',errors='replace').splitlines()) if line.startswith('{'))
def keyed(rows,fields):
    mapping={tuple(row[f] for f in fields):row for row in rows}
    require(len(mapping)==len(rows),'duplicate native key');return mapping

game=get_path('bg2ee_game_root',required=True)
work=ROOT/'sprite/.work/q3m-monster-ankheg-full-x2-20261003-v1';isolated=work/'isolated'
out=work/'combined';assets=out/'iee-assets/creature-sprites'
require(not out.exists() and not (HERE/'baseline.json').exists(),'new run required')
production=load(HERE/'production.json')
require(production['pack']['resources']==12 and production['pack']['frames']==516,'Ankheg scope differs')
require(result(work/'native-isolated-tests.log')['passed'],'isolated native check absent')
previous_dir=ROOT/'docs/measurements/q3m-flying-full-x2-20261003-v1'
previous=load(previous_dir/'current-generation.json');canonical=ROOT/previous['generation_dir']
parent_sha=file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')
require(parent_sha==previous['catalog']['sha256'],'active parent differs from acquired flying catalog')
parent=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',parent_sha)
pmeta=load(canonical/'pack.json')['catalog'];runtime=load(ROOT/previous['runtime']['path'])
require(file_sha(game/'BaldurReal.exe').upper()==runtime['game_profile']['baldur_real_sha256'],'unknown executable')
require(file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256'],'active runtime changed')
ids=['0x3000'];refs=load(HERE/'selection.json')['witnesses'][0]['refs']
require(len(parent['animations'])==87 and parent['total_resources']==4560 and parent['total_frames']==1585656
        and len(parent['directory'])==50241 and not any(a['animation_id'] in ids for a in parent['animations']),'unexpected parent coverage')
config=configparser.ConfigParser(interpolation=None,strict=False);config.read(game/'InfinityEngine-Enhancer.ini')
expected=dict(EnableCreatureSpriteUpscaleTest='true',EnableCreatureSpriteX2Test='false',EnableCreatureSpriteLinearFiltering='false',CreatureSpriteFilter='Box',CreatureSpriteFilterAnimation='0x0')
require(all(config.get('Shaders',k)==v for k,v in expected.items()),'world configuration differs')
collisions=[p.name for p in (game/'override').iterdir() if p.is_file() and p.name.upper() in {'3000.INI',*(r+'.BAM' for r in refs)}]
require(not collisions,'Ankheg source override collision: '+str(collisions))
preserved=[]
for entry in runtime['shaders']+runtime['preserved_packs']+runtime['paperdoll_packs']:
    path=game/entry['target'];preserved.append(dict(relative_path=entry['target'],bytes=path.stat().st_size,sha256=file_sha(path)))
qa_path=ROOT/'sprite/index/qa-decisions/flying/2026-10-03-accepted-full-flying-q3m-v7-k6-x2-box-v1.json'
qa=load(qa_path);require(qa['runtime_contract']['dll']==previous['dll'] and qa['runtime_contract']['runtime']==previous['runtime']
    and qa['runtime_contract']['ini_sha256']==file_sha(game/'InfinityEngine-Enhancer.ini'),'accepted flying runtime differs')
for leaf in qa['resources']:
    require(file_sha(game/leaf['registry'])==leaf['sha256']==file_sha(canonical/leaf['registry']),'accepted flying bytes differ')
baseline=dict(schema='bg2-ankheg-install-baseline-v1',game_root='config://bg2ee_game_root',
    executable_sha256=file_sha(game/'BaldurReal.exe'),parent_catalog_sha256=parent_sha,
    catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog',ini_sha256=file_sha(game/'InfinityEngine-Enhancer.ini'),
    dll_sha256=file_sha(game/'InfinityEngine-Enhancer.dll'),parent_animations=87,parent_resources=4560,
    parent_frames=parent['total_frames'],parent_routes=len(parent['directory']),box_configuration=expected,preserved=preserved,
    inherited_flying_qa=identity(qa_path),inherited_accepted_leaves=qa['resources'])
assets.mkdir(parents=True)
for shard in parent['shards']:
    source=canonical/shard['registry'];live=game/shard['registry']
    require(source.is_file() and live.is_file() and source.stat().st_size==live.stat().st_size==shard['registry_bytes'],'parent leaf absent')
    os.link(source,assets/source.name)
new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
ci,si=len(parent['components']),len(parent['shards'])
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']]
animations=[dict(a) for a in parent['animations']];directory=[dict(r) for r in parent['directory']]
for shard in new['shards']:
    source=isolated/Path(shard['registry']).name;require(file_sha(source).upper()==shard['sha256'],'V7 leaf differs')
    os.link(source,assets/source.name);shards.append(dict(shard,index=si+shard['index']))
components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components'])
animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in new['animations'])
directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in new['directory'])
logical=pmeta['logical_component_digests']+[c['digest'] for c in new['components']]
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
    dict(shard_registry_versions=[6,7],logical_digest_schemes=dict(parent='inherited-V6-V7',delta='V7-complete-native-component-digest')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
# 3000 sorts before old IDs: compare identities, never assume old animation/route rows remain a prefix.
old_a=keyed(parent['animations'],('animation_id',));new_a=keyed(checked['animations'],('animation_id',))
old_r=keyed(parent['directory'],('animation_id','resref'));new_r=keyed(checked['directory'],('animation_id','resref'))
require(checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards']
        and all(new_a[k]==v for k,v in old_a.items()) and all(new_r[k]==v for k,v in old_r.items()),'parent native contracts changed')
require(checked['total_resources']==4572 and checked['total_frames']==1586172 and len(checked['animations'])==88
        and len(checked['directory'])==50253,'combined totals differ')
bird=[r for r in checked['directory'] if r['animation_id'] in ('0xD300','0xD400')]
require(len(bird)==2 and len({(r['component_index'],r['shard_index'],r['resource_ordinal']) for r in bird})==1,'bird alias changed')
proof=dict(schema='bg2-ankheg-catalog-preservation-v1',parent_catalog_sha256=parent_sha,
    parent_animations_unchanged=87,parent_resources_unchanged=4560,parent_routes_unchanged=50241,
    comparison='keyed animation_id and (animation_id,resref); component/shard indices retained; sorted rows may shift',
    new_animation_ids=ids,new_owner=9,new_resources=12,new_frames=516,total_animations=88,total_resources=4572,
    total_frames=1586172,total_routes=50253,shared_bird_component_unchanged=True,
    inherited_flying_QA=identity(qa_path),inherited_accepted_leaf_bytes_verified=4,old_leaf_pixels_recomputed=False)
write_json(HERE/'baseline.json',baseline);write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(schema='bg2-ankheg-mixed-V6-V7-pack-v1',catalog=combined,new_shards=shards[si:],proof=proof))
write_json(HERE/'current-generation.json',dict(schema='bg2-ankheg-Q3m-V7-current-v1',role='production-not-QA-installation-or-release',
    family='monster_ankheg',animation_ids=ids,resources=12,frames=516,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,
    generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),
    production=identity(HERE/'production.json'),runtime=previous['runtime'],dll=previous['dll'],
    state='produced-host-verified-ready-to-install',ingame_QA=False))
print(json.dumps(proof))
