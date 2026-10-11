"""AM0307BH: fixed water-only alpha, unchanged installed RGB and timeline."""
import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.interpolate import splprep, splev
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
import animation_workflow as workflow
from build_spline_alpha_mask import resample_closed
from workspace_paths import get_path

TAG = 'am0307bh-water-only-feather-20261011-v1'
RECIPE = Path(__file__).resolve().parent
BATCH = ROOT / 'animations/batches' / TAG
RUN = ROOT / 'animations/ressources/AM0307BH/runs' / TAG
PACK = ROOT / 'animations/packs-par-zone' / TAG
GAME = get_path('bg2ee_game_root')
AREAS = ['AR0307', 'AR0329']
BASE = ROOT / 'animations/packs-par-zone/combined-20260831-ar0307-ar0329-six-bam-30fps-v2'
EXTRA = ROOT / 'animations/packs-par-zone/am1104b-left-inset8-feather4-complete-20261009-v4/AR1104'
SOURCE_RUN = ROOT / 'animations/runs/ar0307-ar0329-six-bam-apo8-x4-30fps-v2-20260831'

def rel(p):
    return p.relative_to(ROOT).as_posix()

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def payload(p):
    return {f.name: sha(f) for f in p.iterdir() if f.is_file()
            and (f.suffix == '.rgba' or f.name == v2.REGISTRY_NAME)}

def pack(destination, area, resources, source):
    destination.mkdir(parents=True)
    registry = v2.registry_v2_from_resources(resources, 3)
    (destination / v2.REGISTRY_NAME).write_bytes(registry)
    for resource in resources:
        for asset in resource['assets']:
            shutil.copy2(source(resource) / asset['name'], destination / asset['name'])
    manifest = dict(schema=v2.PACK_SCHEMA, status='completed', created_utc=v2.utc_now(),
        scale=4, registry_version=3, registry=v2.REGISTRY_NAME,
        runtime_contract=dict(feature='TimedTimeline', clock='QPC-pause-aware', registry_version=3),
        registry_sha256=sha(destination / v2.REGISTRY_NAME), registry_bytes=len(registry),
        resource_count=len(resources), frame_count=sum(r['frame_count'] for r in resources),
        timed_resources=[r['resref'] for r in resources if r['playback_mode'] == 'TimedTimeline'],
        raw_bytes=sum(a['bytes'] for r in resources for a in r['assets']),
        runtime_budget_enforced=True, base_assets=[], new_assets=[], resources=resources)
    if area:
        manifest['area_id'] = area
    write(destination / 'manifest.json', manifest)
    v2.validate_v2_pack(destination)

def make_mask():
    initial = np.asarray(Image.open(BATCH / 'work/initial-mask.png')) > 127
    paths = plt.contour(initial.astype(np.uint8), levels=[0.5]).get_paths()
    plt.close()
    contour = max((p.vertices for p in paths), key=len)
    if np.allclose(contour[0], contour[-1]):
        contour = contour[:-1]
    points = resample_closed(contour, 1.5)
    spline, _ = splprep([points[:, 0], points[:, 1]], s=len(points), per=True, k=3)
    curve = np.asarray(splev(np.linspace(0, 1, len(points) * 4, endpoint=False), spline)).T
    high = Image.new('L', (680 * 4, 520 * 4))
    ImageDraw.Draw(high).polygon([tuple(p * 4) for p in curve], fill=255)
    inside = np.asarray(high) > 127
    t = np.clip(distance_transform_edt(inside) / (8 * 4), 0, 1)
    t = t * t * (3 - 2 * t)
    mask = Image.fromarray(np.rint(t * 255).astype(np.uint8)).resize((680,520), Image.Resampling.BOX)
    mask.save(BATCH / 'water-mask-fit1-inner8-x4.png')
    return np.asarray(mask)

def prepare():
    assert not RUN.exists() and not PACK.exists(), 'Immutable outputs already exist'
    mask = make_mask()
    _, source_resources = v2.validate_v2_pack(BASE / 'AR0307')
    target = copy.deepcopy(next(r for r in source_resources if r['resref'] == 'AM0307BH'))
    live = GAME / 'iee-assets/areas/AR0307'
    frames_dir = BATCH / 'masked-frames'
    frames_dir.mkdir()
    expected = {a['name']: a for a in target['assets']}
    source_hashes = {}
    samples = []
    for frame in target['frames']:
        original = (live / frame['asset']).read_bytes()
        assert sha(live / frame['asset']) == frame['sha256'].lower(), 'Unexpected active AM0307BH version'
        rgba = np.frombuffer(original, np.uint8).reshape(520,680,4).copy()
        before = rgba.copy()
        rgba[:,:,3] = ((rgba[:,:,3].astype(np.uint16) * mask.astype(np.uint16) + 127) // 255).astype(np.uint8)
        assert np.array_equal(rgba[:,:,:3], before[:,:,:3]), 'RGB changed'
        assert not rgba[mask == 0,3].any()
        assert np.array_equal(rgba[mask == 255], before[mask == 255]), 'Core water changed'
        assert not rgba[0,:,3].any() and not rgba[-1,:,3].any() and not rgba[:,0,3].any() and not rgba[:,-1,3].any()
        destination = frames_dir / frame['asset']
        destination.write_bytes(rgba.tobytes())
        source_hashes[frame['asset']] = sha(live / frame['asset'])
        frame['sha256'] = sha(destination)
        expected[frame['asset']]['sha256'] = frame['sha256']
        if frame['frame'] == 0:
            samples = [Image.fromarray(before), Image.fromarray(rgba)]
    assert v2.resource_binary_v2(target,3) == v2.resource_binary_v2(next(r for r in source_resources if r['resref']=='AM0307BH'),3), 'Runtime timing/geometry changed'
    pack(RUN / '03_runtime_pack', None, [target], lambda r: frames_dir)
    extra = next(r for r in v2.load_json(EXTRA / 'manifest.json')['resources'] if r['resref']=='FLAME2S')
    baselines = {}
    entries = []
    for area in AREAS:
        live = GAME / 'iee-assets/areas' / area
        _, old = v2.validate_v2_pack(BASE / area)
        resources = copy.deepcopy(old) + [copy.deepcopy(extra)]
        resources.sort(key=v2.resource_sort_key)
        registry = (live / v2.REGISTRY_NAME).read_bytes()
        assert v2.registry_v2_from_resources(resources,3) == registry, area + ' unknown registry'
        for resource in resources:
            for asset in resource['assets']:
                assert (live / asset['name']).stat().st_size == asset['bytes']
                asset['sha256'] = sha(live / asset['name'])
            names = {a['name']:a for a in resource['assets']}
            for frame in resource['frames']:
                frame['sha256'] = names[frame['asset']]['sha256']
        current = next(r for r in resources if r['resref']=='AM0307BH')
        assert {a['name']:a['sha256'] for a in current['assets']} == source_hashes, area + ' AM0307BH differs'
        baseline = payload(live)
        resources = [copy.deepcopy(target) if r['resref']=='AM0307BH' else r for r in resources]
        pack(PACK / area, area, resources, lambda r: frames_dir if r['resref']=='AM0307BH' else live)
        assert (PACK / area / v2.REGISTRY_NAME).read_bytes() == registry
        for name,digest in baseline.items():
            if not name.startswith('AAX4-AM0307BH-'):
                assert sha(PACK / area / name) == digest, 'Sibling changed: ' + name
        baselines[area] = dict(payload=baseline, output_payload=payload(PACK / area))
        entries.append(dict(area_id=area, directory=area, manifest_sha256=sha(PACK / area / 'manifest.json'), registry_sha256=sha(PACK / area / v2.REGISTRY_NAME)))
    write(PACK / 'manifest.json', dict(schema='bg2-upscale-area-animation-pack-index-v1',status='completed', created_utc=v2.utc_now(),areas=entries))
    write(RUN / 'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v2.utc_now(),resrefs=['AM0307BH'],
        source_run=rel(SOURCE_RUN), source_run_manifest_sha256=sha(SOURCE_RUN/'manifest.json'),
        output_split_root=rel(PACK),output_manifest_sha256=sha(PACK/'manifest.json'),
        runtime_pack='03_runtime_pack',runtime_pack_manifest_sha256=sha(RUN/'03_runtime_pack/manifest.json'),
        water_mask=rel(BATCH/'water-mask-fit1-inner8-x4.png'),water_mask_sha256=sha(BATCH/'water-mask-fit1-inner8-x4.png'),
        runtime_contract=dict(scale=4,fps=30,frame_count=21,timeline_phases=28,native_lookup=[0,0,1,1,2,2,3,3,4,4,5,5,6,6],
            timing='unchanged installed native-slots-x2; cancelled collapse correction not used',duration_seconds=14/15,RGB='byte-identical all pixels',
            geometry='unchanged canvas170x130 centre85,130',alpha='fixed water-only Fit1 spline; SS4 BOX; smoothstep inside8px x4'),
        qa_status='pending-explicit-user-ingame-approval'))
    write(RECIPE/'baseline.json',dict(areas=baselines))
    bg = Image.open(BATCH/'work/background.png').convert('RGBA')
    board = Image.new('RGB',(1380,560),(25,25,25))
    draw = ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    draw.text((10,7),'Avant : fond rectangulaire opaque',font=font,fill='white')
    draw.text((700,7),'Correctif : eau seule / spline Fit1 / fondu interieur',font=font,fill='white')
    board.paste(samples[0].convert('RGB'),(0,35))
    board.paste(Image.alpha_composite(bg,samples[1]).convert('RGB'),(700,35))
    board.save(BATCH/'AM0307BH-before-after-map.png')
    write(RECIPE/'checks.json',dict(passed=True,frames=21,all_RGB_unchanged=True,water_core_unchanged=True,
        fixed_alpha_all_frames=True,transparent_canvas_edges=True,registry_byte_identical=True,siblings_byte_identical=True,
        mask_opaque_pixels=int((mask==255).sum()),mask_partial_pixels=int(((mask>0)&(mask<255)).sum()),mask_transparent_pixels=int((mask==0).sum()),
        preview='Simulation on processed map PNG crop; not ingame QA'))
    print('21 frames: RGB/core/timing/geometry unchanged; water-only alpha; siblings and registry identical')

def install():
    result=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader|BGMain' }).Count"],capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='0','Game or InfinityLoader running'
    receipt=RECIPE/'installation.json'
    assert not receipt.exists(),'Immutable receipt exists'
    baseline=v2.load_json(RECIPE/'baseline.json')['areas']
    backup=ROOT/'backups/animations'/TAG
    assert not backup.exists()
    for area in AREAS:
        v2.validate_v2_pack(PACK/area)
        assert payload(GAME/'iee-assets/areas'/area)==baseline[area]['payload'],area+' drift since preparation'
    data=dict(schema='bg2-upscale-animation-targeted-alpha-install-v1',status='installed-pending-ingame-qa',created_utc=v2.utc_now(),
        resref='AM0307BH',run=rel(RUN),pack=rel(PACK),areas={})
    for area in AREAS:
        live=GAME/'iee-assets/areas'/area
        saved=backup/area;saved.mkdir(parents=True)
        names=[n for n in baseline[area]['payload'] if n.startswith('AAX4-AM0307BH-')]
        for name in names:shutil.copy2(live/name,saved/name)
        try:
            for name in names:shutil.copy2(PACK/area/name,live/name)
            assert payload(live)==baseline[area]['output_payload'],area+' installation mismatch'
        except Exception:
            for name in names:shutil.copy2(saved/name,live/name)
            raise
        data['areas'][area]=dict(backup=rel(saved),before=baseline[area]['payload'],after=payload(live),registry_unchanged=True,siblings_unchanged=True)
    write(receipt,data)
    row,rows=workflow._registry_row(ROOT,'AM0307BH')
    row['notes']=('Correctif alpha eau seule installe AR0307/AR0329 2026-10-11 : contour eau fixe spline Fit1, SS4 BOX, smoothstep interieur8px x4 ; '
        'decor hors eau transparent pour conserver le raccord avec la map. RGB, 21frames, timeline28phases a30fps, boucle14/15s, geometrie et registres actifs strictement conserves. '
        'Correctif collapse annule non repris. Run '+rel(RUN)+' ; recu '+rel(receipt)+'. QA ingame du masque ouverte ; aucune release.')
    (ROOT/workflow.REGISTRY_REL).write_bytes(workflow._render_registry(rows))
    print('Installed AR0307/AR0329; registry and siblings unchanged; backup '+rel(backup))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    install() if args.install else prepare()
