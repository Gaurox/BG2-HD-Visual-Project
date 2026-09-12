"""Build an AR1000-day WTPOOL candidate without generative spatial processing."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import struct
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from build_ar1000_wtpool_route1_candidate import (
    ROOT,
    decode_legacy_frames,
    parse_wed,
    relative,
    require,
    resolved_sources,
    sha256_bytes,
    sha256_file,
    write_json,
)
from build_water_overlay_30fps_test import write_pvrz
from build_wtlake_timeline_batch import tis_metadata
from workspace_paths import get_path
from water_wed import replace_overlay_resref, replace_overlay_timeline, validate_polygons


AREA = "AR1000"
FAMILY = "pool-wtpool"
OVERLAY_ALIAS = "WTPOOL2"
PAGE_ALIAS = f"{OVERLAY_ALIAS[0]}{OVERLAY_ALIAS[2:]}00"
SOURCE_FRAMES = 6
PHASES_PER_TRANSITION = 6
FRAME_COUNT = SOURCE_FRAMES * PHASES_PER_TRANSITION
TILE_SIZE = 256
PAD = 4
ATLAS_COLUMNS = 7
ATLAS_STRIDE = TILE_SIZE + PAD * 2
PAGE_SIZE = 2048
STOCK_WED_SHA256 = "3B0A65C65B995B0092DAB10BE88CF129929877DF27E9ACCC76E6565C09194472"
STOCK_TIS_SHA256 = "A48DBEAF449FD2AD403EF50C40EB8A1F71B58333DD9625FE071A5B3A224C8CF8"
REJECTED_RUN = ROOT / "maps/water-batches/runs/ar1000-wtpool-route1-20260912-v1"
REJECTED_PAGE_SHA256 = "669B7AA62202F8FF71E84712BA1AD52DBBEA6715D6791D46F381FD951ADED4E9"
SCREENSHOT_SHA256 = "C620DBB16876F8959427E7AEFD7A06E3E7E0DD07C1C17BA806E332F98AD4CDC5"


def periodic_bilinear_x4(image: Image.Image) -> Image.Image:
    """Resize through a 3x3 wrapped context and crop the centre tile."""
    source = image.convert("RGBA")
    require(source.size == (64, 64), "WTPOOL source frame must be 64x64")
    context = Image.new("RGBA", (192, 192))
    for row in range(3):
        for column in range(3):
            context.paste(source, (column * 64, row * 64))
    scaled = context.resize((768, 768), Image.Resampling.BILINEAR)
    return scaled.crop((256, 256, 512, 512))


def cyclic_linear_timeline(anchors: list[Image.Image]) -> list[Image.Image]:
    require(len(anchors) == SOURCE_FRAMES, "WTPOOL requires six source anchors")
    frames: list[Image.Image] = []
    for index, current in enumerate(anchors):
        following = anchors[(index + 1) % len(anchors)]
        for phase in range(PHASES_PER_TRANSITION):
            frames.append(Image.blend(current, following, phase / PHASES_PER_TRANSITION))
    require(len(frames) == FRAME_COUNT, "WTPOOL timeline must contain 36 phases")
    return frames


def build_overlay(frames: list[Image.Image], output: Path) -> tuple[Path, Path]:
    require(len(frames) == FRAME_COUNT, "invalid WTPOOL2 frame count")
    output.mkdir()
    canvas = np.zeros((PAGE_SIZE, PAGE_SIZE, 4), dtype=np.uint8)
    entries: list[tuple[int, int, int]] = []
    for index, image in enumerate(frames):
        row, column = divmod(index, ATLAS_COLUMNS)
        x, y = column * ATLAS_STRIDE + PAD, row * ATLAS_STRIDE + PAD
        frame = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        require(frame.shape == (TILE_SIZE, TILE_SIZE, 4), "invalid WTPOOL2 frame")
        canvas[y:y + TILE_SIZE, x:x + TILE_SIZE] = frame
        canvas[y - PAD:y, x:x + TILE_SIZE] = frame[:1]
        canvas[y + TILE_SIZE:y + TILE_SIZE + PAD, x:x + TILE_SIZE] = frame[-1:]
        canvas[y - PAD:y + TILE_SIZE + PAD, x - PAD:x] = \
            canvas[y - PAD:y + TILE_SIZE + PAD, x:x + 1]
        canvas[y - PAD:y + TILE_SIZE + PAD, x + TILE_SIZE:x + TILE_SIZE + PAD] = \
            canvas[y - PAD:y + TILE_SIZE + PAD, x + TILE_SIZE - 1:x + TILE_SIZE]
        entries.append((0, x, y))
    pvrz = output / f"{PAGE_ALIAS}.PVRZ"
    write_pvrz(Image.fromarray(canvas, mode="RGBA"), pvrz)
    tis = bytearray(b"TIS V1  ")
    tis += struct.pack("<IIII", FRAME_COUNT, 12, 24, TILE_SIZE)
    for entry in entries:
        tis += struct.pack("<3I", *entry)
    tis_path = output / f"{OVERLAY_ALIAS}.TIS"
    tis_path.write_bytes(tis)
    metadata, paths = tis_metadata(OVERLAY_ALIAS, output)
    require(metadata["tile_count"] == FRAME_COUNT and paths == [tis_path, pvrz],
            "WTPOOL2 TIS/PVRZ inventory mismatch")
    return tis_path, pvrz


def high_frequency_energy(image: Image.Image) -> float:
    rgb = image.convert("RGB")
    source = np.asarray(rgb, dtype=np.float32)
    blurred = np.asarray(rgb.filter(ImageFilter.GaussianBlur(2)), dtype=np.float32)
    return float(np.sqrt(np.mean((source - blurred) ** 2)))


def seam_ratios(frames: list[Image.Image]) -> list[float]:
    ratios = []
    for image in frames:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
        seam_x = np.mean(np.abs(rgb[:, -1] - rgb[:, 0]))
        seam_y = np.mean(np.abs(rgb[-1] - rgb[0]))
        inner_x = np.mean(np.abs(rgb[:, 1:] - rgb[:, :-1]))
        inner_y = np.mean(np.abs(rgb[1:] - rgb[:-1]))
        ratios.append((seam_x / max(inner_x, 1e-6), seam_y / max(inner_y, 1e-6)))
    return np.mean(ratios, axis=0).round(4).tolist()


def create_plan(output: Path) -> dict[str, Any]:
    wed, wed_archive, legacy, tis_archive = resolved_sources()
    require(sha256_bytes(wed) == STOCK_WED_SHA256, "stock AR1000 WED changed")
    require(sha256_bytes(legacy) == STOCK_TIS_SHA256, "stock WTPOOL TIS changed")
    rejected = sorted((REJECTED_RUN / "03_anchor_x4").glob("frame-*.png"))
    require(len(rejected) == SOURCE_FRAMES, "rejected SeedVR anchors unavailable")
    require(sha256_file(REJECTED_RUN / "08_candidate/WPL1000.PVRZ") == REJECTED_PAGE_SHA256,
            "rejected SeedVR page changed")
    live = get_path("bg2ee_game_root") / "override"
    require(not (live / f"{OVERLAY_ALIAS}.TIS").exists() and
            not (live / f"{PAGE_ALIAS}.PVRZ").exists(), "WTPOOL2 alias already installed")
    parsed = parse_wed(wed)
    return {
        "schema": "bg2-ar1000-wtpool-periodic-bilinear-plan-v1",
        "status": "planned-not-run",
        "scope": {"area": AREA, "variant": "day", "night": "excluded", "family": FAMILY},
        "output": relative(output),
        "source": {"wed_archive": wed_archive, "wed_sha256": sha256_bytes(wed),
                   "tis_archive": tis_archive, "tis_sha256": sha256_bytes(legacy),
                   "frames": SOURCE_FRAMES, "coverage_cells": parsed["coverage"],
                   "liquid_cells_without_secondary": parsed["flagged_without_secondary"]},
        "rejection": {"candidate": relative(REJECTED_RUN),
                      "screenshot_sha256": SCREENSHOT_SHA256,
                      "cause": "SeedVR x4 amplified weak diagonal source grain into rectangular relief"},
        "recipe": {"spatial": "periodic-3x3-bilinear-x4", "generative_spatial": False,
                   "temporal": "cyclic-linear-6-to-36", "generative_temporal": False,
                   "native_fps": 15, "renderer_fps": 30, "overlay_alias": OVERLAY_ALIAS,
                   "page_alias": PAGE_ALIAS, "route2_strength": 0.0},
        "tests": "none-user-choice",
        "release": "not-requested",
    }


def execute(plan: dict[str, Any], output: Path) -> dict[str, Any]:
    require(not output.exists(), f"immutable run already exists: {output}")
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    wed, _wed_archive, legacy, _tis_archive = resolved_sources()
    source_images = decode_legacy_frames(legacy)
    source_dir = output / "00_source_x1"
    anchor_dir = output / "01_periodic_bilinear_x4"
    frame_dir = output / "02_frames_x4"
    source_dir.mkdir()
    anchor_dir.mkdir()
    frame_dir.mkdir()
    anchors = []
    for index, source in enumerate(source_images):
        source.save(source_dir / f"frame-{index:03d}.png")
        anchor = periodic_bilinear_x4(source)
        anchor.save(anchor_dir / f"frame-{index:03d}.png")
        anchors.append(anchor)
    frames = cyclic_linear_timeline(anchors)
    for index, frame in enumerate(frames):
        frame.save(frame_dir / f"frame-{index:03d}.png")
    tis, pvrz = build_overlay(frames, output / "03_overlay_x4")
    candidate = output / "candidate"
    candidate.mkdir()
    candidate_wed = replace_overlay_resref(
        replace_overlay_timeline(wed, 1, FRAME_COUNT), 1, OVERLAY_ALIAS
    )
    parsed = parse_wed(candidate_wed, OVERLAY_ALIAS)
    require(parsed["timeline_frames"] == FRAME_COUNT and parsed["source_speed"] == 1,
            "WTPOOL2 WED timeline mismatch")
    require(parsed["coverage"] == 37 and parsed["flagged_without_secondary"] == 0,
            "WTPOOL2 WED coverage mismatch")
    require(validate_polygons(candidate_wed) ==
            {"objects": 14, "wall_polygons": 301, "object_polygons": 32},
            "WTPOOL2 WED geometry mismatch")
    (candidate / "AR1000.WED").write_bytes(candidate_wed)
    shutil.copy2(tis, candidate / tis.name)
    shutil.copy2(pvrz, candidate / pvrz.name)
    rejected_energy = float(np.mean([
        high_frequency_energy(Image.open(path))
        for path in sorted((REJECTED_RUN / "03_anchor_x4").glob("frame-*.png"))
    ]))
    metrics = {
        "mean_seam_ratio_xy": seam_ratios(anchors),
        "mean_high_frequency_energy": round(float(np.mean([
            high_frequency_energy(frame) for frame in anchors
        ])), 4),
        "rejected_seedvr_mean_high_frequency_energy": round(rejected_energy, 4),
    }
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for path in sorted(candidate.iterdir()) if path.is_file()
    }
    manifest = {
        "schema": "bg2-upscale-area-animation-override-assets-v1",
        "status": "completed",
        "area": AREA,
        "purpose": "AR1000 day WTPOOL route1 without SeedVR grid amplification",
        "scope": {"variant": "day", "night": "excluded", "family": FAMILY},
        "qa_status": "pending-ingame",
        "recipe": plan["recipe"],
        "metrics": metrics,
        "files": files,
        "timeline": list(range(FRAME_COUNT)),
        "animation_speed_divisor": 1,
        "route2": {"strength": 0.0, "state": "deferred-pending-route1-qa"},
        "rollback": "Restore-AreaOverrideAssets.ps1 with generated installation backup",
    }
    write_json(candidate / "manifest.json", manifest)
    receipt = {
        "schema": "bg2-water-qa-candidate-receipt-v1",
        "status": "assembled-not-installed",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": plan["scope"],
        "candidate": relative(candidate),
        "manifest_sha256": sha256_file(candidate / "manifest.json"),
        "metrics": metrics,
        "qa": "pending-ingame",
        "tests": "none-user-choice",
    }
    write_json(output / "candidate-receipt.json", receipt)
    result = {
        "schema": "bg2-ar1000-wtpool-periodic-bilinear-run-v1",
        "status": "candidate-installable-pending-ingame-qa",
        "created_at_utc": receipt["created_at_utc"],
        "plan_sha256": sha256_file(output / "plan.json"),
        "candidate": relative(candidate),
        "candidate_manifest_sha256": receipt["manifest_sha256"],
        "candidate_receipt_sha256": sha256_file(output / "candidate-receipt.json"),
        "metrics": metrics,
        "tests": "none-user-choice",
        "release": "not-requested",
    }
    write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    require(ROOT == output or ROOT in output.parents, "output must remain inside workspace")
    plan = create_plan(output)
    result = execute(plan, output) if args.run else plan
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
