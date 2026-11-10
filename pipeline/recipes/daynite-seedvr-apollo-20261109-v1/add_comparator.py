from pathlib import Path
import json
import hashlib

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/daynite/runs/daynite-seedvr-apollo-20261109-v1'
report=json.loads((RUN/'production.json').read_text())
assert report['state']=='verified-comparison-ready'
for path in report['outputs'].values():assert (ROOT/path).is_file()
report['sha256']={key:hashlib.sha256((ROOT/path).read_bytes()).hexdigest()for key,path in report['outputs'].items()}
(RUN/'production.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
p=ROOT/'video/tools/comparator.html';s=p.read_text(encoding='utf-8')
assert '// DAYNITE current comparison' not in s
block="""// DAYNITE current comparison; previously accepted movies remain selectable.
sourceItems.unshift({name:'DAYNITE — source originale · 720p15',url:'../daynite/source-preview-720p15.mp4',fps:15});
resultItems.unshift(
 {name:'DAYNITE — SeedVR2 + Apollo 8 · Full HD 30 fps',url:'../daynite/runs/daynite-seedvr-apollo-20261109-v1/DAYNITE-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4',fps:30},
 {name:'DAYNITE — SeedVR2 3B FP16 LAB · Full HD 15 fps',url:'../daynite/runs/daynite-seedvr-apollo-20261109-v1/DAYNITE-SeedVR2-3B-FP16-LAB-1080p15.mp4',fps:15});
"""
anchor='sourceItems.push(...resultItems.map';assert anchor in s;s=s.replace(anchor,block+anchor,1);p.write_text(s,encoding='utf-8')
print('DAYNITE source,15fps and30fps added; no game installation.')
