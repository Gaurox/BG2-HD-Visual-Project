"""Workflow authority for one visual effect BAM.

Runs are produced by a separate renderer. This command never generates pixels:
it reserves an immutable run id, validates its generic ``run.json`` descriptor,
then records the spatial or derived interpolation run in ``processing.csv``.
QA, installation and release are intentionally separate authorities.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROCESSING_FIELDS = (
    "asset_key", "asset_directory", "spatial_run", "spatial_state",
    "interpolation_run", "interpolation_state", "selected_run", "qa_state",
    "qa_evidence", "installation_state", "installation_receipt", "release_state",
    "release_candidate", "notes",
)
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RESREF_RE = re.compile(r"^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$")
SHA256_RE = re.compile(r"^[A-F0-9]{64}$")
RUN_TOP_LEVEL_FIELDS = {
    "$schema", "schema_version", "run_id", "domain", "asset_ids", "pipeline",
    "inputs", "outputs", "provenance", "result",
}
STAGES = {
    "spatial": "effects.spatial-x4.v1",
    "interpolation": "effects.interpolation-30fps.v1",
}
ACTIVE_PRODUCTION_STATES = {"in-progress", "produced", "verified"}


class WorkflowError(ValueError):
    """A requested authority transition or sealed descriptor is invalid."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_resref(raw_value: str) -> str:
    value = raw_value.strip().upper()
    if not RESREF_RE.fullmatch(value):
        raise WorkflowError(f"resref invalide: {raw_value!r}")
    return value


def validate_run_id(raw_value: str) -> str:
    value = raw_value.strip()
    if not RUN_ID_RE.fullmatch(value):
        raise WorkflowError(f"run_id invalide: {raw_value!r}")
    return value


def relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise WorkflowError(f"chemin hors workspace: {path}") from exc


def resolve_relative(root: Path, value: str, label: str) -> Path:
    normalized = value.replace("\\", "/")
    if not normalized or normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise WorkflowError(f"{label}: chemin non relatif: {value!r}")
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise WorkflowError(f"{label}: chemin hors workspace: {value!r}") from exc
    return candidate


def read_csv(path: Path, expected_fields: Sequence[str] | None = None) -> list[dict[str, str]]:
    if not path.is_file():
        raise WorkflowError(f"fichier absent: {path}")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if expected_fields is not None and tuple(reader.fieldnames or ()) != tuple(expected_fields):
            raise WorkflowError(f"schéma CSV inattendu: {path}")
        return list(reader)


def csv_bytes(rows: Iterable[Mapping[str, str]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=PROCESSING_FIELDS, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.partial")
    if partial.exists():
        raise WorkflowError(f"écriture déjà en cours: {partial}")
    partial.write_bytes(content)
    partial.replace(path)


def authority_paths(root: Path) -> tuple[Path, Path]:
    return root / "effects/index/bam-assets.csv", root / "effects/index/processing.csv"


def load_asset(root: Path, raw_resref: str) -> tuple[str, dict[str, str], list[dict[str, str]], Path]:
    resref = validate_resref(raw_resref)
    assets_path, processing_path = authority_paths(root)
    assets = read_csv(assets_path)
    matches = [row for row in assets if row.get("asset_key") == f"effects:bam:{resref}"]
    if len(matches) != 1:
        raise WorkflowError(f"{resref}: asset absent ou dupliqué dans bam-assets.csv")
    asset = matches[0]
    expected_directory = f"effects/ressources/{resref}"
    processing = read_csv(processing_path, PROCESSING_FIELDS)
    rows = [row for row in processing if row.get("asset_key") == asset["asset_key"]]
    if len(rows) != 1:
        raise WorkflowError(f"{resref}: ligne absente ou dupliquée dans processing.csv")
    if rows[0].get("asset_directory") != expected_directory:
        raise WorkflowError(f"{resref}: asset_directory invalide dans processing.csv")
    return resref, asset, processing, root / expected_directory


def processing_row(processing: list[dict[str, str]], resref: str) -> dict[str, str]:
    key = f"effects:bam:{resref}"
    return next(row for row in processing if row["asset_key"] == key)


def run_descriptor_path(resource_root: Path, raw_run_id: str) -> Path:
    return resource_root / "runs" / validate_run_id(raw_run_id) / "run.json"


def reservation_path(resource_root: Path, raw_run_id: str) -> Path:
    return resource_root / f".{validate_run_id(raw_run_id)}.reservation.json"


def safe_timestamp_id(resref: str, stage: str, recipe: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", recipe.casefold()).strip("-") or "recipe"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = f"{resref.casefold()}-{stage}-{token}-{timestamp}"
    if not RUN_ID_RE.fullmatch(candidate):
        raise WorkflowError(f"run_id automatique invalide: {candidate!r}")
    return candidate


def next_run_id(resource_root: Path, resref: str, stage: str, recipe: str) -> str:
    base = safe_timestamp_id(resref, stage, recipe)
    for ordinal in range(1, 10_001):
        candidate = base if ordinal == 1 else f"{base}-{ordinal}"
        if not run_descriptor_path(resource_root, candidate).exists() and not reservation_path(resource_root, candidate).exists():
            return candidate
    raise WorkflowError("aucun run_id libre après 10000 essais")


def evidence_errors(root: Path, entries: Any, label: str, *, required: bool) -> tuple[list[str], list[dict[str, Any]]]:
    if not isinstance(entries, list) or (required and not entries):
        return [f"{label}: tableau non vide requis"], []
    errors: list[str] = []
    verified: list[dict[str, Any]] = []
    for index, entry in enumerate(entries):
        item_label = f"{label}[{index}]"
        if not isinstance(entry, Mapping) or set(entry) != {"role", "path", "sha256", "bytes"}:
            errors.append(f"{item_label}: preuve invalide")
            continue
        role, path_text, digest, size = entry.get("role"), entry.get("path"), entry.get("sha256"), entry.get("bytes")
        if not isinstance(role, str) or not role:
            errors.append(f"{item_label}: rôle invalide")
        if not isinstance(path_text, str):
            errors.append(f"{item_label}: chemin invalide")
            continue
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest.upper()):
            errors.append(f"{item_label}: SHA-256 invalide")
        if not isinstance(size, int) or size < 0:
            errors.append(f"{item_label}: taille invalide")
        try:
            path = resolve_relative(root, path_text, item_label)
        except WorkflowError as error:
            errors.append(str(error))
            continue
        if not path.is_file():
            errors.append(f"{item_label}: fichier absent: {path_text}")
            continue
        if path.stat().st_size != size:
            errors.append(f"{item_label}: taille différente: {path_text}")
        if sha256_file(path) != str(digest).upper():
            errors.append(f"{item_label}: hash différent: {path_text}")
        verified.append(dict(entry))
    return errors, verified


def _timestamp_is_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").tzinfo == timezone.utc
    except ValueError:
        return False


def verify_run_descriptor(
    root: Path, resource_root: Path, resref: str, run_id: str, *, stage: str | None = None,
    spatial_run: str = "",
) -> dict[str, Any]:
    """Verify the generic descriptor and stage-specific effect lineage without writing."""

    run_id = validate_run_id(run_id)
    descriptor_path = run_descriptor_path(resource_root, run_id)
    relative_descriptor = relative_path(root, descriptor_path)
    errors: list[str] = []
    try:
        data = json.loads(descriptor_path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise WorkflowError("objet JSON requis")
    except (OSError, json.JSONDecodeError, WorkflowError) as error:
        return {"ok": False, "run_id": run_id, "descriptor_path": relative_descriptor, "errors": [f"run.json illisible: {error}"]}

    if set(data) != RUN_TOP_LEVEL_FIELDS:
        errors.append("run.json: clés top-level différentes du contrat générique")
    if data.get("$schema") != "docs/workspace-run.schema.json" or data.get("schema_version") != 1:
        errors.append("run.json: schéma générique invalide")
    if data.get("run_id") != run_id or data.get("domain") != "effects":
        errors.append("run.json: identité ou domaine invalide")
    if data.get("asset_ids") != [f"effects:bam:{resref}"]:
        errors.append("run.json: asset_ids doit contenir exactement le BAM propriétaire")

    pipeline = data.get("pipeline")
    if not isinstance(pipeline, Mapping) or set(pipeline) - {"id", "recipe_path", "recipe_sha256", "version"} or not {"id", "recipe_path", "recipe_sha256"}.issubset(pipeline):
        errors.append("run.json: pipeline invalide")
    else:
        if stage and pipeline.get("id") != STAGES[stage]:
            errors.append(f"run.json: pipeline.id attendu {STAGES[stage]!r}")
        try:
            recipe_path = resolve_relative(root, str(pipeline["recipe_path"]), "recette")
            if not recipe_path.is_file() or sha256_file(recipe_path) != str(pipeline["recipe_sha256"]).upper():
                errors.append("run.json: recette absente ou hash différent")
        except WorkflowError as error:
            errors.append(str(error))

    input_errors, inputs = evidence_errors(root, data.get("inputs"), "inputs", required=True)
    output_errors, outputs = evidence_errors(root, data.get("outputs"), "outputs", required=False)
    errors.extend(input_errors)
    errors.extend(output_errors)

    provenance = data.get("provenance")
    if not isinstance(provenance, Mapping) or set(provenance) - {"created_at_utc", "generator", "command", "parents"} or not {"created_at_utc", "generator"}.issubset(provenance):
        errors.append("run.json: provenance invalide")
        provenance = {}
    elif not _timestamp_is_utc(provenance.get("created_at_utc")) or not isinstance(provenance.get("generator"), str) or not provenance.get("generator"):
        errors.append("run.json: provenance incomplète")
    parents = provenance.get("parents", []) if isinstance(provenance, Mapping) else []
    if not isinstance(parents, list) or not all(isinstance(value, str) and RUN_ID_RE.fullmatch(value) for value in parents) or len(parents) != len(set(parents)):
        errors.append("run.json: parents invalides")
        parents = []

    result = data.get("result")
    if not isinstance(result, Mapping) or set(result) - {"status", "sealed", "completed_at_utc", "notes"} or not {"status", "sealed"}.issubset(result):
        errors.append("run.json: résultat invalide")
    elif result.get("status") != "completed" or result.get("sealed") is not True or not _timestamp_is_utc(result.get("completed_at_utc")):
        errors.append("run.json: seul un run completed et scellé est enregistrable")
    elif not outputs:
        errors.append("run.json: un run completed exige au moins une sortie")

    if stage == "spatial":
        expected_source = f"effects/ressources/{resref}/source.bam"
        matches = [item for item in inputs if item.get("role") == "source-bam" and item.get("path") == expected_source]
        if len(matches) != 1:
            errors.append("run spatial: preuve source-bam exacte requise")
    if stage == "interpolation":
        if parents != [spatial_run]:
            errors.append("run interpolation: parent spatial unique requis")
        if not any(item.get("role") == "parent-spatial-output" for item in inputs):
            errors.append("run interpolation: preuve parent-spatial-output requise")

    return {
        "ok": not errors, "run_id": run_id, "descriptor_path": relative_descriptor,
        "descriptor_sha256": sha256_file(descriptor_path), "inputs": inputs,
        "outputs": outputs, "parents": parents, "errors": errors,
    }


def assert_source_matches_inventory(resource_root: Path, asset: Mapping[str, str], verification: Mapping[str, Any]) -> None:
    source_path = resource_root / "source.bam"
    expected_hash = str(asset.get("source_sha256", "")).upper()
    expected_size = str(asset.get("source_size", ""))
    if asset.get("source_state") != "available" or not SHA256_RE.fullmatch(expected_hash) or not expected_size.isdigit():
        raise WorkflowError("source stock indisponible ou inventaire incomplet")
    if not source_path.is_file() or sha256_file(source_path) != expected_hash or source_path.stat().st_size != int(expected_size):
        raise WorkflowError("source.bam ne correspond pas à bam-assets.csv")
    source = next((item for item in verification.get("inputs", []) if item.get("role") == "source-bam"), None)
    if source is not None and (source.get("sha256", "").upper() != expected_hash or source.get("bytes") != int(expected_size)):
        raise WorkflowError("preuve source-bam différente de l'inventaire")


def verify_parent_binding(root: Path, resource_root: Path, resref: str, spatial_run: str, child: Mapping[str, Any]) -> None:
    parent = verify_run_descriptor(root, resource_root, resref, spatial_run, stage="spatial")
    if not parent.get("ok"):
        raise WorkflowError("parent spatial invalide: " + "; ".join(parent.get("errors", [])))
    output_keys = {(item.get("path"), str(item.get("sha256", "")).upper(), item.get("bytes")) for item in parent.get("outputs", [])}
    bindings = {(item.get("path"), str(item.get("sha256", "")).upper(), item.get("bytes")) for item in child.get("inputs", []) if item.get("role") == "parent-spatial-output"}
    if not output_keys or not output_keys & bindings:
        raise WorkflowError("aucune preuve interpolation ne lie une sortie du parent spatial")


def new_run(root: Path, raw_resref: str, stage: str, recipe: str, run_id: str | None, write: bool) -> dict[str, Any]:
    if stage not in STAGES:
        raise WorkflowError(f"étape inconnue: {stage}")
    resref, asset, processing, resource_root = load_asset(root, raw_resref)
    current = processing_row(processing, resref)
    if asset.get("source_state") != "available":
        raise WorkflowError(f"{resref}: source stock indisponible")
    if stage == "interpolation" and (not current.get("spatial_run") or current.get("spatial_state") not in {"produced", "verified"}):
        raise WorkflowError(f"{resref}: interpolation bloquée tant que le spatial n'est pas produit")
    chosen_id = validate_run_id(run_id) if run_id else next_run_id(resource_root, resref, stage, recipe)
    descriptor, reservation = run_descriptor_path(resource_root, chosen_id), reservation_path(resource_root, chosen_id)
    if descriptor.exists() or reservation.exists():
        raise WorkflowError(f"{resref}: run_id déjà occupé: {chosen_id}")
    payload = {
        "schema": "bg2-upscale-effect-run-reservation-v1", "run_id": chosen_id,
        "asset_id": f"effects:bam:{resref}", "stage": stage, "pipeline_id": STAGES[stage],
        "parent_run": current.get("spatial_run", "") if stage == "interpolation" else "",
        "created_at_utc": utc_now(),
    }
    if write:
        atomic_write(reservation, json_bytes(payload))
    return {
        "command": "new-run", "write": write, "resref": resref,
        "asset_id": f"effects:bam:{resref}", "stage": stage, "run_id": chosen_id,
        "run_directory": relative_path(root, descriptor.parent),
        "reservation": relative_path(root, reservation), "pipeline_id": STAGES[stage],
        "parent_run": payload["parent_run"],
        "required_source": f"effects/ressources/{resref}/source.bam", "release_mutation": False,
    }


def register_run(root: Path, raw_resref: str, stage: str, raw_run_id: str, write: bool) -> dict[str, Any]:
    if stage not in STAGES:
        raise WorkflowError(f"étape inconnue: {stage}")
    resref, asset, processing, resource_root = load_asset(root, raw_resref)
    current, run_id = processing_row(processing, resref), validate_run_id(raw_run_id)
    state_field, run_field = f"{stage}_state", f"{stage}_run"
    existing_run = current.get(run_field, "")
    if existing_run and existing_run != run_id and current.get(state_field) in ACTIVE_PRODUCTION_STATES:
        raise WorkflowError(f"{resref}: {stage} déjà actif sous {existing_run}; ne pas écraser un run retenu")
    spatial_run = current.get("spatial_run", "")
    verification = verify_run_descriptor(root, resource_root, resref, run_id, stage=stage, spatial_run=spatial_run)
    if not verification["ok"]:
        raise WorkflowError("run non enregistrable: " + "; ".join(verification["errors"]))
    if stage == "spatial":
        assert_source_matches_inventory(resource_root, asset, verification)
    else:
        verify_parent_binding(root, resource_root, resref, spatial_run, verification)

    reservation = reservation_path(resource_root, run_id)
    if reservation.exists():
        try:
            reserved = json.loads(reservation.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise WorkflowError(f"réservation illisible: {reservation}") from error
        expected = {"asset_id": f"effects:bam:{resref}", "stage": stage, "run_id": run_id}
        if any(reserved.get(key) != value for key, value in expected.items()):
            raise WorkflowError("réservation détenue par un autre run ou une autre étape")

    candidate = {row["asset_key"]: dict(row) for row in processing}
    candidate_row = candidate[f"effects:bam:{resref}"]
    candidate_row[run_field], candidate_row[state_field] = run_id, "produced"
    payload = csv_bytes(candidate[row["asset_key"]] for row in processing)
    if write:
        atomic_write(authority_paths(root)[1], payload)
        reservation.unlink(missing_ok=True)
    return {
        "command": "register-run", "write": write, "resref": resref,
        "asset_id": f"effects:bam:{resref}", "stage": stage, "run_id": run_id,
        "run_descriptor": verification["descriptor_path"],
        "run_descriptor_sha256": verification["descriptor_sha256"],
        "production_state": "produced", "release_mutation": False,
    }


def status_asset(root: Path, raw_resref: str) -> dict[str, Any]:
    resref, asset, processing, resource_root = load_asset(root, raw_resref)
    current = processing_row(processing, resref)
    runs = []
    runs_root = resource_root / "runs"
    if runs_root.is_dir():
        for descriptor in sorted(runs_root.glob("*/run.json"), key=lambda path: path.as_posix().casefold()):
            run_id = descriptor.parent.name
            verification = verify_run_descriptor(root, resource_root, resref, run_id)
            runs.append({"run_id": run_id, "ok": verification["ok"], "errors": verification["errors"]})
    return {"command": "status", "resref": resref, "asset": asset, "processing": current, "runs": runs, "release_mutation": False}


def check_workspace(root: Path, raw_resref: str | None = None) -> dict[str, Any]:
    assets_path, processing_path = authority_paths(root)
    assets, processing = read_csv(assets_path), read_csv(processing_path, PROCESSING_FIELDS)
    requested = validate_resref(raw_resref) if raw_resref else None
    errors: list[str] = []
    checked: list[str] = []
    processing_by_key = {row.get("asset_key", ""): row for row in processing}
    for asset in assets:
        resref = str(asset.get("resref", "")).upper()
        if requested and resref != requested:
            continue
        if not RESREF_RE.fullmatch(resref):
            errors.append(f"inventaire: resref invalide {resref!r}")
            continue
        current = processing_by_key.get(f"effects:bam:{resref}")
        if current is None:
            errors.append(f"{resref}: ligne processing absente")
            continue
        resource_root = root / "effects/ressources" / resref
        for stage in STAGES:
            run_id, state = current.get(f"{stage}_run", ""), current.get(f"{stage}_state", "")
            if state in ACTIVE_PRODUCTION_STATES and not run_id:
                errors.append(f"{resref}: {stage} actif sans run")
            if not run_id:
                continue
            checked.append(relative_path(root, run_descriptor_path(resource_root, run_id)))
            verification = verify_run_descriptor(root, resource_root, resref, run_id, stage=stage, spatial_run=current.get("spatial_run", ""))
            if not verification["ok"]:
                errors.extend(f"{resref}: {message}" for message in verification["errors"])
                continue
            try:
                if stage == "spatial":
                    assert_source_matches_inventory(resource_root, asset, verification)
                else:
                    verify_parent_binding(root, resource_root, resref, current.get("spatial_run", ""), verification)
            except WorkflowError as error:
                errors.append(f"{resref}: {error}")
    return {"command": "check", "resref": requested, "ok": not errors, "checked_files": sorted(set(checked)), "errors": errors, "release_mutation": False}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=PROJECT_ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="affiche un asset et ses runs physiques")
    status.add_argument("--resref", required=True)
    new_run_parser = commands.add_parser("new-run", help="planifie ou réserve un run immuable")
    new_run_parser.add_argument("--resref", required=True)
    new_run_parser.add_argument("--stage", required=True, choices=tuple(STAGES))
    new_run_parser.add_argument("--recipe", required=True, help="libellé utilisé seulement pour le run_id")
    new_run_parser.add_argument("--run-id")
    new_run_parser.add_argument("--run", action="store_true", help="crée la réservation atomique")
    register = commands.add_parser("register-run", help="enregistre un run completed/scellé")
    register.add_argument("--resref", required=True)
    register.add_argument("--stage", required=True, choices=tuple(STAGES))
    register.add_argument("--run-id", required=True)
    register.add_argument("--run", action="store_true", help="met à jour processing.csv")
    check = commands.add_parser("check", help="vérifie les runs référencés par processing.csv")
    check.add_argument("--resref")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.workspace_root.resolve()
    try:
        if args.command == "status":
            result = status_asset(root, args.resref)
        elif args.command == "new-run":
            result = new_run(root, args.resref, args.stage, args.recipe, args.run_id, args.run)
        elif args.command == "register-run":
            result = register_run(root, args.resref, args.stage, args.run_id, args.run)
        else:
            result = check_workspace(root, args.resref)
    except WorkflowError as error:
        print(f"ERROR: {error}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
