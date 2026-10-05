"""Record a runtime-only successor to the immutable MultiNew production."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json, file_sha
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
ref=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
parent=ROOT/'docs/measurements/q3m-multi-new-full-x2-20261005-v1'
gen=load(parent/'current-generation.json'); verification=load(HERE/'verification.json')
assert verification['passed'] and verification['fixed']['cold_native_fallback_groups']==0
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
dll=WORK/'runtime-build/Release/InfinityEngine-Enhancer.dll'
write_json(HERE/'runtime.json',dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id=HERE.name,
    inherited_runtime=gen['runtime'],dll=ref(dll),runtime_patch=ref(HERE/'runtime-delta.patch'),
    source_provenance=[ref(WORK/'runtime-src'/name) for name in (
        'src/iee/creature_sprite_x2.cpp','src/iee/creature_sprite_x2.h','src/iee/hooks.cpp')],
    capability_delta=dict(owner=5,animation_ids=gen['animation_ids'],
        exact_current_group_prefetch=True,authenticated_V2_resource_metadata_wait=True,
        load_timeout_seconds=5,frame_payloads_lazy=True,native_fail_closed_retained=True,
        unchanged_non_owner5_lookup_modes=True),verification=ref(HERE/'verification.json'),ingame_QA=False,release=False))
gen.update(parent_generation=ref(parent/'current-generation.json'),runtime=ref(HERE/'runtime.json'),
           dll=ref(dll),DLL_unchanged=False,assets_unchanged=True,
           unchanged_asset_installation='docs/measurements/'+parent.name+'/ingame-installation/active-test.json')
write_json(HERE/'current-generation.json',gen)
preserved=[dict(relative_path=name,sha256=file_sha(game/name)) for name in (
    'iee-assets/creature-sprites/CreatureSprites-XN.catalog','InfinityEngine-Enhancer.ini',
    'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl','BaldurReal.exe')]
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',
    dll_sha256=load(parent/'current-generation.json')['dll']['sha256'],preserved=preserved,
    inherited_asset_installation=gen['unchanged_asset_installation']))
print('Prepared runtime-only installation; catalog and sprite payloads unchanged.')
