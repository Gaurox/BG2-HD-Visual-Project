"""Benchmark in-memory zlib decoding for one or more PVRZ build directories."""

from __future__ import annotations

import argparse
import json
import statistics
import struct
import time
import zlib
from pathlib import Path


def load_dataset(root: Path) -> list[tuple[str, bytes, int]]:
    directory = root.resolve()
    if not directory.is_dir():
        raise ValueError(f"dossier absent : {directory}")
    files = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.upper() == ".PVRZ"
    )
    if not files:
        raise ValueError(f"aucune PVRZ : {directory}")
    dataset = []
    for path in files:
        blob = path.read_bytes()
        if len(blob) < 5:
            raise ValueError(f"PVRZ tronquée : {path}")
        expected = struct.unpack_from("<I", blob)[0]
        decoded = zlib.decompress(blob[4:])
        if len(decoded) != expected:
            raise ValueError(f"taille décodée incohérente : {path}")
        dataset.append((path.name, blob[4:], expected))
    return dataset


def benchmark_dataset(
    dataset: list[tuple[str, bytes, int]], iterations: int
) -> dict[str, object]:
    if iterations < 1:
        raise ValueError("le nombre d'itérations doit être positif")

    # Warm every stream and allocate its full decoded size before sampling.
    for name, compressed, expected in dataset:
        if len(zlib.decompress(compressed)) != expected:
            raise RuntimeError(f"warm-up divergent : {name}")

    totals = []
    maxima = []
    page_medians = []
    all_page_samples = []
    for _ in range(iterations):
        page_samples = []
        iteration_start = time.perf_counter_ns()
        for name, compressed, expected in dataset:
            start = time.perf_counter_ns()
            decoded = zlib.decompress(compressed)
            elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
            if len(decoded) != expected:
                raise RuntimeError(f"décompression divergente : {name}")
            page_samples.append(elapsed_ms)
        totals.append((time.perf_counter_ns() - iteration_start) / 1_000_000)
        maxima.append(max(page_samples))
        page_medians.append(statistics.median(page_samples))
        all_page_samples.extend(page_samples)

    return {
        "pages": len(dataset),
        "compressed_bytes": sum(len(compressed) + 4 for _, compressed, _ in dataset),
        "decoded_bytes": sum(expected for _, _, expected in dataset),
        "iterations": iterations,
        "total_ms_median": statistics.median(totals),
        "total_ms_samples": totals,
        "maximum_page_ms_median": statistics.median(maxima),
        "maximum_page_ms_samples": maxima,
        "median_page_ms_median": statistics.median(page_medians),
        "all_page_ms_median": statistics.median(all_page_samples),
    }


def parse_dataset(raw: str) -> tuple[str, Path]:
    if "=" not in raw:
        path = Path(raw)
        return path.name, path
    label, path = raw.split("=", 1)
    if not label or not path:
        raise ValueError(f"dataset invalide : {raw!r}")
    return label, Path(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mesure la décompression zlib en mémoire de builds PVRZ."
    )
    parser.add_argument("datasets", nargs="+", help="LABEL=BUILD_DIR ou BUILD_DIR")
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()

    report = {
        "method": "Python zlib, blobs preloaded in memory, one warm-up",
        "datasets": {},
    }
    for raw in args.datasets:
        label, path = parse_dataset(raw)
        if label in report["datasets"]:
            raise ValueError(f"label dupliqué : {label}")
        report["datasets"][label] = benchmark_dataset(
            load_dataset(path), args.iterations
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
