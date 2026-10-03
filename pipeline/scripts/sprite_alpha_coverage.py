"""Light inward alpha smoothing; exact source support, no contour refitting."""
import numpy as np
from scipy import ndimage

def coverage(indices, *, kind=0, sigma=0.65, strength=0.8, minimum=176,
             band=2.0, thin_radius=1.5):
    indices=np.asarray(indices)
    if indices.dtype!=np.uint8 or indices.ndim!=2 or not indices.size:
        raise ValueError('invalid index mask')
    if (kind not in (0,1) or not np.isfinite([sigma,strength,band,thin_radius]).all()
        or sigma<=0 or not 0<strength<=1 or not 1<=minimum<=255 or band<=0 or thin_radius<=0):
        raise ValueError('invalid alpha recipe')
    editable_class=indices >= (3 if kind==0 else 4)
    # Reserved opaque indices contribute to silhouette context but cannot be modified.
    opaque=indices>=2
    pad=max(4,int(np.ceil(sigma*3))+1)
    padded=np.pad(opaque,pad)
    distance=ndimage.distance_transform_edt(padded)
    core=distance>thin_radius
    near_core=ndimage.distance_transform_edt(~core)<=thin_radius if core.any() else np.zeros_like(core)
    editable=np.pad(editable_class,pad)&(distance<=band)&near_core
    blurred=ndimage.gaussian_filter(padded.astype(np.float64),sigma,mode='constant',cval=0,truncate=3.0)
    softened=np.clip(np.rint(255*(1-strength+strength*blurred)),minimum,255).astype(np.uint8)
    result=np.full(padded.shape,255,np.uint8)
    result[editable]=softened[editable]
    result=result[pad:-pad,pad:-pad]
    assert np.all(result[~editable_class]==255) and result.min()>0
    # Strictly positive coverage preserves every visible component and every hole.
    return result,dict(status='alpha-smoothed' if np.any(result!=255) else 'identity',
        changed_pixels=int((result!=255).sum()),cleared_pixels=0,
        intermediate_pixels=int((result!=255).sum()),minimum_coverage=int(result.min()),
        protected_thin_pixels=int((np.pad(editable_class,pad)&~near_core).sum()),
        source_support_preserved=True)

def apply(rgba, mask):
    if (rgba.dtype!=np.uint8 or rgba.ndim!=3 or rgba.shape[2]!=4 or mask.dtype!=np.uint8
        or mask.shape!=rgba.shape[:2]):raise ValueError('invalid RGBA/coverage extent')
    result=rgba.copy()
    result[...,3]=((rgba[...,3].astype(np.uint16)*mask+127)//255).astype(np.uint8)
    result[result[...,3]==0]=0
    return result
