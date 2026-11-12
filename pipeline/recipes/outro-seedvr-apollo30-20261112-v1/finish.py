"""Verify ComfyUI OUTRO portions, assemble once, interpolate once; native silent contract."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,re,shutil,subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
RECIPE=Path(__file__).resolve().parent
RUN=ROOT/'video/outro/runs/outro-seedvr-apollo30-20261112-v1'
FINAL=ROOT/'video/final/outro-seedvr-apollo30-20261112-v1/OUTRO/default'
SOURCE=ROOT/'video/outro/outro.wbm'

def call(args):
    p=subprocess.run([str(x) for x in args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace')[-10000:])
    return p.stdout

def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

spec=importlib.util.spec_from_file_location('ending_tools',ROOT/'pipeline/recipes/endings-shared-30fps-20261111-v1/produce.py')
tools=importlib.util.module_from_spec(spec);spec.loader.exec_module(tools)
tools.run_dir=lambda film:RUN

def part(number):
    production=json.loads((RUN/'production.json').read_text());entry=production['parts'][number-1]
    entry['prompt_id']=json.loads((RUN/'jobs.json').read_text())[str(number)]
    ready=RUN/'portions'/f'part-{number:02d}.json'
    assert not ready.exists(),'Portion already verified'
    raw=list((RUN/'downloads'/f'part-{number:02d}').rglob('*.mov'));assert len(raw)==1,raw
    raw=raw[0];p=tools.probe(raw);v=next(s for s in p['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,entry['input_frames'])
    folder=RUN/'portions';folder.mkdir(exist_ok=True);output=folder/f'OUTRO-part-{number:02d}-1080p15.mp4'
    command=['ffmpeg','-v','error','-nostdin','-n','-threads','2','-i',str(raw),'-map','0:v:0','-an',
        '-vf',f"trim=start_frame={entry['discard_context_frames']},setpts=N/(15*TB)",
        '-c:v','libx264','-crf','12','-preset','medium','-threads','4','-pix_fmt','yuv420p',
        '-fps_mode','passthrough','-enc_time_base','1:1000000','-video_track_timescale','1000000','-movflags','+faststart',str(output)]
    save(folder/f'encode-{number:02d}.json',command)
    if not output.exists():call(command)
    timestamps=tools.frames(output);assert len(timestamps)==entry['kept_frames']
    assert np.max(np.abs(timestamps-np.arange(len(timestamps))/15))<.000002
    result=dict(entry)
    result.update(state='verified',raw=raw.relative_to(ROOT).as_posix(),
        raw_sha256=tools.sha(raw),output=output.relative_to(ROOT).as_posix(),sha256=tools.sha(output))
    save(ready,result);production['parts'][number-1]=result;save(RUN/'production.json',production)
    print('PART_READY',number,len(timestamps),flush=True)

def gray(path,first=None,last=None):
    select='' if first is None else f'select=between(n\\,{first}\\,{last}),'
    return np.frombuffer(call(['ffmpeg','-v','error','-threads','2','-i',path,'-an','-vf',
        select+'scale=160:90:flags=area,format=gray','-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(-1,90,160).astype(np.float32)

def final():
    assert not (RUN/'verification.json').exists(),'Final verification immutable'
    production=json.loads((RUN/'production.json').read_text());assert all(e['state']=='verified' for e in production['parts'])
    listing=RUN/'portions-concat.txt'
    listing.write_text(''.join(f"file '{(ROOT/e['output']).as_posix()}'\n" for e in production['parts']),encoding='utf-8')
    seed=RUN/'OUTRO-SeedVR2-3B-FP16-LAB-1080p15.mp4'
    if not seed.exists():
        call(['ffmpeg','-v','error','-nostdin','-n','-f','concat','-safe','0','-i',listing,'-map','0:v:0','-an','-c:v','copy','-movflags','+faststart',seed])
    ts=tools.frames(seed);assert len(ts)==1225 and np.max(np.abs(ts-np.arange(1225)/15))<.000002
    save(RUN/'run.json',dict(status='inference-completed',film='OUTRO',frames=1225,output=seed.name,
        source='video/outro/outro.wbm',source_sha256=production['source_sha256'],api_portions=4,
        context_frames=33,audio=False,user_visual_qa='pending'))
    master=tools.interpolate('OUTRO');selected=ROOT/master['output'];FINAL.mkdir(parents=True,exist_ok=True)
    preview=FINAL/'OUTRO-default-1080p30.mp4';mkv=FINAL/'OUTRO-default-1080p30-master.mkv';runtime=FINAL/'outro.wbm'
    if not preview.exists():shutil.copy2(selected,preview)
    if not mkv.exists():call(['ffmpeg','-v','error','-nostdin','-n','-i',preview,'-map','0:v:0','-an','-c:v','copy',mkv])
    command=['ffmpeg','-hide_banner','-nostdin','-n','-threads','2','-i',str(preview),'-map','0:v:0','-an',
        '-map_metadata','-1','-c:v','libvpx','-crf','4','-b:v','30M','-qmin','0','-qmax','12',
        '-deadline','good','-cpu-used','2','-threads','2','-pix_fmt','yuv420p','-fps_mode','passthrough',
        '-enc_time_base','1:1000000','-f','webm',str(runtime)]
    save(FINAL/'encoding-command.json',command)
    if not runtime.exists():
        with (FINAL/'encode.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    probes={}
    for label,path in [('preview',preview),('master',mkv),('runtime',runtime)]:
        p=tools.probe(path);assert len(p['streams'])==1 and p['streams'][0]['codec_type']=='video'
        v=p['streams'][0];assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,2450,'30/1')
        if label=='runtime':assert v['codec_name']=='vp8'
        stamps=tools.frames(path);assert np.max(np.abs(stamps-np.arange(2450)/30))<=.0011
        probes[label]=p
    graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
    check=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-threads','2','-i',str(preview),'-threads','2','-i',str(runtime),
        '-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
    (FINAL/'ssim-sampled.log').write_text(check.stderr,encoding='utf-8')
    ssim=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert ssim>.99,ssim
    native,spatial=gray(SOURCE),gray(seed);assert len(native)==len(spatial)==1225
    joins=[dict(frame=n,native_adjacent_mae=float(np.abs(native[n]-native[n-1]).mean()),
        seedvr_adjacent_mae=float(np.abs(spatial[n]-spatial[n-1]).mean())) for n in (330,660,990)]
    s=gray(seed,600,630);o=gray(preview,1200,1260)
    left=np.abs(o[1::2]-o[:-1:2]).mean((1,2));right=np.abs(o[1::2]-o[2::2]).mean((1,2))
    novel=int(((left>.01)&(right>.01)).sum());assert novel>0
    for sec in (5,21.9,22.1,43.9,44.1,65.9,66.1,75):
        call(['ffmpeg','-v','error','-nostdin','-n','-ss',sec,'-i',runtime,'-frames:v','1',FINAL/f'check-{sec:g}s.png'])
    result=dict(schema='outro-final-v1',state='runtime-ready',created_utc=datetime.now(timezone.utc).isoformat(),
        asset_key='movie:default:OUTRO',source=production['source'],source_sha256=production['source_sha256'],
        dimensions=[1920,1080],fps='30/1',frames=2450,duration_s=2450/30,native_source_frames=1225,
        audio='absent in native source and all results',seedvr_profile=production['profile'],apollo=master,
        files={role:dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=tools.sha(p)) for role,p in [('preview',preview),('master',mkv),('game_ready',runtime)]},
        target='config://bg2ee_game_root/movies/outro.wbm',ssim_sampled_all=ssim,full_frame_decode=True,
        interpolation_check=dict(tested_odd_frames=30,novel_odd_frames=novel),seedvr_joins=joins,
        probes=probes,user_visual_qa='pending',ingame_qa='not-performed',installed=False,release_integration=False)
    save(RUN/'verification.json',result);save(FINAL/'verification.json',result)
    save(RECIPE/'metadata/manifest.json',result);save(ROOT/'video/index/outro-finals30-20261112-v1.json',result)
    production['state']='runtime-ready';save(RUN/'production.json',production)
    save(RECIPE/'metadata/parts.json',production)
    print('OUTRO_FULLHD30_RUNTIME_READY SSIM',ssim,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['part','final']);p.add_argument('--number',type=int);a=p.parse_args()
    if a.action=='part':part(a.number)
    else:final()
