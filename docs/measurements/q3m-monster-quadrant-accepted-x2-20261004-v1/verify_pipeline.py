"""CPU parity with accepted producer + native edge and alias regression cases."""
import importlib.util,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_multipart_seams import context_plan,strength,load,apply_context
from palette_work_plan import write_json,file_sha
from q3m_family_witnesses import source_plan
accepted=HERE.parent/'q3m-monster-quadrant-seam-fixed-x2-20261004-v1'
spec=importlib.util.spec_from_file_location('accepted_common',accepted/'common.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
resources,works,summary,contexts,bindings=old.plan()
new_contexts,new_bindings=context_plan(resources,load(accepted/'selection.json'))
assert new_bindings==bindings and new_contexts.keys()==contexts.keys()
checks=0
for key,context in contexts.items():
    assert new_contexts[key]['geometry']==context['geometry']
    for a in context['geometry']:
        assert np.array_equal(strength(a,context['geometry']),old.strength(a,context['geometry']))
        checks+=1
# Adjacent edges only, opposite border unchanged, partial overlap, empty parts.
a=(12,12,0,0);right=(12,6,-12,-3);far=(12,12,-50,0);empty=(0,0,0,0)
s=strength(a,[a,right,empty]);assert not s[:6].any() and not s[18:].any()
assert not s[:,:16].any() and s[6:18,-1].min()==1
assert not strength(a,[a,far,empty]).any()
bottom=(6,12,-3,-12)
assert np.array_equal(strength(a,[a,bottom]),s.T)
# Duplicate draws share contexts. Identical tile bytes with different neighbours
# require different bindings and cannot silently pick the first occurrence.
profile=resources[0]['profile']
w=dict(family='monster_quadrant',animation_id='0x1000',refs=['P1','P2'],multipart_groups=[['P1','P2']])
r1=dict(witness=w,resref='P1',profile=profile,cycles=[[0,0]],frames=[dict(key='a',geometry=a,frame_index=0)])
r2=dict(witness=w,resref='P2',profile=profile,cycles=[[0,0]],frames=[dict(key='b',geometry=right,frame_index=0)])
c,b=context_plan([r1,r2],dict(witnesses=[w]));assert len(c)==1 and len(b)==2
r2['cycles']=[[0,1]];r2['frames'].append(dict(key='c',geometry=right,frame_index=1))
try:context_plan([r1,r2],dict(witnesses=[w]))
except ValueError as e:assert 'different neighbours' in str(e)
else:raise AssertionError('Incompatible frame alias accepted')
report=apply_context(resources,works,accepted/'selection.json',ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1','plan')
assert report['contexts']==3144 and report['referenced_native_frames']==12656 and report['unreferenced_native_frames']==272
assert 'torch' not in sys.modules
write_json(HERE/'pipeline-verification.json',dict(passed=True,producer_sha256=file_sha(ROOT/'pipeline/scripts/q3m_multipart_seams.py'),actual_contexts=3144,actual_bindings=12656,accepted_band_mask_equalities=checks,unreferenced_frames=272,partial_edges=True,empty_parts=True,opposite_edges_unchanged=True,identical_draw_dedup=True,incompatible_alias_rejected=True,plan_no_torch=True,neural_work=0))
print(json.dumps(dict(passed=True,contexts=3144,bindings=12656,mask_equalities=checks,torch_imported=False)))
