"""Rebuild DAYNITE timing from inspected H3 frames; no new generative inference."""
from pathlib import Path
import bisect
import hashlib
import json
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'MiniMax_H3_01604_-original.mp4'
OUTPUT = ROOT / 'DAYNITE-H3-01604-fondus-corriges-24fps-10s-v1.mp4'
WIDTH, HEIGHT, FPS, COUNT = 1344, 768, 24, 240
DAY, NIGHT = 105, 180
# 119/120 are a short bright flash. 106 has a tiny reverse exposure step.
SELECTED = [DAY, *range(107, 119), *range(121, 153), NIGHT]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    metrics = json.loads((ROOT / 'source-frame-analysis.json').read_text())
    means = [metrics[i]['mean'] for i in SELECTED]
    assert all(a > b for a, b in zip(means, means[1:])), means
    progress = [(means[0] - value) / (means[0] - means[-1]) for value in means]
    expression = '+'.join(f'eq(n,{i})' for i in SELECTED)
    decode = ['ffmpeg', '-v', 'error', '-i', str(SOURCE), '-an', '-vf',
              f"select='{expression}'", '-fps_mode', 'vfr', '-pix_fmt', 'rgb24',
              '-f', 'rawvideo', 'pipe:1']
    raw = subprocess.check_output(decode)
    frames = np.frombuffer(raw, np.uint8).reshape(len(SELECTED), HEIGHT, WIDTH, 3)
    command = [
        'ffmpeg', '-hide_banner', '-loglevel', 'warning', '-f', 'rawvideo',
        '-pixel_format', 'rgb24', '-video_size', f'{WIDTH}x{HEIGHT}',
        '-framerate', str(FPS), '-i', 'pipe:0', '-i', str(SOURCE),
        '-map', '0:v:0', '-map', '1:a:0', '-map_metadata', '-1',
        '-vf', 'scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '14',
        '-color_range', 'tv', '-colorspace', 'bt709',
        '-color_primaries', 'bt709', '-color_trc', 'iec61966-2-1',
        '-force_key_frames', '0,9.958333333', '-video_track_timescale', '24000',
        '-af', 'atempo=1.0825,atrim=duration=10,apad=whole_dur=10,'
               'afade=t=in:st=0:d=0.03,afade=t=out:st=9.7:d=0.3',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '32000',
        '-t', '10', '-movflags', '+faststart', str(OUTPUT),
    ]
    mapping = []
    with (ROOT / 'encode.log').open('w', encoding='utf-8') as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
        try:
            for n in range(COUNT):
                if n < 24:
                    # Full day is reached at frame24 (1.000s), continuously.
                    image = frames[0].astype(np.float32) * (n / 24)
                    info = dict(phase='black_to_day', source=[DAY], opacity=n / 24)
                elif n < 72:
                    image = frames[0]
                    info = dict(phase='day_hold', source=[DAY])
                elif n < 168:
                    alpha = (n - 72) / 96
                    right = min(bisect.bisect_right(progress, alpha), len(progress) - 1)
                    left = max(right - 1, 0)
                    mix = (alpha - progress[left]) / (progress[right] - progress[left])
                    image = frames[left].astype(np.float32) * (1 - mix)
                    image += frames[right].astype(np.float32) * mix
                    info = dict(phase='day_to_night', source=[SELECTED[left], SELECTED[right]],
                                mix=mix, progress=alpha)
                elif n < 216:
                    image = frames[-1]
                    info = dict(phase='night_hold', source=[NIGHT])
                else:
                    # Frame239 is pure black, held until the exact 10s endpoint.
                    opacity = 1 - (n - 216) / 23
                    image = frames[-1].astype(np.float32) * opacity
                    info = dict(phase='night_to_black', source=[NIGHT], opacity=opacity)
                if image.dtype != np.uint8:
                    image = np.clip(np.rint(image), 0, 255).astype(np.uint8)
                encoder.stdin.write(image.tobytes())
                mapping.append(dict(frame=n, time=n / FPS, **info))
            encoder.stdin.close()
            return_code = encoder.wait()
        except BaseException:
            encoder.kill()
            encoder.wait()
            raise
    if return_code:
        raise RuntimeError((ROOT / 'encode.log').read_text())
    (ROOT / 'frame-mapping.json').write_text(json.dumps(mapping, indent=2) + '\n')
    report = dict(
        source=str(SOURCE), source_sha256=sha256(SOURCE), output=str(OUTPUT),
        output_sha256=sha256(OUTPUT), output_size=[WIDTH, HEIGHT], fps=FPS, frames=COUNT,
        duration_seconds=10, selected_source_frames=SELECTED,
        day_frame=dict(index=DAY, time=DAY / FPS), night_frame=dict(index=NIGHT, time=NIGHT / FPS),
        removed_flash_frames=[119, 120],
        method='Re-time inspected H3 intermediate frames by monotone measured brightness. '
               'Linear RGB sample blending between adjacent clean selected frames; '
               'no optical-flow warping or new AI image generation. Still holds at day/night. '
               'Fresh black fades, exact first/last black frames.',
        phases=[['black_to_day', 0, 1], ['day_hold', 1, 3], ['day_to_night', 3, 7],
                ['night_hold', 7, 9], ['night_to_black', 9, 10]],
        audio='Preserve complete H3 clip audio content, tempo 1.0825 to fit 10s, '
              'same pitch; short 0.03s opening and 0.3s closing audio fades. '
              'No replacement with native game audio.',
        commands=dict(decode=decode, encode=command), installed=False, user_validation='pending',
    )
    (ROOT / 'production.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(OUTPUT)


if __name__ == '__main__':
    main()
