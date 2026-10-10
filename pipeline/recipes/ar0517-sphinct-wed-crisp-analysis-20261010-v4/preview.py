"""Read-only runtime diagnosis and new preview comparisons, no installed writes."""
from pathlib import Path
import sys, json, hashlib
import numpy as np
from scipy import ndimage
from scipy.interpolate import splprep, splev
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
from build_spline_alpha_mask import resample_closed
from workspace_paths import get_path
OUT=ROOT/'animations/batches/ar0517-sphinct-wed-crisp-analysis-20261010-v4'
OUT.mkdir(parents=True,exist_ok=True)
BASE=ROOT/'animations/packs-par-zone/combined-20260917-active-plus-visual-regression-fix/AR0517'
ACTIVE=ROOT/'animations/packs-par-zone/ar0517-sphinct-wed-splinefit1-20261010-v3/AR0517'
_,resources=v2.validate_v2_pack(BASE); r=resources[0]
_,installed=v2.validate_v2_pack(ACTIVE)
old=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1'
poly=next(p for p in v2.load_json(old/'diagnosis.json')['polygons'] if p['index']==3)
transfer=np.fromfile(old/'arch-transfer.rgba',np.uint8).reshape(120,160,4)
native=(transfer[:,:,0]>0).repeat(4,0).repeat(4,1)
origin=np.array([1680,1588]); pad=32; ss=4; size=(704,544)
samples=resample_closed(np.asarray(poly['points'],float)*4,1.5)
tck,_=splprep(samples.T,s=len(samples),per=True,k=3)
curve=np.asarray(splev(np.linspace(0,1,len(samples)*3,endpoint=False),tck)).T
high=Image.new('L',(size[0]*ss,size[1]*ss),0)
ImageDraw.Draw(high).polygon([tuple((p-origin+pad)*ss) for p in curve],fill=255)
d=ndimage.distance_transform_edt(np.asarray(high)==0)/ss
def coverage(guard,feather=0,clamp=False):
    if feather:
        t=np.clip((d-guard)/feather,0,1); cov=np.rint(255*t*t*(3-2*t)).astype(np.uint8)
    else: cov=np.where(d>guard,255,0).astype(np.uint8)
    result=np.array(Image.fromarray(cov).resize(size,Image.Resampling.BOX))[pad:-pad,pad:-pad]
    if clamp: result[~native]=0
    return result
active_mask=np.array(Image.open(ROOT/'animations/ressources/SPHINCT/runs/ar0517-sphinct-wed-splinefit1-20261010-v3/provenance/world-coverage.png'))
assert np.array_equal(active_mask,coverage(8,8,True))
variants=[('installed','Installe : retrait8 / fondu8',active_mask),
          ('crisp-g8','Meme retrait8 / coupe nette',coverage(8)),
          ('crisp-g4','Retrait4 / coupe nette',coverage(4)),
          ('crisp-g0','Spline Fit1 / aucun retrait',coverage(0))]
bg=Image.open(ROOT/'maps/AR0517/runs/seedvr2-7b-int8-lab-direct-x4/tuiles-principales/01_upscale/AR0517-tuiles-principales-x4-seedvr2-7b-int8-lab.png').convert('RGB')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
fontsmall=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
def rgba(f):
    w,h=f['physical_size_x4']; return np.frombuffer((BASE/f['asset']).read_bytes(),np.uint8).reshape(h,w,4)
def composite(raw,cov):
    scene=bg.copy(); box=(*origin,*(origin+np.array([640,480])))
    back=np.asarray(scene.crop(box)).astype(float)
    a=np.rint(raw[:,:,3].astype(float)*cov/255)[:,:,None]/255
    scene.paste(Image.fromarray(np.rint(back*(1-a)+raw[:,:,:3]*a).clip(0,255).astype(np.uint8)),tuple(origin))
    return scene
board=Image.new('RGB',(1800,1380),(20,23,29)); draw=ImageDraw.Draw(board)
detail=Image.new('RGB',(1600,800),(20,23,29)); dd=ImageDraw.Draw(detail)
f=r['frames'][8]; raw=rgba(f)
crop=(400*4,382*4,590*4,532*4)
detailbox=(530*4,420*4,562*4,494*4)
metrics=[]
for i,(name,label,cov) in enumerate(variants):
    Image.fromarray(cov).save(OUT/(name+'-coverage.png'))
    scene=composite(raw,cov)
    scene.crop(crop).save(OUT/(name+'-frame8.png'))
    x=i%2*900; y=i//2*690
    draw.text((x+16,y+16),label,font=font,fill='white')
    board.paste(scene.crop(crop).resize((836,660),Image.Resampling.LANCZOS),(x+16,y+48))
    dd.text((i*400+10,12),label.replace(' / ','\n'),font=fontsmall,fill='white')
    detail.paste(scene.crop(detailbox).resize((384,888),Image.Resampling.NEAREST).crop((0,0,384,720)),(i*400+8,72))
    band=(cov>0)&(cov<255)&(raw[:,:,3]>0)
    # This fixture marks the old nearest x1 boundary, not a truth for spline geometry.
    cross=(cov>0)&~native
    metrics.append(dict(id=name,partial_occlusion_pixels_frame8=int(band.sum()),
        source_alpha_at_partial_occlusion=np.percentile(raw[:,:,3][band],[0,25,50,75,100]).tolist() if band.any() else [],
        frame8_pixels_outside_old_native_gate=int((cross&(raw[:,:,3]>0)).sum()),
        alpha_sum_frame8=float(np.rint(raw[:,:,3].astype(float)*cov/255).sum())))
board.save(OUT/'comparison.png'); detail.save(OUT/'edge-detail.png')
pair=Image.new('RGB',(1520,640),(20,23,29)); pd=ImageDraw.Draw(pair)
for j,(name,label,cov) in enumerate([variants[0],variants[-1]]):
    pd.text((j*760+12,10),'Actuel : fondu large' if j==0 else 'Proposition : Spline Fit1 + anticrenelage fin',font=fontsmall,fill='white')
    pair.paste(composite(raw,cov).crop(crop),(j*760,40))
pair.save(OUT/'before-after.png')
trace=bg.crop(crop); td=ImageDraw.Draw(trace)
local=curve-np.array(crop[:2]); td.line([tuple(p) for p in local],fill=(0,255,100),width=1)
trace.save(OUT/'spline-on-background.png')
frames=[]; alphas=[]; candidate_checks=[]
outside_distance=ndimage.distance_transform_edt(~native)
for f,old_f in zip(r['frames'],installed[0]['frames'],strict=True):
    raw=rgba(f); expected=raw.copy(); expected[:,:,3]=np.rint(raw[:,:,3].astype(float)*active_mask/255).astype(np.uint8)
    assert expected.tobytes()==(ACTIVE/old_f['asset']).read_bytes()
    assert expected.tobytes()==(get_path('bg2ee_game_root')/'iee-assets/areas/AR0517'/old_f['asset']).read_bytes()
    assert f['centre_x1']==[77,55] and f['logical_size_x1']==[160,120]
    frames.append(f['frame'])
    band=(active_mask>0)&(active_mask<255)&(raw[:,:,3]>0)
    alphas.extend(raw[:,:,3][band].tolist())
    sharp=np.rint(raw[:,:,3].astype(float)*variants[-1][2]/255).astype(np.uint8)
    outside=(sharp>0)&~native
    candidate_checks.append(dict(frame=f['frame'],partial_alpha_pixels_at_occluder=int(((variants[-1][2]>0)&(variants[-1][2]<255)&(raw[:,:,3]>0)).sum()),
        coverage_outside_old_x1_gate_pixels=int(outside.sum()),max_distance_outside_old_x1_gate_x4=float(outside_distance[outside].max()) if outside.any() else 0))
    if f['frame'] in (0,16,32,48):
        row=Image.new('RGB',(1520,640),(20,23,29)); rd=ImageDraw.Draw(row)
        for j,(name,label,cov) in enumerate([variants[0],variants[-1]]):
            rd.text((j*760+8,8),f'Frame {f["frame"]} : {label}',font=fontsmall,fill='white')
            row.paste(composite(raw,cov).crop(crop),(j*760,40))
        row.save(OUT/f'phase-{f["frame"]:02}.png')
v2.write_json(OUT/'analysis.json',dict(status='preview-only',installed=False,area='AR0517',resref='SPHINCT',
    position=[497,452],frames_verified=frames,installed_pack_matches_reconstruction_and_game=True,
    RGB_identical_source_and_installed=True,native_bridge_bypassed_by_position_binding=True,
    fit_error_x4=1,supersampling=4,hard_edge_AA_only=True,
    current_guard_x4=8,current_feather_x4=8,source_alpha_percentiles_in_current_transition=np.percentile(alphas,[0,25,50,75,100]).tolist(),
    recommendation='crisp-g0',recommendation_reason='Hard vector occlusion with subpixel coverage; no feather or inset gap; contour follows background arch.',
    variants=metrics,candidate_checks=candidate_checks,notes=['Native clamp intentionally omitted in crisp spline candidates; position-bound runtime bypasses native mask.',
        'Static map composite; no character or in-game lighting. No game writes.']))
print(json.dumps(metrics,indent=2)); print('49 installed frames match exact reconstruction; previews only')
