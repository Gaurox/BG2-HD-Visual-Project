"""Publish native/produced animation board including six intentionally native masks."""
import json,time,shutil,argparse,re,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import review
from temporal import ROOT,BATCH,load,save
OUT=review.OUT
NATIVE=review.NATIVE
def native_card(a):
 cache=OUT/'data'/(a['resref']+'-native-preserved.json')
 if cache.exists():return load(cache)
 name=a['resref'];n=next(x for x in load(NATIVE/'catalog.json')['assets'] if x['resref']==name)
 atlas=Image.open(NATIVE/n['image']).convert('RGBA');rows=[]
 target=OUT/'native'/(name+'.png');shutil.copyfile(NATIVE/n['image'],target)
 for i in range(a['source_frames']):
  w,h=n['width'],n['height'];x=i%n['cols']*w;y=i//n['cols']*h
  im=atlas.crop((x,y,x+w,y+h)).resize((w*4,h*4),Image.Resampling.NEAREST)
  rows.append(dict(image=review.png(np.array(im)),x=0,y=0,w=w*4,h=h*4))
 profiles=[]
 for c in a['native_cycles']:
  ids=c['frame_indices']
  if ids:profiles.append(dict(id=f"cycle{c['cycle']:03d}-native-preserved",cycle=c['cycle'],loop=True,native=ids,frames=[i for k in ids for i in (k,k)],duration=len(ids)/15))
 result=dict(ordinal=a['ordinal'],resref=name,profile='N-MASK',method='Masque natif préservé · sans IA',sigma=0,feather=0,green=None,nativeOnly=True,width=n['width']*4,height=n['height']*4,native=dict(image='native/'+name+'.png',width=n['width'],height=n['height'],cols=n['cols']),frames=rows,profiles=profiles)
 save(cache,result);return result
def build():
 for f in ['data','images','native']:(OUT/f).mkdir(parents=True,exist_ok=True)
 batch=load(BATCH/'batch.json');records=[]
 for a in batch['assets']:
  if not (BATCH/'verification'/f"{a['resref']}.json").exists():continue
  c=review.card(a);c['nativeOnly']=False
  c['method']='xBR2blend x4 · palette propre · Apollo30' if a['resref']=='BUBLES' else 'xBR4X · Apollo30' if a['recipe_profile']=='X-TINY' else 'SeedVR7B/LAB x4 · Apollo30'
  records.append(c)
 for a in batch['native_masks']:records.append(native_card(a))
 fallback=BATCH/'body-fallback.json'
 if fallback.exists():
  chosen=load(fallback)['card'];records=[chosen if c['resref']=='WTRBODY2' else c for c in records]
 records.sort(key=lambda c:c['ordinal'])
 template=(Path(__file__).parent/'board.html').read_text(encoding='utf-8')
 template=template.replace('50 effets · SeedVR7B x4 + Apollo30','Magie et eau · comparatif de 50 effets')
 template=template.replace('Recettes adaptées aux flammes, halos, fumées et particules.','37 SeedVR7B/LAB · 6 xBR minuscules · BUBLES xBR2blend avec palette propre · 6 masques natifs conservés. Les masques natifs ne sont pas nouvellement interpolés. Halos : variante alpha lumineux affichable, témoin natif conservé.')
 if fallback.exists():
  template=template.replace('37 SeedVR7B/LAB · 6 xBR minuscules','36 SeedVR7B/LAB · 6 xBR minuscules · WTRBODY2 xBR2/nearest2 (repli fidèle)')
  template=template.replace('</header>','<p>WTRBODY2 : SeedVR surinterprétait les pixels sombres ; repli xBR affiché. <a href="revisions/seedvr-baseline-20261108-v1/index.html#WTRBODY2">Comparer la version SeedVR conservée</a>.</p></header>')
 template=template.replace('SeedVR7B x4 · Apollo30</div>','${a.method}</div>')
 template=template.replace('id="neutral">','id="neutral" checked>')
 template=template.replace('Recette ${a.profile} · gauss RGB','${a.nativeOnly?"Source native inchangée":"Production nouvelle"} · recette ${a.profile} · gauss RGB')
 page=template.replace('__CARDS__',json.dumps(records,ensure_ascii=False))
 (OUT/'index.html').write_text(page,encoding='utf-8');save(OUT/'current-cards.json',dict(count=len(records),assets=records))
 save(OUT/'review.json',dict(count=len(records),new_productions=len(records)-6,native_masks=6,expected=50,qa='pending-user-review',installed=False))
 return len(records)
def contact():
 records=load(OUT/'current-cards.json')['assets'];font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
 for page in range((len(records)+19)//20):
  sheet=Image.new('RGB',(1600,1165),(15,20,28));draw=ImageDraw.Draw(sheet);draw.text((12,8),f'Magie/eau : natif / resultat - page{page+1} - QA utilisateur en attente',font=font,fill='white')
  for j,c in enumerate(records[page*20:(page+1)*20]):
   p=c['profiles'][0];scores=[]
   for phase in range(0,len(p['frames']),2):
    f=c['frames'][p['frames'][phase]];im=Image.open(OUT/f.get('neutral',f['image']));arr=np.asarray(im);scores.append((int((arr[:,:,:3].astype(float)*arr[:,:,3:4]).sum()),phase))
   phase=max(scores)[1];f=c['frames'][p['frames'][phase]];n=c['native'];idx=p['native'][phase//2];atlas=Image.open(OUT/n['image']);x=idx%n['cols']*n['width'];y=idx//n['cols']*n['height'];src=atlas.crop((x,y,x+n['width'],y+n['height'])).resize((c['width'],c['height']),Image.Resampling.NEAREST)
   result=Image.new('RGBA',(c['width'],c['height']));result.paste(Image.open(OUT/f.get('neutral',f['image'])),(f['x'],f['y']))
   tile=Image.new('RGB',(400,225),(38,45,57));d=ImageDraw.Draw(tile);d.text((5,3),f"{c['ordinal']:02} {c['resref']} {c['method'].split(' · ')[0]}",font=font,fill='white')
   for k,im in enumerate([src,result]):
    im.thumbnail((190,180),Image.Resampling.NEAREST);tile.paste(im,(k*200+(200-im.width)//2,35+(180-im.height)//2),im)
   sheet.paste(tile,((j%4)*400,35+(j//4)*225))
  sheet.save(BATCH/f'contact-{page+1}.png')
def main():
 p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args();previous=-1
 while True:
  n=build()
  if n!=previous:print('Board',n,'/50',flush=True);previous=n
  if n==50 or not args.wait:break
  time.sleep(20)
 if n==50:contact()
if __name__=='__main__':main()
