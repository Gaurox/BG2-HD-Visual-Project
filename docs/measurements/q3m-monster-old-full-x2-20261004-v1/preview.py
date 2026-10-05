"""All 46 native palette variants from final packed leaves; no GPU."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
import palette_partner_registry as leaves,run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');root=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(root/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
resources,works,summary=source_plan(HERE/'selection.json','monster_old')
cards=[]
for w in load(HERE/'selection.json')['witnesses']:
    r=next(r for r in resources if r['witness']['animation_id']==w['animation_id'] and r['resref'].endswith('G1'))
    slots=[i for i in r['cycles'][0] if i<len(r['frames'])]
    fi=slots[len(slots)//2] if slots else 0
    leaf=leaves.inspect(root/Path(cat['shards'][routes[(w['animation_id'],r['resref'])]['shard_index']]['registry']).name,include_frames=True)['resources'][0]
    f=leaf['frames'][fi];profile=r['profile'];palette=np.column_stack((profile.fitting[0],np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
    indices=works[r['frames'][fi]['key']]['frame'].indices
    original=profile.decode(indices,np.zeros_like(indices),palette)
    original=np.repeat(np.repeat(original,2,axis=0),2,axis=1)
    upscaled=profile.decode(f['I'],f['F'],palette)
    card=Image.new('RGB',(440,250),(28,28,28));draw=ImageDraw.Draw(card)
    draw.text((8,6),w['animation_id']+' '+w['name'],fill='white');draw.text((8,24),'Natif x2',fill='silver');draw.text((226,24),'Q3m x2 ameliore',fill='silver')
    for n,rgba in enumerate((original,upscaled)):
        image=Image.fromarray(rgba,'RGBA');limit=(208,202)
        if image.width>limit[0] or image.height>limit[1]:image.thumbnail(limit,Image.Resampling.LANCZOS)
        x=6+n*220+(208-image.width)//2;y=43+(202-image.height)//2
        draw.rectangle((6+n*220,43,214+n*220,245),fill=(65,65,65));card.paste(image,(x,y),image)
    cards.append(card)
sheet=Image.new('RGB',(440*4,250*((len(cards)+3)//4)),(20,20,20))
for n,card in enumerate(cards):sheet.paste(card,((n%4)*440,(n//4)*250))
sheet.save(HERE/'comparison.png');assert len(cards)==46
print('All 46 final native palette variants previewed; originals x2 nearest vs Q3m x2.')
