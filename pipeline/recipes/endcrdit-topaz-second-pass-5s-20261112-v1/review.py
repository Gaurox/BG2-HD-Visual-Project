"""CPU-only conservative blends and labeled second-pass comparison."""
from produce import *
import shutil
from PIL import Image,ImageDraw,ImageFont
def main():
 state=json.loads((RUN/'production.json').read_text(encoding='utf-8'));assert state['state']=='completed'
 control=RUN/'B0-T1-accepted-1080p15-5s.mp4'
 if not control.exists():shutil.copy2(BASE,control)
 assert sha(control)==state['base']['sha256'];frame('B0',control)
 for tid,parent,fraction in [('P10','P4',.5),('P11','P1',.25)]:
  if tid in state['tests'] or state['tests'][parent]['state']!='ready':continue
  dest=RUN/f'{tid}-ENDCRDIT-T1-second-pass-1080p15-5s.mp4'
  cmd=[FF,'-v','error','-nostdin','-n','-threads','2','-i',BASE,'-i',ROOT/state['tests'][parent]['path'],'-filter_complex_threads','1','-filter_complex',f'[0:v][1:v]blend=all_expr=A*{1-fraction}+B*{fraction},format=yuv420p[v]','-map','[v]','-map','0:a','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-c:a','copy','-fps_mode','passthrough','-color_range','tv','-colorspace','bt709','-movflags','+faststart',dest]
  seconds=run(cmd,RUN/f'{tid}-blend.log');info=dict(state='ready',label=f'{parent} {fraction:.0%} + T1 {1-fraction:.0%}',gpu=False,command=list(map(str,cmd)),seconds=seconds,path=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),probe=verify(dest));state['tests'][tid]=info;frame(tid,dest)
 ready=[('B0',dict(label='T1 valide - une seule passe',path=control.relative_to(ROOT).as_posix()))]+[(k,v) for k,v in state['tests'].items() if v['state']=='ready']
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);contact=Image.new('RGB',(1800,((len(ready)+3)//4)*260),'#202020');draw=ImageDraw.Draw(contact)
 for i,(tid,info) in enumerate(ready):
  im=Image.open(RUN/f'{tid}-4s.png').crop((550,650,1450,1080)).resize((450,215),Image.Resampling.LANCZOS);x=i%4*450;y=i//4*260;contact.paste(im,(x,y+45));draw.text((x+6,y+5),tid+' '+info['label'][:30],font=font,fill='white')
 contact.save(RUN/'second-pass-text-crops-4s.jpg',quality=95)
 (RUN/'concat.txt').write_text(''.join("file '"+Path(v['path']).name+"'\n" for _,v in ready),encoding='utf-8')
 ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Arial,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,2,0,8,20,20,12,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
 def stamp(s):return f'0:{s//60:02d}:{s%60:02d}.00'
 for i,(tid,v) in enumerate(ready):ass+=f'Dialogue: 0,{stamp(i*5)},{stamp((i+1)*5)},Default,,0,0,0,,{tid} — {v["label"]} — 1080p / 15 FPS\n'
 (RUN/'labels.ass').write_text(ass,encoding='utf-8-sig')
 reel=RUN/'ENDCRDIT-T1-second-passes-comparison-1080p15.mp4'
 if not reel.exists():run([FF,'-v','error','-nostdin','-n','-f','concat','-safe','0','-i','concat.txt','-vf','subtitles=labels.ass','-c:v','libx264','-crf','14','-preset','veryfast','-threads','8','-c:a','aac','-b:a','192k','-fps_mode','passthrough','-movflags','+faststart',reel.name],RUN/'reel.log',RUN)
 p=probe(reel);v=p['streams'][0];assert int(v['nb_read_frames'])==75*len(ready) and v['r_frame_rate']=='15/1'
 state['comparison']=dict(path=reel.relative_to(ROOT).as_posix(),sha256=sha(reel),frames=75*len(ready),order=[k for k,_ in ready],seconds_per_test=5)
 save(RUN/'production.json',state);save(RECIPE/'metadata/production.json',state);print('REVIEW_READY',len(ready),'clips',flush=True)
if __name__=='__main__':main()
