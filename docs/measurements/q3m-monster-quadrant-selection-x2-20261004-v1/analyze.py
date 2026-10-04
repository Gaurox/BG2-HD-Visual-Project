"""Read-only source/cache proposal; native scope filtered locally, no production."""
import copy,csv,hashlib,inspect,json,re,sqlite3,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,validate_selection
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from run_creature_sprite_x2 import KeyIndex,canonical_bam
assert not (HERE/'README.md').exists(), 'final proposal already recorded'
rows=[r for r in csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig')) if r['engine_family']=='monster_quadrant']
inv={r['animation_id']:r for r in csv.DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game)
selection=dict(schema='bg2-q3m-family-witness-selection-v1',scale=2,scope='proposal only; complete available monster_quadrant, native four-quadrant G1/G2/G3 + E when extend_direction, all frames/cycles/directions; no SDF',source_absent_animation_ids=[r['animation_id'] for r in rows if not r['bam_resrefs']],witnesses=[])
palettes=[]
for r in rows:
    if not r['bam_resrefs']:continue
    aid=r['animation_id'];ini=json.loads(inv[aid]['ini_sections_json']);native=ini['monster_quadrant'];prefix=native['resref'];assert native['quadrants']=='4' and native['false_color']=='0'
    dirs=['','E'] if native['extend_direction']=='1' else ['']
    groups=[[prefix+'G'+str(bank)+str(part)+d for part in range(1,5)] for bank in range(1,4) for d in dirs]
    refs=[ref for group in groups for ref in group];assert set(refs)<=set(r['bam_resrefs'].split(';'))
    witness=dict(family='monster_quadrant',animation_id=aid,name=r['ids_symbol'],owner=4,native_kind=0,refs=refs,multipart_groups=groups,excluded_non_native_refs=sorted(set(r['bam_resrefs'].split(';'))-set(refs)))
    palette=ini['general'].get('new_palette')
    if palette:
        p=game/'override'/(palette+'.bmp')
        if p.exists():raw=p.read_bytes();source='override'
        else:raw,source=index.resolve(index.resource_map(1)[palette])
        witness['palette_override']=dict(resref=palette,sha256=hashlib.sha256(raw).hexdigest())
        palettes.append(dict(animation_id=aid,resref=palette,sha256=hashlib.sha256(raw).hexdigest(),source=source))
    selection['witnesses'].append(witness)
write_json(HERE/'selection.json',selection)
# Current generic complete validator includes all prefix hits. Validate those
# source memberships/palettes unchanged, then apply only proved native filter.
def scoped_validator(s,complete_family):
    expanded=copy.deepcopy(s)
    for w in expanded['witnesses']:
        w['refs']=next(r['bam_resrefs'].split(';') for r in rows if r['animation_id']==w['animation_id'])
    validate_selection(expanded,complete_family)
    assert {w['animation_id'] for w in s['witnesses']}=={w['animation_id'] for w in expanded['witnesses']}
    return s['witnesses']
namespace=dict(source_plan.__globals__);namespace['validate_selection']=scoped_validator
planning=inspect.getsource(source_plan)
old="require(0 < w*h < 65535 and row['transparent_index'] == 0, 'source geometry contract')"
assert planning.count(old)==1
# Native empty quadrant declarations are real sources; count them without
# producing/normalizing them. Writer support belongs to authorized production.
planning=planning.replace(old,"require(0 <= w*h < 65535 and row['transparent_index'] == 0, 'source geometry contract')")
exec(compile(planning,str(HERE/'analyze.py'),'exec'),namespace)
resources,works,summary=namespace['source_plan'](HERE/'selection.json','monster_quadrant')
refs=sorted({r['resref'] for r in resources});bam_map=index.resource_map(1000);verified=[]
for ref in refs:
    p=game/'override'/(ref+'.bam')
    if p.exists():raw=p.read_bytes();bif='override'
    else:raw,bif=index.resolve(bam_map[ref])
    canonical,_=canonical_bam(raw);sha=hashlib.sha256(canonical).hexdigest();expected=next(r['source_sha256'] for r in resources if r['resref']==ref)
    assert sha.upper()==expected.upper();verified.append(dict(resref=ref,canonical_sha256=sha,source=bif))
encoded=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1/encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py');hits=[]
for key,work in works.items():
    p=encoded/(key+'.npz')
    if p.exists():
        with np.load(p,allow_pickle=False) as a:
            assert a['I'].shape==(work['frame'].height*2,work['frame'].width*2)
            work['profile'].validate(a['I'],a['F'],a['guide'],a['dep'])
        hits.append(dict(key=key,path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p)))
hitkeys={r['key'] for r in hits};new=set(works)-hitkeys;special={k for k in new if not np.any(works[k]['frame'].indices>=2)}
per=[]
for w in selection['witnesses']:
    rr=[r for r in resources if r['witness']['animation_id']==w['animation_id']];keys={f['key'] for r in rr for f in r['frames']}
    per.append(dict(animation_id=w['animation_id'],name=w['name'],model=inv[w['animation_id']]['resref'],palette=w.get('palette_override',{}).get('resref','native BAM'),BAM=len(rr),frames=sum(len(r['frames']) for r in rr),unique_encoded_work=len(keys),cache_hits=len(keys&hitkeys),new_encoded_work=len(keys-hitkeys)))
pointer=json.loads((ROOT/'sprite/index/q3m-source-work-plan.json').read_text());db=sqlite3.connect((ROOT/pointer['path']).as_uri()+'?mode=ro',uri=True);marks=','.join('?' for _ in refs)
physical,baseunique=db.execute(f'SELECT count(*),count(distinct work_id) FROM frames JOIN resources USING(resource_id) WHERE resref IN ({marks})',refs).fetchone()
duplicates=[dict(resrefs=r[0].split(','),count=r[1]) for r in db.execute(f'SELECT group_concat(resref),count(*) FROM resources WHERE resref IN ({marks}) GROUP BY canonical_sha256 HAVING count(*)>1',refs)]
missing=[dict(animation_id=r['animation_id'],name=r['ids_symbol'],resref=r['body_resref']) for r in rows if not r['bam_resrefs']]
report=dict(role='proposal-not-production-QA-installation-release',family='monster_quadrant',scale=2,SDF=False,models=2,available_animation_ids=7,defined_animation_ids=9,source_absent=missing,native_BAM=len(refs),native_physical_frames=physical,base_unique_source_work=baseunique,base_repetitions=physical-baseunique,palette_bound_resources=len(resources),palette_bound_frames=summary['physical_frames'],unique_source_work=summary['unique_source_work'],unique_encoded_work=len(works),compatible_encoded_cache_hits=len(hits),new_encoded_work=len(new),special_work_without_inference=len(special),new_neural_targets=(len(new)-len(special))*6,per_variant=per,native_replacement_palettes=palettes,whole_BAM_duplicates=duplicates,source_resources_verified=verified,cache_hit_files=hits,excluded_prefix_resources=sorted({s for w in selection['witnesses'] for s in w['excluded_non_native_refs']}),native_scope=dict(factory_call='330EB4 -> 314350',constructor='314350',vtable='5AA460',render='3305A0',parser='341010',groups='G1/G2/G3 + part1..4; E only when extend_direction=1',existing_hook=True,production_prerequisite='Extend complete-family validator with exact native exclusions; no canonical code changed for proposal.'),production_started=False,installed=False,release=False)
report['zero_area_native_frames']=[dict(resref=r['resref'],frame_index=f['frame_index'],geometry=f['geometry']) for r in resources for f in r['frames'] if f['geometry'][0]*f['geometry'][1]==0]
report['native_scope']['empty_frame_prerequisite']='Preserve native 0x0 quadrant declarations, including referenced frames; current producer rejects zero geometry. No pixels/centres/cycles may be invented.'
write_json(HERE/'analysis.json',report);write_json(HERE/'plan-summary.json',summary)
print(json.dumps({k:report[k] for k in ('models','native_BAM','native_physical_frames','base_unique_source_work','palette_bound_resources','palette_bound_frames','unique_encoded_work','compatible_encoded_cache_hits','new_encoded_work','special_work_without_inference','new_neural_targets','per_variant','source_absent')}),flush=True)
