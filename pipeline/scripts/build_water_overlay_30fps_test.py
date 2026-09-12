"""Build an isolated AR0900 WTLAKE render-rate timeline experiment.

Plan-only by default. ``--run`` creates a new immutable run containing 36
Apollo-8 phases at 15 Hz, a matching WTLAKE TIS/WED, a 30 FPS render-time
blend review, and an experimental fail-closed route2 registry capped at
strength 0.50.  The six stock phases advance every six 15 Hz engine ticks,
so their authored loop is 2.4 seconds rather than the previously assumed
0.4 seconds.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import shutil
import struct
import subprocess
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageStat

from bg2lib import load_key, resolve_resource
from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_RUN = (
    ROOT
    / "maps/technical-overlays/WTLAKE/runs/seedvr2-7b-int8-wavelet-periodic-x4"
)
PARENT_REGISTRY = ROOT / "pipeline/water/route2-registry-v1.json"
ACTIVE_REGISTRY = (
    ROOT
    / "engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json"
)
TOPAZ_FFMPEG = get_path("topaz_video_ffmpeg")
TOPAZ_MODELS = get_path("topaz_video_models")
REVIEW_FFMPEG = Path("C:/ffmpeg/bin/ffmpeg.exe")
WED_TYPE = 0x03E9
PVR_MAGIC = 0x03525650
PAGE_SIZE = 2048
TILE_SIZE = 256
PAD = 4
MODEL = "apo-8"
SOURCE_FPS = 2.5
NATIVE_TIMELINE_FPS = 15
TARGET_FPS = 30
PHASES_PER_TRANSITION = 6
FRAME_COUNT = 36
ATLAS_COLUMNS = 7
ATLAS_STRIDE = TILE_SIZE + 2 * PAD
RUN_SCHEMA = "bg2-water-overlay-render-timeline-test-v2"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"manifeste absent : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def resolve_stock_wed() -> tuple[bytes, str]:
    bifs, resources = load_key()
    matches = [
        locator
        for name, kind, locator in resources
        if name.upper() == "AR0900" and kind == WED_TYPE
    ]
    require(len(matches) == 1, "AR0900.WED KEY/BIF unique introuvable")
    resolved = resolve_resource(bifs, matches[0])
    require(resolved is not None, "AR0900.WED non résolu")
    return resolved


def source_frames() -> list[Path]:
    directory = SOURCE_RUN / "03_build_input_x4"
    paths = [directory / f"frame-{index:03d}.png" for index in range(6)]
    require(all(path.is_file() for path in paths), "six ancres WTLAKE x4 absentes")
    for path in paths:
        with Image.open(path) as frame:
            require(frame.size == (TILE_SIZE, TILE_SIZE), f"dimension invalide : {path}")
    return paths


def plan(output: Path) -> dict[str, Any]:
    run = load_json(SOURCE_RUN / "run.json")
    wed, source_bif = resolve_stock_wed()
    anchors = source_frames()
    require(run.get("source", {}).get("frame_count") == 6, "run WTLAKE non compatible")
    require(
        sha256_bytes(wed)
        == "471B1A2A5FBF4D78DDDF44851E8A95F18CDA6883B6C048D3382BC84AEE67092A",
        "AR0900.WED stock divergent",
    )
    return {
        "schema": "bg2-water-overlay-render-timeline-plan-v2",
        "output": str(output.resolve()),
        "source_run": str(SOURCE_RUN.relative_to(ROOT)).replace("\\", "/"),
        "source_run_manifest_sha256": sha256_file(SOURCE_RUN / "run.json"),
        "source_wed": {"bif": source_bif, "bytes": len(wed), "sha256": sha256_bytes(wed)},
        "anchors": [
            {"frame": index, "path": str(path.relative_to(ROOT)).replace("\\", "/"),
             "sha256": sha256_file(path)}
            for index, path in enumerate(anchors)
        ],
        "interpolation": {
            "model": MODEL,
            "source_fps": SOURCE_FPS,
            "native_timeline_fps": NATIVE_TIMELINE_FPS,
            "target_fps": TARGET_FPS,
            "phases_per_transition": PHASES_PER_TRANSITION,
            "frame_count": FRAME_COUNT,
            "cycle_duration_seconds": 2.4,
            "runtime_blend": "linear-between-15hz-phases",
        },
        "route2_strength": 0.5,
        "scope": "AR0900 day only",
    }


def run_checked(command: list[str], *, environment: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=environment)


def image_mae(left: Image.Image, right: Image.Image) -> float:
    difference = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    return sum(ImageStat.Stat(difference).mean) / 3.0


def interpolate(plan_data: dict[str, Any], output: Path) -> tuple[list[Path], dict[str, Any]]:
    inputs = output / "00_input_x4"
    raw = output / "01_topaz_30fps"
    frames = output / "02_frames_x4"
    inputs.mkdir(parents=True)
    raw.mkdir()
    frames.mkdir()
    anchors = source_frames()
    for index, source in enumerate(anchors + [anchors[0]]):
        with Image.open(source) as image:
            image.convert("RGB").save(inputs / f"in_{index:04d}.png")

    environment = dict(os.environ)
    environment["TVAI_MODEL_DIR"] = str(TOPAZ_MODELS)
    environment["TVAI_MODEL_DATA_DIR"] = str(TOPAZ_MODELS)
    filter_text = (
        f"tvai_fi=model={MODEL}:fps={NATIVE_TIMELINE_FPS}:rdt=-0.01:device=-2"
    )
    run_checked(
        [
            str(TOPAZ_FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(SOURCE_FPS), "-i", str(inputs / "in_%04d.png"),
            "-vf", filter_text, "-pix_fmt", "rgb24", str(raw / "out_%04d.png"),
        ],
        environment=environment,
    )
    raw_paths = sorted(raw.glob("out_*.png"))
    require(len(raw_paths) in (FRAME_COUNT, FRAME_COUNT + 1),
            f"Topaz a produit {len(raw_paths)} frames")

    anchor_mae: list[float] = []
    for index, source in enumerate(anchors):
        anchor_phase = index * PHASES_PER_TRANSITION
        shutil.copy2(source, frames / f"frame-{anchor_phase:03d}.png")
        with Image.open(raw_paths[anchor_phase]) as generated, Image.open(source) as expected:
            anchor_mae.append(image_mae(generated, expected))

    intermediates: list[dict[str, Any]] = []
    for segment in range(6):
        left = anchors[segment]
        right = anchors[(segment + 1) % 6]
        with Image.open(left) as left_image, Image.open(right) as right_image:
            left_alpha = left_image.convert("RGBA").getchannel("A")
            right_alpha = right_image.convert("RGBA").getchannel("A")
            for phase in range(1, PHASES_PER_TRANSITION):
                frame_index = segment * PHASES_PER_TRANSITION + phase
                destination = frames / f"frame-{frame_index:03d}.png"
                with Image.open(raw_paths[frame_index]) as generated:
                    rgb = generated.convert("RGB")
                    require(rgb.size == (TILE_SIZE, TILE_SIZE),
                            "sortie Apollo de dimension invalide")
                    alpha = Image.blend(
                        left_alpha, right_alpha, phase / PHASES_PER_TRANSITION
                    )
                    rgba = rgb.convert("RGBA")
                    rgba.putalpha(alpha)
                    rgba.save(destination)
                intermediates.append({
                    "frame": frame_index,
                    "between": [segment, (segment + 1) % 6],
                    "fraction": phase / PHASES_PER_TRANSITION,
                    "sha256": sha256_file(destination),
                })
    return [frames / f"frame-{index:03d}.png" for index in range(FRAME_COUNT)], {
        "filter": filter_text,
        "raw_frame_count": len(raw_paths),
        "anchor_rgb_mae": [round(value, 6) for value in anchor_mae],
        "intermediates": intermediates,
    }


def write_pvrz(canvas: Image.Image, destination: Path) -> None:
    buffer = io.BytesIO()
    canvas.save(buffer, format="DDS", pixel_format="DXT5")
    payload = buffer.getvalue()[128:]
    header = struct.pack(
        "<13I", PVR_MAGIC, 0, 11, 0, 0, 0, PAGE_SIZE, PAGE_SIZE, 1, 1, 1, 1, 0
    )
    pvr = header + payload
    destination.write_bytes(struct.pack("<I", len(pvr)) + zlib.compress(pvr, 9))


def build_tileset(frame_paths: list[Path], output: Path) -> tuple[Path, Path]:
    output.mkdir()
    cell = TILE_SIZE + 2 * PAD
    per_row = PAGE_SIZE // cell
    require(per_row == ATLAS_COLUMNS, "layout atlas WTLAKE divergent")
    canvas = Image.new("RGBA", (PAGE_SIZE, PAGE_SIZE), (0, 0, 0, 0))
    entries: list[tuple[int, int, int]] = []
    for index, path in enumerate(frame_paths):
        row, column = divmod(index, per_row)
        x, y = column * cell + PAD, row * cell + PAD
        with Image.open(path) as frame:
            canvas.paste(frame.convert("RGBA"), (x, y))
        entries.append((0, x, y))

    array = np.asarray(canvas).copy()
    for _page, x, y in entries:
        block = array[y - PAD:y + TILE_SIZE + PAD, x - PAD:x + TILE_SIZE + PAD]
        block[:PAD, PAD:-PAD] = block[PAD:PAD + 1, PAD:-PAD]
        block[-PAD:, PAD:-PAD] = block[-PAD - 1:-PAD, PAD:-PAD]
        block[:, :PAD] = block[:, PAD:PAD + 1]
        block[:, -PAD:] = block[:, -PAD - 1:-PAD]
    pvrz_path = output / "WLAKE00.PVRZ"
    write_pvrz(Image.fromarray(array, mode="RGBA"), pvrz_path)

    tis = bytearray(b"TIS V1  ")
    tis += struct.pack("<IIII", FRAME_COUNT, 12, 24, TILE_SIZE)
    for entry in entries:
        tis += struct.pack("<3I", *entry)
    tis_path = output / "WTLAKE.TIS"
    tis_path.write_bytes(tis)
    return tis_path, pvrz_path


def patch_wed(source: bytes) -> bytes:
    require(source[:8] == b"WED V1.3", "signature WED invalide")
    overlay_count, _doors, overlays_offset, secondary_offset = struct.unpack_from(
        "<4I", source, 8
    )
    require(overlay_count == 5, "layout overlay AR0900 divergent")
    slot = overlays_offset + 24
    width, height, resref, _unique, _movement, tilemap, lookup = struct.unpack_from(
        "<HH8sHHII", source, slot
    )
    require((width, height, resref.rstrip(b"\0")) == (1, 1, b"WTLAKE"),
            "overlay WTLAKE AR0900 divergent")
    start, count, secondary, flags = struct.unpack_from("<HHHB3x", source, tilemap)
    require((start, count, secondary, flags) == (0, 6, 65535, 0),
            "tilemap WTLAKE AR0900 divergent")
    require(list(struct.unpack_from("<6H", source, lookup)) == list(range(6)),
            "lookup WTLAKE AR0900 divergent")
    timeline = tuple(range(FRAME_COUNT))
    replacement = struct.pack(f"<{FRAME_COUNT}H", *timeline)
    insertion = lookup + 12
    output = bytearray(source[:lookup] + replacement + source[insertion:])
    inserted_bytes = len(replacement) - 12
    struct.pack_into("<H", output, tilemap + 2, FRAME_COUNT)
    output[tilemap + 7] = 1

    for index in range(overlay_count):
        header = overlays_offset + index * 24
        tilemap_offset, lookup_offset = struct.unpack_from("<II", output, header + 16)
        if tilemap_offset >= insertion:
            struct.pack_into("<I", output, header + 16, tilemap_offset + inserted_bytes)
        if lookup_offset >= insertion:
            struct.pack_into("<I", output, header + 20, lookup_offset + inserted_bytes)

    polygon_count, polygon_offset, vertex_offset, wall_group_offset, polygon_lookup = (
        struct.unpack_from("<5I", output, secondary_offset)
    )
    shifted = [
        value + inserted_bytes if value >= insertion else value
        for value in (polygon_offset, vertex_offset, wall_group_offset, polygon_lookup)
    ]
    struct.pack_into(
        "<5I", output, secondary_offset, polygon_count, shifted[0], shifted[1], shifted[2], shifted[3]
    )
    require(len(output) == len(source) + inserted_bytes, "taille WED interpolée invalide")
    return bytes(output)


def build_review(frame_paths: list[Path], output: Path) -> list[dict[str, Any]]:
    review_frames = output / "05_review_frames"
    review_frames.mkdir()
    review_index = 0
    for phase, current in enumerate(frame_paths):
        following = frame_paths[(phase + 1) % len(frame_paths)]
        shutil.copy2(current, review_frames / f"frame_{review_index:04d}.png")
        review_index += 1
        with Image.open(current) as left, Image.open(following) as right:
            Image.blend(left.convert("RGBA"), right.convert("RGBA"), 0.5).save(
                review_frames / f"frame_{review_index:04d}.png"
            )
        review_index += 1
    exact = output / "review-30fps-exact.mp4"
    loop = output / "review-30fps-loop-4s.mp4"
    run_checked([
        str(REVIEW_FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-i", str(review_frames / "frame_%04d.png"),
        "-frames:v", str(FRAME_COUNT * 2), "-c:v", "libx264", "-preset", "slow", "-crf", "12",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(exact),
    ])
    run_checked([
        str(REVIEW_FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(exact), "-t", "4", "-c:v", "libx264",
        "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(loop),
    ])
    return [
        {"kind": "exact", "path": exact.name, "sha256": sha256_file(exact)},
        {"kind": "loop-4s", "path": loop.name, "sha256": sha256_file(loop)},
    ]


def experimental_registry(wed: Path, tis: Path, pvrz: Path, output: Path) -> Path:
    active = load_json(ACTIVE_REGISTRY)
    parent = load_json(PARENT_REGISTRY)
    entry = copy.deepcopy(parent["entries"][0])
    entry["wed"]["sha256"] = sha256_file(wed)
    entry["overlay"].update({
        "tis_sha256": sha256_file(tis),
        "tis_bytes": tis.stat().st_size,
        "tile_count": FRAME_COUNT,
        "pages": [{
            "resref": "WLAKE00", "width": PAGE_SIZE, "height": PAGE_SIZE,
            "bytes": pvrz.stat().st_size, "sha256": sha256_file(pvrz),
        }],
    })
    entry["approved_strength"] = 0.5
    override = {
        "id": entry["id"],
        "wed": entry["wed"],
        "base_tis": entry["base_tis"],
        "overlay": entry["overlay"],
        "approved_strength": 0.5,
        "overlay_coverage_cells": 1635,
        "allow_stock_wed_when_override_absent": False,
        "material_id": 1,
        "temporal_overlay": {
            "mode": "atlas-linear",
            "frame_count": FRAME_COUNT,
            "source_fps": NATIVE_TIMELINE_FPS,
            "target_fps": TARGET_FPS,
            "atlas_columns": ATLAS_COLUMNS,
            "atlas_stride_pixels": ATLAS_STRIDE,
            "atlas_padding_pixels": PAD,
        },
    }
    registry = {
        "schema": "bg2-water-route2-registry-v2",
        "version": 2,
        "date": datetime.now(timezone.utc).date().isoformat(),
        "parent": active["parent"],
        "entry_overrides": [override],
        "fallback": active["fallback"],
        "experiment": {
            "status": "pending-ingame-qa",
            "scope": "AR0900 day, Apollo-8 2.5->15 Hz plus render-time 30 FPS blend, route2 50 percent",
        },
    }
    destination = output / "registry-v2-experimental.json"
    write_json(destination, registry)
    return destination


def execute(plan_data: dict[str, Any], output: Path) -> dict[str, Any]:
    require(not output.exists(), f"run déjà présent : {output}")
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan_data)
    frame_paths, topaz = interpolate(plan_data, output)
    build = output / "03_build"
    tis, pvrz = build_tileset(frame_paths, build)
    source_wed, _bif = resolve_stock_wed()
    candidate = output / "04_candidate_assets"
    candidate.mkdir()
    wed = candidate / "AR0900.WED"
    wed.write_bytes(patch_wed(source_wed))
    shutil.copy2(tis, candidate / tis.name)
    shutil.copy2(pvrz, candidate / pvrz.name)
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path).lower()}
        for path in sorted(candidate.iterdir()) if path.is_file()
    }
    asset_manifest = {
        "schema": "bg2-upscale-area-animation-override-assets-v1",
        "status": "completed",
        "area": "AR0900",
        "purpose": "WTLAKE Apollo-8 2.5-to-15 Hz plus route2 render-time 30 FPS experiment",
        "qa_status": "pending-ingame",
        "files": files,
        "timeline": list(range(FRAME_COUNT)),
        "animation_speed_divisor": 1,
        "rollback": "Restore-AreaOverrideAssets.ps1 with the generated install backup",
    }
    write_json(candidate / "manifest.json", asset_manifest)
    registry = experimental_registry(wed, candidate / tis.name, candidate / pvrz.name, output)
    reviews = build_review(frame_paths, output)
    result = {
        "schema": RUN_SCHEMA,
        "status": "candidate-installable-pending-qa",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": sha256_file(output / "plan.json"),
        "source": plan_data,
        "topaz": topaz,
        "timeline": {
            "source_fps": SOURCE_FPS,
            "native_fps": NATIVE_TIMELINE_FPS,
            "target_fps": TARGET_FPS,
            "indices": list(range(FRAME_COUNT)),
            "runtime_blend": "linear",
        },
        "candidate_assets": "04_candidate_assets",
        "experimental_registry": registry.name,
        "reviews": reviews,
        "route2_strength": 0.5,
        "qa": "pending-ingame",
        "release": "not-requested",
    }
    write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true", help="exécuter le plan")
    args = parser.parse_args()
    output = args.output.resolve()
    plan_data = plan(output)
    if not args.run:
        print(json.dumps(plan_data, ensure_ascii=False, indent=2))
        return 0
    result = execute(plan_data, output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
