"""CPU-only WHIRLY repair: enclosed key green + palette-derived matte + local despill."""
import copy,sys,shutil,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import temporal,runtime_profiles,review
from temporal import ROOT,BATCH,load,save,rel,workflow
from bam_export import decode_bam
from export_bam_frames import read_bam
OUT=BATCH/'review-feedback-20261108-v1'
def main():
 full='--full-despill' in sys.argv;version='v2' if full else 'v1'
 OUT.mkdir(exist_ok=True);receipt=OUT/('whirly-correction-v2.json' if full else 'whirly-correction.json')
 if receipt.exists():print('WHIRLY repair retained');return
 a=copy.deepcopy(next(a for a in load(BATCH/'batch.json')['assets'] if a['resref']=='WHIRLY'));oldrun=ROOT/'effects/ressources/WHIRLY/runs'/a['interpolation_run'];old=load(oldrun/'02-interpolation/manifest.json');sp=load(ROOT/old['parent']['spatial_manifest']);cw,ch=sp['aligned_canvas_size_x1'];anchor=[sp['frames'][0]['canvas_offset_x1'][i]+sp['frames'][0]['centre_x1'][i] for i in range(2)]
 raw=read_bam(ROOT/a['source']);fs,pal,tr=decode_bam(raw);masks=[];bands=[];key_pixels=0;fringe_pixels=0
 for f,s in zip(fs,sp['frames']):
  idx=f[0];rgb=pal[idx].astype(float);spill=np.maximum(rgb[:,:,1]-np.maximum(rgb[:,:,0],rgb[:,:,2]),0);alpha=255-spill;alpha[idx==tr]=0
  key=idx==178;alpha[key]=0;key_pixels+=int(key.sum());fringe_pixels+=int(((spill>0)&~key).sum())
  # The palette contains green-screen mixtures at the silhouette too. Despill is
  # limited to a1.5px native band around green, rather than recoloring the asset.
  band=(ndi.distance_transform_edt(~key)<=1.5)|(spill>0)
  canvas=np.zeros((ch,cw),np.uint8);halo=np.zeros((ch,cw),bool);x,y=s['canvas_offset_x1'];h,w=idx.shape
  canvas[y:y+h,x:x+w]=np.rint(alpha).astype(np.uint8);halo[y:y+h,x:x+w]=band
  masks.append(canvas.repeat(4,0).repeat(4,1));bands.append(halo.repeat(4,0).repeat(4,1))
 newid='whirly-green-clean-cpu-apollo30-20261108-'+version;a.update(interpolation_run=newid,pack='effects/ressources/WHIRLY/packs/whirly-green-clean-initial-20261108-'+version,final_pack='effects/ressources/WHIRLY/packs/whirly-green-clean-profiles-20261108-'+version)
 run=oldrun.parent/newid;workflow.new_run(ROOT,'WHIRLY','interpolation','source-palette-green-clean-cpu',newid,write=True);stage=run/'02-interpolation';folder=stage/'frames-rgba';folder.mkdir(parents=True,exist_ok=True)
 m=copy.deepcopy(old);changes=green_before=green_after=0
 for f in m['frames']:
  w,h=f['physical_size_x4'];arr=np.frombuffer((oldrun/'02-interpolation'/f['straight_raw_rgba_x4']).read_bytes(),np.uint8).reshape(h,w,4).copy();left,right=f['temporal_source_frames'];t=f['temporal_fraction'];x,y=[(anchor[i]-f['centre_x1'][i])*4 for i in range(2)]
  mask=np.rint(masks[left].astype(float)*(1-t)+masks[right].astype(float)*t).astype(np.uint8)[y:y+h,x:x+w];band=(bands[left]|bands[right])[y:y+h,x:x+w]
  newalpha=np.minimum(arr[:,:,3],mask);changes+=int((newalpha!=arr[:,:,3]).sum());covered=newalpha>0
  green_before+=int(((arr[:,:,1].astype(int)>np.maximum(arr[:,:,0],arr[:,:,2]).astype(int)+8)&(arr[:,:,3]>0)).sum())
  green=(arr[:,:,1].astype(int)>np.maximum(arr[:,:,0],arr[:,:,2]).astype(int)+(8 if full else 0))&(np.ones(band.shape,bool) if full else band)
  arr[:,:,1][green]=np.maximum(arr[:,:,0],arr[:,:,2])[green]
  if full:newalpha[green&(np.maximum(arr[:,:,0],arr[:,:,2])==0)]=0
  arr[:,:,3]=newalpha;covered=newalpha>0;arr[~covered]=0
  green_after+=int(((arr[:,:,1].astype(int)>np.maximum(arr[:,:,0],arr[:,:,2]).astype(int)+8)&covered).sum())
  premul=arr.copy();premul[:,:,:3]=np.rint(arr[:,:,:3].astype(float)*newalpha[:,:,None]/255).astype(np.uint8);assert np.all(premul[:,:,:3]<=premul[:,:,3:4])
  stem=f"frame_{f['frame']:04d}";png=folder/(stem+'.png');rp=folder/(stem+'.rgba');straight=folder/(stem+'-straight.rgba');Image.fromarray(premul).save(png);rp.write_bytes(premul.tobytes());straight.write_bytes(arr.tobytes())
  canvas=np.zeros((ch*4,cw*4,4),np.uint8);canvas[y:y+h,x:x+w]=premul
  f.update(rgba_x4='frames-rgba/'+png.name,rgba_x4_sha256=workflow.sha256_file(png),raw_rgba_x4='frames-rgba/'+rp.name,raw_rgba_x4_sha256=workflow.sha256_file(rp),straight_raw_rgba_x4='frames-rgba/'+straight.name,straight_raw_rgba_x4_sha256=workflow.sha256_file(straight),anchored_rgba_sha256=temporal.digest(canvas.tobytes()),anchored_rgb_sha256=temporal.digest(canvas[:,:,:3].tobytes()))
  f.pop('neutral_raw_rgba_x4',None);f.pop('neutral_raw_rgba_x4_sha256',None)
 carrier=run/'runtime-carrier/WHIRLY.bam';carrier.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/old['runtime_carrier']['path'],carrier);m['runtime_carrier'].update(path=rel(carrier))
 recipe=dict(schema='bg2-upscale-effect-interpolation-recipe-v1',pipeline_id='effects.interpolation-30fps.v1',recipe_id='source-palette-green-clean-cpu',scale=4,target_fps=[30,1],policy='All exact green178 removed including enclosed holes; source green-screen mixture alpha=255-max(G-max(R,B),0); native1.5px boundary band despill G=min(G,max(R,B)); clamp to previous alpha; reuse temporal phases, no inference.',parent_interpolation_run=oldrun.name,tools=[dict(role='producer',path=rel(Path(__file__)),sha256=workflow.sha256_file(Path(__file__)))])
 if full:recipe['policy']+=' v2: residual SeedVR green dominance>8 removed throughout red/metal foreground too; green-only generated pixels made transparent. No legitimate green foreground identified in source palette.'
 save(run/'recipe.json',recipe);m['visual_treatment']=recipe;m['alpha_derivation']=dict(parent_run=oldrun.name,canonical_source_unchanged=True,green_index=178,no_gpu=True);save(stage/'manifest.json',m)
 d=load(oldrun/'run.json');d['run_id']=newid;d['pipeline'].update(version='green-clean-source-matte-cpu.v1',recipe_path=rel(run/'recipe.json'),recipe_sha256=workflow.sha256_file(run/'recipe.json'));d['outputs']=[dict(role='interpolation-manifest',path=rel(stage/'manifest.json'),sha256=workflow.sha256_file(stage/'manifest.json'),bytes=(stage/'manifest.json').stat().st_size),dict(role='runtime-bam-carrier',path=rel(carrier),sha256=workflow.sha256_file(carrier),bytes=carrier.stat().st_size)];d['provenance'].update(generator=rel(Path(__file__)),created_at_utc=workflow.utc_now());save(run/'run.json',d)
 checked=workflow.verify_run_descriptor(ROOT,run.parent.parent,'WHIRLY',newid,stage='interpolation',spatial_run=a['spatial_run']);assert checked['ok'],checked
 temporal.BATCH=OUT;runtime_profiles.BATCH=OUT;plan=temporal.make_plan(a);temporal.finish(a,plan,sp);result=runtime_profiles.build(a)
 oldout=review.OUT;review.OUT=oldout/('alternatives/feedback-green-clean-v2' if full else 'alternatives/feedback-green-clean')
 for f in ['data','native','images']:(review.OUT/f).mkdir(parents=True,exist_ok=True)
 c=review.card(a);c.update(method='SeedVR7B · détourage vert corrigé CPU · Apollo30',nativeOnly=False,profile='GREEN-CLEAN')
 prefix='alternatives/feedback-green-clean-v2/' if full else 'alternatives/feedback-green-clean/';c['native']['image']=prefix+c['native']['image']
 for f in c['frames']:
  for k in ['image','neutral']:
   if k in f:f[k]=prefix+f[k]
 save(receipt,dict(asset=a,result=result,card=c,source_key_green_pixels=key_pixels,source_green_fringe_pixels=fringe_pixels,changed_alpha_pixels=changes,covered_green_before=green_before,covered_green_after=green_after,source_geometry_and_timing_unchanged=True,gpu_used=False,qa='pending-user-review'))
 print('WHIRLY corrected CPU:',green_before,'->',green_after,'green pixels; native geometry/timing retained.',flush=True)
if __name__=='__main__':main()
