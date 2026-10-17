"""Record explicit lot26 QA against final SDF/facefill packs and installed routes."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

BATCH = ROOT / 'effects/batches/lot26-sdf-no-inset-20261017-v1'
FACE = ROOT / 'effects/batches/ohrfear-face-fill-20261017-v1'
INSTALL = ROOT / 'effects/installations/lot26-sdf-no-inset-20261017-v1'
FIX = ROOT / 'effects/installations/lot26-face-visibility-20261017-v1'
OUT = ROOT / 'effects/batches/lot26-accepted-20261017-v1'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
evidence = lambda p: workflow.file_evidence(ROOT, p)
sha = workflow.sha256_file
decision = 'ok les 09 et 26 sont visibles avec le décalage et le 12 est corrigé. tout est validé, mets à jour le suivi et committe.'


def save(name, value):
    path = OUT / name
    assert not path.exists(), 'Final evidence must remain immutable'
    path.write_bytes(workflow.json_bytes(value))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / 'acceptance.json').exists(), 'Final acceptance is immutable'
    assets = load(BATCH / 'batch.json')['assets']
    face = load(FACE / 'batch.json')['assets'][0]
    assets = [face if a['resref'] == 'OHRFEAR' else a for a in assets]
    assert len(assets) == 26
    game = get_path('bg2ee_game_root', required=True)
    manifest_path = game / 'iee-assets/effects/manifest.json'
    installed = load(manifest_path)
    assert sha(manifest_path) == load(FIX / 'installation.json')['manifest_sha256']
    assert installed['registry_version'] == 3 and installed['resource_count'] == 253
    assert sha(game / 'iee-assets/effects/EffectAnimations-X4.registry') == installed['registry_sha256']
    before_install = load(FIX / 'before.json')
    preserved = before_install['preserved']
    assert all(sha(game / name) == value['sha256'] for name, value in preserved.items())
    members = {r['resref']: r for r in installed['resources']}
    frames = {ref: [f for f in installed['frames'] if f['resref'] == ref] for ref in members}
    accepted_runtime = []
    for a in assets:
        ref = a['resref']
        batch = FACE if ref == 'OHRFEAR' else BATCH
        check = load(batch / 'checks' / f'{ref}.json')
        assert sha(ROOT / a['pack'] / 'manifest.json') == check['pack_manifest_sha256']
        stage = ROOT / 'effects/ressources' / ref / 'runs' / a['interpolation_run'] / '02-interpolation'
        m = load(stage / 'manifest.json')
        descriptor = stage.parent / 'run.json'
        assert load(descriptor)['result']['sealed']
        variants = [ref] + (['SPIPLARI', 'X26PLAA'] if ref == 'SPIPLAAI' else [])
        for runtime_ref in variants:
            member = members[runtime_ref]
            assert member['production_bam'] == ref and member['interpolation_run'] == a['interpolation_run']
            # Bind installed metadata to the selected final frames. The transaction
            # already hashed installed payloads; no global re-read of old resources.
            key = 'straight_raw_rgba_x4' if member['rgb_encoding'] == 'straight' else 'raw_rgba_x4'
            sources = {str(stage / f[key]).replace('\\', '/'): f for f in m['frames']}
            for f in frames[runtime_ref]:
                original = sources[str(ROOT / f['source']).replace('\\', '/')]
                assert f['sha256'] == original[key + '_sha256']
                assert f['physical_size_x4'] == original['physical_size_x4']
            accepted_runtime.append({'runtime_resref': runtime_ref, 'production_bam': ref,
                'interpolation_run': a['interpolation_run'], 'rgb_encoding': member['rgb_encoding'],
                'backings': len(frames[runtime_ref]), 'run': evidence(descriptor),
                'interpolation_manifest': evidence(stage / 'manifest.json'),
                'normal_or_alias_contract_accepted': True})
    # Bind exact tested offset controls and the two native mixed-alpha routes.
    controls = {}
    for name in ['Z26V09', 'Z26V26', 'Z26T12', 'ICINHIT', 'ICINTRAV']:
        rel = f'override/{name}.vvc'
        entry = next(c for c in installed['runtime_vvc_controllers'] if c['asset'] == rel)
        assert sha(game / rel) == entry['sha256']
        controls[name] = entry
    before_path = OUT / 'processing-before.csv'
    assert not before_path.exists()
    before_path.write_bytes((ROOT / 'effects/index/processing.csv').read_bytes())
    before = {r['asset_key']: r for r in workflow.read_csv(before_path, workflow.PROCESSING_FIELDS)}
    names = {a['resref'] for a in assets}
    accepted = []
    for a in assets:
        accepted.append(workflow.accept_asset(ROOT, a['resref'], pack_path=a['pack'],
            decision=decision, decision_date='2026-10-17', write=True))
        print('accepted', a['resref'], flush=True)
    proof = []
    for row in workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS):
        old = before[row['asset_key']]
        ref = row['asset_key'].rsplit(':', 1)[-1]
        if ref not in names:
            assert row == old, row['asset_key']
            continue
        assert row['qa_state'] == 'passed' and row['spatial_state'] == row['interpolation_state'] == 'verified'
        assert row['selected_run'] == row['interpolation_run']
        assert all(row[k] == old[k] for k in ('installation_state', 'installation_receipt', 'release_state', 'release_candidate'))
        selection = load(ROOT / f'effects/index/selections/{ref}.json')
        assert selection['selected_run'] == row['selected_run']
        assert selection['qa_evidence']['path'] == row['qa_evidence']
        assert sha(ROOT / row['qa_evidence']) == selection['qa_evidence']['sha256']
        proof.append({'resref': ref, 'passed': True,
                      'selection': evidence(ROOT / f'effects/index/selections/{ref}.json'),
                      'qa_evidence': evidence(ROOT / row['qa_evidence'])})
    assert len(proof) == 26 and len(accepted_runtime) == 28
    clua = load(INSTALL / 'clua.json')
    for r in clua:
        if r['ordinal'] in (9, 26):
            r['original_vvc'] = r['vvc']
            r['vvc'] = f'Z26V{r["ordinal"]:02d}'
            r['clua'] = f'C:Eval(\'CreateVisualEffectObject("{r["vvc"]}",Player1)\',0)'
            r['test_placement'] = 'X offset64, original images/alpha/blending/timing retained'
    save('clua.json', clua)
    text = '# Lot26 accepté — commandes validées\n\n09/26 : contrôleurs décalés validés ;12 : visage corrigé. Lancer BG2EE HD via InfinityLoader, une commande à la fois.\n\n```lua\n'
    for r in clua:
        text += f'-- {r["ordinal"]:02d} {r["bam"]} / {r["profile"]}\n{r["clua"]}\n'
    text += '```\n'
    (OUT / 'CLUA.md').write_text(text, encoding='utf-8')
    save('verification.json', {'schema': 'bg2-effects-acceptance-verification-v1', 'passed': True,
        'accepted_count': 26, 'runtime_resources_bound': 28, 'assets': proof,
        'other_rows_unchanged': True, 'installation_and_release_authorities_unchanged': True,
        'normal_and_alias_metadata_bound_to_final_frames': True})
    save('acceptance.json', {'schema': 'bg2-effects-batch-user-acceptance-v1', 'decision_date': '2026-10-17',
        'user_decision': decision, 'status': 'accepted', 'accepted_count': 26, 'accepted': accepted,
        'accepted_runtime_variants': accepted_runtime,
        'source_alias': {'SPIPLARI': {'canonical': 'SPIPLAAI', 'accepted_runtime_reuse': True,
            'separate_production_or_qa_row_inferred': False}},
        'sdf_assets': load(BATCH / 'batch.json')['sdf_assets'], 'sdf_inset_x4': 0,
        'face_fill_accepted': True, 'offset_visibility_tests_accepted': ['Z26V09', 'Z26V26'],
        'visibility_finding': 'User confirms09/26 visible when moved away from actor; original textures not empty. No new renderer or native-consumer correction inferred.',
        'production': evidence(BATCH / 'production.json'), 'face_production': evidence(FACE / 'production.json'),
        'base_installation': evidence(INSTALL / 'installation.json'), 'face_installation': evidence(FIX / 'installation.json'),
        'installed_manifest_sha256': sha(manifest_path), 'installed_registry_sha256': installed['registry_sha256'],
        'preserved_runtime_profile': preserved, 'accepted_controllers': controls,
        'runtime_contract': {'registry_version': 3, 'production_assets': 245, 'runtime_resources': 253,
            'model': 'seedvr2_7b_int8_convrot.safetensors', 'scale': 4, 'filter': 'NEAREST', 'target_fps': [30, 1],
            'duplicate_native_poses_removed_duration_preserved': True,
            'native_contracts_verified_at_installation': 70888, 'metadata_mib': 32},
        'ingame_qa': 'explicit-user-validation-of-installed-lot26-with-face-fix-and-offset-tests',
        'measured_presentation_cadence': 'no-new-instrumented-measurement-inferred',
        'historical_installation_receipts_immutable': True, 'installed_files_changed': False, 'release_mutation': False})
    print('26 accepted; final runtime/normal aliases/face fix/offset tests bound; other rows and installation/release unchanged.', flush=True)


if __name__ == '__main__':
    main()
