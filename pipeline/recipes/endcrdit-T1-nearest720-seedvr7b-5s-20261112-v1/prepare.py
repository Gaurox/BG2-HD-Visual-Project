from pathlib import Path
import json,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[3];RECIPE=Path(__file__).resolve().parent
RUN=ROOT/'video/endcrdit/runs/endcrdit-T1-nearest720-seedvr7b-5s-20261112-v1'
BASE=ROOT/'video/endcrdit/runs/endcrdit-topaz-tests-5s-20261112-v1/T1-ENDCRDIT-1080p15-5s.mp4'
FF=Path('C:/ffmpeg/bin/ffmpeg.exe');PROBE=FF.with_name('ffprobe.exe')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def probe(p):return json.loads(subprocess.check_output([str(PROBE),'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(p)]))
def main():
 RUN.mkdir(parents=True,exist_ok=False)
 previous=json.loads((ROOT/'video/endcrdit/runs/endcrdit-topaz-tests-5s-20261112-v1/production.json').read_text(encoding='utf-8'))['tests']['T1'];assert sha(BASE)==previous['sha256']
 inp=RUN/'BG2-ENDCRDIT-T1-nearest720-7B-20261112-v1.mkv'
 cmd=[FF,'-v','error','-nostdin','-n','-i',BASE,'-map','0:v','-an','-vf','scale=1280:720:flags=neighbor,format=yuv420p','-c:v','ffv1','-level','3','-fps_mode','passthrough',inp]
 subprocess.run(list(map(str,cmd)),check=True)
 # Verify every nearest-resized frame byte-for-byte against the lossless input.
 def md5(args):return subprocess.check_output([str(FF),'-v','error','-i',str(args[0]),*args[1:],'-map','0:v','-an','-f','framemd5','-'])
 expected=md5([BASE,'-vf','scale=1280:720:flags=neighbor,format=yuv420p']);actual=md5([inp]);assert expected==actual
 p=probe(inp);v=p['streams'][0];assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(1280,720,'15/1',75)
 w=json.loads((ROOT/'pipeline/recipes/logo-seedvr-nativefps-20261112-v1/metadata/part-01.api.json').read_text(encoding='utf-8'))
 w['14']['inputs'].update(model='seedvr2_ema_7b_fp16.safetensors',blocks_to_swap=36)
 w['10']['inputs'].update(batch_size=17)
 w['21']['inputs']['file']=inp.name
 w['24']['inputs']['fps']=15
 w['23']['inputs']['filename_prefix']='BG2_video_upscale/endcrdit-T1-nearest720-seedvr7b-5s-20261112-v1/ENDCRDIT-T1-nearest720-SeedVR7B-LAB'
 save(RECIPE/'workflow.api.json',w)
 save(RECIPE/'metadata/preparation.json',dict(base=BASE.relative_to(ROOT).as_posix(),base_sha256=sha(BASE),input=inp.relative_to(ROOT).as_posix(),input_sha256=sha(inp),nearest_frames_md5_identical=True,command=list(map(str,cmd)),input_probe=p,model='seedvr2_ema_7b_fp16.safetensors',output_resolution=[1920,1080],fps='15/1',frames=75,interpolation=False,user_qa='pending'))
 print('PREPARED',inp,flush=True)
if __name__=='__main__':main()
