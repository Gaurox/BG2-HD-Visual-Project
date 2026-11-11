"""Reuse every INTRO shared-master frame on the Polish timeline, without motion synthesis."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
SPEC=importlib.util.spec_from_file_location('intro_assembly',ROOT/'pipeline/recipes/video-intro-locales-analysis-20261110-v1/assemble_intro_locales.py')
H=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(H)
RUN=ROOT/'video/assembly/intro-polish-master30-20261111-v1'
FPS=30000/1001  # Same rate as the shared master: nominal 30 fps.


def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def plan():
    rows=list(csv.DictReader((H.AUDIT/'INTRO-pl_PL-to-default.csv').open()))
    pts=np.array([float(r['locale_pts_s']) for r in rows])
    default=np.array([int(r['default_frame']) for r in rows])
    video_end=pts[-1]+float(np.median(np.diff(pts[-30:])))
    out_pts=np.arange(int(np.ceil(video_end*FPS)))/FPS
    target=np.interp(out_pts,pts,default)
    cut=int(np.searchsorted(target,210))
    target=target[cut:]-210
    count=len(target);master_count=3137
    # Constrain the path to advancing exactly one master frame or holding it.
    # This removes DTW sampling jitter while retaining EVERY real master frame.
    # Timestamp/index interpolation above does not generate or blend image pixels.
    indices=np.arange(master_count,dtype=np.float32)
    previous=np.full(master_count,np.inf,np.float32);previous[0]=target[0]**2
    advance=np.zeros((count,master_count),bool)
    for i in range(1,count):
        shifted=np.r_[np.inf,previous[:-1]]
        advance[i]=shifted<=previous
        previous=np.minimum(previous,shifted)+(indices-target[i])**2
        previous[i+1:]=np.inf
    path=np.empty(count,np.int32);j=master_count-1
    for i in range(count-1,-1,-1):
        path[i]=j
        if i and advance[i,j]:j-=1
    assert path[0]==0 and path[-1]==master_count-1
    assert set(np.diff(path))<={0,1}
    assert np.array_equal(np.unique(path),np.arange(master_count))
    opening=np.maximum(0,np.searchsorted(pts,out_pts[:cut]+.0005,side='right')-1)
    opening[0]=0
    assert opening.max()<121
    native=np.fromfile(H.AUDIT/'INTRO-pl_PL.gray',np.uint8).reshape(-1,90,160)
    common=np.fromfile(H.AUDIT/'INTRO-default.gray',np.uint8).reshape(-1,90,160)
    out_default=np.zeros(len(out_pts),np.int32);out_default[cut:]=path+210
    anchors=np.clip(np.rint(pts*FPS).astype(int),0,len(out_pts)-1)
    visible=(native.max(axis=(1,2))>8)&(default>=210)
    errors=np.abs(native[visible].astype(np.float32)-common[out_default[anchors[visible]]].astype(np.float32)).mean(axis=(1,2))
    diagnostic=dict(native_visible_anchor_luma_mae_p50=float(np.median(errors)),
        native_visible_anchor_luma_mae_p99=float(np.percentile(errors,99)),
        native_visible_anchor_luma_mae_max=float(errors.max()),
        note='160x90 vanilla picture correspondence; visual-sync diagnostic, not a speech/lip-sync certification')
    assert diagnostic['native_visible_anchor_luma_mae_max']<3.1
    with (RUN/'frame-map.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['output_frame','output_pts_s','image_source','image_index'])
        for n,t in enumerate(out_pts):w.writerow([n,f'{t:.9f}','polish-opening' if n<cut else 'shared-master',int(opening[n]) if n<cut else int(path[n-cut])])
    return out_pts,cut,opening,path,diagnostic


def probe(path):
    return json.loads(H.call(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries',
        'stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames,start_time,duration','-of','json',path]))['streams'][0]


def main():
    RUN.mkdir(parents=True,exist_ok=False)
    pts,cut,opening,path,diagnostic=plan()
    video=RUN/'INTRO-pl_PL-SeedVR2-shared-master-1080p2997-video.mp4'
    master=RUN/'INTRO-pl_PL-SeedVR2-shared-master-1080p2997-native-audio.mkv'
    preview=RUN/'INTRO-pl_PL-SeedVR2-shared-master-1080p2997-audio.mp4'
    source=ROOT/'video/pl_PL_intro/pl_PL_INTRO.wbm'
    own=H.Decoder(H.OPENINGS/'pl_PL/INTRO-pl_PL-SeedVR2-3B-FP16-LAB-1080p.mp4')
    shared=H.Decoder(H.COMMON)
    args=['ffmpeg','-v','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080',
        '-framerate','30000/1001','-i','pipe:0','-an','-c:v','libx264','-crf','12','-preset','medium',
        '-threads','4','-pix_fmt','yuv420p','-fps_mode','passthrough','-video_track_timescale','30000',
        '-movflags','+faststart',str(video)]
    print(f'{len(pts)} output slots; {len(np.unique(path))} shared frames retained; join {cut/FPS:.4f}s; no generated/blended pixels',flush=True)
    with (RUN/'encode.log').open('wb') as log:
        encoder=subprocess.Popen(args,stdin=subprocess.PIPE,stderr=log)
        try:
            for n in range(len(pts)):
                frame=own.get(int(opening[n])) if n<cut else shared.get(int(path[n-cut]))
                encoder.stdin.write(frame)
                if n and n%600==0:print(f'{n}/{len(pts)} frames',flush=True)
        finally:
            encoder.stdin.close();own.close();shared.close()
        assert encoder.wait()==0,(RUN/'encode.log').read_text()
    H.call(['ffmpeg','-v','error','-nostdin','-n','-i',video,'-i',source,'-map','0:v:0','-map','1:a:0',
        '-c','copy','-avoid_negative_ts','disabled','-metadata:s:a:0','language=pol',master])
    assert H.pcm_hash(master)==H.pcm_hash(source)
    H.call(['ffmpeg','-v','error','-nostdin','-n','-i',video,'-i',source,'-map','0:v:0','-map','1:a:0',
        '-c:v','copy','-c:a','aac','-b:a','192k','-metadata:s:a:0','language=pol','-movflags','+faststart',preview])
    info=probe(preview)
    assert info['r_frame_rate']=='30000/1001' and int(info['nb_read_frames'])==len(pts)
    assert (info['width'],info['height'])==(1920,1080)
    original_packets=json.loads(H.call(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time','-of','json',source]))['packets']
    master_packets=json.loads(H.call(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time','-of','json',master]))['packets']
    assert len(original_packets)==len(master_packets)
    audio_drift=max(abs(float(a['pts_time'])-float(b['pts_time'])) for a,b in zip(original_packets,master_packets))
    assert audio_drift<=.0011,audio_drift
    result=dict(status='review-ready',locale='pl_PL',film='INTRO',nominal_fps=30,exact_fps='30000/1001',
        output_frames=len(pts),video_duration_s=float(info['duration']),native_video_end_s=114.772,
        master_frames_reused=3137,master_frames_skipped=0,master_holds=int(np.sum(np.diff(path)==0)),
        cut_frame=cut,cut_pts_s=cut/FPS,opening='Existing Polish ~15fps frames held; no synthesized in-betweens',
        timeline='Monotone alignment to native Polish timestamps; every common master frame retained in order',
        native_audio_pcm_identical=True,audio_packets_identical_count=len(master_packets),max_audio_pts_deviation_s=audio_drift,
        audio_stretched=False,interpolation_ai=False,pixel_blending=False,sync_diagnostic=diagnostic,
        master=master.name,preview=preview.name,previous_15fps_assembly_preserved=True,installed=False,user_validation='pending')
    save(RUN/'verification.json',result)
    (RUN/'README.md').write_text('# INTRO polonais — master commun cadence30, 2026-11-11 v1\n\n'
        '- Variante autonome ; ancien assemblage ~15fps conservé, aucune installation/release.\n'
        '- Sortie1920×1080, cadence exacte30000/1001 (~30 nominal comme le master),3440images. Vidéo≈114.781s ; audio natif complet, queue conservée.\n'
        '- Carton polonais existant≈15fps : images maintenues ; raccord au master commun à6.9069s. Aucune nouvelle inférence ni interpolation IA, aucun mélange de pixels.\n'
        '-3137images du master commun réutilisées intégralement et dans l’ordre ;96maintiens supplémentaires pour le calage polonais. frame-map.csv relie chaque slot à son image réelle.\n'
        '- Correspondance temporelle : carte native INTRO-pl_PL-to-default.csv ; chemin monotone à avances0/1, sans suppression d’images du master. Contrôle luma miniature des ancrages visibles dans verification.json.\n'
        '- Encodage vidéo unique H264CRF12/medium ; copies vidéo dans masterMKV/Vorbis natif et MP4/AAC192k. PCM et PTS des paquets Vorbis vérifiés identiques à la source ; aucun étirement/coupe audio.\n'
        '- Cadence différente ≠ nouvelles images : toutes les images sortantes proviennent de l’ouverture ou du master déjà traité. Validation utilisateur en attente.\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
