"""Materialize runner source trees as hard links to the native sprite store.

The default is a read-only plan. ``--run`` writes only family-local manifests
and NTFS hard links; it never copies BAM payloads, emits PNG frames, upscales,
builds, installs, launches the game, or changes QA.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import extract_sprite_sources as native_sources
from run_creature_sprite_x2 import (
    JOB_SCHEMA,
    SOURCE_SCHEMA,
    catalog_member_leaf_jobs,
    character_layer_config,
    job_path,
    load_work_item,
    relative_project_path,
    sha256_file,
    utc_now,
    verify_sources,
)


ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ROOT / "sprite/index/sprite_families.csv"
RESOURCES = ROOT / "sprite/index/sprite_resources.csv"
RESOURCE_STORE = ROOT / "sprite/ressources"


@dataclass(frozen=True)
class ResourcePlan:
    row: Mapping[str, str]
    source_payload: Path
    canonical_payload: Path


@dataclass(frozen=True)
class LeafPlan:
    job: Mapping[str, Any]
    destination: Path
    family: Mapping[str, str]
    resources: tuple[ResourcePlan, ...]
    missing_resrefs: tuple[str, ...]
    already_materialized: bool


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def split_values(value: str) -> set[str]:
    return {item.strip() for item in value.split(";") if item.strip()}


def normalized_animation_id(value: object) -> str:
    try:
        return f"0x{int(str(value), 16):04X}"
    except ValueError as error:
        raise RuntimeError(f"animation_id invalide: {value!r}") from error


def leaf_jobs(work_item: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    kind = work_item.get("_kind")
    if kind is None and work_item.get("schema") == JOB_SCHEMA:
        candidates = [work_item]
    elif kind == "armor-set":
        candidates = list(work_item["_members"])
    elif kind == "catalog":
        candidates = [
            leaf
            for member in work_item["_catalog_members"]
            for leaf in catalog_member_leaf_jobs(member)
        ]
    else:
        raise RuntimeError(f"type de job sprite non supporté: {kind!r}")
    result: dict[str, Mapping[str, Any]] = {}
    for candidate in candidates:
        key = str(Path(str(candidate["_job_file"])).resolve()).casefold()
        result[key] = candidate
    return [result[key] for key in sorted(result)]


def family_for_job(
    job: Mapping[str, Any], families: Iterable[Mapping[str, str]]
) -> Mapping[str, str]:
    animation = job["animation"]
    animation_id = normalized_animation_id(animation["id"])
    prefix = str(animation["bam_prefix"]).upper()
    matches = [
        row
        for row in families
        if normalized_animation_id(row.get("animation_id", "")) == animation_id
        and row.get("bam_prefix", "").upper() == prefix
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"le job {job['job_id']} doit correspondre à une famille, trouvé: {len(matches)}"
        )
    family = matches[0]
    if (
        family.get("pipeline_ready", "").lower() != "yes"
        or family.get("blocker", "")
        or family.get("override_collision", "")
    ):
        raise RuntimeError(f"famille non éligible: {family['family_id']}")
    return family


def central_payloads(row: Mapping[str, str]) -> tuple[Path, Path] | None:
    resref = row["bam_resref"].upper()
    source_sha256 = row["source_sha256"].upper()
    destination = RESOURCE_STORE / resref / "sources" / source_sha256.lower()
    if not destination.is_dir():
        return None
    native_sources.verify_existing_source(
        destination,
        {
            "bam_resref": resref,
            "source_sha256": source_sha256,
            "canonical_sha256": row["canonical_sha256"].upper(),
        },
    )
    manifest = json.loads((destination / "source.json").read_text(encoding="utf-8"))
    return (
        native_sources.manifest_payload_path(destination, manifest, "source_file"),
        native_sources.manifest_payload_path(destination, manifest, "canonical_file"),
    )


def make_plan(work_item_path: Path) -> list[LeafPlan]:
    work_item = load_work_item(work_item_path)
    families = read_csv(FAMILIES)
    resources = read_csv(RESOURCES)
    plans: list[LeafPlan] = []
    destinations: set[Path] = set()
    for job in leaf_jobs(work_item):
        family = family_for_job(job, families)
        family_id = family["family_id"]
        selected = sorted(
            (
                row
                for row in resources
                if family_id in split_values(row.get("family_ids", ""))
            ),
            key=lambda row: row["bam_resref"],
        )
        expected_count = int(family["resource_count"])
        if len(selected) != expected_count:
            raise RuntimeError(
                f"inventaire ressource divergent pour {family_id}: "
                f"{len(selected)} / {expected_count}"
            )
        blocked = [row["bam_resref"] for row in selected if row.get("blocker", "")]
        if blocked:
            raise RuntimeError(
                f"ressources bloquées dans une famille éligible {family_id}: "
                + ", ".join(blocked)
            )
        destination = job_path(dict(job), "source_dir")
        if destination in destinations:
            raise RuntimeError(f"source_dir partagé entre plusieurs jobs: {destination}")
        destinations.add(destination)
        existing_manifest = destination / "manifest.json"
        if destination.exists() and not existing_manifest.is_file():
            raise RuntimeError(f"source_dir partiel ou étranger: {destination}")
        resource_plans: list[ResourcePlan] = []
        missing: list[str] = []
        if not existing_manifest.is_file():
            for row in selected:
                payloads = central_payloads(row)
                if payloads is None:
                    missing.append(row["bam_resref"])
                    continue
                source, canonical = payloads
                resource_plans.append(ResourcePlan(row, source, canonical))
        plans.append(
            LeafPlan(
                job=job,
                destination=destination,
                family=family,
                resources=tuple(resource_plans),
                missing_resrefs=tuple(missing),
                already_materialized=existing_manifest.is_file(),
            )
        )
    return plans


def _link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.link(source, destination)
    if not os.path.samefile(source, destination):
        raise RuntimeError(f"le lien physique ne partage pas le payload: {destination}")


def _manifest(plan: LeafPlan) -> dict[str, Any]:
    job = plan.job
    animation = job["animation"]
    bams: list[dict[str, Any]] = []
    for resource in plan.resources:
        row = resource.row
        resref = row["bam_resref"].upper()
        source_name = resource.source_payload.name
        canonical_name = resource.canonical_payload.name
        bams.append(
            {
                "name": resref,
                "source": f"resources/{resref}/{source_name}",
                "canonical_bam": f"resources/{resref}/{canonical_name}",
                "source_bif": row["source_bif"].replace("\\", "/"),
                "locator": row["locator"],
                "source_sha256": row["source_sha256"].upper(),
                "canonical_bam_sha256": row["canonical_sha256"].upper(),
                "native_source_manifest": relative_project_path(
                    resource.source_payload.parent / "source.json"
                ),
                "frame_count": int(row["frame_count"]),
                "cycle_count": int(row["cycle_count"]),
                "transparent_palette_index": int(row["transparent_palette_index"]),
            }
        )
    return {
        "schema": SOURCE_SCHEMA,
        "status": "materialized-from-native-store",
        "created_at_utc": utc_now(),
        "job_id": job["job_id"],
        "creature": animation.get("name", job["job_id"]),
        "animation_id": animation["id"],
        "bam_prefix": animation["bam_prefix"],
        "layer": character_layer_config(dict(job))
        if animation.get("runtime_profile") == "character-bg2ee-2.7.3.0"
        else None,
        "runtime_profile": animation.get("runtime_profile"),
        "game_dir": job["paths"]["game_root"],
        "baldur_real_sha256": job["compatibility"]["baldur_real_sha256"],
        "native_store": relative_project_path(RESOURCE_STORE),
        "family_id": plan.family["family_id"],
        "family_inventory": relative_project_path(FAMILIES),
        "family_inventory_sha256": sha256_file(FAMILIES),
        "resource_inventory": relative_project_path(RESOURCES),
        "resource_inventory_sha256": sha256_file(RESOURCES),
        "bams": bams,
        "total_frames": sum(int(resource.row["frame_count"]) for resource in plan.resources),
    }


def apply_leaf(plan: LeafPlan) -> bool:
    if plan.already_materialized:
        verify_sources(dict(plan.job), compare_game=True)
        return False
    if plan.missing_resrefs:
        raise RuntimeError(
            f"sources centrales absentes pour {plan.job['job_id']}: "
            + ", ".join(plan.missing_resrefs)
        )
    destination = plan.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent)
    )
    try:
        for resource in plan.resources:
            resref = resource.row["bam_resref"].upper()
            target = temporary / "resources" / resref
            _link(resource.source_payload, target / resource.source_payload.name)
            if resource.canonical_payload != resource.source_payload:
                _link(
                    resource.canonical_payload,
                    target / resource.canonical_payload.name,
                )
        (temporary / "manifest.json").write_text(
            json.dumps(_manifest(plan), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    try:
        verify_sources(dict(plan.job), compare_game=True)
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return True


def summarize(
    plans: Iterable[LeafPlan], *, run: bool, written_source_trees: int = 0
) -> dict[str, Any]:
    selected = list(plans)
    missing = sorted(
        {
            resref
            for plan in selected
            for resref in plan.missing_resrefs
        }
    )
    return {
        "status": "materialized" if run else "planned",
        "leaf_job_count": len(selected),
        "resource_membership_count": sum(
            int(plan.family["resource_count"]) for plan in selected
        ),
        "already_materialized": sum(plan.already_materialized for plan in selected),
        "written_source_trees": written_source_trees,
        "missing_central_resource_count": len(missing),
        "missing_central_resrefs": missing,
        "writes": written_source_trees > 0,
        "pixels_produced": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    plans = make_plan(args.job)
    written = 0
    if args.run:
        missing = sorted(
            {resref for plan in plans for resref in plan.missing_resrefs}
        )
        if missing:
            raise RuntimeError(
                "extraire d'abord les sources centrales: " + ", ".join(missing)
            )
        for plan in plans:
            written += apply_leaf(plan)
    print(
        json.dumps(
            summarize(plans, run=args.run, written_source_trees=written),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
