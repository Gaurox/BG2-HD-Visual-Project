"""Publish three verified productions for review; grant no visual QA or installation."""
import json,re,sys,subprocess,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from temporal import ROOT,BATCH,load,save,rel,workflow
from compose_effect_runtime_packs import validate_pack
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam
import review
import effect_authority as authority
import effect_tracking as tracking

def contact(batch):
 im=Image.new('RGB',(920,920),(17,23,34));d=ImageDraw.Draw(im)
 font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18);title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',25)
 method=batch.get('display_method','SeedVR7B')
 d.text((24,18),f'Projectiles : natif / {method} x4 + Apollo30',font=title,fill='white')
 d.text((24,59),'Echantillons de production — validation visuelle en attente',font=font,fill='#bac7da')
 for i,a in enumerate(batch['assets']):
  n=a['resref'];y=104+i*265;d.text((24,y),n,font=title,fill='white')
  raw=read_bam(ROOT/a['source']);fs,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr)
  k=max(range(len(fs)),key=lambda j:int(pal[fs[j][0]].astype(np.uint64).sum()))
  native=np.dstack((pal[fs[k][0]],alpha[fs[k][0]]));native[native[:,:,3]==0]=0
  run=ROOT/'effects/ressources'/n/'runs'/a['interpolation_run']/'02-interpolation';m=load(run/'manifest.json')
  v=next(v for v in m['timing']['cycles'] if k in v['native_slots']);f=m['frames'][v['native_frame_indices'][v['native_slots'].index(k)]]
  w,h=f['physical_size_x4'];processed=Image.fromarray(np.frombuffer((run/f['straight_raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4))
  native=Image.fromarray(native).resize((fs[k][0].shape[1]*4,fs[k][0].shape[0]*4),Image.Resampling.NEAREST)
  for x,picture,label in [(30,native,'Natif x4'),(474,processed,f'{method} x4 / alpha natif')]:
   panel=Image.new('RGBA',(412,210),(50,61,76,255));panel.alpha_composite(picture,((412-picture.width)//2,(210-picture.height)//2));im.paste(panel.convert('RGB'),(x,y+38));d.text((x+10,y+216),label,font=font,fill='#c6d3e7')
 im.save(BATCH/'comparison.png')

def main():
 batch=load(BATCH/'batch.json');results=[]
 for a in batch['assets']:
  n=a['resref'];v=load(BATCH/'verification'/f'{n}.json');r=load(BATCH/'runtime-verification'/f'{n}.json');cp=load(BATCH/'runtime-verification'/f'{n}-companions.json')
  assert v['passed'] and r['passed'] and cp['passed'];p=validate_pack(ROOT/r['pack']);assert p.manifest_sha256==r['pack_manifest_sha256']
  assert workflow.sha256_file(ROOT/a['source'])==a['source_sha256']
  results.append(dict(resref=n,source=a['source'],source_sha256=a['source_sha256'],spatial_run=a['spatial_run'],interpolation_run=a['interpolation_run'],pack=r['pack'],pack_manifest_sha256=r['pack_manifest_sha256'],native_cycles=len(a['native_cycles']),profiles=r['profiles'],phases=r['phases'],backings=r['backings'],native_contracts=r['native_contracts'],raw_bytes=r['raw_bytes'],companions=cp['companions'],visual_qa='pending-user-review',installed=False,release='not-evaluated',owners=a['owners'],animation_id=a['animation_id']))
 assert review.build()==3
 h=(BATCH/'review/index.html').read_text(encoding='utf-8');js=ROOT/'.tmp/projectiles3-20261109-v1/board.js';js.write_text(re.search(r'<script>(.*?)</script>',h,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 for a in results:
  c=load(BATCH/'review/data'/f"{a['resref']}.json")
  for p in c['profiles']:
   assert len(p['frames'])==len(p['native'])*2 and p['duration']==len(p['native'])/15
  assert all((BATCH/'review'/f['image']).is_file() and (BATCH/'review'/f['neutral']).is_file() for f in c['frames'])
 summary=dict(assets=3,native_frames=90,native_cycles=7,profiles=sum(r['profiles'] for r in results),phases=sum(r['phases'] for r in results),backings=sum(r['backings'] for r in results),native_contracts=sum(r['native_contracts'] for r in results),native_contracts_all_three_encodings=sum(r['native_contracts'] for r in results)*3,target_fps=[30,1],native_fps_basis='15FPS compatibility, not measured ingame')
 save(BATCH/'production.json',dict(schema='bg2-effects-production-batch-result-v1',status='completed-production-pending-visual-QA',summary=summary,assets=results,board='http://127.0.0.1:8800/',scope='Three authorized projectile animation BAMs only; no visual acceptance, game installation or release. Secondary whitelist source prepared; DLL not built or installed.'))
 contact(batch)
 save(BATCH/'integration-plan.json',dict(state='prepared-not-installed',source='engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/effect_secondary_scope.h',assets=[dict(resref=a['resref'],animation_id=a['animation_id'],role=a['role'],owners=a['owners'],pack=a['final_pack']) for a in batch['assets']],requirements=['Choose blend/alpha companion from native owner contract','Build/install targeted runtime only for authorized ingame review','Keep original ANIMATE IDs and native PROs; SPGLYPHI shared by two owners'],qa='pending'))
 q=tracking.queue(ROOT,limit=3);completion=load(BATCH/'prior-effects-completion.json');completion.update(q['completion'],status='awaiting-visual-qa',recorded_on='2026-11-09',processing_sha256=workflow.sha256_file(ROOT/'effects/index/processing.csv'),extension='effects/batches/projectiles3-production-20261109-v1/production.json',previous_completion=rel(BATCH/'prior-effects-completion.json'),scope='Initial494 closed entries retained; 3 newly authorized projectile BAMs produced, visual QA pending. No installation/release inferred.')
 manifest=load(ROOT/'effects/index/manifest.json');inventory=workflow.read_csv(ROOT/'effects/index/bam-assets.csv');manifest.update(bam_asset_count=len(inventory),bam_source_available_count=sum(r['source_state']=='available' for r in inventory),projectile_animation_extension='effects/index/projectile-animation-sources.json')
 with authority.guard(ROOT,True):authority.commit(ROOT,{'effects/index/completion.json':workflow.json_bytes(completion),'effects/index/manifest.json':workflow.json_bytes(manifest)})
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
