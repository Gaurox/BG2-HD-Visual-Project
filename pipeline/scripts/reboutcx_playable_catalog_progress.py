"""Create an immutable ReboutCX progress snapshot for completed playable families.

The snapshot discovers only families whose every xBR component has a sealed ReboutCX
manifest. It prefers P9 batch-86 outputs and falls back to a complete P8 family.
It records a pending derived catalog separately because shared xBR RESREFs may require
a selection policy before all families can coexist in one installable catalog.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from reboutcx_catalog import read_json, relative, sha256_file
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
PLAYABLE_ROOT = PROJECT_ROOT / "sprite/families/playable-characters"
XBR_PLAYABLE_CATALOG = (
    PROJECT_ROOT
    / "sprite/catalogs/creature-x2-nearest/jobs/append-all-playable-characters-v1.json"
)
SEED_CATALOG = (
    PROJECT_ROOT
    / "sprite/catalogs/creature-x2-reboutcx/jobs/"
    "catalog-reboutcx-character-6100-complete-p8-v1.json"
)
STATUS_DIR = PROJECT_ROOT / "sprite/catalogs/creature-x2-reboutcx/jobs"

P8_RUN = "reboutcx-p8-full-v1"
P9_RUN = "reboutcx-p9-batch86-v1"
FULL_RUN_SCHEMA = "bg2-upscale-reboutcx-full-run-v1"
STATUS_SCHEMA = "bg2-upscale-reboutcx-playable-progress-v1"
CATALOG_JOB_SCHEMA = "bg2-upscale-reboutcx-derived-catalog-job-v1"


def write_immutable_json(path: Path, value: object) -> None:
    encoded = json.dumps(value, indent=2) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != encoded:
            raise RuntimeError(f"immutable snapshot differs: {relative(path)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        stream.write(encoded)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def status_path(snapshot_id: str) -> Path:
    if re.fullmatch(r"[a-z0-9][a-z0-9-]*-v[1-9][0-9]*", snapshot_id) is None:
        raise RuntimeError("snapshot id must look like p9-v1")
    return STATUS_DIR / f"playable-characters-reboutcx-progress-{snapshot_id}.json"


def normal_id(value: object) -> str:
    try:
        number = int(str(value), 16)
    except ValueError as error:
        raise RuntimeError(f"invalid animation id: {value}") from error
    return f"0x{number:04X}"


def playable_roots() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for root in PLAYABLE_ROOT.iterdir():
        if not root.is_dir() or "-" not in root.name:
            continue
        if not list(root.glob("family-runs/complete-xn-xbr2x/jobs/*.json")):
            continue
        animation_id = normal_id(root.name.split("-", 1)[0])
        if animation_id in result:
            raise RuntimeError(f"duplicate playable workspace: {animation_id}")
        result[animation_id] = root
    return result


def source_families() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for animation_id, root in playable_roots().items():
        source_jobs = list(root.glob("family-runs/complete-xn-xbr2x/jobs/*.json"))
        if len(source_jobs) != 1:
            raise RuntimeError(f"ambiguous xBR family source: {relative(root)}")
        path = source_jobs[0]
        job = read_json(path)
        animation = job.get("animation")
        if not isinstance(animation, dict) or "id" not in animation:
            raise RuntimeError(f"invalid xBR family source: {relative(path)}")
        if normal_id(animation["id"]) != animation_id:
            raise RuntimeError(f"xBR source/workspace id differs: {relative(path)}")
        members = job.get("members")
        if not isinstance(members, list) or not members:
            raise RuntimeError(f"invalid xBR family source: {relative(path)}")
        result.append(
            {
                "animation_id": animation_id,
                "source_job": path,
                "family_root": root,
                "expected_members": len(members),
            }
        )
    return sorted(result, key=lambda item: int(item["animation_id"], 16))


def manifest_for_job(job_path: Path) -> Path | None:
    if not job_path.is_file():
        return None
    job = read_json(job_path)
    run_path = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)
    manifest = run_path / "manifest.json"
    if not manifest.is_file():
        return None
    value = read_json(manifest)
    if (
        value.get("schema") != FULL_RUN_SCHEMA
        or value.get("status") != "completed-pending-human-review"
        or value.get("installable") is not False
        or int(value.get("target_scale", 0)) != 2
    ):
        return None
    return manifest


def completed_family(family: dict[str, Any]) -> dict[str, Any] | None:
    root = family["family_root"]
    prepared_path = (
        root / "family-runs/complete-reboutcx-p8-v1/runs/reboutcx-p8-full-v1/prepared.json"
    )
    if not prepared_path.is_file():
        return None
    prepared = read_json(prepared_path)
    members = prepared.get("members")
    if not isinstance(members, list) or len(members) != family["expected_members"]:
        return None
    p8_jobs = [
        resolve_path_reference(item["job"], required=True, root=PROJECT_ROOT)
        for item in members
    ]
    p9_jobs = [path.with_name(f"{P9_RUN}.json") for path in p8_jobs]
    p9_manifests = [manifest_for_job(path) for path in p9_jobs]
    p8_manifests = [manifest_for_job(path) for path in p8_jobs]
    if all(p9_manifests):
        method, manifests = P9_RUN, p9_manifests
    elif all(p8_manifests):
        method, manifests = P8_RUN, p8_manifests
    else:
        return None
    values = [path for path in manifests if path is not None]
    for manifest_path in values:
        manifest = read_json(manifest_path)
        if normal_id(manifest["animation_id"]) != family["animation_id"]:
            raise RuntimeError(f"component has another animation: {relative(manifest_path)}")
    return {
        **family,
        "method": method,
        "manifests": values,
        "component_indices": [int(item["component_index"]) for item in members],
    }


def legacy_catalog_family(family: dict[str, Any], seed: dict[str, Any]) -> dict[str, Any] | None:
    """Use the pre-P9 catalog record for a complete P8 family with sealed members."""

    entries = sorted(
        (
            item
            for item in seed["replacements"]
            if normal_id(item["animation_id"]) == family["animation_id"]
        ),
        key=lambda item: int(item["expected_component_indices"][0]),
    )
    if not entries:
        return None
    if len(entries) != family["expected_members"]:
        raise RuntimeError(f"legacy catalog coverage differs: {family['animation_id']}")
    manifests: list[Path] = []
    indices: list[int] = []
    for item in entries:
        manifest_path = resolve_path_reference(
            item["reboutcx_manifest"], required=True, root=PROJECT_ROOT
        )
        if sha256_file(manifest_path) != str(item["reboutcx_manifest_sha256"]):
            raise RuntimeError(f"legacy catalog manifest differs: {relative(manifest_path)}")
        manifest = read_json(manifest_path)
        if normal_id(manifest["animation_id"]) != family["animation_id"]:
            raise RuntimeError(f"legacy catalog animation differs: {relative(manifest_path)}")
        manifests.append(manifest_path)
        indices.append(int(item["expected_component_indices"][0]))
    return {
        **family,
        "method": P8_RUN,
        "manifests": manifests,
        "component_indices": indices,
    }


def snapshot() -> dict[str, Any]:
    seed = read_json(SEED_CATALOG)
    if seed.get("schema") != CATALOG_JOB_SCHEMA or seed.get("installable") is not False:
        raise RuntimeError("invalid legacy ReboutCX catalog")
    candidates = source_families()
    complete = []
    for family in candidates:
        value = completed_family(family) or legacy_catalog_family(family, seed)
        if value is not None:
            complete.append(value)
    complete_ids = {item["animation_id"] for item in complete}
    pending = [item for item in candidates if item["animation_id"] not in complete_ids]

    family_status: list[dict[str, Any]] = []
    for family in complete:
        components = [
            {
                "component_index": component_index,
                "manifest": relative(manifest_path),
                "manifest_sha256": sha256_file(manifest_path),
            }
            for component_index, manifest_path in zip(
                family["component_indices"], family["manifests"], strict=True
            )
        ]
        if len({item["component_index"] for item in components}) != family["expected_members"]:
            raise RuntimeError(f"incomplete Character coverage: {family['animation_id']}")
        family_status.append(
            {
                "animation_id": family["animation_id"],
                "family": relative(family["family_root"]),
                "method": family["method"],
                "components": components,
                "status": "verified-runs-pending-qa-install-release",
            }
        )

    status = {
        "schema": STATUS_SCHEMA,
        "status": "verified-runs-pending-derived-catalog-qa-install-release",
        "scope": "playable-characters",
        "xbr_source_catalog": relative(XBR_PLAYABLE_CATALOG),
        "xbr_source_catalog_sha256": sha256_file(XBR_PLAYABLE_CATALOG),
        "totals": {
            "playable_families": len(candidates),
            "completed_families": len(family_status),
            "pending_families": len(pending),
            "reboutcx_components": sum(len(item["components"]) for item in family_status),
        },
        "completed": family_status,
        "pending_animation_ids": [item["animation_id"] for item in pending],
        "boundaries": {
            "derived_catalog": "not-built; shared xBR RESREF selection unresolved",
            "qa": "not-accepted",
            "installation": "not-installed",
            "release": "not-candidate",
        },
    }
    return status


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write-status",))
    parser.add_argument("--snapshot-id", default="p9-v1")
    args = parser.parse_args()
    status = snapshot()
    output = status_path(args.snapshot_id)
    status["snapshot_id"] = args.snapshot_id
    write_immutable_json(output, status)
    result = {
        "status": status["status"],
        "tracking": relative(output),
        "families": status["totals"]["completed_families"],
        "pending": status["totals"]["pending_families"],
    }
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
