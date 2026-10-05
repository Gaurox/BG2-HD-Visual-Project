"""Complete native MultiNew Q3m x2 K6, bank palettes, contextual 4/9 parts."""
import json,sys,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from q3m_multipart_seams import apply_context
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    selection=load(HERE.parent/'q3m-multi-new-selection-x2-20261005-v1/selection.json')
    selection['scope']='complete native MultiNew; enhanced palette Q3m K6 V7 x2; contextual four/nine parts; no SDF'
    if not (HERE/'selection.json').exists():write_json(HERE/'selection.json',selection)
    assert load(HERE/'selection.json')==selection
    started=time.time();resources,works,plan=source_plan(HERE/'selection.json','multi_new')
    assert (len(resources),plan['physical_frames'],len(works))==(5155,519867,42772)
    assert plan['unique_original_BAM_source_work']==17103 and len(plan['replacement_palettes'])==30
    print(json.dumps(dict(stage='plan',**{k:plan[k] for k in ('resources','physical_frames','unique_source_work','unique_encoded_work')})),flush=True)
    cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';output=ROOT/'sprite/.work'/HERE.name/'isolated'
    assert not output.exists() and not (HERE/'production.json').exists()
    with exclusive(cache):
        namespace=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
        old={p:file_sha(p) for key in works if (p:=cache/'encoded'/namespace/(key+'.npz')).exists()}
        print(json.dumps(dict(stage='retained-base',retained=len(old),total=len(works),encoder=os.environ.get('Q3M_PALETTE_ENCODER','cpu'))),flush=True)
        stats,directory=produce(resources,works,cache)
        assert all(file_sha(p)==s for p,s in old.items())
        base_seconds=time.time()-started;context_started=time.time()
        contextual=apply_context(resources,works,HERE/'selection.json',cache,'run')
        assert contextual['contexts']==5411
        context_seconds=time.time()-context_started;pack_started=time.time()
        packed=pack(resources,works,output)
    # Prior stages completed 30,197 + 107,786 + 101,973 unique base targets.
    # CPU scheduling resume excludes the now-encoded works from pending targets.
    assert stats.get('new_neural_targets',0)==0
    cumulative=dict(new_neural_targets=30197+107786+101973,initial_acquired_encoded_cache_hits=205,retained_special_encoded_work=2241,retained_body_encoded_work=len(old)-2446,completed_new_guides=40943)
    assert cumulative['new_neural_targets']==239956 and cumulative['retained_body_encoded_work']>=0
    from q3m_guarded_gpu_encode import statistics
    acceleration=dict(mode=os.environ.get('Q3M_PALETTE_ENCODER','cpu'),sha256=file_sha(ROOT/'pipeline/scripts/q3m_guarded_gpu_encode.py'),stats=statistics(),benchmark='acceleration-benchmark.json',validation='acceleration-validation.json')
    write_json(HERE/'production.json',dict(plan=plan,stats=stats,cumulative_stats=cumulative,palette_acceleration=acceleration,resumed_for_parallel_CPU_IO=True,CUDA_unused_cache_trim=True,guide_workers=8,target_IO_workers=8,encode_workers=16,context_encode_workers=8,acquired_encoded_sha256_unchanged=len(old),encoder_namespace=directory.name,pack=packed,pack_directory=output.relative_to(ROOT).as_posix(),multipart_context=contextual,seconds=dict(base=base_seconds,context=context_seconds,pack=time.time()-pack_started,total=time.time()-started),SDF=False,ingame_QA=False))
    print(json.dumps(dict(stage='complete',resources=packed['resources'],frames=packed['frames'],stats=stats)),flush=True)
    
if __name__=='__main__':main()

