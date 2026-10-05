"""Scoped offline comparison; reads vanilla KEY/BIF + installed leaves, no install."""
import hashlib, io, json, runpy, struct, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1'))
from workspace_paths import get_path
from run_creature_sprite_x2 import KeyIndex, read_sealed_catalog_index
from palette_work_plan import file_sha
from palette_oracle import scalar_palette
from palette_frac_encode import CLASS_TABLE
from bam_export import decode_bam
from palette_eval import parse_2da
import palette_partner_registry as leaves

game=get_path('bg2ee_game_root',required=True); key=KeyIndex(game)
catalog_path=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
catalog=read_sealed_catalog_index(catalog_path,file_sha(catalog_path)); bam_entries=key.resource_map(1000)
ramps=np.asarray(Image.open(io.BytesIO(key.resolve(key.resource_map(1)['MPALETTE'])[0])).convert('RGB'))
fixture=(game/'override/QOLD7001.cre').read_bytes()
_,random=parse_2da(key.resolve(key.resource_map(1012)['RANDCOLR'])[0])
skin_column=next(c for c,v in random['0'].items() if int(v)==fixture[0x2f])
skin_rows=sorted({int(r[skin_column]) for n,r in random.items() if n!='0'})
result=dict(role='analysis-not-production-QA-installation-release',catalogue_sha256=file_sha(catalog_path),
    DLL_sha256=file_sha(game/'InfinityEngine-Enhancer.dll'),fixture_colour_fields=list(fixture[0x2c:0x33]),
    fixture_random_skin_rows=skin_rows,models={},runtime_palette_snapshot_available=False)
models={}
for aid in ('0x7000','0x7001','0x7B06'):
    refs=[r for r in catalog['directory'] if r['animation_id']==aid]
    stat=dict(resources=[],frames=0,special_counts_native_x2=[0]*4,special_counts_HD=[0]*4,
        special_mask_changed_pixels=[0]*4,alpha_mask_transitions_native_to_HD={},below_head_hair_samples=[])
    models[aid]=[]
    for route in refs:
        ref=route['resref']; raw,bif=key.resolve(bam_entries[ref])
        canonical=zlib.decompress(raw[12:]) if raw[:4]==b'BAMC' else raw
        # Read frames independently of legacy unused direction-cycle sentinels.
        frames,rgb,tr=decode_bam(canonical)
        shard=catalog['shards'][route['shard_index']]; path=game/shard['registry']
        assert file_sha(path).lower()==shard['sha256'].lower()
        leaf=leaves.inspect(path,include_frames=True)['resources'][0]
        assert hashlib.sha256(canonical).hexdigest()==leaf['source_sha256'] and len(frames)==len(leaf['frames'])
        stat['resources'].append(dict(resref=ref,source_BIF=bif,canonical_sha256=leaf['source_sha256'],
            installed_leaf_sha256=shard['sha256'],frames=len(frames)))
        for fi,(source,hd) in enumerate(zip(frames,leaf['frames'])):
            native=np.repeat(np.repeat(source[0],2,0),2,1); indices=hd['I']
            assert native.shape==indices.shape and tuple(hd['geometry'])==(source[0].shape[1],source[0].shape[0],source[1],source[2],tr)
            for n in range(4):
                stat['special_counts_native_x2'][n]+=int(np.count_nonzero(native==n))
                stat['special_counts_HD'][n]+=int(np.count_nonzero(indices==n))
                stat['special_mask_changed_pixels'][n]+=int(np.count_nonzero((native==n)!=(indices==n)))
            # Native alpha categories: clear=0, reserved shadow=1, material=2.
            a=np.minimum(native,2);b=np.minimum(indices,2)
            values,counts=np.unique(a.astype(np.uint16)*3+b,return_counts=True)
            for v,count in zip(values,counts):
                label=f'{int(v)//3}->{int(v)%3}'
                stat['alpha_mask_transitions_native_to_HD'][label]=stat['alpha_mask_transitions_native_to_HD'].get(label,0)+int(count)
            if aid=='0x7001' and ref=='MOGNG1' and fi==129:
                stat['below_head_hair_samples']=[dict(x=int(x),y=int(y),native_index=int(source[0][y,x]))
                    for y,x in np.argwhere(CLASS_TABLE[source[0]]==10) if y>=16]
            stat['frames']+=1
        models[aid].append((ref,frames,rgb,leaf))
    result['models'][aid]=stat

# Actual pinned native instructions: fixed palette with normal shadow flag,
# then explicit translucent flag at alpha=127. Neither launches the executable.
native_module=runpy.run_path(str(ROOT/'docs/measurements/q3m-monster-contract-x2-20261002-v1/build_contract.py'))
oracle=native_module['NativeFixed']((game/'BaldurReal.exe').read_bytes())
wolf=models['0x7B06'][0][3];source=wolf['profile'].source
native=oracle.realize(source,5,[255,255,255]);translucent=oracle.realize(source,7,[255,255,255],127)
assert native[0,3]==0 and native[1,3]==127 and np.all(native[2:,3]==255)
assert translucent[1,3]==63 and np.all(translucent[2:,3]==127)
result['native_fixed_alpha_oracle']=dict(flags5=dict(clear=0,shadow=127,material=255),flags7_alpha127=dict(clear=0,shadow=63,material=127))

def palette(rgb):
    p=np.column_stack((rgb,np.full(256,255,np.uint8)));p[0]=0;p[1]=(0,0,0,127);return p

def card(ref,fi,source,hd,p,title):
    native=np.repeat(np.repeat(p[source[0]],2,0),2,1);scaled=hd['profile'].decode(hd['frames'][fi]['I'],hd['frames'][fi]['F'],p)
    canvas=Image.new('RGB',(600,350),(35,35,35));draw=ImageDraw.Draw(canvas)
    draw.text((8,5),title,fill='white')
    for n,rgba in enumerate((native,scaled)):
        image=Image.fromarray(rgba,'RGBA').resize((rgba.shape[1]*2,rgba.shape[0]*2),Image.Resampling.NEAREST)
        image.thumbnail((280,320),Image.Resampling.NEAREST)
        bg=Image.new('RGB',(280,320),(170,140,105));bg.paste(image,((280-image.width)//2,(320-image.height)//2),image)
        canvas.paste(bg,(10+n*300,25))
    return canvas

for aid in ('0x7000','0x7001','0x7B06'):
    ref,frames,rgb,leaf=next(m for m in models[aid] if m[0].endswith('G1'))
    rows=[]
    for cycle in (0,1,2,3,4,8,9,10,11,12):
        slots=leaf['cycles'][cycle];fi=slots[len(slots)//2]
        p=palette(scalar_palette(ramps[[30,47,57,12,39,21,3]]) if aid!='0x7B06' else rgb)
        rows.append(card(ref,fi,frames[fi],leaf,p,f'{aid} {ref} c{cycle} f{fi} : vanilla x2 / Q3m x2'))
    sheet=Image.new('RGB',(1200,1750))
    for n,image in enumerate(rows):sheet.paste(image,((n%2)*600,(n//2)*350))
    sheet.save(HERE/(aid[2:]+'-comparison.png'))

ref,frames,rgb,leaf=next(m for m in models['0x7001'] if m[0]=='MOGNG1')
sheet=Image.new('RGB',(1200,1050))
for y,hair in enumerate((0,3,20)):
    for x,fi in enumerate((119,129)):
        p=palette(scalar_palette(ramps[[30,47,57,12,39,21,hair]]))
        sheet.paste(card(ref,fi,frames[fi],leaf,p,f'hair={hair}, skin=12, frame={fi}, vanilla / Q3m'),(600*x,350*y))
sheet.save(HERE/'ogrillon-hair-palette-comparison.png')
# Compact comparison for the report.
compact=Image.new('RGB',(1200,350))
p=palette(scalar_palette(ramps[[30,47,57,12,39,21,0]]))
compact.paste(card(ref,129,frames[129],leaf,p,'Ogrillon hair=0, frame129 : vanilla / Q3m'),(0,0))
ref,frames,rgb,leaf=next(m for m in models['0x7B06'] if m[0]=='MWLSG1')
compact.paste(card(ref,49,frames[49],leaf,palette(rgb),'Wolf shadow frame49 : vanilla / Q3m'),(600,0))
compact.save(HERE/'comparison-detail.png')
(HERE/'analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({aid:dict(frames=m['frames'],alpha_mask_changes=m['special_mask_changed_pixels'][:2],black_reserved_2_3=m['special_counts_HD'][2:]) for aid,m in result['models'].items()}))
