"""Six-frame CPU diagnostic: four nearby blend partners, unchanged eight fractions/K6."""
from pathlib import Path
import os,sys,json,hashlib,time
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
os.environ.setdefault('OMP_NUM_THREADS','4')
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_monster_contract import get_profile,CONTRACT
from reboutcx_quantize import srgb_u8_to_oklab
OUT=Path(__file__).parent;X4=ROOT/'sprite/.work/q3m-colour-comparison-x4-20261003-v1'
OLD=ROOT/'sprite/.work/q3m-colour-comparison-20261003-v1'
N16=ROOT/'sprite/.work/q3m16-colour-comparison-x4-20261003-v1'
comparison=json.loads((X4/'comparison.json').read_text(encoding='utf-8'))
oldcomp=json.loads((OLD/'comparison.json').read_text(encoding='utf-8'))
n16comp=json.loads((N16/'comparison.json').read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def colours(rgba):return len(np.unique(rgba[rgba[:,:,3]==255,:3],axis=0))

def partner_table(profile):
    lab=srgb_u8_to_oklab(profile.fitting[:,:,:3]);table=np.repeat(np.arange(256,dtype=np.uint8)[:,None],4,axis=1)
    for i in range(3,256):
        delta=lab[:,3:]-lab[:,i,None,:]
        distances=np.einsum('kic,kic->i',delta,delta)/6
        duplicate=np.all(profile.fitting[:,3:,:3]==profile.fitting[:,i,None,:3],axis=(0,2))
        distances[duplicate]=np.inf
        ranked=np.argsort(distances,kind='stable')+3
        assert ranked[0]==profile.succ[i], 'nearest-partner rule changed'
        table[i]=ranked[:4]
    assert np.array_equal(table[:,0],profile.succ)
    return table

def decode(profile,table,i,f,b,p):
    assert i.shape==f.shape==b.shape and np.all(f<8) and np.all(b<4)
    j=table[i,b];assert not np.any((f>0)&(p[i,3]!=p[j,3]))
    a,z=p[i,:3].astype(np.uint16),p[j,:3].astype(np.uint16);ff=f[...,None].astype(np.uint16)
    return np.dstack((((a*(8-ff)+z*ff+4)>>3).astype(np.uint8),np.where(i==0,0,p[i,3]).astype(np.uint8)))

def deps(table,i,f,b):
    bits=np.zeros(256,np.uint8);bits[np.unique(i)]=1;bits[np.unique(table[i[f>0],b[f>0]])]=1
    return np.packbits(bits,bitorder='little')

def encode(profile,table,g,old,targets):
    # Keep all old candidates first, then add nonzero fractions for partners 1..3.
    ci=np.concatenate([np.repeat(np.arange(3,256,dtype=np.uint8),n) for n in (8,7,7,7)])
    cf=np.concatenate([np.tile(np.arange(start,8,dtype=np.uint8),253) for start in (0,1,1,1)])
    cb=np.concatenate([np.full(253*n,b,np.uint8) for b,n in enumerate((8,7,7,7))])
    labs=np.stack([srgb_u8_to_oklab(decode(profile,table,ci[None],cf[None],cb[None],p)[0,:,:3]) for p in profile.fitting])
    # Euclidean distance expansion gives the same exhaustive K6 objective, cheaply.
    features=np.ascontiguousarray(labs.transpose(1,0,2).reshape(len(ci),18))
    norm=np.einsum('nc,nc->n',features,features)
    target_lab=srgb_u8_to_oklab(targets.astype(np.float64)*255).reshape(6,-1,3)
    target_features=np.ascontiguousarray(target_lab.transpose(1,0,2).reshape(-1,18))
    positions=np.flatnonzero(g.reshape(-1)>=3)
    i,f,b=g.copy(),np.zeros_like(g),np.zeros_like(g)
    check_positions=set(positions[np.linspace(0,len(positions)-1,min(32,len(positions)),dtype=int)].tolist())
    old_cost=np.zeros(g.size,np.float64);new_cost=np.zeros_like(old_cost)
    for start in range(0,len(positions),256):
        loc=positions[start:start+256];t=target_features[loc]
        cost=norm[None,:]-2*(t@features.T)
        choice=np.argmin(cost,axis=1)
        # Independent direct-distance check on samples of every frame.
        for offset,pixel in enumerate(loc):
            if int(pixel) in check_positions:
                direct=((features-t[offset])**2).sum(axis=1)
                assert direct[choice[offset]]<=direct.min()+1e-12
        i.reshape(-1)[loc],f.reshape(-1)[loc],b.reshape(-1)[loc]=ci[choice],cf[choice],cb[choice]
    for k,p in enumerate(profile.fitting):
        base=profile.decode(old['I'],old['F'],p)
        assert np.array_equal(base,decode(profile,table,old['I'],old['F'],np.zeros_like(g),p))
        expanded=decode(profile,table,i,f,b,p)
        for rgba,cost in ((base,old_cost),(expanded,new_cost)):
            delta=srgb_u8_to_oklab(rgba[:,:,:3]).reshape(-1,3)-target_lab[k]
            cost+=np.einsum('nc,nc->n',delta,delta)
    assert np.all(new_cost[positions]<=old_cost[positions]+1e-12)
    special=g<3;assert np.array_equal(i[special],g[special]) and not np.any(f[special]) and not np.any(b[special])
    assert np.array_equal(np.minimum(g,3),np.minimum(i,3))
    before,after=float(old_cost[positions].mean()/6),float(new_cost[positions].mean()/6)
    metrics=dict(k6_mean_squared_oklab_baseline=before,k6_mean_squared_oklab_4partners=after,
                 relative_k6_error_reduction_percent=100*(1-after/before),
                 exhaustive_candidates=len(ci),direct_distance_checks=len(check_positions),
                 every_material_pixel_objective_nonincreasing=True,old_candidates_embedded_exactly=True)
    return dict(guide=g.copy(),I=i,F=f,partner=b,dep=deps(table,i,f,b)),metrics

frames=[]
for fam in comparison['families']:
    slug=Path(fam['comparison_png']).name.split('-avant-q3m')[0]
    for sample in fam['samples']:
        path=ROOT/sample['encoded_cache'];assert sha(path)==sample['encoded_sha256']
        key=f"{slug}-{sample['resref']}-{sample['frame']}"
        frames.append(dict(key=key,slug=slug,family=fam,sample=sample,path=path,
                           targets=[path.parent/(key+f'-target-{k}.npz') for k in range(6)]))
recipe=dict(role='offline-six-frame-four-partners-experiment-not-V6',scale=4,k=6,fraction_steps=8,partners=4,
            partner_rule='four nearest distinct material RGB vectors across K6; mean squared OKLab f64; ties lowest index; partner zero unchanged',
            objective='exhaustive squared OKLab f64 via Euclidean distance expansion; direct-distance sample verification',
            retained='native fixed palettes, alpha, shadow, classes, xBR4 guide, same direct ReboutCX targets; no dithering',
            source_comparison_sha256=sha(X4/'comparison.json'),profiles_sha256=sha(CONTRACT.parent/'profiles.json'),
            script_sha256=sha(Path(__file__)),GPU_inference=False,runtime_compatible=False,
            target_hashes={str(p.relative_to(ROOT)):sha(p) for d in frames for p in d['targets']})
namespace=hashlib.sha256(json.dumps(recipe,sort_keys=True).encode()).hexdigest()
CACHE=OUT/'cache'/namespace;CACHE.mkdir(parents=True,exist_ok=True);write_json(CACHE/'recipe.json',recipe)
print(json.dumps(dict(stage='targets-reused',frames=6,neural_targets=36,namespace=namespace)),flush=True)
for d in frames:
    s=d['sample'];profile=get_profile(s['profile_id']);table=partner_table(profile)
    with np.load(d['path'],allow_pickle=False) as data:old={k:data[k].copy() for k in data.files}
    g=old['guide'];profile.check_contract(g,old['I'],old['F'],old['dep'])
    ts=[]
    for path in d['targets']:
        with np.load(path,allow_pickle=False) as data:ts.append(data['x4'].copy())
    targets=np.stack(ts);assert targets.dtype==np.float32 and targets.shape==(6,*g.shape,3)
    assert np.isfinite(targets).all() and np.all((targets>=0)&(targets<=1))
    started=time.perf_counter();data,error=encode(profile,table,g,old,targets)
    rgba=decode(profile,table,data['I'],data['F'],data['partner'],profile.fitting[0])
    baseline=np.asarray(Image.open(ROOT/s['png']).convert('RGBA'))
    assert np.array_equal(baseline[:,:,3],rgba[:,:,3])
    cache=CACHE/(d['key']+'-4partners.npz');np.savez_compressed(cache,**data,table=table)
    png=OUT/(d['key']+'-q3m-x4-4partners-rgba.png');Image.fromarray(rgba,'RGBA').save(png)
    d['rgba']=rgba;d['metrics']=dict(resref=s['resref'],frame=s['frame'],cycle=s['cycle'],profile_id=s['profile_id'],
        source_geometry=s['source_geometry'],source_sha256=s['source_sha256'],q3m_x4_baseline_colours=colours(baseline),
        q3m_x4_4partners_colours=colours(rgba),alpha_identical=True,
        opaque_rgb_absolute_difference_mean=float(np.abs(rgba[:,:,:3].astype(np.int16)-baseline[:,:,:3].astype(np.int16))[rgba[:,:,3]==255].mean()),
        extra_partner_material_pixels=int(np.count_nonzero((data['partner']>0)&(g>=3))),
        encoded=str(cache.relative_to(ROOT)),png=str(png.relative_to(ROOT)),png_sha256=sha(png),**error)
    print(json.dumps(dict(stage='frame-ready',frame=d['key'],seconds=time.perf_counter()-started,
        colours=[colours(baseline),colours(rgba)],error_reduction_percent=error['relative_k6_error_reduction_percent'])),flush=True)

FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22);SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def checker(w,h):
    y,x=np.indices((h,w));rgb=np.where(((x//16+y//16)%2)[:,:,None],np.array([53,56,61]),np.array([42,45,50])).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,np.full((h,w),255,np.uint8))),'RGBA')
report=dict(recipe=recipe,frames=6,installation_changed=False,registries_changed=False,QA_changed=False,
            colour_count='distinct opaque RGB before compositing',families=[])
for fam in comparison['families']:
    selected=[d for d in frames if d['family'] is fam];slug=selected[0]['slug']
    prior_fam=next(f for f in n16comp['families'] if f['target']==fam['target'])
    prior=Image.open(ROOT/prior_fam['comparison_png']).convert('RGB');assert prior.width%4==0
    tw=prior.width//4;canvas=Image.new('RGB',(tw*5,prior.height),(25,27,31));canvas.paste(prior,(0,0))
    draw=ImageDraw.Draw(canvas);draw.text((4*tw+20,47),'Q3m x4 — 4 partenaires / 8 niveaux',font=FONT,fill='white')
    row_y=138;oldfam=next(f for f in oldcomp['families'] if f['target']==fam['target'])
    for d in selected:
        s=d['sample'];w,h=s['source_geometry'][:2];img=Image.fromarray(d['rgba'],'RGBA');full_h=h*8+64;x=tw*4
        tile=checker(tw,full_h);full=img.resize((w*8,h*8),Image.Resampling.NEAREST)
        tile.alpha_composite(full,((tw-full.width)//2,48));canvas.paste(tile.convert('RGB'),(x,row_y))
        draw.text((x+16,row_y+8),f"{s['resref']} / frame {s['frame']} / cycle {s['cycle']} — {d['metrics']['q3m_x4_4partners_colours']} couleurs",font=SMALL,fill='white')
        original=next(r for r in oldfam['samples'] if r['resref']==s['resref'] and r['frame']==s['frame'])
        detail=img.crop(tuple(v*2 for v in original['crop']));detail=detail.resize((detail.width*4,detail.height*4),Image.Resampling.NEAREST)
        tile=checker(tw,detail.height+40);tile.alpha_composite(detail,((tw-detail.width)//2,30));canvas.paste(tile.convert('RGB'),(x,row_y+full_h+8))
        draw.text((x+16,row_y+full_h+12),'Même région — détail à taille égale',font=SMALL,fill='white');row_y+=h*8+420
    path=OUT/(slug+'-comparatif-5-traitements.png');canvas.save(path)
    report['families'].append(dict(target=fam['target'],old_method=fam['old_method'],comparison_png=str(path.relative_to(ROOT)),samples=[d['metrics'] for d in selected]))
    print(json.dumps(dict(stage='comparison-ready',path=str(path))),flush=True)
write_json(OUT/'comparison.json',report)
