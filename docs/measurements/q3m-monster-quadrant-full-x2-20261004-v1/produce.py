"""Complete native Quadrant family; improved live palettes, x2, no SDF."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from palette_work_plan import file_sha,write_json
selection=json.loads((HERE.parent/'q3m-monster-quadrant-selection-x2-20261004-v1/selection.json').read_text())
selection['scope']='complete available native Quadrant; all banks/quadrants/cycles/directions; native empty declarations unchanged; Q3m x2 enhanced palettes, no SDF'
write_json(HERE/'selection.json',selection)
resources,works,plan=source_plan(HERE/'selection.json','monster_quadrant')
assert len(resources)==132 and plan['physical_frames']==12928 and len(works)==12476
print(json.dumps(dict(stage='plan',resources=132,frames=12928,encoded_work=len(works))),flush=True)
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';output=ROOT/'sprite/.work'/HERE.name/'isolated'
assert not output.exists() and not (HERE/'production.json').exists()
with exclusive(cache):
    old={p:file_sha(p) for p in (cache/'encoded').rglob('*.npz') if p.stem in works}
    stats,directory=produce(resources,works,cache)
    assert all(file_sha(p)==s for p,s in old.items())
    packed=pack(resources,works,output)
write_json(HERE/'production.json',dict(plan=plan,stats=stats,acquired_encoded_sha256_unchanged=len(old),encoder_namespace=directory.name,pack=packed,pack_directory=output.relative_to(ROOT).as_posix(),SDF=False))
print(json.dumps(dict(stage='complete',resources=packed['resources'],frames=packed['frames'],stats=stats)),flush=True)
