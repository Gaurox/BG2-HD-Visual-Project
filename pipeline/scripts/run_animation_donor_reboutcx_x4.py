#!/usr/bin/env python3
"""Substitution de visuel au niveau x1, puis étage spatial ReboutCX x4.

Une ressource cible garde sa géométrie BAM x1 (canevas, centres, cycles, positions ARE) ; son
visuel x1 est remplacé par celui d'une ressource donneuse déjà exportée en x1. Chaque frame
donneuse est réduite par aire au canevas cible (RGB pondéré par l'alpha, alpha seuillé), puis
l'image x1 obtenue passe dans l'étage ReboutCX x4 habituel
(`run_animation_reboutcx_x4.build` : RGB rempli nearest-opaque-dilate, alpha x1 répété x4).

Le run cible doit avoir été préparé par `run_animation_upscale.py --prepare-only`. L'étage x1
d'origine (BAM cible) est conservé sous `01_frames_x1_bam_original` ; `01_frames_x1` porte alors
les frames substituées, avec leur provenance dans son manifeste. Seule étape GPU : lancer avec le
Python chaiNNer (`config://chainner_python`). Ne touche ni jeu, ni DLL, ni INI, ni catalogue.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from reboutcx_batch import load_model  # noqa: E402
from run_animation_reboutcx_x4 import build as reboutcx_build  # noqa: E402
from workspace_paths import resolve_path_reference  # noqa: E402


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def area_resample(plane: np.ndarray, width: int, height: int) -> np.ndarray:
    image = Image.fromarray(plane.astype(np.float32), mode="F")
    return np.asarray(image.resize((width, height), Image.BOX), dtype=np.float32)


def substitute_x1(run_root: Path, resref: str, donor_run: Path, donor_resref: str,
                  frame_map: list[int], alpha_threshold: float) -> Path:
    resource_root = run_root / "resources" / resref
    frames_x1 = resource_root / "01_frames_x1"
    original = resource_root / "01_frames_x1_bam_original"
    if original.exists():
        raise SystemExit(f"substitution déjà faite (présent : {original})")
    manifest_x1 = json.loads((frames_x1 / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest_x1["frames"]
    if len(frame_map) != len(entries):
        raise SystemExit(f"--frame-map : {len(frame_map)} indices pour {len(entries)} frames cible")

    donor_x1 = donor_run / "resources" / donor_resref / "01_frames_x1"
    donor_manifest_path = donor_x1 / "manifest.json"
    donor_manifest = json.loads(donor_manifest_path.read_text(encoding="utf-8"))
    donor_by_frame = {int(e["frame"]): e for e in donor_manifest["frames"]}
    if any(index not in donor_by_frame for index in frame_map):
        raise SystemExit("--frame-map cite une frame absente du donneur")

    shutil.copytree(frames_x1, original)
    canvas_w, canvas_h = manifest_x1["aligned_canvas_size"]
    frames = []
    for entry, donor_index in zip(entries, frame_map, strict=True):
        donor_entry = donor_by_frame[donor_index]
        rgba = np.asarray(
            Image.open(donor_x1 / "rgba" / donor_entry["file"]).convert("RGBA"), dtype=np.float32
        )
        alpha = (rgba[:, :, 3] > 0).astype(np.float32)
        planes = [area_resample(rgba[:, :, c] * alpha, canvas_w, canvas_h) for c in range(3)]
        coverage = area_resample(alpha, canvas_w, canvas_h)
        opaque = coverage >= alpha_threshold
        rgb = np.zeros((canvas_h, canvas_w, 3), dtype=np.float32)
        for c in range(3):
            rgb[:, :, c] = np.where(coverage > 0, planes[c] / np.maximum(coverage, 1e-6), 0.0)
        out = np.zeros((canvas_h, canvas_w, 4), dtype=np.uint8)
        out[:, :, :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
        out[:, :, 3] = np.where(opaque, 255, 0).astype(np.uint8)
        out[:, :, :3][~opaque] = 0

        name = entry["file"]
        Image.fromarray(out, "RGBA").save(frames_x1 / "rgba" / name)
        Image.fromarray(out[:, :, :3], "RGB").save(frames_x1 / "rgb" / name)
        Image.fromarray(out[:, :, 3], "L").save(frames_x1 / "alpha" / name)
        entry["rgb_sha256"] = sha256_file(frames_x1 / "rgb" / name)
        entry["alpha_sha256"] = sha256_file(frames_x1 / "alpha" / name)
        entry["rgba_sha256"] = sha256_file(frames_x1 / "rgba" / name)
        frames.append({"frame": entry["frame"], "donor_frame": donor_index,
                       "donor_rgba_sha256": donor_entry["rgba_sha256"]})

    manifest_x1["substituted_from"] = {
        "donor_run": str(donor_run),
        "donor_resref": donor_resref,
        "donor_frame_manifest_sha256": sha256_file(donor_manifest_path),
        "donor_frame_map": frame_map,
        "reduction": "aire (BOX, float32), RGB pondéré par l'alpha donneur, alpha seuillé",
        "alpha_threshold": alpha_threshold,
        "original_x1_stage": "01_frames_x1_bam_original",
        "frames": frames,
    }
    manifest_x1["updated_utc"] = datetime.now(timezone.utc).isoformat()
    path = frames_x1 / "manifest.json"
    path.write_text(json.dumps(manifest_x1, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--resref", required=True, help="ressource cible (géométrie conservée)")
    parser.add_argument("--donor-run", type=Path, required=True,
                        help="run du donneur, avec resources/<RESREF>/01_frames_x1")
    parser.add_argument("--donor-resref", required=True)
    parser.add_argument("--frame-map", required=True,
                        help="indices de frames donneuses, un par frame cible (ex. 0,1,3,4,6,7)")
    parser.add_argument("--alpha-threshold", type=float, default=0.5,
                        help="couverture minimale d'un texel cible pour être opaque")
    args = parser.parse_args()

    run_root = args.run_root.resolve()
    resref = args.resref.upper()
    frame_map = [int(value) for value in args.frame_map.split(",")]
    substitute_x1(run_root, resref, args.donor_run.resolve(), args.donor_resref.upper(),
                  frame_map, args.alpha_threshold)

    model_path = resolve_path_reference("config://reboutcx_model", required=True)
    descriptor, _versions = load_model(model_path, device="cuda:0", fp16=True)
    path = reboutcx_build(run_root, resref, descriptor, model_path, False)
    print(json.dumps({"status": "completed", "manifest": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
