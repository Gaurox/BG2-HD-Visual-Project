"""Complete available MonsterOld Q3m V7 K6 x2; no SDF, shared exact cache."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from q3m_multipart_seams import apply_context
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
selection=load(HERE.parent/'q3m-monster-old-selection-x2-20261004-v1/selection.json')
selection['scope']='complete available native MonsterOld G1/G2/G1E/G2E + auxiliary INV; enhanced palette Q3m K6 V7 x2; no SDF'
write_json(HERE/'selection.json',selection)
resources,works,plan=source_plan(HERE/'selection.json','monster_old')
assert len(resources)==218 and plan['physical_frames']==17754 and len(works)==16785
print(json.dumps(dict(stage='plan',**{k:plan[k] for k in ('resources','physical_frames','unique_source_work','unique_encoded_work')})),flush=True)
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';output=ROOT/'sprite/.work'/HERE.name/'isolated'
pause_state_path=output.parent/'PAUSE_STATE.json'
prior=load(pause_state_path) if pause_state_path.exists() else {}
assert not output.exists() and not (HERE/'production.json').exists()
with exclusive(cache):
    namespace=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
    old={p:file_sha(p) for key in works if (p:=cache/'encoded'/namespace/(key+'.npz')).exists()}
    stats,directory=produce(resources,works,cache)
    assert all(file_sha(p)==s for p,s in old.items())
    contextual=apply_context(resources,works,HERE/'selection.json',cache,'run')
    assert contextual['contexts']==0
    packed=pack(resources,works,output)
cumulative=dict(new_guides=prior.get('completed_guides',0)+stats.get('new_guides',0),new_neural_targets=prior.get('completed_neural_targets',0)+stats.get('new_neural_targets',0),new_encoded_work=prior.get('completed_encoded_files',0)+stats.get('new_encoded_work',0))
write_json(HERE/'production.json',dict(plan=plan,stats=stats,cumulative_stats=cumulative,resumed_after_user_pause=bool(prior),acquired_encoded_sha256_unchanged=len(old),encoder_namespace=directory.name,pack=packed,pack_directory=output.relative_to(ROOT).as_posix(),multipart_context=contextual,SDF=False,ingame_QA=False))
print(json.dumps(dict(stage='complete',resources=packed['resources'],frames=packed['frames'],stats=stats)),flush=True)
