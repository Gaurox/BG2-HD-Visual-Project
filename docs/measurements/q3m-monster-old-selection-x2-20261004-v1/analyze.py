"""CPU-only complete available MonsterOld proposal; exact native palettes/cache."""
import csv,hashlib,json,sqlite3,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,validate_encoded
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from run_creature_sprite_x2 import KeyIndex,canonical_bam
assert not (HERE/'analysis.json').exists(),'fresh proposal required'
rows=[r for r in csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig')) if r['engine_family']=='monster_old']
inv={r['animation_id']:r for r in csv.DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);bam_map=index.resource_map(1000);bmp_map=index.resource_map(1)
selection=dict(schema='bg2-q3m-family-witness-selection-v1',scale=2,colour='K6-four-partners-eight-levels',scope='proposal only; complete available MonsterOld, native G1/G2 + E and auxiliary INV, all frames/cycles; enhanced x2/no SDF',source_absent_animation_ids=[r['animation_id'] for r in rows if not r['bam_resrefs']],witnesses=[])
palettes=[];missing=[]
for r in rows:
    aid=r['animation_id'];ini=json.loads(inv[aid]['ini_sections_json']);native=ini['monster_old'];prefix=native['resref']
    if not r['bam_resrefs']:
        assert not any(ref.startswith(prefix) for ref in bam_map)
        assert not any(game.joinpath('override').glob(prefix+'*.bam'))
        missing.append(dict(animation_id=aid,name=r['ids_symbol'],resref=prefix));continue
    refs=r['bam_resrefs'].split(';')
    assert {prefix+s for s in ('G1','G1E','G2','G2E')}<=set(refs)
    w=dict(family='monster_old',animation_id=aid,name=r['ids_symbol'],owner=7,native_kind=int(native['false_color']),refs=refs)
    replacement=ini['general'].get('new_palette')
    if replacement:
        p=game/'override'/(replacement+'.bmp')
        if p.exists():raw=p.read_bytes();origin='override'
        else:
            assert replacement in bmp_map,'palette absent: '+replacement
            raw,origin=index.resolve(bmp_map[replacement])
        sha=hashlib.sha256(raw).hexdigest();w['palette_override']=dict(resref=replacement,sha256=sha)
        palettes.append(dict(animation_id=aid,resref=replacement,sha256=sha,source=origin))
    selection['witnesses'].append(w)
write_json(HERE/'selection.json',selection)
resources,works,summary=source_plan(HERE/'selection.json','monster_old')
refs=sorted({r['resref'] for r in resources});verified=[]
for ref in refs:
    p=game/'override'/(ref+'.bam')
    if p.exists():raw=p.read_bytes();origin='override'
    else:raw,origin=index.resolve(bam_map[ref])
    canonical,_=canonical_bam(raw);sha=hashlib.sha256(canonical).hexdigest()
    assert sha.upper()==next(r['source_sha256'] for r in resources if r['resref']==ref).upper()
    verified.append(dict(resref=ref,canonical_sha256=sha,source=origin))
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';encoded=cache/'encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
hits=[]
for key,work in works.items():
    p=encoded/(key+'.npz')
    if p.exists():
        with np.load(p,allow_pickle=False) as z:
            assert z['I'].shape==(work['frame'].height*2,work['frame'].width*2)
            validate_encoded(work['profile'],z['I'],z['F'],z['guide'],z['dep'])
        hits.append(dict(key=key,path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p)))
hitkeys={h['key'] for h in hits};new=set(works)-hitkeys
special={k for k in new if not np.any(works[k]['profile'].classes[works[k]['frame'].indices]>=(3 if works[k]['profile'].kind==0 else 4))}
backend=json.loads((cache/'backend.json').read_text());backend_key=hashlib.sha256(json.dumps(backend,sort_keys=True).encode()).digest()
requests={}
for key in new-special:
    work=works[key];used=np.unique(work['frame'].indices[work['frame'].indices!=0])
    for palette in work['profile'].fitting:
        target=hashlib.sha256(backend_key+bytes.fromhex(work['input_key'])+used.tobytes()+palette[used].tobytes()).hexdigest()
        requests.setdefault(target,cache/'targets'/target[:2]/(target+'.npz'))
target_hits=sum(p.exists() for p in requests.values())
pointer=json.loads((ROOT/'sprite/index/q3m-source-work-plan.json').read_text());db=sqlite3.connect((ROOT/pointer['path']).as_uri()+'?mode=ro',uri=True);marks=','.join('?' for _ in refs)
physical,base_unique=db.execute(f'SELECT count(*),count(distinct work_id) FROM frames JOIN resources USING(resource_id) WHERE resref IN ({marks})',refs).fetchone()
duplicates=[dict(resrefs=r[0].split(','),count=r[1]) for r in db.execute(f'SELECT group_concat(resref),count(*) FROM resources WHERE resref IN ({marks}) GROUP BY canonical_sha256 HAVING count(*)>1',refs)]
groups={}
for w in selection['witnesses']:
    rr=[r for r in resources if r['witness']['animation_id']==w['animation_id']];keys={f['key'] for r in rr for f in r['frames']};prefix=inv[w['animation_id']]['resref']
    groups.setdefault(prefix,dict(model=prefix,refs=w['refs'],frames=sum(len(r['frames']) for r in rr),variants=[]))['variants'].append(dict(animation_id=w['animation_id'],name=w['name'],palette=w.get('palette_override',{}).get('resref','native BAM'),native_kind=w['native_kind'],unique_encoded_work=len(keys),cache_hits=len(keys&hitkeys)))
report=dict(role='proposal-not-production-QA-installation-release',family='monster_old',scale=2,SDF=False,models=len(groups),available_animation_ids=len(selection['witnesses']),defined_animation_ids=len(rows),source_absent=missing,native_BAM=len(refs),native_physical_frames=physical,base_unique_source_work=base_unique,base_repetitions=physical-base_unique,palette_bound_resources=len(resources),palette_bound_frames=summary['physical_frames'],unique_source_work=summary['unique_source_work'],unique_encoded_work=len(works),compatible_encoded_cache_hits=len(hits),new_encoded_work=len(new),special_work_without_inference=len(special),unique_neural_requests=len(requests),existing_target_cache_hits=target_hits,new_neural_targets=len(requests)-target_hits,models_and_variants=list(groups.values()),native_replacement_palettes=palettes,whole_BAM_duplicates=duplicates,source_resources_verified=verified,cache_hit_files=hits,auxiliary_INV_refs=[r for r in refs if 'INV' in r],production_started=False,installed=False,release=False)
assert 'torch' not in sys.modules
write_json(HERE/'analysis.json',report);write_json(HERE/'plan-summary.json',summary)
print(json.dumps({k:report[k] for k in ('models','available_animation_ids','defined_animation_ids','native_BAM','native_physical_frames','base_unique_source_work','palette_bound_resources','palette_bound_frames','unique_encoded_work','compatible_encoded_cache_hits','new_encoded_work','special_work_without_inference','unique_neural_requests','existing_target_cache_hits','new_neural_targets','whole_BAM_duplicates','auxiliary_INV_refs')}),flush=True)
