"""Export and review an INTRO15F localized opening, preserving native frame timing."""
import csv
import argparse
import importlib.util
import json
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('opening_exports', HERE/'finish_seedvr_openings.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
ROOT = HERE.parents[2]
RUN = ROOT/'video/experiments/intro15f-default-seedvr3b-1080-20261111-v1'
PREP = ROOT/'video/preparation/intro-localized-segments-20261111-v1/INTRO15F/default'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--locale',default='default',choices=['default','de_DE','it_IT','pl_PL'])
    parser.add_argument('--run')
    parser.add_argument('--prompt-id',default='3999d6b1-9979-4f9a-a6a7-dbeecabd10a9')
    parser.add_argument('--no-comparator',action='store_true')
    args=parser.parse_args()
    locale=args.locale
    run=Path(args.run).resolve() if args.run else RUN
    prep=PREP.parent/locale
    label={'default':'anglais','de_DE':'allemand','it_IT':'italien','pl_PL':'polonais'}[locale]
    entry = json.loads((prep/'segment.json').read_text())
    source = next(prep.glob('*.mkv'))
    # Local aliases keep default invocation backward compatible; old media remain untouched.
    export(run,prep,locale,label,args.prompt_id,entry,source,args.no_comparator)


def export(RUN,PREP,locale,label,prompt_id,entry,source,no_comparator=False):
    raw = list((RUN/'comfy-output').rglob('*.mov'))
    assert len(raw) == 1, raw
    raw = raw[0]
    info = helpers.probe(raw)
    assert len(info['frames']) == entry['frames']
    assert (info['streams'][0]['width'],info['streams'][0]['height']) == (1920,1080)
    final = RUN/f'INTRO15F-{locale}-SeedVR2-3B-FP16-LAB-1080p15.mp4'
    preview = RUN/f'INTRO15F-{locale}-source-720p15.mp4'
    timeline = list(csv.DictReader((PREP/'frames.csv').open()))
    checks=[]
    timing='settb=1/1000000,setpts=max(N-1\\,0)*1001/(15000*TB)' if locale=='pl_PL' else 'settb=1/1000000,setpts=N/(15*TB)'
    for src,dst in [(raw,final),(source,preview)]:
        if not dst.exists():
            helpers.run(['ffmpeg','-v','error','-nostdin','-n','-threads','4','-i',src,'-map','0:v:0','-an',
                '-vf',timing,'-fps_mode','passthrough','-enc_time_base','1:1000000',
                '-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p','-threads','4',
                '-video_track_timescale','1000000','-movflags','+faststart',dst])
        p=helpers.probe(dst)
        assert len(p['frames']) == entry['frames']
        drift=max(abs(float(f['best_effort_timestamp_time'])-(float(timeline[i]['source_pts_s'])-entry['source_first_pts_s']))
                  for i,f in enumerate(p['frames']))
        assert drift<.002,drift
        checks.append(dict(file=dst.name,frames=entry['frames'],width=p['streams'][0]['width'],height=p['streams'][0]['height'],max_native_pts_deviation_s=drift))
    if no_comparator:
        result=dict(status='review-ready',user_qa='pending',prompt_id=prompt_id,
            source=source.relative_to(ROOT).as_posix(),raw_master=raw.relative_to(RUN).as_posix(),
            settings=json.loads((RUN/'workflow.api.json').read_text()),checks=checks,audio=False,
            interpolation=False,final_join_not_fixed=True,installed=False,comparator_requested=False)
        (RUN/'results.json').write_text(json.dumps(result,indent=2)+'\n')
        (RUN/'README.md').write_text(f'# INTRO15F {locale} — SeedVR, 2026-11-11\n\n'
            f'- {entry["frames"]} images, 1920×1080, cadence native, muet ; aucune interpolation.\n'
            '- Profil : SeedVR2 3B FP16/LAB, seed42, batch33 uniforme, overlap3 ; workflow.api.json exact.\n'
            '- Master : comfy-output/*.mov ; lecture : INTRO15F-*-1080p15.mp4 ; aperçu source : *-source-720p15.mp4.\n'
            '- PTS natifs rétablis avec écart <2ms ; résultats/contrôles : results.json.\n'
            '- Aucun comparateur supplémentaire demandé ; aucune installation/release ; QA utilisateur en attente.\n',encoding='utf-8')
        print(json.dumps(checks),flush=True)
        return
    comparison=Image.new('RGB',(1920,570),'#202020');draw=ImageDraw.Draw(comparison)
    for x,src,label in [(0,source,'Source + Lanczos'),(960,final,'SeedVR 3B FP16 LAB')]:
        frame=min(range(len(timeline)),key=lambda n:abs(float(timeline[n]['source_pts_s'])-8))
        im=helpers.still(src,frame).resize((960,540),Image.Resampling.LANCZOS)
        comparison.paste(im,(x,30));draw.text((x+12,8),f'INTRO15F {locale} | {label} | 8s',fill='white')
    comparison.save(RUN/'carton-avant-apres.jpg',quality=95)
    sheet=Image.new('RGB',(1920,472),'#202020');draw=ImageDraw.Draw(sheet)
    for i,sec in enumerate([0,1,3,8,15,16.5,17,17.5,18,18.8]):
        frame=min(range(len(timeline)),key=lambda n:abs(float(timeline[n]['source_pts_s'])-sec))
        im=helpers.still(final,frame).resize((384,216),Image.Resampling.LANCZOS)
        x=(i%5)*384;y=(i//5)*236
        sheet.paste(im,(x,y+20));draw.text((x+8,y+3),f'{sec:g}s | frame {frame}',fill='white')
    sheet.save(RUN/'fondus-et-transition.jpg',quality=95)
    result=dict(status='review-ready',user_qa='pending',prompt_id=prompt_id,
        source=str(source.relative_to(ROOT)).replace('\\','/'),raw_master=raw.relative_to(RUN).as_posix(),
        settings=json.loads((RUN/'workflow.api.json').read_text()),checks=checks,audio=False,interpolation=False,
        final_join_not_fixed=True,installed=False)
    (RUN/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    html=f'''<!doctype html><meta charset="utf-8"><title>INTRO15F {locale} — SeedVR</title>
<style>body{{background:#17191c;color:white;font:16px system-ui;margin:24px}}.pair{{display:flex;gap:12px}}figure{{margin:0;width:50%}}video{{width:100%}}button{{padding:10px;margin:10px}}</style>
<h1>INTRO15F {locale} — ouverture ~19 secondes</h1><p>Source à gauche ; SeedVR 3B FP16 LAB Full HD à droite. Cadence native (~15 fps), muet. Fin conservée pour le raccord.</p>
<button onclick="let v=[...document.querySelectorAll('video')];if(v[1].paused){{v[0].currentTime=v[1].currentTime;v.forEach(x=>x.play())}}else v.forEach(x=>x.pause())">Lire / pause ensemble</button>
<button onclick="document.querySelectorAll('video').forEach(v=>{{v.pause();v.currentTime=0}})">Revenir au début</button>
<div class="pair"><figure><video controls preload="metadata" src="{preview.name}"></video><figcaption>Source 720p</figcaption></figure><figure><video controls preload="metadata" src="{final.name}"></video><figcaption>SeedVR 1080p</figcaption></figure></div>'''
    (RUN/'comparateur.html').write_text(html,encoding='utf-8')
    (RUN/'README.md').write_text(f'# INTRO15F {locale} — SeedVR qualité, 2026-11-11 v1\n\n'
        f'- Périmètre : extrait préparé ~19s, {entry["frames"]} images natives ; langue={locale}.\n'
        '- Même profil que les trois INTRO appréciés : SeedVR2 3B FP16, VAE FP16, LAB, seed42, résolution1080, batch33 uniforme, overlap3, aucun bruit ; workflow.api.json exact.\n'
        '- Master MOV ProRes conservé dans comfy-output/ ; MP4 H264 CRF16/slow, 1920×1080, cadence native ~15fps ; muet, sans interpolation.\n'
        '- Cadence/ordre natifs conservés ; départ ramené à0 ; écart PTS source <2ms. Fenêtre ouverture 0–18s + contexte jusqu’à19s ; raccord définitif non choisi.\n'
        '- comparateur.html, carton-avant-apres.jpg, fondus-et-transition.jpg ; results.json : contrôles.\n'
        '- QA utilisateur en attente ; aucune installation/release.\n',encoding='utf-8')
    print(json.dumps(checks),flush=True)


if __name__=='__main__':
    main()
