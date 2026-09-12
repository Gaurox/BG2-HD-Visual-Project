"""Build the AR0404 WTSEW x4/30 FPS route2 pilot; plan-only by default."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageStat

from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from build_water_overlay_30fps_test import write_pvrz
from build_wtlake_timeline_batch import pvrz_metadata, tis_metadata
from workspace_paths import get_path
from water_wed import replace_overlay_timeline, validate_polygons


ROOT = Path(__file__).resolve().parents[2]
AREA = "AR0404"
OVERLAY = "WTSEW"
PAGE = "WSEW00"
WED_TYPE = 0x03E9
TIS_TYPE = 0x03EB
LEGACY_ENTRY_SIZE = 5120
SOURCE_FRAMES = 6
SOURCE_FPS = 2.5
NATIVE_FPS = 15.0
TARGET_FPS = 30.0
PHASES_PER_TRANSITION = 6
FRAME_COUNT = SOURCE_FRAMES * PHASES_PER_TRANSITION
TILE_SIZE = 256
PAD = 4
ATLAS_COLUMNS = 7
ATLAS_STRIDE = TILE_SIZE + PAD * 2
PAGE_SIZE = 2048
STRENGTH = 0.70
MATERIAL_ID = 4
WORKFLOW = ROOT / "pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json"
WORKFLOW_SHA256 = "30DEC619A4C1A3ECDE076C0926A5ED8EE29D5F2CA8B4EB89A75D3B5F7811B61E"
SOURCE_REGISTRY = (
    ROOT / "maps/water-batches/runs/ar0204-ar1600-validated-20260912-v1/registry-v3.json"
)
SOURCE_REGISTRY_SHA256 = "F67E49246BD1468B6C3C086B1F21924D599B09FD3C2C9F14B292EE7E92C1C864"
BASE_SOURCE = (
    ROOT / "maps/water-batches/runs/qa-candidates-20260912-v1/"
    "batches/sewage-wtsew/maps/AR0404"
)
TOPAZ_FFMPEG = get_path("topaz_video_ffmpeg")
TOPAZ_MODELS = get_path("topaz_video_models")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def resolved_sources() -> tuple[bytes, str, bytes, str]:
    bifs, resources = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in resources}
    require((AREA, WED_TYPE) in index and (OVERLAY, TIS_TYPE) in index,
            "AR0404.WED ou WTSEW.TIS absent du KEY")
    wed, wed_archive = resolve_resource(bifs, index[AREA, WED_TYPE])
    tis, count, entry_size, tis_archive = resolve_tileset_resource(
        bifs, index[OVERLAY, TIS_TYPE]
    )
    require(count == SOURCE_FRAMES and entry_size == LEGACY_ENTRY_SIZE,
            "WTSEW stock n'est pas le TIS palette 6x64 attendu")
    return wed, wed_archive, tis, tis_archive


def parse_wed(payload: bytes) -> dict[str, Any]:
    require(payload[:8] == b"WED V1.3", "signature WED invalide")
    layers, _objects, headers = struct.unpack_from("<3I", payload, 8)
    require(2 <= layers <= 5, "nombre de couches WED invalide")
    slots = []
    parsed = []
    for index in range(layers):
        offset = headers + index * 24
        width, height, raw_name, unique, movement, tilemap, lookup = struct.unpack_from(
            "<HH8sHHII", payload, offset
        )
        name = raw_name.rstrip(b"\0").decode("ascii").upper()
        slots.append(name)
        parsed.append({"slot": index, "width": width, "height": height, "name": name,
                       "unique": unique, "movement": movement, "tilemap": tilemap,
                       "lookup": lookup})
    overlay = parsed[1]
    require((overlay["name"], overlay["width"], overlay["height"]) == (OVERLAY, 1, 1),
            "AR0404/WTSEW slot1 divergent")
    start, count, secondary, flags, speed = struct.unpack_from(
        "<HHHBB", payload, overlay["tilemap"]
    )
    timeline = list(struct.unpack_from(f"<{count}H", payload, overlay["lookup"]))
    require((start, count, secondary, flags, speed, timeline) ==
            (0, SOURCE_FRAMES, 0xFFFF, 0, 6, list(range(SOURCE_FRAMES))),
            "timeline WTSEW stock divergente")
    base = parsed[0]
    coverage = sum(
        bool(payload[base["tilemap"] + cell * 10 + 6] & (1 << overlay["slot"]))
        for cell in range(base["width"] * base["height"])
    )
    return {"layers": layers, "slots": slots, "base": base, "overlay": overlay,
            "coverage": coverage, "source_speed": speed}


def decode_legacy_frames(payload: bytes) -> list[Image.Image]:
    frames = []
    for index in range(SOURCE_FRAMES):
        offset = index * LEGACY_ENTRY_SIZE
        palette = np.frombuffer(payload, dtype=np.uint8, count=1024, offset=offset).reshape(256, 4)
        indices = np.frombuffer(
            payload, dtype=np.uint8, count=64 * 64, offset=offset + 1024
        ).reshape(64, 64)
        rgb = palette[:, [2, 1, 0]][indices]
        rgba = np.dstack((rgb, np.full((64, 64), 255, dtype=np.uint8)))
        frames.append(Image.fromarray(rgba, mode="RGBA"))
    return frames


def verify_live_registry(registry: dict[str, Any]) -> int:
    override = get_path("bg2ee_game_root") / "override"
    checked: dict[str, str] = {}
    for entry in registry["entries"]:
        evidence = [
            (entry["wed"]["resref"] + ".WED", entry["wed"]["sha256"],
             entry["allow_stock_wed_when_override_absent"]),
            (entry["base_tis"]["resref"] + ".TIS", entry["base_tis"]["sha256"], False),
            (entry["overlay"]["tis_resref"] + ".TIS", entry["overlay"]["tis_sha256"], False),
        ]
        evidence += [
            (page["resref"] + ".PVRZ", page["sha256"], False)
            for page in entry["base_tis"]["pages"] + entry["overlay"]["pages"]
        ]
        for name, expected, stock_allowed in evidence:
            path = override / name
            if stock_allowed and name.endswith(".WED") and not path.exists():
                continue
            if name not in checked:
                require(path.is_file() and sha256_file(path) == expected,
                        f"preuve live divergente : {name}")
                checked[name] = expected
    return len(checked)


def build_plan(output: Path) -> dict[str, Any]:
    require(SOURCE_REGISTRY.is_file() and sha256_file(SOURCE_REGISTRY) == SOURCE_REGISTRY_SHA256,
            "registre source absent ou divergent")
    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    checked = verify_live_registry(registry)
    wed, wed_archive, tis, tis_archive = resolved_sources()
    parsed = parse_wed(wed)
    require(parsed["coverage"] == 140, "couverture WTSEW AR0404 divergente")
    require(validate_polygons(wed) == {"objects": 1, "wall_polygons": 83, "object_polygons": 2},
            "géométrie WED AR0404 divergente")
    base, base_paths = tis_metadata(AREA, BASE_SOURCE)
    override = get_path("bg2ee_game_root") / "override"
    for source in base_paths:
        live = override / source.name
        require(live.is_file() and sha256_file(live) == sha256_file(source),
                f"voie1 AR0404 live divergente : {source.name}")
    return {
        "schema": "bg2-wtsew-route2-pilot-plan-v1",
        "output": str(output),
        "scope": {"area": AREA, "variant": "day-or-unique", "overlay": OVERLAY,
                  "family": "sewage-wtsew", "coverage_cells": parsed["coverage"]},
        "stock": {"wed_archive": wed_archive, "wed_sha256": sha256_bytes(wed),
                  "overlay_archive": tis_archive, "overlay_sha256": sha256_bytes(tis),
                  "frames": SOURCE_FRAMES, "frame_size": [64, 64], "speed": 6},
        "route1": {"state": "already-installed", "source": relative(BASE_SOURCE),
                   "base_tis": base},
        "upscale": {"model": "seedvr2_7b_int8_convrot.safetensors", "scale": 4,
                    "color_correction_method": "none", "periodic_context": "3x3"},
        "timeline": {"source_fps": SOURCE_FPS, "native_fps": NATIVE_FPS,
                     "target_fps": TARGET_FPS, "frames": FRAME_COUNT,
                     "interpolator": "apo-8", "runtime_blend": "linear"},
        "route2": {"strength": STRENGTH, "material": "sewage", "material_id": MATERIAL_ID,
                   "fallback": "q0-native"},
        "source_registry": relative(SOURCE_REGISTRY),
        "source_registry_sha256": SOURCE_REGISTRY_SHA256,
        "verified_live_registry_files": checked,
        "tests": "not-run",
        "installation": "not-run",
        "release": "not-requested",
    }


def prepare_periodic_inputs(stock: list[Image.Image], output: Path) -> tuple[Path, Path]:
    source = output / "00_source_x1"
    rgb_dir = output / "01_periodic_x1/rgb"
    alpha_dir = output / "01_periodic_x1/alpha"
    source.mkdir()
    rgb_dir.mkdir(parents=True)
    alpha_dir.mkdir(parents=True)
    for index, image in enumerate(stock):
        image.save(source / f"frame-{index:03d}.png")
        rgb = Image.new("RGB", (192, 192))
        alpha = Image.new("L", (192, 192), 255)
        for y in range(3):
            for x in range(3):
                rgb.paste(image.convert("RGB"), (x * 64, y * 64))
        rgb.save(rgb_dir / f"frame_{index:03d}.png")
        alpha.save(alpha_dir / f"frame_{index:03d}.png")
    return rgb_dir, alpha_dir


def upscale_anchors(rgb_dir: Path, alpha_dir: Path, output: Path) -> tuple[list[Path], dict[str, Any]]:
    upscale = output / "02_upscale_x4"
    command = [
        os.fspath(shutil.which("python") or "python"), "-B",
        os.fspath(ROOT / "pipeline/scripts/upscale_animation_frames.py"),
        os.fspath(rgb_dir), os.fspath(alpha_dir), os.fspath(upscale),
        "--scale", "4", "--pad", "0", "--color-correction-method", "none",
        "--workflow", os.fspath(WORKFLOW),
    ]
    subprocess.run(command, check=True)
    manifest = json.loads((upscale / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["parameters"]["color_correction_method"] == "none",
            "SeedVR n'a pas conservé color_correction=none")
    anchors = output / "03_anchor_x4"
    anchors.mkdir()
    paths = []
    ratios = []
    for index in range(SOURCE_FRAMES):
        source = upscale / "rgba" / f"frame_{index:03d}.png"
        with Image.open(source) as image:
            require(image.size == (768, 768), "sortie SeedVR périodique invalide")
            frame = image.convert("RGBA").crop((256, 256, 512, 512))
            destination = anchors / f"frame-{index:03d}.png"
            frame.save(destination)
            array = np.asarray(frame.convert("RGB"), dtype=np.float32)
            seam_x = np.abs(array[:, 0] - array[:, -1]).mean()
            seam_y = np.abs(array[0] - array[-1]).mean()
            inner_x = max(float(np.abs(array[:, 1:] - array[:, :-1]).mean()), 1e-6)
            inner_y = max(float(np.abs(array[1:] - array[:-1]).mean()), 1e-6)
            ratios.append([float(seam_x / inner_x), float(seam_y / inner_y)])
            paths.append(destination)
    mean_ratio = np.mean(np.asarray(ratios), axis=0)
    require(bool(np.all(mean_ratio < 2.0)), f"raccord périodique SeedVR divergent : {mean_ratio}")
    return paths, {"manifest": relative(upscale / "manifest.json"),
                   "manifest_sha256": sha256_file(upscale / "manifest.json"),
                   "mean_seam_ratio_xy": [round(float(value), 4) for value in mean_ratio]}


def image_mae(left: Image.Image, right: Image.Image) -> float:
    difference = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    return sum(ImageStat.Stat(difference).mean) / 3.0


def interpolate(anchors: list[Path], output: Path) -> tuple[list[Path], dict[str, Any]]:
    inputs = output / "04_apollo_input_x4"
    raw = output / "05_apollo_15hz"
    frames = output / "06_frames_x4"
    inputs.mkdir()
    raw.mkdir()
    frames.mkdir()
    for index, source in enumerate(anchors + [anchors[0]]):
        with Image.open(source) as image:
            image.convert("RGB").save(inputs / f"in_{index:04d}.png")
    environment = dict(os.environ)
    environment["TVAI_MODEL_DIR"] = str(TOPAZ_MODELS)
    environment["TVAI_MODEL_DATA_DIR"] = str(TOPAZ_MODELS)
    filter_text = f"tvai_fi=model=apo-8:fps={NATIVE_FPS:g}:rdt=-0.01:device=-2"
    subprocess.run([
        str(TOPAZ_FFMPEG), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", f"{SOURCE_FPS:g}", "-i", str(inputs / "in_%04d.png"),
        "-vf", filter_text, "-pix_fmt", "rgb24", str(raw / "out_%04d.png"),
    ], check=True, env=environment)
    raw_paths = sorted(raw.glob("out_*.png"))
    require(len(raw_paths) in (FRAME_COUNT, FRAME_COUNT + 1),
            f"Apollo-8 a produit {len(raw_paths)} frames")
    anchor_mae = []
    for segment in range(SOURCE_FRAMES):
        anchor_phase = segment * PHASES_PER_TRANSITION
        shutil.copy2(anchors[segment], frames / f"frame-{anchor_phase:03d}.png")
        with Image.open(raw_paths[anchor_phase]) as generated, Image.open(anchors[segment]) as expected:
            anchor_mae.append(image_mae(generated, expected))
        for phase in range(1, PHASES_PER_TRANSITION):
            index = anchor_phase + phase
            with Image.open(raw_paths[index]) as generated:
                rgba = generated.convert("RGBA")
                rgba.putalpha(255)
                rgba.save(frames / f"frame-{index:03d}.png")
    paths = [frames / f"frame-{index:03d}.png" for index in range(FRAME_COUNT)]
    require(all(path.is_file() for path in paths), "timeline Apollo-8 incomplète")
    return paths, {"filter": filter_text, "raw_frames": len(raw_paths),
                   "anchor_rgb_mae": [round(value, 6) for value in anchor_mae]}


def build_overlay(frames: list[Path], output: Path) -> tuple[Path, Path]:
    output.mkdir()
    canvas = np.zeros((PAGE_SIZE, PAGE_SIZE, 4), dtype=np.uint8)
    entries = []
    for index, path in enumerate(frames):
        row, column = divmod(index, ATLAS_COLUMNS)
        x, y = column * ATLAS_STRIDE + PAD, row * ATLAS_STRIDE + PAD
        with Image.open(path) as image:
            frame = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        canvas[y:y + TILE_SIZE, x:x + TILE_SIZE] = frame
        canvas[y - PAD:y, x:x + TILE_SIZE] = frame[:1]
        canvas[y + TILE_SIZE:y + TILE_SIZE + PAD, x:x + TILE_SIZE] = frame[-1:]
        canvas[y - PAD:y + TILE_SIZE + PAD, x - PAD:x] = \
            canvas[y - PAD:y + TILE_SIZE + PAD, x:x + 1]
        canvas[y - PAD:y + TILE_SIZE + PAD, x + TILE_SIZE:x + TILE_SIZE + PAD] = \
            canvas[y - PAD:y + TILE_SIZE + PAD, x + TILE_SIZE - 1:x + TILE_SIZE]
        entries.append((0, x, y))
    pvrz = output / f"{PAGE}.PVRZ"
    write_pvrz(Image.fromarray(canvas, mode="RGBA"), pvrz)
    tis = bytearray(b"TIS V1  ")
    tis += struct.pack("<IIII", FRAME_COUNT, 12, 24, TILE_SIZE)
    for entry in entries:
        tis += struct.pack("<3I", *entry)
    tis_path = output / f"{OVERLAY}.TIS"
    tis_path.write_bytes(tis)
    return tis_path, pvrz


def build_registry(plan: dict[str, Any], wed_path: Path, tis: Path, pvrz: Path,
                   output: Path) -> Path:
    registry = copy.deepcopy(json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8")))
    require(not any(entry["wed"]["resref"] == AREA for entry in registry["entries"]),
            "AR0404 déjà présent dans le registre route2")
    entry = {
        "id": "wtsew-ar0404-slot1-q070-v3",
        "state": "candidate-installable-pending-qa",
        "wed": {"resref": AREA, "sha256": sha256_file(wed_path),
                "grid": {"width": 51, "height": 47},
                "overlay_slots": [AREA, OVERLAY, "", "", ""]},
        "base_tis": plan["route1"]["base_tis"],
        "overlay": {"slot": 1, "tis_resref": OVERLAY, "tis_sha256": sha256_file(tis),
                    "tis_bytes": tis.stat().st_size, "tile_count": FRAME_COUNT,
                    "tile_dimension": TILE_SIZE, "pages": [pvrz_metadata(pvrz)]},
        "approved_strength": STRENGTH,
        "overlay_coverage_cells": 140,
        "allow_stock_wed_when_override_absent": False,
        "material_id": MATERIAL_ID,
        "temporal_overlay": {"mode": "atlas-linear", "frame_count": FRAME_COUNT,
                             "source_fps": NATIVE_FPS, "target_fps": TARGET_FPS,
                             "atlas_columns": ATLAS_COLUMNS,
                             "atlas_stride_pixels": ATLAS_STRIDE,
                             "atlas_padding_pixels": PAD},
        "qa": {"status": "pending-ingame", "reference": "AR0404 WTSEW q=0.70 pilot"},
    }
    registry["entries"].append(entry)
    registry["status"] = "experimental-pending-ingame-qa"
    registry["experiment"] = {
        "scope": [AREA], "family": "sewage-wtsew",
        "previous_registry": relative(SOURCE_REGISTRY),
        "previous_registry_sha256": SOURCE_REGISTRY_SHA256,
        "untargeted_entries": "unchanged", "tests": "not-run-user-choice",
    }
    destination = output / "registry-v3.json"
    write_json(destination, registry)
    return destination


def execute(plan: dict[str, Any], output: Path) -> dict[str, Any]:
    require(not output.exists(), f"run déjà présent : {output}")
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    wed, _wed_archive, legacy, _tis_archive = resolved_sources()
    rgb_dir, alpha_dir = prepare_periodic_inputs(decode_legacy_frames(legacy), output)
    anchors, seedvr = upscale_anchors(rgb_dir, alpha_dir, output)
    frames, apollo = interpolate(anchors, output)
    tis, pvrz = build_overlay(frames, output / "07_overlay_x4")
    candidate = output / "08_candidate"
    candidate.mkdir()
    wed_path = candidate / f"{AREA}.WED"
    wed_path.write_bytes(replace_overlay_timeline(wed, 1, FRAME_COUNT))
    require(validate_polygons(wed_path.read_bytes()) ==
            {"objects": 1, "wall_polygons": 83, "object_polygons": 2},
            "géométrie WED candidate divergente")
    shutil.copy2(tis, candidate / tis.name)
    shutil.copy2(pvrz, candidate / pvrz.name)
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path).lower()}
        for path in sorted(candidate.iterdir()) if path.is_file()
    }
    write_json(candidate / "manifest.json", {
        "schema": "bg2-upscale-area-animation-override-assets-v1",
        "status": "completed", "area": AREA,
        "purpose": "WTSEW x4 36-phase 15 Hz plus route2 30 FPS sewage pilot q0.70",
        "qa_status": "pending-ingame", "files": files,
        "timeline": list(range(FRAME_COUNT)), "animation_speed_divisor": 1,
        "rollback": "Restore-AreaOverrideAssets.ps1 with generated install backup",
    })
    registry = build_registry(plan, wed_path, candidate / tis.name, candidate / pvrz.name, output)
    result = {
        "schema": "bg2-wtsew-route2-pilot-run-v1",
        "status": "candidate-installable-pending-qa",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": sha256_file(output / "plan.json"),
        "seedvr": seedvr, "apollo": apollo,
        "candidate": relative(candidate),
        "candidate_manifest_sha256": sha256_file(candidate / "manifest.json"),
        "registry": relative(registry), "registry_sha256": sha256_file(registry),
        "route2_strength": STRENGTH, "tests": "not-run-user-choice",
        "installation": "not-run", "qa": "pending-ingame", "release": "not-requested",
    }
    write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    plan = build_plan(output)
    if not args.run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(execute(plan, output), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
