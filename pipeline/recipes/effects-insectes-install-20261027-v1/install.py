"""Install selected continuous0.60 insects; replace only their runtime bindings."""
from pathlib import Path
from dataclasses import asdict
import argparse,copy,importlib.util,inspect,json,os,shutil,struct,subprocess,sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import effect_authority as authority
import install_renderer_candidate as tx
from workspace_paths import get_path


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


builder=module('insect_runtime_builder','pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
geometry=module('insect_carrier_builder','pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/install.py')
preview=module('insect_chosen_preview','pipeline/recipes/effects-insectes-continu-20261027-v1/preview.py')
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest
sha=workflow.sha256_file
OUT=ROOT/'effects/installations/insectes-continu-reference060-20261027-v1'
CANDIDATE=OUT/'candidate'
GAME=get_path('bg2ee_game_root',required=True)
BASE=ROOT/'effects/batches/lot26-seedvr7b-apollo30-20261017-v2'
SELECTED=ROOT/'effects/batches/insectes-continu-plusfin-preview-20261027-v2'
PARENT_INSTALL=ROOT/'effects/installations/lot31-latest-20261019-v1'
PROBE=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
EXPECTED_BASE='46690D937B43930DEA7C615FAC6CC1CDBDE1CAF0A4C909BAF24AB240151EA12A'
ASSETS={'SPINSECT','SPIPLAAI','SPIPLAUI'}
REPLACED={'SPINSECT','SPIPLAAI','SPIPLARI','X26PLAA','SPIPLAUI'}
NORMAL={'SPINSECT':'XINSECTN','SPIPLAAI':'X26PLAA','SPIPLAUI':'XIPLAUIN'}
PRO_NAMES=['INSEC1','INSEC2','INSEC3','INSEC4']
tx.MANAGED_FILES+=tuple('override/'+name+'.pro' for name in PRO_NAMES)
PRESERVED=['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','BaldurReal.exe',
    'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
    'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
    'override/Z26T03.vvc','override/Z26T04.vvc','override/Z26T05.vvc',
    'override/ICINHIT.vvc','override/ICINTRAV.vvc']
MANIFESTS={}


def runtime_manifest(a):return MANIFESTS[a['resref']]


encoder=inspect.getsource(builder.build_resource)
old_input="stage=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation'\n    m=load(stage/'manifest.json');"
assert encoder.count(old_input)==1
scope=dict(builder.__dict__,runtime_manifest=runtime_manifest)
exec(compile(encoder.replace(old_input,'stage=ROOT; m=runtime_manifest(a);',1),str(Path(__file__))+'::encoder','exec'),scope)
build_resource=scope['build_resource']
carrier_source=inspect.getsource(geometry.carrier).replace('pad=5','pad=2').replace(
    'target.parent.mkdir(parents=True)','target.parent.mkdir(parents=True,exist_ok=True)')
carrier_scope=dict(geometry.__dict__)
exec(compile(carrier_source,str(Path(__file__))+'::carrier','exec'),carrier_scope)
make_carrier=carrier_scope['carrier']


def registry_blocks(raw):
    magic,version,scale,count,reserved=struct.unpack_from('<8sIIII',raw)
    assert (magic,version,scale,reserved)==(b'IEEEFX4\0',3,4,0)
    cursor=24;result={}
    for _ in range(count):
        start=cursor;name=raw[cursor:cursor+8].rstrip(b'\0').decode();cursor+=8
        nf,nc=struct.unpack_from('<II',raw,cursor);cursor+=8+nf*8
        for _ in range(nc):
            n=struct.unpack_from('<I',raw,cursor)[0];cursor+=4+n*4
        *_,maximum=struct.unpack_from('<IIIII',raw,cursor);cursor+=20+maximum*nc*4
        extras=struct.unpack_from('<I',raw,cursor)[0];cursor+=4
        for _ in range(extras):
            cycle,n=struct.unpack_from('<II',raw,cursor);cursor+=8+n*4
        assert name not in result;result[name]=raw[start:cursor]
    assert cursor==len(raw)
    return result


def derive():
    assert not (OUT/'derivation.json').exists()
    jobs=[a for a in load(BASE/'batch.json')['assets'] if a['resref'] in ASSETS]
    result=[]
    for a in jobs:
        ref=a['resref'];stage=ROOT/'effects/ressources'/ref/'runs'/a['interpolation_run']/'02-interpolation'
        parent=load(stage/'manifest.json')
        spatial=ROOT/'effects/ressources'/ref/'runs'/a['spatial_run']/'01-spatial-x4/manifest.json'
        sp=load(spatial);sources,checks=preview.native_masks(ref,spatial)
        carrier=OUT/'carriers'/f'{ref}.bam';size,centre,geometry_checks=make_carrier(a,sp,carrier)
        w,h=[v*4 for v in size];expected=[v*4+16 for v in sp['aligned_canvas_size_x1']]
        assert [w,h]==expected
        frames=[];verified_loop_phases=0
        for old in parent['frames']:
            source=stage/old['straight_raw_rgba_x4'];data=source.read_bytes()
            assert digest(data)==old['straight_raw_rgba_x4_sha256'].upper()
            fw,fh=old['physical_size_x4'];crop=np.frombuffer(data,np.uint8).reshape(fh,fw,4)
            l,t,r,b=old['runtime_crop_box_x4'];canvas=np.zeros((h,w,4),np.uint8)
            canvas[t+8:b+8,l+8:r+8]=crop
            normal=preview.mask_variants(canvas,old,sources)[1]  # selected isocontour0.60
            if old['mode']=='loop':
                selected=SELECTED/'frames'/f'{ref}-cycle{old["cycle"]:03d}-loop/reference'/f'{old["phase"]:03d}.png'
                assert np.array_equal(normal,np.asarray(Image.open(selected).convert('RGBA'))),'selected preview differs'
                verified_loop_phases+=1
            prem=normal.copy();prem[:,:,:3]=np.rint(normal[:,:,:3].astype(np.float32)*normal[:,:,3:4]/255).astype(np.uint8)
            assert np.all(prem[:,:,:3]<=prem[:,:,3:4]) and not prem[prem[:,:,3]==0].any()
            paths=[]
            for mode,array in [('straight',normal),('premultiplied',prem)]:
                p=OUT/'derived'/ref/'rgba'/f'{old["frame"]:03d}-{mode}.rgba';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(array.tobytes());paths.append(p)
            f=copy.deepcopy(old)
            for key in ('rgba_x4','rgba_x4_sha256'):f.pop(key,None)
            f.update(logical_size_x1=size,physical_size_x4=[w,h],centre_x1=centre,runtime_crop_box_x4=[0,0,w,h],bytes=w*h*4,
                raw_rgba_x4=rel(paths[1]),raw_rgba_x4_sha256=sha(paths[1]),
                straight_raw_rgba_x4=rel(paths[0]),straight_raw_rgba_x4_sha256=sha(paths[0]),
                anchored_rgba_sha256=digest(prem.tobytes()),anchored_rgb_sha256=digest(prem[:,:,:3].tobytes()),
                normal_alpha_policy='selected continuous native isocontour0.60 SS4, then unchanged temporal fraction')
            frames.append(f)
        m=copy.deepcopy(parent)
        m.update(frames=frames,created_utc=workflow.utc_now(),runtime_revision='insectes-continu-reference060-20261027-v1',
            runtime_carrier={'path':rel(carrier),'sha256':sha(carrier),'native_world_pixels_preserved':True},
            parent_visual_treatment=parent['visual_treatment'],
            selected_preview=workflow.file_evidence(ROOT,SELECTED/'result.json'),
            visual_treatment={'method':'continuous native field sigma0.25x1, isocontour0.60, SS4 coverage; unchanged temporal fractions',
                              'scope':'once+loop; no microblur or per-cell particle masks','parent':workflow.file_evidence(ROOT,stage/'manifest.json')})
        for c in m['timing']['cycles']:
            seq=[frames[i] for i in c['timeline_frame_indices']]
            c['unique_rgba']=len({f['anchored_rgba_sha256'] for f in seq});c['unique_rgb']=len({f['anchored_rgb_sha256'] for f in seq})
        save(OUT/'derived'/ref/'manifest.json',m)
        result.append({'resref':ref,'asset':a,'manifest':workflow.file_evidence(ROOT,OUT/'derived'/ref/'manifest.json'),
            'native_mask_checks':checks,'geometry_checks':geometry_checks,'selected_loop_phases_exact':verified_loop_phases,
            'all_phases':len(frames),'profiles':len(m['timing']['cycles']),'size_x1':size,'centre_x1':centre})
        print(ref,len(frames),'phases;',verified_loop_phases,'selected loop frames exact',flush=True)
    assert sum(r['selected_loop_phases_exact'] for r in result)==196
    assert sum(r['all_phases'] for r in result)==392
    save(OUT/'derivation.json',{'status':'completed','assets':result,'selected_isocontour':0.60,
        'selected_preview':workflow.file_evidence(ROOT,SELECTED/'result.json'),'installed':False,'qa_accepted':False})


def probe(target,name):
    with (OUT/name).open('x',encoding='utf-8') as log:
        subprocess.run([str(PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],
            stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)


def prepare():
    assert not (OUT/'plan.json').exists()
    derived=load(OUT/'derivation.json');active=GAME/'iee-assets/effects';old=load(active/'manifest.json')
    assert sha(active/'manifest.json')==EXPECTED_BASE and old['resource_count']==520
    raw_registry=(active/'EffectAnimations-X4.registry').read_bytes();blocks=registry_blocks(raw_registry)
    assert list(blocks)==[r['resref'] for r in old['resources']]
    before={'manifest_sha256':sha(active/'manifest.json'),'registry_sha256':digest(raw_registry),
            'preserved':{n:asdict(tx.snapshot_file(GAME/n)) for n in PRESERVED}}
    save(OUT/'before.json',before);CANDIDATE.mkdir(parents=True,exist_ok=True)
    manifest=copy.deepcopy(old);files={};baselines={};contracts=[];new_resources={};new_frames={};new_blocks={}
    for line in (PARENT_INSTALL/'runtime-contracts.tsv').read_text(encoding='ascii').splitlines():
        if line.split('\t',1)[0].upper() not in REPLACED:contracts.append(line)

    def add(name,raw=None,source=None):
        assert name not in files,name
        dest=tx.managed_path(CANDIDATE,name,create_parents=True)
        if source is not None:
            expected=tx.snapshot_file(source)
            if dest.exists():assert tx.snapshot_file(dest)==expected
            else:
                try:os.link(source,dest)
                except OSError:shutil.copy2(source,dest)
        else:
            if dest.exists():assert dest.read_bytes()==raw
            else:dest.write_bytes(raw)
            expected=tx.snapshot_file(dest)
        files[name]={'name':name,**asdict(expected)}
        old_file=tx.optional_snapshot(GAME/name);baselines[name]=asdict(old_file) if old_file else None

    for d in derived['assets']:
        a=d['asset'];ref=a['resref'];m=load(ROOT/d['manifest']['path']);assert sha(ROOT/d['manifest']['path'])==d['manifest']['sha256']
        MANIFESTS[ref]=m
        variants={'SPINSECT':[('SPINSECT',False),('XINSECTN',True)],
                  'SPIPLAAI':[('SPIPLAAI',False),('SPIPLARI',False),('X26PLAA',True)],
                  'SPIPLAUI':[('SPIPLAUI',False),('XIPLAUIN',True)]}[ref]
        for name,straight in variants:
            raw,resource,frames,copies,checks,_=build_resource(a,name,straight)
            resource.update(runtime_revision=m['runtime_revision'],selected_preview=m['selected_preview'],derived_manifest=d['manifest'])
            if name in REPLACED:
                previous=next(r for r in old['resources'] if r['resref']==name)
                assert resource['cycles']==previous['cycles']
                for key in ('native_fps','target_fps','phase_count','actual_phase_counts_by_cycle','cycle_profiles','once_profiles'):
                    assert resource['timeline'][key]==previous['timeline'][key],(name,key)
            else:assert not any(r['resref']==name for r in old['resources'])
            new_resources[name]=resource;new_frames[name]=frames;new_blocks[name]=raw;contracts.extend(checks)
            for source,filename in copies:add('iee-assets/effects/'+filename,source=source)
            carrier=ROOT/m['runtime_carrier']['path'];add('override/'+name+'.bam',source=carrier)
            entry={'resref':name,'asset':'override/'+name+'.bam','sha256':sha(carrier),'bytes':carrier.stat().st_size,
                'production_bam':ref,'policy':'uniform canvas plus2nativepx margin; original palette/indices/lookup/cycles/world drawings exact'}
            existing=next((i for i,c in enumerate(manifest['runtime_bam_carriers']) if c['resref']==name),None)
            if existing is None:manifest['runtime_bam_carriers'].append(entry)
            else:manifest['runtime_bam_carriers'][existing]=entry
    assert set(new_resources)==REPLACED|{'XINSECTN','XIPLAUIN'}
    manifest['resources']=[new_resources.get(r['resref'],r) for r in old['resources']]+[new_resources[n] for n in ['XINSECTN','XIPLAUIN']]
    old_by_ref={name:[f for f in old['frames'] if f['resref']==name] for name in REPLACED}
    manifest['frames']=[];emitted=set()
    for f in old['frames']:
        ref=f['resref']
        if ref in REPLACED:
            if ref in emitted:continue
            emitted.add(ref);sequence=new_frames[ref]
        else:sequence=[copy.deepcopy(f)]
        for item in sequence:item['frame']=len(manifest['frames']);manifest['frames'].append(item)
    for ref in ['XINSECTN','XIPLAUIN']:
        for f in new_frames[ref]:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
    # Old physical files no longer used by a shortened deduplicated resource
    # are retired transactionally, with a full backup and hash-bound rollback.
    wanted={f['asset'] for f in manifest['frames']};retired=[]
    for seq in old_by_ref.values():
        for f in seq:
            if f['asset'] not in wanted:
                name='iee-assets/effects/'+f['asset'];retired.append({'name':name,**asdict(tx.snapshot_file(GAME/name))})
    routes=[]
    # All four stock owners have normal travel flags8 and area/ring flags0.
    # Adapt only their BAM references, keeping all engine behavior and flags.
    for owner in PRO_NAMES:
        p=ROOT/'projectiles/source'/f'{owner}.pro';raw=p.read_bytes();installed=GAME/'override'/f'{owner}.pro'
        expected={c['source_sha256'].upper() for d in derived['assets'] for c in d['asset']['consumers']
                  if c['consumer_key']=='projectile:'+owner}
        assert expected=={digest(raw)},('source PRO hash differs',owner)
        assert not installed.exists() or installed.read_bytes()==raw,'modified owner requires reconciliation'
        assert struct.unpack_from('<I',raw,0x100)[0]==8
        patches={0x104:'X26PLAA' if owner in ['INSEC1','INSEC2'] else 'XINSECTN'}
        if len(raw)==768:
            assert struct.unpack_from('<I',raw,0x240)[0]==0
            patches.update({0x21c:'XIPLAUIN',0x230:'X26PLAA'})
        changed=bytearray(raw);check=bytearray(raw)
        for offset,target in patches.items():
            source=raw[offset:offset+8].rstrip(b'\0').decode()
            assert source in ['SPIPLARI','SPIPLAUI','SPINSECT']
            changed[offset:offset+8]=target.encode().ljust(8,b'\0')
            routes.append({'owner':owner,'offset':hex(offset),'source':source,'target':target,'encoding':'straight'})
        for offset in patches:check[offset:offset+8]=changed[offset:offset+8]
        assert check==changed
        add('override/'+owner+'.pro',bytes(changed))
    clua=[]
    for name,ref,production,cycle in [('ZINS01','X26PLAA','SPIPLARI',0),('ZINS02','XIPLAUIN','SPIPLAUI',0),
                                      ('ZINS03','XINSECTN','SPINSECT',0),('ZINS04','XINSECTN','SPINSECT',1)]:
        m=MANIFESTS[new_resources[ref]['production_bam']];v=next(c for c in m['timing']['cycles'] if c['cycle']==cycle and c['loop_closed'])
        raw=builder.make_vvc(ref,cycle,True,15,len(v['native_slots']),False);add('override/'+name+'.vvc',raw)
        manifest['runtime_vvc_controllers'].append({'asset':'override/'+name+'.vvc','bam':ref,'sha256':digest(raw),
            'bytes':len(raw),'purpose':'selected insect continuous0.60 alpha-normal bounded loop test'})
        clua.append({'vvc':name,'bam':production,'runtime_bam':ref,'cycle':cycle,'clua':f'C:Eval(\'CreateVisualEffectObject("{name}",Player1)\',0)'})
    order=[r['resref'] for r in manifest['resources']]
    registry=raw_registry[:24]+b''.join(new_blocks.get(name,blocks.get(name,b'')) for name in order)
    registry=registry[:16]+struct.pack('<I',len(order))+registry[20:]
    parsed=registry_blocks(registry)
    assert all(parsed[n]==block for n,block in blocks.items() if n not in REPLACED)
    unchanged=[r for r in old['resources'] if r['resref'] not in REPLACED]
    assert [r for r in manifest['resources'] if r['resref'] not in new_resources]==unchanged
    assert manifest['runtime_vvc_controllers'][:-4]==old['runtime_vvc_controllers']
    old_other=[{k:v for k,v in f.items() if k!='frame'} for f in old['frames'] if f['resref'] not in REPLACED]
    new_other=[{k:v for k,v in f.items() if k!='frame'} for f in manifest['frames'] if f['resref'] not in new_resources]
    assert old_other==new_other
    manifest.update(resource_count=len(order),frame_count=len(manifest['frames']),registry_bytes=len(registry),registry_sha256=digest(registry))
    manifest.setdefault('runtime_corrections',[]).append({'installation':rel(OUT),'derivation':workflow.file_evidence(ROOT,OUT/'derivation.json'),
        'resrefs':sorted(new_resources),'chosen_variant':'Reference appreciee, isocontour0.60','qa':'pending-user-ingame'})
    add('iee-assets/effects/EffectAnimations-X4.registry',registry)
    add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
    save(OUT/'palette-routes.json',routes);save(OUT/'clua.json',clua);save(OUT/'target-baselines.json',baselines)
    text=['# Nuées — référence appréciée0.60','','Relancer via InfinityLoader ; console Ctrl+Espace. Tests normaux, boucles bornées≥4s.','', '```lua']
    for item in clua:text.extend([f'-- {item["bam"]} / cycle{item["cycle"]:03d}-loop',item['clua']])
    text.extend(['```','','Anciennes commandes Z26T03/Z26T04/Z26T05 conservées ;03/05 restent lumineuses.'])
    (OUT/'CLUA.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    probe(CANDIDATE/'iee-assets/effects','candidate-native-loader.log')
    save(OUT/'plan.json',{'files':list(files.values()),'retired':retired,'count':3,'selected_isocontour':0.60,
        'runtime_resources':len(order),'total_backings':len(manifest['frames']),'replaced_resources':sorted(REPLACED),
        'added_resources':['XINSECTN','XIPLAUIN'],'other_resources_unchanged':len(unchanged),'other_backings_unchanged':len(old_other),
        'derived_phases':392,'selected_loop_phases_exact':196,'native_contracts':len(contracts),'normal_pro_owners':PRO_NAMES,
        'manifest_sha256':sha(CANDIDATE/'iee-assets/effects/manifest.json'),'metadata_mib':32,
        'qa_accepted':False,'production_pointers_changed':False,'release_changed':False})
    print('READY',len(files),'files;',len(contracts),'native contracts;',len(retired),'retired',flush=True)


def preserved(before):
    assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())


def rollback(receipt):
    assert Path(receipt['game_root']).resolve()==GAME.resolve()
    for f in reversed(receipt['files']):
        target=tx.managed_path(GAME,f['name'],create_parents=True);current=tx.optional_snapshot(target)
        old=tx.FileSnapshot(**f['before']) if f['before'] else None
        new=None if f.get('delete') else tx.FileSnapshot(f['bytes'],f['sha256'])
        assert current in (old,new),target
        if current==old:continue
        if old:tx.atomic_copy(OUT/'before'/f['name'],target,old)
        elif new:tx.safe_unlink(target,new)
    receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt)


def install():
    assert not (OUT/'transaction.json').exists()
    tx.ensure_game_stopped(tx.running_game_processes)
    before,plan=load(OUT/'before.json'),load(OUT/'plan.json');preserved(before)
    assert sha(GAME/'iee-assets/effects/manifest.json')==before['manifest_sha256']
    assert sha(GAME/'iee-assets/effects/EffectAnimations-X4.registry')==before['registry_sha256']
    (OUT/'before').mkdir(parents=True,exist_ok=True);entries=[];baselines=load(OUT/'target-baselines.json')
    for f in plan['files']:
        expected=tx.FileSnapshot(f['bytes'],f['sha256']);assert tx.snapshot_file(CANDIDATE/f['name'])==expected
        old=tx.optional_snapshot(GAME/f['name']);assert (asdict(old) if old else None)==baselines[f['name']]
        if old:tx.atomic_copy(GAME/f['name'],tx.managed_path(OUT/'before',f['name'],create_parents=True),old)
        entries.append({**f,'before':asdict(old) if old else None})
    for f in plan['retired']:
        old=tx.FileSnapshot(f['bytes'],f['sha256']);assert tx.snapshot_file(GAME/f['name'])==old
        tx.atomic_copy(GAME/f['name'],tx.managed_path(OUT/'before',f['name'],create_parents=True),old)
        entries.append({**f,'delete':True,'before':asdict(old)})
    receipt={'schema':'bg2-effects-resource-delta-transaction-v1','status':'prepared','game_root':str(GAME),
        'candidate_root':rel(CANDIDATE),'created_utc':tx.utc_now(),'files':entries}
    tx.write_json_atomic(OUT/'transaction.json',receipt)
    try:
        tx.ensure_game_stopped(tx.running_game_processes);receipt['status']='installing';tx.write_json_atomic(OUT/'transaction.json',receipt)
        for i,f in enumerate(entries):
            target=tx.managed_path(GAME,f['name'],create_parents=True)
            old=tx.FileSnapshot(**f['before']) if f['before'] else None;assert tx.optional_snapshot(target)==old
            if f.get('delete'):tx.safe_unlink(target,old)
            else:tx.atomic_copy(CANDIDATE/f['name'],target,tx.FileSnapshot(f['bytes'],f['sha256']))
            if i%300==0:print('copied',i+1,'/',len(entries),flush=True)
        for f in entries:assert tx.optional_snapshot(GAME/f['name'])==(None if f.get('delete') else tx.FileSnapshot(f['bytes'],f['sha256']))
        preserved(before);probe(GAME/'iee-assets/effects','installed-native-loader.log')
        receipt['status']='installed';receipt['installed_utc']=tx.utc_now();tx.write_json_atomic(OUT/'transaction.json',receipt)
    except Exception:rollback(receipt);raise
    finish()


def finish():
    receipt,plan,before=load(OUT/'transaction.json'),load(OUT/'plan.json'),load(OUT/'before.json')
    assert receipt['status']=='installed' and sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];preserved(before)
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        if not (OUT/'processing-before.json').exists():save(OUT/'processing-before.json',rows)
        changed=0
        for row in rows:
            if row['asset_key'] in {'effects:bam:'+r for r in ASSETS|{'SPIPLARI'}}:
                row['installation_state']='installed';row['installation_receipt']=rel(OUT/'transaction.json');changed+=1
        assert changed==4
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'installation.json',{k:v for k,v in plan.items() if k not in ['files','retired']}|{
        'status':'installed-offline-verified','transaction':rel(OUT/'transaction.json'),'installed_utc':receipt['installed_utc'],
        'game_and_loader_stopped':True,'game_launched':False,'dll_ini_shaders_character_profile_unchanged':True})
    print('INSTALLED insects selected reference0.60; CLUA ZINS01..04; QA pending ingame',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['derive','prepare','install','finish']);args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);globals()[args.action]()
