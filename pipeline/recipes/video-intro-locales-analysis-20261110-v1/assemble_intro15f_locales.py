"""INTRO15F localized openings + shared SeedVR body, native PTS/audio/framing."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
from assemble_intro_locales import ROOT, AUDIT, Decoder, call, pcm_hash, save

RUN = ROOT/'video/assembly/intro15f-locales-seedvr-1080-20261111-v1'
COMMON = ROOT/'video/experiments/intro15f-common-seedvr3b-stream-1080-20261111-v1/INTRO15F-common-SeedVR2-3B-FP16-LAB-1080p.mp4'


class SharedDecoder(Decoder):
    def __init__(self, polish):
        filters = ['-vf', 'crop=1440:1080:240:0,scale=1920:1440:flags=lanczos,crop=1920:1080:0:180'] if polish else []
        self.p = subprocess.Popen(['ffmpeg','-v','error','-threads','2','-i',str(COMMON),
            '-map','0:v:0','-an',*filters,'-pix_fmt','rgb24','-threads','1',
            '-fps_mode','passthrough','-f','rawvideo','-'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        self.index=-1; self.frame=None


def assemble(locale):
    folder=RUN/locale; folder.mkdir(parents=True,exist_ok=True)
    result_path=folder/'assembly.json'
    if result_path.exists(): return json.loads(result_path.read_text())
    name='INTRO15F-'+locale
    metadata=json.loads((AUDIT/f'{name}.metadata.json').read_text())
    source=ROOT/metadata['source']
    times=json.loads((AUDIT/f'{name}.native-frame-times.json').read_text())['frames']
    stamps=[round(float(t['best_effort_timestamp_time'])*1000000) for t in times]
    if locale=='default':
        opening=ROOT/f'video/experiments/intro15f-default-seedvr3b-1080-20261111-v1/{name}-SeedVR2-3B-FP16-LAB-1080p15.mp4'
        mapped=list(range(len(times)))
    else:
        opening=ROOT/f'video/experiments/intro15f-locales-seedvr3b-1080-20261111-v1/{locale}/{name}-SeedVR2-3B-FP16-LAB-1080p15.mp4'
        suffix='-fitted' if locale=='pl_PL' else ''
        mapped=[int(r['default_frame']) for r in csv.DictReader((AUDIT/f'{name}{suffix}-to-default.csv').open())]
    prep=ROOT/f'video/preparation/intro-localized-segments-20261111-v1/INTRO15F/{locale}/segment.json'
    opening_count=json.loads(prep.read_text())['frames']
    first=next(i for i in range(opening_count) if mapped[i]>=270)
    last=opening_count-1
    assert len(mapped)==len(times) and all(a<=b for a,b in zip(mapped,mapped[1:]))
    assert min(mapped[first:])>=270 and max(mapped)<2574
    def tree(lo,hi):
        if hi-lo==1: return str(stamps[lo])
        mid=(lo+hi)//2
        return f'if(lt(N\\,{mid})\\,{tree(lo,mid)}\\,{tree(mid,hi)})'
    script=folder/'native-pts.filter'
    script.write_text('settb=1/1000000,setpts='+tree(0,len(times)))
    master=folder/f'{name}-SeedVR2-1080-native-audio.mkv'
    preview=folder/f'{name}-SeedVR2-1080-audio.mp4'
    assert not master.exists() and not preview.exists()
    language={'default':'eng','de_DE':'deu','it_IT':'ita','pl_PL':'pol'}[locale]
    command=['ffmpeg','-v','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24',
        '-video_size','1920x1080','-framerate','15','-i','pipe:0','-i',str(source),
        '-map','0:v:0','-map','1:a:0','-filter_script:v',str(script),'-fps_mode','passthrough',
        '-enc_time_base','1:1000000','-c:v','libx264','-crf','12','-preset','medium',
        '-threads','4','-pix_fmt','yuv420p','-c:a','copy','-avoid_negative_ts','disabled',
        '-map_metadata','-1','-metadata:s:a:0','language='+language,str(master)]
    own=Decoder(opening); shared=SharedDecoder(locale=='pl_PL')
    print(f'{locale}: encoding {len(times)} frames; overlap {first}..{last}',flush=True)
    with (folder/'encode.log').open('wb') as log:
        enc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for n,base in enumerate(mapped):
                if n<first: frame=own.get(n)
                elif n<=last:
                    a=np.frombuffer(own.get(n),np.uint8).astype(np.float32)
                    b=np.frombuffer(shared.get(base-270),np.uint8)
                    w=(n-first)/(last-first)
                    frame=np.rint(a*(1-w)+b*w).clip(0,255).astype(np.uint8).tobytes()
                else: frame=shared.get(base-270)
                enc.stdin.write(frame)
                if n and n%600==0: print(f'{locale}: {n}/{len(times)}',flush=True)
        finally:
            enc.stdin.close(); own.close(); shared.close()
        assert enc.wait()==0,(folder/'encode.log').read_text()
    assert pcm_hash(master)==metadata['audio_pcm_hash']
    probe=json.loads(call(['ffprobe','-v','error','-select_streams','v:0','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time,width,height','-of','json',master]))['frames']
    assert len(probe)==len(times)
    assert all((f['width'],f['height'])==(1920,1080) for f in probe)
    drift=max(abs(float(f['best_effort_timestamp_time'])-stamps[i]/1000000) for i,f in enumerate(probe))
    assert drift<=.0011,drift
    def audio_pts(path):
        return [float(p['pts_time']) for p in json.loads(call(['ffprobe','-v','error','-select_streams','a:0',
            '-show_packets','-show_entries','packet=pts_time','-of','json',path]))['packets']]
    a,b=audio_pts(source),audio_pts(master)
    assert len(a)==len(b)
    audio_drift=max(abs(x-y) for x,y in zip(a,b)); assert audio_drift<=.0011
    call(['ffmpeg','-v','error','-nostdin','-n','-i',master,'-map','0:v:0','-map','0:a:0',
        '-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart','-avoid_negative_ts','disabled',preview])
    for sec in [17.9,18.5,19.2,65]:
        call(['ffmpeg','-v','error','-nostdin','-n','-ss',str(sec),'-i',preview,'-frames:v','1',folder/f'check-{sec:g}s.png'])
    with (folder/'assembly-frames.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['locale_frame','native_pts_s','default_frame','opening_weight'])
        for n,base in enumerate(mapped):
            w.writerow([n,stamps[n]/1000000,base,1 if n<first else (0 if n>last else 1-(n-first)/(last-first))])
    result=dict(locale=locale,frames=len(times),dimensions=[1920,1080],source=metadata['source'],
        master=master.relative_to(ROOT).as_posix(),preview=preview.relative_to(ROOT).as_posix(),
        preview_sha256=hashlib.file_digest(preview.open('rb'),'sha256').hexdigest(),
        overlap_frames_inclusive=[first,last],max_native_pts_deviation_s=drift,
        native_audio_pcm_identical=True,audio_packet_count=len(a),max_audio_pts_deviation_s=audio_drift,
        audio_master='Vorbis stream copy',audio_preview='AAC192k',interpolation=False,
        framing='native Polish center zoom 4/3' if locale=='pl_PL' else 'native pillarboxed 4:3',
        user_validation='pending',installed=False,release_integration=False)
    save(result_path,result);print(f'{locale}: ready, native audio/PTS verified',flush=True)
    return result


if __name__=='__main__':
    RUN.mkdir(parents=True,exist_ok=True)
    results=[]
    for locale in ['default','de_DE','it_IT','pl_PL']:
        results.append(assemble(locale))
        save(RUN/'assembly.json',dict(status='review-ready' if len(results)==4 else 'assembling',results=results))
