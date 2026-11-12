"""CPU review media and two conservative blends; validated clips retained."""
from produce import *
from PIL import Image,ImageDraw,ImageFont
def main():
    state=json.loads((RUN/'production.json').read_text(encoding='utf-8'))
    for tid,parent,amount in [('T12','T1',.25),('T13','T4',.5)]:
        if tid in state['tests']:continue
        dest=RUN/f'{tid}-ENDCRDIT-1080p15-5s.mp4'
        graph=f'[0:v][1:v]blend=all_expr=A*{1-amount}+B*{amount},format=yuv420p[v]'
        cmd=[FF,'-v','error','-nostdin','-n','-threads','2','-i',ROOT/state['tests']['R0']['path'],'-i',ROOT/state['tests'][parent]['path'],'-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-map','0:a','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-c:a','copy','-fps_mode','passthrough','-color_range','tv','-colorspace','bt709','-movflags','+faststart',dest]
        seconds=run(cmd,RUN/f'{tid}-blend.log');p=probe(dest);v=p['streams'][0];assert int(v['nb_read_frames'])==75 and v['r_frame_rate']=='15/1'
        state['tests'][tid]=dict(state='ready',label=f'{parent} {amount:.0%} + original Lanczos {1-amount:.0%}',gpu=False,path=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),seconds=seconds,probe=p,command=list(map(str,cmd)))
        run([FF,'-v','error','-nostdin','-n','-ss','4','-i',dest,'-frames:v','1',RUN/f'{tid}-4s.png'],RUN/f'{tid}-frame.log')
    ready=[(k,v) for k,v in state['tests'].items() if v['state']=='ready']
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    contact=Image.new('RGB',(1800,4*260),'#202020');draw=ImageDraw.Draw(contact)
    for n,(tid,info) in enumerate(ready):
        im=Image.open(RUN/f'{tid}-4s.png').crop((550,650,1450,1080)).resize((450,215),Image.Resampling.LANCZOS)
        x=n%4*450;y=n//4*260;contact.paste(im,(x,y+45));draw.text((x+7,y+4),tid+' '+info['label'][:32],font=font,fill='white')
    contact.save(RUN/'all-text-crops-4s.jpg',quality=95)
    # Sequential, labeled full-frame samples; each interval is precisely five seconds.
    (RUN/'review-concat.txt').write_text(''.join("file '"+Path(v['path']).name+"'\n" for _,v in ready),encoding='utf-8')
    ass='[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Default,Arial,32,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,2,0,8,20,20,12,1\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n'
    def stamp(sec):return f'0:{sec//60:02d}:{sec%60:02d}.00'
    for n,(tid,v) in enumerate(ready):ass+=f'Dialogue: 0,{stamp(n*5)},{stamp((n+1)*5)},Default,,0,0,0,,{tid} — {v["label"]} — 1080p / 15 FPS\n'
    (RUN/'labels.ass').write_text(ass,encoding='utf-8-sig')
    reel=RUN/'ENDCRDIT-14-tests-comparison-1080p15.mp4'
    if not reel.exists():
        cmd=[str(x) for x in [FF,'-v','error','-nostdin','-n','-f','concat','-safe','0','-i','review-concat.txt','-vf','subtitles=labels.ass','-c:v','libx264','-crf','14','-preset','fast','-threads','4','-c:a','aac','-b:a','192k','-fps_mode','passthrough','-movflags','+faststart',reel.name]]
        with (RUN/'reel.log').open('w') as f:subprocess.run(cmd,cwd=RUN,stdout=f,stderr=subprocess.STDOUT,check=True)
    p=probe(reel);v=p['streams'][0];assert int(v['nb_read_frames'])==75*len(ready) and v['r_frame_rate']=='15/1'
    state['comparison']=dict(path=reel.relative_to(ROOT).as_posix(),sha256=sha(reel),frames=75*len(ready),order=[k for k,_ in ready],seconds_per_test=5)
    # Remove only regenerable RGB outputs of this run, after verified MP4 generation.
    removed=[]
    for tid,info in state['tests'].items():
        if info['state']!='ready':continue
        path=RUN/f'{tid}-rgb.mkv'
        if path.is_file():
            assert path.resolve().is_relative_to(RUN.resolve());removed.append(dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size));path.unlink()
    state['removed_verified_rgb_intermediates']=removed
    save(RUN/'production.json',state);save(RECIPE/'metadata/production.json',state)
    print('REVIEW_READY',len(ready),'clips; sequential comparison',len(ready)*5,'seconds; intermediates freed',sum(x['bytes'] for x in removed),flush=True)
if __name__=='__main__':main()
