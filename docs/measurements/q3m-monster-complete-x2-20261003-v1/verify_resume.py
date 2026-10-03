"""Verify the complete persistent cache resumes without processor/GPU or changed payloads."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_monster import backend_for_run,produce
from palette_monster_work_plan import Cache,WorkPlan,require
from palette_work_plan import file_sha,write_json


def forbidden_processor(*args,**kwargs):
    raise AssertionError('complete resume must not instantiate a processor')


def verify(cache_root,output):
    require(not output.exists(),'new cache verification destination required')
    plan=WorkPlan()
    try:
        resources=plan.resources();cache=Cache(plan,cache_root,backend_for_run(cache_root))
        paths=[cache.path(plan.work(row)) for row in plan.work_rows(resources)]
        before={p.name:file_sha(p) for p in paths}
        stats=produce(plan,resources,cache,processor_factory=forbidden_processor)
        after={p.name:file_sha(p) for p in paths}
        require(len(before)==3190 and before==after and stats==dict(selected_work=3190,cache_hits=3190),
                'resume coverage or payload bytes differ')
        require('torch' not in sys.modules,'CPU resume imported Torch')
        digest=hashlib.sha256(''.join(f'{n} {before[n]}\n' for n in sorted(before)).encode()).hexdigest()
        report=dict(schema='bg2-monster-q3m-complete-cache-resume-v1',status='passed',stats=stats,
                    namespace=cache.namespace,payload_count=len(before),sorted_payload_sha256_digest=digest,
                    payload_bytes_unchanged=True,processor_created=False,torch_imported=False)
        write_json(output,report);print(report)
    finally:plan.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.cache.resolve(),a.output.resolve())
