"""Four native bird frames, current Q3m V7 x2/x4, lossless RGBA and PNG board."""
from pathlib import Path
import os,sys,json,hashlib,time
from collections import defaultdict,Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,exclusive,save,require
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from reboutcx_multipal import inference_context
from reboutcx_batch import load_model,prepare_inference_rgb
from reboutcx_batch_p12 import infer_float_crops
import run_creature_sprite_x2 as registry

SHARED=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
WORK=ROOT/'sprite/.work/q3m-flying-frame-x2-x4-20261003-v1'
require(not (OUT/'comparison.json').exists(),'final comparison exists; use a new version')
WORK.mkdir(parents=True,exist_ok=True)
resources,works,scope=source_plan(OUT/'selection-scope.json','flying')
selected=[];seen=set()
for resource in resources:
    if resource['resref'] in seen:continue
    seen.add(resource['resref'])
    # Broad, readable wings; only frames actually referenced by native cycles.
    used={i for c in resource['cycles'] for i in c if i<len(resource['frames'])}
    row=max((r for r in resource['frames'] if r['frame_index'] in used),
            key=lambda r:(np.count_nonzero(works[r['key']]['frame'].indices>=3),
                          works[r['key']]['frame'].width,-r['frame_index']))
    frame=works[row['key']]['frame'];profile=resource['profile']
    cycle,slot=next((ci,c.index(frame.index)) for ci,c in enumerate(resource['cycles']) if frame.index in c)
    palette=np.column_stack((profile.fitting[0],np.full(256,255,np.uint8)))
    palette[0]=0;palette[1,3]=127
    source=palette[frame.indices]
    chosen=dict(resource,frames=[row])
    selected.append(dict(resource=chosen,work=works[row['key']],frame=frame,profile=profile,
                         key=row['key'],cycle=cycle,slot=slot,source=source,palette=palette))
require(len(selected)==4,'four distinct bird BAMs required')
subset={d['key']:d['work'] for d in selected}
require(len(subset)==4,'duplicate selected source unexpectedly present')
backend=json.loads((SHARED/'backend.json').read_text(encoding='utf-8'))
backend_key=hashlib.sha256(json.dumps(backend,sort_keys=True).encode()).digest()
recipe=dict(role='four-frame-offline-visual-test-not-full-family-or-installation',
            scales=[2,4],colour='Q3m-K6-four-partners-eight-levels-V7',
            x2='float32 native x4 target reduced with BOX before encoding; acquired shared cache',
            x4='direct native-source inference and independent xBR4 semantic guide; no enlarged x2 raster',
            inference=backend,encoder_sha256=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py'),
            source_scope_sha256=file_sha(OUT/'selection-scope.json'),
            selection='maximum material pixels among native cycle frames, then width, then first frame',
            display='native x8; source nearest x8 / Q3m x2 nearest x4 / Q3m x4 nearest x2',
            palette='same native neutral draw palette; alpha 0/127/255; transparent entry zero')
recipe_path=WORK/'recipe.json'
if recipe_path.exists():require(json.loads(recipe_path.read_text())==recipe,'diagnostic recipe changed')
else:write_json(recipe_path,recipe)
stats=Counter();requests={};timings=[]
with exclusive(SHARED):
    for d in selected:
        frame=d['frame'];work=d['work'];used=np.unique(frame.indices[frame.indices!=0]);d['targets']=[]
        for palette in d['profile'].fitting:
            key=hashlib.sha256(backend_key+bytes.fromhex(work['input_key'])+used.tobytes()+palette[used].tobytes()).hexdigest()
            path=WORK/'raw-x4'/(key+'.npz');d['targets'].append((key,path))
            if not path.exists():requests.setdefault(key,(path,frame,palette))
    if requests:
        import torch
        require(inference_context()==backend,'acquired inference backend changed')
        os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8');torch.set_num_threads(4)
        torch.backends.cudnn.deterministic=True;torch.use_deterministic_algorithms(True)
        descriptor,_=load_model(get_path('reboutcx_model',required=True),device='cuda:0',fp16=True)
        groups=defaultdict(list)
        for request in requests.values():
            frame=request[1];groups[(((frame.height+31)//32)*32,((frame.width+31)//32)*32)].append(request)
        for canvas,group in sorted(groups.items()):
            for start in range(0,len(group),86):
                batch=group[start:start+86]
                inputs=[prepare_inference_rgb(frame,palette) for _,frame,palette in batch]
                crops,timing=infer_float_crops(descriptor,inputs,canvas=canvas,fp16=True)
                timings.append(dict(canvas=list(canvas),unique_inputs=len(batch),timing=timing))
                for (path,frame,_),crop in zip(batch,crops,strict=True):
                    require(crop.shape==(frame.height*4,frame.width*4,3) and crop.dtype==np.float32,'x4 target shape/type differs')
                    save(path,target=crop);stats['new_neural_targets_x4_shared_with_x2']+=1
                print(json.dumps(dict(stage='targets',generated=stats['new_neural_targets_x4_shared_with_x2'],total=len(requests))),flush=True)
        del descriptor;torch.cuda.empty_cache()
    from chainner_ext import resize,ResizeFilter
    # Populate only missing acquired x2 target slots from the same x4 forward pass.
    for d in selected:
        for key,path in d['targets']:
            with np.load(path,allow_pickle=False) as data:target=data['target'].copy()
            require(target.shape==(d['frame'].height*4,d['frame'].width*4,3) and np.isfinite(target).all() and
                    np.all((target>=0)&(target<=1)),'invalid float x4 target')
            derived=np.ascontiguousarray(np.clip(resize(target,(d['frame'].width*2,d['frame'].height*2),ResizeFilter.Box,False),0,1),dtype=np.float32)
            shared_path=SHARED/'targets'/key[:2]/(key+'.npz')
            if shared_path.exists():
                with np.load(shared_path,allow_pickle=False) as data:prior=data['target'].copy()
                require(np.array_equal(prior,derived),'deterministic acquired x2 target differs')
                stats['existing_x2_targets_byte_identical']+=1
            else:save(shared_path,target=derived);stats['new_x2_targets_from_same_forward_pass']+=1
    x2_stats,namespace=produce([d['resource'] for d in selected],subset,SHARED)
    stats.update({'x2_'+k:v for k,v in x2_stats.items()})
    # One independent x4 guide per distinct native source, outside the x2 namespace.
    missing=[d for d in selected if not (WORK/'guides'/(d['key']+'-x4.npz')).exists()]
    if missing:
        outputs=registry.run_xbr([d['frame'] for d in missing],get_path('mmpx_scalepix',required=True),'node',registry.direct_upscale_contract(4))
        for d,(w,h,rgba) in zip(missing,outputs,strict=True):
            frame=d['frame'];g,_=registry.map_output(frame,rgba,registry.xbr_provenance_indices(frame,4))
            require((w,h)==(frame.width*4,frame.height*4),'x4 guide size differs')
            save(WORK/'guides'/(d['key']+'-x4.npz'),guide=g.reshape(h,w))
    records=[]
    for d in selected:
        frame=d['frame'];profile=d['profile']
        with np.load(WORK/'guides'/(d['key']+'-x4.npz'),allow_pickle=False) as data:g=data['guide'].copy()
        path=WORK/'encoded-x4'/(d['key']+'.npz')
        if not path.exists():
            targets=[]
            for _,target_path in d['targets']:
                with np.load(target_path,allow_pickle=False) as data:targets.append(data['target'].copy())
            started=time.perf_counter();arrays=profile.encode(g,np.stack(targets));save(path,**arrays)
            print(json.dumps(dict(stage='encoded-x4',resref=frame.resref,frame=frame.index,seconds=time.perf_counter()-started)),flush=True)
        d['images']=[d['source']];outputs=[]
        for scale,encoded_path in ((2,d['work']['encoded_path']),(4,path)):
            with np.load(encoded_path,allow_pickle=False) as data:arrays={n:data[n].copy() for n in data.files}
            profile.validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep'])
            require(arrays['I'].shape==(frame.height*scale,frame.width*scale),'encoded size differs')
            rgba=profile.decode(arrays['I'],arrays['F'],d['palette'])
            require(np.array_equal(rgba[:,:,3],d['palette'][arrays['guide'],3]),'native guide alpha changed')
            d['images'].append(rgba)
            # Exact payload and profile retained for offline decoding at either scale.
            save(OUT/'encoded'/(frame.resref+f'-frame-{frame.index}-x{scale}.npz'),
                 **arrays,profile=np.frombuffer(profile.metadata(),np.uint8),fitting=profile.fitting)
            outputs.append(dict(scale=scale,encoded_sha256=file_sha(encoded_path),
                                fitting_target_sha256=[file_sha(p) for _,p in d['targets']]))
        files=[]
        for scale,rgba in zip((1,2,4),d['images']):
            png=OUT/(frame.resref+f'-frame-{frame.index}-'+('source' if scale==1 else f'q3m-x{scale}')+'.png')
            Image.fromarray(rgba,'RGBA').save(png,compress_level=9)
            require(np.array_equal(np.asarray(Image.open(png).convert('RGBA')),rgba),'PNG roundtrip is not exact')
            files.append(dict(scale=scale,path=png.relative_to(ROOT).as_posix(),bytes=png.stat().st_size,
                              sha256=file_sha(png),size=[rgba.shape[1],rgba.shape[0]],
                              opaque_RGB_colours=len(np.unique(rgba[rgba[:,:,3]==255,:3],axis=0))))
        ids=[r['witness']['animation_id'] for r in resources if r['resref']==frame.resref]
        records.append(dict(name=d['resource']['witness']['name'],animation_ids=ids,resref=frame.resref,
                            frame=frame.index,cycle=d['cycle'],slot=d['slot'],geometry=d['resource']['frames'][0]['geometry'],
                            source_bam_sha256=d['resource']['source_sha256'],source_work_key=d['work']['source_key'],
                            encoded_work_key=d['key'],native_kind=0,profile_id=8,PNGs=files,encodings=outputs))

FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
TITLE=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30)
margin=24;gap=12;column=max(340,max(d['frame'].width*8+48 for d in selected))
width=margin*2+3*column+2*gap
header=140;row_heights=[max(180,d['frame'].height*8+80) for d in selected]
board=Image.new('RGB',(width,header+sum(row_heights)+20),(23,27,33));draw=ImageDraw.Draw(board)
draw.text((margin,14),'Oiseaux — Q3m x2 / x4 · nouvelles couleurs',font=TITLE,fill=(244,246,248))
draw.text((margin,56),'4 modèles · même frame et palette neutre · PNG sans perte · affichage sans lissage',font=SMALL,fill=(189,199,214))
for col,label in enumerate(('Source native · affichée ×8','Q3m x2 · affiché ×4','Q3m x4 direct · affiché ×2')):
    draw.text((margin+col*(column+gap),99),label,font=FONT,fill=(237,242,249))
y=header
for d,record,row_height in zip(selected,records,row_heights):
    frame=d['frame']
    for col,rgba in enumerate(d['images']):
        x=margin+col*(column+gap)
        yy,xx=np.indices((row_height-gap,column));tiles=(xx//16+yy//16)%2
        rgb=np.where(tiles[:,:,None],np.array([49,56,65]),np.array([41,47,55])).astype(np.uint8)
        tile=Image.fromarray(rgb,'RGB').convert('RGBA')
        sprite=Image.fromarray(rgba,'RGBA').resize((frame.width*8,frame.height*8),Image.Resampling.NEAREST)
        tile.alpha_composite(sprite,((column-sprite.width)//2,62+(row_height-gap-62-sprite.height)//2))
        board.paste(tile.convert('RGB'),(x,y))
        draw.text((x+12,y+9),record['name'],font=FONT,fill=(244,246,248))
        draw.text((x+12,y+39),f"{frame.resref} · frame {frame.index} · {record['PNGs'][col]['size'][0]} × {record['PNGs'][col]['size'][1]} px",font=SMALL,fill=(186,198,211))
    y+=row_height
png=OUT/'comparatif-oiseaux-q3m-x2-x4.png';board.save(png,compress_level=9)
require(np.array_equal(np.asarray(Image.open(png)),np.asarray(board)),'board PNG roundtrip differs')
write_json(OUT/'recipe.json',recipe)
write_json(OUT/'comparison.json',dict(role='offline-four-frame-comparison-not-production-QA-installation-or-release',
    distinct_models=4,selected_source_frames=4,source_scope_animation_ids=5,
    method='Q3m K6 V7 four partners/eight levels',scales=[2,4],palette='native neutral',
    lossless_PNG_roundtrip_verified=True,display_nearest_native_x8=True,
    stats=dict(stats),inference_timings=timings,x2_encoder_namespace=namespace.name,
    source_scope=dict(resources=scope['resources'],physical_frames=scope['physical_frames'],unique_source_work=scope['unique_source_work']),
    samples=records,comparison_png=dict(path=png.relative_to(ROOT).as_posix(),sha256=file_sha(png),size=list(board.size)),
    installed=False,ingame_QA=False,release=False))
print(json.dumps(dict(stage='complete',png=str(png),size=board.size,stats=dict(stats))),flush=True)
