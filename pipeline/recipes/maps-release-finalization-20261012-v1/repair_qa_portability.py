"""Pin exact LF Git blobs beside exact CRLF historical proof files; no QA rewriting."""
import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
target=HERE/'selection-manifest-v3.json';assert not target.exists()
d=json.loads((HERE/'selection-manifest-v2.json').read_text(encoding='utf-8'))
paths=json.loads((HERE/'qa-git-portability.json').read_text())['different_from_git_blob'];fixed={}
for path in paths:
    physical=(ROOT/path).read_bytes();blob=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
    assert physical.replace(b'\r\n',b'\n')==blob
    fixed[path]=hashlib.sha256(blob).hexdigest().upper()
for v in d['variants']:
    for e in v['qa_evidence']:
        if e['path'] in fixed:e['git_blob_sha256']=fixed[e['path']]
target.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copyfile(target,ROOT/'releases/BG2-HD-Upscale/manifests/map-release-assemblies.json')
(HERE/'qa-portability-repair-v3.json').write_text(json.dumps({'reason':'Two existing historical proof files differ from Git only by CRLF/LF; pin both exact encodings. Assets and acquired decisions unchanged.','git_blob_sha256':fixed,'manifest':target.relative_to(ROOT).as_posix(),'manifest_sha256':hashlib.sha256(target.read_bytes()).hexdigest().upper()},indent=2)+'\n',encoding='utf-8')
print('QA BYTE PORTABILITY PINNED:',len(fixed))
