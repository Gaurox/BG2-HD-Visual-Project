import json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path.cwd();out=root/'video/research/endings-locales-analysis-20261111-v1'
r=json.loads((out/'END15FPS-production-mapping.json').read_text());mp=r['mapping'];edits=[e['locale_frame'] for e in r['edits']]
indices=sorted({max(0,min(len(mp)-1,j+d)) for j in edits for d in [-1,0,1]})
requested={'default':sorted({mp[j] for j in indices}),'pl_PL':indices}
images={}
for loc,idx in requested.items():
 src=json.loads((out/f'END15FPS-{loc}.metadata.json').read_text())['source']
 expression='+'.join(f'eq(n\\,{i})' for i in idx)
 raw=subprocess.check_output(['ffmpeg','-v','error','-threads','2','-i',src,'-vf',f'select={expression},scale=240:135','-pix_fmt','rgb24','-fps_mode','passthrough','-threads','1','-f','rawvideo','-'])
 arr=np.frombuffer(raw,np.uint8).reshape(-1,135,240,3);assert len(arr)==len(idx)
 images[loc]={i:Image.fromarray(a) for i,a in zip(idx,arr)}
for page,start in enumerate(range(0,len(edits),8),1):
 sheet=Image.new('RGB',(1440,8*158),(20,20,20));draw=ImageDraw.Draw(sheet)
 for row,j in enumerate(edits[start:start+8]):
  for col,d in enumerate([-1,0,1]):
   k=max(0,min(len(mp)-1,j+d))
   for side,(loc,i) in enumerate([('default',mp[k]),('pl_PL',k)]):
    x=(2*col+side)*240;y=row*158
    sheet.paste(images[loc][i],(x,y+23));draw.text((x+3,y+3),f'{loc} #{i} / edit PL{j}',fill='white')
 sheet.save(out/f'END15FPS-production-edits-{page}.jpg',quality=94)
