"""Wait for durable production, then prepare/verify/preview the authorized full lot."""
import json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
for name in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):os.environ[name]='1'
os.environ['PYTHONPATH']=str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1')
while not (HERE/'production.json').exists():
    log=(HERE/'production-parallel.log').read_text(encoding='utf-8',errors='replace')
    if 'Traceback (most recent call last)' in log:raise RuntimeError(log[-4000:])
    time.sleep(30)
for step in ('prepare.py','verify.py','preview.py'):
    print(json.dumps(dict(stage=step,started=True)),flush=True)
    with (HERE/(step+'.log')).open('w',encoding='utf-8') as stream:
        subprocess.run([sys.executable,'-u',str(HERE/step)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
    print(json.dumps(dict(stage=step,complete=True)),flush=True)
print('Assets complete, all native checks passed, previews ready for inspection; installation next.',flush=True)
