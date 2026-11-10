from common import *
from PIL import Image,ImageDraw
import numpy as np

def main():
    bounds=load(WEB/'board-bounds.json')
    for group,name in [([1,2,3,4,5,6],'weapons'),([22,27],'black')]:
        sheet=Image.new('RGB',(1140,240*len(group)),'#172231');draw=ImageDraw.Draw(sheet)
        for row,ordinal in enumerate(group):
            a=next(j for j in jobs() if j['ordinal']==ordinal and j['primary']);r=load(OUT/'results'/f'{a["job_id"]}.json');profile=r['profiles'][0]
            frames=[f for f in r['frames'] if f['profile']==profile['id']];f=max(frames,key=lambda f:int(np.fromfile(ROOT/f['premultiplied']['path'],np.uint8).reshape(-1,4)[:,:3].sum(dtype=np.uint64)))
            phase=f['phase'];native=min(len(profile['native'])-1,phase//2);crop=bounds[a['resref']][profile['id']];x,y,w,h=crop
            draw.text((12,row*240+4),f'{ordinal:02d} {a["resref"]} / phase{phase}',fill='white')
            versions=[(profile['native'][native],'Vanilla'),(f['before'],'Precedent'),(f['after'],'xBR / masque natif' if ordinal<=6 else 'Noir transparent')]
            for col,(path,label) in enumerate(versions):
                with Image.open(media(path)) as im:im=im.convert('RGBA').crop((x,y,x+w,y+h))
                im.thumbnail((362,200),Image.Resampling.NEAREST)
                tile=Image.new('RGBA',(370,202),(110,94,70,255));tile.alpha_composite(im,((370-im.width)//2,(202-im.height)//2));sheet.paste(tile.convert('RGB'),(col*380+5,row*240+32));draw.text((col*380+10,row*240+19),label,fill='#bdd0e5')
        sheet.save(OUT/(name+'.png'));print(name,flush=True)

if __name__=='__main__':main()
