"""Read-only Quadrant seam diagnosis; replay neutral CatmullRom, no GPU inference."""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import write_json
import palette_partner_registry as leaves,run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prior=HERE.parent/'q3m-monster-quadrant-full-x2-20261004-v1'
rr,works,_=source_plan(prior/'selection.json','monster_quadrant')
gen=load(prior/'current-generation.json'); assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
aid='0x1000'; source={r['resref']:r for r in rr if r['witness']['animation_id']==aid}
group=[source['MWYVG2'+str(i)] for i in range(1,5)]
leaf={r['resref']:leaves.inspect(assets/Path(cat['shards'][routes[(aid,r['resref'])]['shard_index']]['registry']).name,include_frames=True)['resources'][0] for r in group}

def weights(t):
    return [-.5*t**3+t*t-.5*t,1.5*t**3-2.5*t*t+1,-1.5*t**3+2*t*t+.5*t,.5*t**3-.5*t*t]

def sample(image,x,y):
    """Shader 16 taps, GL_NEAREST + CLAMP_TO_EDGE, straight alpha result."""
    data=image.astype(np.float64)/255; data[:,:,:3]*=data[:,:,3:4]
    bx=np.floor(x).astype(int); by=np.floor(y).astype(int)
    wx=weights(x-bx); wy=weights(y-by); out=np.zeros((*x.shape,4))
    for j in range(4):
        for i in range(4):
            tap=data[np.clip(by+j-1,0,image.shape[0]-1),np.clip(bx+i-1,0,image.shape[1]-1)]
            out+=tap*(wx[i]*wy[j])[:,:,None]
    a=np.clip(out[:,:,3:4],0,1); out[:,:,:3]=np.minimum(np.maximum(out[:,:,:3],0),a)/np.maximum(a,1e-12); out[:,:,3:4]=a
    return out

def background(image):
    return np.round(np.clip((image[:,:,:3]*image[:,:,3:4]+.26*(1-image[:,:,3:4]))*255,0,255)).astype(np.uint8)

records=[]; images=[]
for slot in range(10):
    rows=[r['frames'][r['cycles'][0][slot]] for r in group]; g=[r['geometry'] for r in rows]
    left=min(-a[2] for a in g); top=min(-a[3] for a in g); right=max(a[0]-a[2] for a in g); bottom=max(a[1]-a[3] for a in g)
    # Two source pixels of transparent surround. No modifications of packed assets.
    left-=2; top-=2; right+=2; bottom+=2; W=right-left; H=bottom-top
    canvases=[np.zeros((H*s,W*s,4),np.uint8) for s in (1,2)]; parts=[]
    for r,row,a in zip(group,rows,g):
        pal=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8))); pal[0]=0; pal[1,3]=127
        f=leaf[r['resref']]['frames'][row['frame_index']]
        pair=[pal[works[row['key']]['frame'].indices],r['profile'].decode(f['I'],f['F'],pal)]
        x=-a[2]-left; y=-a[3]-top
        parts.append((x,y,a[0],a[1],pair[1]))
        for s,im,c in zip((1,2),pair,canvases):
            dest=c[y*s:(y+a[1])*s,x*s:(x+a[0])*s]; m=im[:,:,3]>0; dest[m]=im[m]
    # Screenshot magnification is approximately five display pixels/native pixel.
    zoom=5; yy,xx=np.mgrid[:H*zoom,:W*zoom]; worldx=(xx+.5)/zoom; worldy=(yy+.5)/zoom
    separate=np.zeros((H*zoom,W*zoom,4)); separate[:,:,3]=1; separate[:,:,:3]=.26
    for x,y,w,h,im in parts:
        mask=(worldx>=x)&(worldx<x+w)&(worldy>=y)&(worldy<y+h)
        s=sample(im,(worldx-x)*2-.5,(worldy-y)*2-.5)
        separate[mask,:3]=s[mask,:3]*s[mask,3:4]+separate[mask,:3]*(1-s[mask,3:4])
    assembled=sample(canvases[1],worldx*2-.5,worldy*2-.5)
    native=np.array(Image.fromarray(canvases[0]).resize((W*zoom,H*zoom),Image.Resampling.NEAREST)).astype(float)/255
    separate_rgb=background(separate); assembled_rgb=background(assembled)
    # Difference is confined to support of the filter around internal splits.
    dx=abs(worldx-(-left)); dy=abs(worldy-(-40-top)); band=(dx<1.5)|(dy<1.5)
    visible=assembled[:,:,3]>.9
    diff=np.max(abs(separate_rgb.astype(int)-assembled_rgb.astype(int)),axis=2)
    def seam_jump(c,s,axis):
        cut=(-left if axis=='x' else -40-top)*s
        if axis=='x':
            a,b=c[:,cut-1],c[:,cut]; m=(a[:,3]==255)&(b[:,3]==255)
        else:
            a,b=c[cut-1],c[cut]; m=(a[:,3]==255)&(b[:,3]==255)
        delta=np.sqrt(np.mean((a[:,:3].astype(float)-b[:,:3].astype(float))**2,axis=1))
        return dict(opaque_pairs=int(m.sum()),mean_RGB_jump=float(delta[m].mean()) if m.any() else 0,max_RGB_jump=float(delta[m].max()) if m.any() else 0)
    record=dict(slot=slot,frame_indices=[r['frame_index'] for r in rows],geometry=g,internal_split_world=[0,-40],source_seam_x=seam_jump(canvases[0],1,'x'),source_seam_y=seam_jump(canvases[0],1,'y'),Q3m_seam_x=seam_jump(canvases[1],2,'x'),Q3m_seam_y=seam_jump(canvases[1],2,'y'),separate_vs_assembled_max_RGB_error=int(diff.max()),changed_opaque_seam_pixels=int(((diff>8)&visible&band).sum()),changed_opaque_interior_pixels=int(((diff>8)&visible&~band).sum()))
    records.append(record); images.append((background(native),separate_rgb,assembled_rgb))
    print(json.dumps(record),flush=True)
    if slot==2:
        sheet=Image.new('RGB',(W*zoom*3,H*zoom+28),(32,32,32)); draw=ImageDraw.Draw(sheet)
        for i,(label,im) in enumerate(zip(['Original / nearest','Q3m / four separate filters','Q3m / assembled then filtered'],images[-1])):
            draw.text((i*W*zoom+8,6),label,fill='white'); sheet.paste(Image.fromarray(im),(i*W*zoom,28))
        sheet.save(HERE/'filter-comparison.png')
    Image.fromarray(canvases[1]).save(HERE/('Q3m-slot-'+str(slot)+'.png'))
# Contact sheet: identify screenshot pose without asserting exact timestamp frame.
thumb=Image.new('RGB',(1000,5*240),(32,32,32)); draw=ImageDraw.Draw(thumb)
for slot,pair in enumerate(images):
    im=Image.fromarray(pair[1]); im.thumbnail((490,212),Image.Resampling.LANCZOS); x=slot%2*500; y=slot//2*240
    draw.text((x+5,y+5),'MWYVG2 seq0 slot '+str(slot),fill='white'); thumb.paste(im,(x+5,y+25))
thumb.save(HERE/'poses.png')
write_json(HERE/'analysis.json',dict(role='diagnostic-only-no-installation',source_generation=gen['production'],native_draw_layout='unbordered exact BAM extent, confirmed session 21:59:40',shader='neutral Stored/Sharpen0/CatmullRom, outline not simulated',records=records,recomputed_neural_targets=0,installed_files_changed=False))
