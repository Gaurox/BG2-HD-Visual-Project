import json,sys,zlib,struct,io,hashlib,importlib.util
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path.cwd();HERE=ROOT/'interface/integration/journal-paper-seedvr7b-20261111-v1';RUN=ROOT/'interface/experiments/journal-paper-seedvr7b-20261111-v1'
spec=importlib.util.spec_from_file_location('oldbuild',ROOT/'interface/integration/four-menus-seedvr7b-20261111-v1/build_assets.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
from bg2lib import load_key,resolve_resource
from workspace_paths import get_path
if (HERE/'assets.json').exists(): raise SystemExit('Existing final assets; create a new run instead of overwriting.')
resources=json.loads((ROOT/'interface/analysis/journal-controls-20261111-v1/resources.json').read_text())[0];pages={};outputs=[]
for f in resources['frames']:
 i=f['frame'];src=Image.open(RUN/'sources'/f'QUESTBG-frame-{i}-x1.png').convert('RGBA');im=Image.open(next((RUN/f'outputs/frame-{i}/raw').glob('*.png'))).convert('RGBA');assert im.size==(512*4,768*4);im=im.crop((0,0,src.width*4,src.height*4));im.putalpha(src.getchannel('A').resize(im.size,Image.Resampling.NEAREST));path=RUN/'outputs'/f'QUESTBG-frame-{i}-7b-x4.png';im.save(path);outputs.append(dict(frame=i,output=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size=list(im.size)))
 for page,sx,sy,w,h,dx,dy in f['blocks']:pages.setdefault(page,[]).append((i,im,sx,sy,w,h,dx,dy))
 # preview native / 7B at same scale
 board=Image.new('RGB',(1000,830),'#262622');d=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
 for c,(pic,label) in enumerate([(src,'Natif'),(im,'SeedVR 7B x4')]):
  d.text((c*500+20,15),label,font=font,fill='white');pic=pic.copy();pic.thumbnail((470,770));bg=Image.new('RGBA',pic.size,'#44443c');bg.alpha_composite(pic);board.paste(bg.convert('RGB'),(c*500+15,55))
 board.save(RUN/'comparison'/f'QUESTBG-frame-{i}-native-7b.png')
b,e=load_key();idx={(n.upper(),k):loc for n,k,loc in e};manifest=[];(HERE/'assets').mkdir(exist_ok=True)
for page,blocks in sorted(pages.items()):
 pvrz=resolve_resource(b,idx[f'MOS{page:04}',1028])[0];pvr=zlib.decompress(pvrz[4:]);header=list(struct.unpack_from('<13I',pvr));h,w=header[6:8];raw=pvr[52+header[12]:];assert header[2]==11;(HERE/'native-fixtures'/f'MOS{page:04}.dxt5').write_bytes(raw)
 stem=f'GAMEPLAY7B-MOS{page:04}';base=get_path('bg2ee_game_root')/'iee-assets'/f'{stem}-x4.dxt5';baseline=base.read_bytes() if page==254 else bytes(old.expand_native(raw,w,h));atlas=Image.new('RGBA',(w*4,h*4));mask=bytearray(w*h);rects=[]
 for frame,im,sx,sy,bw,bh,dx,dy in blocks:
  atlas.paste(im.crop((dx*4,dy*4,(dx+bw)*4,(dy+bh)*4)),(sx*4,sy*4))
  for y in range(sy,sy+bh):
   assert not any(mask[y*w+sx:y*w+sx+bw]),'overlapping frame storage';mask[y*w+sx:y*w+sx+bw]=b'\1'*bw
  rects.append(dict(frame=frame,rect=[sx,sy,bw,bh]))
 buf=io.BytesIO();atlas.save(buf,format='DDS',pixel_format='DXT5');encoded=buf.getvalue()[128:];result=bytearray(baseline)
 for rect in rects:
  sx,sy,bw,bh=rect['rect']
  for y in range(sy,sy+bh):
   o=(y*w+sx)*16;result[o:o+bw*16]=encoded[o:o+bw*16]
 assert all(result[i*16:i*16+16]==baseline[i*16:i*16+16] for i,m in enumerate(mask) if not m)
 asset=HERE/'assets'/f'{stem}-x4.dxt5';asset.write_bytes(result);manifest.append(dict(page=page,asset=asset.name,width=w,height=h,sha256=hashlib.sha256(result).hexdigest(),baseline='installed four-menu x4' if page==254 else 'lossless native x4',baseline_sha256=hashlib.sha256(baseline).hexdigest(),rectangles=rects,untouched_blocks_exact=True,fnv1a64=f'{old.fnv(raw):016X}'))
(HERE/'assets.json').write_text(json.dumps(manifest,indent=2)+'\n');(RUN/'results.json').write_text(json.dumps(dict(state='prepared-for-ingame-test',recipe='SeedVR2 7B int8 convrot x4 LAB, seed959948902156062',outputs=outputs,jobs=['27cdf302-ccda-4a8b-87ed-fcd2f13f7b15','a66d1254-96a9-4a06-a807-b8eba78a7f32']),indent=2)+'\n');print('2 frames, 2 pages; untouched blocks identical')
