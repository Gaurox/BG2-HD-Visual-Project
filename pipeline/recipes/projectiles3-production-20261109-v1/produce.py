"""Sequential, resumable production of the three authorized projectile BAMs."""
from pathlib import Path
import json,sys,subprocess,urllib.request
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
BATCH=ROOT/'effects/batches/projectiles3-production-20261109-v1'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def api(path,data=None):
 req=urllib.request.Request('http://127.0.0.1:8188/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=30) as f:
  body=f.read();return json.loads(body) if body else {}
def main():
 batch=load(BATCH/'batch.json');assert {a['resref'] for a in batch['assets']}=={'BGLRYU','SPCL236U','SPGLYPHI'}
 q=api('queue');assert not q['queue_running'] and not q['queue_pending'],'Comfy queue occupied; no competing asset worker launched'
 for a in batch['assets']:
  d=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'run.json'
  if d.exists() and load(d).get('result',{}).get('sealed'):continue
  cmd=[sys.executable,'-B','pipeline/scripts/run_effect_spatial.py','--resref',a['resref'],'--workflow','pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json','--recipe-id','seedvr2-7b-int8-lab-x4','--run-id',a['spatial_run'],'--timeout-seconds','1800','--poll-seconds','0.5','--server','http://127.0.0.1:8188','--run','--register']
  if d.exists():cmd.append('--resume')
  print('Spatial',a['resref'],flush=True);subprocess.run(cmd,cwd=ROOT,check=True)
 q=api('queue')
 if not q['queue_running'] and not q['queue_pending']:api('free',{'unload_models':True,'free_memory':True})
 import temporal,verify,runtime_profiles,review
 for a in batch['assets']:
  print('Temporal',a['resref'],flush=True);temporal.produce(a)
  verify.verify(a);runtime_profiles.build(a)
 print('Review cards',review.build(),flush=True)
 print('Three productions complete; visual QA pending.',flush=True)
if __name__=='__main__':main()
