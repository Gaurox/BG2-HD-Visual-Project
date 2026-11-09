"""Install only movies/restdung.wbm; verified backup, atomic replace, no release writes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stopped():
    cmd="$p=Get-Process -Name Baldur,BaldurReal,InfinityLoader -ErrorAction SilentlyContinue; if($p){$p | Select-Object Id,ProcessName | ConvertTo-Json -Compress;exit 1};exit 0"
    r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True)
    assert r.returncode==0, 'Game/InfinityLoader must be closed: '+r.stdout

game=get_path('bg2ee_game_root',required=True).resolve()
target=(game/'movies/restdung.wbm').resolve()
assert target.parent==(game/'movies').resolve() and target.name.lower()=='restdung.wbm' and target.is_file()
run=ROOT/'video/restdung/runs/restdung-seedvr-ingame-20261109-v1'
source=run/'restdung.wbm'
encoding=json.loads((run/'encoding.json').read_text())
assert sha(source)==encoding['output_sha256']
assert json.loads((run/'quality-check.json').read_text())['source_audio_exact']
stopped()
receipt_dir=ROOT/'video/installations/restdung-seedvr-20261109-v1'
receipt_dir.mkdir(exist_ok=False,parents=True)
backup=receipt_dir/'before/restdung.wbm';backup.parent.mkdir()
before=sha(target);shutil.copy2(target,backup);assert sha(backup)==before
receipt={'schema':'bg2-video-local-install-v1','asset_key':'movie:default:RESTDUNG','state':'backed-up','target':'config://bg2ee_game_root/movies/restdung.wbm','resolved_target':str(target),'backup':backup.relative_to(ROOT).as_posix(),'before_sha256':before,'source':source.relative_to(ROOT).as_posix(),'after_sha256':sha(source),'qa_ingame':'pending-user','release_integration':False}
path=receipt_dir/'installation.json'
path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
temp=target.with_name('restdung.bg2hd-seedvr-v1.wbm.tmp')
assert not temp.exists()
shutil.copy2(source,temp);assert sha(temp)==sha(source)
stopped();assert sha(target)==before,'Concurrent target change'
os.replace(temp,target)
assert sha(target)==sha(source)
receipt.update(state='installed',installed_at=datetime.now(timezone.utc).isoformat())
path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt,indent=2))
