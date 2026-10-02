"""Freeze dwarf/gnome work and exact aliases from the existing read-only plan."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from collections import Counter

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = ROOT / 'sprite/.work/q3m-dwarf-gnome-x2-20261002-v1'
pointer = json.loads((ROOT / 'sprite/index/palette-work-plan.json').read_text())
assert (ROOT / pointer['path']).is_file(), 'Existing source registry required.'
db = sqlite3.connect((ROOT / pointer['path']).as_uri() + '?mode=ro', uri=True)
db.execute('PRAGMA query_only=ON')
meta = {k: json.loads(v) for k, v in db.execute('SELECT * FROM metadata')}
with (ROOT / 'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig', newline='') as stream:
    inventory = list(csv.DictReader(stream))
rows = sorted((r for r in inventory if r['engine_section'] == 'character'
               and r['symbol_race'] in ('DWARF', 'GNOME')), key=lambda r: int(r['animation_id'], 16))
assert Counter(r['symbol_race'] for r in rows) == {'DWARF': 16, 'GNOME': 8}
models = {a: m for m, a in db.execute('SELECT model_id,animation_id FROM models')}
assert all(r['animation_id'] in models and r['false_color'] == '1' for r in rows)
ids = [r['animation_id'] for r in rows]
character_rows = {r['animation_id']: r for r in inventory if r['animation_id'] in models}
resource_sets = {a: frozenset(r[0] for r in db.execute(
    'SELECT resource_id FROM model_resources WHERE model_id=?', (m,))) for a, m in models.items()}
runtime_fields = ('runtime_profile', 'false_color', 'resref', 'resref_armor_base',
                  'resref_armor_specific', 'height_code', 'height_code_helmet', 'height_code_shield')
aliases = []
for row in rows:
    a = row['animation_id']
    equivalents = [other for other in sorted(models) if other != a and resource_sets[a] == resource_sets[other]
                  and all(row[f] == character_rows[other][f] for f in runtime_fields)]
    if equivalents:
        aliases.append(dict(animation=a, same_world_resources_and_profile_as=equivalents))
groups = {}
for row in rows:
    signature = (resource_sets[row['animation_id']], tuple(row[f] for f in runtime_fields))
    groups.setdefault(signature, []).append(row['animation_id'])
previous = json.loads((ROOT / 'docs/measurements/human-half-orc-q3m-x2-20261002-v1/production.json').read_text())
assert previous['production']['status'] == 'encoded-not-native-or-ingame-verified'
mask = sum(1 << models[a] for a in ids)
previous_mask = sum(1 << models[a] for a in previous['animations'])
namespace = meta['profile']['namespace_by_scale']['2']
cache = ROOT / 'sprite/.work/palette-q3m-shared/x2' / namespace
cached = {e.name[:-4] for e in os.scandir(cache / 'work/encoded') if e.name.endswith('.npz')}
assert not WORK.exists() and not (HERE / 'selection.json').exists(), 'Use a new version for another snapshot.'
WORK.mkdir(parents=True)
counts = Counter()
per_model = {a: Counter() for a in ids}
work_list = WORK / 'work-list.csv'
with work_list.open('w', encoding='utf-8', newline='') as stream:
    out = csv.writer(stream, lineterminator='\n')
    out.writerow(['work_id', 'work_key', 'input_id', 'width', 'height', 'needs_model',
                  'action', 'consumers', 'shared_within_selection', 'shared_with_previous_humans'])
    for wid, raw_key, iid, bits, width, height, needs, supported in db.execute('''
        SELECT w.work_id,w.work_key,w.input_id,w.consumer_models_le_bitset,
               i.width,i.height,i.needs_model,i.current_q3m_processable
        FROM work_items w JOIN inputs i USING(input_id) ORDER BY w.work_id'''):
        bits = int.from_bytes(bits, 'little')
        if not bits & mask:
            continue
        assert supported, ('Unsupported geometry', wid)
        key = raw_key.hex()
        action = 'cached' if key in cached else 'new_gpu' if needs else 'new_special'
        previous_shared = bool(bits & previous_mask)
        assert not previous_shared or action == 'cached', ('Previous human result missing', wid)
        consumers = [a for a in ids if bits & (1 << models[a])]
        out.writerow([wid, key, iid, width, height, needs, action, '|'.join(consumers),
                      len(consumers) > 1, previous_shared])
        counts['unique_work'] += 1
        counts[action] += 1
        counts['shared_between_selected_models'] += len(consumers) > 1
        counts['shared_with_previous_humans'] += previous_shared
        counts['sum_model_unique_work'] += len(consumers)
        for a in consumers:
            per_model[a]['unique_work'] += 1
            per_model[a][action] += 1
            per_model[a]['shared_with_previous_humans'] += previous_shared
counts['cross_model_repeat_work_avoided'] = counts['sum_model_unique_work'] - counts['unique_work']
resources = set().union(*(resource_sets[a] for a in ids))
statistics = {a: json.loads(db.execute('SELECT statistics_json FROM model_statistics WHERE model_id=?',
              (models[a],)).fetchone()[0]) for a in ids}
excluded = [dict(animation_id=r['animation_id'], symbol=r['ids_symbol'], section=r['engine_section'],
                 reason='outside existing Character profile') for r in inventory
            if r['symbol_race'] in ('DWARF', 'GNOME') and r['engine_section'] != 'character']
report = dict(schema='bg2-dwarf-gnome-q3m-selection-v1', status='planned-not-produced',
              scale=2, method='Q3m', k=6, source_plan=dict(path=pointer['path'], sha256=pointer['sha256']),
              namespace=namespace, cache=cache.relative_to(ROOT).as_posix(),
              animations=[dict(animation_id=r['animation_id'], symbol=r['ids_symbol'],
                               resref=r['resref'], paperdoll=r['resref_paperdoll'],
                               stats=statistics[r['animation_id']], cached_state=dict(per_model[r['animation_id']]))
                          for r in rows], exact_world_aliases=aliases,
              selected_world_resource_profile_groups=list(groups.values()), resources=len(resources),
              counts=dict(counts), logical_frames=sum(s['logical_frames'] for s in statistics.values()),
              previous_production='docs/measurements/human-half-orc-q3m-x2-20261002-v1/production.json',
              work_list=dict(path=work_list.relative_to(ROOT).as_posix(),
                             sha256=hashlib.sha256(work_list.read_bytes()).hexdigest()),
              frame_correspondence='existing SQLite frame_map; filter by selected animation IDs',
              excluded_legacy_sprites=excluded, inventory='separate UI pipeline, excluded')
(HERE / 'selection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
db.close()
print(json.dumps(dict(animations=ids, world_resource_profile_groups=list(groups.values()),
                     resources=len(resources), logical_frames=report['logical_frames'],
                     counts=dict(counts), excluded=excluded), indent=2))
