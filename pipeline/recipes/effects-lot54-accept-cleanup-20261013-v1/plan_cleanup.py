"""Plan scoped deletion of rejected trials; archive exact metadata before deletion."""
from pathlib import Path
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow

OUT = ROOT / 'effects/batches/lot54-accepted-cleanup-20261013-v1'
PLAN = OUT / 'purge-plan.json'
if PLAN.exists():
    raise RuntimeError('Purge plan already recorded')
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
accepted = load(OUT / 'acceptance.json')
installed = load(ROOT / 'effects/installations/lot54-accepted-3b-nearest-20261013-v1/result.json')
assert accepted['accepted_count'] == installed['accepted_count'] == 54
batch = load(ROOT / 'effects/batches/lot54-seedvr3b-apollo30-20261013-v1/batch.json')
trials = load(ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1/batch.json')
names = {a['resref'] for a in batch['assets']}
protected = set()
pending = []
for selection_file in (ROOT / 'effects/index/selections').glob('*.json'):
    selection = load(selection_file)
    if selection.get('mode') == 'x4':
        protected.add((ROOT / selection['runtime_pack']['manifest']['path']).parent.resolve())
        pending.append((selection['resref'], selection['contract']['source']['spatial_run']))
        pending.append((selection['resref'], selection['selected_run']))
for row in workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS):
    for field in ['spatial_run', 'interpolation_run']:
        if row[field]:
            pending.append((row['asset_key'].rsplit(':', 1)[-1], row[field]))
while pending:
    name, run_id = pending.pop()
    run = (ROOT / 'effects/ressources' / name / 'runs' / run_id).resolve()
    if run in protected:
        continue
    protected.add(run)
    descriptor = load(run / 'run.json')
    for parent in descriptor.get('provenance', {}).get('parents', []):
        if isinstance(parent, str):
            pending.append((name, parent))

targets = {}
for name in names:
    for run in (ROOT / 'effects/ressources' / name / 'runs').iterdir():
        descriptor = run / 'run.json'
        if descriptor.is_file():
            data = load(descriptor)
            if data.get('result', {}).get('status') == 'failed' and ('lot54' in run.name or 'lot10' in run.name):
                targets[run.resolve()] = 'failed trial; diagnostic metadata retained'
for asset in trials['assets']:
    for key in ['spatial_run', 'apollo_run', 'treatment_run']:
        targets[(ROOT / 'effects/ressources' / asset['resref'] / 'runs' / asset[key]).resolve()] = '7B model trial rejected in favor of accepted 3B'
    targets[(ROOT / asset['pack']).resolve()] = 'unused 7B unit pack; installed rollback bytes preserved separately'

records = []
for target, reason in sorted(targets.items()):
    relative = target.relative_to(ROOT).as_posix()
    assert target not in protected and target.is_dir(), relative
    assert relative.startswith('effects/ressources/') and '/source' not in relative
    files = []
    for folder, dirs, filenames in os.walk(target):
        parent = Path(folder)
        assert not parent.is_symlink() and not parent.is_junction() if hasattr(parent, 'is_junction') else not parent.is_symlink()
        for filename in sorted(filenames):
            path = parent / filename
            assert not path.is_symlink()
            stat = path.stat()
            entry = {'path': path.relative_to(target).as_posix(), 'bytes': stat.st_size,
                     'sha256': workflow.sha256_file(path), 'links': stat.st_nlink}
            files.append(entry)
            if path.suffix.lower() in {'.json', '.md', '.txt', '.log', '.csv', '.yaml', '.yml'}:
                dest = OUT / 'discarded-trial-metadata' / relative / entry['path']
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)
                assert workflow.sha256_file(dest) == entry['sha256']
    records.append({'path': relative, 'absolute_path': str(target), 'reason': reason,
                    'files': files, 'file_count': len(files), 'logical_bytes': sum(f['bytes'] for f in files)})

review = load(ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1/review-artifacts.json')
for relative, digest in review['artifact_sha256'].items():
    assert workflow.sha256_file(ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1' / relative) == digest
PLAN.write_bytes(workflow.json_bytes({
    'schema': 'bg2-effects-scoped-unused-trials-purge-v1', 'accepted_count': 54,
    'protected': sorted(p.relative_to(ROOT).as_posix() for p in protected),
    'targets': records, 'target_count': len(records),
    'file_count': sum(r['file_count'] for r in records),
    'logical_bytes': sum(r['logical_bytes'] for r in records),
    'preserved': ['native BAM sources', 'all selected 3B production and parent runs',
                  'installed resources', 'all installation backups and candidate packs',
                  'final 3B/7B comparison artifacts and exact discarded-trial metadata'],
    'limits': 'logical byte count is not measured free-space gain; hard-linked files may remain retained'}))
print('planned roots', len(records), 'logical bytes', sum(r['logical_bytes'] for r in records), flush=True)
