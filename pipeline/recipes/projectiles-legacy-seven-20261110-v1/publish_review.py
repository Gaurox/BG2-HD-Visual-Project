"""Record seven bounded usage decisions; never writes game, images, QA or release."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path

OUT = ROOT / 'projectiles/analysis/legacy-seven-usage-20261110-v1'
INDEX = ROOT / 'projectiles/index'
STATE = 'reviewed-native-legacy-preserved'
TARGETS = {'LIGHTSTO': (92, 'MAGMIS'), **{
    f'engine-id:{i}': (i, name) for i, name in [
        (21, 'SPBRNHND'), (24, 'SPBRNHND'), (25, 'SPBRNHND'),
        (44, 'SPSMKJET'), (96, 'COLRSPRY'), (241, 'SPHOLYMT')]}}


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def ref(p):
    return dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p))


def write(p, data, new=False):
    # Current index files pin raw CRLF bytes via .gitattributes (-text).
    with p.open('x' if new else 'w', encoding='utf-8', newline='\r\n' if p.parent == INDEX else '\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    assert not (OUT / 'decisions.json').exists()
    prior = load(INDEX / 'owner-reconciliation-current.json')
    owners = load(ROOT / prior['owners']['path'])
    assert Counter(r['state'] for r in owners) == {
        'reconciled-compatible-contracts': 313, 'documented-native-gap-no-static-driver': 7}
    for part in ('owners', 'summary', 'exceptions'):
        assert sha(ROOT / prior[part]['path']) == prior[part]['sha256']
    stock = load(OUT / 'summary.json')
    active = load(OUT / 'active/summary.json')
    native = load(OUT / 'native-review.json')
    for scan in (stock, active):
        assert scan['target_projectile_references'] == scan['effect_provenance_matches'] == 0
        assert scan['warnings'] == []
    assert native['MAGMIS'] == dict(stock_BAM_present=False, override_BAM_present=False)
    assert native['COLRSPRY'] == dict(stock_BAM_present=True, installed_catalogue_present=False)

    game = get_path('bg2ee_game_root', required=True)
    pinned = {
        'BaldurReal.exe': native['executable_sha256'],
        'InfinityEngine-Enhancer.dll': 'ED9A5E4EE34D695DB84448EE7E9A8E221D39E6DEBD340479F114AD4E9132A844',
        'InfinityEngine-Enhancer.ini': 'AB4A3C300C08EC88A137806C4F9C6590C908E67A93028DC4387F68FFAD6D8B0D',
        'iee-assets/effects/manifest.json': '4ED0F7CDD1374F74001B45FCCD6063F8275783BE7F1B11839B0BBFDAAF85B5B9',
    }
    for path, expected in pinned.items():
        assert sha(game / path) == expected, path
    manifest = load(game / 'iee-assets/effects/manifest.json')
    catalog = {r['resref']: r for r in manifest['resources']}
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}

    def bam(name):
        raw = resolve_resource(bifs, key[name, 1000])[0]
        return zlib.decompress(raw[12:]) if raw[:4] == b'BAMC' else raw

    images = {}
    for name in ('SPBRNHND', 'SPSMKJET', 'SPHOLYMT', 'COLRSPRY'):
        raw = bam(name)
        frames, cycles = struct.unpack_from('<HB', raw, 8)
        images[name] = dict(canonical_BAM_sha256=hashlib.sha256(raw).hexdigest().upper(),
                            native_frames=frames, native_cycles=cycles)
        if name != 'COLRSPRY':
            s = load(ROOT / f'effects/index/selections/{name}.json')
            for evidence in (s['qa_evidence'], s['runtime_pack']['manifest']):
                assert sha(ROOT / evidence['path']) == evidence['sha256']
            pack = load(ROOT / s['runtime_pack']['manifest']['path'])
            assert catalog[name]['frame_count'] == pack['frame_count']
            assert catalog[name]['cycles'] == pack['cycles']
            assert catalog[name].get('interpolation_run', catalog[name].get('source', {}).get('interpolation_run')) == s['contract']['source']['interpolation_run']
            images[name]['existing_authorities'] = native['selected_assets'][name]
    assert bam('SPBRNHND') == bam('BURNHAND')
    images['SPBRNHND']['exact_native_alias'] = 'BURNHAND'

    scripts = load(OUT / 'active/script-actions.json')
    smoke = [r for r in scripts if r['action'] == 273 and 'SPSMKJET' in r['strings']]
    assert Counter(r['owner'] for r in smoke) == {'HEXXAT.bcs': 3, 'HEXXA25.bcs': 3}
    spell = resolve_resource(bifs, key['SPIN629', 1006])[0]
    assert struct.unpack_from('<H', spell, 0xfa)[0] == 215
    assert spell[0x10e:0x116].upper() == b'SPHOLYMT'
    hooks = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp'
    text = hooks.read_text(encoding='utf-8')
    vvc = text.split('static void detour_vvc_vid_cell_render(', 1)[1].split('static int detour_effect_fx_lock(', 1)[0]
    assert 'read_registered_effect_resref' in vvc and 'effect_secondary_scope' not in vvc

    rationale = {
        'LIGHTSTO': 'MAGMIS absent KEY+override; no established incoming driver. Preserve PRO, never invent MAGMIS or substitute SPMAGMIS. Appel de la foudre uses80..83 then22/SKYBOLT.',
        'engine-id:21': 'Legacy SPBRNHND constructor; no established driver. Existing accepted/installed image also exact native alias BURNHAND. Modern SPWI103 uses340/BURNHAND.',
        'engine-id:24': 'Legacy cone constructor0x227800; no established driver. SPBRNHND already produced; modern Cone of Cold uses249/CONECOLD.',
        'engine-id:25': 'Legacy recoloured cone constructor0x227800; no established driver. No new palette pack or secondary scope justified without actual consumer.',
        'engine-id:44': 'No established PROJECTL44 driver. SPSMKJET has six action273 calls in Hexxat scripts, using named visual effects, not this projectile. Existing accepted/catalogued image, existing VVC scope.',
        'engine-id:96': 'COLRSPRY stock BAM exists, not catalogued. No established consumer. Modern Color Spray SPWI105 uses248/CSPRAY. Preserve stock; no speculative generation.',
        'engine-id:241': 'No established PROJECTL241 driver. SPIN629 opcode215 and native0x3c0aa1→0x3c0dbb opcode215 dispatcher use SPHOLYMT as named visual effect. Existing accepted/catalogued image, existing VVC scope.',
    }
    decisions = dict(schema='bg2-projectile-legacy-seven-usage-decisions-v1', date='2026-11-10',
        user_request='fais le 1 (7 cas)', state=STATE,
        scope='Stock KEY plus current relevant override; bounded native executable references; excludes player saves and arbitrary runtime/mod inputs.',
        evidence=[ref(OUT / p) for p in ['summary.json', 'active/summary.json', 'inputs.json',
            'active/inputs.json', 'native-review.json', 'active/asset-name-references.json', 'active/script-actions.json']],
        images=images, named_visual_routes=dict(SPSMKJET=smoke,
            SPHOLYMT=dict(owner='SPIN629.spl', effect_offset='0xfa', opcode=215, resource_offset='0x10e'),
            existing_VVC_renderer=ref(hooks), live_draw_claimed=False),
        cases=[dict(owner=owner, PROJECTL=ident, ability_missile=ident+1, image=image,
            decision=STATE, reason=rationale[owner], established_driver_hits=0,
            native_behavior_preserved=True, HD_route_qualified=False, new_manual_test=False)
            for owner, (ident, image) in TARGETS.items()],
        reopen_when='An actual driver/runtime observation is identified for the preserved ID, or source bytes/mod configuration change.',
        limits=native['limits'], new_inference_jobs=0, new_runtime_links=0, new_manual_tests=0,
        visual_QA_changed=False, installation_changed=False, release_changed=False)
    write(OUT / 'decisions.json', decisions, new=True)
    decision_ref = ref(OUT / 'decisions.json')
    for row in owners:
        if row['owner'] in TARGETS:
            assert row['state'] == 'documented-native-gap-no-static-driver'
            row.update(state=STATE, native_usage_review=decision_ref,
                preservation_disposition='Reviewed; no established driver in scanned sources; HD gaps retained as errors, not promoted to qualified.')
    write(OUT / 'owners.json', owners, new=True)
    write(OUT / 'exceptions.json', [], new=True)
    summary = dict(schema='bg2-projectile-owner-reconciliation-native-review-v1', date='2026-11-10',
        prior_authority=prior, decisions=decision_ref, owner_states=dict(Counter(r['state'] for r in owners)),
        total_owners=320, reviewed_owners=320, reviewed_percentage=100,
        technical_qualified_owners=313, technical_percentage=97.8125,
        reviewed_native_preservations=7, native_gap_usage_reviews_pending=0,
        active_exception_families=0, pending_manual_checks=0,
        QA_installation_release_preserved=True, runtime_readback_sha256=pinned)
    write(OUT / 'owner-summary.json', summary, new=True)
    pointer = deepcopy(prior)
    pointer.update(report=(OUT / 'README.md').relative_to(ROOT).as_posix(),
        summary=ref(OUT / 'owner-summary.json'), owners=ref(OUT / 'owners.json'),
        exceptions=ref(OUT / 'exceptions.json'), states=summary['owner_states'],
        reviewed_owners=320, reviewed_percentage=100, reviewed_native_preservations=7,
        native_gap_usage_reviews_pending=0,
        meaning='320 owner dispositions reviewed:313 compatible technical contracts plus7 justified native legacy preservations. Seven HD gaps remain, not pending usage analysis or visual QA; no global whole-chain acceptance claim.')
    # Keep deferred_native_gaps=7: these are still unqualified HD routes.
    write(INDEX / 'owner-reconciliation-current.json', pointer)
    tracking_path = INDEX / 'work-tracking.json'
    tracking = load(tracking_path)
    before = deepcopy(tracking)
    for owner in TARGETS:
        r = tracking['projectiles']['LIGHTSTO'] if owner == 'LIGHTSTO' else tracking['engine_projectiles'][owner.split(':')[1]]
        integ = r['integration']
        integ['evidence'].append(decision_ref['path'])
        integ['automatic_reconciliation'].update(state=STATE, evidence=pointer['owners']['path'])
        integ['native_usage_review'] = dict(state=STATE, evidence=decision_ref,
            scope='Usage disposition only; source/HD gaps/QA/installation/release preserved.', reopen_when=decisions['reopen_when'])
    tracking['owner_evidence_reconciliation'] = pointer
    # Only the seven integration records and authority pointer may change.
    check = deepcopy(tracking)
    check['owner_evidence_reconciliation'] = before['owner_evidence_reconciliation']
    for owner in TARGETS:
        group, keyname = ('projectiles', 'LIGHTSTO') if owner == 'LIGHTSTO' else ('engine_projectiles', owner.split(':')[1])
        check[group][keyname]['integration'] = before[group][keyname]['integration']
    assert check == before
    write(tracking_path, tracking)
    progress_path = INDEX / 'validation-progress-current.json'
    progress = load(progress_path)
    progress['authorities']['work_tracking_sha256'] = sha(tracking_path)
    progress['automatic_owner_reconciliation'] = pointer
    progress['remaining_work'] = [
        'Seven native legacy usage cases reviewed and preserved: no established driver in stock/current override scans; reopen only on a new driver/source change.',
        '0 active route/palette correction, inference job, usage review or manual test pending in this scope;313/320 technical qualification unchanged.',
        'Position interpolation PROJ-MOTION-001 remains deferred;release separate.']
    progress['legacy_native_usage_review'] = decision_ref
    write(progress_path, progress)
    native_path = INDEX / 'native-contract-review-current.json'
    current = load(native_path)
    current.update(owner_reconciliation=pointer, latest_legacy_usage_review=decision_ref,
                   current_summary=ref(progress_path))
    write(native_path, current)
    write(OUT / 'verification.json', dict(seven_integration_records_only=True,
        other_tracking_fields_equal=True, qualified_contracts_unchanged=313,
        reviewed_dispositions=320, runtime_readback_sha256=pinned,
        new_game_writes=0, new_QA_decisions=0, new_release_changes=0), new=True)
    print('7 native preservation decisions;320/320 dispositions reviewed;313/320 technical unchanged;0 new jobs/links/manual tests/game writes.')


if __name__ == '__main__':
    main()
