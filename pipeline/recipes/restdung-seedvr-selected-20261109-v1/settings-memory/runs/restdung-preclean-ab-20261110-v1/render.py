import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1] / 'restdung.wbm'
FF = 'C:/Program Files/Topaz Labs LLC/Topaz Video AI/ffmpeg.exe'
PROBE = 'C:/ffmpeg/bin/ffprobe.exe'
ENV = os.environ.copy()
ENV['TVAI_MODEL_DIR'] = 'C:/ProgramData/Topaz Labs LLC/Topaz Video AI/models'
ENV['TVAI_MODEL_DATA_DIR'] = ENV['TVAI_MODEL_DIR']
ENV['PATH'] = str(Path(FF).parent) + os.pathsep + ENV.get('PATH', '')
COMMON = ':grain=0:device=0:vram=0.8:instances=0:download=0'
CLEAN = {
    'N1-proteus-nettoyage': 'tvai_up=model=prob-4:scale=1:w=1280:h=720:preblur=-0.03:noise=0.02:details=0:halo=0.03:blur=0:compression=0.20:blend=0.25' + COMMON,
    'N2-nyx-nettoyage': 'tvai_up=model=nyx-3:scale=1:w=1280:h=720:preblur=0:noise=0.12:details=0:halo=0:blur=0:compression=0.12:blend=0.30' + COMMON,
}
UPSCALE = 'tvai_up=model=prob-4:scale=2:w=2560:h=1440:preblur=-0.03:noise=0:details=0.12:halo=0.05:blur=0.06:compression=0.15:blend=0.20' + COMMON + ',scale=1920:1080:flags=lanczos'
report = {'source': str(SOURCE), 'qa': 'pending', 'interpolation': False, 'commands': [], 'verification': {}}

def run(cmd, label):
    cmd = [str(x) for x in cmd]
    report['commands'].append(cmd)
    (ROOT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('START', label, flush=True)
    with (ROOT / (label+'.log')).open('w', encoding='utf-8') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=ENV, check=True)
    print('DONE', label, flush=True)

for label, filt in CLEAN.items():
    clean = ROOT / (label+'-720p15.mkv')
    master = ROOT / (label+'-puis-A-1080p15-master.mov')
    preview = ROOT / (label+'-puis-A-1080p15.mp4')
    run([FF, '-hide_banner', '-nostdin', '-n', '-i', SOURCE, '-map', '0:v:0', '-an', '-vf', filt+',scale=1280:720:flags=lanczos', '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough', clean], label+'-clean')
    run([FF, '-hide_banner', '-nostdin', '-n', '-i', clean, '-map', '0:v:0', '-an', '-vf', UPSCALE, '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-fps_mode', 'passthrough', master], label+'-upscale')
    run(['C:/ffmpeg/bin/ffmpeg.exe', '-hide_banner', '-nostdin', '-n', '-i', master, '-i', SOURCE, '-map', '0:v:0', '-map', '1:a:0?', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', preview], label+'-preview')
    for f, expected_size in ((clean, (1280,720)), (preview, (1920,1080))):
        r = subprocess.run([PROBE, '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=width,height,r_frame_rate,nb_read_frames', '-of', 'json', str(f)], capture_output=True, text=True, check=True)
        info = json.loads(r.stdout)['streams'][0]
        assert (info['width'], info['height']) == expected_size, info
        assert info['r_frame_rate'] == '15/1' and info['nb_read_frames'] == '91', info
        report['verification'][f.name] = info
report['state'] = 'rendered'
(ROOT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
