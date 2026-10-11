"""Realize the immutable BMP palette before ReboutCX; preserve native geometry/cycles."""
from common import *
from PIL import Image
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata
from reboutcx_batch import load_model,infer_x4_box_x2
from run_animation_reboutcx_x4 import filled_rgb
import hashlib

JOBS=[('AM3000E','PLT_MAGE'),('FLM2PUR',None),('FLM2PUR','PLT_PURP')]

def main():
    BATCH.mkdir(parents=True,exist_ok=True)
    descriptor,versions=load_model(get_path('reboutcx_model'),device='cuda:0',fp16=True)
    reports=[]
    for ref,pal in JOBS:
        tag=ref+'-'+(pal or 'embedded');out=BATCH/('spatial-'+tag);out.mkdir(parents=True,exist_ok=False)
        src=ROOT/f'animations/ressources/{ref}/source.bam';data=read_bam(src)
        frames,palette,tr=decode_bam(data)
        palette_source=None
        if pal:
            palette_source=ROOT/f'animations/tmp/lot45-analysis-20261011-v1/{pal}.bmp'
            im=Image.open(palette_source);assert im.mode=='P' and im.size==(1,1)
            palette=np.array(im.getpalette(),np.uint8).reshape(256,3)
        left=min(-cx for _,cx,_,_ in frames);top=min(-cy for _,_,cy,_ in frames)
        right=max(-cx+idx.shape[1] for idx,cx,_,_ in frames);bottom=max(-cy+idx.shape[0] for idx,_,cy,_ in frames)
        arrays={};records=[];source_hashes=[]
        for index,(idx,cx,cy,tr) in enumerate(frames):
            h,w=idx.shape;x,y=-cx-left,-cy-top
            rgba=np.dstack([palette[idx],(idx!=tr).astype(np.uint8)*255]);rgba[rgba[...,3]==0,:3]=0
            source_hashes.append(hashlib.sha256(rgba.tobytes()+np.array([cx,cy,w,h],np.int32).tobytes()).hexdigest())
            aligned=np.zeros((bottom-top,right-left,4),np.uint8);aligned[y:y+h,x:x+w]=rgba
            Image.fromarray(aligned).save(out/f'native-{index:03d}.png')
            result,_=infer_x4_box_x2(descriptor,filled_rgb(aligned),fp16=True)
            alpha=aligned[...,3].repeat(4,0).repeat(4,1)
            p=np.dstack([result,alpha])[y*4:(y+h)*4,x*4:(x+w)*4].copy()
            p[p[...,3]==0,:3]=0;arrays[(ref,index)]=p
            Image.fromarray(p).save(out/f'x4-{index:03d}.png')
            records.append(dict(frame=index,logical_size_x1=[w,h],physical_size_x4=[w*4,h*4],centre_x1=[cx,cy]))
            print(tag,index+1,'/',len(frames),flush=True)
        assert len(set(source_hashes))==len(source_hashes),tag+': realized source duplicate poses need hold collapse'
        geometries={(tuple(f['logical_size_x1']),tuple(f['centre_x1'])) for f in records}
        r=dict(resref=ref,frame_count=len(frames),cycle_count=len(cycle_metadata(data,len(frames))),
            geometry_mode='uniform' if len(geometries)==1 else 'per-frame',frames=records,playback_mode='Native',
            native_fps=dict(numerator=0,denominator=0),target_fps=dict(numerator=0,denominator=0),
            cycles=[dict(cycle=c['cycle'],native_frame_indices=c['frame_indices'],timeline_frame_indices=[]) for c in cycle_metadata(data,len(frames))])
        pack=write_pack(BATCH/('base-'+tag),[r],arrays)
        report=dict(status='completed',resref=ref,palette=pal or 'embedded',source_bam=rel(src),source_bam_sha256=v.sha256_file(src),
            palette_source=rel(palette_source) if palette_source else None,palette_sha256=v.sha256_file(palette_source) if palette_source else None,
            model='config://reboutcx_model',model_sha256=v.sha256_file(get_path('reboutcx_model')),versions=versions,
            source_frames=len(frames),duplicate_source_frames=[],cycle_lookups=r['cycles'],aligned_size_x1=[right-left,bottom-top],
            base_pack=rel(pack),base_pack_manifest_sha256=v.sha256_file(pack/'manifest.json'),
            recipe='BMP source palette realized on indices before inference; native transparency; aligned nearest-opaque fill -> ReboutCX x4 fp16')
        v.write_json(out/'manifest.json',report);reports.append(report)
    v.write_json(BATCH/'spatial.json',reports)

if __name__=='__main__':main()
