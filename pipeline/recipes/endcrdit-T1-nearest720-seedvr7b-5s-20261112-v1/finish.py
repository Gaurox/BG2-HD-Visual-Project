from prepare import *
from PIL import Image,ImageDraw,ImageFont
def main():
 raw=list((RUN/'downloads').rglob('*.mov'));assert len(raw)==1
 p=probe(raw[0]);v=p['streams'][0];assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(1920,1080,'15/1',75)
 dest=RUN/'ENDCRDIT-T1-nearest720-SeedVR7B-1080p15-5s.mp4'
 cmd=[FF,'-v','error','-nostdin','-n','-threads','4','-i',raw[0],'-i',BASE,'-map','0:v','-map','1:a','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-pix_fmt','yuv420p','-fps_mode','passthrough','-c:a','copy','-movflags','+faststart',dest]
 if not dest.exists():subprocess.run(list(map(str,cmd)),check=True)
 p=probe(dest);v=p['streams'][0];assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(1920,1080,'15/1',75)
 def audio(path):return subprocess.check_output([str(FF),'-v','error','-i',str(path),'-map','0:a','-c','copy','-f','hash','-hash','sha256','-'])
 assert audio(dest)==audio(BASE)
 for name,path in [('T1',BASE),('SeedVR7B',dest)]:
  for sec in (2,4):
   image=RUN/f'{name}-{sec}s.png'
   if not image.exists():subprocess.run(list(map(str,[FF,'-v','error','-nostdin','-n','-ss',sec,'-i',path,'-frames:v','1',image])),check=True)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
 comparison=Image.new('RGB',(1800,470),'#202020');draw=ImageDraw.Draw(comparison)
 for i,name in enumerate(['T1','SeedVR7B']):
  comparison.paste(Image.open(RUN/f'{name}-4s.png').crop((550,650,1450,1080)),(900*i,40));draw.text((900*i+10,5),name,font=font,fill='white')
 comparison.save(RUN/'T1-vs-SeedVR7B-text-4s.png')
 result=dict(state='review-ready',base=BASE.relative_to(ROOT).as_posix(),base_sha256=sha(BASE),raw=raw[0].relative_to(ROOT).as_posix(),raw_sha256=sha(raw[0]),preview=dest.relative_to(ROOT).as_posix(),preview_sha256=sha(dest),command=list(map(str,cmd)),probe=p,frames=75,fps='15/1',interpolation=False,audio_encoded_identical_to_T1=True,user_visual_qa='pending',full_film_processed=False,installed=False,release_integration=False)
 save(RECIPE/'metadata/result.json',result);save(RUN/'result.json',result);print('SEEDVR7B_REVIEW_READY',dest,flush=True)
if __name__=='__main__':main()
