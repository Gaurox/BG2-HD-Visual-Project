"""Check Icewind native decoding/playback under the appended installed catalog."""
import json,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
PROD=HERE.parent/'q3m-icewind-full-x2-20261006-v1';WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import write_json,file_sha
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(HERE/'verification.json').exists()
gen=load(HERE/'current-generation.json');output=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
resources,_,_=source_plan(PROD/'selection.json','monster_icewind')
exe=ROOT/'sprite/.work/q3m-icewind-full-x2-20261006-v1/runtime-build/Release/iee_palette_partner_tests.exe'
native=runpy.run_path(str(PROD/'verify.py'))['verify_native_batches'](exe,output,resources)
assert native['passed'] and native['resources']==1140 and native['frames']==76955
probe=ROOT/'sprite/.work/q3m-icewind-full-x2-20261006-v1/playback_probe.exe'
oracle=ROOT/'sprite/.work/q3m-icewind-full-x2-20261006-v1/native-playback.oracle'
with(HERE/'playback.log').open('w',encoding='utf-8') as stream:
    subprocess.run([str(probe),str(output),str(oracle)],stdout=stream,stderr=subprocess.STDOUT,check=True)
playback=json.loads(next(line for line in reversed((HERE/'playback.log').read_text(encoding='utf-8').splitlines()) if line.startswith('{')))
assert playback['passed'] and playback['missing_or_wrong_frames']==0 and playback['resources']==1140
write_json(HERE/'verification.json',dict(passed=True,catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],native_world=native,playback=playback,
    inherited_catalog_structure=load(HERE/'catalog-proof.json'),production_generation=gen['production_generation'],ingame_QA=False,release=False))
print(json.dumps(dict(stage='combined-verified',passed=True,resources=1140,frames=76955,playback=playback)),flush=True)
