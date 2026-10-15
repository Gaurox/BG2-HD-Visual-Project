"""Lossless animated cycle browser and 4 synchronized 30 FPS review videos."""
import argparse
import html
import math
import shutil
import subprocess
import time

import numpy as np
from PIL import Image,ImageDraw,ImageFont
from temporal import ROOT,BATCH,load,save

OUT=BATCH/'review'


def world_frames(asset,manifest,variant,size=(240,180)):
    spatial=load(ROOT/manifest['parent']['spatial_manifest'])
    cw,ch=spatial['aligned_canvas_size_x1']
    f0=spatial['frames'][0]
    anchor=[f0['canvas_offset_x1'][i]+f0['centre_x1'][i] for i in range(2)]
    ratio=min(size[0]/(cw*4),size[1]/(ch*4),1)
    target=(max(1,round(cw*4*ratio)),max(1,round(ch*4*ratio)))
    stage=ROOT/'effects/ressources'/asset['resref']/'runs'/asset['interpolation_run']/'02-interpolation'
    result=[]
    for idx in variant['timeline_frame_indices']:
        f=manifest['frames'][idx]
        raw=(stage/f['raw_rgba_x4']).read_bytes();w,h=f['physical_size_x4']
        p=np.frombuffer(raw,np.uint8).reshape(h,w,4)
        image=Image.new('RGB',(cw*4,ch*4),'black')
        image.paste(Image.fromarray(p[:,:,:3]),tuple((anchor[i]-f['centre_x1'][i])*4 for i in range(2)))
        thumb=image.resize(target,Image.Resampling.NEAREST)
        tile=Image.new('RGB',size,'black');tile.paste(thumb,((size[0]-thumb.width)//2,(size[1]-thumb.height)//2))
        result.append(tile)
    return result


def card(asset):
    name=asset['resref'];stage=ROOT/'effects/ressources'/name/'runs'/asset['interpolation_run']/'02-interpolation'
    m=load(stage/'manifest.json');variants=m['timing']['cycles']
    options=[];scores={}
    for v in variants:
        destination=OUT/'cycles'/f'{name}-{v["id"]}.webp'
        frames=world_frames(asset,m,v)
        scores[v['id']]=max(int(np.asarray(im,dtype=np.uint64).sum()) for im in frames)
        if not destination.exists():
            duration=[round((i+1)*1000/30)-round(i*1000/30) for i in range(len(frames))]
            frames[0].save(destination,save_all=True,append_images=frames[1:],duration=duration,loop=0,lossless=True,method=2)
        options.append({'profile':v['id'],'cycle':v['cycle'],'loop':v['loop_closed'],
                        'phases':len(frames),'duration_seconds':len(frames)/30,
                        'constant_native_cycle':v['constant_native_cycle'],
                        'path':destination.relative_to(OUT).as_posix()})
    # Loop body when present; otherwise the strongest visible native cycle.
    loops=[v for v in variants if v['loop_closed'] and not v['transparent_native_cycle']]
    selected=max(loops or variants,key=lambda v:scores[v['id']])
    frames=world_frames(asset,m,selected)
    poster=max(frames,key=lambda im:np.asarray(im,dtype=np.uint64).sum())
    poster.save(OUT/'posters'/f'{name}.png')
    record={'resref':name,'playback':asset['playback'],'default_profile':selected['id'],'variants':options,
            'review_display':'premultiplied RGB over black; NEAREST thumbnail; native world anchor retained; sizes normalized for review only'}
    save(OUT/'cards'/f'{name}.json',record)
    print(name,'animated review ready',len(options),'profiles',flush=True)
    return record


def gallery(records):
    cards=[]
    for i,r in enumerate(records,1):
        options=''.join(f'<option value="{v["path"]}" data-phases="{v["phases"]}" data-duration="{v["duration_seconds"]:.6f}" {"selected" if v["profile"]==r["default_profile"] else ""}>cycle {v["cycle"]} — {"boucle" if v["loop"] else "ponctuel"} — {v["phases"]} phases</option>' for v in r['variants'])
        default=next(v for v in r['variants'] if v['profile']==r['default_profile'])
        cards.append(f'<article><h2>{i:02d} · {r["resref"]}</h2><div class="picture"><img src="{default["path"]}" data-poster="posters/{r["resref"]}.png"></div><select onchange="selectCycle(this)">{options}</select><p class="timing">{default["phases"]} phases · {default["duration_seconds"]:.3f} s</p></article>')
    source='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>64 effets — SeedVR 7B x4 / 30 FPS</title>
<style>body{margin:24px;background:#0c0e13;color:#eef2f9;font:16px system-ui}h1{font-size:27px}header{max-width:1100px}button,select{padding:8px;background:#202734;color:#eef2f9;border:1px solid #46526a;border-radius:5px}button{cursor:pointer;margin:0 6px 10px 0}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:14px}article{background:#151a24;padding:12px;border:1px solid #333d50;border-radius:8px}h2{font:20px monospace;margin:0 0 10px}.picture{height:195px;background:#000;display:flex;align-items:center;justify-content:center}img{width:240px;height:180px;max-width:100%;object-fit:contain;image-rendering:pixelated}select{width:100%;margin-top:10px}.timing{font-size:14px;color:#b9c6d9;margin-bottom:0}a{color:#9ac6ff}</style>
<header><h1>64 effets — SeedVR 7B x4 · NEAREST · Apollo 30 FPS</h1><p>RVB de production prémultiplié sur fond noir, aperçu animé sans compression destructive. Chaque cycle/direction est sélectionnable séparément ; aucune concaténation artificielle. Le sélecteur conserve la durée native du cycle. Les effets ponctuels sont rejoués pour le contrôle.</p><p>Vignettes ajustées à leur case : leur taille ici ne représente pas leur taille ingame. Sources et géométrie monde natives conservées. Le cycle technique transparent de SPCOMEXP n'invente aucune animation. Personnages et installation inchangés.</p><button onclick="togglePlay()" id="toggle">Pause</button><button onclick="restart()">Recommencer</button><p>Vidéos de contrôle à 30 FPS : <a href="lot64-animated-1.mp4">01–16</a> · <a href="lot64-animated-2.mp4">17–32</a> · <a href="lot64-animated-3.mp4">33–48</a> · <a href="lot64-animated-4.mp4">49–64</a></p></header><main>CARDS</main>
<script>let playing=true;function selectCycle(s){let a=s.closest('article'),i=a.querySelector('img'),o=s.selectedOptions[0];i.dataset.animation=o.value;i.src=playing?o.value:i.dataset.poster;a.querySelector('.timing').textContent=o.dataset.phases+' phases · '+Number(o.dataset.duration).toFixed(3)+' s'}function togglePlay(){playing=!playing;document.querySelectorAll('select').forEach(selectCycle);document.getElementById('toggle').textContent=playing?'Pause':'Lecture'}function restart(){document.querySelectorAll('select').forEach(selectCycle)}document.querySelectorAll('select').forEach(selectCycle);</script></html>'''
    (OUT/'index.html').write_text(source.replace('CARDS',''.join(cards)),encoding='utf-8')


def movies(assets,records):
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',21)
    small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15)
    for page,start in enumerate(range(0,len(assets),16),1):
        dest=OUT/f'lot64-animated-{page}.mp4'
        if dest.exists():continue
        cached=[];base=Image.new('RGB',(1080,1016),(12,15,22));d=ImageDraw.Draw(base)
        d.text((18,9),f'64 effets — 7B x4 / NEAREST / 30 FPS — {page}/4',font=font,fill='white')
        d.text((18,38),'Apercu ajuste par case ; cycles autonomes, durees natives conservees.',font=small,fill='#b8c7dd')
        for n,(a,r) in enumerate(zip(assets[start:start+16],records[start:start+16])):
            stage=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation';m=load(stage/'manifest.json')
            v=next(v for v in m['timing']['cycles'] if v['id']==r['default_profile'])
            cached.append((world_frames(a,m,v),v['loop_closed']))
            x,y=(n%4)*270,65+(n//4)*237
            d.text((x+12,y+187),f'{start+n+1:02d} {a["resref"]}',font=font,fill='white')
            d.text((x+12,y+213),f'{len(v["native_slots"])/15:.3f} s | '+('boucle' if v['loop_closed'] else 'ponctuel'),font=small,fill='#aebfd5')
        count=360 # 12 seconds, exact CFR30; multiple native cycles observable.
        command=[shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1016','-r','30','-i','-',
                 '-an','-c:v','libx264','-crf','15','-preset','fast','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)]
        with (OUT/f'video-{page}.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log)
            for phase in range(count):
                image=base.copy()
                for n,(frames,closed) in enumerate(cached):
                    position=phase%(len(frames)+(0 if closed else 15))
                    if position<len(frames):image.paste(frames[position],((n%4)*270+15,65+(n//4)*237))
                process.stdin.write(image.tobytes())
            process.stdin.close();assert process.wait()==0
        info=load_video(dest);assert info['avg_frame_rate']=='30/1' and int(info['nb_frames'])==count
        save(OUT/f'video-{page}.json',{'path':dest.name,'frames':count,'fps':[30,1],
             'encoding':'H264 CRF15 YUV420 review derivative; exact production RGBA and lossless animated WebP retained separately',
             'one_shot_review_gap_frames':15,'loop_review_gap_frames':0})
        print('Animated review movie',page,'verified',flush=True)


def load_video(path):
    import json
    j=json.loads(subprocess.check_output([shutil.which('ffprobe'),'-v','error','-show_streams','-of','json',str(path)]))
    return next(s for s in j['streams'] if s['codec_type']=='video')


def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');p.add_argument('--ready-only',action='store_true');args=p.parse_args()
    for folder in ('cycles','posters','cards'):(OUT/folder).mkdir(parents=True,exist_ok=True)
    assets=load(BATCH/'batch.json')['assets'];ready=[];records=[]
    for a in assets:
        proof=BATCH/'verification'/f'{a["resref"]}.json'
        if args.wait:
            while not proof.exists():time.sleep(3)
        if not proof.exists():
            if args.ready_only:continue
            raise RuntimeError('Missing verification: '+a['resref'])
        path=OUT/'cards'/f'{a["resref"]}.json'
        records.append(load(path) if path.exists() else card(a));ready.append(a)
    gallery(records)
    if len(records)==64:movies(ready,records)
    save(OUT/'review.json',{'assets':records,'count':len(records),'lossless_animated_webp':True,'production_fps':[30,1],
                          'webp_timestamp_policy':'rounded millisecond cumulative timestamps, 33/34ms; videos exact CFR30',
                          'size_policy':'NEAREST thumbnails only; world size unchanged in production'})


if __name__=='__main__':main()
