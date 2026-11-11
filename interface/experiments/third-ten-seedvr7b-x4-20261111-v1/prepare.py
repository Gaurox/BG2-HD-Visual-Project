"""Prepare native MOS compositions for a matched SeedVR2 7B x4 batch."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
if (HERE/'sources.json').exists():raise SystemExit('Existing source manifest; use a new run.')
proposal=json.loads((ROOT/'interface/analysis/third-ten-20261111-v1/proposal.json').read_text(encoding='utf-8'))
template=json.loads((ROOT/'interface/experiments/menus-seedvr-x4-7b-3b-20261110-v1/workflows/INVENTOR-7b-x4.api.json').read_text())
for folder in ['sources','inputs','workflows','outputs','comparison','jobs']:(HERE/folder).mkdir(exist_ok=True)
rows=[]
for item in proposal['items']:
 n=item['resref'];source=ROOT/'interface/analysis/large-surfaces-20261110-v1/previews'/f'{n}.png';im=Image.open(source).convert('RGBA');w,h=im.size;pw=(w+63)//64*64;ph=(h+63)//64*64
 src=HERE/'sources'/f'{n}-x1.png';im.save(src);inputname=f'UI30-20261111-{n}-padded.png';Image.fromarray(np.pad(np.array(im),((0,ph-h),(0,pw-w),(0,0)),mode='edge')).save(HERE/'inputs'/inputname)
 workflow=json.loads(json.dumps(template));workflow['1']['inputs']['image']=inputname;workflow['9']['inputs']['filename_prefix']=f'BG2_UI30_7B_20261111/{n}-7b-x4';(HERE/'workflows'/f'{n}-7b-x4.api.json').write_text(json.dumps(workflow,indent=2)+'\n',encoding='utf-8')
 rows.append(dict(**item,native_size=[w,h],padded_size=[pw,ph],expected_x4=[w*4,h*4],source_sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
(HERE/'sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('Prepared',len(rows),'complete native MOS compositions')
