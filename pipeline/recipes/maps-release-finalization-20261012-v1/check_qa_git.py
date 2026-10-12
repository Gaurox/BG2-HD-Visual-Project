"""Read-only proof portability check against committed evidence bytes."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
data=json.loads((ROOT/'releases/BG2-HD-Upscale/manifests/map-release-assemblies.json').read_text())
evidence={e['path']:e['sha256'] for v in data['variants'] for e in v['qa_evidence']}
process=subprocess.run(['git','cat-file','--batch'],cwd=ROOT,input=''.join('HEAD:'+n+'\n' for n in evidence).encode(),stdout=subprocess.PIPE,check=True)
raw=process.stdout;offset=0;different=[];missing=[]
for name,sha in evidence.items():
    end=raw.index(b'\n',offset);header=raw[offset:end].split();offset=end+1
    if header[-1]==b'missing':missing.append(name);continue
    size=int(header[-1]);blob=raw[offset:offset+size];offset+=size+1
    if hashlib.sha256(blob).hexdigest().upper()!=sha:different.append(name)
result={'proofs':len(evidence),'different_from_git_blob':different,'not_committed':missing}
(HERE/'qa-git-portability.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
