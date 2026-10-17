"""Offline comparison of the validated Ankheg SDF formula on eight effects.

Read-only production inputs. No run registration, pack, shader or installation.
"""
from pathlib import Path
from fractions import Fraction
import hashlib
import importlib.util
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'effects/batches/lot8-sdf-ankheg-preview-20261017-v1'
REVIEW = OUT / 'review'
PARENT = ROOT / 'effects/batches/lot26-seedvr7b-apollo30-20261017-v2'
SPLINE = ROOT / 'effects/batches/lot26-seedvr7b-apollo30-20261017-v3'
REFERENCE = ROOT / 'docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py'
spec = importlib.util.spec_from_file_location('validated_ankheg_sdf', REFERENCE)
ankheg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ankheg)
NAMES = set('SPHEART SPHANDAT SPRAISED GLPHWRDT SKLT SPTRAPBB TRAPGR TRSPEART'.split())
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
digest = lambda raw: hashlib.sha256(raw).hexdigest().upper()
rel = lambda p: p.relative_to(ROOT).as_posix()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def evidence(p):
    return {'path': rel(p), 'sha256': digest(p.read_bytes()), 'bytes': p.stat().st_size}


def durations(values):
    out, elapsed, before = [], Fraction(0), 0
    for pair in values:
        elapsed += Fraction(*pair)
        end = round(elapsed * 1000)
        out.append(end - before)
        before = end
    return out


def smooth_rgba(rgba, cache):
    h, w = rgba.shape[:2]
    alpha = rgba[:, :, 3]
    mask = alpha > 0
    if not mask.any():
        return rgba.copy(), {'empty': True, 'added_pixels': 0}
    # These effects retain native nearest x4 coverage: every 2x2 block is equal.
    coarse_alpha = alpha[::2, ::2]
    assert np.array_equal(np.repeat(np.repeat(coarse_alpha, 2, 0), 2, 1), alpha)
    coarse = coarse_alpha > 0
    key = (coarse.shape, digest(coarse.tobytes()))
    if key not in cache:
        indices = np.where(coarse, 3, 0).astype(np.uint8)
        field, topology = ankheg.reconstruct(indices)
        # Same V9 distance quantization, in the validated x2 coordinate system.
        q = np.clip(np.rint(field * 16), -64, 63)
        q[(q == 0) & (field > 0)] = 1
        q[(q == 0) & (field < 0)] = -1
        coverage = ankheg.sdf_alpha(q / 16, zoom=2, samples=8)[12:-12, 12:-12]
        assert coverage.shape == alpha.shape
        assert topology['solid_components_before'] == topology['solid_components_after']
        assert topology['background_components_before'] == topology['background_components_after']
        cache[key] = coverage, topology
    coverage, topology = cache[key]
    nearest = ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)
    envelope = alpha[nearest[0], nearest[1]]
    result = rgba.copy()
    result[:, :, 3] = np.rint(coverage * envelope).astype(np.uint8)
    added = (result[:, :, 3] > 0) & ~mask
    # Newly covered pixels receive existing neighbouring foreground RGB.
    result[:, :, :3][added] = rgba[nearest[0][added], nearest[1][added], :3]
    assert np.array_equal(result[:, :, :3][mask], rgba[:, :, :3][mask])
    outside = ndimage.distance_transform_edt(~mask)
    maximum = float(outside[added].max()) if added.any() else 0.0
    assert maximum <= 4, maximum
    return result, {'empty': False, 'topology': topology,
                    'added_pixels': int(added.sum()), 'max_added_distance_x4': maximum,
                    'changed_alpha_pixels': int(np.count_nonzero(result[:, :, 3] != alpha)),
                    'alpha_mass_ratio': float(result[:, :, 3].sum()) / float(alpha.sum()),
                    'existing_foreground_rgb_identical': True}


def animated(p, frames, ms):
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        frames[0].save(p, save_all=True, append_images=frames[1:], duration=ms,
                       loop=0, lossless=True, method=2)


def frame(stage, f):
    w, h = f['physical_size_x4']
    raw = (stage / f['straight_raw_rgba_x4']).read_bytes()
    assert digest(raw) == f['straight_raw_rgba_x4_sha256']
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4)


def asset(a, spline_asset):
    n = a['resref']
    stage = ROOT / 'effects/ressources' / n / 'runs' / a['interpolation_run'] / '02-interpolation'
    spline_stage = ROOT / 'effects/ressources' / n / 'runs' / spline_asset['interpolation_run'] / '02-interpolation'
    m, fitted = load(stage / 'manifest.json'), load(spline_stage / 'manifest.json')
    assert m['timing'] == fitted['timing']
    spatial = load(ROOT / m['parent']['spatial_manifest'])
    cw, ch = spatial['aligned_canvas_size_x1']
    report_path = OUT / 'assets' / f'{n}.json'
    if report_path.exists():
        return load(report_path)
    cache, records, profiles = {}, [], []
    best_score, sample = -1, None
    for profile in m['timing']['cycles']:
        images = {key: [] for key in ('native', 'spline', 'sdf')}
        for i in profile['timeline_frame_indices']:
            f = m['frames'][i]
            source, fitted_pixels = frame(stage, f), frame(spline_stage, fitted['frames'][i])
            candidate, checks = smooth_rgba(source, cache)
            for key, pixels in [('native', source), ('spline', fitted_pixels), ('sdf', candidate)]:
                image = Image.new('RGBA', (cw * 4, ch * 4), (0, 0, 0, 0))
                l, t, r, b = f['runtime_crop_box_x4']
                image.paste(Image.fromarray(pixels), (l, t))
                images[key].append(image)
            records.append({'frame': i, 'cycle': f['cycle'], 'mode': f['mode'],
                            'source_sha256': f['straight_raw_rgba_x4_sha256'],
                            'candidate_rgba_sha256': digest(candidate.tobytes()),
                            'geometry_and_temporal_sources_unchanged': True, **checks})
            score = float(source[:, :, 3].sum())
            if score > best_score:
                best_score = score
                sample = {key: value[-1].copy() for key, value in images.items()}
        name = n + '-' + profile['id']
        ms = durations(profile['phase_durations_rational'])
        for key in images:
            animated(REVIEW / key / (name + '.webp'), images[key], ms)
        profiles.append({'id': profile['id'], 'phases': len(ms),
                         'duration': profile['duration_seconds'], 'name': name})
    for key, im in sample.items():
        p = REVIEW / 'posters' / (n + '-' + key + '.png')
        p.parent.mkdir(parents=True, exist_ok=True)
        im.save(p)
    # One transparent-pixel zoom over the most changed rim, plus alpha-only views.
    before = np.asarray(sample['native'])
    after = np.asarray(sample['sdf'])
    delta = ndimage.gaussian_filter(np.abs(after[:, :, 3].astype(float) - before[:, :, 3]), 6)
    cy, cx = np.unravel_index(delta.argmax(), delta.shape)
    half = 28
    zoom = Image.new('RGB', (3 * 240, 2 * 240 + 30), (24, 28, 36))
    draw = ImageDraw.Draw(zoom)
    for col, key in enumerate(('native', 'spline', 'sdf')):
        detail = sample[key].crop((cx - half, cy - half, cx + half, cy + half)).resize((224, 224), Image.Resampling.NEAREST)
        bg = Image.new('RGBA', detail.size, (110, 94, 70, 255))
        zoom.paste(Image.alpha_composite(bg, detail).convert('RGB'), (col * 240, 30))
        zoom.paste(detail.getchannel('A').convert('RGB'), (col * 240, 270))
        draw.text((col * 240 + 4, 8), ['Masque actuel', 'SplineFit1', 'SDF Ankheg adapte'][col], fill='white')
    zoom.save(REVIEW / 'posters' / (n + '-detail.png'))
    report = {'resref': n, 'ordinal': a['ordinal'], 'phases': len(records), 'profiles': profiles,
              'frames': records, 'sdf_masks_computed': len(cache),
              'source': evidence(stage / 'manifest.json'),
              'spline': evidence(spline_stage / 'manifest.json'),
              'preview_only': True, 'registered': False, 'installed': False}
    save(report_path, report)
    print(n, 'SDF preview', len(records), 'phases;', len(cache), 'masks', flush=True)
    return report


def gallery(reports):
    cards = []
    for a in reports:
        n = a['resref']
        choices = ''.join(f'<option value="{p["name"]}">{p["id"]} — {p["phases"]} phases, {p["duration"]:.3f} s</option>' for p in a['profiles'])
        panels = ''.join(f'<figure><figcaption>{title}</figcaption><img data-mode="{key}" src="posters/{n}-{key}.png"></figure>'
                         for key, title in [('native', 'Alpha natif x4'), ('spline', 'Essai SplineFit1'), ('sdf', 'SDF Ankheg adapté')])
        cards.append(f'<article><h2>{a["ordinal"]:02d} · {n}</h2><select onchange="cycle(this)">{choices}</select><div class="row">{panels}</div><details><summary>Gros plan du bord + masques alpha</summary><img class="detail" src="posters/{n}-detail.png"></details></article>')
    page = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Huit effets — comparaison SDF Ankheg</title><style>
body{margin:20px;background:#10151e;color:#eee;font:15px system-ui}header{position:sticky;top:0;background:#10151ef5;padding:8px;z-index:2}button,select{background:#29374b;color:white;padding:8px;border:1px solid #667}article{background:#1c2532;padding:14px;margin:16px 0}h2{font-size:19px}.row{display:flex;gap:12px;flex-wrap:wrap}figure{margin:8px 0}figcaption{margin:8px 0}figure img{max-width:340px;max-height:340px;object-fit:contain;image-rendering:pixelated;background:var(--bg,#6e5e46)}.exact figure img{max-width:none;max-height:none}.row{overflow:auto}.detail{max-width:100%}details{margin-top:12px}a{color:#9dcaff}</style>
<header><h1>Masques — natif / SplineFit1 / SDF</h1><p>Recette SDF validée sur l’ankheg ; adaptation x4 proposée ici. Pas encore validée sur ces effets. RGB déjà produits réutilisés ; couleurs étendues uniquement dans les nouveaux pixels de bord. Durées identiques.</p><button onclick="toggle()" id="play">Lecture</button> <button onclick="document.body.classList.toggle('exact')">Taille réelle x4 / aperçu</button> Fond : <select onchange="document.body.style.setProperty('--bg',this.value)"><option value="#6e5e46">Brun</option><option value="#000">Noir</option><option value="#ddd">Clair</option></select></header>CARDS
<script>let playing=false;function cycle(s){let a=s.closest('article');if(playing)a.querySelectorAll('figure img').forEach(i=>i.src=i.dataset.mode+'/'+s.value+'.webp')}function toggle(){playing=!playing;document.querySelectorAll('article').forEach(a=>{if(playing)cycle(a.querySelector('select'));else a.querySelectorAll('figure img').forEach(i=>{let c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;c.getContext('2d').drawImage(i,0,0);i.src=c.toDataURL()})});document.getElementById('play').textContent=playing?'Pause':'Lecture'}</script></html>'''
    (REVIEW / 'index.html').write_text(page.replace('CARDS', ''.join(cards)), encoding='utf-8')


def main():
    assert not (OUT / 'result.json').exists(), 'Do not rewrite a completed comparison'
    a = load(PARENT / 'batch.json')['assets']
    previous = {item['resref']: item for item in load(SPLINE / 'batch.json')['assets']}
    reports = []
    for item in a:
        if item['resref'] in NAMES:
            reports.append(asset(item, previous[item['resref']]))
            gallery(reports)
    save(OUT / 'result.json', {'schema': 'effects-ankheg-sdf-offline-comparison-v1',
         'assets': reports, 'count': 8, 'phases': sum(a['phases'] for a in reports),
         'reference': evidence(REFERENCE),
         'accepted_ankheg_qa': evidence(ROOT / 'sprite/index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json'),
         'rejected_ankheg_spline_qa': evidence(ROOT / 'sprite/index/qa-decisions/monster_ankheg/2026-10-04-rejected-spline-fit1-q3m-x2-catmullrom-v1.json'),
         'adaptation': {'basis': 'validated x2 grid reconstructed from native nearest x4 mask',
                        'output_zoom': 2, 'equivalent_sigma_x4': 4,
                        'equivalent_bias_limit_x4': 2, 'area_supersampling': 8,
                        'quantization_x2': 1/16, 'existing_rgb_preserved': True,
                        'newly_covered_rgb': 'nearest existing foreground material',
                        'temporal_opacity': 'nearest foreground alpha envelope times SDF area coverage'},
         'new_neural_inference': 0, 'production_authorities_changed': False,
         'installed': False, 'effect_visual_qa': 'pending-user-review'})


if __name__ == '__main__':
    main()
