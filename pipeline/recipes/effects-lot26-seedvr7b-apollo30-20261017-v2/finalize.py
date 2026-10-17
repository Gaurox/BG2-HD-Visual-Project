"""Summarize the authorized production; no acceptance, installation or release."""
from fractions import Fraction
from temporal import ROOT, BATCH, load, save, digest, workflow


def main():
    assets = load(BATCH / 'batch.json')['assets']
    proof = load(BATCH / 'verification.json')
    assert load(BATCH / 'alpha-coverage-verification.json')['fine_assets'] == 19
    assert load(BATCH / 'alpha-coverage-verification.json')['passed']
    assert len(assets) == proof['passed'] == 26 and not proof['failures']
    reports = []
    for a in assets:
        ref = a['resref']
        v = load(BATCH / 'verification' / f'{ref}.json')
        assert v['passed'] and v['native_input_keys_unique_before_apollo']
        assert v['native_pixels_palette_world_geometry_preserved']
        assert v['native_palette_normal_alpha_exact'] and v['straight_alpha_companions_verified']
        run = ROOT / 'effects/ressources' / ref / 'runs' / a['interpolation_run']
        assert load(run / 'run.json')['result']['sealed']
        m = load(run / '02-interpolation/manifest.json')
        for c in m['timing']['cycles']:
            assert sum(Fraction(*d) for d in c['phase_durations_rational']) == Fraction(*c['duration_rational'])
            if not c['constant_native_cycle']:
                assert not c['adjacent_rgb_duplicates'] and not c['loop_seam_duplicate']
                assert c['unique_rgb'] == c['unique_rgba'] == c['phase_count']
        reports.append({'resref': ref, 'spatial_run': a['spatial_run'],
                        'interpolation_run': a['interpolation_run'], 'pack': a['pack'],
                        'pack_manifest_sha256': v['pack_manifest_sha256'],
                        'verification': f'verification/{ref}.json', 'phases': v['phases'],
                        'profiles': v['cycle_mode_variants'], 'raw_bytes': v['raw_bytes']})
    review = load(BATCH / 'review/review.json')
    assert review['count'] == 26
    assert [a['resref'] for a in review['assets']] == [a['resref'] for a in assets]
    result = {'schema': 'bg2-effects-batch-production-result-v1', 'status': 'completed',
              'refinement':'19 fine/figurative assets retain native alpha coverage (feather0); 7 diffuse effects retain feather12; existing SeedVR/Apollo RGB reused without new neural inference.',
              'completed_utc': workflow.utc_now(), 'assets_count': 26, 'resref_count_with_aliases': 27,
              'aliases': {'SPIPLAAI': ['SPIPLARI']},
              'source_frames': sum(a['source_frames'] for a in assets),
              'native_cycles': sum(len(a['native_cycles']) for a in assets),
              'spatial_model': 'seedvr2_7b_int8_convrot.safetensors', 'scale': 4,
              'interpolation_model': 'apo-8', 'target_fps': [30, 1], 'filter': 'NEAREST',
              'native_duplicate_audit': load(BATCH / 'native-duplicate-audit.json')['summary'],
              'output_phases_all_independent_profiles': sum(r['phases'] for r in reports),
              'output_profiles': sum(r['profiles'] for r in reports),
              'runtime_pack_raw_bytes': sum(r['raw_bytes'] for r in reports),
              'native_duration_rationals_preserved': True, 'unexpected_visible_duplicates': 0,
              'constant_native_cycles_policy': 'Native constant/transparent content retained; no invented motion; TRAPGR static.',
              'alpha_contracts': workflow.file_evidence(ROOT, BATCH / 'alpha-contracts.json'),
              'alpha_coverage_verification': workflow.file_evidence(ROOT, BATCH / 'alpha-coverage-verification.json'),
              'normal_alpha': 'Native palette A1..254; A0/255 opaque compatibility; transparent index authoritative; nearest x4, native temporal fractions, per-asset feather0 for fine silhouettes /12 diffuse. Straight companions separate from premultiplied compatibility primary.',
              'native_timing_basis': {'vvc': '15 FPS source VVC field',
                                      'projectiles': '15 FPS compatibility default; not an ingame cadence measurement'},
              'integration_limits': ['Normal consumers must use straight native-palette companions; Blended uses premultiplied outputs.',
                                     'PRO playback/rate and owner coverage require runtime confirmation.',
                                     'SPIPLARI reuses SPIPLAAI production; alias routing remains an installation task.'],
              'review': 'review/index.html',
              'review_sha256': digest((BATCH / 'review/index.html').read_bytes()),
              'qa': 'pending-user-review', 'installed': False, 'release_changed': False,
              'assets': reports}
    assert not (BATCH / 'production.json').exists(), 'Final production summary is immutable'
    save(BATCH / 'production.json', result)
    readme = BATCH / 'README.md'
    readme.write_text(readme.read_text(encoding='utf-8').replace(
        'État : production en cours.', 'État : 26/26 produits et vérifiés ; galerie native/x4 disponible.'),
        encoding='utf-8', newline='\n')
    print('26/26 produced and verified;', result['output_phases_all_independent_profiles'],
          'phases;', result['output_profiles'], 'profiles; native durations and normal palette alpha preserved.', flush=True)


if __name__ == '__main__':
    main()
