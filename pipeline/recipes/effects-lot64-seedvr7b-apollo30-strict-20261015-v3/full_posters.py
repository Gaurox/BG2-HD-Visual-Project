"""A full-resolution x4 RGB frame for each card, for detail inspection."""
import time
import re
import numpy as np
from PIL import Image
from temporal import ROOT,BATCH,load,save,digest


def main():
    out=BATCH/'review/full';out.mkdir(parents=True,exist_ok=True);records=[]
    for a in load(BATCH/'batch.json')['assets']:
        name=a['resref'];card=BATCH/'review/cards'/f'{name}.json'
        while not card.exists():time.sleep(3)
        c=load(card);stage=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']/'02-interpolation'
        m=load(stage/'manifest.json');v=next(v for v in m['timing']['cycles'] if v['id']==c['default_profile'])
        best=None
        for index in v['timeline_frame_indices']:
            f=m['frames'][index];w,h=f['physical_size_x4']
            p=np.frombuffer((stage/f['raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4)
            flux=int(p[:,:,:3].astype(np.uint64).sum())
            if best is None or flux>best[0]:best=(flux,f,p[:,:,:3].copy())
        _,f,rgb=best;s=load(ROOT/m['parent']['spatial_manifest']);cw,ch=s['aligned_canvas_size_x1'];f0=s['frames'][0]
        anchor=[f0['canvas_offset_x1'][i]+f0['centre_x1'][i] for i in range(2)]
        canvas=Image.new('RGB',(cw*4,ch*4),'black')
        canvas.paste(Image.fromarray(rgb),tuple((anchor[i]-f['centre_x1'][i])*4 for i in range(2)))
        path=out/f'{name}.png';canvas.save(path,compress_level=3)
        records.append({'resref':name,'profile':v['id'],'phase':f['phase'],'production_frame':f['frame'],
                        'size':list(canvas.size),'path':'full/'+path.name,'sha256':digest(path.read_bytes()),
                        'encoding':'native x4 premultiplied RGB directly over black; no resize/recompression loss'})
    while not (BATCH/'review/review.json').exists():time.sleep(3)
    page=BATCH/'review/index.html';text=page.read_text(encoding='utf-8')
    if 'Frame x4 sans réduction' not in text:
        text=re.sub(r'(<article><h2>\d+ · ([A-Z0-9_]+)</h2>.*?</select>)',
                    lambda m:m[1]+f'<p><a href="full/{m[2]}.png" target="_blank">Frame x4 sans réduction</a></p>',text)
        page.write_text(text,encoding='utf-8')
    save(BATCH/'review/full-posters.json',{'count':len(records),'assets':records})
    print('64 full-resolution x4 RGB posters ready',flush=True)


if __name__=='__main__':main()
