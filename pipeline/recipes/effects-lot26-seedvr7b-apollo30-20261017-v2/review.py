"""Lossless native/x4 review, one autonomous animation per cycle/profile."""
import argparse
import json

def json_flags(c):
    return json.loads(c.get('flags_json') or '{}')

from fractions import Fraction
import html
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from temporal import ROOT, BATCH, load, save, native_rate
from export_bam_frames import read_bam
from bam_export import decode_bam,native_palette_alpha

OUT = BATCH / 'review'


def millisecond_durations(durations):
    result = []; elapsed = Fraction(0); previous = 0
    for duration in durations:
        elapsed += duration
        cumulative = round(elapsed * 1000)
        result.append(cumulative - previous); previous = cumulative
    return result


def animated(path, frames, durations):
    if not path.exists():
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=millisecond_durations(durations), loop=0, lossless=True, method=2)


def fit(im, size=(240,180)):
    ratio = min(size[0]/im.width, size[1]/im.height, 1)
    im = im.resize((max(1,round(im.width*ratio)),max(1,round(im.height*ratio))),Image.Resampling.NEAREST)
    tile = Image.new('RGB',size,'black')
    tile.paste(im,((size[0]-im.width)//2,(size[1]-im.height)//2))
    return tile


def card(a):
    n=a['resref'];stage=ROOT/'effects/ressources'/n/'runs'/a['interpolation_run']/'02-interpolation'
    m=load(stage/'manifest.json');s=load(ROOT/m['parent']['spatial_manifest']);cw,ch=s['aligned_canvas_size_x1']
    anchor=[s['frames'][0]['canvas_offset_x1'][i]+s['frames'][0]['centre_x1'][i] for i in range(2)]
    native_raw=read_bam(ROOT/a['source'])
    native,palette,transparent=decode_bam(native_raw)
    palette_alpha=native_palette_alpha(native_raw,transparent)
    normal=any(c['owner_route']=='vvc' and not (json_flags(c).get('display',0)&8) for c in a['consumers'])
    background=(110,94,70) if normal else (0,0,0)
    variants=[];scores={};posters={}
    for v in m['timing']['cycles']:
        name=n+'-'+v['id'];full=OUT/'full'/(name+'.webp');thumb=OUT/'cycles'/(name+'.webp')
        images=[]
        for index in v['timeline_frame_indices']:
            f=m['frames'][index];w,h=f['physical_size_x4']
            rgba=np.frombuffer((stage/f['straight_raw_rgba_x4'] if normal else stage/f['raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4)
            im=Image.new('RGB',(cw*4,ch*4),background)
            tile=Image.fromarray(rgba)
            if normal:
                tile=Image.alpha_composite(Image.new('RGBA',tile.size,background+(255,)),tile).convert('RGB')
            else: tile=Image.fromarray(rgba[:,:,:3])
            im.paste(tile,tuple((anchor[i]-f['centre_x1'][i])*4 for i in range(2)))
            images.append(im)
        duration=[Fraction(*d) for d in v['phase_durations_rational']]
        animated(full,images,duration)
        thumbs=[fit(im) for im in images];animated(thumb,thumbs,duration)
        best=max(range(len(images)),key=lambda k:np.abs(np.asarray(images[k],dtype=np.int32)-np.asarray(background)).sum())
        scores[v['id']]=int(np.abs(np.asarray(images[best],dtype=np.int32)-np.asarray(background)).sum());posters[v['id']]=thumbs[best]
        native_path=OUT/'native'/f'{n}-cycle{v["cycle"]:03d}.webp'
        if not native_path.exists():
            old=[]
            for k in v['native_slots']:
                idx,cx,cy,_=native[k];rgb=palette[idx].copy();rgb[idx==transparent]=0
                if normal:
                    rgb=np.rint(rgb.astype(np.float32)*palette_alpha[idx][:,:,None]/255+np.asarray(background)*(1-palette_alpha[idx][:,:,None]/255)).astype(np.uint8)
                im=Image.new('RGB',(cw*4,ch*4),background)
                im.paste(Image.fromarray(rgb).resize((idx.shape[1]*4,idx.shape[0]*4),Image.Resampling.NEAREST),((anchor[0]-cx)*4,(anchor[1]-cy)*4))
                old.append(fit(im))
            animated(native_path,old,[Fraction(1,native_rate(a))]*len(old))
        variants.append({'id':v['id'],'cycle':v['cycle'],'loop':v['loop_closed'],'phases':v['phase_count'],
                         'duration_seconds':v['duration_seconds'],'native_slots':len(v['native_slots']),
                         'keys':len(v['keyframes']),'removed_slots':v['removed_native_slots'],
                         'constant_native_cycle':v['constant_native_cycle'],
                         'animation':'cycles/'+thumb.name,'full':'full/'+full.name,'native':'native/'+native_path.name})
    preferred=max(variants,key=lambda v:(not v['constant_native_cycle'],scores[v['id']],v['loop']))
    posters[preferred['id']].save(OUT/'posters'/f'{n}.png')
    result={'resref':n,'default':preferred['id'],'variants':variants,'native_fps':native_rate(a),
            'review_render_mode':'normal-native-palette-on-brown' if normal else 'blended-premultiplied-on-black',
            'native_rate_basis':'VVC source' if a['native_fps'] else '15 FPS compatibility default; runtime measurement pending'}
    save(OUT/'cards'/f'{n}.json',result)
    return result


def gallery(records):
    cards=[]
    for i,r in enumerate(records,1):
        options=''.join(f'<option value="{html.escape(v["animation"])}" data-full="{v["full"]}" data-native="{v["native"]}" data-duration="{v["duration_seconds"]:.6f}" data-phases="{v["phases"]}" data-removed="{v["removed_slots"]}" {"selected" if v["id"]==r["default"] else ""}>{v["id"]}</option>' for v in r['variants'])
        n=r['resref']
        cards.append(f'<article><h2>{i:02d} Â· {n}</h2><div class="compare"><div><span>Natif Ã—4 NEAREST</span><img class="native" width="240" height="180"></div><div><span>SeedVR 7B Ã—4 + Apollo30</span><img class="result" data-poster="posters/{n}.png" width="240" height="180"></div></div><select onchange="selectCycle(this)">{options}</select><p class="timing"></p><p><a class="full" target="_blank">Animation x4 entiÃ¨re</a></p></article>')
    source='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Lot26 â€” SeedVR7B Ã—4 / Apollo30</title><style>body{margin:24px;background:#0d1118;color:#e6edf7;font:15px system-ui}header{max-width:1100px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(510px,1fr));gap:16px}article{background:#151d29;padding:14px;border-radius:12px}h1{font-size:27px}h2{font-size:18px}.compare{display:flex;gap:12px}.compare span{display:block;font-size:12px;color:#aebcd0}img{display:block;background:#000;image-rendering:pixelated}select,button{background:#202f44;color:white;border:1px solid #526880;padding:7px;border-radius:5px}select{margin-top:12px;width:100%}a{color:#7bbaff}.timing{font-variant-numeric:tabular-nums}</style><header><h1>Lot26 â€” 7B Ã—4 / NEAREST / Apollo 30 FPS</h1><p>Comparaison native / production. Chaque cycle et direction reste autonome. Poses natives rÃ©pÃ©tÃ©es retirÃ©es avant Apollo, durÃ©e d'origine conservÃ©e. Les cycles natifs constants restent constants. QA visuelle en attente.</p><p>VVC : cadence source. Projectiles : base de compatibilitÃ© 15 FPS ; cadence ingame Ã  confirmer. SPFLAST1 : durÃ©e 9/8 s, 34 images, dernier intervalle 25 ms. RGB prÃ©multipliÃ© affichÃ© directement sur noir ; tailles ajustÃ©es par vignette.</p><button id="toggle" onclick="togglePlay()">Pause</button><p class="count">COUNT effets prÃªts.</p></header><main>CARDS</main><script>let playing=true;function selectCycle(s){let a=s.closest('article'),o=s.selectedOptions[0];a.querySelector('.result').src=playing?o.value:a.querySelector('.result').dataset.poster;a.querySelector('.native').src=o.dataset.native;a.querySelector('.full').href=o.dataset.full;a.querySelector('.timing').textContent=o.dataset.phases+' phases Â· '+Number(o.dataset.duration).toFixed(3)+' s Â· '+o.dataset.removed+' slots natifs retirÃ©s'}function togglePlay(){playing=!playing;document.querySelectorAll('select').forEach(selectCycle);document.getElementById('toggle').textContent=playing?'Pause':'Lecture'}document.querySelectorAll('select').forEach(selectCycle);</script></html>'''
    (OUT/'index.html').write_text(source.replace('CARDS',''.join(cards)).replace('COUNT',str(len(records))),encoding='utf-8')


def posters(records):
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    for page,start in enumerate(range(0,len(records),30),1):
        chunk=records[start:start+30];sheet=Image.new('RGB',(1200,((len(chunk)+5)//6)*220+45),(18,22,30));d=ImageDraw.Draw(sheet)
        d.text((12,10),f'LOT26 - SEEDVR7B x4 / APOLLO30 - {start+1}..{start+len(chunk)}',font=font,fill='white')
        for j,r in enumerate(chunk):
            im=Image.open(OUT/'posters'/f'{r["resref"]}.png').convert('RGB').resize((200,150),Image.Resampling.NEAREST)
            x=(j%6)*200;y=45+(j//6)*220;sheet.paste(im,(x,y));d.text((x+5,y+159),f'{start+j+1:02d} {r["resref"]}',font=font,fill='white')
        sheet.save(OUT/f'lot26-x4-{page}.png')


def main():
    p=argparse.ArgumentParser();p.add_argument('--ready-only',action='store_true');p.add_argument('--wait',action='store_true');args=p.parse_args()
    for folder in ('full','cycles','native','posters','cards'):(OUT/folder).mkdir(parents=True,exist_ok=True)
    records=[]
    for a in load(BATCH/'batch.json')['assets']:
        proof=BATCH/'verification'/f'{a["resref"]}.json'
        if args.wait:
            while not proof.exists():
                progress=load(BATCH/'temporal-progress.json') if (BATCH/'temporal-progress.json').exists() else {}
                if progress.get(a['resref'],{}).get('state')=='failed':break
                time.sleep(3)
        if not proof.exists():
            if args.ready_only:continue
            raise RuntimeError('Verification missing '+a['resref'])
        path=OUT/'cards'/f'{a["resref"]}.json'
        records.append(load(path) if path.exists() else card(a))
        gallery(records)
        print(a['resref'],'review ready',flush=True)
    posters(records)
    save(OUT/'review.json',{'count':len(records),'assets':records,'encoding':'lossless animated WebP; normal native-palette over brown or Blended premultiplied over black according to consumers','timestamp_policy':'cumulative rounded millisecond timestamps; exact rational production durations in interpolation manifests'})


if __name__=='__main__':main()
