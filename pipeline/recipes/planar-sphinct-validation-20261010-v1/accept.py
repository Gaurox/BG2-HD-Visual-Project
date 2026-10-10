"""Seal unchanged installed SPHINCT output and explicit six-area QA; no install/release."""
import csv
import hashlib
import io
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import animation_workflow as workflow
from workspace_paths import get_path

TAG = 'sphinct-planar-accepted-20261010-v1'
AREAS = [f'AR{i:04d}' for i in range(516,522)]
PACK = ROOT/'animations/packs-par-zone'/TAG
RUN = ROOT/'animations/ressources/SPHINCT/runs'/TAG
GAME = get_path('bg2ee_game_root')
BATCH = ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7'
def load(p):
    return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def rel(p):
    return p.relative_to(ROOT).as_posix()
def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def payload(p):
    return {f.name:sha(f) for f in p.iterdir() if f.is_file() and (f.suffix=='.rgba' or f.name=='AreaAnimations-X4.registry')}

assert not (PACK/'manifest.json').exists() and not RUN.exists(), 'Immutable acceptance already exists'
installation = load(BATCH/'installation.json')
assert sha(GAME/'InfinityEngine-Enhancer.dll') == installation['dll_sha256'].upper()
original_run = ROOT/installation['run']
sources = {
    'AR0516':ROOT/'animations/packs-par-zone/ar0516-complete-plus-am0516ld-custom-blink-20260917/AR0516',
    'AR0517':ROOT/'animations/packs-par-zone/ar0517-sphinct-wed-crisp-20261010-v5/AR0517',
    **{a:ROOT/'animations/packs-par-zone/planar-sphinct-wed-crisp-20261010-v7'/a for a in AREAS[2:]},
}
for area, source in sources.items():
    assert payload(source)==payload(GAME/'iee-assets/areas'/area), area+' installation drift'
    if area in installation['protected_area_payloads']:
        expected = {k:v.upper() for k,v in installation['protected_area_payloads'][area].items()}
        assert payload(source)==expected, area+' protected payload drift'

# New immutable snapshot: exact copy of installed bytes; previous runs remain untouched.
entries = []
for area, source in sources.items():
    target = PACK/area
    target.mkdir(parents=True, exist_ok=True)
    for p in source.iterdir():
        if not p.is_file() or not (p.suffix=='.rgba' or p.name in ('manifest.json','AreaAnimations-X4.registry')):
            continue
        shutil.copy2(p, target/p.name)
    entries.append(dict(area_id=area, directory=area, manifest_sha256=sha(target/'manifest.json'), registry_sha256=sha(target/'AreaAnimations-X4.registry')))

write(PACK/'manifest.json', dict(schema='bg2-upscale-area-animation-pack-index-v1', status='completed', created_utc=datetime.now(timezone.utc).isoformat(), areas=entries, selection='Exact installed area packs accepted by user; no payload transformation'))
write(RUN/'manifest.json', dict(
    schema='bg2-upscale-animation-final-selection-v1', status='completed',
    created_utc=datetime.now(timezone.utc).isoformat(), resrefs=['SPHINCT'],
    source_run=rel(original_run), source_run_manifest_sha256=sha(original_run/'manifest.json'),
    output_split_root=rel(PACK), output_manifest_sha256=sha(PACK/'manifest.json'),
    runtime_contract=dict(scale=4, fps=30, rgb_policy='unchanged-straight-alpha', fit_error_x4=1, supersampling=4, edge_filter='BOX', guard_x4=0, feather_x4=0, renderer_dll_sha256=installation['dll_sha256'].upper(), renderer_receipt=installation['renderer_receipt'], installation=rel(BATCH/'installation.json'), areas=AREAS, AR0516_positions=installation['AR0516_positions'], AR0516_mode=installation['AR0516_mode'], AR0517='Accepted crisp v5 reference, byte-identical'),
    selection_reason='Utilisateur confirme la validation de SPHINCT sur toutes les maps AR0516-AR0521 ; valider definitivement en etat et committer.',
))
notes = 'QA ingame explicite 2026-10-10 sur AR0516-AR0521. SPHINCT x4 TimedTimeline30fps, WED SplineFit1 monde x4 SS4/BOX retrait0/fondu0. AR0517 reference crisp v5 conservee ; AR0518-AR0521 masques alpha lies aux positions ; AR0516 trois masques renderer aux positions1520,1287/1529,1447/2948,1776, frames originales preservees. DLL et packs installes exacts scelles dans le run accepte. Aucun changement release.'
result = workflow.finalize(ROOT,'SPHINCT',rel(RUN),rel(PACK),AREAS,'accepted','2026-10-10',
    'Validation explicite utilisateur de SPHINCT sur toutes les maps AR0516-AR0521, en etat installe. Contrat runtime et DLL fixes dans le manifeste final ; aucune extension QA implicite.',
    decision_id='2026-10-10-accepted-sphinct-planar-final-v1',
    recipe_id='world-wed-spline-fit1-ss4-box-crisp', correction_id='planar-sphinct-wed-crisp-20261010-v7', notes=notes, apply=True)

corrections = ROOT/'animations/index/animation_alpha_corrections.csv'
raw = corrections.read_bytes()
stream = io.StringIO(newline='')
csv.writer(stream,lineterminator='\n').writerow(['SPHINCT',';'.join(AREAS),'orifice et occlusion branches','planar-sphinct-wed-crisp-20261010-v7-final-accepted','world-wed-spline-fit1;SS4-BOX;guard0;feather0;occurrence-binding;renderer-three-world-masks',0,0,'none','unchanged','validated-installed','2026-10-10',rel(RUN),'QA finale explicite sur les six maps. Selection animations/index/selections/SPHINCT.json ; DLL SHA256 '+installation['dll_sha256'].upper()+'. Historique conserve ; aucune release.'])
corrections.write_bytes(raw+(b'' if raw.endswith(b'\n') else b'\n')+stream.getvalue().encode('utf-8'))
write(Path(__file__).parent/'acceptance.json',dict(schema='bg2-upscale-animation-batch-acceptance-v1',status='accepted-ingame',decision_date='2026-10-10',decision_origin='explicit-user-ingame-qa',resref='SPHINCT',areas=AREAS,final_run=rel(RUN),source_pack=rel(PACK),renderer_sha256=installation['dll_sha256'].upper(),renderer_receipt=installation['renderer_receipt'],installation=rel(BATCH/'installation.json'),qa_decision='animations/index/qa-decisions/SPHINCT/2026-10-10-accepted-sphinct-planar-final-v1.json',release='not-selected'))
print(json.dumps(result,ensure_ascii=False,indent=2))
