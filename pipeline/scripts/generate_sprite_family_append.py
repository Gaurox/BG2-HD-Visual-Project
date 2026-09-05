"""Create immutable x2 sprite-family jobs and cumulative catalog append jobs.

The command has two explicit phases:

* ``member`` turns one canonical ``sprite_families.csv`` row into a leaf x2
  job.  It does not extract a BAM or dispatch xBR.
* ``catalog-append`` turns one *already prepared* leaf job into a new,
  versioned catalog descriptor.  It does not build, install, restore, or
  launch the game.

The inventory row is the identity source of truth.  The active catalog job is
never edited: an append always writes a different file while retaining its
``job_id`` and ``paths.run_dir`` so the existing LIFO restore chain stays
valid.  The generated descriptors use the canonical runner schemas and are
validated before publication.

The leaf member adapter covers MonsterIcewind ``body/base-resref`` families.
Complete Character animations, including equipment, are produced by
``generate_character_complete_x2_jobs.py`` and accepted here directly by the
catalog append phase.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from run_creature_sprite_x2 import (  # noqa: E402
    ARMOR_SET_SCHEMA,
    CATALOG_JOB_SCHEMA,
    JOB_SCHEMA,
    SUPPORTED_RUNTIME_PROFILES,
    character_layer_config,
    direct_upscale_contract,
    load_catalog_job,
    load_armor_set,
    load_job,
    read_json,
    relative_project_path,
    resolve_path,
    upscale_contract,
    verify_all,
    verify_armor_set,
)
from workspace_paths import portable_path_reference  # noqa: E402


DEFAULT_FAMILIES = PROJECT_ROOT / "sprite" / "index" / "sprite_families.csv"
VALIDATION_DIR = PROJECT_ROOT / "sprite" / ".work" / "validation"
CATALOG_ENGINE_BUILD_ROOT = "sprite/.work/cmake/catalog"
FAMILIES_ROOT = PROJECT_ROOT / "sprite" / "families"
CATALOG_JOBS_ROOT = PROJECT_ROOT / "sprite" / "catalogs" / "creature-x2-nearest" / "jobs"
JOB_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")
RESREF_RE = re.compile(r"[A-Z0-9_]{1,8}")
ANIMATION_ID_RE = re.compile(r"0x[0-9A-Fa-f]{4}")
DIRECT_X2_METHOD = direct_upscale_contract(2).method
MEMBER_JOB_FILE_RE = re.compile(r"x2-nearest-v[1-9][0-9]*\.json")
CATALOG_APPEND_FILE_RE = re.compile(
    r"(?:append|qa-refresh)-[a-z0-9][a-z0-9-]*-v[1-9][0-9]*\.json"
)

MONSTER_ICEWIND_GROUPS = {
    "E0": "e0xx-classic-monsters",
    "E2": "e2xx-iwd-mixed-creatures",
    "E3": "e3xx-ghouls-and-ghosts",
    "E4": "e4xx-goblins",
    "E5": "e5xx-lizardfolk",
    "E6": "e6xx-myconids",
    "E7": "e7xx-orogs",
    "E8": "e8xx-orcs",
    "E9": "e9xx-salamanders",
    "EA": "eaxx-shriekers-and-shadows",
    "EB": "ebxx-skeletons",
    "EC": "ecxx-wights",
    "ED": "edxx-yuan-ti",
    "EE": "eexx-zombies",
    "EF": "efxx-water-weird",
}


@dataclass(frozen=True)
class InventoryFamily:
    family_id: str
    animation_id: str
    ids_symbol: str
    runtime_profile: str
    layer_kind: str
    variant_kind: str
    variant_value: str
    bam_prefix: str
    resource_count: int
    frame_count: int
    pipeline_ready: str
    runtime_supported: str
    override_collision: str
    blocker: str


def parse_positive_int(row: dict[str, str], field: str) -> int:
    value = str(row.get(field, "")).strip()
    if not value.isdigit() or int(value) <= 0:
        raise RuntimeError(
            f"inventory family {row.get('family_id', '<unknown>')} has invalid {field}"
        )
    return int(value)


def require_existing_job_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if (
        resolved.suffix.lower() != ".json"
        or PROJECT_ROOT not in resolved.parents
        or "sprite" not in resolved.parts
    ):
        raise RuntimeError(f"{label} must be a JSON job below sprite/: {resolved}")
    return resolved


def family_slug(family: InventoryFamily) -> str:
    label = re.sub(r"[^a-z0-9]+", "-", family.ids_symbol.lower()).strip("-")
    if not label:
        raise RuntimeError(f"inventory family {family.family_id} has no usable ids_symbol")
    return f"{family.animation_id[2:].lower()}-{family.bam_prefix.lower()}-{label}"


def family_workspace(family: InventoryFamily) -> Path:
    if family.runtime_profile == "monster-icewind-bg2ee-2.7.3.0":
        code = family.animation_id[2:4].upper()
        group = MONSTER_ICEWIND_GROUPS.get(code)
        if group is None:
            raise RuntimeError(f"no MonsterIcewind folder group is defined for 0x{code}xx")
        return FAMILIES_ROOT / "monster-icewind" / group / family_slug(family)
    raise RuntimeError(f"no workspace layout adapter for {family.runtime_profile!r}")


def member_job_id(family: InventoryFamily, version: str) -> str:
    profile = "monster-icewind" if family.runtime_profile.startswith("monster-") else "character"
    value = f"{profile}-{family_slug(family)}-x2-{version}"
    if not JOB_ID_RE.fullmatch(value):
        raise RuntimeError(f"generated job_id is invalid or too long: {value}")
    return value


def require_new_member_job_path(path: Path, family: InventoryFamily, label: str) -> Path:
    resolved = resolve_path(path)
    expected_parent = family_workspace(family) / "jobs"
    if resolved.parent != expected_parent or not MEMBER_JOB_FILE_RE.fullmatch(resolved.name):
        raise RuntimeError(
            f"{label} must be {relative_project_path(expected_parent)}/x2-nearest-vN.json"
        )
    if resolved.exists():
        raise RuntimeError(f"{label} already exists; immutable jobs are never overwritten: {resolved}")
    return resolved


def require_new_catalog_job_path(path: Path, label: str) -> Path:
    resolved = resolve_path(path)
    if resolved.parent != CATALOG_JOBS_ROOT or not CATALOG_APPEND_FILE_RE.fullmatch(resolved.name):
        raise RuntimeError(
            f"{label} must be {relative_project_path(CATALOG_JOBS_ROOT)}/append-<family>-vN.json"
        )
    if resolved.exists():
        raise RuntimeError(f"{label} already exists; immutable jobs are never overwritten: {resolved}")
    return resolved


def member_layout(family: InventoryFamily, job_filename: str = "x2-nearest-v1.json") -> dict[str, str]:
    if not MEMBER_JOB_FILE_RE.fullmatch(job_filename):
        raise RuntimeError("member job filename must use x2-nearest-vN.json")
    workspace = family_workspace(family)
    run_name = Path(job_filename).stem
    profile_cache = "mi" if family.runtime_profile.startswith("monster-") else "character"
    return {
        "family_directory": relative_project_path(workspace),
        "member_job": relative_project_path(workspace / "jobs" / job_filename),
        "source_dir": relative_project_path(workspace / "source" / "stock"),
        "run_dir": relative_project_path(workspace / "runs" / run_name),
        "engine_build": relative_project_path(
            PROJECT_ROOT
            / "sprite"
            / ".work"
            / "cmake"
            / profile_cache
            / family.animation_id[2:4].lower()
            / f"{family.animation_id[2:].lower()}-{family.bam_prefix.lower()}-{run_name}"
        ),
    }


def sorted_qa(values: Iterable[str], label: str) -> list[str]:
    result = sorted({str(value).upper() for value in values if str(value).strip()})
    if not result:
        raise RuntimeError(f"{label} requires at least one value")
    if any(not RESREF_RE.fullmatch(value) for value in result):
        raise RuntimeError(f"{label} values must be BAM-safe resrefs")
    return result


def load_inventory_family(families_path: Path, family_id: str) -> InventoryFamily:
    if not family_id:
        raise RuntimeError("--family-id is required")
    with families_path.open(encoding="utf-8-sig", newline="") as stream:
        matches = [
            row
            for row in csv.DictReader(stream)
            if str(row.get("family_id", "")) == family_id
        ]
    if len(matches) != 1:
        raise RuntimeError(
            f"family_id must select exactly one inventory row, found {len(matches)}: {family_id}"
        )
    row = matches[0]
    animation_id = str(row.get("animation_id", ""))
    prefix = str(row.get("bam_prefix", "")).upper()
    profile = str(row.get("runtime_profile", ""))
    if not ANIMATION_ID_RE.fullmatch(animation_id):
        raise RuntimeError(f"inventory family {family_id} has invalid animation_id")
    if not RESREF_RE.fullmatch(prefix):
        raise RuntimeError(f"inventory family {family_id} has invalid bam_prefix")
    if profile not in SUPPORTED_RUNTIME_PROFILES:
        raise RuntimeError(f"inventory family {family_id} has unsupported runtime_profile: {profile!r}")
    family = InventoryFamily(
        family_id=family_id,
        animation_id=f"0x{int(animation_id, 16):04X}",
        ids_symbol=str(row.get("ids_symbol", "")).upper(),
        runtime_profile=profile,
        layer_kind=str(row.get("layer_kind", "")).lower(),
        variant_kind=str(row.get("variant_kind", "")).lower(),
        variant_value=str(row.get("variant_value", "")),
        bam_prefix=prefix,
        resource_count=parse_positive_int(row, "resource_count"),
        frame_count=parse_positive_int(row, "frame_count"),
        pipeline_ready=str(row.get("pipeline_ready", "")).lower(),
        runtime_supported=str(row.get("runtime_supported", "")).lower(),
        override_collision=str(row.get("override_collision", "")),
        blocker=str(row.get("blocker", "")),
    )
    if (
        family.runtime_supported != "yes"
        or family.pipeline_ready != "yes"
        or family.blocker
        or family.override_collision
    ):
        raise RuntimeError(
            f"inventory family {family.family_id} is not eligible: "
            f"runtime_supported={family.runtime_supported}, "
            f"pipeline_ready={family.pipeline_ready}, blocker={family.blocker!r}, "
            f"override_collision={family.override_collision!r}"
        )
    return family


def assert_body_base_resref_adapter(family: InventoryFamily) -> None:
    if family.runtime_profile != "monster-icewind-bg2ee-2.7.3.0":
        raise RuntimeError(
            "family-job supports MonsterIcewind leaves only; use the complete "
            "Character generator for Character animations"
        )
    if family.layer_kind != "body" or family.variant_kind != "base-resref":
        raise RuntimeError(
            "family-job currently supports only inventory layer_kind=body and "
            "variant_kind=base-resref; use the profile-specific generator for other layers"
        )


def validate_member_template(template_path: Path, family: InventoryFamily) -> dict[str, Any]:
    template_path = require_existing_job_path(resolve_path(template_path), "--template-job")
    template = load_job(template_path)
    animation = template["animation"]
    if animation.get("runtime_profile") != family.runtime_profile:
        raise RuntimeError("template runtime profile differs from the selected inventory family")
    contract = upscale_contract(template)
    if contract.scale != 2 or contract.method != DIRECT_X2_METHOD:
        raise RuntimeError("template must use an xBR/x2 NEAREST contract")
    return template


def member_payload(
    *,
    destination: Path,
    template: dict[str, Any],
    family: InventoryFamily,
    name: str | None,
    qa_areas: list[str],
    qa_creatures: list[str],
) -> dict[str, Any]:
    version = destination.stem.removeprefix("x2-nearest-")
    job_id = member_job_id(family, version)
    layout = member_layout(family, destination.name)
    paths = dict(template["paths"])
    paths["game_root"] = portable_path_reference("bg2ee_game_root")
    paths["scalepix"] = portable_path_reference("mmpx_scalepix")
    paths["source_dir"] = layout["source_dir"]
    paths["run_dir"] = layout["run_dir"]
    paths["engine_build"] = layout["engine_build"]
    animation: dict[str, Any] = {
        "name": name or f"{family.ids_symbol.replace('_', ' ').title()} — {family.bam_prefix}",
        "id": family.animation_id,
        "bam_prefix": family.bam_prefix,
        "runtime_profile": family.runtime_profile,
    }
    result: dict[str, Any] = {
        "schema": JOB_SCHEMA,
        "job_id": job_id,
        "animation": animation,
        "paths": paths,
        "compatibility": dict(template["compatibility"]),
        "runtime": dict(template.get("runtime", {})),
        "qa": {
            "areas": qa_areas,
            "creatures": qa_creatures,
            "required_bam_prefixes": [family.bam_prefix],
        },
        "upscale": dict(DIRECT_X2_METHOD),
    }
    if isinstance(template.get("tools"), dict):
        result["tools"] = dict(template["tools"])
    return result


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_text = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_text)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_payload_as_job(destination: Path, payload: dict[str, Any]) -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    handle, temporary_text = tempfile.mkstemp(
        prefix=f".{destination.name}.validation-", suffix=".json", dir=VALIDATION_DIR
    )
    os.close(handle)
    temporary = Path(temporary_text)
    temporary.unlink()
    try:
        atomic_write_json(temporary, payload)
        load_job(temporary)
    finally:
        temporary.unlink(missing_ok=True)


def generate_member(
    *,
    destination: Path,
    template_path: Path,
    families_path: Path,
    family_id: str,
    name: str | None,
    qa_areas: Iterable[str],
    qa_creatures: Iterable[str],
    dry_run: bool,
) -> dict[str, Any]:
    family = load_inventory_family(resolve_path(families_path), family_id)
    assert_body_base_resref_adapter(family)
    destination = require_new_member_job_path(destination, family, "--job")
    template = validate_member_template(template_path, family)
    payload = member_payload(
        destination=destination,
        template=template,
        family=family,
        name=name,
        qa_areas=sorted_qa(qa_areas, "--qa-area"),
        qa_creatures=sorted_qa(qa_creatures, "--qa-creature"),
    )
    validate_payload_as_job(destination, payload)
    if not dry_run:
        atomic_write_json(destination, payload)
        load_job(destination)
    return {
        "status": "family-member-job-planned" if dry_run else "family-member-job-created",
        "job_file": relative_project_path(destination),
        "job_id": payload["job_id"],
        "family_id": family.family_id,
        "animation_id": family.animation_id,
        "bam_prefix": family.bam_prefix,
        "runtime_profile": family.runtime_profile,
        "pixels_produced": False,
        "release_manifest_modified": False,
        "next": (
            "python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job "
            f"{relative_project_path(destination)}"
        ),
    }


def member_qa(member: dict[str, Any]) -> tuple[list[str], list[str]]:
    qa = member.get("qa")
    if not isinstance(qa, dict):
        raise RuntimeError("member job requires qa with areas and creatures")
    return sorted_qa(qa.get("areas", []), "member qa.areas"), sorted_qa(
        qa.get("creatures", []), "member qa.creatures"
    )


def validate_member_against_inventory(member: dict[str, Any], family: InventoryFamily) -> None:
    animation = member["animation"]
    for field, expected in (
        ("id", family.animation_id),
        ("bam_prefix", family.bam_prefix),
        ("runtime_profile", family.runtime_profile),
    ):
        actual = str(animation.get(field, "")).upper() if field != "runtime_profile" else str(animation.get(field, ""))
        expected_value = expected.upper() if field != "runtime_profile" else expected
        if actual != expected_value:
            raise RuntimeError(f"member {field} differs from inventory family {family.family_id}")
    contract = upscale_contract(member)
    if contract.scale != 2 or contract.method != DIRECT_X2_METHOD:
        raise RuntimeError("member must use the explicit xBR/x2 NEAREST contract")


def representative_bam_prefixes(member: dict[str, Any]) -> list[str]:
    leaves = (
        list(member["_members"])
        if member.get("_kind") == "armor-set"
        else [member]
    )
    if member["animation"].get("runtime_profile") != "character-bg2ee-2.7.3.0":
        return [str(leaf["animation"]["bam_prefix"]).upper() for leaf in leaves]
    required = [
        str(leaf["animation"]["bam_prefix"]).upper()
        for leaf in leaves
        if character_layer_config(leaf)["kind"] == "body"
    ]
    for kind in ("helmet", "shield", "weapon"):
        representative = next(
            (
                leaf
                for leaf in leaves
                if character_layer_config(leaf)["kind"] == kind
            ),
            None,
        )
        if representative is not None:
            required.append(str(representative["animation"]["bam_prefix"]).upper())
    if not required:
        raise RuntimeError("Character aggregate has no representative QA prefixes")
    return required


def refresh_catalog_qa_payload(
    raw_catalog: dict[str, Any], loaded_catalog: dict[str, Any], name: str
) -> dict[str, Any]:
    payload = copy.deepcopy(raw_catalog)
    payload["name"] = name
    paths = payload.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError("base catalog requires paths")
    # Every catalog runtime build adds a 64-character generation id.  Do not
    # carry the longer historical .cmake-catalog migration target into newly
    # generated descriptors: Visual Studio 2019 FileTracker rejects it on the
    # canonical Windows workspace before CMake can configure the build.
    paths["engine_build"] = CATALOG_ENGINE_BUILD_ROOT
    paths["game_root"] = portable_path_reference("bg2ee_game_root")
    if "scalepix" in paths:
        paths["scalepix"] = portable_path_reference("mmpx_scalepix")
    qa = payload.get("qa")
    scenarios = qa.get("animations") if isinstance(qa, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        raise RuntimeError("base catalog requires qa.animations")
    members_by_id = {
        f"0x{int(str(member['animation']['id']), 16):04X}": member
        for member in loaded_catalog["_catalog_members"]
    }
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise RuntimeError("base catalog QA animation must be an object")
        try:
            animation_id = f"0x{int(str(scenario.get('animation_id', '')), 16):04X}"
        except ValueError as error:
            raise RuntimeError("base catalog QA animation id is invalid") from error
        member = members_by_id.get(animation_id)
        if member is None:
            raise RuntimeError("base catalog QA scenarios differ from members")
        if "required_bam_prefixes" not in scenario:
            scenario["required_bam_prefixes"] = representative_bam_prefixes(member)
    return payload


def append_payload(
    *,
    base_catalog_path: Path,
    member_path: Path,
    destination: Path,
    name: str,
    families_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], InventoryFamily | None]:
    base_catalog_path = require_existing_job_path(resolve_path(base_catalog_path), "--catalog-job")
    member_path = require_existing_job_path(resolve_path(member_path), "--member-job")
    destination = require_new_catalog_job_path(destination, "--job")
    if destination == base_catalog_path:
        raise RuntimeError("append destination must differ from the active catalog job")
    base = load_catalog_job(base_catalog_path)
    catalog_contract = upscale_contract(base)
    if catalog_contract.scale != 2 or catalog_contract.method != DIRECT_X2_METHOD:
        raise RuntimeError("base catalog must use the explicit xBR/x2 NEAREST contract")
    member_schema = read_json(member_path).get("schema")
    if member_schema == JOB_SCHEMA:
        member = load_job(member_path)
        member_kind = "family"
    elif member_schema == ARMOR_SET_SCHEMA:
        member = load_armor_set(member_path)
        member_kind = "character-complete"
    else:
        raise RuntimeError("append member must be a leaf job or Character aggregate")
    if member_path.resolve() in {
        Path(item["_job_file"]).resolve() for item in base["_catalog_members"]
    }:
        raise RuntimeError("member already belongs to the base catalog")
    animation_id = f"0x{int(str(member['animation']['id']), 16):04X}"
    if animation_id in {
        f"0x{int(str(item['animation']['id']), 16):04X}"
        for item in base["_catalog_members"]
    }:
        raise RuntimeError(
            f"catalog already owns animation {animation_id}; append one full animation identity only once"
        )
    family_id = None
    families_path = resolve_path(families_path)
    family: InventoryFamily | None = None
    if member_kind == "family":
        with families_path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if (
                    f"0x{int(str(row.get('animation_id', '')), 16):04X}"
                    == animation_id
                    and str(row.get("bam_prefix", "")).upper()
                    == str(member["animation"]["bam_prefix"]).upper()
                    and str(row.get("runtime_profile", ""))
                    == str(member["animation"].get("runtime_profile", ""))
                ):
                    family_id = str(row.get("family_id", ""))
                    break
        if not family_id:
            raise RuntimeError("member does not map to a canonical sprite_families.csv row")
        family = load_inventory_family(families_path, family_id)
        validate_member_against_inventory(member, family)
    else:
        inventory = member.get("inventory")
        if not isinstance(inventory, dict):
            raise RuntimeError("Character aggregate requires sealed inventory provenance")
        try:
            inventory_animation_id = (
                f"0x{int(str(inventory.get('animation_id', '')), 16):04X}"
            )
        except ValueError as error:
            raise RuntimeError("Character aggregate inventory animation id is invalid") from error
        if inventory_animation_id != animation_id:
            raise RuntimeError("Character aggregate inventory animation id differs")
        if int(inventory.get("included_family_count", -1)) != len(member["_members"]):
            raise RuntimeError("Character aggregate inventory member count differs")
        if re.fullmatch(
            r"[0-9A-F]{64}",
            str(inventory.get("families_csv_sha256", "")).upper(),
        ) is None:
            raise RuntimeError("Character aggregate inventory hash is invalid")
    areas, creatures = member_qa(member)
    member_qa_block = member.get("qa", {})
    required_prefixes = sorted_qa(
        member_qa_block.get("required_bam_prefixes", []),
        "member qa.required_bam_prefixes",
    )

    raw_base = read_json(base_catalog_path)
    payload = refresh_catalog_qa_payload(raw_base, base, name)
    payload["members"] = list(raw_base["members"]) + [relative_project_path(member_path)]
    qa = payload.get("qa")
    if not isinstance(qa, dict):
        raise RuntimeError("base catalog requires qa.animations")
    animations = qa.get("animations")
    if not isinstance(animations, list) or not animations:
        raise RuntimeError("base catalog requires a non-empty qa.animations list")
    qa["animations"] = list(animations) + [
        {
            "animation_id": animation_id,
            "name": str(member["animation"].get("name", member["job_id"])),
            "areas": areas,
            "creatures": creatures,
            "required_bam_prefixes": required_prefixes,
        }
    ]
    return payload, member, family


def validate_payload_as_catalog(destination: Path, payload: dict[str, Any]) -> None:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    handle, temporary_text = tempfile.mkstemp(
        prefix=f".{destination.name}.validation-", suffix=".json", dir=VALIDATION_DIR
    )
    os.close(handle)
    temporary = Path(temporary_text)
    temporary.unlink()
    try:
        atomic_write_json(temporary, payload)
        load_catalog_job(temporary)
    finally:
        temporary.unlink(missing_ok=True)


def generate_catalog_append(
    *,
    destination: Path,
    base_catalog_path: Path,
    member_path: Path,
    name: str,
    families_path: Path,
    require_prepared: bool,
    dry_run: bool,
) -> dict[str, Any]:
    payload, member, family = append_payload(
        base_catalog_path=base_catalog_path,
        member_path=member_path,
        destination=destination,
        name=name,
        families_path=families_path,
    )
    destination = resolve_path(destination)
    if require_prepared:
        if member.get("_kind") == "armor-set":
            verify_armor_set(member)
        else:
            verify_all(member, compare_game_sources=True)
    validate_payload_as_catalog(destination, payload)
    if not dry_run:
        atomic_write_json(destination, payload)
        load_catalog_job(destination)
    return {
        "status": "catalog-append-job-planned" if dry_run else "catalog-append-job-created",
        "catalog_job": relative_project_path(destination),
        "job_id": payload["job_id"],
        "run_dir": payload["paths"]["run_dir"],
        "added_member": relative_project_path(resolve_path(member["_job_file"])),
        "added_member_kind": (
            "character-complete" if member.get("_kind") == "armor-set" else "family"
        ),
        "added_family_id": family.family_id if family is not None else None,
        "added_animation_id": f"0x{int(str(member['animation']['id']), 16):04X}",
        "require_prepared": require_prepared,
        "pixels_produced": False,
        "release_manifest_modified": False,
        "next": (
            "python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job "
            f"{relative_project_path(destination)}"
        ),
    }


def generate_catalog_qa_refresh(
    *,
    destination: Path,
    base_catalog_path: Path,
    name: str,
    dry_run: bool,
) -> dict[str, Any]:
    base_catalog_path = require_existing_job_path(
        resolve_path(base_catalog_path), "--catalog-job"
    )
    destination = require_new_catalog_job_path(destination, "--job")
    if destination == base_catalog_path:
        raise RuntimeError("QA refresh destination must differ from the active catalog job")
    base = load_catalog_job(base_catalog_path)
    payload = refresh_catalog_qa_payload(read_json(base_catalog_path), base, name)
    before = read_json(base_catalog_path).get("qa", {}).get("animations")
    after = payload.get("qa", {}).get("animations")
    if before == after:
        raise RuntimeError("catalog QA contract is already explicit; refresh is unnecessary")
    validate_payload_as_catalog(destination, payload)
    if not dry_run:
        atomic_write_json(destination, payload)
        load_catalog_job(destination)
    return {
        "status": "catalog-qa-refresh-planned" if dry_run else "catalog-qa-refresh-created",
        "catalog_job": relative_project_path(destination),
        "job_id": payload["job_id"],
        "run_dir": payload["paths"]["run_dir"],
        "animation_count": len(after),
        "pixels_produced": False,
        "release_manifest_modified": False,
        "next": (
            "python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job "
            f"{relative_project_path(destination)}"
        ),
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    layout = commands.add_parser("layout", help="print the canonical V2 paths for one family")
    layout.add_argument("--family-id", required=True)
    layout.add_argument("--families", type=Path, default=DEFAULT_FAMILIES)

    member = commands.add_parser("member", help="create one inventory-backed x2 member job")
    member.add_argument("--job", type=Path, required=True)
    member.add_argument("--template-job", type=Path, required=True)
    member.add_argument("--family-id", required=True)
    member.add_argument("--families", type=Path, default=DEFAULT_FAMILIES)
    member.add_argument("--name")
    member.add_argument("--qa-area", action="append", default=[])
    member.add_argument("--qa-creature", action="append", default=[])
    member.add_argument("--dry-run", action="store_true")

    append = commands.add_parser(
        "catalog-append", help="create one immutable catalog append descriptor"
    )
    append.add_argument("--job", type=Path, required=True)
    append.add_argument("--catalog-job", type=Path, required=True)
    append.add_argument("--member-job", type=Path, required=True)
    append.add_argument("--families", type=Path, default=DEFAULT_FAMILIES)
    append.add_argument("--name", required=True)
    append.add_argument("--require-prepared", action="store_true")
    append.add_argument("--dry-run", action="store_true")
    refresh = commands.add_parser(
        "catalog-qa-refresh",
        help="create an immutable catalog descriptor with explicit representative QA prefixes",
    )
    refresh.add_argument("--job", type=Path, required=True)
    refresh.add_argument("--catalog-job", type=Path, required=True)
    refresh.add_argument("--name", required=True)
    refresh.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    args = make_parser().parse_args(argv)
    if args.command == "layout":
        family = load_inventory_family(resolve_path(args.families), args.family_id)
        assert_body_base_resref_adapter(family)
        result = {
            "status": "family-layout-resolved",
            "family_id": family.family_id,
            "animation_id": family.animation_id,
            "bam_prefix": family.bam_prefix,
            "runtime_profile": family.runtime_profile,
            "folder_slug": family_slug(family),
            **member_layout(family),
        }
    elif args.command == "member":
        result = generate_member(
            destination=args.job,
            template_path=args.template_job,
            families_path=args.families,
            family_id=args.family_id,
            name=args.name,
            qa_areas=args.qa_area,
            qa_creatures=args.qa_creature,
            dry_run=args.dry_run,
        )
    elif args.command == "catalog-append":
        result = generate_catalog_append(
            destination=args.job,
            base_catalog_path=args.catalog_job,
            member_path=args.member_job,
            name=args.name,
            families_path=args.families,
            require_prepared=args.require_prepared,
            dry_run=args.dry_run,
        )
    else:
        result = generate_catalog_qa_refresh(
            destination=args.job,
            base_catalog_path=args.catalog_job,
            name=args.name,
            dry_run=args.dry_run,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: {error}") from error
