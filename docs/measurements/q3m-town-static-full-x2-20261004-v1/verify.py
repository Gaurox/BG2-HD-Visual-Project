"""Targeted complete-family leaf/native validation and source/output contact sheet."""
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
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not (HERE/'verification.json').exists()
production=load(HERE/'production.json'); generation=load(HERE/'current-generation.json')
native={}
for name in ('isolated','combined'):
    native[name]=next(json.loads(s) for s in reversed((HERE/f'native-{name}.log').read_text().splitlines()) if s.startswith('{'))
    assert native[name]['passed'] and native[name]['resources']==18 and native[name]['frames']==1543
assert production['stats']['encoded_cache_hits']==8 and production['stats']['new_encoded_work']==1534
assert production['stats']['new_neural_targets']==9204 and production['resume']==dict(encoded_cache_hits=1542)
resources,works,plan=source_plan(HERE/'selection.json','town_static')
isolated=ROOT/production['pack_directory']
catalog=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
# Reuse only the independent filtering math from the archived horse analysis.
script=(ROOT/'docs/measurements/q3m-horse-eye-directions-20261004-v3/analyze.py').read_text()
namespace={'np':np};exec(script[script.index('def weights('):script.index('def palette(')],namespace)
render=namespace['render']
contact=Image.new('RGB',(1320,6*260),(65,65,65));draw=ImageDraw.Draw(contact)
frame_total=0
for ordinal,r in enumerate(resources):
    route=next(x for x in catalog['directory'] if x['resref']==r['resref'])
    s=catalog['shards'][route['shard_index']]
    p=isolated/Path(s['registry']).name
    assert file_sha(p).upper()==s['sha256']
    info=leaves.inspect(p,include_frames=True);leaf=info['resources'][0]
    assert info['version']==7 and info['decode_rule_id']==3
    assert info['class_profile_id']==(9 if r['witness']['native_kind']==1 else 8)
    assert leaf['source_sha256']==r['source_sha256'] and leaf['cycles']==r['cycles']
    assert len(leaf['frames'])==len(r['frames']) and leaf['profile'].metadata()==r['profile'].metadata()
    for f,source in zip(leaf['frames'],r['frames']):
        assert f['geometry']==source['geometry'] and not ({'S','M','A'} & set(f))
        indices=works[source['key']]['frame'].indices
        values,offsets=np.unique(indices,return_index=True)
        representatives=np.full(256,0xffff,np.uint16);representatives[values]=offsets
        assert np.array_equal(f['representatives'],representatives)
        frame_total+=1
    # Representative native and filtered Q3m views, same palette and display scale.
    f=leaf['frames'][0]; indices=works[r['frames'][0]['key']]['frame'].indices
    palette=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
    original=palette[indices];upscaled=r['profile'].decode(f['I'],f['F'],palette)
    col,row=ordinal%3,ordinal//3;x0,y0=col*440,row*260
    draw.text((x0+10,y0+5),r['witness']['animation_id']+' '+r['resref'],(255,255,255))
    draw.text((x0+10,y0+24),'Original',(255,255,255));draw.text((x0+230,y0+24),'Q3m x2 palette amelioree',(255,255,255))
    for dx,pixels,z in ((10,original,1),(230,upscaled,2)):
        pixels=render(pixels,2/z);im=Image.fromarray(pixels,'RGBA')
        assert im.width<=210 and im.height<=210,(r['resref'],im.size)
        contact.paste(im,(x0+dx,y0+45),im)
assert frame_total==1543
contact.save(HERE/'comparison.png')
write_json(HERE/'verification.json',dict(passed=True,native_isolated=native['isolated'],native_combined=native['combined'],
    resources=18,frames=frame_total,all_native_geometry_cycles_representatives_profiles_preserved=True,
    acquired_encoded_sha256_unchanged=production['acquired_encoded_sha256_unchanged'],
    resume=production['resume'],resume_torch_import_blocked=production['resume_torch_import_blocked'],
    registry_version=7,SDF=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,resources=18,frames=frame_total,native=native['combined'],comparison='comparison.png')))
