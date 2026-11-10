"""Encode / atomically install only DAYNITE WBM for a local user test."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

RUN = ROOT / 'video/daynite/runs/daynite-h3-nearest-ingame-20261110-v1'
SOURCE = ROOT / 'video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1/DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4'
NATIVE = ROOT / 'video/daynite/daynite.wbm'
OUTPUT = RUN / 'daynite.wbm'
RECEIPT_DIR = ROOT / 'video/installations/daynite-h3-nearest-20261110-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stopped():
    command = ("$p=Get-Process | Where-Object { $_.ProcessName -match "
               "'^(Baldur.*|BGMain|BG2.*|InfinityLoader.*)$' }; "
               "if($p){$p | Select-Object Id,ProcessName | ConvertTo-Json -Compress;exit 1};exit 0")
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Game/InfinityLoader must be closed: ' + result.stdout + result.stderr)


def prepare():
    RUN.mkdir(parents=True, exist_ok=False)
    assert SOURCE.is_file() and NATIVE.is_file()
    print('ENCODE_RUNTIME', flush=True)
    command = ['ffmpeg', '-hide_banner', '-nostdin', '-n', '-threads', '8',
        '-i', str(SOURCE), '-i', str(NATIVE), '-map', '0:v:0', '-map', '1:a:0',
        '-map_metadata', '-1', '-c:v', 'libvpx', '-crf', '4', '-b:v', '30M',
        '-qmin', '0', '-qmax', '12', '-deadline', 'good', '-cpu-used', '0',
        '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough', '-c:a', 'copy', '-f', 'webm', str(OUTPUT)]
    with (RUN / 'encode.log').open('w', encoding='utf-8') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
        '-show_entries', 'stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames:'
                         'format=duration,format_name,size', '-of', 'json', str(OUTPUT)]))
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    audio = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    assert (video['codec_name'], video['width'], video['height'], video['r_frame_rate'],
            video['nb_read_frames'], audio['codec_name']) == ('vp8', 1920, 1080, '30/1', '300', 'vorbis'), info
    report = dict(state='runtime-encoded', source=str(SOURCE.relative_to(ROOT)), source_sha256=sha(SOURCE),
                  output=str(OUTPUT.relative_to(ROOT)), output_sha256=sha(OUTPUT), probe=info,
                  audio_source=str(NATIVE.relative_to(ROOT)), audio_mode='native Vorbis packet copy',
                  command=command, qa_ingame='pending-user', release_integration=False)
    (RUN / 'encoding.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    audio_hashes = []
    for path in (NATIVE, OUTPUT):
        h = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0',
            '-acodec', 'pcm_s16le', '-f', 'hash', '-hash', 'sha256', '-'], text=True).strip()
        audio_hashes.append(h)
    assert audio_hashes[0] == audio_hashes[1], audio_hashes
    graph = '[0:v]settb=AVTB,setpts=N/(30*TB)[a];[1:v]settb=AVTB,setpts=N/(30*TB)[b];[a][b]ssim=shortest=1[v]'
    result = subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-i', str(SOURCE), '-i', str(OUTPUT),
        '-filter_complex', graph, '-map', '[v]', '-an', '-f', 'null', 'NUL'], capture_output=True, text=True, check=True)
    (RUN / 'ssim.log').write_text(result.stderr, encoding='utf-8')
    match = re.search(r'All:([0-9.]+)', result.stderr)
    assert match, result.stderr[-2000:]
    ssim = float(match.group(1)); assert ssim > 0.99, ssim
    quality = dict(ssim_all=ssim, source_audio_exact=True, decoded_pcm_audio_hash=audio_hashes[0],
                   source_audio_packet_copy=True, checked_frames=300,
                   qa_ingame='pending-user', release_integration=False)
    (RUN / 'quality-check.json').write_text(json.dumps(quality, indent=2) + '\n', encoding='utf-8')
    print('RUNTIME_VERIFIED', json.dumps(quality), flush=True)


def install():
    game = get_path('bg2ee_game_root', required=True).resolve()
    movies = (game / 'movies').resolve()
    target = (movies / 'daynite.wbm').resolve()
    assert target.parent == movies and target.name == 'daynite.wbm' and target.is_file()
    encoding = json.loads((RUN / 'encoding.json').read_text())
    quality = json.loads((RUN / 'quality-check.json').read_text())
    assert sha(OUTPUT) == encoding['output_sha256']
    assert quality['source_audio_exact'] and quality['ssim_all'] > 0.99
    stopped()
    RECEIPT_DIR.mkdir(parents=True, exist_ok=False)
    backup = RECEIPT_DIR / 'before/daynite.wbm'; backup.parent.mkdir()
    before = sha(target); shutil.copy2(target, backup); assert sha(backup) == before
    receipt = dict(schema='bg2-video-local-install-v1', asset_key='movie:default:DAYNITE',
        state='backed-up', target='config://bg2ee_game_root/movies/daynite.wbm', resolved_target=str(target),
        backup=str(backup.relative_to(ROOT)), before_sha256=before, source=str(OUTPUT.relative_to(ROOT)),
        after_sha256=sha(OUTPUT), qa_ingame='pending-user', release_integration=False)
    path = RECEIPT_DIR / 'installation.json'
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    temp = target.with_name('daynite.bg2hd-h3-nearest-20261110-v1.wbm.tmp')
    assert not temp.exists()
    shutil.copy2(OUTPUT, temp); assert sha(temp) == sha(OUTPUT)
    stopped(); assert sha(target) == before, 'Concurrent target change'
    os.replace(temp, target); assert sha(target) == sha(OUTPUT)
    receipt.update(state='installed', installed_at=datetime.now(timezone.utc).isoformat())
    path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2), flush=True)


if __name__ == '__main__':
    assert len(sys.argv) == 2 and sys.argv[1] in ('prepare', 'install')
    {'prepare': prepare, 'install': install}[sys.argv[1]]()
