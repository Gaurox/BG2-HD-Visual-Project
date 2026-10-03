"""CPU-only inward spline coverage; preserve native special classes and thin features."""
import numpy as np
from scipy import ndimage
from build_per_frame_spline_alpha_30fps_v2 import fit_component

def coverage(indices, *, kind=0, fit_error=1.0, band=2.0, thin_radius=2.0, supersample=4):
    indices=np.asarray(indices)
    if indices.dtype!=np.uint8 or indices.ndim!=2 or not indices.size:raise ValueError('invalid index mask')
    if kind not in (0,1) or fit_error<=0 or band<=0 or thin_radius<=0 or supersample<2:raise ValueError('invalid spline recipe')
    binary=indices >= (3 if kind==0 else 4)
    result=np.full(binary.shape,255,np.uint8)
    if not binary.any():return result,dict(status='special-only',components=0,changed_pixels=0)
    padded=np.pad(binary,4);labels,count=ndimage.label(padded,np.ones((3,3),np.uint8))
    fitted=np.zeros(padded.shape,np.uint8)
    for label in range(1,count+1):
        component=labels==label
        # Use each component's bounding box; protect disconnected tiny features.
        if component.sum()<16:fitted[component]=255;continue
        yy,xx=np.nonzero(component);y0,y1=max(0,yy.min()-3),min(padded.shape[0],yy.max()+4)
        x0,x1=max(0,xx.min()-3),min(padded.shape[1],xx.max()+4)
        local=component[y0:y1,x0:x1]
        outer,_=fit_component(local,fit_error,1.5,supersample)
        holes=ndimage.binary_fill_holes(local)&~local
        hole_labels,hole_count=ndimage.label(holes)
        for hole in range(1,hole_count+1):
            hm=hole_labels==hole
            if hm.sum()<16:continue
            ha,_=fit_component(hm,fit_error,1.5,supersample)
            outer=((outer.astype(np.uint16)*(255-ha.astype(np.uint16))+127)//255).astype(np.uint8)
        fitted[y0:y1,x0:x1]=np.maximum(fitted[y0:y1,x0:x1],outer)
    distance=ndimage.distance_transform_edt(padded)
    core=distance>thin_radius
    near_core=ndimage.distance_transform_edt(~core)<=thin_radius if core.any() else np.zeros_like(core)
    editable=padded&(distance<=band)&near_core
    result_padded=np.full(padded.shape,255,np.uint8);result_padded[editable]=fitted[editable]
    result=result_padded[4:-4,4:-4]
    assert np.all(result[~binary]==255)
    return result,dict(status='fitted',components=int(count),changed_pixels=int((result!=255).sum()),
        cleared_pixels=int((result==0).sum()),intermediate_pixels=int(((result>0)&(result<255)).sum()),
        protected_thin_pixels=int((padded&~near_core).sum()),editable_band_pixels=int(editable.sum()))

def apply(rgba, mask):
    if rgba.dtype!=np.uint8 or rgba.ndim!=3 or rgba.shape[2]!=4 or mask.dtype!=np.uint8 or mask.shape!=rgba.shape[:2]:
        raise ValueError('invalid RGBA/coverage extent')
    result=rgba.copy();result[...,3]=((rgba[...,3].astype(np.uint16)*mask+127)//255).astype(np.uint8)
    result[result[...,3]==0]=0
    return result
