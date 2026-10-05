"""Read-only complete MultiNew proposal; exact native palettes/pixel keys/cache.

SQL distinct work avoids expanding 519,867 occurrences. No Q3m production,
GPU import, game launch, installation or mutation of canonical producers.
"""
import csv,hashlib,json,runpy,sqlite3,struct,sys,zlib
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from analyze_sprite_frame_dedup import ro
from analyze_playable_frame_dedup import identities
from palette_q3m_partners import Profile
from palette_work_plan import file_sha,write_json
from q3m_family_witnesses import bmp_palette,validate_encoded
from run_creature_sprite_x2 import KeyIndex,canonical_bam
from workspace_paths import get_path
assert not (HERE/'analysis.json').exists(),'fresh analysis required'
rows=[r for r in csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig')) if r['engine_family']=='multi_new']
inventory={r['animation_id']:r for r in csv.DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
pointer=json.loads((ROOT/'sprite/index/q3m-source-work-plan.json').read_text());dbpath=ROOT/pointer['path']
assert dbpath.stat().st_size==pointer['bytes'] and file_sha(dbpath)==pointer['sha256'];db=ro(dbpath)
refs=sorted({ref for r in rows for ref in r['bam_resrefs'].split(';') if ref})
resources={r['resref']:r for r in db.execute('SELECT * FROM resources') if r['resref'] in set(refs)}
assert len(resources)==len(refs)==1753
frames={ref:[dict(r) for r in db.execute('SELECT f.frame_index,f.work_id,f.center_x,f.center_y,q.width,q.height,q.input_key FROM frames f JOIN source_work_queue q USING(work_id) WHERE f.resource_id=? ORDER BY f.frame_index',(resources[ref]['resource_id'],))] for ref in refs}
cycles={ref:[list(struct.unpack(f"<{c['slot_count']}H",c['frame_indices_le_u16'])) for c in db.execute('SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index',(resources[ref]['resource_id'],))] for ref in refs}
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);bam_map=index.resource_map(1000);bmp_map=index.resource_map(1)
oracle_mod=runpy.run_path(str(ROOT/'docs/measurements/q3m-monster-contract-x2-20261002-v1/build_contract.py'));oracle=oracle_mod['NativeFixed']((game/'BaldurReal.exe').read_bytes())
profiles={};palette_sources=[];witnesses=[];works={};source_verified=[];models={};contexts={};bindings={};alias_conflicts=[];heterogeneous_groups=[]
@lru_cache(maxsize=18000)
def input_for(wid):
    r=db.execute('SELECT * FROM source_work_queue WHERE work_id=?',(wid,)).fetchone()
    a=np.frombuffer(zlib.decompress(r['indices_zlib']),np.uint8).reshape(r['height'],r['width'])
    assert 0<a.size<65535 and r['transparent_index']==0
    return r,a,np.unique(a[a!=0])
def profile_for(p):
    k=p.tobytes()
    if k not in profiles:
        fits=np.stack([oracle.realize(p,flags,tint)[:,:3] for _,flags,tint in oracle_mod['FITS']])
        profiles[k]=Profile(0,p,fits)
    return profiles[k]
def native_groups(prefix,names,parts):
    grouped=defaultdict(list)
    for ref in names:
        if parts==9:
            assert len(ref)==8 and ref[5] in '123456789'
            signature=ref[:5]+ref[6:]
        else:
            assert ref.startswith(prefix+'G') and ref[6] in '1234'
            signature=ref[:6]+ref[7:]
        grouped[signature].append(ref)
    groups=[sorted(v) for _,v in sorted(grouped.items())]
    assert all(len(g)==parts for g in groups),'native tile group incomplete'
    return groups
for row in rows:
    aid=row['animation_id'];ini=json.loads(inventory[aid]['ini_sections_json']);native=ini['multi_new'];prefix=native['resref'];parts=int(native['quadrants']);names=row['bam_resrefs'].split(';')
    assert names!=[''] and parts in (4,9) and native['false_color']=='0'
    assert {r['resref'] for r in db.execute('SELECT r.resref FROM animation_resources ar JOIN resources r USING(resource_id) WHERE ar.animation_id=?',(aid,))}==set(names)
    groups=native_groups(prefix,names,parts)
    assert {k for k in bam_map if k.startswith(prefix)}==set(names),'extra or absent source BAM'
    w=dict(family='multi_new',animation_id=aid,name=row['ids_symbol'],owner=5,native_kind=0,refs=names,multipart_groups=groups,native_parts=parts)
    replacement=ini['general'].get('new_palette');overrides_by_bank={}
    if replacement:
        w['palette_overrides_by_bank']={}
        for bank in range(1,6):
            actual=replacement+str(bank);p=game/'override'/(actual+'.bmp')
            if p.exists():raw=p.read_bytes();origin='override'
            else:
                assert actual in bmp_map,'native bank BMP absent: '+actual
                raw,origin=index.resolve(bmp_map[actual])
            overrides_by_bank[bank]=bmp_palette(raw);sha=hashlib.sha256(raw).hexdigest()
            w['palette_overrides_by_bank'][str(bank)]=dict(resref=actual,sha256=sha)
            palette_sources.append(dict(animation_id=aid,bank=bank,resref=actual,sha256=sha,source=origin))
    wr={};wkeys=set()
    for ref in names:
        r=resources[ref];original=np.frombuffer(r['palette_bgra'],np.uint8).reshape(256,4);override=overrides_by_bank.get(int(ref[4])) if replacement else None;p=override if override is not None else original;profile=profile_for(p);keys={}
        for wid in {f['work_id'] for f in frames[ref]}:
            q,a,used=input_for(wid);ik,original_key,*_=identities(a,original[:,[2,1,0]],0)
            assert original_key.hex()==q['source_work_key'] and ik.hex()==q['input_key']
            sk=identities(a,p[:,[2,1,0]],0)[1] if override is not None else original_key
            ek=hashlib.sha256(bytes.fromhex(profile.identity)+sk).hexdigest();keys[wid]=ek;wkeys.add(ek)
            works.setdefault(ek,dict(profile=profile,input_key=ik,source_key=sk,used=used,input_indices=a,shape=(a.shape[0]*2,a.shape[1]*2)))
        wr[ref]=dict(profile=profile,keys=keys)
    for group in groups:
        fps={hashlib.sha256(wr[ref]['profile'].fitting.tobytes()).hexdigest() for ref in group}
        if len(fps)>1:heterogeneous_groups.append(dict(animation_id=aid,refs=group,native_palette_contracts=len(fps)))
        assert len({len(cycles[ref]) for ref in group})==1
        for sequence in range(len(cycles[group[0]])):
            assert len({len(cycles[ref][sequence]) for ref in group})==1
            for slot in range(len(cycles[group[0]][sequence])):
                nodes=[]
                for ref in group:
                    fi=cycles[ref][sequence][slot]
                    if fi>=len(frames[ref]):break
                    f=frames[ref][fi];ek=wr[ref]['keys'][f['work_id']];geom=(f['width'],f['height'],f['center_x'],f['center_y'],0)
                    nodes.append((ref,fi,ek,geom))
                if len(nodes)!=parts:continue
                ck=hashlib.sha256(json.dumps([(n[2],n[3]) for n in nodes],sort_keys=True).encode()).hexdigest();contexts.setdefault(ck,parts)
                for part,n in enumerate(nodes):
                    binding=(aid,n[0],n[1]);value=(ck,part)
                    if binding in bindings and bindings[binding]!=value:alias_conflicts.append(dict(animation_id=aid,resref=n[0],frame_index=n[1],previous=bindings[binding],new=value))
                    else:bindings[binding]=value
    w['proposal_unique_encoded_work']=len(wkeys);witnesses.append(w)
    if prefix not in models:
        digest=hashlib.sha256()
        for ref in sorted(names):
            digest.update(ref[len(prefix):].encode()+b'\0')
            for f in frames[ref]:digest.update(bytes.fromhex(f['input_key'])+struct.pack('<IIii',f['width'],f['height'],f['center_x'],f['center_y']))
            digest.update(json.dumps(cycles[ref],separators=(',',':')).encode())
        models[prefix]=dict(prefix=prefix,native_parts=parts,BAM=len(names),native_frames=sum(len(frames[n]) for n in names),base_unique_source_work=len({f['work_id'] for n in names for f in frames[n]}),indices_geometry_cycles_sha256=digest.hexdigest(),variants=[])
    models[prefix]['variants'].append(dict(animation_id=aid,name=row['ids_symbol'],palette=replacement or 'native BAM',unique_encoded_work=len(wkeys)))
    print(json.dumps(dict(stage='variant',animation_id=aid,unique_encoded_work=len(wkeys))),flush=True)
for ref in refs:
    path=game/'override'/(ref+'.bam')
    if path.exists():raw=path.read_bytes();origin='override'
    else:
        assert ref in bam_map
        raw,origin=index.resolve(bam_map[ref])
    raw,_=canonical_bam(raw);sha=hashlib.sha256(raw).hexdigest();assert sha.lower()==resources[ref]['canonical_sha256'].lower(),ref
    source_verified.append(dict(resref=ref,sha256=sha,source=origin))
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';encoded=cache/'encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py');backend=json.loads((cache/'backend.json').read_text());bk=hashlib.sha256(json.dumps(backend,sort_keys=True).encode()).digest()
hits=[];special=[];targets={}
for k,w in works.items():
    p=encoded/(k+'.npz')
    if p.exists():
        with np.load(p,allow_pickle=False) as a:
            assert a['I'].shape==w['shape'];validate_encoded(w['profile'],a['I'],a['F'],a['guide'],a['dep'])
        hits.append(dict(key=k,sha256=file_sha(p)));continue
    if not np.any(w['profile'].classes[w['input_indices']]>=3):special.append(k);continue
    for palette in w['profile'].fitting:
        tk=hashlib.sha256(bk+w['input_key']+w['used'].tobytes()+palette[w['used']].tobytes()).hexdigest();targets.setdefault(tk,cache/'targets'/tk[:2]/(tk+'.npz'))
target_hits=sum(p.exists() for p in targets.values());native_frames=sum(len(frames[n]) for n in refs);base_ids={f['work_id'] for n in refs for f in frames[n]};bound_frames=sum(int(r['source_frame_count']) for r in rows)
dup=defaultdict(list)
for ref,r in resources.items():dup[r['canonical_sha256']].append(ref)
comparisons=[]
for family in ('multi_new','monster','monster_icewind'):
    fr=[r for r in csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig')) if r['engine_family']==family];unique=db.execute('SELECT count(distinct f.work_id) FROM animations a JOIN animation_resources ar USING(animation_id) JOIN frames f USING(resource_id) WHERE a.engine_section=?',(family,)).fetchone()[0]
    comparisons.append(dict(family=family,available_IDs=sum(bool(r['bam_resrefs']) for r in fr),defined_IDs=len(fr),unique_native_source_work=unique))
requirements=['producer validate_selection currently assumes nine-part/8-character MultiNew refs; add the native four-part MDEM route before full production', 'source_plan currently loads one unsuffixed BMP; add native MonsterMulti palette prefix + bank number 1..5, using the 30 verified per-bank BMPs', 'native routing uses hardcoded MonsterMulti for 1200..1208 and MultiNew for 1300, both owner5; retain both hooks']
if heterogeneous_groups:requirements.append('contextual assembly must accept each native part palette: current context_plan requires equal K6 palettes within a group')
if alias_conflicts:requirements.append('split frame/cycle declarations where the same native frame has different ordered neighbour contexts; preserve pixel cache')
selection=dict(schema='bg2-q3m-family-witness-selection-v1',scope='proposal only; all ten native MultiNew IDs, four/nine-part contextual x2 enhanced Q3m; no SDF',scale=2,colour='K6-four-partners-eight-levels',source_absent_animation_ids=[],witnesses=witnesses)
report=dict(role='proposal-not-production-QA-installation-release',family='multi_new',models=list(models.values()),available_animation_ids=10,defined_animation_ids=10,source_absent_animation_ids=[],native_format_reference='https://gibberlings3.github.io/iesdp/file_formats/ie_formats/ini_anim.htm',missing_BAM=[],missing_native_palettes=[],native_BAM=len(refs),native_frames=native_frames,base_unique_source_work=len(base_ids),base_repetitions=native_frames-len(base_ids),palette_bound_resources=sum(len(w['refs']) for w in witnesses),palette_bound_frames=bound_frames,unique_encoded_work=len(works),compatible_encoded_cache_hits=len(hits),new_encoded_work=len(works)-len(hits),special_work_without_inference=len(special),unique_neural_requests=len(targets),existing_target_cache_hits=target_hits,new_neural_targets=len(targets)-target_hits,native_replacement_palettes=palette_sources,whole_BAM_duplicate_groups=[v for v in dup.values() if len(v)>1],duplicate_BAM_files=sum(len(v)-1 for v in dup.values()),contextual_unique_draws=len(contexts),contextual_binding_count=len(bindings),contextual_parts=dict(four=sum(n==4 for n in contexts.values()),nine=sum(n==9 for n in contexts.values())),contextual_additional_neural_targets_max=6*len(contexts),heterogeneous_palette_groups=heterogeneous_groups,frame_alias_conflicts=alias_conflicts,production_adaptations_required=requirements,source_resources_verified=source_verified,cache_hit_files=hits,remaining_family_comparison=comparisons,SDF=False,scale=2,production_started=False,installed=False,Torch_imported='torch' in sys.modules)
assert not report['Torch_imported'] and len({m['indices_geometry_cycles_sha256'] for m in models.values()})==4
write_json(HERE/'selection.json',selection);write_json(HERE/'analysis.json',report)
print(json.dumps({k:report[k] for k in ('native_BAM','native_frames','base_unique_source_work','base_repetitions','palette_bound_resources','palette_bound_frames','unique_encoded_work','compatible_encoded_cache_hits','new_encoded_work','special_work_without_inference','new_neural_targets','existing_target_cache_hits','duplicate_BAM_files','contextual_unique_draws','contextual_parts','contextual_additional_neural_targets_max','production_adaptations_required')}),flush=True)
