import sys, io, json, numpy as np
sys.path.insert(0, r'G:/AI/BG2_Upscale/pipeline/scripts')
from bg2lib import load_key, resolve_resource
from PIL import Image
from reboutcx_quantize import srgb_u8_to_oklab
bifs,res=load_key()
def bmp(name):
    for n,t,l in res:
        if n.upper()==name and t==1:
            raw,_=resolve_resource(bifs,l); return np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'))
R=bmp('RANGES12'); M=bmp('MPALETTE'); P=bmp('MPAL256')
print('RANGES12',R.shape,'MPALETTE same:',np.array_equal(R,M),'MPAL256',P.shape)
np.save(sys.argv[1]+'/ranges12.npy',R); np.save(sys.argv[1]+'/mpal256.npy',P)
lab=srgb_u8_to_oklab(R)  # 256x12x3
L=lab[...,0]; C=np.hypot(lab[...,1],lab[...,2])
dL=np.diff(L,axis=1)
dE=np.linalg.norm(np.diff(lab,axis=1),axis=2)
mono_dark_to_light = np.all(dL<=1e-6,axis=1) | np.all(dL>=-1e-6,axis=1)
dup=(dE<0.004).sum(1)  # nearly identical consecutive shades
print('direction: first shade L mean %.3f, last shade L mean %.3f'%(L[:,0].mean(),L[:,11].mean()))
print('monotone rows', mono_dark_to_light.sum(),'/256')
print('rows with >=1 near-duplicate step', (dup>0).sum(), ' total dup steps', dup.sum())
print('median step dE %.4f  p10 %.4f p90 %.4f'%(np.median(dE),np.percentile(dE,10),np.percentile(dE,90)))
# uniformity: ratio max/min step in L
ratio=(np.abs(dL).max(1)+1e-9)/(np.abs(dL).min(1)+1e-9)
print('L-step max/min ratio median %.2f p90 %.2f'%(np.median(ratio),np.percentile(ratio,90)))
# range of L spanned
print('L span median %.3f min %.3f max %.3f'%(np.median(L[:,0]-L[:,11]),(L[:,0]-L[:,11]).min(),(L[:,0]-L[:,11]).max()))
# hue drift across ramp for chromatic rows
h=np.degrees(np.arctan2(lab[...,2],lab[...,1]))
chrom=C.mean(1)>0.04
hd=np.abs(((h[:,11]-h[:,0])+180)%360-180)
print('chromatic rows',chrom.sum(),' hue drift first->last median %.1f deg p90 %.1f'%(np.median(hd[chrom]),np.percentile(hd[chrom],90)))
# chroma curve: where is max chroma
print('argmax chroma histogram', np.bincount(C.argmax(1),minlength=12).tolist())
# per-row stats for reference rows
for r in [30,47,57,12,39,21,3,21,57,47,8,66,0,2,98,112,152,157,13,84,15,24,25,67]:
    print(r, 'L', np.round(L[r],3).tolist(), 'C', np.round(C[r],3).tolist())
json.dump({'L':L.tolist(),'C':C.tolist(),'dE':dE.tolist()},open(sys.argv[1]+'/ranges12_stats.json','w'))
