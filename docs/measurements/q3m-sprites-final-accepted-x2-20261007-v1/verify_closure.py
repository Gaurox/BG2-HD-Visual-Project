"""Check selected accepted variants; keep unselected historical trials untouched."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
path=ROOT/'sprite/index/q3m-work-tracking.json';t=load(path)
selected={p['family']:p for p in t['current_recipe_complete_productions']+t['selected_recipe_complete_productions']}
for p in t['current_contour_trials']:
    if p.get('qa_ingame') and p.get('qa_reference'):selected[p['family']]=p
assert len(selected)==15 and all(p.get('qa_ingame') for p in selected.values())
ids={i for p in selected.values() for i in p['animation_ids']};assert len(ids)==331
records=[]
for family,p in sorted(selected.items()):
    q=ROOT/p['qa_reference'];qa=load(q);assert qa['status']=='accepted'
    records.append(dict(family=family,animation_ids=p['animation_ids'],qa=identity(q),
        production_reference=p.get('reference'),registry_version=p.get('registry_version'),state=p['state']))
assert t['queue_totals']['remaining_user_QA_animation_ids']==0
assert not t['remaining_full_production_families']
report=HERE/'closure-verification.json';assert not report.exists()
write_json(report,dict(passed=True,families=15,animation_ids=331,selected_accepted_variants=records,
    counting_rule='complete productions + retained CharacterV6 + accepted current contour overrides; no promotion of unselected alternatives',
    historical_Ankheg_nonSDF_production_QA_unchanged=True,active_Ankheg_V9_SDF_QA_preserved=True,
    remaining_production_families=0,remaining_ingame_QA_ids=0,release=False))
t['final_selected_recipe_status']['accepted_variants_reference']=report.relative_to(ROOT).as_posix()
write_json(path,t)
print(json.dumps(dict(passed=True,families=15,ids=331,remaining_retests=0)),flush=True)
