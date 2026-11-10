"""SPDEATH3 Bezier reconstruction, with thin-feature-safe Gaussian alpha edges."""
from prepare import ROOT,OUT,load,save
import sys,hashlib
sys.path.append(str(ROOT/'.tools/potracer'))
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from build_spatial_spline_alpha import potrace_alpha

PAD=20

def build(a,sp):
    target=OUT/'masks'/a['resref'];cache=target/'masks.npz'
    if cache.exists():
        z=np.load(cache);return {int(k):z[k] for k in z.files}
    source=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'00-frames-x1'
    fm=load(source/'manifest.json');result={};reports=[];dedup={}
    for f in fm['frames']:
        alpha=np.array(Image.open(source/'alpha'/f['file']).convert('L')).repeat(4,0).repeat(4,1)
        original=np.pad(alpha,PAD);sig=hashlib.sha256(original.tobytes()).hexdigest()
        if sig in dedup:
            out,report=dedup[sig]
        elif not original.any():
            out=original.copy();report={'empty':True}
        else:
            curve,trace=potrace_alpha(original,threshold=0,alphamax=1.334,opttolerance=.1,supersample=8,band=10000)
            # Local medial thickness protects thin shafts/fingers attached to broad bodies.
            d=ndi.distance_transform_edt(original>0)
            ridge=(d>0)&(d>=ndi.maximum_filter(d,size=3))
            near=ndi.distance_transform_edt(~ridge,return_distances=False,return_indices=True)
            sigma=np.clip(d[tuple(near)]/4,.5,4)
            levels=[.5,1.,2.,4.];blur=np.zeros(curve.shape,np.float32)
            for j in range(len(levels)-1):
                low,high=levels[j:j+2];where=(sigma>=low)&(sigma<=high)
                t=(sigma-low)/(high-low)
                b0=ndi.gaussian_filter(curve.astype(np.float32),low,mode='constant',truncate=4)
                b1=ndi.gaussian_filter(curve.astype(np.float32),high,mode='constant',truncate=4)
                blur[where]=(b0*(1-t)+b1*t)[where]
            edge=ndi.distance_transform_edt(curve>0)
            t=np.clip((edge-2*sigma)/(2*sigma),0,1);weight=1-t*t*(3-2*t)
            out=np.rint(curve*(1-weight)+blur*weight).clip(0,255).astype(np.uint8)
            labels,n=ndi.label(original>0,np.ones((3,3)))
            mass=np.bincount(labels.ravel(),weights=out.ravel(),minlength=n+1)
            assert np.all(mass[1:]>0),(a['resref'],f['frame'],'lost native component')
            assert not out[[0,-1],:].any() and not out[:,[0,-1]].any()
            report={'trace':trace,'sigma_range_x4':[float(sigma.min()),float(sigma.max())],
                'alpha_mass_ratio':float(out.sum())/float(original.sum()),
                'native_components':n,'components_lost':0,'fractional_alpha_pixels':int(((out>0)&(out<255)).sum())}
            dedup[sig]=(out,report)
        result[f['frame']]=out;reports.append({'native_frame':f['frame'],**report})
    target.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(cache,**{str(k):v for k,v in result.items()})
    save(target/'report.json',{'resref':a['resref'],'method':'SPDEATH3 Potrace1.334/SS8, then edge-only Gaussian alpha .5..4 adapted to local thickness',
        'no_inset':True,'rgb_not_filtered':True,'native_masks':reports})
    return result
