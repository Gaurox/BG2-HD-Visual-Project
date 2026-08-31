"""Generate deterministic Character x2 member jobs and one complete aggregate.

This command consumes the canonical ``sprite_families.csv`` inventory and
writes one descriptor in each current-layout Character sprite workspace plus
one aggregate below ``family-runs``.  It never extracts a BAM, dispatches xBR,
builds the runtime, installs files, or launches the game.

One member job is sufficient for every equipment BAM prefix because every ITM
sharing the same animation code resolves to the same stock BAM family.  An
existing compatible x2 job is reused by BAM prefix; otherwise the
lexicographically first stock ITM is used as the representative job identity.
Families with no BAM payload are recorded in the aggregate provenance and are
not turned into empty jobs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
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
    JOB_SCHEMA,
    character_layer_config,
    direct_upscale_contract,
    character_workspace_paths,
    load_armor_set,
    load_job,
    maximum_registry_bytes,
    upscale_contract,
)
from workspace_paths import portable_path_reference  # noqa: E402

DEFAULT_FAMILIES = PROJECT_ROOT / "sprite" / "index" / "sprite_families.csv"
CHARACTER_ROOT = PROJECT_ROOT / "sprite" / "families" / "playable-characters"
VALIDATION_ROOT = PROJECT_ROOT / "sprite" / ".work" / "validation"

DIRECT_X2_METHOD = direct_upscale_contract(2).method
MONOLITH_X2_LIMIT = maximum_registry_bytes(2)
LAYER_ORDER = {"body": 0, "helmet": 1, "shield": 2, "weapon": 3}
JOB_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{1,63}")
RESREF_RE = re.compile(r"[A-Z0-9_]{1,8}")


@dataclass(frozen=True)
class Family:
    animation_id: str
    ids_symbol: str
    runtime_profile: str
    layer_kind: str
    bam_prefix: str
    variant_value: str
    item_resrefs: tuple[str, ...]
    resource_count: int
    frame_count: int
    registry_estimated_bytes: int
    blocker: str

    @property
    def representative_item(self) -> str | None:
        return self.item_resrefs[0] if self.item_resrefs else None

    @property
    def sort_key(self) -> tuple[int, str]:
        return (LAYER_ORDER[self.layer_kind], self.bam_prefix)

    @property
    def needs_member_registry_set(self) -> bool:
        return self.registry_estimated_bytes > MONOLITH_X2_LIMIT


@dataclass(frozen=True)
class PlannedWrite:
    path: Path
    payload: dict[str, Any]


@dataclass(frozen=True)
class GenerationPlan:
    project_root: Path
    character_root: Path
    writes: tuple[PlannedWrite, ...]
    aggregate_path: Path
    aggregate_payload: dict[str, Any]
    reused_jobs: tuple[Path, ...]
    generated_jobs: tuple[Path, ...]
    excluded_families: tuple[dict[str, Any], ...]
    member_set_families: tuple[str, ...]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return value


def normalized_animation_id(value: str) -> str:
    if not re.fullmatch(r"0x[0-9A-Fa-f]{4}", value):
        raise RuntimeError("--animation-id must use 0xFFFF notation")
    return f"0x{int(value, 16):04X}"


def split_values(value: str) -> tuple[str, ...]:
    return tuple(sorted(set(filter(None, (item.strip().upper() for item in value.split(";"))))))


def parse_int(row: dict[str, str], field: str) -> int:
    value = str(row.get(field, "")).strip()
    if not value.isdigit():
        raise RuntimeError(
            f"inventory family {row.get('family_id', '<unknown>')} has invalid {field}"
        )
    return int(value)


def load_families(path: Path, animation_id: str) -> tuple[list[Family], list[dict[str, Any]]]:
    target_id = normalized_animation_id(animation_id)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("animation_id", "").upper() == target_id.upper()]
    if not rows:
        raise RuntimeError(f"no inventory family found for {target_id}")

    families: list[Family] = []
    excluded: list[dict[str, Any]] = []
    seen_prefixes: set[str] = set()
    for row in rows:
        layer = str(row.get("layer_kind", "")).lower()
        if layer not in LAYER_ORDER:
            raise RuntimeError(f"unsupported Character layer in inventory: {layer!r}")
        prefix = str(row.get("bam_prefix", "")).upper()
        if not RESREF_RE.fullmatch(prefix):
            raise RuntimeError(f"invalid inventory BAM prefix: {prefix!r}")
        if prefix in seen_prefixes:
            raise RuntimeError(f"duplicate inventory BAM prefix for {target_id}: {prefix}")
        seen_prefixes.add(prefix)
        resources = parse_int(row, "resource_count")
        frames = parse_int(row, "frame_count")
        estimated_bytes = parse_int(row, "registry_estimated_bytes")
        blocker = str(row.get("blocker", ""))
        if resources == 0:
            if frames != 0:
                raise RuntimeError(f"empty family {prefix} has a non-zero frame count")
            excluded.append(
                {
                    "bam_prefix": prefix,
                    "layer_kind": layer,
                    "item_resrefs": list(split_values(str(row.get("item_resrefs", "")))),
                    "reason": "no-bam-resources",
                    "inventory_blocker": blocker,
                }
            )
            continue
        runtime_profile = str(row.get("runtime_profile", ""))
        runtime_supported = str(row.get("runtime_supported", "")).lower()
        pipeline_ready = str(row.get("pipeline_ready", "")).lower()
        override_collision = str(row.get("override_collision", ""))
        if (
            runtime_profile != "character-bg2ee-2.7.3.0"
            or runtime_supported != "yes"
            or pipeline_ready != "yes"
            or override_collision
        ):
            raise RuntimeError(
                f"inventory family {prefix} is not eligible: "
                f"runtime_profile={runtime_profile!r}, "
                f"runtime_supported={runtime_supported!r}, "
                f"pipeline_ready={pipeline_ready!r}, "
                f"override_collision={override_collision!r}"
            )
        if blocker:
            raise RuntimeError(
                f"inventory family {prefix} is not pipeline-ready: {blocker}"
            )
        if frames <= 0 or estimated_bytes <= 0:
            raise RuntimeError(f"non-empty family {prefix} has invalid inventory totals")

        item_resrefs = split_values(str(row.get("item_resrefs", "")))
        if layer == "body":
            item_resrefs = ()
            variant = str(row.get("variant_value", ""))
            if not variant.isdigit() or int(variant) <= 0:
                raise RuntimeError(f"body family {prefix} has no valid armor code")
        else:
            variant = str(row.get("variant_value", ""))
            if not item_resrefs or any(not RESREF_RE.fullmatch(item) for item in item_resrefs):
                raise RuntimeError(f"equipment family {prefix} has no valid representative ITM")

        families.append(
            Family(
                animation_id=target_id,
                ids_symbol=str(row.get("ids_symbol", "")).upper(),
                runtime_profile=runtime_profile,
                layer_kind=layer,
                bam_prefix=prefix,
                variant_value=variant,
                item_resrefs=item_resrefs,
                resource_count=resources,
                frame_count=frames,
                registry_estimated_bytes=estimated_bytes,
                blocker=blocker,
            )
        )

    families.sort(key=lambda family: family.sort_key)
    excluded.sort(key=lambda record: (LAYER_ORDER[record["layer_kind"]], record["bam_prefix"]))
    return families, excluded


def is_compatible_x2_job(job: dict[str, Any], animation_id: str) -> bool:
    if job.get("schema") != JOB_SCHEMA:
        return False
    animation = job.get("animation")
    if not isinstance(animation, dict) or str(animation.get("id", "")).upper() != animation_id.upper():
        return False
    try:
        contract = upscale_contract(job)
    except (KeyError, RuntimeError, TypeError, ValueError):
        return False
    return contract.scale == 2 and (
        not contract.explicit or contract.method == DIRECT_X2_METHOD
    )


def job_layer(job: dict[str, Any]) -> str:
    return character_layer_config(job)["kind"]


def discover_existing_jobs(
    character_root: Path, animation_id: str
) -> dict[str, tuple[Path, dict[str, Any]]]:
    discovered: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted(character_root.rglob("*.json"), key=lambda item: item.as_posix().lower()):
        if path.parent.name != "jobs":
            continue
        try:
            job = read_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError):
            continue
        if not is_compatible_x2_job(job, animation_id):
            continue
        prefix = str(job.get("animation", {}).get("bam_prefix", "")).upper()
        if not RESREF_RE.fullmatch(prefix):
            continue
        if prefix in discovered:
            raise RuntimeError(
                f"multiple compatible x2 jobs use BAM prefix {prefix}: "
                f"{discovered[prefix][0]} and {path}"
            )
        discovered[prefix] = (path.resolve(), job)
    return discovered


def ensure_template(template: dict[str, Any], animation_id: str) -> None:
    if not is_compatible_x2_job(template, animation_id):
        raise RuntimeError("template must be a compatible Character x2 member job")
    animation = template.get("animation", {})
    if animation.get("runtime_profile") != "character-bg2ee-2.7.3.0":
        raise RuntimeError("template must use the Character BG2EE runtime profile")
    for block in ("paths", "compatibility"):
        if not isinstance(template.get(block), dict):
            raise RuntimeError(f"template requires a {block} object")
    required_paths = ("game_root", "scalepix", "engine_source", "engine_build")
    missing = [name for name in required_paths if not template["paths"].get(name)]
    if missing:
        raise RuntimeError(f"template paths missing: {', '.join(missing)}")


def relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as error:
        raise RuntimeError(f"generated job path is outside the project: {path}") from error


def require_current_character_root(path: Path, animation_id: str) -> Path:
    resolved = path.resolve()
    expected_prefix = normalized_animation_id(animation_id)[2:].lower() + "-"
    if resolved.parent != CHARACTER_ROOT or not resolved.name.startswith(expected_prefix):
        raise RuntimeError(
            "--character-root must be "
            "sprite/families/playable-characters/<animation-id>-<character-type>"
        )
    return resolved


def generated_job_id(job_stem: str, family: Family) -> str:
    if family.layer_kind == "body":
        value = f"{job_stem}-{family.bam_prefix.lower()}-xbr2x"
    else:
        assert family.representative_item is not None
        value = (
            f"{job_stem}-{family.representative_item.lower()}-"
            f"{family.bam_prefix.lower()}-xbr2x"
        )
    if not JOB_ID_RE.fullmatch(value):
        raise RuntimeError(f"generated job id is invalid or too long: {value}")
    return value


def member_workspace(character_root: Path, family: Family) -> Path:
    if family.layer_kind == "body":
        slug = f"body-{family.bam_prefix.lower()}"
    else:
        assert family.representative_item is not None
        slug = f"{family.representative_item.lower()}-{family.bam_prefix.lower()}"
    return character_root / slug


def member_job_path(character_root: Path, family: Family, job_id: str) -> Path:
    return member_workspace(character_root, family) / "jobs" / f"{job_id}.json"


def inherited_qa(template: dict[str, Any]) -> tuple[list[str], list[str]]:
    qa = template.get("qa") if isinstance(template.get("qa"), dict) else {}
    areas = sorted(set(str(value).upper() for value in qa.get("areas", [])))
    creatures = sorted(set(str(value).upper() for value in qa.get("creatures", [])))
    return areas, creatures


def build_member_job(
    template: dict[str, Any],
    family: Family,
    job_id: str,
    destination: Path,
    project_root: Path,
) -> dict[str, Any]:
    paths = dict(template["paths"])
    paths["game_root"] = portable_path_reference("bg2ee_game_root")
    paths["scalepix"] = portable_path_reference("mmpx_scalepix")
    workspace = destination.parent.parent
    paths.update(
        character_workspace_paths(
            workspace, job_id, 2, family.animation_id
        )
    )
    areas, creatures = inherited_qa(template)
    animation: dict[str, Any] = {
        "name": f"{family.ids_symbol.replace('_', ' ').title()} — {family.bam_prefix}",
        "id": family.animation_id,
        "ids_symbol": family.ids_symbol,
        "bam_prefix": family.bam_prefix,
        "runtime_profile": family.runtime_profile,
    }
    qa: dict[str, Any] = {"areas": areas, "creatures": creatures}
    if family.layer_kind == "body":
        animation["armor_code"] = int(family.variant_value)
    else:
        assert family.representative_item is not None
        animation["layer"] = {
            "kind": family.layer_kind,
            "item_resref": family.representative_item,
        }
        qa["items"] = [family.representative_item]

    result: dict[str, Any] = {
        "schema": JOB_SCHEMA,
        "job_id": job_id,
        "animation": animation,
        "paths": paths,
        "compatibility": dict(template["compatibility"]),
        "runtime": dict(template.get("runtime", {})),
        "qa": qa,
        "upscale": dict(DIRECT_X2_METHOD),
    }
    if isinstance(template.get("tools"), dict):
        result["tools"] = dict(template["tools"])
    return result


def validate_reused_job(family: Family, path: Path, job: dict[str, Any]) -> None:
    animation = job["animation"]
    if str(animation.get("ids_symbol", "")).upper() != family.ids_symbol:
        raise RuntimeError(f"existing job {path} has a different ANIMATE.IDS symbol")
    if animation.get("runtime_profile") != family.runtime_profile:
        raise RuntimeError(f"existing job {path} has a different runtime profile")
    if job_layer(job) != family.layer_kind:
        raise RuntimeError(f"existing job {path} has a different Character layer")
    if family.needs_member_registry_set and not upscale_contract(job).explicit:
        raise RuntimeError(
            f"existing job {path} is legacy but {family.bam_prefix} requires explicit xN"
        )
    if family.layer_kind == "body" and int(animation.get("armor_code", -1)) != int(
        family.variant_value
    ):
        raise RuntimeError(f"existing job {path} has a different armor code")


def make_plan(
    *,
    project_root: Path,
    families_path: Path,
    character_root: Path,
    template_path: Path,
    aggregate_path: Path,
    animation_id: str,
    job_stem: str,
    force: bool,
) -> GenerationPlan:
    project_root = project_root.resolve()
    character_root = character_root.resolve()
    aggregate_path = aggregate_path.resolve()
    template_path = template_path.resolve()
    target_id = normalized_animation_id(animation_id)
    if not JOB_ID_RE.fullmatch(job_stem):
        raise RuntimeError("--job-stem must be a lowercase job-id prefix")
    expected_aggregate_root = character_root / "family-runs"
    if (
        aggregate_path.suffix.lower() != ".json"
        or aggregate_path.parent.name != "jobs"
        or aggregate_path.parent.parent.parent != expected_aggregate_root
    ):
        raise RuntimeError(
            "--aggregate-job must be below "
            "<character-root>/family-runs/<aggregate>/jobs/"
        )
    if character_root not in template_path.parents or template_path.parent.name != "jobs":
        raise RuntimeError("--template-job must be a Character member below --character-root")
    aggregate_id = aggregate_path.stem
    if not JOB_ID_RE.fullmatch(aggregate_id) or not aggregate_id.endswith("-xbr2x"):
        raise RuntimeError("aggregate filename must be a valid job id ending in -xbr2x")
    if aggregate_path.exists() and not force:
        raise RuntimeError(f"aggregate job already exists; use --force: {aggregate_path}")

    template = read_json(template_path)
    ensure_template(template, target_id)
    families, excluded = load_families(families_path, target_id)
    symbols = {family.ids_symbol for family in families}
    profiles = {family.runtime_profile for family in families}
    if len(symbols) != 1 or len(profiles) != 1:
        raise RuntimeError("inventory families disagree on Character identity")
    if str(template["animation"].get("ids_symbol", "")).upper() not in symbols:
        raise RuntimeError("template ANIMATE.IDS symbol differs from inventory")
    if template["animation"].get("runtime_profile") not in profiles:
        raise RuntimeError("template runtime profile differs from inventory")

    existing = discover_existing_jobs(character_root, target_id)
    reused: list[Path] = []
    generated: list[Path] = []
    member_paths: list[Path] = []
    writes: list[PlannedWrite] = []
    representatives: list[str] = []
    for family in families:
        match = existing.get(family.bam_prefix)
        if match is not None:
            member_path, member = match
            validate_reused_job(family, member_path, member)
            reused.append(member_path)
        else:
            job_id = generated_job_id(job_stem, family)
            member_path = member_job_path(character_root, family, job_id).resolve()
            if member_path.exists() and not force:
                raise RuntimeError(f"member job already exists; use --force: {member_path}")
            writes.append(
                PlannedWrite(
                    member_path,
                    build_member_job(
                        template, family, job_id, member_path, project_root
                    ),
                )
            )
            generated.append(member_path)
        member_paths.append(member_path)
        if family.representative_item is not None:
            representatives.append(family.representative_item)

    paths = template["paths"]
    areas, creatures = inherited_qa(template)
    required_families = [family for family in families if family.layer_kind == "body"]
    for layer in ("helmet", "shield", "weapon"):
        representative = next(
            (family for family in families if family.layer_kind == layer), None
        )
        if representative is not None:
            required_families.append(representative)
    required_prefixes = [family.bam_prefix for family in required_families]
    required_items = sorted(
        {
            family.representative_item
            for family in required_families
            if family.representative_item is not None
        }
    )
    aggregate_payload: dict[str, Any] = {
        "schema": ARMOR_SET_SCHEMA,
        "job_id": aggregate_id,
        "animation": {
            "name": f"{next(iter(symbols)).replace('_', ' ').title()} — Character complet",
            "id": target_id,
            "ids_symbol": next(iter(symbols)),
            "runtime_profile": next(iter(profiles)),
        },
        "members": [relative_path(path, project_root) for path in member_paths],
        "paths": {
            "game_root": portable_path_reference("bg2ee_game_root"),
            "run_dir": relative_path(
                aggregate_path.parent.parent / "runs" / "xbr2x-x2-xn",
                project_root,
            ),
            "engine_source": paths["engine_source"],
            "engine_build": relative_path(
                project_root
                / "sprite"
                / ".work"
                / "cmake"
                / "character"
                / target_id[2:].lower()
                / aggregate_id,
                project_root,
            ),
        },
        "compatibility": dict(template["compatibility"]),
        "runtime": dict(template.get("runtime", {})),
        "qa": {
            "areas": areas,
            "creatures": creatures,
            "items": sorted(set(representatives)),
            "required_bam_prefixes": required_prefixes,
            "required_items": required_items,
        },
        "upscale": dict(DIRECT_X2_METHOD),
        "inventory": {
            "families_csv": relative_path(families_path, project_root),
            "families_csv_sha256": hashlib.sha256(families_path.read_bytes()).hexdigest().upper(),
            "animation_id": target_id,
            "included_family_count": len(families),
            "excluded_families": excluded,
            "member_registry_set_families": [
                family.bam_prefix for family in families if family.needs_member_registry_set
            ],
        },
    }
    writes.append(PlannedWrite(aggregate_path, aggregate_payload))
    return GenerationPlan(
        project_root=project_root,
        character_root=character_root,
        writes=tuple(writes),
        aggregate_path=aggregate_path,
        aggregate_payload=aggregate_payload,
        reused_jobs=tuple(reused),
        generated_jobs=tuple(generated),
        excluded_families=tuple(excluded),
        member_set_families=tuple(
            family.bam_prefix for family in families if family.needs_member_registry_set
        ),
    )


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_plan(plan: GenerationPlan) -> None:
    """Validate generated descriptors with the canonical runner before publish."""

    VALIDATION_ROOT.mkdir(parents=True, exist_ok=True)
    validation_root = Path(
        tempfile.mkdtemp(prefix="character-jobs-", dir=VALIDATION_ROOT)
    )
    try:
        generated_mapping: dict[Path, Path] = {}
        for position, write in enumerate(
            (item for item in plan.writes if item.path != plan.aggregate_path)
        ):
            validation_path = validation_root / f"member-{position:04}.json"
            write_json_atomic(validation_path, write.payload)
            load_job(validation_path)
            generated_mapping[write.path.resolve()] = validation_path

        validation_payload = json.loads(json.dumps(plan.aggregate_payload))
        validation_members: list[str] = []
        for member_text in plan.aggregate_payload["members"]:
            final_path = (plan.project_root / str(member_text)).resolve()
            validation_path = generated_mapping.get(final_path, final_path)
            validation_members.append(relative_path(validation_path, plan.project_root))
        validation_payload["members"] = validation_members
        validation_aggregate = validation_root / "aggregate.json"
        write_json_atomic(validation_aggregate, validation_payload)
        loaded = load_armor_set(validation_aggregate)
        if len(loaded["_members"]) != len(validation_members):
            raise RuntimeError("validated aggregate member count differs from the plan")
    finally:
        shutil.rmtree(validation_root, ignore_errors=True)


def apply_plan(plan: GenerationPlan) -> dict[str, Any]:
    # Every collision and every payload is resolved by make_plan before the
    # first publication.  Individual publications are atomic on the jobs
    # volume; the aggregate is deliberately published last.
    validate_plan(plan)
    aggregate_write = next(write for write in plan.writes if write.path == plan.aggregate_path)
    for write in plan.writes:
        if write.path != plan.aggregate_path:
            write_json_atomic(write.path, write.payload)
    write_json_atomic(aggregate_write.path, aggregate_write.payload)
    for path in plan.generated_jobs:
        load_job(path)
    loaded_aggregate = load_armor_set(plan.aggregate_path)
    if len(loaded_aggregate["_members"]) != len(plan.aggregate_payload["members"]):
        raise RuntimeError("published aggregate member count differs from the plan")
    return {
        "status": "character-complete-x2-jobs-generated",
        "aggregate_job": str(plan.aggregate_path),
        "member_count": len(plan.aggregate_payload["members"]),
        "generated_member_jobs": [str(path) for path in plan.generated_jobs],
        "reused_member_jobs": [str(path) for path in plan.reused_jobs],
        "excluded_families": list(plan.excluded_families),
        "member_registry_set_families": list(plan.member_set_families),
        "pixels_produced": False,
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--animation-id", required=True)
    parser.add_argument("--template-job", type=Path, required=True)
    parser.add_argument("--job-stem", required=True)
    parser.add_argument("--aggregate-job", type=Path, required=True)
    parser.add_argument("--character-root", type=Path, required=True)
    parser.add_argument("--families", type=Path, default=DEFAULT_FAMILIES)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    args = make_parser().parse_args(argv)
    character_root = require_current_character_root(
        args.character_root, args.animation_id
    )
    plan = make_plan(
        project_root=PROJECT_ROOT,
        families_path=args.families,
        character_root=character_root,
        template_path=args.template_job,
        aggregate_path=args.aggregate_job,
        animation_id=args.animation_id,
        job_stem=args.job_stem,
        force=args.force,
    )
    print(json.dumps(apply_plan(plan), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        raise SystemExit(f"error: {error}") from error
