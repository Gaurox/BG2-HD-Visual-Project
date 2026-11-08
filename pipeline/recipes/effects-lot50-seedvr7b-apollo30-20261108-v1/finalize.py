"""Finalize this production batch only; no game/release writes."""
import csv
from collections import Counter
from temporal import ROOT,BATCH,load,save,workflow

def main():
    batch=load(BATCH/'batch.json');assets=batch['assets'];reports=[]
    tracking={r['asset_key']:r for r in csv.DictReader((ROOT/'effects/index/processing.csv').open(encoding='utf-8-sig',newline=''))}
    for a in assets:
        name=a['resref'];v=load(BATCH/'verification'/f'{name}.json');r=load(BATCH/'runtime-verification'/f'{name}.json')
        assert v['passed'] and r['passed']
        assert r['profiles']==2*sum(bool(c['frame_indices']) for c in a['native_cycles'])
        assert r['phases']==4*sum(len(c['frame_indices']) for c in a['native_cycles'])
        state=tracking['effects:bam:'+name]
        for stage,key in [('spatial','spatial_run'),('interpolation','interpolation_run')]:
            descriptor=ROOT/'effects/ressources'/name/'runs'/a[key]/'run.json'
            assert load(descriptor)['result']['sealed']
        assert not state['selected_run'] and state['qa_state']=='not-assessed'
        assert state['installation_state']=='not-installed' and state['release_state']=='not-evaluated'
        reports.append({**r,'ordinal':a['ordinal'],'profile':a['profile'],'spatial_run':a['spatial_run'],
                        'interpolation_run':a['interpolation_run'],'verification':f'verification/{name}.json',
                        'runtime_verification':f'runtime-verification/{name}.json'})
    assert len(reports)==50 and load(BATCH/'review/review.json')['count']==50
    result=dict(schema='bg2-effects-batch-production-result-v1',status='completed',completed_utc=workflow.utc_now(),
                assets_count=50,source_frames=sum(a['source_frames'] for a in assets),
                source_cycles=sum(len(a['native_cycles']) for a in assets),
                playable_cycles=sum(bool(c['frame_indices']) for a in assets for c in a['native_cycles']),
                output_profiles=sum(r['profiles'] for r in reports),output_phases=sum(r['phases'] for r in reports),
                native_contracts=sum(r['native_contracts'] for r in reports),raw_pack_bytes=sum(r['raw_bytes'] for r in reports),
                profile_counts=dict(Counter(a['profile'] for a in assets)),spatial_model='seedvr2_7b_int8_convrot.safetensors',
                interpolation_model='apo-8',scale=4,target_fps=[30,1],filter='NEAREST',
                native_rate_basis='15FPS compatibility; not measured ingame',
                native_timing='Every native slot at even30FPS phase; adjacent holds and invisible reserves remain at original positions; nonadjacent revisits retained.',
                masks='Source alpha;3green-index border masks derived explicitly; per-asset feather0/2/12 with component thickness cap; no generated alpha.',
                normal_variants='Straight companions all50; neutral-flux companions H15 separate, owner-dependent, not installed.',
                registry_version=3,final_pack_authority='assets[].pack in this file; initial v1 packs are intermediate only',
                empty_cycle_policy='Source/carrier cycles immutable;48trailing empty entries omitted from runtime registry without renumbering playable cycles.',
                review='review/index.html',qa='pending-user-review',installed=False,release_changed=False,assets=reports)
    result['final_pack_authority']='SeedVR baseline archive; current chosen outputs are recorded in production.json after xBR comparisons.'
    assert not (BATCH/'production-seedvr-baseline.json').exists()
    save(BATCH/'production-seedvr-baseline.json',result)
    save(BATCH/'verification.json',dict(passed=50,failures=[],output_phases=result['output_phases'],output_profiles=result['output_profiles'],
                                      native_contracts=result['native_contracts'],assets=[load(BATCH/'verification'/f'{a["resref"]}.json') for a in assets]))
    print('COMPLETE50',result['output_phases'],'phases',result['output_profiles'],'profiles',result['native_contracts'],'native contracts',flush=True)

if __name__=='__main__':main()
