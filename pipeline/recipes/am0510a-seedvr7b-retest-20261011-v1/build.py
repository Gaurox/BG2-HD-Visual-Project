"""AM0510A fresh SeedVR7B trial, same arch mask and original duration."""
from pathlib import Path
import sys,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/recipes/lot45-final-20261011-v1'))
from common import v,pixels,write_pack,rel

REF='AM0510A'
TAG='am0510a-seedvr7b-retest-20261011-v1'
RUN=ROOT/'animations/ressources/AM0510A/runs/am0510a-seedvr7b-lab-x4-retest-20261011-v1'
OUT=ROOT/'animations/batches'/TAG
PREVIOUS=ROOT/'animations/batches/lot45-final-20261011-v1/final-AM0510A'
MASK=ROOT/'animations/batches/lot45-final-20261011-v1/mask-AM0510A/mask.png'
BACKGROUND=ROOT/'animations/ressources/AM0510A/paint-ready-am0510a/background-x4-512.png'

def main():
    assert not (OUT/'manifest.json').exists(),'completed trial is immutable'
    OUT.mkdir(parents=True,exist_ok=True)
    source=RUN/'resources/AM0510A/01_frames_x1'
    fm=v.load_json(source/'manifest.json')
    hashes=[hashlib.sha256(Image.open(source/'rgba'/f['file']).convert('RGBA').tobytes()).hexdigest() for f in fm['frames']]
    assert len(hashes)==9 and len(set(hashes))==9,'duplicate native poses need duration-preserving collapse'
    temporal=OUT/'temporal'
    plan=v.build_plan(RUN,RUN/'03_runtime_pack',[REF],model='apo-8',transparent_rgb_mode='nearest-opaque-dilate')
    v.build_run(RUN,RUN/'03_runtime_pack',temporal,[REF],plan['plan_sha256'],v.DEFAULT_TVAI_FFMPEG,v.DEFAULT_TVAI_MODEL_DIR,
        'apo-8','-2','ffmpeg',False,transparent_rgb_mode='nearest-opaque-dilate')
    pack=temporal/'03_runtime_pack';r=v.validate_v2_pack(pack)[1][0]
    old=v.validate_v2_pack(PREVIOUS)[1][0]
    assert r['cycles']==old['cycles'] and r['frame_count']==18
    assert r['native_fps']==old['native_fps'] and r['target_fps']==old['target_fps']
    mask=np.asarray(Image.open(MASK).convert('L'))
    arrays={};differences=[]
    for f in r['frames']:
        p=pixels(pack,f)
        p[...,3]=np.rint(p[...,3].astype(float)*mask/255).astype(np.uint8)
        p[p[...,3]==0,:3]=0
        prior=pixels(PREVIOUS,old['frames'][f['frame']])
        assert np.array_equal(p[...,3],prior[...,3]),'same alpha required for backend comparison'
        assert all(f[k]==old['frames'][f['frame']][k] for k in ('logical_size_x1','physical_size_x4','centre_x1'))
        differences.append(dict(frame=f['frame'],visible_rgb_mean_absolute_difference=float(np.abs(p[...,:3].astype(float)-prior[...,:3])[p[...,3]>0].mean())))
        arrays[(REF,f['frame'])]=p
    final=write_pack(OUT/'final-assets',[r],arrays)
    assert len({hashlib.sha256(p.tobytes()).hexdigest() for p in arrays.values()})==18
    preview(r,old,arrays)
    v.write_json(OUT/'manifest.json',dict(schema='bg2-upscale-animation-trial-v1',status='completed',created_utc=v.utc_now(),resref=REF,
        source_run=rel(RUN),source_run_manifest_sha256=v.sha256_file(RUN/'manifest.json'),
        final_pack=rel(final),final_pack_manifest_sha256=v.sha256_file(final/'manifest.json'),
        comparison_pack=rel(PREVIOUS),comparison_pack_manifest_sha256=v.sha256_file(PREVIOUS/'manifest.json'),
        mask=rel(MASK),mask_sha256=v.sha256_file(MASK),
        recipe='fresh SeedVR2 7B INT8 LAB x4, seed20261011, pad32 -> Apollo8 15 to 30fps -> same authored arch/motion-weighted halo mask',
        native_duplicate_poses=0,final_duplicate_frames=0,frame_count=18,native_duration_seconds=9/15,output_duration_seconds=18/30,
        geometry_and_cycles_preserved=True,alpha_byte_identical_to_installed=True,differences=differences,
        comparison=rel(OUT/'comparison.png'),qa_status='pending-user-review',installation_status='not-installed',release_status='not-selected'))
    print('AM0510A NEW SEEDVR TEST: 9 unique native poses, 18 frames /30fps/0.6s, same mask and geometry',flush=True)

def preview(r,old,arrays):
    bg=Image.open(BACKGROUND).convert('RGBA')
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',25)
    except OSError:font=ImageFont.load_default()
    timeline=r['cycles'][0]['timeline_frame_indices'];old_timeline=old['cycles'][0]['timeline_frame_indices']
    def pair(phase):
        result=Image.new('RGB',(1064,580),(32,32,32));draw=ImageDraw.Draw(result)
        draw.text((16,10),'SeedVR 7B x4 - version en jeu',font=font,fill='white')
        draw.text((548,10),'SeedVR 7B x4 - nouvel essai',font=font,fill='white')
        a=Image.fromarray(pixels(PREVIOUS,old['frames'][old_timeline[phase]]))
        b=Image.fromarray(arrays[(REF,timeline[phase])])
        result.paste(Image.alpha_composite(bg,a).convert('RGB'),(10,58))
        result.paste(Image.alpha_composite(bg,b).convert('RGB'),(542,58))
        return result
    pair(0).save(OUT/'comparison.png')
    frames=[pair(i) for i in range(18)]
    frames[0].save(OUT/'comparison.gif',save_all=True,append_images=frames[1:],duration=[30,30,40]*6,loop=0)
    sheet=Image.new('RGB',(1064,1740),(32,32,32))
    for row,phase in enumerate((0,6,12)):sheet.paste(pair(phase),(0,row*580))
    sheet.save(OUT/'comparison-three-poses.png')

if __name__=='__main__':main()
