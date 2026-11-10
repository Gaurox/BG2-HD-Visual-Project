"""Write the final immutable result after all release checks complete."""
from common import ROOT, OUT, RELEASE, load, save, evidence, sha


def main():
    dest = ROOT/'docs/validation/effects-shared-storage-status-20261110-v1.json'
    assert not dest.exists(), 'Use a new status version'
    phase2 = (OUT/'phase2.log').read_text(encoding='utf-8-sig')
    assert 'Phase 2 static validation passed:' in phase2
    assert (OUT/'engine-tests.log').read_text(encoding='utf-8-sig').count('Test Passed.') == 5
    assert 'Ran 9 tests' in (OUT/'python-tests-final.log').read_text(encoding='utf-8-sig')
    assert 'INSTALLER_STORAGE_GUARD=PASSED' in (OUT/'installer-guard-package-default.log').read_text(encoding='utf-8-sig')
    projection = load(OUT/'projection-verification.json')
    assert projection['status'] == 'passed'
    for name in projection['mirrored_manifests']:
        assert sha(RELEASE/'manifests'/name) == sha(RELEASE/'bg2hd/manifests'/name), name
    pack = load(OUT/'pack-receipt.json')
    old_size = load(ROOT/'pipeline/recipes/effects-release-finalization-20261110-v1/size-estimate.json')
    size = load(OUT/'size-estimate.json')
    assert size['payload_bytes'] == projection['payload_bytes']
    release = load(RELEASE/'manifests/release.json')
    status = dict(status='implemented-and-locally-verified', version=release['version'],
        renderer=projection['renderer'], logical_frames=pack['logical_frames'],
        physical_rgba_files=pack['physical_frames'], removed_duplicate_rgba_files=pack['removed_files'],
        deduplication='Exact delivered SHA-256/bytes/dimensions only; divergent SeedVR outputs preserved.',
        saved_rgba_bytes=pack['saved_rgba_bytes'], storage_index_bytes=pack['index_bytes'],
        net_frame_storage_saved_bytes=pack['net_frame_storage_saved_bytes'],
        old_payload_bytes=old_size['payload_bytes'], payload_bytes=projection['payload_bytes'],
        net_payload_saved_bytes=old_size['payload_bytes']-projection['payload_bytes'],
        manifest_growth_bytes=pack['net_frame_storage_saved_bytes']-(old_size['payload_bytes']-projection['payload_bytes']),
        payload_files=projection['payload_files'], non_effect_entries_unchanged=projection['non_effect_entries_unchanged'],
        staging=projection['staging'], checks=dict(python_tests=9, engine_suites=5,
            native_phase_contracts=31668, native_loader_metadata_bytes=31785066,
            metadata_budget_bytes=32*1024*1024, release_static='passed', installer_renderer_guard='passed'),
        installer_size_estimate=size, compressed_effect_delta=load(OUT/'archive-delta.json'),
        game_modified=False, new_visual_QA=False,
        ingame_storage_smoke='pending', archive_built=False, public_release='blocked',
        limitations=['Disk storage reduced; RAM/VRAM logical identities retained.',
            'No crop, native BAM sharing or harmonization of divergent neural outputs.',
            'Existing clean-game/save/uninstall lifecycle qualifications remain pending.'],
        evidence=[evidence(p) for p in [OUT/'pack-receipt.json', OUT/'projection-verification.json',
            OUT/'engine-tests.log', OUT/'python-tests-final.log', OUT/'native-loader.log', OUT/'phase2.log',
            OUT/'installer-guard-package-default.log', RELEASE/'manifests/content.json',
            RELEASE/'manifests/renderer-bundle.json']])
    save(dest, status)
    print(dest)


if __name__ == '__main__':
    main()
