import sys,csv,json,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path('pipeline/recipes/video-endings-locales-analysis-20261111-v1').resolve()))
from compare import OUT,read,save
summary={}
for family in ['END15FPS','MELISSAN']:
    a=read(family+'-default');b=read(family+'-pl_PL')
    rows=list(csv.DictReader((OUT/f'{family}-pl_PL-to-default.csv').open()))
    mapping=np.array([int(r['default_frame']) for r in rows]); delta=np.diff(mapping)
    groups=[]; start=0
    for j in range(1,len(mapping)+1):
        if j==len(mapping) or mapping[j]-j!=mapping[start]-start:
            if j-start>=3:groups.append(dict(locale_start=start,locale_end_exclusive=j,default_start=int(mapping[start]),offset=int(mapping[start]-start),locale_pts_start=float(b['pts'][start]),locale_pts_last=float(b['pts'][j-1])))
            start=j
    summary[family]=dict(mapping_steps={str(i):int((delta==i).sum()) for i in np.unique(delta)},long_alignment_runs=groups,source_timings={})
    for name in [family+'-default',family+'-de_DE']+([family+'-it_IT'] if family=='END15FPS' else [])+[family+'-pl_PL']:
        d=read(name);p=d['pts'];m=d['meta'];audio=m['audio']
        summary[family]['source_timings'][name]=dict(frames=len(p),first_pts=float(p[0]),last_pts=float(p[-1]),container_duration=m['format_duration'],audio_rate=audio['sample_rate'],audio_channels=audio['channels'],pts_step_min=float(np.diff(p).min()),pts_step_max=float(np.diff(p).max()))
    # RGB comparison at worst residual in separate time bins + even coverage.
    selected=[]
    for chunk in np.array_split(np.arange(len(rows)),8):
        selected.append(max(chunk,key=lambda j:float(rows[j]['luma_mae_160x90'])))
    sheet=Image.new('RGB',(1280,8*382),(22,22,22));draw=ImageDraw.Draw(sheet)
    for row,j in enumerate(selected):
        i=int(mapping[j])
        for col,(d,idx,label) in enumerate([(a,i,'default'),(b,j,'pl_PL')]):
            src=str(Path(d['meta']['source']).resolve())
            raw=subprocess.check_output(['ffmpeg','-v','error','-threads','2','-i',src,'-vf',f'select=eq(n\\,{idx}),scale=640:360','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
            im=Image.frombytes('RGB',(640,360),raw);sheet.paste(im,(col*640,row*382+22))
            draw.text((col*640+4,row*382+4),f'{label} #{idx} {d["pts"][idx]:.3f}s; MAE {float(rows[j]["luma_mae_160x90"]):.3f}',fill='white')
    sheet.save(OUT/f'{family}-polish-residual-review.jpg',quality=94)
save('timing-alignment-summary.json',summary)
print(json.dumps(summary,indent=2))
