#!/usr/bin/env python3
"""Promote an immutable SeedVR x2 animation run to runtime x4 by nearest x2."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(payload: dict, path: Path) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--output-run", type=Path, required=True)
    parser.add_argument("--resref", required=True)
    args = parser.parse_args()

    source_run = args.source_run.resolve()
    output_run = args.output_run.resolve()
    resref = args.resref.upper()
    if output_run.exists():
        raise SystemExit(f"sortie deja existante : {output_run}")

    source_manifest_path = source_run / "manifest.json"
    source_run_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_record = next(
        (item for item in source_run_manifest.get("resources", []) if item.get("resref") == resref),
        None,
    )
    if source_record is None or source_run_manifest.get("status") != "completed":
        raise SystemExit(f"run x2 incomplet pour {resref}")
    source_stage = source_run / source_record["upscale"]
    source_stage_manifest_path = source_stage / "manifest.json"
    source_stage_manifest = json.loads(source_stage_manifest_path.read_text(encoding="utf-8"))
    if source_stage_manifest.get("status") != "completed" or source_stage_manifest.get("scale") != 2:
        raise SystemExit("la source doit etre un upscale x2 termine")

    resource_root = output_run / "resources" / resref
    shutil.copytree(source_run / "resources" / resref / "00_source", resource_root / "00_source")
    shutil.copytree(source_run / "resources" / resref / "01_frames_x1", resource_root / "01_frames_x1")
    stage = resource_root / "02_upscale_seedvr_x2_nearest2_x4"
    for name in ("aligned_rgba", "rgb", "alpha", "rgba", "raw_rgba"):
        (stage / name).mkdir(parents=True, exist_ok=True)

    frames = []
    for entry in sorted(source_stage_manifest["frames"], key=lambda item: int(item["frame"])):
        index = int(entry["frame"])
        name = f"frame_{index:03d}.png"
        aligned_x2 = np.asarray(Image.open(source_stage / entry["aligned_rgba_xn"]).convert("RGBA"))
        aligned_x4 = aligned_x2.repeat(2, axis=0).repeat(2, axis=1)
        ox, oy = (int(value) for value in entry["canvas_offset_x1"])
        width, height = (int(value) for value in entry["logical_size_x1"])
        crop = [ox * 4, oy * 4, (ox + width) * 4, (oy + height) * 4]
        rgba = aligned_x4[crop[1]:crop[3], crop[0]:crop[2]]
        paths = {
            "aligned_rgba_xn": stage / "aligned_rgba" / name,
            "rgb_xn": stage / "rgb" / name,
            "alpha_xn": stage / "alpha" / name,
            "rgba_xn": stage / "rgba" / name,
            "raw_rgba_xn": stage / "raw_rgba" / f"frame_{index:03d}.rgba",
        }
        Image.fromarray(aligned_x4, "RGBA").save(paths["aligned_rgba_xn"])
        Image.fromarray(rgba[:, :, :3], "RGB").save(paths["rgb_xn"])
        Image.fromarray(rgba[:, :, 3], "L").save(paths["alpha_xn"])
        Image.fromarray(rgba, "RGBA").save(paths["rgba_xn"])
        paths["raw_rgba_xn"].write_bytes(rgba.tobytes(order="C"))
        record = dict(entry)
        record["physical_size_xn"] = [width * 4, height * 4]
        record["runtime_crop_box_xn"] = crop
        record["seedvr_x2_aligned_rgba"] = str((source_stage / entry["aligned_rgba_xn"]).resolve())
        record["seedvr_x2_aligned_rgba_sha256"] = sha256(source_stage / entry["aligned_rgba_xn"])
        for key, path in paths.items():
            record[key] = path.relative_to(stage).as_posix()
            record[f"{key}_sha256"] = sha256(path)
        frames.append(record)

    now = datetime.now(timezone.utc).isoformat()
    stage_manifest = dict(source_stage_manifest)
    stage_manifest.update({
        "created_utc": now,
        "updated_utc": now,
        "completed_utc": now,
        "scale": 4,
        "workflow": {
            "algorithm": "SeedVR2 7B/LAB x2 then nearest-neighbour x2",
            "source_seedvr_x2_manifest": str(source_stage_manifest_path),
            "source_seedvr_x2_manifest_sha256": sha256(source_stage_manifest_path),
        },
        "parameters": {
            "seedvr_scale": 2,
            "post_scale": 2,
            "post_scale_method": "nearest",
        },
        "alpha_policy": "SeedVR x2 source alpha nearest-neighbour x2 to runtime x4",
        "frames": frames,
        "preview": None,
    })
    write_json(stage_manifest, stage / "manifest.json")

    run_manifest = dict(source_run_manifest)
    run_manifest.update({
        "created_utc": now,
        "updated_utc": now,
        "completed_utc": now,
        "run": output_run.name,
        "derived_from": {
            "run": str(source_run),
            "manifest_sha256": sha256(source_manifest_path),
            "operation": "nearest-neighbour x2 from immutable SeedVR x2 output",
        },
    })
    run_manifest["request"] = dict(run_manifest["request"])
    run_manifest["request"]["scale"] = 4
    run_manifest["request"]["source_seedvr_scale"] = 2
    record = dict(source_record)
    record.update({
        "upscale": f"resources/{resref}/{stage.name}",
        "upscale_manifest_sha256": sha256(stage / "manifest.json"),
        "preview": None,
        "completed_utc": now,
    })
    run_manifest["resources"] = [record]
    output_run.mkdir(parents=True, exist_ok=True)
    write_json(run_manifest, output_run / "manifest.json")
    print(stage / "manifest.json")


if __name__ == "__main__":
    main()
