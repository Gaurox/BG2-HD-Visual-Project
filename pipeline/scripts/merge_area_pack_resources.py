"""Merge single-resource area packs, binding variants to exact world positions.

`PATH::X,Y` binds the input resource to the occurrence at the raw ARE coordinates `(X,Y)`.
Several inputs may keep the same resref: registry v3 distinguishes their assets with a stable
variant index and the runtime selects the exact position before considering an unbound fallback.
No ARE rewrite or alternate BAM resref is needed, so explored zones stored in old saves use the
same path as newly entered zones.

Inputs are validated and never modified. The registry and every asset name are regenerated in a
new split-root, then the complete result is validated again.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402


def retarget_variant(resource: dict[str, Any], variant_index: int,
                     sources: dict[str, Path]) -> dict[str, Path]:
    """Assign a stable variant index and rename every asset that encodes it."""
    resref = v2.normalise_resref(str(resource["resref"]))
    resource["variant_index"] = variant_index
    renamed: dict[str, Path] = {}
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    assets = {str(asset["name"]): asset for asset in resource["assets"]}
    for frame in frames:
        old_name = str(frame["asset"])
        new_name = v2.asset_name(resref, int(frame["frame"]), variant_index)
        v2.require(old_name in sources, f"{resref}: asset source absent ({old_name})")
        frame["asset"] = new_name
        assets[old_name]["name"] = new_name
        renamed[new_name] = sources[old_name]
    return renamed


def load_area_pack(spec: str) -> tuple[dict[str, Any], dict[str, Path], str]:
    """Load one area pack; `PATH::X,Y` declares its occurrence position."""
    path_text, separator, position_text = spec.rpartition("::")
    if not separator:
        path_text = spec
    pack = Path(path_text).resolve()
    manifest, resources = v2.validate_v2_pack(pack)
    v2.require(len(resources) == 1,
               f"pack à ressource unique attendu, {len(resources)} trouvées : {pack}")
    resource = copy.deepcopy(resources[0])
    sources = {str(asset["name"]): pack / str(asset["name"]) for asset in resource["assets"]}
    if separator:
        components = position_text.split(",")
        v2.require(len(components) == 2 and all(component.strip() for component in components),
                   f"position attendue sous la forme X,Y : {position_text}")
        try:
            resource["position"] = [int(component.strip()) for component in components]
        except ValueError as exc:
            raise RuntimeError(f"position invalide : {position_text}") from exc
        v2.resource_position(resource)
    return resource, sources, str(manifest.get("area_id", ""))


def merge(specs: list[str], area: str, output: Path, resume: bool) -> dict[str, Any]:
    output = output.resolve()
    resources: list[dict[str, Any]] = []
    loaded: list[tuple[dict[str, Any], dict[str, Path]]] = []
    for spec in specs:
        resource, resource_sources, pack_area = load_area_pack(spec)
        v2.require(not pack_area or pack_area == area,
                   f"pack d'une autre zone ({pack_area}) fourni pour {area}")
        resources.append(resource)
        loaded.append((resource, resource_sources))

    positions: set[tuple[str, tuple[int, int] | None]] = set()
    for resource in resources:
        key = (v2.normalise_resref(str(resource["resref"])), v2.resource_position(resource))
        v2.require(key not in positions,
                   f"variante dupliquée dans la fusion : {key[0]} à {key[1]}")
        positions.add(key)

    # Variant indices are local to a resref and deterministic. The unbound fallback, when one
    # exists, remains variant 0; bound variants then follow raw ARE coordinates.
    by_resref: dict[str, list[tuple[dict[str, Any], dict[str, Path]]]] = {}
    for resource, resource_sources in loaded:
        by_resref.setdefault(v2.normalise_resref(str(resource["resref"])), []).append(
            (resource, resource_sources))
    sources: dict[str, Path] = {}
    for resref in sorted(by_resref):
        variants = sorted(by_resref[resref],
                          key=lambda item: (v2.resource_position(item[0]) is not None,
                                            v2.resource_position(item[0]) or (0, 0)))
        for variant_index, (resource, resource_sources) in enumerate(variants):
            renamed = retarget_variant(resource, variant_index, resource_sources)
            overlap = sources.keys() & renamed.keys()
            v2.require(not overlap, f"noms d'assets en collision : {sorted(overlap)[:3]}")
            sources.update(renamed)

    area_dir = output / area
    if output.exists():
        v2.require(resume, f"sortie déjà présente sans --resume : {output}")
        v2.validate_v2_pack(area_dir)
        return v2.load_json(output / "manifest.json")

    ordered = sorted(resources, key=v2.resource_sort_key)
    registry = v2.registry_v2_from_resources(ordered)
    area_dir.mkdir(parents=True)
    registry_path = area_dir / v2.REGISTRY_NAME
    registry_path.write_bytes(registry)
    for name, source in sources.items():
        shutil.copyfile(source, area_dir / name)

    raw_bytes = sum(int(asset["bytes"]) for item in ordered for asset in item["assets"])
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
        "timed_resources": sorted({v2.normalise_resref(str(item["resref"])) for item in ordered
                                   if item.get("playback_mode") == "TimedTimeline"}),
        "area_id": area,
        "merged_from": list(specs),
        "raw_bytes": raw_bytes,
        "base_assets": [],
        "new_assets": [],
        "resources": ordered,
    }
    v2.write_json(area_dir / "manifest.json", manifest)
    v2.validate_v2_pack(area_dir)

    index = {
        "schema": splitter.INDEX_SCHEMA,
        "status": "completed",
        "created_utc": v2.utc_now(),
        "merged_from": list(specs),
        "runtime_budget_bytes": v2.MAX_RAW_BYTES,
        "area_count": 1,
        "largest_area_raw_bytes": raw_bytes,
        "total_raw_bytes": raw_bytes,
        "areas_over_budget": [area] if raw_bytes > v2.MAX_RAW_BYTES else [],
        "resrefs_without_area": [],
        "areas": [{
            "area_id": area,
            "directory": area,
            "resrefs": sorted({v2.normalise_resref(str(item["resref"])) for item in ordered}),
            "resource_count": manifest["resource_count"],
            "frame_count": manifest["frame_count"],
            "raw_bytes": raw_bytes,
            "registry_sha256": manifest["registry_sha256"],
            "manifest_sha256": v2.sha256_file(area_dir / "manifest.json"),
            "over_runtime_budget": raw_bytes > v2.MAX_RAW_BYTES,
        }],
    }
    v2.write_json(output / "manifest.json", index)
    return index


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", action="append", required=True, dest="packs",
                        help="pack de zone à ressource unique ; `CHEMIN::X,Y` lie l'occurrence")
    parser.add_argument("--area", required=True, help="identifiant de zone, ex. AR0900")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    index = merge(args.packs, args.area.upper(), args.output, args.resume)
    print(json.dumps({key: value for key, value in index.items() if key != "areas"},
                     indent=2, ensure_ascii=False))
    print("resrefs :", index["areas"][0]["resrefs"])


if __name__ == "__main__":
    main()
