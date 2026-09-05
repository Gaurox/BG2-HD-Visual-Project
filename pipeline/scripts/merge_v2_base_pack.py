"""Extend an existing registry-v2 runtime pack with resources from a completed V1 x4 pack.

Gap this fills: `run_animation_upscale_30fps_v2.py plan/build` requires every targeted
resref to already exist as a `Native` entry in `--base-pack`. When a brand-new zone's V1
pack introduces resrefs that have never been part of any V2 pack, there is no documented
way to fold them in — `build_animation_runtime_pack.py --include-pack` only understands
schema v1, and `adopt-clock-patch` is reserved for the historical PORTL1A bootstrap.

This script reuses `run_animation_upscale_30fps_v2`'s own validated loaders and registry
writer (`load_base_pack`, `registry_v2_from_resources`, `validate_v2_pack`) so the merged
registry is produced by the exact same code path as every other V2 pack, not a
reimplementation. Every resource already in `--base-v2-pack` is carried through
byte-for-byte (asset content and hashes copied, never regenerated); every resource in
`--new-v1-pack` is added as a fresh `Native` entry via `normalise_v1_resource`. Resref
collisions are refused. The output is immutable like every other pack in this pipeline.

This does not touch the game, DLL, INI, override, or either input pack.
"""

from __future__ import annotations

import argparse
import copy
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402


def merge(base_v2_pack: Path, new_v1_pack: Path, output: Path, resume: bool) -> dict:
    base_v2_pack = base_v2_pack.resolve()
    new_v1_pack = new_v1_pack.resolve()
    output = output.resolve()

    base_manifest, base_resources, base_sources = v2.load_base_pack(base_v2_pack)
    v2.require(base_manifest.get("schema") == v2.PACK_SCHEMA,
               f"--base-v2-pack doit être un pack registre v2 : {base_v2_pack}")

    new_manifest, new_resources, new_sources = v2.load_base_pack(new_v1_pack)
    v2.require(new_manifest.get("schema") == v2.runtime_v1.PACK_SCHEMA,
               f"--new-v1-pack doit être un pack V1 x4 natif : {new_v1_pack}")

    base_refs = {v2.normalise_resref(str(item["resref"])) for item in base_resources}
    new_refs = {v2.normalise_resref(str(item["resref"])) for item in new_resources}
    collisions = sorted(base_refs & new_refs)
    v2.require(not collisions, f"resref déjà présents dans le pack de base : {collisions}")

    if output.exists():
        v2.require(resume, f"sortie de fusion déjà présente sans --resume : {output}")
        manifest, _resources = v2.validate_v2_pack(output)
        v2.require(manifest.get("merged_from", {}).get("base_v2_pack_manifest_sha256") ==
                   v2.sha256_file(base_v2_pack / "manifest.json") and
                   manifest.get("merged_from", {}).get("new_v1_pack_manifest_sha256") ==
                   v2.sha256_file(new_v1_pack / "manifest.json"),
                   "sortie existante issue d'une autre fusion")
        return manifest

    output_resources = copy.deepcopy(base_resources) + copy.deepcopy(new_resources)
    sources = dict(base_sources)
    sources.update(new_sources)

    ordered = sorted(output_resources, key=v2.resource_sort_key)
    registry = v2.registry_v2_from_resources(ordered)

    output.mkdir(parents=True)
    registry_path = output / v2.REGISTRY_NAME
    registry_path.write_bytes(registry)
    for resource in ordered:
        for asset in resource["assets"]:
            source = sources[str(asset["name"])]
            destination = output / str(asset["name"])
            shutil.copyfile(source, destination)
            v2.require(destination.stat().st_size == int(asset["bytes"]) and
                       v2.sha256_file(destination) == str(asset["sha256"]).lower(),
                       f"copie de fusion corrompue : {destination}")

    manifest = {
        "schema": v2.PACK_SCHEMA,
        "status": "completed",
        "created_utc": v2.utc_now(),
        "scale": 4,
        "registry_version": v2.REGISTRY_VERSION,
        "runtime_contract": {"feature": "TimedTimeline", "clock": "QPC-pause-aware",
                             "registry_version": v2.REGISTRY_VERSION},
        "registry": v2.REGISTRY_NAME,
        "registry_sha256": v2.sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": len(ordered),
        "frame_count": sum(int(item["frame_count"]) for item in ordered),
        "timed_resources": sorted(
            v2.normalise_resref(str(item["resref"]))
            for item in ordered if item.get("playback_mode") == "TimedTimeline"
        ),
        "merged_from": {
            "base_v2_pack": base_v2_pack.as_posix(),
            "base_v2_pack_manifest_sha256": v2.sha256_file(base_v2_pack / "manifest.json"),
            "base_v2_registry_sha256": str(base_manifest["registry_sha256"]).lower(),
            "new_v1_pack": new_v1_pack.as_posix(),
            "new_v1_pack_manifest_sha256": v2.sha256_file(new_v1_pack / "manifest.json"),
            "new_v1_registry_sha256": str(new_manifest["registry_sha256"]).lower(),
            "added_resrefs": sorted(new_refs),
        },
        "resources": ordered,
    }
    v2.write_json(output / "manifest.json", manifest)
    v2.validate_v2_pack(output)
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-v2-pack", type=Path, required=True,
                        help="pack registre v2 immuable à étendre (la pointe actuelle de la chaîne)")
    parser.add_argument("--new-v1-pack", type=Path, required=True,
                        help="pack V1 x4 terminé dont les resrefs sont absents du pack de base")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    manifest = merge(args.base_v2_pack, args.new_v1_pack, args.output, args.resume)
    import json
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
