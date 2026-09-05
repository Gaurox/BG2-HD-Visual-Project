"""Lightweight, explicit workflow for area-animation runs and in-game QA.

Commands that can write are plan-only unless ``--run`` is supplied.  The
workflow records production/QA selection only; release integration is a
separate decision handled by release tooling.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import uuid
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_animation_authority_lock_module():
    module_path = Path(__file__).with_name("animation_authority_lock.py")
    spec = importlib.util.spec_from_file_location("bg2_animation_authority_lock", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module de verrou animation illisible: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANIMATION_AUTHORITY_LOCK = _load_animation_authority_lock_module()
REGISTRY_REL = Path("animations/index/animation_upscale_registry.csv")
RESOURCES_INDEX_REL = Path("animations/index/ressources.csv")
RESOURCES_REL = Path("animations/ressources")
LEGACY_RUNS_REL = Path("animations/runs")
DECISIONS_REL = Path("animations/index/qa-decisions")
SELECTIONS_REL = Path("animations/index/selections")
AUTHORITY_LOCK_REL = ANIMATION_AUTHORITY_LOCK.AUTHORITY_LOCK_REL
TRANSACTION_ROOT_REL = Path(".tmp/workflow-transactions")
AUTHORITY_JOURNAL_REL = TRANSACTION_ROOT_REL / "animation-authority-active.json"
RELEASE_JOURNAL_REL = TRANSACTION_ROOT_REL / "animation-release-active.json"
AUTHORITY_JOURNAL_SCHEMA = "bg2-animation-authority-transaction-journal-v2"
RUN_RESERVATION_SCHEMA = "bg2-animation-run-reservation-v1"

DECISION_SCHEMA_REF = "../../../schemas/animation-qa-decision.schema.json"
SELECTION_SCHEMA_REF = "../../schemas/animation-selection.schema.json"

REGISTRY_FIELDS = (
    "resref",
    "status",
    "areas",
    "occurrences",
    "frames",
    "max_frame_size_x1",
    "format",
    "selected_run",
    "qa_decision",
    "qa_date",
    "correction_id",
    "notes",
)
DEFAULT_LIST_STATUSES = {
    "non-traité",
    "à-corriger",
    "à-arbitrer",
    "à-compléter",
    "à-valider",
}
FINAL_STATUSES = {
    "completed",
    "validated",
    "validated-installed",
}
RUN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
RESREF_RE = re.compile(r"^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$")
AREA_RE = re.compile(r"^(?:AR|OH)[0-9]{4}$")
SHA256_RE = re.compile(r"^[A-F0-9]{64}$")
NEW_RUN_STAGES = ("spatial", "temporal", "alpha", "rgb", "occurrence", "other")
FORBIDDEN_DATA_PARTS = {
    "archive",
    "archives",
    "backup",
    "backups",
    "capture",
    "captures",
    "override",
    "proto",
    "staging",
    "temp",
    "tmp",
}


class WorkflowError(RuntimeError):
    """A validation failure that must not cause a partial write."""


def _load_animation_paths_module():
    module_path = Path(__file__).with_name("animation_paths.py")
    spec = importlib.util.spec_from_file_location("bg2_animation_paths", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module de chemins animation illisible: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANIMATION_PATHS = _load_animation_paths_module()
_RUNTIME_V2: Any | None = None


def _runtime_v2_module() -> Any:
    global _RUNTIME_V2
    if _RUNTIME_V2 is not None:
        return _RUNTIME_V2
    module_path = Path(__file__).with_name("run_animation_upscale_30fps_v2.py")
    script_directory = str(module_path.parent)
    added = script_directory not in sys.path
    if added:
        sys.path.insert(0, script_directory)
    try:
        spec = importlib.util.spec_from_file_location("bg2_animation_runtime_v2", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"validateur runtime animation illisible: {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _RUNTIME_V2 = module
        return module
    finally:
        if added:
            sys.path.remove(script_directory)


def _validate_runtime_pack(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        manifest = load_json(path / "manifest.json")
        validator = _runtime_v2_module()
        if manifest.get("schema") == "bg2-upscale-area-animation-runtime-pack-v1":
            checked, resources = validator.validate_v1_base_pack(path)
            return checked, [validator.normalise_v1_resource(item) for item in resources]
        if manifest.get("schema") == "bg2-upscale-area-animation-runtime-pack-v2":
            return validator.validate_v2_pack(path)
    except WorkflowError:
        raise
    except (ImportError, KeyError, TypeError, ValueError, RuntimeError, OSError) as error:
        raise WorkflowError(f"pack runtime invalide {path}: {error}") from error
    raise WorkflowError(f"schéma de pack runtime inconnu: {path}")


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object and add a precise path to parse/type failures."""

    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as error:
        raise WorkflowError(f"JSON requis absent: {path}") from error
    except json.JSONDecodeError as error:
        raise WorkflowError(f"JSON invalide: {path}: {error}") from error
    if not isinstance(value, dict):
        raise WorkflowError(f"objet JSON attendu: {path}")
    return value


def sha256(path: Path) -> str:
    """Return an uppercase SHA-256 for a physical file."""

    if not path.is_file():
        raise WorkflowError(f"fichier requis absent: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def repo_path(workspace_root: Path, value: str | Path) -> Path:
    """Resolve a workspace-relative/absolute value and reject path escapes."""

    root = workspace_root.resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise WorkflowError(f"chemin hors workspace interdit: {value}") from error
    return candidate


def relative_path(workspace_root: Path, path: Path) -> str:
    return repo_path(workspace_root, path).relative_to(workspace_root.resolve()).as_posix()


@contextmanager
def _animation_authority_lock(workspace_root: Path):
    """Serialize animation QA authority writes with release promotion reads."""

    try:
        with ANIMATION_AUTHORITY_LOCK.animation_authority_lock(workspace_root):
            yield
    except ANIMATION_AUTHORITY_LOCK.AnimationAuthorityLockError as error:
        raise WorkflowError(str(error)) from error


@contextmanager
def _stable_authority_read(workspace_root: Path):
    """Serialize CLI reads and refuse unrecovered multi-file authority state."""

    with _animation_authority_lock(workspace_root):
        active = [
            relative.as_posix()
            for relative in (AUTHORITY_JOURNAL_REL, RELEASE_JOURNAL_REL)
            if repo_path(workspace_root, relative).exists()
        ]
        if active:
            raise WorkflowError(
                "transaction animation interrompue active; relancer sa commande d'origine: "
                + ", ".join(active)
            )
        yield


def _reject_transient_path(workspace_root: Path, path: Path) -> None:
    relative = repo_path(workspace_root, path).relative_to(workspace_root.resolve())
    forbidden = [part for part in relative.parts if part.casefold() in FORBIDDEN_DATA_PARTS]
    if forbidden or any(part.casefold().endswith(".partial") for part in relative.parts):
        raise WorkflowError(f"chemin temporaire/archive interdit comme autorité: {relative.as_posix()}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_resref(value: str) -> str:
    resref = value.strip().upper()
    if not RESREF_RE.fullmatch(resref):
        raise WorkflowError(f"resref invalide: {value!r}")
    return resref


def validate_area(value: str) -> str:
    area = value.strip().upper()
    if not AREA_RE.fullmatch(area):
        raise WorkflowError(f"zone invalide: {value!r}")
    return area


def validate_iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise WorkflowError(f"date QA invalide (YYYY-MM-DD attendu): {value!r}") from error
    if parsed.isoformat() != value:
        raise WorkflowError(f"date QA non canonique: {value!r}")
    return value


def area_key(value: str) -> tuple[str, int, str]:
    prefix = "".join(character for character in value if not character.isdigit())
    digits = "".join(character for character in value if character.isdigit())
    return prefix, int(digits) if digits else -1, value


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def _row_sha256(row: Mapping[str, str]) -> str:
    payload = json.dumps(
        dict(row), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return _bytes_sha256(payload)


def _read_registry(workspace_root: Path) -> tuple[list[dict[str, str]], list[str]]:
    path = repo_path(workspace_root, REGISTRY_REL)
    if not path.is_file():
        raise WorkflowError(f"registre animations absent: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = list(reader.fieldnames or [])
        raw_rows = list(reader)
    duplicate_fields = sorted(
        {field for field in fieldnames if fieldnames.count(field) > 1}
    )
    if duplicate_fields:
        raise WorkflowError(
            "colonnes registre dupliquées: " + ", ".join(duplicate_fields)
        )
    for index, raw_row in enumerate(raw_rows, start=2):
        if raw_row.get(None):
            raise WorkflowError(f"registre ligne {index}: cellules hors en-tête")
    rows = [
        {key: value or "" for key, value in row.items() if key is not None}
        for row in raw_rows
    ]
    unknown = sorted(set(fieldnames) - set(REGISTRY_FIELDS))
    missing_required = sorted({"resref", "status", "areas"} - set(fieldnames))
    if unknown:
        raise WorkflowError("colonnes registre inconnues; arrêt pour préserver les données: " + ", ".join(unknown))
    if missing_required:
        raise WorkflowError("colonnes registre requises absentes: " + ", ".join(missing_required))
    seen: set[str] = set()
    for row in rows:
        resref = validate_resref(row.get("resref", ""))
        if resref in seen:
            raise WorkflowError(f"registre: doublon interdit pour {resref}")
        seen.add(resref)
        row["resref"] = resref
        for field in REGISTRY_FIELDS:
            row.setdefault(field, "")
    return rows, fieldnames


def _registry_row(workspace_root: Path, resref: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    rows, _ = _read_registry(workspace_root)
    matches = [row for row in rows if row["resref"] == resref]
    if len(matches) != 1:
        raise WorkflowError(f"{resref}: entrée unique absente du registre")
    return matches[0], rows


def _native_source(
    workspace_root: Path,
    resref: str,
    registry_row: Mapping[str, str],
) -> dict[str, Any]:
    inventory_path = repo_path(workspace_root, RESOURCES_INDEX_REL)
    if not inventory_path.is_file():
        raise WorkflowError(f"inventaire des extractions absent: {inventory_path}")
    with inventory_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = [
            {key: value or "" for key, value in row.items() if key is not None}
            for row in csv.DictReader(stream)
        ]
    matches = [row for row in rows if str(row.get("bam_resref", "")).upper() == resref]
    if len(matches) != 1:
        raise WorkflowError(f"{resref}: extraction unique absente de ressources.csv")
    inventory_row = matches[0]
    expected_relative = Path("ressources") / resref
    if Path(str(inventory_row.get("relative_path", ""))) != expected_relative:
        raise WorkflowError(f"{resref}: chemin d'extraction non canonique dans ressources.csv")
    source_path = repo_path(workspace_root, Path("animations") / expected_relative / "source.bam")
    source_hash = sha256(source_path)
    declared_hash = str(inventory_row.get("sha256", "")).strip().upper()
    if source_hash != declared_hash:
        raise WorkflowError(f"{resref}: hash de source.bam différent de ressources.csv")
    for registry_key, inventory_key in (("format", "format"), ("frames", "frames")):
        if str(registry_row.get(registry_key, "")) != str(inventory_row.get(inventory_key, "")):
            raise WorkflowError(
                f"{resref}: {registry_key} différent entre les deux inventaires"
            )
    try:
        frame_count = int(inventory_row.get("frames", 0))
    except (TypeError, ValueError) as error:
        raise WorkflowError(f"{resref}: nombre de frames natif invalide") from error
    if frame_count < 1:
        raise WorkflowError(f"{resref}: nombre de frames natif invalide")
    source_bytes = source_path.stat().st_size
    source_format = str(inventory_row.get("format", "")).strip()
    if source_bytes < 1 or not source_format:
        raise WorkflowError(f"{resref}: source native vide ou format absent")
    return {
        "path": relative_path(workspace_root, source_path),
        "sha256": source_hash,
        "bytes": source_bytes,
        "format": source_format,
        "frames": frame_count,
        "inventory_path": RESOURCES_INDEX_REL.as_posix(),
        "inventory_row_sha256": _row_sha256(inventory_row),
    }


def _render_registry(rows: Sequence[Mapping[str, str]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=REGISTRY_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in sorted(rows, key=lambda item: item["resref"].upper()):
        writer.writerow({field: row.get(field, "") for field in REGISTRY_FIELDS})
    return output.getvalue().encode("utf-8")


def _resolve_manifest_reference(workspace_root: Path, owner: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return repo_path(workspace_root, raw)
    normalized = value.replace("\\", "/")
    if normalized.startswith(
        (
            "animations/",
            "config/",
            "docs/",
            "engine/",
            "maps/",
            "pipeline/",
            "releases/",
            "sprite/",
        )
    ):
        return repo_path(workspace_root, raw)
    owner_candidate = repo_path(workspace_root, owner.parent / raw)
    if normalized.startswith(("./", "../")) or owner_candidate.exists():
        return owner_candidate
    root_candidate = repo_path(workspace_root, raw)
    if root_candidate.exists():
        return root_candidate
    return owner_candidate


def _resolve_run_input(workspace_root: Path, value: str | Path, resref: str) -> Path:
    reference = Path(value)
    is_simple_id = reference.parent == Path(".") and not reference.is_absolute()
    if not is_simple_id:
        return repo_path(workspace_root, reference)
    try:
        return ANIMATION_PATHS.resolve_existing_run(
            str(value),
            [resref],
            animations_root=repo_path(workspace_root, "animations"),
        )
    except RuntimeError as error:
        raise WorkflowError(str(error)) from error


def _manifest_for_path(path: Path) -> Path:
    if path.is_file():
        return path
    manifest = path / "manifest.json"
    if not manifest.is_file():
        raise WorkflowError(f"manifest.json absent: {path}")
    return manifest


def _artifact(workspace_root: Path, path: Path) -> tuple[dict[str, str], dict[str, Any], Path]:
    resolved_path = repo_path(workspace_root, path)
    _reject_transient_path(workspace_root, resolved_path)
    manifest_path = _manifest_for_path(resolved_path)
    manifest = load_json(manifest_path)
    schema = str(manifest.get("schema") or "").strip()
    status = str(manifest.get("status") or "").strip()
    if not schema or not status:
        raise WorkflowError(f"schema/status absents: {manifest_path}")
    artifact: dict[str, str] = {
        "path": relative_path(workspace_root, manifest_path.parent),
        "manifest_path": relative_path(workspace_root, manifest_path),
        "manifest_sha256": sha256(manifest_path),
        "schema": schema,
        "status": status,
    }
    if manifest_path.name != "manifest.json":
        artifact["descriptor_path"] = artifact["manifest_path"]
    return artifact, manifest, manifest_path


def _manifest_resrefs(manifest: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str) and RESREF_RE.fullmatch(value.strip().upper()):
            values.add(value.strip().upper())
        elif isinstance(value, Mapping):
            for key in ("asset", "resref", "bam_resref", "resource_resref"):
                if key in value:
                    add(value[key])

    for key in ("asset", "resref", "bam_resref"):
        add(manifest.get(key))
    for key in ("resources", "timed_resources", "resrefs", "targets", "requested_resrefs", "resolved_resrefs"):
        sequence = manifest.get(key)
        if isinstance(sequence, list):
            for item in sequence:
                add(item)
    request = manifest.get("request")
    if isinstance(request, Mapping):
        for key in ("resref", "resrefs", "targets", "requested_resrefs", "resolved_resrefs"):
            sequence = request.get(key)
            if isinstance(sequence, list):
                for item in sequence:
                    add(item)
            else:
                add(sequence)
    return values


def _verify_declared_hash(path: Path, declared: Any, label: str) -> None:
    value = str(declared or "").strip().upper()
    if not SHA256_RE.fullmatch(value):
        raise WorkflowError(f"{label}: SHA-256 déclaré absent ou invalide")
    actual = sha256(path)
    if value != actual:
        raise WorkflowError(f"{label}: SHA-256 différent (déclaré {value}, disque {actual})")


def _verify_embedded_pack(workspace_root: Path, manifest: Mapping[str, Any], manifest_path: Path) -> None:
    pack_value = manifest.get("pack")
    pack_hash = manifest.get("pack_manifest_sha256")
    if pack_value is None and pack_hash is None:
        return
    if not isinstance(pack_value, str) or not pack_value.strip() or not pack_hash:
        raise WorkflowError(f"{manifest_path}: pack/pack_manifest_sha256 incomplets")
    pack_path = _resolve_manifest_reference(workspace_root, manifest_path, pack_value)
    pack_manifest = _manifest_for_path(pack_path)
    _verify_declared_hash(pack_manifest, pack_hash, f"{manifest_path}: pack")


def _collect_lineage(
    workspace_root: Path,
    final_manifest: Mapping[str, Any],
    final_manifest_path: Path,
) -> dict[str, list[dict[str, str]]]:
    source_runs: list[dict[str, str]] = []
    source_packs: list[dict[str, str]] = []
    visited_runs: set[str] = set()
    visited_packs: set[str] = set()

    def add_reference(
        owner_manifest: Mapping[str, Any],
        owner_path: Path,
        path_key: str,
        hash_key: str,
        destination: list[dict[str, str]],
        visited: set[str],
        recurse: bool,
    ) -> None:
        raw_path = owner_manifest.get(path_key)
        raw_hash = owner_manifest.get(hash_key)
        if raw_path is None and raw_hash is None:
            return
        if not isinstance(raw_path, str) or not raw_path.strip() or not raw_hash:
            raise WorkflowError(f"{owner_path}: {path_key}/{hash_key} incomplets")
        referenced_path = _resolve_manifest_reference(workspace_root, owner_path, raw_path)
        artifact, referenced_manifest, referenced_manifest_path = _artifact(workspace_root, referenced_path)
        _verify_declared_hash(referenced_manifest_path, raw_hash, f"{owner_path}: {path_key}")
        identity = artifact["manifest_path"]
        if identity in visited:
            return
        visited.add(identity)
        destination.append(artifact)
        if recurse:
            walk(referenced_manifest, referenced_manifest_path, include_pack=True)

    def walk(
        manifest: Mapping[str, Any],
        manifest_path: Path,
        *,
        include_pack: bool,
    ) -> None:
        add_reference(
            manifest,
            manifest_path,
            "source_run",
            "source_run_manifest_sha256",
            source_runs,
            visited_runs,
            True,
        )
        add_reference(
            manifest,
            manifest_path,
            "source_temporal_run",
            "source_temporal_run_manifest_sha256",
            source_runs,
            visited_runs,
            True,
        )
        add_reference(
            manifest,
            manifest_path,
            "base_pack",
            "base_pack_manifest_sha256",
            source_packs,
            visited_packs,
            False,
        )
        add_reference(
            manifest,
            manifest_path,
            "source_pack",
            "source_pack_manifest_sha256",
            source_packs,
            visited_packs,
            False,
        )
        add_reference(
            manifest,
            manifest_path,
            "source_split_root",
            "source_manifest_sha256",
            source_packs,
            visited_packs,
            False,
        )
        if include_pack:
            add_reference(
                manifest,
                manifest_path,
                "pack",
                "pack_manifest_sha256",
                source_packs,
                visited_packs,
                False,
            )

    walk(final_manifest, final_manifest_path, include_pack=False)
    source_runs.sort(key=lambda item: item["manifest_path"])
    source_packs.sort(key=lambda item: item["manifest_path"])
    return {"source_runs": source_runs, "source_packs": source_packs}


def _verify_output_pack(
    workspace_root: Path,
    final_manifest: Mapping[str, Any],
    final_manifest_path: Path,
    qa_pack: Mapping[str, Any],
) -> bool:
    """Bind legacy split-root correction runs to the exact pack tested in game."""

    raw_path = final_manifest.get("output_split_root")
    raw_hash = final_manifest.get("output_manifest_sha256")
    if raw_path is None and raw_hash is None:
        return False
    if not isinstance(raw_path, str) or not raw_path.strip() or not raw_hash:
        raise WorkflowError(
            f"{final_manifest_path}: output_split_root/output_manifest_sha256 incomplets"
        )
    output_path = _resolve_manifest_reference(
        workspace_root, final_manifest_path, raw_path
    )
    output_manifest = _manifest_for_path(output_path)
    _verify_declared_hash(
        output_manifest,
        raw_hash,
        f"{final_manifest_path}: output_split_root",
    )
    if relative_path(workspace_root, output_path) != qa_pack.get("path"):
        raise WorkflowError(
            f"{final_manifest_path}: le pack QA n'est pas la sortie déclarée du run final"
        )
    if sha256(output_manifest) != str(qa_pack.get("manifest_sha256") or "").upper():
        raise WorkflowError(
            f"{final_manifest_path}: hash du pack QA différent de la sortie du run final"
        )
    return True


def _resource_group(
    resources: Sequence[Mapping[str, Any]], resref: str
) -> list[dict[str, Any]]:
    matching = [
        deepcopy(dict(item))
        for item in resources
        if isinstance(item, Mapping)
        and str(item.get("resref") or "").strip().upper() == resref
    ]
    if not matching:
        raise WorkflowError(f"ressource {resref} absente du pack runtime")
    try:
        return sorted(
            matching,
            key=lambda item: (
                int(item.get("variant_index", 0)),
                json.dumps(item.get("position", []), sort_keys=True),
                json.dumps(item, ensure_ascii=False, sort_keys=True),
            ),
        )
    except (TypeError, ValueError) as error:
        raise WorkflowError(f"ressource {resref}: variante/position invalide") from error


def _verify_pack_binding(
    workspace_root: Path,
    final_manifest: Mapping[str, Any],
    final_manifest_path: Path,
    qa_pack: Mapping[str, Any],
    resref: str,
) -> None:
    """Prove that every tested area contains the exact selected run output."""

    if _verify_output_pack(
        workspace_root,
        final_manifest,
        final_manifest_path,
        qa_pack,
    ):
        return
    pack_value = final_manifest.get("pack")
    pack_hash = final_manifest.get("pack_manifest_sha256")
    if not isinstance(pack_value, str) or not pack_value.strip() or not pack_hash:
        raise WorkflowError(
            f"{final_manifest_path}: filiation run final -> pack QA non démontrable"
        )
    runtime_path = _resolve_manifest_reference(
        workspace_root,
        final_manifest_path,
        pack_value,
    )
    runtime_manifest_path = _manifest_for_path(runtime_path)
    _verify_declared_hash(
        runtime_manifest_path,
        pack_hash,
        f"{final_manifest_path}: pack final",
    )
    _, runtime_resources = _validate_runtime_pack(runtime_manifest_path.parent)
    expected_resources = _resource_group(runtime_resources, resref)
    for area in qa_pack.get("areas", []):
        if not isinstance(area, Mapping):
            raise WorkflowError("entrée de zone QA invalide")
        area_manifest_path = repo_path(
            workspace_root, str(area.get("manifest_path") or "")
        )
        _, area_resources = _validate_runtime_pack(area_manifest_path.parent)
        if _resource_group(area_resources, resref) != expected_resources:
            raise WorkflowError(
                f"pack QA {area.get('area')}: sortie {resref} différente du run final"
            )


def _source_pack(
    workspace_root: Path,
    pack_path: Path,
    resref: str,
    tested_areas: Sequence[str],
) -> dict[str, Any]:
    relative_pack = repo_path(workspace_root, pack_path).relative_to(workspace_root.resolve())
    if tuple(part.casefold() for part in relative_pack.parts[:2]) != (
        "animations",
        "packs-par-zone",
    ):
        raise WorkflowError(
            "pack QA final attendu sous animations/packs-par-zone/: "
            + relative_pack.as_posix()
        )
    root_artifact, manifest, manifest_path = _artifact(workspace_root, pack_path)
    if manifest.get("schema") != "bg2-upscale-area-animation-pack-index-v1":
        raise WorkflowError(f"pack QA non découpé par zone: {manifest_path}")
    if manifest.get("status") != "completed":
        raise WorkflowError(f"pack QA incomplet: {manifest_path}")
    entries = manifest.get("areas")
    if not isinstance(entries, list):
        raise WorkflowError(f"pack QA sans zones: {manifest_path}")
    by_area: dict[str, Mapping[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowError(f"entrée de zone invalide: {manifest_path}")
        area = validate_area(str(entry.get("area_id") or ""))
        if area in by_area:
            raise WorkflowError(f"pack QA: zone dupliquée {area}")
        by_area[area] = entry

    area_records: list[dict[str, Any]] = []
    for area in sorted(set(tested_areas), key=area_key):
        entry = by_area.get(area)
        if entry is None:
            raise WorkflowError(f"pack QA: zone {area} absente")
        directory = entry.get("directory")
        if not isinstance(directory, str) or not directory.strip():
            raise WorkflowError(f"pack QA: répertoire absent pour {area}")
        area_path = repo_path(workspace_root, manifest_path.parent / directory)
        try:
            area_path.relative_to(manifest_path.parent.resolve())
        except ValueError as error:
            raise WorkflowError(f"pack QA {area}: répertoire hors du pack racine") from error
        area_artifact, _, area_manifest_path = _artifact(workspace_root, area_path)
        area_manifest, resources = _validate_runtime_pack(area_manifest_path.parent)
        if area_manifest.get("schema") != "bg2-upscale-area-animation-runtime-pack-v2":
            raise WorkflowError(f"pack QA {area}: schéma runtime inattendu")
        if area_manifest.get("runtime_budget_enforced", True) is not True:
            raise WorkflowError(f"pack QA {area}: budget runtime non appliqué")
        if area_manifest.get("authoring_pack_for_area_split") is True:
            raise WorkflowError(f"pack QA {area}: pack d'authoring non installable")
        try:
            registry_version = int(area_manifest.get("registry_version", 0))
            runtime_contract = area_manifest.get("runtime_contract")
            contract_version = (
                int(runtime_contract.get("registry_version", 0))
                if isinstance(runtime_contract, Mapping)
                else 0
            )
        except (TypeError, ValueError) as error:
            raise WorkflowError(f"pack QA {area}: contrat runtime invalide") from error
        if (
            not isinstance(runtime_contract, Mapping)
            or runtime_contract.get("feature") != "TimedTimeline"
            or contract_version != registry_version
        ):
            raise WorkflowError(f"pack QA {area}: contrat runtime incohérent")
        try:
            actual_raw_bytes = sum(
                int(asset["bytes"])
                for resource in resources
                for asset in resource["assets"]
            )
            declared_raw_bytes = int(area_manifest.get("raw_bytes", -1))
        except (KeyError, TypeError, ValueError) as error:
            raise WorkflowError(f"pack QA {area}: raw_bytes invalide") from error
        if declared_raw_bytes != actual_raw_bytes:
            raise WorkflowError(f"pack QA {area}: raw_bytes incohérent")
        if str(area_manifest.get("area_id") or "").upper() != area:
            raise WorkflowError(f"pack QA {area}: area_id incohérent")
        _verify_declared_hash(area_manifest_path, entry.get("manifest_sha256"), f"pack QA {area}")
        registry_hash = str(area_manifest.get("registry_sha256") or "").strip().upper()
        entry_registry_hash = str(entry.get("registry_sha256") or registry_hash).strip().upper()
        if entry_registry_hash != registry_hash:
            raise WorkflowError(f"pack QA {area}: registry_sha256 racine/zone différent")
        occurrences = sum(
            1
            for item in resources
            if isinstance(item, Mapping) and str(item.get("resref") or "").strip().upper() == resref
        )
        if occurrences < 1:
            raise WorkflowError(f"pack QA {area}: {resref} absent")
        area_records.append(
            {
                "area": area,
                "path": area_artifact["path"],
                "manifest_path": area_artifact["manifest_path"],
                "manifest_sha256": area_artifact["manifest_sha256"],
                "registry_sha256": registry_hash,
                "resource_entries": occurrences,
            }
        )
    return {
        "path": root_artifact["path"],
        "manifest_path": root_artifact["manifest_path"],
        "manifest_sha256": root_artifact["manifest_sha256"],
        "schema": root_artifact["schema"],
        "status": root_artifact["status"],
        "areas": area_records,
    }


def _semantic_without(value: Mapping[str, Any], ignored_key: str) -> dict[str, Any]:
    result = deepcopy(dict(value))
    result.pop(ignored_key, None)
    return result


def _prepare_immutable(path: Path, candidate: dict[str, Any], volatile_key: str) -> tuple[bytes, bool]:
    candidate_bytes = _json_bytes(candidate)
    if not path.exists():
        return candidate_bytes, True
    existing = load_json(path)
    if _semantic_without(existing, volatile_key) != _semantic_without(candidate, volatile_key):
        raise WorkflowError(f"preuve immuable déjà présente avec un contenu différent: {path}")
    return path.read_bytes(), False


def _prepare_mutable(path: Path, candidate: dict[str, Any], volatile_key: str) -> tuple[bytes, bool]:
    candidate_bytes = _json_bytes(candidate)
    if not path.exists():
        return candidate_bytes, True
    existing = load_json(path)
    if _semantic_without(existing, volatile_key) == _semantic_without(candidate, volatile_key):
        return path.read_bytes(), False
    return candidate_bytes, True


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    try:
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _is_authority_target(workspace_root: Path, path: Path) -> bool:
    relative = repo_path(workspace_root, path).relative_to(workspace_root.resolve())
    if relative == REGISTRY_REL:
        return True
    if relative.parent == SELECTIONS_REL and relative.suffix == ".json":
        try:
            return validate_resref(relative.stem) == relative.stem
        except WorkflowError:
            return False
    if (
        len(relative.parts) == len(DECISIONS_REL.parts) + 2
        and Path(*relative.parts[: len(DECISIONS_REL.parts)]) == DECISIONS_REL
        and relative.suffix == ".json"
    ):
        try:
            resref = validate_resref(relative.parts[-2])
        except WorkflowError:
            return False
        decision_id = relative.stem
        return (
            resref == relative.parts[-2]
            and bool(RUN_ID_RE.fullmatch(decision_id))
            and not decision_id.casefold().endswith(".partial")
        )
    return False


def _reject_authority_leaf_link(workspace_root: Path, value: str | Path) -> None:
    lexical = Path(value)
    if not lexical.is_absolute():
        lexical = workspace_root.resolve() / lexical
    is_junction = getattr(lexical, "is_junction", lambda: False)
    if lexical.is_symlink() or is_junction():
        raise WorkflowError(f"cible d'autorité lien/reparse interdite: {lexical}")


def _transaction_backup_root(workspace_root: Path, value: str | Path) -> Path:
    transaction_root = repo_path(workspace_root, TRANSACTION_ROOT_REL)
    backup_root = repo_path(workspace_root, value)
    if (
        backup_root.parent != transaction_root
        or not backup_root.name.startswith("animation-authority-")
    ):
        raise WorkflowError(f"racine de sauvegarde transaction invalide: {backup_root}")
    return backup_root


def _remove_transaction_backup(workspace_root: Path, backup_root: Path) -> None:
    checked = _transaction_backup_root(workspace_root, backup_root)
    if checked.is_dir():
        shutil.rmtree(checked)


def _recover_authority_transaction(workspace_root: Path) -> list[str]:
    """Restore every target from the durable journal; keep evidence on any failure."""

    journal_path = repo_path(workspace_root, AUTHORITY_JOURNAL_REL)
    if not journal_path.is_file():
        return []
    journal = load_json(journal_path)
    if journal.get("schema") != AUTHORITY_JOURNAL_SCHEMA:
        raise WorkflowError(f"journal de transaction animation inconnu: {journal_path}")
    backup_root = _transaction_backup_root(
        workspace_root, str(journal.get("backup_root") or "")
    )
    entries = journal.get("entries")
    if not isinstance(entries, list) or not entries:
        raise WorkflowError(f"journal de transaction animation vide: {journal_path}")

    prepared: list[tuple[Path, bool, Path | None]] = []
    seen: set[Path] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowError(f"entrée de journal animation invalide: {journal_path}")
        target_value = str(entry.get("target") or "")
        _reject_authority_leaf_link(workspace_root, target_value)
        target = repo_path(workspace_root, target_value)
        if not _is_authority_target(workspace_root, target) or target in seen:
            raise WorkflowError(f"cible de journal animation invalide/dupliquée: {target}")
        seen.add(target)
        existed = entry.get("existed")
        if not isinstance(existed, bool):
            raise WorkflowError(f"état de sauvegarde invalide pour {target}")
        published_hash = str(entry.get("published_sha256") or "").strip().upper()
        if not SHA256_RE.fullmatch(published_hash):
            raise WorkflowError(f"hash publié invalide pour {target}")
        backup: Path | None = None
        backup_hash: str | None = None
        if existed:
            backup = repo_path(workspace_root, str(entry.get("backup") or ""))
            if backup.parent != backup_root or not backup.is_file():
                raise WorkflowError(f"sauvegarde absente ou hors transaction: {backup}")
            backup_hash = str(entry.get("backup_sha256") or "").strip().upper()
            if not SHA256_RE.fullmatch(backup_hash) or sha256(backup) != backup_hash:
                raise WorkflowError(f"hash de sauvegarde invalide: {backup}")
        if target.exists() and not target.is_file():
            raise WorkflowError(f"cible de transaction non fichier: {target}")
        if target.is_file():
            current_hash = sha256(target)
            allowed_hashes = {published_hash}
            if backup_hash is not None:
                allowed_hashes.add(backup_hash)
            if current_hash not in allowed_hashes:
                raise WorkflowError(
                    f"cible modifiée depuis l'interruption; récupération refusée: {target}"
                )
        elif existed:
            raise WorkflowError(
                f"cible supprimée depuis l'interruption; récupération refusée: {target}"
            )
        prepared.append((target, existed, backup))

    restored: list[str] = []
    failures: list[str] = []
    for target, existed, backup in reversed(prepared):
        try:
            if existed:
                if backup is None:
                    raise WorkflowError(f"sauvegarde absente pour {target}")
                _write_atomic(target, backup.read_bytes())
            else:
                target.unlink(missing_ok=True)
            restored.append(relative_path(workspace_root, target))
        except Exception as error:
            failures.append(f"{target}: {error}")
    if failures:
        raise WorkflowError(
            "récupération de transaction animation incomplète; journal conservé: "
            + " | ".join(failures)
        )
    journal_path.unlink(missing_ok=True)
    _remove_transaction_backup(workspace_root, backup_root)
    return restored


def _write_transaction(workspace_root: Path, files: Mapping[Path, bytes]) -> None:
    """Publish authority bytes with durable backups and full rollback."""

    if not files:
        return
    normalized: dict[Path, bytes] = {}
    for raw_path, content in files.items():
        _reject_authority_leaf_link(workspace_root, raw_path)
        path = repo_path(workspace_root, raw_path)
        if not _is_authority_target(workspace_root, path):
            raise WorkflowError(f"cible hors autorités animation: {path}")
        if path.exists() and not path.is_file():
            raise WorkflowError(f"cible transactionnelle non fichier: {path}")
        if not isinstance(content, bytes):
            raise WorkflowError(f"contenu transactionnel non binaire: {path}")
        if path in normalized:
            raise WorkflowError(f"cible transactionnelle dupliquée: {path}")
        normalized[path] = content
    changed = {
        path: content
        for path, content in normalized.items()
        if not path.is_file() or path.read_bytes() != content
    }
    if not changed:
        return

    journal_path = repo_path(workspace_root, AUTHORITY_JOURNAL_REL)
    if journal_path.exists():
        raise WorkflowError(
            f"journal actif non récupéré avant écriture: {AUTHORITY_JOURNAL_REL.as_posix()}"
        )
    transaction_root = repo_path(workspace_root, TRANSACTION_ROOT_REL)
    transaction_root.mkdir(parents=True, exist_ok=True)
    backup_root = transaction_root / f"animation-authority-{uuid.uuid4().hex}"
    backup_root.mkdir()
    entries: list[dict[str, Any]] = []
    try:
        for index, path in enumerate(changed):
            original = path.read_bytes() if path.is_file() else None
            entry: dict[str, Any] = {
                "target": relative_path(workspace_root, path),
                "existed": original is not None,
                "published_sha256": _bytes_sha256(changed[path]),
            }
            if original is not None:
                backup = backup_root / f"{index:03d}.bin"
                _write_atomic(backup, original)
                entry["backup"] = relative_path(workspace_root, backup)
                entry["backup_sha256"] = _bytes_sha256(original)
            entries.append(entry)
        _write_atomic(
            journal_path,
            _json_bytes(
                {
                    "schema": AUTHORITY_JOURNAL_SCHEMA,
                    "backup_root": relative_path(workspace_root, backup_root),
                    "entries": entries,
                }
            ),
        )
    except Exception as error:
        if not journal_path.is_file():
            _remove_transaction_backup(workspace_root, backup_root)
        raise WorkflowError(f"préparation de transaction animation impossible: {error}") from error

    try:
        for path, content in changed.items():
            _write_atomic(path, content)
    except Exception as publication_error:
        try:
            _recover_authority_transaction(workspace_root)
        except WorkflowError as rollback_error:
            raise WorkflowError(
                f"transaction animation échouée ({publication_error}); {rollback_error}; "
                f"relancer finalize pour récupérer {AUTHORITY_JOURNAL_REL.as_posix()}"
            ) from publication_error
        raise WorkflowError(
            f"transaction animation échouée; rollback complet: {publication_error}"
        ) from publication_error

    journal_path.unlink(missing_ok=True)
    _remove_transaction_backup(workspace_root, backup_root)


def list_assets(
    workspace_root: Path,
    statuses: Iterable[str] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    rows, _ = _read_registry(workspace_root)
    requested = {value.strip() for value in statuses or DEFAULT_LIST_STATUSES}
    assets = [
        {
            "resref": row["resref"],
            "status": row["status"],
            "areas": [area for area in row["areas"].split(";") if area],
            "frames": row["frames"],
            "max_frame_size_x1": row["max_frame_size_x1"],
        }
        for row in rows
        if row["status"] in requested
    ]
    assets.sort(key=lambda item: item["resref"])
    if limit is not None:
        assets = assets[:limit]
    return {"command": "list", "statuses": sorted(requested), "count": len(assets), "assets": assets}


def _discover_runs(workspace_root: Path, resref: str) -> list[dict[str, str]]:
    candidates: list[Path] = []
    animations_root = repo_path(workspace_root, "animations")
    run_roots = (
        ANIMATION_PATHS.default_run_root([resref], animations_root=animations_root),
        animations_root / "batches",
        repo_path(workspace_root, LEGACY_RUNS_REL),
    )
    for run_root in run_roots:
        if not run_root.is_dir():
            continue
        for manifest_path in run_root.glob("*/manifest.json"):
            try:
                if resref in _manifest_resrefs(load_json(manifest_path)):
                    candidates.append(manifest_path.parent)
            except WorkflowError:
                continue
    runs: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in candidates:
        artifact, _, _ = _artifact(workspace_root, path)
        if artifact["manifest_path"] not in seen:
            seen.add(artifact["manifest_path"])
            runs.append(artifact)
    return sorted(runs, key=lambda item: item["path"])


def status_asset(workspace_root: Path, raw_resref: str) -> dict[str, Any]:
    resref = validate_resref(raw_resref)
    row, _ = _registry_row(workspace_root, resref)
    decision_root = repo_path(workspace_root, DECISIONS_REL / resref)
    decisions = []
    if decision_root.is_dir():
        for path in sorted(decision_root.glob("*.json")):
            record = load_json(path)
            decisions.append(
                {
                    "path": relative_path(workspace_root, path),
                    "decision_id": record.get("decision_id"),
                    "status": record.get("status"),
                    "decision_date": record.get("decision_date"),
                }
            )
    selection_path = repo_path(workspace_root, SELECTIONS_REL / f"{resref}.json")
    tracked_candidates = sorted(decision_root.glob("*.json")) if decision_root.is_dir() else []
    tracked_candidates.append(selection_path)
    return {
        "command": "status",
        "resref": resref,
        "registry": row,
        "runs": _discover_runs(workspace_root, resref),
        "decisions": decisions,
        "selection": load_json(selection_path) if selection_path.is_file() else None,
        "tracked_files": [
            relative_path(workspace_root, path)
            for path in tracked_candidates
            if path.is_file()
        ],
        "release_mutation": False,
    }


def _run_reservation_path(resource_root: Path, run_id: str) -> Path:
    """Keep the claim outside the run leaf so every producer can create it normally."""

    return resource_root / f".{run_id}.reservation.json"


def _path_claimed(path: Path) -> bool:
    is_junction = getattr(path, "is_junction", lambda: False)
    return path.exists() or path.is_symlink() or is_junction()


def _run_candidate(
    workspace_root: Path,
    resource_root: Path,
    resref: str,
    run_id: str,
) -> tuple[Path, Path, Path | None]:
    """Resolve one ID and report the physical run/partial/reservation occupying it."""

    try:
        destination = ANIMATION_PATHS.resolve_run_destination(
            run_id,
            [resref],
            animations_root=repo_path(workspace_root, "animations"),
        )
    except RuntimeError as error:
        raise WorkflowError(str(error)) from error
    run_path = repo_path(workspace_root, destination)
    partial_path = run_path.with_name(run_path.name + ".partial")
    reservation_path = _run_reservation_path(resource_root, run_id)
    occupied = next(
        (path for path in (run_path, partial_path, reservation_path) if _path_claimed(path)),
        None,
    )
    return run_path, reservation_path, occupied


def _automatic_run_id(
    workspace_root: Path,
    resource_root: Path,
    resref: str,
    stage: str,
    recipe: str,
    timestamp: str,
) -> tuple[str, Path, Path]:
    """Choose a bounded ID, adding a deterministic suffix if the instant already exists."""

    prefix = f"{resref.lower()}-{stage}-"
    for ordinal in range(1, 10_001):
        suffix = f"-{timestamp}" + ("" if ordinal == 1 else f"-{ordinal}")
        available = 128 - len(prefix) - len(suffix)
        if available < 1:
            raise WorkflowError("stage/horodatage trop longs pour construire un run-id")
        candidate = f"{prefix}{recipe[:available]}{suffix}"
        if not RUN_ID_RE.fullmatch(candidate):
            raise WorkflowError(f"run-id automatique invalide: {candidate!r}")
        run_path, reservation_path, occupied = _run_candidate(
            workspace_root, resource_root, resref, candidate)
        if occupied is None:
            return candidate, run_path, reservation_path
    raise WorkflowError("impossible de choisir un run-id libre après 10000 tentatives")


def _write_run_reservation(path: Path, payload: Mapping[str, Any]) -> bytes:
    """Create one durable claim with O_EXCL; never replace an existing reservation."""

    content = _json_bytes(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(path, flags, 0o644)
        created = True
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = None
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as error:
        raise WorkflowError(f"run-id déjà réservé: {path}") from error
    except OSError as error:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise WorkflowError(f"écriture de la réservation impossible: {path}: {error}") from error
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        if created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return content


def _remove_own_run_reservation(path: Path, content: bytes) -> None:
    """Remove only the exact claim created by this invocation."""

    try:
        if path.is_file() and path.read_bytes() == content:
            path.unlink()
    except OSError:
        pass


def _reservation_for_run(
    workspace_root: Path,
    resource_root: Path,
    resref: str,
    run_path: Path,
) -> tuple[Path, bytes] | None:
    """Return a validated claim for a canonical mono-asset run, if one exists."""

    canonical_parent = repo_path(workspace_root, resource_root / "runs")
    reservation_path = _run_reservation_path(resource_root, run_path.name)
    if run_path.resolve().parent != canonical_parent:
        if _path_claimed(reservation_path):
            raise WorkflowError(
                "run final différent de la destination réservée: "
                f"{run_path} / {reservation_path}"
            )
        return None
    is_junction = getattr(reservation_path, "is_junction", lambda: False)
    if not reservation_path.exists():
        if reservation_path.is_symlink() or is_junction():
            raise WorkflowError(f"marqueur de réservation invalide: {reservation_path}")
        return None
    if reservation_path.is_symlink() or is_junction() or not reservation_path.is_file():
        raise WorkflowError(f"marqueur de réservation invalide: {reservation_path}")
    content = reservation_path.read_bytes()
    record = load_json(reservation_path)
    expected = {
        "schema": RUN_RESERVATION_SCHEMA,
        "status": "reserved",
        "resref": resref,
        "run_id": run_path.name,
        "destination": relative_path(workspace_root, run_path),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            raise WorkflowError(
                f"marqueur de réservation incohérent ({key}): {reservation_path}"
            )
    if record.get("stage") not in NEW_RUN_STAGES:
        raise WorkflowError(f"étape de réservation invalide: {reservation_path}")
    recipe = str(record.get("recipe") or "")
    if not RUN_ID_RE.fullmatch(recipe):
        raise WorkflowError(f"recette de réservation invalide: {reservation_path}")
    if not str(record.get("created_utc") or "").endswith("Z"):
        raise WorkflowError(f"date de réservation invalide: {reservation_path}")
    return reservation_path, content


def _consume_run_reservation(path: Path, expected_content: bytes) -> None:
    """Consume only the exact validated claim; the completed run now owns the ID."""

    try:
        if not path.is_file() or path.read_bytes() != expected_content:
            raise WorkflowError(f"marqueur de réservation modifié avant consommation: {path}")
        path.unlink()
    except WorkflowError:
        raise
    except OSError as error:
        raise WorkflowError(f"suppression du marqueur de réservation impossible: {path}") from error


def _new_run_unlocked(
    workspace_root: Path,
    raw_resref: str,
    stage: str,
    recipe: str,
    run_id: str | None,
    apply: bool,
) -> dict[str, Any]:
    resref = validate_resref(raw_resref)
    _registry_row(workspace_root, resref)
    resource_root = repo_path(workspace_root, RESOURCES_REL / resref)
    if not resource_root.is_dir():
        raise WorkflowError(f"extraction canonique absente: {resource_root}")
    if stage not in NEW_RUN_STAGES:
        raise WorkflowError(f"étape de run invalide: {stage!r}")
    recipe_slug = recipe.strip().lower()
    if not RUN_ID_RE.fullmatch(recipe_slug):
        raise WorkflowError(f"recipe invalide pour un chemin: {recipe!r}")
    now = datetime.now(timezone.utc)
    if run_id is None:
        run_id, run_path, reservation_path = _automatic_run_id(
            workspace_root,
            resource_root,
            resref,
            stage,
            recipe_slug,
            now.strftime("%Y%m%d-%H%M%S-%f"),
        )
    else:
        if not RUN_ID_RE.fullmatch(run_id) or run_id.casefold().endswith(".partial"):
            raise WorkflowError(f"run-id invalide: {run_id!r}")
        run_path, reservation_path, occupied = _run_candidate(
            workspace_root, resource_root, resref, run_id)
        if occupied is not None:
            raise WorkflowError(
                f"run-id déjà utilisé; reprise/écrasement implicite interdit: {occupied}"
            )

    reservation = {
        "schema": RUN_RESERVATION_SCHEMA,
        "status": "reserved",
        "created_utc": now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "resref": resref,
        "stage": stage,
        "recipe": recipe_slug,
        "run_id": run_id,
        "destination": relative_path(workspace_root, run_path),
    }
    changed_paths: list[str] = []
    if apply:
        content = _write_run_reservation(reservation_path, reservation)
        # A non-cooperating producer may have created a run between the first check and O_EXCL.
        # Refuse that collision without deleting a marker modified by another process.
        try:
            destination = ANIMATION_PATHS.resolve_run_destination(
                run_id,
                [resref],
                animations_root=repo_path(workspace_root, "animations"),
            )
        except RuntimeError as error:
            _remove_own_run_reservation(reservation_path, content)
            raise WorkflowError(str(error)) from error
        resolved_after = repo_path(workspace_root, destination)
        partial_after = resolved_after.with_name(resolved_after.name + ".partial")
        occupied_after = next(
            (path for path in (resolved_after, partial_after) if _path_claimed(path)),
            None,
        )
        if occupied_after is not None:
            _remove_own_run_reservation(reservation_path, content)
            raise WorkflowError(
                "run créé pendant sa réservation; identifiant non attribué: "
                f"{occupied_after}"
            )
        changed_paths.append(relative_path(workspace_root, reservation_path))
    return {
        "command": "new-run",
        "mode": "applied" if apply else "planned",
        "resref": resref,
        "stage": stage,
        "recipe": recipe_slug,
        "run_id": run_id,
        "reservation_path": relative_path(workspace_root, reservation_path),
        "data_paths": [relative_path(workspace_root, run_path)],
        "changed_paths": changed_paths,
        "tracked_files": [],
        "release_mutation": False,
    }


def new_run(
    workspace_root: Path,
    raw_resref: str,
    stage: str,
    recipe: str,
    run_id: str | None,
    apply: bool,
) -> dict[str, Any]:
    """Plan without writes, or reserve the selected identifier under the shared lock."""

    if not apply:
        return _new_run_unlocked(
            workspace_root, raw_resref, stage, recipe, run_id, False)
    with _animation_authority_lock(workspace_root):
        active = [
            relative.as_posix()
            for relative in (AUTHORITY_JOURNAL_REL, RELEASE_JOURNAL_REL)
            if repo_path(workspace_root, relative).exists()
        ]
        if active:
            raise WorkflowError(
                "transaction animation interrompue active; relancer sa commande d'origine: "
                + ", ".join(active)
            )
        return _new_run_unlocked(
            workspace_root, raw_resref, stage, recipe, run_id, True)


def _finalize_unlocked(
    workspace_root: Path,
    raw_resref: str,
    final_run: str | Path | None,
    qa_pack: str | Path | None,
    areas: Sequence[str],
    decision_status: str,
    decision_date: str,
    decision_text: str,
    *,
    decision_id: str | None = None,
    recipe_id: str | None = None,
    correction_id: str | None = None,
    notes: str | None = None,
    registry_status: str = "validé-x4",
    apply: bool = False,
) -> dict[str, Any]:
    resref = validate_resref(raw_resref)
    qa_date = validate_iso_date(decision_date)
    if decision_status not in {"accepted", "rejected"}:
        raise WorkflowError(f"décision QA invalide: {decision_status!r}")
    if registry_status not in {"validé-x4", "validé-natif"}:
        raise WorkflowError(f"statut registre final interdit: {registry_status!r}")
    if not decision_text.strip():
        raise WorkflowError("texte de décision QA requis")
    if correction_id is not None and not correction_id.strip():
        raise WorkflowError("correction-id vide interdit")
    if not registry_status.strip():
        raise WorkflowError("statut registre final vide interdit")
    tested_areas = sorted({validate_area(value) for value in areas}, key=area_key)
    if not tested_areas:
        raise WorkflowError("au moins une zone QA explicite est requise")
    row, rows = _registry_row(workspace_root, resref)
    inventory_areas = {area for area in row["areas"].split(";") if area}
    unknown_areas = sorted(set(tested_areas) - inventory_areas, key=area_key)
    if unknown_areas:
        raise WorkflowError(f"zones absentes de l'inventaire de {resref}: {', '.join(unknown_areas)}")
    missing_areas = sorted(inventory_areas - set(tested_areas), key=area_key)
    if missing_areas:
        raise WorkflowError(
            f"QA globale incomplète pour {resref}; zones restantes: {', '.join(missing_areas)}"
        )

    result_kind = "native" if registry_status == "validé-natif" else "x4"
    if result_kind == "native" and correction_id is not None:
        raise WorkflowError("correction-id interdit pour une validation native")
    effective_correction_id = (
        None
        if result_kind == "native"
        else (correction_id.strip() if correction_id is not None else row.get("correction_id", "").strip())
    )
    if not effective_correction_id:
        effective_correction_id = None
    final_artifact: dict[str, str] | None = None
    source_pack: dict[str, Any] | None = None
    lineage: dict[str, list[dict[str, str]]] | None = None
    native_source: dict[str, Any] | None = None
    run_reservation: tuple[Path, bytes] | None = None
    if result_kind == "native":
        if final_run is not None or qa_pack is not None:
            raise WorkflowError(
                "une validation native ne doit référencer ni run transformé ni pack x4"
            )
        native_source = _native_source(workspace_root, resref, row)
    else:
        if final_run is None or qa_pack is None:
            raise WorkflowError("--final-run et --qa-pack sont requis pour une validation x4")
        resolved_final_run = _resolve_run_input(workspace_root, final_run, resref)
        try:
            ANIMATION_PATHS.validate_run_location(
                resolved_final_run,
                [resref],
                animations_root=repo_path(workspace_root, "animations"),
            )
        except RuntimeError as error:
            raise WorkflowError(str(error)) from error
        final_artifact, final_manifest, final_manifest_path = _artifact(
            workspace_root, resolved_final_run
        )
        if final_artifact["status"] not in FINAL_STATUSES:
            raise WorkflowError(f"run final non terminé: {final_artifact['status']}")
        targets = _manifest_resrefs(final_manifest)
        if resref not in targets:
            raise WorkflowError(f"run final ne déclare pas {resref}: {final_manifest_path}")
        _verify_embedded_pack(workspace_root, final_manifest, final_manifest_path)
        lineage = _collect_lineage(workspace_root, final_manifest, final_manifest_path)
        source_pack = _source_pack(
            workspace_root,
            repo_path(workspace_root, qa_pack),
            resref,
            tested_areas,
        )
        _verify_pack_binding(
            workspace_root,
            final_manifest,
            final_manifest_path,
            source_pack,
            resref,
        )
        run_reservation = _reservation_for_run(
            workspace_root,
            repo_path(workspace_root, RESOURCES_REL / resref),
            resref,
            resolved_final_run,
        )

    if recipe_id is not None and not RUN_ID_RE.fullmatch(recipe_id):
        raise WorkflowError(f"recipe-id invalide: {recipe_id!r}")
    if decision_id is None:
        stem = (
            "native-source"
            if result_kind == "native"
            else re.sub(
                r"[^a-z0-9._-]+",
                "-",
                Path(final_artifact["path"]).name.lower(),
            ).strip("-.")
        )
        decision_id = f"{qa_date}-{decision_status}-{stem}"[:128].rstrip("-.")
    if not RUN_ID_RE.fullmatch(decision_id) or decision_id.casefold().endswith(".partial"):
        raise WorkflowError(f"decision-id invalide: {decision_id!r}")
    now = utc_now()
    decision: dict[str, Any] = {
        "$schema": DECISION_SCHEMA_REF,
        "schema_version": 1,
        "decision_id": decision_id,
        "asset_id": f"animations:bam:{resref}",
        "resref": resref,
        "status": decision_status,
        "result_kind": result_kind,
        "decision_origin": "explicit-user-ingame-qa",
        "decision_date": qa_date,
        "recorded_at_utc": now,
        "decision": decision_text.strip(),
        "tested_areas": tested_areas,
    }
    if result_kind == "x4":
        decision.update(
            {
                "final_run": final_artifact,
                "source_pack": source_pack,
                "lineage": lineage,
            }
        )
    else:
        decision["native_source"] = native_source
    if recipe_id:
        decision["recipe_id"] = recipe_id
    if effective_correction_id:
        decision["correction_id"] = effective_correction_id

    decision_path = repo_path(workspace_root, DECISIONS_REL / resref / f"{decision_id}.json")
    decision_bytes, decision_changed = _prepare_immutable(
        decision_path, decision, "recorded_at_utc"
    )
    planned: dict[Path, bytes] = {}
    if decision_changed:
        planned[decision_path] = decision_bytes
    tracked = [decision_path]

    if decision_status == "accepted":
        decision_sha = _bytes_sha256(decision_bytes)
        selection: dict[str, Any] = {
            "$schema": SELECTION_SCHEMA_REF,
            "schema_version": 1,
            "asset_id": f"animations:bam:{resref}",
            "resref": resref,
            "result_kind": result_kind,
            "updated_at_utc": now,
            "qa_decision": {
                "path": relative_path(workspace_root, decision_path),
                "sha256": decision_sha,
                "status": "accepted",
                "decision_date": qa_date,
            },
            "tested_areas": tested_areas,
        }
        if result_kind == "x4":
            selection.update(
                {
                    "selected_run": final_artifact,
                    "lineage": lineage,
                    "source_pack": source_pack,
                }
            )
        else:
            selection["native_source"] = native_source
        if recipe_id:
            selection["recipe_id"] = recipe_id
        if effective_correction_id:
            selection["correction_id"] = effective_correction_id
        selection_path = repo_path(workspace_root, SELECTIONS_REL / f"{resref}.json")
        selection_bytes, selection_changed = _prepare_mutable(
            selection_path, selection, "updated_at_utc"
        )
        if selection_changed:
            planned[selection_path] = selection_bytes
        tracked.append(selection_path)

        updated = dict(row)
        updated["status"] = registry_status.strip()
        updated["selected_run"] = (
            final_artifact["path"] if result_kind == "x4" and final_artifact else ""
        )
        updated["qa_decision"] = relative_path(workspace_root, decision_path)
        updated["qa_date"] = qa_date
        if result_kind == "native":
            updated["correction_id"] = ""
        elif effective_correction_id is not None:
            updated["correction_id"] = effective_correction_id
        if notes is not None:
            updated["notes"] = notes.strip()
        updated_rows = [updated if item["resref"] == resref else item for item in rows]
        registry_path = repo_path(workspace_root, REGISTRY_REL)
        registry_bytes = _render_registry(updated_rows)
        if not registry_path.is_file() or registry_path.read_bytes() != registry_bytes:
            planned[registry_path] = registry_bytes
        tracked.append(registry_path)

    consumed_reservation: str | None = None
    if apply and run_reservation is not None:
        reservation_path, reservation_content = run_reservation
        _consume_run_reservation(reservation_path, reservation_content)
        consumed_reservation = relative_path(workspace_root, reservation_path)
    if apply:
        _write_transaction(workspace_root, planned)
    data_paths: set[str] = set()
    if result_kind == "x4" and final_artifact and source_pack and lineage:
        data_paths.update((final_artifact["path"], source_pack["path"]))
        data_paths.update(item["path"] for item in source_pack["areas"])
        data_paths.update(item["path"] for item in lineage["source_runs"])
        data_paths.update(item["path"] for item in lineage["source_packs"])
    elif native_source:
        data_paths.add(str(native_source["path"]))
    return {
        "command": "finalize",
        "mode": "applied" if apply else "planned",
        "resref": resref,
        "result_kind": result_kind,
        "decision_status": decision_status,
        "decision_id": decision_id,
        "tracked_files": [relative_path(workspace_root, path) for path in tracked],
        "changed_files": [relative_path(workspace_root, path) for path in planned],
        "reservation_to_consume": (
            relative_path(workspace_root, run_reservation[0])
            if run_reservation is not None
            else None
        ),
        "consumed_reservation": consumed_reservation,
        "data_paths": sorted(data_paths),
        "tested_areas": tested_areas,
        "release_mutation": False,
        "release_next_step": (
            "separate-explicit-decision"
            if decision_status == "accepted" and registry_status == "validé-x4"
            else "not-applicable"
        ),
    }


def finalize(
    workspace_root: Path,
    raw_resref: str,
    final_run: str | Path | None,
    qa_pack: str | Path | None,
    areas: Sequence[str],
    decision_status: str,
    decision_date: str,
    decision_text: str,
    *,
    decision_id: str | None = None,
    recipe_id: str | None = None,
    correction_id: str | None = None,
    notes: str | None = None,
    registry_status: str = "validé-x4",
    apply: bool = False,
) -> dict[str, Any]:
    arguments = {
        "workspace_root": workspace_root,
        "raw_resref": raw_resref,
        "final_run": final_run,
        "qa_pack": qa_pack,
        "areas": areas,
        "decision_status": decision_status,
        "decision_date": decision_date,
        "decision_text": decision_text,
        "decision_id": decision_id,
        "recipe_id": recipe_id,
        "correction_id": correction_id,
        "notes": notes,
        "registry_status": registry_status,
        "apply": apply,
    }
    if not apply:
        with _stable_authority_read(workspace_root):
            return _finalize_unlocked(**arguments)
    with _animation_authority_lock(workspace_root):
        release_journal = repo_path(workspace_root, RELEASE_JOURNAL_REL)
        if release_journal.exists():
            raise WorkflowError(
                "transaction release animation interrompue; relancer d'abord "
                "animation_release.py --run avec la même zone"
            )
        recovered = _recover_authority_transaction(workspace_root)
        result = _finalize_unlocked(**arguments)
        return {**result, "recovered_before_apply": recovered}


def _validate_artifact_hash(workspace_root: Path, artifact: Any, label: str, errors: list[str]) -> None:
    if not isinstance(artifact, Mapping):
        errors.append(f"{label}: objet absent")
        return
    try:
        manifest_path = repo_path(workspace_root, str(artifact.get("manifest_path") or ""))
        artifact_path = repo_path(workspace_root, str(artifact.get("path") or ""))
        if artifact_path != manifest_path.parent:
            errors.append(f"{label}: path ne contient pas le manifeste")
        actual = sha256(manifest_path)
        declared = str(artifact.get("manifest_sha256") or "").upper()
        if actual != declared:
            errors.append(f"{label}: hash manifeste différent")
        manifest = load_json(manifest_path)
        if manifest.get("schema") != artifact.get("schema") or manifest.get("status") != artifact.get("status"):
            errors.append(f"{label}: schema/status différent du manifeste")
    except WorkflowError as error:
        errors.append(f"{label}: {error}")


def _validate_x4_decision(
    workspace_root: Path,
    decision_path: Path,
    record: Mapping[str, Any],
    resref: str,
    tested_areas: Sequence[str],
    errors: list[str],
) -> None:
    label = relative_path(workspace_root, decision_path)
    missing = sorted({"final_run", "source_pack", "lineage"} - set(record))
    if missing:
        errors.append(f"{label}: champs x4 absents {', '.join(missing)}")
        return
    if "native_source" in record:
        errors.append(f"{label}: native_source interdit pour un résultat x4")
    final_run = record.get("final_run")
    source_pack = record.get("source_pack")
    if not isinstance(final_run, Mapping) or not isinstance(source_pack, Mapping):
        errors.append(f"{label}: final_run/source_pack invalides")
        return
    try:
        final_path = repo_path(workspace_root, str(final_run.get("path") or ""))
        ANIMATION_PATHS.validate_run_location(
            final_path,
            [resref],
            animations_root=repo_path(workspace_root, "animations"),
        )
        artifact, manifest, manifest_path = _artifact(workspace_root, final_path)
        if artifact != final_run:
            errors.append(f"{label}: final_run différent du manifeste courant")
        if manifest_path != final_path / "manifest.json":
            errors.append(f"{label}: final_run.manifest_path non canonique")
        if artifact["status"] not in FINAL_STATUSES:
            errors.append(f"{label}: run final non terminé")
        if resref not in _manifest_resrefs(manifest):
            errors.append(f"{label}: final_run ne cible pas {resref}")
        _verify_embedded_pack(workspace_root, manifest, manifest_path)
        expected_lineage = _collect_lineage(workspace_root, manifest, manifest_path)
        if record.get("lineage") != expected_lineage:
            errors.append(f"{label}: lineage différent des manifestes courants")
        expected_pack = _source_pack(
            workspace_root,
            repo_path(workspace_root, str(source_pack.get("path") or "")),
            resref,
            tested_areas,
        )
        if source_pack != expected_pack:
            errors.append(f"{label}: source_pack différent du pack courant")
        _verify_pack_binding(
            workspace_root,
            manifest,
            manifest_path,
            expected_pack,
            resref,
        )
    except (WorkflowError, RuntimeError) as error:
        errors.append(f"{label}: preuve x4 invalide: {error}")


def _validate_decision_record(
    workspace_root: Path,
    path: Path,
    expected_resref: str | None,
    errors: list[str],
    *,
    validate_registry: bool = True,
) -> dict[str, Any] | None:
    try:
        record = load_json(path)
        resref = validate_resref(str(record.get("resref") or ""))
        if expected_resref and resref != expected_resref:
            errors.append(f"{relative_path(workspace_root, path)}: resref incohérent")
        required = {
            "schema_version",
            "decision_id",
            "asset_id",
            "resref",
            "status",
            "result_kind",
            "decision_origin",
            "decision_date",
            "recorded_at_utc",
            "decision",
            "tested_areas",
        }
        missing = sorted(required - set(record))
        if missing:
            errors.append(f"{relative_path(workspace_root, path)}: clés absentes {', '.join(missing)}")
            return record
        allowed = required | {
            "$schema",
            "recipe_id",
            "correction_id",
            "final_run",
            "native_source",
            "source_pack",
            "lineage",
        }
        unknown = sorted(set(record) - allowed)
        if unknown:
            errors.append(
                f"{relative_path(workspace_root, path)}: clés inconnues {', '.join(unknown)}"
            )
        if record.get("schema_version") != 1:
            errors.append(f"{relative_path(workspace_root, path)}: schema_version invalide")
        if record.get("$schema") != DECISION_SCHEMA_REF:
            errors.append(f"{relative_path(workspace_root, path)}: référence de schéma invalide")
        if record.get("decision_id") != path.stem:
            errors.append(f"{relative_path(workspace_root, path)}: nom/decision_id incohérent")
        if str(record.get("decision_id", "")).casefold().endswith(".partial"):
            errors.append(f"{relative_path(workspace_root, path)}: decision_id réservé")
        if record.get("asset_id") != f"animations:bam:{resref}":
            errors.append(f"{relative_path(workspace_root, path)}: asset_id incohérent")
        if record.get("status") not in {"accepted", "rejected"}:
            errors.append(f"{relative_path(workspace_root, path)}: statut invalide")
        if record.get("decision_origin") != "explicit-user-ingame-qa":
            errors.append(f"{relative_path(workspace_root, path)}: origine QA invalide")
        try:
            recorded = datetime.fromisoformat(
                str(record.get("recorded_at_utc") or "").replace("Z", "+00:00")
            )
            if recorded.tzinfo is None:
                raise ValueError("timezone absente")
        except ValueError:
            errors.append(f"{relative_path(workspace_root, path)}: recorded_at_utc invalide")
        validate_iso_date(str(record.get("decision_date") or ""))
        raw_tested = record.get("tested_areas")
        if not isinstance(raw_tested, list):
            errors.append(f"{relative_path(workspace_root, path)}: tested_areas invalide")
            raw_tested = []
        tested = [validate_area(str(area)) for area in raw_tested]
        if not tested or len(tested) != len(set(tested)):
            errors.append(f"{relative_path(workspace_root, path)}: tested_areas vide/dupliqué")
        if tested != sorted(tested, key=area_key):
            errors.append(f"{relative_path(workspace_root, path)}: tested_areas non trié")
        registry_row: dict[str, str] | None = None
        result_kind = record.get("result_kind")
        if validate_registry or result_kind == "native":
            try:
                registry_row, _ = _registry_row(workspace_root, resref)
                if validate_registry:
                    inventory_areas = {
                        area for area in registry_row.get("areas", "").split(";") if area
                    }
                    if set(tested) != inventory_areas:
                        missing = sorted(inventory_areas - set(tested))
                        obsolete = sorted(set(tested) - inventory_areas)
                        detail = []
                        if missing:
                            detail.append("zones non testées " + ", ".join(missing))
                        if obsolete:
                            detail.append("zones hors inventaire " + ", ".join(obsolete))
                        errors.append(
                            f"{relative_path(workspace_root, path)}: tested_areas différent "
                            f"du registre ({'; '.join(detail)})"
                        )
            except WorkflowError as error:
                errors.append(f"{relative_path(workspace_root, path)}: registre: {error}")
        if result_kind == "x4":
            _validate_x4_decision(
                workspace_root,
                path,
                record,
                resref,
                tested,
                errors,
            )
        elif result_kind == "native":
            forbidden = {"correction_id", "final_run", "lineage", "source_pack"} & set(record)
            if forbidden:
                errors.append(
                    f"{relative_path(workspace_root, path)}: champs interdits pour native: "
                    + ", ".join(sorted(forbidden))
                )
            try:
                if registry_row is None:
                    raise WorkflowError(f"{resref}: entrée registre indisponible")
                expected_native = _native_source(workspace_root, resref, registry_row)
                if record.get("native_source") != expected_native:
                    errors.append(
                        f"{relative_path(workspace_root, path)}: source native différente de l'inventaire"
                    )
            except WorkflowError as error:
                errors.append(f"{relative_path(workspace_root, path)}: native_source: {error}")
        else:
            errors.append(f"{relative_path(workspace_root, path)}: result_kind invalide")
        return record
    except (WorkflowError, TypeError, ValueError) as error:
        errors.append(f"{relative_path(workspace_root, path)}: {error}")
        return None


def check_workspace(workspace_root: Path, raw_resref: str | None = None) -> dict[str, Any]:
    resref = validate_resref(raw_resref) if raw_resref else None
    errors: list[str] = []
    checked: list[str] = []
    decision_records: dict[str, dict[str, Any]] = {}
    decision_root = repo_path(workspace_root, DECISIONS_REL)
    pattern = f"{resref}/*.json" if resref else "*/*.json"
    if decision_root.is_dir():
        for path in sorted(decision_root.glob(pattern)):
            checked.append(relative_path(workspace_root, path))
            record = _validate_decision_record(workspace_root, path, path.parent.name, errors)
            if record is not None:
                decision_records[relative_path(workspace_root, path)] = record

    rows, _ = _read_registry(workspace_root)
    rows_by_resref = {row["resref"]: row for row in rows}
    selection_root = repo_path(workspace_root, SELECTIONS_REL)
    if resref and resref not in rows_by_resref:
        errors.append(f"{resref}: absent du registre")
        scoped_rows: dict[str, dict[str, str]] = {}
    else:
        scoped_rows = {resref: rows_by_resref[resref]} if resref else rows_by_resref
    accepted_resrefs = {
        str(record.get("resref", "")).upper()
        for record in decision_records.values()
        if record.get("status") == "accepted"
    }
    expected_selections = accepted_resrefs | {
        item_resref
        for item_resref, row in scoped_rows.items()
        if any(row.get(field, "") for field in ("selected_run", "qa_decision", "qa_date"))
    }
    for item_resref in sorted(expected_selections):
        expected_path = selection_root / f"{item_resref}.json"
        if not expected_path.is_file():
            errors.append(f"{item_resref}: sélection courante absente")
    if resref:
        selection_paths = [selection_root / f"{resref}.json"]
    elif selection_root.is_dir():
        selection_paths = sorted(selection_root.glob("*.json"))
    else:
        selection_paths = []
    for path in selection_paths:
        if not path.is_file():
            continue
        checked.append(relative_path(workspace_root, path))
        try:
            selection = load_json(path)
            selected_resref = validate_resref(str(selection.get("resref") or ""))
            allowed_selection = {
                "$schema",
                "schema_version",
                "asset_id",
                "resref",
                "result_kind",
                "updated_at_utc",
                "recipe_id",
                "correction_id",
                "selected_run",
                "native_source",
                "lineage",
                "qa_decision",
                "source_pack",
                "tested_areas",
            }
            unknown_selection = sorted(set(selection) - allowed_selection)
            if unknown_selection:
                errors.append(
                    f"{relative_path(workspace_root, path)}: clés inconnues "
                    + ", ".join(unknown_selection)
                )
            if path.stem != selected_resref:
                errors.append(f"{relative_path(workspace_root, path)}: nom/resref incohérent")
            if selection.get("schema_version") != 1:
                errors.append(f"{relative_path(workspace_root, path)}: schema_version invalide")
            if selection.get("$schema") != SELECTION_SCHEMA_REF:
                errors.append(f"{relative_path(workspace_root, path)}: référence de schéma invalide")
            if selection.get("asset_id") != f"animations:bam:{selected_resref}":
                errors.append(f"{relative_path(workspace_root, path)}: asset_id incohérent")
            try:
                updated = datetime.fromisoformat(
                    str(selection.get("updated_at_utc") or "").replace("Z", "+00:00")
                )
                if updated.tzinfo is None:
                    raise ValueError("timezone absente")
            except ValueError:
                errors.append(f"{relative_path(workspace_root, path)}: updated_at_utc invalide")
            result_kind = selection.get("result_kind")
            if result_kind not in {"x4", "native"}:
                errors.append(f"{relative_path(workspace_root, path)}: result_kind invalide")
            decision_ref = selection.get("qa_decision")
            if not isinstance(decision_ref, Mapping):
                errors.append(f"{relative_path(workspace_root, path)}: qa_decision invalide")
                continue
            decision_path = repo_path(workspace_root, str(decision_ref.get("path") or ""))
            expected_decision_root = repo_path(workspace_root, DECISIONS_REL / selected_resref)
            try:
                decision_path.relative_to(expected_decision_root)
            except ValueError:
                errors.append(f"{relative_path(workspace_root, path)}: décision hors du dossier de l'asset")
            actual_decision_hash = sha256(decision_path)
            if actual_decision_hash != str(decision_ref.get("sha256") or "").upper():
                errors.append(f"{relative_path(workspace_root, path)}: hash décision différent")
            decision = decision_records.get(relative_path(workspace_root, decision_path)) or load_json(decision_path)
            if decision.get("status") != "accepted" or decision.get("resref") != selected_resref:
                errors.append(f"{relative_path(workspace_root, path)}: décision non acceptée/incohérente")
            if decision.get("result_kind") != result_kind:
                errors.append(f"{relative_path(workspace_root, path)}: résultat différent de la décision")
            if decision_ref.get("status") != "accepted":
                errors.append(f"{relative_path(workspace_root, path)}: statut de référence QA invalide")
            if decision_ref.get("decision_date") != decision.get("decision_date"):
                errors.append(f"{relative_path(workspace_root, path)}: date de décision incohérente")
            for key in ("tested_areas",):
                if selection.get(key) != decision.get(key):
                    errors.append(f"{relative_path(workspace_root, path)}: {key} différent de la décision")
            for key in ("recipe_id", "correction_id"):
                if selection.get(key) != decision.get(key):
                    errors.append(f"{relative_path(workspace_root, path)}: {key} différent de la décision")
            if result_kind == "x4":
                for key in ("selected_run", "lineage", "source_pack"):
                    decision_key = "final_run" if key == "selected_run" else key
                    if selection.get(key) != decision.get(decision_key):
                        errors.append(
                            f"{relative_path(workspace_root, path)}: {key} différent de la décision"
                        )
                if "native_source" in selection:
                    errors.append(f"{relative_path(workspace_root, path)}: native_source interdit")
                _validate_artifact_hash(
                    workspace_root,
                    selection.get("selected_run"),
                    "selected_run",
                    errors,
                )
            elif result_kind == "native":
                forbidden = {
                    "correction_id",
                    "selected_run",
                    "lineage",
                    "source_pack",
                } & set(selection)
                if forbidden:
                    errors.append(
                        f"{relative_path(workspace_root, path)}: champs interdits pour native: "
                        + ", ".join(sorted(forbidden))
                    )
                if selection.get("native_source") != decision.get("native_source"):
                    errors.append(
                        f"{relative_path(workspace_root, path)}: native_source différent de la décision"
                    )
            row = rows_by_resref.get(selected_resref)
            if row is None:
                errors.append(f"{selected_resref}: absent du registre")
            else:
                selected_run = selection.get("selected_run")
                expected = {
                    "status": "validé-x4" if result_kind == "x4" else "validé-natif",
                    "selected_run": (
                        selected_run.get("path", "")
                        if result_kind == "x4" and isinstance(selected_run, Mapping)
                        else ""
                    ),
                    "qa_decision": relative_path(workspace_root, decision_path),
                    "qa_date": decision.get("decision_date", ""),
                }
                for key, value in expected.items():
                    if row.get(key, "") != value:
                        errors.append(f"{selected_resref}: registre.{key} différent de la sélection")
                selected_correction = str(selection.get("correction_id") or "")
                if selected_correction and row.get("correction_id", "") != selected_correction:
                    errors.append(
                        f"{selected_resref}: registre.correction_id différent de la sélection"
                    )
        except (WorkflowError, TypeError, ValueError, AttributeError) as error:
            errors.append(f"{relative_path(workspace_root, path)}: {error}")
    return {
        "command": "check",
        "resref": resref,
        "ok": not errors,
        "checked_files": sorted(set(checked)),
        "errors": errors,
        "release_mutation": False,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build an extensible parser; release remains a separate future module."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=PROJECT_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="liste les animations à traiter")
    list_parser.add_argument("--status", action="append", dest="statuses")
    list_parser.add_argument("--limit", type=int)

    status_parser = subparsers.add_parser("status", help="affiche le suivi complet d'un asset")
    status_parser.add_argument("--resref", required=True)

    new_parser = subparsers.add_parser("new-run", help="prépare un chemin de run standard")
    new_parser.add_argument("--resref", required=True)
    new_parser.add_argument(
        "--stage",
        required=True,
        choices=NEW_RUN_STAGES,
    )
    new_parser.add_argument("--recipe", required=True)
    new_parser.add_argument("--run-id")
    new_parser.add_argument(
        "--run",
        action="store_true",
        help="réserve atomiquement l'identifiant; le producteur crée le run",
    )

    finalize_parser = subparsers.add_parser("finalize", help="consigne une décision QA explicite")
    finalize_parser.add_argument("--resref", required=True)
    finalize_parser.add_argument("--final-run", help="requis pour validé-x4; interdit pour validé-natif")
    finalize_parser.add_argument("--qa-pack", help="requis pour validé-x4; interdit pour validé-natif")
    finalize_parser.add_argument("--area", action="append", required=True, dest="areas")
    finalize_parser.add_argument("--decision-status", choices=("accepted", "rejected"), required=True)
    finalize_parser.add_argument("--qa-date", required=True)
    finalize_parser.add_argument("--decision", required=True)
    finalize_parser.add_argument("--decision-id")
    finalize_parser.add_argument("--recipe-id")
    finalize_parser.add_argument("--correction-id")
    finalize_parser.add_argument("--notes")
    finalize_parser.add_argument(
        "--registry-status",
        choices=("validé-x4", "validé-natif"),
        default="validé-x4",
    )
    finalize_parser.add_argument("--run", action="store_true", help="écrit; sinon plan seulement")

    check_parser = subparsers.add_parser("check", help="contrôle décisions/sélections/hashes")
    check_parser.add_argument("--resref")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.workspace_root.resolve()
    try:
        if args.command == "list":
            with _stable_authority_read(root):
                result = list_assets(root, args.statuses, args.limit)
        elif args.command == "status":
            with _stable_authority_read(root):
                result = status_asset(root, args.resref)
        elif args.command == "new-run":
            result = new_run(root, args.resref, args.stage, args.recipe, args.run_id, args.run)
        elif args.command == "finalize":
            result = finalize(
                root,
                args.resref,
                args.final_run,
                args.qa_pack,
                args.areas,
                args.decision_status,
                args.qa_date,
                args.decision,
                decision_id=args.decision_id,
                recipe_id=args.recipe_id,
                correction_id=args.correction_id,
                notes=args.notes,
                registry_status=args.registry_status,
                apply=args.run,
            )
        elif args.command == "check":
            with _stable_authority_read(root):
                result = check_workspace(root, args.resref)
        else:  # pragma: no cover - argparse enforces the command set.
            parser.error(f"commande inconnue: {args.command}")
            return 2
    except WorkflowError as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
