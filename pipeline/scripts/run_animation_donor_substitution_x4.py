#!/usr/bin/env python3
"""Étage spatial « substitution de visuel » : une ressource reprend l'image d'une ressource donneuse.

Cas d'usage : une ressource cible garde sa géométrie BAM x1 (canevas, centres, cycles, positions ARE)
mais son visuel est remplacé par celui d'une autre animation déjà traitée. Le donneur est un pack
runtime x4 fini. Chaque frame cible est un rééchantillonnage par aire (BOX, float32) de la frame
donneuse choisie, RGB et alpha séparément, aux dimensions physiques cible (logique x1 * 4).

Le donneur est lu **tel que livré** : si son RGB est déjà prémultiplié par l'alpha (ressource
Blended après build_blended_rgb_neutral_pack.py --mode premultiply), l'étage l'est aussi et
la neutralisation ne doit pas être rejouée (double prémultiplication).

Écrit uniquement l'étage `02_upscale_donor_x4` dans un run déjà préparé par
`run_animation_upscale.py --prepare-only` ; mêmes schéma de manifeste et layout que
`run_animation_reboutcx_x4.py`. CPU seul ; ne touche ni jeu, ni DLL, ni INI, ni catalogue.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_animation_small_subject_xbr2 import sha256_bytes, sha256_file  # noqa: E402

STAGE = "02_upscale_donor_x4"


def area_resample(plane: np.ndarray, width: int, height: int) -> np.ndarray:
    image = Image.fromarray(plane.astype(np.float32), mode="F")
    return np.asarray(image.resize((width, height), Image.BOX), dtype=np.float32)


def load_donor(donor_pack: Path, donor_resref: str) -> tuple[dict, dict, str]:
    manifest_path = donor_pack / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for resource in manifest["resources"]:
        if resource["resref"] == donor_resref:
            return manifest, resource, sha256_file(manifest_path)
    raise SystemExit(f"donneur {donor_resref} absent de {donor_pack}")


def build(run_root: Path, resref: str, donor_pack: Path, donor_resref: str,
          frame_map: list[int], resume: bool) -> Path:
    resource_root = run_root / "resources" / resref
    frames_x1 = resource_root / "01_frames_x1"
    manifest_x1_path = frames_x1 / "manifest.json"
    if not manifest_x1_path.is_file():
        raise SystemExit(f"étage x1 absent : {manifest_x1_path}")
    manifest_x1 = json.loads(manifest_x1_path.read_text(encoding="utf-8"))
    entries = manifest_x1["frames"]
    if len(frame_map) != len(entries):
        raise SystemExit(f"--frame-map : {len(frame_map)} indices pour {len(entries)} frames cible")

    donor_manifest, donor, donor_manifest_sha = load_donor(donor_pack, donor_resref)
    donor_frames = {int(f["frame"]): f for f in donor["frames"]}
    if any(index not in donor_frames for index in frame_map):
        raise SystemExit(f"--frame-map cite une frame absente du donneur {donor_resref}")

    stage = resource_root / STAGE
    if stage.exists() and not resume:
        raise SystemExit(f"sortie déjà présente sans --resume : {stage}")
    for sub in ("aligned_rgba", "rgb", "alpha", "rgba", "raw_rgba"):
        (stage / sub).mkdir(parents=True, exist_ok=True)

    canvas_w, canvas_h = manifest_x1["aligned_canvas_size"]
    frames_out = []
    for entry, donor_index in zip(entries, frame_map, strict=True):
        index = entry["frame"]
        name = f"frame_{index:03d}.png"
        sw, sh = entry["source_size"]
        ox, oy = entry["canvas_offset"]
        donor_frame = donor_frames[donor_index]
        dw, dh = donor_frame["physical_size_x4"]
        raw = np.fromfile(donor_pack / donor_frame["asset"], dtype=np.uint8)
        if raw.size != dw * dh * 4:
            raise SystemExit(f"donneur frame {donor_index} : taille {raw.size} != {dw * dh * 4}")
        rgba = raw.reshape(dh, dw, 4).astype(np.float32)

        tw, th = sw * 4, sh * 4
        planes = [area_resample(rgba[:, :, c], tw, th) for c in range(4)]
        resampled = np.clip(np.rint(np.stack(planes, axis=2)), 0, 255).astype(np.uint8)
        # RGB prémultiplié : jamais au-dessus de l'alpha (l'arrondi peut dépasser de 1).
        resampled[:, :, :3] = np.minimum(resampled[:, :, :3], resampled[:, :, 3:4])

        aligned = np.zeros((canvas_h * 4, canvas_w * 4, 4), dtype=np.uint8)
        aligned[oy * 4 : oy * 4 + th, ox * 4 : ox * 4 + tw] = resampled
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
                "physical_size_xn": [tw, th],
                "centre_x1": entry["centre"],
                "canvas_offset_x1": [ox, oy],
                "runtime_crop_box_xn": crop,
                "donor_frame": donor_index,
                "donor_asset": donor_frame["asset"],
                "donor_asset_sha256": donor_frame["sha256"],
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
            "algorithm": "substitution de visuel : frames du donneur rééchantillonnées par aire "
                         "(BOX, float32, RGB et alpha séparément) à la géométrie cible",
            "donor_pack": str(donor_pack),
            "donor_pack_manifest_sha256": donor_manifest_sha,
            "donor_resref": donor_resref,
            "donor_frame_map": frame_map,
        },
        "parameters": {"scale": 4, "resample": "BOX", "rgb_state": "as-delivered-by-donor"},
        "scale": 4,
        "padding_x1": 0,
        "aligned_canvas_size_x1": [canvas_w, canvas_h],
        "geometry_mode": manifest_x1.get("geometry_mode", "per-frame"),
        "alpha_policy": "alpha du donneur rééchantillonné par aire ; RGB du donneur tel que livré "
                        "(prémultiplié si le donneur l'est) — ne pas rejouer la neutralisation Blended",
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
    parser.add_argument("--resref", required=True, help="ressource cible (géométrie conservée)")
    parser.add_argument("--donor-pack", type=Path, required=True,
                        help="dossier d'un pack runtime fini (feuille de zone ou pack de run)")
    parser.add_argument("--donor-resref", required=True)
    parser.add_argument("--frame-map", required=True,
                        help="indices de frames donneuses, un par frame cible (ex. 0,1,3,4,6,7)")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    frame_map = [int(value) for value in args.frame_map.split(",")]
    path = build(args.run_root.resolve(), args.resref.upper(), args.donor_pack.resolve(),
                 args.donor_resref.upper(), frame_map, args.resume)
    print(json.dumps({"status": "completed", "manifest": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
