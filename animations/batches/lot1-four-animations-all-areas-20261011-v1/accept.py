"""Seal the user's complete lot-1 in-game approval; no runtime/release writes."""
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BATCH = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import animation_workflow as workflow
import area_pack_state as state
from animation_authority_lock import animation_authority_lock

RECIPES = {
    'AM5204C': ('am5204c-reboutcx-apo8-x4-30fps-v2-20260922',
                'am5204c-reboutcx-apo8-x4-30fps-v2-aura16-20260922',
                'contour-aura16-sigma5-gain0p9-margin14-premultiply', 'tas de braises'),
    'AM5204D': ('am5204d-seedvr7b-apo8-x4-30fps-v2-20260922',
                'am5204d-seedvr7b-apo8-x4-30fps-v2-innerfeather16-premul-20260922',
                'innerfeather16-premultiply', 'grande flamme'),
    'AM5508C': ('am5508c-reboutcx-apo8-x4-30fps-v2-20260922',
                'am5508c-reboutcx-apo8-x4-30fps-v2-innerfeather16-premul-20260922',
                'innerfeather16-premultiply', 'lumiere verticale'),
    'AM5508D': ('am5508d-reboutcx-apo8-x4-30fps-v2-20260922',
                'am5508d-reboutcx-apo8-x4-30fps-v2-innerfeather16-premul-20260922',
                'innerfeather16-premultiply', 'croissant orange'),
}


def write_new(path, value):
    assert not path.exists(), f'Historical artifact already present: {path}'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    production = json.loads((BATCH / 'manifest.json').read_text(encoding='utf-8'))
    installation = json.loads((BATCH / 'installation.json').read_text(encoding='utf-8'))
    assert installation['status'] == 'completed'
    split_root = ROOT / 'animations/packs-par-zone' / BATCH.name
    areas = []
    for item in production['areas']:
        leaf = ROOT / item['pack']
        assert state.zone_signatures(state.game_areas_dir() / item['area']) == item['expected']
        manifest = json.loads((leaf / 'manifest.json').read_text(encoding='utf-8'))
        assert state.sha256_file(leaf / 'manifest.json') == item['manifest_sha256']
        assert state.sha256_file(state.game_areas_dir() / item['area'] / manifest['registry']) == manifest['registry_sha256']
        areas.append({'area_id': item['area'], 'directory': leaf.relative_to(split_root).as_posix(),
                      'resrefs': sorted({r['resref'] for r in manifest['resources']}),
                      'resource_count': manifest['resource_count'], 'frame_count': manifest['frame_count'],
                      'raw_bytes': manifest['raw_bytes'], 'registry_sha256': manifest['registry_sha256'],
                      'manifest_sha256': state.sha256_file(leaf / 'manifest.json'), 'over_runtime_budget': False})
    write_new(split_root / 'manifest.json', {
        'schema': 'bg2-upscale-area-animation-pack-index-v1', 'status': 'completed',
        'created_utc': state.utc_now(), 'runtime_budget_bytes': 536870912,
        'area_count': len(areas), 'largest_area_raw_bytes': max(x['raw_bytes'] for x in areas),
        'total_raw_bytes': sum(x['raw_bytes'] for x in areas), 'areas_over_budget': [],
        'resrefs_without_area': [], 'areas': areas,
        'provenance': state.rel(BATCH / 'manifest.json'),
    })
    arguments = []
    for resref, (temporal_id, pack_id, correction_id, element) in RECIPES.items():
        tested = sorted(item['area'] for item in production['areas'] if resref in item['lot_resources'])
        source_run = ROOT / 'animations/ressources' / resref / 'runs' / temporal_id
        source_pack = ROOT / 'animations/packs-par-zone' / pack_id / tested[0]
        selected = ROOT / 'animations/ressources' / resref / 'runs' / (resref.lower() + '-lot1-selection-accepted-20261011-v1')
        write_new(selected / 'manifest.json', {
            'schema': 'bg2-upscale-animation-final-selection-v1', 'status': 'completed',
            'created_utc': state.utc_now(), 'resrefs': [resref],
            'source_run': state.rel(source_run), 'source_run_manifest_sha256': state.sha256_file(source_run / 'manifest.json'),
            'source_pack': state.rel(source_pack), 'source_pack_manifest_sha256': state.sha256_file(source_pack / 'manifest.json'),
            'output_split_root': state.rel(split_root), 'output_manifest_sha256': state.sha256_file(split_root / 'manifest.json'),
            'selection_reason': 'Utilisateur : c est bon. tout est verifie et valide. maj le suivi et committe.',
            'tested_areas': tested, 'correction_id': correction_id,
            'installation_receipt': state.rel(BATCH / 'installation.json'),
        })
        arguments.append(dict(
            workspace_root=ROOT, raw_resref=resref, final_run=selected, qa_pack=split_root,
            areas=tested, decision_status='accepted', decision_date='2026-10-11',
            decision_text='Utilisateur : c est bon. tout est verifie et valide. maj le suivi et committe. '
                          + resref + ' accepte en jeu sur toutes ses zones : ' + ', '.join(tested) + '. '
                          'Production x4/30fps de septembre reutilisee sans changement des octets ; installation complete le 2026-10-11.',
            decision_id='2026-10-11-accepted-' + resref.lower() + '-lot1-all-maps-v1',
            recipe_id=resref.lower() + '-lot1-' + correction_id,
            correction_id=correction_id,
            notes=element + ' ; x4/30fps, ' + correction_id + '. QA utilisateur acceptee le 2026-10-11 sur toutes les zones : '
                  + ';'.join(tested) + '. Reprise/recus : ' + state.rel(BATCH) + '. Historique conserve ; aucune integration release.',
        ))
    for argument in arguments:
        workflow.finalize(**argument, apply=False)
    results = []
    for argument in arguments:
        results.append(workflow.finalize(**argument, apply=True))
        print(argument['raw_resref'], 'accepted:', ','.join(argument['areas']), flush=True)
    with animation_authority_lock(ROOT):
        path = ROOT / 'animations/index/animation_alpha_corrections.csv'
        original = path.read_bytes()
        rows = list(csv.DictReader(io.StringIO(original.decode('utf-8-sig'))))
        fields = list(rows[0])
        assert not any(row['resref'] in RECIPES for row in rows)
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator='\r\n' if b'\r\n' in original else '\n')
        for argument in arguments:
            resref = argument['raw_resref']; aura = resref == 'AM5204C'
            writer.writerow({
                'resref': resref, 'areas': ';'.join(argument['areas']), 'element': RECIPES[resref][3],
                'correction_id': argument['correction_id'],
                'alpha_operations': 'inner-distance-feather;contour-aura-sigma5-gain0p9-margin14' if aura else 'inner-distance-feather',
                'inner_radius_x4': '16', 'canvas_radius_x4': '0', 'canvas_edges': 'none',
                'rgb_policy': 'nearest-opaque-for-aura-then-premultiplied-by-final-alpha' if aura else 'premultiplied-by-final-alpha',
                'status': 'validated-installed', 'validated_date': '2026-10-11',
                'prototype': state.rel(argument['final_run']),
                'notes': argument['notes'],
            })
        assert original.endswith(b'\n')
        temporary = path.with_suffix('.csv.part')
        temporary.write_bytes(original + output.getvalue().encode('utf-8'))
        temporary.replace(path)
    finish(results)


def finish(results=None):
    if results is None:
        results = []
        for resref in RECIPES:
            selected = json.loads((ROOT / 'animations/index/selections' / (resref + '.json')).read_text(encoding='utf-8'))
            results.append({'resref': resref, 'qa_decision': selected['qa_decision'],
                            'selected_run': selected['selected_run'], 'tested_areas': selected['tested_areas']})
    checks = []
    for resref in RECIPES:
        result = workflow.check_workspace(ROOT, resref)
        assert not result['errors'], result
        checks.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    write_new(BATCH / 'acceptance.json', {'status': 'accepted', 'qa_date': '2026-10-11',
                                         'scope': '4 assets / 8 areas / 40 occurrences',
                                         'results': results, 'checks': checks, 'release_mutation': False})


if __name__ == '__main__':
    finish() if '--finish' in sys.argv else main()
