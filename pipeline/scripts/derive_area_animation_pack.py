#!/usr/bin/env python3
"""Derive a validated V2 area pack with frame substitution and alpha treatment.

The source leaf is copied intact.  Only explicitly named frames and one optional
Blended resource are rewritten, then the asset hashes and V2 registry are rebuilt.
"""

from __future__ import annotations

import argparse
import copy
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

import run_animation_upscale_30fps_v2 as v2


def parse_frame_map(values: list[str]) -> dict[int, int]:
    result: dict[int, int] = {}
    for value in values:
        left, separator, right = value.partition("=")
        v2.require(separator == "=" and left.isdigit() and right.isdigit(),
                   f"remplacement de frame invalide : {value} (attendu N=M)")
        target, donor = int(left), int(right)
        v2.require(target != donor, f"remplacement identique : {value}")
        result[target] = donor
    v2.require(result, "au moins un remplacement est requis")
    return result


def resource_by_resref(resources: list[dict[str, Any]], resref: str) -> dict[str, Any]:
    matches = [item for item in resources if str(item.get("resref", "")).upper() == resref]
    v2.require(len(matches) == 1, f"{resref}: ressource absente ou ambiguë")
    return matches[0]


def update_asset_record(resource: dict[str, Any], asset_name: str, path: Path) -> None:
    records = [item for item in resource["assets"] if item["name"] == asset_name]
    v2.require(len(records) == 1, f"{resource['resref']}: asset introuvable : {asset_name}")
    records[0]["bytes"] = path.stat().st_size
    records[0]["sha256"] = v2.sha256_file(path)


def replace_frames(pack: Path, resource: dict[str, Any], replacements: dict[int, int]) -> None:
    frame_by_number = {int(item["frame"]): item for item in resource["frames"]}
    v2.require(len(frame_by_number) == len(resource["frames"]),
               f"{resource['resref']}: frames dupliquées")
    for target_number, donor_number in sorted(replacements.items()):
        v2.require(target_number in frame_by_number and donor_number in frame_by_number,
                   f"{resource['resref']}: frame hors séquence : {target_number}={donor_number}")
        target = frame_by_number[target_number]
        donor = frame_by_number[donor_number]
        target_asset = str(target["asset"])
        donor_asset = str(donor["asset"])
        shutil.copyfile(pack / donor_asset, pack / target_asset)
        replacement = copy.deepcopy(donor)
        replacement["frame"] = target_number
        replacement["asset"] = target_asset
        replacement["bytes"] = (pack / target_asset).stat().st_size
        replacement["sha256"] = v2.sha256_file(pack / target_asset)
        index = resource["frames"].index(target)
        resource["frames"][index] = replacement
        frame_by_number[target_number] = replacement
        update_asset_record(resource, target_asset, pack / target_asset)


def blur_and_dim_blended(pack: Path, resource: dict[str, Any], opacity: float, sigma: float) -> None:
    v2.require(0.0 < opacity <= 1.0, "opacité hors intervalle (0, 1]")
    v2.require(0.0 <= sigma <= 4.0, "sigma gaussien hors intervalle [0, 4]")
    for frame in resource["frames"]:
        width, height = map(int, frame["physical_size_x4"])
        path = pack / str(frame["asset"])
        rgba = np.frombuffer(path.read_bytes(), dtype=np.uint8).reshape((height, width, 4)).copy()
        alpha = rgba[:, :, 3].astype(np.float32)
        blurred = gaussian_filter(alpha, sigma=sigma, mode="constant") if sigma else alpha
        final_alpha = np.clip(np.rint(blurred * opacity), 0, 255).astype(np.uint8)

        # The source is premultiplied (Blended).  Recover straight RGB before applying
        # the new alpha; the nearest opaque colour gives a clean, coloured blur fringe.
        straight = np.zeros_like(rgba[:, :, :3], dtype=np.float32)
        opaque = alpha > 0
        straight[opaque] = rgba[:, :, :3][opaque].astype(np.float32) * (255.0 / alpha[opaque, None])
        fringe = (final_alpha > 0) & ~opaque
        if np.any(fringe) and np.any(opaque):
            _, nearest = distance_transform_edt(~opaque, return_indices=True)
            straight[fringe] = straight[nearest[0][fringe], nearest[1][fringe]]
        rgba[:, :, :3] = np.clip(np.rint(straight * (final_alpha[:, :, None] / 255.0)), 0, 255).astype(np.uint8)
        rgba[:, :, 3] = final_alpha
        path.write_bytes(rgba.tobytes())
        frame["bytes"] = path.stat().st_size
        frame["sha256"] = v2.sha256_file(path)
        update_asset_record(resource, str(frame["asset"]), path)


def fade_blended_edges(pack: Path, resource: dict[str, Any], width: float) -> int:
    """Feather only frames whose visible alpha reaches a physical crop edge."""
    v2.require(0.0 <= width <= 32.0, "largeur de fondu hors intervalle [0, 32]")
    if width == 0:
        return 0
    changed = 0
    for frame in resource["frames"]:
        pixel_width, pixel_height = map(int, frame["physical_size_x4"])
        path = pack / str(frame["asset"])
        rgba = np.frombuffer(path.read_bytes(), dtype=np.uint8).reshape(
            (pixel_height, pixel_width, 4)).copy()
        alpha = rgba[:, :, 3]
        touches_edge = (np.any(alpha[0, :]) or np.any(alpha[-1, :]) or
                        np.any(alpha[:, 0]) or np.any(alpha[:, -1]))
        if not touches_edge:
            continue
        x_distance = np.minimum(np.arange(pixel_width), np.arange(pixel_width)[::-1])
        y_distance = np.minimum(np.arange(pixel_height), np.arange(pixel_height)[::-1])
        edge_factor = np.minimum.outer(
            np.clip(y_distance / width, 0.0, 1.0),
            np.clip(x_distance / width, 0.0, 1.0)).astype(np.float32)
        # RGB is already premultiplied, so the same multiplier preserves the
        # Blended contract without introducing a dark halo.
        rgba[:, :, :3] = np.rint(rgba[:, :, :3].astype(np.float32) * edge_factor[:, :, None]).astype(np.uint8)
        rgba[:, :, 3] = np.rint(alpha.astype(np.float32) * edge_factor).astype(np.uint8)
        path.write_bytes(rgba.tobytes())
        frame["sha256"] = v2.sha256_file(path)
        update_asset_record(resource, str(frame["asset"]), path)
        changed += 1
    return changed


def rebuild_manifest(pack: Path, manifest: dict[str, Any]) -> None:
    resources = manifest["resources"]
    registry = v2.registry_v2_from_resources(resources, int(manifest["registry_version"]))
    registry_path = pack / v2.REGISTRY_NAME
    registry_path.write_bytes(registry)
    manifest["registry_bytes"] = len(registry)
    manifest["registry_sha256"] = v2.sha256_file(registry_path)
    manifest["frame_count"] = sum(int(item["frame_count"]) for item in resources)
    manifest["raw_bytes"] = sum(int(asset["bytes"]) for item in resources for asset in item["assets"])
    v2.write_json(pack / "manifest.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="pack leaf source, e.g. .../AR0202")
    parser.add_argument("--output", type=Path, required=True, help="pack leaf destination")
    parser.add_argument("--fire-resref", default="FIRE_3")
    parser.add_argument("--replace-frame", action="append", default=[], metavar="TARGET=DONOR")
    parser.add_argument("--effect-resref", default="AM0202FL")
    parser.add_argument("--opacity", type=float, default=0.70)
    parser.add_argument("--gaussian-sigma-x4", type=float, default=0.60)
    parser.add_argument("--edge-fade-x4", type=float, default=0.0,
                        help="fondu vers alpha 0 sur les bords réellement touchés")
    args = parser.parse_args()

    source, output = args.input.resolve(), args.output.resolve()
    v2.validate_v2_pack(source)
    v2.require(not output.exists(), f"sortie déjà existante : {output}")
    replacements = parse_frame_map(args.replace_frame)
    shutil.copytree(source, output)
    manifest = v2.load_json(output / "manifest.json")
    fire = resource_by_resref(manifest["resources"], v2.normalise_resref(args.fire_resref))
    effect = resource_by_resref(manifest["resources"], v2.normalise_resref(args.effect_resref))
    replace_frames(output, fire, replacements)
    if args.opacity != 1.0 or args.gaussian_sigma_x4 != 0.0:
        blur_and_dim_blended(output, effect, args.opacity, args.gaussian_sigma_x4)
    faded_frames = fade_blended_edges(output, effect, args.edge_fade_x4)
    manifest["derived_from"] = str(source)
    manifest["derivation"] = {
        "fire_frame_replacements": {str(key): value for key, value in sorted(replacements.items())},
        "effect": {"resref": effect["resref"], "opacity": args.opacity,
                   "gaussian_sigma_x4": args.gaussian_sigma_x4,
                   "edge_fade_x4": args.edge_fade_x4,
                   "edge_faded_frame_count": faded_frames, "rgb": "premultiplied"},
    }
    rebuild_manifest(output, manifest)
    v2.validate_v2_pack(output)
    print(f"Pack dérivé validé : {output}")
    print("FIRE replacements : " + ", ".join(f"{k}={v}" for k, v in sorted(replacements.items())))
    print(f"{effect['resref']} : opacity={args.opacity:.2f}, gaussian sigma={args.gaussian_sigma_x4:.2f} x4, "
          f"edge fade={args.edge_fade_x4:.2f} x4 ({faded_frames} frames)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
