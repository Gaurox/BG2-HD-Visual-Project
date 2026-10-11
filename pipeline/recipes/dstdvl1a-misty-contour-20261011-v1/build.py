"""DSTDVL1A edge-only feather/Gaussian from installed AR0411; no installation."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
from workspace_paths import get_path

TAG='dstdvl1a-misty-contour-20261011-v1'
SOURCE=ROOT/'animations/packs-par-zone/ar0411-bubbles2-dstdvl1abc-plus-planar-sphere-20260911/AR0411'
RUN=ROOT/'animations/ressources/DSTDVL1A/runs'/TAG
BATCH=ROOT/'animations/batches'/TAG
LIVE=get_path('bg2ee_game_root')/'iee-assets/areas/AR0411'
PAD=24

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def rel(path): return path.relative_to(ROOT).as_posix()
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def smoothstep(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)
def treat(source,width,sigma):
    if not source[:,:,3].any(): return source.copy(),np.ones(source.shape[:2],bool)
    padded=np.pad(source,((PAD,PAD),(PAD,PAD),(0,0)))
    dist=distance_transform_edt(padded[:,:,3]>0)
    factor=smoothstep((dist-1)/width)
    feathered=padded.astype(np.float32)*factor[:,:,None]
    blurred=gaussian_filter(feathered,(sigma,sigma,0),mode='constant',cval=0,truncate=4)
    edge=1-smoothstep((dist-width-2*sigma)/(2*sigma))
    result=np.rint(feathered*(1-edge[:,:,None])+blurred*edge[:,:,None]).clip(0,255).astype(np.uint8)
    result[:,:,:3]=np.minimum(result[:,:,:3],result[:,:,3:4])
    core=dist>=width+4*sigma
    assert np.array_equal(result[core],padded[core]),'Interior changed'
    assert not result[0].any() and not result[-1].any() and not result[:,0].any() and not result[:,-1].any()
    return result,core

def build():
    assert not RUN.exists() and not BATCH.exists(),'Immutable output exists'
    _,resources=v.validate_v2_pack(SOURCE)
    original=next(r for r in resources if r['resref']=='DSTDVL1A')
    assert (LIVE/v.REGISTRY_NAME).read_bytes().count(v.resource_binary_v2(original,3))==1
    resource=copy.deepcopy(original)
    out=RUN/'03_runtime_pack';out.mkdir(parents=True)
    BATCH.mkdir(parents=True)
    assets={a['name']:a for a in resource['assets']}
    changed=0;core_pixels=0;representative=None
    for frame in resource['frames']:
        blob=(LIVE/frame['asset']).read_bytes()
        assert hashlib.sha256(blob).hexdigest()==frame['sha256']
        w,h=frame['physical_size_x4']
        source=np.frombuffer(blob,np.uint8).reshape(h,w,4)
        assert np.all(source[:,:,:3]<=source[:,:,3:4]),'Input must already be premultiplied'
        result,core=treat(source,20,4)
        core_pixels+=int(core.sum())
        if source[:,:,3].any():
            changed+=1
            frame['physical_size_x4']=[w+PAD*2,h+PAD*2]
            frame['logical_size_x1']=[x+PAD//2 for x in frame['logical_size_x1']]
            frame['centre_x1']=[x+PAD//4 for x in frame['centre_x1']]
            assert [-frame['centre_x1'][0]*4+PAD,-frame['centre_x1'][1]*4+PAD]==[-original['frames'][frame['frame']]['centre_x1'][0]*4,-original['frames'][frame['frame']]['centre_x1'][1]*4]
        destination=out/frame['asset'];destination.write_bytes(result.tobytes())
        frame['sha256']=sha(destination);frame['bytes']=destination.stat().st_size
        assets[frame['asset']]['sha256']=frame['sha256'];assets[frame['asset']]['bytes']=frame['bytes']
        if frame['frame']==10: representative=source.copy()
    assert resource['cycles']==original['cycles']
    binary=v.registry_v2_from_resources([resource],3)
    (out/v.REGISTRY_NAME).write_bytes(binary)
    write(out/'manifest.json',dict(schema=v.PACK_SCHEMA,status='completed',created_utc=v.utc_now(),scale=4,registry_version=3,
        runtime_contract=dict(feature='TimedTimeline',clock='QPC-pause-aware',registry_version=3),registry=v.REGISTRY_NAME,
        registry_sha256=sha(out/v.REGISTRY_NAME),registry_bytes=len(binary),resource_count=1,frame_count=resource['frame_count'],
        timed_resources=['DSTDVL1A'],raw_bytes=sum(a['bytes'] for a in resource['assets']),runtime_budget_enforced=True,base_assets=[],new_assets=[],resources=[resource]))
    v.validate_v2_pack(out)
    write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),resrefs=['DSTDVL1A'],
        source_pack=rel(SOURCE),source_pack_manifest_sha256=sha(SOURCE/'manifest.json'),
        runtime_pack='03_runtime_pack',runtime_pack_manifest_sha256=sha(out/'manifest.json'),
        visual_treatment=dict(kind='edge-only-premultiplied-feather-gaussian',inner_feather_x4=20,sigma_x4=4,padding_x4=PAD,
            formula='smoothstep((distance(alpha>0)-1)/20) multiplies premultiplied RGBA; Gaussian sigma4 blended only in edge band; core distance>=36 unchanged',
            world_alignment='24px x4 padding -> centre+6 x1 and dimensions+12 x1; zero displacement',
            timing='installed 139frames / 214phases / 30fps copied verbatim; September16 segmented-hold candidate not substituted'),
        qa_status='preview-only; not installed; pending-user-review'))
    variants=[('Actuel',None,None),('Doux : fondu12 / sigma2',12,2),('Recommande : fondu20 / sigma4',20,4),('Brume forte : fondu32 / sigma6',32,6)]
    w,h=representative.shape[1]+PAD*2,representative.shape[0]+PAD*2
    board=Image.new('RGB',((w+12)*4,(h+50)*2+30),(25,25,25));draw=ImageDraw.Draw(board)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    for col,(label,width,sigma) in enumerate(variants):
        rgba=np.pad(representative,((PAD,PAD),(PAD,PAD),(0,0))) if width is None else treat(representative,width,sigma)[0]
        for row,bg in enumerate([35,160]):
            # Premultiplied over, controlled backgrounds. This is not an ingame capture.
            background=np.full(rgba.shape[:2]+(3,),bg,np.float32)
            rgb=np.rint(rgba[:,:,:3].astype(np.float32)+background*(1-rgba[:,:,3:4]/255)).clip(0,255).astype(np.uint8)
            x=col*(w+12);y=30+row*(h+50)
            draw.text((x+6,y+3),label,font=font,fill='white')
            board.paste(Image.fromarray(rgb),(x,y+30))
    draw.text((6,3),'DSTDVL1A frame10 - simulation sur fonds controles, pas une capture ingame',font=font,fill='white')
    board.save(BATCH/'DSTDVL1A-misty-contour-comparison.png')
    write(Path(__file__).parent/'checks.json',dict(passed=True,source_resource_matches_installed_AR0411=True,frame_count=139,
        changed_frames=changed,timeline_phases=214,timing_verbatim=True,core_pixels_byte_identical=core_pixels,
        premultiplied_RGBA=True,transparent_padded_canvas_edges=True,world_displacement_x1=[0,0],installation='none',
        preview=rel(BATCH/'DSTDVL1A-misty-contour-comparison.png')))
    print('Preview + runtime candidate ready; cadence/core/alignment preserved; no installation')

if __name__=='__main__': build()
