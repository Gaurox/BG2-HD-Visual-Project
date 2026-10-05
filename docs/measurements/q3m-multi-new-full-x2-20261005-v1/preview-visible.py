"""Additional visible complete poses; preserve original comparison files."""
import json,sys
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
import palette_partner_registry as leaves,run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');root=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(root/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
resources,works,summary=source_plan(HERE/'selection.json','multi_new');source={(r['witness']['animation_id'],r['resref']):r for r in resources}
@lru_cache(maxsize=12)
def leaf(aid,ref):return leaves.inspect(root/Path(cat['shards'][routes[(aid,ref)]['shard_index']]['registry']).name,include_frames=True)['resources'][0]
for pose in range(3):
    cards=[]
    for w in load(HERE/'selection.json')['witnesses']:
        aid=w['animation_id'];groups=w['multipart_groups']
        start=(0,len(groups)//2,len(groups)-1)[pose]
        for offset in range(len(groups)):
            group=groups[(start+offset)%len(groups)];rr=[source[(aid,ref)] for ref in group]
            candidate_seq=next((i for i in range(len(rr[0]['cycles'])) if rr[0]['cycles'][i] and all(r['cycles'][i][0]<len(r['frames']) for r in rr)),None)
            if candidate_seq is None:continue
            candidate_slots=[i for i in range(len(rr[0]['cycles'][candidate_seq])) if all(r['cycles'][candidate_seq][i]<len(r['frames']) for r in rr)]
            candidate_slot=candidate_slots[len(candidate_slots)//2]
            visible=sum(np.count_nonzero(works[r['frames'][r['cycles'][candidate_seq][candidate_slot]]['key']]['frame'].indices>=2) for r in rr)
            if visible>=512:break
        else:raise RuntimeError('No visible native pose: '+aid)
        seq=next(i for i in range(len(rr[0]['cycles'])) if rr[0]['cycles'][i] and all(r['cycles'][i][0]<len(r['frames']) for r in rr))
        slots=[i for i in range(len(rr[0]['cycles'][seq])) if all(r['cycles'][seq][i]<len(r['frames']) for r in rr)];slot=slots[len(slots)//2]
        rows=[r['frames'][r['cycles'][seq][slot]] for r in rr];g=[row['geometry'] for row in rows]
        left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
        images=[np.zeros(((bottom-top)*2,(right-left)*2,4),np.uint8) for _ in range(2)]
        for ref,r,row in zip(group,rr,rows):
            profile=r['profile'];palette=np.column_stack((profile.fitting[0],np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
            indices=works[row['key']]['frame'].indices;native=profile.decode(indices,np.zeros_like(indices),palette);native=np.repeat(np.repeat(native,2,axis=0),2,axis=1)
            f=leaf(aid,ref)['frames'][row['frame_index']];final=profile.decode(f['I'],f['F'],palette)
            a=row['geometry'];x=(-a[2]-left)*2;y=(-a[3]-top)*2
            for canvas,im in zip(images,(native,final)):
                dst=canvas[y:y+im.shape[0],x:x+im.shape[1]];mask=np.any(im!=0,axis=2);dst[mask]=im[mask]
        card=Image.new('RGB',(960,520),(28,28,28));draw=ImageDraw.Draw(card)
        draw.text((8,6),aid+' '+w['name']+' / '+group[0],fill='white');draw.text((8,25),'Natif x2',fill='silver');draw.text((488,25),'Q3m x2 ameliore + raccords contextuels',fill='silver')
        size=(min(460,images[0].shape[1]),min(465,images[0].shape[0]));scale=min(460/images[0].shape[1],465/images[0].shape[0],1)
        target=(max(1,round(images[0].shape[1]*scale)),max(1,round(images[0].shape[0]*scale)))
        for n,rgba in enumerate(images):
            im=Image.fromarray(rgba,'RGBA')
            if im.size!=target:im=im.resize(target,Image.Resampling.LANCZOS)
            x=8+n*480+(460-im.width)//2;y=47+(465-im.height)//2;draw.rectangle((8+n*480,47,468+n*480,512),fill=(65,65,65));card.paste(im,(x,y),im)
        cards.append(card)
    sheet=Image.new('RGB',(1920,520*5),(20,20,20))
    for n,card in enumerate(cards):sheet.paste(card,((n%2)*960,(n//2)*520))
    sheet.save(HERE/('comparison-visible'+('' if pose==0 else '-'+str(pose+1))+'.png'))
print('Ten variants, three visible complete 4/9-part native/Q3m poses; no ingame QA inferred.')

