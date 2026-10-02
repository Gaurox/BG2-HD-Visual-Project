"""Freeze the human/half-orc selection from the existing read-only dedup plan."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = ROOT / 'sprite/.work/q3m-human-half-orc-x2-20261002-v1'
pointer = json.loads((ROOT / 'sprite/index/palette-work-plan.json').read_text())
db = sqlite3.connect((ROOT / pointer['path']).as_uri() + '?mode=ro', uri=True)
db.execute('PRAGMA query_only=ON')
meta = {k: json.loads(v) for k, v in db.execute('SELECT * FROM metadata')}
profile = meta['profile']
with (ROOT / 'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig', newline='') as stream:
    inventory = list(csv.DictReader(stream))
humans = [r for r in inventory if r['engine_section'] == 'character' and r['symbol_race'] == 'HUMAN']
half_orcs = [r for r in inventory if r['engine_section'] == 'character' and r['symbol_race'] == 'HALFORC']
rows = sorted(humans + half_orcs, key=lambda r: int(r['animation_id'], 16))
models = {a: m for m, a in db.execute('SELECT model_id,animation_id FROM models')}
assert len(humans) == 18 and len(half_orcs) == 8
assert all(r['animation_id'] in models and r['false_color'] == '1' for r in rows)
by_symbol = {r['ids_symbol']: r for r in humans}
resource_sets = {}
for row in rows:
    resource_sets[row['animation_id']] = {r[0] for r in db.execute(
        'SELECT resource_id FROM model_resources WHERE model_id=?', (models[row['animation_id']],))}
aliases = []
for row in rows:
    symbol = row['ids_symbol']
    counterpart = None
    if row['symbol_race'] == 'HALFORC':
        counterpart = by_symbol[symbol.replace('HALFORC', 'HUMAN')]
    elif row['symbol_variant'] == 'LOW':
        counterpart = by_symbol[symbol.removesuffix('_LOW')]
    if counterpart:
        assert resource_sets[row['animation_id']] == resource_sets[counterpart['animation_id']]
        for field in ('runtime_profile', 'false_color', 'resref', 'resref_armor_base',
                      'resref_armor_specific', 'height_code', 'height_code_helmet', 'height_code_shield'):
            assert row[field] == counterpart[field], (symbol, field)
        aliases.append(dict(animation=row['animation_id'], same_world_resources_as=counterpart['animation_id']))
ids = [r['animation_id'] for r in rows]
mask = sum(1 << models[a] for a in ids)
female_seed_mask = 1 << models['0x6110']
namespace = profile['namespace_by_scale']['2']
cache = ROOT / 'sprite/.work/palette-q3m-shared/x2' / namespace
cached = {e.name[:-4] for e in os.scandir(cache / 'work/encoded') if e.name.endswith('.npz')}
assert not WORK.exists(), 'Use a new snapshot directory instead of overwriting this selection.'
WORK.mkdir(parents=True)
counts = Counter()
per_model = {a: Counter() for a in ids}
work_list = WORK / 'work-list.csv'
with work_list.open('w', encoding='utf-8', newline='') as stream:
    out = csv.writer(stream, lineterminator='\n')
    out.writerow(['work_id', 'work_key', 'input_id', 'width', 'height', 'needs_model',
                  'action', 'consumers', 'shared_within_selection'])
    for wid, raw_key, iid, bits, width, height, needs, supported in db.execute('''
        SELECT w.work_id,w.work_key,w.input_id,w.consumer_models_le_bitset,
               i.width,i.height,i.needs_model,i.current_q3m_processable
        FROM work_items w JOIN inputs i USING(input_id) ORDER BY w.work_id'''):
        bits = int.from_bytes(bits, 'little')
        selected = bits & mask
        if not selected:
            continue
        assert supported, ('Unsupported geometry', wid)
        key = raw_key.hex()
        action = ('cached' if key in cached else 'reuse_verified_female_seed' if bits & female_seed_mask
                  else 'new_gpu' if needs else 'new_special')
        consumers = [a for a in ids if bits & (1 << models[a])]
        out.writerow([wid, key, iid, width, height, needs, action, '|'.join(consumers), len(consumers) > 1])
        counts['unique_work'] += 1
        counts[action] += 1
        counts['shared_between_selected_models'] += len(consumers) > 1
        counts['sum_model_unique_work'] += len(consumers)
        for a in consumers:
            per_model[a]['unique_work'] += 1
            per_model[a][action] += 1
counts['cross_model_repeat_work_avoided'] = counts['sum_model_unique_work'] - counts['unique_work']
resources = set().union(*resource_sets.values())
statistics = {a: json.loads(db.execute('SELECT statistics_json FROM model_statistics WHERE model_id=?',
              (models[a],)).fetchone()[0]) for a in ids}
excluded = [dict(animation_id=r['animation_id'], symbol=r['ids_symbol'], section=r['engine_section'],
                 reason='outside existing Character profile') for r in inventory
            if r['symbol_race'] == 'HUMAN' and r['engine_section'] != 'character']
report = dict(schema='bg2-human-half-orc-q3m-selection-v1', status='planned-not-produced',
              scale=2, method='Q3m', k=6, source_plan=dict(path=pointer['path'], sha256=pointer['sha256']),
              namespace=namespace, cache=cache.relative_to(ROOT).as_posix(),
              animations=[dict(animation_id=r['animation_id'], symbol=r['ids_symbol'],
                               resref=r['resref'], paperdoll=r['resref_paperdoll'],
                               stats=statistics[r['animation_id']], cached_state=dict(per_model[r['animation_id']]))
                          for r in rows], exact_world_aliases=aliases, resources=len(resources),
              counts=dict(counts), logical_frames=sum(s['logical_frames'] for s in statistics.values()),
              work_list=dict(path=work_list.relative_to(ROOT).as_posix(),
                             sha256=hashlib.sha256(work_list.read_bytes()).hexdigest()),
              frame_correspondence='existing SQLite frame_map; filter by selected animation IDs',
              excluded_legacy_humans=excluded, inventory='separate UI pipeline, excluded')
(HERE / 'selection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
db.close()
print(json.dumps(dict(animations=ids, aliases=len(aliases), resources=len(resources),
                     logical_frames=report['logical_frames'], counts=dict(counts)), indent=2))
