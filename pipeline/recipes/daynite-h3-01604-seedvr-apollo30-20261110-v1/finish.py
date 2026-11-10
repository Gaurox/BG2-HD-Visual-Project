"""Finish corrected H3 -> SeedVR1080 -> Apollo30, with original DAYNITE sound."""
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

RUN = ROOT / 'video/daynite/runs/daynite-h3-01604-seedvr-apollo30-20261110-v1'
BASE = RUN / 'DAYNITE-H3-01604-fondus-corriges-16x9-son-original-24fps-v2.mp4'
SEED = RUN / 'DAYNITE-H3-01604-SeedVR2-1080p24-son-original-v1.mp4'
FINAL = RUN / 'DAYNITE-H3-01604-SeedVR2-Apollo8-1080p30-son-original-v1.mp4'
MASTER = RUN / 'apollo-working.mkv'
REPORT = RUN / 'production.json'
ENC = Path(shutil.which('ffmpeg'))
PROBE = Path(shutil.which('ffprobe'))
TOPAZ = get_path('topaz_video_ffmpeg', required=True)
MODELS = get_path('topaz_video_models', required=True)
ENV = os.environ.copy()
ENV.update(TVAI_MODEL_DIR=str(MODELS), TVAI_MODEL_DATA_DIR=str(MODELS))
ENV['PATH'] = str(TOPAZ.parent) + os.pathsep + ENV.get('PATH', '')
TAGS = ['-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709',
        '-color_trc', 'iec61966-2-1']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def probe(path):
    return json.loads(subprocess.check_output([
        str(PROBE), '-v', 'error', '-threads', '8', '-count_frames',
        '-show_entries', 'stream=index,codec_name,width,height,r_frame_rate,nb_read_frames,'
                         'duration,sample_rate:format=duration', '-of', 'json', str(path)]))


def main():
    raw = list((RUN / 'comfy-output').rglob('*.mov'))
    assert len(raw) == 1, raw
    report = dict(
        state='finishing', installed=False, user_validation='pending',
        prompt_id='5d010aa8-6275-4a9d-aa3e-ecaec3ec50ef',
        source='video/daynite/runs/daynite-minimax-h3-01604-fades-20261110-v1/'
               'DAYNITE-H3-01604-fondus-corriges-24fps-10s-v1.mp4',
        aspect_correction='1344x768 -> crop 1344x756, y=6: remove only 6 black rows '
                          'top/bottom, preserve active scene proportions; SeedVR1080 -> 1920x1080.',
        audio_source='video/daynite/daynite.wbm; full native game audio, AAC encoded '
                     'once into BASE then packet-copied to SEED/FINAL; no tempo change or trim.',
        seedvr=dict(model='seedvr2_ema_3b_fp16.safetensors', vae='ema_vae_fp16.safetensors',
                    node_version='2.5.24', seed=42, resolution=1080, batch_size=33,
                    uniform_batch_size=True, temporal_overlap=3, color_correction='lab',
                    noise=0, blocks_to_swap=32, attention='sdpa'),
        seedvr_postprocess='Keep SeedVR central frames72..167. Freeze day on SeedVR '
                            'frame72, night on frame168. Rebuild black fades at0..1/9..10s '
                            'to preserve accepted timing and exact black endpoints after inference.',
        apollo=dict(model='apo-8', target_fps=30, slowmo=1, rdt=-0.01),
        comfy_raw=str(raw[0].relative_to(ROOT)), comfy_raw_sha256=digest(raw[0]), commands=[])

    def save():
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def command(args, label):
        args = [str(a) for a in args]
        report['commands'].append(dict(label=label, argv=args))
        save()
        print('START', label, flush=True)
        with (RUN / (label + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run(args, env=ENV, stdout=log, stderr=subprocess.STDOUT, check=True)
        print('DONE', label, flush=True)

    p = probe(raw[0]); v = p['streams'][0]
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) == (1920, 1080, '24/1', 240), p
    report['raw_probe'] = p
    if not SEED.exists():
        graph = (
            '[0:v]format=rgb24,split=3[di][mi][ni];'
            '[di]trim=start_frame=72:end_frame=73,setpts=PTS-STARTPTS,'
            'loop=loop=71:size=1:start=0,trim=end_frame=72,setpts=N/(24*TB),'
            'fade=t=in:s=0:n=24[d];'
            '[mi]trim=start_frame=72:end_frame=168,setpts=N/(24*TB)[m];'
            '[ni]trim=start_frame=168:end_frame=169,setpts=PTS-STARTPTS,'
            'loop=loop=71:size=1:start=0,trim=end_frame=72,setpts=N/(24*TB),'
            'fade=t=out:s=48:n=23[n];'
            '[d][m][n]concat=n=3:v=1:a=0,setpts=N/(24*TB),'
            'scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p[v]')
        command([ENC, '-hide_banner', '-nostdin', '-n', '-threads', '8', '-i', raw[0],
                 '-i', BASE, '-filter_complex', graph, '-map', '[v]', '-map', '1:a:0',
                 '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-r', '24',
                 '-fps_mode', 'cfr', '-force_key_frames', '0,9.958333333',
                 '-c:a', 'copy', *TAGS, '-movflags', '+faststart', SEED], 'seedvr24-stable-fades')
    p24 = probe(SEED); v = p24['streams'][0]
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) == (1920, 1080, '24/1', 240), p24
    if not FINAL.exists():
        if not MASTER.exists():
            command([TOPAZ, '-hide_banner', '-nostdin', '-n', '-threads', '8', '-i', SEED,
                     '-map', '0:v:0', '-an', '-vf',
                     'format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:'
                     'device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le',
                     '-c:v', 'ffv1', '-level', '3', '-fps_mode', 'passthrough',
                     '-color_range', 'pc', '-colorspace', 'rgb', MASTER], 'apollo30')
        pm = probe(MASTER); count = int(pm['streams'][0]['nb_read_frames'])
        assert count in (299, 300), pm
        report['apollo_raw_probe'] = pm
        report['end_black_frames_added'] = 300 - count
        vf = ('tpad=stop_mode=clone:stop_duration=0.1,trim=end_frame=300,'
              'setpts=N/(30*TB),scale=in_range=pc:out_range=tv:out_color_matrix=bt709,'
              'format=yuv420p,drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:'
              "enable='eq(n,0)+eq(n,299)'")
        command([ENC, '-hide_banner', '-nostdin', '-n', '-threads', '8', '-i', MASTER,
                 '-i', SEED, '-map', '0:v:0', '-map', '1:a:0', '-vf', vf,
                 '-c:v', 'libx264', '-crf', '16', '-preset', 'slow',
                 '-fps_mode', 'passthrough', '-force_key_frames', '0,9.966666667',
                 '-c:a', 'copy', *TAGS, '-movflags', '+faststart', FINAL], 'final30')
    p30 = probe(FINAL); v = p30['streams'][0]
    assert (v['width'], v['height'], v['r_frame_rate'], int(v['nb_read_frames'])) == (1920, 1080, '30/1', 300), p30
    audio_hashes = []
    for path in (BASE, SEED, FINAL):
        h = subprocess.check_output([str(ENC), '-v', 'error', '-i', str(path), '-map',
                                     '0:a:0', '-c:a', 'copy', '-f', 'hash', '-hash',
                                     'sha256', '-'], text=True).strip()
        audio_hashes.append(h)
    assert len(set(audio_hashes)) == 1, audio_hashes
    report.update(state='encoded-awaiting-visual-check', outputs={
        'base16x9': str(BASE.relative_to(ROOT)), 'seed24': str(SEED.relative_to(ROOT)),
        'final30': str(FINAL.relative_to(ROOT))}, probe24=p24, probe30=p30,
        sha256={p.name: digest(p) for p in (BASE, SEED, FINAL)},
        audio_packet_hash=audio_hashes[0], audio_identical_base_seed_final=True)
    save()
    if MASTER.exists():
        assert MASTER.resolve().parent == RUN.resolve() and MASTER.name == 'apollo-working.mkv'
        MASTER.unlink()
    print('ENCODED', FINAL, flush=True)


if __name__ == '__main__':
    main()
