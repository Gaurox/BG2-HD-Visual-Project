"""Seal the visually reviewed offline report; active game installation stays unchanged."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
trial=load(HERE/'trial.json');pdf=load(HERE/'pdf.json')
assert not (HERE/'verification.json').exists(),'final proof is immutable; use another version'
assert file_sha(ROOT/pdf['pdf'])==pdf['sha256']
assert file_sha(HERE/'trial.json')==pdf['source_trial_sha256']
assert file_sha(HERE/'sdf_trial.py')==trial['processor']['sha256']
assert trial['selected_frames']==trial['unique_mask_work']==12
assert all(r['solid_components_before']==r['solid_components_after'] and
    r['background_components_before']==r['background_components_after'] and
    abs(r['area_change_percent'])<.5 for r in trial['records'])
parent=ROOT/'docs/measurements/q3m-ankheg-alpha-light-x2-20261004-v1/ingame-installation/active-test.json'
receipt=load(parent);game=get_path('bg2ee_game_root',required=True)
for name,key in [('iee-assets/creature-sprites/CreatureSprites-XN.catalog','catalog_sha256'),
    ('InfinityEngine-Enhancer.dll','dll_sha256'),('InfinityEngine-Enhancer.ini','ini_sha256')]:
    assert file_sha(game/name)==receipt[key].lower(),'game installation changed during offline simulation'
pdf['visual_review']='agent-reviewed-five-rendered-pages-layout-and-comparative-content'
pdf['renderer']='Poppler pdftoppm, PNG 144 dpi'
write_json(HERE/'pdf.json',pdf)
write_json(HERE/'verification.json',dict(schema='bg2-ankheg-SDF-offline-final-verification-v1',
    role='offline-test-not-ingame-QA-installation-or-release',trial=identity(HERE/'trial.json'),
    pdf=identity(ROOT/pdf['pdf']),pdf_metadata=identity(HERE/'pdf.json'),
    visual_review=dict(authority='agent',pages=5,layout='passed',comparative_content='reviewed'),
    selected_frames=12,mask_computation_work=12,neural_work=0,
    silhouette_checks=dict(solid_components_and_holes_preserved_at_centres=True,
        maximum_absolute_area_change_percent=max(abs(r['area_change_percent']) for r in trial['records']),
        maximum_field_bias_x2=max(r['maximum_field_change_x2'] for r in trial['records'])),
    code=[identity(HERE/f) for f in ['sdf_trial.py','prepare.py','generate.py','details.py','build_pdf.py']],
    images=[identity(p) for p in sorted((HERE/'images').glob('*.png'))]+[identity(HERE/'comparatif.png')],
    active_installation_unchanged=True,active_receipt=identity(parent),ingame_QA=False,release=False))
print(json.dumps(dict(pdf=pdf['pdf'],pages=5,visual_review='passed',game_unchanged=True,offline_only=True)))
