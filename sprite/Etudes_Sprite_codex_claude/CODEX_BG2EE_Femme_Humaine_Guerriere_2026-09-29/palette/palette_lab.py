"""Independent Codex offline study. Never writes game resources or production files.
Run with configured chaiNNer Python from the repository root.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from reboutcx_quantize import srgb_u8_to_oklab

OUT = Path(__file__).resolve().parent
FONT = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 19)
SMALL = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)


def linear(rgb):
    v = np.asarray(rgb, dtype=np.float64) / 255
    return np.where(v <= .04045, v / 12.92, ((v + .055) / 1.055) ** 2.4)


def encode(rgb):
    v = np.clip(rgb, 0, 1)
    return np.rint(np.where(v <= .0031308, 12.92*v, 1.055*v**(1/2.4)-.055)*255).astype(np.uint8)


def from_lab(lab):
    L,a,b = np.moveaxis(np.asarray(lab), -1, 0)
    l = (L + .3963377774*a + .2158037573*b)**3
    m = (L - .1055613458*a - .0638541728*b)**3
    s = (L - .0894841775*a - 1.291485548*b)**3
    return encode(np.stack((4.0767416621*l-3.3077115913*m+.2309699292*s,
                           -1.2684380046*l+2.6097574011*m-.3413193965*s,
                           -.0041960863*l-.7034186147*m+1.707614701*s), -1))


def even_path(ramp):
    """Diagnostic only: 12 equal arc-distance samples of the original OKLab path."""
    lab = srgb_u8_to_oklab(ramp)
    distances = np.r_[0, np.cumsum(np.linalg.norm(np.diff(lab, axis=0), axis=1))]
    if distances[-1] == 0:
        return ramp.copy()
    positions = np.linspace(0, distances[-1], 12)
    return from_lab(np.stack([np.interp(positions, distances, lab[:,c]) for c in range(3)], -1))


def palette_from_rows(ramps):
    """Neutral reconstruction, no lighting/effects. Native blend hypothesis checked separately."""
    p = np.zeros((256,3), np.uint8)
    p[0] = [0,255,0]
    p[4:88] = ramps.reshape(84,3)
    j = 88
    for a in range(6):
        for b in range(a+1,7):
            p[j:j+8] = (ramps[a,2:10].astype(np.uint16)+ramps[b,2:10])//2
            j += 8
    return p


def class_candidates(value):
    if value < 4:
        return np.array([value], np.uint8)
    if value < 88:
        lo = 4 + (int(value)-4)//12*12
        return np.arange(lo,lo+12,dtype=np.uint8)
    lo = 88 + (int(value)-88)//8*8
    return np.arange(lo,lo+8,dtype=np.uint8)


BAYER = (np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]],float)+.5)/16


def quantize_modes(target, guide, palette, anchor=(0,0), seed=17):
    """Adjacent palette-shade interpolation, class constrained, fixed geometry.
    Stores continuous palette weights separately: these are NOT BAM pixels.
    Spatial dithering uses linear RGB coverage between the selected endpoints.
    """
    h,w = guide.shape
    lab = srgb_u8_to_oklab(target)
    plab = srgb_u8_to_oklab(palette)
    tgtlin = linear(target)
    palin = linear(palette)
    loidx = guide.copy(); hiidx = guide.copy(); weight = np.zeros((h,w))
    nearest = guide.copy()
    done = set()
    for v in np.unique(guide):
        candidates = class_candidates(v)
        key = int(candidates[0])
        if key in done:
            continue
        done.add(key)
        mask = np.isin(guide,candidates)
        x = lab[mask]
        dst = np.sum((x[:,None]-plab[candidates][None])**2,-1)
        nearest[mask] = candidates[dst.argmin(1)]
        if len(candidates)==1:
            continue
        # Adjacent indices preserve the authored ramp order; no frame-wise sorting.
        a = plab[candidates[:-1]]; b = plab[candidates[1:]]; d = b-a
        t = np.clip(np.sum((x[:,None]-a[None])*d[None],-1)/(np.sum(d*d,-1)[None]+1e-12),0,1)
        projection = a[None] + t[:,:,None]*d[None]
        segment = np.sum((x[:,None]-projection)**2,-1).argmin(1)
        ii = candidates[segment]; jj = candidates[segment+1]
        # Linear-light weight for physical area coverage (not gamma-space RGB).
        dl = palin[jj]-palin[ii]
        ww = np.clip(np.sum((tgtlin[mask]-palin[ii])*dl,-1)/(np.sum(dl*dl,-1)+1e-12),0,1)
        loidx[mask]=ii; hiidx[mask]=jj; weight[mask]=ww
    yy,xx = np.indices((h,w))
    threshold = BAYER[(yy-anchor[1])%4,(xx-anchor[0])%4]
    ordered = np.where(weight>threshold,hiidx,loidx).astype(np.uint8)
    rng = np.random.default_rng(seed)
    random = np.where(weight>rng.random((h,w)),hiidx,loidx).astype(np.uint8)
    continuous = encode(palin[loidx]*(1-weight[...,None])+palin[hiidx]*weight[...,None])
    return dict(nearest=nearest,ordered=ordered,random=random,lo=loidx,hi=hiidx,weight=weight,continuous=continuous)


def main():
    ramps = np.array(Image.open(OUT/'RANGES12.bmp').convert('RGB'))
    names = {}
    for line in (OUT/'clownclr.1008').read_text().splitlines():
        bits=line.split(maxsplit=1)
        if len(bits)==2 and bits[0].isdigit(): names[int(bits[0])]=bits[1]
    rows=[]
    for i,r in enumerate(ramps):
        lab=srgb_u8_to_oklab(r); dif=np.linalg.norm(np.diff(lab,axis=0),axis=1)
        rows.append(dict(row=i,name=names.get(i,''),distinct=len(np.unique(r,axis=0)),
                         lightness_inversions=int(np.sum(np.diff(lab[:,0])>1e-6)),
                         gap_min=float(dif.min()),gap_max=float(dif.max()),gap_cv=float(dif.std()/(dif.mean()+1e-12)),
                         rgb_json=json.dumps(r.tolist())))
    with (OUT/'gradient_metrics.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader();w.writerows(rows)
    selected=[30,47,57,12,39,21,3]
    canvas=Image.new('RGB',(1200,850),(22,26,33));d=ImageDraw.Draw(canvas)
    d.text((25,16),'Codex | RANGES12 vanilla : 12 nuances, ordre clair -> sombre',font=FONT,fill='white')
    d.text((25,46),'Diagnostic : repartir les ecarts OKLab ne prouve pas une meilleure direction artistique.',font=SMALL,fill='#b7c4d5')
    results=[]
    for n,i in enumerate(selected):
        y=87+n*105
        d.text((25,y),f'{i}: {names.get(i, "")}',font=SMALL,fill='white')
        base=ramps[i];candidate=even_path(base)
        for row,data,label in [(0,base,'vanilla'),(1,candidate,'ecarts egaux')]:
            for k,col in enumerate(data):
                x=395+k*59; yy=y+row*38
                d.rectangle((x,yy,x+56,yy+32),fill=tuple(col))
            d.text((267,y+row*38+5),label,font=SMALL,fill='#cbd3dd')
        old=rows[i]
        nd=np.linalg.norm(np.diff(srgb_u8_to_oklab(candidate),axis=0),axis=1)
        results.append(dict(row=i,vanilla_gap_cv=old['gap_cv'],candidate_gap_cv=float(nd.std()/nd.mean()),
                            vanilla_max_gap=old['gap_max'],candidate_max_gap=float(nd.max())))
    d.text((25,823),'Ces BMP restent hors du jeu. Ne pas appliquer uniformement aux metaux, lignes speciales ou aleatoires.',font=SMALL,fill='#e7ba85')
    canvas.save(OUT/'gradients_comparison.png')
    np.save(OUT/'experimental_equal_arc_rows.npy',np.array([even_path(r) for r in ramps]))
    summary=dict(source='KEY/BIFF, override excluded',size=list(ramps.shape),
                 ranges12_sha256=hashlib.sha256((OUT/'RANGES12.bmp').read_bytes()).hexdigest(),
                 mpalette_pixels_equal=bool(np.array_equal(ramps,np.array(Image.open(OUT/'MPALETTE.bmp')))),
                 rows_with_nonmonotone_L=[r['row'] for r in rows if r['lightness_inversions']],
                 rows_with_duplicate_rgb=[r['row'] for r in rows if r['distinct']<12],
                 selected=results)
    (OUT/'gradient_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
