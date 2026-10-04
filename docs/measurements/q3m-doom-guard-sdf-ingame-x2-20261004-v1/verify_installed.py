"""Native full SDF compositions from actual installed catalogue/leaves; confirm DLL identity."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');installation=load(HERE/'installation-verification.json');game=get_path('bg2ee_game_root',required=True)
assert installation['status']=='installed-pending-ingame-qa'
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
r=subprocess.run([str(HERE/'composite_probe.exe'),str(game/'iee-assets/creature-sprites'),str(HERE/'work/composite.oracle')],capture_output=True,text=True,encoding='utf-8')
(HERE/'native-installed-composite.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0,(r.stdout[-800:],r.stderr)
report=json.loads(next(s for s in reversed(r.stdout.splitlines()) if s.startswith('{')));assert report['passed']
assert report==load(HERE/'verification.json')['native_composite']
write_json(HERE/'installed-composition.json',dict(passed=True,catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],native_composite=report,ingame_QA=False))
print(json.dumps(dict(installed_compositions=report,QA=False)))
