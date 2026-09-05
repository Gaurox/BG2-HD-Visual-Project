"""Replace one resource in selected v2 area packs without dropping sibling effects.

The output is a partial split-root. Combine it with the complete active split-root
using combine_area_pack_splits.py --replace-area before PerArea installation.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_index(root: Path) -> dict[str, Any]:
    index = v2.load_json(root / "manifest.json")
    require(index.get("schema") == splitter.INDEX_SCHEMA and index.get("status") == "completed",
            f"split-root incompatible : {root}")
    return index


def area_directory(root: Path, entry: dict[str, Any]) -> Path:
    area = str(entry["area_id"])
    directory = root / str(entry["directory"])
    require(v2.sha256_file(directory / "manifest.json") == str(entry["manifest_sha256"]).lower(),
            f"{area}: manifeste divergent de l'index")
    return directory


def replace_resource(base_root: Path, replacement_root: Path, resref: str,
                     output: Path) -> dict[str, Any]:
    base_root, replacement_root, output = (path.resolve() for path in (base_root, replacement_root, output))
    require(not output.exists(), f"sortie déjà présente : {output}")
    resref = v2.normalise_resref(resref)
    base_index = load_index(base_root)
    replacement_index = load_index(replacement_root)
    base_entries = {str(entry["area_id"]): entry for entry in base_index.get("areas") or []}
    replacement_entries = sorted(replacement_index.get("areas") or [], key=lambda item: str(item["area_id"]))
    require(replacement_entries, "aucune zone de remplacement")

    output.mkdir(parents=True)
    entries = []
    for replacement_entry in replacement_entries:
        area = str(replacement_entry["area_id"])
        require(area in base_entries, f"{area}: absent du split-root de base")
        base_dir = area_directory(base_root, base_entries[area])
        replacement_dir = area_directory(replacement_root, replacement_entry)
        base_manifest, base_resources = v2.validate_v2_pack(base_dir)
        replacement_manifest, replacement_resources = v2.validate_v2_pack(replacement_dir)
        require(int(base_manifest["registry_version"]) == int(replacement_manifest["registry_version"]),
                f"{area}: versions de registre incompatibles")
        base_target = [item for item in base_resources if v2.normalise_resref(str(item["resref"])) == resref]
        replacement_target = [item for item in replacement_resources
                              if v2.normalise_resref(str(item["resref"])) == resref]
        require(len(base_target) == 1 and len(replacement_target) == 1,
                f"{area}: {resref} doit être présent une fois dans chaque pack")
        require(len(replacement_resources) == 1,
                f"{area}: le split de remplacement doit contenir seulement {resref}")
        resources = [copy.deepcopy(item) for item in base_resources
                     if v2.normalise_resref(str(item["resref"])) != resref]
        resources.append(copy.deepcopy(replacement_target[0]))
        resources = sorted(resources, key=v2.resource_sort_key)
        assets: dict[str, Path] = {}
        for resource in resources:
            source_dir = replacement_dir if v2.normalise_resref(str(resource["resref"])) == resref else base_dir
            for asset in resource["assets"]:
                name = str(asset["name"])
                require(name not in assets, f"{area}: collision d'asset {name}")
                assets[name] = source_dir / name

        destination = output / area
        destination.mkdir()
        registry = v2.registry_v2_from_resources(resources, int(base_manifest["registry_version"]))
        registry_path = destination / v2.REGISTRY_NAME
        registry_path.write_bytes(registry)
        for name, source in assets.items():
            target = destination / name
            shutil.copyfile(source, target)
            require(v2.sha256_file(target) == v2.sha256_file(source),
                    f"{area}: copie divergente {name}")
        raw_bytes = sum(int(asset["bytes"]) for resource in resources for asset in resource["assets"])
        manifest = {
            "schema": v2.PACK_SCHEMA,
            "status": "completed",
            "created_utc": v2.utc_now(),
            "scale": 4,
            "registry_version": int(base_manifest["registry_version"]),
            "runtime_contract": copy.deepcopy(base_manifest["runtime_contract"]),
            "registry": v2.REGISTRY_NAME,
            "registry_sha256": v2.sha256_file(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "resource_count": len(resources),
            "frame_count": sum(int(item["frame_count"]) for item in resources),
            "timed_resources": sorted(v2.normalise_resref(str(item["resref"])) for item in resources
                                      if item.get("playback_mode") == "TimedTimeline"),
            "area_id": area,
            "replaced_resource": {
                "resref": resref,
                "base_pack": base_dir.as_posix(),
                "base_manifest_sha256": v2.sha256_file(base_dir / "manifest.json"),
                "replacement_pack": replacement_dir.as_posix(),
                "replacement_manifest_sha256": v2.sha256_file(replacement_dir / "manifest.json"),
            },
            "raw_bytes": raw_bytes,
            "base_assets": [],
            "new_assets": [],
            "resources": resources,
        }
        v2.write_json(destination / "manifest.json", manifest)
        v2.validate_v2_pack(destination)
        entries.append({
            "area_id": area,
            "directory": area,
            "resrefs": sorted(v2.normalise_resref(str(item["resref"])) for item in resources),
            "resource_count": manifest["resource_count"],
            "frame_count": manifest["frame_count"],
            "raw_bytes": raw_bytes,
            "registry_sha256": manifest["registry_sha256"],
            "manifest_sha256": v2.sha256_file(destination / "manifest.json"),
            "over_runtime_budget": raw_bytes > v2.MAX_RAW_BYTES,
        })
    index = {
        "schema": splitter.INDEX_SCHEMA,
        "status": "completed",
        "created_utc": v2.utc_now(),
        "base_split_root": base_root.as_posix(),
        "replacement_split_root": replacement_root.as_posix(),
        "replaced_resref": resref,
        "runtime_budget_bytes": v2.MAX_RAW_BYTES,
        "area_count": len(entries),
        "largest_area_raw_bytes": max(entry["raw_bytes"] for entry in entries),
        "total_raw_bytes": sum(entry["raw_bytes"] for entry in entries),
        "areas_over_budget": [entry["area_id"] for entry in entries if entry["over_runtime_budget"]],
        "resrefs_without_area": [],
        "areas": entries,
    }
    v2.write_json(output / "manifest.json", index)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-split-root", type=Path, required=True)
    parser.add_argument("--replacement-split-root", type=Path, required=True)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = replace_resource(args.base_split_root, args.replacement_split_root,
                              args.resref, args.output)
    print(json.dumps({key: value for key, value in result.items() if key != "areas"},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
