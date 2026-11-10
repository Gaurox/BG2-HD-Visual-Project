"""Native RGB review of the highest residuals in the Polish framing comparison."""
import csv,json,shutil
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw
from extract import ROOT,OUT,run


def main():
    rows=list(csv.DictReader((OUT/'INTRO15F-pl_PL-fitted-to-default.csv').open()))
    selected=[]
    for start in [30,60,80,100,110,140]:
        selected.append(max((r for r in rows if start<=float(r['locale_pts_s'])<start+10),key=lambda r:float(r['luma_mae_160x90'])))
    save=OUT/'polish-review-frames';save.mkdir(exist_ok=True)
    sources=json.loads((OUT/'sources.json').read_text())['sources']
    def extract(name,key):
        source=next(s for s in sources if s['name']==name)
        ids=sorted({int(r[key]) for r in selected})
        expression='+'.join(f'eq(n\\,{i})' for i in ids)
        pattern=save/(name+'-%02d.png')
        run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-threads','2','-i',str(ROOT/source['source']),'-map','0:v:0',
             '-vf','select='+expression,'-fps_mode','passthrough',str(pattern)])
        return {i:Image.open(save/(name+f'-{j+1:02d}.png')).convert('RGB') for j,i in enumerate(ids)}
    with ThreadPoolExecutor(max_workers=2) as pool:
        a=pool.submit(extract,'INTRO15F-default','default_frame');b=pool.submit(extract,'INTRO15F-pl_PL','locale_frame')
        base=a.result();other=b.result()
    for page in range(2):
        sheet=Image.new('RGB',(1920,388*3),(25,25,25));draw=ImageDraw.Draw(sheet)
        for row,r in enumerate(selected[page*3:page*3+3]):
            im=base[int(r['default_frame'])]
            transformed=im.crop((160,0,1120,720)).resize((1280,960),Image.Resampling.LANCZOS).crop((0,120,1280,840))
            for col,(label,img) in enumerate([('Default native',im),('Default geometry normalized',transformed),('Polish native',other[int(r['locale_frame'])])]):
                sheet.paste(img.resize((640,360)),(col*640,row*388+28))
                draw.text((col*640+4,row*388+7),f'{label}; PL {r["locale_pts_s"]}s; error {r["luma_mae_160x90"]}',fill='white')
        sheet.save(OUT/f'INTRO15F-polish-review-{page+1}.jpg',quality=95)


if __name__=='__main__':main()
