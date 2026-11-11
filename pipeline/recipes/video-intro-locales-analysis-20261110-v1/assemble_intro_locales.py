"""Assemble INTRO locale openings/shared master on each native timeline, preserving native Vorbis."""
import csv
import argparse
import json
import subprocess
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
AUDIT=ROOT/'video/research/intro-locales-analysis-20261110-v1'
RUN=ROOT/'video/assembly/intro-locales-seedvr-1080-20261111-v1'
COMMON=ROOT/'video/experiments/intro-common-seedvr3b-stream-1080-20261111-v1/INTRO-common-SeedVR2-3B-FP16-LAB-1080p.mp4'
OPENINGS=ROOT/'video/experiments/intro-openings-seedvr3b-1080-20261111-v1'
SIZE=1920*1080*3


def call(args):
    p=subprocess.run([str(a) for a in args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p.stdout


def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class Decoder:
    def __init__(self,path):
        self.p=subprocess.Popen(['ffmpeg','-v','error','-threads','2','-i',str(path),'-map','0:v:0','-an',
            '-pix_fmt','rgb24','-threads','1','-fps_mode','passthrough','-f','rawvideo','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        self.index=-1;self.frame=None
    def get(self,n):
        assert n>=self.index,(n,self.index)
        while self.index<n:
            chunks=[];size=0
            while size<SIZE:
                b=self.p.stdout.read(SIZE-size)
                if not b:raise RuntimeError(f'Decoder EOF at {self.index+1}')
                chunks.append(b);size+=len(b)
            self.frame=b''.join(chunks);self.index+=1
        return self.frame
    def close(self):
        self.p.stdout.close()
        if self.p.poll() is None:self.p.terminate()
        self.p.wait()


def pcm_hash(path):
    return call(['ffmpeg','-v','error','-i',path,'-map','0:a:0','-vn','-c:a','pcm_s16le','-f','hash','-hash','sha256','-']).decode().strip()


def assemble(locale,resume=False):
    name='INTRO-'+locale;folder=RUN/locale;folder.mkdir(parents=True,exist_ok=True)
    metadata=json.loads((AUDIT/f'{name}.metadata.json').read_text())
    source=ROOT/metadata['source'];times=json.loads((AUDIT/f'{name}.native-frame-times.json').read_text())['frames']
    count=len(times);opening_count=121 if locale=='pl_PL' else 240
    opening=OPENINGS/locale/f'{name}-SeedVR2-3B-FP16-LAB-1080p.mp4'
    mapped=list(range(count)) if locale=='default' else [int(r['default_frame']) for r in csv.DictReader((AUDIT/f'{name}-to-default.csv').open())]
    assert len(mapped)==count and all(a<=b for a,b in zip(mapped,mapped[1:]))
    overlap_first=next(i for i in range(opening_count) if mapped[i]>=210)
    overlap_last=opening_count-1
    language={'default':'eng','de_DE':'deu','pl_PL':'pol'}[locale]
    origin=float(times[0]['best_effort_timestamp_time'])
    fps='15000/1001' if locale=='pl_PL' else '30000/1001'
    expression='max(N-1\\,0)*1001/15000' if locale=='pl_PL' else f'N*1001/30000+{origin}'
    master=folder/f'{name}-SeedVR2-1080-native-audio.mkv'
    if resume and master.exists():
        backup=master.with_stem(master.stem+'-timing-attempt1')
        assert not backup.exists(),backup
        master.rename(backup)
    assert not master.exists(),master
    filter_args=['-vf',f'settb=1/1000000,setpts=({expression})/TB']
    if locale=='pl_PL':
        stamps=[int(round(float(t['best_effort_timestamp_time'])*1000000)) for t in times]
        def tree(lo,hi):
            if hi-lo==1:return str(stamps[lo])
            mid=(lo+hi)//2
            return f'if(lt(N\\,{mid})\\,{tree(lo,mid)}\\,{tree(mid,hi)})'
        script=folder/'native-pts.filter'
        script.write_text('settb=1/1000000,setpts='+tree(0,count),encoding='utf-8')
        filter_args=['-filter_script:v',str(script)]
    command=['ffmpeg','-v','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080',
        '-framerate',fps,'-i','pipe:0','-i',str(source),'-map','0:v:0','-map','1:a:0',
        *filter_args,'-fps_mode','passthrough','-enc_time_base','1:1000000',
        '-c:v','libx264','-crf','12','-preset','medium','-threads','4','-pix_fmt','yuv420p',
        '-c:a','copy','-avoid_negative_ts','disabled','-map_metadata','-1','-metadata:s:a:0','language='+language,str(master)]
    print(f'{name}: {count} native frames; blend {overlap_first}..{overlap_last}; encoding',flush=True)
    own=Decoder(opening);shared=Decoder(COMMON)
    with (folder/'encode.log').open('wb') as log:
        enc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for n,base in enumerate(mapped):
                if n<overlap_first:frame=own.get(n)
                elif n<=overlap_last:
                    a=np.frombuffer(own.get(n),np.uint8)
                    b=np.frombuffer(shared.get(base-210),np.uint8)
                    weight=(n-overlap_first)/(overlap_last-overlap_first)
                    frame=np.rint(a.astype(np.float32)*(1-weight)+b.astype(np.float32)*weight).clip(0,255).astype(np.uint8).tobytes()
                else:frame=shared.get(base-210)
                enc.stdin.write(frame)
                if n and n%600==0:print(f'{name}: {n}/{count}',flush=True)
        finally:
            enc.stdin.close();own.close();shared.close()
        assert enc.wait()==0,(folder/'encode.log').read_text()
    # Rewrap original Vorbis intact; browser preview uses AAC, encoded only once.
    assert pcm_hash(master)==metadata['audio_pcm_hash'],'Native audio changed'
    probe=json.loads(call(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries',
        'frame=best_effort_timestamp_time','-of','json',master]))
    assert len(probe['frames'])==count
    drift=max(abs(float(f['best_effort_timestamp_time'])-float(times[i]['best_effort_timestamp_time'])) for i,f in enumerate(probe['frames']))
    assert drift<=.0021,(locale,drift)
    preview=folder/f'{name}-SeedVR2-1080-audio.mp4'
    call(['ffmpeg','-v','error','-nostdin','-n','-i',master,'-map','0:v:0','-map','0:a:0','-c:v','copy',
        '-c:a','aac','-b:a','192k','-movflags','+faststart','-avoid_negative_ts','disabled',preview])
    with (folder/'assembly-frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['locale_frame','native_pts_s','default_frame','shared_frame','opening_weight'])
        for n,base in enumerate(mapped):
            opening_weight=1 if n<overlap_first else (0 if n>overlap_last else 1-(n-overlap_first)/(overlap_last-overlap_first))
            w.writerow([n,times[n]['best_effort_timestamp_time'],base,base-210 if n>=overlap_first else '',opening_weight])
    result=dict(locale=locale,frames=count,source=metadata['source'],native_audio_pcm_identical=True,
        audio_codec_master='vorbis-copy',master=master.relative_to(RUN).as_posix(),preview=preview.relative_to(RUN).as_posix(),
        overlap_frames_inclusive=[overlap_first,overlap_last],blend='same-scene aligned frames, linear opening-to-common weights',
        max_native_pts_deviation_s=drift,installed=False,user_validation='pending')
    save(folder/'assembly.json',result)
    print(f'{name}: ready; native PCM identical; PTS deviation {drift:.6f}s',flush=True)
    return result


def compare(default):
    folder=RUN/'default';source=ROOT/'video/intro/intro.wbm';processed=RUN/default['preview']
    original=folder/'INTRO-original-720-audio-v2.mp4'
    call(['ffmpeg','-v','error','-nostdin','-n','-copyts','-i',source,'-i',processed,'-map','0:v:0','-map','1:a:0',
        '-c:v','libx264','-crf','16','-preset','medium','-threads','4','-pix_fmt','yuv420p','-fps_mode','passthrough',
        '-enc_time_base','1:1000000','-video_track_timescale','1000000',
        '-c:a','copy','-movflags','+faststart',original])
    # Same AAC packets on both sides; do not play two audio tracks simultaneously.
    assert pcm_hash(original)==pcm_hash(processed)
    html=f'''<!doctype html><meta charset="utf-8"><title>INTRO — Original / SeedVR</title>
<style>body{{background:#15171a;color:white;font:16px system-ui;margin:24px}}.pair{{display:flex;gap:12px}}figure{{width:50%;margin:0}}video{{width:100%;background:black}}button{{padding:10px;margin:8px}}</style>
<h1>INTRO — original et version traitée</h1><p>Fichier commun de l’installation, carton anglais. Audio identique dans les deux aperçus. Source 720p à gauche ; SeedVR 1080p à droite.</p>
<button onclick="playPair()">Lire / pause ensemble</button><button onclick="vs.forEach(v=>{{v.pause();v.currentTime=0}})">Revenir au début</button>
<div class="pair"><figure><video controls muted preload="metadata" src="{original.name}"></video><figcaption>Original 720p — son coupé pour éviter l’écho</figcaption></figure><figure><video controls preload="metadata" src="{processed.name}"></video><figcaption>SeedVR 1080p — son actif</figcaption></figure></div>
<script>const vs=[...document.querySelectorAll('video')];function playPair(){{if(vs[1].paused){{vs[0].currentTime=vs[1].currentTime;vs.forEach(v=>v.play())}}else vs.forEach(v=>v.pause())}}vs[1].addEventListener('seeked',()=>{{if(Math.abs(vs[0].currentTime-vs[1].currentTime)>.04)vs[0].currentTime=vs[1].currentTime}});</script>'''
    (folder/'original-vs-seedvr.html').write_text(html,encoding='utf-8')
    return dict(original=original.relative_to(RUN).as_posix(),processed=default['preview'],comparator='default/original-vs-seedvr.html',
                preview_audio_identical=True,french_separate_source=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    RUN.mkdir(parents=True,exist_ok=args.resume)
    results=[]
    for locale in ['default','de_DE','pl_PL']:
        existing=RUN/locale/'assembly.json'
        if args.resume and existing.exists():results.append(json.loads(existing.read_text(encoding='utf-8')))
        else:results.append(assemble(locale,resume=args.resume))
        save(RUN/'assembly.json',dict(status='assembling',results=results))
    comparison=compare(results[0])
    save(RUN/'assembly.json',dict(status='review-ready',results=results,comparison=comparison,
        second_film_started=False,installed=False))
    (RUN/'README.md').write_text('# INTRO — assemblages par langue, 2026-11-11 v1\n\n'
        '- Périmètre : INTRO uniquement ; default/de_DE/pl_PL ; aucun corps commun INTRO15F traité.\n'
        '- Cartons SeedVR + master commun : appariements natifs CSV de l’analyse20261110 ; mêmes images alignées fondues dans le chevauchement ~7–8s. Aucun mélange de deux instants distincts.\n'
        '- Rythme et nombre d’images propres aux langues conservés ; retiming <2.1ms ; détails assembly-frames.csv et assembly.json de chaque langue.\n'
        '- Masters MKV : H264 CRF12/medium 1920×1080 + Vorbis natif copié ; PCM décodé strictement identique à chaque source. Fins audio conservées sans shortest/étirement.\n'
        '- MP4 de lecture : vidéo copiée du master, audio AAC192k ; original/traité utilisent exactement le même AAC pour la comparaison.\n'
        '- Pas de fichier français distinct dans l’installation ; utilisateur a demandé de comparer le fichier commun original et traité. Pas de traduction/doublage ajouté.\n'
        '- Comparaison : default/original-vs-seedvr.html ; aperçu source : default/INTRO-original-720-audio-v2.mp4.\n'
        '- Validation utilisateur en attente ; aucune installation/release.\n',encoding='utf-8')
    print('All three INTRO assemblies and original/processed comparison ready.',flush=True)


if __name__=='__main__':main()
