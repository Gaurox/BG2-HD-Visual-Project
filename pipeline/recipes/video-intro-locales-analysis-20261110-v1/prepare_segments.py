"""Prepare native localized openings only; no inference, interpolation or installation."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / 'video/research/intro-locales-analysis-20261110-v1'
OUT = ROOT / 'video/preparation/intro-localized-segments-20261111-v1'


def run(args):
    p = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if p.returncode:
        raise RuntimeError(p.stderr)
    return p.stdout


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def hashes(text):
    return [line.rsplit(',', 1)[-1].strip() for line in text.splitlines() if line and not line.startswith('#')]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / 'manifest.json').exists(), 'Use a new preparation version'
    entries = []
    for source in json.loads((AUDIT / 'sources.json').read_text(encoding='utf-8'))['sources']:
        name = source['name']
        film, locale = name.split('-', 1)
        core_end = 18 if film == 'INTRO15F' else 7
        times = json.loads((AUDIT / f'{name}.native-frame-times.json').read_text())['frames']
        origin = float(times[0]['best_effort_timestamp_time'])
        count = next(i for i, f in enumerate(times) if float(f['best_effort_timestamp_time']) >= core_end + 1)
        folder = OUT / film / locale
        folder.mkdir(parents=True, exist_ok=True)
        clip = folder / f'{name}__ouverture_contexte__n000000-{count-1:06d}.mkv'
        assert not clip.exists(), clip
        src = ROOT / source['source']
        with src.open('rb') as f:
            assert hashlib.file_digest(f, 'sha256').hexdigest().upper() == source['source_sha256']
        run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-threads', '2', '-i', str(src),
             '-map', '0:v:0', '-an', '-vf', f'trim=end_frame={count},setpts=PTS-STARTPTS',
             '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv420p', '-threads', '2',
             '-fps_mode', 'passthrough', str(clip)])
        actual = hashes(run(['ffmpeg', '-v', 'error', '-threads', '2', '-i', str(clip),
                             '-map', '0:v:0', '-an', '-c:v', 'rawvideo', '-pix_fmt', 'yuv420p',
                             '-threads', '1', '-fps_mode', 'passthrough', '-f', 'framehash', '-hash', 'sha256', '-']))
        expected = hashes((AUDIT / f'{name}.decoded.sha256').read_text())[:count]
        assert actual == expected, f'Native frame mismatch: {name}'
        probe = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_frames',
                               '-show_entries', 'frame=best_effort_timestamp_time', '-of', 'json', str(clip)]))
        output_times = [float(f['best_effort_timestamp_time']) for f in probe['frames']]
        assert len(output_times) == count
        with (folder / 'frames.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['clip_frame_0based', 'source_frame_0based', 'source_pts_s', 'clip_pts_s', 'role', 'native_yuv420p_sha256'])
            for i in range(count):
                t = float(times[i]['best_effort_timestamp_time'])
                w.writerow([i, i, times[i]['best_effort_timestamp_time'], f'{output_times[i]:.6f}',
                            'opening_with_fades' if t < core_end else 'join_context_only', expected[i]])
        drift = max(abs(output_times[i] - (float(times[i]['best_effort_timestamp_time']) - origin)) for i in range(count))
        assert drift <= .0021, (name, drift)
        entry = dict(name=name, source=source['source'], source_sha256=source['source_sha256'],
                     clip=str(clip.relative_to(OUT)).replace('\\', '/'), codec='ffv1', pixel_format='yuv420p',
                     dimensions=[1280, 720], frames=count, source_frame_start=0, source_frame_end_exclusive=count,
                     source_first_pts_s=origin, source_last_pts_s=float(times[count-1]['best_effort_timestamp_time']),
                     opening_planning_end_s=core_end, included_context_end_s=core_end+1,
                     frame_pixels_verified_native=True, max_rebased_pts_deviation_s=drift,
                     audio_in_clip=False, final_join_not_fixed=True, bytes=clip.stat().st_size)
        save(folder / 'segment.json', entry)
        entries.append(entry)
        print(f'{name}: {count} frames; native pixels verified; PTS deviation {drift:.6f}s', flush=True)
    save(OUT / 'manifest.json', dict(status='cut-only-no-ai', segments=entries,
                                   source_analysis=str(AUDIT.relative_to(ROOT)), audio='Native full-length sources retained; no audio edits',
                                   note='7/18s are conservative planning limits, not final assembly cuts. Tail is context only.'))
    lines = ['# Intros — ouvertures localisées prêtes à traiter', '',
             '- Préparation uniquement : aucun SeedVR/interpolation ; sources intactes.',
             '- Classement : `<film>/<locale>/` ; `default` = version anglaise par défaut.',
             '- MKV FFV1 sans perte, YUV420p natif 1280×720 ; toutes les images vérifiées par SHA-256 contre le décodage source.',
             '- INTRO : ouverture 0–7 s + contexte jusqu’à 8 s ; INTRO15F : 0–18 s + contexte jusqu’à 19 s.',
             '- Ces bornes englobent les fondus ; raccord de montage final à choisir après traitement. La courte queue commune sert uniquement au raccord.',
             '- Aucun corps commun complet extrait. Cartons anglais inclus pour disposer des 7 ouvertures.',
             '- Cadences natives conservées sans interpolation. `frames.csv` conserve les PTS source et sortie par image (indices à partir de 0).',
             '- Le MKV rebascule le départ à 0 ; arrondis milliseconde et PTS initiaux dupliqués polonais peuvent déplacer un timestamp de 1 ms. Aucun ajout/retrait d’image ; utiliser les PTS source au montage final.',
             '- Vidéos muettes destinées à SeedVR ; audio natif intégral à reprendre dans les sources indiquées par `segment.json`.',
             '- Cadrage polonais natif conservé pour cette préparation ; décision du cadrage final encore ouverte.',
             '- Pas de fichier français séparé disponible dans les sources analysées.', '',
             '| Film | Locale | Images | Dernier PTS source (s) |', '|---|---|---:|---:|']
    for e in entries:
        film, locale = e['name'].split('-', 1)
        lines.append(f"| {film} | {locale} | {e['frames']} | {e['source_last_pts_s']:.3f} |")
    lines += ['', '- `manifest.json` : inventaire ; `reperage/transitions.jpg` : contrôle visuel des fondus.',
              '- Reproduction : `python -B pipeline/recipes/video-intro-locales-analysis-20261110-v1/prepare_segments.py` (destination neuve requise).']
    (OUT / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
