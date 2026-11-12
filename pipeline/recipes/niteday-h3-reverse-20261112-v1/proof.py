"""CPU-only feasibility preview: reuse reversed DAYNITE H3 images, native NITEDAY clock/audio."""
from analyze import ROOT,OUT,FILES,run,sha,probe,audio,rgb
import json,subprocess
import numpy as np

FOLDER=ROOT/'video/previews/niteday-h3-reverse-proof-20261112-v1'
SOURCE=FILES['generated'];NATIVE=FILES['niteday']
assert not (OUT/'proof.json').exists(), 'Completed feasibility proof is immutable'
data=json.loads((OUT/'analysis.json').read_text())
native=np.array(data['files']['niteday']['mean_rgb_per_frame'])
generated=np.array(data['files']['generated']['mean_rgb_per_frame'])
night=float(np.median(native[20:40]));day=float(np.median(native[110:130]))
night_anchor=240;day_anchor=60
# Use the clean, already interpolated day->night transition in reverse.
indices=np.arange(210,89,-1)
values=generated[indices]
progress=np.maximum.accumulate(np.clip((values-values[0])/(values[-1]-values[0]),0,1))
times=np.arange(300)/30
target=np.interp(times,np.arange(150)/15,native)
mapping=[]
for n,t in enumerate(times):
    if t<1:
        src=night_anchor;opacity=float(np.clip(target[n]/night,0,1));phase='native_fade_in'
    elif t<3:
        src=night_anchor;opacity=1.;phase='night_hold'
    elif t<9:
        p=float(np.clip((target[n]-night)/(day-night),0,1))
        src=int(indices[int(np.argmin(np.abs(progress-p)))]);opacity=1.;phase='native_clock_reverse_transition'
    else:
        src=day_anchor;opacity=float(np.clip(target[n]/day,0,1));phase='native_fade_out'
    mapping.append(dict(frame=n,time_s=float(t),daynite_frame=src,opacity=opacity,phase=phase))
assert all(a['daynite_frame']>=b['daynite_frame'] for a,b in zip(mapping[90:269],mapping[91:270]))
FOLDER.mkdir(parents=True,exist_ok=True)
master=FOLDER/'NITEDAY-H3-inverse-1080p30-son-natif.mkv'
preview=FOLDER/'NITEDAY-H3-inverse-1080p30-apercu.mp4'
webm=FOLDER/'NITEDAY-H3-inverse-1080p30-son-natif.webm'
required=sorted(set(e['daynite_frame'] for e in mapping))
if not master.exists():
    select='+'.join(f'eq(n,{n})' for n in required)
    decoded=run(['ffmpeg','-v','error','-hwaccel','none','-threads','2','-i',SOURCE,'-an','-vf',f"select='{select}',format=rgb24",'-threads','1','-fps_mode','passthrough','-f','rawvideo','-'])
    frames=np.frombuffer(decoded,np.uint8).reshape(len(required),1080,1920,3)
    lookup={n:frames[i] for i,n in enumerate(required)}
    command=['ffmpeg','-v','error','-nostdin','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','30','-i','pipe:0',
        '-i',str(NATIVE),'-map','0:v:0','-map','1:a:0','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p',
        '-c:v','libx264','-crf','14','-preset','medium','-threads','4','-c:a','copy','-avoid_negative_ts','disabled',str(master)]
    with (FOLDER/'encode.log').open('wb') as log:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
        try:
            for e in mapping:
                frame=lookup[e['daynite_frame']]
                if e['opacity']<1:frame=np.rint(frame.astype(np.float32)*e['opacity']).clip(0,255).astype(np.uint8)
                proc.stdin.write(frame.tobytes())
        finally:proc.stdin.close()
        assert proc.wait()==0
from duration import set_duration
native_duration=float(probe(NATIVE)['format']['duration'])
set_duration(master,native_duration)
if not webm.exists():
    run(['ffmpeg','-v','error','-nostdin','-n','-hwaccel','none','-threads','2','-copyts','-i',master,'-map','0:v:0','-map','0:a:0',
        '-c:v','libvpx','-crf','4','-b:v','30M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2',
        '-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',webm])
set_duration(webm,native_duration)
p=probe(master);v=next(s for s in p['streams'] if s['codec_type']=='video')
assert v['width']==1920 and v['height']==1080 and v['r_frame_rate']=='30/1'
def times_of(path):
    return [float(f['best_effort_timestamp_time']) for f in json.loads(run(['ffprobe','-v','error','-select_streams','v:0','-show_frames',
        '-show_entries','frame=best_effort_timestamp_time','-of','json',path]))['frames']]
for path in (master,webm):
    ts=times_of(path);assert len(ts)==300 and np.max(np.abs(np.array(ts)-times))<=.0011
assert audio(master)==audio(NATIVE)
def pcm(path):return run(['ffmpeg','-v','error','-hwaccel','none','-i',path,'-map','0:a:0','-c:a','pcm_s16le','-f','hash','-hash','sha256','-']).decode().strip()
assert pcm(master)==pcm(NATIVE)
def packets(path):return json.loads(run(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time,duration_time','-of','json',path]))['packets']
assert packets(master)==packets(NATIVE)
native_duration=float(probe(NATIVE)['format']['duration'])
mp=probe(master)
assert abs(float(mp['format']['duration'])-native_duration)<.0011
assert abs(float(probe(webm)['format']['duration'])-native_duration)<.0011
assert audio(webm)==audio(NATIVE) and pcm(webm)==pcm(NATIVE) and packets(webm)==packets(NATIVE)
result=dict(state='feasibility-preview-only',gpu_used=False,new_ai_inference=False,source=SOURCE.relative_to(ROOT).as_posix(),source_sha256=sha(SOURCE),
    native_source=NATIVE.relative_to(ROOT).as_posix(),native_source_sha256=sha(NATIVE),
    video_frames=300,fps='30/1',video_duration_s=10,native_total_duration_s=native_duration,
    declared_duration_preserved=True,native_vorbis_last_packet_tail_ms=23,native_audio_encoded_identical=True,native_audio_pcm_identical=True,native_audio_packets_and_pts_identical=True,
    night_luma_reference=night,day_luma_reference=day,used_generated_frames=required,
    core_generated_indices_nonincreasing=True,fade_strategy='native NITEDAY measured opacity; hold night/day anchors; reverse existing H3 transition; no fresh inference',
    files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),probe=probe(path)) for role,path in [('master',master),('preview',webm)]},
    mapping=mapping,installed=False,user_visual_qa='pending')
(OUT/'proof.json').write_text(json.dumps(result,indent=2)+'\n')
print('PROOF_READY exact native duration',native_duration,'300 frames; original audio copied; GPU unused',flush=True)
