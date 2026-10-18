"""Transparent native/x4 previews, independent native cycle/mode selection."""
import argparse
from fractions import Fraction
import html
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from temporal import ROOT, BATCH, load, save, native_rate
from export_bam_frames import read_bam
from bam_export import decode_bam, native_palette_alpha

OUT=BATCH/'review'


def durations_ms(values):
    elapsed=Fraction(0);previous=0;result=[]
    for v in values:
        elapsed+=v;current=round(elapsed*1000);result.append(current-previous);previous=current
    return result


def animated(path,images,durations):
    if not path.exists():
        images[0].save(path,save_all=True,append_images=images[1:],duration=durations_ms(durations),loop=0,lossless=True,method=2)


def fit(im):
    im=im.copy();im.thumbnail((300,220),Image.Resampling.NEAREST)
    canvas=Image.new('RGBA',(300,220));canvas.paste(im,((300-im.width)//2,(220-im.height)//2))
    return canvas


def card(a):
    name=a['resref'];path=OUT/'cards'/f'{name}.json'
    if path.exists():return load(path)
    stage=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']/'02-interpolation'
    m=load(stage/'manifest.json');s=load(ROOT/m['parent']['spatial_manifest']);cw,ch=s['aligned_canvas_size_x1']
    anchor=[s['frames'][0]['canvas_offset_x1'][i]+s['frames'][0]['centre_x1'][i] for i in range(2)]
    raw=read_bam(ROOT/a['source']);native,palette,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr)
    variants=[];scores={};posters={}
    for v in m['timing']['cycles']:
        stem=name+'-'+v['id'];full=OUT/'full'/(stem+'.webp');thumb=OUT/'cycles'/(stem+'.webp')
        images=[]
        for i in v['timeline_frame_indices']:
            f=m['frames'][i];w,h=f['physical_size_x4']
            arr=np.frombuffer((stage/f['straight_raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4)
            im=Image.new('RGBA',(cw*4,ch*4));tile=Image.fromarray(arr)
            im.paste(tile,tuple((anchor[j]-f['centre_x1'][j])*4 for j in range(2)))
            images.append(im)
        durations=[Fraction(*d) for d in v['phase_durations_rational']]
        animated(full,images,durations);thumbs=[fit(im) for im in images];animated(thumb,thumbs,durations)
        values=[int(np.asarray(im)[:,:,:3].astype(np.int64).sum()) for im in images]
        best=max(range(len(values)),key=values.__getitem__);scores[v['id']]=values[best];posters[v['id']]=thumbs[best]
        source=OUT/'native'/f'{name}-cycle{v["cycle"]:03d}.webp'
        if not source.exists():
            originals=[]
            for k in v['native_slots']:
                idx,cx,cy,_=native[k];rgba=np.dstack((palette[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
                im=Image.new('RGBA',(cw*4,ch*4));tile=Image.fromarray(rgba).resize((idx.shape[1]*4,idx.shape[0]*4),Image.Resampling.NEAREST)
                im.paste(tile,((anchor[0]-cx)*4,(anchor[1]-cy)*4));originals.append(fit(im))
            animated(source,originals,[Fraction(1,native_rate(a))]*len(originals))
        variants.append({'id':v['id'],'cycle':v['cycle'],'loop':v['loop_closed'],'phases':v['phase_count'],
            'duration_seconds':v['duration_seconds'],'native_slots':len(v['native_slots']),'removed_slots':v['removed_native_slots'],
            'animation':'cycles/'+thumb.name,'full':'full/'+full.name,'native':'native/'+source.name})
    preferred=max(variants,key=lambda v:(not v['loop'],scores[v['id']]))
    posters[preferred['id']].save(OUT/'posters'/f'{name}.png')
    record={'resref':name,'default':preferred['id'],'variants':variants,'native_fps':native_rate(a),
        'alpha_preview':'straight native-palette RGBA; background selectable',
        'runtime_color':'source palette only; engine tint not simulated',
        'native_rate_basis':'15 FPS compatibility basis, not measured ingame', 'inner_feather_x4':a['inner_feather_x4']}
    save(path,record);return record


def gallery(records):
    cards=[]
    for i,r in enumerate(records,1):
        options=''.join(f'<option value="{html.escape(v["animation"])}" data-full="{v["full"]}" data-native="{v["native"]}" data-time="{v["duration_seconds"]:.6f}" data-phases="{v["phases"]}" data-removed="{v["removed_slots"]}" {"selected" if v["id"]==r["default"] else ""}>{v["id"]}</option>' for v in r['variants'])
        cards.append(f'<article><h2>{i:02d} · {r["resref"]}</h2><div class="compare"><figure><figcaption>Natif ×4 NEAREST</figcaption><img class="native"></figure><figure><figcaption>SeedVR 7B ×4 + Apollo30</figcaption><img class="result" data-poster="posters/{r["resref"]}.png"></figure></div><select onchange="show(this)">{options}</select><p class="timing"></p><a class="full" target="_blank">Animation x4 entière</a></article>')
    source='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Lot33 · impacts natifs · SeedVR7B ×4 / Apollo30</title>
<style>body{margin:24px;background:#0d1118;color:#e6edf7;font:15px system-ui}header{max-width:1150px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(640px,1fr));gap:16px}article{background:#151d29;padding:14px;border-radius:12px}h1{font-size:27px}h2{font-size:18px}.compare{display:flex;gap:12px}figure{margin:0}figcaption{font-size:12px;color:#aebcd0}img{display:block;width:300px;height:220px;image-rendering:pixelated;background:repeating-conic-gradient(#444 0% 25%,#666 0% 50%) 50%/16px 16px}body.black img{background:#000}body.brown img{background:#6e5e46}body.white img{background:#ddd}select,button{background:#202f44;color:white;border:1px solid #526880;padding:7px;border-radius:5px}select{margin-top:12px;width:100%}a{color:#7bbaff}.timing{font-variant-numeric:tabular-nums}</style>
<header><h1>33 effets natifs · SeedVR 7B ×4 / Apollo 30 fps</h1><p>Cycles et directions séparés, poses répétées condensées, durée d’origine conservée. Variantes ponctuelles et bouclées disponibles.</p><p>Alpha droit sur fond réglable ; palette source sans recoloration du moteur. Base de compatibilité 15 fps, cadence native en jeu à confirmer. Les sorties prémultipliées restent conservées séparément.</p><button onclick="toggle(this)">Pause</button> <button onclick="document.body.className=''">Damier</button> <button onclick="document.body.className='black'">Noir</button> <button onclick="document.body.className='brown'">Terrain</button> <button onclick="document.body.className='white'">Clair</button><p>COUNT/33 effets disponibles · QA visuelle en attente.</p></header><main>CARDS</main><script>let playing=true;function show(s){let a=s.closest('article'),o=s.selectedOptions[0];a.querySelector('.result').src=playing?o.value:a.querySelector('.result').dataset.poster;a.querySelector('.native').src=o.dataset.native;a.querySelector('.full').href=o.dataset.full;a.querySelector('.timing').textContent=o.dataset.phases+' phases · '+Number(o.dataset.time).toFixed(3)+' s · '+o.dataset.removed+' slots natifs condensés'}function toggle(b){playing=!playing;document.querySelectorAll('select').forEach(show);b.textContent=playing?'Pause':'Lecture'}document.querySelectorAll('select').forEach(show);</script></html>'''
    (OUT/'index.html').write_text(source.replace('CARDS',''.join(cards)).replace('COUNT',str(len(records))),encoding='utf-8',newline='\n')
    save(OUT/'review.json',{'count':len(records),'assets':records,'encoding':'lossless animated WebP RGBA; selectable background; source palette without native tint'})


def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args()
    for name in ('full','cycles','native','posters','cards'):(OUT/name).mkdir(parents=True,exist_ok=True)
    records=[]
    for a in load(BATCH/'batch.json')['assets']:
        proof=BATCH/'verification'/f'{a["resref"]}.json'
        if args.wait:
            while not proof.exists():
                state=load(BATCH/'temporal-progress.json') if (BATCH/'temporal-progress.json').exists() else {}
                if state.get(a['resref'],{}).get('state')=='failed':break
                time.sleep(3)
        assert proof.exists(),'Verification missing '+a['resref']
        records.append(card(a));gallery(records);print(a['resref'],'review ready',flush=True)


if __name__=='__main__':main()
