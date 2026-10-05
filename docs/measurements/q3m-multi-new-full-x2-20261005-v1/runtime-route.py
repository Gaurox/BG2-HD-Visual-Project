"""Verify both owner-5 native renderers against acquired executable/runtime."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_oracle import pe_rva
from workspace_paths import get_path
from palette_work_plan import file_sha,write_json
game=get_path('bg2ee_game_root',required=True);raw=(game/'BaldurReal.exe').read_bytes()
parent=json.loads((HERE.parent/'q3m-monster-old-full-x2-20261004-v1/current-generation.json').read_text())
assert file_sha(game/'InfinityEngine-Enhancer.dll')==parent['dll']['sha256']
base=ROOT/'sprite/.work/q3m-monster-quadrant-full-x2-20261004-v1/runtime-src'
manifest=(base/'src/iee/game/build_manifest.cpp').read_text()
routes=[]
for name,render,vtable,prefix in [('MonsterMulti',0x32f8d0,0x5aa270,'40 55 53 56 57 41 54 41 55 41 57 48 8D 6C 24 F9'),('MultiNew',0x32fd20,0x5ab000,'40 55 53 56 41 56 41 57 48 8D 6C 24 F9')]:
    assert pe_rva(raw,render,len(bytes.fromhex(prefix)))==bytes.fromhex(prefix)
    pointer=struct.unpack('<Q',pe_rva(raw,vtable+0x130,8))[0]
    imagebase=struct.unpack_from('<Q',raw,struct.unpack_from('<I',raw,0x3c)[0]+48)[0]
    assert pointer-imagebase==render,(name,hex(pointer-imagebase))
    assert hex(render)[2:].upper() in manifest
    routes.append(dict(native_path=name,render_RVA=hex(render),vtable_RVA=hex(vtable),render_slot='0x130',render_prefix_sha256=hashlib.sha256(pe_rva(raw,render,64)).hexdigest()))
write_json(HERE/'runtime-route.json',dict(passed=True,owner=5,native_family='multi_new',routes=routes,game_executable_sha256=hashlib.sha256(raw).hexdigest(),existing_runtime=(base/'src/iee/game/build_manifest.cpp').relative_to(ROOT).as_posix(),existing_DLL_unchanged=True))
print(json.dumps(dict(passed=True,native_paths=2,DLL_unchanged=True)))
