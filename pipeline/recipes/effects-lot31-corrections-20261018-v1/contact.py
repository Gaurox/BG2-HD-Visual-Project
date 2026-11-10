"""Selected visible poses, before/after/alpha at enlarged small-sprite scale."""
from prepare import ROOT,OUT,load
from PIL import Image,ImageDraw
import numpy as np

def main():
    jobs=[a for a in load(OUT/'plan.json')['jobs'] if a['primary']]
    for start in range(0,31,8):
        sheet=Image.new('RGB',(1440,4*300),'#17202d');draw=ImageDraw.Draw(sheet)
        for slot,a in enumerate(jobs[start:start+8]):
            p=OUT/'results'/f'{a["job_id"]}.json'
            if not p.exists():continue
            r=load(p)
            f=max(r['frames'],key=lambda f:int(np.fromfile(ROOT/f['premultiplied']['path'],np.uint8).reshape(-1,4)[:,:3].sum(dtype=np.uint64)))
            before=Image.open(OUT/'review'/f['before']).convert('RGBA');after=Image.open(OUT/'review'/f['after']).convert('RGBA')
            bbox=after.getchannel('A').getbbox() or (0,0,*after.size)
            bbox=(max(0,bbox[0]-8),max(0,bbox[1]-8),min(after.width,bbox[2]+8),min(after.height,bbox[3]+8))
            x=(slot%2)*720;y=(slot//2)*300
            draw.text((x+10,y+5),f'{a["ordinal"]:02d} {a["resref"]} / {f["profile"]} phase{f["phase"]}',fill='white')
            for col,(im,label) in enumerate([(before,'Avant'),(after,'Correction'),(Image.merge('RGB',(after.getchannel('A'),)*3).convert('RGBA'),'Alpha')]):
                im=im.crop(bbox);im.thumbnail((228,246),Image.Resampling.NEAREST)
                if a['black_neutral'] and col<2:
                    q=np.array(im);q[:,:,:3]=np.clip(np.rint(q[:,:,:3].astype(float)*q[:,:,3:4]/255)+[80,74,62],0,255).astype(np.uint8);q[:,:,3]=255;im=Image.fromarray(q)
                tile=Image.new('RGBA',(232,250),(110,94,70,255));tile.alpha_composite(im,((232-im.width)//2,(250-im.height)//2))
                sheet.paste(tile.convert('RGB'),(x+col*238+4,y+42));draw.text((x+col*238+8,y+24),label,fill='#bfd5ef')
        target=OUT/'review'/f'contact-{start//8+1}.jpg';sheet.save(target,quality=95)
        print(target,flush=True)

if __name__=='__main__':main()
