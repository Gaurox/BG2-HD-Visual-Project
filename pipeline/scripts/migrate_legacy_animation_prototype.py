"""Import one verified legacy x4 animation prototype into a generic runtime pack.

This migration is deliberately narrow: it reads the historical frame-by-frame
SeedVR manifest plus its x1 BAM manifest, verifies every raw RGBA buffer, and
emits the current ``AreaAnimations-X4.registry`` format without rerunning GPU
inference. It never edits the game.
"""

from __future__ import annotations

import argparse
import copy
import shutil
from pathlib import Path
from typing import Any

from build_animation_runtime_pack import (
    PACK_SCHEMA,
    REGISTRY_NAME,
    asset_name,
    atomic_write_json,
    load_json,
    registry_from_resources,
    sha256_file,
    utc_now,
    validate_pack_contents,
)


LEGACY_X4_SCHEMA = "bg2-upscale-sprite-x4"


def relative_inside(root: Path, value: str, label: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"{label} hors prototype : {value}") from exc
    return path


def build_resource(
    prototype_x4_manifest: Path,
    frames_x1_manifest: Path,
    resref: str,
) -> tuple[dict[str, Any], dict[str, Path], dict[str, str]]:
    prototype_root = prototype_x4_manifest.parent.resolve()
    legacy = load_json(prototype_x4_manifest)
    x1 = load_json(frames_x1_manifest)
    if legacy.get("schema") != LEGACY_X4_SCHEMA or legacy.get("status") != "completed":
        raise RuntimeError("prototype x4 historique incomplet ou incompatible")
    if int(legacy.get("scale", 0)) != 4:
        raise RuntimeError("seul un prototype x4 est migrable")
    if int(x1.get("frame_count", 0)) <= 0:
        raise RuntimeError("manifeste x1 historique incomplet")

    frames_x1 = sorted(x1.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    frames_x4 = sorted(legacy.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    frame_count = int(x1["frame_count"])
    if len(frames_x1) != frame_count or len(frames_x4) != frame_count:
        raise RuntimeError("nombre de frames historique incoherent")

    frames: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    sources: dict[str, Path] = {}
    signatures: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for index, (frame_x1, frame_x4) in enumerate(zip(frames_x1, frames_x4)):
        if int(frame_x1.get("frame", -1)) != index or int(frame_x4.get("frame", -1)) != index:
            raise RuntimeError("frames historiques non contigues")
        logical_size = [int(value) for value in frame_x1.get("source_size") or []]
        physical_size = [int(value) for value in frame_x4.get("x4_size") or []]
        centre = [int(value) for value in frame_x1.get("centre") or []]
        if len(logical_size) != 2 or len(physical_size) != 2 or len(centre) != 2:
            raise RuntimeError(f"frame {index}: geometrie historique invalide")
        if physical_size != [logical_size[0] * 4, logical_size[1] * 4]:
            raise RuntimeError(f"frame {index}: taille x4 historique invalide")
        source = relative_inside(prototype_root, str(frame_x4.get("raw_rgba_x4", "")), "asset brut")
        expected_bytes = physical_size[0] * physical_size[1] * 4
        expected_hash = str(frame_x4.get("raw_rgba_x4_sha256", "")).lower()
        if (
            not source.is_file()
            or source.stat().st_size != expected_bytes
            or sha256_file(source) != expected_hash
        ):
            raise RuntimeError(f"frame {index}: asset brut historique corrompu")
        name = asset_name(resref, index)
        frame = {
            "frame": index,
            "logical_size_x1": logical_size,
            "physical_size_x4": physical_size,
            "centre_x1": centre,
            "asset": name,
            "sha256": expected_hash,
            "bytes": expected_bytes,
        }
        frames.append(frame)
        assets.append({"name": name, "sha256": expected_hash, "bytes": expected_bytes})
        sources[name] = source
        signatures.add((tuple(logical_size), tuple(centre)))

    cycles = sorted(x1.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    if [int(cycle.get("cycle", -1)) for cycle in cycles] != list(range(len(cycles))):
        raise RuntimeError("cycles historiques non contigus")
    normalized_cycles: list[dict[str, Any]] = []
    for cycle_index, cycle in enumerate(cycles):
        lookup = [int(value) for value in cycle.get("frame_indices") or []]
        if not lookup or any(value < 0 or value >= frame_count for value in lookup):
            raise RuntimeError(f"cycle {cycle_index}: lookup historique invalide")
        normalized_cycles.append({"cycle": cycle_index, "frame_indices": lookup})

    resource = {
        "resref": resref,
        "frame_count": frame_count,
        "cycle_count": len(normalized_cycles),
        "geometry_mode": "uniform" if len(signatures) == 1 else "per-frame",
        "frames": frames,
        "cycles": normalized_cycles,
        "assets": assets,
    }
    registry_from_resources([resource])
    provenance = {
        "prototype_x4_manifest": prototype_x4_manifest.resolve().as_posix(),
        "prototype_x4_manifest_sha256": sha256_file(prototype_x4_manifest),
        "frames_x1_manifest": frames_x1_manifest.resolve().as_posix(),
        "frames_x1_manifest_sha256": sha256_file(frames_x1_manifest),
        "resref": resref,
    }
    return resource, sources, provenance


def write_pack(
    partial: Path,
    resource: dict[str, Any],
    sources: dict[str, Path],
    provenance: dict[str, str],
) -> dict[str, Any]:
    registry_path = partial / REGISTRY_NAME
    registry_path.write_bytes(registry_from_resources([resource]))
    for asset in resource["assets"]:
        name = str(asset["name"])
        destination = partial / name
        shutil.copyfile(sources[name], destination)
        if destination.stat().st_size != int(asset["bytes"]) or sha256_file(destination) != str(asset["sha256"]):
            raise RuntimeError(f"copie historique corrompue : {destination}")
    manifest = {
        "schema": PACK_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "legacy_prototype": provenance,
        "scale": 4,
        "registry": REGISTRY_NAME,
        "registry_sha256": sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": 1,
        "frame_count": int(resource["frame_count"]),
        "resources": [resource],
    }
    atomic_write_json(manifest, partial / "manifest.json")
    validate_pack_contents(partial)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prototype_x4_manifest", type=Path)
    parser.add_argument("frames_x1_manifest", type=Path)
    parser.add_argument("resref", help="resref BAM de un a huit caracteres")
    parser.add_argument("output", type=Path, nargs="?", help="pack runtime a creer")
    parser.add_argument("--resume", action="store_true", help="valide sans reecrire un pack migre")
    args = parser.parse_args(argv)

    prototype_x4_manifest = args.prototype_x4_manifest.resolve()
    frames_x1_manifest = args.frames_x1_manifest.resolve()
    resref = args.resref.upper()
    if not resref.isascii() or not 1 <= len(resref) <= 8:
        raise RuntimeError(f"resref invalide : {resref}")
    output = args.output.resolve() if args.output else prototype_x4_manifest.parent / "03_runtime_pack"
    resource, sources, provenance = build_resource(prototype_x4_manifest, frames_x1_manifest, resref)
    if output.exists() and any(output.iterdir()):
        if not args.resume:
            raise RuntimeError(f"destination runtime non vide : {output}")
        manifest, resources = validate_pack_contents(output)
        if manifest.get("legacy_prototype") != provenance or resources != [resource]:
            raise RuntimeError(f"pack runtime migre existant incoherent : {output}")
        print(f"already completed and validated migrated runtime pack: 1 BAM, {resource['frame_count']} frames in {output}")
        return
    if output.exists():
        output.rmdir()
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise RuntimeError(f"dossier partiel existant : {partial}")
    partial.mkdir(parents=True)
    manifest = write_pack(partial, copy.deepcopy(resource), sources, provenance)
    partial.replace(output)
    print(f"completed migrated runtime pack: {manifest['resource_count']} BAM, {manifest['frame_count']} frames in {output}")


if __name__ == "__main__":
    main()
