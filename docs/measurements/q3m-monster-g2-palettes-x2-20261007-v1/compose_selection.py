"""Current complete selection from base77 +MFIE +G2 corrections; no inference."""
import copy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from q3m_family_witnesses import validate_selection
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
base=HERE.parent/'q3m-monster-full-x2-20261006-v2/selection.json'
deltas=[HERE.parent/'q3m-mfie-native-palettes-x2-20261007-v3/selection.json',HERE.parent/'q3m-monster-final-checks-x2-20261007-v1/correction-selection.json']
selection=load(base);original=copy.deepcopy(selection['witnesses']);replacements={}
for path in deltas:
    for w in load(path)['witnesses']:assert w['animation_id'] not in replacements;replacements[w['animation_id']]=w
assert set(replacements)=={'0x7312','0x7313','0x7314'}
selection['witnesses']=[replacements.get(w['animation_id'],w) for w in original]
selection['scope']='current complete native Monster family; base plus three native bank palette corrections'
assert len(validate_selection(selection,'monster'))==77
assert [w for w in original if w['animation_id'] not in replacements]==[w for w in selection['witnesses'] if w['animation_id'] not in replacements]
path=HERE/'full-selection.json';assert not path.exists();write_json(path,selection)
write_json(HERE/'full-selection-provenance.json',dict(base=dict(path=base.relative_to(ROOT).as_posix(),sha256=file_sha(base)),
    deltas=[dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p)) for p in deltas],witnesses=77,unchanged_witnesses=74,
    current_selection=dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path)),validation_passed=True,inference=False))
index=ROOT/'sprite/index/q3m-work-tracking.json';tracking=load(index);f=next(f for f in tracking['families'] if f['engine_section']=='monster')
for item in (f['current_full_production'],next(r for r in tracking['current_recipe_complete_productions'] if r['family']=='monster')):
    item.update(selection=path.relative_to(ROOT).as_posix(),selection_provenance=(HERE/'full-selection-provenance.json').relative_to(ROOT).as_posix(),
        work_statistics_scope='original complete batch before native palette deltas; not global keys recounted after corrections',
        correction_cost_reference=(HERE/'production-resume-evidence.json').relative_to(ROOT).as_posix())
write_json(index,tracking)
print('Complete selection77:74 witnesses unchanged,7312/7313/7314 native bank corrections validated.')
