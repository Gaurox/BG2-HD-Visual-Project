"""Complete native ambient, fixed animals and live ramp humanoids; shared V7 source/target/encoded caches, no duplicate inference."""
import builtins,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from palette_work_plan import file_sha,write_json

cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
output=ROOT/'sprite/.work/q3m-ambient-full-x2-20261004-v1/isolated'
assert not output.exists() and not (HERE/'production.json').exists(),'new run required'
resources,works,plan=source_plan(HERE/'selection.json','ambient')
assert plan['families']==1 and plan['physical_frames']==2734 and len(resources)==39 and len(works)==2406
print(json.dumps(dict(stage='plan',**{k:plan[k] for k in ('resources','physical_frames','unique_source_work','unique_encoded_work')})),flush=True)
with exclusive(cache):
    # Keep acquired witness encodings immutable; produce checks every hit's contract.
    old={p:file_sha(p) for p in (cache/'encoded').rglob('*.npz') if p.stem in works}
    stats,directory=produce(resources,works,cache)
    assert all(file_sha(p)==digest for p,digest in old.items()),'acquired encoded bytes changed'
    result=pack(resources,works,output)
    assert result['animation_count']==18 and result['resources']==34 and result['frames']==2580 and result['shared_resource_bindings']==5 and result['logical_resource_bindings']==39
    original=builtins.__import__
    def no_torch(name,*args,**kwargs):
        if name.split('.')[0]=='torch':raise RuntimeError('Torch imported by all-hit resume')
        return original(name,*args,**kwargs)
    builtins.__import__=no_torch
    try:hits,_=produce(resources,works,cache)
    finally:builtins.__import__=original
    assert hits=={'encoded_cache_hits':len(works)}
write_json(HERE/'production.json',dict(plan=plan,stats=stats,resume=hits,resume_torch_import_blocked=True,
    acquired_encoded_sha256_unchanged=len(old),encoder_namespace=directory.name,pack=result,
    pack_directory=output.relative_to(ROOT).as_posix()))
print(json.dumps(dict(resources=34,frames=2580,animations=18,stats=stats,resume=hits)),flush=True)
