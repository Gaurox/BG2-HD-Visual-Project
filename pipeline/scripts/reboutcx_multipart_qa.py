"""Build and verify composite QA GIFs from an offline ReboutCX prototype run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw

from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
RUN_SCHEMA = "bg2-upscale-reboutcx-multipart-qa-run-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def checkerboard(width: int, height: int, cell: int = 8) -> Image.Image:
    image = Image.new("RGBA", (width, height), (88, 88, 88, 255))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if ((x // cell) + (y // cell)) & 1:
                draw.rectangle(
                    (x, y, min(x + cell - 1, width - 1), min(y + cell - 1, height - 1)),
                    fill=(120, 120, 120, 255),
                )
    return image


def frame_lookup(manifest: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    result: dict[tuple[str, int], dict[str, Any]] = {}
    for frame in manifest["frames"]:
        key = (str(frame["resref"]).upper(), int(frame["source_frame"]))
        if key in result:
            raise RuntimeError(f"duplicate prototype frame: {key[0]} {key[1]}")
        result[key] = frame
    return result


def validate_compositions(
    job: dict[str, Any], lookup: dict[tuple[str, int], dict[str, Any]]
) -> list[dict[str, Any]]:
    compositions = job.get("multipart_qa", {}).get("compositions", [])
    if not compositions:
        raise RuntimeError("multipart QA has no compositions")
    names: set[str] = set()
    validated: list[dict[str, Any]] = []
    for composition in compositions:
        name = str(composition["name"])
        if name in names:
            raise RuntimeError(f"duplicate multipart composition: {name}")
        names.add(name)
        steps = composition.get("steps", [])
        if not steps:
            raise RuntimeError(f"multipart composition has no steps: {name}")
        expected_parts = int(composition["part_count"])
        if expected_parts < 2:
            raise RuntimeError(f"invalid multipart part count: {name}")
        normalized_steps = []
        for step_index, step in enumerate(steps):
            parts = step.get("parts", [])
            keys = [
                (str(part["resref"]).upper(), int(part["frame"])) for part in parts
            ]
            if len(keys) != expected_parts or len(keys) != len(set(keys)):
                raise RuntimeError(f"invalid multipart step {name} {step_index}")
            missing = [key for key in keys if key not in lookup]
            if missing:
                key = missing[0]
                raise RuntimeError(f"unknown multipart frame: {key[0]} {key[1]}")
            normalized_steps.append(
                {"label": str(step.get("label", step_index)), "keys": keys}
            )
        validated.append(
            {
                "name": name,
                "duration_ms": int(composition["duration_ms"]),
                "part_count": expected_parts,
                "steps": normalized_steps,
            }
        )
    return validated


def render_composition(
    composition: dict[str, Any],
    lookup: dict[tuple[str, int], dict[str, Any]],
    destination: Path,
) -> dict[str, Any]:
    scale = 2
    records = [lookup[key] for step in composition["steps"] for key in step["keys"]]
    left = min(-int(record["center_x"]) * scale for record in records)
    top = min(-int(record["center_y"]) * scale for record in records)
    right = max(
        -int(record["center_x"]) * scale + int(record["width"]) * scale
        for record in records
    )
    bottom = max(
        -int(record["center_y"]) * scale + int(record["height"]) * scale
        for record in records
    )
    panel_width, panel_height = right - left, bottom - top
    margin, label_height = 12, 28
    variants = (
        ("NATIF x2", "native_x2"),
        ("xBR2X", "xbr_x2"),
        ("ReboutCX brut", "reboutcx_raw_x2"),
        ("ReboutCX indexe", "reboutcx_quantized_x2"),
    )
    animation: list[Image.Image] = []
    for step in composition["steps"]:
        canvas = Image.new(
            "RGBA",
            ((panel_width + margin) * len(variants) + margin, panel_height + label_height + margin),
            (24, 26, 30, 255),
        )
        draw = ImageDraw.Draw(canvas)
        for column, (label, variant) in enumerate(variants):
            origin_x = margin + column * (panel_width + margin)
            draw.text((origin_x + 3, 7), label, fill="white")
            panel = checkerboard(panel_width, panel_height)
            for key in step["keys"]:
                record = lookup[key]
                evidence = record["files"][variant]
                image_path = resolve_path_reference(
                    evidence["path"], required=True, root=PROJECT_ROOT
                )
                if sha256_file(image_path) != str(evidence["sha256"]):
                    raise RuntimeError(f"prototype frame hash differs: {image_path}")
                with Image.open(image_path) as opened:
                    part = opened.convert("RGBA")
                expected_size = (
                    int(record["width"]) * scale,
                    int(record["height"]) * scale,
                )
                if part.size != expected_size:
                    raise RuntimeError(f"prototype frame geometry differs: {key[0]} {key[1]}")
                x = -int(record["center_x"]) * scale - left
                y = -int(record["center_y"]) * scale - top
                panel.alpha_composite(part, (x, y))
            canvas.alpha_composite(panel, (origin_x, label_height))
        draw.text((margin, panel_height + label_height), str(step["label"]), fill="white")
        animation.append(canvas.convert("RGB"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    animation[0].save(
        destination,
        save_all=True,
        append_images=animation[1:],
        duration=int(composition["duration_ms"]),
        loop=0,
        disposal=2,
        optimize=False,
    )
    return {
        "name": composition["name"],
        "path": relative(destination),
        "sha256": sha256_file(destination),
        "steps": len(animation),
        "part_count": composition["part_count"],
        "duration_ms": composition["duration_ms"],
        "panel_size": [panel_width, panel_height],
    }


def execute(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if job.get("schema") != "bg2-upscale-reboutcx-prototype-job-v1":
        raise RuntimeError("invalid ReboutCX prototype job")
    if job.get("installable") is not False or int(job["reboutcx"]["target_scale"]) != 2:
        raise RuntimeError("multipart QA requires a non-installable x2 prototype")
    source_run = resolve_path_reference(job["paths"]["run_dir"], required=True, root=PROJECT_ROOT)
    source_manifest_path = source_run / "manifest.json"
    source_manifest = read_json(source_manifest_path)
    if (
        source_manifest.get("schema") != "bg2-upscale-reboutcx-prototype-run-v1"
        or source_manifest.get("status") != "completed-pending-human-review"
        or source_manifest.get("job_sha256") != sha256_file(job_path)
    ):
        raise RuntimeError("invalid or stale ReboutCX prototype run")
    output = resolve_path_reference(job["paths"]["multipart_qa_run_dir"], root=PROJECT_ROOT)
    if output.exists():
        raise RuntimeError(f"multipart QA run already exists: {output}")
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise RuntimeError(f"multipart QA temporary path already exists: {temporary}")
    temporary.mkdir(parents=True)
    lookup = frame_lookup(source_manifest)
    compositions = validate_compositions(job, lookup)
    qa = [
        render_composition(item, lookup, temporary / "qa" / f"{item['name']}.gif")
        for item in compositions
    ]
    temporary_prefix = relative(temporary)
    output_prefix = relative(output)
    manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed-pending-human-review",
        "installable": False,
        "target_scale": 2,
        "animation_id": job["animation_id"],
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "source_run_manifest": relative(source_manifest_path),
        "source_run_manifest_sha256": sha256_file(source_manifest_path),
        "code": {"path": relative(Path(__file__)), "sha256": sha256_file(Path(__file__))},
        "qa": qa,
    }
    manifest = json.loads(json.dumps(manifest).replace(temporary_prefix, output_prefix))
    (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.rename(output)
    result = {
        "status": manifest["status"],
        "run": relative(output),
        "manifest_sha256": sha256_file(output / "manifest.json"),
        "qa": len(qa),
    }
    print(json.dumps(result, indent=2))
    return result


def verify(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    output = resolve_path_reference(job["paths"]["multipart_qa_run_dir"], required=True, root=PROJECT_ROOT)
    manifest_path = output / "manifest.json"
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != RUN_SCHEMA
        or manifest.get("status") != "completed-pending-human-review"
        or manifest.get("installable") is not False
        or int(manifest.get("target_scale", 0)) != 2
        or manifest.get("job_sha256") != sha256_file(job_path)
    ):
        raise RuntimeError("invalid multipart QA manifest")
    source_manifest = resolve_path_reference(
        manifest["source_run_manifest"], required=True, root=PROJECT_ROOT
    )
    if sha256_file(source_manifest) != manifest["source_run_manifest_sha256"]:
        raise RuntimeError("source prototype manifest hash differs")
    code = resolve_path_reference(manifest["code"]["path"], required=True, root=PROJECT_ROOT)
    if sha256_file(code) != manifest["code"]["sha256"]:
        raise RuntimeError("multipart QA code hash differs")
    for evidence in manifest["qa"]:
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != evidence["sha256"]:
            raise RuntimeError(f"multipart QA hash differs: {path}")
        with Image.open(path) as image:
            if int(getattr(image, "n_frames", 1)) != int(evidence["steps"]):
                raise RuntimeError(f"multipart QA frame count differs: {path}")
    result = {
        "status": "verified",
        "run": relative(output),
        "manifest_sha256": sha256_file(manifest_path),
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
