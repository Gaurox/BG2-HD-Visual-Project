"""Derive complete Ankheg V8 coverage from sealed V7 planes; zero neural inference."""
import hashlib,json,os,struct,sys,copy
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from sprite_sdf_registry import planes
import importlib.util
offline=ROOT/'docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1'
spec=importlib.util.spec_from_file_location('sdf_reference',offline/'sdf_trial.py');reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)

def require(ok,message):
    if not ok:raise ValueError(message)
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
parent_run=ROOT/'docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1'
original_run=parent_run
parent_run=ROOT/'docs/measurements/q3m-ankheg-alpha-light-x2-20261004-v1'
previous=load(parent_run/'current-generation.json');production=load(original_run/'production.json')
parent_root=ROOT/previous['generation_dir'];source_dir=ROOT/production['pack_directory']
game=get_path('bg2ee_game_root',required=True)
require(file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==previous['catalog']['sha256'],'active catalog differs')
require(file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256'],'active DLL differs')
work=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1';isolated=work/'isolated'
require(not work.exists() and not (HERE/'production.json').exists(),'fresh run required')
isolated.mkdir(parents=True);cache=work/'mask-cache';cache.mkdir()
recipe=dict(reference.RECIPE,installation='V9-adaptive-runtime',distance_quantization_x2=1/16,sdf_pad_x2=6)
recipe_bytes=json.dumps(reference.RECIPE,sort_keys=True).encode()+bytes.fromhex(file_sha(offline/'sdf_trial.py'))
# K6 palettes and metadata are acquired from the original native oracle.
old_oracle=(source_dir/'witnesses.oracle').read_bytes();pos=12;palette_map={};chunks=[]
for _ in range(struct.unpack_from('<I',old_oracle,8)[0]):
    start=pos;aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',old_oracle,pos);pos+=24
    palettes=np.frombuffer(old_oracle,np.uint8,6*256*4,pos).reshape(6,256,4).copy();pos+=6*256*4+2052
    for __ in range(nc):count=struct.unpack_from('<I',old_oracle,pos)[0];pos+=4+count*4
    prefix=old_oracle[start:pos];geometry=[]
    for __ in range(nf):geometry.append(struct.unpack_from('<IIii',old_oracle,pos));pos+=16+6*32
    name=ref.split(b'\0')[0].decode();palette_map[name]=palettes;chunks.append((name,prefix,geometry))
require(pos==len(old_oracle) and len(chunks)==12,'original oracle differs')
resources={};infos=[];mask_cache={};stats=dict(physical_frames=0,unique_masks=0,mask_cache_hits=0,
    acquired_offline_masks_reused=0,new_neural_targets=0,new_Q3m_encodings=0)
details=[]
for info in production['pack']['leaves']:
    source=source_dir/registry.catalog_shard_filename(info['sha256'])
    require(file_sha(source).upper()==info['sha256'],'sealed V7 leaf changed')
    parsed=leaves.inspect(source,include_frames=True);resource=parsed['resources'][0]
    ref=resource['resref'];profile=resource['profile'];rows=[];changed=0
    for ordinal,frame in enumerate(resource['frames']):
        binary=np.minimum(frame['I'],3)
        key=hashlib.sha256(recipe_bytes+struct.pack('<II',*binary.shape)+binary.tobytes()).hexdigest()
        if key in mask_cache:distance,report=mask_cache[key];stats['mask_cache_hits']+=1
        else:
            acquired=ROOT/'sprite/.work/q3m-ankheg-sdf-offline-x2-20261004-v1'/ (key+'.npz')
            if acquired.exists():
                distance=np.load(acquired)['SDF'];stats['acquired_offline_masks_reused']+=1
                report=dict(reused_offline_field=True)
            elif np.any(frame['I']>=2):distance,report=reference.reconstruct(frame['I'])
            else:distance=np.full((binary.shape[0]+12,binary.shape[1]+12),-4,np.float32);report=dict(empty_foreground=True)
            np.savez_compressed(cache/(key+'.npz'),SDF=distance)
            mask_cache[key]=(distance,report);stats['unique_masks']+=1
        frame['S'],frame['M']=planes(frame['I'],distance)
        frame['guide']=frame['I'].copy();frame['dep']=np.frombuffer(frame['dep'],np.uint8).copy()
        rows.append(dict(frame=ordinal,mask_key=key,**report))
        stats['physical_frames']+=1
    materials=dict(resref=ref,source_sha256=resource['source_sha256'],frames=resource['frames'],cycles=resource['cycles'])
    path=isolated/(ref+'.registry');new=leaves.write(path,[materials],profile,version=9)
    sealed=isolated/registry.catalog_shard_filename(new['sha256']);path.replace(sealed)
    checked=leaves.inspect(sealed,include_frames=True)['resources'][0]
    require(checked['cycles']==resource['cycles'] and checked['source_sha256']==resource['source_sha256'],'source/cycles altered')
    require(all(a['geometry']==b['geometry'] and np.array_equal(a['I'],b['I']) and np.array_equal(a['F'],b['F']) and
        np.array_equal(a['S'],b['S']) and np.array_equal(a['M'],b['M']) for a,b in zip(resource['frames'],checked['frames'])),'V8 planes differ')
    infos.append(new);resources[ref]=resource;details.append(dict(resref=ref,frames=len(rows),sdf_bytes=int(new['sdf_bytes']),
        V7_sha256=info['sha256'],V9_sha256=new['sha256'],frame_masks=rows))
    print(json.dumps(dict(resref=ref,frames=len(rows),unique_masks=stats['unique_masks'])),flush=True)
require(stats['physical_frames']==516 and stats['acquired_offline_masks_reused']==12,'complete mask scope missing')
(isolated/'witnesses.oracle').write_bytes(old_oracle)
# Independent Python oracle for the encoded upload plane and native bordered compositor.
sdf_oracle=bytearray(b'IEESDF1\0')
for ref,prefix,geometry in chunks:
    resource=resources[ref]
    for frame in resource['frames']:
        for k,palette in enumerate(palette_map[ref]):
            rgba=resource['profile'].decode(frame['I'],frame['F'],palette)
            require(np.all(rgba[frame['I']>=2,3]==255),'foreground alpha contract')
            shadow=rgba[frame['I']==1]
            require(np.all(shadow[:,:3]==0) and np.all(shadow[:,3]==127),'shadow contract differs')
            m=frame['M'];valid=m!=0xffffffff
            encoded=np.zeros((*m.shape,4),np.uint8)
            encoded[valid,:3]=rgba.reshape(-1,4)[m[valid],:3]
            encoded[...,3]=frame['S']
            encoded[6:-6,6:-6,3]|=(frame['I']==1).astype(np.uint8)*128
            sdf_oracle.extend(hashlib.sha256(encoded.tobytes()).digest())
            if k==0:composite_sha=hashlib.sha256(encoded[4:-4,4:-4].tobytes()).digest()
        sdf_oracle.extend(composite_sha)
(isolated/'sdf.oracle').write_bytes(sdf_oracle)
components=[];shards=[];directory=[]
for n,(info,detail) in enumerate(zip(infos,details)):
    entry=registry.catalog_shard_entry_bytes(info,isolated);digest=registry.catalog_component_digest(2,[entry])
    components.append(dict(index=n,digest=digest,shard_start=n,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=info['registry_bytes']))
    shards.append(dict(index=n,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(info['sha256']),**info))
    directory.append(dict(animation_id='0x3000',resref=detail['resref'],component_index=n,shard_index=n,resource_ordinal=0))
isolated_catalog=registry.write_registry_catalog_index(isolated/'CreatureSprites-XN.catalog',2,
    [dict(animation_id='0x3000',owner=9,component_indices=list(range(12)))],components,shards,directory,
    [c['digest'] for c in components],dict(shard_registry_versions=[9]))
write_json(isolated/'pack.json',dict(catalog=isolated_catalog,leaves=infos))

# Replace exactly the twelve Ankheg components; all other native routes remain byte-identical.
parent=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',previous['catalog']['sha256'])
mixed=copy.deepcopy(parent);logical=load(parent_root/'pack.json')['catalog']['logical_component_digests'][:]
out=work/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
targets={r['resref']:r for r in parent['directory'] if r['animation_id']=='0x3000'}
require(set(targets)==set(resources),'parent Ankheg scope differs')
replacement={}
for local,(info,detail) in enumerate(zip(infos,details)):
    binding=targets[detail['resref']];ci,si=binding['component_index'],binding['shard_index']
    require(parent['components'][ci]['shard_count']==1 and parent['shards'][si]['resource_count']==1,'unexpected component layout')
    replacement[si]=isolated/registry.catalog_shard_filename(info['sha256'])
    mixed['shards'][si]=dict(shards[local],index=si)
    mixed['components'][ci]=dict(components[local],index=ci,shard_start=si)
    logical[ci]=components[local]['digest']
for si,shard in enumerate(mixed['shards']):
    source=replacement.get(si,parent_root/shard['registry']);require(source.is_file(),'source leaf missing')
    os.link(source,assets/source.name)
catalog=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,mixed['animations'],mixed['components'],
    mixed['shards'],mixed['directory'],logical,dict(shard_registry_versions=[6,7,9]))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',catalog['sha256'])
require(checked['animations']==parent['animations'] and checked['directory']==parent['directory'],'native bindings altered')
require(all(checked['shards'][i]==s for i,s in enumerate(parent['shards']) if i not in replacement),'unrelated leaf changed')
require(checked['total_resources']==4572 and checked['total_frames']==1586172,'physical scope altered')
write_json(out/'pack.json',dict(catalog=catalog,new_shards=[mixed['shards'][i] for i in sorted(replacement)]))
baseline=dict(game_root='config://bg2ee_game_root',catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog',
    parent_generation=identity(parent_run/'current-generation.json'),parent_catalog_sha256=previous['catalog']['sha256'],
    dll_sha256=file_sha(game/'InfinityEngine-Enhancer.dll'),ini_sha256=file_sha(game/'InfinityEngine-Enhancer.ini'),
    executable_sha256=file_sha(game/'BaldurReal.exe'),inherited_animations_unchanged=87,unchanged_assets=[])
runtime=load(ROOT/previous['runtime']['path'])
for entry in runtime['shaders']+runtime['preserved_packs']+runtime['paperdoll_packs']:
    path=game/entry['target']
    if path.name in ('fpDraw.glsl','fpSprite.glsl','fpSELECT.glsl'):continue
    baseline['unchanged_assets'].append(dict(relative_path=entry['target'],sha256=file_sha(path)))
baseline['replaced_shaders']=[dict(relative_path='override/'+n,sha256=file_sha(game/'override'/n)) for n in ('fpDraw.glsl','fpSprite.glsl','fpSELECT.glsl')]
write_json(HERE/'baseline.json',baseline)
write_json(HERE/'production.json',dict(recipe=recipe,stats=stats,details=details,
    Q3m_colour_planes_byte_identical=True,source_geometry_cycles_byte_identical=True,reference_offline_masks_reused=12,
    original_generation=identity(original_run/'current-generation.json'),original_production=identity(original_run/'production.json'),
    oracle=identity(isolated/'witnesses.oracle'),catalog=identity(assets/'CreatureSprites-XN.catalog'),
    registry_version=9,colour_profile=8,decode_rule=3,scope='complete monster_ankheg only',
    unchanged_native_bindings=50253,unchanged_other_animations=87,ingame_QA=False))

print(json.dumps(dict(stats=stats,catalog=catalog['sha256'],complete=True)),flush=True)
