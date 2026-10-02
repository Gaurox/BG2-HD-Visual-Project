"""Produce the frozen human selection through the existing Q3m producer.

Restrict historical seed adoption to missing keys/resources. The normal producer
still validates every cache hit and processes each missing key once.
"""
import csv
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter

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
with work_list.open(encoding='utf-8', newline='') as stream:
    seed_ids = {int(r['work_id']) for r in csv.DictReader(stream)
                if r['action'] == 'reuse_verified_female_seed'}
plan = playable.active_plan()
try:
    assert plan.descriptor['sha256'] == selection['source_plan']['sha256']
    cache = ResultCache(plan, 2)
    assert cache.namespace == selection['namespace']
    with cache.exclusive():
        print(json.dumps(dict(phase='human-selection', animations=ids,
                              expected=selection['counts'])), flush=True)
        seeded = Counter()
        if seed_ids:
            placeholders = ','.join('?' for _ in seed_ids)
            refs = {r[0] for r in plan.db.execute(f'''SELECT DISTINCT r.resref FROM frames f
                    JOIN resources r USING(resource_id) WHERE f.work_id IN ({placeholders})''',
                    sorted(seed_ids))}
            for record in plan.descriptor.get('trusted_seed_runs', []):
                seeded.update(playable.seed_verified_run(plan, cache, record,
                                                       resrefs=refs, work_ids=seed_ids))
        print(json.dumps(dict(phase='unique-human-production', seeded=dict(seeded))), flush=True)
        counts = playable.produce(plan, cache, ids)
        assert counts['selected_unique_work'] == selection['counts']['unique_work']
        assert counts.get('new_unique_results', 0) <= selection['counts'].get('new_gpu', 0)
        result = dict(status='encoded-not-native-or-ingame-verified',
                      source_plan_sha256=plan.descriptor['sha256'], seeded=dict(seeded), counts=counts)
        write_json(cache.root / 'last-run.json', result)
        report = dict(schema='bg2-human-half-orc-q3m-production-v1', animations=ids,
                      scale=2, method='Q3m', k=6, namespace=cache.namespace,
                      selection='docs/measurements/human-half-orc-q3m-x2-20261002-v1/selection.json',
                      production=result)
        write_json(HERE / 'production.json', report)
        print(json.dumps(report), flush=True)
finally:
    plan.close()
