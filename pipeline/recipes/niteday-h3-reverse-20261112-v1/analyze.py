from pathlib import Path
import subprocess,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'video/research/niteday-reverse-analysis-20261112-v1'
FILES=dict(niteday=ROOT/'video/niteday/niteday.wbm',daynite=ROOT/'video/daynite/daynite.wbm',
    generated=ROOT/'video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4')
def run(args):return subprocess.check_output([str(x) for x in args])
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def rgb(p):return np.frombuffer(run(['ffmpeg','-v','error','-hwaccel','none','-threads','2','-i',p,'-an','-vf','scale=160:90:flags=area,format=rgb24',
    '-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(-1,90,160,3).astype(np.float32)
def probe(p):return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p]))
def audio(p):return run(['ffmpeg','-v','error','-hwaccel','none','-i',p,'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
if __name__=='__main__':
    frames={k:rgb(p) for k,p in FILES.items()}
    means={k:v.mean((1,2,3)) for k,v in frames.items()}
    assert len(frames['niteday'])==len(frames['daynite'])==150 and len(frames['generated'])==300
    delta=np.abs(frames['niteday']-frames['daynite'][::-1]).mean((1,2,3))
    report=dict(files={k:dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),probe=probe(p),audio_packet_hash=audio(p),
        mean_rgb_per_frame=means[k].tolist()) for k,p in FILES.items()},native_reverse=dict(mean_absolute_rgb_error=float(delta.mean()),
        per_frame_error=delta.tolist(),correlation=float(np.corrcoef(means['niteday'],means['daynite'][::-1])[0,1])),
        generated_black_frames=[int(i) for i,v in enumerate(frames['generated'].max((1,2,3))) if v<=1],gpu_used=False)
    (OUT/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    for k,m in means.items():
        rate=30 if k=='generated' else 15
        print(k,'frames',len(m),'luma each 0.5sec',[(round(i/rate,2),round(float(m[i]),3)) for i in range(0,len(m),rate//2)])
    print('REVERSE_NATIVE',report['native_reverse']['mean_absolute_rgb_error'],report['native_reverse']['correlation'])
    print('BLACK_GENERATED',report['generated_black_frames'])
