"""Read-only native/installed comparison and a local horse eye candidate; no install."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,pack,save
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
from workspace_paths import get_path
WORK=ROOT/'sprite/.work/q3m-horse-eye-directions-20261004-v2'
CURRENT=ROOT/'docs/measurements/q3m-horse-eye-x2-20261004-v1'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not (HERE/'analysis.json').exists()
generation=load(CURRENT/'current-generation.json')
catalog=registry.read_sealed_catalog_index(ROOT/generation['catalog']['path'],generation['catalog']['sha256'])
installed={}
for route in catalog['directory']:
 if route['animation_id']=='0xB100':
  shard=catalog['shards'][route['shard_index']]
  installed[route['resref']]=leaves.inspect(ROOT/generation['generation_dir']/shard['registry'],include_frames=True)['resources'][0]
resources,allworks,_=source_plan(ROOT/'docs/measurements/q3m-ambient-static-full-x2-20261004-v1/selection.json','ambient_static')
resources=[r for r in resources if r['resref'] in installed]
keys={f['key'] for r in resources for f in r['frames']};works={k:allworks[k] for k in keys}
assert len(keys)==44
# Native dark brown iris cluster, NOT a guessed black dot; motion follows source.
eyes={0:[(8,25),(9,25),(9,26)],1:[(9,25),(8,26),(9,26)],2:[(9,26),(9,27)],3:[(8,25),(9,25),(9,26)],4:[(9,25),(9,26)]}
# Nearby skin sample is outside the eye footprint in all five front poses.
cheek=[(5,23),(6,23),(7,23)]

def weights(t):
 return np.stack((-.5*t+t*t-.5*t**3,1-2.5*t*t+1.5*t**3,.5*t+2*t*t-1.5*t**3,-.5*t*t+.5*t**3),axis=-1)
def sample(rgba,x,y):
 a=np.asarray(rgba,dtype=np.float64)/255;ix=np.floor(x).astype(int);iy=np.floor(y).astype(int);wx=weights(x-ix);wy=weights(y-iy)
 alpha=np.zeros(np.broadcast_shapes(np.shape(x),np.shape(y)));rgb=np.zeros((*alpha.shape,3))
 for yy in range(4):
  for xx in range(4):
   p=a[np.clip(iy+yy-1,0,a.shape[0]-1),np.clip(ix+xx-1,0,a.shape[1]-1)];w=wx[...,xx]*wy[...,yy];alpha+=w*p[...,3];rgb+=w[...,None]*p[...,:3]*p[...,3,None]
 alpha=np.clip(alpha,0,1);rgb=np.clip(rgb,0,alpha[...,None]);rgb=np.divide(rgb,alpha[...,None],out=np.zeros_like(rgb),where=alpha[...,None]>1e-12)
 return np.concatenate((rgb,alpha[...,None]),axis=-1)*255
def render(rgba,scale):
 yy,xx=np.meshgrid((np.arange(int(rgba.shape[0]*scale))+.5)/scale-.5,(np.arange(int(rgba.shape[1]*scale))+.5)/scale-.5,indexing='ij')
 return np.rint(sample(rgba,xx,yy)).astype(np.uint8)
def palette(profile,k):
 p=np.column_stack((profile.fitting[k],np.full(256,255,np.uint8)));p[0]=0;p[1,3]=127;return p
def contrast(native,rgba,z,points,phase):
 # Screen grid phase affects where pixel centres land; test screen sampling near each source core.
 def luminance(coords):
  xy=np.array(coords,float);position=np.round((xy+.5)*z-.5-np.array(phase))+.5+np.array(phase);position=position/z-.5
  out=sample(rgba,(position[:,0]+.5)*(2 if not native else 1)-.5,(position[:,1]+.5)*(2 if not native else 1)-.5)
  return (out[:,:3]@np.array([.2126,.7152,.0722])).mean()
 return float(luminance(cheek)-luminance(points))
variants={};measurements=[];metadata={};native_frames={};current_frames={}
for r in resources:
 ref=r['resref'];profile=r['profile'];old=installed[ref]
 assert profile.metadata()==old['profile'].metadata()
 assert r['cycles']==old['cycles']
 for f in r['frames']:
  key=f['key'];fi=f['frame_index'];w=works[key];current=old['frames'][fi]
  assert tuple(current['geometry'])==tuple(f['geometry'])
  native_frames[(ref,fi)]=w['frame'].indices;current_frames[(ref,fi)]=current
  original_path=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1/encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')/(key+'.npz')
  with np.load(original_path,allow_pickle=False) as data:guide=data['guide'].copy()
  metadata[str(original_path.relative_to(ROOT))]=file_sha(original_path)
  base=dict(guide=guide,I=current['I'].copy(),F=current['F'].copy(),dep=np.frombuffer(current['dep'],np.uint8).copy())
  choices={name:{n:a.copy() for n,a in base.items()} for name in ('exact','0.85','0.70','0.55','0.40')}
  if ref=='AHRSG1' and fi in eyes:
   for name,arrays in choices.items():
    if name=='exact':
     for x,y in eyes[fi]:
      ni=int(w['frame'].indices[y,x]);arrays['I'][y*2:y*2+2,x*2:x*2+2]=ni;arrays['F'][y*2:y*2+2,x*2:x*2+2]=0
    else:
     centres=np.array(eyes[fi],float);centre=(centres.mean(axis=0)+.5)*2-.5
     yy,xx=np.meshgrid(np.arange(guide.shape[0]),np.arange(guide.shape[1]),indexing='ij')
     distance=((xx-centre[0])/2.2)**2+((yy-centre[1])/2.0)**2
     mask=distance<=1
     alpha=np.exp(-distance*1.7)*mask
     core_indices=[int(w['frame'].indices[y,x]) for x,y in eyes[fi]]
     dark=profile.fitting[:,core_indices,:].mean(axis=1)/255*float(name)
     locations=np.flatnonzero(mask);oldfits=np.stack([profile.decode(base['I'],base['F'],p).reshape(-1,3)[locations] for p in profile.fitting])/255
     targets=oldfits*(1-alpha.reshape(-1)[locations][None,:,None])+dark[:,None,:]*alpha.reshape(-1)[locations][None,:,None]
     encoded=profile.encode(guide.reshape(-1)[locations][None,:],targets[:,None,:,:])
     arrays['I'].reshape(-1)[locations]=encoded['I'][0];arrays['F'].reshape(-1)[locations]=encoded['F'][0]
    arrays['dep']=profile.dependencies(arrays['I'],arrays['F']);profile.validate(arrays['I'],arrays['F'],guide,arrays['dep'])
   for name,arrays in choices.items():
    cases=[]
    for k in range(6):
     p=palette(profile,k);native=p[w['frame'].indices];before=profile.decode(base['I'],base['F'],p);after=profile.decode(arrays['I'],arrays['F'],p)
     for zoom in (1,2,4):
      for px in (0,.25,.5,.75):
       for py in (0,.25,.5,.75):
        phase=(px,py);cn=contrast(True,native,zoom,eyes[fi],phase);cb=contrast(False,before,zoom,eyes[fi],phase);ca=contrast(False,after,zoom,eyes[fi],phase)
        cases.append(dict(k=k,zoom=zoom,phase=[px,py],native=cn,current=cb,candidate=ca))
    measurements.append(dict(frame_index=fi,variant=name,cases=cases))
  variants[(ref,fi)]=choices

summary=[]
for name in ('exact','0.85','0.70','0.55','0.40'):
 cases=[c for m in measurements if m['variant']==name for c in m['cases']]
 ratio=[c['candidate']/c['native'] for c in cases if c['native']>1]
 summary.append(dict(variant=name,samples=len(cases),native_contrast_min=min(c['native'] for c in cases),candidate_contrast_min=min(c['candidate'] for c in cases),minimum_gain_over_current=min(c['candidate']-c['current'] for c in cases),minimum_ratio_to_native=min(ratio),median_ratio_to_native=float(np.median(ratio)),cases_below_native=sum(c['candidate']<c['native'] for c in cases)))
# Local candidate: bounded modest reinforcement; preserve source shape/area, never enlarge pupil.
chosen='0.55'
changed=[]
for r in resources:
 for f in r['frames']:
  fi=f['frame_index'];ref=r['resref'];arrays=variants[(ref,fi)][chosen];before=current_frames[(ref,fi)];delta=(arrays['I']!=before['I'])|(arrays['F']!=before['F']);mask=np.zeros(delta.shape,bool)
  if ref=='AHRSG1' and fi in eyes:
   centres=np.array(eyes[fi],float);centre=(centres.mean(axis=0)+.5)*2-.5
   yy,xx=np.meshgrid(np.arange(mask.shape[0]),np.arange(mask.shape[1]),indexing='ij')
   mask=((xx-centre[0])/2.2)**2+((yy-centre[1])/2.0)**2<=1
  assert not np.any(delta&~mask)
  if delta.any():changed.append(dict(resref=ref,frame_index=fi,source_core=eyes[fi],changed_x2_pixels=int(delta.sum())))
  dest=WORK/'encoded'/(f['key']+'.npz');save(dest,**arrays);works[f['key']]['encoded_path']=dest
result=pack(resources,works,WORK/'candidate')
assert all(file_sha(ROOT/p)==sha for p,sha in metadata.items())
write_json(HERE/'candidate.json',dict(role='local-candidate-not-installed-or-QA',recipe='horse-front-native-eye-elliptical-K6-55percent-v2',selected=chosen,changed_frames=len(changed),unchanged_frames=44-len(changed),changed_x2_pixels=sum(p['changed_x2_pixels'] for p in changed),patches=changed,retained_previous_profile_eye_frames=10,no_new_neural_inference=True,pack=result,pack_directory=(WORK/'candidate').relative_to(ROOT).as_posix(),SDF=False,ingame_QA=False,installed=False))

def head_box(ref,fi):
 if ref=='AHRSG1':return (0,10,25,43) if fi<11 else (0,0,28,28)
 return (43,0,82,32) if fi<11 else (55,8,87,37)
def crop(a,box,z):
 x0,y0,x1,y1=box;return a[y0*z:min(y1*z,a.shape[0]),x0*z:min(x1*z,a.shape[1])]
def put(canvas,rgba,x,y,scale=1):
 im=Image.fromarray(rgba,'RGBA');canvas.paste(im,(x,y),im)
atlas=Image.new('RGB',(1160,8*240),(65,65,65));draw=ImageDraw.Draw(atlas)
for row,(ref,fi,mirror) in enumerate([(ref,fi,mirror) for ref,fi in [('AHRSG1',0),('AHRSG1',11),('AHRSG1E',0),('AHRSG1E',11)] for mirror in (False,True)]):
 r=next(r for r in resources if r['resref']==ref);p=palette(r['profile'],0);native=p[native_frames[(ref,fi)]];old=current_frames[(ref,fi)];q=r['profile'].decode(old['I'],old['F'],p);arrays=variants[(ref,fi)][chosen];corrected=r['profile'].decode(arrays['I'],arrays['F'],p);box=head_box(ref,fi)
 for col,(title,rgba,z) in enumerate([('Natif Nearest',native,1),('Natif CatmullRom',native,1),('Installe CatmullRom',q,2),('Candidat CatmullRom',corrected,2)]):
  a=crop(rgba,box,z)
  if mirror:a=np.fliplr(a)
  if col==0:a=np.array(Image.fromarray(a).resize((a.shape[1]*5,a.shape[0]*5),Image.Resampling.NEAREST))
  else:a=render(a,5/z)
  put(atlas,a,col*290+15,row*240+42);draw.text((col*290+15,row*240+22),title,(255,255,255))
 draw.text((15,row*240+3),f'{ref} {fi} '+('miroir' if mirror else 'direct'),(255,255,255))
atlas.save(HERE/'directions-comparison.png')
pose=Image.new('RGB',(1000,650),(65,65,65));draw=ImageDraw.Draw(pose)
ref,fi='AHRSG1',0;r=next(r for r in resources if r['resref']==ref);p=palette(r['profile'],0);native=p[native_frames[(ref,fi)]];old=current_frames[(ref,fi)];q=r['profile'].decode(old['I'],old['F'],p);arr=variants[(ref,fi)][chosen];fixed=r['profile'].decode(arr['I'],arr['F'],p)
for col,(title,a,z) in enumerate([('Original natif',native,1),('Q3m installe',q,2),('Correction proposee',fixed,2)]):
 put(pose,render(a,4/z),col*330+20,35);draw.text((col*330+20,12),title,(255,255,255));put(pose,render(crop(a,head_box(ref,fi),z),8/z),col*330+20,360)
pose.save(HERE/'capture-pose-comparison.png')
# All sixteen idle source frames, including mirrored presentations and native occlusions.
coverage=[]
for ref in ('AHRSG1','AHRSG1E'):
 for fi in list(range(4))+list(range(11,15)):
  coverage.append(dict(resref=ref,frame_index=fi,mirrors_checked=True,eye_protection=('new-brown-core-reinforced' if ref=='AHRSG1' and fi<4 else 'previous-native-core-retained' if fi>=11 else 'back-view-native-occlusion-no-eye-added')))
native_direction=[dict(direction=d,nonmirrored=dict(resref='AHRSG1' if d<=7 else 'AHRSG1E',cycle=d//2),mirrored_mode=dict(resref='AHRSG1',cycle=d//2 if d<=7 else (15-d)//2,mirror=d>7)) for d in range(16)]
write_json(HERE/'analysis.json',dict(scope='horse-only-local-analysis-no-install',capture_match=dict(resref='AHRSG1',frame_group=[0,1,2,3],exact_frame_and_cycle_slot_not_identifiable_from_screenshot=True,previous_patch_did_not_cover_pose=True),native_resources=2,frames_reviewed=44,idle_frames=16,idle_presentations_with_mirrors=32,coverage=coverage,direction_threshold=7,direction_map=native_direction,native_reference_analysis='docs/measurements/q3m-horse-eye-directions-20261004-v1/native-vtable-functions.asm',native_rvas=dict(constructor='0x307df6',direction='0x318630',render='0x32be60'),contrast_summaries=summary,contrast_definition='nearby skin minus iris-core RGB luminance; six native K6 palettes, CatmullRom premultiplied, zoom1/2/4, 16 screen phases; lighting/background of screenshot not replicated',selected_variant=chosen,full_sample_results='contrast-cases.json',candidate='candidate.json',unchanged_shared_cache_files=44,installed=False,ingame_QA=False,release=False))
write_json(HERE/'contrast-cases.json',measurements)
print(json.dumps(dict(summary=summary,changed_frames=len(changed),changed_x2_pixels=sum(p['changed_x2_pixels'] for p in changed),candidate_resources=2,candidate_frames=44,installed=False)))
