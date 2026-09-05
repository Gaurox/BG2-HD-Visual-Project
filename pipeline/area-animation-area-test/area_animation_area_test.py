"""Transactionally install or restore one completed per-area animation pack.

The tool owns exactly ``iee-assets/areas/<AREA_ID>``. It intentionally does not
install a renderer DLL, edit the INI, modify the global registry, or infer QA / release
state. PowerShell entrypoints forward to this module; tests use its functions directly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_animation_upscale_30fps_v2 as runtime_v2
from workspace_paths import get_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME_ROOT = Path(get_path("bg2ee_game_root"))
DEFAULT_BACKUP_ROOT = PROJECT_ROOT / "backups" / "animations" / "area-tests"
RECEIPT_NAME = "install-backup.json"
RECEIPT_SCHEMA = "bg2-upscale-area-animation-area-test-transaction-v1"
AREA_PATTERN = re.compile(r"^[A-Z0-9]{1,8}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TRANSACTION_PATTERN = re.compile(r"^[A-Z0-9]{1,8}-\d{8}T\d{6}\d{6}Z-[0-9a-f]{8}$")
PROCESS_NAMES = {"baldur.exe", "baldurreal.exe", "infinityloader.exe"}
TRANSIENT_PREFIX = ".bg2hd-"
REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)


class TransactionError(RuntimeError):
    """A precondition, integrity or transactional operation failed."""


@dataclass(frozen=True)
class FileSnapshot:
    bytes: int
    sha256: str


@dataclass(frozen=True)
class DirectorySnapshot:
    present: bool
    files: tuple[tuple[str, FileSnapshot], ...]


@dataclass(frozen=True)
class SourceFile:
    name: str
    path: Path
    snapshot: FileSnapshot


@dataclass(frozen=True)
class AreaPack:
    root: Path
    area_id: str
    manifest: FileSnapshot
    registry_version: int
    registry: FileSnapshot
    files: tuple[SourceFile, ...]


@dataclass(frozen=True)
class GamePaths:
    root: Path
    dll: Path
    ini: Path
    areas: Path


@dataclass(frozen=True)
class InstallResult:
    status: str
    area_id: str
    receipt_path: Path | None
    incoming_files: int
    incoming_bytes: int


ProcessChecker = Callable[[], list[str]]
FailureHook = Callable[[str], None]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_reparse(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & REPARSE_POINT)


def path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def require_safe_file(path: Path, label: str) -> Path:
    if not path_exists(path) or path.is_symlink() or is_reparse(path) or not path.is_file():
        raise TransactionError(f"fichier ordinaire requis : {label}: {path}")
    return path.resolve(strict=True)


def require_safe_directory(path: Path, label: str) -> Path:
    if not path_exists(path) or path.is_symlink() or is_reparse(path) or not path.is_dir():
        raise TransactionError(f"dossier ordinaire requis : {label}: {path}")
    return path.resolve(strict=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_snapshot(path: Path, label: str) -> FileSnapshot:
    file_path = require_safe_file(path, label)
    return FileSnapshot(file_path.stat().st_size, sha256_file(file_path))


def safe_name(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw or Path(raw).name != raw or raw in {".", ".."}:
        raise TransactionError(f"nom de fichier non sûr : {label}: {raw!r}")
    return raw


def require_exact_int(raw: object, label: str) -> int:
    if type(raw) is not int:
        raise TransactionError(f"entier JSON requis : {label}")
    return raw


def require_exact_bool(raw: object, label: str) -> bool:
    if type(raw) is not bool:
        raise TransactionError(f"booléen JSON requis : {label}")
    return raw


def require_sha256(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not SHA256_PATTERN.fullmatch(raw.lower()):
        raise TransactionError(f"SHA-256 invalide : {label}")
    return raw.lower()


def normalise_area(raw: object, label: str = "area_id") -> str:
    if not isinstance(raw, str) or not AREA_PATTERN.fullmatch(raw):
        raise TransactionError(f"identifiant de zone invalide : {label}: {raw!r}")
    return raw


def snapshot_directory(path: Path, label: str) -> DirectorySnapshot:
    if not path_exists(path):
        return DirectorySnapshot(False, ())
    directory = require_safe_directory(path, label)
    seen: set[str] = set()
    files: list[tuple[str, FileSnapshot]] = []
    for child in directory.iterdir():
        if child.is_symlink() or is_reparse(child) or not child.is_file():
            raise TransactionError(f"contenu de zone non plat ou non ordinaire : {child}")
        name = safe_name(child.name, str(child))
        folded = name.casefold()
        if folded in seen:
            raise TransactionError(f"collision de casse dans {label}: {name}")
        seen.add(folded)
        files.append((name, file_snapshot(child, f"{label}/{name}")))
    return DirectorySnapshot(True, tuple(sorted(files, key=lambda entry: entry[0].casefold())))


def snapshot_to_json(snapshot: FileSnapshot) -> dict[str, object]:
    return {"bytes": snapshot.bytes, "sha256": snapshot.sha256}


def snapshot_from_json(raw: object, label: str) -> FileSnapshot:
    if not isinstance(raw, dict):
        raise TransactionError(f"snapshot fichier invalide : {label}")
    byte_count = require_exact_int(raw.get("bytes"), f"{label}.bytes")
    if byte_count < 0:
        raise TransactionError(f"taille négative : {label}")
    return FileSnapshot(byte_count, require_sha256(raw.get("sha256"), f"{label}.sha256"))


def aggregate_directory(snapshot: DirectorySnapshot) -> str:
    digest = hashlib.sha256()
    digest.update(b"present\0" + (b"1" if snapshot.present else b"0") + b"\n")
    for name, state in snapshot.files:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0" + str(state.bytes).encode("ascii") + b"\0")
        digest.update(state.sha256.encode("ascii") + b"\n")
    return digest.hexdigest()


def directory_to_json(snapshot: DirectorySnapshot) -> dict[str, object]:
    return {
        "present": snapshot.present,
        "files": [
            {"name": name, **snapshot_to_json(state)}
            for name, state in snapshot.files
        ],
        "aggregate_sha256": aggregate_directory(snapshot),
    }


def directory_from_json(raw: object, label: str) -> DirectorySnapshot:
    if not isinstance(raw, dict):
        raise TransactionError(f"snapshot dossier invalide : {label}")
    present = require_exact_bool(raw.get("present"), f"{label}.present")
    raw_files = raw.get("files")
    if not isinstance(raw_files, list):
        raise TransactionError(f"inventaire absent : {label}.files")
    seen: set[str] = set()
    files: list[tuple[str, FileSnapshot]] = []
    for index, item in enumerate(raw_files):
        if not isinstance(item, dict):
            raise TransactionError(f"fichier reçu invalide : {label}.files[{index}]")
        name = safe_name(item.get("name"), f"{label}.files[{index}].name")
        folded = name.casefold()
        if folded in seen:
            raise TransactionError(f"collision de casse dans le reçu : {label}/{name}")
        seen.add(folded)
        files.append((name, snapshot_from_json(item, f"{label}/{name}")))
    snapshot = DirectorySnapshot(
        present,
        tuple(sorted(files, key=lambda entry: entry[0].casefold())),
    )
    if raw.get("aggregate_sha256") != aggregate_directory(snapshot):
        raise TransactionError(f"empreinte d'inventaire incohérente : {label}")
    if not present and snapshot.files:
        raise TransactionError(f"dossier absent avec fichiers dans le reçu : {label}")
    return snapshot


def same_directory(left: DirectorySnapshot, right: DirectorySnapshot) -> bool:
    return left == right


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def running_game_processes() -> list[str]:
    if os.name != "nt":
        return []
    try:
        completed = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise TransactionError("vérification des processus impossible") from exc
    if completed.returncode != 0:
        raise TransactionError("vérification des processus impossible")
    found = {
        row[0].strip()
        for row in csv.reader(completed.stdout.splitlines())
        if row and row[0].strip().casefold() in PROCESS_NAMES
    }
    return sorted(found, key=str.casefold)


def ensure_game_stopped(process_checker: ProcessChecker) -> None:
    running = process_checker()
    if running:
        raise TransactionError(
            "fermez BG2EE et InfinityLoader avant cette opération : " + ", ".join(running)
        )


def validate_game_root(game_root: Path) -> GamePaths:
    root = require_safe_directory(game_root, "racine de jeu")
    require_safe_file(root / "chitin.key", "chitin.key")
    dll = require_safe_file(root / "InfinityEngine-Enhancer.dll", "DLL runtime")
    ini = require_safe_file(root / "InfinityEngine-Enhancer.ini", "INI runtime")
    assets = require_safe_directory(root / "iee-assets", "iee-assets")
    areas = require_safe_directory(assets / "areas", "iee-assets/areas")
    if areas.parent != assets or assets.parent != root:
        raise TransactionError("hiérarchie iee-assets/areas inattendue")
    return GamePaths(root, dll, ini, areas)


def validate_ini_enabled(ini_path: Path) -> dict[str, object]:
    try:
        lines = ini_path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError as exc:
        raise TransactionError(f"INI illisible : {ini_path}") from exc
    section = ""
    matches: list[tuple[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith((";", "#")):
            continue
        section_match = re.fullmatch(r"\[([^\]]+)\]", stripped)
        if section_match:
            section = section_match.group(1).strip()
            continue
        assignment = re.match(r"^([^=]+)=(.*)$", stripped)
        if assignment and assignment.group(1).strip().casefold() == "enableareaanimationx4":
            value = assignment.group(2).strip()
            for marker in (";", "#"):
                marker_index = value.find(marker)
                if marker_index >= 0:
                    value = value[:marker_index].strip()
            matches.append((section, value))
    if len(matches) != 1 or matches[0][0].casefold() != "shaders" or matches[0][1].casefold() != "true":
        raise TransactionError("l'INI doit contenir exactement [Shaders] EnableAreaAnimationX4 = true")
    return {
        "path": str(ini_path),
        **snapshot_to_json(file_snapshot(ini_path, "INI runtime")),
        "key": "EnableAreaAnimationX4",
        "section": "Shaders",
        "effective_assignments": 1,
        "value": True,
    }


def load_manifest(pack_root: Path) -> dict[str, Any]:
    manifest_path = require_safe_file(pack_root / "manifest.json", "manifest pack")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionError(f"manifest JSON illisible : {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise TransactionError(f"manifest JSON objet requis : {manifest_path}")
    return payload


def validate_area_pack(area_pack: Path) -> AreaPack:
    root = require_safe_directory(area_pack, "pack de zone")
    manifest = load_manifest(root)
    if manifest.get("schema") != runtime_v2.PACK_SCHEMA or manifest.get("status") != "completed":
        raise TransactionError(f"pack de zone incomplet ou incompatible : {root}")
    if require_exact_int(manifest.get("scale"), "scale") != 4:
        raise TransactionError("échelle de pack différente de x4")
    registry_version = require_exact_int(manifest.get("registry_version"), "registry_version")
    if registry_version not in runtime_v2.SUPPORTED_REGISTRY_VERSIONS:
        raise TransactionError("version de registre non prise en charge")
    runtime_contract = manifest.get("runtime_contract")
    if not isinstance(runtime_contract, dict) or require_exact_int(
        runtime_contract.get("registry_version"), "runtime_contract.registry_version"
    ) != registry_version:
        raise TransactionError("contrat runtime/registre incohérent")
    if require_exact_bool(manifest.get("runtime_budget_enforced"), "runtime_budget_enforced") is not True:
        raise TransactionError("pack d'auteur ou budget runtime non confirmé")
    area_id = normalise_area(manifest.get("area_id"))
    if root.name != area_id:
        raise TransactionError(f"dossier de pack différent de son area_id : {root.name} != {area_id}")

    # The shared validator reconstructs the binary registry and validates every declared asset.
    try:
        validated_manifest, resources = runtime_v2.validate_v2_pack(root)
    except (RuntimeError, OSError, KeyError, TypeError, ValueError) as exc:
        raise TransactionError(f"pack runtime v2 invalide : {root}: {exc}") from exc
    if validated_manifest != manifest:
        raise TransactionError("manifest relu divergent")

    raw_bytes = 0
    source_files: list[SourceFile] = []
    expected_names = {"manifest.json"}
    registry_name = str(manifest.get("registry", ""))
    if registry_name != runtime_v2.REGISTRY_NAME:
        raise TransactionError("nom de registre runtime inattendu")
    registry_path = root / registry_name
    registry = file_snapshot(registry_path, "registre runtime")
    if registry.bytes != require_exact_int(manifest.get("registry_bytes"), "registry_bytes") or registry.sha256 != require_sha256(
        manifest.get("registry_sha256"), "registry_sha256"
    ):
        raise TransactionError("registre divergent du manifest")
    expected_names.add(registry_name)
    source_files.append(SourceFile(registry_name, registry_path, registry))

    for resource in resources:
        assets = resource.get("assets")
        if not isinstance(assets, list):
            raise TransactionError("assets runtime absents")
        for asset in assets:
            if not isinstance(asset, dict):
                raise TransactionError("asset runtime invalide")
            name = safe_name(asset.get("name"), "asset runtime")
            if name in expected_names:
                raise TransactionError(f"asset runtime dupliqué : {name}")
            path = root / name
            snapshot = file_snapshot(path, f"asset runtime {name}")
            if snapshot.bytes != require_exact_int(asset.get("bytes"), f"{name}.bytes") or snapshot.sha256 != require_sha256(
                asset.get("sha256"), f"{name}.sha256"
            ):
                raise TransactionError(f"asset runtime divergent : {path}")
            expected_names.add(name)
            raw_bytes += snapshot.bytes
            source_files.append(SourceFile(name, path, snapshot))
    if raw_bytes != require_exact_int(manifest.get("raw_bytes"), "raw_bytes"):
        raise TransactionError("raw_bytes divergent du contenu du pack")
    if raw_bytes > runtime_v2.MAX_RAW_BYTES:
        raise TransactionError("pack de zone au-delà du budget runtime")

    actual_names: set[str] = set()
    for child in root.iterdir():
        if child.is_symlink() or is_reparse(child) or not child.is_file():
            raise TransactionError(f"contenu supplémentaire ou non ordinaire dans le pack : {child}")
        actual_names.add(child.name)
    if actual_names != expected_names:
        raise TransactionError("inventaire physique du pack divergent du manifest")
    ordered = tuple(sorted(source_files, key=lambda item: item.name.casefold()))
    return AreaPack(
        root=root,
        area_id=area_id,
        manifest=file_snapshot(root / "manifest.json", "manifest pack"),
        registry_version=registry_version,
        registry=registry,
        files=ordered,
    )


def copy_file_checked(source: Path, target: Path, expected: FileSnapshot) -> None:
    temporary = target.parent / f".{target.name}.tmp-{uuid.uuid4().hex}"
    try:
        shutil.copyfile(source, temporary)
        if file_snapshot(temporary, f"copie temporaire {target.name}") != expected:
            raise TransactionError(f"copie temporaire divergente : {source}")
        os.replace(temporary, target)
    finally:
        if path_exists(temporary):
            temporary.unlink()


def copy_directory_snapshot(source: Path, snapshot: DirectorySnapshot, target: Path) -> None:
    if not snapshot.present:
        return
    if path_exists(target):
        raise TransactionError(f"staging déjà présent : {target}")
    target.mkdir(parents=False)
    try:
        for name, expected in snapshot.files:
            copy_file_checked(source / name, target / name, expected)
        if snapshot_directory(target, "staging sauvegarde") != snapshot:
            raise TransactionError("sauvegarde staging divergente")
    except Exception:
        if path_exists(target):
            safe_remove_tree(target, target.parent, target.name)
        raise


def copy_pack_payload(pack: AreaPack, target: Path) -> DirectorySnapshot:
    if path_exists(target):
        raise TransactionError(f"staging déjà présent : {target}")
    target.mkdir(parents=False)
    expected = DirectorySnapshot(
        True,
        tuple((entry.name, entry.snapshot) for entry in pack.files),
    )
    try:
        for entry in pack.files:
            copy_file_checked(entry.path, target / entry.name, entry.snapshot)
        actual = snapshot_directory(target, "staging installation")
        if actual != expected:
            raise TransactionError("staging installation divergent")
        return expected
    except Exception:
        if path_exists(target):
            safe_remove_tree(target, target.parent, target.name)
        raise


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    temporary = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if path_exists(temporary):
            temporary.unlink()


def safe_remove_tree(path: Path, expected_parent: Path, expected_name: str) -> None:
    if not path_exists(path):
        return
    if path.name != expected_name or path.parent.resolve(strict=True) != expected_parent.resolve(strict=True):
        raise TransactionError(f"suppression hors cible refusée : {path}")
    if path.is_symlink() or is_reparse(path) or not path.is_dir():
        raise TransactionError(f"suppression d'un dossier non sûr refusée : {path}")
    for child in path.rglob("*"):
        if child.is_symlink() or is_reparse(child):
            raise TransactionError(f"suppression d'un contenu lié refusée : {child}")
    shutil.rmtree(path)


def safe_remove_transient(path: Path, areas: Path, area_id: str, transaction_id: str) -> None:
    expected_prefix = f"{TRANSIENT_PREFIX}{area_id}-{transaction_id}-"
    if not path.name.startswith(expected_prefix):
        raise TransactionError(f"nom transitoire inattendu : {path}")
    safe_remove_tree(path, areas, path.name)


def transient_path(areas: Path, area_id: str, transaction_id: str, role: str) -> Path:
    if role not in {"incoming", "previous", "restore", "outgoing"}:
        raise TransactionError(f"rôle transitoire invalide : {role}")
    return areas / f"{TRANSIENT_PREFIX}{area_id}-{transaction_id}-{role}"


def assert_no_active_transient(areas: Path, area_id: str) -> None:
    prefix = f"{TRANSIENT_PREFIX}{area_id}-"
    found = [child.name for child in areas.iterdir() if child.name.startswith(prefix)]
    if found:
        raise TransactionError(
            f"transaction inachevée pour {area_id}; restauration requise avant nouvel essai : {sorted(found)}"
        )


def validate_backup_root(backup_root: Path, pack_root: Path, areas: Path) -> Path:
    candidate = backup_root.resolve(strict=False)
    if is_within(candidate, pack_root) or is_within(candidate, areas):
        raise TransactionError("BackupRoot ne peut pas être dans le pack source ni iee-assets/areas")
    candidate.mkdir(parents=True, exist_ok=True)
    return require_safe_directory(candidate, "BackupRoot")


def dll_observation(dll_path: Path) -> dict[str, object]:
    return {"path": str(dll_path), **snapshot_to_json(file_snapshot(dll_path, "DLL runtime"))}


def make_receipt(
    transaction_id: str,
    game: GamePaths,
    pack: AreaPack,
    backup_directory: Path,
    incoming: Path,
    previous_transient: Path,
    before: DirectorySnapshot,
    installed: DirectorySnapshot,
    ini_observation: dict[str, object],
) -> dict[str, object]:
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "prepared",
        "transaction_id": transaction_id,
        "created_at_utc": utc_now(),
        "area_id": pack.area_id,
        "game_root": str(game.root),
        "areas_root": str(game.areas),
        "target_area": str(game.areas / pack.area_id),
        "backup_directory": str(backup_directory),
        "previous_directory": str(backup_directory / "previous"),
        "transient": {
            "incoming": str(incoming),
            "previous": str(previous_transient),
        },
        "source_pack": {
            "root": str(pack.root),
            "manifest": snapshot_to_json(pack.manifest),
            "registry_version": pack.registry_version,
            "registry": snapshot_to_json(pack.registry),
        },
        "runtime_observed": {
            "dll": dll_observation(game.dll),
            "ini": ini_observation,
        },
        "before": directory_to_json(before),
        "installed": directory_to_json(installed),
    }


def load_receipt(path: Path) -> tuple[Path, dict[str, object]]:
    receipt_path = path
    if path_exists(receipt_path) and receipt_path.is_dir():
        receipt_path = receipt_path / RECEIPT_NAME
    receipt_path = require_safe_file(receipt_path, "reçu transactionnel")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionError(f"reçu JSON illisible : {receipt_path}") from exc
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise TransactionError(f"schéma de reçu incompatible : {receipt_path}")
    return receipt_path, receipt


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve(strict=False))) == os.path.normcase(
        str(right.resolve(strict=False))
    )


def receipt_transients(
    receipt: dict[str, object], areas: Path, area_id: str, transaction_id: str
) -> tuple[Path, Path]:
    raw = receipt.get("transient")
    if not isinstance(raw, dict):
        raise TransactionError("transitoires absents du reçu")
    incoming = transient_path(areas, area_id, transaction_id, "incoming")
    previous = transient_path(areas, area_id, transaction_id, "previous")
    if raw.get("incoming") != str(incoming) or raw.get("previous") != str(previous):
        raise TransactionError("transitoires incohérents dans le reçu")
    return incoming, previous


def validate_receipt_observation(raw: object, label: str) -> None:
    if not isinstance(raw, dict) or not isinstance(raw.get("path"), str):
        raise TransactionError(f"observation runtime invalide : {label}")
    snapshot_from_json(raw, label)


def validate_receipt_source_pack(raw: object) -> FileSnapshot:
    if not isinstance(raw, dict) or not isinstance(raw.get("root"), str):
        raise TransactionError("source_pack invalide dans le reçu")
    registry_version = require_exact_int(raw.get("registry_version"), "source_pack.registry_version")
    if registry_version not in runtime_v2.SUPPORTED_REGISTRY_VERSIONS:
        raise TransactionError("version de registre invalide dans le reçu")
    snapshot_from_json(raw.get("manifest"), "source_pack.manifest")
    return snapshot_from_json(raw.get("registry"), "source_pack.registry")


def cleanup_transient_if_present(path: Path, areas: Path, area_id: str, transaction_id: str) -> None:
    if path_exists(path):
        safe_remove_transient(path, areas, area_id, transaction_id)


def validate_receipt(
    receipt_path: Path, receipt: dict[str, object], game: GamePaths
) -> tuple[str, str, DirectorySnapshot, DirectorySnapshot, Path]:
    status = receipt.get("status")
    if status not in {"prepared", "switching", "installed", "restoring", "restored", "rolled-back", "recovery-required"}:
        raise TransactionError(f"statut de reçu invalide : {status!r}")
    transaction_id = receipt.get("transaction_id")
    if not isinstance(transaction_id, str) or not TRANSACTION_PATTERN.fullmatch(transaction_id):
        raise TransactionError("transaction_id invalide dans le reçu")
    area_id = normalise_area(receipt.get("area_id"), "reçu.area_id")
    if not transaction_id.startswith(area_id + "-"):
        raise TransactionError("transaction_id/zone incohérents dans le reçu")
    recorded_game = receipt.get("game_root")
    recorded_areas = receipt.get("areas_root")
    recorded_target = receipt.get("target_area")
    if not all(isinstance(item, str) for item in (recorded_game, recorded_areas, recorded_target)):
        raise TransactionError("chemins de jeu absents du reçu")
    try:
        if not same_path(Path(str(recorded_game)), game.root) or not same_path(Path(str(recorded_areas)), game.areas):
            raise TransactionError("le reçu appartient à une autre racine de jeu")
        if not same_path(Path(str(recorded_target)), game.areas / area_id):
            raise TransactionError("cible du reçu hors zones runtime")
    except (OSError, RuntimeError) as exc:
        if isinstance(exc, TransactionError):
            raise
        raise TransactionError("chemin de reçu invalide") from exc
    expected_backup = receipt_path.parent.resolve(strict=True)
    if receipt.get("backup_directory") != str(expected_backup):
        raise TransactionError("répertoire de sauvegarde incohérent dans le reçu")
    previous = expected_backup / "previous"
    if receipt.get("previous_directory") != str(previous):
        raise TransactionError("répertoire previous incohérent dans le reçu")
    source_registry = validate_receipt_source_pack(receipt.get("source_pack"))
    runtime_observed = receipt.get("runtime_observed")
    if not isinstance(runtime_observed, dict):
        raise TransactionError("observations runtime absentes du reçu")
    validate_receipt_observation(runtime_observed.get("dll"), "runtime_observed.dll")
    ini_observed = runtime_observed.get("ini")
    validate_receipt_observation(ini_observed, "runtime_observed.ini")
    if not isinstance(ini_observed, dict) or ini_observed.get("key") != "EnableAreaAnimationX4" or \
            ini_observed.get("section") != "Shaders" or ini_observed.get("effective_assignments") != 1 or \
            ini_observed.get("value") is not True:
        raise TransactionError("observation INI incohérente dans le reçu")
    before = directory_from_json(receipt.get("before"), "before")
    installed = directory_from_json(receipt.get("installed"), "installed")
    if not installed.present or not installed.files:
        raise TransactionError("état installé vide ou absent dans le reçu")
    installed_by_name = dict(installed.files)
    if "manifest.json" in installed_by_name or installed_by_name.get(runtime_v2.REGISTRY_NAME) != source_registry:
        raise TransactionError("inventaire installé incohérent avec le pack du reçu")
    if before.present:
        if snapshot_directory(previous, "sauvegarde précédente") != before:
            raise TransactionError("sauvegarde précédente divergente du reçu")
    elif path_exists(previous):
        raise TransactionError("sauvegarde précédente inattendue pour une zone absente")
    return str(status), transaction_id, before, installed, previous


def update_receipt_status(receipt_path: Path, receipt: dict[str, object], status: str, **extra: object) -> dict[str, object]:
    updated = dict(receipt)
    updated["status"] = status
    updated.update(extra)
    write_json_atomic(receipt_path, updated)
    return updated


def invoke_failure(hook: FailureHook | None, point: str) -> None:
    if hook is not None:
        hook(point)


def restore_from_receipt(
    backup_path: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
    final_status: str = "restored",
) -> dict[str, object]:
    ensure_game_stopped(process_checker)
    game = validate_game_root(game_root)
    receipt_path, receipt = load_receipt(backup_path)
    status, transaction_id, before, installed, previous = validate_receipt(receipt_path, receipt, game)
    area_id = normalise_area(receipt["area_id"])
    incoming, previous_transient = receipt_transients(receipt, game.areas, area_id, transaction_id)
    target = game.areas / area_id
    current = snapshot_directory(target, "zone runtime courante")

    if status in {"restored", "rolled-back"}:
        if current != before:
            raise TransactionError("état restauré divergent du reçu")
        return receipt
    if status == "installed":
        if current != installed:
            raise TransactionError("état installé divergent ; restauration refusée")
    elif current not in {before, installed, DirectorySnapshot(False, ())}:
        raise TransactionError("état transactionnel non récupérable ; restauration refusée")

    if verify_only:
        return receipt
    if current == before:
        cleanup_transient_if_present(incoming, game.areas, area_id, transaction_id)
        cleanup_transient_if_present(previous_transient, game.areas, area_id, transaction_id)
        return update_receipt_status(
            receipt_path,
            receipt,
            final_status,
            restored_at_utc=utc_now(),
        )

    restore_stage = transient_path(game.areas, area_id, transaction_id, "restore")
    outgoing = transient_path(game.areas, area_id, transaction_id, "outgoing")
    try:
        # Stages from an interrupted restoration are disposable: the durable backup remains
        # authoritative and the target was already checked against a recognized state.
        cleanup_transient_if_present(restore_stage, game.areas, area_id, transaction_id)
        cleanup_transient_if_present(outgoing, game.areas, area_id, transaction_id)
        if before.present:
            copy_directory_snapshot(previous, before, restore_stage)
        receipt = update_receipt_status(receipt_path, receipt, "restoring", restoration_started_at_utc=utc_now())
        if current.present:
            os.replace(target, outgoing)
        if before.present:
            os.replace(restore_stage, target)
        if snapshot_directory(target, "zone restaurée") != before:
            raise TransactionError("vérification post-restauration échouée")
        receipt = update_receipt_status(receipt_path, receipt, final_status, restored_at_utc=utc_now())
        cleanup_transient_if_present(outgoing, game.areas, area_id, transaction_id)
        cleanup_transient_if_present(restore_stage, game.areas, area_id, transaction_id)
        cleanup_transient_if_present(incoming, game.areas, area_id, transaction_id)
        cleanup_transient_if_present(previous_transient, game.areas, area_id, transaction_id)
        return receipt
    except Exception as restore_error:
        try:
            update_receipt_status(
                receipt_path,
                receipt,
                "recovery-required",
                restoration_failure_at_utc=utc_now(),
                restoration_failure=str(restore_error),
            )
        except Exception:
            pass
        raise


def install_area_pack(
    area_pack: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
    failure_hook: FailureHook | None = None,
) -> InstallResult:
    ensure_game_stopped(process_checker)
    game = validate_game_root(game_root)
    pack = validate_area_pack(area_pack)
    assert_no_active_transient(game.areas, pack.area_id)
    target = game.areas / pack.area_id
    before = snapshot_directory(target, "zone runtime cible")
    installed = DirectorySnapshot(True, tuple((entry.name, entry.snapshot) for entry in pack.files))
    incoming_bytes = sum(entry.snapshot.bytes for entry in pack.files)
    ini = validate_ini_enabled(game.ini)
    if verify_only:
        return InstallResult("verified-only", pack.area_id, None, len(pack.files), incoming_bytes)
    if before == installed:
        return InstallResult("already-installed", pack.area_id, None, len(pack.files), incoming_bytes)

    backup_parent = validate_backup_root(backup_root, pack.root, game.areas)
    transaction_id = (
        f"{pack.area_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-"
        f"{uuid.uuid4().hex[:8]}"
    )
    backup_staging = backup_parent / f".{transaction_id}.installing"
    backup_directory = backup_parent / transaction_id
    incoming = transient_path(game.areas, pack.area_id, transaction_id, "incoming")
    previous_transient = transient_path(game.areas, pack.area_id, transaction_id, "previous")
    if path_exists(backup_staging) or path_exists(backup_directory) or path_exists(incoming) or path_exists(previous_transient):
        raise TransactionError("collision de transaction")

    receipt_path: Path | None = None
    receipt: dict[str, object] | None = None
    try:
        backup_staging.mkdir(parents=False)
        if before.present:
            copy_directory_snapshot(target, before, backup_staging / "previous")
        invoke_failure(failure_hook, "after-backup")
        copy_pack_payload(pack, incoming)
        invoke_failure(failure_hook, "after-staging")
        receipt = make_receipt(
            transaction_id,
            game,
            pack,
            backup_directory,
            incoming,
            previous_transient,
            before,
            installed,
            ini,
        )
        write_json_atomic(backup_staging / RECEIPT_NAME, receipt)
        os.replace(backup_staging, backup_directory)
        receipt_path = backup_directory / RECEIPT_NAME
        invoke_failure(failure_hook, "before-switch")
        if snapshot_directory(target, "zone runtime avant bascule") != before:
            raise TransactionError("zone cible modifiée pendant la prévalidation")
        receipt = update_receipt_status(receipt_path, receipt, "switching", switch_started_at_utc=utc_now())
        if before.present:
            os.replace(target, previous_transient)
        invoke_failure(failure_hook, "after-target-moved")
        os.replace(incoming, target)
        invoke_failure(failure_hook, "after-install-published")
        if snapshot_directory(target, "zone runtime installée") != installed:
            raise TransactionError("vérification post-installation échouée")
        if path_exists(previous_transient):
            safe_remove_transient(previous_transient, game.areas, pack.area_id, transaction_id)
        receipt = update_receipt_status(receipt_path, receipt, "installed", installed_at_utc=utc_now())
        return InstallResult("installed", pack.area_id, receipt_path, len(pack.files), incoming_bytes)
    except Exception as install_error:
        if receipt_path is None or receipt is None:
            if path_exists(incoming):
                safe_remove_transient(incoming, game.areas, pack.area_id, transaction_id)
            if path_exists(backup_staging):
                safe_remove_tree(backup_staging, backup_parent, backup_staging.name)
            raise
        try:
            restore_from_receipt(
                receipt_path,
                game_root=game.root,
                process_checker=lambda: [],
                final_status="rolled-back",
            )
        except Exception as rollback_error:
            try:
                update_receipt_status(
                    receipt_path,
                    receipt,
                    "recovery-required",
                    install_failure_at_utc=utc_now(),
                    install_failure=str(install_error),
                    rollback_failure=str(rollback_error),
                )
            except Exception:
                pass
            raise TransactionError(
                f"installation échouée ; récupération manuelle requise avec {receipt_path}"
            ) from install_error
        raise TransactionError(
            f"installation échouée ; état initial restauré, reçu {receipt_path}"
        ) from install_error


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Installe/restaure transactionnellement un pack d'animations d'une seule zone."
    )
    commands = result.add_subparsers(dest="command", required=True)
    install = commands.add_parser("install", help="installer un pack de zone terminé")
    install.add_argument("--area-pack", required=True, type=Path)
    install.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    install.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    install.add_argument("--verify-only", action="store_true")
    restore = commands.add_parser("restore", help="restaurer une transaction")
    restore.add_argument("--backup-path", required=True, type=Path)
    restore.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    restore.add_argument("--verify-only", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "install":
            result = install_area_pack(
                args.area_pack,
                game_root=args.game_root,
                backup_root=args.backup_root,
                verify_only=args.verify_only,
            )
            if result.status == "verified-only":
                print(
                    f"VerifyOnly : {result.area_id}, {result.incoming_files} fichier(s), "
                    f"{result.incoming_bytes} octets ; aucune écriture."
                )
            elif result.status == "already-installed":
                print(f"Déjà installé et byte-identique : {result.area_id}; aucune écriture.")
            else:
                print(
                    f"Installation vérifiée : {result.area_id}, {result.incoming_files} fichier(s), "
                    f"{result.incoming_bytes} octets."
                )
                print(f"Sauvegarde : {result.receipt_path.parent if result.receipt_path else ''}")
            return 0
        receipt = restore_from_receipt(
            args.backup_path,
            game_root=args.game_root,
            verify_only=args.verify_only,
        )
        if args.verify_only:
            print(f"VerifyOnly : reçu et état {receipt['status']} vérifiés ; aucune écriture.")
        else:
            print(f"Restauration vérifiée : {receipt['area_id']}; statut {receipt['status']}.")
        return 0
    except TransactionError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
