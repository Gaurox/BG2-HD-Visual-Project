"""UI work queue. Source/production/QA/installation/release remain independent."""
import argparse
import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TRACKER = ROOT / 'interface/index/work-tracking.json'


def read():
    return json.loads(TRACKER.read_text(encoding='utf-8'))


def summary(data):
    rows = data['resources']
    return dict(schema='bg2-ui-progress-v1', authority='interface/index/work-tracking.json',
                updated_on=data['updated_on'], unit='logical native resref; all frames for complete production',
                total=len(rows), produced=sum(r['production']['state'] in ('complete-existing-x4', 'complete-selected-x4') for r in rows),
                partial_production=sum(r['production']['state'] == 'partial-existing-x4' for r in rows),
                qa_observed_resources=sum(r['qa']['state'] == 'accepted-observed-menu' for r in rows),
                qa_complete=sum(r['qa']['state'] == 'accepted-complete' for r in rows),
                qa_observed_normal=sum(r['qa']['state'] == 'accepted-observed-normal' for r in rows),
                release_confirmed=sum(r['release']['state'] == 'confirmed-current-scope' for r in rows),
                release_unreconciled=sum(r['release']['state'] == 'not-reconciled' for r in rows),
                next_actions=dict(collections.Counter(r['next_action'] for r in rows)),
                limits=data['limits'])


def export(data):
    (HERE / 'progress.json').write_text(json.dumps(summary(data), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    fields = ['resref', 'kind', 'category', 'source', 'production', 'qa', 'installation', 'release', 'next_action']
    with (HERE / 'resources.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in data['resources']:
            writer.writerow({k: r[k]['state'] if isinstance(r[k], dict) else r[k] for k in fields})


def validate(data):
    names = [r['resref'] for r in data['resources']]
    assert len(names) == len(set(names)), 'Duplicate resrefs'
    inventory = json.loads((ROOT / data['selection_inventory']).read_text(encoding='utf-8'))
    expected = {r['resref'] for r in inventory['resources'] if r['status'].startswith('keep')}
    assert set(names) == expected, 'Active queue differs from selection'
    for row in data['resources']:
        for stage in ('source', 'production', 'qa', 'installation', 'release'):
            assert row[stage]['state']
            for evidence in row[stage].get('evidence', []):
                assert (ROOT / evidence).is_file(), f'Missing evidence: {evidence}'
    excluded = list(csv.DictReader((HERE / 'out-of-scope.csv').open(encoding='utf-8-sig')))
    assert not set(names) & {r['resref'] for r in excluded}, 'Active/excluded overlap'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'queue', 'show', 'export', 'check'])
    parser.add_argument('resref', nargs='?')
    parser.add_argument('--limit', type=int, default=20)
    args = parser.parse_args()
    data = read()
    if args.command == 'status':
        print(json.dumps(summary(data), ensure_ascii=False, indent=2))
    elif args.command == 'queue':
        for r in data['resources'][:args.limit]:
            print(f"{r['resref']:10} {r['production']['state']:24} {r['next_action']}")
    elif args.command == 'show':
        print(json.dumps(next(r for r in data['resources'] if r['resref'] == (args.resref or '').upper()), ensure_ascii=False, indent=2))
    else:
        validate(data)
        if args.command == 'export':
            export(data)
        print('OK')


if __name__ == '__main__':
    main()
