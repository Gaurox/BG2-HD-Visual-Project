"""Repair relative/absolute WED inclusion comparison; retain v1 technical selection."""
import csv,json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;R=ROOT/'releases/BG2-HD-Upscale'
p=HERE/'selection-manifest-v2.json';assert not p.exists()
d=json.loads((HERE/'selection-manifest.json').read_text(encoding='utf-8'));fixed=[]
for v in d['variants']:
    include=any(f['name'].endswith('.WED') and Path(f['source']).parent.as_posix()==v['source_path'] for f in v['files'])
    if v['include_wed']!=include:fixed.append(v['area']);v['include_wed']=include
assert len(fixed)==63
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
shutil.copyfile(p,R/'manifests/map-release-assemblies.json')
csvpath=R/'manifests/map-release-candidates.csv';rows=list(csv.DictReader(csvpath.open(encoding='utf-8-sig',newline='')))
by={v['area']:v for v in d['variants']}
for row in rows:row['include_wed']=str(by[row['area']]['include_wed']).lower()
with csvpath.open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(HERE/'selection-repair-v2.json').write_text(json.dumps({'reason':'Relative/absolute path comparison incorrectly excluded WED; source bytes and acquired QA unchanged','fixed':fixed,'manifest':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest().upper()},indent=2)+'\n',encoding='utf-8')
print('WED INCLUSION REPAIRED:',len(fixed))
