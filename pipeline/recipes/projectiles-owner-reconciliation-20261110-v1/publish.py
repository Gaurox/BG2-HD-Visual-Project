"""Publish scoped owner reconciliation, preserving QA/install/release decisions."""
from pathlib import Path
from collections import Counter
import copy
import json
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reconcile import ROOT, load, save, sha
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from projectile_tracking import validate_tracking, read_csv
from workspace_paths import get_path

OUT = ROOT / 'projectiles/analysis/owner-contracts-20261110-v1'


def main():
    assert not (OUT / 'publication.json').exists(), 'Already published; use a new version'
    summary = load(OUT / 'summary.json')
    owners = load(OUT / 'owners.json')
    components = load(OUT / 'components.json')
    physical = load(OUT / 'physical.json')
    game = get_path('bg2ee_game_root', required=True)
    assert not physical['metadata_only'] and not physical['issues']
    assert 'contracts checked: 31668' in (ROOT / '.tmp/projectile-reconciliation-loader.log').read_text(encoding='utf-8')
    shutil.copyfile(ROOT / '.tmp/projectile-reconciliation-loader.log', OUT / 'native-loader.log')
    changes = []
    recorded_inputs = load(OUT / 'inputs.json')
    source_snapshot = load(ROOT / summary['snapshot'] / 'analysis.json')
    assert sha(game / 'chitin.key') == source_snapshot['inputs']['config://bg2ee_game_root/chitin.key']
    for name, expected in recorded_inputs.items():
        if name.startswith('KEY://'):
            continue  # Native resource hashes recorded by reader; KEY/active overrides separately pinned.
        if name.startswith('ABSENT://'):
            n = name.split('://', 1)[1]
            if (game / 'override' / n).exists():
                changes.append(name)
            continue
        p = game / name.split('config://bg2ee_game_root/', 1)[1] if name.startswith('config://') else ROOT / name
        if not p.exists() or sha(p) != expected:
            changes.append(name)
    assert not changes, changes
    common_source_hashes = {n for n in recorded_inputs.keys() & source_snapshot['inputs'].keys()
                            if n.startswith(('KEY://', 'effects/ressources/', 'projectiles/ressources/'))}
    assert all(recorded_inputs[n] == source_snapshot['inputs'][n] for n in common_source_hashes)
    assert sha(HERE / 'reconcile.py') == summary['recipe_sha256']
    assert len(owners) == len({o['owner'] for o in owners}) == 320
    assert len([o for o in owners if o['owner'].startswith('engine-id:')]) == 77
    assert Counter(o['state'] for o in owners) == {
        'reconciled-compatible-contracts': 299,
        'exception-to-treat': 13,
        'documented-native-gap-no-static-driver': 8}
    exceptions = []
    for name, resource_names, ids, action in [
        ('SHWATER', ['SHWATER'], [120, 123, 126, 129, 132, 135, 138, 141],
         'Register the native SpellHit FX cell; add source-specific realized-palette transfer for SHWATER1..7 before enabling coloured HD.'),
        ('FLMSTRK', ['FLMSTRK'], [145],
         'Register and qualify the existing FLMSTRK pack on the native SkyStrike route; ID66 shares this image but has no scanned driver.'),
        ('SPDIMDR1-SPDIMDR2', ['SPDIMDR1', 'SPDIMDR2'], [109],
         'Register both native DimensionDoor phases and qualify the 2->1->2 occurrence lifecycle; images already produced/accepted.'),
        ('SPBOOM-palettes', ['SPBOOM'], [142, 143, 144],
         'Preserve the accepted neutral/fireball route. Qualify/apply native range0 colours67/65/69 to the private GPU upload for opcode141 variants32/33/34.')]:
        affected = [c for c in components if c['owner'] in {f'engine-id:{i}' for i in ids} and c['errors']]
        assert affected and all(c['native_resource'] in resource_names for c in affected)
        exceptions.append(dict(id=name, state='technical-exception-to-treat', resources=resource_names,
            engine_IDs=ids, owners=[f'engine-id:{i}' for i in ids],
            errors=sorted({e for c in affected for e in c['errors']}), action=action,
            new_inference_required=False, new_manual_tests_prepared=False,
            source_evidence=['opcode-references.csv', 'engine-owners.json', 'components.json']))
    assert {o for e in exceptions for o in e['owners']} == {o['owner'] for o in owners if o['state'] == 'exception-to-treat'}
    save(OUT / 'exceptions.json', exceptions)
    tracking_path = ROOT / 'projectiles/index/work-tracking.json'
    tracking = load(tracking_path)
    original = copy.deepcopy(tracking)
    baseline = load(OUT / 'qa-baseline.json')
    for ns, records in baseline.items():
        for name, states in records.items():
            actual = {k: v for k, v in tracking[ns][name].items() if k in ('qa', 'component_visual_qa', 'release')}
            assert actual == states, (ns, name, 'QA/release changed during reconciliation')
    evidence = (OUT / 'owners.json').relative_to(ROOT).as_posix()
    for record in owners:
        ns, name = ('engine_projectiles', record['owner'].split(':')[1]) if record['owner'].startswith('engine-id:') else ('projectiles', record['owner'])
        item = tracking[ns].setdefault(name, {})
        integration = item.setdefault('integration', dict(state='technical-reconciliation-recorded', evidence=[evidence]))
        integration['automatic_reconciliation'] = dict(state=record['state'], evidence=evidence,
            owner=record['owner'], reviewed_on='2026-11-10',
            contract_PRO_sha256=record['active_PRO_sha256'], errors=record['errors'],
            scope='Static native owner/child/geometry/cycles/palette/installed backing contract; no new visual approval, live draw or full spell-chain claim.')
    pointer = dict(schema='bg2-projectile-owner-reconciliation-current-v1', date='2026-11-10',
        report=(OUT / 'README.md').relative_to(ROOT).as_posix(),
        summary=dict(path=(OUT / 'summary.json').relative_to(ROOT).as_posix(), sha256=sha(OUT / 'summary.json')),
        owners=dict(path=evidence, sha256=sha(OUT / 'owners.json')),
        exceptions=dict(path=(OUT / 'exceptions.json').relative_to(ROOT).as_posix(), sha256=sha(OUT / 'exceptions.json')),
        states=summary['owner_states'], actionable_families=4, actionable_engine_IDs=13,
        deferred_native_gaps=8, new_manual_tests=0,
        meaning='Technical reconciliation only. Existing visual QA and installation/release decisions remain separate.')
    tracking['owner_evidence_reconciliation'] = pointer
    validate_tracking(tracking, {r['resref'] for r in read_csv(ROOT / 'projectiles/index/resources.csv')})
    # Existing independent decisions are byte-semantically preserved, including installation.
    for ns in ('projectiles', 'engine_projectiles'):
        for name, previous in original[ns].items():
            for field in ('qa', 'component_visual_qa', 'installation', 'release'):
                assert previous.get(field) == tracking[ns][name].get(field)
    tracking_path.write_text(json.dumps(tracking, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / 'projectiles/index/owner-reconciliation-current.json').write_text(json.dumps(pointer, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    progress_path = ROOT / 'projectiles/index/validation-progress-current.json'
    progress = load(progress_path)
    progress['authorities']['work_tracking_sha256'] = sha(tracking_path)
    progress['source_inventory']['engine_IDs_referenced'] = 60
    progress['source_inventory']['engine_driver_scan'] = 'Abilities + PRO children + active SPL/ITM/EFF op140/op141;32 opcode-targeted engineIDs,27 additional to the33 previously counted.'
    progress['automatic_owner_reconciliation'] = pointer
    progress['remaining_work'] = [e['id'] + ': ' + e['action'] for e in exceptions] + [
        'Eight native gaps without scanned drivers retained separately, including LIGHTSTO/MAGMIS. No speculative asset production or test request.',
        'Manual QA only for genuine new visual differences after technical fixes. Position interpolation remains deferred; release separate.']
    progress['technical_projection']['meaning'] = 'Historical conservative projection. Current per-owner technical disposition: owner-reconciliation-current.json; generic source tasks are not actionable exceptions or manual tests.'
    progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    native_path = ROOT / 'projectiles/index/native-contract-review-current.json'
    native = load(native_path)
    native['owner_reconciliation'] = pointer
    native['current_summary']['sha256'] = sha(progress_path)
    native_path.write_text(json.dumps(native, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save(OUT / 'publication.json', dict(owners_linked=320, QA_states_changed=0, installation_states_changed=0,
        release_states_changed=0, game_files_changed=0, actionable_families=4,
        work_tracking_sha256=sha(tracking_path), progress_sha256=sha(progress_path),
        pointer_sha256=sha(ROOT / 'projectiles/index/owner-reconciliation-current.json')))
    print('Published:320 owners;4 active exception families;QA/installation/release unchanged.')


if __name__ == '__main__':
    main()
