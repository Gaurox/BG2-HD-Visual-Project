"""Produce the frozen halfling selection through the shared Q3m producer."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import palette_playable as playable
from palette_work_plan import ResultCache, write_json

if (HERE / 'production.json').exists():
    raise SystemExit('Completed run: preserve its report and use a new version for another production.')

selection = json.loads((HERE / 'selection.json').read_text())
work_list = ROOT / selection['work_list']['path']
assert hashlib.sha256(work_list.read_bytes()).hexdigest() == selection['work_list']['sha256']
ids = [r['animation_id'] for r in selection['animations']]
assert (ROOT / selection['source_plan']['path']).is_file(), 'Existing source registry required.'
plan = playable.active_plan()
try:
    assert plan.descriptor['sha256'] == selection['source_plan']['sha256']
    cache = ResultCache(plan, 2)
    assert cache.namespace == selection['namespace']
    with cache.exclusive():
        print(json.dumps(dict(phase='halfling-selection', animations=ids,
                              expected=selection['counts'])), flush=True)
        counts = playable.produce(plan, cache, ids)
        assert counts['selected_unique_work'] == selection['counts']['unique_work']
        assert counts.get('new_unique_results', 0) <= selection['counts'].get('new_gpu', 0)
        assert counts.get('special_unique_results', 0) <= selection['counts'].get('new_special', 0)
        result = dict(status='encoded-not-native-or-ingame-verified',
                      source_plan_sha256=plan.descriptor['sha256'], counts=counts)
        write_json(cache.root / 'last-run.json', result)
        covered = set(selection['playable_coverage_before']['previously_produced_ids']) | set(ids)
        assert covered == set(plan.models)
        report = dict(schema='bg2-halfling-q3m-production-v1', animations=ids,
                      scale=2, method='Q3m', k=6, namespace=cache.namespace,
                      selection=(HERE / 'selection.json').relative_to(ROOT).as_posix(),
                      production=result,
                      playable_coverage_after=dict(total_models=len(plan.models), produced_models=len(covered),
                          remaining_animation_ids=[], evidence='this production plus the three pinned-compatible previous reports',
                          status='encoded production only; native assembly, QA, installation and release separate'))
        write_json(HERE / 'production.json', report)
        print(json.dumps(report), flush=True)
finally:
    plan.close()
