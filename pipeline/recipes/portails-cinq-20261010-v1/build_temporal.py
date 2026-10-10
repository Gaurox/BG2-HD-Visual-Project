"""Apollo-8 production; SPDIMNDR linear cycles reuse the validated segmented path.

Cycles 0/2/3/4: no appended first pose; last native slot held for both 30fps phases.
Cycle 1 and all other assets: ordinary native closed loop. No shared pipeline edits.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as splitter
import build_blended_rgb_neutral_pack as neutral
from build_spatial import JOBS, BATCH

ORIGINAL_PLAN = v2.build_plan
ORIGINAL_INTERPOLATE = v2.interpolate_cycle


def adapted_plan(*args, **kwargs):
    plan = ORIGINAL_PLAN(*args, **kwargs)
    if not any(t['resref'] == 'SPDIMNDR' for t in plan['targets']):
        return plan
    base = Path(plan['base_pack'])
    _, resources, _ = v2.load_base_pack(base)
    resource = next(r for r in resources if r['resref'] == 'SPDIMNDR')
    frames = sorted(resource['frames'], key=lambda f: f['frame'])
    for target in plan['targets']:
        if target['resref'] != 'SPDIMNDR':
            continue
        next_frame = target['base_frame_count']
        added_bytes = 0
        for cycle in target['cycles']:
            lookup = cycle['native_frame_indices']
            linear = cycle['cycle'] in (0, 2, 3, 4)
            transitions = []
            intermediates = []
            timeline = []
            for slot, left in enumerate(lookup):
                timeline.append(left)
                if linear and slot == len(lookup) - 1:
                    timeline.append(left)
                    continue
                right = lookup[(slot + 1) % len(lookup)]
                assert left != right
                output_index = next_frame
                next_frame += 1
                width, height = frames[left]['physical_size_x4']
                added_bytes += width * height * 4
                intermediates.append(output_index)
                timeline.append(output_index)
                transitions.append({'segment': len(transitions), 'slot': slot,
                                    'left_native_frame': left, 'right_native_frame': right,
                                    'intermediate_frame_indices': [output_index]})
            cycle['intermediate_frame_indices'] = intermediates
            cycle['timeline_frame_indices'] = timeline
            if linear:
                cycle.update({'timing_strategy': 'preserve-segmented-holds',
                              'interpolation_input_frame_indices': lookup.copy(),
                              'interpolation_path_mode': 'linear-terminal-native-hold',
                              'phases_per_transition': 2,
                              'interpolation_segments': transitions,
                              'exact_hold_boundary_count': 1})
                assert timeline[-2:] == [lookup[-1], lookup[-1]]
                assert len(transitions) == len(lookup) - 1
                assert not any(s['left_native_frame'] == lookup[-1] and
                               s['right_native_frame'] == lookup[0] for s in transitions)
            assert timeline[::2] == lookup and len(timeline) == len(lookup) * 2
            assert cycle['duration_seconds'] == len(lookup) / 15
        target.update({'output_frame_count': next_frame,
                       'added_intermediate_frames': next_frame - target['base_frame_count'],
                       'added_raw_bytes': added_bytes})
    plan['linear_cycle_strategy'] = {'SPDIMNDR': [0, 2, 3, 4],
                                    'terminal_slot': 'two exact native-anchor phases',
                                    'stable_loop_cycle': 1}
    plan['topaz']['loop_strategy'] = 'SPDIMNDR mixed linear/closed cycles; other assets closed'
    plan['gates'] = [g for g in plan['gates'] if 'closed cycle' not in g]
    plan['gates'].append('linear Topaz input excludes the synthetic last-to-first transition')
    plan.pop('plan_sha256')
    plan['plan_sha256'] = v2.sha256_json(plan)
    return plan


def interpolate_progress(*args, **kwargs):
    context, cycle = args[2], args[3]
    print(f"APOLLO {context['resref']} cycle {cycle['cycle']} "
          f"{cycle.get('interpolation_path_mode', 'closed-loop')}", flush=True)
    result = ORIGINAL_INTERPOLATE(*args, **kwargs)
    print(f"APOLLO COMPLETED {context['resref']} cycle {cycle['cycle']}", flush=True)
    return result


def main():
    v2.build_plan = adapted_plan
    v2.interpolate_cycle = interpolate_progress
    batch = {'schema': 'bg2-upscale-animation-batch-production-v1',
             'status': 'working', 'created_utc': v2.utc_now(), 'resources': [],
             'qa_status': 'pending-user-preview', 'installed': False, 'release_status': 'not-selected'}
    for ref, method, radius in JOBS:
        spatial = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-{method}-spatial-20261010-v1'
        base = spatial / '03_runtime_pack'
        output = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-apo8-portails-20261010-v1'
        plan = adapted_plan(spatial, base, [ref], model='apo-8',
                            transparent_rgb_mode='nearest-opaque-dilate')
        v2.write_json(BATCH / f'{ref}-temporal-plan.json', plan)
        v2.build_run(spatial, base, output, [ref], plan['plan_sha256'],
                     v2.DEFAULT_TVAI_FFMPEG, v2.DEFAULT_TVAI_MODEL_DIR, 'apo-8',
                     v2.DEFAULT_DEVICE, 'ffmpeg', True,
                     transparent_rgb_mode='nearest-opaque-dilate')
        source_split = BATCH / 'artifacts' / f'{ref}-source-split'
        final_split = BATCH / 'artifacts' / f'{ref}-final-split'
        splitter.split(output / '03_runtime_pack', source_split,
                       ROOT / 'animations/index/occurrences.csv', source_split.exists())
        neutral.build(source_split, final_split, {ref}, final_split.exists(), 'premultiply', None, radius)
        wrapper = ROOT / f'animations/ressources/{ref}/runs/{ref.lower()}-portails-final-20261010-v1'
        wrapper.mkdir(exist_ok=True)
        record = {'schema': 'bg2-upscale-animation-visual-treatment-v1', 'status': 'completed',
                  'resref': ref, 'created_utc': v2.utc_now(),
                  'source_run': output.relative_to(ROOT).as_posix(),
                  'source_run_manifest_sha256': v2.sha256_file(output / 'manifest.json'),
                  'output_split_root': final_split.relative_to(ROOT).as_posix(),
                  'output_manifest_sha256': v2.sha256_file(final_split / 'manifest.json'),
                  'recipe': {'spatial': method, 'temporal': 'Apollo-8 15->30',
                             'inner_feather_x4': radius, 'rgb_policy': 'premultiply-once',
                             'linear_cycles': [0, 2, 3, 4] if ref == 'SPDIMNDR' else []},
                  'qa_status': 'pending-user-preview', 'installed': False,
                  'recipe_script': Path(__file__).relative_to(ROOT).as_posix()}
        v2.write_json(wrapper / 'manifest.json', record)
        batch['resources'].append({'resref': ref, 'spatial_run': spatial.relative_to(ROOT).as_posix(),
                                   'temporal_run': output.relative_to(ROOT).as_posix(),
                                   'final_run': wrapper.relative_to(ROOT).as_posix(),
                                   'final_split': final_split.relative_to(ROOT).as_posix(),
                                   'recipe': record['recipe']})
        v2.write_json(BATCH / 'manifest.json', batch)
        print('FINAL COMPLETED ' + ref, flush=True)
    batch['status'] = 'completed'
    v2.write_json(BATCH / 'manifest.json', batch)


if __name__ == '__main__':
    main()
