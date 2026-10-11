"""Explicit batch approval on nine maps; retain unchanged AR0411 QA; close all three assets."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('batch', Path(__file__).with_name('build.py'))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
ROOT, h, v, w = b.ROOT, b.h, b.v, b.workflow
TAG = 'dstdvl1abc-all-maps-accepted-20261011-v1'
RUN = ROOT / 'animations/batches' / TAG
PACK = ROOT / 'animations/packs-par-zone' / TAG
AREAS = ['AR0411'] + b.AREAS


def accept():
    assert not RUN.exists() and not PACK.exists(), 'Immutable final output exists'
    baseline = v.load_json(b.RECIPE / 'baseline.json')
    assert h.payload(b.LIVE / 'AR0411') == baseline['protected_AR0411']
    entries = []; proofs = {}
    for area in AREAS:
        source = b.APPROVED if area == 'AR0411' else b.PACK / area
        _, resources = v.validate_v2_pack(source)
        targets = [r for r in resources if r['resref'] in b.TARGETS]
        assert len(targets) == 3
        live = b.LIVE / area
        if area != 'AR0411':
            assert h.payload(live) == baseline['areas'][area]['after']
        for resource in targets:
            assert (live / v.REGISTRY_NAME).read_bytes().count(v.resource_binary_v2(resource, 3)) == 1
            assert all(h.sha(live / a['name']) == a['sha256'] for a in resource['assets'])
        # QA snapshots contain only the selected clouds; game payload is not modified.
        h.pack(PACK / area, targets, lambda r: source, area)
        entries.append(dict(area_id=area, directory=area, manifest_sha256=h.sha(PACK / area / 'manifest.json'),
            registry_sha256=h.sha(PACK / area / v.REGISTRY_NAME)))
        proofs[area] = dict(source=h.rel(source), source_manifest_sha256=h.sha(source / 'manifest.json'),
            installed_frame_hashes_and_runtime_records_identical=True,
            QA_origin='prior explicit AR0411 approval retained' if area == 'AR0411' else 'explicit user approval of nine-map batch')
    h.write(PACK / 'manifest.json', dict(schema='bg2-upscale-area-animation-pack-index-v1', status='completed',
        created_utc=v.utc_now(), scope='QA snapshots of DSTDVL1A/B/C only; installed area versions preserved', areas=entries))
    h.write(RUN / 'manifest.json', dict(schema='bg2-upscale-animation-final-selection-v1', status='completed',
        created_utc=v.utc_now(), resrefs=b.TARGETS, source_run=h.rel(b.RUN), source_run_manifest_sha256=h.sha(b.RUN / 'manifest.json'),
        source_pack=h.rel(b.APPROVED), source_pack_manifest_sha256=h.sha(b.APPROVED / 'manifest.json'),
        output_split_root=h.rel(PACK), output_manifest_sha256=h.sha(PACK / 'manifest.json'),
        visual_treatment=dict(inner_feather_x4=20, gaussian_sigma_x4=4, premultiplied_RGBA=True,
            core_native_geometry_and_each_area_timing_preserved=True), QA='explicit user batch approval; AR0411 prior QA retained',
        installed_area_proofs=proofs, game_files_modified=False, release_modified=False))
    for name in b.TARGETS:
        w.finalize(ROOT, name, RUN, PACK, AREAS, 'accepted', '2026-10-11',
            'Utilisateur : valide ! Maj le suivi et committe. '+name+' accepte pour le lot de neuf maps AR0414/AR1100/AR1200/AR1600/AR1700/AR5200/AR5500/AR6300/OH6400. '
            'Validation AR0411 anterieure conservee sur les memes octets et contrat runtime. Contours brumeux fondu interne20px x4 + Gaussian sigma4 ; coeur, centres, dimensions, timelines et variantes temporelles de chaque map preserves. Validation globale des dix maps.',
            decision_id='2026-10-11-accepted-'+name.lower()+'-all-maps-misty-v1', recipe_id=b.TAG,
            notes='QA ingame utilisateur acceptee sur les dix maps le 2026-10-11 : lot neuf maps accepte, QA AR0411 anterieure conservee. '
            'Fondu20px x4 + Gaussian sigma4 en bordure sur RGBA premultiplie ; coeur, dimensions/centres, version temporelle139/50frames et cadence preserves. '
            'Installation pipeline/recipes/'+b.TAG+'/installation.json ; autres assets et registres inchanges. Aucune integration release.', apply=True)
        errors = []
        decision = ROOT / 'animations/index/qa-decisions' / name / ('2026-10-11-accepted-'+name.lower()+'-all-maps-misty-v1.json')
        w._validate_decision_record(ROOT, decision, name, errors)
        assert not errors, errors
    h.write(b.RECIPE / 'acceptance.json', dict(status='accepted', resrefs=b.TARGETS, tested_areas=AREAS,
        installed_area_proofs=proofs, final_run=h.rel(RUN), qa_pack=h.rel(PACK), game_files_changed=False, release_changed=False))
    print('DSTDVL1A/B/C globally accepted on all ten maps; decision checks passed')


if __name__ == '__main__':
    accept()
