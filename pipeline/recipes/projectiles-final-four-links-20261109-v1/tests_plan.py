"""Prepare only three real palette variants; keep equivalent neutral/beam checks automatic."""
from pathlib import Path
import csv
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path

OUT = ROOT / 'projectiles/analysis/final-four-links-20261109-v1'


def main():
    assert not (OUT / 'visual-tests.json').exists()
    game = get_path('bg2ee_game_root', required=True)
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    current = json.loads((ROOT / 'projectiles/index/work-analysis-current.json').read_text())
    usage = list(csv.DictReader((ROOT / current['snapshot'] / 'usage.csv').open(encoding='utf-8-sig')))
    tests = []
    for number, spell, ident, resource, variant, target in [
        # SPWI985 also applies Remove Creature168; future drivers must use a
        # disposable enemy. The originally tested Player2 command is archived.
        (1, 'SPWI985', 194, 'HLYMITE', 'Native RED_HOLY_MIGHT tint', 'NearestEnemyOf(Myself)'),
        (2, 'SPIN835', 130, 'SHAIR', 'Native SHAIR4 BMP palette', 'Player1'),
        (3, 'SPIN782', 137, 'SHEARTH', 'Native SHEARTH6 BMP palette', 'Player2'),
    ]:
        override = game / 'override' / (spell + '.spl')
        raw = override.read_bytes() if override.exists() else resolve_resource(bifs, key[spell, 1006])[0]
        digest = hashlib.sha256(raw).hexdigest().upper()
        refs = [r for r in usage if r['resource'] == spell and r['format'] == 'SPL']
        assert refs and all(int(r['projectl_id']) == ident and r['source_sha256'] == digest for r in refs)
        for r in refs:
            assert struct.unpack_from('<H', raw, int(r['offset'], 16))[0] == ident + 1
        tests.append(dict(id=f'F4-C{number}', resource=resource, variant=variant,
            source_spell=spell, source_sha256=digest, native_projectl=ident,
            command=f'C:Eval(\'ForceSpellRES("{spell}",{target})\',0)',
            state='pending-new-colour-review', inspect='Colour only, plus obvious transparency/placement anomaly.',
            capability_references=refs))
        if number==1:
            tests[-1].update(setup_command='C:CreateCreature("OGRE01")',
                gameplay_effect='Opcode168 Remove Creature, delayed2seconds; never target a party member.')
    skipped = [dict(resource=n, reason='Neutral source-to-realized palette is identity; pixel copies unchanged and native loader geometry/cycles pass.')
               for n in ['HLYMITE', 'SHAIR', 'SHEARTH']]
    skipped.append(dict(resource='SPSCORIC', reason='Existing visual approval retained; nine native orientation cycles and both phase profiles qualify automatically. No new artwork/geometry/motion; live HD draw not measured.'))
    payload = dict(manual_tests=tests, manual_test_count=3, automated_instead_of_retest=skipped,
        no_repeat_of_previous_six=True, beam_retest_requested=False,
        new_image_generation=0, status='installed-three-colour-checks-only')
    (OUT / 'visual-tests.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Three native palette drivers verified; neutral variants and beam not queued for manual retest.')


if __name__ == '__main__':
    main()
