"""Prototype: fit one smooth periodic spline to a binary alpha silhouette."""

from __future__ import annotations

import argparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import splprep, splev


def resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    loop = np.vstack((points, points[0]))
    distances = np.hypot(np.diff(loop[:, 0]), np.diff(loop[:, 1]))
    cumulative = np.concatenate(([0.0], np.cumsum(distances)))
    positions = np.arange(0.0, cumulative[-1], spacing)
    return np.column_stack((np.interp(positions, cumulative, loop[:, 0]),
                            np.interp(positions, cumulative, loop[:, 1])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--fit-error", type=float, default=2.0, help="mean geometric deviation in source x4 pixels")
    parser.add_argument("--sample-spacing", type=float, default=1.5)
    parser.add_argument("--supersample", type=int, default=4)
    args = parser.parse_args()

    alpha = Image.open(args.source).convert("L")
    binary = np.asarray(alpha) > 127
    contours = plt.contour(binary.astype(np.uint8), levels=[0.5]).get_paths()
    plt.close()
    if not contours:
        raise SystemExit("no silhouette contour found")
    contour = max((path.vertices for path in contours), key=len)
    samples = resample_closed(contour, args.sample_spacing)
    smoothing = len(samples) * args.fit_error ** 2
    tck, _ = splprep([samples[:, 0], samples[:, 1]], s=smoothing, per=True, k=3)
    curve = np.asarray(splev(np.linspace(0.0, 1.0, len(samples) * 3, endpoint=False), tck)).T

    high = Image.new("L", (alpha.width * args.supersample, alpha.height * args.supersample), 0)
    ImageDraw.Draw(high).polygon([tuple(point * args.supersample) for point in curve], fill=255)
    high.resize(alpha.size, Image.Resampling.LANCZOS).save(args.output)
    print(f"input vertices={len(contour)}, fit samples={len(samples)}, curve points={len(curve)}")
    print(f"wrote {args.output}: fit-error={args.fit_error}, sample-spacing={args.sample_spacing}")


if __name__ == "__main__":
    main()
