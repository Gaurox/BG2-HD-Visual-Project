"""Read-only selection and compatible cache accounting; never produce/install."""
import csv, hashlib, importlib.metadata, json, sqlite3, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not (HERE/'analysis.json').exists()
with (ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig',newline='') as stream:
    items=[r for r in csv.DictReader(stream) if r['engine_family']=='character_old']
selection=dict(schema='bg2-q3m-family-witness-selection-v1',scale=2,
    colour='four partners; eight blend levels; K6; V7',
    scope='proposal only: complete available native character_old; all frames/cycles/directions; no SDF',
    source_absent_animation_ids=[r['animation_id'] for r in items if not r['bam_resrefs']],
    witnesses=[dict(family='character_old',animation_id=r['animation_id'],name=r['ids_symbol'],owner=6,
        native_kind=int(r['false_color']),refs=r['bam_resrefs'].split(';')) for r in items if r['bam_resrefs']])
write_json(HERE/'selection.json',selection)
resources,works,summary=source_plan(HERE/'selection.json','character_old')
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
backend=load(cache/'backend.json')
assert file_sha(get_path('reboutcx_model',required=True))==backend['model_sha256']
for name,version in backend['dependencies'].items():
    assert importlib.metadata.version(name)==version
for name,digest in backend['kernels'].items():
    assert file_sha(ROOT/'pipeline/scripts'/name)==digest
encoded=cache/'encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
hits=[]
for key,work in works.items():
    p=encoded/(key+'.npz')
    if not p.exists(): continue
    with np.load(p,allow_pickle=False) as arrays:
        assert arrays['I'].shape==(work['frame'].height*2,work['frame'].width*2)
        work['profile'].validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep'])
    hits.append(dict(key=key,path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p)))
pointer=load(ROOT/'sprite/index/q3m-source-work-plan.json')
db=sqlite3.connect('file:'+str(ROOT/pointer['path']).replace('\\','/')+'?mode=ro',uri=True)
refs=sorted({r['resref'] for r in resources}); marks=','.join('?' for _ in refs)
whole=list(db.execute(f'SELECT canonical_sha256,group_concat(resref),count(*) FROM resources WHERE resref IN ({marks}) GROUP BY canonical_sha256 HAVING count(*)>1',refs))
duplicates=list(db.execute(f'SELECT group_concat(r.resref || ":" || f.frame_index),count(*) FROM frames f JOIN resources r USING(resource_id) WHERE r.resref IN ({marks}) GROUP BY f.work_id HAVING count(*)>1',refs))
db.close()
analysis=dict(role='proposal-not-production-QA-installation-or-release',family='character_old',scale=2,SDF=False,
    summary=summary,available_animation_ids=len(selection['witnesses']),defined_animation_ids=len(items),
    absent=[dict(animation_id=r['animation_id'],symbol=r['ids_symbol'],resref=r['body_resref']) for r in items if not r['bam_resrefs']],
    unique_models=len({tuple(w['refs']) for w in selection['witnesses']}),distinct_source_bams=len(refs),physical_frames_distinct_bams=sum(next(r for r in resources if r['resref']==ref)['frames'].__len__() for ref in refs),whole_BAM_duplicates=whole,duplicate_frame_groups=duplicates,
    physical_repetitions=summary['physical_frames']-summary['unique_source_work'],
    compatible_encoded_cache_hits=len(hits),new_encoded_work=len(works)-len(hits),
    cache_hit_files=hits,cache_backend_verified=True,production_started=False,installed=False,release=False)
write_json(HERE/'analysis.json',analysis)
print(json.dumps(dict(physical=summary['physical_frames'],source_unique=summary['unique_source_work'],
    encoded_unique=len(works),hits=len(hits),new_work=len(works)-len(hits),whole_BAM_duplicates=whole,
    duplicate_frame_groups=duplicates,absent=analysis['absent'],witnesses=summary['witnesses'])))
