"""Complete contextual repair, batch6 fp16; encode ROI only, keep immutable parent."""
from common import *
from scipy.ndimage import distance_transform_edt
from reboutcx_batch_p10 import pack_normalized
from workspace_paths import get_path
from chainner_ext import resize,ResizeFilter
import time
resources,works,summary,contexts,bindings=plan();WORK.mkdir(parents=True,exist_ok=True)
for sub in ('contexts','encoded'):(WORK/sub).mkdir(exist_ok=True)
assert not (HERE/'production.json').exists(),'final production already recorded'
write_json(HERE/'selection.json',load(PARENT/'selection.json'))
recipe=dict(schema='bg2-q3m-quadrant-contextual-seam-repair-v1',parent_generation=identity(PARENT/'current-generation.json'),band_native_pixels=4,encoder_scope='ROI only; unchanged I/F outside four-pixel native bands',scale=2,neural_batch=6,fp16=True,reduce='Box x4 to x2',model_sha256=BACKEND['model_sha256'],parent_backend=BACKEND,producer=identity(HERE/'produce.py'),common=identity(HERE/'common.py'),encoder=identity(ROOT/'pipeline/scripts/palette_q3m_partners.py'),contexts=len(contexts),native_bindings=len(bindings),unreferenced_native_frames=272,SDF=False)
recipe_key=digest(recipe);write_json(HERE/'recipe.json',recipe)
print(json.dumps(dict(stage='plan',contexts=len(contexts),frames=12928,native_bindings=len(bindings),unreferenced=272)),flush=True)
assert file_sha(get_path('reboutcx_model',required=True))==BACKEND['model_sha256']
model=None;stats=dict(context_cache_hits=0,processed_contexts=0,new_neural_targets=0,repaired_frame_bindings=0,changed_encoded_pixels=0,encoded_ROI_pixels=0,changed_outside_band=0)
started=time.monotonic()
for done,(ck,c) in enumerate(sorted(contexts.items()),1):
    checkpoint=WORK/'contexts'/(ck+'.json')
    if checkpoint.exists():
        record=load(checkpoint);assert record['recipe_key']==recipe_key
        for n in record['nodes']:
            if n['encoded_key']!=n['parent_key']:assert file_sha(WORK/'encoded'/(n['encoded_key']+'.npz'))==n['encoded_sha256']
        stats['context_cache_hits']+=1
    else:
        geometries=c['geometry'];prepared=[];active=False
        for n,(r,row) in enumerate(c['nodes']):
            old=old_arrays(row['key']);validate_encoded(r['profile'],old['I'],old['F'],old['guide'],old['dep'])
            a=geometries[n];s=strength(a,geometries);roi=(s>0)&(r['profile'].classes[old['guide']]>=3)
            prepared.append((r,row,old,s,roi));active|=bool(roi.any())
        nodes=[];changed=0;roi_count=0
        if active:
            if model is None:
                import torch
                os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8');torch.set_num_threads(4)
                torch.backends.cudnn.deterministic=True;torch.use_deterministic_algorithms(True)
                model,_=load_model(get_path('reboutcx_model',required=True),device='cuda:0',fp16=True)
            positive=[a for a in geometries if a[0]*a[1]];left=min(-a[2] for a in positive);top=min(-a[3] for a in positive);right=max(a[0]-a[2] for a in positive);bottom=max(a[1]-a[3] for a in positive);W=right-left;H=bottom-top
            rgb=np.zeros((6,H,W,3),np.uint8);mask=np.zeros((H,W),bool)
            for r,row in c['nodes']:
                a=row['geometry'];x=-a[2]-left;y=-a[3]-top
                if not a[0]*a[1]:continue
                indices=works[row['key']]['frame'].indices;m=indices!=0
                for k in range(6):rgb[k,y:y+a[1],x:x+a[0]][m]=r['profile'].fitting[k][indices][m]
                mask[y:y+a[1],x:x+a[0]]|=m
            assert mask.any()
            nearest=distance_transform_edt(~mask,return_distances=False,return_indices=True);inputs=[np.ascontiguousarray(im[tuple(nearest)]) for im in rgb];canvas=(((H+31)//32)*32,((W+31)//32)*32)
            tensor=torch.from_numpy(pack_normalized(inputs,*canvas).transpose(0,3,1,2)).cuda().half()
            with torch.inference_mode():prediction=model(tensor)
            assert tuple(prediction.shape)==(6,3,canvas[0]*4,canvas[1]*4)
            output=prediction.float().clamp(0,1).cpu().numpy()
            targets=np.stack([np.ascontiguousarray(np.clip(resize(o[:,:H*4,:W*4].transpose(1,2,0),(W*2,H*2),ResizeFilter.Box,False),0,1),dtype=np.float32) for o in output]);del tensor,prediction,output
        for n,(r,row,old,s,roi) in enumerate(prepared):
            node=dict(parent_key=row['key'],encoded_key=row['key'],changed_pixels=0,roi_pixels=int(roi.sum()))
            if roi.any():
                a=geometries[n];x=-a[2]-left;y=-a[3]-top;h,w=a[1]*2,a[0]*2
                crop=targets[:,y*2:y*2+h,x*2:x*2+w][:,roi,:];weight=s[roi][None,:,None]
                blend=(old_targets(works[row['key']],roi)*(1-weight)+crop*weight).astype(np.float32)
                new=r['profile'].encode(old['guide'][roi][None,:],blend[:,None,:,:])
                arrays={k:v.copy() for k,v in old.items()};arrays['I'][roi]=new['I'][0];arrays['F'][roi]=new['F'][0]
                arrays['dep']=r['profile'].dependencies(arrays['I'],arrays['F']);r['profile'].validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep'])
                assert np.array_equal(arrays['I'][~roi],old['I'][~roi]) and np.array_equal(arrays['F'][~roi],old['F'][~roi])
                diff=(arrays['I']!=old['I'])|(arrays['F']!=old['F']);node['changed_pixels']=int(diff.sum())
                if diff.any():
                    newkey=digest([recipe_key,ck,n,row['key']]);dest=WORK/'encoded'/(newkey+'.npz')
                    if dest.exists():
                        with np.load(dest,allow_pickle=False) as z:assert all(np.array_equal(z[k],v) for k,v in arrays.items())
                    else:save(dest,**arrays)
                    node.update(encoded_key=newkey,encoded_sha256=file_sha(dest))
                changed+=node['changed_pixels'];roi_count+=node['roi_pixels']
            nodes.append(node)
        record=dict(recipe_key=recipe_key,context_key=ck,representative=c['representative'],geometry=geometries,nodes=nodes,new_neural_targets=6 if active else 0,changed_pixels=changed,roi_pixels=roi_count,changed_outside_band=0)
        write_json(checkpoint,record)
        stats['processed_contexts']+=1;stats['new_neural_targets']+=record['new_neural_targets']
    stats['changed_encoded_pixels']+=record['changed_pixels'];stats['encoded_ROI_pixels']+=record['roi_pixels'];stats['repaired_frame_bindings']+=sum(n['encoded_key']!=n['parent_key'] for n in record['nodes'])
    if done%16==0 or done==len(contexts):print(json.dumps(dict(stage='contextual-seam-repair',done=done,total=len(contexts),new_neural_targets=stats['new_neural_targets'],changed_pixels=stats['changed_encoded_pixels'],seconds=round(time.monotonic()-started,1))),flush=True)
if model is not None:del model
original_keys,patched=bound_plan(resources,works,contexts,bindings)
write_json(HERE/'frame-bindings.json',dict(frames=[dict(animation_id=a,resref=r,frame_index=i,parent_key=key,encoded_key=next(row['key'] for row in next(res for res in resources if res['witness']['animation_id']==a and res['resref']==r)['frames'] if row['frame_index']==i),context_key=bindings[(a,r,i)][0] if (a,r,i) in bindings else None) for (a,r,i),key in original_keys.items()]))
assert not (WORK/'isolated').exists(),'fresh immutable pack required'
packed=pack(resources,works,WORK/'isolated')
write_json(HERE/'production.json',dict(schema='bg2-q3m-quadrant-seam-production-v1',plan=summary,recipe=identity(HERE/'recipe.json'),parent_generation=identity(PARENT/'current-generation.json'),stats=stats,contexts=3144,referenced_native_frames=12656,unreferenced_native_frames_preserved=272,changed_native_frame_bindings=len(patched),local_encoded_directory=relative(WORK/'encoded'),frame_bindings=identity(HERE/'frame-bindings.json'),pack=packed,pack_directory=relative(WORK/'isolated'),encoder_namespace=PROD['encoder_namespace'],parent_global_cache_read_only=True,SDF=False,ingame_QA=False))
print(json.dumps(dict(stage='complete',resources=packed['resources'],frames=packed['frames'],stats=stats)),flush=True)
