"""Install lot58 from sealed phases; preserve active161 and the streaming DLL."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from compose_effect_runtime_packs import validate_pack, sha256_file
from workspace_paths import get_path
import install_renderer_candidate as installer
import effect_authority as authority
import effect_workflow as workflow

BATCH = ROOT/'effects/batches/lot58-seedvr7b-apollo30-20261016-v1'
OUT = ROOT/'effects/installations/lot58-7b-x4-nearest30-20261017-v1'
CANDIDATE = OUT/'candidate'
PROBE = ROOT/'build/iee-effect-streaming-20261015-v1/Release/iee_effect_animation_x4_registry_tests.exe'
STRAIGHT = {'MINORGLB','OHBGOLD','SPSTURNI','SPSKULLT','BDWOFOGA','SPCLOUDK','SPCLOUDS','SPDFOGA'}
ALIASES = {'SPFIRSDI': ('X58SDI','SPFIRSD2'), 'SPFLMBLD': ('X58BLD','SPFLMBLD')}
PRESERVED = ['override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
             'iee-assets/creature-sprites/CreatureSprites-XN.catalog']

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rel(p): return p.relative_to(ROOT).as_posix()
def digest(raw): return hashlib.sha256(raw).hexdigest().upper()
def immutable_write(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists(): assert path.read_bytes()==raw, path
    else: path.write_bytes(raw)
def copy(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists(): assert sha256_file(target)==sha256_file(source),target
    else: shutil.copy2(source,target)

def build_resource(a,ref,straight):
    stage=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation'
    m=load(stage/'manifest.json'); frames=[]; copies=[]; identities={}; mapping=[]
    for f in m['frames']:
        key='straight_raw_rgba_x4' if straight else 'raw_rgba_x4'
        sha=f[key+'_sha256']; identity=(sha,tuple(f['physical_size_x4']))
        if identity not in identities:
            n=len(frames); assert n<4096
            identities[identity]=n; source=stage/f[key]; assert sha256_file(source)==sha
            name=f'EFX4-{ref}-frame{n:03d}.rgba'
            frames.append({'frame':n,'asset':name,'resref':ref,'resource_frame':n,'source':rel(source),
                'sha256':sha,'bytes':f['bytes'],'logical_size_x1':f['logical_size_x1'],
                'physical_size_x4':f['physical_size_x4'],'source_centre_x1':f['centre_x1']})
            copies.append((source,name))
        mapping.append(identities[identity])
    primary=[]; alternates=[]
    for c in a['native_cycles']:
        choices=[v for v in m['timing']['cycles'] if v['cycle']==c['cycle']]
        chosen=max(choices,key=lambda v:v['loop_closed']); primary.append(chosen)
        alternates.extend(v for v in choices if v is not chosen)
    rate=(a['native_fps'] or [15])[0]
    native=[[mapping[i] for i in v['native_frame_indices']] for v in primary]
    tables=[[mapping[i] for i in v['timeline_frame_indices']] for v in primary]
    extra=[(v['cycle'],[mapping[i] for i in v['timeline_frame_indices']]) for v in alternates]
    # v3 alternates are currently integer 15->30 only. SPFLAST1/8FPS has
    # only a primary once profile; no unsupported alternate is emitted.
    assert all(rate==15 and len(t)==2*len(native[c]) for c,t in extra)
    maximum=max(map(len,tables)); raw=bytearray(ref.encode().ljust(8,b'\0'))
    raw.extend(struct.pack('<II',len(frames),len(native)))
    for f in frames: raw.extend(struct.pack('<II',*f['logical_size_x1']))
    for t in native: raw.extend(struct.pack(f'<I{len(t)}I',len(t),*t))
    raw.extend(struct.pack('<IIIII',rate,1,30,1,maximum))
    for t in tables: raw.extend(struct.pack(f'<{maximum}I',*(t+[t[-1]]*(maximum-len(t)))))
    raw.extend(struct.pack('<I',len(extra)))
    for c,t in extra: raw.extend(struct.pack(f'<II{len(t)}I',c,len(t),*t))
    contracts=[]
    for c,t,once in [(c,t,False) for c,t in enumerate(tables)]+[(c,t,True) for c,t in extra]:
        assert len(t)==math.ceil(len(native[c])*30/rate)
        for phase,target in enumerate(t):
            slot=min(len(native[c])-1,phase*rate//30)
            fallback=t[slot*2] if once else native[c][slot]
            dims=frames[target]['logical_size_x1']; assert frames[fallback]['logical_size_x1']==dims
            for name in (ref,ref.lower()):
                contracts.append(f'{name}\t{slot}\t{dims[0]}\t{dims[1]}\t{phase}\t{c}\t{fallback}\t{target}\t{int(once)}')
    resource={'resref':ref,'frame_count':len(frames),'cycles':a['native_cycles'],
        'production_bam':a['resref'],'interpolation_run':a['interpolation_run'],
        'rgb_encoding':'straight' if straight else 'premultiplied',
        'timeline':{'native_fps':[rate,1],'target_fps':[30,1],'phase_count':maximum,
            'native_frame_indices_by_cycle':native,'timeline_frame_indices_by_cycle':tables,
            'actual_phase_counts_by_cycle':list(map(len,tables)),
            'cycle_profiles':[v['id'] for v in primary],
            'once_profiles':[v['id'] for v in alternates]}}
    return bytes(raw),resource,frames,copies,contracts,m

def make_vvc(ref,cycle,loop,rate,slots,blended):
    raw=bytearray(0x1EC); raw[:8]=b'VVC V1.0'; raw[8:16]=ref.encode().ljust(8,b'\0')
    struct.pack_into('<H',raw,0x18,8 if blended else 0)
    struct.pack_into('<I',raw,0x20,9 if loop else 8)
    struct.pack_into('<I',raw,0x34,rate); struct.pack_into('<I',raw,0x38,1)
    struct.pack_into('<I',raw,0x5C,max(60,math.ceil(slots/rate*15)) if loop else 0xFFFFFFFF)
    struct.pack_into('<I',raw,0x68,cycle+1)
    struct.pack_into('<I',raw,0x6C,cycle+1 if loop else 0)
    return bytes(raw)

def prepare():
    assert not (OUT/'installation.json').exists()
    assets=load(BATCH/'batch.json')['assets']; assert len(assets)==58
    assert load(BATCH/'verification.json')['passed']==58
    game=get_path('bg2ee_game_root',required=True)
    old=validate_pack(game/'iee-assets/effects'); assert old.resource_count==161 and old.registry_version==3
    assert not ({a['resref'] for a in assets}&{r['resref'] for r in old.resources})
    before={'dll_sha256':sha256_file(game/'InfinityEngine-Enhancer.dll'),
        'ini_sha256':sha256_file(game/'InfinityEngine-Enhancer.ini'),
        'manifest_sha256':old.manifest_sha256,
        'profile_sha256':{n:sha256_file(game/n) for n in PRESERVED},
        'carriers':{c['asset']:sha256_file(game/c['asset']) for c in old.manifest['runtime_bam_carriers']}}
    if (OUT/'before.json').exists(): assert load(OUT/'before.json')==before
    else: save(OUT/'before.json',before)
    copy(game/'InfinityEngine-Enhancer.dll',CANDIDATE/'InfinityEngine-Enhancer.dll')
    ini=(game/'InfinityEngine-Enhancer.ini').read_bytes()
    assert b'EnableEffectAnimationStreaming = true' in ini
    assert ini.count(b'EffectMetadataMiB = 16')==1
    immutable_write(CANDIDATE/'InfinityEngine-Enhancer.ini',ini)
    registry=bytearray(old.registry_records); resources=list(old.resources); frames=list(old.frames)
    copies=[(old.root/f['asset'],f['asset']) for f in old.frames]
    carriers=list(old.manifest['runtime_bam_carriers']); controllers=[]
    for c in carriers: copy(game/c['asset'],CANDIDATE/c['asset'])
    contracts=(ROOT/'effects/installations/lot64-7b-x4-nearest30-20261015-v1/runtime-contracts.tsv').read_text().splitlines()
    review={a['resref']:a for a in load(BATCH/'review/review.json')['assets']}
    clua=[]; variants=[]; provenance=[]; wrapper_id=0
    def add_vvc(name,bam,raw,purpose):
        target=CANDIDATE/f'override/{name}.vvc'; immutable_write(target,raw)
        controllers.append({'asset':f'override/{name}.vvc','bam':bam,'sha256':digest(raw),
                            'bytes':len(raw),'purpose':purpose})
    for a in assets:
        unit=validate_pack(ROOT/a['pack'])
        assert unit.manifest_sha256==load(BATCH/'checks'/(a['resref']+'.json'))['pack_manifest_sha256']
        ref=a['resref']; built={}
        for name,straight in [(ref,ref in STRAIGHT)]+([(ALIASES[ref][0],True)] if ref in ALIASES else []):
            raw,resource,newframes,newcopies,newcontracts,m=build_resource(a,name,straight)
            built[name]=m; registry.extend(raw); resources.append(resource); contracts.extend(newcontracts)
            for f in newframes: f['frame']=len(frames); frames.append(f)
            copies.extend(newcopies)
            source=ROOT/m['runtime_carrier']['path']; assert sha256_file(source)==m['runtime_carrier']['sha256']
            copy(source,CANDIDATE/f'override/{name}.bam')
            carriers.append({'resref':name,'asset':f'override/{name}.bam','sha256':sha256_file(source),
                'bytes':source.stat().st_size,'production_bam':ref,'policy':'native pixels/centres/cycles; transparent padding only'})
        if ref in ALIASES:
            alias,vvc=ALIASES[ref]; source=ROOT/f'effects/source/vvc/{vvc}.vvc'
            raw=source.read_bytes(); assert raw[8:16].rstrip(b'\0').decode()==ref
            changed=raw[:8]+alias.encode().ljust(8,b'\0')+raw[16:]
            assert changed[:8]+raw[8:16]+changed[16:]==raw
            add_vvc(vvc,alias,changed,'native non-Blended consumer; BAM reference only')
        m=built[ref]; rate=(a['native_fps'] or [15])[0]
        natural=[c['consumer_key'].rsplit(':',1)[-1] for c in a['consumers'] if c['owner_route']=='vvc']
        for v in m['timing']['cycles']:
            wrapper_id+=1; name=f'Z58{wrapper_id:04d}'
            assert not (game/f'override/{name}.vvc').exists()
            raw=make_vvc(ref,v['cycle'],v['loop_closed'],rate,len(v['native_slots']),ref not in STRAIGHT)
            add_vvc(name,ref,raw,'isolated cycle visual test; bounded loops, no gameplay effect')
            record={'bam':ref,'profile':v['id'],'vvc':name,
                'clua':f'C:Eval(\'CreateVisualEffectObject("{name}",Player1)\',0)'}
            variants.append(record)
            if v['id']==review[ref]['default']:
                clua.append({**record,'ordinal':a['ordinal'],'native_vvcs':natural,'group':a['group']})
        provenance.append({'resref':ref,'pack':a['pack'],'pack_sha256':unit.manifest_sha256,
                           'rgb_encoding':'straight' if ref in STRAIGHT else 'premultiplied'})
        print(ref,'prepared',flush=True)
    assert len(clua)==58 and len(resources)==221
    raw=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(resources),0)+registry
    manifest={'schema':old.manifest['schema'],'status':'completed','scale':4,'registry':'EffectAnimations-X4.registry',
        'registry_magic':'IEEEFX4','registry_version':3,'registry_bytes':len(raw),'registry_sha256':digest(raw),
        'resource_count':len(resources),'resources':resources,'frame_count':len(frames),'frames':frames,
        'runtime_bam_carriers':carriers,'runtime_vvc_controllers':controllers,
        'source_packs':[{'active_manifest_sha256':old.manifest_sha256,'resource_count':161}]+provenance}
    target=CANDIDATE/'iee-assets/effects'; target.mkdir(parents=True,exist_ok=True)
    immutable_write(target/'EffectAnimations-X4.registry',raw)
    for source,name in copies: copy(source,target/name)
    immutable_write(target/'manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    immutable_write(OUT/'runtime-contracts.tsv',('\n'.join(contracts)+'\n').encode('ascii'))
    save(OUT/'clua.json',clua); save(OUT/'clua-all-profiles.json',variants)
    text='# Lot58 — commandes CLUA\n\nJeu lancé via InfinityLoader ; exécuter séparément. VVC Z58 : tests visuels isolés, sans dégâts. Boucles bornées à au moins 4 s ; période native conservée. Ils ne reproduisent pas le trajet/la dispersion des PRO.\n\n'
    labels={'casting-schools':'Incantations','fire-explosions-breath':'Feu, explosions et souffles',
            'clouds-magical-smoke':'Nuages et fumées magiques','orbs-lightning-energy':'Orbes, éclairs et énergie'}
    for group in dict.fromkeys(a['group'] for a in assets):
        text+=f'## {labels[group]}\n\n```lua\n'
        for r in clua:
            if r['group']==group: text+=f'-- {r["ordinal"]:02d} {r["bam"]} / {r["profile"]}\n{r["clua"]}\n'
        text+='```\n\n'
    text+='## Contrôleurs natifs VVC\n\n```lua\n'
    for r in clua:
        for n in r['native_vvcs']: text+=f'-- {r["bam"]}\nC:Eval(\'CreateVisualEffectObject("{n}",Player1)\',0)\n'
    text+='```\n\nTous les cycles et modes : [CLUA-tous-profils.md](CLUA-tous-profils.md). Les VVC natifs persistants conservent leur durée stock.\n'
    immutable_write(OUT/'CLUA.md',text.encode())
    text='# Lot58 — tous les profils produits\n\nVVC de test isolés, un cycle à la fois. Une commande à la fois.\n\n'
    for a in assets:
        text+=f'## {a["resref"]}\n\n```lua\n'
        for r in variants:
            if r['bam']==a['resref']: text+=f'-- {r["profile"]}\n{r["clua"]}\n'
        text+='```\n\n'
    immutable_write(OUT/'CLUA-tous-profils.md',text.encode())
    probe(target,OUT/'candidate-native-loader.log')
    installer.install_candidate(CANDIDATE,game_root=game,backup_root=OUT/'backups',verify_only=True)
    save(OUT/'plan.json',{'count':58,'total_effect_assets':219,'runtime_resources':221,'aliases':ALIASES,
        'existing_resources_unchanged':161,'registry_version':3,'filter':'NEAREST','scale':4,'target_fps':[30,1],
        'native_contracts':len(contracts),'profiles':len(variants),'controllers':len(controllers),
        'straight_resources':sorted(STRAIGHT),'metadata_mib':16,'raw_bytes':sum(f['bytes'] for f in frames),
        'manifest_sha256':sha256_file(target/'manifest.json'),'dll_sha256':before['dll_sha256'],
        'ini_sha256':sha256_file(CANDIDATE/'InfinityEngine-Enhancer.ini'),
        'native_pro_cadence':'15 FPS compatibility default; ingame measurement pending',
        'visual_qa':'pending-user','release_changed':False})
    print('READY',OUT,flush=True)

def probe(target,log):
    with log.open('w',encoding='utf-8') as stream:
        subprocess.run([str(PROBE),'--catalogue-only',str(target),
            str(OUT/'runtime-contracts.tsv')],stdout=stream,stderr=subprocess.STDOUT,check=True)

def install():
    assert not (OUT/'installation.json').exists()
    game=get_path('bg2ee_game_root',required=True); before=load(OUT/'before.json'); plan=load(OUT/'plan.json')
    installer.ensure_game_stopped(installer.running_game_processes)
    assert sha256_file(game/'InfinityEngine-Enhancer.dll')==before['dll_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.ini')==before['ini_sha256']
    assert sha256_file(game/'iee-assets/effects/manifest.json')==before['manifest_sha256']
    assert all(sha256_file(game/n)==h for n,h in before['profile_sha256'].items())
    assert all(sha256_file(game/n)==h for n,h in before['carriers'].items())
    for original, (alias,vvc) in ALIASES.items():
        source=ROOT/f'effects/source/vvc/{vvc}.vvc'
        target=game/f'override/{vvc}.vvc'
        # Preserve an unexpected modded controller instead of silently replacing it.
        if target.exists(): assert target.read_bytes()==source.read_bytes(),target
        raw=(CANDIDATE/f'override/{vvc}.vvc').read_bytes()
        assert raw[:8]+original.encode().ljust(8,b'\0')+raw[16:]==source.read_bytes()
    result=installer.install_candidate(CANDIDATE,game_root=game,backup_root=OUT/'backups')
    finish(result.receipt_path)

def finish(receipt_path):
    # install_candidate already hashes each staged/backup copy and verifies
    # every installed target before publishing status=installed. Avoid a
    # second complete payload/backup/target audit of the same bytes.
    assert not (OUT/'installation.json').exists()
    game=get_path('bg2ee_game_root',required=True)
    before=load(OUT/'before.json'); plan=load(OUT/'plan.json')
    receipt=installer.load_receipt(receipt_path)
    assert receipt['status']=='installed' and Path(receipt['game_root'])==game
    assert Path(receipt['candidate_root'])==CANDIDATE
    installer.receipt_files(receipt)
    assert sha256_file(game/'iee-assets/effects/manifest.json')==plan['manifest_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.dll')==plan['dll_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']
    assert all(sha256_file(game/n)==h for n,h in before['profile_sha256'].items())
    probe(game/'iee-assets/effects',OUT/'installed-native-loader.log')
    names={a['resref'] for a in load(BATCH/'batch.json')['assets']}
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        save(OUT/'processing-before.json',rows)
        for row in rows:
            if row['asset_key'].rsplit(':',1)[-1] in names:
                row['installation_state']='installed';row['installation_receipt']=rel(receipt_path)
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'installation.json',{**plan,'status':'installed-offline-verified','receipt':rel(receipt_path),
        'dll_byte_identical':True,'ini_byte_identical':True,'character_profile_byte_identical':True,'game_launched':False,
        'qa_accepted':False,'installed_vvcs_include': '397 isolated test wrappers +2 native normal-alpha routing refs',
        'integrity_verification':'canonical transaction: staged/backup copies hashed, all installed targets hashed before installed status; no repeated full receipt audit'})
    print('INSTALLED',plan['count'],'new effects,',plan['total_effect_assets'],'total',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','install']);args=p.parse_args()
    {'prepare':prepare,'install':install}[args.action]()
