"""Continue the approved production with isolated verification and previews."""
import ctypes
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name
state=json.loads((WORK/'process.json').read_text(encoding='utf-8-sig'))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
kernel.GetExitCodeProcess.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
handle=kernel.OpenProcess(0x1000|0x100000,False,state['pid'])
assert handle,'production process not found'
print(json.dumps(dict(stage='waiting-for-production',pid=state['pid'])),flush=True)
while kernel.WaitForSingleObject(handle,5000)==258:
    pass
exit_code=ctypes.c_ulong();assert kernel.GetExitCodeProcess(handle,ctypes.byref(exit_code))
kernel.CloseHandle(handle)
assert exit_code.value==0 and (HERE/'production.json').exists(),f'production failed: {exit_code.value}'
for script in ('verify.py','preview.py','finalize_tracking.py'):
    print(json.dumps(dict(stage='postproduction',script=script)),flush=True)
    subprocess.run([sys.executable,'-u','-B',str(HERE/script)],cwd=ROOT,check=True)
print(json.dumps(dict(stage='finished',production=True,host_verification=True,previews=True,installation=False,ingame_QA=False,release=False)),flush=True)
