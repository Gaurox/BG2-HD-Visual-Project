"""Build isolated dry/rain WTSWAM timelines for two pilots; plan-only without --run."""
from __future__ import annotations
import argparse
import copy
import json
import shutil
import struct
from pathlib import Path
import build_wtswam_route2_pilot as pilot
import build_wtsew_route2_pilot as common
from build_wtlake_timeline_batch import pvrz_metadata

ROOT = pilot.ROOT
PARENT = ROOT/'maps/water-batches/runs/wtswam-ar1607-ar1800-repair-20260912-v2/registry-v3.json'
PARENT_SHA = '877BC199CB31B70F2A5D31EDAF77E19E55D8556819B493797CAD8CF46BC854C5'
RAIN_SHA = 'F127DCE6A09F2F26C61E169533E9F1FEB5A349D441F6F44EFF01CE87F9F76403'
AREAS = ('AR1607', 'AR1800')
DRY, WET = 'WSWPIL', 'WSWPILR'
DRY_PAGE, WET_PAGE = 'WWPIL00', 'WWPILR00'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    common.require(ROOT in out.parents and not out.exists(), 'new workspace run required')
    common.require(common.sha256_file(PARENT) == PARENT_SHA, 'registry drift')
    registry = json.loads(PARENT.read_text(encoding='utf-8'))
    verified = common.verify_live_registry(registry)
    bifs, resources = pilot.load_key()
    locator = next(loc for name, kind, loc in resources if name.upper() == 'WTSWAMR' and kind == 0x3eb)
    raw, count, size, archive = pilot.resolve_tileset_resource(bifs, locator)
    common.require((count, size) == (6, 5120) and common.sha256_bytes(raw) == RAIN_SHA, 'rain source drift')
    live = common.get_path('bg2ee_game_root')/'override'
    for name in (DRY, WET, DRY_PAGE, WET_PAGE):
        common.require(not any((live/(name+ext)).exists() for ext in ('.TIS','.PVRZ')), 'alias already installed')
        common.require(not any(n.upper() == name for n,k,l in resources), 'alias KEY collision')
    plan = {'schema': 'bg2-wtswam-rain-repair-v1', 'asset_ids': ['overlays:WTSWAMR','maps:AR1607:day','maps:AR1800:day'],
            'parent_registry': common.relative(PARENT), 'parent_sha256': PARENT_SHA,
            'stock_rain': {'resref':'WTSWAMR','sha256':RAIN_SHA,'archive':archive,'frames':count},
            'aliases': [DRY,WET], 'verified_live_files': verified,
            'recipe': 'SeedVR2 x4 none periodic3x3; Apollo8 36phases15Hz; renderer30FPS q0.70',
            'tests':'not-run-user-choice', 'qa':'pending-ingame', 'release':'not-requested'}
    print(json.dumps(plan), flush=True)
    if not args.run:
        return
    out.mkdir(parents=True)
    common.write_json(out/'plan.json', plan)
    rgb, alpha = common.prepare_periodic_inputs(common.decode_legacy_frames(raw), out)
    anchors, seedvr = common.upscale_anchors(rgb, alpha, out)
    frames, apollo = common.interpolate(anchors, out)
    rain_tis, rain_page = pilot.build_overlay(frames, out/'07_rain_x4')
    candidate = out/'08_candidate'
    candidate.mkdir()
    for src, name in ((live/'WTSWAM.TIS',DRY+'.TIS'),(live/'WSWAM00.PVRZ',DRY_PAGE+'.PVRZ'),
                      (rain_tis,WET+'.TIS'),(rain_page,WET_PAGE+'.PVRZ')):
        shutil.copy2(src, candidate/name)
    rain_entries = []
    for area in AREAS:
        entry = next(e for e in registry['entries'] if e['wed']['resref'] == area)
        wed = bytearray((live/(area+'.WED')).read_bytes())
        common.require(common.sha256_bytes(wed) == entry['wed']['sha256'], 'WED drift')
        header = struct.unpack_from('<I',wed,16)[0]+24
        common.require(wed[header+4:header+12].rstrip(b'\0') == b'WTSWAM', 'overlay name drift')
        wed[header+4:header+12] = DRY.encode().ljust(8,b'\0')
        (candidate/(area+'.WED')).write_bytes(wed)
        entry['wed']['sha256'] = common.sha256_bytes(wed)
        entry['wed']['overlay_slots'][1] = DRY
        entry['overlay'].update(tis_resref=DRY, pages=[pvrz_metadata(candidate/(DRY_PAGE+'.PVRZ'))])
        entry['qa'] = {'status':'pending-ingame','reference':common.relative(out/'run.json')}
        rain = copy.deepcopy(entry)
        rain['id'] = f'wtswamr-{area.lower()}-rain-slot1-q070-v4'
        rain['overlay'].update(tis_resref=WET, tis_sha256=common.sha256_file(candidate/(WET+'.TIS')),
                               tis_bytes=(candidate/(WET+'.TIS')).stat().st_size,
                               pages=[pvrz_metadata(candidate/(WET_PAGE+'.PVRZ'))])
        rain_entries.append(rain)
    original = json.loads(PARENT.read_text(encoding='utf-8'))
    common.require(registry['entries'][:15] == original['entries'][:15], 'prior identities changed')
    registry['entries'].extend(rain_entries)
    registry['experiment'] = {'scope':list(AREAS),'dry_rain_aliases':[DRY,WET],'parent':common.relative(PARENT)}
    common.write_json(out/'registry-v3.json',registry)
    files = {p.name:{'sha256':common.sha256_file(p),'bytes':p.stat().st_size} for p in candidate.iterdir()}
    common.write_json(candidate/'manifest.json', {'schema':'bg2-upscale-area-animation-override-assets-v1',
        'status':'completed','area':'AR1607-AR1800','files':files,'qa_status':'pending-ingame'})
    common.write_json(out/'run.json', plan | {'seedvr':seedvr,'apollo':apollo,
        'producer_sha256':common.sha256_file(Path(__file__)),
        'registry_sha256':common.sha256_file(out/'registry-v3.json'),
        'candidate_manifest_sha256':common.sha256_file(candidate/'manifest.json'),'installation':'not-run'})
    print('candidate completed', flush=True)


if __name__ == '__main__':
    main()
