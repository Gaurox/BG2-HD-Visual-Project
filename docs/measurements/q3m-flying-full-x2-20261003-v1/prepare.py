"""Prepare four shared V7 bird leaves on the acquired installed Ogre catalog."""
import configparser,json,os,sys
from pathlib import Path
from datetime import datetime,timezone
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

game=get_path('bg2ee_game_root',required=True)
work=ROOT/'sprite/.work/q3m-flying-full-x2-20261003-v1';isolated=work/'isolated'
out=work/'combined';assets=out/'iee-assets/creature-sprites'
require(not out.exists() and not (HERE/'baseline.json').exists(),'new run required')
production=load(HERE/'production.json');require(production['pack']['resources']==4 and production['pack']['frames']==243,'flying scope differs')
require(result(work/'native-isolated-tests.log')['passed'],'isolated native check absent')
previous_dir=ROOT/'docs/measurements/q3m-monster-large-full-x2-20261003-v1'
previous=load(previous_dir/'current-generation.json');canonical=ROOT/previous['generation_dir']
parent_sha=file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')
require(parent_sha==previous['catalog']['sha256'],'active parent differs from acquired Ogre catalog')
parent=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',parent_sha)
pmeta=load(canonical/'pack.json')['catalog'];runtime=load(ROOT/previous['runtime']['path'])
require(file_sha(game/'BaldurReal.exe').upper()==runtime['game_profile']['baldur_real_sha256'],'unknown game executable')
require(file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256'],'active runtime changed')
ids=['0xD000','0xD100','0xD200','0xD300','0xD400']
require(len(parent['animations'])==82 and not any(a['animation_id'] in ids for a in parent['animations']),'unexpected parent coverage')
config=configparser.ConfigParser(interpolation=None,strict=False);config.read(game/'InfinityEngine-Enhancer.ini')
expected=dict(EnableCreatureSpriteUpscaleTest='true',EnableCreatureSpriteX2Test='false',EnableCreatureSpriteLinearFiltering='false',CreatureSpriteFilter='Box',CreatureSpriteFilterAnimation='0x0')
require(all(config.get('Shaders',k)==v for k,v in expected.items()),'world configuration differs')
collisions=[p.name for p in (game/'override').iterdir() if p.is_file() and p.name.upper() in
            {*(i[2:]+'.INI' for i in ids),'AEAGG1.BAM','AGULG1.BAM','AVULG1.BAM','ABIRG1.BAM'}]
require(not collisions,'flying source override collision: '+str(collisions))
preserved=[]
for entry in runtime['shaders']+runtime['preserved_packs']+runtime['paperdoll_packs']:
    path=game/entry['target'];preserved.append(dict(relative_path=entry['target'],bytes=path.stat().st_size,sha256=file_sha(path)))
baseline=dict(schema='bg2-flying-install-baseline-v1',game_root='config://bg2ee_game_root',
              executable_sha256=file_sha(game/'BaldurReal.exe'),parent_catalog_sha256=parent_sha,
              catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog',ini_sha256=file_sha(game/'InfinityEngine-Enhancer.ini'),
              dll_sha256=file_sha(game/'InfinityEngine-Enhancer.dll'),parent_animations=82,parent_resources=4556,
              parent_frames=parent['total_frames'],parent_routes=len(parent['directory']),box_configuration=expected,preserved=preserved)
write_json(HERE/'baseline.json',baseline);assets.mkdir(parents=True)
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
require(checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards'] and
        checked['animations'][:82]==parent['animations'] and checked['directory'][:len(parent['directory'])]==parent['directory'],'parent native contracts changed')
require(checked['total_resources']==4560 and checked['total_frames']==1585656 and len(checked['animations'])==87,'combined totals differ')
bird=[r for r in checked['directory'] if r['animation_id'] in ('0xD300','0xD400')]
require(len(bird)==2 and len({(r['component_index'],r['shard_index'],r['resource_ordinal']) for r in bird})==1,'bird alias not shared')
proof=dict(schema='bg2-flying-catalog-preservation-v1',parent_animations_unchanged=82,parent_resources_unchanged=4556,
           parent_routes_unchanged=len(parent['directory']),new_animation_ids=ids,new_owner=15,new_resources=4,new_frames=243,
           total_animations=87,total_resources=4560,total_frames=1585656,shared_bird_component=True,old_leaf_pixels_recomputed=False)
write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(schema='bg2-flying-mixed-V6-V7-pack-v1',catalog=combined,new_shards=shards[si:],proof=proof))
comparison_path=ROOT/'docs/measurements/q3m-flying-frame-x2-x4-20261003-v1/comparison.json';comparison=load(comparison_path)
write_json(HERE/'visual-acceptance.json',dict(schema='bg2-flying-x2-comparison-acceptance-v1',authority='user',
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),status='accepted',scope='four displayed x2 frames and recipe; no inferred full-animation ingame QA',
    user_statement='je valide totalement la version x2. traite toute la famille en x2 q3m et installe ingame',
    comparison=identity(comparison_path),samples=[dict(resref=s['resref'],frame=s['frame'],encoded_work_key=s['encoded_work_key'],
        encoded_sha256=s['encodings'][0]['encoded_sha256'],PNG=next(p for p in s['PNGs'] if p['scale']==2)) for s in comparison['samples']],
    scale=2,ingame_QA=False))
write_json(HERE/'current-generation.json',dict(schema='bg2-flying-Q3m-V7-current-v1',role='production-not-QA-installation-or-release',
    family='flying',animation_ids=ids,resources=4,frames=243,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,
    generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),
    production=identity(HERE/'production.json'),runtime=previous['runtime'],dll=previous['dll'],
    accepted_comparison=identity(HERE/'visual-acceptance.json'),state='produced-host-verified-ready-to-install',ingame_QA=False))
print(json.dumps(proof))
