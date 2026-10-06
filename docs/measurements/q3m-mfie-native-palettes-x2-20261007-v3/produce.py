"""Correct only MFIE's native bank palettes; reuse immutable Q3m cache hits."""
import json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1')]
from q3m_family_witnesses import source_plan,produce,pack,exclusive
from palette_work_plan import file_sha,write_json
from q3m_guarded_gpu_encode import statistics
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def main():
    started=time.time();assert not(HERE/'production.json').exists()
    resources,works,plan=source_plan(HERE/'selection.json','monster',animation_ids=['0x7314'])
    assert len(resources)==14 and plan['physical_frames']==5888
    cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';namespace=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
    with exclusive(cache):
        hits={p:file_sha(p) for k in works if (p:=cache/'encoded'/namespace/(k+'.npz')).exists()}
        print(json.dumps(dict(stage='plan',resources=14,frames=5888,encoded_work=len(works),hits=len(hits),missing=len(works)-len(hits))),flush=True)
        stats,directory=produce(resources,works,cache)
        assert all(file_sha(p)==sha for p,sha in hits.items()),'acquired cache hit modified'
        write_json(HERE/'encoding.json',dict(plan=plan,stats=stats,encoder_namespace=directory.name,acquired_hits_verified=len(hits),
            encoded_directory=directory.relative_to(ROOT).as_posix(),palette_acceleration=statistics()))
        output=WORK/'isolated';assert not output.exists()
        result=pack(resources,works,output)
    write_json(HERE/'production.json',dict(scope=['0x7314'],plan=plan,stats=stats,pack=result,pack_directory=output.relative_to(ROOT).as_posix(),
        seconds=time.time()-started,other_ids_unchanged=True,installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='complete',resources=14,frames=5888,stats=stats)),flush=True)
if __name__=='__main__':main()
