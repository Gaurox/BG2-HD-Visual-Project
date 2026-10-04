"""Neutral K6 comparison of original indexed layers and Q3m layered pixels."""
import json,sys,sqlite3,zlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
resources,works,_=source_plan(HERE/'selection.json','monster_layered');byref={r['resref']:r for r in resources}
gen=json.loads((HERE/'current-generation.json').read_text());assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
sheet=Image.new('RGB',(1000,7*350),(64,64,64));draw=ImageDraw.Draw(sheet)
for n,(prefix,weapon,aid) in enumerate([('MSIR','B','0x2000'),('UVOL','M','0x2100'),('MOGM','S','0x2200'),('MDKN','','0x2300'),('MGNL','H','0x8000'),('MHOB','B','0x8100'),('MKOB','B','0x8200')]):
    ref=prefix+'G1';body=byref[ref];seq=16 if len(body['cycles'])>16 and body['cycles'][16] else next(i for i,c in enumerate(body['cycles']) if c)
    slot=0;fi=body['cycles'][seq][slot];sources=[(body,fi)];er=prefix+weapon+'G1'
    if weapon and er in byref:
        equip=byref[er]
        if seq<len(equip['cycles']) and slot<len(equip['cycles'][seq]) and equip['cycles'][seq][slot]<len(equip['frames']):sources.append((equip,equip['cycles'][seq][slot]))
    g=[r['frames'][f]['geometry'] for r,f in sources];left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
    canvases=[np.zeros(((bottom-top)*scale,(right-left)*scale,4),np.uint8) for scale in (1,2)]
    for r,fi in sources:
        row=r['frames'][fi];indices=works[row['key']]['frame'].indices;pal=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8)));pal[0]=0;pal[1,3]=127
        route=routes[(aid,r['resref'])];f=leaves.inspect(assets/Path(cat['shards'][route['shard_index']]['registry']).name,include_frames=True)['resources'][0]['frames'][fi]
        pixels=[pal[indices],r['profile'].decode(f['I'],f['F'],pal)]
        for scale,image,canvas in zip((1,2),pixels,canvases):
            x=(-row['geometry'][2]-left)*scale;y=(-row['geometry'][3]-top)*scale;dest=canvas[y:y+image.shape[0],x:x+image.shape[1]];mask=np.any(image!=0,axis=2);dest[mask]=image[mask]
    y0=n*350;draw.text((10,y0+5),f'{aid} {prefix}, cycle {seq}, corps/equipement, palette K6 neutre',(255,255,255))
    for col,canvas,scale in zip((0,1),canvases,(1,2)):
        image=Image.fromarray(canvas,'RGBA');image=image.resize((image.width*3//scale,image.height*3//scale),Image.Resampling.NEAREST if scale==1 else Image.Resampling.BICUBIC)
        assert image.width<=475 and image.height<=310,(prefix,image.size)
        draw.text((col*500+10,y0+22),'Original x3' if col==0 else 'Q3m x2, affichage x1.5',(255,255,255));sheet.paste(image,(col*500+10,y0+40),image)
sheet.save(HERE/'comparison.png')
print('comparison.png')
