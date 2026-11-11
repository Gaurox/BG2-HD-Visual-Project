"""Export the three SeedVR opening trials and synchronized review assets."""
import csv
import io
import json
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
PREP = ROOT / 'video/preparation/intro-localized-segments-20261111-v1'
RUN = ROOT / 'video/experiments/intro-openings-seedvr3b-1080-20261111-v1'


def run(args):
    p = subprocess.run([str(a) for a in args], capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8', errors='replace'))
    return p.stdout


def probe(path):
    return json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams',
                          '-show_frames', '-show_entries', 'frame=best_effort_timestamp_time:stream=width,height,r_frame_rate,nb_frames',
                          '-of', 'json', path]))


def still(path, frame):
    b = run(['ffmpeg', '-v', 'error', '-threads', '2', '-i', path, '-vf', f'select=eq(n\\,{frame})',
             '-frames:v', '1', '-f', 'image2pipe', '-c:v', 'png', '-'])
    return Image.open(io.BytesIO(b)).convert('RGB')


def main():
    review = RUN / 'comparatifs'
    review.mkdir(exist_ok=True)
    results = []
    sheet = Image.new('RGB', (1920, 3 * 410), '#202020')
    full_sheet = Image.new('RGB', (1920, 3 * 570), '#202020')
    draw = ImageDraw.Draw(sheet)
    for row, lang in enumerate(['default', 'de_DE', 'pl_PL']):
        name = f'INTRO-{lang}'
        entry = next(e for e in json.loads((PREP / 'manifest.json').read_text())['segments'] if e['name'] == name)
        src = PREP / entry['clip']
        folder = RUN / lang
        folder.mkdir(exist_ok=True)
        raw = list((RUN / 'comfy-output' / lang).rglob('*.mov'))
        if not raw and '--partial' in sys.argv:
            continue
        assert len(raw) == 1, (lang, raw)
        raw = raw[0]
        raw_probe = probe(raw)
        assert len(raw_probe['frames']) == entry['frames'], (lang, len(raw_probe['frames']), entry['frames'])
        assert (raw_probe['streams'][0]['width'], raw_probe['streams'][0]['height']) == (1920, 1080)
        # Restore source frame timing after ComfyUI's constant-fps CreateVideo.
        # Polish has two distinct initial frames both stamped 0 in the native file.
        expression = 'max(N-1,0)*1001/(15000*TB)' if lang == 'pl_PL' else 'N*1001/(30000*TB)'
        timing = f'settb=1/1000000,setpts={expression.replace(",", chr(92)+",")}'
        final = folder / f'{name}-SeedVR2-3B-FP16-LAB-1080p.mp4'
        source_preview = folder / f'{name}-source-720p.mp4'
        for input_path, dest in [(raw, final), (src, source_preview)]:
            if not dest.exists():
                run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-threads', '4', '-i', input_path, '-map', '0:v:0', '-an',
                     '-vf', timing, '-fps_mode', 'passthrough', '-enc_time_base', '1:1000000',
                     '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-threads', '4',
                     '-video_track_timescale', '1000000', '-movflags', '+faststart', dest])
        pp = probe(final)
        assert len(pp['frames']) == entry['frames']
        timeline = list(csv.DictReader((PREP / entry['clip']).with_name('frames.csv').open()))
        origin = float(timeline[0]['source_pts_s'])
        drift = max(abs(float(f['best_effort_timestamp_time']) - (float(timeline[i]['source_pts_s']) - origin))
                    for i, f in enumerate(pp['frames']))
        assert drift < .002, (lang, drift)
        # Full-size center crop at the stable card, source enlarged only by Lanczos.
        idx = min(range(len(timeline)), key=lambda i: abs(float(timeline[i]['source_pts_s']) - 3))
        before = still(src, idx).resize((1920,1080), Image.Resampling.LANCZOS)
        after = still(final, idx)
        fd = ImageDraw.Draw(full_sheet)
        for x, im, label in [(0, before, 'Source + Lanczos'), (960, after, 'SeedVR 3B FP16 LAB')]:
            full_sheet.paste(im.resize((960, 540), Image.Resampling.LANCZOS), (x, row * 570 + 30))
            fd.text((x + 12, row * 570 + 8), f'{name} | {label}', fill='white')
        card = Image.new('RGB',(1920,410),'#202020'); d=ImageDraw.Draw(card)
        for x,im,label in [(0,before,'Source + Lanczos'),(960,after,'SeedVR 3B FP16 LAB')]:
            card.paste(im.crop((480,300,1440,680)),(x,30));d.text((x+12,8),f'{name} | {label} | frame {idx}',fill='white')
        card.save(review / f'{name}-texte-avant-apres.png')
        sheet.paste(card,(0,row*410))
        # Native-sized output frames for inspection of fades and the shared tail context.
        for sec in [0,1,3,5.5,6,7.5]:
            n=min(range(len(timeline)),key=lambda i:abs(float(timeline[i]['source_pts_s'])-sec))
            still(final,n).save(review / f'{name}-{sec:g}s.png')
        results.append(dict(name=name,frames=entry['frames'],dimensions=[1920,1080],video=final.relative_to(RUN).as_posix(),
                            source_preview=source_preview.relative_to(RUN).as_posix(),raw_master=raw.relative_to(RUN).as_posix(),
                            source=entry['clip'],max_native_pts_deviation_s=drift,audio=False,interpolation=False))
        print(f'{name}: export and timing verified; {entry["frames"]} frames; drift {drift:.6f}s',flush=True)
    if len(results) != 3:
        return
    sheet.save(review / 'INTRO-trois-langues-textes-avant-apres.jpg',quality=95)
    full_sheet.save(review / 'INTRO-trois-langues-cartons-complets.jpg', quality=95)
    (RUN/'results.json').write_text(json.dumps(dict(status='review-ready',user_qa='pending',installed=False,
        settings=dict(model='seedvr2_ema_3b_fp16.safetensors',vae='ema_vae_fp16.safetensors',resolution=1080,
                      seed=42,batch_size=33,temporal_overlap=3,color_correction='lab'),results=results),indent=2)+'\n')
    html='''<!doctype html><meta charset="utf-8"><title>INTRO — SeedVR / sources</title>
<style>body{background:#15171a;color:#eee;font:16px system-ui;margin:24px}section{margin-bottom:30px} .pair{display:flex;gap:12px}figure{margin:0;width:50%}video{width:100%;background:black}button{margin:8px;padding:8px}figcaption{padding:8px}</style>
<h1>INTRO — trois ouvertures SeedVR Full HD</h1><p>Gauche : source. Droite : SeedVR 3B FP16 LAB. Muet ; cadence native, sans interpolation. Les images finales après 7 s servent au raccord.</p>'''
    for e in results:
        html+=f'<section><h2>{e["name"]}</h2><button onclick="playPair(this)">Lire / pause ensemble</button><button onclick="resetPair(this)">Revenir au début</button><div class="pair"><figure><video controls preload="metadata" src="{e["source_preview"]}"></video><figcaption>Source 720p</figcaption></figure><figure><video controls preload="metadata" src="{e["video"]}"></video><figcaption>SeedVR 1080p</figcaption></figure></div></section>'
    html+='''<script>function playPair(b){let v=[...b.parentElement.querySelectorAll('video')];if(v[1].paused){v[0].currentTime=v[1].currentTime;v.forEach(x=>x.play())}else v.forEach(x=>x.pause())}function resetPair(b){b.parentElement.querySelectorAll('video').forEach(v=>{v.pause();v.currentTime=0})}</script>'''
    (RUN/'comparateur.html').write_text(html,encoding='utf-8')
    (RUN/'README.md').write_text('# INTRO — SeedVR ouvertures, 2026-11-11 v1\n\n'
        '- Trois variantes : default (anglais), de_DE, pl_PL ; uniquement les extraits préparés ~8s.\n'
        '- SeedVR2 3B FP16, VAE FP16, LAB, 1080, seed42, batch33 uniforme, overlap3 ; voir workflows exacts.\n'
        '- MOV ProRes ComfyUI conservés dans comfy-output/ ; MP4 H264 CRF16 pour lecture dans chaque dossier de langue.\n'
        '- Cadence native sans interpolation, aucun son ; PTS source rétablis (écart <2ms). Noir/fondus laissés tels que produits par SeedVR.\n'
        '- comparateur.html : lecture source/résultat ; comparatifs/ : textes et images de contrôle.\n'
        '- results.json : comptages, dimensions et timings. Validation visuelle utilisateur en attente ; aucune installation/release.\n',encoding='utf-8')


if __name__=='__main__':
    main()
