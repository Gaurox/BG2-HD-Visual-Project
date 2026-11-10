"""Freeze exact accepted DLL and current retained shader/source files for alpha.8."""
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).parent))
from build import ROOT, OUT, RELEASE, evidence, load, rel, save, sha

SOURCE = ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
BUNDLE = RELEASE/'release-inputs/renderer/iee-0.1.0-alpha.10'
SNAPSHOT = RELEASE/'release-inputs/renderer/iee-0.1.0-alpha.10-source'
EXPECTED_DLL = 'ED9A5E4EE34D695DB84448EE7E9A8E221D39E6DEBD340479F114AD4E9132A844'


def main():
    assert not SNAPSHOT.exists(), 'Frozen source destination already exists'
    old = load(RELEASE/'manifests/renderer-bundle.json')
    compat = load(RELEASE/'manifests/runtime-compatibility.json')
    save(OUT/'renderer-bundle-before.json', old)
    save(OUT/'runtime-compatibility-before.json', compat)
    save(OUT/'release-before.json', load(RELEASE/'manifests/release.json'))
    dll = ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1/candidate/InfinityEngine-Enhancer.dll'
    assert sha(dll) == EXPECTED_DLL
    build_dll = ROOT/'build/iee-projectile-secondary-links-20261028-v1/Release/InfinityEngine-Enhancer.dll'
    assert sha(build_dll) == EXPECTED_DLL
    before = load(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1/before.json')
    for name, digest in before['source_sha256'].items():
        assert sha(SOURCE/name) == digest, name
    for f in old['files']:
        name = f['path']
        if name == 'InfinityEngine-Enhancer.dll': src = dll
        elif name == 'InfinityEngine-Enhancer.sample.ini': src = SOURCE/'tools/InfinityEngine-Enhancer.sample.ini'
        elif name == 'override/M_IEEE.lua': src = RELEASE/'bg2hd/renderer'/name
        elif name.startswith('override/'): src = SOURCE/'assets'/name
        else: src = RELEASE/'bg2hd/renderer'/name
        dest = BUNDLE/name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    display = load(ROOT/'sprite/display-default.json')
    for s in display['shaders']:
        assert sha(ROOT/s['path']) == s['sha256']
        assert sha(BUNDLE/'override'/Path(s['path']).name) == s['sha256']
    # Pin the same cache budget that was qualified with the complete catalogue.
    sample = BUNDLE/'InfinityEngine-Enhancer.sample.ini'
    text = sample.read_text(encoding='utf-8-sig')
    text = text.replace('EnableEffectAnimationX4 = false', 'EnableEffectAnimationX4 = false\nEnableEffectAnimationStreaming = true\nEnableEffectStreamingTrace = false\nEffectCpuCacheMiB = 768\nEffectInFlightMiB = 32\nEffectHeadCacheMiB = 256\nEffectGpuCacheMiB = 288\nEffectMetadataMiB = 32\nEffectMaxResources = 8192')
    sample.write_text(text, encoding='utf-8')
    SNAPSHOT.mkdir(parents=True)
    for p in SOURCE.iterdir():
        if p.is_file() and p.suffix.lower() in ('.txt','.md','.json','.yml','.yaml','.in',''):
            shutil.copy2(p, SNAPSHOT/p.name)
    for name in ['src','tests','tools','licenses','cmake','include']:
        if (SOURCE/name).is_dir():
            shutil.copytree(SOURCE/name, SNAPSHOT/name, ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['override','game-textures']:
        shutil.copytree(SOURCE/'assets'/name, SNAPSHOT/'assets'/name)
    save(OUT/'renderer-source-inventory.json', dict(source=rel(SNAPSHOT),
        files={p.relative_to(SNAPSHOT).as_posix():sha(p) for p in sorted(SNAPSHOT.rglob('*')) if p.is_file()},
        installed_dll=evidence(dll), build_dll=evidence(build_dll),
        build_origin=rel(ROOT/'build/iee-projectile-secondary-links-20261028-v1'),
        source_qualification=evidence(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-residual-four-20261110-v1/before.json'),
        note='Retained corresponding source and exact already-built accepted DLL; no new reproducible binary build claimed. Optional historical media/cache inputs excluded.'))
    files=[dict(path=p.relative_to(BUNDLE).as_posix(), bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(BUNDLE.rglob('*')) if p.is_file()]
    record=dict(old,bundle_id='iee-0.1.0-alpha.10',source_tree=rel(SNAPSHOT),files=files,
        status='integrated-awaiting-clean-lifecycle-test')
    record['build_environment'].update(compiler='MSVC 19.29.30158.0 (v142, toolset 14.29.30133, x64)',command='Retained exact DLL from build/iee-projectile-secondary-links-20261028-v1/Release; source inventory pipeline/recipes/effects-release-finalization-20261110-v1/renderer-source-inventory.json')
    record['validation_required'] += ['Combined accepted effect v3 catalogue, retained native routes and COW bridge on clean game', 'Future native saves/full uninstall with renderer alpha.10']
    # Preserve the previous immutable renderer under its versioned release-inputs path.
    for f in old['files']:
        current = RELEASE/'bg2hd/renderer'/f['path']
        assert sha(current) == f['sha256'], f['path']
    for f in files:
        shutil.copy2(BUNDLE/f['path'],RELEASE/'bg2hd/renderer'/f['path'])
    save(RELEASE/'manifests/renderer-bundle.json',record)
    compat['renderer']['active_development_install'].update(sha256=EXPECTED_DLL,bytes=dll.stat().st_size,
        qa_evidence='projectiles/analysis/residual-four-colours-accepted-20261110-v1/acceptance.json')
    compat['renderer']['reproducible_source_build'].update(source=rel(SNAPSHOT),output_sha256=EXPECTED_DLL,output_bytes=dll.stat().st_size,
        build_status='Exact retained accepted DLL; corresponding source snapshot retained; clean-game combined lifecycle pending.')
    compat['renderer']['publication_rule']='Alpha.10 integrates acquired effect/projectile/sprite-display fixes; clean-game, future-save and full-uninstall lifecycle gates remain required.'
    compat['renderer']['effect_animation_runtime']=dict(status='integrated',registry_version=3,supported_registry_versions=[1,2,3],
        qa_scope='Accepted images and scoped native owner qualifications; no exhaustive gameplay QA or interpolated projectile motion claimed.',
        integration_evidence='pipeline/recipes/effects-release-finalization-20261110-v1/integration.json')
    keys=compat['owned_ini_keys']
    keys['core-steam']['Shaders'].update(EnableEffectAnimationStreaming='true',EnableEffectStreamingTrace='false',
        EffectCpuCacheMiB='768',EffectInFlightMiB='32',EffectHeadCacheMiB='256',EffectGpuCacheMiB='288',EffectMetadataMiB='32',EffectMaxResources='8192')
    for section,values in display['ini'].items():
        if section=='Shaders':
            keys['sprites-approved-creatures-x2'].setdefault(section,{}).update({k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in values.items()})
        else:
            keys['sprites-approved-creatures-x2'][section]={k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in values.items()}
    save(RELEASE/'manifests/runtime-compatibility.json',compat)
    release=load(RELEASE/'manifests/release.json')
    release['version']='0.1.0-alpha.8'
    release['content_scope']['effects']='424 accepted x4 effects plus scoped retained normal/palette variants, native carriers, five native VVC routes, lot31 PRO reference routing and accepted COW sprite bridge; six native masks preserved, 67 exclusions retained.'
    release['content_scope']['sprites'] += ' Display: accepted Nearest RGB / silhouette alpha AA, pinned in renderer alpha.10.'
    release['blocking_conditions'] = list(dict.fromkeys(
        'renderer-alpha.10-effects-projectiles-combined-clean-game-lifecycle-test-pending'
        if value == 'renderer-alpha.9-clean-game-combined-lifecycle-test-pending' else value
        for value in release['blocking_conditions']))
    save(RELEASE/'manifests/release.json',release)
    print('Integrated exact renderer alpha.10 and release alpha.8; public status remains blocked.',flush=True)


if __name__=='__main__': main()
