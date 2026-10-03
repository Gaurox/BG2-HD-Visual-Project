"""Phase 5: complete the three Monster families using the acquired recipe/cache; no installation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_monster import backend_for_run,produce
from palette_monster_work_plan import Cache,WorkPlan,require
from palette_work_plan import write_json


def main(cache_root,output):
    require(not output.exists(),'new production report directory required')
    output.mkdir(parents=True)
    plan=WorkPlan()
    try:
        cache=Cache(plan,cache_root,backend_for_run(cache_root))
        for animation in ('0x7F30','0x7F07','0x7F02'):
            resources=plan.resources(ids=[animation]);started=time.monotonic()
            print(json.dumps(dict(starting=animation,resources=len(resources),cache_namespace=cache.namespace)),flush=True)
            stats=produce(plan,resources,cache,workers=4)
            record=dict(animation_id=animation,resources=[r['resref'] for r in resources],stats=stats,
                        cache_namespace=cache.namespace,elapsed_seconds=time.monotonic()-started,
                        neural_targets=stats.get('model_work',0)*6,status='encoded-not-assembled-or-ingame-QA')
            write_json(output/(animation+'.json'),record)
            print(json.dumps(record),flush=True)
    finally: plan.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.cache.resolve(),a.output.resolve())
