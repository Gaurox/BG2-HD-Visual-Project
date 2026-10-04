"""Create the Ambient run from the compatible Town tools; never mutate the parent."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
parent=ROOT/'docs/measurements/q3m-town-static-full-x2-20261004-v1'
proposal=ROOT/'docs/measurements/q3m-ambient-selection-x2-20261004-v1'
selection=json.loads((proposal/'selection.json').read_text(encoding='utf-8-sig'))
selection['scope']='complete available native ambient production; all frames/cycles/directions; no SDF'
(HERE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')
(HERE/'.gitignore').write_text('work/\ningame-installation/\n',encoding='utf-8')
def source(name):return (parent/name).read_text(encoding='utf-8')
def save(name,s):
    assert not (HERE/name).exists(),name
    (HERE/name).write_text(s,encoding='utf-8')
s=source('produce.py').replace('town_static','ambient').replace('town-static','ambient')
s=s.replace("plan['physical_frames']==1543 and len(resources)==18","plan['physical_frames']==2734 and len(resources)==39 and len(works)==2406")
s=s.replace("result['resources']==18 and result['frames']==1543 and result['shared_resource_bindings']==0","result['resources']==34 and result['frames']==2580 and result['shared_resource_bindings']==5 and result['logical_resource_bindings']==39")
s=s.replace('dict(resources=18,frames=1543,animations=18','dict(resources=34,frames=2580,animations=18')
save('produce.py',s)
s=source('creatures.py').replace('town-static','ambient').replace("ref=f'QTST{aid:04X}'","ref=f'QAMB{aid:04X}'")
s=s.replace(".read_text()",".read_text(encoding='utf-8-sig')").replace("for r in representatives)+'\\n')","for r in representatives)+'\\n',encoding='utf-8')")
save('creatures.py',s)
s=source('prepare.py').replace('town_static','ambient').replace('town-static','ambient')
s=s.replace("q3m-horse-eye-ingame-x2-20261004-v1","q3m-town-static-full-x2-20261004-v1")
s=s.replace("new['total_resources']==18 and new['total_frames']==1543","new['total_resources']==34 and new['total_frames']==2580")
s=s.replace("qa-decisions/ambient_static/2026-10-04-accepted-full-ambient-static-horse-eye-v3-q3m-v7-x2-catmullrom-v1.json","qa-decisions/town_static/2026-10-04-accepted-full-available-town-static-q3m-v7-x2-catmullrom-v1.json")
s=s.replace("qa=ROOT/", "for f in receipt['fixtures']:\n    preserved[f['target']]=dict(relative_path=f['target'],sha256=f['sha256'])\nqa=ROOT/")
s=s.replace("len(checked['animations'])==122 and checked['total_resources']==4636 and len(checked['directory'])==50317","len(checked['animations'])==140 and checked['total_resources']==4670 and checked['total_frames']==1593131 and len(checked['directory'])==50356")
s=s.replace("new_owner=14,new_resources=18,new_frames=1543,source_absent_animation_ids=['0x4001']","new_owner=12,new_resources=34,new_frames=2580,logical_resource_bindings=39,shared_resource_bindings=5,source_absent_animation_ids=selection['source_absent_animation_ids']")
s=s.replace('accepted_ambient_static_resources_preserved=26','accepted_town_static_resources_preserved=18')
s=s.replace('resources=18,frames=1543','resources=34,frames=2580')
s=s.replace("source_absent_animation_ids=['0x4001']","source_absent_animation_ids=selection['source_absent_animation_ids']")
s=s.replace('"""Append ambient to the exact installed, accepted horse-v3 parent."""','"""Append Ambient to the installed accepted Town parent; preserve horse-v3 and every acquired leaf."""')
save('prepare.py',s)
s=source('install.ps1').replace('town_static','ambient').replace('town-static','ambient')
s=s.replace('$generation.resources -ne 18 -or $generation.frames -ne 1543','$generation.resources -ne 34 -or $generation.frames -ne 2580')
s=s.replace('$native.resources -ne 18 -or $native.frames -ne 1543','$native.resources -ne 39 -or $native.frames -ne 2734')
s=s.replace('resources=18;frames=1543','resources=34;frames=2580').replace('new_leaf_sha256_verified=18','new_leaf_sha256_verified=34')
s=s.replace('18 IDs / 18 BAM / 1543 frames','18 IDs / 34 BAM / 2580 physical frames')
save('install.ps1',s)
save('restore.ps1',source('restore.ps1').replace('seven generated test CRE removed','generated test CRE removed'))
