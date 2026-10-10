from pathlib import Path
import sys,numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
OUT=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v6';report=v2.load_json(OUT/'analysis.json')
area=report['areas']['AR0516'];base=ROOT/area['base'];_,resources=v2.validate_v2_pack(base)
for occurrence in area['occurrences']:
 resource=next(r for r in resources if r['resref']==occurrence['resource_resref'])
 masks=[]
 for d in [d for d in area['intersections'] if d['occurrence']==occurrence['occurrence_index']]:
  p=d['polygon'];box=d['box'];lw,lh=resource['frames'][0]['logical_size_x1'];mask=Image.new('L',(lw*4,lh*4))
  ImageDraw.Draw(mask).polygon([((x-box[0])*4,(y-box[1])*4) for x,y in p['points']],fill=255)
  masks.append((p,np.array(mask)>0))
 for p,mask in masks:
  counts=[]
  for f in resource['frames']:
   w,h=f['physical_size_x4'];raw=np.frombuffer((base/f['asset']).read_bytes(),np.uint8).reshape(h,w,4)
   counts.append(int((mask&(raw[:,:,3]>0)).sum()))
  p['active_pixels_min_all_frames']=min(counts);p['active_pixels_max_all_frames']=max(counts)
  print(occurrence['occurrence_index'],p['index'],hex(p['flags']),min(counts),max(counts))
v2.write_json(OUT/'analysis-all-phases.json',report)
