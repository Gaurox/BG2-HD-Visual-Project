"""Create a fresh Character_old run from compatible scoped Ambient tools."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
parent=ROOT/'docs/measurements/q3m-ambient-full-x2-20261004-v1'
proposal=ROOT/'docs/measurements/q3m-character-old-selection-x2-20261004-v1'
selection=json.loads((proposal/'selection.json').read_text(encoding='utf-8-sig'))
selection['scope']='complete available native character_old production; all frames/cycles/directions; no SDF'
assert not (HERE/'selection.json').exists()
(HERE/'selection.json').write_text(json.dumps(selection,indent=2)+'\n',encoding='utf-8')
(HERE/'.gitignore').write_text('work/\ningame-installation/\n',encoding='utf-8')
def source(name):return (parent/name).read_text(encoding='utf-8')
def save(name,s):
    assert not (HERE/name).exists(),name
    (HERE/name).write_text(s,encoding='utf-8')
def counts(s):
    return s.replace('2734','5661').replace('2580','4725').replace('2406','3771')
s=counts(source('produce.py').replace('ambient-full','character-old-full').replace("'ambient'","'character_old'"))
s=s.replace('len(resources)==39','len(resources)==121')
s=s.replace("result['animation_count']==18 and result['resources']==34","result['animation_count']==7 and result['resources']==99")
s=s.replace("result['shared_resource_bindings']==5 and result['logical_resource_bindings']==39","result['shared_resource_bindings']==22 and result['logical_resource_bindings']==121")
s=s.replace('dict(resources=34,frames=4725,animations=18','dict(resources=99,frames=4725,animations=7')
s=s.replace('Complete native ambient, fixed animals and live ramp humanoids','Complete Character_old, fixed/ramp bodies and transparent native guards')
save('produce.py',s)
s=counts(source('prepare.py').replace('ambient-full','character-old-full').replace("family='ambient'","family='character_old'"))
s=s.replace("q3m-town-static-full-x2-20261004-v1","q3m-ambient-full-x2-20261004-v1")
s=s.replace("len(new['animations'])==18 and new['total_resources']==34","len(new['animations'])==7 and new['total_resources']==99")
s=s.replace('qa-decisions/town_static/2026-10-04-accepted-full-available-town-static-q3m-v7-x2-catmullrom-v1.json','qa-decisions/ambient/2026-10-04-accepted-full-available-ambient-q3m-v7-x2-catmullrom-v1.json')
s=s.replace('len(checked[\'animations\'])==140 and checked[\'total_resources\']==4670 and checked[\'total_frames\']==1593131 and len(checked[\'directory\'])==50356',"len(checked['animations'])==147 and checked['total_resources']==4769 and checked['total_frames']==1597856 and len(checked['directory'])==50477")
s=s.replace('new_owner=12,new_resources=34','new_owner=6,new_resources=99')
s=s.replace('logical_resource_bindings=39,shared_resource_bindings=5','logical_resource_bindings=121,shared_resource_bindings=22')
s=s.replace('accepted_town_static_resources_preserved=18','accepted_ambient_resources_preserved=34')
s=s.replace('resources=34,frames=4725','resources=99,frames=4725')
s=s.replace('V7-complete-ambient','V7-complete-character_old').replace('bg2-ambient','bg2-character-old')
s=s.replace('Append Ambient to the installed accepted Town parent','Append Character_old to the installed accepted Ambient parent')
save('prepare.py',s)
s=source('creatures.py').replace('ambient-full','character-old-full').replace("QAMB{aid:04X}","QCOL{aid:04X}")
begin=s.index('preferred={');end=s.index('\nfor aid,w in ids.items():',begin)
s=s[:begin]+"preferred={0x6400:'DRIZZT',0x6401:'AMELM01',0x6402:'MONKTU1',0x6403:'SKELET01',0x6404:'SAREVOKD'}"+s[end:]
s=s.replace('if existing:representatives.append','if existing and aid not in (0x6405,0x6406):representatives.append')
save('creatures.py',s)
s=counts(source('install.ps1').replace('ambient','character_old'))
s=s.replace('$generation.resources -ne 34','$generation.resources -ne 99').replace('$generation.animation_ids.Count -ne 18','$generation.animation_ids.Count -ne 7')
s=s.replace('$native.resources -ne 39','$native.resources -ne 121')
s=s.replace('resources=34;frames=4725','resources=99;frames=4725').replace('new_leaf_sha256_verified=34','new_leaf_sha256_verified=99')
s=s.replace('18 IDs / 34 BAM','7 IDs / 99 BAM')
save('install.ps1',s)
save('restore.ps1',source('restore.ps1'))
s=counts(source('verify.py').replace("'ambient'","'character_old'"))
s=s.replace("native[name]['resources']==39","native[name]['resources']==121")
s=s.replace("['encoded_cache_hits']==1024","['encoded_cache_hits']==288").replace('==1382','==3483').replace("['acquired_encoded_sha256_unchanged']==1024","['acquired_encoded_sha256_unchanged']==288")
s=s.replace("(('0xC000','0xC500'),('0xC300','0xCC04'))","(('0x6405','0x6406'),)")
s=s.replace('(1320,6*260)','(1320,2*260)').replace('len(unique_refs)==34 and len(models)==16','len(unique_refs)==99 and len(models)==6')
s=s.replace('resources=34','resources=99').replace('logical_resources=39','logical_resources=121').replace('models=16,shared_resource_bindings=5','models=6,shared_resource_bindings=22')
s=s.replace('All physical frames, both alias bindings, native K6 pixel oracle; 16-model contact sheet','All Character_old physical frames/guard alias/transparent bodies; native K6 oracle')
save('verify.py',s)
