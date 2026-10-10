"""Analyse effective ARE/WED resources for six planar areas, no game writes."""
from pathlib import Path
import sys,struct,hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bg2lib import load_key,resolve_resource
from extract_area_animations import parse_area,decode_resref
from build_wed_cover_animation_patch import polygon_table
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v2
TAG='planar-sphinct-wed-crisp-20261010-v6';OUT=ROOT/'animations/batches'/TAG;OUT.mkdir(parents=True,exist_ok=True)
GAME=get_path('bg2ee_game_root');bifs,entries=load_key()
def effective(name,typ,ext):
 p=GAME/'override'/f'{name}.{ext}'
 if p.exists():return p.read_bytes(),str(p)
 matches=[loc for n,t,loc in entries if n.upper()==name and t==typ];assert len(matches)==1
 data,bif=resolve_resource(bifs,matches[0]);return data,bif
def polygons(data):
 n,po=polygon_table(data);so=struct.unpack_from('<I',data,20)[0];vo=struct.unpack_from('<I',data,so+8)[0]
 out=[]
 for i in range(n):
  first,count,flags,height=struct.unpack_from('<IIBB',data,po+i*18)
  points=[struct.unpack_from('<HH',data,vo+4*(first+j)) for j in range(count)]
  if len(points)>=3:out.append(dict(index=i,flags=flags,height=height,points=points))
 return out
def payload(path):
 return {p.name:v2.sha256_file(p) for p in path.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
def intersects(points,box):
 return max(p[0] for p in points)>=box[0] and min(p[0] for p in points)<box[2] and max(p[1] for p in points)>=box[1] and min(p[1] for p in points)<box[3]
report=dict(areas={},created_utc=v2.utc_now(),installed=False)
lock=v2.load_json(ROOT/'animations/index/area-pack-lock.json')['areas']
for area in ['AR0516','AR0517','AR0518','AR0519','AR0520','AR0521']:
 are,asource=effective(area,1010,'ARE');wedref=decode_resref(are,8);wed,wsource=effective(wedref,1001,'WED')
 occs=[o for o in parse_area(area,are) if o['resource_resref'] in ('SPHINCT','SPHINCT2')]
 base=ROOT/lock[area]['build']['leaf'] if 'leaf' in lock[area]['build'] else ROOT/'animations/packs-par-zone/ar0517-sphinct-wed-crisp-20261010-v5/AR0517'
 _,resources=v2.validate_v2_pack(base);assert payload(GAME/'iee-assets/areas'/area)==payload(base),area+' installed drift'
 polys=polygons(wed);details=[]
 for o in occs:
  r=next(r for r in resources if r['resref']==o['resource_resref']);lw,lh=r['frames'][0]['logical_size_x1'];cx,cy=r['frames'][0]['centre_x1']
  box=[o['x']-cx,o['y']-cy,o['x']-cx+lw,o['y']-cy+lh]
  selected=[p for p in polys if intersects(p['points'],box)]
  raw=np.frombuffer((base/r['frames'][8]['asset']).read_bytes(),np.uint8).reshape(lh*4,lw*4,4)
  for p in selected:
   m=Image.new('L',(lw*4,lh*4));ImageDraw.Draw(m).polygon([((x-box[0])*4,(y-box[1])*4) for x,y in p['points']],fill=255)
   p=dict(p);p['active_pixels_frame8']=int(((np.asarray(m)>0)&(raw[:,:,3]>0)).sum())
   details.append(dict(occurrence=o['occurrence_index'],resref=o['resource_resref'],position=[o['x'],o['y']],box=box,polygon=p))
 report['areas'][area]=dict(wed_ref=wedref,wed_sha256=hashlib.sha256(wed).hexdigest(),wed_source=wsource,are_sha256=hashlib.sha256(are).hexdigest(),
   are_source=asource,base=base.relative_to(ROOT).as_posix(),resources=[dict(resref=r['resref'],position=r.get('position'),frames=r['frame_count'],physical_size=r['frames'][0]['physical_size_x4']) for r in resources],
   occurrences=occs,intersections=details)
v2.write_json(OUT/'analysis.json',report)
bg=Image.open(ROOT/'maps/AR0516/runs/seedvr2-7b-int8-lab-grid-2x3-x4/tuiles-principales/03_assemble/AR0516-tuiles-principales-x4-seedvr2-7b-int8-lab-overlap.png').convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
palette=[(0,255,80),(255,60,60),(50,180,255),(250,220,0),(220,100,255),(255,160,80)]
area=report['areas']['AR0516']
for o in area['occurrences']:
 info=[d for d in area['intersections'] if d['occurrence']==o['occurrence_index']];box=info[0]['box']
 cb=(box[0]*4-64,box[1]*4-64,box[2]*4+64,box[3]*4+64)
 plain=bg.crop(cb);marked=plain.copy();draw=ImageDraw.Draw(marked)
 for k,d in enumerate(info):
  p=d['polygon'];pts=[(x*4-cb[0],y*4-cb[1]) for x,y in p['points']]
  draw.line(pts+[pts[0]],fill=palette[k%len(palette)],width=2)
  # Label inside cropped polygon near its centroid, clamped to the view.
  pts=np.asarray(pts);pos=np.mean(pts,axis=0);pos=np.clip(pos,[4,4],[plain.width-125,plain.height-25])
  draw.text(tuple(pos),f"P{p['index']} f{p['flags']:02x}",font=font,fill=palette[k%len(palette)],stroke_width=1,stroke_fill='black')
 board=Image.new('RGB',(plain.width*2,plain.height+35),(20,23,29));bd=ImageDraw.Draw(board)
 bd.text((8,8),f"AR0516 {o['resource_resref']} occurrence{o['occurrence_index']} @ {o['x']},{o['y']}",font=font,fill='white')
 board.paste(plain,(0,35));board.paste(marked,(plain.width,35));board.save(OUT/f"AR0516-occ{o['occurrence_index']}-polygons.png")
for a,info in report['areas'].items():
 print(a,info['wed_ref'],info['wed_sha256'][:12],[(o['resource_resref'],o['x'],o['y']) for o in info['occurrences']])
 if a=='AR0516':print([(d['occurrence'],d['polygon']['index'],hex(d['polygon']['flags']),d['polygon']['active_pixels_frame8']) for d in info['intersections']])
