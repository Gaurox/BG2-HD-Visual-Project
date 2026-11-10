from scanner import *
import struct
from run_creature_sprite_x2 import read_sealed_catalog_index
cat=A/'creature-sprites/CreatureSprites-XN.catalog';ci=read_sealed_catalog_index(cat,sha(cat.read_bytes()))
print('SPRITE MATCHES',[(d['resref'],d['animation_id']) for d in ci['directory'] if d['resref'] in remaining])
area=[]
for p in [A/'AreaAnimations-X4.registry']+list((A/'areas').glob('*/AreaAnimations-X4.registry')):
 raw=p.read_bytes();magic,v,scale,n,res=struct.unpack_from('<8sIIII',raw);pos=24
 for _ in range(n):
  start=pos;name=raw[pos:pos+8].rstrip(b'\0').decode();pos+=8;nf,nc=struct.unpack_from('<II',raw,pos);pos+=8
  if v>=2:pos+=20
  if v>=3:pos+=16
  pos+=nf*8
  for _ in range(nc):
   ns=struct.unpack_from('<I',raw,pos)[0];pos+=4+ns*4
   if v>=2:
    nt=struct.unpack_from('<I',raw,pos)[0];pos+=4+nt*4
  if name in remaining:area.append(dict(resref=name,path=str(p),block_sha256=sha(raw[start:pos]),registry_sha256=sha(raw)))
 assert pos==len(raw),(p,pos,len(raw))
print('AREA MATCHES',[(x['resref'],Path(x['path']).parent.name) for x in area])
(OUT/'installed183.json').write_text(json.dumps(dict(area=area,sprite=[d for d in ci['directory'] if d['resref'] in remaining]),indent=2))
