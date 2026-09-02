"""Promote explicit animation in-game QA decisions into the release manifests.

The command is plan-only unless ``--run`` is supplied.  It consumes tracked,
immutable per-resref QA decisions and one exact per-area pack.  Legacy release
records remain readable but every new record uses structured run provenance and
versioned area QA.  Media runs and sealed historical approvals are never
modified.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence
import uuid


ROOT = Path(__file__).resolve().parents[2]
RELEASE_ROOT = ROOT / "releases" / "BG2-HD-Upscale"
CANDIDATES = RELEASE_ROOT / "manifests" / "animation-release-candidates.json"
CONTENT = RELEASE_ROOT / "manifests" / "content.json"
COMPONENTS = RELEASE_ROOT / "manifests" / "components.json"
RUNTIME_COMPATIBILITY = RELEASE_ROOT / "manifests" / "runtime-compatibility.json"
PACKAGE_MANIFESTS = RELEASE_ROOT / "bg2hd" / "manifests"
PACKAGE_TP2 = RELEASE_ROOT / "bg2hd" / "bg2hd.tp2"
PACKAGE_SYNC_MARKER = PACKAGE_MANIFESTS / ".package-metadata-sync.partial"
SELECTIONS = ROOT / "animations" / "index" / "selections"
REGISTRY = ROOT / "animations" / "index" / "animation_upscale_registry.csv"
AREAS = ROOT / "areas.csv"
QA_APPROVALS = RELEASE_ROOT / "manifests" / "animation-qa-approvals"
SCRIPT_ROOT = Path(__file__).resolve().parent
TRANSACTION_ROOT = ROOT / ".tmp" / "workflow-transactions"
PUBLICATION_JOURNAL = TRANSACTION_ROOT / "animation-release-active.json"
AUTHORITY_JOURNAL = TRANSACTION_ROOT / "animation-authority-active.json"
PUBLICATION_JOURNAL_SCHEMA = "bg2-animation-release-publication-journal-v2"
_RUNTIME_V2: Any | None = None
_WORKFLOW: Any | None = None

AREA_RE = re.compile(r"^(?:AR|OH)[0-9]{4}$")
RESREF_RE = re.compile(r"^(?=.*[A-Z0-9])[A-Z0-9_]{1,8}$")
SHA256_RE = re.compile(r"^[A-F0-9]{64}$")
PACK_PATH_RE = re.compile(
    r"^animations/packs-par-zone/[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?/(?:AR|OH)[0-9]{4}$"
)
QA_DECISION_PATH_RE = re.compile(
    r"^animations/index/qa-decisions/[A-Z0-9_]{1,8}/[A-Za-z0-9][A-Za-z0-9._-]*[.]json$"
)
QA_APPROVAL_PATH_RE = re.compile(
    r"^releases/BG2-HD-Upscale/manifests/animation-qa-approvals/(?:AR|OH)[0-9]{4}/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?[.]json$"
)
RELATIVE_PATH_RE = re.compile(
    r"^(?![A-Za-z]:)(?!/)(?!.*(?:^|/)[.][.](?:/|$))[A-Za-z0-9._/-]+$"
)
SOURCE_RUN_PATH_RE = re.compile(
    r"^(?!.*[.]partial$)animations/(?:ressources/[A-Z0-9_]{1,8}/runs|batches|runs)/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?$"
)
SOURCE_RUN_MANIFEST_RE = re.compile(
    r"^(?!.*[.]partial/manifest[.]json$)animations/(?:ressources/[A-Z0-9_]{1,8}/runs|batches|runs)/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9_-])?/manifest[.]json$"
)
RENDERER_CONTRACTS = {
    "area-animation-per-area-registry-v2-timed-timeline",
    "area-animation-per-area-registry-v3-position-timed-timeline",
}
FORBIDDEN_PARTS = {
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
FINAL_RUN_STATUSES = {
    "completed",
    "validated",
    "validated-installed",
}


class ReleasePromotionError(RuntimeError):
    """Raised before publication when the requested promotion is inconsistent."""


def _load_animation_authority_lock_module() -> Any:
    module_path = SCRIPT_ROOT / "animation_authority_lock.py"
    spec = importlib.util.spec_from_file_location("bg2_animation_authority_lock_release", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module de verrou animation introuvable : {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANIMATION_AUTHORITY_LOCK = _load_animation_authority_lock_module()


def configure_workspace_root(root: Path) -> None:
    """Point the verifier at an explicit workspace without changing code location."""

    global ROOT, RELEASE_ROOT, CANDIDATES, CONTENT, COMPONENTS
    global RUNTIME_COMPATIBILITY, PACKAGE_MANIFESTS
    global PACKAGE_SYNC_MARKER
    global PACKAGE_TP2, SELECTIONS, REGISTRY, AREAS, QA_APPROVALS, TRANSACTION_ROOT
    global PUBLICATION_JOURNAL, AUTHORITY_JOURNAL
    ROOT = root.resolve()
    RELEASE_ROOT = ROOT / "releases" / "BG2-HD-Upscale"
    CANDIDATES = RELEASE_ROOT / "manifests" / "animation-release-candidates.json"
    CONTENT = RELEASE_ROOT / "manifests" / "content.json"
    COMPONENTS = RELEASE_ROOT / "manifests" / "components.json"
    RUNTIME_COMPATIBILITY = RELEASE_ROOT / "manifests" / "runtime-compatibility.json"
    PACKAGE_MANIFESTS = RELEASE_ROOT / "bg2hd" / "manifests"
    PACKAGE_TP2 = RELEASE_ROOT / "bg2hd" / "bg2hd.tp2"
    PACKAGE_SYNC_MARKER = PACKAGE_MANIFESTS / ".package-metadata-sync.partial"
    SELECTIONS = ROOT / "animations" / "index" / "selections"
    REGISTRY = ROOT / "animations" / "index" / "animation_upscale_registry.csv"
    AREAS = ROOT / "areas.csv"
    QA_APPROVALS = RELEASE_ROOT / "manifests" / "animation-qa-approvals"
    TRANSACTION_ROOT = ROOT / ".tmp" / "workflow-transactions"
    PUBLICATION_JOURNAL = TRANSACTION_ROOT / "animation-release-active.json"
    AUTHORITY_JOURNAL = TRANSACTION_ROOT / "animation-authority-active.json"


def runtime_v2_module() -> Any:
    global _RUNTIME_V2
    if _RUNTIME_V2 is None:
        module_path = SCRIPT_ROOT / "run_animation_upscale_30fps_v2.py"
        spec = importlib.util.spec_from_file_location("bg2_animation_runtime_v2_release", module_path)
        if spec is None or spec.loader is None:
            raise ReleasePromotionError(f"validateur runtime introuvable : {module_path}")
        module = importlib.util.module_from_spec(spec)
        scripts = str(SCRIPT_ROOT)
        inserted = scripts not in sys.path
        if inserted:
            sys.path.insert(0, scripts)
        try:
            spec.loader.exec_module(module)
        except Exception as error:
            raise ReleasePromotionError(f"chargement du validateur runtime impossible : {error}") from error
        finally:
            if inserted:
                sys.path.remove(scripts)
        _RUNTIME_V2 = module
    return _RUNTIME_V2


def validate_runtime_pack(pack: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    runtime = runtime_v2_module()
    try:
        manifest = load_json(pack / "manifest.json")
        if manifest.get("schema") == getattr(runtime, "PACK_SCHEMA", None):
            return runtime.validate_v2_pack(pack)
        if manifest.get("schema") == getattr(runtime.runtime_v1, "PACK_SCHEMA", None):
            raw_manifest, raw_resources = runtime.validate_v1_base_pack(pack)
            return raw_manifest, [runtime.normalise_v1_resource(item) for item in raw_resources]
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        raise ReleasePromotionError(f"pack runtime invalide : {repo_path(pack)} : {error}") from error
    raise ReleasePromotionError(f"schéma de pack runtime inconnu : {repo_path(pack)}")


def workflow_module() -> Any:
    global _WORKFLOW
    if _WORKFLOW is None:
        module_path = SCRIPT_ROOT / "animation_workflow.py"
        spec = importlib.util.spec_from_file_location("bg2_animation_workflow_release", module_path)
        if spec is None or spec.loader is None:
            raise ReleasePromotionError(f"validateur workflow introuvable : {module_path}")
        module = importlib.util.module_from_spec(spec)
        scripts = str(SCRIPT_ROOT)
        inserted = scripts not in sys.path
        if inserted:
            sys.path.insert(0, scripts)
        try:
            spec.loader.exec_module(module)
        except Exception as error:
            raise ReleasePromotionError(f"chargement du workflow impossible : {error}") from error
        finally:
            if inserted:
                sys.path.remove(scripts)
        _WORKFLOW = module
    return _WORKFLOW


def validate_workflow_resref(resref: str) -> None:
    try:
        result = workflow_module().check_workspace(ROOT, resref)
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as error:
        raise ReleasePromotionError(f"workflow invalide pour {resref} : {error}") from error
    if not bool(result.get("ok")):
        errors = result.get("errors") or ["erreur non détaillée"]
        raise ReleasePromotionError(f"workflow invalide pour {resref} : " + "; ".join(map(str, errors)))


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as error:
        raise ReleasePromotionError(f"fichier requis absent : {repo_path(path)}") from error
    except json.JSONDecodeError as error:
        raise ReleasePromotionError(f"JSON invalide : {repo_path(path)} : {error}") from error
    if not isinstance(value, dict):
        raise ReleasePromotionError(f"objet JSON attendu : {repo_path(path)}")
    return value


def json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError as error:
        raise ReleasePromotionError(f"chemin hors workspace : {resolved}") from error


def resolve_repo_path(value: str, *, forbidden: bool = False) -> Path:
    normalized = str(value).replace("\\", "/").strip().strip("/")
    if not normalized or re.match(r"^[A-Za-z]:", normalized):
        raise ReleasePromotionError(f"chemin workspace relatif attendu : {value!r}")
    target = (ROOT / normalized).resolve()
    repo_path(target)
    if forbidden and any(part.casefold() in FORBIDDEN_PARTS for part in Path(normalized).parts):
        raise ReleasePromotionError(f"chemin interdit pour une promotion : {normalized}")
    return target


def reject_leaf_link(value: str | Path, label: str) -> None:
    lexical = Path(value)
    if not lexical.is_absolute():
        lexical = ROOT.resolve() / lexical
    is_junction = getattr(lexical, "is_junction", lambda: False)
    require(
        not lexical.is_symlink() and not is_junction(),
        f"{label} lien/reparse interdit : {lexical}",
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleasePromotionError(message)


def normalize_area(value: str) -> str:
    area = value.strip().upper()
    require(bool(AREA_RE.fullmatch(area)), f"zone invalide : {value!r}")
    return area


def normalize_resref(value: str) -> str:
    resref = value.strip().upper()
    require(bool(RESREF_RE.fullmatch(resref)), f"resref invalide : {value!r}")
    return resref


def normalize_hash(value: object, label: str) -> str:
    digest = str(value).upper()
    require(bool(SHA256_RE.fullmatch(digest)), f"SHA-256 invalide ({label})")
    return digest


def integer(value: object, label: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ReleasePromotionError(f"entier invalide ({label})") from error


def schema_string(
    value: object,
    label: str,
    *,
    pattern: re.Pattern[str] | None = None,
    min_length: int = 0,
) -> str:
    require(isinstance(value, str), f"chaîne invalide ({label})")
    require(len(value) >= min_length, f"chaîne vide ou trop courte ({label})")
    if pattern is not None:
        require(bool(pattern.fullmatch(value)), f"format invalide ({label})")
    return value


def schema_integer(value: object, label: str, *, minimum: int | None = None) -> int:
    require(type(value) is int, f"entier JSON invalide ({label})")
    if minimum is not None:
        require(value >= minimum, f"entier hors limite ({label})")
    return value


def schema_hash(value: object, label: str) -> str:
    return schema_string(value, label, pattern=SHA256_RE)


def schema_resrefs(value: object, label: str, *, single: bool = False) -> list[str]:
    require(isinstance(value, list) and bool(value), f"liste de resrefs invalide ({label})")
    require(all(isinstance(item, str) and RESREF_RE.fullmatch(item) for item in value), f"resref invalide ({label})")
    require(len(value) == len(set(value)), f"resrefs dupliqués ({label})")
    if single:
        require(len(value) == 1, f"un seul resref attendu ({label})")
    return value


def validate_candidates_document_shape(
    document: Mapping[str, Any], *, label: str
) -> list[Mapping[str, Any]]:
    """Validate the complete candidate register against its JSON schema shape."""

    required_top = {"schema_version", "generated_by", "candidates"}
    allowed_top = required_top | {"$schema"}
    require(set(document) in (required_top, allowed_top), f"champs du registre candidats invalides : {label}")
    if "$schema" in document:
        schema_string(document["$schema"], f"$schema {label}")
    require(schema_integer(document.get("schema_version"), f"version {label}") in {2, 3}, f"version du registre de candidats inconnue : {label}")
    schema_string(document.get("generated_by"), f"generated_by {label}", min_length=1)
    raw_candidates = document.get("candidates")
    require(isinstance(raw_candidates, list), f"liste de candidats animation invalide : {label}")

    required_candidate = {
        "area",
        "component_id",
        "component_label",
        "payload_group",
        "approval_status",
        "qa_approval",
        "qa_approval_sha256",
        "source_pack",
        "pack_manifest",
        "pack_manifest_sha256",
        "registry",
        "registry_version",
        "registry_sha256",
        "registry_bytes",
        "required_resrefs",
        "renderer_contract",
    }
    optional_candidate = {"source_run", "source_runs", "occlusion_contract"}
    source_run_roles = {"spatial", "temporal", "correction", "final", "batch"}
    areas: list[str] = []
    component_ids: list[int] = []
    normalized: list[Mapping[str, Any]] = []
    for index, item in enumerate(raw_candidates):
        item_label = f"{label}/candidates/{index}"
        require(isinstance(item, Mapping), f"candidat invalide : {item_label}")
        keys = set(item)
        require(required_candidate <= keys and keys <= required_candidate | optional_candidate, f"champs candidat invalides : {item_label}")
        require(("source_run" in item) != ("source_runs" in item), f"provenance de run ambiguë ou absente : {item_label}")

        area = schema_string(item.get("area"), f"area {item_label}", pattern=AREA_RE)
        areas.append(area)
        component_id = schema_integer(item.get("component_id"), f"component_id {item_label}", minimum=3000)
        component_ids.append(component_id)
        schema_string(
            item.get("component_label"),
            f"component_label {item_label}",
            pattern=re.compile(r"^animation-(?:ar|oh)[0-9]{4}$"),
        )
        schema_string(
            item.get("payload_group"),
            f"payload_group {item_label}",
            pattern=re.compile(r"^animation-(?:ar|oh)[0-9]{4}$"),
        )
        require(item.get("approval_status") in {"validated-awaiting-manifest-approval", "approved-for-release"}, f"statut candidat invalide : {item_label}")
        schema_string(item.get("qa_approval"), f"qa_approval {item_label}", pattern=QA_APPROVAL_PATH_RE)
        schema_hash(item.get("qa_approval_sha256"), f"qa_approval_sha256 {item_label}")
        schema_string(item.get("source_pack"), f"source_pack {item_label}", pattern=PACK_PATH_RE)
        require(item.get("pack_manifest") == "manifest.json", f"pack_manifest invalide : {item_label}")
        schema_hash(item.get("pack_manifest_sha256"), f"pack_manifest_sha256 {item_label}")
        require(item.get("registry") == "AreaAnimations-X4.registry", f"registre invalide : {item_label}")
        require(schema_integer(item.get("registry_version"), f"registry_version {item_label}") in {2, 3}, f"version registre invalide : {item_label}")
        schema_hash(item.get("registry_sha256"), f"registry_sha256 {item_label}")
        schema_integer(item.get("registry_bytes"), f"registry_bytes {item_label}", minimum=1)
        schema_resrefs(item.get("required_resrefs"), f"required_resrefs {item_label}")
        require(item.get("renderer_contract") in RENDERER_CONTRACTS, f"contrat renderer invalide : {item_label}")

        if "source_run" in item:
            schema_string(item.get("source_run"), f"source_run {item_label}", min_length=1)
        else:
            source_runs = item.get("source_runs")
            require(isinstance(source_runs, list) and bool(source_runs), f"source_runs invalide : {item_label}")
            for run_index, run in enumerate(source_runs):
                run_label = f"{item_label}/source_runs/{run_index}"
                require(isinstance(run, Mapping), f"run source invalide : {run_label}")
                require(set(run) == {"path", "manifest_path", "manifest_sha256", "role", "asset_ids"}, f"champs de run source invalides : {run_label}")
                schema_string(run.get("path"), f"path {run_label}", pattern=SOURCE_RUN_PATH_RE)
                schema_string(run.get("manifest_path"), f"manifest_path {run_label}", pattern=SOURCE_RUN_MANIFEST_RE)
                schema_hash(run.get("manifest_sha256"), f"manifest_sha256 {run_label}")
                require(run.get("role") in source_run_roles, f"rôle de run invalide : {run_label}")
                schema_resrefs(run.get("asset_ids"), f"asset_ids {run_label}")

        if "occlusion_contract" in item:
            contract = item["occlusion_contract"]
            contract_label = f"{item_label}/occlusion_contract"
            contract_keys = {
                "mode", "map_component_id", "map_component_label", "map_payload_group",
                "source_spec", "source", "destination", "bytes", "sha256",
                "qa_evidence", "qa_evidence_sha256", "ini_owner", "ini_section",
                "ini_key", "ini_value",
            }
            require(isinstance(contract, Mapping) and set(contract) == contract_keys, f"contrat d'occlusion invalide : {contract_label}")
            require(contract.get("mode") == "native-wed-bridge-v1", f"mode d'occlusion invalide : {contract_label}")
            schema_integer(contract.get("map_component_id"), f"map_component_id {contract_label}", minimum=1)
            schema_string(contract.get("map_component_label"), f"map_component_label {contract_label}", pattern=re.compile(r"^map-(?:ar|oh)[0-9]{4}$"))
            schema_string(contract.get("map_payload_group"), f"map_payload_group {contract_label}", pattern=re.compile(r"^map-(?:ar|oh)[0-9]{4}$"))
            source_spec = schema_string(contract.get("source_spec"), f"source_spec {contract_label}", pattern=re.compile(r"^maps/wed-corrections/(?:AR|OH)[0-9]{4}/[A-Za-z0-9._/-]+[.]json$"))
            require(bool(RELATIVE_PATH_RE.fullmatch(source_spec)), f"source_spec non relatif : {contract_label}")
            source = schema_string(contract.get("source"), f"source {contract_label}", pattern=re.compile(r"^maps/wed-corrections/(?:AR|OH)[0-9]{4}/[A-Za-z0-9._/-]+[.]WED$"))
            require(bool(RELATIVE_PATH_RE.fullmatch(source)), f"source non relative : {contract_label}")
            schema_string(contract.get("destination"), f"destination {contract_label}", pattern=re.compile(r"^override/(?:AR|OH)[0-9]{4}[.]WED$"))
            schema_integer(contract.get("bytes"), f"bytes {contract_label}", minimum=1)
            schema_hash(contract.get("sha256"), f"sha256 {contract_label}")
            qa_evidence = schema_string(contract.get("qa_evidence"), f"qa_evidence {contract_label}", pattern=re.compile(r"^engine/InfinityEngine-Enhancer/source-patchee/docs/validation/[A-Za-z0-9._/-]+[.]md$"))
            require(bool(RELATIVE_PATH_RE.fullmatch(qa_evidence)), f"qa_evidence non relative : {contract_label}")
            schema_hash(contract.get("qa_evidence_sha256"), f"qa_evidence_sha256 {contract_label}")
            require(contract.get("ini_owner") == "core-steam", f"ini_owner invalide : {contract_label}")
            require(contract.get("ini_section") == "Shaders", f"ini_section invalide : {contract_label}")
            require(contract.get("ini_key") == "EnableNativeOcclusionBridge", f"ini_key invalide : {contract_label}")
            require(contract.get("ini_value") == "true", f"ini_value invalide : {contract_label}")
        normalized.append(item)

    require(len(areas) == len(set(areas)), f"zones dupliquées dans le registre de candidats : {label}")
    require(len(component_ids) == len(set(component_ids)), f"component_id dupliqués dans le registre de candidats : {label}")
    return normalized


def _validated_map_authorities() -> dict[str, dict[str, str]]:
    try:
        stream = AREAS.open(encoding="utf-8-sig", newline="")
    except FileNotFoundError as error:
        raise ReleasePromotionError(f"autorité cartes absente : {repo_path(AREAS)}") from error
    with stream:
        reader = csv.DictReader(stream)
        require(
            reader.fieldnames is not None
            and {"area_id", "status", "build", "runs"} <= set(reader.fieldnames),
            "colonnes requises absentes de areas.csv pour l'occlusion",
        )
        rows = list(reader)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        area = str(row.get("area_id", "")).upper()
        if not AREA_RE.fullmatch(area):
            continue
        require(area not in result, f"zone dupliquée dans areas.csv : {area}")
        result[area] = row
    return result


def _resolve_occlusion_file(value: str, *, label: str) -> Path:
    reject_leaf_link(value, label)
    path = resolve_repo_path(value)
    require(repo_path(path) == value, f"chemin non canonique ({label}) : {value}")
    require(path.is_file(), f"fichier d'occlusion absent ({label}) : {value}")
    return path


def validate_occlusion_contracts(
    candidates: Sequence[Mapping[str, Any]],
    *,
    validate_release_mapping: bool = False,
    components_document: Mapping[str, Any] | None = None,
    content_document: Mapping[str, Any] | None = None,
    require_animation_dependencies: bool = False,
) -> None:
    """Validate physical WED contracts and their optional release projection."""

    contracted = [item for item in candidates if "occlusion_contract" in item]
    if not contracted:
        return
    animation_component_ids = {
        schema_integer(
            item.get("component_id"),
            "component_id animation du registre avec occlusion",
            minimum=3000,
        )
        for item in candidates
    }
    require(
        validate_release_mapping or not require_animation_dependencies,
        "la vérification des dépendances d'occlusion exige les manifestes release",
    )

    map_authorities = _validated_map_authorities()
    runtime = load_json(RUNTIME_COMPATIBILITY)
    owned_ini_keys = runtime.get("owned_ini_keys")
    require(isinstance(owned_ini_keys, Mapping), "clés INI possédées absentes du contrat runtime")

    component_rows: list[Any] = []
    content_rows: list[Any] = []
    if validate_release_mapping:
        if components_document is None:
            components_document = load_json(COMPONENTS)
        if content_document is None:
            content_document = load_json(CONTENT)
        raw_components = components_document.get("components")
        raw_content = content_document.get("entries")
        require(isinstance(raw_components, list), "liste des composants release invalide")
        require(isinstance(raw_content, list), "liste du contenu release invalide")
        component_rows = raw_components
        content_rows = raw_content

    for candidate in contracted:
        area = schema_string(candidate.get("area"), "zone du contrat d'occlusion", pattern=AREA_RE)
        contract = candidate.get("occlusion_contract")
        require(isinstance(contract, Mapping), f"contrat d'occlusion invalide : {area}")
        label = f"contrat d'occlusion {area}"
        expected_map_label = f"map-{area.lower()}"
        expected_animation_label = f"animation-{area.lower()}"
        require(
            contract.get("mode") == "native-wed-bridge-v1",
            f"mode d'occlusion invalide : {area}",
        )
        require(
            candidate.get("component_label") == expected_animation_label
            and candidate.get("payload_group") == expected_animation_label,
            f"identité du composant animation hors zone : {area}",
        )
        map_component_id = schema_integer(
            contract.get("map_component_id"), f"map_component_id {label}", minimum=1
        )
        animation_component_id = schema_integer(
            candidate.get("component_id"), f"component_id animation {label}", minimum=3000
        )
        require(
            map_component_id not in animation_component_ids,
            f"component_id map en collision avec une animation : {area}",
        )
        require(
            contract.get("map_component_label") == expected_map_label,
            f"label du composant map hors zone : {area}",
        )
        require(
            contract.get("map_payload_group") == expected_map_label,
            f"payload group map hors zone : {area}",
        )

        source_spec = schema_string(
            contract.get("source_spec"), f"source_spec {label}", pattern=RELATIVE_PATH_RE
        )
        source = schema_string(
            contract.get("source"), f"source WED {label}", pattern=RELATIVE_PATH_RE
        )
        qa_evidence = schema_string(
            contract.get("qa_evidence"), f"preuve QA {label}", pattern=RELATIVE_PATH_RE
        )
        correction_root = f"maps/wed-corrections/{area}/"
        require(
            source_spec.startswith(correction_root) and source_spec.endswith(".json"),
            f"spécification WED hors zone : {area}",
        )
        require(
            source.startswith(correction_root)
            and Path(source).name == f"{area}.WED",
            f"source WED hors zone : {area}",
        )
        destination = schema_string(contract.get("destination"), f"destination {label}")
        require(destination == f"override/{area}.WED", f"destination WED hors zone : {area}")

        source_spec_path = _resolve_occlusion_file(source_spec, label=f"spécification {area}")
        source_path = _resolve_occlusion_file(source, label=f"source WED {area}")
        evidence_path = _resolve_occlusion_file(qa_evidence, label=f"preuve QA {area}")
        expected_bytes = schema_integer(contract.get("bytes"), f"bytes {label}", minimum=1)
        expected_hash = schema_hash(contract.get("sha256"), f"sha256 {label}")
        evidence_hash = schema_hash(
            contract.get("qa_evidence_sha256"), f"qa_evidence_sha256 {label}"
        )
        require(source_path.stat().st_size == expected_bytes, f"taille WED invalide : {area}")
        require(sha256_file(source_path) == expected_hash, f"hash WED invalide : {area}")
        require(sha256_file(evidence_path) == evidence_hash, f"hash preuve occlusion invalide : {area}")

        spec = load_json(source_spec_path)
        require(
            spec.get("schema") == "bg2-upscale-wed-wall-polygon-spec-v1"
            and spec.get("status") == "validated-installed"
            and spec.get("area") == area,
            f"spécification WED non validée pour la zone : {area}",
        )
        validated_output = spec.get("validated_output")
        require(isinstance(validated_output, Mapping), f"sortie WED validée absente : {area}")
        require(
            validated_output.get("release_source") == source
            and validated_output.get("file") == f"{area}.WED",
            f"source release WED incohérente : {area}",
        )
        require(
            schema_integer(validated_output.get("bytes"), f"bytes spec WED {area}", minimum=1)
            == expected_bytes,
            f"taille WED différente dans la spécification : {area}",
        )
        require(
            normalize_hash(validated_output.get("sha256"), f"hash spec WED {area}")
            == expected_hash,
            f"hash WED différent dans la spécification : {area}",
        )
        qa = spec.get("qa")
        require(
            isinstance(qa, Mapping)
            and qa.get("verdict") == "validated-installed"
            and qa.get("validated_by") == "user"
            and qa.get("release_manifest") == "selected-pending-content-regeneration",
            f"correction WED non sélectionnée pour la release : {area}",
        )
        revalidation = qa.get("revalidation")
        require(
            isinstance(revalidation, Mapping)
            and revalidation.get("verdict") == "validated-installed"
            and revalidation.get("evidence") == qa_evidence
            and normalize_hash(
                revalidation.get("registry_sha256"), f"registre revalidation WED {area}"
            )
            == schema_hash(candidate.get("registry_sha256"), f"registre candidat {area}"),
            f"revalidation WED/renderer incohérente : {area}",
        )
        authority = map_authorities.get(area)
        require(
            authority is not None
            and authority.get("status") == "validated-installed"
            and authority.get("build") == "yes"
            and bool(str(authority.get("runs", "")).strip()),
            f"carte non validée-installed dans areas.csv : {area}",
        )

        renderer = runtime.get("renderer")
        area_runtime = (
            renderer.get("area_animation_runtime")
            if isinstance(renderer, Mapping)
            else None
        )
        bridge = (
            area_runtime.get("native_occlusion_bridge")
            if isinstance(area_runtime, Mapping)
            else None
        )
        registry_version = schema_integer(
            candidate.get("registry_version"), f"registry_version {label}"
        )
        supported_registry_versions = (
            area_runtime.get("supported_registry_versions")
            if isinstance(area_runtime, Mapping)
            else None
        )
        require(
            isinstance(area_runtime, Mapping)
            and area_runtime.get("status") == "integrated"
            and area_runtime.get("config_owner") == contract.get("ini_owner")
            and isinstance(supported_registry_versions, list)
            and registry_version in supported_registry_versions,
            f"runtime animation incompatible avec l'occlusion : {area}",
        )
        require(
            isinstance(bridge, Mapping)
            and bridge.get("required") is True
            and bridge.get("ini_section") == contract.get("ini_section")
            and bridge.get("ini_key") == contract.get("ini_key")
            and bridge.get("qa_evidence") == qa_evidence
            and bridge.get("wed_correction") == source_spec,
            f"contrat runtime du bridge d'occlusion incohérent : {area}",
        )
        owner = owned_ini_keys.get(contract.get("ini_owner"))
        section = owner.get(contract.get("ini_section")) if isinstance(owner, Mapping) else None
        runtime_value = section.get(contract.get("ini_key")) if isinstance(section, Mapping) else None
        require(
            runtime_value == contract.get("ini_value") == "true",
            f"le Core release n'active pas le bridge d'occlusion : {area}",
        )

        if not validate_release_mapping:
            continue
        map_components = [
            item
            for item in component_rows
            if isinstance(item, Mapping)
            and type(item.get("id")) is int
            and item.get("id") == map_component_id
        ]
        require(len(map_components) == 1, f"composant map absent ou dupliqué : {area}")
        map_component = map_components[0]
        require(
            map_component.get("label") == expected_map_label
            and map_component.get("status") == "validated"
            and map_component.get("payload_groups") == [expected_map_label]
            and isinstance(map_component.get("depends_on"), list)
            and 0 in map_component["depends_on"],
            f"composant map incohérent : {area}",
        )
        require(
            len(
                [
                    item
                    for item in component_rows
                    if isinstance(item, Mapping) and item.get("label") == expected_map_label
                ]
            )
            == 1,
            f"label de composant map absent ou dupliqué : {area}",
        )

        area_map_entries = [
            item
            for item in content_rows
            if isinstance(item, Mapping)
            and item.get("kind") == "map"
            and item.get("area") == area
        ]
        require(bool(area_map_entries), f"contenu du composant map absent : {area}")
        for map_entry in area_map_entries:
            require(
                type(map_entry.get("component_id")) is int
                and map_entry.get("component_id") == map_component_id
                and map_entry.get("component_label") == expected_map_label
                and map_entry.get("payload_group") == expected_map_label,
                f"identité du composant map incohérente dans content.json : {area}",
            )

        wed_entries = [
            item
            for item in content_rows
            if isinstance(item, Mapping) and item.get("destination") == destination
        ]
        require(len(wed_entries) == 1, f"entrée WED release absente ou dupliquée : {area}")
        wed_entry = wed_entries[0]
        wed_component_id = schema_integer(
            wed_entry.get("component_id"), f"component_id content WED {area}"
        )
        wed_bytes = schema_integer(wed_entry.get("bytes"), f"bytes content WED {area}")
        wed_scale = schema_integer(wed_entry.get("scale"), f"scale content WED {area}")
        wed_install_order = schema_integer(
            wed_entry.get("install_order"), f"install_order content WED {area}"
        )
        require(
            wed_entry.get("kind") == "map"
            and wed_entry.get("area") == area
            and wed_component_id == map_component_id
            and wed_entry.get("component_label") == expected_map_label
            and wed_entry.get("payload_group") == expected_map_label
            and wed_entry.get("source") == source
            and wed_entry.get("source_run") == Path(source).parent.as_posix()
            and wed_bytes == expected_bytes
            and normalize_hash(wed_entry.get("sha256"), f"hash content WED {area}")
            == expected_hash
            and wed_entry.get("qa_status") == "validated"
            and wed_scale == 4
            and wed_entry.get("model") == "WED-Native-Occlusion-v1"
            and wed_install_order == map_component_id
            and wed_entry.get("replaces_component_output") is False,
            f"entrée WED release incohérente : {area}",
        )

        if require_animation_dependencies:
            animation_components = [
                item
                for item in component_rows
                if isinstance(item, Mapping)
                and type(item.get("id")) is int
                and item.get("id") == animation_component_id
            ]
            require(
                len(animation_components) == 1,
                f"composant animation absent ou dupliqué pour l'occlusion : {area}",
            )
            dependencies = animation_components[0].get("depends_on")
            require(
                isinstance(dependencies, list)
                and 0 in dependencies
                and map_component_id in dependencies,
                f"dépendance animation vers le composant map absente : {area}",
            )


def renderer_contract(registry_version: int) -> str:
    require(registry_version in {2, 3}, f"version de registre release invalide : {registry_version}")
    return (
        "area-animation-per-area-registry-v3-position-timed-timeline"
        if registry_version == 3
        else "area-animation-per-area-registry-v2-timed-timeline"
    )


def canonical_sha256(value: Any) -> str:
    data = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(data)


def resource_group(resources: Sequence[Mapping[str, Any]], resref: str) -> list[dict[str, Any]]:
    group = [dict(item) for item in resources if str(item.get("resref", "")).upper() == resref]
    require(bool(group), f"ressource absente du pack : {resref}")
    return sorted(
        group,
        key=lambda item: (
            integer(item.get("variant_index", 0), f"variante {resref}"),
            canonical_sha256(item),
        ),
    )


def manifest_resrefs(manifest: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str):
            normalized = value.strip().upper()
            if RESREF_RE.fullmatch(normalized):
                values.add(normalized)
        elif isinstance(value, Mapping):
            for key in ("asset", "resref", "bam_resref", "resource_resref"):
                if key in value:
                    add(value[key])

    for key in ("asset", "resref", "bam_resref"):
        add(manifest.get(key))
    for key in (
        "resources",
        "timed_resources",
        "resrefs",
        "targets",
        "requested_resrefs",
        "resolved_resrefs",
    ):
        items = manifest.get(key)
        if isinstance(items, list):
            for item in items:
                add(item)
    request = manifest.get("request")
    if isinstance(request, Mapping):
        for key in ("resref", "resrefs", "targets", "requested_resrefs", "resolved_resrefs"):
            items = request.get(key)
            if isinstance(items, list):
                for item in items:
                    add(item)
            else:
                add(items)
    return values


def registry_rows() -> dict[str, dict[str, str]]:
    with REGISTRY.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fieldnames = reader.fieldnames or []
        require(len(fieldnames) == len(set(fieldnames)), "en-têtes dupliqués dans le registre animation")
        require(
            {"resref", "status", "areas", "selected_run", "qa_decision", "qa_date"}
            <= set(fieldnames),
            "colonnes requises absentes du registre animation",
        )
        rows = list(reader)
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        require(None not in row, "cellules surnuméraires dans le registre animation")
        resref = normalize_resref(row.get("resref", ""))
        require(resref not in result, f"resref dupliqué dans le registre : {resref}")
        result[resref] = row
    return result


def selection_area_record(selection: Mapping[str, Any], area: str) -> Mapping[str, Any] | None:
    source_pack = selection.get("source_pack")
    if not isinstance(source_pack, Mapping):
        return None
    records = source_pack.get("areas", [])
    if not isinstance(records, list):
        return None
    matches = [
        item
        for item in records
        if isinstance(item, Mapping) and str(item.get("area", "")).upper() == area
    ]
    require(len(matches) <= 1, f"zone {area} dupliquée dans une sélection")
    return matches[0] if matches else None


def load_area_selections(
    area: str, requested_pack: str | None
) -> tuple[str, dict[str, tuple[Path, dict[str, Any], Mapping[str, Any]]]]:
    candidates: dict[str, dict[str, tuple[Path, dict[str, Any], Mapping[str, Any]]]] = {}
    if SELECTIONS.is_dir():
        for path in sorted(SELECTIONS.glob("*.json"), key=lambda item: item.name.casefold()):
            selection = load_json(path)
            qa_decision = selection.get("qa_decision")
            if not isinstance(qa_decision, Mapping) or str(qa_decision.get("status", "")) != "accepted":
                continue
            area_record = selection_area_record(selection, area)
            if area_record is None or area not in {
                str(item).upper() for item in selection.get("tested_areas", [])
            }:
                continue
            pack_path = repo_path(resolve_repo_path(str(area_record.get("path", "")), forbidden=True))
            resref = normalize_resref(str(selection.get("resref", "")))
            require(path.stem.upper() == resref, f"nom de sélection incohérent : {repo_path(path)}")
            require(resref not in candidates.setdefault(pack_path, {}), f"sélection dupliquée : {resref}/{pack_path}")
            candidates[pack_path][resref] = (path, selection, area_record)

    if requested_pack:
        requested = resolve_repo_path(requested_pack, forbidden=True)
        if requested.is_dir() and requested.name.upper() != area and (requested / area).is_dir():
            requested = requested / area
        selected_pack = repo_path(requested)
        require(selected_pack in candidates, f"aucune sélection QA ne référence {selected_pack}")
    else:
        require(bool(candidates), f"aucune sélection QA acceptée ne couvre {area}")
        require(
            len(candidates) == 1,
            "plusieurs packs QA couvrent la zone ; préciser --pack : "
            + ", ".join(sorted(candidates)),
        )
        selected_pack = next(iter(candidates))
    return selected_pack, candidates[selected_pack]


def validate_pack(
    area: str, pack_path: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], Path, Path]:
    pack = resolve_repo_path(pack_path, forbidden=True)
    pack_relative = Path(repo_path(pack))
    require(
        len(pack_relative.parts) == 4
        and tuple(part.casefold() for part in pack_relative.parts[:2])
        == ("animations", "packs-par-zone"),
        f"pack final hors layout canonique : {pack_path}",
    )
    require(pack.name.upper() == area, f"pack final rangé sous une autre zone : {pack_path}")
    require(pack.is_dir(), f"pack de zone absent : {pack_path}")
    manifest_path = pack / "manifest.json"
    registry_path = pack / "AreaAnimations-X4.registry"
    manifest, resources = validate_runtime_pack(pack)
    require(manifest.get("schema") == "bg2-upscale-area-animation-runtime-pack-v2", "schéma de pack animation inattendu")
    require(manifest.get("status") == "completed", "pack animation non terminé")
    require(integer(manifest.get("scale", 0), "scale pack") == 4, "pack animation non x4")
    require(manifest.get("runtime_budget_enforced", True) is True, "pack d'authoring hors budget interdit en release")
    require(manifest.get("authoring_pack_for_area_split") is not True, "pack d'authoring non découpé interdit en release")
    require(str(manifest.get("area_id", "")).upper() == area, f"pack destiné à une autre zone : {manifest.get('area_id')}")
    require(registry_path.is_file(), f"registre du pack absent : {repo_path(registry_path)}")
    registry_hash = sha256_file(registry_path)
    require(registry_hash == normalize_hash(manifest.get("registry_sha256"), "registre pack"), "hash du registre du pack incohérent")
    require(registry_path.stat().st_size == integer(manifest.get("registry_bytes", -1), "taille registre pack"), "taille du registre du pack incohérente")
    resrefs = sorted({normalize_resref(str(item.get("resref", ""))) for item in resources})
    return manifest, resources, resrefs, manifest_path, registry_path


def validate_decision(
    *,
    area: str,
    resref: str,
    selection_path: Path,
    selection: Mapping[str, Any],
    area_record: Mapping[str, Any],
    pack_path: str,
    pack_manifest_hash: str,
    registry_hash: str,
) -> tuple[Path, dict[str, Any], str]:
    require(selection.get("result_kind") == "x4", f"sélection non x4 inéligible à la release : {resref}")
    require(str(selection.get("resref", "")).upper() == resref, f"sélection incohérente : {repo_path(selection_path)}")
    require(selection.get("asset_id") == f"animations:bam:{resref}", f"asset_id de sélection incohérent : {resref}")
    require(selection_path == SELECTIONS / f"{resref}.json", f"chemin de sélection non canonique : {resref}")
    row_qa = selection.get("qa_decision", {})
    require(isinstance(row_qa, Mapping), f"référence QA absente : {resref}")
    decision_path = resolve_repo_path(str(row_qa.get("path", "")))
    require(decision_path.is_file(), f"décision QA absente : {repo_path(decision_path)}")
    require(
        decision_path.parent == ROOT / "animations" / "index" / "qa-decisions" / resref,
        f"décision QA hors dossier asset : {resref}",
    )
    decision_hash = sha256_file(decision_path)
    require(decision_hash == normalize_hash(row_qa.get("sha256"), f"décision {resref}"), f"hash de décision QA incohérent : {resref}")
    decision = load_json(decision_path)
    require(int(decision.get("schema_version", 0)) == 1, f"version de décision QA inconnue : {resref}")
    require(decision.get("status") == "accepted", f"décision QA non acceptée : {resref}")
    require(decision.get("decision_origin") == "explicit-user-ingame-qa", f"origine QA invalide : {resref}")
    require(decision.get("result_kind") == "x4", f"décision QA non x4 inéligible à la release : {resref}")
    require(str(decision.get("resref", "")).upper() == resref, f"décision QA destinée à un autre asset : {resref}")
    require(decision.get("asset_id") == f"animations:bam:{resref}", f"asset_id de décision incohérent : {resref}")
    require(str(row_qa.get("decision_date", "")) == str(decision.get("decision_date", "")), f"date de décision différente : {resref}")
    require(area in {str(item).upper() for item in decision.get("tested_areas", [])}, f"{resref} non testé dans {area}")
    require(selection.get("tested_areas") == decision.get("tested_areas"), f"zones de sélection différentes de la décision : {resref}")
    require(selection.get("lineage") == decision.get("lineage"), f"lineage de sélection différent de la décision : {resref}")
    require(selection.get("source_pack") == decision.get("source_pack"), f"pack de sélection différent de la décision : {resref}")

    source_pack = selection.get("source_pack")
    require(isinstance(source_pack, Mapping), f"pack source absent de la sélection : {resref}")
    source_pack_path = resolve_repo_path(str(source_pack.get("path", "")), forbidden=True)
    source_pack_manifest = resolve_repo_path(str(source_pack.get("manifest_path", "")), forbidden=True)
    require(source_pack_path.is_dir(), f"pack source absent : {resref}")
    require(source_pack_manifest.is_file(), f"manifest du pack source absent : {resref}")
    require(source_pack_manifest == source_pack_path / "manifest.json", f"manifest de pack source non canonique : {resref}")
    require(sha256_file(source_pack_manifest) == normalize_hash(source_pack.get("manifest_sha256"), f"pack source {resref}"), f"hash du pack source incohérent : {resref}")

    require(repo_path(resolve_repo_path(str(area_record.get("path", "")), forbidden=True)) == pack_path, f"pack de sélection différent : {resref}")
    require(normalize_hash(area_record.get("manifest_sha256"), f"pack sélection {resref}") == pack_manifest_hash, f"manifest de pack non couvert par la QA : {resref}")
    require(normalize_hash(area_record.get("registry_sha256"), f"registre sélection {resref}") == registry_hash, f"registre de pack non couvert par la QA : {resref}")

    decision_area = selection_area_record(decision, area)
    require(decision_area is not None, f"décision sans preuve du pack {area} : {resref}")
    require(repo_path(resolve_repo_path(str(decision_area.get("path", "")), forbidden=True)) == pack_path, f"pack de décision différent : {resref}")
    require(normalize_hash(decision_area.get("manifest_sha256"), f"pack décision {resref}") == pack_manifest_hash, f"hash de pack de décision différent : {resref}")
    require(normalize_hash(decision_area.get("registry_sha256"), f"registre décision {resref}") == registry_hash, f"hash de registre de décision différent : {resref}")

    final_run = decision.get("final_run")
    require(isinstance(final_run, Mapping), f"run final absent de la décision : {resref}")
    run_path = resolve_repo_path(str(final_run.get("path", "")), forbidden=True)
    manifest_path = resolve_repo_path(str(final_run.get("manifest_path", "")), forbidden=True)
    run_relative = repo_path(run_path)
    run_parts = Path(run_relative).parts
    run_parts_lower = tuple(part.casefold() for part in run_parts)
    valid_layout = (
        len(run_parts) == 3
        and run_parts_lower[0:2] in (("animations", "runs"), ("animations", "batches"))
    ) or (
        len(run_parts) == 5
        and run_parts_lower[0:2] == ("animations", "ressources")
        and run_parts[2].upper() == resref
        and run_parts_lower[3] == "runs"
    )
    require(valid_layout, f"run final hors layout canonique/legacy : {resref}/{run_relative}")
    require(run_path.is_dir(), f"run final absent : {repo_path(run_path)}")
    require(manifest_path.is_file(), f"manifest de run final absent : {repo_path(manifest_path)}")
    require(manifest_path == run_path / "manifest.json", f"manifest de run final non canonique : {resref}")
    try:
        manifest_path.relative_to(run_path)
    except ValueError as error:
        raise ReleasePromotionError(f"manifest hors run final : {resref}") from error
    require(sha256_file(manifest_path) == normalize_hash(final_run.get("manifest_sha256"), f"run final {resref}"), f"hash de run final incohérent : {resref}")
    final_manifest = load_json(manifest_path)
    require(
        final_manifest.get("schema") == final_run.get("schema")
        and final_manifest.get("status") == final_run.get("status"),
        f"identité du manifeste de run différente : {resref}",
    )
    require(str(final_manifest.get("status", "")) in FINAL_RUN_STATUSES, f"run final non terminé : {resref}")
    require(resref in manifest_resrefs(final_manifest), f"run final ne déclare pas {resref}")
    require(selection.get("selected_run") == final_run, f"run sélectionné différent de la décision : {resref}")
    validate_workflow_resref(resref)
    return decision_path, decision, decision_hash


def source_runs_from_decisions(
    decisions: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str, str], set[str]] = {}
    for resref, decision in decisions.items():
        final_run = decision["final_run"]
        path = repo_path(resolve_repo_path(str(final_run["path"])))
        manifest_path = repo_path(resolve_repo_path(str(final_run["manifest_path"])))
        digest = normalize_hash(final_run["manifest_sha256"], f"run final {resref}")
        merged.setdefault((path, manifest_path, digest), set()).add(resref)
    return [
        {
            "path": path,
            "manifest_path": manifest_path,
            "manifest_sha256": digest,
            "role": "final",
            "asset_ids": sorted(asset_ids),
        }
        for (path, manifest_path, digest), asset_ids in sorted(merged.items())
    ]


def allocate_component_id(candidates: Sequence[Mapping[str, Any]]) -> int:
    used = {integer(item.get("component_id", -1), "component_id candidat") for item in candidates}
    if COMPONENTS.is_file():
        used.update(
            integer(item.get("id", -1), "component_id components.json")
            for item in load_json(COMPONENTS).get("components", [])
        )
    value = 3000
    while value in used:
        value += 1
    return value


def validate_candidate_pack_metadata(
    candidate: Mapping[str, Any],
    area: str,
    manifest: Mapping[str, Any],
    resrefs: Sequence[str],
    manifest_path: Path,
    registry_path: Path,
) -> None:
    version = integer(manifest.get("registry_version"), f"registre pack {area}")
    require(candidate.get("pack_manifest") == "manifest.json", f"manifest candidat non canonique : {area}")
    require(
        normalize_hash(candidate.get("pack_manifest_sha256"), f"manifest candidat {area}")
        == sha256_file(manifest_path),
        f"hash manifest candidat incohérent : {area}",
    )
    require(candidate.get("registry") == "AreaAnimations-X4.registry", f"registre candidat invalide : {area}")
    require(integer(candidate.get("registry_version"), f"version candidat {area}") == version, f"version registre candidat incohérente : {area}")
    require(normalize_hash(candidate.get("registry_sha256"), f"registre candidat {area}") == sha256_file(registry_path), f"hash registre candidat incohérent : {area}")
    require(integer(candidate.get("registry_bytes"), f"taille registre candidat {area}") == registry_path.stat().st_size, f"taille registre candidat incohérente : {area}")
    require(candidate.get("renderer_contract") == renderer_contract(version), f"contrat renderer candidat incohérent : {area}")
    required = candidate.get("required_resrefs")
    require(isinstance(required, list) and required == sorted(set(map(str, required))), f"required_resrefs candidat non canonique : {area}")
    require(required == list(resrefs), f"inventaire candidat différent du pack : {area}")


def validate_candidate_source_runs(
    candidate: Mapping[str, Any],
    *,
    area: str,
    expected_asset_ids: Sequence[str] | None,
    require_structured: bool,
) -> list[dict[str, Any]]:
    """Validate physical run provenance when a candidate uses structured runs."""

    raw_runs = candidate.get("source_runs")
    if raw_runs is None:
        require(not require_structured, f"runs source structurés absents : {area}")
        source_run = candidate.get("source_run")
        require(
            isinstance(source_run, str) and bool(source_run.strip()),
            f"provenance de run legacy absente : {area}",
        )
        return []

    require(isinstance(raw_runs, list) and bool(raw_runs), f"runs source invalides : {area}")
    normalized_runs: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    seen_assets: set[str] = set()
    for item in raw_runs:
        require(isinstance(item, Mapping), f"run source invalide : {area}")
        require(item.get("role") == "final", f"rôle de run source non final : {area}")
        run_path = resolve_repo_path(str(item.get("path", "")), forbidden=True)
        run_relative = repo_path(run_path)
        parts = Path(run_relative).parts
        folded = tuple(part.casefold() for part in parts)
        valid_layout = (
            len(parts) == 3
            and folded[:2] in (("animations", "runs"), ("animations", "batches"))
        ) or (
            len(parts) == 5
            and folded[:2] == ("animations", "ressources")
            and folded[3] == "runs"
            and bool(RESREF_RE.fullmatch(parts[2].upper()))
        )
        require(valid_layout and not run_relative.casefold().endswith(".partial"), f"layout de run source invalide : {run_relative}")
        require(run_relative == str(item.get("path", "")), f"chemin de run source non canonique : {area}")
        require(run_relative not in seen_paths, f"run source dupliqué : {run_relative}")
        seen_paths.add(run_relative)
        require(run_path.is_dir(), f"run source absent : {run_relative}")

        manifest_path = resolve_repo_path(str(item.get("manifest_path", "")), forbidden=True)
        manifest_relative = repo_path(manifest_path)
        require(manifest_path == run_path / "manifest.json", f"manifest hors run source : {run_relative}")
        require(manifest_relative == str(item.get("manifest_path", "")), f"chemin de manifeste source non canonique : {run_relative}")
        require(manifest_path.is_file(), f"manifest de run source absent : {manifest_relative}")
        manifest_hash = normalize_hash(item.get("manifest_sha256"), f"run source {run_relative}")
        require(sha256_file(manifest_path) == manifest_hash, f"hash de run source incohérent : {run_relative}")
        manifest = load_json(manifest_path)
        require(str(manifest.get("status", "")) in FINAL_RUN_STATUSES, f"run source non terminé : {run_relative}")

        raw_assets = item.get("asset_ids")
        require(isinstance(raw_assets, list) and bool(raw_assets), f"assets de run source absents : {run_relative}")
        assets = [normalize_resref(str(value)) for value in raw_assets]
        require(assets == sorted(set(assets)), f"assets de run source non canoniques : {run_relative}")
        if len(parts) == 5:
            require(len(assets) == 1 and assets[0] == parts[2].upper(), f"run mono-asset rangé sous un autre resref : {run_relative}")
        declared = manifest_resrefs(manifest)
        for resref in assets:
            require(resref not in seen_assets, f"run source dupliqué pour {resref} : {area}")
            require(resref in declared, f"manifest de run source sans {resref} : {run_relative}")
            seen_assets.add(resref)
        normalized_runs.append(dict(item))

    if expected_asset_ids is not None:
        expected = sorted({normalize_resref(str(value)) for value in expected_asset_ids})
        require(sorted(seen_assets) == expected, f"couverture des runs source incohérente : {area}")
    return normalized_runs


def validate_approval_shape(
    approval: Mapping[str, Any], *, area: str, label: str
) -> int:
    """Enforce the release QA schema invariants without trusting caller-side Test-Json."""

    required = {
        "schema_version",
        "area",
        "status",
        "decision_date",
        "decision_origin",
        "recorded_at_utc",
        "source_pack",
        "pack_manifest_sha256",
        "registry",
        "registry_version",
        "registry_sha256",
        "required_resrefs",
        "evidence",
        "decision",
    }
    allowed = required | {"$schema"}
    require(set(approval) == required or set(approval) == allowed, f"champs d'approbation invalides : {label}")
    if "$schema" in approval:
        schema_string(approval["$schema"], f"$schema {label}")
    schema_value = approval.get("schema_version")
    require(type(schema_value) is int and schema_value in {1, 2, 3}, f"version d'approbation invalide : {label}")
    schema = int(schema_value)
    require(
        isinstance(approval.get("area"), str)
        and AREA_RE.fullmatch(approval["area"])
        and approval["area"] == area,
        f"zone d'approbation invalide : {label}",
    )
    require(approval.get("status") == "accepted", f"statut d'approbation invalide : {label}")
    require(bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", str(approval.get("decision_date", "")))), f"date d'approbation invalide : {label}")
    require(isinstance(approval.get("recorded_at_utc"), str) and len(str(approval.get("recorded_at_utc"))) >= 20, f"horodatage d'approbation invalide : {label}")
    require(isinstance(approval.get("decision"), str) and bool(str(approval.get("decision")).strip()), f"décision d'approbation absente : {label}")
    schema_string(approval.get("source_pack"), f"source_pack {label}", pattern=PACK_PATH_RE)
    schema_hash(approval.get("pack_manifest_sha256"), f"manifest {label}")
    schema_hash(approval.get("registry_sha256"), f"registre {label}")
    require(approval.get("registry") == "AreaAnimations-X4.registry", f"registre d'approbation invalide : {label}")
    registry_version = approval.get("registry_version")
    require(type(registry_version) is int and registry_version in {2, 3}, f"version registre d'approbation invalide : {label}")
    raw_resrefs = approval.get("required_resrefs")
    require(isinstance(raw_resrefs, list) and bool(raw_resrefs), f"inventaire d'approbation absent : {label}")
    normalized_resrefs = schema_resrefs(raw_resrefs, f"required_resrefs {label}")
    require(raw_resrefs == sorted(normalized_resrefs), f"inventaire d'approbation non canonique : {label}")
    origins = {
        1: "preserved-existing-user-qa",
        2: "explicit-user-ingame-qa",
        3: "explicit-user-ingame-qa-with-byte-identical-carry-forward",
    }
    require(approval.get("decision_origin") == origins[schema], f"origine d'approbation invalide : {label}")
    evidence = approval.get("evidence")
    require(isinstance(evidence, list) and bool(evidence), f"preuves d'approbation absentes : {label}")
    legacy_kinds = {"run-qa-approval", "canonical-registry", "canonical-alpha-corrections"}
    direct_count = 0
    continuity_count = 0
    for item in evidence:
        require(isinstance(item, Mapping), f"preuve d'approbation invalide : {label}")
        kind = item.get("kind")
        base_keys = {"kind", "path", "sha256", "accepted_resrefs"}
        if kind == "byte-identical-release-continuity":
            expected_keys = base_keys | {
                "source_pack",
                "pack_manifest_sha256",
                "registry_version",
                "renderer_contract",
                "resource_sha256",
            }
            continuity_count += 1
        else:
            expected_keys = base_keys
            if kind == "ingame-qa-decision":
                direct_count += 1
        require(set(item) == expected_keys, f"champs de preuve invalides : {label}/{kind}")
        path_value = item.get("path")
        schema_hash(item.get("sha256"), f"preuve {label}")
        accepted = item.get("accepted_resrefs")
        normalized = schema_resrefs(
            accepted,
            f"accepted_resrefs {label}",
            single=kind in {"ingame-qa-decision", "byte-identical-release-continuity"},
        )
        if kind in {"ingame-qa-decision", "byte-identical-release-continuity"}:
            require(len(normalized) == 1, f"preuve multi-resrefs interdite : {label}")
        if schema == 1:
            require(kind in legacy_kinds, f"type de preuve QA v1 invalide : {label}/{kind}")
            schema_string(path_value, f"path {label}/{kind}", pattern=RELATIVE_PATH_RE)
        elif schema == 2:
            require(kind == "ingame-qa-decision", f"type de preuve QA v2 invalide : {label}/{kind}")
            schema_string(path_value, f"path {label}/{kind}", pattern=QA_DECISION_PATH_RE)
        else:
            require(kind in {"ingame-qa-decision", "byte-identical-release-continuity"}, f"type de preuve QA v3 invalide : {label}/{kind}")
            schema_string(
                path_value,
                f"path {label}/{kind}",
                pattern=QA_DECISION_PATH_RE if kind == "ingame-qa-decision" else QA_APPROVAL_PATH_RE,
            )
        if kind == "byte-identical-release-continuity":
            schema_string(item.get("source_pack"), f"source_pack {label}", pattern=PACK_PATH_RE)
            schema_hash(item.get("pack_manifest_sha256"), f"pack_manifest_sha256 {label}")
            require(
                schema_integer(item.get("registry_version"), f"registry_version {label}") in {2, 3},
                f"version de continuité invalide : {label}",
            )
            require(item.get("renderer_contract") in RENDERER_CONTRACTS, f"contrat renderer de continuité invalide : {label}")
            schema_hash(item.get("resource_sha256"), f"resource_sha256 {label}")
    if schema == 2:
        require(direct_count == len(evidence), f"approbation QA v2 sans preuves directes exclusives : {label}")
    if schema == 3:
        require(direct_count > 0 and continuity_count > 0, f"approbation QA v3 sans preuve directe et continuité : {label}")
    return schema


def verify_legacy_evidence(
    approval: Mapping[str, Any],
    *,
    area: str,
    expected_resrefs: Sequence[str],
    evidence_cache: set[tuple[str, str, str]] | None = None,
) -> None:
    """Verify the sealed legacy evidence, including historical CSV hashes."""

    coverage: set[str] = set()
    for item in approval["evidence"]:
        kind = str(item["kind"])
        relative = str(item["path"])
        path = resolve_repo_path(relative)
        require(repo_path(path) == relative, f"chemin de preuve QA legacy non canonique : {area}/{relative}")
        if kind == "run-qa-approval":
            require(bool(re.fullmatch(r"animations/runs/[^/]+/qa-approval[.]json", relative)), f"chemin de preuve run QA legacy invalide : {area}/{relative}")
        elif kind == "canonical-registry":
            require(relative == "animations/index/animation_upscale_registry.csv", f"registre QA legacy inattendu : {area}/{relative}")
        elif kind == "canonical-alpha-corrections":
            require(relative == "animations/index/animation_alpha_corrections.csv", f"registre alpha QA legacy inattendu : {area}/{relative}")
        expected_hash = normalize_hash(item.get("sha256"), f"preuve QA legacy {area}")
        cache_key = (kind, relative, expected_hash)
        if evidence_cache is None or cache_key not in evidence_cache:
            current_matches = path.is_file() and sha256_file(path) == expected_hash
            if not current_matches:
                adapter = ROOT / "pipeline" / "scripts" / "verify_historical_git_evidence.py"
                require(adapter.is_file(), f"adaptateur de preuve historique absent : {area}")
                completed = subprocess.run(
                    (sys.executable, str(adapter), "--path", relative, "--sha256", expected_hash, "--quiet"),
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                require(completed.returncode == 0, f"hash de preuve QA legacy introuvable : {area}/{relative}")
            if kind == "run-qa-approval":
                require(path.is_file(), f"preuve run QA legacy absente : {area}/{relative}")
                run_approval = load_json(path)
                require(run_approval.get("status") == "accepted", f"preuve run QA legacy non acceptée : {area}/{relative}")
            if evidence_cache is not None:
                evidence_cache.add(cache_key)
        coverage.update(normalize_resref(str(value)) for value in item["accepted_resrefs"])
    require(sorted(coverage) == list(expected_resrefs), f"couverture des preuves QA legacy incohérente : {area}")


def load_candidate_approval(
    candidate: Mapping[str, Any],
    area: str,
    manifest: Mapping[str, Any],
    resrefs: Sequence[str],
    manifest_path: Path,
    registry_path: Path,
) -> tuple[Path, dict[str, Any]]:
    approval_path = resolve_repo_path(str(candidate.get("qa_approval", "")))
    require(
        approval_path.parent == QA_APPROVALS / area,
        f"approbation QA hors dossier zone : {area}",
    )
    approval_hash = sha256_file(approval_path)
    require(
        approval_hash == normalize_hash(candidate.get("qa_approval_sha256"), f"approbation {area}"),
        f"hash approbation candidat incohérent : {area}",
    )
    approval = load_json(approval_path)
    validate_approval_shape(approval, area=area, label=repo_path(approval_path))
    require(str(approval.get("area", "")).upper() == area and approval.get("status") == "accepted", f"approbation QA invalide : {area}")
    require(approval.get("source_pack") == candidate.get("source_pack"), f"pack différent entre candidat et approbation : {area}")
    require(normalize_hash(approval.get("pack_manifest_sha256"), f"manifest approbation {area}") == sha256_file(manifest_path), f"manifest différent dans l'approbation : {area}")
    version = integer(manifest.get("registry_version"), f"registre pack {area}")
    require(integer(approval.get("registry_version"), f"registre approbation {area}") == version, f"version registre différente dans l'approbation : {area}")
    require(approval.get("registry") == "AreaAnimations-X4.registry", f"registre d'approbation invalide : {area}")
    require(normalize_hash(approval.get("registry_sha256"), f"registre approbation {area}") == sha256_file(registry_path), f"registre différent dans l'approbation : {area}")
    require(approval.get("required_resrefs") == list(resrefs), f"inventaire différent dans l'approbation : {area}")
    return approval_path, approval


def carry_evidence_from_existing(
    *,
    area: str,
    existing: Mapping[str, Any],
    new_manifest: Mapping[str, Any],
    new_resources: Sequence[Mapping[str, Any]],
    new_resrefs: Sequence[str],
    carried_resrefs: Sequence[str],
) -> list[dict[str, Any]]:
    require(existing.get("approval_status") == "approved-for-release", f"base release non approuvée : {area}")
    old_pack_path = repo_path(resolve_repo_path(str(existing.get("source_pack", "")), forbidden=True))
    old_manifest, old_resources, old_resrefs, old_manifest_path, old_registry_path = validate_pack(area, old_pack_path)
    validate_candidate_pack_metadata(existing, area, old_manifest, old_resrefs, old_manifest_path, old_registry_path)
    old_approval_path, old_approval = load_candidate_approval(
        existing,
        area,
        old_manifest,
        old_resrefs,
        old_manifest_path,
        old_registry_path,
    )
    validate_approval_chain(
        approval_path=old_approval_path,
        approval_sha256=sha256_file(old_approval_path),
        area=area,
        expected_source_pack=old_pack_path,
        active=set(),
        cache={},
    )
    removed = sorted(set(old_resrefs) - set(new_resrefs))
    require(not removed, f"suppression de ressource sans workflow dédié : {area}/" + ",".join(removed))
    old_version = integer(old_manifest.get("registry_version"), f"registre historique {area}")
    new_version = integer(new_manifest.get("registry_version"), f"nouveau registre {area}")
    require(old_version == new_version, f"continuité impossible après changement de version registre : {area}")
    require(old_manifest.get("runtime_contract") == new_manifest.get("runtime_contract"), f"continuité impossible après changement de contrat runtime : {area}")
    require(existing.get("renderer_contract") == renderer_contract(new_version), f"continuité impossible après changement de renderer : {area}")

    require(isinstance(old_approval.get("evidence"), list), f"preuves historiques invalides : {area}")
    result: list[dict[str, Any]] = []
    for resref in carried_resrefs:
        require(resref in old_resrefs, f"nouvelle ressource sans QA directe : {area}/{resref}")
        old_group = resource_group(old_resources, resref)
        new_group = resource_group(new_resources, resref)
        digest = canonical_sha256(old_group)
        require(old_group == new_group, f"ressource non identique sans nouvelle QA : {area}/{resref}")

        result.append(
            {
                "kind": "byte-identical-release-continuity",
                "path": repo_path(old_approval_path),
                "sha256": sha256_file(old_approval_path),
                "accepted_resrefs": [resref],
                "source_pack": old_pack_path,
                "pack_manifest_sha256": sha256_file(old_manifest_path),
                "registry_version": old_version,
                "renderer_contract": renderer_contract(old_version),
                "resource_sha256": digest,
            }
        )
    return result


def build_promotion(area: str, requested_pack: str | None, note: str) -> dict[str, Any]:
    pack_path, selections = load_area_selections(area, requested_pack)
    pack, resources, required_resrefs, pack_manifest_path, registry_path = validate_pack(area, pack_path)
    require(pack.get("runtime_budget_enforced") is True, f"budget runtime non confirmé : {area}")
    require(pack.get("authoring_pack_for_area_split") is not True, f"pack d'authoring non découpé : {area}")
    require(bool(selections), f"aucune nouvelle décision QA directe pour {area}")
    missing = sorted(set(required_resrefs) - set(selections))
    extra = sorted(set(selections) - set(required_resrefs))
    require(
        not extra,
        "sélections QA hors pack : " + ",".join(extra),
    )

    candidates_document = load_json(CANDIDATES)
    candidates = list(
        validate_candidates_document_shape(
            candidates_document,
            label=repo_path(CANDIDATES),
        )
    )
    existing_areas = [str(item.get("area", "")).upper() for item in candidates]
    component_ids = [integer(item.get("component_id", -1), "component_id animation") for item in candidates]
    require(len(existing_areas) == len(set(existing_areas)), "zones dupliquées dans le registre de candidats")
    require(len(component_ids) == len(set(component_ids)), "component_id animation dupliqué")
    existing = [item for item in candidates if str(item.get("area", "")).upper() == area]
    require(len(existing) <= 1, f"candidat release dupliqué : {area}")

    registry = registry_rows()
    pack_manifest_hash = sha256_file(pack_manifest_path)
    registry_hash = sha256_file(registry_path)
    decisions: dict[str, dict[str, Any]] = {}
    decision_refs: list[dict[str, Any]] = []
    for resref in required_resrefs:
        require(resref in registry, f"asset absent du registre : {resref}")
        row = registry[resref]
        require(area in {item for item in row.get("areas", "").split(";") if item}, f"asset hors zone dans le CSV : {resref}/{area}")
        if resref in selections:
            require(row.get("status") == "validé-x4", f"asset non validé x4 dans le CSV : {resref}")

    for resref in sorted(selections):
        row = registry[resref]
        selection_path, selection, area_record = selections[resref]
        decision_path, decision, decision_hash = validate_decision(
            area=area,
            resref=resref,
            selection_path=selection_path,
            selection=selection,
            area_record=area_record,
            pack_path=pack_path,
            pack_manifest_hash=pack_manifest_hash,
            registry_hash=registry_hash,
        )
        require(row.get("selected_run", "") == str(selection["selected_run"]["path"]), f"run sélectionné différent dans le CSV : {resref}")
        require(row.get("qa_decision", "") == repo_path(decision_path), f"décision QA différente dans le CSV : {resref}")
        require(row.get("qa_date", "") == str(decision.get("decision_date", "")), f"date QA différente dans le CSV : {resref}")
        decisions[resref] = decision
        decision_refs.append(
            {
                "kind": "ingame-qa-decision",
                "path": repo_path(decision_path),
                "sha256": decision_hash,
                "accepted_resrefs": [resref],
            }
        )

    carry_refs: list[dict[str, Any]] = []
    if missing:
        require(bool(existing), "ressources sans nouvelle QA et aucune base release approuvée : " + ",".join(missing))
        carry_refs = carry_evidence_from_existing(
            area=area,
            existing=existing[0],
            new_manifest=pack,
            new_resources=resources,
            new_resrefs=required_resrefs,
            carried_resrefs=missing,
        )

    decision_dates = sorted(str(item["decision_date"]) for item in decisions.values())
    recorded_dates = sorted(str(item["recorded_at_utc"]) for item in decisions.values())
    schema_version = 3 if carry_refs else 2
    origin = (
        "explicit-user-ingame-qa-with-byte-identical-carry-forward"
        if carry_refs
        else "explicit-user-ingame-qa"
    )
    evidence = sorted(
        [*decision_refs, *carry_refs],
        key=lambda item: (str(item["accepted_resrefs"][0]), str(item["kind"])),
    )
    approval_decision = note.strip() or (
        f"QA ingame explicite pour {area}: {', '.join(sorted(decisions))}."
        + (f" Continuité binaire vérifiée: {', '.join(missing)}." if missing else "")
    )
    identity_material = canonical_sha256(
        {
            "area": area,
            "pack_manifest_sha256": pack_manifest_hash,
            "decision": approval_decision,
            "evidence": evidence,
        }
    )
    approval_id = f"qa-v{schema_version}-" + identity_material[:16].lower()
    approval_rel = f"releases/BG2-HD-Upscale/manifests/animation-qa-approvals/{area}/{approval_id}.json"
    approval_path = ROOT / approval_rel
    approval = {
        "$schema": "../../../schemas/animation-qa-approval.schema.json",
        "schema_version": schema_version,
        "area": area,
        "status": "accepted",
        "decision_date": decision_dates[-1],
        "decision_origin": origin,
        "recorded_at_utc": recorded_dates[-1],
        "source_pack": pack_path,
        "pack_manifest_sha256": pack_manifest_hash,
        "registry": "AreaAnimations-X4.registry",
        "registry_version": integer(pack["registry_version"], "version registre pack"),
        "registry_sha256": registry_hash,
        "required_resrefs": required_resrefs,
        "evidence": evidence,
        "decision": approval_decision,
    }
    approval_data = json_bytes(approval)
    if approval_path.exists():
        require(
            approval_path.is_file() and approval_path.read_bytes() == approval_data,
            f"une autre approbation existe : {repo_path(approval_path)}",
        )

    component_id = integer(existing[0]["component_id"], f"component_id {area}") if existing else allocate_component_id(candidates)
    candidate: dict[str, Any] = {
        "area": area,
        "component_id": component_id,
        "component_label": f"animation-{area.lower()}",
        "payload_group": f"animation-{area.lower()}",
        "approval_status": "approved-for-release",
        "qa_approval": approval_rel,
        "qa_approval_sha256": sha256_bytes(approval_data),
        "source_pack": pack_path,
        "source_runs": source_runs_from_decisions(decisions),
        "pack_manifest": "manifest.json",
        "pack_manifest_sha256": pack_manifest_hash,
        "registry": "AreaAnimations-X4.registry",
        "registry_version": integer(pack["registry_version"], "version registre pack"),
        "registry_sha256": registry_hash,
        "registry_bytes": registry_path.stat().st_size,
        "required_resrefs": required_resrefs,
        "renderer_contract": renderer_contract(integer(pack["registry_version"], "version registre pack")),
    }
    if existing and "occlusion_contract" in existing[0]:
        candidate["occlusion_contract"] = existing[0]["occlusion_contract"]
    candidates = [item for item in candidates if str(item.get("area", "")).upper() != area]
    candidates.append(candidate)
    candidates.sort(key=lambda item: (integer(item["component_id"], "component_id animation"), str(item["area"])))
    updated_candidates = {
        "$schema": "../schemas/animation-release-candidates.schema.json",
        "schema_version": 3,
        "generated_by": "pipeline/scripts/animation_release.py",
        "candidates": candidates,
    }
    updated_candidate_rows = validate_candidates_document_shape(
        updated_candidates, label="registre candidats généré"
    )
    validate_occlusion_contracts(
        updated_candidate_rows,
        validate_release_mapping=True,
    )
    return {
        "area": area,
        "source_pack": pack_path,
        "required_resrefs": required_resrefs,
        "direct_resrefs": sorted(decisions),
        "carried_resrefs": missing,
        "component_id": component_id,
        "qa_approval_path": approval_path,
        "qa_approval": approval,
        "qa_approval_bytes": approval_data,
        "candidates": updated_candidates,
        "candidate_bytes": json_bytes(updated_candidates),
        "source_runs": candidate["source_runs"],
    }


def validate_approval_chain(
    *,
    approval_path: Path,
    approval_sha256: str,
    area: str,
    expected_source_pack: str | None,
    active: set[str],
    cache: dict[str, tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str], Path, Path]],
    legacy_evidence_cache: set[tuple[str, str, str]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str], Path, Path]:
    """Validate a historical approval recursively; schema-v1 is the sealed legacy base."""

    relative_approval = repo_path(approval_path)
    require(approval_path.parent == QA_APPROVALS / area, f"approbation historique hors dossier zone : {area}")
    require(sha256_file(approval_path) == approval_sha256, f"hash d'approbation historique invalide : {relative_approval}")
    cache_key = f"{relative_approval}:{approval_sha256}"
    if cache_key in cache:
        cached = cache[cache_key]
        cached_source_pack = repo_path(
            resolve_repo_path(str(cached[0].get("source_pack", "")), forbidden=True)
        )
        if expected_source_pack is not None:
            require(
                cached_source_pack == expected_source_pack,
                f"pack d'approbation historique différent : {relative_approval}",
            )
        return cached
    require(cache_key not in active, f"cycle dans les preuves de continuité : {relative_approval}")
    active.add(cache_key)
    try:
        approval = load_json(approval_path)
        schema = validate_approval_shape(
            approval, area=area, label=relative_approval
        )
        origins = {
            1: "preserved-existing-user-qa",
            2: "explicit-user-ingame-qa",
            3: "explicit-user-ingame-qa-with-byte-identical-carry-forward",
        }
        require(schema in origins, f"version d'approbation historique inconnue : {relative_approval}")
        require(approval.get("status") == "accepted" and str(approval.get("area", "")).upper() == area, f"approbation historique non acceptée : {relative_approval}")
        require(approval.get("decision_origin") == origins[schema], f"origine d'approbation historique invalide : {relative_approval}")
        source_pack = repo_path(resolve_repo_path(str(approval.get("source_pack", "")), forbidden=True))
        if expected_source_pack is not None:
            require(source_pack == expected_source_pack, f"pack d'approbation historique différent : {relative_approval}")
        manifest, resources, resrefs, manifest_path, registry_path = validate_pack(area, source_pack)
        require(normalize_hash(approval.get("pack_manifest_sha256"), f"manifest {relative_approval}") == sha256_file(manifest_path), f"manifest historique non couvert : {relative_approval}")
        version = integer(manifest.get("registry_version"), f"registre {relative_approval}")
        require(approval.get("registry") == "AreaAnimations-X4.registry", f"registre historique invalide : {relative_approval}")
        require(integer(approval.get("registry_version"), f"version {relative_approval}") == version, f"version registre historique non couverte : {relative_approval}")
        require(normalize_hash(approval.get("registry_sha256"), f"registre {relative_approval}") == sha256_file(registry_path), f"registre historique non couvert : {relative_approval}")
        require(approval.get("required_resrefs") == resrefs, f"inventaire historique non couvert exactement : {relative_approval}")
        context = (approval, manifest, resources, resrefs, manifest_path, registry_path)
        if schema == 1:
            verify_legacy_evidence(
                approval,
                area=area,
                expected_resrefs=resrefs,
                evidence_cache=legacy_evidence_cache,
            )
            cache[cache_key] = context
            return context

        evidence = approval.get("evidence")
        require(isinstance(evidence, list) and evidence, f"preuves historiques absentes : {relative_approval}")
        coverage: list[str] = []
        kinds: set[str] = set()
        for item in evidence:
            require(isinstance(item, Mapping), f"preuve historique invalide : {relative_approval}")
            accepted = item.get("accepted_resrefs")
            require(isinstance(accepted, list) and len(accepted) == 1, f"preuve historique multi-resrefs interdite : {relative_approval}")
            resref = normalize_resref(str(accepted[0]))
            coverage.append(resref)
            kind = str(item.get("kind", ""))
            kinds.add(kind)
            evidence_path = resolve_repo_path(str(item.get("path", "")), forbidden=True)
            evidence_hash = normalize_hash(item.get("sha256"), f"preuve {relative_approval}/{resref}")
            require(evidence_path.is_file() and sha256_file(evidence_path) == evidence_hash, f"preuve historique courante invalide : {relative_approval}/{resref}")

            if kind == "ingame-qa-decision":
                require(
                    evidence_path.parent
                    == ROOT / "animations" / "index" / "qa-decisions" / resref,
                    f"décision historique hors dossier asset : {relative_approval}/{resref}",
                )
                errors: list[str] = []
                decision = workflow_module()._validate_decision_record(
                    ROOT,
                    evidence_path,
                    resref,
                    errors,
                    validate_registry=False,
                )
                require(not errors and isinstance(decision, Mapping), f"décision historique invalide : {relative_approval}/{resref}: " + "; ".join(errors))
                require(decision.get("status") == "accepted" and decision.get("result_kind") == "x4", f"décision historique non x4 : {relative_approval}/{resref}")
                require(area in decision.get("tested_areas", []), f"zone absente de la décision historique : {relative_approval}/{resref}")
                area_record = selection_area_record(decision, area)
                require(area_record is not None, f"pack absent de la décision historique : {relative_approval}/{resref}")
                require(repo_path(resolve_repo_path(str(area_record.get("path", "")), forbidden=True)) == source_pack, f"pack différent dans la décision historique : {relative_approval}/{resref}")
                require(normalize_hash(area_record.get("manifest_sha256"), f"décision historique {resref}") == sha256_file(manifest_path), f"manifest différent dans la décision historique : {relative_approval}/{resref}")
                require(normalize_hash(area_record.get("registry_sha256"), f"décision historique {resref}") == sha256_file(registry_path), f"registre différent dans la décision historique : {relative_approval}/{resref}")
                continue

            require(schema == 3 and kind == "byte-identical-release-continuity", f"type de preuve historique invalide : {relative_approval}/{resref}")
            previous_pack = repo_path(resolve_repo_path(str(item.get("source_pack", "")), forbidden=True))
            previous_context = validate_approval_chain(
                approval_path=evidence_path,
                approval_sha256=evidence_hash,
                area=area,
                expected_source_pack=previous_pack,
                active=active,
                cache=cache,
                legacy_evidence_cache=legacy_evidence_cache,
            )
            _, previous_manifest, previous_resources, previous_resrefs, previous_manifest_path, _ = previous_context
            require(resref in previous_resrefs, f"ressource absente de l'approbation précédente : {relative_approval}/{resref}")
            require(normalize_hash(item.get("pack_manifest_sha256"), f"pack précédent {resref}") == sha256_file(previous_manifest_path), f"manifest précédent incohérent : {relative_approval}/{resref}")
            previous_version = integer(previous_manifest.get("registry_version"), f"registre précédent {resref}")
            require(integer(item.get("registry_version"), f"preuve précédente {resref}") == previous_version == version, f"version registre rompue : {relative_approval}/{resref}")
            require(item.get("renderer_contract") == renderer_contract(version), f"contrat renderer rompu : {relative_approval}/{resref}")
            require(previous_manifest.get("runtime_contract") == manifest.get("runtime_contract"), f"contrat runtime rompu : {relative_approval}/{resref}")
            previous_digest = canonical_sha256(resource_group(previous_resources, resref))
            current_digest = canonical_sha256(resource_group(resources, resref))
            require(previous_digest == current_digest == normalize_hash(item.get("resource_sha256"), f"ressource précédente {resref}"), f"continuité binaire historique rompue : {relative_approval}/{resref}")

        require(coverage == sorted(coverage) and len(coverage) == len(set(coverage)), f"couverture historique non canonique : {relative_approval}")
        require(coverage == resrefs, f"couverture historique différente du pack : {relative_approval}")
        require("ingame-qa-decision" in kinds, f"approbation historique sans QA directe : {relative_approval}")
        if schema == 2:
            require(kinds == {"ingame-qa-decision"}, f"preuve de continuité interdite en v2 : {relative_approval}")
        else:
            require("byte-identical-release-continuity" in kinds, f"approbation v3 sans continuité : {relative_approval}")
        cache[cache_key] = context
        return context
    finally:
        active.remove(cache_key)


def _verify_release_candidate_from_validated_registry(
    *,
    area: str,
    candidates: Sequence[Mapping[str, Any]],
    approval_override_path: Path | None = None,
    allow_pending: bool = False,
    approval_cache: dict[
        str,
        tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str], Path, Path],
    ] | None = None,
    legacy_evidence_cache: set[tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """Recompute one candidate already selected from a shape-checked registry."""

    matches = [
        item
        for item in candidates
        if isinstance(item, Mapping) and str(item.get("area", "")).upper() == area
    ]
    require(len(matches) == 1, f"candidat release absent ou dupliqué : {area}")
    candidate = matches[0]
    validate_occlusion_contracts([candidate])
    approval_status = candidate.get("approval_status")
    require(
        approval_status == "approved-for-release"
        or (
            allow_pending
            and approval_status == "validated-awaiting-manifest-approval"
        ),
        f"candidat non approuvé : {area}",
    )
    pack_path = repo_path(resolve_repo_path(str(candidate.get("source_pack", "")), forbidden=True))
    manifest, resources, resrefs, manifest_path, registry_path = validate_pack(area, pack_path)
    validate_candidate_pack_metadata(candidate, area, manifest, resrefs, manifest_path, registry_path)
    declared_approval_path = resolve_repo_path(str(candidate.get("qa_approval", "")))
    require(declared_approval_path.parent == QA_APPROVALS / area, f"approbation QA hors dossier zone : {area}")
    approval_path = approval_override_path.resolve() if approval_override_path else declared_approval_path
    require(approval_path.is_file(), f"approbation QA absente : {approval_path}")
    require(sha256_file(approval_path) == normalize_hash(candidate.get("qa_approval_sha256"), f"approbation {area}"), f"hash approbation candidat incohérent : {area}")
    approval = load_json(approval_path)
    approval_schema = validate_approval_shape(
        approval, area=area, label=repo_path(declared_approval_path)
    )
    if approval_schema in {2, 3}:
        require(manifest.get("runtime_budget_enforced") is True, f"budget runtime non confirmé : {area}")
        require(manifest.get("authoring_pack_for_area_split") is not True, f"pack d'authoring non découpé : {area}")
    require(approval.get("status") == "accepted", f"approbation non acceptée : {area}")
    expected_origins = {
        1: "preserved-existing-user-qa",
        2: "explicit-user-ingame-qa",
        3: "explicit-user-ingame-qa-with-byte-identical-carry-forward",
    }
    require(approval.get("decision_origin") == expected_origins[approval_schema], f"origine d'approbation invalide : {area}")
    require(str(approval.get("area", "")).upper() == area, f"zone d'approbation incohérente : {area}")
    require(approval.get("source_pack") == pack_path, f"pack d'approbation incohérent : {area}")
    require(normalize_hash(approval.get("pack_manifest_sha256"), f"manifest approbation {area}") == sha256_file(manifest_path), f"manifest non couvert par l'approbation : {area}")
    version = integer(manifest.get("registry_version"), f"registre {area}")
    require(approval.get("registry") == "AreaAnimations-X4.registry", f"registre d'approbation invalide : {area}")
    require(integer(approval.get("registry_version"), f"version approbation {area}") == version, f"version registre non couverte : {area}")
    require(normalize_hash(approval.get("registry_sha256"), f"registre approbation {area}") == sha256_file(registry_path), f"registre non couvert par l'approbation : {area}")
    require(approval.get("required_resrefs") == resrefs, f"inventaire non couvert exactement : {area}")

    if approval_schema == 1:
        validate_candidate_source_runs(
            candidate,
            area=area,
            expected_asset_ids=resrefs if candidate.get("source_runs") is not None else None,
            require_structured=False,
        )
        verify_legacy_evidence(
            approval,
            area=area,
            expected_resrefs=resrefs,
            evidence_cache=legacy_evidence_cache,
        )
        return {
            "area": area,
            "source_pack": pack_path,
            "direct_resrefs": [],
            "carried_resrefs": [],
            "legacy_qa": True,
        }

    evidence = approval.get("evidence")
    require(isinstance(evidence, list) and evidence, f"preuves structurées absentes : {area}")
    coverage: list[str] = []
    direct_decisions: dict[str, dict[str, Any]] = {}
    direct_count = 0
    carry_count = 0
    chain_cache = approval_cache if approval_cache is not None else {}
    for item in evidence:
        require(isinstance(item, Mapping), f"preuve structurée invalide : {area}")
        accepted = item.get("accepted_resrefs")
        require(isinstance(accepted, list) and len(accepted) == 1, f"une preuve structurée doit couvrir un seul resref : {area}")
        resref = normalize_resref(str(accepted[0]))
        coverage.append(resref)
        kind = item.get("kind")
        evidence_path = resolve_repo_path(str(item.get("path", "")), forbidden=True)
        require(evidence_path.is_file(), f"preuve absente : {repo_path(evidence_path)}")
        require(sha256_file(evidence_path) == normalize_hash(item.get("sha256"), f"preuve {resref}"), f"hash courant de preuve invalide : {area}/{resref}")

        if kind == "ingame-qa-decision":
            direct_count += 1
            require(
                evidence_path.parent
                == ROOT / "animations" / "index" / "qa-decisions" / resref,
                f"décision directe hors dossier asset : {area}/{resref}",
            )
            errors: list[str] = []
            decision = workflow_module()._validate_decision_record(
                ROOT,
                evidence_path,
                resref,
                errors,
                validate_registry=False,
            )
            require(not errors and isinstance(decision, Mapping), f"décision directe invalide : {area}/{resref}: " + "; ".join(errors))
            require(decision.get("status") == "accepted" and decision.get("result_kind") == "x4", f"décision directe non x4 : {area}/{resref}")
            require(area in decision.get("tested_areas", []), f"zone absente de la décision directe : {area}/{resref}")
            area_record = selection_area_record(decision, area)
            require(area_record is not None, f"pack absent de la décision directe : {area}/{resref}")
            require(repo_path(resolve_repo_path(str(area_record.get("path", "")), forbidden=True)) == pack_path, f"pack différent dans la décision directe : {area}/{resref}")
            require(normalize_hash(area_record.get("manifest_sha256"), f"décision directe {resref}") == sha256_file(manifest_path), f"manifest différent dans la décision directe : {area}/{resref}")
            require(normalize_hash(area_record.get("registry_sha256"), f"décision directe {resref}") == sha256_file(registry_path), f"registre différent dans la décision directe : {area}/{resref}")
            direct_decisions[resref] = decision
            continue

        require(approval_schema == 3 and kind == "byte-identical-release-continuity", f"type de preuve structurée inconnu : {area}/{resref}")
        carry_count += 1
        old_pack_path = repo_path(resolve_repo_path(str(item.get("source_pack", "")), forbidden=True))
        old_context = validate_approval_chain(
            approval_path=evidence_path,
            approval_sha256=normalize_hash(item.get("sha256"), f"approbation historique {resref}"),
            area=area,
            expected_source_pack=old_pack_path,
            active=set(),
            cache=chain_cache,
            legacy_evidence_cache=legacy_evidence_cache,
        )
        old_approval, old_manifest, old_resources, old_resrefs, old_manifest_path, old_registry_path = old_context
        require(resref in old_resrefs, f"ressource absente du pack historique : {area}/{resref}")
        require(normalize_hash(item.get("pack_manifest_sha256"), f"manifest historique {resref}") == sha256_file(old_manifest_path), f"manifest historique incohérent : {area}/{resref}")
        require(normalize_hash(old_approval.get("pack_manifest_sha256"), f"approbation historique {resref}") == sha256_file(old_manifest_path), f"approbation historique liée à un autre pack : {area}/{resref}")
        old_version = integer(old_manifest.get("registry_version"), f"registre historique {resref}")
        require(integer(item.get("registry_version"), f"preuve registre {resref}") == old_version == version, f"version registre différente : {area}/{resref}")
        require(item.get("renderer_contract") == renderer_contract(old_version) == candidate.get("renderer_contract"), f"contrat renderer différent : {area}/{resref}")
        require(old_manifest.get("runtime_contract") == manifest.get("runtime_contract"), f"contrat runtime différent : {area}/{resref}")
        old_digest = canonical_sha256(resource_group(old_resources, resref))
        new_digest = canonical_sha256(resource_group(resources, resref))
        recorded_digest = normalize_hash(item.get("resource_sha256"), f"ressource {resref}")
        require(old_digest == new_digest == recorded_digest, f"ressource non identique à la release approuvée : {area}/{resref}")

    require(direct_count > 0, f"approbation structurée sans QA directe : {area}")
    if approval_schema == 2:
        require(carry_count == 0, f"continuité interdite en QA v2 : {area}")
    else:
        require(carry_count > 0, f"approbation v3 sans continuité : {area}")
    require(coverage == sorted(coverage) and len(coverage) == len(set(coverage)), f"couverture de preuves non canonique ou dupliquée : {area}")
    require(coverage == resrefs, f"couverture de preuves différente du pack : {area}")
    expected_runs = source_runs_from_decisions(direct_decisions)
    require(candidate.get("source_runs") == expected_runs, f"runs source différents des décisions directes : {area}")
    validate_candidate_source_runs(
        candidate,
        area=area,
        expected_asset_ids=sorted(direct_decisions),
        require_structured=True,
    )
    return {
        "area": area,
        "source_pack": pack_path,
        "direct_resrefs": sorted(direct_decisions),
        "carried_resrefs": sorted(set(resrefs) - set(direct_decisions)),
    }


def verify_release_candidate(
    *,
    area: str,
    candidates_path: Path,
    approval_override_path: Path | None = None,
    allow_pending: bool = False,
) -> dict[str, Any]:
    """Recompute pack, provenance and QA proof for one release candidate."""

    resolved_candidates_path = candidates_path.resolve()
    document = load_json(resolved_candidates_path)
    candidates = validate_candidates_document_shape(
        document,
        label=str(resolved_candidates_path),
    )
    return _verify_release_candidate_from_validated_registry(
        area=area,
        candidates=candidates,
        approval_override_path=approval_override_path,
        allow_pending=allow_pending,
    )


def verify_release_candidate_registry(
    *,
    candidates_path: Path,
    approval_overrides: Mapping[str, Path] | None = None,
    allow_pending: bool = False,
) -> list[dict[str, Any]]:
    """Physically verify every candidate carried by one complete registry."""

    resolved_candidates_path = candidates_path.resolve()
    document = load_json(resolved_candidates_path)
    candidates = validate_candidates_document_shape(
        document,
        label=str(resolved_candidates_path),
    )
    normalized_overrides: dict[str, Path] = {}
    for raw_area, path in (approval_overrides or {}).items():
        area = normalize_area(str(raw_area))
        require(area not in normalized_overrides, f"override d'approbation dupliqué : {area}")
        normalized_overrides[area] = Path(path).resolve()

    areas = [normalize_area(str(candidate.get("area", ""))) for candidate in candidates]
    unknown_overrides = sorted(set(normalized_overrides) - set(areas))
    require(
        not unknown_overrides,
        "override d'approbation sans candidat : " + ",".join(unknown_overrides),
    )

    results: list[dict[str, Any]] = []
    approval_cache: dict[
        str,
        tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], list[str], Path, Path],
    ] = {}
    legacy_evidence_cache: set[tuple[str, str, str]] = set()
    for area in areas:
        results.append(
            _verify_release_candidate_from_validated_registry(
                area=area,
                candidates=candidates,
                approval_override_path=normalized_overrides.get(area),
                allow_pending=allow_pending,
                approval_cache=approval_cache,
                legacy_evidence_cache=legacy_evidence_cache,
            )
        )
    return results


def powershell() -> str:
    executable = shutil.which("pwsh")
    if not executable:
        raise ReleasePromotionError("PowerShell 7 (pwsh) est requis pour générer les manifestes release")
    return executable


def run_command(argv: Sequence[str]) -> None:
    completed = subprocess.run(
        list(argv), cwd=ROOT, text=True, capture_output=True, check=False
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()
        raise ReleasePromotionError(
            f"commande de prévalidation échouée ({completed.returncode}) : "
            + subprocess.list2cmdline(list(argv))
            + (f"\n{detail}" if detail else "")
        )


@contextmanager
def workflow_lock():
    """Serialize QA and release authority access with a crash-safe OS lock."""

    try:
        with ANIMATION_AUTHORITY_LOCK.animation_authority_lock(ROOT):
            yield
    except ANIMATION_AUTHORITY_LOCK.AnimationAuthorityLockError as error:
        raise ReleasePromotionError(str(error)) from error


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.{uuid.uuid4().hex}.partial")
    try:
        with temporary.open("wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _remove_backup_root(path: Path) -> None:
    resolved = path.resolve()
    require(
        resolved.parent == TRANSACTION_ROOT.resolve()
        and resolved.name.startswith("animation-release-"),
        f"dossier de sauvegarde transaction invalide : {resolved}",
    )
    if resolved.is_dir():
        shutil.rmtree(resolved)


def _allowed_publication_target(path: Path) -> bool:
    resolved = path.resolve()
    fixed = {
        CANDIDATES.resolve(),
        CONTENT.resolve(),
        COMPONENTS.resolve(),
        (PACKAGE_MANIFESTS / CANDIDATES.name).resolve(),
        (PACKAGE_MANIFESTS / CONTENT.name).resolve(),
        (PACKAGE_MANIFESTS / COMPONENTS.name).resolve(),
        PACKAGE_TP2.resolve(),
    }
    if resolved in fixed:
        return True
    try:
        relative = resolved.relative_to(QA_APPROVALS.resolve())
    except ValueError:
        return False
    return (
        len(relative.parts) == 2
        and bool(AREA_RE.fullmatch(relative.parts[0]))
        and resolved.suffix.casefold() == ".json"
    )


def recover_publication_journal(journal_path: Path | None = None) -> list[str]:
    if journal_path is None:
        journal_path = PUBLICATION_JOURNAL
    if not journal_path.is_file():
        return []
    journal = load_json(journal_path)
    require(journal.get("schema") == PUBLICATION_JOURNAL_SCHEMA, "journal de publication inconnu")
    backup_root = resolve_repo_path(str(journal.get("backup_root", "")))
    require(
        backup_root.parent == TRANSACTION_ROOT.resolve()
        and backup_root.name.startswith("animation-release-"),
        "racine de sauvegarde transaction invalide",
    )
    entries = journal.get("entries")
    require(isinstance(entries, list) and entries, "journal de publication vide")
    prepared: list[tuple[Path, bool, Path | None]] = []
    seen: set[Path] = set()
    for entry in entries:
        require(isinstance(entry, Mapping), "entrée de journal invalide")
        target_value = str(entry.get("target", ""))
        reject_leaf_link(target_value, "cible de journal")
        target = resolve_repo_path(target_value)
        require(_allowed_publication_target(target), f"cible de journal interdite : {repo_path(target)}")
        require(target not in seen, f"cible de journal dupliquée : {repo_path(target)}")
        seen.add(target)
        existed = entry.get("existed")
        require(isinstance(existed, bool), "état de sauvegarde invalide")
        published_hash = normalize_hash(
            entry.get("published_sha256"), f"cible publiée {repo_path(target)}"
        )
        backup: Path | None = None
        backup_hash: str | None = None
        if existed:
            backup = resolve_repo_path(str(entry.get("backup", "")))
            require(backup.parent == backup_root, "fichier de sauvegarde hors transaction")
            require(backup.is_file(), f"sauvegarde absente : {repo_path(backup)}")
            backup_hash = normalize_hash(
                entry.get("backup_sha256"), f"sauvegarde {repo_path(backup)}"
            )
            require(
                sha256_file(backup) == backup_hash,
                f"hash de sauvegarde incohérent : {repo_path(backup)}",
            )
        require(not target.exists() or target.is_file(), f"cible de transaction non fichier : {repo_path(target)}")
        if target.is_file():
            allowed_hashes = {published_hash}
            if backup_hash is not None:
                allowed_hashes.add(backup_hash)
            require(
                sha256_file(target) in allowed_hashes,
                f"cible modifiée depuis l'interruption; récupération refusée : {repo_path(target)}",
            )
        else:
            require(
                not existed,
                f"cible supprimée depuis l'interruption; récupération refusée : {repo_path(target)}",
            )
        prepared.append((target, existed, backup))

    restored: list[str] = []
    failures: list[str] = []
    for target, existed, backup in reversed(prepared):
        try:
            if existed:
                require(backup is not None, f"sauvegarde absente : {repo_path(target)}")
                write_atomic(target, backup.read_bytes())
            else:
                target.unlink(missing_ok=True)
            restored.append(repo_path(target))
        except Exception as error:
            failures.append(str(error))
    if failures:
        raise ReleasePromotionError("récupération de transaction incomplète : " + " | ".join(failures))
    journal_path.unlink(missing_ok=True)
    _remove_backup_root(backup_root)
    return restored


def publish_transaction(
    files: Mapping[Path, bytes],
    *,
    journal_path: Path | None = None,
) -> list[str]:
    if journal_path is not None:
        recover_publication_journal(journal_path)
    normalized: dict[Path, bytes] = {}
    for path, data in files.items():
        reject_leaf_link(path, "cible de publication")
        resolved = path.resolve(strict=False)
        require(resolved not in normalized, f"cible de publication dupliquée : {resolved}")
        require(not resolved.exists() or resolved.is_file(), f"cible de publication non fichier : {resolved}")
        normalized[resolved] = data
    changed = [
        path
        for path, data in normalized.items()
        if not path.is_file() or path.read_bytes() != data
    ]
    if not changed:
        return []
    originals = {path: path.read_bytes() if path.is_file() else None for path in changed}
    backup_root: Path | None = None
    if journal_path is not None:
        for path in changed:
            require(_allowed_publication_target(path), f"cible de publication interdite : {repo_path(path)}")
        TRANSACTION_ROOT.mkdir(parents=True, exist_ok=True)
        backup_root = TRANSACTION_ROOT / f"animation-release-{uuid.uuid4().hex}"
        backup_root.mkdir()
        entries: list[dict[str, Any]] = []
        try:
            for index, path in enumerate(changed):
                target_rel = repo_path(path)
                original = originals[path]
                entry: dict[str, Any] = {
                    "target": target_rel,
                    "existed": original is not None,
                    "published_sha256": sha256_bytes(normalized[path]),
                }
                if original is not None:
                    backup = backup_root / f"{index:03d}.bin"
                    write_atomic(backup, original)
                    entry["backup"] = repo_path(backup)
                    entry["backup_sha256"] = sha256_bytes(original)
                entries.append(entry)
            write_atomic(
                journal_path,
                json_bytes(
                    {
                        "schema": PUBLICATION_JOURNAL_SCHEMA,
                        "backup_root": repo_path(backup_root),
                        "entries": entries,
                    }
                ),
            )
        except Exception:
            if backup_root.is_dir():
                _remove_backup_root(backup_root)
            raise

    try:
        for path in changed:
            write_atomic(path, normalized[path])
    except Exception as publication_error:
        if journal_path is not None:
            try:
                recover_publication_journal(journal_path)
            except Exception as rollback_error:
                raise ReleasePromotionError(
                    f"publication échouée ({publication_error}); récupération sûre refusée ou incomplète "
                    f"({rollback_error}); journal conservé : {repo_path(journal_path)}"
                ) from publication_error
            raise
        failures: list[str] = []
        for path in reversed(changed):
            try:
                original = originals[path]
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    write_atomic(path, original)
            except Exception as rollback_error:
                failures.append(f"{path}: {rollback_error}")
        if failures:
            raise ReleasePromotionError(
                f"publication échouée ({publication_error}); rollback incomplet : "
                + " | ".join(failures)
            ) from publication_error
        raise
    if journal_path is not None:
        journal_path.unlink(missing_ok=True)
        if backup_root is not None:
            _remove_backup_root(backup_root)
    return [repo_path(path) for path in changed]


def merge_animation_delta(area: str, delta_path: Path, output_path: Path) -> None:
    """Replace one area's entries without rebuilding unrelated release content."""

    current = load_json(CONTENT)
    delta = load_json(delta_path)
    current_entries = current.get("entries")
    delta_entries = delta.get("entries")
    require(isinstance(current_entries, list), "content.json: entries invalides")
    require(isinstance(delta_entries, list) and bool(delta_entries), f"delta release vide : {area}")
    require(
        all(
            isinstance(entry, Mapping)
            and entry.get("kind") == "area-animation"
            and str(entry.get("area", "")).upper() == area
            for entry in delta_entries
        ),
        f"delta release hors zone : {area}",
    )
    merged_entries = [
        entry
        for entry in current_entries
        if not (
            isinstance(entry, Mapping)
            and entry.get("kind") == "area-animation"
            and str(entry.get("area", "")).upper() == area
        )
    ]
    merged_entries.extend(delta_entries)
    merged_entries.sort(
        key=lambda entry: (
            int(entry.get("component_id", -1)),
            int(entry.get("install_order", -1)),
            str(entry.get("destination", "")),
            str(entry.get("source", "")),
        )
    )
    merged = dict(current)
    merged["entries"] = merged_entries
    output_path.write_bytes(json_bytes(merged))


def validate_generated_manifest_set(
    *,
    temp_root: Path,
    pwsh: str,
    candidate_path: Path,
    approval_path: Path,
    content_path: Path,
    components_path: Path,
    tp2_path: Path,
    plan: Mapping[str, Any],
) -> None:
    validator = temp_root / "validate-generated-manifests.ps1"
    validator.write_text(
        """[CmdletBinding()]
param([string]$ReleaseRoot,[string]$Candidate,[string]$Approval,[string]$Content,[string]$Components)
$ErrorActionPreference = 'Stop'
$checks = @(
  @($Candidate, (Join-Path $ReleaseRoot 'schemas/animation-release-candidates.schema.json')),
  @($Approval, (Join-Path $ReleaseRoot 'schemas/animation-qa-approval.schema.json')),
  @($Content, (Join-Path $ReleaseRoot 'schemas/content.schema.json')),
  @($Components, (Join-Path $ReleaseRoot 'schemas/components.schema.json'))
)
foreach ($check in $checks) {
  if (-not (Test-Json -LiteralPath $check[0] -SchemaFile $check[1])) { throw ('Schema invalide: ' + $check[0]) }
}
""",
        encoding="utf-8",
    )
    run_command(
        (
            pwsh,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(validator),
            "-ReleaseRoot",
            str(RELEASE_ROOT),
            "-Candidate",
            str(candidate_path),
            "-Approval",
            str(approval_path),
            "-Content",
            str(content_path),
            "-Components",
            str(components_path),
        )
    )
    content = load_json(content_path)
    components = load_json(components_path)
    generated_candidate_rows = validate_candidates_document_shape(
        load_json(candidate_path),
        label=str(candidate_path.resolve()),
    )
    validate_occlusion_contracts(
        generated_candidate_rows,
        validate_release_mapping=True,
        components_document=components,
        content_document=content,
        require_animation_dependencies=True,
    )
    entries = content.get("entries")
    component_rows = components.get("components")
    require(isinstance(entries, list) and entries, "content.json généré vide")
    require(isinstance(component_rows, list) and component_rows, "components.json généré vide")
    target_components = [
        item
        for item in component_rows
        if isinstance(item, Mapping) and integer(item.get("id", -1), "id composant généré") == integer(plan["component_id"], "component_id plan")
    ]
    require(len(target_components) == 1, f"composant animation généré absent ou dupliqué : {plan['area']}")
    component = target_components[0]
    require(component.get("label") == f"animation-{str(plan['area']).lower()}", f"label composant animation incohérent : {plan['area']}")
    require(f"animation-{str(plan['area']).lower()}" in (component.get("payload_groups") or []), f"payload group animation absent : {plan['area']}")
    tp2 = tp2_path.read_text(encoding="utf-8-sig")
    require(bool(tp2.strip()), "TP2 généré vide")
    require(f"DESIGNATED {integer(plan['component_id'], 'component_id plan')}" in tp2, f"composant absent du TP2 : {plan['area']}")
    require(f"BEGIN ~{plan['area']} area animations (x4)~" in tp2, f"bloc animation absent du TP2 : {plan['area']}")


def apply_promotion(plan: Mapping[str, Any], *, test_delta: bool) -> list[str]:
    approval_path = Path(plan["qa_approval_path"])
    approval_data = bytes(plan["qa_approval_bytes"])
    if approval_path.is_file():
        require(approval_path.read_bytes() == approval_data, f"une autre approbation existe : {repo_path(approval_path)}")
    with tempfile.TemporaryDirectory(prefix="bg2-animation-release-") as temporary:
        temp = Path(temporary)
        candidate_path = temp / "animation-release-candidates.json"
        approval_override_path = temp / approval_path.name
        delta_content_path = temp / "content.animation-delta.json"
        content_path = temp / "content.json"
        components_path = temp / "components.json"
        tp2_path = temp / "bg2hd.tp2"
        candidate_path.write_bytes(bytes(plan["candidate_bytes"]))
        approval_override_path.write_bytes(approval_data)
        verify_release_candidate_registry(
            candidates_path=candidate_path,
            approval_overrides={str(plan["area"]): approval_override_path},
            allow_pending=True,
        )
        pwsh = powershell()
        run_command(
            (
                pwsh,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(RELEASE_ROOT / "tools" / "New-BG2HD-ContentManifest.ps1"),
                "-WorkspaceRoot",
                str(ROOT),
                "-AnimationCandidatesPath",
                str(candidate_path),
                "-AnimationQaApprovalOverridePath",
                str(approval_override_path),
                "-OutputPath",
                str(delta_content_path),
                "-OnlyAnimationArea",
                str(plan["area"]),
            )
        )
        merge_animation_delta(str(plan["area"]), delta_content_path, content_path)
        run_command(
            (
                pwsh,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(RELEASE_ROOT / "tools" / "New-BG2HD-ComponentManifest.ps1"),
                "-ReleaseRoot",
                str(RELEASE_ROOT),
                "-AnimationCandidatesPath",
                str(candidate_path),
                "-ContentPath",
                str(content_path),
                "-OutputPath",
                str(components_path),
            )
        )
        run_command(
            (
                pwsh,
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(RELEASE_ROOT / "tools" / "Generate-BG2HD-Tp2.ps1"),
                "-ReleaseRoot",
                str(RELEASE_ROOT),
                "-ContentPath",
                str(content_path),
                "-ComponentsPath",
                str(components_path),
                "-OutputPath",
                str(tp2_path),
            )
        )
        validate_generated_manifest_set(
            temp_root=temp,
            pwsh=pwsh,
            candidate_path=candidate_path,
            approval_path=approval_override_path,
            content_path=content_path,
            components_path=components_path,
            tp2_path=tp2_path,
            plan=plan,
        )
        if test_delta:
            run_command(
                (
                    pwsh,
                    "-NoLogo",
                    "-NoProfile",
                    "-NonInteractive",
                    "-File",
                    str(RELEASE_ROOT / "tools" / "Test-BG2HDAreaAnimationCandidate.ps1"),
                    "-Area",
                    str(plan["area"]),
                    "-AnimationCandidatesPath",
                    str(candidate_path),
                    "-AnimationQaApprovalOverridePath",
                    str(approval_override_path),
                )
            )
        candidate_data = candidate_path.read_bytes()
        content_data = content_path.read_bytes()
        components_data = components_path.read_bytes()
        tp2_data = tp2_path.read_bytes()
        files = {
            approval_path: approval_data,
            CANDIDATES: candidate_data,
            CONTENT: content_data,
            COMPONENTS: components_data,
            PACKAGE_MANIFESTS / CANDIDATES.name: candidate_data,
            PACKAGE_MANIFESTS / CONTENT.name: content_data,
            PACKAGE_MANIFESTS / COMPONENTS.name: components_data,
            PACKAGE_TP2: tp2_data,
        }
        return publish_transaction(files, journal_path=PUBLICATION_JOURNAL)


def public_plan(plan: Mapping[str, Any], *, test_delta: bool = False) -> dict[str, Any]:
    writes = [
        repo_path(Path(plan["qa_approval_path"])),
        repo_path(CANDIDATES),
        repo_path(CONTENT),
        repo_path(COMPONENTS),
        repo_path(PACKAGE_MANIFESTS / CANDIDATES.name),
        repo_path(PACKAGE_MANIFESTS / CONTENT.name),
        repo_path(PACKAGE_MANIFESTS / COMPONENTS.name),
        repo_path(PACKAGE_TP2),
    ]
    return {
        "mode": "plan",
        "area": plan["area"],
        "source_pack": plan["source_pack"],
        "required_resrefs": plan["required_resrefs"],
        "direct_resrefs": plan.get("direct_resrefs", plan["required_resrefs"]),
        "carried_resrefs": plan.get("carried_resrefs", []),
        "component_id": plan["component_id"],
        "qa_approval": repo_path(Path(plan["qa_approval_path"])),
        "source_runs": plan["source_runs"],
        "writes": writes,
        "tests": "delta gate requested" if test_delta else "not run unless --test-delta is explicit",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promouvoir une QA ingame animation vers les manifestes release"
    )
    parser.add_argument("--area", required=True)
    parser.add_argument("--pack", help="pack de zone exact si plusieurs sélections existent")
    parser.add_argument("--decision-note", default="")
    parser.add_argument("--approve", action="store_true", help="accord release explicite obligatoire")
    parser.add_argument("--run", action="store_true", help="publier la transaction; sinon plan seulement")
    parser.add_argument("--test-delta", action="store_true", help="lancer aussi la gate ciblée autorisée")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if not args.approve:
        parser.error("--approve est requis : la QA et la release sont deux décisions distinctes")
    if args.test_delta and not args.run:
        parser.error("--test-delta exige --run")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        area = normalize_area(args.area)
        if not args.run:
            with workflow_lock():
                require(
                    not AUTHORITY_JOURNAL.exists()
                    and not PUBLICATION_JOURNAL.exists()
                    and not PACKAGE_SYNC_MARKER.exists(),
                    "transaction animation interrompue active; relancer sa commande d'origine avant de recalculer le plan",
                )
                plan = build_promotion(area, args.pack, args.decision_note)
            payload = public_plan(plan, test_delta=args.test_delta)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"PLAN release animation : {payload['area']}")
                print(f"pack : {payload['source_pack']}")
                print("assets : " + ", ".join(payload["required_resrefs"]))
                if payload["carried_resrefs"]:
                    print("QA directe : " + ", ".join(payload["direct_resrefs"]))
                    print("continuité binaire : " + ", ".join(payload["carried_resrefs"]))
                print("écritures prévues :")
                for path in payload["writes"]:
                    print(f"  - {path}")
                print("Aucune écriture. Relancer avec --run après le choix de reconstruction.")
            return 0
        with workflow_lock():
            require(
                not AUTHORITY_JOURNAL.exists() and not PACKAGE_SYNC_MARKER.exists(),
                "transaction QA ou synchronisation des miroirs animation interrompue; "
                "relancer d'abord la commande d'origine",
            )
            recovered = recover_publication_journal()
            plan = build_promotion(area, args.pack, args.decision_note)
            payload = public_plan(plan, test_delta=args.test_delta)
            changed = apply_promotion(plan, test_delta=args.test_delta)
        result = {
            **payload,
            "mode": "applied",
            "recovered_before_apply": recovered,
            "changed": changed,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Release animation intégrée : {payload['area']}")
            if recovered:
                print("Transaction interrompue précédente restaurée avant publication.")
            if changed:
                print("fichiers à contrôler/committer :")
                for path in changed:
                    print(f"  - {path}")
            else:
                print("Aucun changement : transaction déjà appliquée à l'identique.")
        return 0
    except (OSError, ValueError, ReleasePromotionError) as error:
        print(f"ERROR: {error}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
