"""Precompute a few distant VVC assets while the serial PRO queue runs.

Do not touch the serial progress journal. Skip any item approached by that
queue; completed immutable reports are reused by its normal resume path.
"""
import time
from temporal import ROOT, BATCH, load, save, produce


def main():
    assets=load(BATCH/'batch.json')['assets'];positions={a['resref']:i for i,a in enumerate(assets)}
    targets=[a for a in assets if 'vvc' in a['owner_routes']]
    progress={}
    for a in targets:
        name=a['resref'];parent=ROOT/'effects/ressources'/name/'runs'/a['spatial_run']/'run.json'
        while not (parent.exists() and load(parent).get('result',{}).get('sealed')):
            time.sleep(3)
        serial=load(BATCH/'temporal-progress.json')
        reached=max([positions[n] for n in serial if n in positions],default=-1)
        if (BATCH/'checks'/f'{name}.json').exists():
            progress[name]={'state':'already-completed'}
        elif reached >= positions[name]-8:
            progress[name]={'state':'left-to-serial-queue'}
        else:
            print('Priority',name,flush=True)
            try:
                produce(a);progress[name]={'state':'completed'}
            except Exception as exc:
                progress[name]={'state':'failed','error':repr(exc)}
                print('Priority failed',name,repr(exc),flush=True)
        save(BATCH/'priority-progress.json',progress)


if __name__=='__main__':main()
