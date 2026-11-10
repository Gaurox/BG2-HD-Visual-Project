"""Inspect title cards and representative film composition in native sources."""
import json, shutil
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw
from extract import ROOT, OUT, run


def main():
    sources=json.loads((OUT/'sources.json').read_text(encoding='utf-8'))['sources']
    cache=OUT/'inspection-frames';cache.mkdir(exist_ok=True)
    groups=[('INTRO-title',[(s,3) for s in sources if s['name'].startswith('INTRO-')]),
            ('INTRO15F-title',[(s,8) for s in sources if s['name'].startswith('INTRO15F-')]),
            ('INTRO15F-composition',[(s,65) for s in sources if s['name'].startswith('INTRO15F-')])]
    jobs=[(s,t) for _,items in groups for s,t in items]
    def extract(job):
        s,t=job;p=cache/f'{s["name"]}-{t}s.png'
        if not p.exists():run([shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-threads','2','-ss',str(t),'-i',str(ROOT/s['source']),'-map','0:v:0','-frames:v','1',str(p)])
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(extract,jobs))
    for name,items in groups:
        sheet=Image.new('RGB',(1280,388*((len(items)+1)//2)),(25,25,25));draw=ImageDraw.Draw(sheet)
        for i,(s,t) in enumerate(items):
            x=(i%2)*640;y=(i//2)*388
            im=Image.open(cache/f'{s["name"]}-{t}s.png');sheet.paste(im.resize((640,360)),(x,y+28))
            draw.text((x+5,y+8),f'{s["name"]} native source, ~{t}s',fill='white')
        sheet.save(OUT/f'{name}.jpg',quality=96)


if __name__=='__main__':main()
