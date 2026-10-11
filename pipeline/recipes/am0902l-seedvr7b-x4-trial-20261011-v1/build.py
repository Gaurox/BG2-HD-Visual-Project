"""Isolated AM0902L SeedVR trial: native tiles, seam context, shared Apollo timing."""
from pathlib import Path
import copy, hashlib, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/recipes/lot3-decor-x4-20261011-v1'))
from common import v, pixels, write_pack, rel
from build_alpha_feather import inner_feather_ramp

TAG = 'am0902l-seedvr7b-x4-trial-20261011-v1'
OUT = ROOT/'animations/batches'/TAG
SEED = ROOT/'animations/ressources/AM0902L/runs/am0902l-seedvr7b-lab-x4-trial-20261011-v1'
REB = ROOT/'animations/batches/lot3-decor-x4-20261011-v1'
SOURCE = SEED/'resources/AM0902L/01_frames_x1'
REF = 'AM0902L'

def prepare():
    dest=OUT/'assembled-native'
    dest.mkdir(parents=True, exist_ok=False)
    for kind in ('rgb','alpha','rgba'): (dest/kind).mkdir()
    source=v.load_json(SOURCE/'manifest.json')
    cycles=[c['frame_indices'] for c in source['cycles']]
    hashes=[]; frames=[]
    for slot in range(8):
        full=np.zeros((317,256,4),np.uint8)
        for cycle in cycles:
            part=np.asarray(Image.open(SOURCE/'rgba'/source['frames'][cycle[slot]]['file']).convert('RGBA'))
            mask=part[...,3]>0
            full[mask]=part[mask]
        digest=hashlib.sha256(full.tobytes()).hexdigest();hashes.append(digest)
        nearest=distance_transform_edt(full[...,3]==0,return_distances=False,return_indices=True)
        name=f'frame_{slot:03d}.png'
        Image.fromarray(full).save(dest/'rgba'/name)
        Image.fromarray(full[...,:3][tuple(nearest)]).save(dest/'rgb'/name)
        Image.fromarray(full[...,3]).save(dest/'alpha'/name)
        frames.append(dict(frame=slot,file=name,source_size=[256,317],centre=[129,158],canvas_offset=[0,0],rgba_sha256=digest))
    assert len(set(hashes))==8,'Duplicate whole poses require explicit hold treatment'
    v.write_json(dest/'manifest.json',dict(schema='bg2-upscale-animation-frames-x1-v1',frame_count=8,
        aligned_canvas_size=[256,317],geometry_mode='uniform',frames=frames,
        cycles=[dict(cycle=0,frame_indices=list(range(8)))],source_manifest=rel(SOURCE/'manifest.json'),
        source_manifest_sha256=v.sha256_file(SOURCE/'manifest.json'),duplicate_poses=0,
        native_duration_seconds=8/15,recipe='native synchronized tile union -> nearest opaque RGB fill after assembly'))
    print('PREPARED 8 unique synchronized whole poses',flush=True)

def context():
    output=OUT/'context-spatial';output.mkdir(parents=True,exist_ok=False)
    base=SEED/'03_runtime_pack'
    _,resources,_=v.load_base_pack(base);r=resources[0]
    cycles=[c['native_frame_indices'] for c in r['cycles']]
    boxes=[]
    for c in cycles:
        f=r['frames'][c[0]];w,h=f['logical_size_x1'];cx,cy=f['centre_x1']
        boxes.append((-cx,-cy,w-cx,h-cy))
    arrays={};checks=[]
    inferred_root=OUT/'assembled-seedvr-x4'
    assert v.load_json(inferred_root/'manifest.json')['status']=='completed'
    for slot in range(8):
        inferred=np.asarray(Image.open(inferred_root/'rgb'/f'frame_{slot:03d}.png').convert('RGB'))
        full=np.zeros((1268,1024,4),np.uint8)
        for tile,c in enumerate(cycles):
            f=r['frames'][c[slot]];part=pixels(base,f)
            x0,y0,x1,y1=boxes[tile];h,w=part.shape[:2]
            xx=(np.arange(w)+.5)/4+x0;yy=(np.arange(h)+.5)/4+y0
            weight=np.zeros((h,w),float)
            for j,(a0,b0,a1,b1) in enumerate(boxes):
                if j==tile:continue
                if x0==a1 or x1==a0:
                    edge=x0 if x0==a1 else x1
                    inside=(yy>=max(y0,b0))&(yy<min(y1,b1))
                    weight=np.maximum(weight,inside[:,None]*np.clip((4-np.abs(xx-edge))/3,0,1)[None,:])
                if y0==b1 or y1==b0:
                    edge=y0 if y0==b1 else y1
                    inside=(xx>=max(x0,a0))&(xx<min(x1,a1))
                    weight=np.maximum(weight,np.clip((4-np.abs(yy-edge))/3,0,1)[:,None]*inside[None,:])
            ox,oy=(x0+129)*4,(y0+158)*4
            crop=inferred[oy:oy+h,ox:ox+w]
            corrected=np.rint(part[...,:3]*(1-weight[...,None])+crop*weight[...,None]).astype(np.uint8)
            assert np.array_equal(corrected[weight==0],part[...,:3][weight==0])
            part[...,:3]=corrected
            region=full[oy:oy+h,ox:ox+w];visible=part[...,3]>0;region[visible]=part[visible]
            checks.append(dict(slot=slot,tile=tile,band_pixels=int((weight>0).sum()),outside_band_unchanged=True))
        arrays[(REF,slot)]=full
        Image.fromarray(full).save(output/f'assembled-x4-{slot:03d}.png')
    synthetic=copy.deepcopy(r)
    synthetic.update(frame_count=8,cycle_count=1,geometry_mode='uniform',cycles=[dict(cycle=0,
        native_frame_indices=list(range(8)),timeline_frame_indices=[])])
    synthetic['frames']=[dict(frame=i,logical_size_x1=[256,317],physical_size_x4=[1024,1268],centre_x1=[129,158]) for i in range(8)]
    write_pack(OUT/'context-base',[synthetic],arrays)
    v.write_json(output/'manifest.json',dict(status='completed',source_pack=rel(base),
        source_manifest_sha256=v.sha256_file(base/'manifest.json'),
        assembled_manifest_sha256=v.sha256_file(inferred_root/'manifest.json'),slot_count=8,
        recipe='SeedVR2 7B INT8 LAB x4, seed20261011, pad32; assembled context only shared-edge RGB bands; native alpha nearest x4',checks=checks))
    print('CONTEXT complete, 32 seam checks passed',flush=True)

def finish():
    base=OUT/'context-base';temporal=OUT/'temporal-AM0902L'
    if not temporal.exists():
        plan=v.build_plan(None,base,[REF],model='apo-8',collapse_uniform_duplicate_holds=False,
            transparent_rgb_mode='nearest-opaque-dilate')
        v.build_run(None,base,temporal,[REF],plan['plan_sha256'],v.DEFAULT_TVAI_FFMPEG,v.DEFAULT_TVAI_MODEL_DIR,
            'apo-8','-2','ffmpeg',False,collapse_uniform_duplicate_holds=False,
            transparent_rgb_mode='nearest-opaque-dilate')
    whole=temporal/'03_runtime_pack'
    full_r=v.validate_v2_pack(whole)[1][0];timeline=full_r['cycles'][0]['timeline_frame_indices']
    assert len(timeline)==16
    native=v.load_base_pack(SEED/'03_runtime_pack')[1][0];r=copy.deepcopy(native)
    r.update(playback_mode='TimedTimeline',native_fps=full_r['native_fps'],target_fps=full_r['target_fps'])
    frames=copy.deepcopy(r['frames']);arrays={};whole_frames=[]
    for index in timeline:
        p=pixels(whole,full_r['frames'][index])
        p[...,3]=np.rint(p[...,3]*inner_feather_ramp(p[...,3],2)).astype(np.uint8)
        p[p[...,3]==0,:3]=0;whole_frames.append(p)
    for tile,c in enumerate(r['cycles']):
        tiled_timeline=[]
        for slot,original in enumerate(c['native_frame_indices']):
            for parity in (0,1):
                index=original if parity==0 else 32+tile*8+slot
                f=copy.deepcopy(native['frames'][original]);f['frame']=index
                if parity:frames.append(f)
                cx,cy=f['centre_x1'];w,h=f['physical_size_x4'];x,y=(129-cx)*4,(158-cy)*4
                arrays[(REF,index)]=whole_frames[2*slot+parity][y:y+h,x:x+w].copy()
                tiled_timeline.append(index)
        c['timeline_frame_indices']=tiled_timeline
    r['frames']=sorted(frames,key=lambda f:f['frame']);r['frame_count']=64
    for f in native['frames']:
        new=r['frames'][f['frame']]
        assert all(f[k]==new[k] for k in ['logical_size_x1','physical_size_x4','centre_x1'])
    hashes=[hashlib.sha256(p.tobytes()).hexdigest() for p in whole_frames]
    assert len(set(hashes))==16 and all(hashes[i]!=hashes[(i+1)%16] for i in range(16))
    for c,old in zip(r['cycles'],native['cycles']):
        assert c['native_frame_indices']==old['native_frame_indices']
        assert len(c['timeline_frame_indices'])/30==len(old['native_frame_indices'])/15
    final=write_pack(OUT/'final-assets',[r],arrays)
    preview(whole_frames)
    v.write_json(OUT/'manifest.json',dict(schema='bg2-upscale-animation-trial-v1',status='completed',created_utc=v.utc_now(),
        resref=REF,source_run=rel(SEED),source_run_manifest_sha256=v.sha256_file(SEED/'manifest.json'),
        recipe='SeedVR2 7B INT8 LAB x4 contextual seam bands -> Apollo8 shared whole 30fps -> outer silhouette inner2 -> native four-tile recut',
        target_fps=30,native_duration_seconds=8/15,target_duration_seconds=16/30,
        native_pose_duplicates=0,target_pose_duplicates=0,native_geometry_and_lookup_preserved=True,
        final_pack=rel(final),final_pack_manifest_sha256=v.sha256_file(final/'manifest.json'),
        comparison=rel(OUT/'comparison.png'),qa_status='pending-user-review',installation_status='not-installed',
        installed_comparison_pack=rel(REB/'final-assets'),comparison_pack_manifest_sha256=v.sha256_file(REB/'final-assets/manifest.json')))
    print('TRIAL COMPLETE',rel(OUT),flush=True)

def assembled(pack,r,phase):
    full=np.zeros((1268,1024,4),np.uint8)
    for c in r['cycles']:
        f=r['frames'][c['timeline_frame_indices'][phase]];part=pixels(pack,f)
        cx,cy=f['centre_x1'];h,w=part.shape[:2];x,y=(129-cx)*4,(158-cy)*4
        region=full[y:y+h,x:x+w];mask=part[...,3]>0;region[mask]=part[mask]
    return full

def preview(whole_frames):
    pack=REB/'final-assets';r=next(x for x in v.validate_v2_pack(pack)[1] if x['resref']==REF)
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
    except OSError:font=ImageFont.load_default()
    def panel(phase,scale=1):
        sheet=Image.new('RGB',(2088,1340),(34,34,34));draw=ImageDraw.Draw(sheet)
        for column,(name,p) in enumerate([('ReboutCX x4 - version en jeu',assembled(pack,r,phase)),('SeedVR2 7B INT8 / LAB x4 - test',whole_frames[phase])]):
            image=Image.alpha_composite(Image.new('RGBA',(1024,1268),(34,34,34,255)),Image.fromarray(p)).convert('RGB')
            x=20+1044*column;sheet.paste(image,(x,60));draw.text((x,14),name,font=font,fill='white')
        if scale!=1:sheet=sheet.resize((round(sheet.width*scale),round(sheet.height*scale)),Image.Resampling.LANCZOS)
        return sheet
    panel(0).save(OUT/'comparison.png')
    frames=[]
    for phase in range(16):
        frame=panel(phase,.5);frames.append(frame)
        panel_dir=OUT/'comparison-frames';panel_dir.mkdir(exist_ok=True)
        frame.save(panel_dir/f'frame_{phase:03d}.png')
    # GIF supports centiseconds only; PNG sequence and runtime retain exact 30fps.
    frames[0].save(OUT/'comparison.gif',save_all=True,append_images=frames[1:],duration=[30,30,40]*5+[30],loop=0)
    contact=Image.new('RGB',(1044*3,670),(34,34,34))
    for column,phase in enumerate((0,6,12)):contact.paste(panel(phase,.5),(column*1044,0))
    contact.save(OUT/'comparison-three-poses.png')

if __name__=='__main__':
    {'prepare':prepare,'context':context,'finish':finish}[sys.argv[1]]()
