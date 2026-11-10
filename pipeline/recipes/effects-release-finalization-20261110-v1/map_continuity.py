"""Bind the unchanged acquired water registry to the exact successor DLL."""
import importlib.util
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0,str(Path(__file__).parent))
from build import ROOT, OUT, RELEASE, evidence,load,rel,save,sha


def main():
    dest=OUT/'map-runtime-continuity.json'
    assert not dest.exists()
    old=RELEASE/'release-inputs/renderer/iee-0.1.0-alpha.9-source'
    new=RELEASE/'release-inputs/renderer/iee-0.1.0-alpha.10-source'
    stable=['src/iee/core/water_overlay_policy.h','src/iee/water_route2_registry.h',
            'src/iee/water_textures.cpp','src/iee/water_textures.h','src/iee/game/tile_liquid.h',
            'src/iee/game/area_texture.h','src/iee/area_animation_x4_registry.cpp',
            'src/iee/area_animation_x4_registry.h','src/iee/area_state.h']
    for name in stable: assert sha(old/name)==sha(new/name),name
    a=(old/'src/iee/water_route2_registry.cpp').read_text()
    b=(new/'src/iee/water_route2_registry.cpp').read_text()
    b=re.sub(r'// The exported reference keeps the registry fingerprint.*?\n}\n\n','',b,count=1,flags=re.S)
    assert a==b,'Water runtime implementation changed beyond fingerprint export'
    spec=importlib.util.spec_from_file_location('release_water_generator',ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools/generate_water_route2_registry.py')
    generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)
    runtime=load(RELEASE/'manifests/map-release-assemblies.json')['runtime']
    registry=ROOT/runtime['registry'];dll=RELEASE/'bg2hd/renderer/InfinityEngine-Enhancer.dll'
    contract=generator.verify_dll_contract(dll,registry)
    inputs=OUT/'renderer-build-inputs';inputs.mkdir()
    generated=ROOT/'build/iee-projectile-secondary-links-20261028-v1/generated/iee/water_route2_registry.generated.h'
    shutil.copy2(generated,inputs/generated.name)
    save(inputs/'water-registry-source.json',dict(registry=evidence(registry),current_pointer=evidence(ROOT/'pipeline/water/route2-registry-current.json'),
         generated_header=evidence(inputs/generated.name),build_contract=contract))
    proof=dict(schema='bg2-map-renderer-successor-contract-v1',inherited_from_dll_sha256=runtime['dll_sha256'],
        dll_sha256=sha(dll),registry=evidence(registry),entries=runtime['entries'],build_contract=contract,
        identical_source_files=[dict(path=name,sha256=sha(new/name)) for name in stable],
        water_implementation='Byte-identical source after removing only exported registry fingerprint function.',
        shared_area_resolver='Existing safe loaded-area resolution extracted into game/active_area_runtime.h; exercised by iee_tests.',
        engine_tests=evidence(OUT/'engine-tests.log'),fingerprint_tests=evidence(OUT/'water-contract-tests.log'),
        assets_and_QA_unchanged=True,new_ingame_QA=False,clean_game_combined_lifecycle='pending')
    save(dest,proof)
    compat=load(RELEASE/'manifests/runtime-compatibility.json')
    compat['renderer']['map_water_runtime']=dict(inherited_from_dll_sha256=runtime['dll_sha256'],dll_sha256=sha(dll),
        registry_sha256=runtime['registry_sha256'],build_contract=contract,evidence=evidence(dest))
    save(RELEASE/'manifests/runtime-compatibility.json',compat)
    print(contract)


if __name__=='__main__':main()
