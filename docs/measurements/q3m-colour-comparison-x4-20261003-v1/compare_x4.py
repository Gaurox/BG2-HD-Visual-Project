"""Six-frame Q3m x4 diagnostic; scoped GPU inference, unchanged x2/runtime/registries."""
from pathlib import Path
from collections import defaultdict
import os,sys,json,hashlib,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_oracle import read_bam_p8
from palette_monster_contract import get_profile, CONTRACT
from reboutcx_batch import load_model,prepare_inference_rgb
from reboutcx_batch_p12 import infer_float_crops
from reboutcx_multipal import inference_context,save_npz
from workspace_paths import get_path
import run_creature_sprite_x2 as registry

OUT=Path(__file__).parent
PREVIOUS=ROOT/'sprite/.work/q3m-colour-comparison-20261003-v1'
comparison=json.loads((PREVIOUS/'comparison.json').read_text(encoding='utf-8'))
resources={r['resref']:r for r in json.loads(CONTRACT.read_text())['resources']}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def colours(rgba):return len(np.unique(rgba[rgba[:,:,3]==255,:3],axis=0))
def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import torch
torch.set_num_threads(4)
torch.backends.cudnn.deterministic=True
torch.use_deterministic_algorithms(True)
context=inference_context()
assert context==json.loads((ROOT/'sprite/.work/q3m-monster-pilot-x2-20261003-v1/backend.json').read_text()), 'x2 acquired inference contract changed'
scalepix=get_path('mmpx_scalepix',required=True)
recipe=dict(role='six-frame-offline-comparison-only',scale=4,k=6,source='indexed native BAM; not enlarged x2 PNG',
            inference=context,target='direct x4 float32 crop; no downscale',
            encoder='monster-fixed-exhaustive-oklab-f64-integer-k6-v1',rule=2,
            guide=registry.direct_upscale_contract(4).method,dither=False,boundary_mixing=False,
            contract_sha256=sha(CONTRACT),profiles_sha256=sha(CONTRACT.parent/'profiles.json'),
            code={name:sha(ROOT/'pipeline/scripts'/name) for name in ('palette_monster_contract.py','reboutcx_quantize.py','run_creature_sprite_x2.py','xbr2x_batch.js')},
            scalepix_sha256=sha(scalepix),comparison_source_sha256=sha(PREVIOUS/'comparison.json'))
namespace=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()
CACHE=OUT/'cache'/namespace;CACHE.mkdir(parents=True,exist_ok=True)
if (CACHE/'recipe.json').exists():assert json.loads((CACHE/'recipe.json').read_text())==recipe
else:write_json(CACHE/'recipe.json',recipe)

frames=[]
for fam in comparison['families']:
    slug=Path(fam['comparison_png']).name.split('-avant-apres')[0]
    for sample in fam['samples']:
        ref,n=sample['resref'],sample['frame'];r=resources[ref]
        native=read_bam_p8((ROOT/r['source']).read_bytes());s=native['frames'][n]
        assert hashlib.sha256(native['canonical']).hexdigest()==sample['source_sha256']
        assert [s['width'],s['height'],s['center_x'],s['center_y'],native['transparent']]==sample['native_geometry']
        indices=s['indices'];palette=native['palette_rgb'];rgba=np.dstack((palette[indices],np.where(indices==0,0,255).astype(np.uint8)))
        frame=registry.SourceFrame(ref,n,s['width'],s['height'],s['center_x'],s['center_y'],0,indices,palette,rgba.tobytes())
        key=f'{slug}-{ref}-{n}'
        frames.append(dict(key=key,slug=slug,family=fam,sample=sample,frame=frame,profile=get_profile(r['palette_profile_id'])))

missing=[d for d in frames if not (CACHE/(d['key']+'-guide.npz')).exists()]
if missing:
    outputs=registry.run_xbr([d['frame'] for d in missing],scalepix,'node',registry.direct_upscale_contract(4))
    for d,(w,h,rgba) in zip(missing,outputs,strict=True):
        fr=d['frame'];assert (w,h)==(fr.width*4,fr.height*4)
        provenance=registry.xbr_provenance_indices(fr,4) if registry.has_duplicate_used_rgba_indices(fr) else None
        g,_=registry.map_output(fr,rgba,provenance);save_npz(CACHE/(d['key']+'-guide.npz'),guide=g.reshape(h,w))
print(json.dumps(dict(stage='guides-ready',frames=len(frames),scale=4,namespace=namespace)),flush=True)

pending=defaultdict(list)
for d in frames:
    fr=d['frame'];canvas=((fr.height+31)//32*32,(fr.width+31)//32*32)
    for k in range(6):
        path=CACHE/(d['key']+f'-target-{k}.npz')
        if not path.exists():pending[canvas].append((d,k,path))
descriptor=None;targets_generated=0;timings=[]
if pending:descriptor,_=load_model(get_path('reboutcx_model',required=True),device='cuda:0',fp16=True)
for canvas,requests in sorted(pending.items()):
    for start in range(0,len(requests),86):
        batch=requests[start:start+86]
        rgb=[prepare_inference_rgb(d['frame'],d['profile'].fitting[k,:,:3]) for d,k,_ in batch]
        crops,elapsed=infer_float_crops(descriptor,rgb,canvas=canvas,fp16=True)
        for (d,k,path),crop in zip(batch,crops,strict=True):
            assert crop.shape==(d['frame'].height*4,d['frame'].width*4,3) and crop.dtype==np.float32
            save_npz(path,x4=crop)
        targets_generated+=len(batch);timings.append(dict(canvas=list(canvas),real_targets=len(batch),timing=elapsed))
        print(json.dumps(dict(stage='targets',generated=targets_generated,real_targets=len(batch),canvas=canvas)),flush=True)
del descriptor
torch.cuda.empty_cache()

for d in frames:
    path=CACHE/(d['key']+'-encoded.npz');profile=d['profile'];fr=d['frame']
    with np.load(CACHE/(d['key']+'-guide.npz'),allow_pickle=False) as data:g=data['guide'].copy()
    if not path.exists():
        targets=[]
        for k in range(6):
            with np.load(CACHE/(d['key']+f'-target-{k}.npz'),allow_pickle=False) as data:targets.append(data['x4'].copy())
        started=time.perf_counter();encoded=profile.encode(g,np.stack(targets));save_npz(path,**encoded)
        print(json.dumps(dict(stage='encoded',frame=d['key'],seconds=time.perf_counter()-started)),flush=True)
    with np.load(path,allow_pickle=False) as data:encoded={k:data[k].copy() for k in data.files}
    profile.check_contract(encoded['guide'],encoded['I'],encoded['F'],encoded['dep'])
    assert np.array_equal(encoded['guide'],g) and g.shape==(fr.height*4,fr.width*4)
    rgba=profile.decode(encoded['I'],encoded['F'],profile.fitting[0])
    assert np.array_equal(rgba[:,:,3],profile.fitting[0,g,3]),'guide/live alpha changed'
    d['x4']=rgba
    Image.fromarray(rgba,'RGBA').save(OUT/(d['key']+'-q3m-x4-rgba.png'))
    d['metrics']=dict(resref=fr.resref,frame=fr.index,cycle=d['sample']['cycle'],
                     source_sha256=d['sample']['source_sha256'],source_geometry=d['sample']['native_geometry'],
                     x4_size=[rgba.shape[1],rgba.shape[0]],profile_id=profile.profile_id,
                     before_colours=d['sample']['before_colours'],q3m_x2_colours=d['sample']['q3m_colours'],q3m_x4_colours=colours(rgba),
                     q3m_x4_fractional_opaque_pixels=int(np.count_nonzero((encoded['F']>0)&(rgba[:,:,3]==255))),
                     encoded_cache=str(path.relative_to(ROOT)),encoded_sha256=sha(path),png=str((OUT/(d['key']+'-q3m-x4-rgba.png')).relative_to(ROOT)))

FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def checker(w,h):
    y,x=np.indices((h,w));dark=(x//16+y//16)%2
    rgb=np.where(dark[:,:,None],np.array([53,56,61]),np.array([42,45,50])).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,np.full((h,w),255,np.uint8))),'RGBA')

report=dict(role='offline-diagnostic-not-ingame-QA',scale=4,k=6,frames=len(frames),
            recipe=recipe,cache_namespace=namespace,neural_targets_generated=targets_generated,inference_timings=timings,
            colours='distinct RGB on opaque pixels before compositing; same native neutral palette',
            display='equal physical size; x2 nearest x4 and x4 nearest x2 = native x8; details x2 nearest x8, x4 nearest x4 = native x16',
            installation_changed=False,registries_changed=False,QA_changed=False,families=[])
for family in comparison['families']:
    selected=[d for d in frames if d['family'] is family];slug=selected[0]['slug']
    tw=max(520,max(d['frame'].width*8+48 for d in selected))
    row_heights=[d['frame'].height*8+420 for d in selected]
    canvas=Image.new('RGB',(tw*3,138+sum(row_heights)),(25,27,31));draw=ImageDraw.Draw(canvas)
    draw.text((20,10),family['target']+' — mêmes frames, palette neutre, PNG sans perte',font=FONT,fill='white')
    labels=[family['old_method'],'Q3m K6 x2','Q3m K6 x4 direct']
    for col,label in enumerate(labels):draw.text((tw*col+20,47),label,font=FONT,fill='white')
    draw.text((20,88),'Taille égale : pixels x2 agrandis x4 / pixels x4 agrandis x2. Détails : x8 / x4. Aucun lissage.',font=SMALL,fill=(210,210,210))
    row_y=138
    for d in selected:
        fr=d['frame'];full_h=fr.height*8+64
        before=np.asarray(Image.open(PREVIOUS/(d['key']+'-avant-rgba.png')).convert('RGBA'))
        x2=np.asarray(Image.open(PREVIOUS/(d['key']+'-q3m-rgba.png')).convert('RGBA'))
        assert colours(before)==d['metrics']['before_colours'] and colours(x2)==d['metrics']['q3m_x2_colours']
        images=[before,x2,d['x4']];counts=[d['metrics'][k] for k in ('before_colours','q3m_x2_colours','q3m_x4_colours')]
        for col,(rgba,num) in enumerate(zip(images,counts)):
            x=tw*col;img=Image.fromarray(rgba,'RGBA');tile=checker(tw,full_h)
            full=img.resize((fr.width*8,fr.height*8),Image.Resampling.NEAREST)
            tile.alpha_composite(full,((tw-full.width)//2,48));canvas.paste(tile.convert('RGB'),(x,row_y))
            draw.text((x+16,row_y+8),f'{fr.resref} / frame {fr.index} / cycle {d["sample"]["cycle"]} — {num} couleurs',font=SMALL,fill='white')
            crop=tuple(v*(2 if col==2 else 1) for v in d['sample']['crop'])
            detail=img.crop(crop);zoom=4 if col==2 else 8
            detail=detail.resize((detail.width*zoom,detail.height*zoom),Image.Resampling.NEAREST)
            dt=checker(tw,detail.height+40);dt.alpha_composite(detail,((tw-detail.width)//2,30))
            canvas.paste(dt.convert('RGB'),(x,row_y+full_h+8))
            draw.text((x+16,row_y+full_h+12),'Même région — détail à taille égale',font=SMALL,fill='white')
        row_y+=fr.height*8+420
    image_path=OUT/(slug+'-avant-q3m-x2-x4.png');canvas.save(image_path)
    record=dict(target=family['target'],old_method=family['old_method'],comparison_png=str(image_path.relative_to(ROOT)),samples=[d['metrics'] for d in selected])
    report['families'].append(record)
    print(json.dumps(dict(stage='comparison-ready',target=family['target'],path=str(image_path),colours=counts)),flush=True)
write_json(OUT/'comparison.json',report)
