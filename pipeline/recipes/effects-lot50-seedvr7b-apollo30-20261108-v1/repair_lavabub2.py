"""New temporal versions for distinct frame records encoding identical blank holds."""
import importlib
import time
from temporal import ROOT,BATCH,load
from run_temporal import save

ALT=ROOT/'effects/batches/lot50-xbr-small-20261108-v1'

def main():
    # Avoid competing production/index writers on the same BAM.
    while load(BATCH/'temporal-progress.json').get('SPOUTA',{}).get('state') not in {'completed','failed'}:time.sleep(3)
    while load(ALT/'progress.json').get('LAVABUB2',{}).get('state') not in {'completed','failed'}:time.sleep(3)
    for directory,module_name,verify_name in [(BATCH,'temporal','verify'),(ALT,'temporal_xbr','verify_xbr')]:
        batch=load(directory/'batch.json');a=next(a for a in batch['assets'] if a['resref']=='LAVABUB2')
        if a['interpolation_run'].endswith('-v1'):
            old=dict(a);save(directory/'lavabub2-initial-plan.json',old)
            a['interpolation_run']=a['interpolation_run'][:-3]+'-v2'
            a['pack']=a['pack'][:-3]+'-v2'
            save(directory/'batch.json',batch)
        temporal=importlib.import_module(module_name);verification=importlib.import_module(verify_name)
        temporal.save=verification.save=save
        temporal.workflow.register_run(ROOT,'LAVABUB2','spatial',a['spatial_run'],write=True)
        temporal.produce(a);verification.verify(a)
        if directory==ALT:
            import runtime_profiles_xbr as runtime
            runtime.save=save;runtime.build(a)
        journal=directory/('temporal-progress.json' if directory==BATCH else 'progress.json')
        progress=load(journal);progress['LAVABUB2']={'state':'completed','repaired_with_new_run':a['interpolation_run']};save(journal,progress)
    print('LAVABUB2 repaired in new versions; original failed runs retained.',flush=True)

if __name__=='__main__':main()
