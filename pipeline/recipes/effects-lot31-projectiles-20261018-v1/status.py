"""Compact local progress; does not touch production or network."""
from pathlib import Path
import collections
import json

BATCH=Path(__file__).resolve().parents[3]/'effects/batches/lot31-projectiles-7b-apollo30-20261018-v1'
for stage in ('spatial','temporal'):
    p=BATCH/(stage+'-progress.json')
    if not p.exists():continue
    state=json.loads(p.read_text(encoding='utf-8-sig'))
    print(stage,dict(collections.Counter(v['state'] for v in state.values())))
    print('running:',','.join(k for k,v in state.items() if v['state']=='running'))
    for key,value in state.items():
        if value['state']=='failed':print('FAILED',key,value.get('error'))
for stage in ('verification','review'):
    if stage=='verification':
        files=list((BATCH/stage).glob('*.json'))
        print('verified contexts',len(files))
        proof=BATCH/'verification.json'
        if proof.exists():print('verification failures',json.loads(proof.read_text(encoding='utf-8-sig'))['failures'])
    else:
        proof=BATCH/'review/review.json'
        if proof.exists():
            v=json.loads(proof.read_text(encoding='utf-8-sig'));print('review',v['count'],'BAMs',v['contexts'],'palettes')
