"""Native endings audit only: decoded hashes, original PTS, small luma previews, audio hashes."""
import csv, hashlib, json, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'video/research/endings-locales-analysis-20261111-v1'
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        raise RuntimeError(f'{args}: {result.stderr}')
    return result.stdout


def main():
    assert not OUT.exists(), 'New analysis version required'
    OUT.mkdir(parents=True)
    (OUT/'.gitignore').write_text('*.gray\n', encoding='utf-8')
    ffmpeg = shutil.which('ffmpeg'); ffprobe = shutil.which('ffprobe')
    assert ffmpeg and ffprobe
    rows = list(csv.DictReader((ROOT/'video/index/resources.csv').open(encoding='utf-8-sig')))
    rows = [r for r in rows if r['resref'] in ('END15FPS', 'MELISSAN')]
    game = get_path('bg2ee_game_root', required=True)
    locales = {d.name: sorted(p.name for p in (d/'movies').glob('*') if p.is_file()) for d in (game/'lang').iterdir() if d.is_dir()}
    save(OUT/'locale-movies.json', locales)
    def extract(row):
        src = ROOT/row['extracted_path']; name = f"{row['resref']}-{row['locale']}"
        digest = sha(src); assert digest == row['source_sha256']
        before = (src.stat().st_size, src.stat().st_mtime_ns)
        probe = json.loads(run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(src)]))
        save(OUT/f'{name}.probe.json', probe)
        frame_times = json.loads(run([ffprobe, '-v', 'error', '-threads', '2', '-select_streams', 'v:0',
            '-show_frames', '-show_entries', 'frame=best_effort_timestamp_time,pkt_duration_time,key_frame', '-of', 'json', str(src)]))
        save(OUT/f'{name}.native-frame-times.json', frame_times)
        run([ffmpeg, '-v', 'error', '-nostdin', '-n', '-copyts', '-threads', '2', '-i', str(src),
             '-map', '0:v:0', '-an', '-c:v', 'rawvideo', '-pix_fmt', 'yuv420p', '-threads', '1', '-fps_mode', 'passthrough',
             '-f', 'framehash', '-hash', 'sha256', str(OUT/f'{name}.decoded.sha256'),
             '-map', '0:v:0', '-an', '-vf', 'scale=160:90:flags=area,format=gray', '-threads', '1',
             '-fps_mode', 'passthrough', '-f', 'rawvideo', str(OUT/f'{name}.gray')])
        run([ffmpeg, '-v', 'error', '-nostdin', '-n', '-copyts', '-i', str(src), '-map', '0:v:0', '-an',
             '-c:v', 'copy', '-f', 'framehash', '-hash', 'sha256', str(OUT/f'{name}.packets.sha256')])
        audio_encoded = run([ffmpeg, '-v', 'error', '-nostdin', '-i', str(src), '-map', '0:a:0', '-vn', '-c:a', 'copy', '-f', 'hash', '-hash', 'sha256', '-']).strip()
        audio_pcm = run([ffmpeg, '-v', 'error', '-nostdin', '-i', str(src), '-map', '0:a:0', '-vn', '-c:a', 'pcm_s16le', '-f', 'hash', '-hash', 'sha256', '-']).strip()
        video = next(s for s in probe['streams'] if s['codec_type']=='video')
        audio = next(s for s in probe['streams'] if s['codec_type']=='audio')
        hashes = [line for line in (OUT/f'{name}.decoded.sha256').read_text().splitlines() if line and not line.startswith('#')]
        assert (OUT/f'{name}.gray').stat().st_size == len(hashes)*160*90
        assert before == (src.stat().st_size, src.stat().st_mtime_ns)
        result = dict(name=name, asset_key=row['asset_key'], source=row['extracted_path'], source_sha256=digest,
                      bytes=before[0], frames=len(hashes), video=video, audio=audio,
                      format_duration=probe['format']['duration'], audio_encoded_hash=audio_encoded, audio_pcm_hash=audio_pcm)
        save(OUT/f'{name}.metadata.json', result)
        print(f"{name}: {len(hashes)} frames; native SHA verified; decoded video/audio analysed", flush=True)
        return result
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(extract, rows))
    save(OUT/'sources.json', dict(status='extracted', sources=results, thumbnail_shape=[90,160],
        ffmpeg_version=run([ffmpeg,'-version']).splitlines()[0], sources_modified=False,
        production_started=False, game_modified=False, release_modified=False))


if __name__=='__main__':
    main()
