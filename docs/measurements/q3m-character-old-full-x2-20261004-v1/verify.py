"""All Character_old physical frames/guard alias/transparent bodies; native K6 oracle."""
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
production=load(HERE/'production.json');native={}
for name in ('isolated','combined'):
    native[name]=next(json.loads(s) for s in reversed((HERE/f'native-{name}.log').read_text(encoding='utf-8').splitlines()) if s.startswith('{'))
    assert native[name]['passed'] and native[name]['resources']==120 and native[name]['frames']==5659
assert production['stats']['encoded_cache_hits']==288
assert production['stats'].get('new_encoded_work',0)+production['stats'].get('special_work',0)==3483
assert production['resume']==dict(encoded_cache_hits=3771) and production['acquired_encoded_sha256_unchanged']==288
resources,works,plan=source_plan(HERE/'selection.json','character_old')
isolated=ROOT/production['pack_directory']
catalog=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
routes={(x['animation_id'],x['resref']):x for x in catalog['directory']}
for aid1,aid2 in (('0x6405','0x6406'),):
    refs={ref for aid,ref in routes if aid==aid1}
    assert refs and refs=={ref for aid,ref in routes if aid==aid2}
    for ref in refs:
        assert {k:v for k,v in routes[aid1,ref].items() if k!='animation_id'}=={k:v for k,v in routes[aid2,ref].items() if k!='animation_id'}
script=(ROOT/'docs/measurements/q3m-horse-eye-directions-20261004-v3/analyze.py').read_text(encoding='utf-8')
namespace={'np':np};exec(script[script.index('def weights('):script.index('def palette(')],namespace)
render=namespace['render'];contact=Image.new('RGB',(1320,2*260),(65,65,65));draw=ImageDraw.Draw(contact)
frame_total=0;unique_refs=set();models=set();guard_frames=0;auxiliary_frames=0
for r in resources:
    if r['resref'] in unique_refs:continue
    unique_refs.add(r['resref']);route=routes[r['witness']['animation_id'],r['resref']]
    shard=catalog['shards'][route['shard_index']];p=isolated/Path(shard['registry']).name
    assert file_sha(p).upper()==shard['sha256']
    info=leaves.inspect(p,include_frames=True);leaf=info['resources'][0]
    assert info['version']==7 and info['decode_rule_id']==3
    assert info['class_profile_id']==(9 if r['witness']['native_kind']==1 else 8)
    assert leaf['source_sha256']==r['source_sha256'] and leaf['cycles']==r['cycles']
    assert len(leaf['frames'])==len(r['frames']) and leaf['profile'].metadata()==r['profile'].metadata()
    for f,source in zip(leaf['frames'],r['frames']):
        assert f['geometry']==source['geometry'] and not ({'S','M','A'} & set(f))
        values,offsets=np.unique(works[source['key']]['frame'].indices,return_index=True)
        representatives=np.full(256,0xffff,np.uint16);representatives[values]=offsets
        assert np.array_equal(f['representatives'],representatives)
        if r['resref']=='CMNKINV':
            assert leaf['cycles']==[[]]
            cached=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1/encoded'/production['encoder_namespace']/(source['key']+'.npz')
            with np.load(cached,allow_pickle=False) as data:
                assert np.array_equal(f['I'],data['I']) and np.array_equal(f['F'],data['F'])
                r['profile'].validate(f['I'],f['F'],data['guide'],data['dep'])
            auxiliary_frames+=1
        if r['resref'].startswith('MDGU1'):
            assert not np.any(works[source['key']]['frame'].indices)
            assert not np.any(f['I']) and not np.any(f['F'])
            guard_frames+=1
        frame_total+=1
    model=r['witness']['animation_id']
    if model in models:continue
    ordinal=len(models);models.add(model)
    f=leaf['frames'][0];indices=works[r['frames'][0]['key']]['frame'].indices
    palette=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
    original=palette[indices];upscaled=r['profile'].decode(f['I'],f['F'],palette)
    col,row=ordinal%3,ordinal//3;x0,y0=col*440,row*260
    draw.text((x0+10,y0+5),model+' '+r['resref'],(255,255,255))
    draw.text((x0+10,y0+24),'Original',(255,255,255));draw.text((x0+230,y0+24),'Q3m x2 palette amelioree',(255,255,255))
    for dx,pixels,z in ((10,original,1),(230,upscaled,2)):
        im=Image.fromarray(render(pixels,2/z),'RGBA')
        assert im.width<=210 and im.height<=210,(r['resref'],im.size)
        contact.paste(im,(x0+dx,y0+45),im)
assert frame_total==4725 and len(unique_refs)==99 and len(models)==6 and guard_frames==936 and auxiliary_frames==2
contact.save(HERE/'comparison.png')
write_json(HERE/'verification.json',dict(passed=True,native_isolated=native['isolated'],native_combined=native['combined'],
    resources=99,frames=frame_total,logical_resources=121,logical_frames=5661,models=6,shared_resource_bindings=22,
    native_world_bindings=120,native_world_bound_frames=5659,uncycled_auxiliary_resref='CMNKINV',uncycled_auxiliary_frames_leaf_cache_verified=2,
    alias_bindings_identical=True,transparent_guard_native_frames_preserved=936,all_native_geometry_cycles_representatives_profiles_preserved=True,
    acquired_encoded_sha256_unchanged=production['acquired_encoded_sha256_unchanged'],resume=production['resume'],
    resume_torch_import_blocked=production['resume_torch_import_blocked'],registry_version=7,SDF=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,resources=99,frames=frame_total,native=native['combined'],comparison='comparison.png')))
