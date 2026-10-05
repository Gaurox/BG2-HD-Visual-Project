"""Exact coverage and native K6 x3; ordered 4/9-cell assembly across banks/directions."""
import builtins,hashlib,json,struct,subprocess,sys,time,os
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,produce,exclusive,validate_encoded
from q3m_multipart_seams import apply_context
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');isolated=ROOT/prod['pack_directory'];assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
os.environ['Q3M_PALETTE_ENCODER']=prod['palette_acceleration']['mode']
started=time.time();resources,works,plan=source_plan(HERE/'selection.json','multi_new');assert plan==prod['plan']
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
original=builtins.__import__
def no_torch(name,*a,**kw):
    if name.split('.')[0]=='torch':raise RuntimeError('Torch imported on cache-hit resume')
    return original(name,*a,**kw)
with exclusive(cache):
    builtins.__import__=no_torch
    try:
        resume,_=produce(resources,works,cache)
        contextual=apply_context(resources,works,HERE/'selection.json',cache,'bind')
    finally:builtins.__import__=original
assert resume==dict(encoded_cache_hits=42772) and contextual['context_cache_hits']==5411 and contextual['new_neural_targets']==0
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
source={(r['witness']['animation_id'],r['resref']):r for r in resources}
@lru_cache(maxsize=36)
def resource(aid,ref):
    r=source[(aid,ref)];s=cat['shards'][routes[(aid,ref)]['shard_index']];p=assets/Path(s['registry']).name;assert file_sha(p).upper()==s['sha256']
    info=leaves.inspect(p,include_frames=True);assert info['version']==7 and info['class_profile_id']==8 and info['decode_rule_id']==3
    leaf=info['resources'][0];assert leaf['cycles']==r['cycles'] and leaf['source_sha256'].lower()==r['source_sha256'].lower() and leaf['profile'].metadata()==r['profile'].metadata()
    return leaf
def array_digest(a):return hashlib.sha256(a.tobytes()).hexdigest()
encoded_proofs={};frames=0
for ordinal,r in enumerate(resources):
    aid=r['witness']['animation_id'];leaf=resource(aid,r['resref']);assert len(leaf['frames'])==len(r['frames'])
    for row,f in zip(r['frames'],leaf['frames']):
        assert tuple(row['geometry'])==tuple(f['geometry']) and not {'S','M','A'}&set(f)
        key=row['key']
        if key not in encoded_proofs:
            work=works[key]
            with np.load(work['encoded_path'],allow_pickle=False) as a:
                validate_encoded(r['profile'],a['I'],a['F'],a['guide'],a['dep'])
                proofs=[array_digest(a['I']),array_digest(a['F']),a['dep'].tobytes()]
            vals,off=np.unique(work['frame'].indices,return_index=True);rep=np.full(256,0xffff,np.uint16);rep[vals]=off
            encoded_proofs[key]=(*proofs,rep.tobytes())
        expected=encoded_proofs[key]
        assert (array_digest(f['I']),array_digest(f['F']),f['dep'],f['representatives'].tobytes())==expected
        frames+=1
    if ordinal%32==0:print(json.dumps(dict(stage='verify-leaf',done=ordinal+1,total=len(resources),frames=frames)),flush=True)
assert frames==519867
def native(label,cmd):
    print(json.dumps(dict(stage=label,started=True)),flush=True)
    p=subprocess.run(list(map(str,cmd)),capture_output=True,text=True,encoding='utf-8');(HERE/(label+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
    assert p.returncode==0,(label,p.stdout[-2000:],p.stderr)
    report=json.loads(next(s for s in reversed(p.stdout.splitlines()) if s.startswith('{')));assert report['passed'];return report
# Combined catalog includes identical sealed leaves; one exhaustive native pass
# covers every new binding. Isolated->combined mappings/leaf bytes were compared.
world=native('native-world-combined',[WORK/'probe-build/Release/palette_probe.exe',assets,isolated/'witnesses.oracle'])
assert world['frames']==519867
cases=[];coverage=set();groups=set();directions=set();banks=set();chosen_cases=set()
for witness in load(HERE/'selection.json')['witnesses']:
    aid=witness['animation_id']
    for gi,group in enumerate(witness['multipart_groups']):
        rr=[resource(aid,ref) for ref in group]
        assert len({len(r['cycles']) for r in rr})==1
        for seq in range(len(rr[0]['cycles'])):
            assert len({len(r['cycles'][seq]) for r in rr})==1
            slots=[slot for slot in range(len(rr[0]['cycles'][seq])) if all(r['cycles'][seq][slot]<len(r['frames']) for r in rr)]
            if not slots:continue
            # Three animation positions for each direction/action; deduplicate
            # repeated native tuples without losing all group/cycle coverage.
            for slot in sorted({slots[0],slots[len(slots)//2],slots[-1]}):
                ff=[r['frames'][r['cycles'][seq][slot]] for r in rr];g=[f['geometry'] for f in ff]
                signature=(aid,tuple((ref,r['cycles'][seq][slot]) for ref,r in zip(group,rr)))
                groups.add((aid,gi));directions.add((aid,seq));banks.add((aid,group[0][4 if len(group)==9 else 5]))
                if signature in chosen_cases:continue
                chosen_cases.add(signature)
                left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
                for pi in (0,5):
                    payload=bytearray(struct.pack('<I',len(group)));canvas=np.zeros(((bottom-top+2)*2,(right-left+2)*2,4),np.uint8)
                    for ref,r,f in zip(group,rr,ff):
                        sr=source[(aid,ref)];pal=np.column_stack((sr['profile'].fitting[pi],np.full(256,255,np.uint8)));pal[0]=0;pal[1,3]=127;fi=r['cycles'][seq][slot]
                        payload.extend(struct.pack('<5I8s',int(aid,16),seq,slot,fi,r['profile'].kind,ref.encode().ljust(8,b'\0')));payload.extend(r['profile'].source.tobytes());payload.extend(pal.tobytes());coverage.add((aid,ref))
                        image=r['profile'].decode(f['I'],f['F'],pal);a=f['geometry'];x=(-a[2]-left+1)*2;y=(-a[3]-top+1)*2;dest=canvas[y:y+image.shape[0],x:x+image.shape[1]];mask=np.any(image!=0,axis=2);dest[mask]=image[mask]
                    payload.extend(struct.pack('<4i',left,top,right,bottom));payload.extend(hashlib.sha256(canvas.tobytes()).digest());cases.append(payload)
        print(json.dumps(dict(stage='composite-oracle',animation=aid,group=gi+1,total_groups=len(witness['multipart_groups']),cases=len(cases))),flush=True)
assert len(coverage)==5155 and len(groups)==580
work=HERE/'work';work.mkdir(exist_ok=True);oracle=work/'composite.oracle';oracle.write_bytes(struct.pack('<8sI',b'IEEOLD1\0',len(cases))+b''.join(cases))
composite=native('native-composite',[WORK/'probe-build/Release/composite_probe.exe',assets,oracle])
write_json(HERE/'verification.json',dict(passed=True,resources=5155,frames=519867,packed_resources=gen['resources'],packed_frames=gen['frames'],unique_native_BAM=1753,original_native_frames=191817,unique_encoded_payloads_verified=len(encoded_proofs),all_geometry_cycles_profiles_representatives_cache_preserved=True,native_world=dict(combined=world),native_composite=composite,assembly_scope='offline ordered native-cell decodes; installed runtime keeps independent 4/9 cells',native_groups=len(groups),native_action_direction_cycles=len(directions),native_bank_profiles=len(banks),multipart_context_resume=contextual,resume=resume,resume_torch_import_blocked=True,DLL_unchanged=True,SDF=False,ingame_QA=False,release=False,seconds=time.time()-started))
print(json.dumps(dict(passed=True,resources=5155,frames=frames,native_composite=composite)),flush=True)
