"""Icewind-only installation candidate; inherit installed catalog exactly."""
import json,os,shutil,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;PROD=HERE.parent/'q3m-icewind-full-x2-20261006-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)

def main():
    assert not(HERE/'baseline.json').exists(),'new installation version required'
    game=get_path('bg2ee_game_root',required=True)
    parentdir=HERE.parent/'q3m-multi-new-frame-stability-20261005-v2'
    previous=load(parentdir/'current-generation.json');generation=load(PROD/'current-generation.json')
    assert load(PROD/'verification.json')['passed'] and load(PROD/'runtime-verification.json')['passed']
    relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
    assert file_sha(game/relative)==previous['catalog']['sha256']
    assert file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
    assert load(PROD/'runtime.json')['inherited_dll']['sha256']==previous['dll']['sha256']
    for field in ('production','catalog','recipe','runtime','dll','verification','runtime_verification'):
        r=generation[field];assert file_sha(ROOT/r['path'])==r['sha256'],field
    parent=registry.read_sealed_catalog_index(game/relative,previous['catalog']['sha256'])
    isolated=ROOT/generation['generation_dir']
    new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',generation['catalog']['sha256'])
    assert len(parent['animations'])==217 and len(new['animations'])==40
    assert new['total_resources']==1115 and new['total_frames']==75176 and len(new['directory'])==1140
    assert not {a['animation_id'] for a in parent['animations']}&{a['animation_id'] for a in new['animations']}
    assert all(a['owner']==2 for a in new['animations'])
    canonical=ROOT/previous['generation_dir'];out=WORK/'combined';assets=out/'iee-assets/creature-sprites'
    assets.mkdir(parents=True)
    components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']]
    directory=[dict(r) for r in parent['directory']];animations=[dict(a) for a in parent['animations']]
    logical=load(canonical/'pack.json')['catalog']['logical_component_digests'][:]
    for s in parent['shards']:
        p=canonical/s['registry'];installed=game/s['registry']
        assert p.stat().st_size==installed.stat().st_size==s['registry_bytes'],s['registry']
        os.link(p,assets/p.name)
    ci,si=len(components),len(shards);new_shards=[]
    for s in new['shards']:
        p=isolated/Path(s['registry']).name;assert file_sha(p).upper()==s['sha256']
        assert not(assets/p.name).exists(),'unexpected cross-owner leaf identity'
        os.link(p,assets/p.name);ns=dict(s,index=si+s['index']);shards.append(ns);new_shards.append(ns)
    components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components'])
    logical.extend(c['digest'] for c in new['components'])
    animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in new['animations'])
    directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in new['directory'])
    combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
        dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-installed',delta='V7-complete-native-monster_icewind')))
    checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
    assert checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards']
    routes={(r['animation_id'],r['resref']):r for r in checked['directory']}
    assert all(routes[(r['animation_id'],r['resref'])]==r for r in parent['directory'])
    aa={a['animation_id']:a for a in checked['animations']}
    assert all(aa[a['animation_id']]==a for a in parent['animations'])
    assert len(aa)==257 and checked['total_resources']==13372 and checked['total_frames']==2318470 and len(checked['directory'])==62028
    shutil.copyfile(isolated/'witnesses.oracle',assets/'witnesses.oracle')
    preserved=[dict(relative_path=name,sha256=file_sha(game/name)) for name in
        ('InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl','BaldurReal.exe')]
    selection=load(PROD/'selection.json')
    source_names={r['resref']+'.BAM' for r in new['directory']}|{a['animation_id'][2:]+'.INI' for a in new['animations']}|{w['palette_override']['resref']+'.BMP' for w in selection['witnesses'] if 'palette_override' in w}
    assert not source_names&{p.name.upper() for p in (game/'override').iterdir()}
    # Neutral fixtures make the unused alias and three alternate palettes testable.
    index=registry.KeyIndex(game);entries=index.resource_map(1009);seed,source=index.resolve(entries['ARNMAN01'])
    assert struct.unpack_from('<I',seed,0x20)[0]==0 and seed[0x7e]==0
    assert struct.unpack_from('<I',seed,0x2c8)[0]==struct.unpack_from('<I',seed,0x2c0)[0]==0
    fixture_dir=WORK/'fixtures';fixture_dir.mkdir();fixtures=[];representatives=[]
    for w in selection['witnesses']:
        ref='QICE'+w['animation_id'][2:];assert len(ref)==8 and ref not in entries and not(game/'override'/(ref+'.cre')).exists()
        b=bytearray(seed);struct.pack_into('<I',b,0x28,int(w['animation_id'],16));b[0x270]=128
        offsets=(0x248,0x250,0x258,0x260,0x268,0x2cc)
        for o in offsets:b[o:o+8]=bytes(8)
        b[0x280:0x2a0]=ref.encode().ljust(32,b'\0')
        allowed=set(range(0x28,0x2c))|{0x270}|set(range(0x280,0x2a0))|{i for o in offsets for i in range(o,o+8)}
        assert len(b)==len(seed) and all(a==v or i in allowed for i,(a,v) in enumerate(zip(seed,b)))
        p=fixture_dir/(ref+'.cre');p.write_bytes(b)
        fixtures.append(dict(path=p.relative_to(ROOT).as_posix(),target='override/'+p.name,sha256=file_sha(p),derived_from='ARNMAN01',source_BIF=source,source_sha256=__import__('hashlib').sha256(seed).hexdigest(),invisible_states_effects_equipment_absent=True))
        representatives.append(dict(resref=ref,animation_id=w['animation_id'],name=w['name'],clua=f'C:CreateCreature("{ref}")'))
    write_json(HERE/'creatures.json',dict(fixtures=fixtures,representatives=representatives,ingame_spawn_verified=False))
    (HERE/'CLUA.txt').write_text('\n'.join(r['clua']+' -- '+r['animation_id']+' '+r['name'] for r in representatives)+'\n',encoding='utf-8')
    proof=dict(passed=True,inherited_animations_unchanged=217,inherited_components_unchanged=ci,inherited_routes_unchanged=len(parent['directory']),
        inherited_shards_unchanged=si,new_animations=40,new_resources=1115,new_frames=75176,new_bindings=1140,
        active_animations=257,active_resources=13372,active_frames=2318470,active_routes=62028,ingame_QA=False,release=False)
    write_json(out/'pack.json',dict(schema='bg2-icewind-combined-pack-v1',catalog=combined,new_shards=new_shards,proof=proof))
    write_json(HERE/'catalog-proof.json',proof)
    write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative=relative,parent_catalog_sha256=previous['catalog']['sha256'],
        parent_dll_sha256=previous['dll']['sha256'],parent_generation=identity(parentdir/'current-generation.json'),preserved=preserved,source_names=sorted(source_names)))
    write_json(HERE/'current-generation.json',dict(schema='bg2-icewind-ingame-candidate-v1',role='installation-candidate-not-QA-or-release',family='monster_icewind',
        animation_ids=generation['animation_ids'],models=36,resources=1115,frames=75176,logical_resource_bindings=1140,bound_frames=76955,
        scale=2,SDF=False,colour='K6-four-partners-eight-levels',generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),
        production_generation=identity(PROD/'current-generation.json'),runtime=generation['runtime'],dll=generation['dll'],
        production_verification=generation['verification'],runtime_verification=generation['runtime_verification'],ingame_QA=False,release=False))
    print(json.dumps(dict(stage='prepared',**proof,fixtures=40)),flush=True)

if __name__=='__main__':main()
