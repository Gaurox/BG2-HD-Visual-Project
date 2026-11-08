"""Sequential resumable SeedVR worker; existing sealed outputs retained."""
import json,subprocess,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
def main():
 if (BATCH/'gpu-paused.json').exists():raise SystemExit('GPU paused by user; wait for explicit resume signal.')
 data=json.loads((BATCH/'batch.json').read_text(encoding='utf-8'));p=BATCH/('retry-spatial-progress.json' if '--retry' in sys.argv else 'blob-spatial-progress.json' if '--blobs' in sys.argv else 'spatial-progress.json')
 progress=json.loads(p.read_text()) if p.exists() else {}
 for a in data['assets']:
  if (BATCH/'gpu-paused.json').exists():raise SystemExit('GPU paused by user; no new spatial job.')
  if '--retry' in sys.argv and a['resref'] not in {'WHIRLY','HIHEDGE','SPBASEWT'}:continue
  if '--blobs' in sys.argv:
   if a['recipe_profile']!='A-BLOB':continue
  elif not a['recipe_profile'].startswith('S-'):continue
  n=a['resref'];run=ROOT/'effects/ressources'/n/'runs'/a['spatial_run'];d=run/'run.json'
  if d.exists() and json.loads(d.read_text()).get('result',{}).get('sealed'):continue
  progress[n]={'state':'running'};w.atomic_write(p,w.json_bytes(progress));print('SeedVR',n,flush=True)
  args=[sys.executable,'-B',str(HERE/'spatial_one.py'),'--resref',n,'--workflow','pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json','--recipe-id','seedvr2-7b-int8-lab-x4','--run-id',a['spatial_run'],'--timeout-seconds','1800','--poll-seconds','0.2','--server','http://127.0.0.1:8188','--run','--register']
  if d.exists():args.append('--resume')
  log=BATCH/'logs'/(n+'-spatial.log');log.parent.mkdir(exist_ok=True)
  try:
   with log.open('a',encoding='utf-8') as f:subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
   progress[n]={'state':'completed'}
  except Exception as exc:progress[n]={'state':'failed','error':str(exc)};print(n,repr(exc),flush=True)
  w.atomic_write(p,w.json_bytes(progress))
 print('SeedVR worker complete',flush=True)
if __name__=='__main__':main()
