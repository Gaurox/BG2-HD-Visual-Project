"""Complete verification/previews/tracking after the isolated production succeeds."""
import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
while not(HERE/'production.json').exists():time.sleep(5)
for script,proof in [('verify.py','verification.json'),('verify_runtime.py','runtime-verification.json'),('preview.py','previews.json')]:
    if(HERE/proof).exists():continue
    print(json.dumps(dict(stage='postproduction',script=script)),flush=True)
    subprocess.run([sys.executable,'-u','-B',str(HERE/script)],cwd=ROOT,check=True)
print(json.dumps(dict(stage='postproduction',script='finalize.py')),flush=True)
subprocess.run([sys.executable,'-u','-B',str(HERE/'finalize.py')],cwd=ROOT,check=True)
print(json.dumps(dict(stage='finished',production=True,DLL_candidate=True,host_verification=True,previews=True,installation=False,ingame_QA=False,release=False)),flush=True)
