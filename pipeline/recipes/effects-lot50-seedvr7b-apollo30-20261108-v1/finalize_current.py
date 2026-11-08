"""Current50 outputs after scoped visual recipe correction; QA remains independent."""
import copy
import csv
from collections import Counter
from temporal import ROOT,BATCH,load,save,workflow
from merged_review import build as publish
import finalize as baseline

ALT=ROOT/'effects/batches/lot50-xbr-small-20261108-v1'

def main():
    original=load(BATCH/'batch.json')['assets'];alternatives={a['resref']:a for a in load(ALT/'batch.json')['assets']}
    assert len(alternatives)==25
    if not (BATCH/'production-seedvr-baseline.json').exists():baseline.main()
    records=[];proofs=[]
    states={r['asset_key']:r for r in csv.DictReader((ROOT/'effects/index/processing.csv').open(encoding='utf-8-sig',newline=''))}
    for source in original:
        name=source['resref'];a=alternatives.get(name,source);directory=ALT if name in alternatives else BATCH
        r=load(directory/'runtime-verification'/f'{name}.json');v=load(directory/'verification'/f'{name}.json')
        assert r['passed'] and v['passed'];state=states['effects:bam:'+name]
        assert state['spatial_run']==a['spatial_run'] and state['interpolation_run']==a['interpolation_run']
        assert not state['selected_run'] and state['qa_state']=='not-assessed' and state['installation_state']=='not-installed'
        model='xBR4X' if name in alternatives else 'SeedVR7B'
        records.append({**r,'ordinal':a['ordinal'],'model':model,'profile':a['profile'],
                        'spatial_run':a['spatial_run'],'interpolation_run':a['interpolation_run'],
                        'source':a['source'],'source_sha256':a['source_sha256'],
                        'verification':(directory/'verification'/f'{name}.json').relative_to(ROOT).as_posix(),
                        'runtime_verification':(directory/'runtime-verification'/f'{name}.json').relative_to(ROOT).as_posix()})
        proofs.append(v)
    assert sum(r['phases'] for r in records)==5164 and sum(r['profiles'] for r in records)==150
    assert publish(final=True)==(50,25)
    result=copy.deepcopy(load(BATCH/'production-seedvr-baseline.json'))
    result.update(completed_utc=workflow.utc_now(),assets=records,spatial_model='per-asset:SeedVR7B or xBR4X',
                  model_counts=dict(Counter(r['model'] for r in records)),
                  raw_pack_bytes=sum(r['raw_bytes'] for r in records),native_contracts=sum(r['native_contracts'] for r in records),
                  final_pack_authority='assets[].pack in this file; SeedVR baseline and initial packs retained separately',
                  visual_recipe_revision='25small motifs use xBR4X after direct observation of invented glyphs/lines in SeedVR results; all50SeedVR runs retained, comparison toggle available.',
                  review='review/index.html',alternative_seedvr_baseline='production-seedvr-baseline.json')
    assert not (BATCH/'production.json').exists();save(BATCH/'production.json',result)
    save(BATCH/'verification-current.json',dict(passed=50,failures=[],models=result['model_counts'],profiles=150,phases=5164,
                                               native_contracts=result['native_contracts'],assets=proofs,qa='pending-user-review',installed=False))
    save(ALT/'production.json',dict(status='completed',assets_count=25,assets=[r for r in records if r['model']=='xBR4X'],
                                  reason=result['visual_recipe_revision'],qa='pending-user-review',installed=False))
    print('CURRENT50 COMPLETE',result['model_counts'],result['native_contracts'],'native contracts',flush=True)

if __name__=='__main__':main()
