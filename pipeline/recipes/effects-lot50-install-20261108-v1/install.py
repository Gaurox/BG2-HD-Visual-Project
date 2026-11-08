"""Append current50 corrected effects to active game; reversible scoped transaction."""
from pathlib import Path
from dataclasses import asdict
import argparse
import copy
import importlib.util
import json
import shutil
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import effect_authority as authority
import install_renderer_candidate as tx
from workspace_paths import get_path
from compose_effect_runtime_packs import validate_pack

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
builder=module('lot50_runtime_builder','pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
transaction=module('lot50_scoped_tx','pipeline/recipes/effects-lot33-install-20261018-v1/install.py')
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest
sha=workflow.sha256_file
GAME=get_path('bg2ee_game_root',required=True)
SOURCE=ROOT/'effects/batches/lot50-black-transparent-20261108-v1'
BASE=ROOT/'effects/batches/lot50-seedvr7b-apollo30-20261108-v1'
OUT=ROOT/'effects/installations/lot50-current-20261108-v1'
CANDIDATE=OUT/'candidate'
PROBE=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
ALPHA7={'SPFINODI','SPFIRET','SPPFIRAI','SPPFIRXI','STEAM1','STEAM4','SPOUTA'}
PRESERVED=['InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini','BaldurReal.exe',
           'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
           'iee-assets/creature-sprites/CreatureSprites-XN.catalog','iee-assets/AreaAnimations-X4.registry']
transaction.OUT=OUT;transaction.CANDIDATE=CANDIDATE;transaction.GAME=GAME

def command(vvc):return f'C:Eval(\'CreateVisualEffectObject("{vvc}",Player1)\',0)'

def assets():
    original={a['resref']:a for a in load(BASE/'batch.json')['assets']}
    return [{**original[a['resref']],**a} for a in load(SOURCE/'production.json')['assets']]

def blended(a):
    return a['resref'] not in ALPHA7 and (a['profile'] in {'F','T','H','G'} or a['resref'] in {'SPMETSWN','SPRDRAEX'})

def probe(target,name):
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/name).open('w',encoding='utf-8') as log:
        subprocess.run([str(PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
transaction.probe=probe

def preserved(before):
    assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
transaction.preserved=preserved

def prepare():
    assert not (OUT/'plan.json').exists(),'Create a new installation version'
    OUT.mkdir(parents=True,exist_ok=True)
    jobs=assets();assert len(jobs)==50
    active=GAME/'iee-assets/effects';old=load(active/'manifest.json');registry=(active/'EffectAnimations-X4.registry').read_bytes()
    assert digest(registry)==old['registry_sha256'] and old['registry_version']==3
    assert not {a['resref'] for a in jobs}&{r['resref'] for r in old['resources']}
    assert b'EffectMetadataMiB = 32' in (GAME/'InfinityEngine-Enhancer.ini').read_bytes()
    paths=[p for p in PRESERVED if (GAME/p).is_file()]
    paths+=list(str(p.relative_to(GAME)).replace('\\','/') for p in (GAME/'iee-assets/areas').glob('*/AreaAnimations-X4.registry'))
    before=dict(manifest_sha256=sha(active/'manifest.json'),registry_sha256=digest(registry),
                preserved={n:asdict(tx.snapshot_file(GAME/n)) for n in paths},
                resources=old['resource_count'],backings=old['frame_count'])
    save(OUT/'before.json',before)
    manifest=copy.deepcopy(old);records=bytearray();files=[];contracts=[];clua=[];profiles=[];comparisons=[];provenance=[]
    target=CANDIDATE/'iee-assets/effects';target.mkdir(parents=True,exist_ok=True)
    manifest.setdefault('runtime_vvc_controllers',[]);manifest.setdefault('runtime_bam_carriers',[])

    def add(name,raw=None,source=None):
        assert not (GAME/name).exists() or name in {'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry'},name
        dest=tx.managed_path(CANDIDATE,name,create_parents=True)
        if source is not None:
            if not dest.exists():shutil.copy2(source,dest)
            assert tx.snapshot_file(dest)==tx.snapshot_file(source)
        else:
            if dest.exists():assert dest.read_bytes()==raw
            else:dest.write_bytes(raw)
        files.append(dict(name=name,**asdict(tx.snapshot_file(dest))))

    def vvc(name,ref,raw,purpose):
        assert len(name)<=8
        add('override/'+name+'.vvc',raw)
        manifest['runtime_vvc_controllers'].append(dict(asset='override/'+name+'.vvc',bam=ref,sha256=digest(raw),bytes=len(raw),purpose=purpose))

    for source_asset in jobs:
        a=copy.deepcopy(source_asset);name=a['resref'];number=a['ordinal']
        unit=validate_pack(ROOT/a['pack']);assert unit.manifest_sha256==a['pack_manifest_sha256']
        # Only trailing, zero-length native cycles are omitted by the runtime registry.
        original_cycles=copy.deepcopy(a['native_cycles'])
        while a['native_cycles'] and not a['native_cycles'][-1]['frame_indices']:a['native_cycles'].pop()
        assert a['native_cycles'] and all(c['frame_indices'] for c in a['native_cycles'])
        normal=f'X50N{number:02d}'
        for runtime_ref,straight in [(name,False),(normal,True)]:
            raw,resource,frames,copies,new_contracts,m=builder.build_resource(a,runtime_ref,straight)
            resource.update(native_source_cycles=original_cycles,
                            empty_source_cycle_policy='Carrier retains trailing empty cycles; unplayable trailing entries omitted from registry only.',
                            production_pack=a['pack'],production_pack_sha256=unit.manifest_sha256)
            if name in ALPHA7:resource['alpha_revision']='black-transparent exact premultiplied RGB; straight reconstructed'
            records.extend(raw);manifest['resources'].append(resource);contracts.extend(new_contracts)
            for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
            for src,file in copies:add('iee-assets/effects/'+file,source=src)
            carrier=ROOT/m['runtime_carrier']['path'];assert sha(carrier)==m['runtime_carrier']['sha256']
            add(f'override/{runtime_ref}.bam',source=carrier)
            manifest['runtime_bam_carriers'].append(dict(resref=runtime_ref,asset=f'override/{runtime_ref}.bam',sha256=sha(carrier),bytes=carrier.stat().st_size,
                production_bam=name,policy='Source indexed pixels/palette/cycles/world anchors unchanged; inherited transparent padding'))
        luminous=blended(a);main_ref=name if luminous else normal
        for profile in m['timing']['cycles']:
            vname=f'Z50P{len(profiles)+1:04d}'
            raw=builder.make_vvc(main_ref,profile['cycle'],profile['loop_closed'],15,len(profile['native_slots']),luminous)
            vvc(vname,main_ref,raw,'lot50 isolated cycle/profile; bounded visual test, no gameplay')
            r=dict(ordinal=number,bam=name,runtime_bam=main_ref,profile=profile['id'],vvc=vname,
                   blend='lumineux' if luminous else 'normal',clua=command(vname))
            profiles.append(r)
        # Repeated cycle0 is useful for reviewing brief particles; native once profiles remain separate.
        main=next(p for p in m['timing']['cycles'] if p['cycle']==0 and p['loop_closed'])
        main_name=f'Z50T{number:02d}';raw=builder.make_vvc(main_ref,0,True,15,len(main['native_slots']),luminous)
        vvc(main_name,main_ref,raw,'lot50 main isolated test; cycle0 loop, >=4s; not native owner semantics')
        clua.append(dict(ordinal=number,bam=name,runtime_bam=main_ref,profile=main['id'],blend='lumineux' if luminous else 'normal',vvc=main_name,clua=command(main_name),model=a['model']))
        for suffix,ref,mode in [('B',name,True),('N',normal,False)]:
            vname=f'Z50{suffix}{number:02d}';raw=builder.make_vvc(ref,0,True,15,len(main['native_slots']),mode)
            vvc(vname,ref,raw,'lot50 isolated normal/luminous comparison')
            comparisons.append(dict(ordinal=number,bam=name,vvc=vname,blend='lumineux' if mode else 'normal',clua=command(vname)))
        provenance.append(dict(resref=name,pack=a['pack'],pack_manifest_sha256=unit.manifest_sha256,spatial_run=a['spatial_run'],
                               interpolation_run=a['interpolation_run'],normal_alias=normal,primary_test_blend='lumineux' if luminous else 'normal',native_owner_flags_measured=False))
        print(name,'prepared',len(m['timing']['cycles']),'profiles',flush=True)

    assert len(clua)==50 and len(profiles)==150 and len(comparisons)==100 and len(contracts)==20656
    assert manifest['resources'][:len(old['resources'])]==old['resources']
    assert manifest['frames'][:len(old['frames'])]==old['frames']
    newregistry=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+records
    assert newregistry[24:len(registry)]==registry[24:]
    manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(newregistry),registry_sha256=digest(newregistry))
    manifest.setdefault('source_packs',[]).extend(provenance)
    manifest.setdefault('runtime_corrections',[]).append(dict(installation=rel(OUT),production=rel(SOURCE/'production.json'),resrefs=[a['resref'] for a in jobs],qa='pending-user-ingame'))
    add('iee-assets/effects/EffectAnimations-X4.registry',newregistry)
    add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
    save(OUT/'clua.json',clua);save(OUT/'clua-all-profiles.json',profiles);save(OUT/'clua-blend-comparison.json',comparisons)
    text=['# Lot50 — commandes CLUA','','Relancer BG2EE via InfinityLoader ; console Ctrl+Espace. Une commande à la fois. Tests visuels sans dégâts, cycle0 répété pendant au moins4s. Les profils natifs once/loop sont conservés séparément.','','29/31/35/36/41/42/50 utilisent le noir transparent corrigé en alpha normal. Mélange des autres tests choisi pour revue ; flags des vrais consommateurs non mesurés.','','```lua']
    for r in clua:text.extend([f'-- {r["ordinal"]:02d} {r["bam"]} · {r["blend"]} · {r["model"]}',r['clua']])
    text+=['```','','[150profils](CLUA-tous-profils.md) · [Comparaison normal/lumineux](CLUA-transparence.md).']
    (OUT/'CLUA.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    for filename,title,rows in [('CLUA-tous-profils.md','150profils natifs indépendants',profiles),('CLUA-transparence.md','Normal et lumineux, même cycle0',comparisons)]:
        lines=['# Lot50 — '+title,'','Une commande à la fois ; tests isolés sans dégâts.','']
        for a in jobs:
            lines.extend([f'## {a["ordinal"]:02d} {a["resref"]}','','```lua'])
            for r in rows:
                if r['bam']==a['resref']:lines.extend(['-- '+r.get('profile',r['blend']),r['clua']])
            lines+=['```','']
        (OUT/filename).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    probe(target,'candidate-native-loader.log')
    save(OUT/'plan.json',dict(files=files,count=50,runtime_resources=len(manifest['resources']),total_backings=len(manifest['frames']),
                            old_resources_unchanged=len(old['resources']),old_backings_unchanged=len(old['frames']),
                            native_contracts=len(contracts),primary_tests=50,profiles=150,blend_comparisons=100,
                            black_transparent=sorted(ALPHA7),metadata_mib=32,ini_changed=False,
                            manifest_sha256=sha(target/'manifest.json'),source_production=rel(SOURCE/'production.json'),
                            source_production_sha256=sha(SOURCE/'production.json'),qa_accepted=False,release_changed=False))
    print('READY50',len(files),'files;',len(manifest['resources']),'resources;',len(contracts),'new native contracts',flush=True)

def finish():
    receipt=load(OUT/'transaction.json');plan=load(OUT/'plan.json');before=load(OUT/'before.json')
    assert receipt['status']=='installed' and sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];preserved(before)
    refs={'effects:bam:'+a['resref'] for a in assets()}
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        if not (OUT/'processing-before.json').exists():save(OUT/'processing-before.json',rows)
        count=0
        for row in rows:
            if row['asset_key'] in refs:row.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'));count+=1
        assert count==50
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'installation.json',{k:v for k,v in plan.items() if k!='files'}|dict(status='installed-offline-verified',transaction=rel(OUT/'transaction.json'),installed_utc=receipt['installed_utc'],
        game_and_loader_stopped=True,game_launched=False,dll_ini_shaders_characters_maps_preserved=True))
    print('INSTALLED50; CLUA Z50T01..Z50T50; QA pending user test',flush=True)
transaction.finish=finish

def install():transaction.install()
def restore():transaction.restore()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','install','finish','restore']);args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True);globals()[args.action]()
