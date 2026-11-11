"""Apollo8 15->30fps review of assembled default INTRO15F; audio packet copy."""
import hashlib
import argparse
import math
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
RUN=ROOT/'video/intro15f/runs/intro15f-default-apollo30-20261111-v1'
SOURCE=ROOT/'video/assembly/intro15f-locales-seedvr-1080-20261111-v1/default/INTRO15F-default-SeedVR2-1080-audio.mp4'
FINAL=RUN/'INTRO15F-default-SeedVR2-Apollo8-1080p30-audio.mp4'
ENC=shutil.which('ffmpeg');PROBE=shutil.which('ffprobe')
TOPAZ=get_path('topaz_video_ffmpeg',required=True);MODELS=get_path('topaz_video_models',required=True)
ENV=os.environ.copy();ENV.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));ENV['PATH']=str(TOPAZ.parent)+os.pathsep+ENV.get('PATH','')


def call(args):
    p=subprocess.run([str(a) for a in args],capture_output=True,check=True)
    return p.stdout


def probe(path):
    return json.loads(call([PROBE,'-v','error','-count_frames','-show_streams','-show_format','-of','json',path]))


def main():
    global RUN,SOURCE,FINAL
    parser=argparse.ArgumentParser();parser.add_argument('--locale',choices=['default','de_DE','it_IT','pl_PL'],default='default');args=parser.parse_args()
    locale=args.locale
    if locale!='default':
        RUN=ROOT/f'video/intro15f/runs/intro15f-{locale}-apollo30-20261111-v1'
        SOURCE=ROOT/f'video/assembly/intro15f-locales-seedvr-1080-20261111-v1/{locale}/INTRO15F-{locale}-SeedVR2-1080-audio.mp4'
        FINAL=RUN/f'INTRO15F-{locale}-SeedVR2-Apollo8-1080p30-audio.mp4'
    RUN.mkdir(parents=True,exist_ok=False)
    p=probe(SOURCE);v=next(s for s in p['streams'] if s['codec_type']=='video')
    native_count=2572 if locale=='pl_PL' else 2574
    assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,native_count)
    origin=float(v['start_time']);count=5148
    timing=f'settb=1/1000000,setpts=(N/30+{origin})/TB'
    if locale=='pl_PL':
        timeline=json.loads((ROOT/'video/research/intro-locales-analysis-20261110-v1/INTRO15F-pl_PL.native-frame-times.json').read_text())['frames']
        times=[float(x['best_effort_timestamp_time']) for x in timeline]
        stamps=[]
        for i,t in enumerate(times):
            stamps.append(round(t*1000000))
            stamps.append(round(((t+times[i+1])/2 if i+1<len(times) else t+1/30)*1000000))
        def tree(lo,hi):
            if hi-lo==1:return str(stamps[lo])
            mid=(lo+hi)//2
            return f'if(lt(N\\,{mid})\\,{tree(lo,mid)}\\,{tree(mid,hi)})'
        count=math.ceil((times[-1]+1/15)*30)
        timing='settb=1/1000000,setpts='+tree(0,len(stamps))+',fps=fps=30:start_time=0:round=near,tpad=stop_mode=clone:stop_duration=0.033333333'
        (RUN/'native-anchor-timeline.json').write_text(json.dumps(dict(native_pts_s=times,apollo_pts_us=stamps,output_frames=count)))
    duration=count/30
    report=dict(state='rendering',source=SOURCE.relative_to(ROOT).as_posix(),
        source_sha256=hashlib.file_digest(SOURCE.open('rb'),'sha256').hexdigest(),
        output=FINAL.relative_to(ROOT).as_posix(),model='apo-8',fps=30,slowmo=1,
        source_video_origin_s=origin,expected_frames=count,expected_duration_s=duration,locale=locale,
        user_validation='pending',installed=False,release_integration=False)
    def save(): (RUN/'production.json').write_text(json.dumps(report,indent=2)+'\n')
    topaz=[str(TOPAZ),'-hide_banner','-nostdin','-n','-threads','8','-i',str(SOURCE),
        '-map','0:v:0','-an','-vf',
        'setpts=N/(15*TB),format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le',
        '-c:v','rawvideo','-pix_fmt','gbrp16le','-fps_mode','passthrough','-f','rawvideo','pipe:1']
    if locale=='pl_PL':
        at=topaz.index('-vf')+1
        topaz[at]=topaz[at].replace('setpts=N/(15*TB),','setpts=N/(15*TB),fps=15,',1)
    encode=[ENC,'-hide_banner','-nostdin','-n','-f','rawvideo','-pixel_format','gbrp16le',
        '-video_size','1920x1080','-framerate','30','-i','pipe:0','-i',str(SOURCE),
        '-map','0:v:0','-map','1:a:0','-vf',
        f'tpad=stop_mode=clone:stop_duration=0.033333333,{timing},trim=end_frame={count},scale=in_range=pc:out_range=tv:out_color_matrix=bt601,format=yuv420p',
        '-c:v','libx264','-crf','14','-preset','slow','-threads','4','-fps_mode','passthrough',
        '-enc_time_base','1:1000000','-video_track_timescale','1000000','-color_range','tv',
        '-c:a','copy','-avoid_negative_ts','disabled','-movflags','+faststart',str(FINAL)]
    if locale=='pl_PL':
        # Native timestamp tree exceeds Windows command-line length.
        at=encode.index('-vf');script=RUN/'native-pts.filter'
        script.write_text(encode[at+1]);encode[at:at+2]=['-filter_script:v',str(script)]
    report['commands']=[topaz,encode];save()
    with (RUN/'apollo30.log').open('wb') as a,(RUN/'encode30.log').open('wb') as b:
        producer=subprocess.Popen(topaz,stdout=subprocess.PIPE,stderr=a,env=ENV)
        consumer=subprocess.Popen(encode,stdin=producer.stdout,stdout=b,stderr=b)
        producer.stdout.close()
        cr=consumer.wait()
        if cr and producer.poll() is None:producer.terminate()
        pr=producer.wait()
    report['exit_codes']=[pr,cr];save();assert pr==cr==0,report['exit_codes']
    if locale=='pl_PL':
        import re
        generated=int(re.findall(r'frame=\s*(\d+)',(RUN/'apollo30.log').read_text(errors='replace'))[-1])
        assert generated==2*native_count-1,generated
        report['apollo_generated_frames']=generated
    q=probe(FINAL);w=next(s for s in q['streams'] if s['codec_type']=='video')
    assert (w['width'],w['height'],int(w['nb_read_frames']))==(1920,1080,count),w
    assert abs(float(w['duration'])-duration)<.001
    assert abs(float(w['start_time'])-origin)<.001
    def audio(path):
        h=call([ENC,'-v','error','-i',path,'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
        pts=json.loads(call([PROBE,'-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time','-of','json',path]))['packets']
        return h,[float(x['pts_time']) for x in pts]
    a,b=audio(SOURCE),audio(FINAL);assert a[0]==b[0] and len(a[1])==len(b[1])
    drift=max(abs(x-y) for x,y in zip(a[1],b[1]));assert drift<.000002
    def samples(path,start,end):
        data=call([ENC,'-v','error','-i',path,'-vf',f"select='between(n,{start},{end})',scale=320:180:flags=area,format=gray",'-fps_mode','passthrough','-f','rawvideo','-'])
        return np.frombuffer(data,np.uint8).reshape(-1,180,320).astype(np.float32)
    s=samples(SOURCE,600,630);o=samples(FINAL,1200,1260)
    left=np.abs(o[1::2]-o[:-1:2]).mean(axis=(1,2));right=np.abs(o[1::2]-o[2::2]).mean(axis=(1,2))
    novel=int(((left>.01)&(right>.01)).sum());assert novel>0
    for sec in [8,18.5,40,100,160]:
        call([ENC,'-v','error','-nostdin','-n','-ss',str(sec),'-i',FINAL,'-frames:v','1',RUN/f'check-{sec:g}s.png'])
    report.update(state='review-ready',output_probe=q,source_probe=p,
        output_sha256=hashlib.file_digest(FINAL.open('rb'),'sha256').hexdigest(),
        audio_packets_identical=True,max_audio_pts_deviation_s=drift,
        interpolation_check=dict(sample='40-42s',novel_odd_frames=novel,tested_odd_frames=30,
            even_anchor_luma_mae=float(np.abs(s-o[::2]).mean())),
        endpoint='Apollo interpolates 2N-1 images; final hold padded to native video duration',
        timeline='Native Polish anchors/midpoints restored then sampled at 30fps' if locale=='pl_PL' else 'Native origin, uniform 30fps')
    save();print(json.dumps({k:report[k] for k in ['state','output','max_audio_pts_deviation_s','interpolation_check']}),flush=True)


if __name__=='__main__':main()
