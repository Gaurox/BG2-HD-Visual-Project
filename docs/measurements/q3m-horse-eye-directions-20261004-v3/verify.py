"""Verify candidate isolation, all idle views/mirrors and unchanged installed state."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from q3m_family_witnesses import source_plan
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not (HERE/'verification.json').exists()
# Load just the pure sampling definitions without rerunning the producer.
script=(HERE/'analyze.py').read_text();namespace={'np':np}
exec(script[script.index('def weights('):script.index('def palette(')],namespace)
sample,render=namespace['sample'],namespace['render']
for t in (0,.25,.5,.75,1):
 w=namespace['weights'](np.array(t));assert abs(w.sum()-1)<1e-12
 assert np.allclose(w,namespace['weights'](np.array(1-t))[::-1],atol=1e-12)
g=load(ROOT/'docs/measurements/q3m-horse-eye-x2-20261004-v1/current-generation.json')
oldcat=registry.read_sealed_catalog_index(ROOT/g['catalog']['path'],g['catalog']['sha256'])
c=load(HERE/'candidate.json');pack=ROOT/c['pack_directory'];newcat=registry.read_sealed_catalog_index(pack/'CreatureSprites-XN.catalog',c['pack']['catalog_sha256'])
resources,works,_=source_plan(ROOT/'docs/measurements/q3m-ambient-static-full-x2-20261004-v1/selection.json','ambient_static')
resources=[r for r in resources if r['resref'] in ('AHRSG1','AHRSG1E')]
total_changed=0;frames_changed=[];mirror_samples=0
old,new={},{}
for r in resources:
 ref=r['resref'];route=next(x for x in oldcat['directory'] if x['animation_id']=='0xB100' and x['resref']==ref)
 old[ref]=leaves.inspect(ROOT/g['generation_dir']/oldcat['shards'][route['shard_index']]['registry'],include_frames=True)['resources'][0]
 route=next(x for x in newcat['directory'] if x['resref']==ref)
 new[ref]=leaves.inspect(pack/Path(newcat['shards'][route['shard_index']]['registry']).name,include_frames=True)['resources'][0]
 assert new[ref]['source_sha256']==old[ref]['source_sha256'] and new[ref]['cycles']==old[ref]['cycles']
 assert new[ref]['profile'].metadata()==old[ref]['profile'].metadata()
 for fi,(a,b) in enumerate(zip(old[ref]['frames'],new[ref]['frames'])):
  assert a['geometry']==b['geometry'] and np.array_equal(a['representatives'],b['representatives'])
  delta=(a['I']!=b['I'])|(a['F']!=b['F']);total_changed+=int(delta.sum())
  if delta.any():
   assert ref=='AHRSG1' and fi in range(5)
   assert not np.any(delta&(r['profile'].classes[a['I']]<3));frames_changed.append(fi)
  elif ref=='AHRSG1E' or fi>=5:assert a['dep']==b['dep']
  if fi in list(range(4))+list(range(11,15)):
   for k in range(6):
    p=np.column_stack((r['profile'].fitting[k],np.full(256,255,np.uint8)));p[0]=0;p[1,3]=127
    pixels=r['profile'].decode(b['I'],b['F'],p)
    xx=np.linspace(0,pixels.shape[1]-1,32)+.173;yy=np.linspace(0,pixels.shape[0]-1,32)+.371
    assert np.allclose(sample(pixels,xx,yy),sample(np.fliplr(pixels),pixels.shape[1]-1-xx,yy),atol=1e-8)
    mirror_samples+=32
 assert len(new[ref]['frames'])==22
assert frames_changed==[0,1,2,3,4] and total_changed==134
for r in resources:
 ref=r['resref'];profile=r['profile'];p=np.column_stack((profile.fitting[0],np.full(256,255,np.uint8)));p[0]=0;p[1,3]=127
 for bank in (0,11):
  atlas=Image.new('RGB',(870,8*235),(65,65,65));draw=ImageDraw.Draw(atlas)
  for row,(fi,mirror) in enumerate((fi,m) for fi in range(bank,bank+4) for m in (False,True)):
   f=r['frames'][fi];native=p[works[f['key']]['frame'].indices];a=old[ref]['frames'][fi];b=new[ref]['frames'][fi]
   before=profile.decode(a['I'],a['F'],p);after=profile.decode(b['I'],b['F'],p)
   box=(0,10,25,43) if ref=='AHRSG1' and bank==0 else (0,0,28,28) if ref=='AHRSG1' else (43,0,82,32) if bank==0 else (55,8,87,37)
   x0,y0,x1,y1=box
   for col,(rgba,z,title) in enumerate([(native,1,'Original'),(before,2,'Installe'),(after,2,'Candidat')]):
    crop=rgba[y0*z:min(y1*z,rgba.shape[0]),x0*z:min(x1*z,rgba.shape[1])]
    if mirror:crop=np.fliplr(crop)
    image=Image.fromarray(render(crop,5/z),'RGBA');atlas.paste(image,(col*290+15,row*235+44),image)
    draw.text((col*290+15,row*235+24),title,(255,255,255))
   draw.text((15,row*235+3),f'{ref} {fi} '+('miroir' if mirror else 'direct'),(255,255,255))
  atlas.save(HERE/f'idle-all-{ref}-bank{bank}.png')
native=next(json.loads(x) for x in reversed((HERE/'native-candidate.log').read_text().splitlines()) if x.startswith('{'))
assert native['passed'] and native['frames']==44 and native['resources']==2
cases=[v for m in load(HERE/'contrast-cases.json') if m['variant']=='0.40' for v in m['cases']]
assert len(cases)==1440 and all(v['candidate']>=v['native'] and v['candidate']>v['current'] for v in cases)
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==g['catalog']['sha256']
baseline=load(ROOT/'docs/measurements/q3m-horse-eye-x2-20261004-v1/baseline.json')
for p in baseline['preserved']:assert file_sha(game/p['relative_path']).lower()==p['sha256'].lower()
write_json(HERE/'verification.json',dict(passed=True,native_candidate=native,changed_frames=5,unchanged_frames=39,changed_x2_pixels=134,native_geometry_cycles_palette_metadata_identical=True,outside_eye_planes_I_F_identical=True,mirrored_filter_samples_equal=mirror_samples,idle_source_frames_compared=16,idle_presentations_with_mirrors=32,contrast_samples=1440,contrast_below_original=0,contrast_worse_than_installed=0,current_installed_catalog_unchanged=True,preserved_installed_files_sha256_verified=len(baseline['preserved']),installed=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,changed_frames=5,changed_x2_pixels=134,mirrored_samples=mirror_samples,contrast_samples=1440,below_native=0,installed=False)))
