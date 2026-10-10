"""Build from the source snapshot of the installed DLL; preserve unrelated changes."""
from pathlib import Path
import difflib, hashlib, shutil, sys, json
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v2
BATCH=ROOT/'animations/batches/portails-deux-correctif-20261010-v1'
BASE=ROOT/'sprite/.work/q3m-all-sprite-playback-x2-20261007-v1/runtime-src'
CANON=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
WORK=BATCH/'.work'; DEST=WORK/'runtime-src'
assert v2.sha256_file(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.dll')=='70a2745b212babe378c6ccd8b1660110ad3aac5a9ef7523ecbbfcea776bb6d09'
changed=['CMakeLists.txt','src/iee/hooks.cpp','src/iee/native_occlusion_bridge.cpp','src/iee/native_occlusion_bridge.h','src/iee/core/native_occlusion_feather.h','tests/native_occlusion_feather_tests.cpp']
if not DEST.exists():
    shutil.copytree(BASE,DEST)
patch=[]
for name in changed:
    before=(BASE/name).read_text(encoding='utf-8').splitlines(True) if (BASE/name).exists() else []
    after=(CANON/name).read_text(encoding='utf-8').splitlines(True)
    if name == 'CMakeLists.txt':
        # Retain the snapshot's absolute water dependency path for relocated sources.
        canonical=''.join(after)
        anchor='    add_executable(iee_map_page_shadow_preflight'
        new_test=canonical.split('if(BUILD_TESTING)\n',1)[1].split(anchor,1)[0]
        after=''.join(before).replace('if(BUILD_TESTING)\n','if(BUILD_TESTING)\n'+new_test,1).splitlines(True)
    patch.extend(difflib.unified_diff(before,after,fromfile='installed-source/'+name,tofile='corrected/'+name))
    (DEST/name).parent.mkdir(parents=True,exist_ok=True)
    (DEST/name).write_text(''.join(after),encoding='utf-8')
(BATCH/'renderer-delta.patch').write_text(''.join(patch),encoding='utf-8')
# Entire snapshot beyond the six listed files must remain byte-identical.
for p in BASE.rglob('*'):
    if p.is_file() and p.relative_to(BASE).as_posix() not in changed:
        assert p.read_bytes()==(DEST/p.relative_to(BASE)).read_bytes(),str(p)
v2.write_json(BATCH/'renderer-source.json',dict(schema='bg2-targeted-renderer-repair-v1',baseline_dll_sha256='70a2745b212babe378c6ccd8b1660110ad3aac5a9ef7523ecbbfcea776bb6d09',baseline_source=str(BASE.relative_to(ROOT)),source=str(DEST.relative_to(ROOT)),changed=changed,delta_sha256=v2.sha256_file(BATCH/'renderer-delta.patch'),scope='BDFORCEW ARE registry, non-dithered binary native visibility; 16px x4 inward continuous coverage; native R/G/B unchanged',other_snapshot_files_identical=True))
print(DEST,flush=True)
