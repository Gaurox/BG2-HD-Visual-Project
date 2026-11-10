"""Publish retained video status/catalogue after the completed cleanup."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
VIDEO = ROOT / 'video'


def main():
    cleanup = json.loads((HERE / 'cleanup.json').read_text())
    assert cleanup['state'] == 'complete'
    plan = json.loads((HERE / 'plan.json').read_text())
    processing = VIDEO / 'index/processing.csv'
    with processing.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f); fields = reader.fieldnames; rows = list(reader)
    if not any(r['asset_key'] == 'movie:default:POCKETZZ' for r in rows):
        row = {k: '' for k in fields}
        row.update(asset_key='movie:default:POCKETZZ', asset_id='videos:movie-default-pocketzz',
            asset_directory='video/pocketzz', upscale_run='pocketzz-comfyui-experiments-20260814',
            upscale_state='produced', interpolation_state='not-started',
            validation_scope='candidate-kept-not-validated', patch_state='not-integrated',
            notes='Utilisateur 2026-11-10 conserve uniquement ComfyUI_00002_.mp4 SeedVR FullHD15 '
                  'comme candidat; aucun rendu valide ni installation deduit; autres essais supprimes')
        rows.append(row)
    with processing.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n'); writer.writeheader(); writer.writerows(rows)

    finals = {
        'DEATHAND': 'deathand/runs/deathand-interpolation-apollo8-30fps-v1/03_interpolation/video-1080p-30fps-apollo8.mov',
        'FLYTHR03': 'flythr03/runs/flythr03-lab-interpolation-apollo8-30fps-v1/03_interpolation/video-1080p-30fps-apollo8.mov',
        'RESTDUNG': 'restdung/runs/restdung-seedvr-apollo30-20261109-v1/SeedVR2-RESTDUNG-3B-FP16-LAB-Apollo8-1080p30.mp4',
        'RESTINN': 'restinn/runs/restinn-seedvr-apollo-20261109-v1/RESTINN-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4',
        'REST': 'rest/runs/rest-seedvr-apollo-20261109-v1/REST-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4',
        'DAYNITE': 'daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4',
        'POCKETZZ': 'pocketzz/runs/pocketzz-comfyui-experiments-20260814/ComfyUI_00002_.mp4',
    }
    with (VIDEO / 'index/resources.csv').open(encoding='utf-8-sig', newline='') as f:
        resources = list(csv.DictReader(f))
    selected = {r['asset_key']: r for r in rows}
    statuses = []
    for resource in resources:
        key, name = resource['asset_key'], resource['resref']
        row = selected.get(key)
        installed = name in {'DAYNITE', 'RESTDUNG'} and key.startswith('movie:default:')
        output = 'video/' + finals[name] if row else ''
        if output:
            assert (ROOT / output).is_file(), output
        statuses.append(dict(asset_key=key, source=resource['extracted_path'], source_state='present',
            retained_output=output, production_state='produced' if row else 'not-started',
            qa_scope=row['validation_scope'] if row else 'not-evaluated',
            installation_state='installed-local-test' if installed else 'not-installed',
            ingame_qa='pending-user' if installed else 'not-performed', release_state='not-integrated'))
    with (VIDEO / 'index/status.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(statuses[0]), lineterminator='\n'); writer.writeheader(); writer.writerows(statuses)
    media = [x for x in plan['retained'] if Path(x['path']).suffix.lower() in
             {'.wbm', '.webm', '.mp4', '.mov', '.mkv', '.m4a', '.png', '.jpg', '.jpeg'}]
    for item in media:
        p = ROOT / item['path']; assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256']
    retained = dict(schema='video-retained-media-v1', date='2026-11-10',
        cleanup='pipeline/recipes/video-retained-cleanup-20261110-v1/cleanup.json',
        source_count=50, selected_outputs={k: 'video/' + v for k, v in finals.items()},
        pocketzz_status='candidate only; user keeps this file, not a QA acceptance',
        relocated_dependencies=plan['relocated_dependencies'], files=media)
    (VIDEO / 'index/retained-media-20261110-v1.json').write_text(json.dumps(retained, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    # Only retained, browser-playable endpoints and actual intermediate inputs.
    sources = [dict(name=f'{a} — source originale · 720p15', url=f'../{a.lower()}/source-preview-720p15.mp4', fps=15)
               for a in ['DAYNITE', 'REST', 'RESTINN', 'RESTDUNG']]
    results = []
    def add(name, path, fps):
        assert (VIDEO / path).is_file(), path
        results.append(dict(name=name, url='../'+path, fps=fps))
    add('DAYNITE — NEAREST + Apollo8 retenu · 1080p30 · son original', finals['DAYNITE'], 30)
    add('DAYNITE — NEAREST étape conservée · 1080p24 · son original',
        'daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/DAYNITE-H3-01604-NEAREST-1080p24-son-original-v1.mp4', 24)
    add('DAYNITE — montage H3 avant upscale · 24 fps',
        'daynite/runs/daynite-minimax-h3-01604-fades-20261110-v1/DAYNITE-H3-01604-fondus-corriges-24fps-10s-v1.mp4', 24)
    for name in ['REST', 'RESTINN', 'RESTDUNG']:
        add(f'{name} — SeedVR2 + Apollo8 retenu · 1080p30', finals[name], 30)
        path = ('restdung/runs/restdung-seedvr-reference-20261109-v1/SeedVR2-RESTDUNG-3B-FP16-LAB-1080p15.mp4'
                if name == 'RESTDUNG' else f'{name.lower()}/runs/{name.lower()}-seedvr-apollo-20261109-v1/{name}-SeedVR2-3B-FP16-LAB-1080p15.mp4')
        add(f'{name} — SeedVR2 étape conservée · 1080p15', path, 15)
    for item in sources:
        assert (VIDEO / 'tools' / item['url']).resolve().is_file(), item
    html = VIDEO / 'tools/comparator.html'; text = html.read_text(encoding='utf-8')
    old_marker = "const base='../restdung/runs/';"
    current_marker = '// Retained results and actual inputs; cleanup2026-11-10.'
    start = text.index(old_marker if old_marker in text else current_marker)
    end = text.index('let loopStart=0')
    catalogue = ('// Retained results and actual inputs; cleanup2026-11-10.\n'
        'const sourceItems='+json.dumps(sources, ensure_ascii=False, indent=1)+';\n'
        'const resultItems='+json.dumps(results, ensure_ascii=False, indent=1)+';\n'
        'sourceItems.push(...resultItems.map(item=>({...item})));\n')
    html.write_text(text[:start]+catalogue+text[end:], encoding='utf-8')
    check = HERE / 'comparator-check.js'
    check.write_text('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', html.read_text(encoding='utf-8'), re.S)), encoding='utf-8')
    subprocess.run(['node', '--check', str(check)], check=True)
    check.unlink()
    print(json.dumps(dict(sources=50, processing_rows=len(rows), status_rows=len(statuses),
        selected_outputs=len(finals), comparator_sources=len(sources), comparator_results=len(results),
        retained_media=len(media), removed_files=cleanup['removed_files'], removed_bytes=cleanup['removed_bytes'])))


if __name__ == '__main__':
    main()
