"""Build an isolated AR1000-day WTPOOL route-1 candidate; plan-only by default."""
from __future__ import annotations

import argparse
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
from water_wed import replace_overlay_resref, replace_overlay_timeline, validate_polygons


ROOT = Path(__file__).resolve().parents[2]
AREA = "AR1000"
OVERLAY = "WTPOOL"
OVERLAY_ALIAS = "WTPOOL1"
PAGE_ALIAS = f"{OVERLAY_ALIAS[0]}{OVERLAY_ALIAS[2:]}00"
FAMILY = "pool-wtpool"
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
WORKFLOW = ROOT / "pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json"
WORKFLOW_SHA256 = "30DEC619A4C1A3ECDE076C0926A5ED8EE29D5F2CA8B4EB89A75D3B5F7811B61E"
SOURCE_REGISTRY = (
    ROOT / "maps/water-batches/runs/ar0300n-reflections-alpha160-20260912-v10/registry-v3.json"
)
SOURCE_REGISTRY_SHA256 = "A1001BE419C374DD7B2D22B932EB47ABE4569E1B2E6C6E777835CB10E328EB4C"
BASE_SOURCE = (
    ROOT / "maps/AR1000/runs/seedvr2-7b-int8-lab-grid-2x5-x4-jour/05_build/x4"
)
CANONICAL_OVERLAY = ROOT / "maps/technical-overlays/WTPOOL/runs/seedvr2-7b-x2/03_build/x2"
CANONICAL_OVERLAY_HASHES = {
    "WTPOOL.TIS": "AAB8EEC55DCB08D742331A31D117544AF4085DF1CC5289D3B8FB0870BA992AED",
    "WPOOL00.PVRZ": "A15EE27AEA064AFF65BAED538338860C9AC527151A455A57AB91357204390143",
}
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
            "AR1000.WED ou WTPOOL.TIS absent du KEY")
    wed, wed_archive = resolve_resource(bifs, index[AREA, WED_TYPE])
    tis, count, entry_size, tis_archive = resolve_tileset_resource(
        bifs, index[OVERLAY, TIS_TYPE]
    )
    require(count == SOURCE_FRAMES and entry_size == LEGACY_ENTRY_SIZE,
            "WTPOOL stock n'est pas le TIS palette 6x64 attendu")
    return wed, wed_archive, tis, tis_archive


def parse_wed(payload: bytes, expected_overlay: str = OVERLAY) -> dict[str, Any]:
    require(payload[:8] == b"WED V1.3", "signature WED invalide")
    layers, _objects, headers = struct.unpack_from("<3I", payload, 8)
    require(2 <= layers <= 5, "nombre de couches WED invalide")
    parsed = []
    for index in range(layers):
        offset = headers + index * 24
        width, height, raw_name, unique, movement, tilemap, lookup = struct.unpack_from(
            "<HH8sHHII", payload, offset
        )
        parsed.append({
            "slot": index, "width": width, "height": height,
            "name": raw_name.rstrip(b"\0").decode("ascii").upper(),
            "unique": unique, "movement": movement, "tilemap": tilemap, "lookup": lookup,
        })
    overlay = parsed[1]
    require((overlay["name"], overlay["width"], overlay["height"]) ==
            (expected_overlay, 1, 1), "AR1000/WTPOOL slot1 divergent")
    start, count, secondary, flags, speed = struct.unpack_from(
        "<HHHBB", payload, overlay["tilemap"]
    )
    timeline = list(struct.unpack_from(f"<{count}H", payload, overlay["lookup"]))
    require((start, secondary, flags) == (0, 0xFFFF, 0), "cellule overlay WTPOOL divergente")
    require(timeline == list(range(count)), "timeline WTPOOL non séquentielle")
    base = parsed[0]
    coverage = 0
    without_secondary = 0
    for cell in range(base["width"] * base["height"]):
        offset = base["tilemap"] + cell * 10
        cell_secondary = struct.unpack_from("<H", payload, offset + 4)[0]
        cell_flags = payload[offset + 6]
        if cell_flags & (1 << overlay["slot"]):
            coverage += 1
            without_secondary += cell_secondary == 0xFFFF
    return {
        "layers": layers, "slots": [row["name"] for row in parsed],
        "base": base, "overlay": overlay, "coverage": coverage,
        "flagged_without_secondary": without_secondary, "source_speed": speed,
        "timeline_frames": count,
    }


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


def verify_live_files(base_paths: list[Path]) -> int:
    override = get_path("bg2ee_game_root") / "override"
    checked = 0
    for source in base_paths:
        live = override / source.name
        require(live.is_file() and sha256_file(live) == sha256_file(source),
                f"voie1 AR1000 live divergente : {source.name}")
        checked += 1
    for name, expected in CANONICAL_OVERLAY_HASHES.items():
        source = CANONICAL_OVERLAY / name
        live = override / name
        require(source.is_file() and sha256_file(source) == expected,
                f"candidat WTPOOL canonique divergent : {name}")
        require(live.is_file() and sha256_file(live) == expected,
                f"WTPOOL live divergent : {name}")
        checked += 1
    return checked


def build_plan(output: Path) -> dict[str, Any]:
    require(WORKFLOW.is_file() and sha256_file(WORKFLOW) == WORKFLOW_SHA256,
            "workflow SeedVR absent ou divergent")
    require(SOURCE_REGISTRY.is_file() and sha256_file(SOURCE_REGISTRY) == SOURCE_REGISTRY_SHA256,
            "registre courant absent ou divergent")
    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    require(not any(entry["wed"]["resref"] == AREA for entry in registry["entries"]),
            "AR1000 possède déjà une entrée route2 : la voie1 q0 ne serait plus isolée")
    wed, wed_archive, tis, tis_archive = resolved_sources()
    parsed = parse_wed(wed)
    require(parsed["coverage"] == 37 and parsed["flagged_without_secondary"] == 0,
            "contrat voie1 AR1000 divergent")
    require(parsed["timeline_frames"] == SOURCE_FRAMES and parsed["source_speed"] == 6,
            "timeline WTPOOL stock divergente")
    polygons = validate_polygons(wed)
    require(polygons == {"objects": 14, "wall_polygons": 301, "object_polygons": 32},
            "géométrie WED AR1000 divergente")
    base, base_paths = tis_metadata(AREA, BASE_SOURCE)
    checked = verify_live_files(base_paths)
    override = get_path("bg2ee_game_root") / "override"
    live_wed = override / f"{AREA}.WED"
    require(not live_wed.exists() or sha256_file(live_wed) == sha256_bytes(wed),
            "AR1000.WED live divergent du stock")
    for name in (f"{OVERLAY_ALIAS}.TIS", f"{PAGE_ALIAS}.PVRZ"):
        require(not (override / name).exists(), f"alias déjà présent dans override : {name}")
    return {
        "schema": "bg2-ar1000-wtpool-route1-plan-v1",
        "output": str(output),
        "scope": {
            "area": AREA, "variant": "day", "night": "excluded",
            "overlay": OVERLAY, "alias": OVERLAY_ALIAS, "family": FAMILY,
            "coverage_cells": parsed["coverage"],
        },
        "stock": {
            "wed_archive": wed_archive, "wed_sha256": sha256_bytes(wed),
            "wed_bytes": len(wed), "polygons": polygons,
            "overlay_archive": tis_archive, "overlay_sha256": sha256_bytes(tis),
            "frames": SOURCE_FRAMES, "frame_size": [64, 64], "speed": 6,
        },
        "route1": {
            "base_state": "already-conform-installed",
            "base_source": relative(BASE_SOURCE), "base_tis": base,
            "all_liquid_cells_have_secondary": True,
            "alpha_central_action": "none",
            "canonical_x2_baseline": relative(CANONICAL_OVERLAY),
            "canonical_x2_issue": "non-periodic dark right/bottom borders",
            "new_overlay": {
                "scale": 4, "color_correction_method": "none",
                "periodic_context": "3x3", "alias": OVERLAY_ALIAS,
                "page": PAGE_ALIAS,
            },
        },
        "timeline": {
            "source_fps": SOURCE_FPS, "native_fps": NATIVE_FPS,
            "target_fps": TARGET_FPS, "frames": FRAME_COUNT,
            "interpolator": "apollo-8", "runtime_blend": "linear",
        },
        "route2": {
            "state": "deferred-until-route1-ingame-qa", "strength": 0.0,
            "registry": relative(SOURCE_REGISTRY),
            "registry_sha256": SOURCE_REGISTRY_SHA256,
            "fallback": "q0-native",
        },
        "verified_live_files": checked,
        "tests": "not-run-user-choice", "installation": "not-run",
        "qa": "pending-ingame", "release": "not-requested",
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
    return paths, {
        "manifest": relative(upscale / "manifest.json"),
        "manifest_sha256": sha256_file(upscale / "manifest.json"),
        "mean_seam_ratio_xy": [round(float(value), 4) for value in mean_ratio],
    }


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
    return paths, {
        "filter": filter_text, "raw_frames": len(raw_paths),
        "anchor_rgb_mae": [round(value, 6) for value in anchor_mae],
    }


def build_overlay(frames: list[Path], output: Path) -> tuple[Path, Path]:
    require(len(frames) == FRAME_COUNT, "nombre de frames WTPOOL candidat invalide")
    output.mkdir()
    canvas = np.zeros((PAGE_SIZE, PAGE_SIZE, 4), dtype=np.uint8)
    entries = []
    for index, path in enumerate(frames):
        row, column = divmod(index, ATLAS_COLUMNS)
        x, y = column * ATLAS_STRIDE + PAD, row * ATLAS_STRIDE + PAD
        with Image.open(path) as image:
            frame = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        require(frame.shape == (TILE_SIZE, TILE_SIZE, 4), f"frame invalide : {path}")
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
    metadata, pages = tis_metadata(OVERLAY_ALIAS, output)
    require(metadata["tile_count"] == FRAME_COUNT and pages == [tis_path, pvrz],
            "inventaire TIS/PVRZ WTPOOL1 incohérent")
    return tis_path, pvrz


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
    wed_payload = replace_overlay_timeline(wed, 1, FRAME_COUNT)
    wed_payload = replace_overlay_resref(wed_payload, 1, OVERLAY_ALIAS)
    parsed = parse_wed(wed_payload, OVERLAY_ALIAS)
    require(parsed["timeline_frames"] == FRAME_COUNT and parsed["source_speed"] == 1,
            "timeline WTPOOL candidate divergente")
    require(validate_polygons(wed_payload) == plan["stock"]["polygons"],
            "géométrie WED candidate divergente")
    wed_path = candidate / f"{AREA}.WED"
    wed_path.write_bytes(wed_payload)
    shutil.copy2(tis, candidate / tis.name)
    shutil.copy2(pvrz, candidate / pvrz.name)
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path).lower()}
        for path in sorted(candidate.iterdir()) if path.is_file()
    }
    manifest = {
        "schema": "bg2-upscale-area-animation-override-assets-v1",
        "status": "completed", "area": AREA,
        "purpose": "AR1000 day isolated WTPOOL route1: periodic x4, 36 phases at 15 Hz, q0",
        "scope": {"variant": "day", "night": "excluded", "family": FAMILY},
        "qa_status": "pending-ingame", "files": files,
        "timeline": list(range(FRAME_COUNT)), "animation_speed_divisor": 1,
        "route2": {"strength": 0.0, "state": "not-added-pending-route1-qa"},
        "rollback": "Restore-AreaOverrideAssets.ps1 with generated install backup",
    }
    write_json(candidate / "manifest.json", manifest)
    receipt = {
        "schema": "bg2-water-qa-candidate-receipt-v1",
        "status": "assembled-not-installed", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {"area": AREA, "variant": "day", "night": "excluded", "family": FAMILY},
        "candidate": relative(candidate),
        "manifest_sha256": sha256_file(candidate / "manifest.json"),
        "files": files, "source_plan_sha256": sha256_file(output / "plan.json"),
        "tests": "not-run-user-choice", "installation": "not-run",
        "qa": "pending-ingame", "release": "not-requested",
    }
    write_json(output / "candidate-receipt.json", receipt)
    result = {
        "schema": "bg2-ar1000-wtpool-route1-run-v1",
        "status": "candidate-installable-pending-ingame-qa",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": sha256_file(output / "plan.json"),
        "seedvr": seedvr, "apollo": apollo,
        "candidate": relative(candidate),
        "candidate_manifest_sha256": sha256_file(candidate / "manifest.json"),
        "candidate_receipt": relative(output / "candidate-receipt.json"),
        "candidate_receipt_sha256": sha256_file(output / "candidate-receipt.json"),
        "route2": "deferred-until-route1-ingame-qa", "route2_strength": 0.0,
        "tests": "not-run-user-choice", "installation": "not-run",
        "qa": "pending-ingame", "release": "not-requested",
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
