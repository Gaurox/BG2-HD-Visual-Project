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

GREEN={'FLLGBLUE':47,'FLMDBLU':39,'FLSM1PUR':245}
original_export=producer.export_frames
original_recipe=producer.recipe_snapshot

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
if __name__=='__main__':raise SystemExit(producer.main())
