"""Two bounded interpolation workers; independent assets, one progress writer."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
from temporal import ROOT, BATCH, load, save, produce, workflow, jobkey


def main():
    assets=load(BATCH/'batch.json')['jobs']
    journal=BATCH/'temporal-progress.json'
    state=load(journal) if journal.exists() else {}
    lock=threading.Lock()

    def update(name, **values):
        with lock:
            state.setdefault(name,{}).update(values)
            save(journal,state)

    def work(a):
        name=jobkey(a);resref=a['resref']
        try:
            if (BATCH/'checks'/f'{name}.json').exists():
                update(name,state='completed');return name,True
            update(name,state='waiting-spatial')
            parent=ROOT/'effects/ressources'/resref/'runs'/a['spatial_run']/'run.json'
            deadline=time.monotonic()+21600
            while not (parent.exists() and load(parent).get('result',{}).get('sealed')):
                spatial=load(BATCH/'spatial-progress.json')
                if spatial.get(name,{}).get('state')=='failed':raise RuntimeError('spatial failed')
                if time.monotonic()>deadline:raise RuntimeError('spatial wait timeout')
                time.sleep(3)
            update(name,state='running',started_utc=workflow.utc_now(),error=None)
            print('Interpolation',name,flush=True)
            produce(a)
            update(name,state='completed',finished_utc=workflow.utc_now())
            return name,True
        except Exception as exc:
            update(name,state='failed',error=repr(exc))
            print('FAILED',name,repr(exc),flush=True)
            return name,False

    results=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in as_completed([pool.submit(work,a) for a in assets]):results.append(future.result())
    failures=[name for name,ok in results if not ok]
    print('Interpolation complete; failures:',failures,flush=True)
    return bool(failures)


if __name__=='__main__':raise SystemExit(main())
