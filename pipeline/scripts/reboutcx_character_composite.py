"""Compose sealed Character body/equipment ReboutCX prototypes for offline QA."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import struct
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw

import reboutcx_batch as batch
from reboutcx_quantize import reconstruct_rgba
from run_creature_sprite_x2 import (
    LEGACY_UPSCALE,
    REGISTRY_FRAME_HEADER_BYTES,
    REGISTRY_HEADER_BYTES,
    REGISTRY_RESOURCE_HEADER_BYTES,
    SourceFrame,
    has_duplicate_used_rgba_indices,
    load_source_frames,
    map_output,
    run_xbr,
    xbr_provenance_indices,
)
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
JOB_SCHEMA = "bg2-upscale-reboutcx-character-composite-job-v1"
RUN_SCHEMA = "bg2-upscale-reboutcx-character-composite-run-v1"
PANELS = (
    ("xbr-body-xbr-weapon", "xBR body + arme"),
    ("reboutcx-body-xbr-weapon", "ReboutCX body + arme xBR"),
    ("reboutcx-body-reboutcx-weapon", "ReboutCX body + arme"),
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    return batch.sha256_file(path)


def sha256_pixels(array: np.ndarray) -> str:
    return batch.sha256_pixels(array)


def relative(path: Path) -> str:
    return batch.relative(path)


def composite_bounds(frames: Sequence[SourceFrame]) -> tuple[int, int, int, int]:
    if not frames:
        raise RuntimeError("Character composite has no layers")
    left = min(-frame.center_x for frame in frames)
    top = min(-frame.center_y for frame in frames)
    right = max(-frame.center_x + frame.width for frame in frames)
    bottom = max(-frame.center_y + frame.height for frame in frames)
    if right <= left or bottom <= top:
        raise RuntimeError("Character composite bounds are empty")
    return left, top, right, bottom


def compose_index_layers(
    frames: Mapping[str, SourceFrame],
    indices: Mapping[str, np.ndarray],
    order: Sequence[str],
    palette_rgb: np.ndarray,
    bounds: tuple[int, int, int, int],
    *,
    scale: int = 2,
) -> np.ndarray:
    if scale <= 0 or set(order) != set(frames) or len(order) != len(frames):
        raise RuntimeError("Character composite layer order differs")
    left, top, right, bottom = bounds
    output = np.zeros(((bottom - top) * scale, (right - left) * scale, 4), dtype=np.uint8)
    for name in order:
        frame = frames[name]
        mapped = np.asarray(indices[name], dtype=np.uint8)
        if mapped.shape != (frame.height * scale, frame.width * scale):
            raise RuntimeError(f"Character composite layer dimensions differ: {name}")
        rgba = reconstruct_rgba(mapped, palette_rgb, frame.transparent)
        x = (-frame.center_x - left) * scale
        y = (-frame.center_y - top) * scale
        target = output[y : y + rgba.shape[0], x : x + rgba.shape[1]]
        mask = rgba[..., 3] != 0
        target[mask] = rgba[mask]
    return output


def read_prototype_indices(
    registry_path: Path, manifest: Mapping[str, Any]
) -> dict[int, np.ndarray]:
    frame_records = list(manifest["frames"])
    with registry_path.open("rb") as stream:
        header = stream.read(REGISTRY_HEADER_BYTES)
        if header[:8] != b"IEECSXN\0":
            raise RuntimeError("prototype registry magic differs")
        version, scale, resource_count, animation_id = struct.unpack_from("<IIII", header, 8)
        if (
            version != 3
            or scale != 2
            or resource_count != 1
            or animation_id != int(str(manifest["animation_id"]), 16)
        ):
            raise RuntimeError("prototype registry header differs")
        resource_header = stream.read(REGISTRY_RESOURCE_HEADER_BYTES)
        resref = resource_header[:8].split(b"\0", 1)[0].decode("ascii")
        frame_count, cycle_count = struct.unpack_from("<II", resource_header, 40)
        if frame_count != len(frame_records) or cycle_count != 1:
            raise RuntimeError("prototype registry resource metadata differs")
        if any(str(record["resref"]) != resref for record in frame_records):
            raise RuntimeError("prototype registry resref differs")
        result: dict[int, np.ndarray] = {}
        for record in frame_records:
            frame_header = stream.read(REGISTRY_FRAME_HEADER_BYTES)
            width, height, center_x, center_y, transparent, stored = struct.unpack_from(
                "<HHhhB3xI", frame_header, 0
            )
            expected = (
                int(record["width"]),
                int(record["height"]),
                int(record["center_x"]),
                int(record["center_y"]),
                int(record["transparent_index"]),
                int(record["width"]) * int(record["height"]) * scale * scale,
            )
            if (width, height, center_x, center_y, transparent, stored) != expected:
                raise RuntimeError("prototype registry frame geometry differs")
            payload = np.frombuffer(stream.read(stored), dtype=np.uint8).copy()
            indices = payload.reshape(height * scale, width * scale)
            if sha256_pixels(indices) != str(record["quantized_index_sha256"]):
                raise RuntimeError("prototype registry frame indices differ")
            source_frame = int(record["source_frame"])
            if source_frame in result:
                raise RuntimeError("prototype registry source frame is duplicated")
            result[source_frame] = indices
        slots_raw = stream.read(4)
        if len(slots_raw) != 4:
            raise RuntimeError("prototype registry cycle lookup is missing")
        slots = struct.unpack("<I", slots_raw)[0]
        lookup = struct.unpack(f"<{slots}I", stream.read(slots * 4))
        if slots != frame_count or lookup != tuple(range(frame_count)) or stream.read(1):
            raise RuntimeError("prototype registry synthetic cycle differs")
    return result


def verified_layer(specification: Mapping[str, Any]) -> dict[str, Any]:
    job_path = resolve_path_reference(
        str(specification["job"]), required=True, root=PROJECT_ROOT
    )
    with contextlib.redirect_stdout(io.StringIO()):
        batch.verify(job_path)
    job = read_json(job_path)
    run_dir = resolve_path_reference(job["paths"]["run_dir"], required=True, root=PROJECT_ROOT)
    manifest_path = run_dir / "manifest.json"
    if sha256_file(manifest_path) != str(specification["manifest_sha256"]):
        raise RuntimeError(f"sealed child manifest differs: {specification['name']}")
    manifest = read_json(manifest_path)
    source_manifest_path = resolve_path_reference(
        job["paths"]["source_manifest"], required=True, root=PROJECT_ROOT
    )
    all_frames, _resources, _source_manifest = load_source_frames(source_manifest_path)
    resref = str(specification["resref"]).upper()
    source_frames = {frame.index: frame for frame in all_frames if frame.resref == resref}
    wanted = {int(record["source_frame"]) for record in manifest["frames"]}
    if wanted != set(source_frames).intersection(wanted):
        raise RuntimeError(f"sealed child source frames differ: {specification['name']}")
    registry_path = resolve_path_reference(
        manifest["registry"]["path"], required=True, root=PROJECT_ROOT
    )
    quantized = read_prototype_indices(registry_path, manifest)
    selected = [source_frames[int(record["source_frame"])] for record in manifest["frames"]]
    scalepix = resolve_path_reference(job["paths"]["scalepix"], required=True, root=PROJECT_ROOT)
    xbr_outputs = run_xbr(selected, scalepix, str(job["tools"]["node"]), LEGACY_UPSCALE)
    guides: dict[int, np.ndarray] = {}
    for frame, (width, height, pixels), record in zip(selected, xbr_outputs, manifest["frames"]):
        provenance = (
            xbr_provenance_indices(frame, 2)
            if has_duplicate_used_rgba_indices(frame)
            else None
        )
        guide, _representatives = map_output(frame, pixels, provenance)
        guide = guide.reshape(height, width)
        if sha256_pixels(guide) != str(record["guide_index_sha256"]):
            raise RuntimeError(f"sealed child xBR guide differs: {specification['name']}")
        guides[frame.index] = guide
    return {
        "name": str(specification["name"]),
        "job": job,
        "job_path": job_path,
        "manifest": manifest,
        "manifest_path": manifest_path,
        "source_frames": source_frames,
        "guides": guides,
        "quantized": quantized,
    }


def make_comparison_gif(
    destination: Path,
    frames: Sequence[dict[str, np.ndarray]],
    labels: Sequence[str],
    *,
    duration_ms: int,
) -> None:
    margin, label_height = 12, 28
    panel_width = max(170, max(frame[label].shape[1] for frame in frames for label in labels))
    panel_height = max(frame[label].shape[0] for frame in frames for label in labels)
    animation: list[Image.Image] = []
    for frame_number, frame in enumerate(frames):
        canvas = Image.new(
            "RGBA",
            ((panel_width + margin) * len(labels) + margin, panel_height + label_height + margin),
            (24, 26, 30, 255),
        )
        draw = ImageDraw.Draw(canvas)
        for column, label in enumerate(labels):
            origin_x = margin + column * (panel_width + margin)
            draw.text((origin_x + 3, 7), dict(PANELS)[label], fill="white")
            background = batch.checkerboard(panel_width, panel_height)
            pixels = frame[label]
            background.alpha_composite(
                Image.fromarray(pixels, "RGBA"), ((panel_width - pixels.shape[1]) // 2, 0)
            )
            canvas.alpha_composite(background, (origin_x, label_height))
        draw.text((margin, panel_height + label_height), f"pose {frame_number + 1}", fill="white")
        animation.append(canvas.convert("RGB"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    animation[0].save(
        destination,
        save_all=True,
        append_images=animation[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )


def execute(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if job.get("schema") != JOB_SCHEMA or job.get("installable") is not False:
        raise RuntimeError("invalid or installable Character composite job")
    output = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)
    if output.exists():
        raise RuntimeError(f"Character composite run already exists: {output}")
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise RuntimeError(f"temporary Character composite run already exists: {temporary}")
    layers = {str(spec["name"]): verified_layer(spec) for spec in job["layers"]}
    if set(layers) != {"body", "weapon"}:
        raise RuntimeError("P6.3 requires exactly body and weapon layers")
    palette_profiles, palette_evidence = batch.load_palette_profiles(layers["body"]["job"])
    if palette_evidence is None or palette_evidence != layers["body"]["manifest"]["palette_reference"]:
        raise RuntimeError("body Character palette evidence differs")
    if palette_evidence != layers["weapon"]["manifest"]["palette_reference"]:
        raise RuntimeError("body and weapon Character palettes differ")
    profile_by_name = {str(profile["name"]): profile for profile in palette_profiles}
    profile_names = [str(name) for name in job["palette_profiles"]]
    if len(profile_names) != len(set(profile_names)) or any(
        name not in profile_by_name for name in profile_names
    ):
        raise RuntimeError("Character composite palette selection differs")

    qa: list[dict[str, Any]] = []
    frame_evidence: list[dict[str, Any]] = []
    temporary.mkdir(parents=True)
    try:
        for group in job["groups"]:
            group_name = str(group["name"])
            order = [str(name) for name in group["order"]]
            group_frames = [int(value) for value in group["frames"]]
            sources_by_frame = {
                frame_index: {
                    name: layer["source_frames"][frame_index]
                    for name, layer in layers.items()
                }
                for frame_index in group_frames
            }
            group_bounds = composite_bounds(
                [
                    frame
                    for source in sources_by_frame.values()
                    for frame in source.values()
                ]
            )
            rendered_by_profile: dict[str, list[dict[str, np.ndarray]]] = {
                name: [] for name in profile_names
            }
            for frame_index in group_frames:
                source = sources_by_frame[frame_index]
                variants = {
                    "xbr-body-xbr-weapon": {
                        name: layer["guides"][frame_index] for name, layer in layers.items()
                    },
                    "reboutcx-body-xbr-weapon": {
                        "body": layers["body"]["quantized"][frame_index],
                        "weapon": layers["weapon"]["guides"][frame_index],
                    },
                    "reboutcx-body-reboutcx-weapon": {
                        name: layer["quantized"][frame_index] for name, layer in layers.items()
                    },
                }
                hashes: dict[str, dict[str, str]] = {}
                for profile_name in profile_names:
                    palette = profile_by_name[profile_name]["palette"]
                    rendered = {
                        panel: compose_index_layers(
                            source, indices, order, palette, group_bounds
                        )
                        for panel, indices in variants.items()
                    }
                    rendered_by_profile[profile_name].append(rendered)
                    hashes[profile_name] = {
                        panel: sha256_pixels(pixels) for panel, pixels in rendered.items()
                    }
                frame_evidence.append(
                    {
                        "group": group_name,
                        "source_frame": frame_index,
                        "order": order,
                        "bounds": list(group_bounds),
                        "pixel_sha256": hashes,
                    }
                )
            for profile_index, profile_name in enumerate(profile_names):
                path = temporary / "qa" / f"{group_name}-palette-{profile_index:02d}.gif"
                make_comparison_gif(
                    path,
                    rendered_by_profile[profile_name],
                    [name for name, _label in PANELS],
                    duration_ms=int(group["duration_ms"]),
                )
                qa.append(
                    {
                        "group": group_name,
                        "palette": profile_name,
                        "path": relative(path),
                        "sha256": sha256_file(path),
                        "frames": len(group_frames),
                        "duration_ms": int(group["duration_ms"]),
                    }
                )
        manifest = {
            "schema": RUN_SCHEMA,
            "status": "completed-pending-human-review",
            "installable": False,
            "job": relative(job_path),
            "job_sha256": sha256_file(job_path),
            "animation_id": str(job["animation_id"]),
            "code": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "layers": [
                {
                    "name": name,
                    "resref": str(layer["manifest"]["frames"][0]["resref"]),
                    "job": relative(layer["job_path"]),
                    "job_sha256": sha256_file(layer["job_path"]),
                    "manifest": relative(layer["manifest_path"]),
                    "manifest_sha256": sha256_file(layer["manifest_path"]),
                    "registry_sha256": str(layer["manifest"]["registry"]["sha256"]),
                }
                for name, layer in layers.items()
            ],
            "palette_reference": palette_evidence,
            "palette_profiles": profile_names,
            "composition": {
                "scale": 2,
                "placement": "native-centers-x1-then-scale-x2",
                "transfer": "ordered-overwrite-alpha-nonzero",
                "panels": [name for name, _label in PANELS],
            },
            "groups": job["groups"],
            "frames": frame_evidence,
            "qa": qa,
        }
        temporary_prefix = relative(temporary)
        output_prefix = relative(output)
        manifest = json.loads(json.dumps(manifest).replace(temporary_prefix, output_prefix))
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        temporary.rename(output)
    except BaseException:
        if temporary.exists():
            import shutil

            shutil.rmtree(temporary)
        raise
    result = {
        "status": manifest["status"],
        "run": relative(output),
        "manifest_sha256": sha256_file(output / "manifest.json"),
        "qa": len(qa),
    }
    print(json.dumps(result, indent=2))
    return manifest


def verify(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    output = resolve_path_reference(job["paths"]["run_dir"], required=True, root=PROJECT_ROOT)
    manifest_path = output / "manifest.json"
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != RUN_SCHEMA
        or manifest.get("status") != "completed-pending-human-review"
        or manifest.get("installable") is not False
        or manifest.get("job_sha256") != sha256_file(job_path)
        or manifest.get("code", {}).get("sha256") != sha256_file(Path(__file__))
    ):
        raise RuntimeError("Character composite manifest differs")
    layer_specs = {str(spec["name"]): spec for spec in job["layers"]}
    for evidence in manifest["layers"]:
        specification = layer_specs[str(evidence["name"])]
        if str(evidence["manifest_sha256"]) != str(specification["manifest_sha256"]):
            raise RuntimeError("Character composite child pin differs")
        verified_layer(specification)
    checked = 2
    for evidence in manifest["qa"]:
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError("Character composite QA file differs")
        checked += 1
    result = {
        "status": "verified",
        "run": relative(output),
        "manifest_sha256": sha256_file(manifest_path),
        "checked_files": checked,
        "qa": len(manifest["qa"]),
    }
    print(json.dumps(result, indent=2))
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("job", type=Path)
    arguments = parser.parse_args(argv)
    if arguments.command == "run":
        execute(arguments.job.resolve())
    else:
        verify(arguments.job.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
