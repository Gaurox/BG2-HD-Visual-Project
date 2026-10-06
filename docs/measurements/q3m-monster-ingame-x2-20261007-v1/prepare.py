"""Replace three Monster pilots, append complete production, create 77 neutral CRE."""
import hashlib,json,os,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
WORK=ROOT/'sprite/.work'/HERE.name;PROD=HERE.parent/'q3m-monster-full-x2-20261006-v2'
PARENT=HERE.parent/'q3m-icewind-ingame-x2-20261006-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)

def signatures(cat,ids):
    return sorted((r['animation_id'],r['resref'],r['resource_ordinal'],
        cat['shards'][r['shard_index']]['sha256'],cat['components'][r['component_index']]['digest'])
        for r in cat['directory'] if r['animation_id'] in ids)

def main():
    assert not(HERE/'baseline.json').exists(),'new installation version required'
    game=get_path('bg2ee_game_root',required=True);previous=load(PARENT/'current-generation.json')
    generation=load(PROD/'current-generation.json');pv=load(PROD/'verification.json')
    assert pv['passed'] and pv['native_world']['passed'] and pv['resources']==1040 and pv['bound_frames']==496822
    for name in ('catalog','production','recipe'):
        assert file_sha(ROOT/generation[name]['path'])==generation[name]['sha256']
    relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
    assert file_sha(game/relative)==previous['catalog']['sha256']
    assert file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
    parent=registry.read_sealed_catalog_index(game/relative,previous['catalog']['sha256'])
    isolated=ROOT/generation['generation_dir']
    new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',generation['catalog']['sha256'])
    ids=set(generation['animation_ids']);priorids={a['animation_id'] for a in parent['animations']}
    replaced=priorids&ids;kept=priorids-ids
    assert len(priorids)==257 and replaced=={'0x7F02','0x7F07','0x7F30'} and len(kept)==254
    assert len(new['animations'])==77 and all(a['owner']==3 for a in new['animations'])
    assert new['total_resources']==1037 and new['total_frames']==496816 and len(new['directory'])==1040
    canonical=ROOT/previous['generation_dir']
    oldlogical=load(canonical/'pack.json')['catalog']['logical_component_digests']
    out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
    components=[];shards=[];logical=[];seen={};shahits={};oldmap={};newmap={};oldsmap={};newsmap={}
    selected_new_shards=[]
    def add_component(cat,index,source,logical_digest,cmap,smap):
        c=cat['components'][index];digest=c['digest'];ss=cat['shards'][c['shard_start']:c['shard_start']+c['shard_count']]
        if digest in seen:
            mapped=seen[digest];existing=components[mapped]
            assert [s['sha256'] for s in ss]==[s['sha256'] for s in shards[existing['shard_start']:existing['shard_start']+existing['shard_count']]]
            cmap[index]=mapped
            for n,s in enumerate(ss):smap[s['index']]=existing['shard_start']+n
            return
        mapped=len(components);start=len(shards);seen[digest]=mapped;cmap[index]=mapped
        for s in ss:
            assert s['sha256'] not in shahits,'overlapping non-identical catalog components'
            p=source/Path(s['registry']).name
            if cat is new:
                assert file_sha(p).upper()==s['sha256']
                selected_new_shards.append(dict(s))
            else:
                assert p.stat().st_size==(game/s['registry']).stat().st_size==s['registry_bytes']
            os.link(p,assets/p.name)
            smap[s['index']]=len(shards);shahits[s['sha256']]=len(shards)
            shards.append(dict(s,index=len(shards)))
        components.append(dict(c,index=mapped,shard_start=start));logical.append(logical_digest)
    keepcomponents=sorted({i for a in parent['animations'] if a['animation_id'] in kept for i in a['component_indices']})
    for i in keepcomponents:add_component(parent,i,canonical/'iee-assets/creature-sprites',oldlogical[i],oldmap,oldsmap)
    for c in new['components']:add_component(new,c['index'],isolated,c['digest'],newmap,newsmap)
    animations=[dict(a,component_indices=[oldmap[i] for i in a['component_indices']]) for a in parent['animations'] if a['animation_id'] in kept]
    animations.extend(dict(a,component_indices=[newmap[i] for i in a['component_indices']]) for a in new['animations'])
    directory=[dict(r,component_index=oldmap[r['component_index']],shard_index=oldsmap[r['shard_index']]) for r in parent['directory'] if r['animation_id'] in kept]
    directory.extend(dict(r,component_index=newmap[r['component_index']],shard_index=newsmap[r['shard_index']]) for r in new['directory'])
    catalog=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
        dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-installed',delta='V7-complete-monster')))
    checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',catalog['sha256'])
    assert signatures(checked,kept)==signatures(parent,kept)
    assert signatures(checked,ids)==signatures(new,ids)
    am={a['animation_id']:a for a in checked['animations']}
    for a in parent['animations']:
        if a['animation_id'] not in kept:continue
        assert am[a['animation_id']]['owner']==a['owner']
        assert {checked['components'][i]['digest'] for i in am[a['animation_id']]['component_indices']}=={parent['components'][i]['digest'] for i in a['component_indices']}
    assert len(am)==331
    selection=load(PROD/'selection.json')
    source_names={r['resref']+'.BAM' for r in new['directory']}|{a[2:]+'.INI' for a in ids}|{w['palette_override']['resref']+'.BMP' for w in selection['witnesses'] if 'palette_override' in w}
    assert not source_names&{p.name.upper() for p in (game/'override').iterdir()}
    preserved=[dict(relative_path=name,sha256=file_sha(game/name)) for name in ('InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl','BaldurReal.exe')]
    ini=registry.parse_animation_ini((game/'InfinityEngine-Enhancer.ini').read_bytes())
    assert [v['creaturespritefilter'] for v in ini.values() if 'creaturespritefilter' in v]==['Nearest']
    index=registry.KeyIndex(game);entries=index.resource_map(1009);seed,source=index.resolve(entries['ARNMAN01'])
    u=lambda o:struct.unpack_from('<I',seed,o)[0]
    assert seed[:8]==b'CRE V1.0' and u(0x20)==0 and seed[0x7e]==0 and u(0x2c8)==u(0x2c0)==0
    fixture_dir=WORK/'fixtures';fixture_dir.mkdir();fixtures=[];representatives=[]
    for w in selection['witnesses']:
        ref='QMON'+w['animation_id'][2:]
        assert len(ref)==8 and ref not in entries and not(game/'override'/(ref+'.cre')).exists()
        b=bytearray(seed);struct.pack_into('<I',b,0x28,int(w['animation_id'],16));b[0x270]=128
        offsets=(0x248,0x250,0x258,0x260,0x268,0x2cc)
        for o in offsets:b[o:o+8]=bytes(8)
        b[0x280:0x2a0]=ref.encode().ljust(32,b'\0')
        allowed=set(range(0x28,0x2c))|{0x270}|set(range(0x280,0x2a0))|{i for o in offsets for i in range(o,o+8)}
        assert len(b)==len(seed) and all(a==v or i in allowed for i,(a,v) in enumerate(zip(seed,b)))
        p=fixture_dir/(ref+'.cre');p.write_bytes(b)
        fixtures.append(dict(path=p.relative_to(ROOT).as_posix(),target='override/'+p.name,sha256=file_sha(p),animation_id=w['animation_id'],derived_from='ARNMAN01',source_BIF=source,source_sha256=hashlib.sha256(seed).hexdigest(),neutral_no_scripts_effects_items=True))
        representatives.append(dict(resref=ref,animation_id=w['animation_id'],name=w['name'],clua=f'C:CreateCreature("{ref}")'))
    write_json(HERE/'creatures.json',dict(fixtures=fixtures,representatives=representatives,ingame_spawn_verified=False))
    (HERE/'CLUA.txt').write_text('\n'.join(r['clua']+' -- '+r['animation_id']+' '+r['name'] for r in representatives)+'\n',encoding='utf-8',newline='\n')
    retained=len(signatures(parent,kept))
    proof=dict(passed=True,retained_animations_unchanged=254,retained_bindings_unchanged=retained,retained_memberships_same_component_digests=True,
        replaced_pilot_ids=sorted(replaced),replaced_pilot_bindings=len(signatures(parent,replaced)),newly_covered_ids=74,
        complete_monster_ids=77,monster_physical_resources=1037,monster_physical_frames=496816,monster_bindings=1040,monster_bound_frames=496822,
        selected_routes_and_leaf_identities_match_production=True,active_animations=331,active_resources=checked['total_resources'],active_frames=checked['total_frames'],active_routes=len(checked['directory']),
        inherited_files_not_deleted=True,index_relocation_only_for_retained_families=True,ingame_QA=False,release=False)
    selected_leaves=[dict(checked['shards'][i]) for i in sorted({r['shard_index'] for r in checked['directory'] if r['animation_id'] in ids})]
    assert len(selected_leaves)==1037
    write_json(out/'pack.json',dict(schema='bg2-monster-combined-pack-v1',catalog=catalog,monster_shards=selected_leaves,proof=proof))
    write_json(HERE/'catalog-proof.json',proof)
    write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=relative,parent_catalog_sha256=previous['catalog']['sha256'],
        parent_generation=identity(PARENT/'current-generation.json'),preserved=preserved,source_names=sorted(source_names)))
    write_json(HERE/'current-generation.json',dict(schema='bg2-monster-ingame-candidate-v1',role='installation-candidate-not-QA-or-release',family='monster',animation_ids=generation['animation_ids'],models=62,resources=1037,frames=496816,logical_resource_bindings=1040,bound_frames=496822,
        scale=2,SDF=False,colour='K6-four-partners-eight-levels',generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),
        production_generation=identity(PROD/'current-generation.json'),production_verification=identity(PROD/'verification.json'),runtime=previous['runtime'],dll=previous['dll'],runtime_changed=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='prepared',**proof,fixtures=77)),flush=True)

if __name__=='__main__':main()
