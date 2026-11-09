import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parents[1] / 'restdung.wbm'
TOPAZ = Path('C:/Program Files/Topaz Labs LLC/Topaz Video AI/ffmpeg.exe')
FFMPEG = Path('C:/ffmpeg/bin/ffmpeg.exe')
ENV = os.environ.copy()
ENV['TVAI_MODEL_DIR'] = 'C:/ProgramData/Topaz Labs LLC/Topaz Video AI/models'
ENV['TVAI_MODEL_DATA_DIR'] = ENV['TVAI_MODEL_DIR']
ENV['PATH'] = str(TOPAZ.parent) + os.pathsep + ENV.get('PATH', '')
FILTERS = {
    'A-proteus-doux': 'tvai_up=model=prob-4:scale=0:w=1920:h=1080:preblur=-0.03:noise=0:details=0.12:halo=0.05:blur=0.06:compression=0.15:blend=0.20:grain=0:device=0:vram=0.8:instances=0:download=0',
    'B-gaia-cg': 'tvai_up=model=gcg-5:scale=0:w=1920:h=1080:grain=0:device=0:vram=0.8:instances=0:download=0',
}

def run(cmd, log):
    with log.open('w', encoding='utf-8') as stream:
        subprocess.run([str(x) for x in cmd], stdout=stream, stderr=subprocess.STDOUT, env=ENV, check=True)

def main():
    report = {'source': str(SOURCE), 'state': 'working', 'qa': 'pending', 'commands': {}}
    report_path = ROOT / 'render-report.json'
    for label, filt in FILTERS.items():
        native = ROOT / (label + '-1440p15-native.mov')
        master = ROOT / (label + '-1080p15-master.mov')
        cmd = [TOPAZ, '-hide_banner', '-nostdin', '-n', '-i', SOURCE,
               '-map', '0:v:0', '-an', '-vf', filt,
               '-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le',
               '-fps_mode', 'passthrough', native]
        report['commands'][label] = [str(x) for x in cmd]
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('START', label, flush=True)
        start = time.monotonic()
        run(cmd, ROOT / (label + '-topaz.log'))
        print('MASTER_DONE', label, round(time.monotonic()-start, 1), 'seconds', flush=True)
        run([FFMPEG, '-hide_banner', '-nostdin', '-n', '-i', native,
             '-vf', 'scale=1920:1080:flags=lanczos', '-an', '-c:v', 'prores_ks',
             '-profile:v', '3', '-pix_fmt', 'yuv422p10le', '-fps_mode', 'passthrough', master],
            ROOT / (label + '-resize.log'))
        preview = ROOT / (label + '-1080p15.mp4')
        run([FFMPEG, '-hide_banner', '-nostdin', '-n', '-i', master, '-i', SOURCE,
             '-map', '0:v:0', '-map', '1:a:0?', '-c:v', 'libx264', '-preset', 'slow',
             '-crf', '16', '-pix_fmt', 'yuv420p', '-fps_mode', 'passthrough',
             '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', preview],
            ROOT / (label + '-preview.log'))
        print('PREVIEW_DONE', preview, flush=True)
    report['state'] = 'rendered'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
