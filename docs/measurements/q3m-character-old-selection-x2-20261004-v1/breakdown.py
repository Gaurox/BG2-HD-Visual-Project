"""Read-only native model/alias/cache/placeholder accounting; no production or install."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
analysis=load(HERE/'analysis.json');selection=load(HERE/'selection.json')
resources,works,summary=source_plan(HERE/'selection.json','character_old')
hits={r['key'] for r in analysis['cache_hit_files']};models={};physical={};blank_resources=[]
for r in resources:
    w=r['witness'];model=tuple(w['refs'])
    entry=models.setdefault(model,dict(animation_ids=set(),name=w['name'],native_kind=w['native_kind'],refs=w['refs'],keys=set(),frames=0,blank_frames=0))
    entry['animation_ids'].add(w['animation_id']);entry['keys'].update(f['key'] for f in r['frames'])
    if r['resref'] in physical:continue
    physical[r['resref']]=r
    blank=sum(not np.any(works[f['key']]['frame'].indices) for f in r['frames'])
    entry['frames']+=len(r['frames']);entry['blank_frames']+=blank
    if blank==len(r['frames']):blank_resources.append(dict(resref=r['resref'],frames=blank,source_sha256=r['source_sha256']))
rows=[]
for entry in models.values():
    keys=entry.pop('keys');entry['animation_ids']=sorted(entry['animation_ids'])
    entry.update(unique_encoded_work=len(keys),compatible_encoded_cache_hits=len(keys&hits),new_encoded_work=len(keys-hits))
    rows.append(entry)
assert len(rows)==6 and len(physical)==99 and sum(e['frames'] for e in rows)==4725
assert len(works)==3771 and len(hits)==288
transparent_keys={k for k,w in works.items() if not np.any(w['frame'].indices)}
assert len(transparent_keys)==41 and not transparent_keys&hits
result=dict(models=rows,logical_animation_ids=7,unique_models=6,distinct_source_bams=99,
    physical_frames_distinct_bams=4725,physical_frames_counted_per_animation_binding=5661,logical_resource_bindings=121,
    duplicate_alias_frame_bindings=936,distinct_BAM_source_repetitions=954,whole_BAM_duplicate_groups=analysis['whole_BAM_duplicates'],
    fully_transparent_native_resources=blank_resources,fully_transparent_unique_work=41,
    visible_body_models=5,unique_encoded_work=3771,compatible_encoded_cache_hits=288,new_encoded_work=3483,
    source_absent=analysis['absent'],production_started=False,installed=False,release=False)
write_json(HERE/'model-summary.json',result)
print(json.dumps(dict(models=[{k:v for k,v in r.items() if k!='refs'} for r in rows],physical=4725,unique=3771,hits=288,new=3483,blank_resources=len(blank_resources))))
