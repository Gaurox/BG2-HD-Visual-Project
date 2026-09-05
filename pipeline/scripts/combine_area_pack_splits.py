"""Combine several split-per-area outputs into one installable index.

Why this exists: `Install-AreaAnimations-PerArea.ps1` replaces the whole `iee-assets\areas`
directory with exactly the areas listed in the split-root it is given — it does not merge
with what is already deployed. Installing a fresh split for one new zone alone would delete
every previously-installed zone's pack. This tool unions several already-produced,
already-validated split-root outputs (each from `split_animation_pack_by_area.py`) into one
combined split-root, so the installer's replace-in-full behaviour covers the whole desired
state, not just the newest batch.

Each input area directory is revalidated with the same `validate_v2_pack` used everywhere
else in this pipeline — not re-derived, just re-checked — and copied byte-for-byte into the
combined output. Area IDs must not collide between inputs; if the same area appears in two
inputs, the caller must resolve which one wins before combining (this tool refuses to guess).

This never touches the game, the DLL, INI, override, or any of the input split-roots.
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


def combine(inputs: list[Path], output: Path, resume: bool,
            replace_areas: set[str] | None = None) -> dict[str, Any]:
    output = output.resolve()
    inputs = [path.resolve() for path in inputs]
    replace_areas = {area.upper() for area in replace_areas or set()}
    v2.require(len(inputs) >= 1, "au moins un split-root d'entrée est requis")

    by_area: dict[str, tuple[Path, dict[str, Any]]] = {}
    for split_root in inputs:
        index = v2.load_json(split_root / "manifest.json")
        v2.require(index.get("schema") == splitter.INDEX_SCHEMA and index.get("status") == "completed",
                   f"index de découpage incompatible : {split_root}")
        for entry in index.get("areas") or []:
            area_id = str(entry["area_id"])
            area_dir = split_root / str(entry["directory"])
            manifest_path = area_dir / "manifest.json"
            v2.require(v2.sha256_file(manifest_path) == str(entry["manifest_sha256"]).lower(),
                       f"{area_id}: manifeste divergent de son index dans {split_root}")
            manifest, _resources = v2.validate_v2_pack(area_dir)
            v2.require(manifest.get("area_id") == area_id, f"{area_id}: area_id incohérent")
            if area_id in by_area:
                previous_root, _ = by_area[area_id]
                v2.require(area_id in replace_areas,
                           f"{area_id}: présent dans deux split-roots "
                           f"({previous_root} et {split_root}) ; résoudre avant de combiner")
            by_area[area_id] = (area_dir, manifest)

    v2.require(by_area, "aucune zone à combiner")

    if output.exists():
        v2.require(resume, f"sortie déjà présente sans --resume : {output}")
        existing = v2.load_json(output / "manifest.json")
        expected_areas = sorted(by_area)
        v2.require(existing.get("schema") == splitter.INDEX_SCHEMA and
                   sorted(item["area_id"] for item in existing.get("areas") or []) == expected_areas,
                   "sortie existante issue d'une autre combinaison")
        return existing

    output.mkdir(parents=True)
    entries = []
    for area_id in sorted(by_area):
        source_dir, manifest = by_area[area_id]
        destination = output / area_id
        shutil.copytree(source_dir, destination)
        raw_bytes = sum(int(asset["bytes"]) for resource in manifest["resources"]
                        for asset in resource["assets"])
        entries.append({
            "area_id": area_id,
            "directory": area_id,
            "resrefs": sorted({v2.normalise_resref(str(r["resref"]))
                               for r in manifest["resources"]}),
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
        "combined_from": [path.as_posix() for path in inputs],
        "replaced_areas": sorted(replace_areas),
        "runtime_budget_bytes": v2.MAX_RAW_BYTES,
        "area_count": len(entries),
        "largest_area_raw_bytes": max(item["raw_bytes"] for item in entries),
        "total_raw_bytes": sum(item["raw_bytes"] for item in entries),
        "areas_over_budget": [item["area_id"] for item in entries if item["over_runtime_budget"]],
        "resrefs_without_area": [],
        "areas": entries,
    }
    v2.write_json(output / "manifest.json", index)
    return index


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, action="append", required=True, dest="inputs",
                        help="split-root déjà produit par split_animation_pack_by_area.py ; répétable")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--replace-area", action="append", default=[],
                        help="zone dont une entrée ultérieure remplace explicitement le pack précédent")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    index = combine(args.inputs, args.output, args.resume, set(args.replace_area))
    summary = {key: value for key, value in index.items() if key != "areas"}
    summary["areas_list"] = [item["area_id"] for item in index["areas"]]
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
