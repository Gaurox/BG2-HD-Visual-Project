"""Offline only: bounded smoothed signed-distance contour and CPU Catmull reference."""
import numpy as np
from scipy import ndimage

RECIPE=dict(method='bounded-smoothed-SDF-with-area-coverage',sigma_x2=2.0,
    distance_bias_limit_x2=1.0,core_radius_x2=2.0,near_core_radius_x2=3.0,
    area_supersampling=8,colour_filter='CatmullRom-premultiplied-16-taps',
    native_shadows='separate unchanged source layer',
    topology='preserve foreground-8 and background-4 components at texel centres',installation=False)

def signed_distance(mask):
    inside=ndimage.distance_transform_edt(mask)
    outside=ndimage.distance_transform_edt(~mask)
    return np.where(mask,inside-0.5,-outside+0.5)

def reconstruct(indices):
    """Return floating field at x2 texel centers, including six clear border texels."""
    if indices.dtype!=np.uint8 or indices.ndim!=2:raise ValueError('invalid index mask')
    pad=6;opaque=np.pad(indices>=2,pad)
    original=signed_distance(opaque)
    smooth=ndimage.gaussian_filter(original,RECIPE['sigma_x2'],mode='nearest')
    inside=ndimage.distance_transform_edt(opaque)
    core=inside>=RECIPE['core_radius_x2']
    near=ndimage.distance_transform_edt(~core) if core.any() else np.full(opaque.shape,999.0)
    weight=np.clip((RECIPE['near_core_radius_x2']-near)/1.5,0,1)
    special_opaque=np.pad(indices==2,pad)
    weight[special_opaque]=0
    field=original+weight*np.clip(smooth-original,-1.0,1.0)
    # Admit sign changes only while preserving both foreground components and holes.
    fg_structure=np.ones((3,3));bg_structure=ndimage.generate_binary_structure(2,1)
    fg_count=ndimage.label(opaque,fg_structure)[1]
    bg_count=ndimage.label(~opaque,bg_structure)[1]
    binary=opaque.copy();target=field>0
    yy,xx=np.nonzero(target!=opaque)
    order=np.argsort(-np.abs(field[yy,xx]-original[yy,xx]));pending=list(zip(yy[order],xx[order]))
    for attempt in range(2):
        rejected=[]
        for y,x in pending:
            binary[y,x]=target[y,x]
            if (ndimage.label(binary,fg_structure)[1]!=fg_count or
                ndimage.label(~binary,bg_structure)[1]!=bg_count):
                binary[y,x]=opaque[y,x];rejected.append((y,x))
        pending=rejected
    for y,x in pending:field[y,x]=original[y,x]
    assert np.array_equal(field>0,binary)
    new=field>0
    old_count=ndimage.label(opaque,np.ones((3,3)))[1]
    new_count=ndimage.label(new,np.ones((3,3)))[1]
    report=dict(opaque_pixels_before=int(opaque.sum()),opaque_pixels_after=int(new.sum()),
        solid_components_before=int(old_count),solid_components_after=int(new_count),
        background_components_before=int(bg_count),background_components_after=int(ndimage.label(~new,bg_structure)[1]),
        topology_protected_pixels=len(pending),
        added_solid_pixels=int((new&~opaque).sum()),removed_solid_pixels=int((opaque&~new).sum()),
        area_change_percent=round((new.sum()/opaque.sum()-1)*100,4),
        maximum_field_change_x2=float(np.abs(field-original).max()),
        maximum_added_solid_distance_x2=float(np.max(np.where(new&~opaque,-original,0))),
        maximum_removed_solid_distance_x2=float(np.max(np.where(opaque&~new,original,0))))
    return field.astype(np.float32),report

def weights(t):
    t2=t*t;t3=t2*t
    return np.stack((-.5*t3+t2-.5*t,1.5*t3-2.5*t2+1,-1.5*t3+2*t2+.5*t,.5*t3-.5*t2))

def catmull(rgba,zoom):
    """Shader-equivalent mathematical sampling, float64 CPU, straight RGBA output."""
    h,w=rgba.shape[:2];oh,ow=int(np.ceil(h*zoom)),int(np.ceil(w*zoom))
    y=(np.arange(oh)+.5)/zoom-.5;x=(np.arange(ow)+.5)/zoom-.5
    iy=np.floor(y).astype(int);ix=np.floor(x).astype(int)
    wy=weights(y-iy);wx=weights(x-ix)
    a=rgba.astype(np.float64)/255;premul=a.copy();premul[...,:3]*=a[...,3,None]
    result=np.zeros((oh,ow,4),np.float64)
    for row in range(4):
        for col in range(4):
            tap=premul[np.clip(iy+row-1,0,h-1)[:,None],np.clip(ix+col-1,0,w-1)[None,:]]
            result+=tap*(wy[row,:,None]*wx[col,None,:])[...,None]
    alpha=np.clip(result[...,3],0,1)
    rgb=np.clip(result[...,:3],0,alpha[...,None])/np.maximum(alpha[...,None],1e-6)
    rgb[alpha<=1e-6]=0
    return np.dstack((rgb,alpha))

def material_layers(raw,indices):
    """Extrude foreground RGB from nearest Q3m pixel; retain native shadow pixels."""
    pad=6;rgba=np.pad(raw,((pad,pad),(pad,pad),(0,0)))
    opaque=np.pad(indices>=2,pad)
    nearest=ndimage.distance_transform_edt(~opaque,return_distances=False,return_indices=True)
    extended=rgba.copy();extended[...,:3]=rgba[nearest[0],nearest[1],:3];extended[...,3]=255
    shadow=rgba.copy();shadow[~np.pad(indices==1,pad)]=0
    return extended,shadow

def sdf_alpha(field,zoom,samples=8):
    """Integrate continuous bilinear SDF sign over an 8x8 screen-pixel footprint."""
    h,w=field.shape;oh,ow=int(np.ceil(h*zoom)),int(np.ceil(w*zoom))
    coverage=np.zeros((oh,ow),np.float64)
    for sy in range(samples):
        y=(np.arange(oh)+(sy+.5)/samples)/zoom-.5
        iy=np.floor(y).astype(int);fy=y-iy
        y0=np.clip(iy,0,h-1);y1=np.clip(iy+1,0,h-1)
        for sx in range(samples):
            x=(np.arange(ow)+(sx+.5)/samples)/zoom-.5
            ix=np.floor(x).astype(int);fx=x-ix
            x0=np.clip(ix,0,w-1);x1=np.clip(ix+1,0,w-1)
            upper=field[y0[:,None],x0[None,:]]*(1-fx)+field[y0[:,None],x1[None,:]]*fx
            lower=field[y1[:,None],x0[None,:]]*(1-fx)+field[y1[:,None],x1[None,:]]*fx
            coverage+=((upper*(1-fy[:,None])+lower*fy[:,None])>0)
    return coverage/(samples*samples)

def render_reconstructed(raw,indices,field,zoom):
    extended,shadow=material_layers(raw,indices)
    colours=catmull(extended,zoom);shadow_sample=catmull(shadow,zoom)
    a=sdf_alpha(field,zoom,RECIPE['area_supersampling'])
    sa=shadow_sample[...,3]*(1-a);alpha=a+sa
    rgb=(colours[...,:3]*a[...,None]+shadow_sample[...,:3]*sa[...,None])/np.maximum(alpha[...,None],1e-6)
    rgb[alpha<=1e-6]=0
    return np.dstack((rgb,alpha))

def composite(rgba,background):
    bg=np.asarray(background,dtype=np.float64)/255
    if bg.ndim==1:bg=np.broadcast_to(bg,(*rgba.shape[:2],3))
    return np.clip(np.rint((rgba[...,:3]*rgba[...,3,None]+bg*(1-rgba[...,3,None]))*255),0,255).astype(np.uint8)
