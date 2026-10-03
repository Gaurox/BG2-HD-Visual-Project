"""Prepare a seven-leaf V7 Ogre delta preserving the active 81-animation catalog."""
import configparser,copy,json,os,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path

def require(ok,message):
    if not ok:raise ValueError(message)
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
def result(path):return next(json.loads(line) for line in reversed(path.read_text(encoding='utf-8',errors='replace').splitlines()) if line.startswith('{'))

game=get_path('bg2ee_game_root',required=True)
work=ROOT/'sprite/.work/q3m-monster-large-full-x2-20261003-v1'
isolated=work/'isolated';out=work/'combined';assets=out/'iee-assets/creature-sprites'
require(not out.exists() and not (HERE/'baseline.json').exists(),'new run required')
production=json.loads((HERE/'production.json').read_text())
require(production['pack']['resources']==7 and production['pack']['frames']==434,'Ogre scope differs')
require(result(work/'native-isolated-tests.log')['passed'],'native isolated test absent')
live_catalog=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
parent_sha=file_sha(live_catalog);parent=registry.read_sealed_catalog_index(live_catalog,parent_sha)
require(len(parent['animations'])==81 and parent['total_resources']==4549,'active parent differs')
require(not any(a['animation_id']=='0x9000' for a in parent['animations']),'Ogre already registered; inspect existing run')
canonical=ROOT/'sprite/.work/q3m-character-monster-x2-pack-20261003-v1'
parent_pack=json.loads((canonical/'pack.json').read_text());pmeta=parent_pack['catalog']
require(pmeta['sha256'].lower()==parent_sha,'active catalog does not match acquired sealed parent')
runtime_path=ROOT/'docs/measurements/q3m-monster-phase3-x2-20261003-v1/runtime.json'
runtime=json.loads(runtime_path.read_text())
require(file_sha(game/'BaldurReal.exe').upper()==runtime['game_profile']['baldur_real_sha256'],'unidentified game')
require(file_sha(game/'InfinityEngine-Enhancer.dll').lower()==runtime['dll']['sha256'].lower(),'active DLL differs from acquired parent')
config=configparser.ConfigParser(interpolation=None,strict=False);config.read(game/'InfinityEngine-Enhancer.ini')
expected=dict(EnableCreatureSpriteUpscaleTest='true',EnableCreatureSpriteX2Test='false',
              EnableCreatureSpriteLinearFiltering='false',CreatureSpriteFilter='Box',CreatureSpriteFilterAnimation='0x0')
require(all(config.get('Shaders',key)==value for key,value in expected.items()),'active world filter differs')
collisions=[p.name for p in (game/'override').iterdir() if p.is_file() and p.name.upper() in
            {'9000.INI',*(ref+'.BAM' for ref in production['plan']['witnesses'][0]['refs'])}]
require(not collisions,'Ogre native source override collision: '+str(collisions))
preserved=[]
for record in runtime['shaders']+runtime['preserved_packs']+runtime['paperdoll_packs']:
    path=game/record['target'];require(path.is_file(),'inherited asset missing '+record['target'])
    preserved.append(dict(relative_path=record['target'],bytes=path.stat().st_size,sha256=file_sha(path)))
baseline=dict(schema='bg2-monster-large-install-baseline-v1',game_root='config://bg2ee_game_root',
              executable_sha256=file_sha(game/'BaldurReal.exe'),parent_catalog_sha256=parent_sha,
              catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog',
              ini_sha256=file_sha(game/'InfinityEngine-Enhancer.ini'),dll_sha256=file_sha(game/'InfinityEngine-Enhancer.dll'),
              parent_animations=81,parent_resources=4549,parent_frames=parent['total_frames'],parent_routes=len(parent['directory']),
              box_configuration=expected,preserved=preserved,selected_overrides=collisions)
write_json(HERE/'baseline.json',baseline)
assets.mkdir(parents=True)
for shard in parent['shards']:
    name=Path(shard['registry']).name;source=canonical/'iee-assets/creature-sprites'/name
    require(source.is_file() and source.stat().st_size==shard['registry_bytes'],'sealed parent leaf absent '+name)
    live=game/shard['registry'];require(live.is_file() and live.stat().st_size==shard['registry_bytes'],'installed parent leaf absent '+name)
    os.link(source,assets/name)
new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
ci,si=len(parent['components']),len(parent['shards'])
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']]
animations=[dict(a) for a in parent['animations']];directory=[dict(r) for r in parent['directory']]
for shard in new['shards']:
    name=Path(shard['registry']).name;source=isolated/name
    require(file_sha(source).upper()==shard['sha256'],'new V7 leaf identity differs')
    os.link(source,assets/name);shards.append(dict(shard,index=si+shard['index']))
components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components'])
animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in new['animations'])
directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in new['directory'])
logical=pmeta['logical_component_digests']+[c['digest'] for c in new['components']]
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
          dict(shard_registry_versions=[6,7],logical_digest_schemes=dict(parent='inherited-V6',delta='V7-complete-native-component-digest')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
require(checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards'] and
        checked['animations'][:81]==parent['animations'] and checked['directory'][:len(parent['directory'])]==parent['directory'],
        'parent routes/memberships/components changed')
require(checked['total_resources']==4556 and checked['total_frames']==1585413 and len(checked['animations'])==82,'combined scope differs')
proof=dict(schema='bg2-monster-large-catalog-preservation-v1',parent_animations_unchanged=81,
           parent_resources_unchanged=4549,parent_routes_unchanged=len(parent['directory']),
           new_animation='0x9000',new_owner=10,new_resources=7,new_frames=434,total_animations=82,
           total_resources=4556,total_frames=1585413,old_catalog_components_and_shards_identical=True,
           old_leaf_pixels_recomputed=False,preserved_UI_packs=81)
write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(schema='bg2-monster-large-mixed-V6-V7-pack-v1',catalog=combined,
                               new_shards=shards[si:],baseline=identity(HERE/'baseline.json'),proof=proof))
candidate=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-q3m-families-20261003-v1/Release/InfinityEngine-Enhancer.dll'
caps=copy.deepcopy(runtime);caps['runtime_id']='iee-sprite-q3m-v7-x2-all-families-20261003-v1';caps['dll']=identity(candidate)
catalog_caps=caps['capabilities']['creature_sprite_xn_catalog'];catalog_caps['shard_registry_versions']=[3,5,6,7]
catalog_caps['mixed_v6_v7_components']=True;catalog_caps['frame_storage'].append('q3m-v7-packed-four-partner-eight-level-plane')
catalog_caps['q3m_profiles'].extend(dict(profile_id=p,decode_rule_id=3,owners=list(range(1,16)),scales=[2],native_kind=k,partners=4,levels=8) for p,k in ((8,0),(9,1)))
caps['inherited_runtime']=identity(runtime_path)
caps['source_provenance']=dict(commit_base='1fbb3574',V7_contract='pipeline/PALETTE_Q3M_V7.md',
                               native_family_analysis='docs/measurements/q3m-families-engine-x2-20261003-v2/native-analysis.json')
caps['verification']=dict(native_isolated=result(work/'native-isolated-tests.log'),python_tests=7,ingame_QA=False)
caps['installation']=dict(state='candidate; run-specific receipt is installation authority')
caps_path=ROOT/'pipeline/runtime/manifests/iee-sprite-q3m-v7-x2-all-families-20261003-v1.json'
require(not caps_path.exists(),'runtime capability manifest already exists');write_json(caps_path,caps)
write_json(HERE/'current-generation.json',dict(schema='bg2-monster-large-Q3m-V7-current-v1',
          role='production-not-QA-installation-or-release',family='monster_large',animation_ids=['0x9000'],
          resources=7,frames=434,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,
          generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),
          production=identity(HERE/'production.json'),runtime=identity(caps_path),dll=identity(candidate),
          state='produced-host-verified-ready-to-install',ingame_QA=False))
print(json.dumps(proof))
