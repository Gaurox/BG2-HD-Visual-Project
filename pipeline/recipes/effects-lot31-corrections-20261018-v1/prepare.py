"""Explicit correction trial; original31 productions and unrelated work stay intact."""
from pathlib import Path
import copy,json,sys,time,os,threading

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
BASE=ROOT/'effects/batches/lot31-projectiles-7b-apollo30-20261018-v1'
OUT=ROOT/'effects/batches/lot31-corrections-preview-20261018-v1'
REBOUT={1,2,3,4,5,6,7,15,23,26}
MASK={8,9,10,11,13,16,17,18,19,21,22,27,31}
TIMING={12,20,30}
SMOOTH=REBOUT|MASK|{30}
BLACK={12,14,20}
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_name('.'+p.name+f'.{os.getpid()}.{threading.get_ident()}.partial')
    temp.write_bytes(workflow.json_bytes(v))
    for attempt in range(100):
        try:temp.replace(p);return
        except PermissionError:
            if attempt==99:raise
            time.sleep(.05)

def main():
    assert not (OUT/'plan.json').exists(),'new version required'
    b=load(BASE/'batch.json');jobs=[]
    for old in b['jobs']:
        a=copy.deepcopy(old);n=a['ordinal']
        a.update(rebout=n in REBOUT,smooth=n in SMOOTH,retime=n in TIMING,black_neutral=n in BLACK)
        a['changed']=any(a[k] for k in ('rebout','smooth','retime','black_neutral'))
        jobs.append(a)
    save(OUT/'plan.json',{'schema':'bg2-effects-correction-trial-v1','parent':str(BASE.relative_to(ROOT)/'production.json'),
        'authorization':'User requested listed ReboutCX/mask/timing/black-transparency corrections; no install or acceptance requested.',
        'groups':{'rebout_and_mask':sorted(REBOUT),'mask_only':sorted(MASK),'timing':sorted(TIMING),'black_neutral':sorted(BLACK)},
        'jobs':jobs,'assets':b['assets'],'changed_assets':27,'changed_contexts':sum(a['changed'] for a in jobs),
        'native_timing_fix':'Preserve native clock anchors and invisible terminal holds; remove adjacent repeated inputs, never spread visible motion across blank reserve.',
        'mask':'Native Potrace alphamax1.334/SS8 before phase mixing, Gaussian edge alpha capped4x4 and reduced on thin parts; RGB preserved for mask-only edits.',
        'black':'Anew=round(A*max(RGB)/255), straight RGB renormalized; emissive premultiplied RGB energy preserved to rounding.'})
    print('Prepared27 assets/95 contexts;41 ReboutCX contexts; unchanged24,25,28,29',flush=True)

if __name__=='__main__':main()
