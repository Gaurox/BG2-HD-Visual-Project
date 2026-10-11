"""Confirm staged raw evidence survives Git attributes byte for byte."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[3]
files=subprocess.check_output(['git','diff','--cached','--name-only','--diff-filter=AM','-z'],cwd=ROOT).decode().split('\0')
files=[p for p in files if p]
attrs=subprocess.check_output(['git','check-attr','-z','text','--stdin'],input=('\0'.join(files)+'\0').encode(),cwd=ROOT).decode().split('\0')
raw=[attrs[i] for i in range(0,len(attrs)-1,3) if attrs[i+2]=='unset']
process=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,cwd=ROOT)
for path in raw:
    process.stdin.write((':'+path+'\n').encode());process.stdin.flush()
    header=process.stdout.readline().decode().split();assert len(header)==3,header
    remaining=int(header[2]);digest=hashlib.sha256()
    while remaining:
        chunk=process.stdout.read(min(1024*1024,remaining));assert chunk
        remaining-=len(chunk);digest.update(chunk)
    assert process.stdout.read(1)==b'\n'
    assert digest.digest()==hashlib.sha256((ROOT/path).read_bytes()).digest(),path
process.stdin.close();assert process.wait()==0
print('GIT_RAW_EVIDENCE=PASSED',len(raw))
