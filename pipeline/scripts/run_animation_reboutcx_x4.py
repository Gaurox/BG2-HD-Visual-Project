#!/usr/bin/env python3
"""Étage spatial ReboutCX x4 pour une animation de zone (test comparatif avec xBR2).

Contrat : RGB du canvas x1 aligné (transparent rempli par `nearest-opaque-dilate`) -> ReboutCX x4 natif,
sans réduction BOX ; alpha = alpha source répété x4 (nearest), donc strictement binaire si la source
l'est. Géométrie, centres, cycles et ordre restent ceux du BAM x1.

Écrit uniquement l'étage `02_upscale_reboutcx_x4` dans un run déjà préparé par
`run_animation_upscale.py --prepare-only`, avec le même schéma de manifeste que
`run_animation_small_subject_xbr2.py`. Seule étape GPU ; à lancer avec le Python chaiNNer
(`config://chainner_python`). Ne touche ni jeu, ni DLL, ni INI, ni override, ni catalogue.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from reboutcx_batch import infer_x4_box_x2, load_model  # noqa: E402
from run_animation_small_subject_xbr2 import sha256_bytes, sha256_file  # noqa: E402
from workspace_paths import resolve_path_reference  # noqa: E402

STAGE = "02_upscale_reboutcx_x4"


def filled_rgb(rgba: np.ndarray) -> np.ndarray:
    opaque = rgba[:, :, 3] > 0
    if not np.any(opaque):
        return np.zeros((*opaque.shape, 3), dtype=np.uint8)
    nearest = distance_transform_edt(~opaque, return_distances=False, return_indices=True)
    return np.asarray(rgba[:, :, :3][tuple(nearest)], dtype=np.uint8)


def build(run_root: Path, resref: str, descriptor, model_path: Path, resume: bool) -> Path:
    resource_root = run_root / "resources" / resref
    frames_x1 = resource_root / "01_frames_x1"
    manifest_x1_path = frames_x1 / "manifest.json"
    if not manifest_x1_path.is_file():
        raise SystemExit(f"étage x1 absent : {manifest_x1_path}")
    manifest_x1 = json.loads(manifest_x1_path.read_text(encoding="utf-8"))

    stage = resource_root / STAGE
    if stage.exists() and not resume:
        raise SystemExit(f"sortie déjà présente sans --resume : {stage}")
    for sub in ("aligned_rgba", "rgb", "alpha", "rgba", "raw_rgba"):
        (stage / sub).mkdir(parents=True, exist_ok=True)

    canvas_w, canvas_h = manifest_x1["aligned_canvas_size"]
    frames_out = []
    for entry in manifest_x1["frames"]:
        index = entry["frame"]
        name = f"frame_{index:03d}.png"
        source = np.asarray(
            Image.open(frames_x1 / "rgba" / entry["file"]).convert("RGBA"), dtype=np.uint8
        )
        sw, sh = entry["source_size"]
        ox, oy = entry["canvas_offset"]
        if source.shape[:2] != (canvas_h, canvas_w):
            raise SystemExit(f"frame {index} : canvas {source.shape[:2]} != {(canvas_h, canvas_w)}")

        rgb_x4, _rgb_x2 = infer_x4_box_x2(descriptor, filled_rgb(source), fp16=True)
        alpha_x4 = source[:, :, 3].repeat(4, axis=0).repeat(4, axis=1)
        aligned = np.dstack((rgb_x4, alpha_x4))
        if aligned.shape[:2] != (canvas_h * 4, canvas_w * 4):
            raise SystemExit(f"frame {index} : dimensions x4 inattendues {aligned.shape}")
        crop = [ox * 4, oy * 4, (ox + sw) * 4, (oy + sh) * 4]
        cropped = aligned[crop[1] : crop[3], crop[0] : crop[2]]

        Image.fromarray(aligned, "RGBA").save(stage / "aligned_rgba" / name)
        Image.fromarray(cropped[:, :, :3], "RGB").save(stage / "rgb" / name)
        Image.fromarray(cropped[:, :, 3], "L").save(stage / "alpha" / name)
        Image.fromarray(cropped, "RGBA").save(stage / "rgba" / name)
        raw_name = f"frame_{index:03d}.rgba"
        raw_bytes = cropped.tobytes()
        (stage / "raw_rgba" / raw_name).write_bytes(raw_bytes)

        frames_out.append(
            {
                "frame": index,
                "source_rgb": entry["file"],
                "source_rgb_sha256": entry["rgb_sha256"],
                "source_alpha": entry["file"],
                "source_alpha_sha256": entry["alpha_sha256"],
                "aligned_size_x1": [canvas_w, canvas_h],
                "logical_size_x1": [sw, sh],
                "physical_size_xn": [sw * 4, sh * 4],
                "centre_x1": entry["centre"],
                "canvas_offset_x1": [ox, oy],
                "runtime_crop_box_xn": crop,
                "aligned_rgba_xn": f"aligned_rgba/{name}",
                "rgb_xn": f"rgb/{name}",
                "alpha_xn": f"alpha/{name}",
                "rgba_xn": f"rgba/{name}",
                "raw_rgba_xn": f"raw_rgba/{raw_name}",
                "aligned_rgba_xn_sha256": sha256_file(stage / "aligned_rgba" / name),
                "rgb_xn_sha256": sha256_file(stage / "rgb" / name),
                "alpha_xn_sha256": sha256_file(stage / "alpha" / name),
                "rgba_xn_sha256": sha256_file(stage / "rgba" / name),
                "raw_rgba_xn_sha256": sha256_bytes(raw_bytes),
            }
        )

    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "schema": "bg2-upscale-animation-frames-v1",
        "status": "completed",
        "created_utc": now,
        "updated_utc": now,
        "job_signature": manifest_x1["source_sha256"],
        "source": {
            "rgb": str(frames_x1 / "rgb"),
            "alpha": str(frames_x1 / "alpha"),
            "frame_manifest": str(manifest_x1_path),
            "frame_manifest_sha256": sha256_file(manifest_x1_path),
        },
        "workflow": {
            "algorithm": "ReboutCX x4 (RGB, fp16), alpha nearest x4",
            "model": str(model_path),
            "model_sha256": sha256_file(model_path),
        },
        "parameters": {"scale": 4, "fp16": True, "transparent_rgb_input": "nearest-opaque-dilate"},
        "scale": 4,
        "padding_x1": 0,
        "aligned_canvas_size_x1": [canvas_w, canvas_h],
        "geometry_mode": manifest_x1.get("geometry_mode", "per-frame"),
        "alpha_policy": "source alpha repeated x4 (nearest); RGB reconstructed by ReboutCX",
        "raw_rgba_layout": "RGBA8, tightly packed, top-to-bottom rows",
        "frames": frames_out,
        "completed_utc": now,
    }
    path = stage / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    run_manifest_path = run_root / "manifest.json"
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    for resource in run_manifest.get("resources", []):
        if resource.get("resref") != resref:
            continue
        resource["status"] = "completed"
        resource["frame_count"] = len(frames_out)
        resource["aligned_canvas_size_x1"] = [canvas_w, canvas_h]
        resource["geometry_mode"] = manifest["geometry_mode"]
        resource["frame_manifest_sha256"] = sha256_file(manifest_x1_path)
        resource["upscale"] = f"resources/{resref}/{STAGE}"
        resource["upscale_manifest_sha256"] = sha256_file(path)
        resource["preview"] = None
        resource["completed_utc"] = now
    if all(r.get("status") == "completed" for r in run_manifest.get("resources", [])):
        run_manifest["status"] = "completed"
        run_manifest["completed_utc"] = now
    run_manifest["updated_utc"] = now
    run_manifest_path.write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--resref", action="append", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    model_path = resolve_path_reference("config://reboutcx_model", required=True)
    descriptor, _versions = load_model(model_path, device="cuda:0", fp16=True)
    for resref in args.resref:
        path = build(args.run_root.resolve(), resref.upper(), descriptor, model_path, args.resume)
        print(json.dumps({"status": "completed", "manifest": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
