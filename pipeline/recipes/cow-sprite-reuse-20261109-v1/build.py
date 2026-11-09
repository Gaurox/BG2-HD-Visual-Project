"""Decode accepted COW Q3m pixels; adapt x2 to effect-x4 storage without inference."""
from pathlib import Path
import hashlib,json,struct,sys,copy
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam
import palette_partner_registry as q3m
from compose_effect_runtime_packs import validate_pack
OUT=ROOT/'projectiles/analysis/cow-sprite-reuse-20261109-v1'
SOURCE=ROOT/'sprite/.work/q3m-ambient-static-full-x2-20261004-v1/isolated'
HASH='46E72975D7D72C16667010420DC567A428597F2ECB0D9E410A0DEEEAC790FD97'
QA=ROOT/'sprite/index/qa-decisions/ambient_static/2026-10-04-accepted-full-ambient-static-horse-eye-v3-q3m-v7-x2-catmullrom-v1.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def digest(b):return hashlib.sha256(b).hexdigest().upper()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rel(p):return p.relative_to(ROOT).as_posix()
def main():
 assert not (OUT/'reuse.json').exists(),'Immutable completed bridge; use a new version'
 OUT.mkdir(parents=True,exist_ok=True);game=get_path('bg2ee_game_root',required=True)
 catalog=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog';raw=catalog.read_bytes()
 magic,version,scale,an,co,me,sh,*_=struct.unpack_from('<8sIIIIIIQQQQ',raw);assert version==2 and scale==2
 nd,entry=struct.unpack_from('<II',raw,64);assert entry==24
 shard_offset=104+an*16+me*4+co*72;directory=shard_offset+sh*64
 routes=[struct.unpack_from('<I8sIII',raw,directory+i*24) for i in range(nd)]
 route=next(t for t in routes if t[0]==0xB000 and t[1].split(b'\0')[0]==b'ACOWG1')
 active_hash=raw[shard_offset+route[3]*64:shard_offset+route[3]*64+32].hex().upper();assert active_hash==HASH
 filename='CreatureSprites-XN-'+HASH+'.registry';source=SOURCE/filename;active=catalog.parent/filename
 assert sha(source)==sha(active)==HASH
 data=q3m.inspect(source,include_frames=True);resource=data['resources'][0]
 assert data['version']==7 and data['scale']==2 and resource['resref']=='ACOWG1'
 qa=json.loads(QA.read_text(encoding='utf-8'));assert qa['status']=='accepted' and '0xB000' in qa['scope']['animation_ids']
 bifs,entries=load_key();key={(n.upper(),t):l for n,t,l in entries};native,_=resolve_resource(bifs,key['ACOWG1',1000])
 import zlib
 uncompressed=zlib.decompress(native[12:]) if native[:4]==b'BAMC' else native
 assert digest(uncompressed)==resource['source_sha256'].upper();native_frames,pal,tr=decode_bam(uncompressed);cycles=cycle_metadata(uncompressed,len(native_frames))
 assert [c['frame_indices'] for c in cycles]==resource['cycles'] and len(native_frames)==22
 # The stored K6 oracle pins exact accepted V7 decode, including shadow alpha127.
 oracle=(SOURCE/'witnesses.oracle').read_bytes();assert oracle[:8]==b'IEEQP7\0\0'
 aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',oracle,12);assert (aid,owner,ref.rstrip(b'\0'),nf,nc)==(0xB000,13,b'ACOWG1',22,40)
 pos=12+24;palettes=np.frombuffer(oracle,np.uint8,6*1024,pos).reshape(6,256,4).copy();pos+=6*1024
 assert oracle[pos:pos+2052]==resource['profile'].metadata();pos+=2052
 for c in resource['cycles']:
  count=struct.unpack_from('<I',oracle,pos)[0];pos+=4;assert count==len(c)
  assert list(struct.unpack_from(f'<{count}I',oracle,pos))==c;pos+=count*4
 pack=OUT/'pack';pack.mkdir(exist_ok=True);frames=[];proof=[];checks=[]
 for n,(frame,native_frame) in enumerate(zip(resource['frames'],native_frames)):
  w,h,cx,cy,transparent=frame['geometry'];idx,ncx,ncy,_=native_frame
  assert (w,h,cx,cy,transparent)==(idx.shape[1],idx.shape[0],ncx,ncy,tr)
  ow,oh,ox,oy=struct.unpack_from('<IIii',oracle,pos);pos+=16;assert (ow,oh,ox,oy)==(w,h,cx,cy)
  expected=[oracle[pos+i*32:pos+(i+1)*32] for i in range(6)];pos+=192
  for p,e in zip(palettes,expected):assert hashlib.sha256(resource['profile'].decode(frame['I'],frame['F'],p).tobytes()).digest()==e
  rgba2=resource['profile'].decode(frame['I'],frame['F'],palettes[0]);rgba4=rgba2.repeat(2,0).repeat(2,1)
  assert np.array_equal(rgba4[::2,::2],rgba2)
  source2=OUT/'decoded-x2'/f'frame{n:03d}.rgba';source2.parent.mkdir(exist_ok=True);source2.write_bytes(rgba2.tobytes())
  name=f'EFX4-ACOWG1-frame{n:03d}.rgba';(pack/name).write_bytes(rgba4.tobytes())
  frames.append(dict(frame=n,resource_frame=n,resref='ACOWG1',asset=name,source=rel(pack/name),source_q3m_x2=rel(source2),sha256=digest(rgba4.tobytes()),bytes=rgba4.nbytes,logical_size_x1=[w,h],physical_size_x4=[w*4,h*4],source_centre_x1=[cx,cy]))
  proof.append(dict(frame=n,q3m_x2_sha256=digest(rgba2.tobytes()),effect_storage_x4_sha256=digest(rgba4.tobytes()),native_geometry=[w,h,cx,cy],six_palette_oracle_hashes_exact=True,nearest2_inverse_exact=True))
 native_cycles=resource['cycles'];tables=[[f for f in c for _ in (0,1)] for c in native_cycles];maximum=max(map(len,tables))
 block=bytearray(b'ACOWG1\0\0'+struct.pack('<II',22,40))
 for f in frames:block.extend(struct.pack('<II',*f['logical_size_x1']))
 for c in native_cycles:block.extend(struct.pack(f'<I{len(c)}I',len(c),*c))
 block.extend(struct.pack('<IIIII',15,1,30,1,maximum))
 for t in tables:block.extend(struct.pack(f'<{maximum}I',*(t+[t[-1]]*(maximum-len(t)))))
 block.extend(struct.pack('<I',0))
 registry=b'IEEEFX4\0'+struct.pack('<IIII',3,4,1,0)+block;(pack/'EffectAnimations-X4.registry').write_bytes(registry)
 timing=dict(native_fps=[15,1],target_fps=[30,1],phase_count=maximum,native_frame_indices_by_cycle=native_cycles,timeline_frame_indices_by_cycle=tables,actual_phase_counts_by_cycle=list(map(len,tables)),policy='Every native frame repeated twice; no interpolation or new poses; native slot remains authoritative.')
 res=dict(resref='ACOWG1',production_bam='sprite:ACOWG1',frame_count=22,cycles=cycles,rgb_encoding='straight',source_sprite_scale=2,storage_adapter='nearest2-only to required effect x4 backing; exact original x2 pixels retained',source_q3m_shard_sha256=HASH,source_qa=rel(QA),timeline=timing)
 save(pack/'manifest.json',dict(schema='bg2-upscale-effect-animation-runtime-pack-v1',status='completed',scale=4,registry='EffectAnimations-X4.registry',registry_magic='IEEEFX4',registry_version=3,registry_bytes=len(registry),registry_sha256=digest(registry),resource_count=1,resources=[res],frame_count=22,frames=frames))
 validate_pack(pack)
 for c,(native_c,timeline) in enumerate(zip(native_cycles,tables)):
  for ph,target in enumerate(timeline):
   slot=ph//2;w,h=frames[target]['logical_size_x1']
   for once in (0,1):
    for name in ['ACOWG1','acowg1']:checks.append(f'{name}\t{slot}\t{w}\t{h}\t{ph}\t{c}\t{native_c[slot]}\t{target}\t{once}')
 (OUT/'runtime-contracts.tsv').write_text('\n'.join(checks)+'\n',encoding='ascii')
 # Review image uses the existing accepted x2 pixels, no image model or resampling.
 k=0;f=frames[k];w,h=f['logical_size_x1'];native_img=Image.fromarray(np.dstack((pal[native_frames[k][0]],np.where(native_frames[k][0]==tr,0,255).astype(np.uint8))))
 raw2=np.frombuffer((OUT/'decoded-x2/frame000.rgba').read_bytes(),np.uint8).reshape(h*2,w*2,4)
 sheet=Image.new('RGBA',(600,210),(35,44,58,255));sheet.alpha_composite(native_img.resize((w*2,h*2),Image.Resampling.NEAREST),(70,45));sheet.alpha_composite(Image.fromarray(raw2),(360,45));draw=ImageDraw.Draw(sheet);draw.text((28,15),'ACOWG1 natif x2',fill='white');draw.text((330,15),'Q3m x2 accepte / reutilise',fill='white');sheet.convert('RGB').save(OUT/'comparison.png')
 save(OUT/'reuse.json',dict(status='produced-adapter-awaiting-projectile-test',source_sprite=rel(source),source_shard_sha256=HASH,active_catalog_sha256=sha(catalog),active_route=dict(animation='0xB000',resource='ACOWG1',component=route[2],shard=route[3],ordinal=route[4]),sprite_QA=rel(QA),sprite_QA_sha256=sha(QA),frames=22,cycles=40,native_slots=sum(map(len,native_cycles)),contracts=len(checks),palette='Pinned neutral native fixed Realize K6 oracle; alpha0/127/255 retained',palette_oracle=rel(SOURCE/'witnesses.oracle'),pixel_checks=proof,pack=rel(pack),pack_manifest_sha256=sha(pack/'manifest.json'),neural_inference=0,temporal_interpolation=0,scale_policy='Reuse approved x2 pixels; nearest2 duplicates only for mandatory effect x4 storage, not a new x4 model production',limits=['Fixed neutral native palette; scene lighting variants not independently validated','Creature Q3m source/QA/catalogue unchanged; projectile QA remains separate','No position smoothing, gameplay or frame timing changes']))
 print('COW reused: 22 accepted x2 frames /40 native cycles; 132 palette oracle matches;',len(checks),'contracts; no inference/interpolation.')
if __name__=='__main__':main()
