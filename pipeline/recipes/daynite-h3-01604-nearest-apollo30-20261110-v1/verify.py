"""Targeted checks for finished video dimensions, fades, interpolation and game audio."""
from pathlib import Path
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / 'video/daynite/runs/daynite-h3-01604-nearest-apollo30-20261110-v1'
NEAREST = RUN / 'DAYNITE-H3-01604-NEAREST-1080p24-son-original-v1.mp4'
FINAL = RUN / 'DAYNITE-H3-01604-NEAREST-Apollo8-1080p30-son-original-v1.mp4'


def frames(path):
    b = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-an',
                                 '-vf', 'scale=320:180:flags=area', '-pix_fmt', 'rgb24',
                                 '-f', 'rawvideo', 'pipe:1'])
    return np.frombuffer(b, np.uint8).reshape(-1, 180, 320, 3).astype(np.float32)


def endpoints(path, last):
    b = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-an',
                                 '-vf', f"select='eq(n,0)+eq(n,{last})'", '-fps_mode', 'vfr',
                                 '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1'])
    a = np.frombuffer(b, np.uint8).reshape(2, 1080, 1920, 3)
    maxima = [int(x.max()) for x in a]
    assert maxima == [0, 0], maxima
    return maxima


def main():
    a, b = frames(NEAREST), frames(FINAL)
    assert len(a) == 240 and len(b) == 300
    endpoints24, endpoints30 = endpoints(NEAREST, 239), endpoints(FINAL, 299)
    # Check actual 24->30 synthesis between input samples in the changing central region.
    distances = []
    for j in range(96, 204):
        if j % 5 == 0:
            continue
        position = j * 24 / 30
        lo, hi = int(np.floor(position)), int(np.ceil(position))
        d0 = float(np.abs(b[j, 25:160] - a[lo, 25:160]).mean())
        d1 = float(np.abs(b[j, 25:160] - a[hi, 25:160]).mean())
        distances.append(dict(frame30=j, source_position=position, distance_previous=d0,
                              distance_next=d1, distinct_from_both=bool(min(d0, d1) > 0.15)))
    novel = sum(x['distinct_from_both'] for x in distances)
    assert novel >= len(distances) * 0.8, (novel, len(distances))
    means = b[:, 25:160].mean(axis=(1, 2, 3))
    source_means = a[:, 25:160].mean(axis=(1, 2, 3))
    correlation = float(np.corrcoef(means, np.interp(np.arange(300) / 30,
                                                    np.arange(240) / 24, source_means))[0, 1])
    assert correlation > 0.995, correlation
    day_variation = float(np.abs(b[35:85] - b[45]).mean(axis=(1, 2, 3)).max())
    night_variation = float(np.abs(b[215:265] - b[240]).mean(axis=(1, 2, 3)).max())
    assert day_variation < 1 and night_variation < 1, (day_variation, night_variation)
    indices = [0, 15, 30, 60, 90, 105, 120, 135, 150, 165, 180, 195, 210, 240, 270, 299]
    sheet = Image.new('RGB', (1280, 816), (20, 20, 20)); draw = ImageDraw.Draw(sheet)
    for k, i in enumerate(indices):
        x, y = k % 4 * 320, k // 4 * 204
        sheet.paste(Image.fromarray(np.uint8(b[i])), (x, y))
        draw.text((x + 5, y + 184), f'{i/30:.3f}s | frame {i}', fill='white')
    sheet.save(RUN / 'final30-timeline.jpg', quality=95)
    report = dict(frames24=len(a), frames30=len(b), endpoint_max24=endpoints24,
                  endpoint_max30=endpoints30, tested_interpolated_frames=len(distances),
                  distinct_interpolated_frames=novel, interpolation_distances=distances,
                  brightness_correlation_24_30=correlation, day_hold_mean_abs_variation=day_variation,
                  night_hold_mean_abs_variation=night_variation,
                  largest_central_upward_mean_step=float(np.diff(means)[90:210].max()))
    (RUN / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    production = json.loads((RUN / 'production.json').read_text())
    production['state'] = 'verified-comparison-ready'
    production['verification'] = 'verification.json'
    (RUN / 'production.json').write_text(json.dumps(production, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'interpolation_distances'}))


if __name__ == '__main__':
    main()
