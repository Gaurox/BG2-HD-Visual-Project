"""Workflow authority for one visual effect BAM.

Runs are produced by a separate renderer. This command never generates pixels:
it reserves an immutable run id, validates its generic ``run.json`` descriptor,
then records the latest trial in ``processing.csv``. ``accept`` pins the exact
user-approved result transactionally. Installation and release stay independent.
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

import effect_authority as authority


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
PRODUCTION_STATES = ACTIVE_PRODUCTION_STATES | {"not-started", "rejected", "blocked", "not-applicable"}
SELECTION_SCHEMA = "bg2-effects-selection-v1"


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


@authority.guarded
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


@authority.guarded
def register_run(root: Path, raw_resref: str, stage: str, raw_run_id: str, write: bool) -> dict[str, Any]:
    if stage not in STAGES:
        raise WorkflowError(f"étape inconnue: {stage}")
    resref, asset, processing, resource_root = load_asset(root, raw_resref)
    current, run_id = processing_row(processing, resref), validate_run_id(raw_run_id)
    state_field, run_field = f"{stage}_state", f"{stage}_run"
    existing_run = current.get(run_field, "")
    # Production points at the latest trial. Accepted bytes stay pinned separately
    # in selections/<RESREF>.json; correcting a BAM never discards its acquired QA.
    if current.get("qa_state") in {"passed", "native"} and not selection_path(root, resref).is_file():
        raise WorkflowError("sélection historique à importer : bootstrap --run")
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
    production_state = current[state_field] if existing_run == run_id and current[state_field] == "verified" else "produced"
    candidate_row[run_field], candidate_row[state_field] = run_id, production_state
    if stage == "spatial" and existing_run != run_id:
        candidate_row["interpolation_run"] = ""
        candidate_row["interpolation_state"] = "not-started"
    payload = csv_bytes(candidate[row["asset_key"]] for row in processing)
    if write:
        authority.commit(root, {"effects/index/processing.csv": payload})
        reservation.unlink(missing_ok=True)
    return {
        "command": "register-run", "write": write, "resref": resref,
        "asset_id": f"effects:bam:{resref}", "stage": stage, "run_id": run_id,
        "run_descriptor": verification["descriptor_path"],
        "run_descriptor_sha256": verification["descriptor_sha256"],
        "production_state": production_state, "release_mutation": False,
    }


def selection_path(root: Path, resref: str) -> Path:
    return root / f"effects/index/selections/{validate_resref(resref)}.json"


def file_evidence(root: Path, path: Path) -> dict[str, Any]:
    return {"path": relative_path(root, path), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def pinned_file(root: Path, path_text: str, digest: str) -> Path:
    path = resolve_relative(root, path_text, "preuve")
    if not SHA256_RE.fullmatch(str(digest).upper()) or not path.is_file() or sha256_file(path) != digest.upper():
        raise WorkflowError(f"preuve absente ou modifiée : {path_text}")
    return path


def pack_binding(root: Path, resref: str, asset: Mapping[str, str], manifest_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    pack = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if pack.get("schema") != "bg2-upscale-effect-animation-runtime-pack-v1" or pack.get("status") != "completed" or pack.get("scale") != 4:
        raise WorkflowError("pack effects incomplet ou incompatible")
    members = pack.get("resources", [pack])
    matches = [m for m in members if m.get("resref") == resref]
    if len(matches) != 1:
        raise WorkflowError("BAM absent ou dupliqué dans le pack")
    resource = matches[0]
    source = resource.get("source", {})
    if str(source.get("source_bam_sha256", "")).upper() != asset["source_sha256"].upper():
        raise WorkflowError("source du pack différente de l'inventaire")
    resource_root = root / f"effects/ressources/{resref}"
    spatial = validate_run_id(source.get("spatial_run", ""))
    verification = verify_run_descriptor(root, resource_root, resref, spatial, stage="spatial")
    if not verification["ok"]:
        raise WorkflowError("spatial du pack invalide : " + "; ".join(verification["errors"]))
    assert_source_matches_inventory(resource_root, asset, verification)
    if verification["descriptor_sha256"] != str(source.get("spatial_run_descriptor_sha256", "")).upper():
        raise WorkflowError("descripteur spatial différent du pack")
    if not any(item.get("role") == "spatial-manifest"
               and item.get("sha256", "").upper() == str(source.get("spatial_manifest_sha256", "")).upper()
               for item in verification["outputs"]):
        raise WorkflowError("sortie spatiale différente du pack")
    temporal = source.get("interpolation_run", "")
    if temporal:
        child = verify_run_descriptor(root, resource_root, resref, temporal, stage="interpolation", spatial_run=spatial)
        if not child["ok"]:
            raise WorkflowError("interpolation du pack invalide : " + "; ".join(child["errors"]))
        verify_parent_binding(root, resource_root, resref, spatial, child)
        if child["descriptor_sha256"] != str(source.get("interpolation_run_descriptor_sha256", "")).upper():
            raise WorkflowError("descripteur interpolation différent du pack")
    for name in ("runtime_geometry", "alpha_policy"):
        if source.get(name):
            pinned_file(root, source[name]["path"], source[name]["sha256"])
    registry = pack.get("registry")
    if registry != "EffectAnimations-X4.registry" or pack.get("registry_version") not in {1, 2, 3}:
        raise WorkflowError("registre effects incompatible")
    registry_path = manifest_path.parent / registry
    if not registry_path.is_file() or sha256_file(registry_path) != str(pack.get("registry_sha256", "")).upper():
        raise WorkflowError("registre runtime modifié")
    return pack, resource


def selection_from_qa(root: Path, resref: str, asset: Mapping[str, str], qa_relative: str) -> dict[str, Any]:
    qa_path = resolve_relative(root, qa_relative, "QA")
    if qa_path.parent != root / f"effects/index/qa-decisions/{resref}":
        raise WorkflowError("décision QA hors du BAM propriétaire")
    qa = json.loads(qa_path.read_text(encoding="utf-8-sig"))
    if (qa.get("schema") != "bg2-upscale-effect-qa-decision-v1" or qa.get("schema_version") != 1
            or qa.get("asset_id") != f"effects:bam:{resref}" or qa.get("resref") != resref
            or qa.get("status") not in {"accepted", "accepted-native"} or not qa.get("decision")):
        raise WorkflowError("décision QA acceptée invalide")
    try:
        if not isinstance(qa.get("decision_date"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", qa["decision_date"]):
            raise ValueError("ISO date required")
        datetime.strptime(qa["decision_date"], "%Y-%m-%d")
    except (KeyError, TypeError, ValueError) as error:
        raise WorkflowError("date QA invalide") from error
    native = qa["status"] == "accepted-native"
    origin = "explicit-user-native-decision" if native else "explicit-user-ingame-qa"
    if qa.get("decision_origin") != origin:
        raise WorkflowError("origine de décision utilisateur explicite requise")
    selected = {"$schema": "../../schemas/effect-selection.schema.json", "schema": SELECTION_SCHEMA,
                "schema_version": 1, "asset_id": asset["asset_key"], "resref": resref,
                "mode": "native" if native else "x4", "decision_date": qa["decision_date"],
                "qa_evidence": file_evidence(root, qa_path), "selected_run": "",
                "source": file_evidence(root, root / asset["extracted_path"])}
    if selected["source"]["sha256"] != asset["source_sha256"].upper():
        raise WorkflowError("source native différente de l'inventaire")
    if native:
        if qa.get("source_bam") != selected["source"]:
            raise WorkflowError("décision native non liée au BAM exact")
        return selected
    run = qa.get("selected_run", {})
    run_id = validate_run_id(run.get("run_id", ""))
    descriptor = root / f"effects/ressources/{resref}/runs/{run_id}/run.json"
    if relative_path(root, descriptor) != run.get("descriptor_path"):
        raise WorkflowError("chemin du run QA divergent")
    pinned_file(root, run["descriptor_path"], run.get("descriptor_sha256", ""))
    evidence = qa.get("runtime_pack", qa.get("installed_candidate", {}))
    manifest = pinned_file(root, evidence.get("manifest_path", ""), evidence.get("manifest_sha256", ""))
    pack, resource = pack_binding(root, resref, asset, manifest)
    source = resource["source"]
    if run_id != (source.get("interpolation_run") or source["spatial_run"]):
        raise WorkflowError("run QA différent de celui du pack")
    if evidence.get("registry_sha256", "").upper() != pack["registry_sha256"].upper():
        raise WorkflowError("registre QA différent du pack")
    selected.update({"selected_run": run_id, "run_descriptor": file_evidence(root, descriptor),
                     "runtime_pack": {"manifest": file_evidence(root, manifest),
                                      "registry": file_evidence(root, manifest.parent / pack["registry"]),
                                      "registry_version": pack["registry_version"]},
                     "contract": {"source": source, "cycles": resource.get("cycles", []),
                                  "timeline": resource.get("timeline"), "frame_count": resource["frame_count"]}})
    # Historical decisions can carry detailed policy evidence; don't drop it.
    for name in ("runtime_geometry", "alpha_policy"):
        if qa.get(name):
            pinned_file(root, qa[name]["path"], qa[name]["sha256"])
            if source.get(name, {}).get("sha256", "").upper() != qa[name]["sha256"].upper():
                raise WorkflowError(f"{name} QA différente du pack")
    return selected


def release_reference(root: Path, current: Mapping[str, str], selection: Mapping[str, Any] | None) -> dict[str, Any]:
    path = root / "releases/BG2-HD-Upscale/manifests/effect-release-candidates.json"
    result = {"recorded_state": current["release_state"], "candidate": current["release_candidate"],
              "matches_current_selection": False}
    if selection and path.is_file():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        result["matches_current_selection"] = any(
            c.get("candidate_id") == current["release_candidate"] and c.get("approval_status") == "approved-for-release"
            and any(r.get("asset_id") == current["asset_key"]
                    and r.get("selected_run") == selection["selected_run"]
                    and r.get("qa_evidence_sha256", "").upper() == selection["qa_evidence"]["sha256"]
                    for r in c.get("resources", [])) for c in data.get("candidates", []))
    return result


@authority.guarded
def accept_asset(root: Path, raw_resref: str, *, qa_evidence: str | None = None,
                 pack_path: str | None = None, decision: str | None = None,
                 decision_date: str | None = None, native: bool = False, write: bool = False) -> dict[str, Any]:
    resref, asset, processing, _ = load_asset(root, raw_resref)
    current = processing_row(processing, resref)
    if asset["source_state"] != "available":
        raise WorkflowError("source absente : aucune acceptation possible")
    changes, immutable = {}, ()
    if qa_evidence:
        if any((pack_path, decision, decision_date, native)):
            raise WorkflowError("QA existante et nouvelle décision ne se combinent pas")
        selection = selection_from_qa(root, resref, asset, qa_evidence)
    else:
        if not decision or not decision.strip() or not decision_date:
            raise WorkflowError("décision utilisateur et date requises")
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision_date):
                raise ValueError("ISO date required")
            datetime.strptime(decision_date, "%Y-%m-%d")
        except ValueError as error:
            raise WorkflowError("date attendue YYYY-MM-DD") from error
        qa = {"schema": "bg2-upscale-effect-qa-decision-v1", "schema_version": 1,
              "asset_id": asset["asset_key"], "resref": resref,
              "status": "accepted-native" if native else "accepted",
              "decision_origin": "explicit-user-native-decision" if native else "explicit-user-ingame-qa",
              "decision_date": decision_date, "decision": decision.strip()}
        if native:
            if pack_path:
                raise WorkflowError("décision native sans pack x4")
            qa["source_bam"] = file_evidence(root, root / asset["extracted_path"])
            if qa["source_bam"]["sha256"] != asset["source_sha256"].upper():
                raise WorkflowError("source native modifiée")
        else:
            if not pack_path:
                raise WorkflowError("pack mono-BAM requis")
            pack_root = resolve_relative(root, pack_path, "pack")
            from compose_effect_runtime_packs import PackError, validate_pack
            try:
                validated = validate_pack(pack_root)
            except PackError as error:
                raise WorkflowError(str(error)) from error
            if validated.resource_count != 1 or validated.resources[0]["resref"] != resref:
                raise WorkflowError("acceptation quotidienne : un pack mono-BAM requis")
            pack, resource = pack_binding(root, resref, asset, pack_root / "manifest.json")
            source = resource["source"]
            run_id = source.get("interpolation_run") or source["spatial_run"]
            descriptor = root / f"effects/ressources/{resref}/runs/{run_id}/run.json"
            qa["selected_run"] = {"run_id": run_id, "descriptor_path": relative_path(root, descriptor),
                                  "descriptor_sha256": sha256_file(descriptor)}
            qa["runtime_pack"] = {"manifest_path": relative_path(root, pack_root / "manifest.json"),
                                  "manifest_sha256": validated.manifest_sha256,
                                  "registry_sha256": pack["registry_sha256"]}
        qa_bytes = json_bytes(qa)
        qa_evidence = f"effects/index/qa-decisions/{resref}/{decision_date}-accepted-{authority.digest(qa_bytes)[:12].lower()}.json"
        changes[qa_evidence], immutable = qa_bytes, (qa_evidence,)
        # Build the current selection without writing a temporary QA file.
        selection = {"$schema": "../../schemas/effect-selection.schema.json", "schema": SELECTION_SCHEMA,
                     "schema_version": 1, "asset_id": asset["asset_key"], "resref": resref,
                     "mode": "native" if native else "x4", "decision_date": decision_date,
                     "qa_evidence": {"path": qa_evidence, "sha256": authority.digest(qa_bytes), "bytes": len(qa_bytes)},
                     "selected_run": "", "source": file_evidence(root, root / asset["extracted_path"])}
        if not native:
            selection.update({"selected_run": run_id, "run_descriptor": file_evidence(root, descriptor),
                              "runtime_pack": {"manifest": file_evidence(root, pack_root / "manifest.json"),
                                               "registry": file_evidence(root, pack_root / pack["registry"]),
                                               "registry_version": pack["registry_version"]},
                              "contract": {"source": source, "cycles": resource.get("cycles", []),
                                           "timeline": resource.get("timeline"), "frame_count": resource["frame_count"]}})
    # Acceptance alone changes neither installation nor release authority.
    current["selected_run"] = selection["selected_run"]
    current["qa_state"] = "native" if selection["mode"] == "native" else "passed"
    current["qa_evidence"] = qa_evidence
    if selection["mode"] == "native":
        for stage in STAGES:
            current[f"{stage}_run"] = ""
            current[f"{stage}_state"] = "not-applicable"
    if selection["mode"] == "x4":
        source = selection["contract"]["source"]
        for stage, field in (("spatial", "spatial_run"), ("interpolation", "interpolation_run")):
            if current[field] and current[field] == source.get(field):
                current[f"{stage}_state"] = "verified"
        if current["spatial_run"] == source["spatial_run"] and not source.get("interpolation_run"):
            current["interpolation_run"] = ""
            current["interpolation_state"] = "not-applicable"
    changes[relative_path(root, selection_path(root, resref))] = json_bytes(selection)
    changes["effects/index/processing.csv"] = csv_bytes(processing)
    if write:
        authority.commit(root, changes, immutable=immutable)
    return {"command": "accept", "resref": resref, "write": write, "mode": selection["mode"],
            "selected_run": selection["selected_run"], "qa_evidence": qa_evidence,
            "selection": relative_path(root, selection_path(root, resref)), "release_mutation": False}


@authority.guarded
def bootstrap(root: Path, write: bool = False) -> dict[str, Any]:
    assets = {r["asset_key"]: r for r in read_csv(root / "effects/index/bam-assets.csv")}
    processing = read_csv(root / "effects/index/processing.csv", PROCESSING_FIELDS)
    changes = {}
    selected = []
    for row in processing:
        if row["qa_state"] not in {"passed", "native"}:
            continue
        asset = assets[row["asset_key"]]
        selection = selection_from_qa(root, asset["resref"], asset, row["qa_evidence"])
        if row["selected_run"] != selection["selected_run"]:
            raise WorkflowError("sélection historique/processing divergents")
        path = selection_path(root, asset["resref"])
        if path.is_file() and json.loads(path.read_text(encoding="utf-8-sig")) != selection:
            raise WorkflowError("bootstrap ne remplace pas une sélection courante")
        changes[relative_path(root, path)] = json_bytes(selection)
        selected.append(asset["resref"])
    # Correct stale pointers only when the existing release authority pins the
    # very same run and QA bytes. No approval, manifest or payload is changed.
    candidate_path = root / "releases/BG2-HD-Upscale/manifests/effect-release-candidates.json"
    corrected = []
    if candidate_path.is_file():
        candidates = json.loads(candidate_path.read_text(encoding="utf-8-sig")).get("candidates", [])
        for row in processing:
            if row["release_state"] != "approved":
                continue
            matches = [c["candidate_id"] for c in candidates if c.get("approval_status") == "approved-for-release"
                       and any(r.get("asset_id") == row["asset_key"] and r.get("selected_run") == row["selected_run"]
                               and r.get("qa_evidence") == row["qa_evidence"]
                               and r.get("qa_evidence_sha256", "").upper() == sha256_file(root / row["qa_evidence"])
                               for r in c.get("resources", []))]
            if len(matches) == 1 and row["release_candidate"] != matches[0]:
                row["release_candidate"] = matches[0]
                corrected.append(row["asset_key"])
    changes["effects/index/processing.csv"] = csv_bytes(processing)
    if write:
        authority.commit(root, changes)
    return {"command": "bootstrap", "write": write, "imported_selections": selected,
            "corrected_local_candidate_references": corrected, "new_qa": False, "release_mutation": False}


@authority.guarded
def status_asset(root: Path, raw_resref: str, *, deep: bool = False) -> dict[str, Any]:
    resref, asset, processing, resource_root = load_asset(root, raw_resref)
    current = processing_row(processing, resref)
    runs = []
    runs_root = resource_root / "runs"
    if runs_root.is_dir():
        for descriptor in sorted(runs_root.glob("*/run.json"), key=lambda path: path.as_posix().casefold()):
            run_id = descriptor.parent.name
            if deep:
                verification = verify_run_descriptor(root, resource_root, resref, run_id)
                runs.append({"run_id": run_id, "ok": verification["ok"], "errors": verification["errors"]})
            else:
                data = json.loads(descriptor.read_text(encoding="utf-8-sig"))
                runs.append({"run_id": run_id, "result": data.get("result", {}), "parents": data.get("provenance", {}).get("parents", [])})
    from effect_tracking import work_item
    selected = json.loads(selection_path(root, resref).read_text(encoding="utf-8-sig")) if selection_path(root, resref).is_file() else None
    return {"command": "status", "resref": resref, "asset": asset, "work": work_item(root, resref),
            "processing": current, "selection": selected, "runs": runs, "deep": deep,
            "release": release_reference(root, current, selected),
            "installation_note": "CSV receipt is recorded history; current game state is not inferred",
            "release_mutation": False}


@authority.guarded
def check_workspace(root: Path, raw_resref: str | None = None) -> dict[str, Any]:
    assets_path, processing_path = authority_paths(root)
    assets, processing = read_csv(assets_path), read_csv(processing_path, PROCESSING_FIELDS)
    requested = validate_resref(raw_resref) if raw_resref else None
    errors: list[str] = []
    checked: list[str] = []
    processing_by_key = {row.get("asset_key", ""): row for row in processing}
    asset_keys = [row.get("asset_key", "") for row in assets]
    if len(asset_keys) != len(set(asset_keys)) or len(processing_by_key) != len(processing):
        errors.append("identité dupliquée dans les autorités")
    if set(asset_keys) != set(processing_by_key):
        errors.append("couverture inventory/processing différente")
    if requested and requested not in {a.get("resref") for a in assets}:
        errors.append(f"asset inconnu : {requested}")
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
        if current.get("asset_directory") != f"effects/ressources/{resref}":
            errors.append(f"{resref}: asset_directory invalide")
        if current.get("spatial_state") not in PRODUCTION_STATES or current.get("interpolation_state") not in PRODUCTION_STATES:
            errors.append(f"{resref}: état de production inconnu")
        if current.get("qa_state") not in {"not-assessed", "passed", "native", "failed", "pending"}:
            errors.append(f"{resref}: état QA inconnu")
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
        try:
            if current.get("qa_state") in {"passed", "native"}:
                path = selection_path(root, resref)
                if not path.is_file():
                    raise WorkflowError("sélection absente : bootstrap --run")
                saved = json.loads(path.read_text(encoding="utf-8-sig"))
                expected = selection_from_qa(root, resref, asset, current["qa_evidence"])
                if saved != expected or current.get("selected_run", "") != expected.get("selected_run", ""):
                    raise WorkflowError("sélection/QA/processing divergents")
                if current["qa_state"] != ("native" if expected["mode"] == "native" else "passed"):
                    raise WorkflowError("mode de sélection différent du statut QA")
            elif current.get("selected_run") or current.get("qa_evidence"):
                raise WorkflowError("sélection sans décision QA acceptée")
        except (WorkflowError, OSError, ValueError, KeyError) as error:
            errors.append(f"{resref}: {error}")
    return {"command": "check", "resref": requested, "ok": not errors, "checked_files": sorted(set(checked)), "errors": errors, "release_mutation": False}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=PROJECT_ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="affiche un asset et ses runs physiques")
    status.add_argument("--resref", required=True)
    status.add_argument("--deep", action="store_true", help="vérifie les hashes des runs de cet asset")
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
    accept = commands.add_parser("accept", help="enregistre la décision utilisateur, sélection et suivi en une transaction")
    accept.add_argument("--resref", required=True)
    accept.add_argument("--qa-evidence", help="décision immuable déjà existante")
    accept.add_argument("--pack", help="pack mono-BAM déjà produit et revu")
    accept.add_argument("--native", action="store_true", help="décision explicite de conserver le BAM natif")
    accept.add_argument("--decision", help="décision visuelle explicite de l'utilisateur, sans l'inférer")
    accept.add_argument("--date", help="date de la décision YYYY-MM-DD")
    accept.add_argument("--run", action="store_true")
    bootstrap_parser = commands.add_parser("bootstrap", help="importe les QA historiques sans en créer")
    bootstrap_parser.add_argument("--run", action="store_true")
    recovery = commands.add_parser("recover", help="termine une transaction interrompue")
    recovery.add_argument("--run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.workspace_root.resolve()
    try:
        if args.command == "status":
            result = status_asset(root, args.resref, deep=args.deep)
        elif args.command == "new-run":
            result = new_run(root, args.resref, args.stage, args.recipe, args.run_id, args.run)
        elif args.command == "register-run":
            result = register_run(root, args.resref, args.stage, args.run_id, args.run)
        elif args.command == "accept":
            result = accept_asset(root, args.resref, qa_evidence=args.qa_evidence, pack_path=args.pack,
                                  decision=args.decision, decision_date=args.date, native=args.native, write=args.run)
        elif args.command == "bootstrap":
            result = bootstrap(root, args.run)
        elif args.command == "recover":
            pending = (root / authority.JOURNAL).is_file()
            if args.run:
                with authority.guard(root, True):
                    pass
            result = {"command": "recover", "pending": pending, "write": args.run}
        else:
            result = check_workspace(root, args.resref)
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"ERROR: {error}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
