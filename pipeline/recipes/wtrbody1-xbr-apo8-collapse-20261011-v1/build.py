"""WTRBODY1 only: deduplicate xBR anchors, interpolate at unchanged duration, install."""
from pathlib import Path
import argparse
import copy
import csv
import io
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v
import merge_area_pack_resources as merge
import area_animation_area_test as installer
import area_pack_state as state
from animation_authority_lock import animation_authority_lock
from sync_animation_upscale_registry import write_atomic
from workspace_paths import get_path

TAG = 'wtrbody1-xbr-apo8-collapse-20261011-v1'
BATCH = ROOT/'animations/batches'/TAG
BASE = BATCH/'00_deduplicated_native_pack'
RUN = ROOT/'animations/ressources/WTRBODY1/runs'/TAG
PACK = ROOT/'animations/packs-par-zone'/TAG
OLD = ROOT/'animations/packs-par-zone/lot2-small-effects-20261011-v1-complete/AR0502'
GAME = get_path('bg2ee_game_root')


def rel(path):
    return path.relative_to(ROOT).as_posix()


def payload(path):
    return {p.name: v.sha256_file(p) for p in path.iterdir()
            if p.is_file() and p.name != 'manifest.json'}


def prepare():
    BATCH.mkdir(parents=True, exist_ok=False)
    old_manifest, old_resources = v.validate_v2_pack(OLD)
    old = next(r for r in old_resources if r['resref'] == 'WTRBODY1')
    assert old['frame_count'] == 20 and old['cycles'][0]['native_frame_indices'] == list(range(20))
    assert payload(OLD) == payload(GAME/'iee-assets/areas/AR0502')
    groups = {}
    lookup, frames, assets = [], [], []
    BASE.mkdir()
    for f in old['frames']:
        key = (tuple(f['logical_size_x1']), tuple(f['centre_x1']), f['sha256'])
        if key not in groups:
            index = len(groups)
            groups[key] = index
            name = v.asset_name('WTRBODY1', index)
            new = copy.deepcopy(f)
            new.update(frame=index, asset=name)
            frames.append(new)
            assets.append(dict(name=name, sha256=f['sha256'], bytes=f['bytes']))
            shutil.copy2(OLD/f['asset'], BASE/name)
        lookup.append(groups[key])
    assert lookup == [i for i in range(10) for _ in range(2)]
    target = copy.deepcopy(old)
    target.update(frame_count=10, frames=frames, assets=assets,
                  cycles=[dict(cycle=0, native_frame_indices=lookup, timeline_frame_indices=[])])
    registry = v.registry_v2_from_resources([target], 3)
    (BASE/v.REGISTRY_NAME).write_bytes(registry)
    manifest = copy.deepcopy(old_manifest)
    for key in ('area_id', 'merged_from'):
        manifest.pop(key, None)
    manifest.update(created_utc=v.utc_now(), resource_count=1, frame_count=10,
                    resources=[target], registry_bytes=len(registry),
                    registry_sha256=v.sha256_file(BASE/v.REGISTRY_NAME),
                    raw_bytes=sum(a['bytes'] for a in assets), timed_resources=[],
                    derived_from=rel(OLD), deduplicated_native_lookup=lookup)
    v.write_json(BASE/'manifest.json', manifest)
    v.validate_v2_pack(BASE)
    plan = v.build_plan(None, BASE, ['WTRBODY1'], collapse_uniform_duplicate_holds=True)
    cycle = plan['targets'][0]['cycles'][0]
    assert cycle['interpolation_input_frame_indices'] == list(range(10))
    assert cycle['timeline_phases'] == 40 and cycle['duration_seconds'] == 20/15
    v.write_json(BATCH/'plan.json', plan)
    v.build_run(None, BASE, RUN, ['WTRBODY1'], plan['plan_sha256'],
                v.DEFAULT_TVAI_FFMPEG, v.DEFAULT_TVAI_MODEL_DIR, 'apo-8', '-2', 'ffmpeg', False,
                collapse_uniform_duplicate_holds=True)
    finish()


def finish():
    _, old_resources = v.validate_v2_pack(OLD)
    old = next(r for r in old_resources if r['resref'] == 'WTRBODY1')
    _, resources = v.validate_v2_pack(RUN/'03_runtime_pack')
    r = next(x for x in resources if x['resref'] == 'WTRBODY1')
    assert r['frame_count'] == 40 and len(r['cycles'][0]['timeline_frame_indices']) == 40
    assert r['cycles'][0]['timeline_frame_indices'][::4] == list(range(10))
    for i in range(10):
        assert (OLD/old['frames'][i*2]['asset']).read_bytes() == (RUN/'03_runtime_pack'/r['frames'][i]['asset']).read_bytes()
    specs = [str(OLD)+'::'+r['resref'] for r in old_resources if r['resref'] != 'WTRBODY1']
    specs.append(str(RUN/'03_runtime_pack')+'::WTRBODY1')
    merge.merge(specs, 'AR0502', PACK, False)
    before, after = payload(OLD), payload(PACK/'AR0502')
    for name, digest in before.items():
        if name != v.REGISTRY_NAME and not name.startswith('AAX4-WTRBODY1-'):
            assert after[name] == digest
    v.write_json(BATCH/'baseline.json', dict(before=before, after=after))
    v.write_json(BATCH/'checks.json', dict(native_frames=20, unique_input_poses=10,
        input_fps='15/2', output_fps=30, timeline_phases=40, duration_seconds=20/15,
        stored_frames=r['frame_count'], distinct_output_pixels=len({f['sha256'] for f in r['frames']}),
        anchors_byte_identical=10, sibling_payload_unchanged=True,
        native_lookup_slots_preserved=20, loop_closure_interpolated=True))
    print('PREPARED: 10 unique xBR anchors -> 40 phases at 30 FPS; duration 20/15 s', flush=True)


def install():
    installer.ensure_game_stopped(installer.running_game_processes)
    assert not (BATCH/'installation.json').exists()
    baseline = v.load_json(BATCH/'baseline.json')
    leaf, live = PACK/'AR0502', GAME/'iee-assets/areas/AR0502'
    assert payload(live) == baseline['before']
    other_areas = {a: payload(GAME/'iee-assets/areas'/a) for a in ['AR0504', 'AR4000', 'AR0329', 'AR2903']}
    result = installer.install_area_pack(leaf, game_root=GAME)
    assert payload(live) == baseline['after']
    for area, hashes in other_areas.items():
        assert payload(GAME/'iee-assets/areas'/area) == hashes
    for attempt in range(3):
        try:
            state.record_zone('AR0502', GAME/'iee-assets/areas', leaf=leaf)
            break
        except PermissionError:
            if attempt == 2:
                raise
            time.sleep(.25)
    assert state.zone_signatures(live) == state.load_lock()['areas']['AR0502']['resources']
    v.write_json(BATCH/'installation.json', dict(status='installed', installed_utc=v.utc_now(),
        resref='WTRBODY1', area='AR0502', occurrences=1, run=rel(RUN), pack=rel(leaf),
        receipt=rel(result.receipt_path) if result.receipt_path else None,
        sibling_and_other_area_payloads_unchanged=True, qa_status='pending-ingame', release_status='not-selected'))
    with animation_authority_lock(ROOT):
        registry = ROOT/'animations/index/animation_upscale_registry.csv'
        rows = list(csv.DictReader(registry.open(encoding='utf-8-sig', newline='')))
        row = next(r for r in rows if r['resref'] == 'WTRBODY1')
        assert row['status'] == 'à-valider' and not row['qa_decision']
        row.update(selected_run=rel(RUN), correction_id=TAG,
            notes='WTRBODY1 xBR x4/Apollo8 : 20frames natives -> 10poses uniques avant interpolation 7.5->30fps; '
                  '40phases, duree20/15s conservee; 10ancres byte-identiques, FLAME2S et autres zones inchanges; '
                  'installe AR0502 le 2026-10-11; reçu animations/batches/'+TAG+'/installation.json; '
                  'QA ingame en attente; aucune release.')
        buf = io.StringIO(newline='')
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
        write_atomic(registry, buf.getvalue())
    print('INSTALLED: WTRBODY1 only, AR0502; all other choices preserved', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--finish', action='store_true')
    args = parser.parse_args()
    install() if args.install else finish() if args.finish else prepare()
