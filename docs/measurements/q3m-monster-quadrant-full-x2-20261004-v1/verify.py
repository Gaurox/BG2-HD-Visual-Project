"""Native K6 x3 formats, exact cycles/geometry, four-part assembly including empty parts."""
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
resources,works,plan=source_plan(HERE/'selection.json','monster_quadrant');assert plan==prod['plan']
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';encoded=cache/'encoded'/prod['encoder_namespace']
original=builtins.__import__
def no_torch(name,*a,**kw):
    if name.split('.')[0]=='torch':raise RuntimeError('Torch imported on cache-hit resume')
    return original(name,*a,**kw)
with exclusive(cache):
    builtins.__import__=no_torch
    try:resume,_=produce(resources,works,cache)
    finally:builtins.__import__=original
assert resume==dict(encoded_cache_hits=12476)
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
source={(r['witness']['animation_id'],r['resref']):r for r in resources}
@lru_cache(maxsize=28)
def resource(aid,ref):
    r=source[(aid,ref)];s=cat['shards'][routes[(aid,ref)]['shard_index']];p=assets/Path(s['registry']).name;assert file_sha(p).upper()==s['sha256']
    info=leaves.inspect(p,include_frames=True);assert info['version']==7 and info['class_profile_id']==8 and info['decode_rule_id']==3
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
assert frames==12928 and len(empty)==65
def native(label,cmd):
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,encoding='utf-8');(HERE/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode==0,(label,p.stdout[-2000:],p.stderr)
    report=json.loads(next(s for s in reversed(p.stdout.splitlines()) if s.startswith('{')));assert report['passed'];return report
reports={name:native('native-'+name,[WORK/'runtime-build/Release/iee_palette_partner_tests.exe',path,isolated/'witnesses.oracle']) for name,path in [('isolated',isolated),('combined',assets)]}
assert all(r['frames']==12928 for r in reports.values())
# Quadrant is a native per-cell renderer. The offline assembly oracle checks
# common origins/cycle selection/ordered four-part pixels; it does not add a CPU compositor hook.
cases=[];empty_cases=0;coverage=set();group_cycles=0
for witness in load(HERE/'selection.json')['witnesses']:
    aid=witness['animation_id']
    for group in witness['multipart_groups']:
        rr=[resource(aid,ref) for ref in group]
        for seq in range(min(len(r['cycles']) for r in rr)):
            slots=[slot for slot in range(min(len(r['cycles'][seq]) for r in rr)) if all(r['cycles'][seq][slot]<len(r['frames']) for r in rr)]
            if not slots:continue
            group_cycles+=1;chosen={slots[0],slots[len(slots)//2],slots[-1]}
            chosen.update(slot for slot in slots if any(not r['frames'][r['cycles'][seq][slot]]['I'].size for r in rr))
            for slot in sorted(chosen):
                ff=[r['frames'][r['cycles'][seq][slot]] for r in rr];g=[f['geometry'] for f in ff if f['I'].size]
                if not g:continue
                left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
                for pi in (0,5):
                    payload=bytearray(struct.pack('<I',4));canvas=np.zeros(((bottom-top+2)*2,(right-left+2)*2,4),np.uint8)
                    if len(g)<4:empty_cases+=1
                    for ref,r,f in zip(group,rr,ff):
                        sr=source[(aid,ref)];pal=np.column_stack((sr['profile'].fitting[pi],np.full(256,255,np.uint8)));pal[0]=0;pal[1,3]=127;fi=r['cycles'][seq][slot]
                        payload.extend(struct.pack('<5I8s',int(aid,16),seq,slot,fi,r['profile'].kind,ref.encode().ljust(8,b'\0')));payload.extend(r['profile'].source.tobytes());payload.extend(pal.tobytes());coverage.add((aid,ref))
                        if f['I'].size:
                            image=r['profile'].decode(f['I'],f['F'],pal);a=f['geometry'];x=(-a[2]-left+1)*2;y=(-a[3]-top+1)*2;dest=canvas[y:y+image.shape[0],x:x+image.shape[1]];mask=np.any(image!=0,axis=2);dest[mask]=image[mask]
                    payload.extend(struct.pack('<4i',left,top,right,bottom));payload.extend(hashlib.sha256(canvas.tobytes()).digest());cases.append(payload)
assert len(coverage)==132 and empty_cases>0
work=HERE/'work';work.mkdir(exist_ok=True);oracle=work/'composite.oracle';oracle.write_bytes(struct.pack('<8sI',b'IEEOLD1\0',len(cases))+b''.join(cases))
composite=native('native-composite',[HERE/'composite_probe.exe',assets,oracle])
ankheg=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated'
inherited=native('native-inherited-ankheg',[WORK/'runtime-build/Release/iee_palette_partner_tests.exe',assets,ankheg/'witnesses.oracle',ankheg/'sdf-composite.oracle'])
write_json(HERE/'verification.json',dict(passed=True,resources=132,unique_native_BAM=36,frames=12928,original_native_frames=3552,all_geometry_cycles_profiles_representatives_cache_preserved=True,native_world=reports,native_composite=composite,assembly_scope='offline ordered four-quadrant check; runtime remains native per-cell',empty_native_declarations=empty,assembly_cases_with_empty_parts=empty_cases,native_group_cycles=group_cycles,coverage=[dict(animation_id=a,resref=r) for a,r in sorted(coverage)],inherited_ankheg_V9=inherited,resume=resume,resume_torch_import_blocked=True,SDF=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,resources=132,frames=12928,native_composite=composite,empty_cases=empty_cases)),flush=True)
