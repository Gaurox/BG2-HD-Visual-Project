"""Source-only proposal; preserve production/QA/install/release authorities."""
import csv, hashlib, json, re, sys
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam,cycle_metadata
from workspace_paths import get_path
OUT=ROOT/'effects/batches/lot50-fire-smoke-proposal-20261028-v1'
GROUPS={
 'flammes-colorees':'FIM1YEL FIM2YEL FIRE_1B FIRE_1C FIRE_1GR FIRE_1GS FIRE_2 FIRE_2A FIRE_4BL FIRE_4G2 FIRE_4GR FISM1YEL FLLGBLU FLLGBLUE FLLGRED FLM1PUR FLM1RED FLM2RED FLMDBLU FLML FLSM1PUR FLSM1RED LAVAFIR1'.split(),
 'explosions-jets-feu':'EXPLODE SPBDBUR SPBDBURS SPBURNS1 SPFBSMAL SPFINODI SPFIRE SPFIRET SPFLADOW SPFLSTRI SPFSTRMI SPPFIRAI SPPFIRXI SPRDRAEX SPMETSWN'.split(),
 'fumees-nuages':'DSTDVL2A FALLMIST STEAM1 STEAM4 SPSMOLD SPSTINK SPAGSCHO SPGREACI ACIDDTH'.split(),
 'bulles-eruptions':'LAVABUB1 LAVABUB2 SPOUTA'.split(),
}
def rows(p):return list(csv.DictReader((ROOT/p).open(encoding='utf-8-sig',newline='')))
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 assert not (OUT/'batch.json').exists(), 'Existing proposal is immutable'
 work={r['resref']:r for r in rows('effects/index/work-items.csv')}
 src={r['resref']:r for r in rows('effects/index/bam-assets.csv')}
 states={r['asset_key'].rsplit(':',1)[-1]:r for r in rows('effects/index/processing.csv')}
 consumers=rows('effects/index/consumers.csv')
 used={w['canonical_sha256'] for n,w in work.items() if states[n]['spatial_state'] not in ('not-started','blocked')}
 anim={r['resref']:r for r in rows('animations/index/animation_upscale_registry.csv')}
 exe=(get_path('bg2ee_game_root',required=True)/'BaldurReal.exe').read_bytes()
 assets=[];audits=[];tiles=[]
 font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
 for group,names in GROUPS.items():
  for n in names:
   w,s=work[n],states[n]
   assert s['spatial_state']=='not-started' and not s['selected_run'],n
   assert w['canonical_sha256'] not in used,n
   assert not anim.get(n,{}).get('selected_run'),n
   data=(ROOT/src[n]['extracted_path']).read_bytes();raw=read_bam(ROOT/src[n]['extracted_path'])
   assert sha(data)==src[n]['source_sha256'].upper() and sha(raw)==w['canonical_sha256'],n
   fs,p,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr);cycles=cycle_metadata(raw,len(fs))
   l=min(-cx for _,cx,_,_ in fs);t=min(-cy for _,_,cy,_ in fs)
   r=max(-cx+idx.shape[1] for idx,cx,_,_ in fs);b=max(-cy+idx.shape[0] for idx,_,cy,_ in fs)
   keys=[];scores=[];black=0;coverage=0
   for idx,cx,cy,_ in fs:
    rgba=np.dstack((p[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
    canvas=np.zeros((b-t,r-l,4),np.uint8);x,y=-cx-l,-cy-t
    canvas[y:y+idx.shape[0],x:x+idx.shape[1]]=rgba;keys.append(sha(canvas.tobytes()))
    mask=alpha[idx]>0;rgb=p[idx][mask];coverage+=len(rgb);black+=int((rgb.max(1)<=8).sum())
    scores.append(int(rgb.astype(np.int64).max(1).sum()))
   ca=[]
   for c in cycles:
    ks=[keys[i] for i in c['frame_indices']]
    ca.append(dict(cycle=c['cycle'],native_slots=len(ks),distinct_anchored_rgba=len(set(ks)),repeated_slots=len(ks)-len(set(ks)),adjacent_duplicate_slots=[i for i in range(1,len(ks)) if ks[i]==ks[i-1]]))
   aliases=[nn for nn,ww in work.items() if nn!=n and ww['canonical_sha256']==w['canonical_sha256']]
   owners=[c for c in consumers if c['asset_key'].rsplit(':',1)[-1] in [n]+aliases]
   match=re.search(rb'(?<![A-Z0-9_])'+n.encode()+rb'\x00',exe.upper())
   assets.append(dict(ordinal=len(assets)+1,resref=n,asset_key=w['asset_key'],group=group,source=src[n]['extracted_path'],source_sha256=sha(data),canonical_sha256=sha(raw),reuse_aliases=aliases,source_frames=len(fs),native_cycles=cycles,native_fps=w['native_fps'],playback_hint=w['playback'],native_canvas=[r-l,b-t],raw_x4_bytes=int(w['raw_x4_bytes']),normal_palette_alpha_levels=sorted(map(int,np.unique(alpha))),opaque_nearblack_pixels=black,covered_pixels=coverage,consumers=owners,engine_literal_offset=hex(match.start()) if match else None,usage_evidence='controller-consumer' if owners else 'executable-literal-only' if match else 'unresolved',production=s))
   audits.append(dict(resref=n,cycles=ca))
   tile=Image.new('RGB',(256,180),(28,30,37));d=ImageDraw.Draw(tile)
   d.text((6,5),f'{len(assets):02d} {n} {len(fs)}f/{len(cycles)}c',font=font,fill='white')
   choices=[]
   for i in sorted(range(len(fs)),key=lambda i:scores[i],reverse=True):
    if all(abs(i-j)>max(1,len(fs)//5) for j in choices):choices.append(i)
    if len(choices)==3:break
   for j,i in enumerate(sorted(choices)):
    idx=fs[i][0];im=Image.fromarray(np.dstack((p[idx],alpha[idx])));im.thumbnail((80,140),Image.Resampling.NEAREST)
    tile.paste(im,(j*85+(85-im.width)//2,30+(140-im.height)//2),im)
   tiles.append(tile)
 assert len(assets)==50 and len({a['canonical_sha256'] for a in assets})==50
 summary=dict(distinct_productions=50,covered_resrefs=len({n for a in assets for n in [a['resref']]+a['reuse_aliases']}),groups={k:len(v) for k,v in GROUPS.items()},source_frames=sum(a['source_frames'] for a in assets),native_cycles=sum(len(a['native_cycles']) for a in assets),native_slots=sum(c['native_slots'] for a in audits for c in a['cycles']),repeated_slots=sum(c['repeated_slots'] for a in audits for c in a['cycles']),assets_with_repeats=sum(any(c['repeated_slots'] for c in a['cycles']) for a in audits),usage_evidence=dict(Counter(a['usage_evidence'] for a in assets)))
 payload=dict(schema='bg2-effects-batch-proposal-v1',date='2026-10-28',status='proposed-source-only',family='Flammes, explosions, fumees et eruptions',summary=summary,subgroups=GROUPS,assets=assets,engine_sha256=sha(exe),limits=['Executable literal is not runtime usage/blend/FPS proof. Unresolved assets remain explicitly unresolved.','Native cycles/directions are alternatives, not a single concatenated timeline.','Preserve indexed source/palettes/native graded alpha; black transparency depends on owner blend.','No production, QA, installation or release authority changed.'])
 for name,value in [('batch.json',payload),('native-duplicate-audit.json',dict(summary=summary,assets=audits))]:
  (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (OUT/'preview').mkdir()
 for page in range(2):
  sheet=Image.new('RGB',(1280,945),(15,17,23));d=ImageDraw.Draw(sheet);d.text((10,8),f'Lot50 feu/fumee - sources natives - {page+1}/2',font=font,fill='white')
  for i,tile in enumerate(tiles[page*25:(page+1)*25]):sheet.paste(tile,((i%5)*256,45+(i//5)*180))
  sheet.save(OUT/f'preview/native-{page+1}.png')
 print(json.dumps(summary,indent=2));print('aliases',{a['resref']:a['reuse_aliases'] for a in assets if a['reuse_aliases']})
if __name__=='__main__':main()
