"""All physical V9 pixels/K6/encodings/slots; complete guard composites and inherited Ankheg."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
from functools import lru_cache
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves,run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
gen=load(HERE/'current-generation.json');assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites';exe=WORK/'runtime-build/Release/iee_palette_partner_tests.exe'
def native(label,command):
    r=subprocess.run(list(map(str,command)),capture_output=True,text=True,encoding='utf-8');(HERE/(label+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    assert r.returncode==0,(label,r.stdout[-1200:],r.stderr)
    report=json.loads(next(s for s in reversed(r.stdout.splitlines()) if s.startswith('{')));assert report['passed'];return report
reports=[]
for n in range(8):
    if '--resume' in sys.argv:
        lines=(HERE/f'native-physical-{n}.log').read_text(encoding='utf-8').splitlines()
        reports.append(json.loads(next(s for s in reversed(lines) if s.startswith('{'))));assert reports[-1]['passed']
    else:reports.append(native(f'native-physical-{n}',[exe,assets,HERE/f'work/physical-{n}.oracle',HERE/f'work/sdf-{n}.oracle']))
    print(json.dumps(dict(stage='native-V9',group=n,passed=True)),flush=True)
assert sum(r['resources'] for r in reports)==974
# Original palettes and profile contracts from immutable native physical records.
palettes={}
for n in range(8):
    raw=(HERE/f'work/physical-{n}.oracle').read_bytes();pos=12
    for _ in range(struct.unpack_from('<I',raw,8)[0]):
        aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',raw,pos);pos+=24;ref=ref.rstrip(b'\0').decode()
        palettes[ref]=np.frombuffer(raw,np.uint8,6144,pos).reshape(6,256,4).copy();pos+=6144+2052
        for __ in range(nc):count=struct.unpack_from('<I',raw,pos)[0];pos+=4+count*4
        pos+=nf*208
    assert pos==len(raw)
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256']);routes={r['resref']:r for r in cat['directory'] if r['animation_id']=='0x6405'}
@lru_cache(maxsize=32)
def resource(ref):return leaves.inspect(assets/Path(cat['shards'][routes[ref]['shard_index']]['registry']).name,include_frames=True)['resources'][0]
cases=[];coverage=set();shadow_only=0
for aid in (0x6405,0x6406):
    for ref in sorted(r for r in routes if r.startswith('MDGU')):
        body=resource(ref);suffix=ref[5:];shadow_ref='CSHD'+suffix;assert shadow_ref in routes;shadow=resource(shadow_ref)
        for sequence,cycle in enumerate(body['cycles']):
            valid=[s for s,f in enumerate(cycle) if f<len(body['frames'])]
            if not valid:continue
            slots=sorted({valid[0],valid[len(valid)//2],valid[-1]}|({30,31,32}&set(valid) if sequence==16 and suffix=='G1' else set()))
            for slot in slots:
                # Native empty E cycles do not draw a shadow layer; never invent a slot.
                has_shadow=sequence<len(shadow['cycles']) and slot<len(shadow['cycles'][sequence]) and shadow['cycles'][sequence][slot]<len(shadow['frames'])
                basics=([(shadow_ref,shadow['cycles'][sequence][slot])] if has_shadow else [])+[(ref,cycle[slot])];equipped=basics[:]
                for token in ('MC','D1','H0'):
                    er='WPM'+token+suffix
                    if er in routes:
                        e=resource(er)
                        if sequence<len(e['cycles']) and slot<len(e['cycles'][sequence]):
                            ef=e['cycles'][sequence][slot]
                            if ef<len(e['frames']):equipped.append((er,ef))
                choices=[basics]+([equipped] if len(equipped)>len(basics) else [])
                if len(equipped)>len(basics) and sequence%8>=4:
                    start=int(has_shadow);choices.append(equipped[:start]+equipped[start+1:]+equipped[start:start+1])
                for sources in choices:
                    for pi in (0,5):
                        payload=bytearray(struct.pack('<I',len(sources)));frames=[];images=[]
                        for rr,fi in sources:
                            r=resource(rr);f=r['frames'][fi];frames.append(f);palette=palettes[rr][pi];images.append(r['profile'].decode(f['I'],f['F'],palette))
                            payload.extend(struct.pack('<5I8s',aid,sequence,slot,fi,r['profile'].kind,rr.encode().ljust(8,b'\0')));payload.extend(r['profile'].source.tobytes());payload.extend(palette.tobytes());coverage.add((aid,rr))
                        g=[f['geometry'] for f in frames];left=min(-a[2] for a in g);top=min(-a[3] for a in g);right=max(a[0]-a[2] for a in g);bottom=max(a[1]-a[3] for a in g)
                        h,w=(bottom-top+2)*2,(right-left+2)*2;plain=np.zeros((h,w,4),np.uint8);encoded=plain.copy()
                        for f,rgba in zip(frames,images):
                            _,_,cx,cy,_=f['geometry'];x=(-cx-left+1)*2;y=(-cy-top+1)*2
                            view=plain[y:y+rgba.shape[0],x:x+rgba.shape[1]];active=np.any(rgba!=0,axis=2);view[active]=rgba[active]
                            s,m=f['S'],f['M'];extended=np.zeros((*s.shape,4),np.uint8);material=m!=0xffffffff;extended[material,:3]=rgba.reshape(-1,4)[m[material],:3];extended[...,3]=s
                            x0=max(0,x-6);y0=max(0,y-6);x1=min(w,x-6+s.shape[1]);y1=min(h,y-6+s.shape[0])
                            view=extended[y0-y+6:y1-y+6,x0-x+6:x1-x+6];dest=encoded[y0:y1,x0:x1];take=view[...,3]>=dest[...,3];dest[take]=view[take]
                        active=plain[...,3]==255;encoded[active,:3]=plain[active,:3];encoded[...,3]|=(plain[...,3]==127).astype(np.uint8)*128
                        if sources==basics:assert not np.any(active);shadow_only+=1
                        payload.extend(struct.pack('<4i',left,top,right,bottom));payload.extend(hashlib.sha256(plain.tobytes()).digest());payload.extend(hashlib.sha256(encoded.tobytes()).digest());cases.append(payload)
oracle=HERE/'work/composite.oracle';oracle.write_bytes(struct.pack('<8sI',b'IEEOLD1\0',len(cases))+b''.join(cases))
composite=native('native-composite',[HERE/'composite_probe.exe',assets,oracle])
parent=ROOT/'sprite/.work/q3m-character-old-runtime-fix-x2-20261004-v1/combined/iee-assets/creature-sprites'
regression=native('native-parent-regression',[HERE/'composite_probe.exe',parent,'regression']);assert regression['old_catalog_missing_shadows']==2
ankheg=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated'
inherited=native('native-inherited-ankheg',[exe,assets,ankheg/'witnesses.oracle',ankheg/'sdf-composite.oracle'])
assert inherited['resources']==12 and inherited['frames']==516
assert sum(r['frames'] for r in reports)==gen['frames']
write_json(HERE/'verification.json',dict(passed=True,resources=974,frames=gen['frames'],native_physical=reports,native_composite=composite,shadow_only_composites=shadow_only,coverage=[dict(animation_id=f'0x{a:04X}',resref=r) for a,r in sorted(coverage)],parent_missing_guard_shadows=regression,inherited_ankheg_V9=inherited,SDF=True,ingame_QA=False,release=False))
print(json.dumps(dict(passed=True,resources=974,frames=gen['frames'],composite=composite,shadow_only=shadow_only)),flush=True)
