"""Complete only this production batch; QA/installation/release remain separate."""
from fractions import Fraction
from temporal import ROOT,BATCH,load,save,workflow,jobkey


def main():
    batch=load(BATCH/'batch.json');jobs=batch['jobs'];assets=batch['assets']
    proof=load(BATCH/'verification.json');pal=load(BATCH/'palette-verification.json')
    assert len(assets)==31 and len(jobs)==proof['passed']==pal['contexts']==99
    assert not proof['failures'] and pal['native_rgb_exact']
    inputs=load(BATCH/'input-palette-alpha-verification.json')
    assert inputs['passed'] and inputs['contexts']==99 and inputs['actual_model_rgb_matches_native_palette']
    review=load(BATCH/'review/review.json')
    assert review['count']==31 and review['contexts']==99
    reports=[];bindings=[]
    for a in jobs:
        v=load(BATCH/'verification'/f'{jobkey(a)}.json')
        assert v['passed'] and v['palette_context_exact_at_input']
        assert v['native_pixels_palette_world_geometry_preserved'] and v['native_palette_normal_alpha_exact']
        run=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']
        assert load(run/'run.json')['result']['sealed']
        spatial=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']
        palette_sha=workflow.sha256_file(ROOT/a['palette_file'])
        assert load(spatial/'recipe.json')['palette_context']['sha256']==palette_sha
        assert load(run/'recipe.json')['palette_context']['sha256']==palette_sha
        bindings.append({'resref':a['resref'],'job_id':jobkey(a),'primary_for_review':a['primary'],
            'palette_file':a['palette_file'],'palette_file_sha256':palette_sha,'pack':a['pack'],
            'consumers':a['consumers'],'runtime_route':'not-installed; explicit palette/owner dispatch required'})
        m=load(run/'02-interpolation/manifest.json')
        for c in m['timing']['cycles']:
            assert sum(Fraction(*d) for d in c['phase_durations_rational'])==Fraction(*c['duration_rational'])
            if not c['constant_native_cycle']:
                assert not c['adjacent_rgb_duplicates'] and not c['loop_seam_duplicate']
                assert c['unique_rgb']==c['unique_rgba']==c['phase_count']
        reports.append(load(BATCH/'checks'/f'{jobkey(a)}.json'))
    save(BATCH/'palette-bindings.json',{'schema':'bg2-effects-palette-bindings-v1','assets':31,
        'contexts':len(bindings),'bindings':bindings,
        'policy':'Primary denotes review/index choice only; never select it unconditionally for every native owner.'})
    result={'schema':'bg2-effects-palette-batch-production-result-v1','status':'completed',
        'completed_utc':workflow.utc_now(),'assets_count':31,'palette_contexts':99,
        'source_frames':sum(a['source_frames'] for a in assets),
        'native_cycles':sum(len(a['native_cycles']) for a in assets),
        'spatial_model':'seedvr2_7b_int8_convrot.safetensors','scale':4,
        'interpolation_model':'apo-8','target_fps':[30,1],'filter':'NEAREST',
        'native_duplicate_audit':load(BATCH/'native-duplicate-audit.json')['summary'],
        'output_phases_all_independent_profiles':sum(r['phases'] for r in reports),
        'output_profiles':sum(r['cycle_mode_variants'] for r in reports),
        'runtime_pack_raw_bytes':sum(r['raw_bytes'] for r in reports),
        'native_duration_rationals_preserved':True,'unexpected_visible_duplicates':0,
        'alpha_policy':'Native index/graded palette alpha, per-phase reconstruction, no erosion/feather; premultiplied and straight encodings retained.',
        'palette_policy':'All99 distinct full RGB palettes of known PRO/VVC consumers realized before SeedVR; native mixing verified; source indexed BAMs/carrier palettes unchanged.',
        'integration_limits':['Palette variants are separate packs; native owner/palette dispatch remains to integrate before ingame tests.',
            'VVC source FPS where present, otherwise15FPS compatibility default; no actual runtime rate measurement.',
            'No fixed-color universal replacement for palette-dependent BAMs; runtime tint/blend remains consumer-specific.'],
        'palette_bindings':'palette-bindings.json',
        'review':'review/index.html','qa':'pending-user-review','installed':False,'release_changed':False,'jobs':reports}
    assert not (BATCH/'production.json').exists()
    save(BATCH/'production.json',result)
    print('31/31 produced;',len(jobs),'palettes;',result['output_phases_all_independent_profiles'],'phases;',result['output_profiles'],'profiles')


if __name__=='__main__':main()
