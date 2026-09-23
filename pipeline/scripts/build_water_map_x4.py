"""Standard spatial x4 water chain for one map, driven by plan_water_map.py.

    python pipeline/scripts/build_water_map_x4.py --run <run> --stage all
    python pipeline/scripts/build_water_map_x4.py --run <run> --stage verify-installed

Stages (each calls the existing, unchanged producer; outputs are immutable):
  overlays          build_liquid_periodic_x4_trial.py prepare/generate/build -> <run>/overlays
                    (generate needs ComfyUI for seedvr families; bilinear needs nothing)
  select            <run>/selection.json: one build per group (read by the 30 fps producer)
  bases             build_liquid_base_x4_trial.py --run -> <run>/bases (alpha/RGB repairs)
  snapshot          assemble_liquid_family_x4_trial.py snapshot -> <run>/live-before.json
  assemble          -> <run>/override-candidate (WED alias repoint + overlays + base pages)
  all               overlays -> select -> bases -> snapshot -> assemble
  verify-installed  after Install-AreaOverrideAssets.ps1
Installation and receipts stay separate (WATER_MAP_RUNBOOK.md).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

from workspace_paths import ROOT, get_path

SCRIPTS = ROOT / 'pipeline/scripts'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def run(*args):
    command = [sys.executable, '-B', *map(str, args)]
    print('> ' + ' '.join(map(str, args)), flush=True)
    subprocess.run(command, check=True, cwd=ROOT)


def overlays(ctx):
    for stage in ('prepare', 'generate', 'build'):
        run(SCRIPTS / 'build_liquid_periodic_x4_trial.py', '--vanilla-root', ctx['vanilla'],
            '--output', ctx['run'] / 'overlays', '--plan', ctx['run'] / 'overlays-plan.json', '--stage', stage,
            *(['--resume'] if stage == 'generate' else []))


def select(ctx):
    path = ctx['run'] / 'selection.json'
    if path.exists():
        raise SystemExit('selection.json already written')
    groups = []
    for group in read(ctx['run'] / 'overlays-plan.json')['groups']:
        build = ctx['run'] / 'overlays/groups' / group['id'] / 'build.json'
        if not build.is_file():
            raise SystemExit(f"{group['id']}: overlay build missing")
        groups.append({'id': group['id'], 'method': group['method'],
                       'build_manifest': build.relative_to(ROOT).as_posix()})
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump({'schema': 'bg2-liquid-overlays-selected-v1', 'status': 'candidate-ready',
                   'groups': groups}, stream, indent=2)
        stream.write('\n')
    print(f'Selected {len(groups)} group builds', flush=True)


def bases(ctx):
    run(SCRIPTS / 'build_liquid_base_x4_trial.py', '--vanilla-root', ctx['vanilla'], '--game-root', ctx['game'],
        '--plan', ctx['run'] / 'request.json', '--output', ctx['run'] / 'bases', '--run')


def assembler(ctx, stage, *extra):
    run(SCRIPTS / 'assemble_liquid_family_x4_trial.py', '--run', ctx['run'], '--game-root', ctx['game'],
        '--vanilla-root', ctx['vanilla'], '--stage', stage, *extra)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--run', type=Path, required=True, help='run folder written by plan_water_map.py')
    parser.add_argument('--stage', required=True, choices=['overlays', 'select', 'bases', 'snapshot', 'assemble',
                                                           'all', 'verify-installed'])
    args = parser.parse_args()
    folder = args.run.resolve()
    folder.relative_to(ROOT / 'maps')
    report = read(folder / 'plan-report.json')
    if report['stops']:
        raise SystemExit('STOP in plan: ' + ' | '.join(report['stops']))
    ctx = {'run': folder, 'game': get_path('bg2ee_game_root', required=True),
           'vanilla': read(folder / 'request.json')['source_vanilla']}
    extra = ('--bases-root', folder / 'bases', '--overlays-root', folder / 'overlays')
    steps = {'overlays': [overlays], 'select': [select], 'bases': [bases],
             'snapshot': [lambda c: assembler(c, 'snapshot')],
             'assemble': [lambda c: assembler(c, 'assemble', *extra)],
             'verify-installed': [lambda c: assembler(c, 'verify-installed')]}
    steps['all'] = steps['overlays'] + steps['select'] + steps['bases'] + steps['snapshot'] + steps['assemble']
    for step in steps[args.stage]:
        step(ctx)


if __name__ == '__main__':
    main()
