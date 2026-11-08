"""Requested xBR06 + native-alpha34; CPU interpolation only, global GPU pause untouched."""
import copy,sys,subprocess,re,os
from pathlib import Path
import numpy as np
from PIL import Image
import temporal,verify,runtime_profiles,review,local_spatial
from temporal import ROOT,BATCH,load,save,workflow
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam,fill_transparent
OUT=BATCH/'review-feedback-0634-20261108-v1'
def native_spatial(a):
 sp=local_spatial.sp
 original=sp.export_frames
 def export(p,source,resume):
  m=original(p,source,resume)
  if m.get('native_palette_mask'):return m
  raw=read_bam(p.source);fs,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr);cw,ch=m['aligned_canvas_size']
  for f,(idx,*_) in zip(m['frames'],fs):
   canvas=np.zeros((ch,cw,4),np.uint8);x,y=f['canvas_offset'];h,w=idx.shape;canvas[y:y+h,x:x+w,:3]=pal[idx];canvas[y:y+h,x:x+w,3]=alpha[idx];canvas[canvas[:,:,3]==0]=0
   for kind,arr in [('rgba',canvas),('rgb',fill_transparent(canvas[:,:,:3],canvas[:,:,3])),('alpha',canvas[:,:,3])]:
    target=p.frame_root/kind/f['file'];Image.fromarray(arr).save(target);f[kind+'_sha256']=workflow.sha256_file(target)
  m.update(alpha_policy='native-palette',native_palette_mask=True);sp.write_json(p.frame_root/'manifest.json',m);return m
 # Reuse the deterministic4x writer with exact source alpha; all RGB here are black.
 sp.export_frames=export
 try:local_spatial.produce(a)
 finally:sp.export_frames=original
 p=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run'];m=load(p/'01-spatial-x4/manifest.json');m['parameters']['model']='NATIVE/palette-alpha-nearest4';m['alpha_policy']='Native palette alpha nearest4, black sourceRGB unchanged; no inference';save(p/'01-spatial-x4/manifest.json',m)
 d=load(p/'run.json')
 for evidence in d['outputs']:
  if evidence['role']=='spatial-manifest':evidence.update(sha256=workflow.sha256_file(p/'01-spatial-x4/manifest.json'),bytes=(p/'01-spatial-x4/manifest.json').stat().st_size)
 # Unaccepted working writer initially sealed xBR on flat RGB; new source-label
 # accurately records the equivalent native nearest4 operation, no image changes.
 save(p/'run.json',d)
def cpu_apollo(plan,v,images):
 folder=plan.interpolation_root/v['id'];folder.mkdir(parents=True,exist_ok=True);samples=[s for s in v['apollo_samples'] if s is not None]
 if not samples:return None
 if plan.resref=='SPSDRAE2':
  p=folder/'black-source.png';Image.fromarray(images[v['keyframes'][0]][:,:,:3]).save(p);return [p]*(max(samples)+1)
 inputs=folder/'cpu-input';outputs=folder/'cpu-flow';inputs.mkdir(exist_ok=True);outputs.mkdir(exist_ok=True);slots=v['native_slots']
 extra=slots[:3] if v['loop_closed'] else [slots[-1]]*3;extended=[slots[0]]*2+slots+extra
 for i,k in enumerate(extended):Image.fromarray(images[k][:,:,:3]).save(inputs/f'in_{i:04d}.png')
 cmd=[str(plan.tvai_ffmpeg),'-hide_banner','-loglevel','info','-y','-threads','4','-framerate','15','-i',str(inputs/'in_%04d.png'),'-vf','format=yuv444p,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,showinfo','-vsync','0','-pix_fmt','rgb24',str(outputs/'out_%04d.png')]
 log=folder/'cpu-motion.log'
 if not (folder/'cpu-complete.json').exists():
  with log.open('w',encoding='utf-8') as stream:subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
  save(folder/'cpu-complete.json',dict(model='ffmpeg-minterpolate-mci',gpu_used=False,command=cmd,clock='Native slots plus2 leading/3 trailing context frames, midpoint sampled at4+nativePhase'))
 pts=[float(x) for x in re.findall(r'\bn:\s*\d+.*?pts_time:([\d.\-]+)',log.read_text(encoding='utf-8'))];files=sorted(outputs.glob('out_*.png'));assert len(pts)==len(files),(len(pts),len(files));bytime={round(t*30):p for t,p in zip(pts,files)};result=[files[0]]*(max(samples)+1)
 for phase,sample in enumerate(v['apollo_samples']):
  if sample is not None:assert 4+phase in bytime,(phase,sorted(bytime));result[sample]=bytime[4+phase]
 return result
def main():
 OUT.mkdir(exist_ok=True);assert (BATCH/'gpu-paused.json').exists();batch=load(BATCH/'batch.json');native={a['resref']:a for a in batch['native_masks']};jobs=[]
 a=copy.deepcopy(next(a for a in batch['assets'] if a['resref']=='SPARMOR2'));a.update(spatial_run='sparmor2-xbr4x-20261108-v1',interpolation_run='sparmor2-xbr4x-cpu-flow30-20261108-v1',pack='effects/ressources/SPARMOR2/packs/sparmor2-xbr4x-cpu-initial-20261108-v1',final_pack='effects/ressources/SPARMOR2/packs/sparmor2-xbr4x-cpu-flow30-profiles-20261108-v1',sigma_x4=0,inner_feather_x4=0,profile='N',recipe_profile='X-STRUCT',temporal_model='CPU/ffmpeg-minterpolate-mci',temporal_recipe_id='cpu-motion-compensated-native-clock');jobs.append(a)
 a=copy.deepcopy(native['SPSDRAE2']);a.update(native_fps=[],spatial_run='spsdrae2-native-palette-alpha-x4-20261108-v1',interpolation_run='spsdrae2-native-alpha-cpu30-20261108-v1',pack='effects/ressources/SPSDRAE2/packs/spsdrae2-native-alpha-cpu-initial-20261108-v1',final_pack='effects/ressources/SPSDRAE2/packs/spsdrae2-native-alpha-cpu30-profiles-20261108-v1',sigma_x4=0,inner_feather_x4=0,profile='N',recipe_profile='NATIVE-MASK',green_index=None,temporal_model='CPU/native-alpha-linear30',temporal_recipe_id='cpu-native-mask-alpha-clock',mask_alpha_authoritative=True);jobs.append(a)
 temporal.BATCH=verify.BATCH=runtime_profiles.BATCH=OUT;temporal.apollo=cpu_apollo;results=[]
 for a in jobs:
  receipt=OUT/(a['resref']+'-result.json')
  if receipt.exists():results.append(load(receipt));continue
  if a['resref']=='SPSDRAE2':native_spatial(a)
  else:local_spatial.produce(a)
  temporal.produce(a);verify.verify(a);r=runtime_profiles.build(a);review.OUT=BATCH/'review/alternatives/feedback-cpu-0634'/a['resref']
  for f in ['data','native','images']:(review.OUT/f).mkdir(parents=True,exist_ok=True)
  c=review.card(a);c.update(method='xBR4X · mouvement CPU30' if a['resref']=='SPARMOR2' else 'Masque natif RGBA · alpha CPU30 · sans IA',nativeOnly=False,profile=a['recipe_profile']);prefix='alternatives/feedback-cpu-0634/'+a['resref']+'/'
  c['native']['image']=prefix+c['native']['image']
  for f in c['frames']:
   for k in ['image','neutral']:
    if k in f:f[k]=prefix+f[k]
  result=dict(asset=a,result=r,card=c,gpu_used=False,qa='pending-user-retest');save(receipt,result);results.append(result)
 save(OUT/'production.json',dict(assets=results,gpu_used=False));print('06 xBR CPU30 and34 native-alpha RGBA CPU30 ready.',flush=True)
if __name__=='__main__':main()
