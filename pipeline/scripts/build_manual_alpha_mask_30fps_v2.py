"""Apply a user-authored alpha mask to one completed 30 fps V2 temporal run.

The source temporal run and its base pack stay immutable.  The output is another
complete V2 run: original base anchors affected by the mask become explicit
``replacement_assets``; interpolated phases remain ``new_assets``.  The V2
installer therefore validates and backs up every overwritten anchor.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops

import animation_paths
import run_animation_upscale_30fps_v2 as temporal


MASK_SCHEMA = "bg2-upscale-area-animation-manual-alpha-mask-v2"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_mask(path: Path, expected_size: tuple[int, int]) -> Image.Image:
    require(path.is_file(), f"masque absent : {path}")
    with Image.open(path) as opened:
        require(opened.size == expected_size,
                f"masque {path}: dimensions {opened.size}, attendu {expected_size}")
        rgb = opened.convert("RGB")
        red, green, blue = rgb.getchannel("R"), rgb.getchannel("G"), rgb.getchannel("B")
        require(ImageChops.difference(red, green).getbbox() is None and
                ImageChops.difference(red, blue).getbbox() is None,
                f"masque {path}: RGB non monochrome")
        return red.copy()


def masked_rgba(path: Path, physical_size: list[int], mask: Image.Image) -> bytes:
    rgba = temporal.rgba_from_raw(path, physical_size)
    rgb_before = rgba.convert("RGB").tobytes()
    alpha = rgba.getchannel("A")
    output = rgba.copy()
    output.putalpha(ImageChops.multiply(alpha, mask))
    require(output.convert("RGB").tobytes() == rgb_before,
            f"RGB modifié par le masque : {path}")
    return output.tobytes()


def render_reviews(pack_root: Path, resource: dict[str, Any], work_root: Path,
                   review_ffmpeg: str) -> list[dict[str, Any]]:
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    physical = tuple(int(value) for value in frames[0]["physical_size_x4"])
    require(all(tuple(int(value) for value in frame["physical_size_x4"]) == physical
                for frame in frames),
            f"{resource['resref']}: preview manuel exige une géométrie uniforme")
    by_index = {int(frame["frame"]): frame for frame in frames}
    cycles = sorted(resource["cycles"], key=lambda item: int(item["cycle"]))
    require(len(cycles) == 1, f"{resource['resref']}: preview manuel multi-cycle non supporté")
    timeline = [int(value) for value in cycles[0]["timeline_frame_indices"]]
    require(timeline, f"{resource['resref']}: timeline V2 absente")

    review_frames = work_root / "review_frames"
    review_frames.mkdir(parents=True)
    background = temporal.checkerboard(physical).convert("RGBA")
    for phase, frame_index in enumerate(timeline):
        frame = by_index[frame_index]
        rgba = temporal.rgba_from_raw(pack_root / str(frame["asset"]), frame["physical_size_x4"])
        Image.alpha_composite(background, rgba).convert("RGB").save(
            review_frames / f"frame_{phase:04d}.png")

    exact = work_root / "review-30fps-exact.mp4"
    loop = work_root / "review-30fps-loop-4s.mp4"
    temporal.run_checked([
        review_ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-i", str(review_frames / "frame_%04d.png"),
        "-frames:v", str(len(timeline)), "-c:v", "libx264", "-preset", "slow",
        "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(exact),
    ])
    temporal.run_checked([
        review_ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(exact), "-t", "4", "-c:v", "libx264",
        "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(loop),
    ])
    return [
        {"resref": resource["resref"], "cycle": 0, "kind": "exact",
         "file": str(exact.relative_to(work_root.parents[2])).replace("\\", "/"),
         "sha256": sha256_file(exact)},
        {"resref": resource["resref"], "cycle": 0, "kind": "loop-4s",
         "file": str(loop.relative_to(work_root.parents[2])).replace("\\", "/"),
         "sha256": sha256_file(loop)},
    ]


def build(temporal_run: Path, resref: str | list[str], mask_path: Path | list[Path], output: Path,
          review_ffmpeg: str) -> dict[str, Any]:
    temporal_run = temporal_run.resolve()
    output = output.resolve()
    require(not output.exists() and not output.with_name(output.name + ".partial").exists(),
            f"sortie déjà présente : {output}")
    requested_resrefs = [resref] if isinstance(resref, str) else resref
    requested_masks = [mask_path] if isinstance(mask_path, Path) else mask_path
    require(len(requested_resrefs) == len(requested_masks) and requested_resrefs,
            "fournir un masque pour chaque resref")
    targets = {
        temporal.normalise_resref(value): Path(mask).resolve()
        for value, mask in zip(requested_resrefs, requested_masks, strict=True)
    }
    require(len(targets) == len(requested_resrefs), "resref masqué en double")
    temporal_manifest = temporal.validate_run(temporal_run)
    source_timed_resources = [temporal.normalise_resref(value)
                              for value in temporal_manifest.get("timed_resources") or []]
    require(set(targets) <= set(source_timed_resources),
            "le run temporel source doit couvrir chaque resref masqué")
    source_pack = temporal_run / "03_runtime_pack"
    source_pack_manifest, source_resources = temporal.validate_v2_pack(source_pack)
    base_pack = Path(str(temporal_manifest["base_pack"])).resolve()
    base_manifest, base_resources, _sources = temporal.load_base_pack(base_pack)
    require(sha256_file(base_pack / "manifest.json") == temporal_manifest["base_pack_manifest_sha256"],
            "pack de base du run temporel modifié")
    source_by_resref = {str(item["resref"]): copy.deepcopy(item) for item in source_resources}
    base_by_resref = {str(item["resref"]): item for item in base_resources}
    target_specs: dict[str, dict[str, Any]] = {}
    for target_resref, target_mask_path in targets.items():
        source_resource = source_by_resref.get(target_resref)
        require(source_resource is not None and source_resource["playback_mode"] == "TimedTimeline",
                f"{target_resref}: ressource temporelle absente")
        base_resource = base_by_resref.get(target_resref)
        require(base_resource is not None and base_resource["playback_mode"] == "Native",
                f"{target_resref}: les anchors de base doivent être Native")
        anchor_count = int(base_resource["frame_count"])
        require(anchor_count < int(source_resource["frame_count"]),
                f"{target_resref}: aucune phase temporelle à masquer")
        require(all(source_resource["frames"][index]["asset"] == base_resource["frames"][index]["asset"] and
                    source_resource["frames"][index]["sha256"] == base_resource["frames"][index]["sha256"]
                    for index in range(anchor_count)),
                f"{target_resref}: anchors du run temporel divergentes du pack de base")
        dimensions = tuple(int(value) for value in base_resource["frames"][0]["physical_size_x4"])
        require(all(tuple(int(value) for value in frame["physical_size_x4"]) == dimensions
                    for frame in source_resource["frames"]),
                f"{target_resref}: masque répété exige une géométrie uniforme")
        target_specs[target_resref] = {
            "mask_path": target_mask_path,
            "mask_sha256": sha256_file(target_mask_path),
            "mask": load_mask(target_mask_path, dimensions),
            "dimensions": dimensions,
            "anchor_count": anchor_count,
            "source_resource": source_resource,
            "base_resource": base_resource,
        }

    partial = output.with_name(output.name + ".partial")
    partial.mkdir(parents=True)
    pack_root = partial / "03_runtime_pack"
    shutil.copytree(source_pack, pack_root, ignore=shutil.ignore_patterns("install-backups"))
    manual_masks = partial / "manual-mask"
    manual_masks.mkdir()
    for target_resref in sorted(target_specs):
        spec = target_specs[target_resref]
        mask_root = manual_masks / target_resref
        mask_root.mkdir()
        sealed_mask = mask_root / "source.png"
        shutil.copyfile(spec["mask_path"], sealed_mask)
        require(
            sha256_file(sealed_mask) == spec["mask_sha256"],
            f"{target_resref}: masque modifié pendant sa copie",
        )
        spec["sealed_mask"] = sealed_mask
        for index in range(int(spec["anchor_count"])):
            shutil.copyfile(sealed_mask, mask_root / f"frame_{index:03d}.png")

    pack_manifest = copy.deepcopy(source_pack_manifest)
    resources = copy.deepcopy(source_resources)
    original_base = {str(item["name"]): copy.deepcopy(item) for item in pack_manifest["base_assets"]}
    original_new_names = {str(item["name"]) for item in pack_manifest["new_assets"]}
    anchor_names = {
        str(frame["asset"])
        for spec in target_specs.values()
        for frame in spec["base_resource"]["frames"]
    }
    require(anchor_names <= original_base.keys(), f"{resref}: anchors absentes de l'inventaire base")

    for resource in resources:
        spec = target_specs.get(str(resource["resref"]))
        if spec is None:
            continue
        for frame in resource["frames"]:
            asset_path = pack_root / str(frame["asset"])
            payload = masked_rgba(asset_path, frame["physical_size_x4"], spec["mask"])
            asset_path.write_bytes(payload)
            frame["bytes"] = len(payload)
            frame["sha256"] = sha256_file(asset_path)
    by_name = {str(frame["asset"]): frame for item in resources for frame in item["frames"]}
    for item in resources:
        item["assets"] = [
            {"name": str(frame["asset"]), "sha256": str(frame["sha256"]), "bytes": int(frame["bytes"])}
            for frame in item["frames"]
        ]

    replacement_assets = []
    for name in sorted(anchor_names):
        frame = by_name[name]
        original = original_base[name]
        replacement_assets.append({
            "name": name,
            "sha256": frame["sha256"],
            "bytes": frame["bytes"],
            "expected_base_sha256": original["sha256"],
            "expected_base_bytes": original["bytes"],
        })
    pack_manifest["resources"] = resources
    pack_manifest["base_assets"] = [
        {"name": name, "sha256": by_name[name]["sha256"], "bytes": by_name[name]["bytes"]}
        for name in sorted(original_base.keys() - anchor_names)
    ]
    pack_manifest["new_assets"] = [
        {"name": name, "sha256": by_name[name]["sha256"], "bytes": by_name[name]["bytes"]}
        for name in sorted(original_new_names)
    ]
    pack_manifest["replacement_assets"] = replacement_assets
    patch_targets = [
        {
            "resref": target_resref,
            "mask_source": Path("manual-mask", target_resref, "source.png").as_posix(),
            "mask_sha256": spec["mask_sha256"],
            "mask_size_x4": list(spec["dimensions"]),
            "anchor_count": int(spec["anchor_count"]),
            "masked_frame_count": int(spec["source_resource"]["frame_count"]),
        }
        for target_resref, spec in sorted(target_specs.items())
    ]
    pack_manifest["manual_alpha_patch"] = {
        "schema": MASK_SCHEMA,
        "mask_storage": "run-relative-v1",
        "targets": patch_targets,
        "mask_assignment": "one mask per resref, replicated to every anchor and interpolation phase",
        "alpha_formula": "alpha_final = alpha_source * grayscale_mask / 255",
        "rgb_policy": "byte-identical",
    }
    pack_manifest["registry_version"] = temporal.REGISTRY_VERSION
    pack_manifest["runtime_contract"]["registry_version"] = temporal.REGISTRY_VERSION
    registry = temporal.registry_v2_from_resources(resources)
    registry_path = pack_root / temporal.REGISTRY_NAME
    registry_path.write_bytes(registry)
    pack_manifest["registry_sha256"] = sha256_file(registry_path)
    pack_manifest["registry_bytes"] = len(registry)
    temporal.write_json(pack_root / "manifest.json", pack_manifest)
    temporal.validate_v2_pack(pack_root)

    reviews = []
    for target_resref in targets:
        resource = next(item for item in resources if item["resref"] == target_resref)
        work_root = partial / "work" / target_resref / "cycle_000"
        reviews.extend(render_reviews(pack_root, resource, work_root, review_ffmpeg))
    mask_record = {
        "schema": MASK_SCHEMA,
        "status": "completed",
        "mask_storage": "run-relative-v1",
        "targets": patch_targets,
        "source_temporal_run": temporal_run.as_posix(),
        "source_temporal_run_manifest_sha256": sha256_file(temporal_run / "manifest.json"),
        "alpha_formula": "alpha_final = alpha_source * grayscale_mask / 255",
        "rgb_policy": "byte-identical",
    }
    temporal.write_json(partial / "manual-mask.json", mask_record)
    manifest = {
        "schema": temporal.RUN_SCHEMA,
        "status": "completed",
        "created_utc": temporal.utc_now(),
        "input_mode": "manual-alpha-mask-on-timed-run",
        "source_run": temporal_run.as_posix(),
        "source_run_manifest_sha256": sha256_file(temporal_run / "manifest.json"),
        "base_pack": base_pack.as_posix(),
        "base_pack_manifest_sha256": sha256_file(base_pack / "manifest.json"),
        "native_fps": temporal.rate_record(temporal.NATIVE_FPS),
        "target_fps": temporal.rate_record(temporal.TARGET_FPS),
        "timed_resources": source_timed_resources,
        "pack": "03_runtime_pack",
        "pack_manifest_sha256": sha256_file(pack_root / "manifest.json"),
        "registry_sha256": pack_manifest["registry_sha256"],
        "reviews": reviews,
        "qa_status": "pending-explicit-user-approval",
        "manual_alpha_patch": mask_record,
    }
    temporal.write_json(partial / "manifest.json", manifest)
    temporal.validate_run(partial)
    partial.replace(output)
    return temporal.validate_run(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--temporal-run", type=Path, required=True)
    parser.add_argument("--resref", action="append", required=True,
                        help="resref cible ; répéter avec un --mask correspondant")
    parser.add_argument("--mask", type=Path, action="append", required=True,
                        help="masque PNG correspondant au --resref de même position")
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument(
        "--run",
        help="identifiant du nouveau run; routage mono-resref ou batch automatique",
    )
    output_group.add_argument(
        "--output",
        type=Path,
        help="chemin explicite, réservé à la reprise legacy",
    )
    parser.add_argument("--review-ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    output = (
        animation_paths.resolve_run_destination(args.run, args.resref)
        if args.run
        else args.output.resolve()
    )
    temporal_run = animation_paths.resolve_existing_run(args.temporal_run, args.resref)
    result = build(temporal_run, args.resref, args.mask, output, args.review_ffmpeg)
    print(__import__("json").dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
