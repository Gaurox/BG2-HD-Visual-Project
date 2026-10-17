"""Compare unchanged SDF and inward distance offsets of one/two x4 pixels."""
from pathlib import Path
import importlib.util
import json
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'effects/batches/lot8-sdf-ankheg-preview-20261017-v1'
OUT = ROOT / 'effects/batches/lot8-sdf-inset-preview-20261017-v1'
REVIEW = OUT / 'review'
spec = importlib.util.spec_from_file_location('sdf_reference_preview', ROOT / 'pipeline/recipes/effects-lot8-sdf-ankheg-preview-20261017-v1/preview.py')
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)
load, digest = ref.load, ref.digest
OFFSETS = {'current': 0, 'inset1': 1, 'inset2': 2}


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def candidates(rgba, cache):
    alpha = rgba[:, :, 3]
    mask = alpha > 0
    if not mask.any():
        return {k: rgba.copy() for k in OFFSETS}, {'empty_source': True}
    coarse = alpha[::2, ::2] > 0
    assert np.array_equal(np.repeat(np.repeat(alpha[::2, ::2], 2, 0), 2, 1), alpha)
    key = (coarse.shape, digest(coarse.tobytes()))
    if key not in cache:
        field, topology = ref.ankheg.reconstruct(np.where(coarse, 3, 0).astype(np.uint8))
        q = np.clip(np.rint(field * 16), -64, 63)
        q[(q == 0) & (field > 0)] = 1
        q[(q == 0) & (field < 0)] = -1
        # Positive-inside SDF in x2 units: subtract x4_inset/2 before integrating.
        coverage = {k: ref.ankheg.sdf_alpha(q / 16 - offset / 2, zoom=2, samples=8)[12:-12, 12:-12]
                    for k, offset in OFFSETS.items()}
        assert np.all(coverage['inset2'] <= coverage['inset1'])
        assert np.all(coverage['inset1'] <= coverage['current'])
        cache[key] = coverage
    coverage = cache[key]
    nearest = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
    envelope = alpha[nearest[0], nearest[1]]
    alphas = {k: np.rint(v * envelope).astype(np.uint8) for k, v in coverage.items()}
    colour = rgba.copy()
    added = (alphas['current'] > 0) & ~mask
    colour[:, :, :3][added] = rgba[nearest[0][added], nearest[1][added], :3]
    outputs = {}
    labels, components = ndimage.label(alphas['current'] > 0, structure=np.ones((3, 3)))
    checks = {'empty_source': False, 'offsets': {}}
    for k in OFFSETS:
        out = colour.copy()
        out[:, :, 3] = alphas[k]
        outputs[k] = out
        assert np.array_equal(out[:, :, :3], colour[:, :, :3])
        masses = np.bincount(labels.ravel(), weights=alphas[k].ravel(), minlength=components + 1)
        checks['offsets'][k] = {
            'mass_ratio_to_current_sdf': float(alphas[k].sum()) / float(alphas['current'].sum()) if alphas['current'].any() else 1.0,
            'empty_after_inset': bool(not alphas[k].any()),
            'lost_current_sdf_components': int(np.count_nonzero(masses[1:] == 0)),
            'changed_alpha_pixels': int(np.count_nonzero(alphas[k] != alphas['current'])),
            'rgba_sha256': digest(out.tobytes())}
    assert np.all(alphas['inset2'] <= alphas['inset1']) and np.all(alphas['inset1'] <= alphas['current'])
    return outputs, checks


def asset(a):
    n = a['resref']
    if (OUT / 'assets' / f'{n}.json').exists():
        return load(OUT / 'assets' / f'{n}.json')
    original = load(BASE / 'assets' / f'{n}.json')
    hashes = {f['frame']: f['candidate_rgba_sha256'] for f in original['frames']}
    stage = ROOT / 'effects/ressources' / n / 'runs' / a['interpolation_run'] / '02-interpolation'
    m = load(stage / 'manifest.json')
    s = load(ROOT / m['parent']['spatial_manifest'])
    cw, ch = s['aligned_canvas_size_x1']
    cache, rows, profiles = {}, [], []
    best, poster = -1, None
    for profile in m['timing']['cycles']:
        images = {k: [] for k in OFFSETS}
        for idx in profile['timeline_frame_indices']:
            f = m['frames'][idx]
            source = ref.frame(stage, f)
            out, checks = candidates(source, cache)
            assert digest(out['current'].tobytes()) == hashes[idx], (n, idx, 'baseline changed')
            l, t, r, b = f['runtime_crop_box_x4']
            for k, pixels in out.items():
                image = Image.new('RGBA', (cw * 4, ch * 4), (0, 0, 0, 0))
                image.paste(Image.fromarray(pixels), (l, t))
                images[k].append(image)
            rows.append({'frame': idx, 'cycle': f['cycle'], 'mode': f['mode'],
                         'baseline_sha256_exact': True, 'geometry_and_timing_unchanged': True, **checks})
            score = float(source[:, :, 3].sum())
            if score > best:
                best = score
                poster = {k: v[-1].copy() for k, v in images.items()}
        name = n + '-' + profile['id']
        ms = ref.durations(profile['phase_durations_rational'])
        for k in images:
            ref.animated(REVIEW / k / (name + '.webp'), images[k], ms)
        profiles.append({'name': name, 'id': profile['id'], 'phases': len(ms), 'duration': profile['duration_seconds']})
    posters = REVIEW / 'posters'
    posters.mkdir(parents=True, exist_ok=True)
    for k, image in poster.items():
        image.save(posters / f'{n}-{k}.png')
    delta = np.abs(np.asarray(poster['current'])[:, :, 3].astype(float) - np.asarray(poster['inset2'])[:, :, 3])
    cy, cx = np.unravel_index(ndimage.gaussian_filter(delta, 6).argmax(), delta.shape)
    sheet = Image.new('RGB', (720, 510), (24, 28, 36))
    draw = ImageDraw.Draw(sheet)
    for col, (k, offset) in enumerate(OFFSETS.items()):
        crop = poster[k].crop((cx - 28, cy - 28, cx + 28, cy + 28)).resize((224, 224), Image.Resampling.NEAREST)
        bg = Image.new('RGBA', crop.size, (110, 94, 70, 255))
        sheet.paste(Image.alpha_composite(bg, crop).convert('RGB'), (col * 240, 30))
        sheet.paste(crop.getchannel('A').convert('RGB'), (col * 240, 270))
        draw.text((col * 240 + 4, 8), ['SDF actuel', 'Retrait 1 pixel x4', 'Retrait 2 pixels x4'][col], fill='white')
    sheet.save(posters / f'{n}-detail.png')
    summary = {}
    visible = [f for f in rows if not f['empty_source']]
    for k in OFFSETS:
        summary[k] = {'mean_mass_retained': float(np.mean([f['offsets'][k]['mass_ratio_to_current_sdf'] for f in visible])),
                      'empty_phases': sum(f['offsets'][k]['empty_after_inset'] for f in visible),
                      'lost_component_occurrences': sum(f['offsets'][k]['lost_current_sdf_components'] for f in visible)}
    report = {'resref': n, 'ordinal': a['ordinal'], 'phases': len(rows), 'profiles': profiles,
              'frames': rows, 'summary': summary, 'source': ref.evidence(stage / 'manifest.json'),
              'baseline_sdf_preview': ref.evidence(BASE / 'assets' / f'{n}.json'),
              'preview_only': True, 'production_authorities_changed': False}
    save(OUT / 'assets' / f'{n}.json', report)
    print(n, 'inset comparisons', len(rows), 'phases;', summary, flush=True)
    return report


def gallery(reports):
    cards = []
    for a in reports:
        n = a['resref']
        options = ''.join(f'<option value="{p["name"]}">{p["id"]} — {p["phases"]} phases, {p["duration"]:.3f} s</option>' for p in a['profiles'])
        panels = ''.join(f'<figure><figcaption>{label}</figcaption><img data-mode="{k}" src="posters/{n}-{k}.png"></figure>'
                         for k, label in [('current', 'SDF actuel'), ('inset1', 'Retrait 1 pixel x4'), ('inset2', 'Retrait 2 pixels x4')])
        cards.append(f'<article><h2>{a["ordinal"]:02d} · {n}</h2><select onchange="cycle(this)">{options}</select><div class="row">{panels}</div><details><summary>Gros plan et masques alpha</summary><img class="detail" src="posters/{n}-detail.png"></details></article>')
    page = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Effets — SDF resserré</title><style>
body{margin:20px;background:#10151e;color:#eee;font:15px system-ui}header{position:sticky;top:0;background:#10151ef5;padding:8px;z-index:2}button,select{background:#29374b;color:white;padding:8px;border:1px solid #667}article{background:#1c2532;padding:14px;margin:16px 0}h2{font-size:19px}.row{display:flex;gap:12px;flex-wrap:wrap;overflow:auto}figure{margin:8px 0}figcaption{margin:8px 0}figure img{max-width:340px;max-height:340px;object-fit:contain;image-rendering:pixelated;background:var(--bg,#6e5e46)}.exact figure img{max-width:none;max-height:none}.detail{max-width:100%}details{margin-top:12px}</style>
<header><h1>SDF — retrait intérieur du masque</h1><p>Comparaison du SDF actuel avec des retraits de 1 et 2 pixels x4 (0,25 et 0,5 pixel natif). Couleurs et durées identiques. Le retrait est un décalage du champ de distance, sans fondu supplémentaire. Observer les détails fins, surtout la lance.</p><button onclick="toggle()" id="play">Lecture</button> <button onclick="document.body.classList.toggle('exact')">Taille réelle x4 / aperçu</button> Fond : <select onchange="document.body.style.setProperty('--bg',this.value)"><option value="#6e5e46">Brun</option><option value="#000">Noir</option><option value="#ddd">Clair</option></select></header>CARDS
<script>let playing=false;function cycle(s){let a=s.closest('article');if(playing)a.querySelectorAll('figure img').forEach(i=>i.src=i.dataset.mode+'/'+s.value+'.webp')}function toggle(){playing=!playing;document.querySelectorAll('article').forEach(a=>{if(playing)cycle(a.querySelector('select'));else a.querySelectorAll('figure img').forEach(i=>{let c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;c.getContext('2d').drawImage(i,0,0);i.src=c.toDataURL()})});document.getElementById('play').textContent=playing?'Pause':'Lecture'}</script></html>'''
    (REVIEW / 'index.html').write_text(page.replace('CARDS', ''.join(cards)), encoding='utf-8')


def main():
    assert not (OUT / 'result.json').exists(), 'Completed comparison is immutable'
    reports = []
    for a in load(ref.PARENT / 'batch.json')['assets']:
        if a['resref'] in ref.NAMES:
            reports.append(asset(a))
            gallery(reports)
    assert len(reports) == 8 and sum(a['phases'] for a in reports) == 404
    save(OUT / 'result.json', {'schema': 'effects-sdf-inset-preview-v1', 'count': 8, 'phases_per_variant': 404,
         'offsets_x4': OFFSETS, 'formula': 'coverage = area8x8(bilinear(SDF_x2 - inset_x4/2) > 0)',
         'baseline_preview': ref.evidence(BASE / 'result.json'), 'reference_recipe': ref.evidence(ref.REFERENCE),
         'assets': reports, 'preview_only': True, 'neural_inference_runs': 0,
         'production_authorities_changed': False, 'installed': False})


if __name__ == '__main__':
    main()
