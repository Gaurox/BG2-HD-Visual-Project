#!/usr/bin/env python3
"""Étage spatial `Small Subject xBR2 -> Nearest2 x4` pour une animation de zone.

Pourquoi ce script existe : sur un sujet de quelques pixels, SeedVR ne fait pas un
agrandissement, il reconstruit. Mesuré sur `FPIT1S` (23x20) le 2026-09-02 : la sortie x4 ne
contient plus de flamme mais des volutes et des rubans inventés. La recette
`ANIMATION_SMALL_SUBJECT_XBR2_30FPS.md`, validée sur `BUTRFLY` le 2026-09-01, interdit
explicitement toute reconstruction générative pour cette classe d'assets et impose
`xBR 2x` sans blend ni anti-alias, puis `nearest 2x` vers x4.

Le run `butrfly-xbr2x-nearest2-x4` avait été produit sans runner versionné. Ce script rejoue
exactement le même contrat et écrit le même schéma de manifeste, pour que l'étage soit
reproductible et hashé comme les autres.

`--second-pass xbr2x` propose une variante hors recette figée : le deuxième doublement passe
lui aussi par xBR au lieu de la répétition de texels. Elle exige son propre run et sa propre QA.

`--xbr-blend` est une autre variante hors recette figée : active l'antialiasing xBR
(blendColors) sur chaque passe xBR2x, ce qui grade l'alpha de bord (non binaire) et impose
`--mode premultiply` à `build_blended_rgb_neutral_pack.py` au lieu de `zero`. Testé et validé
visuellement sur `BUBBLES2` le 2026-09-05 : contours plus ronds, moins de tons inventés que
SeedVR, sans le lissage indiscriminé d'un flou gaussien.

Il ne touche ni le jeu, ni la DLL, ni l'INI, ni l'override, ni aucun catalogue : il écrit
uniquement son étage `02_upscale_*` dans un run déjà préparé par
`run_animation_upscale.py --prepare-only`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from workspace_paths import resolve_path_reference  # noqa: E402

XBR_ADAPTER = SCRIPT_DIR / "xbr2x_batch.js"

# Deux seconds étages sont disponibles. `nearest` est la recette figée et validée sur BUTRFLY :
# le doublement par répétition de texels n'introduit aucun ton nouveau et garde le pixel art
# strictement intact. `xbr2x` rejoue l'analyse de contour sur le résultat du premier passage,
# ce qui lisse davantage les diagonales mais fait travailler l'algorithme sur sa propre sortie
# plutôt que sur le pixel art d'origine. Hors recette figée : exige son propre run et sa QA.
SECOND_PASS_MODES = {
    "nearest": {
        "stage": "02_upscale_xbr2x_nearest2_x4",
        "algorithm": "XBR/xbr2X then nearest2x",
        "xbr_passes": 1,
        "post_scale_method": "nearest",
        "alpha_policy": (
            "source RGBA transformed by xBR2x then nearest2x; no generative upscale"
        ),
    },
    "xbr2x": {
        "stage": "02_upscale_xbr2x_xbr2x_x4",
        "algorithm": "XBR/xbr2X then XBR/xbr2X",
        "xbr_passes": 2,
        "post_scale_method": "xbr2x",
        "alpha_policy": (
            "source RGBA transformed by xBR2x twice; no generative upscale"
        ),
    },
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_xbr2x(
    frames: list[np.ndarray], scalepix: Path, node: str, xbr_blend: bool = False
) -> list[np.ndarray]:
    """Appelle l'adaptateur binaire approuvé, protocole legacy `XBR2BAT`.

    Le mode legacy est celui qu'a utilisé le run BUTRFLY de référence ; il n'encode pas
    l'échelle dans l'en-tête et sort toujours en x2. `xbr_blend` est une variante hors
    recette figée (voir `--xbr-blend` sur `build`) : la recette BUTRFLY impose blend=false.
    """
    if not scalepix.is_file():
        raise SystemExit(f"scalepix introuvable : {scalepix}")
    if not XBR_ADAPTER.is_file():
        raise SystemExit(f"adaptateur xBR introuvable : {XBR_ADAPTER}")

    payload = bytearray(b"XBR2BAT\0")
    payload.extend(struct.pack("<I", len(frames)))
    for rgba in frames:
        height, width = rgba.shape[:2]
        raw = rgba.tobytes()
        payload.extend(struct.pack("<III", width, height, len(raw)))
        payload.extend(raw)

    result = subprocess.run(
        [node, str(XBR_ADAPTER), str(scalepix), "legacy-xbr2x",
         "true" if xbr_blend else "false"],
        input=bytes(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "échec du lot xBR2x :\n" + result.stderr.decode("utf-8", errors="replace")
        )

    raw = result.stdout
    if len(raw) < 12 or raw[:8] != b"XBR2OUT\0":
        raise SystemExit("sortie de lot xBR2x invalide")
    count = struct.unpack_from("<I", raw, 8)[0]
    if count != len(frames):
        raise SystemExit(f"xBR2x a rendu {count} frames, {len(frames)} attendues")

    outputs: list[np.ndarray] = []
    offset = 12
    for index in range(count):
        width, height, byte_count = struct.unpack_from("<III", raw, offset)
        offset += 12
        if byte_count != width * height * 4 or offset + byte_count > len(raw):
            raise SystemExit(f"frame xBR2x {index} invalide")
        block = np.frombuffer(raw[offset : offset + byte_count], dtype=np.uint8)
        outputs.append(block.reshape(height, width, 4).copy())
        offset += byte_count
    if offset != len(raw):
        raise SystemExit("octets excédentaires en sortie de xBR2x")
    return outputs


def nearest_x2(rgba: np.ndarray) -> np.ndarray:
    """Doublement strict par répétition de texels : aucune interpolation, aucun nouveau ton."""
    return rgba.repeat(2, axis=0).repeat(2, axis=1)


def build(
    run_root: Path, resref: str, node: str, resume: bool, second_pass: str,
    xbr_blend: bool = False,
) -> Path:
    recipe = SECOND_PASS_MODES[second_pass]
    stage_name = recipe["stage"]

    resource_root = run_root / "resources" / resref
    frames_x1 = resource_root / "01_frames_x1"
    manifest_x1_path = frames_x1 / "manifest.json"
    if not manifest_x1_path.is_file():
        raise SystemExit(f"étage x1 absent : {manifest_x1_path}")
    manifest_x1 = json.loads(manifest_x1_path.read_text(encoding="utf-8"))

    stage = resource_root / stage_name
    if stage.exists() and not resume:
        raise SystemExit(f"sortie déjà présente sans --resume : {stage}")

    for sub in ("xbr2x_rgba", "aligned_rgba", "rgb", "alpha", "rgba", "raw_rgba"):
        (stage / sub).mkdir(parents=True, exist_ok=True)

    scalepix = resolve_path_reference("config://mmpx_scalepix", required=True)

    sources = []
    for entry in manifest_x1["frames"]:
        path = frames_x1 / "rgba" / entry["file"]
        image = Image.open(path).convert("RGBA")
        sources.append(np.asarray(image, dtype=np.uint8))

    doubled = run_xbr2x(sources, scalepix, node, xbr_blend)
    if second_pass == "xbr2x":
        quadrupled = run_xbr2x(doubled, scalepix, node, xbr_blend)
    else:
        quadrupled = [nearest_x2(frame) for frame in doubled]

    canvas_w, canvas_h = manifest_x1["aligned_canvas_size"]
    frames_out = []
    for entry, source, xbr, aligned in zip(
        manifest_x1["frames"], sources, doubled, quadrupled
    ):
        index = entry["frame"]
        name = f"frame_{index:03d}.png"

        if xbr.shape[0] != source.shape[0] * 2 or xbr.shape[1] != source.shape[1] * 2:
            raise SystemExit(f"frame {index} : xBR2x n'a pas exactement doublé la frame")
        if aligned.shape[0] != canvas_h * 4 or aligned.shape[1] != canvas_w * 4:
            raise SystemExit(f"frame {index} : dimensions x4 inattendues {aligned.shape}")

        ox, oy = entry["canvas_offset"]
        sw, sh = entry["source_size"]
        crop = [ox * 4, oy * 4, (ox + sw) * 4, (oy + sh) * 4]
        cropped = aligned[crop[1] : crop[3], crop[0] : crop[2]]

        # `aligned_rgba` garde le canvas commun ; rgb/alpha/rgba portent la géométrie
        # logique de la frame, que le pack runtime et la timeline v2 revalident.
        Image.fromarray(xbr, "RGBA").save(stage / "xbr2x_rgba" / name)
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
                "xbr2x_rgba": f"xbr2x_rgba/{name}",
                "xbr2x_rgba_sha256": sha256_file(stage / "xbr2x_rgba" / name),
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
            "algorithm": recipe["algorithm"] + (" (blend=true)" if xbr_blend else ""),
            "scalepix": str(scalepix),
            "xbr_blend": xbr_blend,
        },
        "parameters": {
            "xbr_scale": 2,
            "xbr_passes": recipe["xbr_passes"],
            "xbr_blend": xbr_blend,
            "post_scale": 2,
            "post_scale_method": recipe["post_scale_method"],
        },
        "scale": 4,
        "padding_x1": 0,
        "aligned_canvas_size_x1": [canvas_w, canvas_h],
        "geometry_mode": manifest_x1.get("geometry_mode", "per-frame"),
        "alpha_policy": (
            recipe["alpha_policy"] + "; xbr_blend=true grades edge alpha, no longer binary"
            if xbr_blend else recipe["alpha_policy"]
        ),
        "raw_rgba_layout": "RGBA8, tightly packed, top-to-bottom rows",
        "frames": frames_out,
        "completed_utc": now,
    }
    path = stage / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Clôture du manifeste de run : sans elle la ressource reste `prepared` et le
    # constructeur de pack refuse le run.
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
        resource["upscale"] = f"resources/{resref}/{stage_name}"
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
    parser.add_argument("--resref", required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--second-pass", choices=sorted(SECOND_PASS_MODES),
                        default="nearest",
                        help="second étage x2 : `nearest` (recette figée) ou `xbr2x` (variante)")
    parser.add_argument("--xbr-blend", action="store_true",
                        help="active l'antialiasing xBR (blendColors) sur chaque passe xBR2x ; "
                             "variante hors recette figée (BUTRFLY impose blend=false), grade "
                             "l'alpha de bord (non binaire) et exige --mode premultiply en aval")
    args = parser.parse_args()

    path = build(args.run_root.resolve(), args.resref.upper(), args.node, args.resume,
                 args.second_pass, args.xbr_blend)
    print(json.dumps({"status": "completed", "manifest": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
