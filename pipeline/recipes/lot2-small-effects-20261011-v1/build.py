"""Lot2: ReboutCX flames; xBR bubbles/eyes/dark motif; scoped QA packs."""
from pathlib import Path
import json
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
import split_animation_pack_by_area as split
import build_blended_rgb_neutral_pack as neutral
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
from build_alpha_feather import inner_feather_ramp
from workspace_paths import get_path

TAG = 'lot2-small-effects-20261011-v1'
BATCH = ROOT / 'animations/batches' / TAG
PACKS = ROOT / 'animations/packs-par-zone'
SOURCE = ROOT / 'animations/batches/lot2-apo8-x4-30fps-20261011-v1/03_runtime_pack'
SPATIAL = ROOT / 'animations/batches/lot2-reboutcx-xbr-x4-20261011-v1'
GAME = get_path('bg2ee_game_root')
JOBS = {'AM0504SB': ('AR0504', 'ReboutCX', 12),
        'AM4000Z': ('AR4000', 'ReboutCX', 0),
        'BUBBLEA': ('AR2903', 'xBR2 blend -> nearest2', 0),
        'EYESRED1': ('AR0329', 'xBR2 -> nearest2', 0),
        'WTRBODY1': ('AR0502', 'xBR2 -> nearest2', 0)}


def rel(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def payload(path):
    return {p.name: v.sha256_file(p) for p in sorted(path.iterdir())
            if p.is_file() and p.name != 'manifest.json'} if path.exists() else None


def pixels(pack, frame):
    w, h = frame['physical_size_x4']
    return np.frombuffer((pack / frame['asset']).read_bytes(), np.uint8).reshape(h, w, 4)


def sweep(resources):
    result = {}
    for r in resources:
        ref = r['resref']
        if ref not in ('AM0504SB', 'AM4000Z'):
            continue
        tests = []
        for radius in ([4, 8, 12] if ref == 'AM0504SB' else [0, 2, 4]):
            losses, cores, sparks, edges = [], [], [], []
            for frame in r['frames']:
                p = pixels(SOURCE, frame)
                a = p[..., 3]
                lum = p[..., :3].astype(float) @ np.array([.2126, .7152, .0722])
                visible = a > 0
                ramp = inner_feather_ramp(a, radius) if radius else np.ones(a.shape)
                after = lum * ramp * a / 255
                core = visible & (lum >= max(20, float(np.percentile(lum[visible], 90))))
                if core.any():
                    cores.append(1 - float(after[core].sum() / lum[core].sum()))
                losses.append(1 - float(after.sum() / lum[visible].sum()))
                components, _ = label(visible, np.ones((3, 3)))
                counts = np.bincount(components.ravel())
                small = (counts <= 48) & (counts > 0)
                small[0] = False
                tiny = small[components] & (lum > 20)
                if tiny.any():
                    sparks.append(1 - float(after[tiny].sum() / lum[tiny].sum()))
                edges.extend(np.concatenate([after[:4].ravel(), after[-4:].ravel(),
                                             after[:, :4].ravel(), after[:, -4:].ravel()]))
            tests.append(dict(radius_x4=radius, max_core_loss_pct=100 * max(cores),
                              mean_energy_loss_pct=100 * float(np.mean(losses)),
                              max_tiny_component_loss_pct=100 * max(sparks, default=0),
                              mean_canvas_edge_luminance=float(np.mean(edges))))
        result[ref] = dict(tests=tests, selected_radius_x4=JOBS[ref][2])
    assert result['AM0504SB']['tests'][-1]['max_core_loss_pct'] <= 5
    assert result['AM4000Z']['tests'][1]['max_tiny_component_loss_pct'] > 80
    return result


def preview(final):
    sheet = Image.new('RGB', (960, 1020), (34, 34, 34))
    draw = ImageDraw.Draw(sheet)
    for row, (ref, (area, _, _)) in enumerate(JOBS.items()):
        pack = final / area
        manifest = v.load_json(pack / 'manifest.json')
        resource = next(r for r in manifest['resources'] if r['resref'] == ref)
        cycle = resource['cycles'][0]
        sequence = cycle['timeline_frame_indices'] or cycle['native_frame_indices']
        phases = [0, len(sequence)//3, len(sequence)*2//3]
        if ref == 'BUBBLEA':
            phases = [0, 24, 36]
        draw.text((12, row * 204 + 5), f'{ref} / {area} / additive preview, not ingame', fill='white')
        for column, phase in enumerate(phases):
            frame = resource['frames'][sequence[phase]]
            rgba = pixels(pack, frame)
            # Blended assets add premultiplied RGB directly; alpha_composite would multiply twice.
            rgb = rgba[..., :3].astype(np.uint16)
            h, w = rgb.shape[:2]
            base = np.full((h, w, 3), 34, np.uint16)
            image = Image.fromarray(np.minimum(base + rgb, 255).astype(np.uint8))
            factor = min(1.0, 290 / w, 165 / h)
            if factor != 1:
                image = image.resize((round(w*factor), round(h*factor)), Image.Resampling.LANCZOS)
            if ref == 'EYESRED1':
                image = image.resize((w*3, h*3), Image.Resampling.NEAREST)
            sheet.paste(image, (column*320 + (320-image.width)//2, row*204 + 35))
            draw.text((column*320+12, row*204+185), f'phase {phase} / frame {frame["frame"]}', fill='white')
    sheet.save(BATCH / 'preview-additive.png')


def main():
    BATCH.mkdir(parents=True, exist_ok=False)
    _, resources = v.validate_v2_pack(SOURCE)
    v.write_json(BATCH / 'feather-sweep.json', sweep(resources))
    initial = PACKS / (TAG + '-source')
    split.split(SOURCE, initial, ROOT / 'animations/index/occurrences.csv', False)
    first = PACKS / (TAG + '-purple-inner12')
    neutral.build(initial, first, {'AM0504SB'}, False, 'premultiply', None, 12)
    final = PACKS / (TAG + '-final-assets')
    neutral.build(first, final, set(JOBS) - {'AM0504SB'}, False, 'premultiply', None, 0)

    # Reconstruct only targeted installed areas. AR0329 has newer accepted water/timing
    # than its old lock recipe; use the exact current accepted complete leaf.
    lock = v.load_json(ROOT / 'animations/index/area-pack-lock.json')
    baselines, selected = {}, []
    for ref, (area, spatial, radius) in JOBS.items():
        live = GAME / 'iee-assets/areas' / area
        before = payload(live)
        baselines[area] = dict(present=live.exists(), payload=before)
        specs = []
        if live.exists():
            if area == 'AR0329':
                preserved = PACKS / 'am307red-collapse-preserve-look-20261011-v1' / area
            else:
                build = lock['areas'][area]['build']
                inputs = build.get('merged_from') or [build['leaf']]
                baseline = PACKS / (TAG + '-baseline-' + area)
                merge.merge([str(ROOT / p) for p in inputs], area, baseline, False)
                preserved = baseline / area
            _, old = v.validate_v2_pack(preserved)
            assert payload(preserved) == before, f'{area}: active pack diverges from baseline'
            specs.append(str(preserved))
        specs.append(str(final / area) + '::' + ref)
        destination = PACKS / (TAG + '-merged-' + area)
        merge.merge(specs, area, destination, False)
        selected.append(destination)
        after = payload(destination / area)
        for name, digest in (before or {}).items():
            if name != v.REGISTRY_NAME:
                assert after[name] == digest, f'sibling changed: {area}/{name}'
        baselines[area]['output_payload'] = after
    complete = PACKS / (TAG + '-complete')
    combine.combine(selected, complete, False)
    v.write_json(BATCH / 'baseline.json', baselines)

    checks = []
    for ref, (area, spatial, radius) in JOBS.items():
        pack = final / area
        _, rs = v.validate_v2_pack(pack)
        r = next(r for r in rs if r['resref'] == ref)
        original = next(r0 for r0 in resources if r0['resref'] == ref)
        assert v.resource_binary_v2(r, 3) == v.resource_binary_v2(original, 3)
        for frame in r['frames']:
            rgba = pixels(pack, frame)
            assert not rgba[rgba[..., 3] == 0, :3].any()
            assert np.all(rgba[..., :3] <= rgba[..., 3, None])
        if ref in ('EYESRED1', 'WTRBODY1'):
            assert r['playback_mode'] == 'Native'
            assert r['cycles'][0]['native_frame_indices'] == list(range(20))
            assert all(np.array_equal(pixels(pack, r['frames'][i]), pixels(pack, r['frames'][i+1]))
                       for i in range(0, 20, 2))
        if ref == 'AM4000Z':
            assert [c['native_frame_indices'] for c in r['cycles']] == [list(range(10, 22)), list(range(10))]
        if ref == 'BUBBLEA':
            assert len(r['cycles']) == 3
            for cycle in r['cycles']:
                assert len(cycle['native_frame_indices']) == 49
                assert len(cycle['timeline_frame_indices']) == 98
                assert cycle['native_frame_indices'].count(0) == 30
                for slot, native in enumerate(cycle['native_frame_indices']):
                    assert cycle['timeline_frame_indices'][2*slot] == native
                    if native == cycle['native_frame_indices'][(slot+1) % 49]:
                        assert cycle['timeline_frame_indices'][2*slot+1] == native
        wrapper = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-{TAG}'
        wrapper.mkdir(parents=True, exist_ok=False)
        record = dict(schema='bg2-upscale-animation-visual-treatment-v1', status='completed',
                      created_utc=v.utc_now(), resrefs=[ref], resref=ref,
                      source_run=rel(SPATIAL), source_run_manifest_sha256=v.sha256_file(SPATIAL/'manifest.json'),
                      temporal_pack=rel(SOURCE), output_split_root=rel(final),
                      output_manifest_sha256=v.sha256_file(final/'manifest.json'),
                      source_pack=rel(pack), source_pack_manifest_sha256=v.sha256_file(pack/'manifest.json'),
                      recipe=dict(spatial=spatial, scale=4, inner_feather_x4=radius,
                                  rgb='premultiply once', playback=r['playback_mode'],
                                  occlusion='unbound; installed native occlusion bridge, no static WED clipping'),
                      qa_status='pending-ingame', release_status='not-selected')
        v.write_json(wrapper/'manifest.json', record)
        checks.append(dict(resref=ref, area=area, frames=r['frame_count'], playback=r['playback_mode'],
                           cycles=r['cycles'], production=rel(wrapper/'manifest.json')))
    ini = (GAME/'InfinityEngine-Enhancer.ini').read_text()
    assert 'EnableNativeOcclusionBridge = true' in ini
    dll = GAME/'InfinityEngine-Enhancer.dll'
    assert b'Native occlusion phase1 bridge' in dll.read_bytes()
    v.write_json(BATCH/'checks.json', dict(status='completed', resources=checks,
                 native_geometry_and_cycles_preserved=True, siblings_preserved=True,
                 occlusion='native bridge enabled; WED unchanged; no baked occurrence mask',
                 dll_sha256=v.sha256_file(dll), qa_status='pending-ingame'))
    v.write_json(BATCH/'manifest.json', dict(schema='bg2-upscale-animation-batch-production-v1',
                 status='completed', created_utc=v.utc_now(), resrefs=list(JOBS),
                 complete_pack=rel(complete), asset_pack=rel(final),
                 recipe_script=rel(Path(__file__)), qa_status='pending-ingame', release_status='not-selected'))
    preview(final)
    print(json.dumps(dict(status='completed', complete_pack=rel(complete), checks=rel(BATCH/'checks.json'))))


if __name__ == '__main__':
    main()
