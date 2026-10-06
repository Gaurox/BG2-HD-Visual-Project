"""Review all 77 variants from final isolated leaves; original and Q3m side by side."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import write_json
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    prod=load(HERE/'production.json');output=ROOT/prod['pack_directory']
    cat=registry.read_sealed_catalog_index(output/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
    routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
    resources,works,_=source_plan(HERE/'selection.json','monster')
    cards,chosen=[],[]
    for witness in load(HERE/'selection.json')['witnesses']:
        candidates=[r for r in resources if r['witness']['animation_id']==witness['animation_id'] and not r['resref'].endswith('INV')]
        candidates.sort(key=lambda r:not r['resref'].endswith('G1'))
        selected=None
        for resource in candidates:
            slots=list(dict.fromkeys(fi for cycle in resource['cycles'] for fi in cycle if fi<len(resource['frames'])))
            for fi in slots[len(slots)//2:]+slots[:len(slots)//2]:
                indices=works[resource['frames'][fi]['key']]['frame'].indices
                classes=resource['profile'].classes[indices]
                if np.count_nonzero(classes>=(3 if resource['profile'].kind==0 else 4))>=20:
                    selected=(resource,fi);break
            if selected:break
        if not selected:
            for resource in candidates:
                for fi,row in enumerate(resource['frames']):
                    if np.any(works[row['key']]['frame'].indices!=0):selected=(resource,fi);break
                if selected:break
        assert selected,witness['animation_id']
        r,fi=selected;shard=cat['shards'][routes[(witness['animation_id'],r['resref'])]['shard_index']]
        leaf=leaves.inspect(output/Path(shard['registry']).name,include_frames=True)['resources'][0]
        f=leaf['frames'][fi];profile=r['profile']
        palette=np.column_stack((profile.fitting[0],np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
        indices=works[r['frames'][fi]['key']]['frame'].indices
        native=profile.decode(indices,np.zeros_like(indices),palette)
        native=np.repeat(np.repeat(native,2,axis=0),2,axis=1)
        upscaled=profile.decode(f['I'],f['F'],palette)
        card=Image.new('RGB',(480,290),(28,28,28));draw=ImageDraw.Draw(card)
        draw.text((8,6),witness['animation_id']+' '+witness['name'],fill='white')
        draw.text((8,24),'Natif x2 nearest',fill='silver');draw.text((250,24),'Q3m V7 x2',fill='silver')
        for n,rgba in enumerate((native,upscaled)):
            image=Image.fromarray(rgba,'RGBA');image.thumbnail((228,236),Image.Resampling.NEAREST)
            x=6+n*240+(228-image.width)//2;y=45+(236-image.height)//2
            draw.rectangle((6+n*240,45,234+n*240,281),fill=(65,65,65));card.paste(image,(x,y),image)
        cards.append(card);chosen.append(dict(animation_id=witness['animation_id'],resref=r['resref'],frame_index=fi))
    sheets=[]
    for start in range(0,len(cards),16):
        group=cards[start:start+16];sheet=Image.new('RGB',(1920,290*((len(group)+3)//4)),(20,20,20))
        for n,card in enumerate(group):sheet.paste(card,((n%4)*480,(n//4)*290))
        name=f'comparison-{start//16+1:02}.png';sheet.save(HERE/name);sheets.append(name)
    write_json(HERE/'previews.json',dict(animation_ids=len(cards),sheets=sheets,frames=chosen,ingame_QA=False))
    print(json.dumps(dict(stage='previews',animation_ids=len(cards),sheets=sheets)),flush=True)

if __name__=='__main__':main()
