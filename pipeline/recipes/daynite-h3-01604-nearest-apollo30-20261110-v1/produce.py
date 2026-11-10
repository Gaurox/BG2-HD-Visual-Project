"""Nearest-only FullHD upscale of corrected H3, original game sound, Apollo30."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

RUN = ROOT / 'video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1'
PREVIOUS = ROOT / 'video/daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1'
# This is only the lossless 6px black-bar crop of the corrected H3 input, before SeedVR.
INPUT = PREVIOUS / 'DAYNITE-H3-01604-corrected-16x9-input-v1.mkv'
AUDIO = PREVIOUS / 'DAYNITE-H3-01604-fondus-corriges-16x9-son-original-24fps-v2.mp4'
NEAREST = RUN / 'DAYNITE-H3-01604-NEAREST-1080p24-son-original-v1.mp4'
FINAL = RUN / 'DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4'
MASTER = RUN / 'apollo-working.mkv'
ENC = Path(shutil.which('ffmpeg'))
PROBE = Path(shutil.which('ffprobe'))
TOPAZ = get_path('topaz_video_ffmpeg', required=True)
MODELS = get_path('topaz_video_models', required=True)
ENV = os.environ.copy()
ENV.update(TVAI_MODEL_DIR=str(MODELS), TVAI_MODEL_DATA_DIR=str(MODELS))
ENV['PATH'] = str(TOPAZ.parent) + os.pathsep + ENV.get('PATH', '')
TAGS = ['-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709',
        '-color_trc', 'iec61966-2-1']


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def probe(path):
    return json.loads(subprocess.check_output([str(PROBE), '-v', 'error', '-threads', '8',
        '-count_frames', '-show_entries', 'stream=index,codec_name,width,height,r_frame_rate,'
        'nb_read_frames,duration,sample_rate:format=duration', '-of', 'json', str(path)]))


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    report = dict(state='working', installed=False, user_validation='pending',
        source=str(INPUT.relative_to(ROOT)), source_sha256=sha256(INPUT),
        source_contract='Lossless crop of accepted corrected H3, before any SeedVR '
                        'postprocessing; no post-H3 SeedVR render used.',
        upscale='scale=1920:1080:flags=neighbor; pure nearest-neighbor, no sharpening or restoration',
        seedvr_used=False, audio_source='video/daynite/daynite.wbm; AAC packet copy from '
        'previous verified 16:9 baseline, no trim/tempo change', commands=[])

    def save():
        (RUN / 'production.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def command(args, label):
        args = [str(a) for a in args]
        report['commands'].append(dict(label=label, argv=args)); save()
        print('START', label, flush=True)
        with (RUN / (label + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run(args, env=ENV, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('DONE', label, flush=True)

    p = probe(INPUT); v = p['streams'][0]
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) == (1344, 756, '24/1', 240), p
    if not NEAREST.exists():
        command([ENC, '-hide_banner', '-nostdin', '-n', '-i', INPUT, '-i', AUDIO,
            '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '-1', '-vf',
            'scale=1920:1080:flags=neighbor,format=yuv420p', '-c:v', 'libx264',
            '-crf', '14', '-preset', 'slow', '-fps_mode', 'passthrough',
            '-force_key_frames', '0,9.958333333', '-c:a', 'copy', *TAGS,
            '-movflags', '+faststart', NEAREST], 'nearest24')
    p24 = probe(NEAREST); v = p24['streams'][0]
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) == (1920, 1080, '24/1', 240), p24
    if not FINAL.exists():
        if not MASTER.exists():
            command([TOPAZ, '-hide_banner', '-nostdin', '-n', '-threads', '8', '-i', NEAREST,
                '-map', '0:v:0', '-an', '-vf',
                'format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:'
                'device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le',
                '-c:v', 'ffv1', '-level', '3', '-fps_mode', 'passthrough',
                '-color_range', 'pc', '-colorspace', 'rgb', MASTER], 'apollo30')
        pm = probe(MASTER); count = int(pm['streams'][0]['nb_read_frames'])
        assert count in (299, 300), pm
        report['apollo_raw_probe'] = pm
        report['end_black_frames_added'] = 300 - count
        vf = ('tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame=300,setpts=N/(30*TB),'
            'scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p,'
            "drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='eq(n,0)+eq(n,299)'")
        command([ENC, '-hide_banner', '-nostdin', '-n', '-threads', '8', '-i', MASTER,
            '-i', NEAREST, '-map', '0:v:0', '-map', '1:a:0', '-vf', vf,
            '-c:v', 'libx264', '-crf', '14', '-preset', 'slow', '-fps_mode', 'passthrough',
            '-force_key_frames', '0,9.966666667', '-c:a', 'copy', *TAGS,
            '-movflags', '+faststart', FINAL], 'final30')
    p30 = probe(FINAL); v = p30['streams'][0]
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) == (1920, 1080, '30/1', 300), p30
    hashes = [subprocess.check_output([str(ENC), '-v', 'error', '-i', str(f), '-map',
        '0:a:0', '-c:a', 'copy', '-f', 'hash', '-hash', 'sha256', '-'], text=True).strip()
        for f in (AUDIO, NEAREST, FINAL)]
    assert len(set(hashes)) == 1, hashes
    report.update(state='encoded-awaiting-visual-check', probe24=p24, probe30=p30,
        outputs={'nearest24': str(NEAREST.relative_to(ROOT)), 'nearest_apollo30': str(FINAL.relative_to(ROOT))},
        sha256={f.name: sha256(f) for f in (NEAREST, FINAL)},
        audio_packet_hash=hashes[0], original_game_audio_identical_to_verified_baseline=True)
    save()
    if MASTER.exists():
        assert MASTER.resolve().parent == RUN.resolve() and MASTER.name == 'apollo-working.mkv'
        MASTER.unlink()
    print('ENCODED', FINAL, flush=True)


if __name__ == '__main__':
    main()
