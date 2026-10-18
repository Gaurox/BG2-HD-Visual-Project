"""Finalize only the33 produced assets; no installation, QA or release inferred."""
from fractions import Fraction
from temporal import ROOT,BATCH,load,save,workflow


def main():
    assets=load(BATCH/'batch.json')['assets'];proof=load(BATCH/'verification.json')
    assert len(assets)==proof['passed']==33 and not proof['failures']
    assert load(BATCH/'review/review.json')['count']==33
    reports=[]
    for a in assets:
        name=a['resref'];v=load(BATCH/'verification'/f'{name}.json')
        assert v['passed'] and v['native_input_keys_unique_before_apollo'] and v['native_palette_normal_alpha_exact']
        assert v['native_pixels_palette_world_geometry_preserved'] and v['straight_alpha_companions_verified']
        run=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run'];m=load(run/'02-interpolation/manifest.json')
        assert load(run/'run.json')['result']['sealed']
        for c in m['timing']['cycles']:
            assert sum(Fraction(*d) for d in c['phase_durations_rational'])==Fraction(*c['duration_rational'])
            if not c['constant_native_cycle']:
                assert not c['adjacent_rgb_duplicates'] and not c['loop_seam_duplicate']
                assert c['unique_rgb']==c['unique_rgba']==c['phase_count']
        reports.append({**load(BATCH/'checks'/f'{name}.json'),'verification':f'verification/{name}.json'})
    result={'schema':'bg2-effects-batch-production-result-v1','status':'completed','completed_utc':workflow.utc_now(),
        'assets_count':33,'resref_count_with_aliases':36,'aliases':load(BATCH/'batch.json')['alias_policy'],
        'source_frames':sum(a['source_frames'] for a in assets),'native_cycles':sum(len(a['native_cycles']) for a in assets),
        'spatial_model':'seedvr2_7b_int8_convrot.safetensors','scale':4,'interpolation_model':'apo-8','target_fps':[30,1],'filter':'NEAREST',
        'native_duplicate_audit':load(BATCH/'native-duplicate-audit.json')['summary'],
        'output_phases_all_independent_profiles':sum(r['phases'] for r in reports),
        'output_profiles':sum(r['cycle_mode_variants'] for r in reports),
        'runtime_pack_raw_bytes':sum(r['raw_bytes'] for r in reports),
        'native_duration_rationals_preserved':True,'unexpected_visible_duplicates':0,
        'alpha_policy':'28 fine assets feather0,5 diffuse feather12; source alpha carried, normal native-palette companions separate from premultiplied defaults',
        'native_timing_basis':'15 FPS compatibility default for native engine owners; no instrumented ingame rate measurement',
        'integration_limits':['once/loop variants retained independently per native cycle/direction',
            'engine tint/blend/owner/rate needs observation at integration; no source-palette preview tint inferred as native tint',
            'BURNHAND and SPPRISM3/SPPRISMT reuse canonical productions'],
        'review':'review/index.html','qa':'pending-user-review','installed':False,'release_changed':False,'assets':reports}
    assert not (BATCH/'production.json').exists()
    save(BATCH/'production.json',result)
    print('33/33 produced and verified;',result['output_phases_all_independent_profiles'],'phases;',result['output_profiles'],'profiles',flush=True)


if __name__=='__main__':main()
