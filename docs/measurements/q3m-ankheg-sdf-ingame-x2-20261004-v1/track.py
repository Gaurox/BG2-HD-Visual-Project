"""Current Ankheg trial pointer; retain immutable production and QA decisions."""
import sys,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
receipt=load(HERE/'ingame-installation/active-test.json');p=load(HERE/'production.json')
assert receipt['status']=='installed-pending-ingame-qa' and receipt['registry_version']==9
path=ROOT/'sprite/index/q3m-work-tracking.json';track=load(path)
family=next(f for f in track['families'] if f['engine_section']=='monster_ankheg')
old=copy.deepcopy(family['current_contour_trial']);assert 'alpha-light' in old['reference']
old.update(family='monster_ankheg',state='superseded-by-SDF-trial',installation_state='superseded',
    user_feedback='les pixels de contours sont encores tres marqués en escalier',qa_ingame=False)
track.setdefault('historical_contour_trials',[]).append(old)
prefix=HERE.relative_to(ROOT).as_posix();trial=copy.deepcopy(family['current_contour_trial'])
for key,filename in [('reference','current-generation.json'),('production_reference','production.json'),
    ('installation_reference','ingame-installation/active-test.json'),('installation_snapshot','installation-verification.json'),
    ('runtime_reference','runtime.json'),('restore_script','restore.ps1')]:trial[key]=prefix+'/'+filename
trial.pop('positive_source_support_preserved',None);trial.pop('replaces_rejected_trial_decision',None)
trial.update(registry_version=9,recipe=p['recipe'],stats=p['stats'],qa_state='pending',state='SDF-trial-produced-host-verified-installed-ingame-QA-pending',
    qa_ingame=False,reference_offline='docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1/trial.json',
    native_Q3m_planes_unchanged=True,screen_coverage='8x8 bilinear signed-distance samples per screen pixel')
family['current_contour_trial']=trial;track['current_contour_trials']=[dict(family='monster_ankheg',**trial)]
track['engine_integration']['installed_candidate_reference']=prefix+'/installation-verification.json';track['recorded_on']='2026-10-04'
write_json(path,track)
csv=ROOT/'sprite/index/q3m-work-items.csv';raw=csv.read_bytes()
assert raw.count(b'v7-colours-with-v8-alpha-light-trial-installed-QA-pending')==1
csv.write_bytes(raw.replace(b'v7-colours-with-v8-alpha-light-trial-installed-QA-pending',b'v7-colours-with-v9-sdf-trial-installed-QA-pending'))
print(json.dumps(dict(current_trial=prefix,previous='superseded-alpha-light',QA='pending')))
