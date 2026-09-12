"""Plan and explicitly execute bounded BG2EE water-batch preparation stages.

Default mode is read-only. ``--run`` creates a new immutable orchestration root.
Only ``preflight`` and ``seedvr`` stages are executable in phase 5. The script
never builds, installs, tests, packages, publishes, or edits release state.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shlex
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATRIX = ROOT / ".tmp" / "water-phase23-20260912" / "matrix.json"
DEFAULT_FAMILY_POLICY = ROOT / "pipeline" / "water" / "family-policy-v1.json"
DEFAULT_ROUTE2_REGISTRY = ROOT / "pipeline" / "water" / "route2-registry-v1.json"
DEFAULT_OUTPUT_ROOT = ROOT / "maps" / "water-batches" / "runs"
SUPPORTED_EXECUTION_STAGES = {"preflight", "seedvr"}
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def repository_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError as error:
        raise RuntimeError(f"le fichier doit rester dans le workspace : {path}") from error


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise RuntimeError(f"fichier requis absent : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_family_policy(policy: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if policy.get("schema") != "bg2-water-family-policy-v1" or policy.get("version") != 1:
        raise RuntimeError("family policy invalide ou version non supportée")
    method = policy.get("seedvr", {}).get("new_processing_color_correction_method")
    if method != "none":
        raise RuntimeError(f"le lot eau exige SeedVR color_correction_method=none, reçu {method!r}")
    overlay_to_family: dict[str, dict[str, Any]] = {}
    for family in policy.get("families", []):
        family_id = family.get("id")
        if not family_id:
            raise RuntimeError("famille sans id")
        for overlay in family.get("overlays", []):
            upper = str(overlay).upper()
            if upper in overlay_to_family:
                raise RuntimeError(f"overlay présent dans plusieurs familles : {upper}")
            overlay_to_family[upper] = family
    if not overlay_to_family:
        raise RuntimeError("family policy vide")
    return overlay_to_family


def validate_route2_registry(registry: dict[str, Any]) -> None:
    if registry.get("schema") != "bg2-water-route2-registry-v1" or registry.get("version") != 1:
        raise RuntimeError("registre route2 invalide ou version non supportée")
    if registry.get("fallback", {}).get("strength") != 0.0:
        raise RuntimeError("le fallback route2 doit être q=0")
    ids: set[str] = set()
    identities: set[tuple[str, int, str]] = set()
    for entry in registry.get("entries", []):
        entry_id = str(entry.get("id", ""))
        overlay = entry.get("overlay", {})
        identity = (
            str(entry.get("wed", {}).get("resref", "")).upper(),
            int(overlay.get("slot", -1)),
            str(overlay.get("tis_resref", "")).upper(),
        )
        if not entry_id or entry_id in ids or identity in identities:
            raise RuntimeError(f"entrée route2 dupliquée/invalide : {entry_id or identity}")
        ids.add(entry_id)
        identities.add(identity)
        strength = entry.get("approved_strength")
        if not isinstance(strength, (int, float)) or not 0.0 <= float(strength) <= 1.0:
            raise RuntimeError(f"dosage route2 invalide : {entry_id}")
        if entry.get("state") != "approved-ingame" or entry.get("qa", {}).get("status") != "validated-ingame":
            raise RuntimeError(f"entrée route2 non approuvée dans l'allowlist active : {entry_id}")
        if not overlay.get("pages") or not entry.get("base_tis", {}).get("pages"):
            raise RuntimeError(f"pages incomplètes dans l'entrée route2 : {entry_id}")


def validate_matrix(
    rows: list[dict[str, Any]], overlay_to_family: dict[str, dict[str, Any]]
) -> None:
    if not rows:
        raise RuntimeError("matrice eau vide")
    identities: set[tuple[str, int, str]] = set()
    unknown: set[str] = set()
    for row in rows:
        identity = (
            str(row.get("wed", "")).upper(),
            int(row.get("overlay_slot", -1)),
            str(row.get("overlay_resref", "")).upper(),
        )
        if not identity[0] or identity[1] < 1 or not identity[2] or identity in identities:
            raise RuntimeError(f"identité matrice dupliquée/invalide : {identity}")
        identities.add(identity)
        if identity[2] not in overlay_to_family:
            unknown.add(identity[2])
    if unknown:
        raise RuntimeError("overlays sans famille explicite : " + ", ".join(sorted(unknown)))


def route2_match(row: dict[str, Any], entry: dict[str, Any]) -> bool:
    wed = entry.get("wed", {})
    base = entry.get("base_tis", {})
    overlay = entry.get("overlay", {})
    row_overlay = row.get("overlay_tis", {})
    return (
        str(row.get("wed", "")).upper() == str(wed.get("resref", "")).upper()
        and row.get("wed_sha256") == wed.get("sha256")
        and row.get("grid") == wed.get("grid")
        and [str(layer.get("resref", "")).upper() for layer in row.get("all_layers", [])]
        == [str(slot).upper() for slot in wed.get("overlay_slots", [])]
        and row.get("base_tis", {}).get("resref") == base.get("resref")
        and row.get("base_tis", {}).get("sha256") == base.get("sha256")
        and row.get("base_tis", {}).get("tile_count") == base.get("tile_count")
        and row.get("base_tis", {}).get("tile_dimension") == base.get("tile_dimension")
        and row.get("overlay_slot") == overlay.get("slot")
        and row.get("overlay_resref") == overlay.get("tis_resref")
        and row_overlay.get("sha256") == overlay.get("tis_sha256")
        and row_overlay.get("tile_count") == overlay.get("tile_count")
        and row_overlay.get("tile_dimension") == overlay.get("tile_dimension")
        and row_overlay.get("pages")
        == [page.get("resref") for page in overlay.get("pages", [])]
    )


def live_route2_registry_status(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    try:
        override = Path(get_path("bg2ee_game_root")) / "override"
    except Exception as error:
        return {
            str(entry["id"]): {"approved": False, "errors": [f"game-root:{error}"]}
            for entry in registry.get("entries", [])
        }
    statuses: dict[str, dict[str, Any]] = {}
    for entry in registry.get("entries", []):
        expected_files = [
            {
                "name": f"{entry['base_tis']['resref']}.TIS",
                "bytes": entry["base_tis"]["bytes"],
                "sha256": entry["base_tis"]["sha256"],
            },
            *(
                {"name": f"{page['resref']}.PVRZ", **page}
                for page in entry["base_tis"]["pages"]
            ),
            {
                "name": f"{entry['overlay']['tis_resref']}.TIS",
                "bytes": entry["overlay"]["tis_bytes"],
                "sha256": entry["overlay"]["tis_sha256"],
            },
            *(
                {"name": f"{page['resref']}.PVRZ", **page}
                for page in entry["overlay"]["pages"]
            ),
        ]
        errors: list[str] = []
        for expected in expected_files:
            path = override / expected["name"]
            if not path.is_file():
                errors.append(f"missing:{expected['name']}")
                continue
            if path.stat().st_size != int(expected["bytes"]):
                errors.append(f"bytes:{expected['name']}")
                continue
            if sha256(path) != str(expected["sha256"]).upper():
                errors.append(f"sha256:{expected['name']}")
        statuses[str(entry["id"])] = {
            "approved": not errors,
            "checked_root": str(override),
            "checked_files": len(expected_files),
            "errors": errors,
        }
    return statuses


def route2_decision(
    row: dict[str, Any], registry: dict[str, Any],
    live_approved_ids: set[str] | None = None,
) -> tuple[float, str | None]:
    matches = [entry for entry in registry.get("entries", []) if route2_match(row, entry)]
    if len(matches) > 1:
        raise RuntimeError(f"plusieurs entrées route2 correspondent à {row['wed']} slot {row['overlay_slot']}")
    if not matches:
        return 0.0, None
    if live_approved_ids is not None and str(matches[0]["id"]) not in live_approved_ids:
        return 0.0, None
    return float(matches[0]["approved_strength"]), str(matches[0]["id"])


def base_repair_reasons(row: dict[str, Any]) -> list[str]:
    diagnostics = row.get("base_diagnostics", {})
    reasons: list[str] = []
    for field in (
        "alpha0_native_divergence_ids",
        "alpha255_native_divergence_ids",
        "missing_primary_ids",
    ):
        count = int(diagnostics.get(field, 0) or 0)
        if count:
            reasons.append(f"{field}:{count}")
    interface = diagnostics.get("interface_heuristic", {})
    if int(interface.get("secondary_alpha_drop", 0) or 0):
        reasons.append(f"secondary_alpha_drop:{interface['secondary_alpha_drop']}")
    padding = diagnostics.get("padding", {})
    if int(padding.get("out_of_bounds", 0) or 0):
        reasons.append(f"padding_out_of_bounds:{padding['out_of_bounds']}")
    return reasons


def overlay_repair_reasons(row: dict[str, Any]) -> list[str]:
    return [str(issue) for issue in row.get("overlay_diagnostics", {}).get("issues", [])]


def final_state(row: dict[str, Any], strength: float) -> tuple[str, list[str]]:
    if strength > 0.0:
        return "corrected", []
    phase3 = row.get("phase3_status")
    if phase3 == "already-conform-structural":
        return "already-conform", ["route2-unapproved-q0"]
    reasons = [*base_repair_reasons(row), *overlay_repair_reasons(row)]
    reasons.extend(str(value) for value in row.get("blockers", []))
    if phase3 == "requires-qualified-review":
        reasons.append("qualified-review-required")
    if not reasons:
        reasons.append(f"phase3-status:{phase3}")
    return "blocked", sorted(set(reasons))


def read_area_catalog() -> dict[str, dict[str, str]]:
    with (ROOT / "areas.csv").open(encoding="utf-8-sig", newline="") as stream:
        return {row["area_id"].upper(): row for row in csv.DictReader(stream)}


def day_area(wed: str) -> str:
    return wed[:-1] if wed.endswith("N") else wed


def split_arguments(catalog_row: dict[str, str] | None) -> list[str]:
    value = (catalog_row or {}).get("split_seedvr", "")
    grid = re.search(r"--split-grid\s+(\d+)\s+(\d+)", value)
    if grid:
        return ["--split-grid", grid.group(1), grid.group(2)]
    if "--split-rows" in value:
        return ["--split-rows"]
    return []


def required_tile_kinds(row: dict[str, Any]) -> list[str]:
    suffix = "-nuit" if str(row["wed"]).endswith("N") else ""
    kinds = [f"tuiles-principales{suffix}"]
    diagnostics = row.get("base_diagnostics", {})
    if int(diagnostics.get("liquid_cells", 0) or 0) > int(
        diagnostics.get("liquid_cells_without_secondary", 0) or 0
    ):
        kinds.append(f"tuiles-secondaires{suffix}")
    return kinds


def source_render(area: str, wed: str, tile_kind: str) -> Path:
    base_kind = tile_kind.removesuffix("-nuit")
    stem = wed if tile_kind.endswith("-nuit") else area
    return ROOT / "maps" / area / "rendus-x1" / tile_kind / f"{stem}-{base_kind}-x1.png"


def seedvr_argv(
    *, area: str, map_run: str, preflight: str, tile_kind: str,
    split_args: list[str], append: bool,
) -> list[str]:
    argv = [
        sys.executable, "-B", "pipeline/scripts/run_seedvr_comfyui.py",
        "--area", area,
        "--run", map_run,
        "--preflight", preflight,
        "--tile-kind", tile_kind,
        "--scale", "4",
        "--expected-scale", "4",
        "--color-correction-method", "none",
        "--variant", "seedvr2-7b-int8-none",
        *split_args,
    ]
    if append:
        argv.append("--append")
    return argv


def filter_rows(
    rows: list[dict[str, Any]], overlay_to_family: dict[str, dict[str, Any]],
    weds: set[str], families: set[str]
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        family_id = overlay_to_family[row["overlay_resref"]]["id"]
        if weds and row["wed"] not in weds:
            continue
        if families and family_id not in families:
            continue
        selected.append(row)
    if not selected:
        raise RuntimeError("aucune cible après filtrage")
    return selected


def build_plan(
    *, rows: list[dict[str, Any]], policy: dict[str, Any], registry: dict[str, Any],
    matrix_path: Path, policy_path: Path, registry_path: Path, run_id: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    selected_weds: set[str] | None = None, selected_families: set[str] | None = None,
) -> dict[str, Any]:
    overlay_to_family = validate_family_policy(policy)
    validate_route2_registry(registry)
    validate_matrix(rows, overlay_to_family)
    expected_matrix_hash = policy.get("inputs", {}).get("phase23_matrix_sha256")
    actual_matrix_hash = sha256(matrix_path)
    if expected_matrix_hash != actual_matrix_hash:
        raise RuntimeError(
            f"matrice divergente : {actual_matrix_hash}; attendue {expected_matrix_hash}"
        )
    selected = filter_rows(
        rows, overlay_to_family,
        {value.upper() for value in (selected_weds or set())},
        set(selected_families or set()),
    )
    targets: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    live_registry = live_route2_registry_status(registry)
    live_approved_ids = {
        entry_id for entry_id, status in live_registry.items() if status["approved"]
    }
    for row in selected:
        family = overlay_to_family[row["overlay_resref"]]
        strength, registry_id = route2_decision(row, registry, live_approved_ids)
        state, reasons = final_state(row, strength)
        target = {
            "id": f"{row['wed']}:{row['overlay_slot']}:{row['overlay_resref']}",
            "wed": row["wed"],
            "variant": "night" if row["wed"].endswith("N") else "day",
            "overlay_slot": row["overlay_slot"],
            "overlay": row["overlay_resref"],
            "family": family["id"],
            "phase3_status": row["phase3_status"],
            "voie1": {
                "required": bool(base_repair_reasons(row) or overlay_repair_reasons(row)),
                "base_reasons": base_repair_reasons(row),
                "overlay_reasons": overlay_repair_reasons(row),
            },
            "route2": {
                "strength": strength,
                "registry_entry": registry_id,
                "fallback": registry_id is None,
            },
            "state": state,
            "state_reasons": reasons,
        }
        targets.append(target)
        grouped[row["wed"]].append(row)

    catalog = read_area_catalog()
    batch_root = Path(repository_path(output_root)) / run_id
    preflight_commands: list[dict[str, Any]] = []
    for area in sorted({day_area(wed) for wed in grouped}):
        preflight_commands.append({
            "kind": "preflight",
            "area": area,
            "argv": [
                sys.executable, "-B", "pipeline/scripts/audit_area_preflight.py", area,
                (batch_root / "preflight" / f"{area}.json").as_posix(),
            ],
        })

    seedvr_commands: list[dict[str, Any]] = []
    seedvr_blockers: list[dict[str, Any]] = []
    for wed, wed_rows in sorted(grouped.items()):
        if wed == "AR0900":
            continue
        base_reasons = sorted({reason for row in wed_rows for reason in base_repair_reasons(row)})
        if not base_reasons:
            continue
        area = day_area(wed)
        representative = wed_rows[0]
        kinds = required_tile_kinds(representative)
        missing = [
            source_render(area, wed, kind).relative_to(ROOT).as_posix()
            for kind in kinds if not source_render(area, wed, kind).is_file()
        ]
        if missing:
            seedvr_blockers.append({"wed": wed, "reason": "missing-x1-render", "paths": missing})
            continue
        map_run = f"{run_id}-{wed.lower()}-seedvr2-7b-int8-none-x4"
        for index, kind in enumerate(kinds):
            argv = seedvr_argv(
                area=area,
                map_run=map_run,
                preflight=(batch_root / "preflight" / f"{area}.json").as_posix(),
                tile_kind=kind,
                split_args=split_arguments(catalog.get(area)),
                append=bool(index),
            )
            seedvr_commands.append({
                "kind": "seedvr",
                "area": area,
                "wed": wed,
                "tile_kind": kind,
                "color_correction_method": "none",
                "argv": argv,
            })

    state_counts = Counter(target["state"] for target in targets)
    family_counts = Counter(target["family"] for target in targets)
    return {
        "schema": "bg2-water-orchestration-plan-v1",
        "run_id": run_id,
        "mode": "plan-only-unless-run",
        "inputs": {
            "matrix": {
                "role": "water-target-matrix",
                "path": repository_path(matrix_path),
                "sha256": actual_matrix_hash,
                "bytes": matrix_path.stat().st_size,
            },
            "family_policy": {
                "role": "water-family-policy",
                "path": repository_path(policy_path),
                "sha256": sha256(policy_path),
                "bytes": policy_path.stat().st_size,
            },
            "route2_registry": {
                "role": "water-route2-registry",
                "path": repository_path(registry_path),
                "sha256": sha256(registry_path),
                "bytes": registry_path.stat().st_size,
            },
        },
        "contracts": {
            "seedvr_color_correction_method": "none",
            "voie1_before_route2": True,
            "route2_unknown_or_divergent_strength": 0.0,
            "historical_ar0900_and_wtlake_artifacts_unchanged": True,
            "install": "out-of-scope",
            "tests": "out-of-scope",
            "release": "out-of-scope",
        },
        "coverage": {
            "matrix_rows_total": len(rows),
            "selected_rows": len(targets),
            "selected_weds": len(grouped),
            "states": dict(sorted(state_counts.items())),
            "families": dict(sorted(family_counts.items())),
            "silent_exclusions": 0,
        },
        "targets": targets,
        "route2_registry_live": live_registry,
        "commands": {
            "preflight": preflight_commands,
            "seedvr": seedvr_commands,
        },
        "blocked_execution": {
            "seedvr": seedvr_blockers,
            "voie1": "phase7-parameterized-builder-required",
            "route2_engine": "phase6-registry-consumer-required",
            "candidate_installation": "separate-user-approval-required",
        },
    }


def powershell_command(argv: list[str]) -> str:
    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"
    return "& " + " ".join(quote(str(value)) for value in argv)


def write_run(plan: dict[str, Any], output_root: Path) -> Path:
    run_root = output_root / plan["run_id"]
    if run_root.exists():
        raise FileExistsError(f"refus de réécrire le run : {run_root}")
    run_root.mkdir(parents=True)
    plan_path = run_root / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    command_lines = [
        "# Generated plan; execute only the user-approved stage.",
        *(
            powershell_command(command["argv"])
            for stage in ("preflight", "seedvr")
            for command in plan["commands"][stage]
        ),
    ]
    (run_root / "commands.ps1").write_text("\n".join(command_lines) + "\n", encoding="utf-8")
    plan_repo_path = repository_path(plan_path)
    commands_path = run_root / "commands.ps1"
    commands_repo_path = repository_path(commands_path)
    now = datetime.now(timezone.utc).isoformat()
    run_manifest = {
        "$schema": "docs/workspace-run.schema.json",
        "schema_version": 1,
        "run_id": plan["run_id"],
        "domain": "maps",
        "asset_ids": sorted({
            f"maps:{target['wed']}:{target['variant']}" for target in plan["targets"]
        }),
        "pipeline": {
            "id": "water-batch-orchestration-v1",
            "recipe_path": plan_repo_path,
            "recipe_sha256": sha256(plan_path),
            "version": "1",
        },
        "inputs": list(plan["inputs"].values()),
        "outputs": [
            {
                "role": "orchestration-plan",
                "path": plan_repo_path,
                "sha256": sha256(plan_path),
                "bytes": plan_path.stat().st_size,
            },
            {
                "role": "commands",
                "path": commands_repo_path,
                "sha256": sha256(commands_path),
                "bytes": commands_path.stat().st_size,
            },
        ],
        "provenance": {
            "created_at_utc": now,
            "generator": "pipeline/scripts/orchestrate_water_batch.py",
        },
        "result": {
            "status": "planned",
            "sealed": True,
            "notes": "No inference, build, test, installation, QA or release was inferred.",
        },
    }
    (run_root / "run.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return run_root


def write_execution_receipt(
    run_root: Path, stage: str, exit_code: int, error: str | None = None
) -> Path:
    receipt = run_root / f"{stage}-execution-receipt.json"
    if receipt.exists():
        raise FileExistsError(f"refus de réécrire le reçu : {receipt}")
    payload = {
        "schema": "bg2-water-orchestration-execution-receipt-v1",
        "stage": stage,
        "status": "completed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "preflight-and-seedvr-only; no build/install/test/qa/release",
    }
    if error:
        payload["error"] = error
    receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def execute_stage(plan: dict[str, Any], stage: str, keep_going: bool) -> int:
    if stage not in SUPPORTED_EXECUTION_STAGES:
        raise RuntimeError(f"étape non exécutable en phase 5 : {stage}")
    commands = list(plan["commands"]["preflight"])
    if stage == "seedvr":
        blockers = plan["blocked_execution"]["seedvr"]
        if blockers:
            raise RuntimeError("SeedVR refusé : rendus x1 manquants : " + json.dumps(blockers))
        commands.extend(plan["commands"]["seedvr"])
    failures = 0
    for command in commands:
        result = subprocess.run(command["argv"], cwd=ROOT, check=False)
        if result.returncode:
            failures += 1
            if not keep_going:
                return result.returncode
    return 1 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--family-policy", type=Path, default=DEFAULT_FAMILY_POLICY)
    parser.add_argument("--route2-registry", type=Path, default=DEFAULT_ROUTE2_REGISTRY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id")
    parser.add_argument("--stage", choices=("plan", "preflight", "seedvr"), default="plan")
    parser.add_argument("--wed", action="append", default=[])
    parser.add_argument("--family", action="append", default=[])
    parser.add_argument("--run", action="store_true", help="écrit un nouveau run et exécute l'étape choisie")
    parser.add_argument("--keep-going", action="store_true")
    parser.add_argument("--json", action="store_true", help="affiche le plan intégral en mode lecture seule")
    args = parser.parse_args()
    if args.run:
        if not args.run_id or not RUN_ID_RE.fullmatch(args.run_id):
            parser.error("--run exige un --run-id neuf et sûr")
    elif args.keep_going:
        parser.error("--keep-going exige --run")
    elif args.stage != "plan":
        parser.error("une étape autre que plan exige --run")
    if args.run_id and not RUN_ID_RE.fullmatch(args.run_id):
        parser.error("--run-id invalide")
    return args


def main() -> int:
    args = parse_args()
    matrix_path = args.matrix.resolve()
    policy_path = args.family_policy.resolve()
    registry_path = args.route2_registry.resolve()
    policy = load_json(policy_path)
    registry = load_json(registry_path)
    rows = load_json(matrix_path)
    if not isinstance(rows, list):
        raise RuntimeError("matrix.json doit contenir une liste")
    run_id = args.run_id or "<new-run-id>"
    plan = build_plan(
        rows=rows,
        policy=policy,
        registry=registry,
        matrix_path=matrix_path,
        policy_path=policy_path,
        registry_path=registry_path,
        run_id=run_id,
        output_root=args.output_root.resolve(),
        selected_weds=set(args.wed),
        selected_families=set(args.family),
    )
    if not args.run:
        if args.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
        else:
            print(json.dumps({"coverage": plan["coverage"], "contracts": plan["contracts"]}, ensure_ascii=False, indent=2))
            print("Plan only; add --stage preflight|seedvr --run --run-id <new-id> after explicit approval.")
        return 0
    run_root = write_run(plan, args.output_root.resolve())
    print(f"Run planifié : {run_root}")
    if args.stage == "plan":
        return 0
    try:
        exit_code = execute_stage(plan, args.stage, args.keep_going)
    except Exception as error:
        receipt = write_execution_receipt(run_root, args.stage, 1, str(error))
        print(f"Reçu d'échec : {receipt}", file=sys.stderr)
        raise
    receipt = write_execution_receipt(run_root, args.stage, exit_code)
    print(f"Reçu d'exécution : {receipt}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
