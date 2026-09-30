import sys, json, glob, os, numpy as np
sys.path.insert(0, r'G:/AI/BG2_Upscale/pipeline/scripts')
from run_creature_sprite_x2 import load_source_frames
from reboutcx_quantize import character_chmb1_classes
root=r'G:/AI/BG2_Upscale/sprite/families/playable-characters/6110-human-female-fighter'
classes=character_chmb1_classes(); cls=np.full(256,-1); names=list(classes)
for i,n in enumerate(names):
    for v in classes[n]: cls[v]=i
out={}
for man in sorted(glob.glob(root+'/*/source/manifest.json')):
    comp=os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(man))))
    frames,resources,_=load_source_frames(__import__('pathlib').Path(man))
    hist=np.zeros(256,np.int64); perframe=[]; pal_hashes=set(); nf=0; nnull=0; px=0
    for f in frames:
        pal_hashes.add(f.palette.tobytes().__hash__())
        if f.width==1 and f.height==1 and int(f.indices[0,0])==2: nnull+=1; continue
        nf+=1
        h=np.bincount(f.indices.ravel(),minlength=256); h[f.transparent]=0; hist+=h; px+=h.sum()
        used=np.flatnonzero(h)
        # per class distinct shades used this frame
        d={}
        for u in used:
            c=names[cls[u]]; d[c]=d.get(c,0)+1
        perframe.append(d)
    used=np.flatnonzero(hist)
    per_class={}
    for u in used:
        c=names[cls[u]]; per_class.setdefault(c,{'indices':[],'pixels':0}); per_class[c]['indices'].append(int(u)); per_class[c]['pixels']+=int(hist[u])
    # per-frame shade counts for ranges
    pf={}
    for d in perframe:
        for c,v in d.items(): pf.setdefault(c,[]).append(v)
    pfm={c:(float(np.median(v)),int(np.min(v)),int(np.max(v))) for c,v in pf.items()}
    out[comp]={'frames':nf,'null_frames':nnull,'visible_px':int(px),'palettes':len(pal_hashes),'transparent':int(frames[0].transparent),
               'classes':{c:{'n':len(v['indices']),'share':round(v['pixels']/px,4),'idx':v['indices'],'perframe_median_min_max':pfm.get(c)} for c,v in per_class.items()}}
    top=sorted(out[comp]['classes'].items(),key=lambda kv:-kv[1]['share'])
    print(comp, 'frames',nf,'null',nnull,'pals',len(pal_hashes),'| '+'; '.join(f"{c}:{v['n']}sh {v['share']*100:.1f}% pf{v['perframe_median_min_max'][0]:.0f}" for c,v in top[:9]))
json.dump(out,open(sys.argv[1]+'/usage_6110.json','w'),indent=1)
