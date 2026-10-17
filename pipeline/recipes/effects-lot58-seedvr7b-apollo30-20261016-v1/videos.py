"""Four compact CFR30 overview videos, derived from exact production frames."""
from fractions import Fraction
import json
import shutil
import subprocess
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from temporal import ROOT, BATCH, load, save
from review import OUT, fit


def main():
    assets=load(BATCH/'batch.json')['assets'];results=[]
    ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
    assert ffmpeg and ffprobe
    font=ImageFont.truetype('consola.ttf',19);small=ImageFont.truetype('consola.ttf',14)
    for page,start in enumerate(range(0,len(assets),16),1):
        path=OUT/f'lot58-animated-{page}.mp4';proof=OUT/f'video-{page}.json'
        if proof.exists():results.append(load(proof));continue
        cached=[];base=Image.new('RGB',(1080,1016),(12,15,22));draw=ImageDraw.Draw(base)
        draw.text((18,9),f'58 effets - SeedVR7B x4 / NEAREST / Apollo30 - {page}/4',font=font,fill='white')
        draw.text((18,38),'Tailles ajustees pour la planche ; durees natives conservees.',font=small,fill='#b8c7dd')
        for cell,a in enumerate(assets[start:start+16]):
            card=OUT/'cards'/f'{a["resref"]}.json'
            while not card.exists():time.sleep(3)
            r=load(card);stage=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation'
            m=load(stage/'manifest.json');v=next(v for v in m['timing']['cycles'] if v['id']==r['default'])
            s=load(ROOT/m['parent']['spatial_manifest']);cw,ch=s['aligned_canvas_size_x1']
            anchor=[s['frames'][0]['canvas_offset_x1'][i]+s['frames'][0]['centre_x1'][i] for i in range(2)]
            frames=[]
            for index in v['timeline_frame_indices']:
                f=m['frames'][index];w,h=f['physical_size_x4'];rgba=np.frombuffer((stage/f['raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4)
                im=Image.new('RGB',(cw*4,ch*4),'black');im.paste(Image.fromarray(rgba[:,:,:3]),tuple((anchor[i]-f['centre_x1'][i])*4 for i in range(2)))
                frames.append(fit(im))
            duration=Fraction(*v['duration_rational']);gap=Fraction(0) if v['loop_closed'] else Fraction(1,2)
            cached.append((frames,duration,gap))
            x=(cell%4)*270;y=65+(cell//4)*237
            draw.text((x+12,y+187),f'{start+cell+1:02d} {a["resref"]}',font=font,fill='white')
            draw.text((x+12,y+213),f'{float(duration):.3f} s / '+('boucle' if v['loop_closed'] else 'ponctuel'),font=small,fill='#aebfd5')
        command=[ffmpeg,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1016','-r','30','-i','-',
                 '-an','-c:v','libx264','-crf','15','-preset','fast','-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(path)]
        with (OUT/f'video-{page}.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log)
            for phase in range(360):
                im=base.copy()
                for cell,(frames,duration,gap) in enumerate(cached):
                    t=Fraction(phase,30)%(duration+gap)
                    if t<duration:im.paste(frames[min(int(t*30),len(frames)-1)],((cell%4)*270+15,65+(cell//4)*237))
                process.stdin.write(im.tobytes())
            process.stdin.close();assert process.wait()==0
        metadata=json.loads(subprocess.check_output([ffprobe,'-v','error','-select_streams','v:0','-show_streams','-show_frames','-show_entries','frame=best_effort_timestamp_time:stream=avg_frame_rate,nb_frames','-of','json',str(path)]))
        stream=metadata['streams'][0];pts=[Fraction(f['best_effort_timestamp_time']) for f in metadata['frames']]
        assert stream['avg_frame_rate']=='30/1' and int(stream['nb_frames'])==len(pts)==360
        assert all(abs(t-Fraction(i,30))<Fraction(1,1000000) for i,t in enumerate(pts))
        value={'path':path.name,'frames':360,'fps':[30,1],'duration_seconds':12,'pts_checked':True,'source':'exact production RGB; NEAREST thumbnails; native period, including 8 FPS fractional ending, sampled at CFR30'}
        save(proof,value);results.append(value);print('Video',page,'CFR30 verified',flush=True)
    save(OUT/'videos.json',{'videos':results})


if __name__=='__main__':main()
