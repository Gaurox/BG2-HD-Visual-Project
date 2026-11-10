"""Verify actual RGB files sent to SeedVR against each native palette and mask."""
import numpy as np
from PIL import Image
from temporal import ROOT,BATCH,load,save,workflow,jobkey
from bam_export import decode_bam
from export_bam_frames import read_bam


def main():
    reports=[]
    for a in load(BATCH/'batch.json')['jobs']:
        run=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']
        assert load(run/'run.json')['result']['sealed']
        frames,_,tr=decode_bam(read_bam(ROOT/a['source']))
        p=np.array(load(ROOT/a['palette_file'])['palette_rgb'],np.uint8)
        manifest=load(run/'00-frames-x1/manifest.json')
        pad=load(run/'recipe.json')['parameters']['pad_x1']
        count=0
        for f,(idx,_,_,_) in zip(manifest['frames'],frames):
            name=f['file'];x,y=f['canvas_offset'];h,w=idx.shape
            with Image.open(run/'00-frames-x1/rgb'/name) as im:rgb=np.array(im.convert('RGB'))
            with Image.open(run/'00-frames-x1/alpha'/name) as im:alpha=np.array(im.convert('L'))
            with Image.open(run/'01-spatial-x4/00_padded_x1'/name) as im:padded=np.array(im.convert('RGB'))
            visible=idx!=tr
            assert np.array_equal(rgb[y:y+h,x:x+w][visible],p[idx][visible]),(jobkey(a),name,'RGB palette')
            expected=np.zeros_like(alpha);expected[y:y+h,x:x+w]=visible.astype(np.uint8)*255
            assert np.array_equal(alpha,expected),(jobkey(a),name,'input alpha')
            assert np.array_equal(padded[pad:pad+rgb.shape[0],pad:pad+rgb.shape[1]],rgb)
            count+=1
        reports.append({'job_id':jobkey(a),'passed':True,'frames':count,
            'frame_manifest_sha256':workflow.sha256_file(run/'00-frames-x1/manifest.json')})
    save(BATCH/'input-palette-alpha-verification.json',{'passed':True,'contexts':len(reports),
        'source_frame_contexts':sum(r['frames'] for r in reports),'actual_model_rgb_matches_native_palette':True,
        'binary_input_alpha_exact':True,'normal_native_palette_alpha':'verified independently per interpolated output by verify.py',
        'results':reports})
    print('Actual SeedVR input palette/alpha PASS:',len(reports),'contexts,',sum(r['frames'] for r in reports),'frames')


if __name__=='__main__':main()
