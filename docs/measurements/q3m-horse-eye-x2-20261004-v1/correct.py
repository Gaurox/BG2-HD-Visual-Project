"""Protect only manually identified native horse eye pixels; shared Q3m cache read-only."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,pack,save
from palette_work_plan import file_sha,write_json
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
work=ROOT/'sprite/.work/q3m-horse-eye-x2-20261004-v1'
assert not (HERE/'production.json').exists() and not (work/'isolated').exists()
resources,allworks,summary=source_plan(ROOT/'docs/measurements/q3m-ambient-static-full-x2-20261004-v1/selection.json','ambient_static')
resources=[r for r in resources if r['resref'] in ('AHRSG1','AHRSG1E')]
keys={f['key'] for r in resources for f in r['frames']};works={k:allworks[k] for k in keys};assert len(works)==44
# Coordinates are native pixels; no eye is invented on back-facing/occluded poses.
anchors={
 'AHRSG1':{11:[(12,8,7)],12:[(12,8,16)],13:[(12,7,7)],14:[(12,8,7)],15:[(12,8,7)]},
 'AHRSG1E':{11:[(63,24,7),(63,25,7)],12:[(62,24,7)],13:[(62,25,7)],14:[(63,24,7),(63,25,7)],15:[(63,24,7)]},
}
patches=[];changed_total=0;old_identity={};images=[]
for r in resources:
 profile=r['profile'];rgb=profile.source[:,[2,1,0]];palette=np.column_stack((rgb,np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
 for f in r['frames']:
  w=works[f['key']];src=cache/'encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')/(f['key']+'.npz');old_identity[src.relative_to(ROOT).as_posix()]=file_sha(src)
  with np.load(src,allow_pickle=False) as data:arrays={n:data[n].copy() for n in data.files}
  before={n:a.copy() for n,a in arrays.items()};mask=np.zeros(arrays['I'].shape,bool)
  for x,y,expected in anchors.get(r['resref'],{}).get(f['frame_index'],[]):
   assert int(w['frame'].indices[y,x])==expected,(r['resref'],f['frame_index'],x,y)
   mask[y*2:y*2+2,x*2:x*2+2]=True
   arrays['I'][y*2:y*2+2,x*2:x*2+2]=expected;arrays['F'][y*2:y*2+2,x*2:x*2+2]=0
  changed=(arrays['I']!=before['I'])|(arrays['F']!=before['F'])
  assert not np.any(changed&~mask)
  assert np.array_equal(arrays['guide'],before['guide'])
  arrays['dep']=profile.dependencies(arrays['I'],arrays['F']);profile.validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep'])
  if mask.any():
   patches.append(dict(resref=r['resref'],frame_index=f['frame_index'],native_eye_pixels=anchors[r['resref']][f['frame_index']],changed_x2_pixels=int(changed.sum())))
   native=palette[w['frame'].indices];old=profile.decode(before['I'],before['F'],palette);new=profile.decode(arrays['I'],arrays['F'],palette)
   xs=[a[0] for a in anchors[r['resref']][f['frame_index']]];ys=[a[1] for a in anchors[r['resref']][f['frame_index']]];x0=max(0,min(xs)-6);y0=max(0,min(ys)-6);x1=min(native.shape[1],max(xs)+7);y1=min(native.shape[0],max(ys)+7)
   images.append((r['resref'],f['frame_index'],[Image.fromarray(native[y0:y1,x0:x1],'RGBA'),Image.fromarray(old[y0*2:y1*2,x0*2:x1*2],'RGBA'),Image.fromarray(new[y0*2:y1*2,x0*2:x1*2],'RGBA')]))
  changed_total+=int(changed.sum());dst=work/'encoded'/(f['key']+'.npz');save(dst,**arrays);w['encoded_path']=dst
result=pack(resources,works,work/'isolated')
assert all(file_sha(ROOT/p)==sha for p,sha in old_identity.items())
assert result['resources']==2 and result['frames']==44 and result['animation_count']==1
write_json(HERE/'production.json',dict(scope='horse-only-native-eye-preservation',recipe='native-eye-2x2-I-exact-F0-local-v1',scale=2,registry_version=7,SDF=False,changed_frames=len(patches),unchanged_frames=44-len(patches),changed_x2_pixels=changed_total,patches=patches,shared_cache_files_sha256_unchanged=old_identity,new_neural_targets=0,new_Q3m_encoding=0,pack=result,pack_directory=(work/'isolated').relative_to(ROOT).as_posix(),ingame_QA=False,release=False))
canvas=Image.new('RGB',(850,len(images)*220),(65,65,65));draw=ImageDraw.Draw(canvas)
for row,(ref,fi,ims) in enumerate(images):
 draw.text((5,row*220+2),f'{ref} frame {fi}: native / Q3m before / corrected',(255,255,255))
 for col,im in enumerate(ims):
  im=im.resize((im.width*(12 if col==0 else 6),im.height*(12 if col==0 else 6)),Image.Resampling.NEAREST);canvas.paste(im,(col*280+10,row*220+22),im)
canvas.save(HERE/'comparison.png');print(json.dumps(dict(changed_frames=len(patches),changed_x2_pixels=changed_total,resources=2,frames=44,new_inference=0)))
