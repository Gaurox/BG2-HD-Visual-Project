"""Complete the approved canonical production; no installation or QA decision."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
for script in ('native_validate.py','preview.py','finalize_tracking.py'):
    print(json.dumps(dict(stage='postproduction',script=script)),flush=True)
    subprocess.run([sys.executable,'-u','-B',str(HERE/script)],cwd=ROOT,check=True)
print(json.dumps(dict(stage='finished',production=True,host_verification=True,previews=True,installation=False,ingame_QA=False,release=False)),flush=True)
