"""Seal the diagnostic/proposal comparison without changing the installed runtime."""
from pathlib import Path
import sys,json,subprocess,re
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_work_plan import file_sha,write_json
def result(name):
    return next(json.loads(l) for l in reversed((HERE/name).read_text().splitlines()) if l.startswith('{'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
before=result('cold-lookup.log');after=result('proposed-lookup.log')
assert before['cold_misses']==12 and after['cold_misses']==0 and before['warm_hits']==after['warm_hits']==12
check=subprocess.run(['git','apply','--check',str(HERE/'proposed-fix.patch')],cwd=ROOT,capture_output=True,text=True);assert check.returncode==0,check.stderr
assert subprocess.run(['git','diff','--quiet','--','engine/InfinityEngine-Enhancer/source-patchee'],cwd=ROOT).returncode==0
generation=json.loads((HERE.parent/'q3m-ankheg-sdf-ingame-x2-20261004-v1/current-generation.json').read_text());game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==generation['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==generation['catalog']['sha256']
timings=[float(m[1]) for l in (HERE/'proposed-lookup.log').read_text().splitlines() if (m:=re.search(r'ready_ms=([\d.]+)',l))]
write_json(HERE/'proposal-verification.json',dict(schema='bg2-ankheg-SDF-stability-proposed-fix-verification-v1',base_commit='a46a319a',
    original_probe=before,proposed_probe=after,proposed_wait_ms=dict(maximum=max(timings),total=sum(timings)),
    patch=identity(HERE/'proposed-fix.patch'),applies_cleanly=True,proposed_resolver_compiled=True,
    runtime_hook_change='patch-reviewed-and-applies-cleanly; no DLL compilation or game installation requested',
    game_DLL_byte_identical=True,game_catalog_byte_identical=True,assets_changed=False,engine_source_changed=False,ingame_QA=False,
    session_analysis=identity(HERE/'log-analysis.json'),source_probe=identity(HERE/'cold_lookup_probe.cpp')))
print(json.dumps(dict(before_cold_misses=12,after_cold_misses=0,installed_runtime_changed=False)))
