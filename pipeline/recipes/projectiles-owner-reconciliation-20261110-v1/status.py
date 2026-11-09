"""Read the current technical exceptions without replaying the old source queue."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent))
from reconcile import ROOT, load, sha

pointer = load(ROOT / 'projectiles/index/owner-reconciliation-current.json')
for field in ('summary', 'owners', 'exceptions'):
    ref = pointer[field]
    assert sha(ROOT / ref['path']) == ref['sha256'], field
print(json.dumps(dict(states=pointer['states'], actionable_families=pointer['actionable_families'],
                     exceptions=load(ROOT / pointer['exceptions']['path']),
                     new_manual_tests=pointer['new_manual_tests'], meaning=pointer['meaning']),
                 ensure_ascii=True, indent=2))
