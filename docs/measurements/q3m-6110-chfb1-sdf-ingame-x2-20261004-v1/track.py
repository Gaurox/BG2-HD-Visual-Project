"""Record installed Character body trial; no QA inferred."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
snapshot=load(HERE/'installation-verification.json');production=load(HERE/'production.json')
assert snapshot['status']=='installed-pending-ingame-qa'
path=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(path)
assert not any(x.get('body')=='CHFB1' and '0x6110' in x.get('animation_ids',[]) for x in tracking['current_contour_trials'])
rel=HERE.relative_to(ROOT).as_posix()
trial=dict(family='character',body='CHFB1',scope='0x6110 unarmoured world body only; equipment/UI/other consumers unchanged',
           animation_ids=['0x6110'],resources=23,physical_frames=10323,registry_version=10,colour_profile=1,decode_rule=1,
           world_filter='CatmullRom',recipe=production['recipe'],stats=production['stats'],
           reference=f'{rel}/current-generation.json',production_reference=f'{rel}/production.json',
           runtime_reference=f'{rel}/runtime.json',installation_reference=f'{rel}/ingame-installation/active-test.json',
           installation_snapshot=f'{rel}/installation-verification.json',restore_script=f'{rel}/restore.ps1',
           state='Character-CHFB1-SDF-trial-installed-ingame-QA-pending',qa_ingame=False,qa_state='pending',release=False,
           colour_I_F_stored_bytes_unchanged=True,native_shadow_alpha=128)
tracking['current_contour_trials'].append(trial)
family=next(x for x in tracking['families'] if x['engine_section']=='character')
family.setdefault('current_contour_trials',[]).append(copy.deepcopy(trial))
tracking['engine_integration']['installed_candidate_reference']=f'{rel}/installation-verification.json'
path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
csv=ROOT/'sprite/index/q3m-work-items.csv';lines=csv.read_text(encoding='utf-8').splitlines(keepends=True)
header=lines[0].strip().split(',');colour=header.index('colour_variant_state')
for n,line in enumerate(lines):
    if line.startswith('0x6110,'):
        cells=line.rstrip('\n').split(',');assert len(cells)==len(header)
        cells[colour]='v6-colours-with-v10-SDF-CHFB1-only-trial-installed-QA-pending'
        lines[n]=','.join(cells)+'\n'
csv.write_text(''.join(lines),encoding='utf-8',newline='\n')
print('Recorded 0x6110 CHFB1 SDF trial; existing QA decisions and Ankheg trial retained.')
