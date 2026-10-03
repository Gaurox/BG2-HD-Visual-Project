"""Complete Ogre family using the shared acquired V7 cache; no game writes."""
import builtins,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from palette_work_plan import file_sha,write_json

cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
output=ROOT/'sprite/.work/q3m-monster-large-full-x2-20261003-v1/isolated'
assert not output.exists() and not (HERE/'production.json').exists()
resources,works,plan=source_plan(HERE/'selection.json','monster_large')
assert plan['families']==1 and plan['resources']==7 and plan['physical_frames']==434
with exclusive(cache):
    stats,directory=produce(resources,works,cache)
    result=pack(resources,works,output)
    original=builtins.__import__
    def no_torch(name,*args,**kwargs):
        if name.split('.')[0]=='torch':raise RuntimeError('Torch imported by all-hit resume')
        return original(name,*args,**kwargs)
    builtins.__import__=no_torch
    hits,_=produce(resources,works,cache);builtins.__import__=original
    assert hits=={'encoded_cache_hits':len(works)}
write_json(HERE/'production.json',dict(plan=plan,stats=stats,resume=hits,resume_torch_import_blocked=True,
                                    encoder_namespace=directory.name,pack=result,pack_directory=output.relative_to(ROOT).as_posix()))
print(json.dumps(dict(resources=7,frames=434,unique_work=len(works),stats=stats,resume=hits)))
