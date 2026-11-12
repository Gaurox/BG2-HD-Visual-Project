"""Encode accepted POCKETZZ preview for the game; no new AI inference."""
from produce import ROOT, RECIPE, FINAL, tools
import json
import re
import subprocess
import numpy as np

report = json.loads((FINAL/'verification.json').read_text())
preview = ROOT/report['output']
assert tools.sha(preview) == report['sha256']
runtime = FINAL/'pocketzz.wbm'
command = [tools.FF,'-hide_banner','-nostdin','-n','-threads','2','-i',str(preview),
    '-map','0:v:0','-map','0:a:0','-map_metadata','-1','-c:v','libvpx','-crf','4',
    '-b:v','30M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2',
    '-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:1000000',
    '-c:a','libvorbis','-q:a','6','-f','webm',str(runtime)]
tools.save(RECIPE/'metadata/runtime-command.json',command)
if not runtime.exists():
    with (FINAL/'runtime-encode.log').open('wb') as log:
        subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
p = tools.probe(runtime)
v = next(s for s in p['streams'] if s['codec_type']=='video')
a = next(s for s in p['streams'] if s['codec_type']=='audio')
assert (v['codec_name'],v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']),a['codec_name']) == ('vp8',1920,1080,'30/1',180,'vorbis')
ts = tools.frames(runtime)
assert 0 <= ts[0] <= .015  # WebM shifts negative Vorbis encoder priming to zero.
assert np.max(np.abs(ts-ts[0]-np.arange(180)/30)) < .0011
graph = '[0:v]settb=AVTB,setpts=N/(30*TB)[a];[1:v]settb=AVTB,setpts=N/(30*TB)[b];[a][b]ssim=shortest=1[v]'
check = subprocess.run([tools.FF,'-hide_banner','-nostdin','-threads','2','-i',str(preview),
    '-threads','2','-i',str(runtime),'-filter_complex_threads','1','-filter_complex',graph,
    '-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
(FINAL/'ssim.log').write_text(check.stderr,encoding='utf-8')
ssim = float(re.search(r'All:([0-9.]+)',check.stderr)[1])
assert ssim > .99
result = dict(state='runtime-ready',asset_key='movie:default:POCKETZZ',dimensions=[1920,1080],
    fps='30/1',frames=180,duration_s=6,ssim_all=ssim,full_frame_decode=True,
    webm_video_start_s=float(ts[0]),webm_mux_offset_reason='Vorbis encoder priming; constant container shift',
    interpolation_verification=report,probe=p,
    audio='selected six-second preview AAC; copied for preview, transcoded Vorbis q6 for runtime',
    target='config://bg2ee_game_root/movies/pocketzz.wbm',
    files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=tools.sha(path),bytes=path.stat().st_size)
        for role,path in [('preview',preview),('game_ready',runtime)]},
    visual_qa='accepted-user',runtime_ingame_qa='pending-user',installed=False,release_integration=False)
tools.save(FINAL/'runtime-verification.json',result)
tools.save(RECIPE/'metadata/manifest.json',result)
tools.save(ROOT/'video/index/pocketzz-finals30-20261112-v1.json',result)
print('RUNTIME_READY SSIM',ssim,flush=True)
