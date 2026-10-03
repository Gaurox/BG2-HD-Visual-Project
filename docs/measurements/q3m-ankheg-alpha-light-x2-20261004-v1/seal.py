"""Seal new generation after verification; produce reversible installation entry points."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
old=ROOT/'docs/measurements/q3m-ankheg-spline-fit1-x2-20261003-v1'
p=load(HERE/'production.json');v=load(HERE/'verification.json');g=load(old/'current-generation.json')
assert v['V8_alpha']['passed'] and v['source_support_preserved']
assert not (HERE/'runtime.json').exists() and not (HERE/'current-generation.json').exists()
runtime=load(old/'runtime.json')
runtime['runtime_id']='iee-q3m-v8-ankheg-alpha-light-x2-20261004-v1'
runtime['source_provenance']=[v['source'],v['mask_processor'],v['leaf_writer']]
runtime['verification']=identity(HERE/'verification.json')
runtime['installation']['mask_recipe']=p['recipe']
runtime['reused_V8_runtime_compatibility_proof']=v['unchanged_runtime_compatibility_proof']
write_json(HERE/'runtime.json',runtime)
g.update(schema='bg2-ankheg-Q3m-alpha-V8-current-v1',mask_recipe=p['recipe'],
    generation_dir='sprite/.work/q3m-ankheg-alpha-light-x2-20261004-v1/combined',
    catalog=p['catalog'],production=identity(HERE/'production.json'),runtime=identity(HERE/'runtime.json'),
    host_verification=identity(HERE/'verification.json'),replaces_rejected_trial=dict(
        generation=identity(old/'current-generation.json'),
        decision=identity(ROOT/'sprite/index/qa-decisions/monster_ankheg/2026-10-04-rejected-spline-fit1-q3m-x2-catmullrom-v1.json')))
write_json(HERE/'current-generation.json',g)
for name in ('install.ps1','restore.ps1'):
    text=(old/name).read_text()
    text=text.replace('q3m-ankheg-spline-fit1-x2-20261003-v1','q3m-ankheg-alpha-light-x2-20261004-v1')
    text=text.replace('V8_spline','V8_alpha').replace('native_spline','native_alpha')
    text=text.replace('bg2-ankheg-spline','bg2-ankheg-alpha').replace('Unexpected spline scope','Unexpected alpha scope')
    text=text.replace('No active spline test','No active alpha test')
    text=text.replace('Installed Ankheg Spline Fit 1','Installed Ankheg light alpha')
    text=text.replace('sans spline restauré','sans lissage alpha restauré')
    if name=='install.ps1':
        text=text.replace('Assert-GameClosed\nAssert-Preserved',
            "if (-not $verified.source_support_preserved -or $verified.physical_pixels_cleared -ne 0) { throw 'Alpha topology verification incomplete.' }\nAssert-GameClosed\nAssert-Preserved",1)
    (HERE/name).write_text(text,encoding='utf-8')
print(json.dumps(dict(generation=g['generation_dir'],dll=g['dll']['sha256'],catalog=g['catalog']['sha256'])))
