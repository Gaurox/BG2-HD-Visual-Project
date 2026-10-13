"""Record explicit user QA for the exact 54 3B unit packs; no release mutation."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow

BATCH = ROOT / 'effects/batches/lot54-seedvr3b-apollo30-20261013-v1'
OUT = ROOT / 'effects/batches/lot54-accepted-cleanup-20261013-v1'
OUT.mkdir(exist_ok=True)
FINAL = OUT / 'acceptance.json'
if FINAL.exists():
    raise RuntimeError('Acceptance already recorded; historical result must remain immutable')

load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
batch = load(BATCH / 'batch.json')
verification = load(BATCH / 'verification.json')
assert len(batch['assets']) == verification['checked'] == verification['passed'] == 54
assert not verification['failures']
before = OUT / 'processing-before.csv'
if not before.exists():
    before.write_bytes((ROOT / 'effects/index/processing.csv').read_bytes())
original = workflow.read_csv(before, workflow.PROCESSING_FIELDS)
selected = {a['resref'] for a in batch['assets']}
decision = ('je valide le parck des 54 effets en 3b. ils sont ok. '
            'SeedVR2 3B x4/LAB, Apollo 30 FPS, Gaussian sigma 1.2 px x4, '
            'fondu intérieur 12 px x4, RGB prémultiplié ; affichage effects nearest.')
accepted = []
for asset in batch['assets']:
    checked = next(r for r in verification['assets'] if r['resref'] == asset['resref'])
    assert workflow.sha256_file(ROOT / asset['pack'] / 'manifest.json') == checked['checked_inputs']['pack_manifest_sha256']
    result = workflow.accept_asset(
        ROOT, asset['resref'], pack_path=asset['pack'], decision=decision,
        decision_date='2026-10-13', write=True)
    accepted.append(result)
    print('accepted', asset['resref'], flush=True)

current = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
old_by_key = {r['asset_key']: r for r in original}
for row in current:
    old = old_by_key[row['asset_key']]
    if row['asset_key'].rsplit(':', 1)[-1] not in selected:
        assert row == old, row['asset_key']
    else:
        for field in ('installation_state', 'installation_receipt', 'release_state', 'release_candidate'):
            assert row[field] == old[field]
report = {
    'schema': 'bg2-effects-lot54-explicit-acceptance-v1',
    'status': 'accepted', 'date': '2026-10-13',
    'user_decision': 'oui c\'est ca. bon ok ca me va. je valide le parck des 54 effets en 3b. ils sont ok. supprime les test non utilisés et committe',
    'batch': BATCH.relative_to(ROOT).as_posix(),
    'batch_sha256': workflow.sha256_file(BATCH / 'batch.json'),
    'verification_sha256': workflow.sha256_file(BATCH / 'verification.json'),
    'accepted': accepted, 'accepted_count': len(accepted),
    'renderer_contract': 'effects NEAREST; creature NearestRGB-SilhouetteAlphaAA retained',
    'installation_is_separate': True, 'release_mutation': False,
    'known_runtime_exception': 'FDAWNX native fallback due logical 31x32 vs native 31x76 previously observed; not repaired or reclassified by this visual decision',
}
FINAL.write_bytes(workflow.json_bytes(report))
print('54 accepted; unrelated rows, installation and release preserved', flush=True)
