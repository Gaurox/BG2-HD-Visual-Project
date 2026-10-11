"""Approved edge treatment on every remaining DSTDVL1A/B/C area; no timing change."""
import argparse
import copy
import hashlib
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import animation_workflow as workflow
import area_pack_state as state
from workspace_paths import get_path

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

h = module('pack_helpers', ROOT / 'pipeline/recipes/dstdvl1a-misty-contour-native-geometry-20261011-v2/install.py')
blur = module('approved_edge_recipe', ROOT / 'pipeline/recipes/dstdvl1a-misty-contour-20261011-v1/build.py')
TAG = 'dstdvl1abc-nine-maps-misty-20261011-v1'
AREAS = ['AR0414', 'AR1100', 'AR1200', 'AR1600', 'AR1700', 'AR5200', 'AR5500', 'AR6300', 'OH6400']
TARGETS = ['DSTDVL1A', 'DSTDVL1B', 'DSTDVL1C']
RECIPE = Path(__file__).resolve().parent
RUN = ROOT / 'animations/batches' / TAG
PACK = ROOT / 'animations/packs-par-zone' / TAG
LIVE = get_path('bg2ee_game_root') / 'iee-assets/areas'
APPROVED = ROOT / 'animations/packs-par-zone/ar0411-dstdvl-family-misty-contour-20261011-v1/AR0411'

def prepare():
    assert not RUN.exists() and not PACK.exists(), 'Immutable output exists'
    lock = v.load_json(state.LOCK_PATH)
    approved = v.load_json(APPROVED / 'manifest.json')['resources']
    approved_hashes = {r['resref']: {f['frame']: f['sha256'] for f in r['frames']} for r in approved if r['resref'] in TARGETS}
    cache = {}; baselines = {}; metrics = {}; entries = []; sources = {}; samples = {}
    protected = h.payload(LIVE / 'AR0411')
    for area in AREAS:
        live = LIVE / area
        build = lock['areas'][area]['build']
        refs = [build['leaf']] if 'leaf' in build else build['merged_from']
        resources_by_key = {}; sources[area] = []
        for ref in refs:
            path, sep, selection = ref.partition('::')
            source = ROOT / path
            _, resources = v.validate_v2_pack(source)
            sources[area].append(dict(path=path, manifest_sha256=h.sha(source / 'manifest.json'), selected_resource=selection or '*'))
            for r in resources:
                if not sep or r['resref'] == selection:
                    resources_by_key[(r['resref'], r.get('variant_index', 0))] = copy.deepcopy(r)
        resources = sorted(resources_by_key.values(), key=v.resource_sort_key)
        assert (live / v.REGISTRY_NAME).read_bytes() == v.registry_v2_from_resources(resources, 3)
        before = h.payload(live)
        stage = RUN / 'frames' / area
        stage.mkdir(parents=True)
        metrics[area] = {}
        for r in resources:
            # Preserve the actual installed bytes of every sibling, including recent smoke corrections.
            by_name = {a['name']: a for a in r['assets']}
            for f in r['frames']:
                assert (live / f['asset']).stat().st_size == f['bytes']
                if r['resref'] in TARGETS:
                    assert before[f['asset']] == f['sha256'], 'Unexpected target version'
                f['sha256'] = before[f['asset']]
                by_name[f['asset']]['sha256'] = f['sha256']
            if r['resref'] not in TARGETS:
                continue
            original = copy.deepcopy(r)
            changed = core_count = approved_match = 0
            best = -1
            for f in r['frames']:
                w, height = f['physical_size_x4']
                blob = (live / f['asset']).read_bytes()
                key = (f['sha256'], w, height)
                source = np.frombuffer(blob, np.uint8).reshape(height, w, 4)
                assert np.all(source[:, :, :3] <= source[:, :, 3:4])
                if key not in cache:
                    padded, core = blur.treat(source, 20, 4)
                    if source[:, :, 3].any():
                        result = padded[24:-24, 24:-24].copy()
                        core = core[24:-24, 24:-24]
                    else:
                        result = padded
                    assert result.shape == source.shape and np.array_equal(result[core], source[core])
                    assert np.all(result[:, :, :3] <= result[:, :, 3:4])
                    cache[key] = (result.tobytes(), int(core.sum()))
                output, core_pixels = cache[key]
                core_count += core_pixels
                changed += int(output != blob)
                dest = stage / f['asset']
                dest.write_bytes(output)
                f['sha256'] = hashlib.sha256(output).hexdigest()
                by_name[f['asset']]['sha256'] = f['sha256']
                if r['frame_count'] == 139:
                    assert f['sha256'] == approved_hashes[r['resref']][f['frame']], 'AR0411 recipe mismatch'
                    approved_match += 1
                profile = (r['resref'], r['frame_count'])
                score = int(source[:, :, :3].sum())
                if profile not in samples or score > samples[profile][0]:
                    samples[profile] = (score, source.copy(), np.frombuffer(output, np.uint8).reshape(height, w, 4).copy())
            assert v.resource_binary_v2(r, 3) == v.resource_binary_v2(original, 3)
            metrics[area][r['resref']] = dict(frame_count=r['frame_count'], changed_frames=changed,
                core_pixels_byte_identical=core_count, approved_AR0411_matching_frames=approved_match,
                geometry_centres_and_timeline_preserved=True)
        h.pack(PACK / area, resources, lambda r: stage if r['resref'] in TARGETS else live, area)
        after = h.payload(PACK / area)
        assert before.keys() == after.keys()
        changed_names = sorted(n for n in before if before[n] != after[n])
        assert all(any(n.startswith('AAX4-' + ref + '-') for ref in TARGETS) for n in changed_names)
        assert before[v.REGISTRY_NAME] == after[v.REGISTRY_NAME]
        baselines[area] = dict(before=before, after=after, changed_files=changed_names)
        entries.append(dict(area_id=area, directory=area, manifest_sha256=h.sha(PACK / area / 'manifest.json'), registry_sha256=h.sha(PACK / area / v.REGISTRY_NAME)))
        print(area + ': ' + str(len(changed_names)) + ' edge frames; registry/timing/siblings unchanged', flush=True)
    h.write(PACK / 'manifest.json', dict(schema='bg2-upscale-area-animation-pack-index-v1', status='completed', created_utc=v.utc_now(), areas=entries))
    h.write(RUN / 'manifest.json', dict(schema='bg2-upscale-animation-final-selection-v1', status='completed', created_utc=v.utc_now(), resrefs=TARGETS,
        output_split_root=h.rel(PACK), output_manifest_sha256=h.sha(PACK / 'manifest.json'), source_area_packs=sources,
        visual_treatment=dict(recipe=h.rel(Path(blur.__file__)), inner_feather_x4=20, gaussian_sigma_x4=4,
            native_canvas_crop=True, core_distance36_byte_identical=True, premultiplied_RGBA=True,
            timing='every installed area version preserved; 139 or 50 frames; no deduplication/interpolation'),
        metrics=metrics, qa_status='pending-user-ingame-QA on nine areas; previous AR0411 QA unchanged'))
    h.write(RECIPE / 'baseline.json', dict(areas=baselines, protected_AR0411=protected))
    h.write(RECIPE / 'checks.json', dict(passed=True, metrics=metrics, registry_and_siblings_preserved=True,
        AR0411_preserved=True, applied_once=True, unique_frame_transforms=len(cache)))
    board = Image.new('RGB', (1860,780), (24,24,28)); d = ImageDraw.Draw(board)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    for row, count in enumerate([139,50]):
        for col, name in enumerate(TARGETS):
            _, src, dst = samples[(name,count)]
            x=col*620; y=row*390
            d.text((x+12,y+10),name+' / '+str(count)+' frames : avant -> apres',fill='white',font=font)
            for j,a in enumerate([src,dst]):
                rgb=np.clip(a[:,:,:3].astype(float)+30*(1-a[:,:,3:4]/255),0,255).astype('uint8')
                im=Image.fromarray(rgb);im.thumbnail((300,300),Image.Resampling.LANCZOS)
                board.paste(im,(x+j*310+(300-im.width)//2,y+70+(300-im.height)//2))
    board.save(RUN / 'DSTDVL-nine-maps-before-after.png')

def install():
    check=subprocess.run(['powershell','-NoProfile','-Command',"@(Get-Process | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader|BGMain' }).Count"],capture_output=True,text=True,check=True)
    assert check.stdout.strip()=='0', 'Game or InfinityLoader running'
    assert not (RECIPE / 'installation.json').exists()
    baseline=v.load_json(RECIPE / 'baseline.json')
    assert h.payload(LIVE / 'AR0411')==baseline['protected_AR0411']
    backup=ROOT / 'backups/animations' / TAG
    assert not backup.exists()
    for area in AREAS:
        v.validate_v2_pack(PACK / area)
        assert h.payload(LIVE / area)==baseline['areas'][area]['before'], 'Installed payload drift '+area
        (backup / area).mkdir(parents=True)
        for name in baseline['areas'][area]['changed_files']:
            shutil.copy2(LIVE / area / name, backup / area / name)
    try:
        for area in AREAS:
            for name in baseline['areas'][area]['changed_files']:
                shutil.copy2(PACK / area / name,LIVE / area / name)
            assert h.payload(LIVE / area)==baseline['areas'][area]['after']
        assert h.payload(LIVE / 'AR0411')==baseline['protected_AR0411']
    except Exception:
        for area in AREAS:
            for name in baseline['areas'][area]['changed_files']:
                shutil.copy2(backup / area / name,LIVE / area / name)
            assert h.payload(LIVE / area)==baseline['areas'][area]['before']
        raise
    for area in AREAS:
        state.record_zone(area,LIVE,leaf=PACK / area)
    receipt=RECIPE / 'installation.json'
    h.write(receipt,dict(schema='bg2-upscale-animation-targeted-visual-install-v1',status='installed-pending-ingame-qa',created_utc=v.utc_now(),
        areas=AREAS,resrefs=TARGETS,run=h.rel(RUN),pack=h.rel(PACK),backup=h.rel(backup),
        changed_files={a:baseline['areas'][a]['changed_files'] for a in AREAS},
        registry_and_siblings_unchanged=True,AR0411_unchanged=True,game_and_loader_closed=True,release_changed=False))
    _,rows=workflow._registry_row(ROOT,TARGETS[0])
    for row in rows:
        if row['resref'] in TARGETS:
            row['notes'] = 'QA ingame AR0411 validee utilisateur 2026-10-11 ; decision animations/index/area-qa-decisions/'+row['resref']+'/2026-10-11-accepted-'+row['resref'].lower()+'-ar0411-misty-contour-v1.json. '
            row['notes'] += 'Correctif brumeux identique propage le 2026-10-11 aux neuf autres maps ('+';'.join(AREAS)+') : fondu20px x4 + Gaussian sigma4 en bordure, RGBA premultiplie, coeur et version temporelle de chaque map conserves (139/50frames). '
            row['notes'] += 'Run '+h.rel(RUN)+' ; recu '+h.rel(receipt)+'. QA AR0411 acquise et inchangee ; QA neuf autres maps ouverte, statut global a-valider. Aucune release.'
    (ROOT / workflow.REGISTRY_REL).write_bytes(workflow._render_registry(rows))
    print('Installed nine areas; all registries, siblings, timing and AR0411 unchanged',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');args=p.parse_args()
    install() if args.install else prepare()
