"""Finalize the eight exact SeedVR outputs and render matched comparison boards."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
if not (P/'seedvr-3b-x4').exists():
 raise SystemExit('Comparison finalized: 3B intentionally removed, selected 7B must not be overwritten.')
rows=json.loads((P/'sources.json').read_text(encoding='utf-8'));results=[]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
crops={'INVENTOR':[(0,0),(30,260)],'QUESTBAK':[(0,110),(0,590)],'GUIREC2':[(0,0),(25,400)],'STONEOPT':[(200,100),(90,380)]}
for row in rows:
 n=row['resref'];src=Image.open(P/'sources'/f'{n}-x1.png').convert('RGBA');w,h=src.size;images=[src.resize((w*4,h*4),Image.Resampling.NEAREST)]
 for model in ['7b','3b']:
  folder=P/f'seedvr-{model}-x4'/n;raw=list((folder/'raw').glob('*.png'));assert len(raw)==1
  im=Image.open(raw[0]).convert('RGBA');expected=tuple(v*4 for v in row['padded_size']);assert im.size==expected,(n,im.size,expected)
  im=im.crop((0,0,w*4,h*4));im.putalpha(images[0].getchannel('A'));out=folder/f'{n}-seedvr-{model}-x4.png';im.save(out);images.append(im)
  results.append(dict(resref=n,model=model,state='produced-awaiting-user-comparison',output=out.relative_to(P).as_posix(),size=list(im.size),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),raw_output=raw[0].relative_to(P).as_posix()))
 # 3 columns at equal physical scale. Full images fitted, crops are 1 output pixel per PNG pixel.
 overviewh=780 if n=='QUESTBAK' else 460;height=90+overviewh+2*410
 board=Image.new('RGB',(1536,height),'#20201e');draw=ImageDraw.Draw(board)
 draw.text((18,12),row['label']+' — original / SeedVR 7B / SeedVR 3B',font=font,fill='white')
 for col,(im,label) in enumerate(zip(images,['Original x1 agrandi x4','SeedVR 7B x4','SeedVR 3B x4'])):
  x=col*512;draw.text((x+16,55),label,font=small,fill='white');preview=im.copy();preview.thumbnail((480,overviewh-15),Image.Resampling.LANCZOS);bg=Image.new('RGBA',preview.size,'#383834');bg.alpha_composite(preview);board.paste(bg.convert('RGB'),(x+16+(480-preview.width)//2,90))
  for j,(cx,cy) in enumerate(crops[n]):
   y=90+overviewh+j*410;draw.text((x+16,y),f'Detail {j+1} — pixels x4 a 100 %',font=small,fill='white');crop=im.crop((cx*4,cy*4,cx*4+480,cy*4+360));bg=Image.new('RGBA',crop.size,'#383834');bg.alpha_composite(crop);board.paste(bg.convert('RGB'),(x+16,y+34))
 board.save(P/'comparison'/f'{n}-original-7b-3b.png')
manifest=dict(schema='bg2-ui-seedvr-comparison-v1',state='awaiting-user-comparison',seed=959948902156062,scale=4,color_correction='lab',steps=1,cfg=1,sampler='euler',scheduler='simple',padding='right/bottom edge replication to multiple64; exact crop after inference',alpha='native alpha nearest x4 applied separately after RGB inference',results=results,qa='not accepted',installation='not installed',release='unchanged')
(P/'results.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Verified and rendered',len(results),'outputs')
