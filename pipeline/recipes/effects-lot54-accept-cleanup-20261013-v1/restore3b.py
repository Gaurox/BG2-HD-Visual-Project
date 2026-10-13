"""Install the accepted 3B pack, retaining the active nearest renderer and character profile."""
from pathlib import Path
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'pipeline/scripts'), str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import effect_workflow as workflow
import effect_authority as authority
import install_renderer_candidate as installer
from compose_effect_runtime_packs import validate_pack
from workspace_paths import get_path

OUT = ROOT / 'effects/installations/lot54-accepted-3b-nearest-20261013-v1'
OUT.mkdir(exist_ok=True)
FINAL = OUT / 'result.json'
if FINAL.exists():
    raise RuntimeError('Installed result already recorded; use a new version')
game = get_path('bg2ee_game_root', required=True)
installer.ensure_game_stopped(installer.running_game_processes)
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
batch = load(ROOT / 'effects/batches/lot54-seedvr3b-apollo30-20261013-v1/batch.json')
assert load(ROOT / 'effects/batches/lot54-accepted-cleanup-20261013-v1/acceptance.json')['accepted_count'] == 54
source_root = ROOT / 'effects/installations/lot54-seedvr3b-apollo30-gauss12-feather12-20261013-v1/candidate/iee-assets/effects'
source = validate_pack(source_root)
old = validate_pack(game / 'iee-assets/effects')
selected = {a['resref']: a for a in batch['assets']}
assert source.resource_count == old.resource_count == 64
for resource in source.resources:
    name = resource['resref']
    if name in selected:
        assert resource['source']['spatial_run'] == selected[name]['spatial_run']
        assert resource['source']['interpolation_run'] == selected[name]['treatment_run']
        assert resource['timeline']['target_fps'] == [30, 1]
    else:
        assert resource == next(r for r in old.resources if r['resref'] == name)
old_frames = {f['asset']: f for f in old.frames}
changed = []
for frame in source.frames:
    if frame['sha256'] != old_frames[frame['asset']]['sha256']:
        assert frame['resref'] in selected
        changed.append(frame['asset'])
assert len(changed) == 545
preserved_names = ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini',
    'override/fpDraw.glsl', 'override/fpSprite.glsl', 'override/fpSELECT.glsl',
    'iee-assets/creature-sprites/CreatureSprites-XN.catalog']
preserved = {n: workflow.sha256_file(game / n) for n in preserved_names}
nearest = load(ROOT / 'engine/InfinityEngine-Enhancer/installations/effects-nearest-20261013-v1/result.json')
assert preserved['InfinityEngine-Enhancer.dll'] == nearest['dll_sha256']
candidate = OUT / 'candidate'
candidate.mkdir(exist_ok=True)
pack_root = candidate / 'iee-assets/effects'
pack_root.mkdir(parents=True, exist_ok=True)
for file in source_root.iterdir():
    if file.is_file():
        destination = pack_root / file.name
        if not destination.exists():
            try:
                os.link(file, destination)
            except OSError:
                shutil.copy2(file, destination)
for name in ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini']:
    shutil.copy2(game / name, candidate / name)
(OUT / 'before.json').write_bytes(workflow.json_bytes({
    'preserved_sha256': preserved, 'old_effect_manifest_sha256': old.manifest_sha256,
    'new_effect_manifest_sha256': source.manifest_sha256, 'changed_backings': changed}))
result = installer.install_candidate(candidate, game_root=game, backup_root=OUT / 'backups')
installer.verify_transaction(result.receipt_path, game_root=game)
installed = validate_pack(game / 'iee-assets/effects')
assert installed.manifest_sha256 == source.manifest_sha256
assert all(workflow.sha256_file(game / n) == digest for n, digest in preserved.items())
receipt = result.receipt_path.relative_to(ROOT).as_posix()
with authority.guard(ROOT, write=True):
    rows = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
    for row in rows:
        name = row['asset_key'].rsplit(':', 1)[-1]
        if name in selected:
            selection = load(ROOT / f'effects/index/selections/{name}.json')
            assert selection['selected_run'] == selected[name]['treatment_run']
            row['spatial_run'] = selected[name]['spatial_run']
            row['spatial_state'] = 'verified'
            row['interpolation_run'] = selected[name]['treatment_run']
            row['interpolation_state'] = 'verified'
            row['installation_state'] = 'installed'
            row['installation_receipt'] = receipt
    authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(rows)})
FINAL.write_bytes(workflow.json_bytes({
    'schema': 'bg2-effects-accepted-3b-nearest-install-v1', 'status': 'installed-verified',
    'receipt': receipt, 'accepted_assets': sorted(selected), 'accepted_count': 54,
    'resource_count': 64, 'previous_other_resources_preserved': 10,
    'changed_backings': len(changed), 'manifest_sha256': installed.manifest_sha256,
    'registry_sha256': installed.manifest['registry_sha256'], 'preserved_sha256': preserved,
    'effect_filter': 'NEAREST', 'character_profile': 'NearestRGB-SilhouetteAlphaAA',
    'release_mutation': False}))
print('54 accepted 3B effects installed; 545 trial backings replaced; nearest and character AA preserved', flush=True)
