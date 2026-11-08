"""Canonical spatial producer with explicit source-derived green-matte exception."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_effect_spatial as producer
from bam_export import decode_bam
from export_bam_frames import read_bam,fill_transparent,save_png_atomic

GREEN={'WHIRLY':178}
original_export=producer.export_frames
original_recipe=producer.recipe_snapshot
original_upscale=producer.upscale_frames

def recipe(plan):
    r=original_recipe(plan)
    r['tools'].append(producer.file_evidence(ROOT,'producer',Path(__file__)))
    if plan.resref in GREEN:
        r['alpha_policy']='Source-derived: exact green palette index connected to border removed in working export only; native BAM unchanged; then nearest4.'
        r['green_index']=GREEN[plan.resref]
    return r

def export(plan,source,resume):
    m=original_export(plan,source,resume)
    if plan.resref not in GREEN or m.get('green_matte_derivation'):return m
    frames,pal,tr=decode_bam(read_bam(plan.source));green=GREEN[plan.resref]
    assert list(map(int,pal[green]))==[0,255,0]
    counts=[]
    for row,(indices,cx,cy,_) in zip(m['frames'],frames):
        labels,_=ndi.label(indices==green)
        boundary=set(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])).tolist())-{0}
        removed=np.isin(labels,list(boundary))
        x,y=row['canvas_offset'];h,w=indices.shape
        rgba=np.asarray(Image.open(plan.frame_root/'rgba'/row['file']).convert('RGBA')).copy()
        crop=rgba[y:y+h,x:x+w];crop[removed]=0
        alpha=rgba[:,:,3];rgb=fill_transparent(rgba[:,:,:3],alpha)
        assert alpha.any(),(plan.resref,row['frame'],'empty green derivation')
        for kind,array in [('rgba',rgba),('alpha',alpha),('rgb',rgb)]:
            path=plan.frame_root/kind/row['file'];save_png_atomic(Image.fromarray(array),path)
            row[kind+'_sha256']=producer.workflow.sha256_file(path)
        counts.append(int(removed.sum()))
    m['green_matte_derivation']={'palette_index':green,'policy':'exact indexed green connected to source-frame border; source/palette/cycles unchanged','removed_pixels_by_record':counts,'producer':producer.file_evidence(ROOT,'producer',Path(__file__))}
    producer.write_json(plan.frame_root/'manifest.json',m)
    return producer.validate_frame_stage(ROOT,plan.frame_root,source)

producer.recipe_snapshot=recipe
producer.export_frames=export
def upscale(plan,frame_manifest,resume):
    result=original_upscale(plan,frame_manifest,resume)
    # RIPPLE_1 ends in an opaque, entirely black native control frame. SeedVR
    # must not invent a visible event during that pause (last-lot LAVABUB2 lesson).
    if plan.resref!='RIPPLE_1' or result.get('native_black_controls'):return result
    frames,pal,tr=decode_bam(read_bam(plan.source));controls=[]
    for i,(idx,_,_,_) in enumerate(frames):
        if pal[idx][idx!=tr].any():continue
        f=result['frames'][i];stage=plan.spatial_root
        rgba=np.array(Image.open(stage/f['aligned_rgba_xn']).convert('RGBA'));rgba[:,:,:3]=0
        aligned=Image.fromarray(rgba);crop=aligned.crop(tuple(f['runtime_crop_box_xn']))
        for key,im in [('aligned_rgba_xn',aligned),('rgba_xn',crop),('rgb_xn',crop.convert('RGB')),('alpha_xn',crop.getchannel('A'))]:
            path=stage/f[key];im.save(path);f[key+'_sha256']=producer.workflow.sha256_file(path)
        path=stage/f['raw_rgba_xn'];path.write_bytes(crop.tobytes());f['raw_rgba_xn_sha256']=producer.workflow.sha256_file(path);controls.append(i)
    if controls:
        from upscale_animation_frames import make_contact_sheet
        preview=plan.spatial_root/result['preview'];make_contact_sheet([plan.spatial_root/f['rgba_xn'] for f in result['frames']],preview)
        result.update(native_black_controls=controls,native_black_control_policy='Native all-zero RGB forcibly retained, source alpha unchanged; no event invented on black pause',preview_sha256=producer.workflow.sha256_file(preview))
        producer.write_json(plan.spatial_root/'manifest.json',result)
    return result
producer.upscale_frames=upscale
if __name__=='__main__':
    batchroot=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
    if (batchroot/'gpu-paused.json').exists():
        permit=batchroot/'gpu-one-test.json'
        allowed=json.loads(permit.read_text()) if permit.exists() else {}
        requested=sys.argv[sys.argv.index('--resref')+1] if '--resref' in sys.argv else None
        if allowed.get('state')!='running' or allowed.get('resref')!=requested:
            raise SystemExit('GPU paused by user; no SeedVR except authorized one-asset test.')
    # One whole asset owns SeedVR at a time; the two batch workers share this lock.
    # It also lets an earlier already-running worker drain before the next asset.
    import msvcrt,time,urllib.request
    lockpath=ROOT/'.tmp/magic-water-seedvr-exclusive.lock';lockpath.parent.mkdir(exist_ok=True)
    with lockpath.open('a+b') as lock:
        lock.seek(0);lock.write(b'0');lock.flush()
        while True:
            try:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);break
            except OSError:time.sleep(1)
        quiet=None
        while True:
            with urllib.request.urlopen('http://127.0.0.1:8188/queue',timeout=15) as response:q=json.load(response)
            if q.get('queue_running') or q.get('queue_pending'):quiet=None
            elif quiet is None:quiet=time.monotonic()
            elif time.monotonic()-quiet>=3:break
            time.sleep(.5)
        raise SystemExit(producer.main())
