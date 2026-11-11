"""Prepare INTRO shared body and run installed SeedVR CLI in bounded-memory streaming mode."""
import csv
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/experiments/intro-common-seedvr3b-stream-1080-20261111-v1'
AUDIT=ROOT/'video/research/intro-locales-analysis-20261110-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
PYTHON=get_path('comfyui_python',required=True)
COMFY=get_path('comfyui_root',required=True)
MODELS=get_path('seedvr_models',required=True)
CLI=COMFY/'custom_nodes/seedvr2_videoupscaler/inference_cli.py'


def save(value):
    (RUN/'run.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def call(args):
    p=subprocess.run([str(a) for a in args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p.stdout.decode('utf-8')


def main():
    global RUN
    parser=argparse.ArgumentParser();parser.add_argument('--film',choices=['INTRO','INTRO15F'],default='INTRO');options=parser.parse_args()
    film=options.film
    if film=='INTRO15F':RUN=ROOT/'video/experiments/intro15f-common-seedvr3b-stream-1080-20261111-v1'
    RUN.mkdir(parents=True,exist_ok=False)
    src=ROOT/f'video/{film.lower()}/{film.lower()}.wbm'
    times=json.loads((AUDIT/f'{film}-default.native-frame-times.json').read_text())['frames']
    first=next(i for i,f in enumerate(times) if float(f['best_effort_timestamp_time'])>=(18 if film=='INTRO15F' else 7))
    count=len(times)-first
    source=RUN/f'{film}-common-native-input.mkv'
    call(['ffmpeg','-v','error','-nostdin','-n','-threads','2','-i',src,'-map','0:v:0','-an',
        '-vf',f'trim=start_frame={first},setpts=PTS-STARTPTS','-c:v','ffv1','-level','3',
        '-pix_fmt','yuv420p','-threads','2','-fps_mode','passthrough',source])
    h=call(['ffmpeg','-v','error','-threads','2','-i',source,'-map','0:v:0','-an','-c:v','rawvideo',
        '-pix_fmt','yuv420p','-threads','1','-fps_mode','passthrough','-f','framehash','-hash','sha256','-'])
    hashes=lambda s:[l.rsplit(',',1)[-1].strip() for l in s.splitlines() if l and not l.startswith('#')]
    native=hashes((AUDIT/f'{film}-default.decoded.sha256').read_text())[first:]
    assert hashes(h)==native
    with (RUN/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['clip_frame_0based','source_frame_0based','source_pts_s','rebased_pts_s','source_yuv420p_sha256'])
        origin=float(times[first]['best_effort_timestamp_time'])
        for i,t in enumerate(times[first:]):w.writerow([i,first+i,t['best_effort_timestamp_time'],f"{float(t['best_effort_timestamp_time'])-origin:.6f}",native[i]])
    output=RUN/f'{film}-common-SeedVR2-3B-FP16-LAB-1080-stream-raw.mp4'
    bootstrap=Path(__file__).with_name('seedvr_cli_bootstrap.py')
    args=[str(PYTHON),'-u',str(bootstrap),str(CLI),str(source),'--output',str(output),'--output_format','mp4',
        '--video_backend','ffmpeg','--model_dir',str(MODELS),
        '--dit_model','seedvr2_ema_3b_fp16.safetensors','--resolution','1080','--max_resolution','0',
        '--batch_size','33','--uniform_batch_size','--chunk_size','330','--temporal_overlap','3',
        '--seed','42','--prepend_frames','0','--input_noise_scale','0','--latent_noise_scale','0',
        '--color_correction','lab','--cuda_device','0','--dit_offload_device','cpu','--vae_offload_device','cpu',
        '--tensor_offload_device','cpu','--blocks_to_swap','32','--vae_encode_tiled','--vae_encode_tile_size','1024',
        '--vae_encode_tile_overlap','128','--vae_decode_tiled','--vae_decode_tile_size','768',
        '--vae_decode_tile_overlap','128','--attention_mode','sdpa','--cache_dit','--cache_vae']
    report=dict(status='running',film=film,started_utc=datetime.now(timezone.utc).isoformat(),source=src.relative_to(ROOT).as_posix(),
        source_first_frame=first,source_frames_end_exclusive=len(times),frames=count,source_first_pts_s=origin,
        source_last_pts_s=float(times[-1]['best_effort_timestamp_time']),input_pixels_native_verified=True,
        command=args,chunk_frames=330,expected_chunks=(count+329)//330,output=output.name,
        audio=False,interpolation=False,second_film_started=film=='INTRO15F',installed=False,
        log='seedvr-stream.log',export_conversion_batch=8,finalized_portions=True)
    save(report)
    env=os.environ.copy();env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8'
    env['PATH']=str(Path(shutil.which('ffmpeg')).parent)+os.pathsep+env.get('PATH','')
    env['PYTHONDONTWRITEBYTECODE']='1'
    print(f'Start streaming: {count} frames, {report["expected_chunks"]} chunks; source begins at frame {first} / {origin:.3f}s',flush=True)
    with (RUN/'seedvr-stream.log').open('wb') as log:
        p=subprocess.Popen(args,cwd=COMFY,env=env,stdout=log,stderr=subprocess.STDOUT)
        report['pid']=p.pid;save(report)
        code=p.wait()
    report.update(status='inference-completed' if code==0 else 'failed',exit_code=code,finished_utc=datetime.now(timezone.utc).isoformat())
    save(report)
    print(f'SeedVR CLI exit={code}',flush=True)
    if code:raise SystemExit(code)


if __name__=='__main__':main()
