"""Complete flying family; shared acquired V7 cache and one leaf per native BAM."""
import builtins,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from palette_work_plan import file_sha,write_json

cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
output=ROOT/'sprite/.work/q3m-flying-full-x2-20261003-v1/isolated'
assert not output.exists() and not (HERE/'production.json').exists()
resources,works,plan=source_plan(HERE/'selection.json','flying')
assert plan['families']==1 and plan['unique_encoded_work']==243 and len(resources)==5
comparison=json.loads((ROOT/'docs/measurements/q3m-flying-frame-x2-x4-20261003-v1/comparison.json').read_text(encoding='utf-8'))
with exclusive(cache):
    stats,directory=produce(resources,works,cache)
    for sample in comparison['samples']:
        path=directory/(sample['encoded_work_key']+'.npz')
        assert file_sha(path)==sample['encodings'][0]['encoded_sha256'],'accepted x2 bytes changed'
    result=pack(resources,works,output)
    assert result['animation_count']==5 and result['resources']==4 and result['frames']==243 and result['shared_resource_bindings']==1
    original=builtins.__import__
    def no_torch(name,*args,**kwargs):
        if name.split('.')[0]=='torch':raise RuntimeError('Torch imported by all-hit resume')
        return original(name,*args,**kwargs)
    builtins.__import__=no_torch
    try:hits,_=produce(resources,works,cache)
    finally:builtins.__import__=original
    assert hits=={'encoded_cache_hits':len(works)}
write_json(HERE/'production.json',dict(plan=plan,stats=stats,resume=hits,resume_torch_import_blocked=True,
    accepted_sample_encodings_unchanged=4,encoder_namespace=directory.name,pack=result,
    pack_directory=output.relative_to(ROOT).as_posix()))
print(json.dumps(dict(resources=4,frames=243,animations=5,stats=stats,resume=hits)))
