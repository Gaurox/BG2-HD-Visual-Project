"""Render selected closeups from the acquired field; never refit an existing mask."""
import sys,json
import numpy as np
from PIL import Image
from prepare import sources,ROOT,HERE,load
from sdf_trial import catmull,render_reconstructed,composite
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha
from sprite_alpha_coverage import apply
trial=load(HERE/'trial.json')
assert file_sha(HERE/'sdf_trial.py')==trial['processor']['sha256']
record=next(r for r in trial['records'] if r['resref']=='MAKHG1' and r['frame']==25)
field=np.load(ROOT/'sprite/.work/q3m-ankheg-sdf-offline-x2-20261004-v1'/(record['mask_key']+'.npz'))['SDF']
b=sources()['MAKHG1'];r=b['original'];f=r['frames'][25]
raw=r['profile'].decode(f['I'],f['F'],b['palettes'][0]);current=apply(raw,b['current']['frames'][25]['A'])
zoom=6.0
pair=(catmull(np.pad(current,((6,6),(6,6),(0,0))),zoom),render_reconstructed(raw,f['I'],field,zoom))
regions=dict(dos=(48,2,134,36),patte=(42,95,130,130))
for name,roi in regions.items():
    box=tuple(int((v+6)*zoom) for v in roi)
    for label,rgba in zip(('actuel','sdf'),pair):
        im=Image.fromarray(composite(rgba,(119,122,123))).crop(box)
        im.save(HERE/'images'/('detail-'+name+'-'+label+'.png'))
print(json.dumps(dict(details=list(regions),mask_cache_reused=True,zoom=zoom)))
