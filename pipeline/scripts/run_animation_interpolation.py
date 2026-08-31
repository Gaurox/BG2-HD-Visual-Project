"""Prepare, audit and package interpolated x4 area-animation frames.

This tool never modifies the game. It creates a small, hash-checked runtime
patch which must be installed later with Install-AreaAnimation-Interpolation-Patch.ps1.
Only one BAM cycle is supported in this first generic version; multi-cycle
resources stop explicitly rather than receiving an unsafe guessed timeline.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

import build_animation_runtime_pack as runtime_pack
from workspace_paths import get_path


HANDOFF_SCHEMA = "bg2-upscale-area-animation-interpolation-handoff-v1"
INTAKE_SCHEMA = "bg2-upscale-area-animation-interpolation-intake-v1"
INTERPOLATION_SCHEMA = "bg2-upscale-area-animation-interpolation-run-v1"
PATCH_SCHEMA = "bg2-upscale-area-animation-frame-expansion-test-v1"
SCALE = 4

DEFAULT_TVAI_FFMPEG = get_path("topaz_video_ffmpeg")
DEFAULT_TVAI_MODEL_DIR = get_path("topaz_video_models")
DEFAULT_FI_MODEL = "apo-8"
# Topaz drops frames it judges duplicated as soon as rdt is positive, which would
# silently break the exact frame-count contract. The filter clamps rdt to
# [-0.01, 0.2] and treats any value at or below zero as "never remove".
FI_REPLACE_DUPLICATE_THRESHOLD = -0.01


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"fichier absent : {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def validate_base_pack(pack_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate a runtime pack while allowing its installer-owned backup folder.

    The generic installer stores reversible backups under ``install-backups`` in
    the pack directory. That operational folder is not part of the immutable
    asset inventory and must not invalidate an otherwise exact base pack.
    """
    pack_root = pack_root.resolve()
    manifest = load_json(pack_root / "manifest.json")
    require(
        manifest.get("schema") == runtime_pack.PACK_SCHEMA
        and manifest.get("status") == "completed"
        and int(manifest.get("scale", 0)) == SCALE,
        f"pack runtime incompatible : {pack_root}",
    )
    resources = sorted(manifest.get("resources") or [], key=lambda item: str(item.get("resref", "")).upper())
    require(resources and int(manifest.get("resource_count", 0)) == len(resources), "inventaire pack invalide")
    require(int(manifest.get("frame_count", 0)) == sum(int(item.get("frame_count", 0)) for item in resources),
            "nombre de frames pack invalide")
    expected_registry = runtime_pack.registry_from_resources(resources)
    registry_name = str(manifest.get("registry", ""))
    registry_path = pack_root / registry_name
    require(registry_name == runtime_pack.REGISTRY_NAME and registry_path.is_file(), "registre pack invalide")
    require(registry_path.read_bytes() == expected_registry, "registre pack incohérent")
    require(sha256_file(registry_path) == str(manifest.get("registry_sha256", "")).lower(),
            "hash du registre pack incohérent")
    expected_names = {"manifest.json", runtime_pack.REGISTRY_NAME}
    for resource in resources:
        runtime_pack.resource_binary_from_manifest(resource)
        for asset in resource.get("assets") or []:
            name = str(asset.get("name", ""))
            require(Path(name).name == name and name not in expected_names, f"nom asset pack invalide : {name}")
            expected_names.add(name)
            path = pack_root / name
            require(path.is_file() and path.stat().st_size == int(asset.get("bytes", -1)) and
                    sha256_file(path) == str(asset.get("sha256", "")).lower(),
                    f"asset pack incohérent : {path}")
    actual_files = {path.name for path in pack_root.iterdir() if path.is_file()}
    require(actual_files == expected_names, "fichiers supplémentaires ou manquants dans le pack")
    extra_dirs = {path.name for path in pack_root.iterdir() if path.is_dir()}
    require(extra_dirs.issubset({"install-backups"}), f"dossiers inattendus dans le pack : {sorted(extra_dirs)}")
    return manifest, resources


def apply_interpolation_patches(
    resources: list[dict[str, Any]],
    base_registry_sha256: str,
    patch_paths: list[Path],
) -> tuple[list[dict[str, Any]], str, list[dict[str, str]]]:
    """Apply prior interpolation deltas to a pack definition without copying assets.

    This is required when a second resref is interpolated while a first one is
    already active in the game. Every delta is chained by registry hash, so a
    patch built from an obsolete global state is rejected before any output.
    """
    effective = copy.deepcopy(resources)
    actual_base_hash = sha256_bytes(runtime_pack.registry_from_resources(effective))
    require(actual_base_hash == base_registry_sha256, "registre de base non reproductible")
    current_hash = actual_base_hash
    provenance: list[dict[str, str]] = []
    seen_resrefs: set[str] = set()
    for requested_path in patch_paths:
        patch_root = requested_path.resolve()
        manifest_path = patch_root / "manifest.json"
        patch = load_json(manifest_path)
        resref = normalise_resref(str(patch.get("resref", "")))
        require(
            patch.get("schema") == PATCH_SCHEMA
            and patch.get("status") == "completed"
            and int(patch.get("scale", 0)) == SCALE
            and resref not in seen_resrefs,
            f"patch interpolation incompatible ou dupliqué : {patch_root}",
        )
        require(str(patch.get("base_registry_sha256", "")).lower() == current_hash,
                f"{resref}: patch fondé sur un registre global différent")
        replacement = copy.deepcopy(patch.get("resource") or {})
        require(str(replacement.get("resref", "")).upper() == resref, f"{resref}: ressource patch invalide")
        runtime_pack.resource_binary_from_manifest(replacement)
        matches = [index for index, resource in enumerate(effective) if str(resource.get("resref", "")).upper() == resref]
        require(len(matches) == 1, f"{resref}: ressource absente ou dupliquée dans la base effective")
        effective[matches[0]] = replacement
        target_registry = runtime_pack.registry_from_resources(effective)
        target_hash = sha256_bytes(target_registry)
        require(target_hash == str(patch.get("target_registry_sha256", "")).lower(),
                f"{resref}: registre cible du patch incohérent")
        registry_path = patch_root / str(patch.get("target_registry", ""))
        require(registry_path.is_file() and sha256_file(registry_path) == target_hash,
                f"{resref}: registre fichier du patch incohérent")
        current_hash = target_hash
        seen_resrefs.add(resref)
        provenance.append({
            "patch": patch_root.as_posix(),
            "manifest_sha256": sha256_file(manifest_path),
            "resref": resref,
            "target_registry_sha256": target_hash,
        })
    return effective, current_hash, provenance


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def normalise_resref(value: str) -> str:
    resref = value.upper()
    require(bool(re.fullmatch(r"[A-Z0-9]{1,8}", resref)), f"resref invalide : {value}")
    return resref


def frame_value(record: dict[str, Any], *names: str, fallback: dict[str, Any] | None = None) -> Any:
    for name in names:
        if name in record:
            return record[name]
    if fallback is not None:
        for name in names:
            if name in fallback:
                return fallback[name]
    raise RuntimeError(f"champ frame absent : {' / '.join(names)}")


def relative_file(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"chemin hors manifeste : {value}") from exc
    if not path.is_file():
        raise RuntimeError(f"asset absent : {path}")
    return path


def grouped_runs(values: list[int]) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    for value in values:
        if runs and runs[-1][0] == value:
            runs[-1] = (value, runs[-1][1] + 1)
        else:
            runs.append((value, 1))
    return runs


def image_mae(left: Image.Image, right: Image.Image) -> float:
    difference = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    return sum(ImageStat.Stat(difference).mean) / 3.0


def parse_numbered_pngs(directory: Path) -> list[Path]:
    files = sorted(path for path in directory.glob("*.png") if path.is_file())
    require(files, f"aucun PNG dans : {directory}")
    numbers: list[int] = []
    for path in files:
        match = re.search(r"(\d+)$", path.stem)
        require(match is not None, f"numérotation absente : {path.name}")
        numbers.append(int(match.group(1)))
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    require(numbers == expected, "numérotation PNG non contiguë")
    return files


def duration_tolerance(fps: float) -> float:
    return max(0.05, 1.25 / fps)


def read_upscale_frame(
    record: dict[str, Any],
    root: Path,
    source_record: dict[str, Any],
) -> dict[str, Any]:
    index = int(record.get("frame", -1))
    logical = [int(value) for value in frame_value(record, "logical_size_x1", "source_size", fallback=source_record)]
    physical_value = record.get("physical_size_xn") or record.get("x4_size")
    physical = [int(value) for value in physical_value] if physical_value else [logical[0] * SCALE, logical[1] * SCALE]
    centre = [int(value) for value in frame_value(record, "centre_x1", "centre", fallback=source_record)]
    require(len(logical) == len(physical) == len(centre) == 2, f"frame {index}: géométrie invalide")
    require(
        physical == [logical[0] * SCALE, logical[1] * SCALE],
        f"frame {index}: dimensions physiques incompatibles avec x4",
    )
    rgb = relative_file(root, str(frame_value(record, "rgb_xn", "rgb_x4")))
    alpha = relative_file(root, str(frame_value(record, "alpha_xn", "alpha_x4")))
    aligned_value = record.get("aligned_rgba_xn") or record.get("rgba_x4")
    aligned = relative_file(root, str(aligned_value)) if aligned_value else None
    crop = record.get("runtime_crop_box_xn") or [0, 0, physical[0], physical[1]]
    crop = [int(value) for value in crop]
    require(len(crop) == 4 and crop[2] - crop[0] == physical[0] and crop[3] - crop[1] == physical[1],
            f"frame {index}: crop runtime invalide")
    return {
        "frame": index,
        "logical_size_x1": logical,
        "physical_size_x4": physical,
        "centre_x1": centre,
        "rgb": rgb,
        "alpha": alpha,
        "aligned": aligned,
        "runtime_crop_box_x4": crop,
    }


def load_context(
    *,
    resref: str,
    frames_manifest_path: Path,
    upscale_manifest_path: Path,
    base_pack_path: Path,
    slot_fps: float,
    interpolation_patches: list[Path] | None = None,
) -> dict[str, Any]:
    resref = normalise_resref(resref)
    require(slot_fps > 0, "--slot-fps doit être strictement positif")
    frames_manifest_path = frames_manifest_path.resolve()
    upscale_manifest_path = upscale_manifest_path.resolve()
    base_pack_path = base_pack_path.resolve()
    frames_manifest = load_json(frames_manifest_path)
    upscale_manifest = load_json(upscale_manifest_path)
    require(int(upscale_manifest.get("scale", 0)) == SCALE, "seules les sources x4 sont admises")
    require(upscale_manifest.get("status") in (None, "completed"), "upscale source non terminé")

    source_count = int(frames_manifest.get("frame_count", 0))
    require(source_count > 0, "nombre de frames source invalide")
    cycles = sorted(frames_manifest.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    require(len(cycles) == 1 and int(cycles[0].get("cycle", -1)) == 0,
            "v1 ne traite qu'un cycle BAM ; créer une spécification par cycle")
    lookup = [int(value) for value in cycles[0].get("frame_indices") or []]
    require(lookup and all(0 <= value < source_count for value in lookup), "lookup de cycle invalide")

    source_x1_records = sorted(frames_manifest.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    require(len(source_x1_records) == source_count, "frames x1 source incomplètes")
    source_records = sorted(upscale_manifest.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    require(len(source_records) == source_count, "frames x4 source incomplètes")
    require([int(item.get("frame", -1)) for item in source_x1_records] == list(range(source_count)),
            "indices de frames x1 non contigus")
    require([int(item.get("frame", -1)) for item in source_records] == list(range(source_count)),
            "indices de frames x4 non contigus")
    source_frames = [
        read_upscale_frame(record, upscale_manifest_path.parent, source_x1_records[index])
        for index, record in enumerate(source_records)
    ]
    require([record["frame"] for record in source_frames] == list(range(source_count)),
            "indices de frames x4 non contigus")
    geometry_mode = str(upscale_manifest.get("geometry_mode") or frames_manifest.get("geometry_mode") or "uniform")
    uniform = len({tuple(frame["physical_size_x4"]) for frame in source_frames}) == 1
    if geometry_mode == "uniform":
        require(uniform, "manifeste uniforme mais tailles physiques différentes")
    if uniform:
        video_size = source_frames[0]["physical_size_x4"]
    else:
        aligned = upscale_manifest.get("aligned_canvas_size_x1") or frames_manifest.get("aligned_canvas_size")
        require(aligned is not None and len(aligned) == 2, "canvas aligné absent pour géométrie variable")
        video_size = [int(aligned[0]) * SCALE, int(aligned[1]) * SCALE]
        require(all(frame["aligned"] is not None for frame in source_frames),
                "aligned_rgba_xn absent pour géométrie variable")

    base_manifest, base_resources = validate_base_pack(base_pack_path)
    effective_resources, effective_registry_sha256, patch_provenance = apply_interpolation_patches(
        base_resources,
        sha256_file(base_pack_path / runtime_pack.REGISTRY_NAME),
        interpolation_patches or [],
    )
    targets = [resource for resource in effective_resources if str(resource.get("resref", "")).upper() == resref]
    require(len(targets) == 1, f"{resref}: ressource absente ou dupliquée dans le pack global")
    base_resource = copy.deepcopy(targets[0])
    require(int(base_resource.get("frame_count", 0)) == source_count,
            f"{resref}: le pack de base ne correspond pas au nombre de frames source")
    base_cycles = base_resource.get("cycles") or []
    require(len(base_cycles) == 1 and [int(value) for value in base_cycles[0].get("frame_indices") or []] == lookup,
            f"{resref}: cycle du pack de base différent de la source")

    runs = grouped_runs(lookup)
    run_lengths = {count for _, count in runs}
    source_video_indices = [index for index, _ in runs] if len(run_lengths) == 1 else lookup
    source_fps = slot_fps / next(iter(run_lengths)) if len(run_lengths) == 1 else slot_fps
    target_count = len(lookup)
    return {
        "resref": resref,
        "scale": SCALE,
        "slot_fps": slot_fps,
        "duration_seconds": target_count / slot_fps,
        "source_frame_count": source_count,
        "target_frame_count": target_count,
        "source_lookup": lookup,
        "source_runs": [{"frame": index, "slots": count} for index, count in runs],
        "source_video_indices": source_video_indices,
        "source_video_fps": source_fps,
        "source_video_mode": "compressed-uniform-holds" if len(run_lengths) == 1 else "native-slot-sequence",
        "geometry_mode": "uniform" if uniform else "per-frame",
        "video_size_x4": video_size,
        "frames_manifest": frames_manifest_path,
        "upscale_manifest": upscale_manifest_path,
        "base_pack": base_pack_path,
        "base_manifest": base_manifest,
        "base_resources": effective_resources,
        "base_registry_sha256": effective_registry_sha256,
        "base_runtime_overrides": patch_provenance,
        "base_resource": base_resource,
        "source_frames": source_frames,
    }


def public_plan(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "resref": context["resref"],
        "geometry_mode": context["geometry_mode"],
        "source": {
            "unique_frame_count": context["source_frame_count"],
            "cycle_slots": context["target_frame_count"],
            "slot_fps": context["slot_fps"],
            "cycle_lookup": context["source_lookup"],
        },
        "recommendation": {
            "interpolated_frame_count": context["target_frame_count"],
            "playback_fps": context["slot_fps"],
            "loop_duration_seconds": context["duration_seconds"],
            "reason": "une image distincte par position temporelle du cycle BAM ; aucune DLL modifiée",
        },
        "source_video": {
            "frame_count": len(context["source_video_indices"]),
            "fps": context["source_video_fps"],
            "duration_seconds": context["duration_seconds"],
            "size_x4": context["video_size_x4"],
            "mode": context["source_video_mode"],
        },
        "return_contract": {
            "png_count": context["target_frame_count"],
            "fps": context["slot_fps"],
            "duration_seconds": context["duration_seconds"],
            "size_x4": context["video_size_x4"],
            "alpha_required": False,
            "duplicate_first_frame_at_end": False,
        },
    }


def source_asset_hashes(context: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for frame in context["source_frames"]:
        record = {
            "frame": frame["frame"],
            "rgb": frame["rgb"].as_posix(),
            "rgb_sha256": sha256_file(frame["rgb"]),
            "alpha": frame["alpha"].as_posix(),
            "alpha_sha256": sha256_file(frame["alpha"]),
        }
        if frame["aligned"] is not None:
            record["aligned"] = frame["aligned"].as_posix()
            record["aligned_sha256"] = sha256_file(frame["aligned"])
        records.append(record)
    return records


def image_for_video(context: dict[str, Any], source_index: int) -> Image.Image:
    frame = context["source_frames"][source_index]
    source = frame["rgb"] if context["geometry_mode"] == "uniform" else frame["aligned"]
    require(source is not None, f"frame {source_index}: canvas aligné absent")
    with Image.open(source) as image:
        rgb = image.convert("RGB")
    require(list(rgb.size) == context["video_size_x4"],
            f"frame {source_index}: dimensions MP4 inattendues {rgb.size}")
    return rgb


def run_ffprobe(path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration", "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    streams = json.loads(completed.stdout).get("streams") or []
    require(len(streams) == 1, "ffprobe ne trouve pas exactement une piste vidéo")
    return streams[0]


def rational_value(value: str) -> float:
    numerator, denominator = str(value).split("/", 1)
    result = float(numerator) / float(denominator)
    require(result > 0, "cadence ffprobe invalide")
    return result


def prepare_video(context: dict[str, Any], output: Path) -> dict[str, Any]:
    output = output.resolve()
    require(not output.exists(), f"destination déjà présente : {output}")
    partial = output.with_name(output.name + ".partial")
    require(not partial.exists(), f"destination partielle déjà présente : {partial}")
    sequence = partial / "source_rgb"
    sequence.mkdir(parents=True)
    try:
        source_records = []
        for output_index, source_index in enumerate(context["source_video_indices"]):
            image = image_for_video(context, source_index)
            target = sequence / f"frame_{output_index:03d}.png"
            image.save(target, format="PNG", compress_level=9)
            source_records.append({
                "video_frame": output_index,
                "source_frame": source_index,
                "name": target.name,
                "sha256": sha256_file(target),
            })

        video_name = f"{context['resref']}-x4-source.mp4"
        video_path = partial / video_name
        fps_text = f"{context['source_video_fps']:.9g}"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", fps_text,
                "-i", str(sequence / "frame_%03d.png"), "-an", "-c:v", "libx264rgb", "-crf", "0",
                "-preset", "slow", "-pix_fmt", "rgb24", "-r", fps_text, str(video_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        probe = run_ffprobe(video_path)
        actual_fps = rational_value(probe["avg_frame_rate"])
        actual_count = int(probe.get("nb_frames") or 0)
        actual_duration = float(probe.get("duration") or 0)
        require([int(probe["width"]), int(probe["height"])] == context["video_size_x4"],
                "MP4: résolution incorrecte après encodage")
        require(actual_count == len(source_records), "MP4: nombre de frames incorrect après encodage")
        require(abs(actual_fps - context["source_video_fps"]) < 0.0001, "MP4: FPS incorrect après encodage")
        require(abs(actual_duration - context["duration_seconds"]) <= duration_tolerance(context["source_video_fps"]),
                "MP4: durée incorrecte après encodage")

        handoff = {
            "schema": HANDOFF_SCHEMA,
            "status": "prepared",
            "created_utc": utc_now(),
            "plan": public_plan(context),
            "inputs": {
                "frames_manifest": context["frames_manifest"].as_posix(),
                "frames_manifest_sha256": sha256_file(context["frames_manifest"]),
                "upscale_manifest": context["upscale_manifest"].as_posix(),
                "upscale_manifest_sha256": sha256_file(context["upscale_manifest"]),
                "base_pack": context["base_pack"].as_posix(),
                "base_pack_manifest_sha256": sha256_file(context["base_pack"] / "manifest.json"),
                "base_registry_sha256": context["base_registry_sha256"],
                "base_runtime_overrides": context["base_runtime_overrides"],
            },
            "source_assets": source_asset_hashes(context),
            "source_video": {
                "name": video_name,
                "sha256": sha256_file(video_path),
                "bytes": video_path.stat().st_size,
                "ffprobe": probe,
                "source_frames": source_records,
            },
            "return_contract": public_plan(context)["return_contract"],
        }
        write_json(partial / "handoff.json", handoff)
        partial.replace(output)
        return handoff
    except Exception:
        raise


def load_handoff(work_root: Path) -> tuple[Path, dict[str, Any]]:
    work_root = work_root.resolve()
    handoff = load_json(work_root / "handoff.json")
    require(handoff.get("schema") == HANDOFF_SCHEMA and handoff.get("status") == "prepared",
            "handoff incompatible")
    return work_root, handoff


def audit_returned_frames(work_root: Path, input_frames: Path) -> dict[str, Any]:
    work_root, handoff = load_handoff(work_root)
    contract = handoff["return_contract"]
    input_frames = input_frames.resolve()
    files = parse_numbered_pngs(input_frames)
    expected_count = int(contract["png_count"])
    expected_size = [int(value) for value in contract["size_x4"]]
    require(len(files) == expected_count, f"{expected_count} PNG requis, trouvé : {len(files)}")
    records: list[dict[str, Any]] = []
    images: list[Image.Image] = []
    try:
        for index, path in enumerate(files):
            with Image.open(path) as original:
                require(original.mode in ("RGB", "RGBA"), f"{path.name}: mode PNG invalide {original.mode}")
                require(list(original.size) == expected_size,
                        f"{path.name}: dimensions inattendues {original.size}, attendu {expected_size}")
                alpha = None
                if original.mode == "RGBA":
                    alpha = list(original.getchannel("A").getextrema())
                records.append({
                    "frame": index,
                    "source": path.as_posix(),
                    "source_sha256": sha256_file(path),
                    "mode": original.mode,
                    "size_x4": list(original.size),
                    "alpha_extrema": alpha,
                })
                images.append(original.convert("RGB"))
        adjacent = [image_mae(images[index], images[(index + 1) % len(images)]) for index in range(len(images))]
        seam = adjacent[-1]
        internal = adjacent[:-1]
        seam_percentile = sum(value <= seam for value in internal) / len(internal) if internal else 0.0
    finally:
        for image in images:
            image.close()
    intake = {
        "schema": INTAKE_SCHEMA,
        "status": "audited",
        "created_utc": utc_now(),
        "handoff_sha256": sha256_file(work_root / "handoff.json"),
        "input_frames": input_frames.as_posix(),
        "frame_count": len(records),
        "frames": records,
        "adjacent_rgb_mae": [round(value, 6) for value in adjacent],
        "seam_rgb_mae": round(seam, 6),
        "seam_percentile_against_internal": round(seam_percentile, 6),
    }
    intake_path = work_root / "intake.json"
    require(not intake_path.exists(), f"intake déjà présent : {intake_path}")
    write_json(intake_path, intake)
    return intake


def context_from_handoff(handoff: dict[str, Any]) -> dict[str, Any]:
    plan = handoff["plan"]
    source = plan["source"]
    inputs = handoff["inputs"]
    context = load_context(
        resref=str(plan["resref"]),
        frames_manifest_path=Path(inputs["frames_manifest"]),
        upscale_manifest_path=Path(inputs["upscale_manifest"]),
        base_pack_path=Path(inputs["base_pack"]),
        slot_fps=float(source["slot_fps"]),
        interpolation_patches=[Path(item["patch"]) for item in inputs.get("base_runtime_overrides") or []],
    )
    require(sha256_file(context["frames_manifest"]) == inputs["frames_manifest_sha256"],
            "manifeste frames x1 modifié depuis la préparation")
    require(sha256_file(context["upscale_manifest"]) == inputs["upscale_manifest_sha256"],
            "manifeste x4 modifié depuis la préparation")
    require(sha256_file(context["base_pack"] / "manifest.json") == inputs["base_pack_manifest_sha256"],
            "manifeste du pack global modifié depuis la préparation")
    require(context["base_registry_sha256"] == inputs["base_registry_sha256"],
            "registre global effectif modifié depuis la préparation")
    require(context["base_runtime_overrides"] == inputs.get("base_runtime_overrides", []),
            "chaîne de patchs globaux modifiée depuis la préparation")
    expected_assets = source_asset_hashes(context)
    require(handoff.get("source_assets") == expected_assets, "assets RGB/alpha x4 modifiés depuis la préparation")
    return context


def rate_text(value: float) -> str:
    """Render a frame rate exactly, as an integer or an ffmpeg rational."""
    fraction = Fraction(value).limit_denominator(1000)
    require(fraction > 0, "cadence invalide")
    if fraction.denominator == 1:
        return str(fraction.numerator)
    return f"{fraction.numerator}/{fraction.denominator}"


def alpha_phase_map(context: dict[str, Any]) -> list[int]:
    """Map each interpolated slot to the source phase it sits closest to.

    Slot ``j`` lands exactly at source position ``j * U / N``. The nearest whole
    position is taken with half-up rounding and wraps back to the first frame,
    because the final slots interpolate across the loop seam rather than holding
    the last source frame.
    """
    video_indices = context["source_video_indices"]
    unique = len(video_indices)
    target = context["target_frame_count"]
    require(unique > 0 and target % unique == 0,
            "positions du cycle non divisibles par le nombre de frames uniques")
    return [
        video_indices[((2 * slot * unique + target) // (2 * target)) % unique]
        for slot in range(target)
    ]


def looks_like_closure(files: list[Path]) -> tuple[bool, float, float]:
    """Decide whether the final frame repeats the first one, closing the loop."""
    with Image.open(files[-1]) as last, Image.open(files[0]) as first:
        closing = image_mae(last, first)
    samples: list[float] = []
    for index in range(min(len(files) - 1, 12)):
        with Image.open(files[index]) as left, Image.open(files[index + 1]) as right:
            samples.append(image_mae(left, right))
    reference = sorted(samples)[len(samples) // 2] if samples else 0.0
    return closing < reference, closing, reference


def retime_sequence(
    files: list[Path],
    *,
    target_count: int,
    slot_fps: float,
    staging: Path,
    output: Path,
) -> list[Path]:
    """Resample a sequence that already covers the whole loop onto exactly N slots.

    This is the fallback montage. The nominal path picks frames by index and
    never resamples, because resampling can only duplicate or drop frames. It
    assumes the input spans the complete loop: stretching a sequence that is
    missing the seam interval would silently drift every phase instead.
    """
    staging.mkdir(parents=True)
    output.mkdir(parents=True)
    for index, path in enumerate(files):
        shutil.copyfile(path, staging / f"span_{index:04d}.png")
    rate = Fraction(len(files)) * Fraction(slot_fps).limit_denominator(1000) / Fraction(target_count)
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", f"{rate.numerator}/{rate.denominator}",
        "-i", str(staging / "span_%04d.png"),
        "-vf", f"fps={rate_text(slot_fps)}",
        "-pix_fmt", "rgb24",
        str(output / "slot_%04d.png"),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    require(completed.returncode == 0,
            f"montage ffmpeg échoué : {(completed.stderr or '').strip()[:800]}")
    produced = parse_numbered_pngs(output)
    require(len(produced) == target_count,
            f"montage : {len(produced)} frames produites, {target_count} attendues")
    return produced


def topaz_banner(ffmpeg: Path) -> str:
    completed = subprocess.run([str(ffmpeg), "-hide_banner", "-version"],
                               check=True, capture_output=True, text=True)
    lines = [line.strip() for line in (completed.stdout or "").splitlines() if line.strip()]
    return lines[0] if lines else ""


def interpolate_frames(
    work_root: Path,
    *,
    ffmpeg: Path,
    model_dir: Path,
    model: str,
    oversample: int,
    device: str,
    retime: str = "auto",
) -> dict[str, Any]:
    """Interpolate the prepared x4 frames with Topaz Video AI, loop included.

    The input handed to the model is the validated source sequence with its
    first frame appended, so the model also interpolates the wrap from the last
    source frame back to the first. Without that closure the model only covers
    the internal intervals and the loop ends up one interval short, which then
    has to be hidden by stretching the result and drifts every phase.
    """
    work_root, handoff = load_handoff(work_root)
    context = context_from_handoff(handoff)
    require(oversample >= 1, "--oversample doit valoir au moins 1")
    require(
        context["source_video_mode"] == "compressed-uniform-holds",
        "répétitions non uniformes : écrire une spécification par segment avant d'interpoler",
    )
    require(bool(re.fullmatch(r"[a-z]{2,4}-\d{1,2}", model)), f"modèle invalide : {model}")
    require(bool(re.fullmatch(r"-?\d+(\.\d+)*", device)), f"device invalide : {device}")
    require(ffmpeg.is_file(), f"ffmpeg Topaz absent : {ffmpeg}")
    require(model_dir.is_dir(), f"dossier de modèles Topaz absent : {model_dir}")
    require((model_dir / f"{model}.json").is_file(), f"modèle absent du dossier Topaz : {model}")

    target_count = int(context["target_frame_count"])
    expected_size = [int(value) for value in handoff["return_contract"]["size_x4"]]
    source_fps = float(handoff["plan"]["source_video"]["fps"])
    output_fps = float(context["slot_fps"]) * oversample

    video_records = sorted(handoff["source_video"]["source_frames"], key=lambda item: int(item["video_frame"]))
    require(len(video_records) == len(context["source_video_indices"]),
            "inventaire du MP4 source incohérent avec le plan")
    sequence_dir = work_root / "source_rgb"
    for record in video_records:
        path = sequence_dir / str(record["name"])
        require(path.is_file() and sha256_file(path) == str(record["sha256"]),
                f"frame RGB source modifiée depuis la préparation : {path}")

    output = work_root / "interpolation"
    require(not output.exists(), f"interpolation déjà présente : {output}")
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    input_dir = partial / "input"
    raw_dir = partial / "raw"
    frames_dir = partial / "frames"
    for directory in (input_dir, raw_dir, frames_dir):
        directory.mkdir(parents=True)

    # Close the loop: the first frame is appended so the seam interval is modelled too.
    for index, record in enumerate(video_records):
        shutil.copyfile(sequence_dir / str(record["name"]), input_dir / f"in_{index:03d}.png")
    shutil.copyfile(sequence_dir / str(video_records[0]["name"]),
                    input_dir / f"in_{len(video_records):03d}.png")

    filter_text = (
        f"tvai_fi=model={model}:fps={rate_text(output_fps)}"
        f":rdt={FI_REPLACE_DUPLICATE_THRESHOLD}:device={device}"
    )
    command = [
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", rate_text(source_fps),
        "-i", str(input_dir / "in_%03d.png"),
        "-vf", filter_text,
        "-pix_fmt", "rgb24",
        str(raw_dir / "out_%04d.png"),
    ]
    environment = dict(os.environ)
    environment["TVAI_MODEL_DIR"] = str(model_dir)
    environment["TVAI_MODEL_DATA_DIR"] = str(model_dir)
    completed = subprocess.run(command, capture_output=True, text=True, env=environment)
    require(completed.returncode == 0,
            f"Topaz a échoué ({completed.returncode}) : {(completed.stderr or '').strip()[:800]}")

    raw_files = parse_numbered_pngs(raw_dir)
    expected_raw = target_count * oversample + 1
    if len(raw_files) == expected_raw:
        coverage, closure_present = "exact", True
    elif len(raw_files) == target_count * oversample:
        coverage, closure_present = "exact", False
    else:
        coverage = "irregular"
        closure_present, closure_mae, closure_reference = looks_like_closure(raw_files)

    require(
        not (coverage == "irregular" and retime != "always"),
        f"Topaz a produit {len(raw_files)} frames au lieu de {expected_raw} : la couverture "
        "de boucle n'est pas certaine. Vérifier le modèle et la cadence, ou forcer le "
        "montage ffmpeg avec --retime always en sachant qu'il suppose une boucle complète.",
    )
    require(
        not (retime == "never" and coverage != "exact"),
        f"--retime never : {len(raw_files)} frames produites, {expected_raw} attendues",
    )

    # Nominal path: the model landed on the expected count, so every slot is an
    # existing frame picked by index. The montage below only runs as a fallback.
    use_montage = retime == "always" or coverage == "irregular"
    if use_montage:
        span = raw_files[:-1] if closure_present else list(raw_files)
        kept = retime_sequence(
            span,
            target_count=target_count,
            slot_fps=float(context["slot_fps"]),
            staging=partial / "montage_input",
            output=partial / "montage",
        )
        if coverage == "exact":
            with Image.open(raw_files[-1]) as closing, Image.open(raw_files[0]) as opening:
                closure_mae = image_mae(closing, opening)
            closure_reference = None
    else:
        kept = [raw_files[slot * oversample] for slot in range(target_count)]
        closure_reference = None
        if closure_present:
            with Image.open(raw_files[-1]) as closing, Image.open(kept[0]) as opening:
                closure_mae = image_mae(closing, opening)
        else:
            closure_mae = None

    frame_records: list[dict[str, Any]] = []
    for slot, path in enumerate(kept):
        with Image.open(path) as image:
            require(image.mode == "RGB", f"frame {slot}: mode Topaz inattendu {image.mode}")
            require(list(image.size) == expected_size,
                    f"frame {slot}: dimensions Topaz {image.size}, attendu {expected_size}")
        target = frames_dir / f"frame_{slot:03d}.png"
        shutil.copyfile(path, target)
        frame_records.append({
            "frame": slot,
            "raw": path.name,
            "name": target.name,
            "sha256": sha256_file(target),
        })

    report = {
        "schema": INTERPOLATION_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "resref": context["resref"],
        "handoff_sha256": sha256_file(work_root / "handoff.json"),
        "engine": {
            "ffmpeg": ffmpeg.as_posix(),
            "version": topaz_banner(ffmpeg),
            "model_dir": model_dir.as_posix(),
            "model": model,
            "device": device,
            "filter": filter_text,
            "replace_duplicate_threshold": FI_REPLACE_DUPLICATE_THRESHOLD,
        },
        "timing": {
            "input_fps": source_fps,
            "output_fps": output_fps,
            "oversample": oversample,
            "slot_fps": context["slot_fps"],
            "frame_count": target_count,
            "loop_duration_seconds": context["duration_seconds"],
        },
        "loop_closure": {
            "appended_source_frame": int(video_records[0]["source_frame"]),
            "raw_frame_count": len(raw_files),
            "coverage": coverage,
            "closure_frame_present": closure_present,
            "closure_rgb_mae": None if closure_mae is None else round(closure_mae, 6),
            "closure_reference_mae": None if closure_reference is None else round(closure_reference, 6),
        },
        "montage": {
            "used": use_montage,
            "mode": retime,
            "reason": "repli ffmpeg" if use_montage else "inutile : cadence et durée déjà exactes",
        },
        "alpha_phase_map": alpha_phase_map(context),
        "frames_directory": (output / "frames").as_posix(),
        "frames": frame_records,
    }
    write_json(partial / "interpolation.json", report)
    partial.replace(output)
    return report


def nearest_source_frame(image: Image.Image, context: dict[str, Any]) -> tuple[int, float]:
    values: list[float] = []
    for index in range(context["source_frame_count"]):
        reference = image_for_video(context, index)
        try:
            values.append(image_mae(image, reference))
        finally:
            reference.close()
    selected = min(range(len(values)), key=values.__getitem__)
    return selected, values[selected]


def build_patch(work_root: Path, output: Path, resume: bool) -> dict[str, Any]:
    work_root, handoff = load_handoff(work_root)
    intake = load_json(work_root / "intake.json")
    require(intake.get("schema") == INTAKE_SCHEMA and intake.get("status") == "audited",
            "intake incompatible")
    require(intake.get("handoff_sha256") == sha256_file(work_root / "handoff.json"),
            "handoff modifié depuis l'audit")
    context = context_from_handoff(handoff)
    contract = handoff["return_contract"]
    frames = sorted(intake.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    require(len(frames) == int(contract["png_count"]), "intake: nombre de frames invalide")
    require(int(context["target_frame_count"]) >= int(context["source_frame_count"]),
            "la v1 ne prend en charge que l'extension du nombre de frames runtime")

    # Frames produced by the `interpolate` step have a phase known by construction,
    # so the alpha of each slot is read from that map instead of being guessed by
    # image comparison. Frames interpolated outside the pipeline keep the search.
    phase_map: list[int] | None = None
    interpolation_path = work_root / "interpolation" / "interpolation.json"
    if interpolation_path.is_file():
        report = load_json(interpolation_path)
        require(report.get("schema") == INTERPOLATION_SCHEMA and report.get("status") == "completed",
                "rapport d'interpolation incompatible")
        require(report.get("handoff_sha256") == sha256_file(work_root / "handoff.json"),
                "handoff modifié depuis l'interpolation")
        phase_map = [int(value) for value in report.get("alpha_phase_map") or []]
        require(len(phase_map) == int(contract["png_count"]),
                "carte des phases incompatible avec le contrat de retour")
        require(all(0 <= value < int(context["source_frame_count"]) for value in phase_map),
                "carte des phases hors des frames source")

    output = output.resolve()
    if output.exists():
        if not resume:
            raise RuntimeError(f"destination déjà présente : {output}")
        manifest = load_json(output / "manifest.json")
        require(manifest.get("schema") == PATCH_SCHEMA and manifest.get("status") == "completed",
                "patch existant incompatible")
        for frame in manifest.get("frames") or []:
            path = output / str(frame["asset"])
            require(path.is_file() and path.stat().st_size == int(frame["bytes"]) and
                    sha256_file(path) == str(frame["sha256"]), "patch existant corrompu")
        require(sha256_file(output / str(manifest["target_registry"])) == manifest["target_registry_sha256"],
                "registre du patch existant corrompu")
        return manifest
    partial = output.with_name(output.name + ".partial")
    require(not partial.exists(), f"destination partielle déjà présente : {partial}")
    partial.mkdir(parents=True)
    try:
        frame_records: list[dict[str, Any]] = []
        for target_index, record in enumerate(frames):
            require(int(record.get("frame", -1)) == target_index, "intake: indices de frames non contigus")
            source_path = Path(str(record["source"])).resolve()
            require(source_path.is_file() and sha256_file(source_path) == record["source_sha256"],
                    f"frame livrée modifiée ou absente : {source_path}")
            with Image.open(source_path) as source:
                rgb_full = source.convert("RGB")
            require(list(rgb_full.size) == [int(value) for value in contract["size_x4"]],
                    f"frame livrée : dimensions modifiées {source_path}")
            matched_index, match_mae = nearest_source_frame(rgb_full, context)
            if phase_map is None:
                alpha_source_index = matched_index
                alpha_phase_source = "nearest-rgb"
            else:
                alpha_source_index = phase_map[target_index]
                alpha_phase_source = "deterministic"
            source_frame = context["source_frames"][alpha_source_index]
            crop = tuple(source_frame["runtime_crop_box_x4"])
            rgb = rgb_full.crop(crop)
            with Image.open(source_frame["alpha"]) as alpha_source:
                alpha = alpha_source.convert("L")
            require(rgb.size == alpha.size == tuple(source_frame["physical_size_x4"]),
                    f"frame {target_index}: alpha/crop incompatibles")
            rgba = Image.merge("RGBA", (*rgb.split(), alpha))
            asset = runtime_pack.asset_name(context["resref"], target_index)
            asset_path = partial / asset
            asset_path.write_bytes(rgba.tobytes())
            expected_bytes = rgba.size[0] * rgba.size[1] * 4
            require(asset_path.stat().st_size == expected_bytes, f"frame {target_index}: taille RGBA invalide")
            frame_records.append({
                "frame": target_index,
                "source": source_path.as_posix(),
                "source_sha256": record["source_sha256"],
                "alpha_source_frame": alpha_source_index,
                "alpha_phase_source": alpha_phase_source,
                "alpha_nearest_rgb_frame": matched_index,
                "alpha_match_mae": round(match_mae, 6),
                "logical_size_x1": source_frame["logical_size_x1"],
                "physical_size_x4": source_frame["physical_size_x4"],
                "centre_x1": source_frame["centre_x1"],
                "asset": asset,
                "sha256": sha256_file(asset_path),
                "bytes": expected_bytes,
            })

        new_resource = {
            "resref": context["resref"],
            "frame_count": len(frame_records),
            "cycle_count": 1,
            "geometry_mode": context["geometry_mode"],
            "frames": [
                {
                    "frame": frame["frame"],
                    "logical_size_x1": frame["logical_size_x1"],
                    "physical_size_x4": frame["physical_size_x4"],
                    "centre_x1": frame["centre_x1"],
                    "asset": frame["asset"],
                    "sha256": frame["sha256"],
                    "bytes": frame["bytes"],
                }
                for frame in frame_records
            ],
            "cycles": [{"cycle": 0, "frame_indices": list(range(len(frame_records)))}],
            "assets": [
                {"name": frame["asset"], "sha256": frame["sha256"], "bytes": frame["bytes"]}
                for frame in frame_records
            ],
        }
        resources = copy.deepcopy(context["base_resources"])
        for index, resource in enumerate(resources):
            if str(resource.get("resref", "")).upper() == context["resref"]:
                resources[index] = new_resource
                break
        registry = runtime_pack.registry_from_resources(resources)
        registry_path = partial / runtime_pack.REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest = {
            "schema": PATCH_SCHEMA,
            "status": "completed",
            "created_utc": utc_now(),
            "resref": context["resref"],
            "scale": SCALE,
            "frame_count": len(frame_records),
            "native_cycle_slots": context["target_frame_count"],
            "playback_fps": context["slot_fps"],
            "loop_duration_seconds": context["duration_seconds"],
            "geometry_mode": context["geometry_mode"],
            "handoff": (work_root / "handoff.json").as_posix(),
            "handoff_sha256": sha256_file(work_root / "handoff.json"),
            "intake": (work_root / "intake.json").as_posix(),
            "intake_sha256": sha256_file(work_root / "intake.json"),
            "base_pack": context["base_pack"].as_posix(),
            "base_pack_manifest_sha256": sha256_file(context["base_pack"] / "manifest.json"),
            "base_registry_sha256": context["base_registry_sha256"],
            "base_runtime_overrides": context["base_runtime_overrides"],
            "target_registry": runtime_pack.REGISTRY_NAME,
            "target_registry_sha256": sha256_file(registry_path),
            "target_registry_bytes": registry_path.stat().st_size,
            "base_resource": context["base_resource"],
            "resource": new_resource,
            "frames": frame_records,
        }
        write_json(partial / "manifest.json", manifest)
        # Reconstruct before publication; this checks all dimensions, names and lookup values.
        require(registry_path.read_bytes() == runtime_pack.registry_from_resources(resources),
                "registre patch non reproductible")
        partial.replace(output)
        return manifest
    except Exception:
        raise


def add_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--resref", required=True)
    parser.add_argument("--frames-manifest", type=Path, required=True)
    parser.add_argument("--upscale-manifest", type=Path, required=True)
    parser.add_argument("--base-pack", type=Path, required=True)
    parser.add_argument("--slot-fps", type=float, required=True,
                        help="cadence mesurée des positions temporelles BAM")
    parser.add_argument("--interpolation-patch", type=Path, action="append", default=[],
                        help="patch interpolation déjà actif à conserver ; répétable et ordonné")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="analyse en lecture seule et proposition frames/FPS/durée")
    add_source_arguments(plan)
    prepare = commands.add_parser("prepare-video", help="crée le MP4 x4 et le contrat de retour")
    add_source_arguments(prepare)
    prepare.add_argument("--output", type=Path, required=True, help="dossier de travail neuf")
    interpolate = commands.add_parser(
        "interpolate", help="interpole les frames x4 avec Topaz Video AI, boucle fermée")
    interpolate.add_argument("--work-root", type=Path, required=True)
    interpolate.add_argument("--model", default=DEFAULT_FI_MODEL,
                             help="modèle Topaz d'interpolation (apo-8 = Apollo, apf-* = Apollo Fast)")
    interpolate.add_argument("--oversample", type=int, default=1,
                             help="multiplie la cadence demandée à Topaz puis décime d'autant ; "
                                  "1 suffit et produit les mêmes phases")
    interpolate.add_argument("--device", default="-2", help="Auto: -2, CPU: -1, GPU0: 0")
    interpolate.add_argument("--retime", choices=("auto", "never", "always"), default="auto",
                             help="montage ffmpeg : auto = seulement si la sortie n'est pas exacte")
    interpolate.add_argument("--tvai-ffmpeg", type=Path, default=DEFAULT_TVAI_FFMPEG)
    interpolate.add_argument("--tvai-model-dir", type=Path, default=DEFAULT_TVAI_MODEL_DIR)
    ingest = commands.add_parser("ingest-frames", help="audite les PNG interpolés fournis")
    ingest.add_argument("--work-root", type=Path, required=True)
    ingest.add_argument("--input-frames", type=Path, required=True)
    build = commands.add_parser("build-patch", help="crée le registre et les buffers du patch réversible")
    build.add_argument("--work-root", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)

    if args.command in ("plan", "prepare-video"):
        context = load_context(
            resref=args.resref,
            frames_manifest_path=args.frames_manifest,
            upscale_manifest_path=args.upscale_manifest,
            base_pack_path=args.base_pack,
            slot_fps=args.slot_fps,
            interpolation_patches=args.interpolation_patch,
        )
        if args.command == "plan":
            print(json.dumps(public_plan(context), ensure_ascii=False, indent=2))
            return
        handoff = prepare_video(context, args.output)
        print(f"MP4 et contrat créés : {args.output.resolve()} ({handoff['source_video']['name']})")
        return
    if args.command == "interpolate":
        report = interpolate_frames(
            args.work_root,
            ffmpeg=args.tvai_ffmpeg,
            model_dir=args.tvai_model_dir,
            model=args.model,
            oversample=args.oversample,
            device=args.device,
            retime=args.retime,
        )
        montage = "montage ffmpeg" if report["montage"]["used"] else "sans montage"
        print(
            f"Interpolation {report['engine']['model']} : {report['timing']['frame_count']} frames, "
            f"{report['timing']['slot_fps']} FPS, {montage} -> {report['frames_directory']}"
        )
        print(
            "Etape suivante : run_animation_interpolation.py ingest-frames "
            f"--work-root {args.work_root} --input-frames {report['frames_directory']}"
        )
        return
    if args.command == "ingest-frames":
        intake = audit_returned_frames(args.work_root, args.input_frames)
        print(f"Frames validées techniquement : {intake['frame_count']}, couture MAE {intake['seam_rgb_mae']}")
        return
    manifest = build_patch(args.work_root, args.output, args.resume)
    print(
        f"Patch construit : {manifest['resref']} {manifest['frame_count']} frames, "
        f"{manifest['playback_fps']} FPS -> {args.output.resolve()}"
    )


if __name__ == "__main__":
    main()
