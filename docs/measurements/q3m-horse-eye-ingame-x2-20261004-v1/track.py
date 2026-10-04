"""Record this installed replacement only; preserve all existing QA and other items."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
receipt=load(HERE/'ingame-installation/active-test.json')
assert receipt['status']=='installed-pending-ingame-qa' and not receipt['ingame_QA']
old='docs/measurements/q3m-horse-eye-x2-20261004-v1'
new=HERE.relative_to(ROOT).as_posix()
path=ROOT/'sprite/index/q3m-work-tracking.json'
tracking=load(path)
changed=0
def update(obj):
    global changed
    if isinstance(obj,dict):
        for replacement in obj.get('current_resource_replacements',[]):
            if replacement.get('reference')==old+'/current-generation.json':
                replacement.update(reference=new+'/current-generation.json',
                    installation_snapshot=new+'/installation-verification.json',
                    state='horse-front-eye-v3-installed-ingame-QA-pending', changed_frames=5,
                    changed_x2_pixels=134, new_inference=0, new_leaves=1,
                    retained_previous_profile_eye_frames=10,
                    previous_reference=old+'/current-generation.json',
                    analysis_reference='docs/measurements/q3m-horse-eye-directions-20261004-v3/analysis.json')
                changed+=1
        for value in obj.values():
            update(value)
    elif isinstance(obj,list):
        for value in obj:
            update(value)
update(tracking)
assert changed==2
tracking['engine_integration']['latest_installation_verification_reference']=new+'/installation-verification.json'
path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
csv=ROOT/'sprite/index/q3m-work-items.csv'
text=csv.read_text(encoding='utf-8-sig')
rows=text.splitlines(keepends=True)
matches=0
for i,row in enumerate(rows):
    if row.startswith('0xB100,HORSE,ambient_static,'):
        assert old+'/current-generation.json' in row
        rows[i]=row.replace(old,new).replace('v7-x2-native-eye-corrected-installed-ingame-QA-pending',
                                            'v7-x2-front-eye-v3-installed-ingame-QA-pending')
        matches+=1
assert matches==1
csv.write_text(''.join(rows),encoding='utf-8')
print('Updated two horse current-replacement references and the HORSE row; QA unchanged.')
