"""One GPU interpolation worker, isolated from the spatial queue; resumable per asset."""
import time
import traceback
import uuid
import json
import temporal as temporal_module
import verify as verify_module
from temporal import ROOT,BATCH,load,save,produce,workflow
from verify import verify

def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    partial=p.with_name('.'+p.name+'.'+uuid.uuid4().hex+'.partial')
    partial.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for attempt in range(100):
        try:partial.replace(p);return
        except PermissionError:
            if attempt==99:raise
            time.sleep(.1)

temporal_module.save=save
verify_module.save=save

def main():
    import sys
    retry='--retry' in sys.argv
    small='--small' in sys.argv
    journal=BATCH/('small-temporal-progress.json' if small else 'retry-temporal-progress.json' if retry else 'temporal-progress.json');state=load(journal) if journal.exists() else {}
    for a in load(BATCH/'batch.json')['assets']:
        name=a['resref'];parent=ROOT/'effects/ressources'/name/'runs'/a['spatial_run']/'run.json'
        if small and a['recipe_profile'] not in {'X-TINY','A-BUBBLE'}:continue
        if retry and name not in {'WHIRLY','HIHEDGE','SPBASEWT'}:continue
        if (BATCH/'verification'/f'{name}.json').exists():continue
        state[name]={'state':'waiting-spatial'};save(journal,state)
        while not (parent.exists() and load(parent).get('result',{}).get('sealed')):
            sp=load(BATCH/'spatial-progress.json') if (BATCH/'spatial-progress.json').exists() else {}
            if not retry and sp.get(name,{}).get('state')=='failed':break
            time.sleep(3)
        try:
            assert parent.exists() and load(parent).get('result',{}).get('sealed'),'Spatial failed'
            state[name]={'state':'running','started_utc':workflow.utc_now()};save(journal,state)
            produce(a);verify(a)
            state[name].update(state='completed',finished_utc=workflow.utc_now())
        except Exception as exc:
            traceback.print_exc();state[name].update(state='failed',error=repr(exc))
        save(journal,state)
    failures=[n for n,v in state.items() if v['state']=='failed']
    print('Temporal failures:',failures,flush=True)
    return bool(failures)

if __name__=='__main__':raise SystemExit(main())
