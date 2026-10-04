"""Seal two-ID runtime delta after native and GPU checks."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
assert load(HERE/'verification.json')['passed'] and load(HERE/'gpu-verification.json')['passed']
assert not (HERE/'runtime.json').exists()
prior=ROOT/'docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1/runtime.json';inherited=load(prior)
dll=WORK/'runtime-build/Release/InfinityEngine-Enhancer.dll'
write_json(HERE/'runtime.json',dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id=HERE.name,inherited_runtime=identity(prior),base_commit='16b01e52',capability_delta=dict(V9_native_palette_kinds=[0,1],registry_profiles=[8,9],decode_rule=3,only_new_SDF_ids=['0x6405','0x6406']),dll=identity(dll),source_provenance=[identity(WORK/'runtime-src/src/iee'/n) for n in ('creature_sprite_x2.cpp','creature_sprite_x2.h','hooks.cpp')],runtime_patch=identity(HERE/'runtime-delta.patch'),shaders=inherited['shaders'],verification=identity(HERE/'verification.json'),GPU=identity(HERE/'gpu-verification.json'),ingame_QA=False,release=False))
gen=load(HERE/'current-generation.json');gen.update(runtime=identity(HERE/'runtime.json'),dll=identity(dll));write_json(HERE/'current-generation.json',gen)
print(json.dumps(dict(sealed=True,dll=gen['dll']['sha256'],catalog=gen['catalog']['sha256'])))
