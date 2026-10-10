"""DLL-only successor; no change to production/QA authorities or sprite bytes."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
assert not(HERE/'current-generation.json').exists()
r=load(HERE/'runtime.json');v=load(HERE/'runtime-verification.json');a=load(HERE/'analysis.json');b=load(HERE/'baseline.json')
assert v['passed'] and v['all_playback']['animation_ids']==331 and v['all_playback']['observed_6110_fixed']
write_json(HERE/'current-generation.json',dict(schema='bg2-common-sprite-runtime-successor-v1',role='installation-candidate-not-QA-or-release',
    animation_ids=a['animation_ids'],family_scope='all 15 installed creature/character families',
    runtime=identity(HERE/'runtime.json'),dll=r['dll'],catalog_sha256=b['catalog_sha256'],
    parent_generation=identity(HERE.parent/'q3m-monster-g2-palettes-x2-20261007-v1/current-generation.json'),
    runtime_verification=identity(HERE/'runtime-verification.json'),sprites_recalculated=0,changed_files=['InfinityEngine-Enhancer.dll'],
    production_changed=False,existing_QA_decisions_immutable=True,ingame_QA=False,release=False))
print(json.dumps(dict(stage='install-prepared',ids=331,changed_files=1)),flush=True)
