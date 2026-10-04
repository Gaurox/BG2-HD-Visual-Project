"""Proposal only: complete grouped native 2000+8000 bodies/equipment; source/cache dedup."""
import csv,hashlib,json,sqlite3,sys,struct,inspect
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from run_creature_sprite_x2 import KeyIndex,canonical_bam,BAM_TYPE
from palette_oracle import pe_rva,EXE_SHA256
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not (HERE/'analysis.json').exists()
items=[r for r in csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig')) if r['engine_family']=='monster_layered']
selection=dict(schema='bg2-q3m-family-witness-selection-v1',scale=2,colour='four partners; eight blend levels; K6; V7',scope='proposal only: complete available monster_layered grouped native 2000+8000, body/equipment/all frames/cycles/directions; no SDF',source_absent_animation_ids=[r['animation_id'] for r in items if not r['bam_resrefs']],witnesses=[dict(family='monster_layered',animation_id=r['animation_id'],name=r['ids_symbol'],owner=8,native_kind=int(r['false_color'] or 1),refs=r['bam_resrefs'].split(';')) for r in items if r['bam_resrefs']])
write_json(HERE/'selection.json',selection)
# Analysis permits native zero-area declarations; the production writer remains unchanged.
# MSIRG2BE contains 30 height-zero native frames; do not normalize or invent pixels.
namespace=dict(source_plan.__globals__);planning=inspect.getsource(source_plan)
old="require(0 < w*h < 65535 and row['transparent_index'] == 0, 'source geometry contract')"
assert planning.count(old)==1
exec(compile(planning.replace(old,"require(0 <= w*h < 65535 and row['transparent_index'] == 0, 'source geometry contract')"),str(HERE/'analyze.py'),'exec'),namespace)
resources,works,summary=namespace['source_plan'](HERE/'selection.json','monster_layered')
pointer=load(ROOT/'sprite/index/q3m-source-work-plan.json');db=sqlite3.connect((ROOT/pointer['path']).as_uri()+'?mode=ro&immutable=1',uri=True);db.row_factory=sqlite3.Row
refs=sorted({r['resref'] for r in resources});marks=','.join('?' for _ in refs)
whole=[dict(sha256=r[0],resrefs=r[1].split(','),count=r[2]) for r in db.execute(f'SELECT canonical_sha256,group_concat(resref),count(*) FROM resources WHERE resref IN ({marks}) GROUP BY canonical_sha256 HAVING count(*)>1',refs)]
duplicates=[dict(examples=r[0].split(','),count=r[1]) for r in db.execute(f'SELECT group_concat(r.resref || ":" || f.frame_index),count(*) FROM frames f JOIN resources r USING(resource_id) WHERE r.resref IN ({marks}) GROUP BY f.work_id HAVING count(*)>1',refs)]
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);bam_map=index.resource_map(BAM_TYPE);verified=[]
for ref in refs:
    row=db.execute('SELECT * FROM resources WHERE resref=?',(ref,)).fetchone();assert ref in bam_map
    raw,bif=index.resolve(bam_map[ref]);canonical,_=canonical_bam(raw);assert hashlib.sha256(canonical).hexdigest().upper()==row['canonical_sha256'].upper()
    override=game/'override'/(ref+'.bam');assert not override.exists()
    verified.append(dict(resref=ref,sha256=row['canonical_sha256'],BIF=bif,frames=row['frame_count']))
db.close()
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';encoded=cache/'encoded'/file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py');hits=[]
for key,work in works.items():
    path=encoded/(key+'.npz')
    if path.exists():
        with np.load(path,allow_pickle=False) as arrays:
            assert arrays['I'].shape==(work['frame'].height*2,work['frame'].width*2)
            work['profile'].validate(arrays['I'],arrays['F'],arrays['guide'],arrays['dep'])
        hits.append(dict(key=key,path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path)))
hit_keys={h['key'] for h in hits};byid=[]
for witness in selection['witnesses']:
    rr=[r for r in resources if r['witness']['animation_id']==witness['animation_id']];keys={f['key'] for r in rr for f in r['frames']}
    special={k for k in keys-hit_keys if not np.any(works[k]['frame'].indices>=2)}
    byid.append(dict(animation_id=witness['animation_id'],name=witness['name'],BAM=len(rr),frames=sum(len(r['frames']) for r in rr),unique_source_work=len({works[k]['source_key'] for k in keys}),unique_encoded_work=len(keys),compatible_cache_hits=len(keys&hit_keys),new_encoded_work=len(keys-hit_keys),special_work_without_inference=len(special),refs=witness['refs']))
exe=(game/'BaldurReal.exe').read_bytes();assert hashlib.sha256(exe).hexdigest()==EXE_SHA256.lower();native=[]
for kind,vt,ctor in [('2000',0x5aa650,0x311300),('8000',0x5aa840,0x3119a0)]:
    pointers=struct.unpack('<62Q',pe_rva(exe,vt,62*8));native.append(dict(animation_type=kind,vtable_rva=hex(vt),render_rva=hex(pointers[38]-0x140000000),ini_parser_rva=hex(pointers[61]-0x140000000),constructor_rva=hex(ctor)))
assert native[1]['render_rva']=='0x32f3b0' and native[1]['ini_parser_rva']=='0x340610'
manifest=(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.cpp').read_text();assert '0x32ee90, 0x5aa650, 8' in manifest and '0x5aa840' not in manifest
native8000prereq=dict(reason='grouped source index merges monster_layered 2000 and monster_layered_spell 8000; current manifest only hooks the first',animation_ids=['0x8000','0x8100','0x8200'],needed='add native 8000 render/vtable to scoped owner8 composite hook before installation',native_paths=native,no_runtime_changes_made=True)
new_keys=set(works)-hit_keys;special={k for k in new_keys if not np.any(works[k]['frame'].indices>=2)}
report=dict(role='proposal-not-production-QA-installation-or-release',family='monster_layered',scale=2,SDF=False,summary=summary,models=7,available_animation_ids=7,defined_animation_ids=7,source_absent=[],whole_BAM_duplicates=whole,duplicate_frame_groups=duplicates,source_frames=6512,unique_source_work=summary['unique_source_work'],unique_encoded_work=len(works),physical_repetitions=6512-summary['unique_source_work'],compatible_encoded_cache_hits=len(hits),new_encoded_work=len(new_keys),special_work_without_inference=len(special),per_model=byid,source_resources_verified=verified,cache_hit_files=hits,native_runtime_prerequisite=native8000prereq,production_started=False,installed=False,release=False)
report['zero_area_native_frames']=[dict(resref=r['resref'],frame_index=f['frame_index'],geometry=f['geometry']) for r in resources for f in r['frames'] if f['geometry'][0]*f['geometry'][1]==0]
assert len(report['zero_area_native_frames'])==30
report['native_empty_frame_prerequisite']='preserve 30 zero-height MSIRG2BE declarations; V7 producer currently rejects them; establish native active/unused routes before any packing'
write_json(HERE/'analysis.json',report)
print(json.dumps({k:report[k] for k in ('models','source_frames','unique_source_work','unique_encoded_work','physical_repetitions','compatible_encoded_cache_hits','new_encoded_work','special_work_without_inference','whole_BAM_duplicates','per_model')}),flush=True)
