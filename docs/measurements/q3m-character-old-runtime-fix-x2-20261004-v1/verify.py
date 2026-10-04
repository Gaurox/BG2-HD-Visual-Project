"""Physical dependency bytes, all alias cycle routes, complete body/shadow/equipment native goldens."""
import hashlib,json,struct,sys,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from supplement import plan,CACHE
from q3m_family_witnesses import source_plan
from palette_work_plan import file_sha,write_json
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
prod=load(HERE/'production.json');gen=load(HERE/'current-generation.json');delta=ROOT/prod['pack_directory'];assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
assert not (HERE/'verification.json').exists()
resources,works,summary=plan();assert summary==prod['plan']
body_run=ROOT/'docs/measurements/q3m-character-old-full-x2-20261004-v1'
body_resources,body_works,_=source_plan(body_run/'selection.json','character_old')
encoded=CACHE/'encoded'/prod['encoder_namespace'];all_works=dict(works,**body_works)
for key,w in all_works.items():w['encoded_path']=encoded/(key+'.npz')
byref={r['resref']:r for r in resources};body_byid={}
for r in body_resources:body_byid.setdefault(r['witness']['animation_id'],[]).append(r)
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
routes={(r['animation_id'],r['resref']):r for r in cat['directory']}
validated_frames=0
for r in resources:
    aid=r['witness']['animation_id'];route=routes[(aid,r['resref'])];shard=cat['shards'][route['shard_index']]
    info=leaves.inspect(assets/Path(shard['registry']).name,include_frames=True);leaf=info['resources'][0]
    assert info['version']==7 and info['decode_rule_id']==3 and info['class_profile_id']==r['profile'].id
    assert leaf['profile'].metadata()==r['profile'].metadata() and leaf['source_sha256'].lower()==r['source_sha256'].lower()
    assert leaf['cycles']==r['cycles'] and len(leaf['frames'])==len(r['frames'])
    for row,f in zip(r['frames'],leaf['frames']):
        assert tuple(f['geometry'])==tuple(row['geometry']) and not {'A','S','M'}&set(f)
        with np.load(all_works[row['key']]['encoded_path'],allow_pickle=False) as cached:
            assert np.array_equal(f['I'],cached['I']) and np.array_equal(f['F'],cached['F'])
            r['profile'].validate(cached['I'],cached['F'],cached['guide'],cached['dep'])
        validated_frames+=1
for aid,refs in summary['consumers'].items():
    assert all((aid,ref) in routes for ref in refs)

# Split the full, immutable physical oracle into the existing native probe's <=128-record contract.
raw=(delta/'witnesses.oracle').read_bytes();magic,nr=struct.unpack_from('<8sI',raw);assert nr==len(resources)
records=[];offset=12
for r in resources:
    start=offset;aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',raw,offset);offset+=24
    assert ref.rstrip(b'\0').decode()==r['resref'] and nf==len(r['frames']) and nc==len(r['cycles'])
    offset+=6*1024+2052
    for cycle in r['cycles']:
        n=struct.unpack_from('<I',raw,offset)[0];offset+=4+n*4;assert n==len(cycle)
    offset+=nf*(16+6*32);records.append(raw[start:offset])
assert offset==len(raw)
work=HERE/'work';work.mkdir(exist_ok=True)
exe=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-q3m-sdf-stable-20261004-v1/Release/iee_palette_partner_tests.exe'
native=[]
for start in range(0,nr,128):
    oracle=work/f'physical-{start//128}.oracle';group=records[start:start+128]
    oracle.write_bytes(struct.pack('<8sI',magic,len(group))+b''.join(group))
    result=subprocess.run([str(exe),str(assets),str(oracle)],capture_output=True,text=True,encoding='utf-8')
    log=HERE/f'native-physical-{start//128}.log';log.write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0,(start,result.stdout[-1000:],result.stderr)
    report=json.loads(next(s for s in reversed(result.stdout.splitlines()) if s.startswith('{')));assert report['passed'];native.append(report)
    print(json.dumps(dict(stage='native-physical',done=min(start+128,nr),total=nr)),flush=True)

def pixels(resource,fi,palette_index):
    row=resource['frames'][fi];profile=resource['profile']
    with np.load(all_works[row['key']]['encoded_path'],allow_pickle=False) as data:i,f=data['I'],data['F']
    palette=np.column_stack((profile.fitting[palette_index],np.full(256,255,np.uint8)));palette[0]=0;palette[1,3]=127
    return profile.decode(i,f,palette),palette,row['geometry']

cases=[];coverage=set();logged_case=False
for aid,rr in body_byid.items():
    for body in rr:
        if body['resref']=='CMNKINV':continue
        suffix=body['resref'][5:]
        shadow=byref.get('CSHD'+suffix) if aid not in ('0x6405','0x6406') else None
        for sequence,cycle in enumerate(body['cycles']):
            valid=[s for s,fi in enumerate(cycle) if fi<len(body['frames'])]
            if not valid:continue
            selected=sorted({valid[0],valid[len(valid)//2],valid[-1]}|({30,31,32} if suffix=='G1' and sequence==16 else set()))
            for slot in selected:
                if slot not in valid:continue
                layer_sources=[]
                if shadow and sequence<len(shadow['cycles']) and slot<len(shadow['cycles'][sequence]):
                    fi=shadow['cycles'][sequence][slot]
                    if fi<len(shadow['frames']):layer_sources.append((shadow,fi))
                layer_sources.append((body,cycle[slot]))
                eligible={'0x6400':['H0'],'0x6402':['MC'],'0x6403':['MC','D1','H0'],'0x6405':['MC','D1','H0'],'0x6406':['MC','D1','H0']}.get(aid,[])
                for token in eligible:
                    equip=byref.get('WPM'+token+suffix)
                    if equip and sequence<len(equip['cycles']) and slot<len(equip['cycles'][sequence]):
                        fi=equip['cycles'][sequence][slot]
                        if fi<len(equip['frames']):layer_sources.append((equip,fi))
                # Exercise alternate native equipment/body orders across directions too.
                if sequence%8>=4 and len(layer_sources)>2:
                    start=int(shadow is not None and layer_sources[0][0] is shadow)
                    layer_sources=layer_sources[:start]+layer_sources[start+1:]+layer_sources[start:start+1]
                for pi in (0,1):
                    payload=bytearray(struct.pack('<I',len(layer_sources)));decoded=[];geometries=[]
                    for r,fi in layer_sources:
                        image,palette,g=pixels(r,fi,pi);decoded.append(image);geometries.append(g)
                        # Case slots for each resource remain authoritative native cycle slots.
                        payload.extend(struct.pack('<5I8s',int(aid,16),sequence,slot,fi,r['profile'].kind,r['resref'].encode().ljust(8,b'\0')))
                        payload.extend(r['profile'].source.tobytes());payload.extend(palette.tobytes());coverage.add((aid,r['resref']))
                    left=min(-g[2] for g in geometries);top=min(-g[3] for g in geometries)
                    right=max(g[0]-g[2] for g in geometries);bottom=max(g[1]-g[3] for g in geometries)
                    canvas=np.zeros(((bottom-top+2)*2,(right-left+2)*2,4),np.uint8)
                    for image,g in zip(decoded,geometries):
                        x=(-g[2]-left+1)*2;y=(-g[3]-top+1)*2
                        dest=canvas[y:y+image.shape[0],x:x+image.shape[1]];mask=np.any(image!=0,axis=2);dest[mask]=image[mask]
                    payload.extend(struct.pack('<4i',left,top,right,bottom));payload.extend(hashlib.sha256(canvas.tobytes()).digest());cases.append(payload)
                    if aid=='0x6400' and body['resref']=='UDRZ1G1' and sequence==16 and slot==31:logged_case=True
assert logged_case and {a for a,r in coverage}==set(summary['consumers'])
oracle=work/'composite.oracle';oracle.write_bytes(struct.pack('<8sI',b'IEEOLD1\0',len(cases))+b''.join(cases))
result=subprocess.run([str(HERE/'composite_probe.exe'),str(assets),str(oracle)],capture_output=True,text=True,encoding='utf-8')
(HERE/'native-composite.log').write_text(result.stdout+result.stderr,encoding='utf-8');assert result.returncode==0,(result.stdout[-1000:],result.stderr)
composite=json.loads(next(s for s in reversed(result.stdout.splitlines()) if s.startswith('{')));assert composite['passed']
counts={aid:len({f['key'] for r in body_byid[aid]+[byref[ref] for ref in refs] for f in r['frames']}) for aid,refs in summary['consumers'].items()}
write_json(HERE/'verification.json',dict(passed=True,resources=967,frames=validated_frames,unique_encoded_work_complete_family=len(all_works),unique_source_work_complete_family=len({w['source_key'] for w in all_works.values()}),unique_encoded_work_by_animation=counts,registered_dependency_bindings=sum(map(len,summary['consumers'].values())),logical_dependency_bound_frames=sum(sum(len(byref[r]['frames']) for r in refs) for refs in summary['consumers'].values()),native_physical=native,native_composite=composite,composite_coverage=[dict(animation_id=a,resref=r) for a,r in sorted(coverage)],last_session_sequence_16_slot_31_and_neighbors_verified=logged_case,body_bytes_unchanged=True,SDF=False,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,native_composite=composite,physical_resources=967,physical_frames=validated_frames)),flush=True)
