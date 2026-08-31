"""Upscale extracted BAM frames with SeedVR while preserving native BAM geometry.

RGB is sent to SeedVR. Alpha is always enlarged from the x1 source with nearest
neighbour. With ``--frame-manifest``, aligned model canvases are cropped back to
each frame's native BAM rectangle before runtime PNG and raw RGBA assets are
written. Runs are resumable frame by frame and validated with SHA-256.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from workspace_paths import get_service

from run_seedvr_comfyui import (
    APPROVED_3B_SHA256,
    APPROVED_7B_SHA256,
    ComfyClient,
    find_single_node,
    sha256_file,
    validate_approved_7b_settings,
    validate_seedvr_baseline,
    workflow_summary,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = (
    PROJECT_ROOT / "pipeline" / "comfyui" / "workflows" / "SeedVR-Image-BG2-Pipeline-7B.api.json"
)
SCHEMA = "bg2-upscale-animation-frames-v1"


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args(argv: list[str] | None = None, default_scale: int = 4) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rgb_frames", type=Path, help="dossier frame_XXX.png RGB x1 aligné")
    parser.add_argument("alpha_frames", type=Path, help="dossier frame_XXX.png alpha x1 aligné")
    parser.add_argument("output", type=Path, help="dossier de sortie")
    parser.add_argument(
        "--frame-manifest",
        type=Path,
        help="manifest.json produit par export_bam_frames.py; requis pour les géométries variables",
    )
    parser.add_argument("--scale", type=int, choices=(2, 4), default=default_scale)
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--server", default=get_service("comfyui_url"))
    parser.add_argument("--pad", type=int, default=32, help="marge x1 autour du canvas aligné")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument(
        "--upload-folder",
        default="BG2_Upscale/animation-runs",
        help="sous-dossier d'upload ComfyUI réservé au lot",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="reprend les frames absentes après validation des sorties déjà terminées",
    )
    args = parser.parse_args(argv)
    if args.pad < 0:
        parser.error("--pad doit être positif ou nul")
    if args.poll_seconds <= 0 or args.timeout_seconds <= 0:
        parser.error("les délais doivent être strictement positifs")
    return args


def atomic_save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    image.save(partial, format="PNG")
    partial.replace(path)


def atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    partial.replace(path)


def list_frames(directory: Path) -> list[Path]:
    frames = sorted(directory.glob("frame_*.png"))
    if not frames:
        raise RuntimeError(f"aucune frame frame_XXX.png dans {directory}")
    expected = [f"frame_{index:03d}.png" for index in range(len(frames))]
    actual = [path.name for path in frames]
    if actual != expected:
        raise RuntimeError(f"numérotation de frames non contiguë dans {directory}: {actual}")
    return frames


def padded_source(source: Path, destination: Path, pad: int) -> tuple[int, int]:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    padded = Image.new("RGBA", (image.width + 2 * pad, image.height + 2 * pad), (0, 0, 0, 0))
    padded.paste(image, (pad, pad))
    atomic_save(padded, destination)
    return image.size


def save_raw_rgba(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".part")
    partial.write_bytes(image.convert("RGBA").tobytes())
    partial.replace(path)


def make_contact_sheet(frames: list[Path], destination: Path) -> None:
    images: list[Image.Image] = []
    for path in frames:
        with Image.open(path) as opened:
            images.append(opened.convert("RGBA"))
    columns = min(4, max(1, len(images)))
    rows = (len(images) + columns - 1) // columns
    cell_width = max(image.width for image in images)
    cell_height = max(image.height for image in images)
    label_height = 24
    canvas = Image.new(
        "RGBA",
        (columns * cell_width, rows * (cell_height + label_height)),
        (38, 38, 38, 255),
    )
    draw = ImageDraw.Draw(canvas)
    for index, frame in enumerate(images):
        x = (index % columns) * cell_width
        y = (index // columns) * (cell_height + label_height)
        draw.text((x + 4, y + 4), f"frame {index:03d}", fill=(236, 236, 236, 255))
        canvas.alpha_composite(frame, (x, y + label_height))
    atomic_save(canvas, destination)


def load_geometry(
    manifest_path: Path | None,
    frame_paths: list[Path],
    aligned_size: tuple[int, int],
) -> tuple[dict[str, dict[str, Any]], str | None, str]:
    if manifest_path is None:
        geometry = {
            path.name: {
                "frame": index,
                "source_size": list(aligned_size),
                "centre": None,
                "canvas_offset": [0, 0],
            }
            for index, path in enumerate(frame_paths)
        }
        return geometry, None, "uniform"

    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise RuntimeError(f"manifeste de frames introuvable : {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") not in (None, "bg2-upscale-animation-frames-x1-v1"):
        raise RuntimeError(f"schéma de frames non pris en charge : {payload.get('schema')}")
    if tuple(payload.get("aligned_canvas_size", ())) != aligned_size:
        raise RuntimeError(
            f"canvas du manifeste {payload.get('aligned_canvas_size')}, images {list(aligned_size)}"
        )
    entries = {str(item.get("file")): item for item in payload.get("frames", [])}
    geometry: dict[str, dict[str, Any]] = {}
    for index, path in enumerate(frame_paths):
        item = entries.get(path.name)
        if item is None or item.get("frame") != index:
            raise RuntimeError(f"géométrie absente ou incohérente pour {path.name}")
        width, height = (int(value) for value in item["source_size"])
        offset_x, offset_y = (int(value) for value in item["canvas_offset"])
        if width <= 0 or height <= 0:
            raise RuntimeError(f"taille native invalide pour {path.name}")
        if offset_x < 0 or offset_y < 0 or offset_x + width > aligned_size[0] or offset_y + height > aligned_size[1]:
            raise RuntimeError(f"rectangle natif hors canvas pour {path.name}")
        centre = item.get("centre")
        if not isinstance(centre, list) or len(centre) != 2:
            raise RuntimeError(f"centre BAM invalide pour {path.name}")
        geometry[path.name] = {
            "frame": index,
            "source_size": [width, height],
            "centre": [int(centre[0]), int(centre[1])],
            "canvas_offset": [offset_x, offset_y],
        }
    return geometry, sha256_file(manifest_path), str(payload.get("geometry_mode", "unknown"))


def job_signature(payload: dict[str, Any]) -> str:
    serialised = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialised).hexdigest()


def resolve_output(output: Path, relative: str) -> Path:
    path = (output / relative).resolve()
    try:
        path.relative_to(output)
    except ValueError as exc:
        raise RuntimeError(f"chemin de sortie hors dossier : {relative}") from exc
    return path


def validate_completed_record(
    record: dict[str, Any],
    output: Path,
    geometry: dict[str, Any],
    aligned_size: tuple[int, int],
    scale: int,
) -> Path:
    logical_size = tuple(int(value) for value in geometry["source_size"])
    offset_x, offset_y = (int(value) for value in geometry["canvas_offset"])
    expected_physical = (logical_size[0] * scale, logical_size[1] * scale)
    expected_crop = (
        offset_x * scale,
        offset_y * scale,
        (offset_x + logical_size[0]) * scale,
        (offset_y + logical_size[1]) * scale,
    )
    metadata_checks = {
        "aligned_size_x1": list(aligned_size),
        "logical_size_x1": list(logical_size),
        "physical_size_xn": list(expected_physical),
        "centre_x1": geometry["centre"],
        "canvas_offset_x1": [offset_x, offset_y],
        "runtime_crop_box_xn": list(expected_crop),
    }
    for key, expected in metadata_checks.items():
        if record.get(key) != expected:
            raise RuntimeError(f"frame {record.get('frame')}: métadonnée {key} incohérente")

    path_keys = ("aligned_rgba_xn", "rgb_xn", "alpha_xn", "rgba_xn", "raw_rgba_xn")
    for key in path_keys:
        relative = record.get(key)
        expected_hash = record.get(f"{key}_sha256")
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise RuntimeError(f"frame {record.get('frame')}: sortie {key} non enregistrée")
        path = resolve_output(output, relative)
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise RuntimeError(f"frame {record.get('frame')}: sortie modifiée ou absente : {path}")

    rgba_path = resolve_output(output, record["rgba_xn"])
    aligned_path = resolve_output(output, record["aligned_rgba_xn"])
    with Image.open(rgba_path) as image:
        if image.size != expected_physical:
            raise RuntimeError(f"frame {record.get('frame')}: dimensions runtime invalides")
    with Image.open(aligned_path) as image:
        if image.size != (aligned_size[0] * scale, aligned_size[1] * scale):
            raise RuntimeError(f"frame {record.get('frame')}: dimensions alignées invalides")
    raw_path = resolve_output(output, record["raw_rgba_xn"])
    expected_bytes = logical_size[0] * scale * logical_size[1] * scale * 4
    if raw_path.stat().st_size != expected_bytes:
        raise RuntimeError(f"frame {record.get('frame')}: taille RGBA brute invalide")
    return rgba_path


def main(argv: list[str] | None = None, default_scale: int = 4) -> None:
    args = parse_args(argv, default_scale)
    rgb_dir = args.rgb_frames.resolve()
    alpha_dir = args.alpha_frames.resolve()
    output = args.output.resolve()
    if not rgb_dir.is_dir() or not alpha_dir.is_dir():
        raise RuntimeError("les dossiers RGB et alpha doivent exister")
    if output.exists() and any(output.iterdir()) and not args.resume:
        raise RuntimeError(f"destination non vide; utiliser --resume : {output}")

    rgb_frames = list_frames(rgb_dir)
    alpha_frames = {path.name: path for path in list_frames(alpha_dir)}
    if set(alpha_frames) != {path.name for path in rgb_frames}:
        raise RuntimeError("les ensembles de frames RGB et alpha diffèrent")

    with Image.open(rgb_frames[0]) as first:
        aligned_size = first.size
    for rgb_path in rgb_frames:
        with Image.open(rgb_path) as rgb_image, Image.open(alpha_frames[rgb_path.name]) as alpha_image:
            if rgb_image.size != aligned_size or alpha_image.size != aligned_size:
                raise RuntimeError(f"{rgb_path.name}: canvas RGB/alpha non aligné")

    geometry, geometry_hash, geometry_mode = load_geometry(
        args.frame_manifest,
        rgb_frames,
        aligned_size,
    )

    workflow_path = args.workflow.resolve()
    workflow_hash = sha256_file(workflow_path)
    if workflow_hash.lower() not in (APPROVED_7B_SHA256, APPROVED_3B_SHA256):
        raise RuntimeError(f"workflow non approuvé pour les animations : {workflow_hash}")
    prompt_template = json.loads(workflow_path.read_text(encoding="utf-8"))
    load_id = find_single_node(prompt_template, "LoadImage")
    save_id = find_single_node(prompt_template, "SaveImage")
    resize_id = find_single_node(prompt_template, "ResizeImageMaskNode")
    prompt_template[resize_id]["inputs"]["resize_type.multiplier"] = args.scale
    baseline = workflow_summary(prompt_template)
    if workflow_hash.lower() == APPROVED_7B_SHA256:
        validate_approved_7b_settings(baseline)
    else:
        validate_seedvr_baseline(baseline)

    source_records = []
    for rgb_path in rgb_frames:
        source_records.append({
            "file": rgb_path.name,
            "rgb_sha256": sha256_file(rgb_path),
            "alpha_sha256": sha256_file(alpha_frames[rgb_path.name]),
            "geometry": geometry[rgb_path.name],
        })
    signature_payload = {
        "scale": args.scale,
        "padding_x1": args.pad,
        "workflow_sha256": workflow_hash,
        "frame_manifest_sha256": geometry_hash,
        "sources": source_records,
    }
    signature = job_signature(signature_payload)
    manifest_path = output / "manifest.json"
    manifest: dict[str, Any]
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not args.resume:
            raise RuntimeError(f"manifeste existant; utiliser --resume : {manifest_path}")
        if manifest.get("schema") != SCHEMA or manifest.get("job_signature") != signature:
            raise RuntimeError("le run existant ne correspond pas aux sources ou paramètres demandés")
    else:
        if output.exists() and any(output.iterdir()):
            raise RuntimeError(f"sorties sans manifeste, reprise impossible : {output}")
        output.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema": SCHEMA,
            "status": "running",
            "created_utc": utc_now(),
            "updated_utc": utc_now(),
            "job_signature": signature,
            "source": {
                "rgb": rgb_dir.as_posix(),
                "alpha": alpha_dir.as_posix(),
                "frame_manifest": args.frame_manifest.resolve().as_posix() if args.frame_manifest else None,
                "frame_manifest_sha256": geometry_hash,
            },
            "workflow": {"path": workflow_path.as_posix(), "sha256": workflow_hash},
            "parameters": {key: value for key, value in baseline.items() if key != "node_ids"},
            "scale": args.scale,
            "padding_x1": args.pad,
            "aligned_canvas_size_x1": list(aligned_size),
            "geometry_mode": geometry_mode,
            "alpha_policy": "source alpha enlarged with nearest-neighbour; never generated by SeedVR",
            "raw_rgba_layout": "RGBA8, tightly packed, top-to-bottom rows",
            "frames": [],
        }
        atomic_write_json(manifest, manifest_path)

    completed: dict[int, dict[str, Any]] = {}
    result_frames: list[Path] = []
    for record in manifest.get("frames", []):
        frame_index = int(record.get("frame", -1))
        if frame_index in completed or frame_index < 0 or frame_index >= len(rgb_frames):
            raise RuntimeError("index de frame dupliqué ou invalide dans le manifeste de reprise")
        meta = geometry[rgb_frames[frame_index].name]
        result_frames.append(validate_completed_record(
            record,
            output,
            meta,
            aligned_size,
            args.scale,
        ))
        completed[frame_index] = record

    pending = [index for index in range(len(rgb_frames)) if index not in completed]
    if not pending and manifest.get("status") == "completed":
        preview_relative = manifest.get("preview")
        preview_hash = manifest.get("preview_sha256")
        if not isinstance(preview_relative, str) or not isinstance(preview_hash, str):
            raise RuntimeError("aperçu absent du manifeste terminé")
        preview_path = resolve_output(output, preview_relative)
        if not preview_path.is_file() or sha256_file(preview_path) != preview_hash:
            raise RuntimeError(f"aperçu modifié ou absent : {preview_path}")
        print(f"already completed and validated: {len(completed)} frame(s) in {output}")
        return

    client: ComfyClient | None = None
    try:
        if pending:
            client = ComfyClient(args.server, args.poll_seconds, args.timeout_seconds)
            stats = client.preflight()
            manifest["comfyui"] = {
                "server": args.server,
                "device": (stats.get("devices") or [{}])[0].get("name"),
            }
            manifest["status"] = "running"
            manifest.pop("last_error", None)
            atomic_write_json(manifest, manifest_path)

        for position, frame_index in enumerate(pending, start=1):
            assert client is not None
            rgb_source = rgb_frames[frame_index]
            alpha_source = alpha_frames[rgb_source.name]
            label = rgb_source.stem
            meta = geometry[rgb_source.name]
            padded = output / "00_padded_x1" / rgb_source.name
            actual_aligned_size = padded_source(rgb_source, padded, args.pad)
            if actual_aligned_size != aligned_size:
                raise RuntimeError(f"{label}: canvas source modifié pendant le run")
            with Image.open(alpha_source) as opened:
                alpha_x1 = opened.convert("L")

            uploaded = client.upload(padded, args.upload_folder)
            prompt = copy.deepcopy(prompt_template)
            prompt[load_id]["inputs"]["image"] = uploaded
            prompt[save_id]["inputs"]["filename_prefix"] = (
                f"{args.upload_folder}/{label}-x{args.scale}"
            )
            prompt_id = client.queue(prompt)
            manifest["active_frame"] = frame_index
            manifest["updated_utc"] = utc_now()
            atomic_write_json(manifest, manifest_path)
            print(f"{position}/{len(pending)} {label}: prompt {prompt_id}", flush=True)
            history = client.wait_history(prompt_id)
            images = history.get("outputs", {}).get(save_id, {}).get("images", [])
            if len(images) != 1:
                raise RuntimeError(f"{label}: {len(images)} sortie(s) ComfyUI, une attendue")

            padded_xn_path = output / f"01_comfy_padded_x{args.scale}" / rgb_source.name
            client.download(images[0], padded_xn_path)
            expected_padded_size = (
                (aligned_size[0] + 2 * args.pad) * args.scale,
                (aligned_size[1] + 2 * args.pad) * args.scale,
            )
            with Image.open(padded_xn_path) as opened:
                padded_xn = opened.convert("RGB")
            if padded_xn.size != expected_padded_size:
                raise RuntimeError(f"{label}: {padded_xn.size}, attendu {expected_padded_size}")

            pad_n = args.pad * args.scale
            aligned_rgb = padded_xn.crop((
                pad_n,
                pad_n,
                pad_n + aligned_size[0] * args.scale,
                pad_n + aligned_size[1] * args.scale,
            ))
            aligned_alpha = alpha_x1.resize(aligned_rgb.size, Image.Resampling.NEAREST)
            aligned_rgba = aligned_rgb.convert("RGBA")
            aligned_rgba.putalpha(aligned_alpha)

            offset_x, offset_y = meta["canvas_offset"]
            logical_width, logical_height = meta["source_size"]
            crop_box = (
                offset_x * args.scale,
                offset_y * args.scale,
                (offset_x + logical_width) * args.scale,
                (offset_y + logical_height) * args.scale,
            )
            runtime_rgb = aligned_rgb.crop(crop_box)
            runtime_alpha = aligned_alpha.crop(crop_box)
            runtime_rgba = runtime_rgb.convert("RGBA")
            runtime_rgba.putalpha(runtime_alpha)

            aligned_rgba_path = output / "aligned_rgba" / rgb_source.name
            rgb_path = output / "rgb" / rgb_source.name
            alpha_path = output / "alpha" / rgb_source.name
            rgba_path = output / "rgba" / rgb_source.name
            raw_path = output / "raw_rgba" / f"{label}.rgba"
            atomic_save(aligned_rgba, aligned_rgba_path)
            atomic_save(runtime_rgb, rgb_path)
            atomic_save(runtime_alpha, alpha_path)
            atomic_save(runtime_rgba, rgba_path)
            save_raw_rgba(runtime_rgba, raw_path)

            record = {
                "frame": frame_index,
                "source_rgb": rgb_source.name,
                "source_rgb_sha256": sha256_file(rgb_source),
                "source_alpha": alpha_source.name,
                "source_alpha_sha256": sha256_file(alpha_source),
                "aligned_size_x1": list(aligned_size),
                "logical_size_x1": [logical_width, logical_height],
                "physical_size_xn": list(runtime_rgba.size),
                "centre_x1": meta["centre"],
                "canvas_offset_x1": [offset_x, offset_y],
                "runtime_crop_box_xn": list(crop_box),
                "padded_x1": padded.relative_to(output).as_posix(),
                "comfy_padded_xn": padded_xn_path.relative_to(output).as_posix(),
                "aligned_rgba_xn": aligned_rgba_path.relative_to(output).as_posix(),
                "rgb_xn": rgb_path.relative_to(output).as_posix(),
                "alpha_xn": alpha_path.relative_to(output).as_posix(),
                "rgba_xn": rgba_path.relative_to(output).as_posix(),
                "raw_rgba_xn": raw_path.relative_to(output).as_posix(),
                "prompt_id": prompt_id,
            }
            for key in ("aligned_rgba_xn", "rgb_xn", "alpha_xn", "rgba_xn", "raw_rgba_xn"):
                record[f"{key}_sha256"] = sha256_file(resolve_output(output, record[key]))
            completed[frame_index] = record
            manifest["frames"] = [completed[index] for index in sorted(completed)]
            manifest["updated_utc"] = utc_now()
            manifest.pop("active_frame", None)
            atomic_write_json(manifest, manifest_path)
            print(
                f"OK {label}: logique {logical_width}x{logical_height} -> "
                f"physique {runtime_rgba.width}x{runtime_rgba.height}",
                flush=True,
            )

        result_frames = [resolve_output(output, completed[index]["rgba_xn"]) for index in sorted(completed)]
        preview_name = f"animation-x{args.scale}-contact-sheet.png"
        preview_path = output / "preview" / preview_name
        make_contact_sheet(result_frames, preview_path)
        manifest["preview"] = preview_path.relative_to(output).as_posix()
        manifest["preview_sha256"] = sha256_file(preview_path)
        manifest["status"] = "completed"
        manifest["completed_utc"] = utc_now()
        manifest["updated_utc"] = utc_now()
        manifest.pop("active_frame", None)
        manifest.pop("last_error", None)
        atomic_write_json(manifest, manifest_path)
        print(f"completed: {len(result_frames)} frame(s) in {output}")
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["updated_utc"] = utc_now()
        manifest["last_error"] = str(exc)
        atomic_write_json(manifest, manifest_path)
        raise


if __name__ == "__main__":
    configure_utf8_console()
    main()
