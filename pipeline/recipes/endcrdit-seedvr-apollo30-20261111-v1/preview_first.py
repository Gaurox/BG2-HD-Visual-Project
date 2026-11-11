"""Publish the first finalized 22-second portion while full inference continues."""
from pathlib import Path
import hashlib,json,subprocess,time
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/endcrdit/runs/endcrdit-seedvr-apollo30-20261111-v1'
OUT=ROOT/'video/previews/endcrdit-text-20261111-v1'
SOURCE=ROOT/'video/endcrdit/endcrdit.wbm'
PART=RUN/'portions/ENDCRDIT-common-part-01.mp4'

def call(args):
    p=subprocess.run([str(x) for x in args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p.stdout

def main():
    deadline=time.monotonic()+1800
    while True:
        assert time.monotonic()<deadline,'First portion timed out'
        log=RUN/'seedvr-stream.log'
        if log.exists() and 'BG2_PORTION_SAVED 1 ' in log.read_text(encoding='utf-8',errors='replace'):break
        time.sleep(3)
    OUT.mkdir(parents=True,exist_ok=True)
    original=OUT/'ENDCRDIT-source-0-22s-1080-lanczos-audio.mp4'
    processed=OUT/'ENDCRDIT-SeedVR2-0-22s-1080p15-audio.mp4'
    assert not original.exists() and not processed.exists()
    call(['ffmpeg','-v','error','-nostdin','-n','-threads','2','-i',SOURCE,'-map','0:v:0','-map','0:a:0',
        '-t','22','-vf','trim=end_frame=330,setpts=PTS-STARTPTS,scale=1920:1080:flags=lanczos',
        '-c:v','libx264','-crf','12','-preset','fast','-threads','4','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-movflags','+faststart',original])
    call(['ffmpeg','-v','error','-nostdin','-n','-i',PART,'-i',original,'-map','0:v:0','-map','1:a:0',
        '-c','copy','-movflags','+faststart',processed])
    sheet=Image.new('RGB',(1440,682),(22,22,22));draw=ImageDraw.Draw(sheet)
    for col,(label,path) in enumerate([('Source agrandie sans IA',original),('SeedVR FP16 LAB',processed)]):
        raw=call(['ffmpeg','-v','error','-threads','2','-ss','12','-i',path,'-vf',
            'crop=720:660:600:200','-frames:v','1','-threads','1','-pix_fmt','rgb24','-f','rawvideo','-'])
        sheet.paste(Image.frombytes('RGB',(720,660),raw),(720*col,22))
        draw.text((720*col+4,4),f'{label} - texte 12s, crop 1:1',fill='white')
    sheet.save(OUT/'text-12s-source-vs-seedvr.jpg',quality=97)
    for path in (original,processed):
        p=json.loads(call(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_streams','-of','json',path]))
        v=p['streams'][0];assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,330)
    report=dict(state='first-portion-review-ready',source_frames=[0,329],seconds=[0,22],fps=15,
        processed=processed.relative_to(ROOT).as_posix(),reference=original.relative_to(ROOT).as_posix(),
        stage='SeedVR spatial only; full SeedVR then Apollo30 continues independently',
        user_text_validation='pending',full_processing_continues=True)
    (OUT/'first-portion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
