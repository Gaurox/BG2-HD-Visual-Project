"""CPU-only 16-fraction experiment on six existing x4 frames; no V6/runtime changes."""
from pathlib import Path
import hashlib,json,sys,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_monster_contract import get_profile,CONTRACT
from reboutcx_quantize import srgb_u8_to_oklab

OUT=Path(__file__).parent
X4=ROOT/'sprite/.work/q3m-colour-comparison-x4-20261003-v1'
OLD=ROOT/'sprite/.work/q3m-colour-comparison-20261003-v1'
comparison=json.loads((X4/'comparison.json').read_text(encoding='utf-8'))
old_comparison=json.loads((OLD/'comparison.json').read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def colours(rgba):return len(np.unique(rgba[rgba[:,:,3]==255,:3],axis=0))
def save_npz(path,**data):
    tmp=path.with_suffix('.part')
    with tmp.open('wb') as s:np.savez_compressed(s,**data)
    tmp.replace(path)

def decode16(profile,i,f,palette):
    assert i.dtype==f.dtype==np.uint8 and i.shape==f.shape and np.all(f<16)
    assert not np.any((i<3)&(f!=0))
    assert not np.any((f>0)&(palette[i,3]!=palette[profile.succ[i],3]))
    a,b=palette[i,:3].astype(np.uint16),palette[profile.succ[i],:3].astype(np.uint16)
    frac=f[...,None].astype(np.uint16)
    rgb=((a*(16-frac)+b*frac+8)>>4).astype(np.uint8)
    return np.dstack((rgb,np.where(i==0,0,palette[i,3]).astype(np.uint8)))

def dep_mask(profile,i,f):
    bits=np.zeros(256,np.uint8);bits[np.unique(i)]=1;bits[np.unique(profile.succ[i[f>0]])]=1
    return np.packbits(bits,bitorder='little')

def validate16(profile,guide,data):
    i,f=data['I'],data['F']
    assert np.array_equal(data['guide'],guide) and i.shape==f.shape==guide.shape
    assert i.dtype==f.dtype==guide.dtype==np.uint8 and np.all(f<16)
    assert np.array_equal(np.minimum(i,3),np.minimum(guide,3))
    special=guide<3;assert np.array_equal(i[special],guide[special]) and np.all(f[special]==0)
    assert np.array_equal(data['dep'],dep_mask(profile,i,f))

def encode16(profile,g,targets):
    ci=np.repeat(np.arange(3,256,dtype=np.uint8),16)
    cf=np.tile(np.arange(16,dtype=np.uint8),253)
    labs=np.stack([srgb_u8_to_oklab(decode16(profile,ci[None],cf[None],p)[0,:,:3]) for p in profile.fitting])
    target_lab=srgb_u8_to_oklab(targets.astype(np.float64)*255).reshape(6,-1,3)
    i,f=g.copy(),np.zeros_like(g);positions=np.flatnonzero(g.reshape(-1)>=3)
    for start in range(0,len(positions),128):
        loc=positions[start:start+128];cost=np.zeros((len(loc),len(ci)),np.float64)
        for k in range(6):
            delta=target_lab[k,loc,None,:]-labs[k,None,:,:]
            cost+=np.einsum('nci,nci->nc',delta,delta,optimize=True)
        choice=np.argmin(cost,axis=1)
        i.reshape(-1)[loc],f.reshape(-1)[loc]=ci[choice],cf[choice]
    data=dict(guide=g.copy(),I=i,F=f,dep=dep_mask(profile,i,f));validate16(profile,g,data)
    return data

def errors(profile,g,old,new,targets):
    positions=g>=3;before=np.zeros(g.shape,np.float64);after=np.zeros_like(before)
    target_lab=srgb_u8_to_oklab(targets.astype(np.float64)*255)
    # Every old 1/8 fraction is represented exactly by an even 1/16 fraction.
    for k,p in enumerate(profile.fitting):
        original=profile.decode(old['I'],old['F'],p)
        assert np.array_equal(original,decode16(profile,old['I'],old['F']*2,p))
        enhanced=decode16(profile,new['I'],new['F'],p)
        for rgba,cost in ((original,before),(enhanced,after)):
            delta=srgb_u8_to_oklab(rgba[:,:,:3])-target_lab[k]
            cost+=np.einsum('...c,...c->...',delta,delta,optimize=True)
    assert np.all(after[positions]<=before[positions]+1e-12),'expanded candidate set worsened K6 objective'
    mean8,mean16=float(before[positions].mean()/6),float(after[positions].mean()/6)
    return dict(k6_mean_squared_oklab_8=mean8,k6_mean_squared_oklab_16=mean16,
                relative_k6_error_reduction_percent=100*(1-mean16/mean8) if mean8 else 0,
                objective_nonincreasing_every_material_pixel=True,old_candidates_exactly_embedded=True,
                material_pixels=int(np.count_nonzero(positions)))

frames=[]
for fam in comparison['families']:
    slug=Path(fam['comparison_png']).name.split('-avant-q3m')[0]
    for sample in fam['samples']:
        encoded=ROOT/sample['encoded_cache'];assert sha(encoded)==sample['encoded_sha256']
        key=f"{slug}-{sample['resref']}-{sample['frame']}"
        targets=[encoded.parent/(key+f'-target-{k}.npz') for k in range(6)]
        frames.append(dict(key=key,slug=slug,family=fam,sample=sample,encoded=encoded,targets=targets))
recipe=dict(role='offline-six-frame-16-fraction-experiment-not-V6',scale=4,k=6,fraction_steps=16,
            decode='((16-F)*P[I] + F*P[succ[I]] + 8) >> 4; primary live alpha',
            candidate_order='I=3..255 ascending, F=0..15 ascending; minimum sum K6 squared OKLab f64',
            retained='same successor table, fixed palettes, semantic classes, xBR4 guide, direct float32 ReboutCX targets, no dithering',
            source_comparison_sha256=sha(X4/'comparison.json'),profile_sha256=sha(CONTRACT.parent/'profiles.json'),
            profile_code_sha256=sha(ROOT/'pipeline/scripts/palette_monster_contract.py'),
            colour_kernel_sha256=sha(ROOT/'pipeline/scripts/reboutcx_quantize.py'),test_code_sha256=sha(Path(__file__)),
            target_hashes={str(p.relative_to(ROOT)):sha(p) for d in frames for p in d['targets']},
            GPU_inference=False,runtime_compatible=False)
namespace=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()
CACHE=OUT/'cache'/namespace;CACHE.mkdir(parents=True,exist_ok=True)
write_json(CACHE/'recipe.json',recipe)
print(json.dumps(dict(stage='targets-reused',frames=len(frames),neural_targets=36,namespace=namespace)),flush=True)
for d in frames:
    sample=d['sample'];profile=get_profile(sample['profile_id'])
    with np.load(d['encoded'],allow_pickle=False) as data:old={k:data[k].copy() for k in data.files}
    g=old['guide'];profile.check_contract(g,old['I'],old['F'],old['dep'])
    targets=[]
    for p in d['targets']:
        with np.load(p,allow_pickle=False) as data:targets.append(data['x4'].copy())
    targets=np.stack(targets)
    assert targets.dtype==np.float32 and targets.shape==(6,*g.shape,3) and np.isfinite(targets).all()
    assert np.all((targets>=0)&(targets<=1))
    cache=CACHE/(d['key']+'-16steps.npz')
    if cache.exists():
        with np.load(cache,allow_pickle=False) as data:encoded={k:data[k].copy() for k in data.files}
    else:
        started=time.perf_counter();encoded=encode16(profile,g,targets);save_npz(cache,**encoded)
        print(json.dumps(dict(stage='encoded16',frame=d['key'],seconds=time.perf_counter()-started)),flush=True)
    validate16(profile,g,encoded)
    error=errors(profile,g,old,encoded,targets)
    rgba=decode16(profile,encoded['I'],encoded['F'],profile.fitting[0])
    original=np.asarray(Image.open(ROOT/sample['png']).convert('RGBA'))
    assert np.array_equal(original,profile.decode(old['I'],old['F'],profile.fitting[0]))
    assert np.array_equal(original[:,:,3],rgba[:,:,3])
    different=(original[:,:,:3]!=rgba[:,:,:3]).any(axis=2)&(rgba[:,:,3]==255)
    rgb_delta=np.abs(original[:,:,:3].astype(np.int16)-rgba[:,:,:3].astype(np.int16))
    png=OUT/(d['key']+'-q3m-x4-16steps-rgba.png');Image.fromarray(rgba,'RGBA').save(png)
    d['rgba']=rgba
    d['metrics']=dict(resref=sample['resref'],frame=sample['frame'],cycle=sample['cycle'],profile_id=sample['profile_id'],
                     source_sha256=sample['source_sha256'],source_geometry=sample['source_geometry'],
                     q3m_x4_8steps_colours=colours(original),q3m_x4_16steps_colours=colours(rgba),
                     alpha_identical=True,opaque_pixels_changed=int(np.count_nonzero(different)),
                     opaque_rgb_absolute_difference_mean=float(rgb_delta[rgba[:,:,3]==255].mean()),
                     png=str(png.relative_to(ROOT)),png_sha256=sha(png),encoded=str(cache.relative_to(ROOT)),**error)
    print(json.dumps(dict(stage='frame-ready',frame=d['key'],colours=[colours(original),colours(rgba)],
                          k6_error_reduction_percent=error['relative_k6_error_reduction_percent'])),flush=True)

FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def checker(w,h):
    y,x=np.indices((h,w));dark=(x//16+y//16)%2
    rgb=np.where(dark[:,:,None],np.array([53,56,61]),np.array([42,45,50])).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,np.full((h,w),255,np.uint8))),'RGBA')
report=dict(recipe=recipe,frames=6,GPU_inference=False,installation_changed=False,registries_changed=False,
            QA_changed=False,colours='distinct RGB on opaque pixels before compositing',families=[])
for fam in comparison['families']:
    selected=[d for d in frames if d['family'] is fam];slug=selected[0]['slug']
    prior=Image.open(ROOT/fam['comparison_png']).convert('RGB');assert prior.width%3==0
    tw=prior.width//3;canvas=Image.new('RGB',(tw*4,prior.height),(25,27,31));canvas.paste(prior,(0,0))
    draw=ImageDraw.Draw(canvas);draw.text((3*tw+20,47),'Q3m K6 x4 — test 16 niveaux',font=FONT,fill='white')
    # Identify the standard x4 reference explicitly without changing its pixels.
    draw.rectangle((2*tw,40,3*tw,78),fill=(25,27,31))
    draw.text((2*tw+20,47),'Q3m K6 x4 — 8 niveaux',font=FONT,fill='white')
    row_y=138;oldfam=next(f for f in old_comparison['families'] if f['target']==fam['target'])
    for d in selected:
        s=d['sample'];w,h=s['source_geometry'][:2];img=Image.fromarray(d['rgba'],'RGBA');full_h=h*8+64;x=tw*3
        tile=checker(tw,full_h);full=img.resize((w*8,h*8),Image.Resampling.NEAREST)
        tile.alpha_composite(full,((tw-full.width)//2,48));canvas.paste(tile.convert('RGB'),(x,row_y))
        draw.text((x+16,row_y+8),f"{s['resref']} / frame {s['frame']} / cycle {s['cycle']} — {d['metrics']['q3m_x4_16steps_colours']} couleurs",font=SMALL,fill='white')
        osample=next(r for r in oldfam['samples'] if r['resref']==s['resref'] and r['frame']==s['frame'])
        detail=img.crop(tuple(v*2 for v in osample['crop']));detail=detail.resize((detail.width*4,detail.height*4),Image.Resampling.NEAREST)
        dt=checker(tw,detail.height+40);dt.alpha_composite(detail,((tw-detail.width)//2,30));canvas.paste(dt.convert('RGB'),(x,row_y+full_h+8))
        draw.text((x+16,row_y+full_h+12),'Même région — détail à taille égale',font=SMALL,fill='white')
        row_y+=h*8+420
    png=OUT/(slug+'-comparatif-q3m-16-niveaux.png');canvas.save(png)
    report['families'].append(dict(target=fam['target'],old_method=fam['old_method'],comparison_png=str(png.relative_to(ROOT)),samples=[d['metrics'] for d in selected]))
    print(json.dumps(dict(stage='comparison-ready',path=str(png))),flush=True)
write_json(OUT/'comparison.json',report)
