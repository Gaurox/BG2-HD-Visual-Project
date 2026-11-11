"""Validate ten x4 images and create matched 100% crops without further enhancement."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
if (HERE/'results.json').exists():raise SystemExit('Results already finalized; preserve outputs, create a new run for replacements.')
rows=json.loads((HERE/'sources.json').read_text(encoding='utf-8'));results=[]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
crops={'INVSTATS':[(0,0),(80,210)],'GUIINVHI':[(0,0),(250,220)],'GUIMGX':[(0,0),(160,460)],'GUIMGB':[(0,0),(365,250)],'GUIPRB':[(0,0),(70,200)],'GUIMGCP':[(0,0),(30,180)],'GUICUSTB':[(0,0),(300,320)],'GUICHISD':[(0,0),(360,250)],'GUITUTB':[(0,0),(370,200)],'GUILOAD':[(0,0),(20,400)]}
cache={}
def flatten(im,bg='#363630'):
 base=Image.new('RGBA',im.size,bg);base.alpha_composite(im.convert('RGBA'));return base.convert('RGB')
for row in rows:
 n=row['resref'];src=Image.open(HERE/'sources'/f'{n}-x1.png').convert('RGBA');expected=tuple(row['expected_x4']);native=src.resize(expected,Image.Resampling.NEAREST);raws=list((HERE/'outputs'/n/'raw').glob('*.png'));assert len(raws)==1;raw=Image.open(raws[0]).convert('RGBA');assert raw.size==tuple(v*4 for v in row['padded_size']);output=raw.crop((0,0,*expected));output.putalpha(native.getchannel('A'));path=HERE/'outputs'/n/f'{n}-seedvr-7b-x4.png';output.save(path);assert output.getchannel('A').tobytes()==native.getchannel('A').tobytes()
 results.append(dict(number=row['number'],resref=n,label=row['label'],state='produced-awaiting-user-review',size=list(output.size),output=path.relative_to(HERE).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),raw=raws[0].relative_to(HERE).as_posix(),crops_native_xy=crops[n]));cache[n]=(native,output)
 board=Image.new('RGB',(1024,1340),'#242321');d=ImageDraw.Draw(board);d.text((16,12),f"{row['number']}. {row['label']}",font=font,fill='white')
 for col,(im,label) in enumerate([(native,'Original agrandi x4'),(output,'SeedVR 7B x4')]):
  x=col*512;d.text((x+16,52),label,font=small,fill='white');preview=im.copy();preview.thumbnail((480,430),Image.Resampling.LANCZOS);board.paste(flatten(preview),(x+16+(480-preview.width)//2,90))
  for j,(cx,cy) in enumerate(crops[n]):
   y=550+j*390;d.text((x+16,y),f'Zoom {j+1} — pixels x4 à 100 %',font=small,fill='white');crop=im.crop((cx*4,cy*4,cx*4+480,cy*4+336));board.paste(flatten(crop),(x+16,y+34))
 board.save(HERE/'comparison'/f'{row["number"]:02}-{n}-original-7b-zooms.png')
for group in range(2):
 batch=rows[group*5:group*5+5];overview=Image.new('RGB',(1700,1680),'#242321');d=ImageDraw.Draw(overview);zoom=Image.new('RGB',(1024,1670),'#242321');dz=ImageDraw.Draw(zoom)
 dz.text((16,10),'Original agrandi x4',font=font,fill='white');dz.text((528,10),'SeedVR 7B x4',font=font,fill='white')
 for j,row in enumerate(batch):
  n=row['resref'];native,output=cache[n];x=j%2*850;y=j//2*560;d.rounded_rectangle((x+8,y+8,x+842,y+552),10,fill='#302e2a',outline='#6a6253',width=2);d.text((x+22,y+20),f"{row['number']}. {row['label']}",font=font,fill='white');d.text((x+22,y+52),f'{n} — SeedVR 7B x4',font=small,fill='#c9c3b7');preview=output.copy();preview.thumbnail((800,450),Image.Resampling.LANCZOS);overview.paste(flatten(preview),(x+25+(800-preview.width)//2,y+88+(450-preview.height)//2))
  yy=55+j*320;dz.text((16,yy),f"{row['number']}. {row['label']}",font=small,fill='white');cx,cy=crops[n][0]
  for col,im in enumerate((native,output)):zoom.paste(flatten(im.crop((cx*4,cy*4,cx*4+480,cy*4+256))),(col*512+16,yy+36))
 overview.save(HERE/'comparison'/f'overview-{group*5+1:02}-{group*5+5:02}.png');zoom.save(HERE/'comparison'/f'zooms-{group*5+1:02}-{group*5+5:02}.png')
manifest=dict(schema='bg2-ui-seedvr7b-batch-v1',state='produced-awaiting-user-review',recipe=dict(model='seedvr2_7b_int8_convrot.safetensors',scale=4,color_correction='lab',seed=959948902156062,steps=1,cfg=1,sampler='euler',scheduler='simple',padding='edge replication to64, exact crop after inference',alpha='native alpha nearest x4 reapplied separately'),results=results,qa='awaiting user comparison; not ingame accepted',installation='not installed',release='unchanged')
(HERE/'results.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('10/10 dimensions and alpha checked; all sheets generated')
