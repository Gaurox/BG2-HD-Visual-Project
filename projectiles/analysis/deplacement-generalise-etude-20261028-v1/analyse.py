"""Read-only projectile motion feasibility audit. Never edits runtime, PROs or productions."""
from pathlib import Path
from datetime import datetime,timezone
import csv,json,hashlib,struct,sys,importlib.util,collections
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from projectile_tracking import parse_pro
if (OUT/'summary.json').exists():raise SystemExit('Historical study exists: use a new version')
spec=importlib.util.spec_from_file_location('native_readonly',ROOT/'pipeline/recipes/projectiles-secondary-links-20261028-v1/native.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);pe=module.PE()
GAME=get_path('bg2ee_game_root',required=True);BASE=0x140000000
bifs,entries=load_key();key={(n.upper(),t):v for n,t,v in entries}
compressed=pe.at(0x22eebc,255);jumps=struct.unpack('<56I',pe.at(0x22eddc,224))
def source(n):
 p=GAME/f'override/{n}.pro';return (p.read_bytes(),'override') if p.exists() else (resolve_resource(bifs,key[n,1021])[0],'KEY/BIF')
def rows(path):return list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
def writecsv(name,rs):
 with (OUT/name).open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def save(name,d):
 with (OUT/name).open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def factory(pid):
 pid=3 if pid==13 else pid
 return (compressed[pid],jumps[compressed[pid]]) if pid<255 else (-1,0x22e8f5)
def vft_at_lea(address):
 ins=next(pe.instructions(address,address+7));assert ins.mnemonic=='lea'
 disp=int(ins.op_str.split('rip + ')[1].split(']')[0],16);vft=ins.address+ins.size+disp
 pointers=struct.unpack('<39Q',pe.at(vft,312));assert all(BASE<=v<BASE+0x500000 for v in pointers)
 return vft,pointers
locations={'CProjectileBAM':0x227110,'CProjectileArea':0x226bb2,'CProjectileMulti':0x22ebb6,'CProjectileNewScorcher':0x22ec73,'CProjectileSkyStrikeBAM':0x22eb34,'CProjectileSpellHit':0x227e1d,'CProjectile':0x226945}
classes=[]
for name,lea in locations.items():
 vft,ps=vft_at_lea(lea);classes.append(dict(name=name,constructor_vtable_lea=hex(lea),vtable_rva=hex(vft),AIUpdate_slot='0x18',AIUpdate_rva=hex(ps[3]-BASE),Render_slot='0x98',Render_rva=hex(ps[19]-BASE),first_bytes_AIUpdate=pe.at(ps[3]-BASE,16).hex(),first_bytes_Render=pe.at(ps[19]-BASE,16).hex(),status='Read-only binary observation; signatures/ABI/lifecycle not yet approved as hook contract'))
byclass={c['name']:c for c in classes};assert byclass['CProjectileBAM']['Render_rva']==byclass['CProjectileArea']['Render_rva']=='0x233f20'
flags={0:'bounce',1:'pass-target',3:'immediate-hit',5:'curve-flag-not-proof-of-curve',7:'pillar',10:'multi',12:'falling',13:'comet',14:'line',15:'rectangle',21:'random'}
coverage=[]
for r in rows(ROOT/'projectiles/index/work-items.csv'):
 n=r['resref'];raw,where=source(n);p=parse_pro(raw);e=p['extended_flags'];ids=[int(x) for x in r['projectl_ids'].split(';') if x]
 cases=[factory(i)[1] for i in ids];assert all(c==0x22e8f5 for c in cases)
 cls='CProjectileArea' if p['type']==3 else 'CProjectileSkyStrikeBAM' if e&128 else 'CProjectileMulti' if e&1024 else 'CProjectileNewScorcher' if e&16384 else 'CProjectileBAM'
 tag=[v for bit,v in flags.items() if e&(1<<bit)];deps=dict((role,res) for role,o,res,fmt in p['resources'])
 coverage.append(dict(resref=n,PROJECTL_ids=r['projectl_ids'],active_source=where,source_sha256=hashlib.sha256(raw).hexdigest().upper(),type=p['type'],speed=p['speed'],extended_flags=hex(e),factory_cases=';'.join(map(hex,cases)),factory_class_prediction=cls,Render_rva=byclass[cls]['Render_rva'],AIUpdate_rva=byclass[cls]['AIUpdate_rva'],special_flags=';'.join(tag),travel_animation=deps.get('travel-animation',''),source_animation=deps.get('source-animation',''),shadow_animation=deps.get('shadow-animation',''),trail_animations=';'.join(v for k,v in deps.items() if k.startswith('trailing-animation')),smoke_animation_id=p.get('smoke_animation_id',0),fragment_animation_id=p.get('fragment_animation_id',0),has_height=bool(p['sparking_flags']&2),binding='PROJECTL-generic-PRO-route' if ids else 'no-PROJECTL-binding-do-not-infer-runtime-coverage',motion_qualification='not-measured',proposal='shared-flight-adapter-with-phase-guard' if cls in ['CProjectileBAM','CProjectileArea'] else 'special-render-adapter'))
assert len(coverage)==243
writecsv('coverage-243.csv',coverage)
native=[]
for r in rows(ROOT/'projectiles/index/engine-projectiles.csv'):
 i=int(r['projectl_id']);index,case=factory(i)
 native.append(dict(PROJECTL_id=i,missile_id=r['missile_id'],symbol=r['missile_symbol'],documented_family=r['documented_family'],native_switch_index=index,case_rva=hex(case),status='Factory route located only; runtime motion/render/lifecycle require adapter verification'))
assert len(native)==78;writecsv('engine-78.csv',native)
# Native ranges preserve the exact static evidence, not a guessed full-function boundary.
for name,a,b in [('factory-pro-branch',0x22e954,0x22edb0),('BAM-render',0x233f20,0x234520),('BAM-update-excerpt',0x228650,0x228df0),('BAM-render-FXRect',0x22b7b0,0x22b9a0),('constructor-BAM',0x2270e0,0x227260)]:
 (OUT/(name+'.txt')).write_text(pe.dump(a,b)+'\n',encoding='utf-8')
save('native-classes.json',classes)
codepaths=['engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp','engine/InfinityEngine-Enhancer/source-patchee/src/iee/frame_hook.cpp','engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.h','engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/runtime_types_x64.h']
counts=dict(collections.Counter(r['factory_class_prediction'] for r in coverage));flagcounts={v:sum(v in r['special_flags'].split(';') for r in coverage) for v in flags.values()}
save('summary.json',dict(schema='bg2-projectile-motion-feasibility-v1',utc=datetime.now(timezone.utc).isoformat(),scope='Study only; generalized visual movement interpolation, separate from sprite animation',executable_sha256=hashlib.sha256(pe.data).hexdigest().upper(),source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest().upper() for p in codepaths},PROs=243,source_types=dict(collections.Counter(r['type'] for r in coverage)),generic_factory_class_counts=counts,shared_Render_descriptor_count=sum(r['Render_rva']=='0x233f20' for r in coverage),PROs_with_PROJECTL_binding=sum(bool(r['PROJECTL_ids']) for r in coverage),PROJECTL_bindings=sum(len(r['PROJECTL_ids'].split(';')) for r in coverage if r['PROJECTL_ids']),PROs_without_PROJECTL_binding=[r['resref'] for r in coverage if not r['PROJECTL_ids']],native_IDs_without_PRO=78,special_flag_counts=flagcounts,declared_travel=sum(bool(r['travel_animation']) for r in coverage),limits=['Class/Render predictions do not prove a moving instance or ingame smoothing','Actual motion cadence, latency, threading and final draw positions remain unmeasured','No build, runtime install, gameplay/image/release modification'],decision='General service is feasible as a prototype; universal coverage requires multiple render/lifecycle adapters and an explicit impact-latency policy'))
print(json.dumps({'classes':counts,'shared_Render_descriptors':sum(r['Render_rva']=='0x233f20' for r in coverage),'bindings':sum(bool(r['PROJECTL_ids']) for r in coverage),'unbound':[r['resref'] for r in coverage if not r['PROJECTL_ids']],'native_ids':len(native),'flags':flagcounts}))
