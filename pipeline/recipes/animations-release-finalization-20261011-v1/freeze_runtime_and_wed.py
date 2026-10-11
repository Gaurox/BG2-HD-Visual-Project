"""Freeze the accepted current renderer and bind unchanged AR0516 WED evidence."""
from prepare import *

def main():
    release_root=ROOT/'releases/BG2-HD-Upscale'
    game=state.game_areas_dir().parents[1]
    tree_runtime=ROOT/'pipeline/recipes/trees-night-color-20261011-v2/runtime.json'
    tree_accept=ROOT/'pipeline/recipes/trees-night-color-20261011-v2/acceptance.json'
    current=load(tree_runtime);accepted=load(tree_accept)
    sha=current['dll_sha256'];dll=ROOT/'backups/renderer/20261011T165415004898Z-3d179d5f/candidate/InfinityEngine-Enhancer.dll'
    assert digest(dll)==sha==v.sha256_file(game/'InfinityEngine-Enhancer.dll')
    assert accepted['renderer_dll_sha256']==sha
    canonical=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
    assert all(digest(canonical/name)==expected for name,expected in current['source_sha256'].items())
    src=release_root/'release-inputs/renderer/iee-0.1.0-alpha.9-source';assert not src.exists()
    src.mkdir(parents=True)
    for item in canonical.iterdir():
        if item.is_file():shutil.copyfile(item,src/item.name)
        elif item.name in {'src','tests','tools','assets','cmake','include'}:shutil.copytree(item,src/item.name)
    parent=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7/.work/runtime-src'
    same=['src/iee/core/planar_sphinct_world_masks.h','src/iee/core/area_occlusion_smoothing.h',
          'src/iee/native_occlusion_bridge.h','src/iee/native_occlusion_bridge.cpp']
    inherited={name:digest(src/name) for name in same}
    assert all(inherited[name]==digest(parent/name) for name in same)
    old_manifest=release_root/'manifests/renderer-bundle.json'
    old=load(old_manifest)
    shutil.copyfile(old_manifest,HERE/'renderer-bundle-before.json')
    shutil.copyfile(release.RUNTIME_COMPATIBILITY,HERE/'runtime-compatibility-before.json')
    snapshot=release_root/'release-inputs/renderer/iee-0.1.0-alpha.9';assert not snapshot.exists()
    old_payload=release_root/'bg2hd/renderer'
    archive=release_root/'archive/renderer-before-alpha6-20261011';assert not archive.exists()
    shutil.copytree(old_payload,archive)
    files=[];provenance=[]
    for entry in old['files']:
        name=entry['path']
        source=(dll if name=='InfinityEngine-Enhancer.dll' else
            src/'tools/InfinityEngine-Enhancer.sample.ini' if name=='InfinityEngine-Enhancer.sample.ini' else game/name)
        assert source.is_file(),source
        destination=snapshot/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        files.append(dict(path=name,bytes=destination.stat().st_size,sha256=digest(destination).upper()))
        provenance.append(dict(path=name,source=str(source),sha256=digest(destination)))
    source_inventory={f.relative_to(src).as_posix():digest(f) for f in src.rglob('*') if f.is_file()}
    write(HERE/'renderer-source-inventory.json',dict(source=rel(src),files=source_inventory,
        inherited_planar_world_mask_sources=inherited,accepted_current_renderer=rel(tree_accept)))
    manifest=copy.deepcopy(old);manifest.update(bundle_id='iee-0.1.0-alpha.9',
        status='integrated-awaiting-clean-lifecycle-test',source_tree=rel(src),files=files)
    manifest['build_environment']['command']='Pinned accepted installed DLL, retained exact source snapshot; source inventory: '+rel(HERE/'renderer-source-inventory.json')
    old_manifest.write_bytes(release.json_bytes(manifest))
    runtime=release.load_json(release.RUNTIME_COMPATIBILITY)
    runtime['renderer']['active_development_install'].update(sha256=sha.upper(),bytes=dll.stat().st_size,
        qa_evidence=rel(tree_accept))
    runtime['renderer']['reproducible_source_build'].update(source=rel(src),output_sha256=sha.upper(),
        output_bytes=dll.stat().st_size,build_status='alpha.9 exact accepted installed DLL and retained source snapshot; clean-game lifecycle remains pending')
    runtime['renderer']['publication_rule']='Alpha.9 preserves acquired animation contracts; publication requires clean-game, future-save and full-uninstall lifecycle gates.'
    release.RUNTIME_COMPATIBILITY.write_bytes(release.json_bytes(runtime))
    sphinct=load(ROOT/'animations/index/qa-decisions/SPHINCT/2026-10-10-accepted-sphinct-planar-final-v1.json')
    installation_path=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7/installation.json'
    installed=load(installation_path)
    assert fresh_payload(PACK/'AR0516')==installed['protected_area_payloads']['AR0516']
    assert 'AR0516' in sphinct['tested_areas'] and sphinct['status']=='accepted'
    registry_sha=digest(PACK/'AR0516'/v.REGISTRY_NAME)
    evidence_path=HERE/'ar0516-wed-acquired-qa-binding.json'
    write(evidence_path,dict(schema='bg2-ar0516-wed-acquired-qa-binding-v1',
        source_qa='animations/index/qa-decisions/SPHINCT/'+sphinct['decision_id']+'.json',
        source_qa_sha256=digest(ROOT/'animations/index/qa-decisions/SPHINCT'/(sphinct['decision_id']+'.json')),
        acquired_qa_date=sphinct['decision_date'],source_installation=rel(installation_path),
        source_installation_sha256=digest(installation_path),registry_sha256=registry_sha,
        source_wed_sha256=installed['ARE_WED_digests_unchanged']['AR0516']['WED'],
        current_payload_equals_acquired_installation=True,current_renderer_sha256=sha,
        inherited_planar_world_mask_sources=inherited,game_mutation=False,new_ingame_qa=False))
    doc=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/docs/validation/ar0516-acquired-release-binding-20261011-v1.md'
    assert not doc.exists()
    doc.write_text('# AR0516 — rattachement des QA acquises pour release\n\n'+
        '- QA explicite conservée : `animations/index/qa-decisions/SPHINCT/'+sphinct['decision_id']+'.json`.\n'+
        '- Reçu installation et WED inchangés ; registre complet `'+registry_sha+'`.\n'+
        '- Preuve hashée : `'+rel(evidence_path)+'`, SHA256 `'+digest(evidence_path)+'`.\n'+
        '- Aucune nouvelle QA ingame ; runtime courant accepté, modules SPHINCT/bridge/masks inchangés. Cycle combiné sur jeu propre encore requis.\n',encoding='utf-8')
    old_spec=ROOT/'maps/wed-corrections/AR0516/lower-sphinct-cover.json'
    spec=copy.deepcopy(load(old_spec));assert digest(game/'override/AR0516.WED')==spec['validated_output']['sha256']
    spec['previous_spec']=dict(path=rel(old_spec),sha256=digest(old_spec))
    spec['qa']['previous_revalidation']=copy.deepcopy(spec['qa']['revalidation'])
    spec['qa']['revalidation'].update(date=sphinct['decision_date'],registry_sha256=registry_sha,
        renderer_dll_sha256=installed['dll_sha256'],evidence=rel(doc))
    new_spec=old_spec.with_name('lower-sphinct-cover-acquired-20261011-v2.json');write(new_spec,spec)
    runtime['renderer']['area_animation_runtime']['native_occlusion_bridge'].update(
        qa_evidence=rel(doc),wed_correction=rel(new_spec))
    release.RUNTIME_COMPATIBILITY.write_bytes(release.json_bytes(runtime))
    with release.workflow_lock():
        candidates=release.load_json(release.CANDIDATES)
        candidate=next(c for c in candidates['candidates'] if c['area']=='AR0516')
        candidate['occlusion_contract'].update(source_spec=rel(new_spec),qa_evidence=rel(doc),
            qa_evidence_sha256=digest(doc).upper())
        release.write_atomic(release.CANDIDATES,release.json_bytes(candidates))
        # Promote this area first: the old pending candidate has an obsolete registry pin.
        plan=release.build_promotion('AR0516',rel(PACK/'AR0516'),'QA acquise 2026-10-10 et WED inchangé ; contrat runtime complet rattaché pour release.')
        changed=release.apply_acceptance(plan)
    write(HERE/'runtime-and-wed-freeze.json',dict(bundle_id=manifest['bundle_id'],files=provenance,
        source_inventory=rel(HERE/'renderer-source-inventory.json'),current_dll_sha256=sha,
        source_acceptance=rel(tree_accept),ar0516_first_promotion=release.public_plan(plan),changed=changed,
        historical_wed_spec_unchanged=digest(old_spec),new_wed_spec=rel(new_spec),game_mutation=False,new_ingame_qa=False))
    print('RENDERER ALPHA.9 FROZEN; AR0516 PROMOTED')

if __name__=='__main__':main()
