"""Freeze the approved 77-ID Monster selection and its replacement palette sources."""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from palette_work_plan import write_json
from run_creature_sprite_x2 import KeyIndex
from workspace_paths import get_path
from q3m_family_witnesses import validate_selection

def main():
    assert not (HERE / 'selection.json').exists(), 'immutable selection already exists'
    rows = list(csv.DictReader((ROOT / 'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig')))
    inventory = {r['animation_id']: r for r in csv.DictReader((ROOT / 'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
    game = get_path('bg2ee_game_root', required=True)
    key = KeyIndex(game)
    bmps = key.resource_map(1)
    selected = [r for r in rows if r['engine_family'] == 'monster' and int(r['source_bam_count'])]
    absent = [r['animation_id'] for r in rows if r['engine_family'] == 'monster' and not int(r['source_bam_count'])]
    assert len(selected) == 77 and len(absent) == 25 and len({r['body_resref'] for r in selected}) == 62
    witnesses, palettes = [], {}
    for row in selected:
        native = inventory[row['animation_id']]
        witness = dict(family='monster', animation_id=row['animation_id'], name=row['ids_symbol'], owner=3,
                       native_kind=int(native['false_color']), refs=row['bam_resrefs'].split(';'))
        replacement = json.loads(native['ini_sections_json']).get('general', {}).get('new_palette')
        if replacement:
            assert not (game / 'override' / (replacement + '.bmp')).exists(), 'unexpected palette override'
            raw, bif = key.resolve(bmps[replacement])
            witness['palette_override'] = dict(resref=replacement, sha256=hashlib.sha256(raw).hexdigest())
            witness['palette_override_scope'] = 'world'
            palettes[replacement] = dict(**witness['palette_override'], bytes=len(raw), source_bif=bif)
        witnesses.append(witness)
    selection = dict(schema='bg2-q3m-family-witness-selection-v1', scale=2, colour='K6-four-partners-eight-levels',
                     scope='complete available Monster; native frames/actions/centres/cycles retained; Q3m V7 x2; no SDF',
                     source_absent_animation_ids=absent, witnesses=witnesses)
    validate_selection(selection, 'monster')
    assert len({ref for w in witnesses for ref in w['refs']}) == 850 and len(palettes) == 15
    write_json(HERE / 'selection.json', selection)
    write_json(HERE / 'source-scope.json', dict(models=62, animation_ids=77, source_absent_animation_ids=absent,
               unique_native_BAM=850, original_native_frames=409599, replacement_palettes=list(palettes.values()),
               installation=False, ingame_QA=False, release=False))
    print(json.dumps(dict(stage='selection', models=62, animation_ids=77, unique_native_BAM=850, palettes=len(palettes))), flush=True)

if __name__ == '__main__':
    main()
