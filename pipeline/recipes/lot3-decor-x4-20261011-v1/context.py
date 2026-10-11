"""AM0902L: infer eight assembled poses; modify only shared-edge RGB bands."""
from common import *
from PIL import Image
from reboutcx_batch import load_model,infer_x4_box_x2
from run_animation_reboutcx_x4 import filled_rgb
from workspace_paths import get_path

def main():
    output=BATCH/'context-spatial'
    output.mkdir(parents=True,exist_ok=False)
    source=REB/'resources/AM0902L/01_frames_x1'
    fm=v.load_json(source/'manifest.json')
    _,rs,_=v.load_base_pack(REB/'03_runtime_pack')
    r=next(r for r in rs if r['resref']=='AM0902L')
    cycles=[c['native_frame_indices'] for c in r['cycles']]
    descriptor,versions=load_model(get_path('reboutcx_model'),device='cuda:0',fp16=True)
    arrays,checks={},[]
    boxes=[]
    for c in cycles:
        f=r['frames'][c[0]]; w,h=f['logical_size_x1']; cx,cy=f['centre_x1']
        boxes.append((-cx,-cy,w-cx,h-cy))
    for slot in range(8):
        native=np.zeros((317,256,4),np.uint8)
        for c in cycles:
            image=np.asarray(Image.open(source/'rgba'/fm['frames'][c[slot]]['file']).convert('RGBA'))
            visible=image[...,3]>0
            native[visible]=image[visible]
        Image.fromarray(native).save(output/f'assembled-native-{slot:03d}.png')
        inferred,_=infer_x4_box_x2(descriptor,filled_rgb(native),fp16=True)
        full=np.zeros((1268,1024,4),np.uint8)
        for tile,c in enumerate(cycles):
            f=r['frames'][c[slot]]; base=pixels(REB/'03_runtime_pack',f)
            x0,y0,x1,y1=boxes[tile]; h,w=base.shape[:2]
            xx=(np.arange(w)+.5)/4+x0; yy=(np.arange(h)+.5)/4+y0
            weight=np.zeros((h,w),float)
            for j,b in enumerate(boxes):
                if j==tile: continue
                a0,b0,a1,b1=b
                if x0==a1 or x1==a0:
                    edge=x0 if x0==a1 else x1
                    inside=(yy>=max(y0,b0)) & (yy<min(y1,b1))
                    weight=np.maximum(weight,inside[:,None]*np.clip((4-np.abs(xx-edge))/3,0,1)[None,:])
                if y0==b1 or y1==b0:
                    edge=y0 if y0==b1 else y1
                    inside=(xx>=max(x0,a0)) & (xx<min(x1,a1))
                    weight=np.maximum(weight,np.clip((4-np.abs(yy-edge))/3,0,1)[:,None]*inside[None,:])
            ox,oy=(x0+129)*4,(y0+158)*4
            crop=inferred[oy:oy+h,ox:ox+w]
            corrected=np.rint(base[...,:3]*(1-weight[...,None])+crop*weight[...,None]).astype(np.uint8)
            assert np.array_equal(corrected[weight==0],base[...,:3][weight==0])
            base[...,:3]=corrected
            region=full[oy:oy+h,ox:ox+w]; visible=base[...,3]>0
            region[visible]=base[visible]
            checks.append(dict(slot=slot,tile=tile,corrected_band_pixels=int((weight>0).sum()),outside_band_unchanged=True))
        arrays[('AM0902L',slot)]=full
        Image.fromarray(full).save(output/f'assembled-x4-{slot:03d}.png')
        print('CONTEXT',slot+1,'/8',flush=True)
    synthetic=copy.deepcopy(r)
    synthetic.update(frame_count=8,cycle_count=1,geometry_mode='uniform',cycles=[dict(cycle=0,
                     native_frame_indices=list(range(8)),timeline_frame_indices=[])])
    synthetic['frames']=[dict(frame=i,logical_size_x1=[256,317],physical_size_x4=[1024,1268],centre_x1=[129,158]) for i in range(8)]
    write_pack(BATCH/'context-base',[synthetic],arrays)
    v.write_json(output/'manifest.json',dict(status='completed',source_run=rel(REB),
        source_run_manifest_sha256=v.sha256_file(REB/'manifest.json'),model=rel(get_path('reboutcx_model')) if get_path('reboutcx_model').is_relative_to(ROOT) else 'config://reboutcx_model',
        model_sha256=v.sha256_file(get_path('reboutcx_model')),versions=versions,slot_count=8,
        recipe='assemble x1 -> opaque fill -> ReboutCX x4; contextual RGB only within shared-edge bands; alpha union native nearest x4',checks=checks))

if __name__=='__main__': main()
