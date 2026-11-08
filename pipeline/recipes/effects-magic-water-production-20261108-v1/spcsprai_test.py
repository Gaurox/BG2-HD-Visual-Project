"""Explicit user-requested one-asset GPU test; batch pause preserved, no active tracking switch."""
import copy,json,subprocess,sys,urllib.request
from pathlib import Path
import temporal,verify,runtime_profiles,review
from temporal import ROOT,BATCH,load,save
TEST=BATCH/'alternatives/spcsprai-seedvr7b-test-20261108-v1'
def main():
 TEST.mkdir(parents=True,exist_ok=True)
 pause=BATCH/'gpu-paused.json';assert pause.exists()
 a=copy.deepcopy(next(a for a in load(BATCH/'batch.json')['assets'] if a['resref']=='SPCSPRAI'))
 a.update(spatial_run='spcsprai-seedvr7b-test-x4-20261108-v1',interpolation_run='spcsprai-seedvr7b-test-apollo30-20261108-v1',pack='effects/ressources/SPCSPRAI/packs/spcsprai-seedvr7b-test-initial-20261108-v1',final_pack='effects/ressources/SPCSPRAI/packs/spcsprai-seedvr7b-test-apollo30-profiles-20261108-v1',sigma_x4=0,inner_feather_x4=0,recipe_profile='S-DETAIL',profile='H')
 authority=ROOT/'effects/index/processing.csv';before=authority.read_bytes()
 permit=BATCH/'gpu-one-test.json';save(permit,dict(state='running',resref='SPCSPRAI',authorization='User explicitly requested SeedVR test; single-asset resumption only; keep batch paused and unload after test.'))
 try:
  run=ROOT/'effects/ressources/SPCSPRAI/runs'/a['spatial_run'];descriptor=run/'run.json'
  if not descriptor.exists() or not load(descriptor).get('result',{}).get('sealed'):
   args=[sys.executable,'-B',str(Path(__file__).with_name('spatial_one.py')),'--resref','SPCSPRAI','--workflow','pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json','--recipe-id','seedvr2-7b-int8-lab-x4-test','--run-id',a['spatial_run'],'--timeout-seconds','1800','--poll-seconds','.2','--run']
   if descriptor.exists():args.append('--resume')
   with (TEST/'spatial.log').open('a',encoding='utf-8') as log:subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  temporal.BATCH=verify.BATCH=runtime_profiles.BATCH=TEST
  # Comparison only: do not change selected xBR production or tracking columns.
  temporal.workflow.register_run=lambda *args,**kwargs:dict(comparison_only=True,registered=False)
  temporal.produce(a);verify.verify(a);r=runtime_profiles.build(a)
  out=BATCH/'review/alternatives/spcsprai-seedvr7b-test';review.OUT=out
  for folder in ['data','native','images']:(out/folder).mkdir(parents=True,exist_ok=True)
  c=review.card(a);c.update(method='Test SeedVR7B/LAB x4 · Apollo30',nativeOnly=False,profile='S-DETAIL')
  prefix='alternatives/spcsprai-seedvr7b-test/';c['native']['image']=prefix+c['native']['image']
  for f in c['frames']:
   for k in ['image','neutral']:
    if k in f:f[k]=prefix+f[k]
  assert authority.read_bytes()==before
  save(TEST/'result.json',dict(asset=a,result=r,card=c,active_tracking_unchanged=True,qa='pending-user-choice',installed=False));print('SPCSPRAI SeedVR test complete; baseline xBR retained.',flush=True)
 finally:
  save(permit,dict(state='closed',resref='SPCSPRAI',global_gpu_pause_retained=True))
  request=urllib.request.Request('http://127.0.0.1:8188/free',data=json.dumps(dict(unload_models=True,free_memory=True)).encode(),headers={'Content-Type':'application/json'},method='POST')
  with urllib.request.urlopen(request,timeout=15) as response:print('GPU models unloaded; batch pause remains active.',flush=True)
if __name__=='__main__':main()
