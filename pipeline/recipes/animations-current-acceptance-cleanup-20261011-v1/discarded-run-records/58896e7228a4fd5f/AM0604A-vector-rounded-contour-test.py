"""Prototype: geometrically simplify a binary alpha silhouette without blur.

The contour is extracted at alpha 127, simplified with Ramer-Douglas-Peucker,
then rebuilt as straight segments joined by small quadratic rounded corners.
It is supersampled before Lanczos reduction to retain a fine alpha edge.
"""

from __future__ import annotations

import argparse
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw


def perpendicular_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    length = float(np.hypot(segment[0], segment[1]))
    if length == 0:
        return float(np.hypot(*(point - start)))
    offset = point - start
    return abs(float(segment[0] * offset[1] - segment[1] * offset[0])) / length


def rdp(points: np.ndarray, tolerance: float) -> np.ndarray:
    if len(points) <= 2:
        return points
    distances = np.array([perpendicular_distance(point, points[0], points[-1]) for point in points[1:-1]])
    if len(distances) == 0 or float(distances.max()) <= tolerance:
        return points[[0, -1]]
    index = int(distances.argmax()) + 1
    return np.vstack((rdp(points[:index + 1], tolerance)[:-1], rdp(points[index:], tolerance)))


def simplify_closed(points: np.ndarray, tolerance: float) -> np.ndarray:
    # Split a closed loop at two distant points, simplify both open arcs, then
    # join them again. This avoids a false straight chord across the silhouette.
    anchor = points[0]
    opposite = int(np.argmax(np.sum((points - anchor) ** 2, axis=1)))
    first = rdp(points[:opposite + 1], tolerance)
    second = rdp(np.vstack((points[opposite:], points[0])), tolerance)
    return np.vstack((first[:-1], second[:-1]))


def rounded_polygon(points: np.ndarray, radius: float, samples: int = 8) -> np.ndarray:
    output: list[np.ndarray] = []
    count = len(points)
    for index, vertex in enumerate(points):
        previous = points[(index - 1) % count]
        following = points[(index + 1) % count]
        incoming = vertex - previous
        outgoing = following - vertex
        incoming_length = float(np.hypot(*incoming))
        outgoing_length = float(np.hypot(*outgoing))
        if incoming_length == 0 or outgoing_length == 0:
            continue
        distance = min(radius, incoming_length * 0.28, outgoing_length * 0.28)
        start = vertex - incoming / incoming_length * distance
        end = vertex + outgoing / outgoing_length * distance
        if not output:
            output.append(start)
        else:
            output.append(start)
        for step in range(1, samples + 1):
            t = step / samples
            output.append((1 - t) ** 2 * start + 2 * (1 - t) * t * vertex + t ** 2 * end)
    return np.asarray(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--tolerance", type=float, default=3.5, help="RDP pixels at source x4")
    parser.add_argument("--corner-radius", type=float, default=3.0, help="rounded-corner radius at source x4")
    parser.add_argument("--supersample", type=int, default=4)
    args = parser.parse_args()
    if args.tolerance <= 0 or args.corner_radius < 0 or args.supersample < 2:
        raise SystemExit("invalid geometry parameters")

    alpha = Image.open(args.source).convert("L")
    binary = np.asarray(alpha) > 127
    contour_set = plt.contour(binary.astype(np.uint8), levels=[0.5])
    paths = contour_set.get_paths()
    plt.close()
    if not paths:
        raise SystemExit("no silhouette contour found")
    contour = max((path.vertices for path in paths), key=len)
    simplified = simplify_closed(contour, args.tolerance)
    rounded = rounded_polygon(simplified, args.corner_radius)

    scale = args.supersample
    high = Image.new("L", (alpha.width * scale, alpha.height * scale), 0)
    draw = ImageDraw.Draw(high)
    draw.polygon([tuple(point * scale) for point in rounded], fill=255)
    result = high.resize(alpha.size, Image.Resampling.LANCZOS)
    result.save(args.output)
    print(f"input vertices={len(contour)}, simplified vertices={len(simplified)}, rounded samples={len(rounded)}")
    print(f"wrote {args.output}: tolerance={args.tolerance}, corner-radius={args.corner_radius}, supersample={scale}")


if __name__ == "__main__":
    main()
