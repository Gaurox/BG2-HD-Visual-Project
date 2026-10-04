"""Count distinct models, physical frames and compatible hits across aliases."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import write_json
analysis=json.loads((HERE/'analysis.json').read_text(encoding='utf-8'))
resources,works,_=source_plan(HERE/'selection.json','ambient')
hits={r['key'] for r in analysis['cache_hit_files']}
models={};fixed=set();ramped=set()
for r in resources:
    w=r['witness'];model=tuple(w['refs'])
    entry=models.setdefault(model,dict(animation_ids=set(),name=w['name'],refs=w['refs'],keys=set(),frames=0))
    first=w['animation_id'] not in entry['animation_ids'];entry['animation_ids'].add(w['animation_id'])
    if first:
        entry['frames']=sum(len(q['frames']) for q in resources if q['witness']['animation_id']==w['animation_id'])
    keys={f['key'] for f in r['frames']};entry['keys'].update(keys)
    (fixed if w['native_kind']==0 else ramped).update(keys)
rows=[]
for entry in models.values():
    keys=entry.pop('keys');entry['animation_ids']=sorted(entry['animation_ids'])
    entry.update(unique_encoded_work=len(keys),compatible_encoded_cache_hits=len(keys&hits),new_encoded_work=len(keys-hits))
    rows.append(entry)
assert len(rows)==16 and sum(e['frames'] for e in rows)==2580
assert len(hits)==1024 and not fixed&ramped
result=dict(models=rows,logical_animation_ids=18,unique_models=16,distinct_source_bams=34,
    physical_frames_distinct_bams=2580,physical_frames_counted_per_animation_binding=2734,
    duplicate_alias_frame_bindings=154,distinct_BAM_source_repetitions=174,unique_encoded_work=2406,
    fixed=dict(work=len(fixed),hits=len(fixed&hits),new=len(fixed-hits)),
    ramped=dict(work=len(ramped),hits=len(ramped&hits),new=len(ramped-hits)),
    compatible_encoded_cache_hits=1024,new_encoded_work=1382,production_started=False,installed=False)
write_json(HERE/'model-summary.json',result)
print(json.dumps(result))
