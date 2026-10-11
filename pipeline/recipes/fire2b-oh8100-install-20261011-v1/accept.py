"""Close FIRE_2B QA: explicit OH8100 approval + unchanged AR3017 approval."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('installer', Path(__file__).with_name('install.py'))
i = importlib.util.module_from_spec(spec)
spec.loader.exec_module(i)
w, v, h, ROOT = i.workflow, i.v, i.h, i.ROOT
RUN = i.SOURCE.parent
TAG = 'fire2b-two-maps-validation-20261011-v1'
PACK = ROOT / 'animations/packs-par-zone' / TAG


def accept():
    _, selected = v.validate_v2_pack(i.SOURCE)
    assert len(selected) == 1 and selected[0]['resref'] == 'FIRE_2B'
    target = selected[0]
    record = v.resource_binary_v2(target, 3)
    proofs = {}
    for area in ['AR3017', 'OH8100']:
        live = i.LIVE.parent / area
        assert (live / v.REGISTRY_NAME).read_bytes().count(record) == 1
        assert all(h.sha(live / a['name']) == a['sha256'] for a in target['assets'])
        proofs[area] = dict(frame_hashes_identical=True, runtime_record_identical=True,
            registry_sha256=h.sha(live / v.REGISTRY_NAME))
    assert h.payload(i.LIVE) == v.load_json(i.RECIPE / 'baseline.json')['after']
    assert not PACK.exists(), 'Immutable QA output exists'
    for area in proofs:
        h.pack(PACK / area, selected, lambda r: i.SOURCE, area)
    h.write(PACK / 'manifest.json', dict(schema='bg2-upscale-area-animation-pack-index-v1', status='completed',
        created_utc=v.utc_now(), scope='FIRE_2B only; exact installed resource bytes and runtime record in both areas',
        areas=[dict(area_id=area, directory=area, manifest_sha256=h.sha(PACK / area / 'manifest.json'),
                    registry_sha256=h.sha(PACK / area / v.REGISTRY_NAME)) for area in proofs]))
    result = w.finalize(ROOT, 'FIRE_2B', RUN, PACK, list(proofs), 'accepted', '2026-10-11',
        'Utilisateur : ok valide. MAJ le suivi et committe. FIRE_2B accepte sur OH8100 apres installation du traitement deja accepte sur AR3017 le 2026-09-17. '
        '30 frames/30fps, alpha luminance0-16, fondu canvas8px x4, RGB premultiplie. Les deux occurrences de map utilisent exactement les memes octets et le meme contrat runtime ; validation globale acquise.',
        decision_id='2026-10-11-accepted-fire2b-ar3017-oh8100-v1', recipe_id=i.TAG,
        notes='QA ingame utilisateur acceptee AR3017 (2026-09-17) et OH8100 (2026-10-11), octets et contrat identiques verifies. '
        'Traitement luminance0-16, canvas fade8px x4, RGB premultiplie ; 30frames/30fps, dimensions70x70 et centre35,35 natifs. '
        'Installation OH8100 pipeline/recipes/'+i.TAG+'/installation.json ; autres assets et maps conserves. Aucune integration release.', apply=True)
    errors = []
    decision = ROOT / 'animations/index/qa-decisions/FIRE_2B/2026-10-11-accepted-fire2b-ar3017-oh8100-v1.json'
    w._validate_decision_record(ROOT, decision, 'FIRE_2B', errors)
    assert not errors, errors
    h.write(i.RECIPE / 'acceptance.json', dict(status='accepted', resref='FIRE_2B', tested_areas=list(proofs),
        proof=proofs, decision=h.rel(decision), qa_pack=h.rel(PACK), installation=h.rel(i.RECIPE / 'installation.json'),
        qa_origin='explicit user OH8100 approval; prior AR3017 approval retained on identical bytes and runtime contract',
        documentation_only=True, game_files_changed=False, release_changed=False))
    print('FIRE_2B globally validated: AR3017 + OH8100; decision checks passed')


if __name__ == '__main__':
    accept()
