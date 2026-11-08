"""CPU-only exact-energy alpha alternatives for SPBASEWT/SPENTAXI; no active pack mutation."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from temporal import ROOT,BATCH,load,save
OUT=BATCH/'alternatives/black-alpha-check-20261108-v1'
REVIEW=BATCH/'review'
def main():
 OUT.mkdir(parents=True,exist_ok=True);batch=load(BATCH/'batch.json');results=[]
 for name in ['SPBASEWT','SPENTAXI']:
  a=next(a for a in batch['assets'] if a['resref']==name);stage=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']/'02-interpolation';m=load(stage/'manifest.json')
  c=copy.deepcopy(load(REVIEW/'data'/f'{name}.json'));c.update(method='SeedVR7B/LAB · noir transparent progressif',nativeOnly=False,profile='ALPHA-FLUX')
  folder=REVIEW/'alternatives/black-alpha-check-20261108-v1'/name;folder.mkdir(parents=True,exist_ok=True)
  beforeblack=afterblack=changed=0;proofs=[]
  for f,row in zip(m['frames'],c['frames']):
   w,h=f['physical_size_x4'];raw=(stage/f['raw_rgba_x4']).read_bytes();p=np.frombuffer(raw,np.uint8).reshape(h,w,4)
   alpha=p[:,:,:3].max(2);assert np.all(alpha<=p[:,:,3]);straight=np.zeros_like(p);straight[:,:,3]=alpha;mask=alpha>0
   straight[:,:,:3][mask]=np.clip(np.rint(p[:,:,:3][mask].astype(float)*255/alpha[mask,None]),0,255).astype(np.uint8)
   rec=np.rint(straight[:,:,:3].astype(float)*alpha[:,:,None]/255).astype(np.uint8);err=int(np.abs(rec.astype(int)-p[:,:,:3].astype(int)).max());assert err<=1
   target=folder/f"frame_{f['frame']:04d}.png";Image.fromarray(straight).save(target,compress_level=3)
   path=target.relative_to(REVIEW).as_posix();row['image']=path;row.pop('neutral',None)
   beforeblack+=int(((p[:,:,:3].max(2)==0)&(p[:,:,3]>0)).sum());afterblack+=int(((straight[:,:,:3].max(2)==0)&(alpha>0)).sum());changed+=int((alpha!=p[:,:,3]).sum())
   proofs.append(dict(frame=f['frame'],parent_raw_sha256=hashlib.sha256(raw).hexdigest().upper(),straight_png_sha256=hashlib.sha256(target.read_bytes()).hexdigest().upper(),roundtrip_error_max=err))
  assert afterblack==0
  result=dict(resref=name,card=c,frames=len(proofs),changed_alpha_pixels=changed,exact_black_opaque_before=beforeblack,exact_black_opaque_after=afterblack,premultiplied_rgb_policy='Original P unchanged, A=max(P.r,P.g,P.b); straight RGB reconstructed, rounded reconstruction<=1. No threshold, erosion, feather or interpolation.',owner_blend='No owner found in indexed effects consumers or projectile contexts; source BAM palette does not establish native blend mode.',decision='Recommend alpha-flux variant for this luminous rendering; native-alpha witness retained; final owner routing and visual acceptance pending.',proofs=proofs,installed=False,active_production_unchanged=True)
  save(OUT/f'{name}.json',result);results.append(dict(resref=name,frames=len(proofs),changed_alpha_pixels=changed,exact_black_opaque_before=beforeblack,exact_black_opaque_after=afterblack))
 save(OUT/'result.json',dict(assets=results,source_findings=dict(SPBASEWT=dict(exact_black_source_pixels=0,nearblack_source_pixels=38043,covered_source_pixels=243509),SPENTAXI=dict(exact_black_source_pixels=0,nearblack_source_pixels=5324,covered_source_pixels=134881))))
 print(json.dumps(results))
if __name__=='__main__':main()
