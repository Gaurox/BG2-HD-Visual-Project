"""Animated board only; existing candidate/source pixels and timings are untouched."""
from pathlib import Path
import json,hashlib,shutil
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
REVIEW=ROOT/'effects/batches/lot31-corrections-preview-20261018-v1/review'
HERE=Path(__file__).resolve().parent

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    catalog=read(REVIEW/'catalog.json');bounds={};cache={}
    assert len(catalog['assets'])==31 and catalog['contexts']==99
    for asset in catalog['assets']:
        data=read(REVIEW/asset['contexts'][0]['data']);w,h=data['size_x4'];profiles={}
        for profile in data['profiles']:
            rectangles=[]
            for path in set(profile['native']):
                if path not in cache:
                    with Image.open(REVIEW/path) as im:cache[path]=im.getchannel('A').getbbox()
                if cache[path]:rectangles.append(cache[path])
            if rectangles:
                # Same source-space crop for all three versions;20px contains the existing feather.
                x0=max(0,min(r[0] for r in rectangles)-20);y0=max(0,min(r[1] for r in rectangles)-20)
                x1=min(w,max(r[2] for r in rectangles)+20);y1=min(h,max(r[3] for r in rectangles)+20)
                profiles[profile['id']]=[x0,y0,x1-x0,y1-y0]
            else:profiles[profile['id']]=[0,0,w,h]
        bounds[asset['resref']]=profiles
    (REVIEW/'board-bounds.json').write_text(json.dumps(bounds,separators=(',',':'))+'\n',encoding='utf-8')
    page=(HERE/'board.html').read_bytes()
    old=REVIEW/'index-static-v1.html'
    if not old.exists():shutil.copyfile(REVIEW/'index.html',old)
    (REVIEW/'animated-v1.html').write_bytes(page)
    (REVIEW/'index.html').write_bytes(page)
    record={'scope':'animated comparison UI only','assets':31,'contexts':99,
        'versions':['native','before','after'],'profiles':sum(len(b) for b in bounds.values()),
        'clock':'shared across three versions; native15fps, previous/corrected30fps; native durations unchanged',
        'viewport':'animate visible cards; decoded-image LRU256MiB; no candidate pixels regenerated',
        'previous_index_sha256':digest(old),'index_sha256':digest(REVIEW/'index.html'),
        'catalog_sha256':digest(REVIEW/'catalog.json'),'bounds_sha256':digest(REVIEW/'board-bounds.json'),
        'recipe_sha256':digest(Path(__file__)),'template_sha256':digest(HERE/'board.html'),
        'source_or_candidate_changed':False,'production_or_installation_changed':False}
    (REVIEW/'animated-board.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Animated board ready:31 cards x3 animated views,99 palettes; candidate data unchanged.')

if __name__=='__main__':main()
