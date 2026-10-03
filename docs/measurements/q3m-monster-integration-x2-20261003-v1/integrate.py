"""Append the sealed three-Monster pack; preserve acquired Character index and hardlinked leaves."""
from __future__ import annotations
import argparse
import configparser
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_monster_work_plan import require
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path

CHAR=ROOT/'docs/measurements/playable-q3m-x2-ingame-20261002-v1'
PHASE5=ROOT/'docs/measurements/q3m-monster-complete-x2-20261003-v1'
RUNTIME=ROOT/'docs/measurements/q3m-monster-phase3-x2-20261003-v1/runtime.json'
BOX=dict(EnableCreatureSpriteUpscaleTest='true',EnableCreatureSpriteX2Test='false',
         EnableCreatureSpriteLinearFiltering='false',CreatureSpriteFilter='Box',CreatureSpriteFilterAnimation='0x0')


def read(p):return json.loads(p.read_text())
def relative(p):return p.relative_to(ROOT).as_posix()


def integrate(output):
    require(not output.exists() and not (HERE/'baseline.json').exists(),'new integration version required')
    output.relative_to(ROOT);output.mkdir(parents=True)
    assets=output/'iee-assets/creature-sprites';assets.mkdir(parents=True)
    pointer=read(CHAR/'current-generation.json');parent_dir=ROOT/pointer['generation_dir']
    require(file_sha(parent_dir/'pack.json').upper()==pointer['build_manifest_sha256'],'sealed Character manifest changed')
    parent=read(parent_dir/'pack.json');pmeta=parent['catalog']
    pindex=registry.read_sealed_catalog_index(parent_dir/'CreatureSprites-XN.catalog',pmeta['sha256'])
    require(len(pindex['animations'])==78 and all(a['owner']==1 for a in pindex['animations']) and
            pindex['total_resources']==4510 and pindex['total_frames']==1564054,'Character parent scope changed')
    require(registry.catalog_logical_content_digest(2,pindex['animations'],pmeta['logical_component_digests'])==
            pmeta['logical_content_sha256'],'acquired Character logical digest differs')
    final5=read(PHASE5/'verification.json');monster=final5['pack']
    require(final5['status']=='complete-produced-isolated-native-host-verified-not-installed','phase5 not complete')
    mpath=ROOT/monster['catalog']['path'];mdir=mpath.parent
    require(file_sha(mdir.parents[1]/'pack.json')==final5['pack_manifest_sha256'],'sealed Monster manifest changed')
    mindex=registry.read_sealed_catalog_index(mpath,monster['catalog']['sha256'])
    old_ids={a['animation_id'] for a in pindex['animations']};new_ids={a['animation_id'] for a in mindex['animations']}
    require(new_ids=={'0x7F02','0x7F07','0x7F30'} and old_ids.isdisjoint(new_ids),'animation ID collision')
    require({r['resref'] for r in pindex['directory']}.isdisjoint({r['resref'] for r in mindex['directory']}),'resource collision')
    game=get_path('bg2ee_game_root',required=True)
    live=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
    require(file_sha(live).upper()==pmeta['sha256'],'active catalog differs from acquired Character parent')
    config=configparser.ConfigParser(interpolation=None,strict=False);config.read(game/'InfinityEngine-Enhancer.ini')
    require(all(config.get('Shaders',k)==v for k,v in BOX.items()),'active BOX configuration changed')
    inherited=read(RUNTIME);oldrt=read(ROOT/inherited['inherited_runtime']['path'])
    require(file_sha(ROOT/inherited['inherited_runtime']['path'])==inherited['inherited_runtime']['sha256'],'inherited runtime manifest differs')
    require(file_sha(game/'InfinityEngine-Enhancer.dll').upper()==oldrt['dll']['sha256'].upper(),'active runtime baseline changed')
    overrides=[r['resref'] for r in monster['resources'] if (game/'override'/(r['resref']+'.BAM')).exists()]
    require(not overrides,'selected native BAM override collision')
    require(len(inherited['paperdoll_packs'])+len(inherited['preserved_packs'])==81,'paperdoll inherited scope changed')
    baseline=dict(schema='bg2-q3m-monster-integration-baseline-v1',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                  game_root=str(game),parent_pointer=relative(CHAR/'current-generation.json'),
                  parent_pack=relative(parent_dir/'pack.json'),parent_pack_sha256=file_sha(parent_dir/'pack.json'),
                  character_catalog_sha256=pmeta['sha256'],character_animations=78,character_resources=4510,
                  character_native_frames=1564054,selected_BAM_overrides=overrides,box_configuration=BOX,
                  live_files=[dict(relative_path=p,sha256=file_sha(game/p),bytes=(game/p).stat().st_size)
                              for p in ('iee-assets/creature-sprites/CreatureSprites-XN.catalog',
                                        'InfinityEngine-Enhancer.ini','InfinityEngine-Enhancer.dll')],
                  preserved_assets_authority=relative(CHAR/'baseline.json'),
                  preserved_assets_authority_sha256=file_sha(CHAR/'baseline.json'),
                  paperdolls=81,UI_sampler='Nearest',shader_writes_required=False,
                  runtime_manifest=relative(RUNTIME),runtime_manifest_sha256=file_sha(RUNTIME),
                  runtime_dll=inherited['dll'])
    write_json(HERE/'baseline.json',baseline)
    for shard in pindex['shards']:
        name=Path(shard['registry']).name;source=parent_dir/name;destination=assets/name
        require(source.is_file(),'acquired Character leaf missing: '+name)
        os.link(source,destination)
        require(os.path.samefile(source,destination),'Character hardlink identity differs')
    ci,si=len(pindex['components']),len(pindex['shards'])
    components=[dict(c) for c in pindex['components']]
    shards=[dict(s) for s in pindex['shards']]
    animations=[dict(a) for a in pindex['animations']]
    directory=[dict(r) for r in pindex['directory']]
    logical=list(pmeta['logical_component_digests'])
    extra_storage={k:0 for k in ('stored_index_bytes','stored_fraction_bytes','fraction_bytes','compressed_frame_count',
                               'raw_frame_count','compressed_fraction_count','fractional_frame_count')}
    for shard in mindex['shards']:
        name=Path(shard['registry']).name;source=mdir/name;destination=assets/name
        require(not destination.exists(),'physical leaf collision')
        info=v6.inspect(source,include_resource_records=True)
        require(info['sha256']==shard['sha256'] and info['class_profile_id'] in range(2,8) and
                info['decode_rule_id']==2,'Monster sealed leaf profile/SHA differs')
        shutil.copyfile(source,destination)
        require(file_sha(destination).upper()==shard['sha256'],'Monster copied leaf differs')
        logical.append(registry.catalog_source_component_sha256(2,info['resource_records']))
        shards.append(dict(shard,index=si+shard['index']))
        for k in extra_storage:extra_storage[k]+=info[k]
    components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in mindex['components'])
    animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in mindex['animations'])
    directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in mindex['directory'])
    storage=dict(shard_registry_version=6,**{k:pmeta[k]+v for k,v in extra_storage.items()})
    path=assets/'CreatureSprites-XN.catalog'
    catalog=registry.write_registry_catalog_index(path,2,animations,components,shards,directory,logical,storage)
    checked=registry.read_sealed_catalog_index(path,catalog['sha256'])
    require(checked['components'][:ci]==pindex['components'] and checked['shards'][:si]==pindex['shards'] and
            checked['animations'][:78]==pindex['animations'] and checked['directory'][:len(pindex['directory'])]==pindex['directory'],
            'acquired Character routes/memberships/components changed')
    require(checked['total_resources']==4549 and checked['total_frames']==1584979 and len(checked['animations'])==81,
            'integrated totals differ')
    require(logical[:ci]==pmeta['logical_component_digests'] and
            {a['animation_id']:a['owner'] for a in checked['animations'] if a['animation_id'] in new_ids}==
            {a:3 for a in new_ids},'logical prefix or new owners changed')
    for r in mindex['directory']:
        wanted=dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index'])
        require(wanted in checked['directory'],'Monster route missing')
    pack=dict(schema='bg2-q3m-character-monster-integrated-catalog-v1',status='integrated-not-installed',
              scale=2,catalog=catalog,character_parent=relative(parent_dir/'pack.json'),
              monster_parent=relative(PHASE5/'verification.json'),runtime_manifest=relative(RUNTIME),
              runtime_manifest_sha256=file_sha(RUNTIME),new_shards=catalog['shards'][si:],
              proof=dict(character_routes_identical=len(pindex['directory']),character_hardlinked_shards=si,
                         character_pixel_checks_repeated=False,paperdolls_untouched=81,new_resources=39,
                         native_frames_preserved=20925,installation_changed=False,QA_changed=False,release_changed=False))
    write_json(output/'pack.json',pack)
    write_json(HERE/'current-generation.json',dict(schema='bg2-q3m-monster-integrated-current-v1',role='production-not-QA-or-release',
               generation_dir=relative(output),manifest='pack.json',manifest_sha256=file_sha(output/'pack.json'),
               catalog_sha256=catalog['sha256'],animation_count=81,resources=4549,native_frames=1584979,
               status='integrated-pending-native-binding-verification'))
    print(json.dumps(dict(animations=81,resources=4549,frames=1584979,new_resources=39,
                         preserved_character_routes=len(pindex['directory']),catalog_sha256=catalog['sha256'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();integrate(a.output.resolve())
