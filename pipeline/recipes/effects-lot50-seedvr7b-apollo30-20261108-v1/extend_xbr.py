"""Additional tiny smoke/particles observed after the first xBR comparison."""
import copy
import json
import time
from xbr_variants import ROOT,BASE,OUT,produce_spatial
from run_temporal import save
import temporal_xbr as temporal
import verify_xbr as verification
import runtime_profiles_xbr as runtime

NAMES={'SPFIRET','FALLMIST','SPSMOLD','SPAGSCHO','ACIDDTH','LAVABUB1','LAVABUB2'}

def main():
    # Initial producer owns progress.json until its original18 complete.
    while not (OUT/'progress.json').exists() or len([r for r in json.loads((OUT/'progress.json').read_text()).values() if r['state']=='completed'])<18:time.sleep(3)
    baseline=json.loads((BASE/'batch.json').read_text(encoding='utf-8'));batch=json.loads((OUT/'batch.json').read_text(encoding='utf-8'))
    existing={a['resref'] for a in batch['assets']}
    for old in baseline['assets']:
        if old['resref'] not in NAMES or old['resref'] in existing:continue
        a=copy.deepcopy(old);n=a['resref'];a.update(seedvr_spatial_run=a['spatial_run'],seedvr_interpolation_run=a['interpolation_run'],
            spatial_run=f'{n.lower()}-xbr4x-nativealpha-20261108-v1',interpolation_run=f'{n.lower()}-xbr4x-apollo30-native-20261108-v1',
            pack=f'effects/ressources/{n}/packs/{n.lower()}-xbr4x-apollo30-initial-20261108-v1',sigma_x4=0)
        batch['assets'].append(a)
    batch['assets_count']=len(batch['assets']);batch['scope_extension']='Tiny smoke, white trails, acid flame and lava droplets: preserve native texture after direct SeedVR contact-sheet inspection; SeedVR alternatives retained.'
    save(OUT/'batch.json',batch)
    temporal.save=verification.save=runtime.save=save
    progress=json.loads((OUT/'progress.json').read_text())
    for a in batch['assets']:
        if a['resref'] not in NAMES:continue
        try:
            produce_spatial(a);temporal.produce(a);verification.verify(a);runtime.build(a);progress[a['resref']]={'state':'completed'}
        except Exception as exc:
            import traceback
            traceback.print_exc();progress[a['resref']]={'state':'failed','error':repr(exc)}
        save(OUT/'progress.json',progress)
    return any(r['state']=='failed' for r in progress.values())

if __name__=='__main__':raise SystemExit(main())
