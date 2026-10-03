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
from sprite_spline_coverage import coverage,apply

def require(ok,message):
    if not ok:raise ValueError(message)
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
parent_run=ROOT/'docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1'
previous=load(parent_run/'current-generation.json');production=load(parent_run/'production.json')
parent_root=ROOT/previous['generation_dir'];source_dir=ROOT/production['pack_directory']
game=get_path('bg2ee_game_root',required=True)
require(file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==previous['catalog']['sha256'],'active catalog differs')
require(file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256'],'active DLL differs')
work=ROOT/'sprite/.work/q3m-ankheg-spline-fit1-x2-20261003-v1';isolated=work/'isolated'
require(not work.exists() and not (HERE/'production.json').exists(),'fresh run required')
isolated.mkdir(parents=True);cache=work/'mask-cache';cache.mkdir()
recipe=dict(method='periodic-cubic-spline-fit1-inward-coverage',fit_error_x2=1.0,band_x2=2.0,
    thin_radius_x2=2.0,supersample=4,spacing_x2=1.5,protect_special_classes=True,expand_outside_source=False)
recipe_bytes=json.dumps(recipe,sort_keys=True).encode()+bytes.fromhex(file_sha(ROOT/'pipeline/scripts/sprite_spline_coverage.py'))+bytes.fromhex(file_sha(ROOT/'pipeline/scripts/build_per_frame_spline_alpha_30fps_v2.py'))
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
    frames_changed=0,physical_pixels_changed=0,physical_pixels_cleared=0,new_neural_targets=0,new_Q3m_encodings=0)
details=[]
for info in production['pack']['leaves']:
    source=source_dir/registry.catalog_shard_filename(info['sha256'])
    require(file_sha(source).upper()==info['sha256'],'sealed V7 leaf changed')
    parsed=leaves.inspect(source,include_frames=True);resource=parsed['resources'][0]
    ref=resource['resref'];profile=resource['profile'];rows=[];changed=0
    for ordinal,frame in enumerate(resource['frames']):
        binary=frame['I']>=3
        key=hashlib.sha256(recipe_bytes+struct.pack('<II',*binary.shape)+np.packbits(binary).tobytes()).hexdigest()
        if key in mask_cache:mask,report=mask_cache[key];stats['mask_cache_hits']+=1
        else:
            mask,report=coverage(frame['I'],fit_error=1.0,band=2.0,thin_radius=2.0,supersample=4)
            np.savez_compressed(cache/(key+'.npz'),A=mask);mask_cache[key]=(mask,report);stats['unique_masks']+=1
        require(np.all(mask[frame['I']<3]==255),'native special altered')
        frame['A']=mask;frame['guide']=frame['I'].copy();frame['dep']=np.frombuffer(frame['dep'],np.uint8).copy()
        rows.append(dict(frame=ordinal,mask_key=key,**report))
        stats['physical_frames']+=1;stats['frames_changed']+=int(report['changed_pixels']>0)
        stats['physical_pixels_changed']+=report['changed_pixels'];stats['physical_pixels_cleared']+=report.get('cleared_pixels',0)
        changed+=report['changed_pixels']>0
    materials=dict(resref=ref,source_sha256=resource['source_sha256'],frames=resource['frames'],cycles=resource['cycles'])
    path=isolated/(ref+'.registry');new=leaves.write(path,[materials],profile,version=8)
    sealed=isolated/registry.catalog_shard_filename(new['sha256']);path.replace(sealed)
    checked=leaves.inspect(sealed,include_frames=True)['resources'][0]
    require(checked['cycles']==resource['cycles'] and checked['source_sha256']==resource['source_sha256'],'source/cycles altered')
    require(all(a['geometry']==b['geometry'] and np.array_equal(a['I'],b['I']) and np.array_equal(a['F'],b['F']) and
        np.array_equal(a['A'],b['A']) for a,b in zip(resource['frames'],checked['frames'])),'V8 planes differ')
    infos.append(new);resources[ref]=resource;details.append(dict(resref=ref,frames=len(rows),frames_changed=int(changed),
        V7_sha256=info['sha256'],V8_sha256=new['sha256'],frame_masks=rows))
    print(json.dumps(dict(resref=ref,frames=len(rows),changed=changed,unique_masks=stats['unique_masks'])),flush=True)
require(stats['physical_frames']==516 and stats['frames_changed']>0,'complete mask scope missing')
oracle=bytearray(old_oracle[:12])
for ref,prefix,geometry in chunks:
    oracle.extend(prefix);resource=resources[ref]
    for frame,(w,h,cx,cy) in zip(resource['frames'],geometry):
        require(frame['geometry'][:4]==(w,h,cx,cy),'oracle geometry changed')
        oracle.extend(struct.pack('<IIii',w,h,cx,cy))
        for palette in palette_map[ref]:
            rgba=resource['profile'].decode(frame['I'],frame['F'],palette)
            oracle.extend(hashlib.sha256(apply(rgba,frame['A']).tobytes()).digest())
(isolated/'witnesses.oracle').write_bytes(oracle)
components=[];shards=[];directory=[]
for n,(info,detail) in enumerate(zip(infos,details)):
    entry=registry.catalog_shard_entry_bytes(info,isolated);digest=registry.catalog_component_digest(2,[entry])
    components.append(dict(index=n,digest=digest,shard_start=n,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=info['registry_bytes']))
    shards.append(dict(index=n,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(info['sha256']),**info))
    directory.append(dict(animation_id='0x3000',resref=detail['resref'],component_index=n,shard_index=n,resource_ordinal=0))
isolated_catalog=registry.write_registry_catalog_index(isolated/'CreatureSprites-XN.catalog',2,
    [dict(animation_id='0x3000',owner=9,component_indices=list(range(12)))],components,shards,directory,
    [c['digest'] for c in components],dict(shard_registry_versions=[8]))
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
    mixed['shards'],mixed['directory'],logical,dict(shard_registry_versions=[6,7,8]))
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
    path=game/entry['target'];baseline['unchanged_assets'].append(dict(relative_path=entry['target'],sha256=file_sha(path)))
write_json(HERE/'baseline.json',baseline)
write_json(HERE/'production.json',dict(recipe=recipe,stats=stats,details=details,
    Q3m_colour_planes_byte_identical=True,source_geometry_cycles_byte_identical=True,
    original_generation=identity(parent_run/'current-generation.json'),original_production=identity(parent_run/'production.json'),
    oracle=identity(isolated/'witnesses.oracle'),catalog=identity(assets/'CreatureSprites-XN.catalog'),
    registry_version=8,colour_profile=8,decode_rule=3,scope='complete monster_ankheg only',
    unchanged_native_bindings=50253,unchanged_other_animations=87,ingame_QA=False))

# Four body poses on two backgrounds, original Q3m / Q3m+spline; no interpolation in PNG.
preview=Image.new('RGB',(980,620),(32,34,38));draw=ImageDraw.Draw(preview)
draw.text((15,10),'Ankheg Q3m x2 - original (left) / Spline Fit 1 (right)',fill='white')
for pose,ref in enumerate(('MAKHG1','MAKHG1E','MAKHG2','MAKHG3')):
    resource=resources[ref];ordinal=11 if ref=='MAKHG1' else len(resource['frames'])//2
    frame=resource['frames'][ordinal];raw=resource['profile'].decode(frame['I'],frame['F'],palette_map[ref][0]);masked=apply(raw,frame['A'])
    x=(pose%2)*490;y=40+(pose//2)*285;draw.text((x+12,y),ref+' / frame '+str(ordinal),fill='white')
    for variant,rgba in enumerate((raw,masked)):
        im=Image.fromarray(rgba,'RGBA');im.thumbnail((210,235),Image.Resampling.NEAREST)
        background=Image.new('RGBA',(220,240),(95,104,112,255));background.alpha_composite(im,((220-im.width)//2,(240-im.height)//2))
        preview.paste(background.convert('RGB'),(x+10+variant*235,y+24))
preview.save(HERE/'comparison.png')
print(json.dumps(dict(stats=stats,catalog=catalog['sha256'],complete=True)),flush=True)
