import csv,json,sys,hashlib,zlib
from pathlib import Path
from collections import defaultdict,Counter
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'pipeline/scripts'))
from export_bam_frames import read_bam
from workspace_paths import get_path
G=get_path('bg2ee_game_root');A=G/'iee-assets'
def rows(p):return list(csv.DictReader((R/p).open(encoding='utf-8-sig')))
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(b):return hashlib.sha256(b).hexdigest().upper()
states={r['asset_key'].split(':')[-1]:r for r in rows('effects/index/processing.csv')}
work={r['resref']:r for r in rows('effects/index/work-items.csv')}
remaining=[n for n,s in states.items() if s['spatial_state']=='not-started']
sources=defaultdict(list)
for n,w in work.items():sources[w['canonical_sha256']].append(('effects',n,states[n]['spatial_state']))
for x in rows('animations/index/ressources.csv'):
 n=x['bam_resref'];p=R/'animations/ressources'/n/'source.bam'
 if not p.exists():print('MISSING ANIMSOURCE',n);continue
 key=sha(read_bam(p));sel=R/'animations/index/selections'/f'{n}.json'
 sources[key].append(('animations',n,'selected' if sel.exists() else 'unselected'))
for x in rows('sprite/index/sprite_resources.csv'):sources[x['canonical_sha256']].append(('sprite',x['bam_resref'],x['runtime_relevant']))
OUT=R/'effects/research/remaining183-audit-20261028-v1';OUT.mkdir(parents=True,exist_ok=True)
out=[]
for n in remaining:
 matches=[s for s in sources[work[n]['canonical_sha256']] if s[0]!='effects' or s[1]!=n]
 out.append(dict(resref=n,matches=matches))
(OUT/'cross183.json').write_text(json.dumps(out,indent=2))
for o in out:
 if o['matches']:print(o['resref'],o['matches'])
print('TOTAL matched',sum(bool(o['matches']) for o in out))
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import cycle_metadata
import numpy as np,struct
def visual(p):
 raw=read_bam(p);fs,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr);h=hashlib.sha256()
 h.update(json.dumps(cycle_metadata(raw,len(fs)),sort_keys=True).encode())
 for idx,cx,cy,_ in fs:
  rgba=np.dstack((pal[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
  h.update(struct.pack('<IIii',idx.shape[1],idx.shape[0],cx,cy));h.update(rgba.tobytes())
 return h.hexdigest()
vmap=defaultdict(list)
for n in work:
 p=R/'effects/ressources'/n/'source.bam'
 if p.exists():vmap[visual(p)].append(('effects',n,states[n]['spatial_state']))
for x in rows('animations/index/ressources.csv'):
 n=x['bam_resref'];p=R/'animations/ressources'/n/'source.bam'
 if p.exists():vmap[visual(p)].append(('animations',n,'selected' if (R/'animations/index/selections'/f'{n}.json').exists() else 'unselected'))
for o in out:
 o['visual_matches']=[x for x in vmap[visual(R/'effects/ressources'/o['resref']/'source.bam')] if x[:2]!=('effects',o['resref'])]
 if o['visual_matches']!=o['matches']:print('VISUAL EXTRA',o['resref'],o['visual_matches'])
(OUT/'cross183.json').write_text(json.dumps(out,indent=2))
