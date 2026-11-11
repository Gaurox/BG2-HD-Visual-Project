"""Verify INTRO shared-body streaming output and prepare a review MP4, without comparator."""
import csv
import json
import subprocess
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/experiments/intro-common-seedvr3b-stream-1080-20261111-v1'


def call(args):
    p=subprocess.run([str(a) for a in args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p.stdout


def main():
    report=json.loads((RUN/'run.json').read_text())
    assert report['status']=='inference-completed',report['status']
    raw=RUN/report['output']
    probe=json.loads(call(['ffprobe','-v','error','-select_streams','v:0','-show_streams','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time:stream=width,height,r_frame_rate,avg_frame_rate,duration',
        '-of','json',raw]))
    assert len(probe['frames'])==report['frames']==3137
    s=probe['streams'][0];assert (s['width'],s['height'])==(1920,1080)
    timeline=list(csv.DictReader((RUN/'frames.csv').open()))
    drift=max(abs(float(f['best_effort_timestamp_time'])-float(timeline[i]['rebased_pts_s']))
              for i,f in enumerate(probe['frames']))
    assert drift<.002,(drift,s)
    final=RUN/'INTRO-common-SeedVR2-3B-FP16-LAB-1080p.mp4'
    assert not final.exists(),final
    call(['ffmpeg','-v','error','-nostdin','-n','-i',raw,'-map','0:v:0','-an','-c:v','copy',
          '-movflags','+faststart',final])
    review=RUN/'controle';review.mkdir(exist_ok=True)
    for sec in [5,25,55,85,103]:
        call(['ffmpeg','-v','error','-nostdin','-n','-ss',str(sec),'-i',final,'-frames:v','1',review/f'{sec:03d}s.png'])
    # Diagnostic only: compare adjacent luma changes around streaming boundaries.
    # Source-normalized changes distinguish natural cuts from potential inference joins.
    output=np.frombuffer(call(['ffmpeg','-v','error','-threads','2','-i',final,'-an','-vf',
        'scale=160:90:flags=area,format=gray','-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(-1,90,160)
    source=np.fromfile(ROOT/'video/research/intro-locales-analysis-20261110-v1/INTRO-default.gray',np.uint8).reshape(-1,90,160)[report['source_first_frame']:]
    assert len(source)==len(output)==3137
    native_change=np.abs(np.diff(source.astype(np.float32),axis=0)).mean(axis=(1,2))
    final_change=np.abs(np.diff(output.astype(np.float32),axis=0)).mean(axis=(1,2))
    joins=[]
    for n in range(330,3137,330):
        joins.append(dict(frame=n,clip_time_s=float(probe['frames'][n]['best_effort_timestamp_time']),
            native_adjacent_luma_mae=float(native_change[n-1]),output_adjacent_luma_mae=float(final_change[n-1]),
            output_local_adjacent_mae_median=float(np.median(final_change[max(0,n-6):n+5]))))
    verification=dict(status='review-ready',frames=3137,width=1920,height=1080,
        duration_s=float(s['duration']),fps=s['r_frame_rate'],max_native_pts_deviation_s=drift,
        completed_chunks=report['expected_chunks'],chunk_frames=330,joins=joins,
        video=final.name,audio=False,interpolation=False,second_film_started=False,
        user_validation='pending',installed=False,comparator=False)
    (RUN/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    (RUN/'README.md').write_text('# INTRO — corps commun SeedVR streaming, 2026-11-11 v1\n\n'
        '- Source : video/intro/intro.wbm, images210..3346 incluses ; PTS7.019..111.656s ; 3137 images, ~104.67s. Recouvrement avec la fin du carton anglais : images210..239.\n'
        '- Entrée FFV1 YUV420p1280×720 ; égalité de toutes les images décodées vérifiée avec les SHA natifs ; frames.csv conserve correspondance/PTS.\n'
        '- SeedVR2 CLI installé2.5.24 : 3B FP16, VAE FP16, LAB, seed42, résolution1080, batch33 uniforme, overlap3, bruits0 ; swap32, SDPA, CPU offload ; VAE encode1024/128 et decode768/128.\n'
        '- Streaming330 images/portion, cache DiT/VAE actif ; 10 portions avec contexte précédent. Commande exacte/run/horaires : run.json.\n'
        '- Démarrage CLI direct : erreur métadonnées flash_attn de Transformers ; bootstrap local au processus force cette optimisation optionnelle indisponible, attention réelle SDPA inchangée. Aucun paquet installé/modifié.\n'
        '- Export CLI initial : allocation float32 trop grande pour330 images ; bootstrap convertit par groupes de8 et finalise chaque portion. portions/ conserve les intermédiaires lisibles, assemblés sans réencodage.\n'
        '- MP4 H264 CRF12 produit par le CLI ; copie vidéo sans réencodage vers le MP4 de validation avec faststart. Cadence native30000/1001, muet, sans interpolation.\n'
        '- verification.json : dimensions, compte, PTS, diagnostic des jointures (non équivalent à validation utilisateur) ; controle/ : images de revue.\n'
        '- Validation utilisateur en attente ; second film non commencé ; aucune installation/release ; aucun comparateur.\n',encoding='utf-8')
    print(json.dumps(verification),flush=True)


if __name__=='__main__':main()
