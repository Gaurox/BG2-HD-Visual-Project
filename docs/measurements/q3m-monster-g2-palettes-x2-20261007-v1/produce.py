"""Finish only native G2 palette fixes7312/7313; keep compatible cache immutable."""
import json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1')]
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from palette_work_plan import file_sha,write_json
from q3m_guarded_gpu_encode import statistics,MODE
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    started=time.time();assert not(HERE/'production.json').exists()
    assert os.environ.get('Q3M_PALETTE_ENCODER','cpu') in ('cpu',MODE),'unknown palette encoder mode'
    selection=HERE.parent/'q3m-monster-final-checks-x2-20261007-v1/correction-selection.json'
    resources,works,plan=source_plan(selection,'monster',animation_ids=['0x7312','0x7313'])
    assert len(resources)==27 and plan['physical_frames']==11774
    cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';namespace=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
    with exclusive(cache):
        hits={p:file_sha(p) for k in works if (p:=cache/'encoded'/namespace/(k+'.npz')).exists()}
        print(json.dumps(dict(stage='plan',resources=27,frames=11774,encoded_work=len(works),hits=len(hits),missing=len(works)-len(hits))),flush=True)
        stats,directory=produce(resources,works,cache)
        assert all(file_sha(p)==sha for p,sha in hits.items()),'acquired cache hit modified'
        write_json(HERE/'encoding.json',dict(plan=plan,stats=stats,encoder_namespace=directory.name,acquired_hits_verified=len(hits),
            encoded_directory=directory.relative_to(ROOT).as_posix(),palette_acceleration=statistics()))
        output=WORK/'isolated';assert not output.exists()
        result=pack(resources,works,output)
    write_json(HERE/'production.json',dict(scope=['0x7312','0x7313'],plan=plan,stats=stats,pack=result,pack_directory=output.relative_to(ROOT).as_posix(),
        seconds=time.time()-started,other_ids_unchanged=True,runtime_changed=False,installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='complete',resources=27,frames=11774,stats=stats)),flush=True)
if __name__=='__main__':main()
