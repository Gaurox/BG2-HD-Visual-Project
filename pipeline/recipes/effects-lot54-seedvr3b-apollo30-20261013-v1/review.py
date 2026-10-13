"""Native / final sample, same anchor and scale; final RGB already premultiplied."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
BATCH = ROOT / 'effects/batches/lot54-seedvr3b-apollo30-20261013-v1'


def main():
    assets = json.loads((BATCH / 'batch.json').read_text(encoding='utf-8'))['assets']
    ready = [a for a in assets if (BATCH / 'checks' / (a['resref']+'.json')).exists()
             and json.loads((BATCH / 'checks' / (a['resref']+'.json')).read_text())['passed']]
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
    out = BATCH / 'preview'; out.mkdir(exist_ok=True)
    for page in range((len(ready)+17)//18):
        items = ready[page*18:(page+1)*18]
        sheet = Image.new('RGB', (1440, ((len(items)+5)//6)*196), (15,15,19)); draw=ImageDraw.Draw(sheet)
        for i, a in enumerate(items):
            root = ROOT / 'effects/ressources' / a['resref'] / 'runs'
            native_root = root / a['spatial_run'] / '00-frames-x1'
            final_root = root / a['treatment_run'] / '02-interpolation'
            native = json.loads((native_root/'manifest.json').read_text()); final=json.loads((final_root/'manifest.json').read_text())
            sequence = native['cycles'][0]['frame_indices']; poses={}
            for idx in set(sequence):
                with Image.open(native_root/'rgba'/native['frames'][idx]['file']) as im:
                    arr=np.array(im.convert('RGBA'));arr[arr[:,:,3]==0]=0;poses[idx]=Image.fromarray(arr[:,:,:3])
            slot=max(range(len(sequence)),key=lambda s:np.asarray(poses[sequence[s]]).astype(np.uint64).sum())
            idx=sequence[slot];frame=final['frames'][slot*2];source=poses[idx]
            with Image.open(final_root/frame['rgba_x4']) as im: result=im.convert('RGB')
            target=Image.new('RGB',tuple(v*4 for v in source.size),'black');crop=frame['runtime_crop_box_x4'];target.paste(result,(crop[0],crop[1]))
            scale=min(113/source.width,144/source.height)
            display=(max(1,round(source.width*scale)),max(1,round(source.height*scale)))
            source=source.resize(display,Image.Resampling.NEAREST);target=target.resize(display,Image.Resampling.LANCZOS)
            x=(i%6)*240;y=(i//6)*196
            draw.text((x+7,y+3),a['resref'],font=font,fill='white')
            sheet.paste(source,(x+3+(113-source.width)//2,y+26+(144-source.height)//2))
            sheet.paste(target,(x+123+(113-target.width)//2,y+26+(144-target.height)//2))
            draw.text((x+20,y+175),'natif',font=font,fill=(160,160,175));draw.text((x+140,y+175),'x4',font=font,fill=(160,160,175))
        path=out/f'native-x4-review-{page+1}.png';sheet.save(path);print(path)


if __name__=='__main__': main()
