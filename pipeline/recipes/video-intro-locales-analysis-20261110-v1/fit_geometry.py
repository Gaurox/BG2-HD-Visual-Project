"""Fit a constant spatial transform on the shared film, excluding title cards."""
import csv
import numpy as np
from scipy.ndimage import map_coordinates, affine_transform
from scipy.optimize import least_squares
from compare import OUT, read, compare, save


def main():
    base=read('INTRO15F-default');other=read('INTRO15F-pl_PL')
    rows=list(csv.DictReader((OUT/'INTRO15F-pl_PL-normalized-to-default.csv').open()))
    eligible=[r for r in rows if 25<float(r['locale_pts_s'])<165]
    chosen=[eligible[i] for i in np.linspace(0,len(eligible)-1,24).astype(int)]
    pairs=[(base['frames'][int(r['default_frame'])].astype(float),other['frames'][int(r['locale_frame'])].astype(float)) for r in chosen]
    y,x=np.mgrid[2:88:2,2:158:2]
    def residual(p):
        sx,sy,tx,ty,gain,bias=p
        coords=np.array([(y-ty)/sy,(x-tx)/sx])
        return np.concatenate([(map_coordinates(a,coords,order=1,mode='nearest')*gain+bias-b[2:88:2,2:158:2]).ravel() for a,b in pairs])
    initial=[4/3,4/3,-80/3,-15,1,0]
    fit=least_squares(residual,initial,bounds=([1.2,1.2,-45,-30,.8,-15],[1.5,1.6,-10,0,1.2,15]),loss='soft_l1',f_scale=3,max_nfev=60)
    sx,sy,tx,ty,gain,bias=fit.x
    initial_mae=float(np.mean(np.abs(residual(initial))));fitted_mae=float(np.mean(np.abs(residual(fit.x))))
    native=base['frames']
    base['frames']=np.stack([np.clip(affine_transform(f.astype(float),np.diag([1/sy,1/sx]),offset=[-ty/sy,-tx/sx],
        output_shape=(90,160),order=1,mode='nearest',prefilter=False)*gain+bias,0,255).astype('uint8') for f in native])
    result=compare('INTRO15F-default-spatial-fit','INTRO15F-pl_PL-fitted',base,other)
    result.update(fit_parameters=dict(scale_x=sx,scale_y=sy,offset_x_pixels_160=tx,offset_y_pixels_90=ty,luma_gain=gain,luma_bias=bias),
        fit_sample_frames=24,initial_sample_mae=initial_mae,fitted_sample_mae=fitted_mae,
        note='Registration estimate from 160x90 luma, not a final rendering recipe or exact pixel identity.')
    save('INTRO15F-pl_PL-fitted-geometry-analysis.json',result)
    print(result,flush=True)


if __name__=='__main__':main()
