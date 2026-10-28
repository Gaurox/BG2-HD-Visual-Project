"""Freeze the six-spell test and verify the existing alpha-corrected cloud pair."""
from pathlib import Path
import hashlib, json, re, sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
GAME=get_path('bg2ee_game_root',required=True)
if (OUT/'evidence.json').exists(): raise SystemExit('Existing evidence; create another version')
def sha(raw):return hashlib.sha256(raw).hexdigest().upper()
raw=(GAME/'InfinityEngine-Enhancer.log').read_bytes();(OUT/'runtime.log').write_bytes(raw)
lines=raw.decode('utf-8',errors='replace').splitlines()
start=max(i for i,l in enumerate(lines) if 'Infinity Engine Enhancer initializing...' in l)
session=[(i+1,lines[i].replace('\0','')) for i in range(start,len(lines))]
refs=['SPCLOUDK','Y31P069','SKLT','SKLH','SPCHRORB','X26PLAA','XIPLAUIN','Y31P067','COLDH','SPCHLGT1','SPCHLGT2','SPCHLGT3']
observed={n:[dict(line=i,text=l) for i,l in session if f'resref={n} ' in l and
    ('EFX_STREAM_DIAGNOSTIC' in l or 'EFX_MASK_FALLBACK' in l or 'EFX_NATIVE_SURFACE' in l)] for n in refs}
m=json.loads((GAME/'iee-assets/effects/manifest.json').read_text());catalog={r['resref']:r for r in m['resources']}
a=catalog['SPCLOUDK'];b=catalog['X58CLK']
for field in ('cycles','timeline','frame_count','production_bam','rgb_encoding'):assert a[field]==b[field],field
original=sorted([f for f in m['frames'] if f['resref']=='SPCLOUDK'],key=lambda f:f['resource_frame'])
fixed=sorted([f for f in m['frames'] if f['resref']=='X58CLK'],key=lambda f:f['resource_frame'])
assert len(original)==len(fixed)==425
checks=[];changed=0;total_bytes=0
for i,(x,y) in enumerate(zip(original,fixed)):
 for key in ('resource_frame','bytes','logical_size_x1','physical_size_x4','source_centre_x1'):assert x[key]==y[key],(i,key)
 xr=(GAME/'iee-assets/effects'/x['asset']).read_bytes();yr=(GAME/'iee-assets/effects'/y['asset']).read_bytes()
 assert sha(xr)==x['sha256'].upper() and sha(yr)==y['sha256'].upper(),i
 xp=np.frombuffer(xr,dtype=np.uint8).reshape(-1,4);yp=np.frombuffer(yr,dtype=np.uint8).reshape(-1,4)
 assert np.array_equal(xp[:,:3],yp[:,:3]),i
 changed+=int(not np.array_equal(xp[:,3],yp[:,3]));total_bytes+=len(xr)+len(yr)
 if i==len(original)//2:
  support=xp[:,3]>0
  sample=dict(frame=i,legacy_alpha_median=float(np.median(xp[support,3])),
    corrected_alpha_median=float(np.median(yp[support,3])),
    old_opaque_pixels=int(np.count_nonzero(xp[:,3]==255)),
    corrected_opaque_pixels=int(np.count_nonzero(yp[:,3]==255)))
 checks.append(dict(frame=i,legacy=x['asset'],corrected=y['asset'],sha_and_rgb_equal=True))
carriers={c['resref']:c for c in m['runtime_bam_carriers']}
assert (GAME/carriers['SPCLOUDK']['asset']).read_bytes()==(GAME/carriers['X58CLK']['asset']).read_bytes()
evidence=dict(log_sha256=sha(raw),session_start=session[0],session_end=session[-1][1][:25],
 dll_sha256=sha((GAME/'InfinityEngine-Enhancer.dll').read_bytes()),observed=observed,
 user_feedback='Tous les tests semblent corrects sauf nuage avec fond opaque; ancien correctif deja existant',
 cloud_pair=dict(native='SPCLOUDK',corrected='X58CLK',pairs=425,bytes_checked=total_bytes,
  RGB_identical=True,alpha_changed_frames=changed,sample=sample,
  identical_cycles_timeline_geometry_encoding=True,identical_native_carriers=True),checks=checks,
 limits='Visual acceptance of the five other tests is not proof of HD: SKLT/SPCHRORB still geometry fallback; no SKLH observed; SPCHLGT3 cycle2 observed but cycle9 not validated')
(OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'events.txt').write_text('\n'.join(f'{i}: {l}' for i,l in session if any(f'resref={n} ' in l for n in refs))+'\n',encoding='utf-8')
print(json.dumps(evidence['cloud_pair'],ensure_ascii=False,indent=2))
