"""Build one immutable x4 projectile/effect runtime pack from a sealed spatial run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA_VERSION = 1
FRAME_SCHEMA = "bg2-upscale-animation-frames-x1-v1"
SPATIAL_SCHEMA = "bg2-upscale-animation-frames-v1"
INTERPOLATION_SCHEMA = "bg2-upscale-effect-interpolation-30fps-v1"
PACK_SCHEMA = "bg2-upscale-effect-animation-runtime-pack-v1"
REGISTRY_MAGIC = b"IEEEFX4\0"
REGISTRY_VERSION = 1
TIMELINE_REGISTRY_VERSION = 2
REGISTRY_NAME = "EffectAnimations-X4.registry"
MAX_FRAME_DIMENSION = 2048


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"manifeste absent : {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"manifeste invalide : {path}")
    return payload


def relative_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"chemin hors workspace : {path}") from exc


def require_relative(parent: Path, value: str, label: str) -> Path:
    target = (parent / value).resolve()
    try:
        target.relative_to(parent.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} hors de son répertoire : {value}") from exc
    return target


def frame_asset_name(resref: str, frame_index: int) -> str:
    return f"EFX4-{resref}-frame{frame_index:03d}.rgba"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_hash(path: Path, expected: str, label: str) -> str:
    digest = sha256_file(path)
    if digest != expected.upper():
        raise RuntimeError(f"hash {label} incohérent : {path}")
    return digest


def validate_input(resref: str, run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    descriptor_path = run_dir / "run.json"
    descriptor = load_json(descriptor_path)
    if (
        descriptor.get("schema_version") != RUN_SCHEMA_VERSION
        or descriptor.get("domain") != "effects"
        or descriptor.get("run_id") != run_dir.name
        or descriptor.get("result", {}).get("sealed") is not True
        or descriptor.get("result", {}).get("status") != "completed"
        or descriptor.get("pipeline", {}).get("id") != "effects.spatial-x4.v1"
        or descriptor.get("asset_ids") != [f"effects:bam:{resref}"]
    ):
        raise RuntimeError("run spatial non scellé ou incompatible")

    spatial_outputs = [
        item for item in descriptor.get("outputs", []) if item.get("role") == "spatial-manifest"
    ]
    if len(spatial_outputs) != 1:
        raise RuntimeError("run spatial sans manifeste de sortie unique")
    spatial_record = spatial_outputs[0]
    spatial_path = require_relative(REPO_ROOT, str(spatial_record.get("path", "")), "manifeste spatial")
    require_hash(spatial_path, str(spatial_record.get("sha256", "")), "manifeste spatial")
    spatial = load_json(spatial_path)
    if spatial.get("schema") != SPATIAL_SCHEMA or spatial.get("status") != "completed" or spatial.get("scale") != 4:
        raise RuntimeError("manifeste spatial incomplet ou non x4")

    source = spatial.get("source")
    if not isinstance(source, dict):
        raise RuntimeError("provenance x1 absente")
    source_manifest = require_relative(
        REPO_ROOT, str(source.get("frame_manifest", "")), "manifeste x1"
    )
    require_hash(source_manifest, str(source.get("frame_manifest_sha256", "")), "manifeste x1")
    frames_x1 = load_json(source_manifest)
    if frames_x1.get("schema") != FRAME_SCHEMA or frames_x1.get("source_sha256") is None:
        raise RuntimeError("manifeste x1 incompatible")
    return descriptor, frames_x1, spatial


def validate_interpolation_input(
    resref: str,
    run_dir: Path,
    parent_descriptor: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    descriptor_path = run_dir / "run.json"
    descriptor = load_json(descriptor_path)
    if (
        descriptor.get("schema_version") != RUN_SCHEMA_VERSION
        or descriptor.get("domain") != "effects"
        or descriptor.get("run_id") != run_dir.name
        or descriptor.get("result", {}).get("sealed") is not True
        or descriptor.get("result", {}).get("status") != "completed"
        or descriptor.get("pipeline", {}).get("id") != "effects.interpolation-30fps.v1"
        or descriptor.get("asset_ids") != [f"effects:bam:{resref}"]
        or descriptor.get("provenance", {}).get("parents") != [parent_descriptor["run_id"]]
    ):
        raise RuntimeError("run d'interpolation non scellé ou incompatible")
    parent_outputs = {
        (item.get("path"), str(item.get("sha256", "")).upper(), item.get("bytes"))
        for item in parent_descriptor.get("outputs", [])
    }
    bindings = {
        (item.get("path"), str(item.get("sha256", "")).upper(), item.get("bytes"))
        for item in descriptor.get("inputs", [])
        if item.get("role") == "parent-spatial-output"
    }
    if not parent_outputs & bindings:
        raise RuntimeError("run interpolation non lié à une sortie spatiale parent")
    records = [item for item in descriptor.get("outputs", []) if item.get("role") == "interpolation-manifest"]
    if len(records) != 1:
        raise RuntimeError("run interpolation sans manifeste de sortie unique")
    record = records[0]
    manifest_path = require_relative(REPO_ROOT, str(record.get("path", "")), "manifeste interpolation")
    require_hash(manifest_path, str(record.get("sha256", "")), "manifeste interpolation")
    manifest = load_json(manifest_path)
    if (
        manifest.get("schema") != INTERPOLATION_SCHEMA
        or manifest.get("status") != "completed"
        or manifest.get("resref") != resref
        or manifest.get("scale") != 4
    ):
        raise RuntimeError("manifeste interpolation incomplet")
    return descriptor, manifest, manifest_path


def build_pack_record(resref: str, frames_x1: dict[str, Any], spatial: dict[str, Any], spatial_dir: Path) -> tuple[bytes, list[dict[str, Any]]]:
    encoded_resref = resref.encode("ascii")
    if not encoded_resref or len(encoded_resref) > 8 or not all(
        character.isalnum() or character == "_" for character in resref
    ):
        raise RuntimeError(f"resref invalide : {resref}")

    frame_count = frames_x1.get("frame_count")
    if type(frame_count) is not int or frame_count <= 0:
        raise RuntimeError("nombre de frames x1 invalide")
    source_frames = frames_x1.get("frames")
    scaled_frames = spatial.get("frames")
    if not isinstance(source_frames, list) or not isinstance(scaled_frames, list):
        raise RuntimeError("liste de frames absente")
    if len(source_frames) != frame_count or len(scaled_frames) != frame_count:
        raise RuntimeError("nombre de frames x1/x4 divergent")

    registry = bytearray(encoded_resref.ljust(8, b"\0"))
    cycles = frames_x1.get("cycles")
    if not isinstance(cycles, list) or not cycles:
        raise RuntimeError("cycles BAM absents")
    ordered_cycles = sorted(cycles, key=lambda item: item.get("cycle", -1))
    if [item.get("cycle") for item in ordered_cycles] != list(range(len(ordered_cycles))):
        raise RuntimeError("cycles BAM non contigus")
    if len(ordered_cycles) > 256:
        raise RuntimeError("trop de cycles BAM")
    registry.extend(struct.pack("<II", frame_count, len(ordered_cycles)))

    assets: list[dict[str, Any]] = []
    for index, (source_frame, scaled_frame) in enumerate(zip(source_frames, scaled_frames)):
        if source_frame.get("frame") != index or scaled_frame.get("frame") != index:
            raise RuntimeError("frames non contiguës")
        source_size = source_frame.get("source_size")
        logical_size = scaled_frame.get("logical_size_x1")
        physical_size = scaled_frame.get("physical_size_xn")
        if (
            not isinstance(source_size, list)
            or not isinstance(logical_size, list)
            or not isinstance(physical_size, list)
            or len(source_size) != 2
            or len(logical_size) != 2
            or len(physical_size) != 2
        ):
            raise RuntimeError(f"frame {index}: dimensions absentes")
        width, height = (int(value) for value in logical_size)
        if (
            width <= 0
            or height <= 0
            or width > MAX_FRAME_DIMENSION
            or height > MAX_FRAME_DIMENSION
            or source_size != logical_size
            or physical_size != [width * 4, height * 4]
        ):
            raise RuntimeError(f"frame {index}: géométrie x1/x4 invalide")
        raw_relative = scaled_frame.get("raw_rgba_xn")
        if not isinstance(raw_relative, str):
            raise RuntimeError(f"frame {index}: RGBA x4 absent")
        raw_path = require_relative(spatial_dir, raw_relative, f"frame {index}")
        expected_bytes = width * 4 * height * 4 * 4
        if not raw_path.is_file() or raw_path.stat().st_size != expected_bytes:
            raise RuntimeError(f"frame {index}: RGBA x4 absent ou tronqué")
        digest = require_hash(raw_path, str(scaled_frame.get("raw_rgba_xn_sha256", "")), f"frame {index}")
        name = frame_asset_name(resref, index)
        registry.extend(struct.pack("<II", width, height))
        assets.append(
            {
                "frame": index,
                "asset": name,
                "source": relative_to_repo(raw_path),
                "sha256": digest,
                "bytes": expected_bytes,
                "logical_size_x1": [width, height],
                "physical_size_x4": [width * 4, height * 4],
            }
        )

    for cycle in ordered_cycles:
        frames = cycle.get("frame_indices")
        if not isinstance(frames, list) or not frames or len(frames) > 65536:
            raise RuntimeError("cycle BAM vide ou trop long")
        if any(type(frame) is not int or frame < 0 or frame >= frame_count for frame in frames):
            raise RuntimeError("cycle BAM avec frame invalide")
        registry.extend(struct.pack("<I", len(frames)))
        registry.extend(struct.pack(f"<{len(frames)}I", *frames))
    return bytes(registry), assets


def build_interpolated_pack_record(
    resref: str, interpolation: dict[str, Any], interpolation_dir: Path
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    frames = interpolation.get("frames")
    timing = interpolation.get("timing")
    if not isinstance(frames, list) or not frames or not isinstance(timing, dict):
        raise RuntimeError("frames ou timing interpolation absents")
    if [frame.get("frame") for frame in frames] != list(range(len(frames))):
        raise RuntimeError("frames interpolées non contiguës")
    native_fps = timing.get("native_fps")
    target_fps = timing.get("target_fps")
    native_indices = timing.get("native_frame_indices")
    timeline_indices = timing.get("timeline_frame_indices")
    if (
        not isinstance(native_fps, list)
        or not isinstance(target_fps, list)
        or len(native_fps) != 2
        or len(target_fps) != 2
        or not all(type(value) is int and value > 0 for value in native_fps + target_fps)
        or not isinstance(native_indices, list)
        or not isinstance(timeline_indices, list)
        or timeline_indices != list(range(len(frames)))
        or int(timing.get("timeline_phase_count", 0)) != len(frames)
        or not native_indices
        or any(type(value) is not int or value < 0 or value >= len(frames) for value in native_indices)
    ):
        raise RuntimeError("timing interpolation invalide")
    multiplier_numerator = target_fps[0] * native_fps[1]
    multiplier_denominator = native_fps[0] * target_fps[1]
    if multiplier_numerator <= multiplier_denominator or multiplier_numerator % multiplier_denominator:
        raise RuntimeError("ratio FPS interpolation invalide")
    if len(frames) != len(native_indices) * multiplier_numerator // multiplier_denominator:
        raise RuntimeError("nombre de phases interpolation incompatible avec le cycle natif")

    registry = bytearray(resref.encode("ascii").ljust(8, b"\0"))
    registry.extend(struct.pack("<II", len(frames), 1))
    assets: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        logical = frame.get("logical_size_x1")
        physical = frame.get("physical_size_x4")
        raw_relative = frame.get("raw_rgba_x4")
        if (
            not isinstance(logical, list)
            or not isinstance(physical, list)
            or len(logical) != 2
            or len(physical) != 2
            or not all(type(value) is int and value > 0 for value in logical + physical)
            or physical != [logical[0] * 4, logical[1] * 4]
            or not isinstance(raw_relative, str)
        ):
            raise RuntimeError(f"frame interpolée {index}: géométrie absente ou invalide")
        raw_path = require_relative(interpolation_dir, raw_relative, f"frame interpolée {index}")
        expected_bytes = physical[0] * physical[1] * 4
        if not raw_path.is_file() or raw_path.stat().st_size != expected_bytes:
            raise RuntimeError(f"frame interpolée {index}: RGBA absent ou tronqué")
        digest = require_hash(raw_path, str(frame.get("raw_rgba_x4_sha256", "")), f"frame interpolée {index}")
        registry.extend(struct.pack("<II", logical[0], logical[1]))
        assets.append(
            {
                "frame": index,
                "asset": frame_asset_name(resref, index),
                "source": relative_to_repo(raw_path),
                "sha256": digest,
                "bytes": expected_bytes,
                "logical_size_x1": logical,
                "physical_size_x4": physical,
                "alpha_source_frame": frame.get("alpha_source_frame"),
            }
        )
    registry.extend(struct.pack(f"<I{len(native_indices)}I", len(native_indices), *native_indices))
    registry.extend(
        struct.pack(
            "<IIIII",
            native_fps[0], native_fps[1], target_fps[0], target_fps[1], len(timeline_indices),
        )
    )
    registry.extend(struct.pack(f"<{len(timeline_indices)}I", *timeline_indices))
    timeline = {
        "native_fps": native_fps,
        "target_fps": target_fps,
        "phase_count": len(timeline_indices),
        "native_frame_indices": native_indices,
        "timeline_frame_indices": timeline_indices,
    }
    return bytes(registry), assets, timeline


def write_pack(output: Path, registry: bytes, assets: list[dict[str, Any]],
               descriptor: dict[str, Any], frames_x1: dict[str, Any], spatial: dict[str, Any],
               *, registry_version: int = REGISTRY_VERSION,
               timeline: dict[str, Any] | None = None,
               interpolation_descriptor: dict[str, Any] | None = None) -> dict[str, Any]:
    if output.exists():
        if not output.is_dir():
            raise RuntimeError(f"sortie runtime non répertoire : {output}")
        residual = {path.name for path in output.iterdir()} - {"README.md"}
        if residual:
            raise RuntimeError(f"sortie runtime déjà occupée : {output}")
    else:
        output.mkdir(parents=True)
    try:
        registry_path = output / REGISTRY_NAME
        registry_path.write_bytes(registry)
        for asset in assets:
            source = REPO_ROOT / asset["source"]
            target = output / asset["asset"]
            shutil.copyfile(source, target)
            if sha256_file(target) != asset["sha256"]:
                raise RuntimeError(f"copie runtime corrompue : {asset['asset']}")
        manifest = {
            "schema": PACK_SCHEMA,
            "status": "completed",
            "created_utc": utc_now(),
            "resref": descriptor["asset_ids"][0].rsplit(":", 1)[-1],
            "scale": 4,
            "registry": REGISTRY_NAME,
            "registry_magic": REGISTRY_MAGIC.rstrip(b"\0").decode("ascii"),
            "registry_version": registry_version,
            "registry_sha256": sha256_file(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "frame_count": len(assets),
            "cycles": frames_x1["cycles"],
            "frames": assets,
            "source": {
                "spatial_run": descriptor["run_id"],
                "spatial_run_descriptor_sha256": sha256_file(
                    REPO_ROOT / "effects" / "ressources" / descriptor["asset_ids"][0].rsplit(":", 1)[-1] / "runs" / descriptor["run_id"] / "run.json"
                ),
                "source_bam_sha256": frames_x1["source_sha256"],
                "spatial_manifest_sha256": sha256_file(
                    REPO_ROOT / next(
                        item["path"] for item in descriptor["outputs"] if item["role"] == "spatial-manifest"
                    )
                ),
            },
        }
        if timeline is not None:
            manifest["timeline"] = timeline
        if interpolation_descriptor is not None:
            manifest["source"]["interpolation_run"] = interpolation_descriptor["run_id"]
            manifest["source"]["interpolation_run_descriptor_sha256"] = sha256_file(
                REPO_ROOT / "effects" / "ressources" / descriptor["asset_ids"][0].rsplit(":", 1)[-1]
                / "runs" / interpolation_descriptor["run_id"] / "run.json"
            )
        (output / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest
    except Exception:
        # A partial pack is deliberately left visible for diagnosis and cannot
        # be used: the runtime requires registry + all exact payloads.
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True, help="BAM effect resref")
    parser.add_argument("--spatial-run", required=True, help="sealed spatial run id")
    parser.add_argument(
        "--interpolation-run",
        help="sealed 30 FPS derived run; omitted builds the native-cadence x4 pack",
    )
    parser.add_argument(
        "--output",
        default="engine/InfinityEngine-Enhancer/source-patchee/assets/effects",
        help="empty runtime-pack destination relative to the workspace",
    )
    parser.add_argument("--run", action="store_true", help="write the runtime pack")
    args = parser.parse_args(argv)
    try:
        resref = args.resref.strip().upper()
        run_dir = REPO_ROOT / "effects" / "ressources" / resref / "runs" / args.spatial_run
        output = require_relative(REPO_ROOT, args.output, "sortie runtime")
        descriptor, frames_x1, spatial = validate_input(resref, run_dir)
        spatial_path = REPO_ROOT / next(
            item["path"] for item in descriptor["outputs"] if item["role"] == "spatial-manifest"
        )
        registry_version = REGISTRY_VERSION
        timeline: dict[str, Any] | None = None
        interpolation_descriptor: dict[str, Any] | None = None
        if args.interpolation_run:
            interpolation_dir = (
                REPO_ROOT / "effects" / "ressources" / resref / "runs" / args.interpolation_run
            )
            interpolation_descriptor, interpolation, interpolation_path = validate_interpolation_input(
                resref, interpolation_dir, descriptor
            )
            registry_record, assets, timeline = build_interpolated_pack_record(
                resref, interpolation, interpolation_path.parent
            )
            registry_version = TIMELINE_REGISTRY_VERSION
        else:
            registry_record, assets = build_pack_record(resref, frames_x1, spatial, spatial_path.parent)
        registry = bytearray(REGISTRY_MAGIC)
        registry.extend(struct.pack("<IIII", registry_version, 4, 1, 0))
        registry.extend(registry_record)
        plan = {
            "resref": resref,
            "spatial_run": args.spatial_run,
            "output": relative_to_repo(output),
            "registry": REGISTRY_NAME,
            "registry_version": registry_version,
            "registry_bytes": len(registry),
            "frame_count": len(assets),
            "frame_bytes": sum(int(asset["bytes"]) for asset in assets),
            "interpolation_run": args.interpolation_run,
            "write": bool(args.run),
        }
        if not args.run:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        manifest = write_pack(
            output, bytes(registry), assets, descriptor, frames_x1, spatial,
            registry_version=registry_version, timeline=timeline,
            interpolation_descriptor=interpolation_descriptor,
        )
        plan["manifest_sha256"] = sha256_file(output / "manifest.json")
        plan["registry_sha256"] = manifest["registry_sha256"]
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"erreur: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
