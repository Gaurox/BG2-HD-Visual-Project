"""Check accepted authority and dependency closure after deleting unused trials."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

OUT = ROOT / 'effects/batches/lot54-accepted-cleanup-20261013-v1'
FINAL = OUT / 'verification-after-cleanup.json'
if FINAL.exists():
    raise RuntimeError('Final verification already recorded')
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
acceptance = load(OUT / 'acceptance.json')
plan = load(OUT / 'purge-plan.json')
receipt = load(OUT / 'purge-receipt.json')
assert receipt['root_count'] == plan['target_count'] == 51
for item in plan['targets']:
    assert not (ROOT / item['path']).exists()
    for file in item['files']:
        archived = OUT / 'discarded-trial-metadata' / item['path'] / file['path']
        if archived.is_file():
            assert workflow.sha256_file(archived) == file['sha256']
for relative in plan['protected']:
    assert (ROOT / relative).is_dir(), relative
checked = []
for asset in acceptance['accepted']:
    result = workflow.check_workspace(ROOT, asset['resref'])
    assert result['ok'], result['errors']
    selected = load(ROOT / asset['selection'])
    assert selected['selected_run'] == asset['selected_run']
    checked.append({'resref': asset['resref'], 'ok': True,
                    'selected_run': asset['selected_run'], 'qa_evidence': asset['qa_evidence']})
original = {r['asset_key']: r for r in workflow.read_csv(OUT / 'processing-before.csv', workflow.PROCESSING_FIELDS)}
current = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
scope = {r['resref'] for r in checked}
for row in current:
    old = original[row['asset_key']]
    assert row['release_state'] == old['release_state']
    assert row['release_candidate'] == old['release_candidate']
    if row['asset_key'].rsplit(':', 1)[-1] not in scope:
        assert row == old
review_root = ROOT / 'effects/batches/effects-lot10-seedvr7b-compare-20261013-v1'
review = load(review_root / 'review-artifacts.json')
for relative, digest in review['artifact_sha256'].items():
    assert workflow.sha256_file(review_root / relative) == digest
installation = load(ROOT / 'effects/installations/lot54-accepted-3b-nearest-20261013-v1/result.json')
game = get_path('bg2ee_game_root', required=True)
assert workflow.sha256_file(game / 'iee-assets/effects/manifest.json') == installation['manifest_sha256']
assert all(workflow.sha256_file(game / n) == digest for n, digest in installation['preserved_sha256'].items())
FINAL.write_bytes(workflow.json_bytes({
    'schema': 'bg2-effects-acceptance-cleanup-verification-v1', 'status': 'passed',
    'checked_count': len(checked), 'checks': checked, 'deleted_roots': receipt['root_count'],
    'deleted_files': receipt['file_count'], 'logical_bytes': receipt['logical_bytes'],
    'all_protected_roots_present': True, 'final_comparison_artifacts_unchanged': True,
    'unrelated_processing_rows_unchanged': True, 'release_fields_unchanged': True,
    'installed_3b_manifest_matches': True, 'nearest_renderer_and_character_profile_preserved': True}))
print('54 asset checks passed; retained references intact; scoped deletion verified', flush=True)
