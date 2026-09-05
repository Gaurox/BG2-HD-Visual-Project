"""Split a completed runtime pack into one immutable pack per game area.

Why this exists: the runtime loads a single `AreaAnimations-X4.registry` holding every
converted resource for the whole game, and its raw RGBA payload is capped at 512 MiB.
That budget is cumulative across every zone ever converted and never resets, so a single
global pack cannot hold the game (measured: ~2.7 GiB in plain x4, ~8 GiB once interpolated).
Splitting per area turns the cap into a per-zone limit that 234 of 236 zones satisfy alone.

This reads a finished pack and the project's occurrence index, then writes one
self-contained pack per area containing only the resources that area actually poses.
Each output is a normal registry-v3 pack, validated by the same code path as every other
pack in this pipeline (`registry_v2_from_resources` / `validate_v2_pack`) rather than a
reimplementation, so the runtime needs no special case to read one.

Shared resources are duplicated into every area that uses them; that is the deliberate
trade (about x1.47 on disk) that makes each area pack independently loadable and hashable.

This never touches the game, the DLL, INI files, override, the source pack, or catalogues.
"""

from __future__ import annotations

import argparse
import collections
import copy
import csv
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402

INDEX_SCHEMA = "bg2-upscale-area-animation-pack-index-v1"
DEFAULT_OCCURRENCES = Path("animations/index/occurrences.csv")


def load_area_map(occurrences: Path) -> dict[str, set[str]]:
    """area_id -> eligible BAM resrefs from the canonical occurrence index."""
    v2.require(occurrences.is_file(), f"index d'occurrences absent : {occurrences}")
    mapping: dict[str, set[str]] = collections.defaultdict(set)
    with occurrences.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        resref_field = "resource_resref" if "resource_resref" in fields else "bam_resref"
        v2.require("area_id" in fields and resref_field in fields,
                   f"colonnes area_id/resref absentes : {occurrences}")
        for row in reader:
            resource_kind = str(row.get("resource_kind") or "BAM").strip().upper()
            palette_mode = str(row.get("palette_mode") or "embedded").strip().lower()
            palette_resref = str(row.get("palette_resref") or "").strip()
            if resource_kind != "BAM" or palette_mode == "external" or palette_resref:
                continue
            area = str(row["area_id"]).strip().upper()
            resref = str(row[resref_field]).strip().upper()
            if not area or not resref:
                continue
            mapping[area].add(resref)
    v2.require(mapping, f"aucune occurrence exploitable dans {occurrences}")
    return mapping


def write_area_pack(output: Path, source_pack: Path, source_manifest: dict[str, Any],
                    resources: list[dict[str, Any]], sources: dict[str, Path],
                    area: str) -> dict[str, Any]:
    ordered = sorted(resources, key=v2.resource_sort_key)
    registry = v2.registry_v2_from_resources(ordered)
    raw_bytes = sum(int(asset["bytes"]) for item in ordered for asset in item["assets"])

    output.mkdir(parents=True)
    registry_path = output / v2.REGISTRY_NAME
    registry_path.write_bytes(registry)
    for resource in ordered:
        for asset in resource["assets"]:
            destination = output / str(asset["name"])
            shutil.copyfile(sources[str(asset["name"])], destination)
            v2.require(destination.stat().st_size == int(asset["bytes"]) and
                       v2.sha256_file(destination) == str(asset["sha256"]).lower(),
                       f"copie corrompue : {destination}")

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
        "split_from": {
            "pack": source_pack.as_posix(),
            "pack_manifest_sha256": v2.sha256_file(source_pack / "manifest.json"),
            "pack_registry_sha256": str(source_manifest["registry_sha256"]).lower(),
        },
        "raw_bytes": raw_bytes,
        "base_assets": [],
        "new_assets": [],
        "resources": ordered,
    }
    v2.write_json(output / "manifest.json", manifest)
    v2.validate_v2_pack(output)
    return manifest


def split(pack: Path, output: Path, occurrences: Path, resume: bool) -> dict[str, Any]:
    pack = pack.resolve()
    output = output.resolve()
    source_manifest, resources, sources = v2.load_base_pack(pack)
    by_resref: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for item in resources:
        by_resref[v2.normalise_resref(str(item["resref"]))].append(item)
    area_map = load_area_map(occurrences)

    # Only areas that actually pose at least one converted resource get a pack; every
    # other area falls back to the engine's own BAM path, which costs nothing.
    planned: dict[str, list[str]] = {}
    for area, refs in area_map.items():
        present = sorted(refs & by_resref.keys())
        if present:
            planned[area] = present
    v2.require(planned, "aucune zone ne référence une ressource de ce pack")

    index_path = output / "manifest.json"
    if output.exists():
        v2.require(resume, f"sortie déjà présente sans --resume : {output}")
        existing = v2.load_json(index_path)
        v2.require(existing.get("schema") == INDEX_SCHEMA and
                   existing.get("source_pack_manifest_sha256") ==
                   v2.sha256_file(pack / "manifest.json"),
                   "sortie existante issue d'un autre pack source")
        for area in planned:
            v2.validate_v2_pack(output / area)
        return existing

    output.mkdir(parents=True)
    entries = []
    orphans = sorted(by_resref.keys() - set().union(*area_map.values()))
    for area in sorted(planned):
        refs = planned[area]
        manifest = write_area_pack(output / area, pack, source_manifest,
                                   [copy.deepcopy(resource) for ref in refs
                                    for resource in by_resref[ref]],
                                   sources, area)
        entries.append({
            "area_id": area,
            "directory": area,
            "resrefs": refs,
            "resource_count": manifest["resource_count"],
            "frame_count": manifest["frame_count"],
            "raw_bytes": manifest["raw_bytes"],
            "registry_sha256": manifest["registry_sha256"],
            "manifest_sha256": v2.sha256_file(output / area / "manifest.json"),
            "over_runtime_budget": manifest["raw_bytes"] > v2.MAX_RAW_BYTES,
        })

    index = {
        "schema": INDEX_SCHEMA,
        "status": "completed",
        "created_utc": v2.utc_now(),
        "source_pack": pack.as_posix(),
        "source_pack_manifest_sha256": v2.sha256_file(pack / "manifest.json"),
        "source_registry_sha256": str(source_manifest["registry_sha256"]).lower(),
        "occurrences_index": occurrences.resolve().as_posix(),
        "occurrences_sha256": v2.sha256_file(occurrences.resolve()),
        "runtime_budget_bytes": v2.MAX_RAW_BYTES,
        "area_count": len(entries),
        "largest_area_raw_bytes": max(item["raw_bytes"] for item in entries),
        "total_raw_bytes": sum(item["raw_bytes"] for item in entries),
        "areas_over_budget": [item["area_id"] for item in entries if item["over_runtime_budget"]],
        "resrefs_without_area": orphans,
        "areas": entries,
    }
    v2.write_json(index_path, index)
    return index


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pack", type=Path, required=True,
                        help="pack runtime terminé (registre v1 ou v2) à découper")
    parser.add_argument("--output", type=Path, required=True,
                        help="dossier recevant un sous-dossier par zone")
    parser.add_argument("--occurrences", type=Path, default=DEFAULT_OCCURRENCES,
                        help=f"index des occurrences (défaut : {DEFAULT_OCCURRENCES})")
    parser.add_argument("--resume", action="store_true",
                        help="revalider une sortie existante sans réécrire")
    args = parser.parse_args(argv)
    index = split(args.pack, args.output, args.occurrences, args.resume)
    summary = {key: value for key, value in index.items() if key != "areas"}
    summary["areas_sample"] = [item["area_id"] for item in index["areas"][:10]]
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
