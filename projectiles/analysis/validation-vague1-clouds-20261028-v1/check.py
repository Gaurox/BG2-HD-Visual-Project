"""Freeze wave1 observations; verify existing corrected cloud variants, no image writes."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
GAME=get_path('bg2ee_game_root',required=True)
if (OUT/'evidence.json').exists():raise SystemExit('Existing evidence: new version required')
def sha(raw):return hashlib.sha256(raw).hexdigest().upper()
raw=(GAME/'InfinityEngine-Enhancer.log').read_bytes();all_lines=raw.splitlines(keepends=True)
start=max(i for i,l in enumerate(all_lines) if b'Infinity Engine Enhancer initializing...' in l)
snapshot=b''.join(all_lines[start:]);(OUT/'runtime-session.log').write_bytes(snapshot)
lines=snapshot.decode('utf-8',errors='replace').replace('\0','').splitlines()
refs=('SPCLOUDS','SPDFOGA','SPINCINA','SPHORWIL','SPHORWIA')
events={n:[dict(line=i+1,text=l) for i,l in enumerate(lines) if f'resref={n} ' in l and
 ('EFX_' in l)] for n in refs}
m=json.loads((GAME/'iee-assets/effects/manifest.json').read_text());catalog={r['resref']:r for r in m['resources']}
carriers={r['resref']:r for r in m['runtime_bam_carriers']}
pairs=[]
for native,corrected in [('SPCLOUDS','X58CLS'),('SPDFOGA','X58DFOG'),('BDWOFOGA','X58WFOG')]:
 a=catalog[native];b=catalog[corrected]
 mismatches=[field for field in ('cycles','timeline','frame_count','production_bam','rgb_encoding') if a[field]!=b[field]]
 if mismatches:
  pairs.append(dict(native=native,corrected=corrected,eligible=False,contract_mismatches=mismatches))
  continue
 old=sorted([f for f in m['frames'] if f['resref']==native],key=lambda f:f['resource_frame'])
 new=sorted([f for f in m['frames'] if f['resref']==corrected],key=lambda f:f['resource_frame'])
 assert len(old)==len(new)==a['frame_count']
 changed=0;total=0;sample={}
 for i,(x,y) in enumerate(zip(old,new)):
  for k in ('resource_frame','bytes','logical_size_x1','physical_size_x4','source_centre_x1'):assert x[k]==y[k],(native,i,k)
  xr=(GAME/'iee-assets/effects'/x['asset']).read_bytes();yr=(GAME/'iee-assets/effects'/y['asset']).read_bytes()
  assert sha(xr)==x['sha256'].upper() and sha(yr)==y['sha256'].upper(),(native,i)
  xp=np.frombuffer(xr,dtype=np.uint8).reshape(-1,4);yp=np.frombuffer(yr,dtype=np.uint8).reshape(-1,4)
  assert np.array_equal(xp[:,:3],yp[:,:3]),(native,i)
  changed+=int(not np.array_equal(xp[:,3],yp[:,3]));total+=len(xr)+len(yr)
  if i==len(old)//2:
   support=xp[:,3]>0
   sample=dict(frame=i,old_alpha_median=float(np.median(xp[support,3])),new_alpha_median=float(np.median(yp[support,3])))
 assert (GAME/carriers[native]['asset']).read_bytes()==(GAME/carriers[corrected]['asset']).read_bytes()
 pairs.append(dict(native=native,corrected=corrected,eligible=True,frames=len(old),bytes_checked=total,
  all_SHA_RGB_geometry_cycles_timeline_encoding_carriers_ok=True,alpha_changed_frames=changed,sample=sample))
evidence=dict(snapshot_sha256=sha(snapshot),source_first_line=start+1,session_start=lines[0],session_end=lines[-1][:25],
 dll_sha256=sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes()),
 user_feedback="les 2 premiers ont le meme niveau d'opacite. les 2 suivants me semblent ok",
 events=events,cloud_pairs=pairs,
 scoped_visual_acceptance=['SPWI810 / SPINCINA','SPWI812 / SPHORWIL + SPHORWIA'],
 limits=['No explicit visual acceptance of the first two clouds','0x8/0x20 observed but no per-phase final trace for these resources; no measured30fps claim',
 'Cold-load0x10 present; do not claim all frames alwaysHD','BDWOFOGA same corrected-alpha family, not part of this user test'])
(OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(pairs,ensure_ascii=False,indent=2))
