"""Native four-quadrant original/Q3m comparison for all seven colour variants."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text())
resources,works,_=source_plan(HERE/'selection.json','monster_quadrant');source={(r['witness']['animation_id'],r['resref']):r for r in resources}
gen=load(HERE/'current-generation.json');assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites';cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
sheet=Image.new('RGB',(1040,7*360),(55,55,55));draw=ImageDraw.Draw(sheet)
for n,w in enumerate(load(HERE/'selection.json')['witnesses']):
    aid=w['animation_id'];rr=[source[(aid,ref)] for ref in w['multipart_groups'][0]];seq=0;slot=0;rows=[r['frames'][r['cycles'][seq][slot]] for r in rr];g=[row['geometry'] for row in rows];left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
    canvases=[np.zeros(((bottom-top)*s,(right-left)*s,4),np.uint8) for s in (1,2)]
    for r,row in zip(rr,rows):
        ref=r['resref'];fi=row['frame_index'];route=routes[(aid,ref)];f=leaves.inspect(assets/Path(cat['shards'][route['shard_index']]['registry']).name,include_frames=True)['resources'][0]['frames'][fi]
        pal=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8)));pal[0]=0;pal[1,3]=127
        images=[pal[works[row['key']]['frame'].indices],r['profile'].decode(f['I'],f['F'],pal)]
        for s,image,canvas in zip((1,2),images,canvases):
            a=row['geometry'];x=(-a[2]-left)*s;y=(-a[3]-top)*s;dest=canvas[y:y+image.shape[0],x:x+image.shape[1]];mask=np.any(image!=0,axis=2);dest[mask]=image[mask]
    y0=n*360;draw.text((10,y0+4),aid+' '+w['name']+' / '+w.get('palette_override',{}).get('resref','native BAM'),fill='white')
    ratio=min(2.5,490/(right-left),300/(bottom-top));size=(round((right-left)*ratio),round((bottom-top)*ratio))
    for col,c in enumerate(canvases):
        im=Image.fromarray(c,'RGBA').resize(size,Image.Resampling.NEAREST if col==0 else Image.Resampling.BICUBIC)
        draw.text((col*520+10,y0+24),'Original' if col==0 else 'Q3m x2, palette amelioree',fill='white');sheet.paste(im,(col*520+10,y0+44),im)
sheet.save(HERE/'comparison.png');print('comparison.png: seven native palette variants.')
