"""Native contact sheets only; no production/authority/install mutation."""
from pathlib import Path
import csv,json,sys,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata
OUT=ROOT/'effects/batches/next-lot-inspection-20261017-v1'
def rows(n):return list(csv.DictReader((ROOT/n).open(encoding='utf-8-sig',newline='')))
def main():
    work=rows('effects/index/work-items.csv'); sources={x['asset_key']:x for x in rows('effects/index/bam-assets.csv')}
    states={x['asset_key']:x for x in rows('effects/index/processing.csv')}
    used={w['canonical_sha256'] for w in work if states[w['asset_key']]['spatial_state']!='not-started' or states[w['asset_key']]['qa_state'] in ('passed','native')}
    animations={p.stem.upper() for p in (ROOT/'animations/index/selections').glob('*.json')}
    used|={w['canonical_sha256'] for w in work if w['resref'] in animations}
    candidates=[]; excluded=[]; seen=set()
    for w in work:
        s=states[w['asset_key']]; ref=w['resref']
        if w['source_state']!='available' or s['spatial_state']!='not-started' or s['selected_run']: continue
        if w['canonical_sha256'] in used or ref in animations:
            excluded.append(ref);continue
        if w['canonical_sha256'] in seen:continue
        seen.add(w['canonical_sha256'])
        if w['usage']!='known' and not (ref.startswith('SP') or ref in {'ACIDDTH','BLOODCR','BLOODL','BLOODM','BLOODS','DUST','EXPLODE','GREASED','GREASEH','HLYMITE','SANCTRY','SHAREA','SHEARTH','SHWATER','SKLH','STNKCLDD','TRBLOBA','TRBLOBB','WEBBOMB','WEBC','WEBENTD','WEBENTH','WHIRL01','WHIRLY'}):continue
        frame,palette,tr=decode_bam(read_bam(ROOT/sources[w['asset_key']]['extracted_path']))
        candidates.append({**w,'source':sources[w['asset_key']]['extracted_path']})
        scores=[int(np.maximum(palette[idx].max(axis=2)-12,0).astype(np.int64)[idx!=tr].sum()) for idx,_,_,_ in frame]
        selected=sorted(range(len(frame)),key=lambda n:scores[n],reverse=True)
        choices=[]
        for n in selected:
            if all(abs(n-v)>max(1,len(frame)//5) for v in choices):choices.append(n)
            if len(choices)==3:break
        tile=Image.new('RGB',(256,178),(22,25,31)); d=ImageDraw.Draw(tile)
        d.text((8,5),ref+'  '+w['frames']+'f / '+w['cycles']+'c',font=FONT,fill='white')
        d.text((8,24),w['usage']+' | '+w['owner_routes']+' | '+('palette' if 'palette' in w['tags'] else 'fixed'),font=SMALL,fill=(145,175,195))
        for j,n in enumerate(sorted(choices)):
            idx,cx,cy,_=frame[n]; rgb=palette[idx].copy();rgb[idx==tr]=0
            im=Image.fromarray(rgb).convert('RGB'); im.thumbnail((78,120),Image.Resampling.NEAREST)
            if max(im.size)<55:
                factor=max(1,min(3,78//max(1,im.width),115//max(1,im.height)))
                im=im.resize((im.width*factor,im.height*factor),Image.Resampling.NEAREST)
            tile.paste(im,(j*84+(84-im.width)//2,48+(120-im.height)//2))
        tiles[ref]=tile
    OUT.mkdir(parents=True,exist_ok=True)
    for kind in ('known','unresolved'):
        group=[w for w in candidates if w['usage']==kind]
        for start in range(0,len(group),30):
            page=group[start:start+30]; sheet=Image.new('RGB',(1280,178*math.ceil(len(page)/5)),(14,16,21))
            for k,w in enumerate(page):sheet.paste(tiles[w['resref']],((k%5)*256,(k//5)*178))
            sheet.save(OUT/f'{kind}-{start//30+1}.png')
    (OUT/'candidates.json').write_text(json.dumps({'candidates':candidates,'excluded_existing':excluded},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Native inspection:',len(candidates),'candidates;',len(excluded),'existing assets excluded')
tiles={}
FONT=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
SMALL=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
if __name__=='__main__': main()
