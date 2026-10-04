"""Small contextual Q3m seam probe; immutable production/cache/game untouched."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4');os.environ.setdefault('OMP_NUM_THREADS','4')
import ast,hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,load_model
from palette_work_plan import file_sha,write_json
from reboutcx_batch_p12 import pack_normalized
from workspace_paths import get_path
from chainner_ext import resize,ResizeFilter
import torch
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prior=HERE.parent/'q3m-monster-quadrant-full-x2-20261004-v1'; prod=load(prior/'production.json')
rr,works,_=source_plan(prior/'selection.json','monster_quadrant'); source={(r['witness']['animation_id'],r['resref']):r for r in rr}
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'; encoded=cache/'encoded'/prod['encoder_namespace']
backend=load(cache/'backend.json'); bk=hashlib.sha256(json.dumps(backend,sort_keys=True).encode()).digest()
assert file_sha(get_path('reboutcx_model',required=True))==backend['model_sha256']
# Replay exactly the diagnostic filter functions without running its main loop.
namespace=dict(np=np);tree=ast.parse((HERE/'analyze.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('sample','weights','background')],type_ignores=[]),str(HERE/'analyze.py'),'exec'),namespace)
sample=namespace['sample'];background=namespace['background']
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8'); torch.set_num_threads(4)
torch.backends.cudnn.deterministic=True;torch.use_deterministic_algorithms(True)
model,_=load_model(get_path('reboutcx_model',required=True),device='cuda:0',fp16=True)
cases=[('0x1000','MWYV',0,1),('0x1000','MWYV',0,2),('0x1000','MWYV',0,3),('0x1000','MWYV',4,2),('0x1004','MWYV',0,2),('0x1100','MTAN',0,2)]
records=[];work=HERE/'work';work.mkdir(exist_ok=True)
for aid,prefix,seq,slot in cases:
    group=[source[(aid,prefix+'G2'+str(i))] for i in range(1,5)]
    assert all(seq<len(r['cycles']) and slot<len(r['cycles'][seq]) for r in group)
    rows=[r['frames'][r['cycles'][seq][slot]] for r in group]; geom=[r['geometry'] for r in rows]
    nonempty=[a for a in geom if a[0]*a[1]]
    left=min(-a[2] for a in nonempty); top=min(-a[3] for a in nonempty); right=max(a[0]-a[2] for a in nonempty); bottom=max(a[1]-a[3] for a in nonempty)
    W=right-left;H=bottom-top; rgb=np.zeros((6,H,W,3),np.uint8); mask=np.zeros((H,W),bool)
    for r,row,a in zip(group,rows,geom):
        native=works[row['key']]['frame'].indices;m=native!=0;x=-a[2]-left;y=-a[3]-top
        for k in range(6):rgb[k,y:y+a[1],x:x+a[0]][m]=r['profile'].fitting[k][native][m]
        mask[y:y+a[1],x:x+a[0]]|=m
    nearest=distance_transform_edt(~mask,return_distances=False,return_indices=True)
    inputs=[np.ascontiguousarray(im[tuple(nearest)]) for im in rgb]
    canvas=(((H+31)//32)*32,((W+31)//32)*32)
    # Experimental batch six, not the production batch86/cache identity.
    tensor=torch.from_numpy(pack_normalized(inputs,*canvas).transpose(0,3,1,2)).cuda().half()
    with torch.inference_mode():prediction=model(tensor)
    assert tuple(prediction.shape)==(6,3,canvas[0]*4,canvas[1]*4)
    outputs=prediction.float().clamp(0,1).cpu().numpy()
    targets=np.stack([np.ascontiguousarray(np.clip(resize(o[:,:H*4,:W*4].transpose(1,2,0),(W*2,H*2),ResizeFilter.Box,False),0,1),dtype=np.float32) for o in outputs])
    del tensor,prediction,outputs
    versions=[np.zeros((H*2,W*2,4),np.uint8) for _ in range(3)]; changed=0;total=0;outside=0
    for r,row,a in zip(group,rows,geom):
        x=-a[2]-left;y=-a[3]-top;h,w=a[1]*2,a[0]*2
        if not h*w:continue
        wk=works[row['key']]
        with np.load(encoded/(row['key']+'.npz'),allow_pickle=False) as z:old={n:z[n].copy() for n in z.files}
        crop=targets[:,y*2:y*2+h,x*2:x*2+w]; fresh=r['profile'].encode(old['guide'],crop)
        used=np.unique(wk['frame'].indices[wk['frame'].indices!=0]); old_targets=[]
        for pal in r['profile'].fitting:
            key=hashlib.sha256(bk+bytes.fromhex(wk['input_key'])+used.tobytes()+pal[used].tobytes()).hexdigest()
            with np.load(cache/'targets'/key[:2]/(key+'.npz'),allow_pickle=False) as z:old_targets.append(z['target'].copy())
        # Interpolate neural targets in a four-native-pixel band at actual shared edges.
        yy,xx=np.mgrid[:h,:w];wx=-a[2]+(xx+.5)/2;wy=-a[3]+(yy+.5)/2
        others=[b for b in geom if b is not a and b[0]*b[1]];distance=np.full((h,w),np.inf)
        for b in others:
            bx=-b[2];by=-b[3];br=bx+b[0];bt=by+b[1]
            if -a[2]+a[0]==bx or br==-a[2]:
                cut=bx if -a[2]+a[0]==bx else br
                overlap=(wy>=max(-a[3],by))&(wy<min(-a[3]+a[1],bt));distance=np.minimum(distance,np.where(overlap,abs(wx-cut),np.inf))
            if -a[3]+a[1]==by or bt==-a[3]:
                cut=by if -a[3]+a[1]==by else bt
                overlap=(wx>=max(-a[2],bx))&(wx<min(-a[2]+a[0],br));distance=np.minimum(distance,np.where(overlap,abs(wy-cut),np.inf))
        strength=np.clip((4-distance)/3,0,1); roi=strength>0
        blend=np.stack(old_targets)*(1-strength[None,:,:,None])+crop*strength[None,:,:,None]
        repaired=r['profile'].encode(old['guide'],blend.astype(np.float32))
        for n in ('I','F'):repaired[n][~roi]=old[n][~roi]
        repaired['dep']=r['profile'].dependencies(repaired['I'],repaired['F']);r['profile'].validate(repaired['I'],repaired['F'],old['guide'],repaired['dep'])
        changed+=int(((old['I']!=repaired['I'])|(old['F']!=repaired['F'])).sum());total+=roi.size
        outside+=int((((old['I']!=repaired['I'])|(old['F']!=repaired['F']))&~roi).sum())
        assert outside==0
        pal=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8)));pal[0]=0;pal[1,3]=127
        for c,z in zip(versions,(old,fresh,repaired)):
            im=r['profile'].decode(z['I'],z['F'],pal);dest=c[y*2:y*2+h,x*2:x*2+w];m=im[:,:,3]>0;dest[m]=im[m]
        np.savez_compressed(work/(aid[2:]+'-s'+str(seq)+'-t'+str(slot)+'-'+r['resref']+'.npz'),**repaired)
    zoom=5;yy,xx=np.mgrid[:H*zoom,:W*zoom];out=[background(sample(c,(xx+.5)*2/zoom-.5,(yy+.5)*2/zoom-.5)) for c in versions]
    sheet=Image.new('RGB',(W*zoom*3,H*zoom+26),(32,32,32));draw=ImageDraw.Draw(sheet)
    for i,(label,im) in enumerate(zip(['Current Q3m / assembled filter','Full context Q3m / assembled filter','Context Q3m only 4px seams / assembled filter'],out)):
        draw.text((i*W*zoom+5,6),label,fill='white');sheet.paste(Image.fromarray(im),(i*W*zoom,26))
    label=aid[2:]+'-s'+str(seq)+'-t'+str(slot);sheet.save(HERE/(label+'-context.png'))
    for i,c in enumerate(versions):Image.fromarray(c).save(work/(label+'-v'+str(i)+'.png'))
    rec=dict(animation_id=aid,seq=seq,slot=slot,geometry=geom,new_context_targets=6,changed_encoded_pixels=changed,encoded_pixels=total,changed_outside_four_native_pixel_band=outside,source_geometry_palette_cycles_unchanged=True,preview=label+'-context.png')
    records.append(rec);print(json.dumps(rec),flush=True)
write_json(HERE/'context-probe.json',dict(role='experimental-prototype-no-production-or-installation',method='assemble original RGB under K6, whole-image nearest fill, Q3m inference, crop native parts, refit same partner profiles; feather new targets only within four native pixels of shared edges',model_sha256=backend['model_sha256'],scale=2,neural_batch=6,production_neural_batch=86,source_colour_geometry_cycles_unchanged=True,cases=records,new_neural_targets=6*len(records),global_cache_modified=False,installed_files_changed=False,SDF=False,ingame_QA=False))
