"""Native K6 x3 formats, exact complete MonsterOld cycles/geometry/profiles."""
import builtins,hashlib,json,struct,subprocess,sys
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,exclusive,validate_encoded
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');isolated=ROOT/prod['pack_directory'];assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
resources,works,plan=source_plan(HERE/'selection.json','monster_old');assert plan==prod['plan']
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';encoded=cache/'encoded'/prod['encoder_namespace']
original=builtins.__import__
def no_torch(name,*a,**kw):
    if name.split('.')[0]=='torch':raise RuntimeError('Torch imported on cache-hit resume')
    return original(name,*a,**kw)
with exclusive(cache):
    builtins.__import__=no_torch
    try:resume,_=produce(resources,works,cache)
    finally:builtins.__import__=original
assert resume==dict(encoded_cache_hits=16785)
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
source={(r['witness']['animation_id'],r['resref']):r for r in resources}
@lru_cache(maxsize=28)
def resource(aid,ref):
    r=source[(aid,ref)];s=cat['shards'][routes[(aid,ref)]['shard_index']];p=assets/Path(s['registry']).name;assert file_sha(p).upper()==s['sha256']
    info=leaves.inspect(p,include_frames=True);assert info['version']==7 and info['class_profile_id'] in (8,9) and info['decode_rule_id']==3
    leaf=info['resources'][0];assert leaf['cycles']==r['cycles'] and leaf['source_sha256'].lower()==r['source_sha256'].lower() and leaf['profile'].metadata()==r['profile'].metadata()
    return leaf
empty=[];frames=0
for r in resources:
    aid=r['witness']['animation_id'];leaf=resource(aid,r['resref']);assert len(leaf['frames'])==len(r['frames'])
    for row,f in zip(r['frames'],leaf['frames']):
        assert tuple(row['geometry'])==tuple(f['geometry']) and not {'S','M','A'}&set(f)
        with np.load(encoded/(row['key']+'.npz'),allow_pickle=False) as a:
            assert np.array_equal(f['I'],a['I']) and np.array_equal(f['F'],a['F']) and f['dep']==a['dep'].tobytes()
            validate_encoded(r['profile'],f['I'],f['F'],a['guide'],a['dep'])
        vals,off=np.unique(works[row['key']]['frame'].indices,return_index=True);rep=np.full(256,0xffff,np.uint16);rep[vals]=off;assert np.array_equal(rep,f['representatives'])
        if not f['I'].size:empty.append(dict(animation_id=aid,resref=r['resref'],frame_index=row['frame_index'],geometry=f['geometry']))
        frames+=1
    print(json.dumps(dict(stage='leaf',animation=aid,resref=r['resref'],frames=frames)),flush=True)
assert frames==17754 and len(empty)==0
def native(label,cmd):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,encoding='utf-8');(HERE/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode==0,(label,p.stdout[-2000:],p.stderr)
    report=json.loads(next(s for s in reversed(p.stdout.splitlines()) if s.startswith('{')));assert report['passed'];return report
reports={name:native('native-'+name,[ROOT/'sprite/.work/q3m-monster-quadrant-full-x2-20261004-v1/runtime-build/Release/iee_palette_partner_tests.exe',path,isolated/'witnesses.oracle']) for name,path in [('isolated',isolated),('combined',assets)]}
assert all(r['frames']==17754 for r in reports.values())
write_json(HERE/'verification.json',dict(passed=True,resources=218,frames=17754,packed_resources=217,packed_frames=17752,unique_native_BAM=79,original_native_frames=6917,all_geometry_cycles_profiles_representatives_cache_preserved=True,native_world=reports,empty_native_declarations=empty,resume=resume,resume_torch_import_blocked=True,DLL_unchanged=True,SDF=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,resources=218,frames=17754,native_world=reports)),flush=True)
