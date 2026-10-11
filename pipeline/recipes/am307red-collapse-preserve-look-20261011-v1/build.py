"""Install existing AM307RED collapse candidate only; preserve all siblings."""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import animation_workflow as workflow
from workspace_paths import get_path

TAG = 'am307red-collapse-preserve-look-20261011-v1'
RECIPE = Path(__file__).resolve().parent
RUN = ROOT / 'animations/ressources/AM307RED/runs' / TAG
PACK = ROOT / 'animations/packs-par-zone' / TAG
BASE = ROOT / 'animations/packs-par-zone/am0307bh-water-only-feather-20261011-v1'
SOURCE = ROOT / 'animations/batches/ar0307-ar0329-am0307bh-am307red-apo8-x4-30fps-collapse-holds-20260916'
GAME = get_path('bg2ee_game_root')
AREAS = ['AR0307', 'AR0329']

def rel(path):
    return path.relative_to(ROOT).as_posix()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def payload(path):
    return {p.name: sha(p) for p in path.iterdir() if p.is_file()
            and (p.suffix == '.rgba' or p.name == v.REGISTRY_NAME)}

def pack(path, area, resources, source):
    path.mkdir(parents=True)
    registry = v.registry_v2_from_resources(resources, 3)
    (path / v.REGISTRY_NAME).write_bytes(registry)
    for resource in resources:
        for asset in resource['assets']:
            shutil.copy2(source(resource) / asset['name'], path / asset['name'])
    manifest = dict(schema=v.PACK_SCHEMA, status='completed', created_utc=v.utc_now(),
        scale=4, registry_version=3, registry=v.REGISTRY_NAME,
        runtime_contract=dict(feature='TimedTimeline', clock='QPC-pause-aware', registry_version=3),
        registry_sha256=sha(path / v.REGISTRY_NAME), registry_bytes=len(registry),
        resource_count=len(resources), frame_count=sum(r['frame_count'] for r in resources),
        timed_resources=[r['resref'] for r in resources if r['playback_mode']=='TimedTimeline'],
        raw_bytes=sum(a['bytes'] for r in resources for a in r['assets']),
        runtime_budget_enforced=True, base_assets=[], new_assets=[], resources=resources)
    if area:
        manifest['area_id']=area
    write(path / 'manifest.json', manifest)
    v.validate_v2_pack(path)

def prepare():
    assert not RUN.exists() and not PACK.exists(), 'Immutable output exists'
    _, source_resources=v.validate_v2_pack(SOURCE / '03_runtime_pack')
    target=copy.deepcopy(next(r for r in source_resources if r['resref']=='AM307RED'))
    assert target['frame_count']==28
    assert len({f['sha256'] for f in target['frames']})==28
    assert target['cycles'][0]['native_frame_indices']==[i for i in range(7) for _ in range(2)]
    assert len(target['cycles'][0]['timeline_frame_indices'])==28
    assert target['cycles'][0]['timeline_frame_indices'][::4]==list(range(7))
    pack(RUN / '03_runtime_pack', None, [target], lambda r: SOURCE / '03_runtime_pack')
    baselines={}
    entries=[]
    for area in AREAS:
        _, current=v.validate_v2_pack(BASE / area)
        live=GAME / 'iee-assets/areas' / area
        before=payload(live)
        assert before==payload(BASE / area), area+' unexpected live bytes'
        old=next(r for r in current if r['resref']=='AM307RED')
        assert old['frame_count']==21
        assert old['cycles'][0]['native_frame_indices']==target['cycles'][0]['native_frame_indices']
        assert old['native_fps']==target['native_fps'] and old['target_fps']==target['target_fps']
        for i in range(7):
            assert old['frames'][i]==target['frames'][i], 'Native reference/geometry changed'
        resources=[copy.deepcopy(target if r['resref']=='AM307RED' else r) for r in current]
        assert [(r['resref'],v.resource_binary_v2(r,3)) for r in current if r['resref']!='AM307RED']==[(r['resref'],v.resource_binary_v2(r,3)) for r in resources if r['resref']!='AM307RED']
        pack(PACK / area, area, resources, lambda r: SOURCE/'03_runtime_pack' if r['resref']=='AM307RED' else live)
        after=payload(PACK / area)
        for name,digest in before.items():
            if name!=v.REGISTRY_NAME and not name.startswith('AAX4-AM307RED-'):
                assert after[name]==digest, 'Sibling changed: '+name
        baselines[area]=dict(before=before,after=after)
        entries.append(dict(area_id=area,directory=area,manifest_sha256=sha(PACK/area/'manifest.json'),registry_sha256=sha(PACK/area/v.REGISTRY_NAME)))
    write(PACK/'manifest.json',dict(schema='bg2-upscale-area-animation-pack-index-v1',status='completed',created_utc=v.utc_now(),areas=entries))
    write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),resrefs=['AM307RED'],
        source_run=rel(SOURCE),source_run_manifest_sha256=sha(SOURCE/'manifest.json'),
        output_split_root=rel(PACK),output_manifest_sha256=sha(PACK/'manifest.json'),
        runtime_pack='03_runtime_pack',runtime_pack_manifest_sha256=sha(RUN/'03_runtime_pack/manifest.json'),
        runtime_contract=dict(scale=4,fps=30,frame_count=28,timeline_phases=28,duration_seconds=14/15,
            timing='collapse uniform doubled holds; input7.5fps to30fps; 3 interpolants between native references',
            preserved='7 native references byte-identical; geometry, spatial upscale, alpha and duration unchanged; AM0307BH and all siblings unchanged'),
        qa_status='pending-explicit-user-ingame-approval'))
    write(RECIPE/'baseline.json',dict(areas=baselines))
    write(RECIPE/'checks.json',dict(passed=True,distinct_frames=28,native_anchors_byte_identical=7,geometry_unchanged=True,duration_seconds=14/15,sibling_payload_and_contract_unchanged=True))
    a,m,p=workflow._artifact(ROOT,RUN)
    workflow._verify_embedded_pack(ROOT,m,p)
    workflow._verify_pack_binding(ROOT,m,p,workflow._source_pack(ROOT,PACK,'AM307RED',AREAS),'AM307RED')
    print('Prepared: 28 distinct frames; 7 anchors and all siblings unchanged; bindings OK')

def install():
    result=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader|BGMain' }).Count"],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='0','Close game and InfinityLoader first'
    receipt=RECIPE/'installation.json'
    assert not receipt.exists(), 'Immutable receipt exists'
    baselines=v.load_json(RECIPE/'baseline.json')['areas']
    backup=ROOT/'backups/animations'/TAG
    assert not backup.exists()
    for area in AREAS:
        v.validate_v2_pack(PACK/area)
        assert payload(GAME/'iee-assets/areas'/area)==baselines[area]['before'], area+' live drift'
    mutation={}
    for area in AREAS:
        live=GAME/'iee-assets/areas'/area
        saved=backup/area
        saved.mkdir(parents=True)
        old=[n for n in baselines[area]['before'] if n==v.REGISTRY_NAME or n.startswith('AAX4-AM307RED-')]
        new=[n for n in baselines[area]['after'] if n==v.REGISTRY_NAME or n.startswith('AAX4-AM307RED-')]
        for name in old:
            shutil.copy2(live/name,saved/name)
        mutation[area]=dict(old=old,new=new)
    try:
        for area in AREAS:
            live=GAME/'iee-assets/areas'/area
            for name in mutation[area]['new']:
                shutil.copy2(PACK/area/name,live/name)
            assert payload(live)==baselines[area]['after'],area+' installation mismatch'
    except Exception:
        for area in AREAS:
            live=GAME/'iee-assets/areas'/area
            for name in mutation[area]['old']:
                shutil.copy2(backup/area/name,live/name)
            for name in set(mutation[area]['new'])-set(mutation[area]['old']):
                path=live/name
                assert path.parent==live and path.name.startswith('AAX4-AM307RED-')
                if path.exists(): path.unlink()
            assert payload(live)==baselines[area]['before']
        raise
    write(receipt,dict(schema='bg2-upscale-animation-targeted-timing-install-v1',status='installed-pending-ingame-qa',created_utc=v.utc_now(),resref='AM307RED',run=rel(RUN),pack=rel(PACK),backup=rel(backup),areas=baselines))
    row,rows=workflow._registry_row(ROOT,'AM307RED')
    assert row['status']=='à-valider'
    row['notes']=('Correctif temporel installe AR0307/AR0329 2026-10-11 : doublons uniformes regroupes avant Apollo8 7.5->30fps ; 28frames distinctes, boucle14/15s. '
        '7images natives byte-identiques, geometrie et rendu spatial conserves. AM0307BH masque eau valide et tous autres assets inchanges. '
        'Run '+rel(RUN)+' ; recu '+rel(receipt)+'. QA visuelle utilisateur propre, saccades signalees sur ancien21frames ; nouvelle fluidite a valider. Aucune release.')
    (ROOT/workflow.REGISTRY_REL).write_bytes(workflow._render_registry(rows))
    print('Installed AR0307/AR0329; AM0307BH and all other assets unchanged; backup '+rel(backup))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    install() if args.install else prepare()
