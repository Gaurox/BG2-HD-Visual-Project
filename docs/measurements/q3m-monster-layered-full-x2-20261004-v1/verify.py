"""All native frames/profiles/geometry/cycles; K6 x3 formats; body/each weapon composition."""
import sys,json,struct,subprocess,hashlib,builtins
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from q3m_family_witnesses import source_plan,produce,exclusive
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites';isolated=ROOT/prod['pack_directory']
resources,works,plan=source_plan(HERE/'selection.json','monster_layered');assert plan==prod['plan']
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';encoded=cache/'encoded'/prod['encoder_namespace']
original=builtins.__import__
def no_torch(name,*a,**kw):
    if name.split('.')[0]=='torch':raise RuntimeError('Torch imported by all-hit resume')
    return original(name,*a,**kw)
with exclusive(cache):
    builtins.__import__=no_torch
    try:hits,_=produce(resources,works,cache)
    finally:builtins.__import__=original
assert hits==dict(encoded_cache_hits=len(works))
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
byref={r['resref']:r for r in resources}
@lru_cache(maxsize=20)
def resource(ref):
    r=byref[ref];route=routes[(r['witness']['animation_id'],ref)];s=cat['shards'][route['shard_index']];p=assets/Path(s['registry']).name
    assert file_sha(p).upper()==s['sha256'];info=leaves.inspect(p,include_frames=True)
    assert info['version']==7 and info['decode_rule_id']==3 and info['class_profile_id']==r['profile'].id
    leaf=info['resources'][0];assert leaf['cycles']==r['cycles'] and leaf['source_sha256'].lower()==r['source_sha256'].lower() and leaf['profile'].metadata()==r['profile'].metadata()
    return leaf
aux=[];frames=0
for r in resources:
    leaf=resource(r['resref']);assert len(leaf['frames'])==len(r['frames'])
    if not any(f<len(r['frames']) for c in r['cycles'] for f in c):aux.append(r['resref'])
    for row,f in zip(r['frames'],leaf['frames']):
        assert tuple(row['geometry'])==tuple(f['geometry']) and not {'S','M','A'}&set(f)
        with np.load(encoded/(row['key']+'.npz'),allow_pickle=False) as cached:
            assert np.array_equal(f['I'],cached['I']) and np.array_equal(f['F'],cached['F']) and f['dep']==cached['dep'].tobytes()
            r['profile'].validate(f['I'],f['F'],cached['guide'],cached['dep'])
        values,offsets=np.unique(works[row['key']]['frame'].indices,return_index=True);rep=np.full(256,0xffff,np.uint16);rep[values]=offsets
        assert np.array_equal(rep,f['representatives']);frames+=1
    print(json.dumps(dict(stage='leaf',resref=r['resref'],frames=frames)),flush=True)
assert frames==6422
# Preserve physical auxiliary geometry/cycles; exclude uncycled records only from native world-slot oracle.
raw=(isolated/'witnesses.oracle').read_bytes();pos=12;records=[];aux_frames=0
for r in resources:
    start=pos;aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',raw,pos);pos+=24+6144+2052
    assert ref.rstrip(b'\0').decode()==r['resref']
    for c in r['cycles']:n=struct.unpack_from('<I',raw,pos)[0];assert n==len(c);pos+=4+n*4
    pos+=nf*208
    if r['resref'] in aux:aux_frames+=nf
    else:records.append(raw[start:pos])
assert pos==len(raw);work=HERE/'work';work.mkdir(exist_ok=True);oracle=work/'world.oracle';oracle.write_bytes(struct.pack('<8sI',b'IEEQP7\0\0',len(records))+b''.join(records))
def native(label,command):
    p=subprocess.run(list(map(str,command)),capture_output=True,text=True,encoding='utf-8');(HERE/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode==0,(label,p.stdout[-1000:],p.stderr)
    report=json.loads(next(s for s in reversed(p.stdout.splitlines()) if s.startswith('{')));assert report['passed'];return report
if '--resume-native' in sys.argv:
    reports={name:json.loads(next(s for s in reversed((HERE/('native-'+name+'.log')).read_text().splitlines()) if s.startswith('{'))) for name in ('isolated','combined')}
    assert all(r['passed'] for r in reports.values())
else:
    reports={name:native('native-'+name,[WORK/'runtime-build/Release/iee_palette_partner_tests.exe',path,oracle]) for name,path in [('isolated',isolated),('combined',assets)]}
assert all(r['frames']==6422-aux_frames for r in reports.values())
palettes={}
for r in resources:
    pals=np.concatenate((r['profile'].fitting,np.full((6,256,1),255,np.uint8)),axis=2);pals[:,0]=0;pals[:,1,3]=127;palettes[r['resref']]=pals
cases=[];coverage=set();weapon_cases=0
for witness in load(HERE/'selection.json')['witnesses']:
    aid=int(witness['animation_id'],16);prefix={'0x2000':'MSIR','0x2100':'UVOL','0x2200':'MOGM','0x2300':'MDKN','0x8000':'MGNL','0x8100':'MHOB','0x8200':'MKOB'}[witness['animation_id']]
    for suffix in ('G1','G2','G1E','G2E'):
        ref=prefix+suffix;body=resource(ref)
        equips=[r for r in witness['refs'] if r.startswith(prefix) and r.endswith(suffix) and r!=ref]
        for seq,cycle in enumerate(body['cycles']):
            valid=[s for s,f in enumerate(cycle) if f<len(body['frames'])]
            if not valid:continue
            for slot in sorted({valid[0],valid[len(valid)//2],valid[-1]}):
                choices=[[(ref,cycle[slot])]]
                for er in equips:
                    e=resource(er)
                    if seq<len(e['cycles']) and slot<len(e['cycles'][seq]) and e['cycles'][seq][slot]<len(e['frames']):
                        choice=[(ref,cycle[slot]),(er,e['cycles'][seq][slot])]
                        choices.append(choice if seq%8<4 else choice[::-1]);weapon_cases+=1
                for sources in choices:
                    for pi in (0,5):
                        payload=bytearray(struct.pack('<I',len(sources)));g=[];images=[]
                        for rr,fi in sources:
                            leaf=resource(rr);f=leaf['frames'][fi];p=palettes[rr][pi];g.append(f['geometry']);images.append(leaf['profile'].decode(f['I'],f['F'],p));coverage.add((aid,rr))
                            payload.extend(struct.pack('<5I8s',aid,seq,slot,fi,leaf['profile'].kind,rr.encode().ljust(8,b'\0')));payload.extend(leaf['profile'].source.tobytes());payload.extend(p.tobytes())
                        left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
                        canvas=np.zeros(((bottom-top+2)*2,(right-left+2)*2,4),np.uint8)
                        for geometry,image in zip(g,images):
                            x=(-geometry[2]-left+1)*2;y=(-geometry[3]-top+1)*2;view=canvas[y:y+image.shape[0],x:x+image.shape[1]];mask=np.any(image!=0,axis=2);view[mask]=image[mask]
                        payload.extend(struct.pack('<4i',left,top,right,bottom));payload.extend(hashlib.sha256(canvas.tobytes()).digest());cases.append(payload)
assert {a for a,_ in coverage}=={int(w['animation_id'],16) for w in load(HERE/'selection.json')['witnesses']} and weapon_cases>0
co=work/'composite.oracle';co.write_bytes(struct.pack('<8sI',b'IEEOLD1\0',len(cases))+b''.join(cases))
composite=native('native-composite',[HERE/'composite_probe.exe',assets,co])
# Inherited V9 Ankheg still reconstructed by the exact new runtime reader.
ankheg=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated'
inherited=native('native-inherited-ankheg',[WORK/'runtime-build/Release/iee_palette_partner_tests.exe',assets,ankheg/'witnesses.oracle',ankheg/'sdf-composite.oracle'])
write_json(HERE/'verification.json',dict(passed=True,resources=65,frames=6422,all_geometry_cycles_profiles_representatives_cache_preserved=True,auxiliary_uncycled_resources=aux,auxiliary_frames_cache_verified=aux_frames,native_world=reports,native_composite=composite,weapon_cases=weapon_cases,coverage=[dict(animation_id=f'0x{a:04X}',resref=r) for a,r in sorted(coverage)],inherited_ankheg_V9=inherited,resume=hits,resume_torch_import_blocked=True,SDF=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,resources=65,frames=6422,native_composite=composite,auxiliary=aux)),flush=True)
