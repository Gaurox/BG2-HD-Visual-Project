"""Install exact latest lot31 previews; palette-owner dispatch and reversible delta.

No inference, production pointer promotion, QA decision or release mutation.
"""
from pathlib import Path
from dataclasses import asdict
import argparse
import copy
import importlib.util
import inspect
import json
import os
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import effect_authority as authority
import install_renderer_candidate as tx
from workspace_paths import get_path


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


builder = module('lot31_runtime_builder', 'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
geometry = module('lot31_carrier_builder', 'pipeline/recipes/effects-spdeath3-soft4-install-20261018-v1/install.py')
load, save, rel, digest = builder.load, builder.save, builder.rel, builder.digest
sha = workflow.sha256_file
BASE = ROOT/'effects/batches/lot31-projectiles-7b-apollo30-20261018-v1'
PREV = ROOT/'effects/batches/lot31-corrections-preview-20261018-v1'
LATEST = ROOT/'effects/batches/lot31-xbr-nativealpha-black-20261019-v1'
OUT = ROOT/'effects/installations/lot31-latest-20261019-v1'
CANDIDATE = OUT/'candidate'
GAME = get_path('bg2ee_game_root', required=True)
PROBE = ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
CONTRACTS = ROOT/'effects/installations/spdeath3-bezier-soft4-20261018-v1/runtime-contracts.tsv'
EXPECTED_BASE = 'DCE23D121BBA6060B023A8A72A6EBF6A2C055C33B936538DB00917FEE4C86F1C'
PRESERVED = ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini', 'BaldurReal.exe',
             'override/fpDraw.glsl', 'override/fpSprite.glsl', 'override/fpSELECT.glsl',
             'iee-assets/creature-sprites/CreatureSprites-XN.catalog']
BLACK = {12, 14, 20, 22, 27}
MANIFESTS = {}
# Explicit scope extension for this recipe only; the generic installer remains
# unchanged. These exact stock owners are hash-checked before any patch/write.
PRO_OWNERS = {c['consumer_key'].split(':')[-1]
    for a in load(BASE/'batch.json')['jobs'] for c in a['consumers']
    if c['owner_route']=='projectile' and c['relation']=='travel-animation'}
assert all(1<=len(n)<=8 and n.isascii() and n.replace('_','').isalnum() for n in PRO_OWNERS)
tx.MANAGED_FILES += tuple('override/'+n+'.pro' for n in sorted(PRO_OWNERS))


def runtime_manifest(a):
    return MANIFESTS[a['job_id']]


# Keep the previously exercised v3 table/contract encoder byte-for-byte, changing
# only its input adapter. All raw paths in the selected preview are root-relative.
encoder = inspect.getsource(builder.build_resource)
old_input = "stage=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation'\n    m=load(stage/'manifest.json');"
assert encoder.count(old_input) == 1
encoder = encoder.replace(old_input, 'stage=ROOT; m=runtime_manifest(a);', 1)
encoder_globals = dict(builder.__dict__, runtime_manifest=runtime_manifest)
exec(compile(encoder, str(Path(__file__))+'::v3-input-adapter', 'exec'), encoder_globals)
build_resource = encoder_globals['build_resource']
carrier_source = inspect.getsource(geometry.carrier).replace(
    'target.parent.mkdir(parents=True)', 'target.parent.mkdir(parents=True,exist_ok=True)')
carrier_globals = dict(geometry.__dict__)
exec(compile(carrier_source,str(Path(__file__))+'::carrier-input-adapter','exec'),carrier_globals)
make_carrier = carrier_globals['carrier']


def command(name):
    return f'C:Eval(\'CreateVisualEffectObject("{name}",Player1)\',0)'


def probe(target, name):
    with (OUT/name).open('x', encoding='utf-8') as log:
        subprocess.run([str(PROBE), '--catalogue-only', str(target), str(OUT/'runtime-contracts.tsv')],
                       stdout=log, stderr=subprocess.STDOUT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def prepare():
    assert not (OUT/'plan.json').exists(), 'Use a new version after sealing'
    OUT.mkdir(parents=True, exist_ok=True)
    CANDIDATE.mkdir(parents=True, exist_ok=True)
    assert load(LATEST/'verification.json')['status'] == 'passed'
    assert load(PREV/'verification.json')['all_native_durations_preserved']
    jobs = sorted(load(BASE/'batch.json')['jobs'], key=lambda a:(a['ordinal'], a['job_id']))
    assert len(jobs) == 99 and sum(a['primary'] for a in jobs) == 31
    active = GAME/'iee-assets/effects'; old = load(active/'manifest.json')
    assert sha(active/'manifest.json') == EXPECTED_BASE
    assert old['resource_count'] == 322 and old['frame_count'] == 43357
    before = {'manifest_sha256': sha(active/'manifest.json'),
              'registry_sha256': sha(active/'EffectAnimations-X4.registry'),
              'preserved': {n:asdict(tx.snapshot_file(GAME/n)) for n in PRESERVED}}
    save(OUT/'before.json', before)
    manifest = copy.deepcopy(old); records = bytearray(); files = {}; baselines = {}
    contracts = CONTRACTS.read_text(encoding='ascii').splitlines()
    primary, palettes, profiles, blends, selections, routes = [], [], [], [], [], []
    defaults = {a['job_id']:a['default'] for a in load(BASE/'review/review.json')['assets']}
    existing = {r['resref'] for r in old['resources']}

    def add(name, raw=None, source=None, allow_existing=False):
        assert name not in files, name
        current = tx.optional_snapshot(GAME/name)
        assert current is None or allow_existing, name
        dest = tx.managed_path(CANDIDATE, name, create_parents=True)
        if source is not None:
            expected = tx.snapshot_file(source)
            if dest.exists(): assert tx.snapshot_file(dest) == expected
            else:
                try: os.link(source, dest)
                except OSError: shutil.copy2(source, dest)
        else:
            if dest.exists(): assert dest.read_bytes() == raw
            else: dest.write_bytes(raw)
            expected = tx.snapshot_file(dest)
        files[name] = {'name':name, **asdict(expected)}
        baselines[name] = asdict(current) if current else None

    def vvc(name, ref, profile, rate, blended, purpose):
        raw = builder.make_vvc(ref, profile['cycle'], profile['loop_closed'], rate,
                               len(profile['native_slots']), blended)
        add('override/'+name+'.vvc', raw)
        manifest['runtime_vvc_controllers'].append({'asset':'override/'+name+'.vvc',
            'bam':ref, 'sha256':digest(raw), 'bytes':len(raw), 'purpose':purpose})
        return command(name)

    for index, a in enumerate(jobs, 1):
        key, ref, number = a['job_id'], a['resref'], a['ordinal']
        selected = LATEST/'results'/f'{key}.json'
        if not selected.exists(): selected = PREV/'results'/f'{key}.json'
        r = load(selected); assert r['passed'] and r['job_id'] == key
        original_stage = ROOT/'effects/ressources'/ref/'runs'/a['interpolation_run']/'02-interpolation'
        parent = load(original_stage/'manifest.json')
        spatial = load(ROOT/'effects/ressources'/ref/'runs'/a['spatial_run']/'01-spatial-x4/manifest.json')
        carrier = OUT/'carriers'/f'{ref}.bam'
        if not carrier.exists(): size, centre, checks = make_carrier(a, spatial, carrier)
        else: size, centre = r['logical_size_x1'], r['centre_x1']
        assert size == r['logical_size_x1'] and centre == r['centre_x1']
        assert r['size_x4'] == [v*4 for v in size]
        m = copy.deepcopy(parent); m['runtime_carrier'] = {'path':rel(carrier), 'sha256':sha(carrier)}
        frames = []
        assert len(r['frames']) == len(parent['frames'])
        for old_f, f in zip(parent['frames'], r['frames'], strict=True):
            assert f['frame'] == old_f['frame']
            out = copy.deepcopy(old_f)
            out.update(logical_size_x1=size, physical_size_x4=r['size_x4'], centre_x1=centre,
                       runtime_crop_box_x4=[0,0,*r['size_x4']], bytes=f['premultiplied']['bytes'],
                       raw_rgba_x4=f['premultiplied']['path'], raw_rgba_x4_sha256=f['premultiplied']['sha256'],
                       straight_raw_rgba_x4=f['straight']['path'], straight_raw_rgba_x4_sha256=f['straight']['sha256'],
                       temporal_source_frames=f['temporal_source_frames'], temporal_fraction=f['temporal_fraction'])
            assert f['straight']['bytes'] == size[0]*size[1]*64 == out['bytes']
            frames.append(out)
        m['frames'] = frames
        for timeline, p in zip(m['timing']['cycles'], r['profiles'], strict=True):
            assert timeline['id'] == p['id']
            assert timeline['duration_rational'] == p['duration_rational']
            assert timeline['phase_durations_rational'] == p['phase_durations_rational']
            assert len(timeline['timeline_frame_indices']) == p['phases']
            seq = [frames[i] for i in timeline['timeline_frame_indices']]
            assert [f['frame'] for f in r['frames'] if f['profile'] == p['id']] == timeline['timeline_frame_indices']
            timeline['unique_rgba'] = len({f['raw_rgba_x4_sha256'] for f in seq})
        m['selected_preview'] = workflow.file_evidence(ROOT, selected)
        save(OUT/'runtime-inputs'/f'{key}.json', m); MANIFESTS[key] = m
        # Hardcoded owners keep the established premultiplied native default.
        # PRO owners can select either encoding through explicit palette routes.
        native_straight = number <= 15 and number not in BLACK
        refs = {'straight':f'Y31N{index:03d}', 'premultiplied':f'Y31P{index:03d}'}
        if a['primary']: refs['straight' if native_straight else 'premultiplied'] = ref
        for encoding, runtime_ref in refs.items():
            assert runtime_ref not in existing; existing.add(runtime_ref)
            raw, resource, new_frames, copies, checks, _ = build_resource(a, runtime_ref, encoding=='straight')
            resource['selected_preview'] = m['selected_preview']; resource['palette_job'] = key
            records.extend(raw); manifest['resources'].append(resource); contracts.extend(checks)
            for f in new_frames:
                f['frame'] = len(manifest['frames']); manifest['frames'].append(f)
            for source, name in copies: add('iee-assets/effects/'+name, source=source)
            add(f'override/{runtime_ref}.bam', source=carrier)
            manifest['runtime_bam_carriers'].append({'resref':runtime_ref, 'asset':f'override/{runtime_ref}.bam',
                'sha256':sha(carrier), 'bytes':carrier.stat().st_size, 'production_bam':ref,
                'policy':'native palette/indices/cycles/lookup/world pixels exact; uniform transparent padding5x1'})
        # Patch only the8-byte travel BAM reference. Leave palette, colors, all
        # timing/gameplay fields and owner blend flags byte-identical.
        for consumer in a['consumers']:
            if consumer['owner_route'] != 'projectile' or consumer['relation'] != 'travel-animation': continue
            owner = consumer['consumer_key'].split(':')[-1]
            source = ROOT/'projectiles/source'/f'{owner}.pro'
            stock = source.read_bytes(); assert digest(stock) == consumer['source_sha256']
            installed = GAME/'override'/f'{owner}.pro'
            original = installed.read_bytes() if installed.exists() else stock
            assert original == stock, ('existing modified PRO needs context reconciliation', owner)
            assert original[0x104:0x10c].rstrip(b'\0').decode('ascii').upper() == ref
            flags = struct.unpack_from('<I',original,0x100)[0]
            assert flags == json.loads(consumer['flags_json'])['bam']
            bright = bool(flags & (0x80|0x100|0x200))
            target_ref = refs['premultiplied' if bright else 'straight']
            patched = original[:0x104]+target_ref.encode().ljust(8,b'\0')+original[0x10c:]
            assert patched[:0x104]+original[0x104:0x10c]+patched[0x10c:] == original
            if patched != original: add(f'override/{owner}.pro', patched, allow_existing=True)
            routes.append({'owner':owner, 'palette_job':key, 'source_sha256':digest(original),
                'runtime_bam':target_ref, 'encoding':'premultiplied' if bright else 'straight',
                'native_bam_flags':flags, 'patched':patched != original, 'only_bam_reference_changed':True})
        rate = (a['native_fps'] or [15])[0]
        blended = number in BLACK
        test_ref = refs['premultiplied' if blended else 'straight']
        default_id = defaults[key]
        if number in {30,31}: default_id = next(p['id'] for p in m['timing']['cycles'] if p['loop_closed'])
        for p in m['timing']['cycles']:
            name = f'Z31P{len(profiles)+1:04d}'
            clua = vvc(name, test_ref, p, rate, blended, 'lot31 isolated profile; bounded loop, no gameplay')
            entry = {'ordinal':number, 'bam':ref, 'job_id':key, 'runtime_bam':test_ref,
                     'profile':p['id'], 'blend':'blended' if blended else 'normal', 'vvc':name, 'clua':clua}
            profiles.append(entry)
            if p['id'] == default_id:
                palette_name = f'Z31C{index:03d}'
                c = vvc(palette_name, test_ref, p, rate, blended, 'lot31 palette-context isolated test')
                palettes.append({**entry, 'vvc':palette_name, 'clua':c,
                                 'owners':[v['consumer_key'] for v in a['consumers']]})
                if a['primary']:
                    name = f'Z31T{number:02d}'
                    c = vvc(name, test_ref, p, rate, blended, 'lot31 primary isolated test')
                    primary.append({**entry, 'vvc':name, 'clua':c})
                    for suffix, enc, blend in [('N','straight',False),('B','premultiplied',True)]:
                        name=f'Z31{suffix}{number:02d}'
                        c=vvc(name,refs[enc],p,rate,blend,'lot31 explicit normal/luminous comparison')
                        blends.append({**entry,'runtime_bam':refs[enc],'vvc':name,'clua':c,'blend':enc})
        selections.append({'job_id':key, 'resref':ref, 'primary':a['primary'], 'runtime_refs':refs,
            'preview':m['selected_preview'], 'actions':r['actions'], 'phases':len(frames),
            'profiles':len(m['timing']['cycles']), 'durations_exact_to_latest_preview':True})
        print(index, '/99', key, 'prepared', flush=True)
    assert len(primary)==31 and len(palettes)==99 and len(profiles)==658 and len(blends)==62
    assert sum(s['phases'] for s in selections)==9968
    assert len(manifest['resources'])==520
    assert manifest['resources'][:322]==old['resources'] and manifest['frames'][:43357]==old['frames']
    registry=(active/'EffectAnimations-X4.registry').read_bytes()
    raw=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+records
    assert raw[24:len(registry)]==registry[24:]
    manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),
                    registry_bytes=len(raw),registry_sha256=digest(raw))
    manifest.setdefault('source_candidates',[]).append({'installation':rel(OUT),'selections':selections})
    add('iee-assets/effects/EffectAnimations-X4.registry',raw,allow_existing=True)
    add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode(),allow_existing=True)
    (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
    save(OUT/'selections.json',selections);save(OUT/'palette-routes.json',routes)
    for name,data in [('clua',primary),('clua-palettes',palettes),('clua-all-profiles',profiles),('clua-blends',blends)]:
        save(OUT/(name+'.json'),data)
        lines=['# Lot31 — '+name,'','Relancer via InfinityLoader ; console Ctrl+Espace. Une commande à la fois. Boucles de test bornées (au moins4s).','', '```lua']
        for r in data:
            lines.extend([f'-- {r["ordinal"]:02d} {r["bam"]} / {r["job_id"]} / {r["profile"]} / {r["blend"]}',r['clua']])
        lines.extend(['```',''])
        (OUT/('CLUA.md' if name=='clua' else name.upper()+'.md')).write_text('\n'.join(lines),encoding='utf-8')
    save(OUT/'target-baselines.json',baselines)
    probe(CANDIDATE/'iee-assets/effects','candidate-native-loader.log')
    save(OUT/'plan.json',{'count':31,'palette_contexts':99,'phases':9968,'profiles':658,
        'runtime_resources':520,'total_backings':len(manifest['frames']),'new_backings':len(manifest['frames'])-43357,
        'new_bytes':sum(f['bytes'] for f in manifest['frames'][43357:]),'native_contracts':len(contracts),
        'native_pro_routes':len(routes),'patched_pro_owners':sum(r['patched'] for r in routes),
        'files':list(files.values()),'manifest_sha256':sha(CANDIDATE/'iee-assets/effects/manifest.json'),
        'existing_resources_unchanged':322,'existing_frames_unchanged':43357,
        'metadata_mib':32,'ini_changed':False,'native_blend_runtime_measured':False,
        'qa_accepted':False,'production_pointers_changed':False,'release_changed':False})
    print('READY31',len(files),'targets;',len(contracts),'native contracts',flush=True)


def preserved(before):
    assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())


def rollback(receipt):
    assert Path(receipt['game_root']).resolve()==GAME.resolve()
    for item in reversed(receipt['files']):
        target=tx.managed_path(GAME,item['name'],create_parents=True)
        current=tx.optional_snapshot(target);expected=tx.FileSnapshot(item['bytes'],item['sha256'])
        old=tx.FileSnapshot(**item['before']) if item['before'] else None
        assert current in (old,expected),target
        if current==old:continue
        if old:tx.atomic_copy(OUT/'before'/item['name'],target,old)
        else:tx.safe_unlink(target,expected)
    receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt)


def install():
    assert not (OUT/'transaction.json').exists()
    tx.ensure_game_stopped(tx.running_game_processes)
    before,plan=load(OUT/'before.json'),load(OUT/'plan.json');preserved(before)
    assert sha(GAME/'iee-assets/effects/manifest.json')==before['manifest_sha256']
    assert sha(GAME/'iee-assets/effects/EffectAnimations-X4.registry')==before['registry_sha256']
    (OUT/'before').mkdir(parents=True,exist_ok=True)
    baselines=load(OUT/'target-baselines.json');entries=[]
    for index,item in enumerate(plan['files']):
        expected=tx.FileSnapshot(item['bytes'],item['sha256'])
        assert tx.snapshot_file(CANDIDATE/item['name'])==expected
        old=tx.optional_snapshot(GAME/item['name'])
        assert (asdict(old) if old else None)==baselines[item['name']],item['name']
        if old:tx.atomic_copy(GAME/item['name'],tx.managed_path(OUT/'before',item['name'],create_parents=True),old)
        entries.append({**item,'before':asdict(old) if old else None})
        if index%1500==0:print('verified',index+1,'/',len(plan['files']),flush=True)
    receipt={'schema':'bg2-effects-resource-delta-transaction-v1','status':'prepared',
             'game_root':str(GAME),'candidate_root':rel(CANDIDATE),'created_utc':tx.utc_now(),'files':entries}
    tx.write_json_atomic(OUT/'transaction.json',receipt)
    try:
        tx.ensure_game_stopped(tx.running_game_processes)
        receipt['status']='installing';tx.write_json_atomic(OUT/'transaction.json',receipt)
        for index,item in enumerate(entries):
            target=tx.managed_path(GAME,item['name'],create_parents=True)
            old=tx.FileSnapshot(**item['before']) if item['before'] else None
            assert tx.optional_snapshot(target)==old
            tx.atomic_copy(CANDIDATE/item['name'],target,tx.FileSnapshot(item['bytes'],item['sha256']))
            if index%1500==0:print('copied',index+1,'/',len(entries),flush=True)
        for item in entries:
            assert tx.snapshot_file(GAME/item['name'])==tx.FileSnapshot(item['bytes'],item['sha256'])
        preserved(before);probe(GAME/'iee-assets/effects','installed-native-loader.log')
        receipt['status']='installed';receipt['installed_utc']=tx.utc_now()
        tx.write_json_atomic(OUT/'transaction.json',receipt)
    except Exception:
        rollback(receipt);raise
    finish()


def finish():
    receipt,plan,before=load(OUT/'transaction.json'),load(OUT/'plan.json'),load(OUT/'before.json')
    assert receipt['status']=='installed'
    assert sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];preserved(before)
    refs={a['resref'] for a in load(OUT/'selections.json')}
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        if not (OUT/'processing-before.json').exists():save(OUT/'processing-before.json',rows)
        changed=0
        for row in rows:
            if row['asset_key'] in {'effects:bam:'+ref for ref in refs}:
                row['installation_state']='installed';row['installation_receipt']=rel(OUT/'transaction.json');changed+=1
        assert changed==31
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    save(OUT/'installation.json',{k:v for k,v in plan.items() if k!='files'}|{
        'status':'installed-offline-verified','transaction':rel(OUT/'transaction.json'),
        'installed_utc':receipt['installed_utc'],'game_and_loader_stopped':True,
        'dll_ini_character_profile_byte_identical':True,'game_launched':False})
    print('INSTALLED31; latest99palette contexts; primary CLUA31; QA pending user test',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','install','finish']);args=p.parse_args()
    globals()[args.action]()
