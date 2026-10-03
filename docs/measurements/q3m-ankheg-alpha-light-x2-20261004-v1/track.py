"""Update current trial; archive rejection without altering historical production proofs."""
import sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json,file_sha
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
p=load(HERE/'production.json');receipt=load(HERE/'ingame-installation/active-test.json')
assert receipt['status']=='installed-pending-ingame-qa'
assert load(ROOT/'docs/measurements/q3m-ankheg-spline-fit1-x2-20261003-v1/ingame-installation/active-test.json')['status']=='restored-parent'
path=ROOT/'sprite/index/q3m-work-tracking.json';track=load(path)
family=next(f for f in track['families'] if f['engine_section']=='monster_ankheg')
old=copy.deepcopy(family['current_contour_trial'])
assert 'spline-fit1' in old['reference']
decision='sprite/index/qa-decisions/monster_ankheg/2026-10-04-rejected-spline-fit1-q3m-x2-catmullrom-v1.json'
old.update(family='monster_ankheg',state='rejected-ingame-restored-parent',qa_state='failed',
    qa_decision=decision,qa_decision_sha256=file_sha(ROOT/decision),installation_state='restored-parent')
track.setdefault('historical_contour_trials',[]).append(old)
trial=copy.deepcopy(family['current_contour_trial'])
prefix=HERE.relative_to(ROOT).as_posix()
for key,filename in (('reference','current-generation.json'),('production_reference','production.json'),
    ('installation_reference','ingame-installation/active-test.json'),('installation_snapshot','installation-verification.json'),
    ('runtime_reference','runtime.json'),('restore_script','restore.ps1')):trial[key]=prefix+'/'+filename
trial.update(recipe=p['recipe'],stats=p['stats'],qa_state='pending',
    state='alpha-trial-produced-host-verified-installed-ingame-QA-pending',qa_ingame=False,
    positive_source_support_preserved=True,replaces_rejected_trial_decision=decision)
family['current_contour_trial']=trial
track['current_contour_trials']=[dict(family='monster_ankheg',**trial)]
track['engine_integration']['installed_candidate_reference']=prefix+'/installation-verification.json'
track['recorded_on']='2026-10-04'
write_json(path,track)
csv=ROOT/'sprite/index/q3m-work-items.csv';raw=csv.read_bytes()
assert raw.count(b'v7-colours-with-v8-spline-fit1-trial-installed-QA-pending')==1
csv.write_bytes(raw.replace(b'v7-colours-with-v8-spline-fit1-trial-installed-QA-pending',
    b'v7-colours-with-v8-alpha-light-trial-installed-QA-pending'))
print(json.dumps(dict(current_trial=prefix,previous='rejected-ingame-restored-parent',QA='pending')))
