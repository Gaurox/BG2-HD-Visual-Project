"""Add the AR3017-approved FIRE_2B bytes to OH8100; preserve installed siblings."""
import argparse
import copy
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import animation_workflow as workflow
import area_pack_state as state
from workspace_paths import get_path

spec = importlib.util.spec_from_file_location('pack_helpers', ROOT / 'pipeline/recipes/dstdvl1a-misty-contour-native-geometry-20261011-v2/install.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
TAG = 'fire2b-oh8100-install-20261011-v1'
RECIPE = Path(__file__).resolve().parent
SOURCE = ROOT / 'animations/ressources/FIRE_2B/runs/ar3017-fire2b-luma0-16-edge8-premult-20260917/03_runtime_pack'
BASE = ROOT / 'animations/packs-par-zone/portails-deux-correctif-20261010-v1-complete/OH8100'
PACK = ROOT / 'animations/packs-par-zone' / TAG
LIVE = get_path('bg2ee_game_root') / 'iee-assets/areas/OH8100'


def prepare():
    assert not PACK.exists(), 'Immutable output exists'
    _, original = v.validate_v2_pack(BASE)
    _, selected = v.validate_v2_pack(SOURCE)
    target = selected[0]
    assert target['resref'] == 'FIRE_2B'
    assert (LIVE / v.REGISTRY_NAME).read_bytes() == v.registry_v2_from_resources(original, 3)
    before = h.payload(LIVE)
    resources = copy.deepcopy(original)
    for resource in resources:
        by_name = {a['name']: a for a in resource['assets']}
        for frame in resource['frames']:
            p = LIVE / frame['asset']
            assert p.stat().st_size == frame['bytes']
            frame['sha256'] = h.sha(p)
            by_name[frame['asset']]['sha256'] = frame['sha256']
    comparison = get_path('bg2ee_game_root') / 'iee-assets/areas/AR3017'
    assert all(h.sha(comparison / a['name']) == a['sha256'] for a in target['assets'])
    assert not any(n.startswith('AAX4-FIRE_2B-') for n in before)
    resources.append(copy.deepcopy(target))
    resources.sort(key=v.resource_sort_key)
    h.pack(PACK / 'OH8100', resources, lambda r: SOURCE if r['resref'] == 'FIRE_2B' else LIVE, 'OH8100')
    after = h.payload(PACK / 'OH8100')
    added = sorted(after.keys() - before.keys())
    assert len(added) == 30 and all(n.startswith('AAX4-FIRE_2B-') for n in added)
    assert all(before[n] == after[n] for n in before if n != v.REGISTRY_NAME)
    h.write(PACK / 'manifest.json', dict(schema='bg2-upscale-area-animation-pack-index-v1', status='completed', created_utc=v.utc_now(),
        areas=[dict(area_id='OH8100', directory='OH8100', manifest_sha256=h.sha(PACK / 'OH8100/manifest.json'),
                    registry_sha256=h.sha(PACK / 'OH8100' / v.REGISTRY_NAME))]))
    h.write(RECIPE / 'baseline.json', dict(before=before, after=after, added=added))
    h.write(RECIPE / 'checks.json', dict(passed=True, source=h.rel(SOURCE), source_manifest_sha256=h.sha(SOURCE / 'manifest.json'),
        frame_count=30, fps=30, native_canvas=[70,70], native_centre=[35,35], sequence=0,
        AR3017_approved_bytes_identical=True, installed_siblings_bytes_and_runtime_contract_preserved=True,
        raw_bytes=sum(a['bytes'] for r in resources for a in r['assets']), runtime_budget_bytes=v.MAX_RAW_BYTES,
        ingame_QA='OH8100 pending'))
    print('Prepared: FIRE_2B 30 frames; all OH8100 siblings preserved')


def install():
    result = subprocess.run(['powershell', '-NoProfile', '-Command',
        "@(Get-Process | Where-Object { $_.ProcessName -match 'Baldur|InfinityLoader|BGMain' }).Count"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == '0', 'Game or InfinityLoader running'
    receipt = RECIPE / 'installation.json'
    assert not receipt.exists()
    baseline = v.load_json(RECIPE / 'baseline.json')
    v.validate_v2_pack(PACK / 'OH8100')
    assert h.payload(LIVE) == baseline['before'], 'Installed payload drift'
    backup = ROOT / 'backups/animations' / TAG / 'OH8100'
    assert not backup.exists()
    backup.mkdir(parents=True)
    shutil.copy2(LIVE / v.REGISTRY_NAME, backup / v.REGISTRY_NAME)
    try:
        for name in baseline['added']:
            shutil.copy2(PACK / 'OH8100' / name, LIVE / name)
        shutil.copy2(PACK / 'OH8100' / v.REGISTRY_NAME, LIVE / v.REGISTRY_NAME)
        assert h.payload(LIVE) == baseline['after']
    except Exception:
        for name in baseline['added']:
            (LIVE / name).unlink(missing_ok=True)
        shutil.copy2(backup / v.REGISTRY_NAME, LIVE / v.REGISTRY_NAME)
        assert h.payload(LIVE) == baseline['before']
        raise
    state.record_zone('OH8100', LIVE.parent, leaf=PACK / 'OH8100')
    h.write(receipt, dict(schema='bg2-upscale-animation-targeted-install-v1', status='installed-pending-ingame-qa',
        created_utc=v.utc_now(), area='OH8100', resref='FIRE_2B', source=h.rel(SOURCE), pack=h.rel(PACK),
        backup=h.rel(backup), added_files=baseline['added'], registry_changed=True, siblings_unchanged=True,
        other_areas='not modified', game_and_loader_closed=True))
    row, rows = workflow._registry_row(ROOT, 'FIRE_2B')
    row['notes'] += ' OH8100 : version AR3017 identique installee 2026-10-11 (30frames/30fps, alpha luminance0-16, canvas fade8px x4, RGB premultiplie). Pack ' + h.rel(PACK) + ' ; recu ' + h.rel(receipt) + '. QA OH8100 ouverte ; autres assets et maps conserves ; aucune release.'
    (ROOT / workflow.REGISTRY_REL).write_bytes(workflow._render_registry(rows))
    print('Installed FIRE_2B on OH8100; 30 added frames; siblings unchanged; QA pending')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--install', action='store_true')
    args = p.parse_args()
    install() if args.install else prepare()
