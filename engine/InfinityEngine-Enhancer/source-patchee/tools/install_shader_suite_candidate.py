"""Prepare, install, verify, or restore a shader-suite candidate transaction.

The candidate manifest fixes both the exact shader list and the expected
pre-install state. An unexpected target shader is treated as a third-party
collision and is never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from workspace_paths import get_path  # noqa: E402

DEFAULT_GAME_ROOT = get_path("bg2ee_game_root")
DEFAULT_BACKUP_ROOT = PROJECT_ROOT / "backups" / "shader-suite"
CANDIDATE_MANIFEST = "shader-candidate.json"
CANDIDATE_SCHEMA = "bg2-upscale-shader-suite-candidate-v1"
RECEIPT_NAME = "shader-install-receipt.json"
RECEIPT_SCHEMA = "bg2-upscale-shader-suite-install-backup-v1"
PAYLOAD_DIRECTORY = "candidate"
BACKUP_DIRECTORY = "before"
OVERRIDE_DIRECTORY = "override"
TARGET_SHADERS = (
    "fpSprite.glsl",
    "fpSELECT.glsl",
    "fpDraw.glsl",
    "fpTone.glsl",
    "fpFONT.glsl",
    "fpSEAM.glsl",
    "fpYUV.glsl",
    "fpYUVGRY.glsl",
)
TARGET_BY_CASEFOLD = {name.casefold(): name for name in TARGET_SHADERS}
GAME_EXECUTABLES = ("BaldurReal.exe", "Baldur.exe")
PROCESS_NAMES = {"baldur.exe", "baldurreal.exe", "infinityloader.exe"}
KNOWN_STATUSES = {
    "prepared",
    "installing",
    "installed",
    "restoring",
    "restored",
    "rolled-back",
    "recovery-required",
}


class TransactionError(RuntimeError):
    """A fail-closed candidate or transaction error."""


@dataclass(frozen=True)
class FileSnapshot:
    bytes: int
    sha256: str


@dataclass(frozen=True)
class CandidateFile:
    name: str
    path: Path
    snapshot: FileSnapshot
    expected_before: FileSnapshot | None


@dataclass(frozen=True)
class OperationResult:
    status: str
    receipt_path: Path | None
    files: tuple[str, ...]


ProcessChecker = Callable[[], list[str]]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def snapshot_file(path: Path) -> FileSnapshot:
    if path.is_symlink() or not path.is_file():
        raise TransactionError(f"fichier ordinaire attendu : {path}")
    return FileSnapshot(path.stat().st_size, sha256_file(path))


def optional_snapshot(path: Path) -> FileSnapshot | None:
    if path.is_symlink():
        raise TransactionError(f"lien symbolique interdit : {path}")
    if not path.exists():
        return None
    return snapshot_file(path)


def state_to_json(state: FileSnapshot | None) -> dict[str, object]:
    if state is None:
        return {"present": False, "bytes": None, "sha256": None}
    return {"present": True, "bytes": state.bytes, "sha256": state.sha256}


def state_from_json(raw: object, label: str) -> FileSnapshot | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("present"), bool):
        raise TransactionError(f"état invalide : {label}")
    if not raw["present"]:
        if raw.get("bytes") is not None or raw.get("sha256") is not None:
            raise TransactionError(f"état absent incohérent : {label}")
        return None
    byte_count = raw.get("bytes")
    digest = raw.get("sha256")
    if not isinstance(byte_count, int) or byte_count <= 0:
        raise TransactionError(f"taille invalide : {label}")
    if not isinstance(digest, str) or not re.fullmatch(r"[A-Fa-f0-9]{64}", digest):
        raise TransactionError(f"SHA-256 invalide : {label}")
    return FileSnapshot(byte_count, digest.upper())


def aggregate_hash(items: Iterable[tuple[str, FileSnapshot | None]]) -> str:
    digest = hashlib.sha256()
    for name, state in sorted(items):
        digest.update(name.encode("ascii"))
        digest.update(b"\0")
        if state is None:
            digest.update(b"ABSENT")
        else:
            digest.update(str(state.bytes).encode("ascii"))
            digest.update(b"\0")
            digest.update(state.sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest().upper()


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    temporary = path.parent / f".{path.name}.tmp-{uuid.uuid4().hex}"
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_copy(source: Path, target: Path, expected: FileSnapshot) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".{target.name}.tmp-{uuid.uuid4().hex}"
    try:
        shutil.copy2(source, temporary)
        if snapshot_file(temporary) != expected:
            raise TransactionError(f"copie temporaire divergente : {source}")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def safe_unlink(target: Path, expected: FileSnapshot) -> None:
    if optional_snapshot(target) != expected:
        raise TransactionError(f"refus de retirer un fichier divergent : {target}")
    target.unlink()


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
        raise TransactionError("impossible de vérifier les processus actifs") from exc
    if completed.returncode != 0:
        raise TransactionError("impossible de vérifier les processus actifs")
    found: list[str] = []
    for row in csv.reader(completed.stdout.splitlines()):
        if row and row[0].strip().casefold() in PROCESS_NAMES:
            found.append(row[0].strip())
    return sorted(set(found), key=str.casefold)


def ensure_game_stopped(process_checker: ProcessChecker) -> None:
    running = process_checker()
    if running:
        raise TransactionError(
            "fermez BG2EE et InfinityLoader avant cette opération : "
            + ", ".join(running)
        )


def validate_game_root(game_root: Path) -> Path:
    if game_root.is_symlink():
        raise TransactionError(f"racine de jeu liée interdite : {game_root}")
    game = game_root.resolve(strict=True)
    if not game.is_dir() or game.is_symlink():
        raise TransactionError(f"racine de jeu invalide : {game}")
    if not any(
        (game / name).is_file() and not (game / name).is_symlink()
        for name in GAME_EXECUTABLES
    ):
        raise TransactionError(f"racine de jeu sans exécutable BG2EE : {game}")
    return game


def validate_backup_root(backup_root: Path, game: Path, *, create: bool) -> Path:
    if backup_root.is_symlink():
        raise TransactionError(f"racine de sauvegarde liée interdite : {backup_root}")
    backup = backup_root.resolve()
    if backup == game or game in backup.parents:
        raise TransactionError("la racine de sauvegarde ne peut pas être dans le jeu")
    if create:
        backup.mkdir(parents=True, exist_ok=True)
    if backup.exists() and (not backup.is_dir() or backup.is_symlink()):
        raise TransactionError(f"racine de sauvegarde invalide : {backup}")
    return backup


def exact_shader_inventory(root: Path, *, allow_subset: bool) -> tuple[str, ...]:
    if root.is_symlink() or not root.is_dir():
        raise TransactionError(f"répertoire shaders invalide : {root}")
    names: dict[str, str] = {}
    for entry in root.iterdir():
        if entry.is_symlink() or not entry.is_file():
            raise TransactionError(f"inventaire shaders invalide : {entry}")
        folded = entry.name.casefold()
        if folded in names:
            raise TransactionError(f"collision de casse dans le candidat : {entry.name}")
        canonical = TARGET_BY_CASEFOLD.get(folded)
        if canonical is None or entry.name != canonical:
            raise TransactionError(f"shader non géré ou casse non canonique : {entry.name}")
        names[folded] = entry.name
    if not names and not allow_subset:
        raise TransactionError(f"aucun shader candidat : {root}")
    ordered = tuple(name for name in TARGET_SHADERS if name.casefold() in names)
    if not allow_subset and set(ordered) != set(TARGET_SHADERS):
        missing = [name for name in TARGET_SHADERS if name not in ordered]
        raise TransactionError("suite D3 incomplète : " + ", ".join(missing))
    return ordered


def validate_shader(path: Path, name: str) -> FileSnapshot:
    snapshot = snapshot_file(path)
    try:
        source = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TransactionError(f"shader non UTF-8 : {path}") from exc
    stem = name.removesuffix(".glsl")
    if (
        f"// {name}" not in source
        or "void main" not in source
        or "uIeeShaderSuiteEnabled" not in source
        or "#version" in source
        or not re.search(rf"\b{re.escape(stem)}\b", f"// {name}")
    ):
        raise TransactionError(f"contrat shader D3 invalide : {path}")
    return snapshot


def prepare_candidate(
    source_override: Path,
    candidate_root: Path,
    *,
    baseline_override: Path | None = None,
) -> Path:
    source = source_override.resolve(strict=True)
    shaders = exact_shader_inventory(source, allow_subset=False)
    baseline: Path | None = None
    baseline_names: tuple[str, ...] = ()
    if baseline_override is not None:
        baseline = baseline_override.resolve(strict=True)
        baseline_names = exact_shader_inventory(baseline, allow_subset=True)
    candidate = candidate_root.resolve()
    if candidate.exists() or candidate.is_symlink():
        raise TransactionError(f"le candidat doit être nouveau : {candidate}")
    candidate.parent.mkdir(parents=True, exist_ok=True)
    temporary = candidate.parent / f".{candidate.name}.tmp-{uuid.uuid4().hex}"
    try:
        override = temporary / OVERRIDE_DIRECTORY
        override.mkdir(parents=True)
        files: list[dict[str, object]] = []
        for name in shaders:
            source_path = source / name
            installed = validate_shader(source_path, name)
            target = override / name
            shutil.copy2(source_path, target)
            if snapshot_file(target) != installed:
                raise TransactionError(f"copie candidat divergente : {name}")
            expected_before = (
                snapshot_file(baseline / name)
                if baseline is not None and name in baseline_names
                else None
            )
            files.append(
                {
                    "name": name,
                    "path": f"{OVERRIDE_DIRECTORY}/{name}",
                    "candidate": state_to_json(installed),
                    "expected_before": state_to_json(expected_before),
                }
            )
        manifest: dict[str, object] = {
            "schema": CANDIDATE_SCHEMA,
            "created_at_utc": utc_now(),
            "suite_contract": "sprite/catmull-rom/profiles/shader-suite-contract-v1.json",
            "status": "prepared",
            "files": files,
        }
        write_json_atomic(temporary / CANDIDATE_MANIFEST, manifest)
        os.replace(temporary, candidate)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return candidate / CANDIDATE_MANIFEST


def load_json(path: Path, schema: str, label: str) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise TransactionError(f"{label} absent ou lié : {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionError(f"{label} JSON illisible : {path}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != schema:
        raise TransactionError(f"schéma {label} incompatible : {path}")
    return payload


def validate_candidate(candidate_root: Path) -> tuple[Path, tuple[CandidateFile, ...]]:
    if candidate_root.is_symlink():
        raise TransactionError(f"candidat lié interdit : {candidate_root}")
    root = candidate_root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise TransactionError(f"candidat invalide : {root}")
    root_entries = {entry.name for entry in root.iterdir()}
    if root_entries != {CANDIDATE_MANIFEST, OVERRIDE_DIRECTORY}:
        raise TransactionError("inventaire racine candidat invalide")
    manifest = load_json(root / CANDIDATE_MANIFEST, CANDIDATE_SCHEMA, "manifeste candidat")
    override = root / OVERRIDE_DIRECTORY
    inventory = exact_shader_inventory(override, allow_subset=False)
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise TransactionError("liste de shaders candidate invalide")
    files: list[CandidateFile] = []
    names: list[str] = []
    for raw in raw_files:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise TransactionError("entrée shader candidate invalide")
        name = raw["name"]
        if name not in TARGET_SHADERS or name in names:
            raise TransactionError(f"shader candidat dupliqué ou non géré : {name}")
        if raw.get("path") != f"{OVERRIDE_DIRECTORY}/{name}":
            raise TransactionError(f"chemin shader candidat invalide : {name}")
        candidate_state = state_from_json(raw.get("candidate"), f"{name}.candidate")
        if candidate_state is None:
            raise TransactionError(f"état candidat absent : {name}")
        actual = validate_shader(override / name, name)
        if actual != candidate_state:
            raise TransactionError(f"hash shader candidat divergent : {name}")
        files.append(
            CandidateFile(
                name=name,
                path=override / name,
                snapshot=actual,
                expected_before=state_from_json(
                    raw.get("expected_before"), f"{name}.expected_before"
                ),
            )
        )
        names.append(name)
    if tuple(names) != inventory:
        raise TransactionError("manifeste et inventaire shaders divergent")
    return root, tuple(files)


def resolve_game_targets(
    game: Path, files: tuple[CandidateFile, ...]
) -> dict[str, Path]:
    override = game / OVERRIDE_DIRECTORY
    if override.is_symlink():
        raise TransactionError(f"override lié interdit : {override}")
    entries = list(override.iterdir()) if override.exists() else []
    targets: dict[str, Path] = {}
    for file in files:
        matches = [entry for entry in entries if entry.name.casefold() == file.name.casefold()]
        if len(matches) > 1:
            raise TransactionError(f"collision de casse dans override : {file.name}")
        if matches and (matches[0].name != file.name or matches[0].is_symlink()):
            raise TransactionError(f"collision shader non canonique : {matches[0]}")
        targets[file.name] = override / file.name
    return targets


def create_receipt(
    transaction_root: Path,
    game: Path,
    candidate_root: Path,
    files: tuple[CandidateFile, ...],
) -> dict[str, object]:
    payload_root = transaction_root / PAYLOAD_DIRECTORY / OVERRIDE_DIRECTORY
    before_root = transaction_root / BACKUP_DIRECTORY / OVERRIDE_DIRECTORY
    payload_root.mkdir(parents=True)
    before_root.mkdir(parents=True)
    rows: list[dict[str, object]] = []
    for file in files:
        before = optional_snapshot(game / OVERRIDE_DIRECTORY / file.name)
        if before != file.expected_before:
            raise TransactionError(
                f"collision ou état initial inattendu : {OVERRIDE_DIRECTORY}/{file.name}"
            )
        staged = payload_root / file.name
        atomic_copy(file.path, staged, file.snapshot)
        if before is not None:
            atomic_copy(game / OVERRIDE_DIRECTORY / file.name, before_root / file.name, before)
        rows.append(
            {
                "name": file.name,
                "target": f"{OVERRIDE_DIRECTORY}/{file.name}",
                "payload": f"{PAYLOAD_DIRECTORY}/{OVERRIDE_DIRECTORY}/{file.name}",
                "backup": (
                    f"{BACKUP_DIRECTORY}/{OVERRIDE_DIRECTORY}/{file.name}"
                    if before is not None
                    else None
                ),
                "before": state_to_json(before),
                "installed": state_to_json(file.snapshot),
            }
        )
    before_hash = aggregate_hash(
        (str(row["target"]), state_from_json(row["before"], str(row["target"])))
        for row in rows
    )
    installed_hash = aggregate_hash(
        (str(row["target"]), state_from_json(row["installed"], str(row["target"])))
        for row in rows
    )
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "prepared",
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "game_root": str(game),
        "source_candidate": str(candidate_root),
        "managed_files": [row["target"] for row in rows],
        "before_aggregate_sha256": before_hash,
        "installed_aggregate_sha256": installed_hash,
        "files": rows,
    }


def set_receipt_status(
    receipt_path: Path, receipt: dict[str, object], status: str
) -> None:
    receipt["status"] = status
    receipt["updated_at_utc"] = utc_now()
    write_json_atomic(receipt_path, receipt)


def receipt_path_from(argument: Path) -> Path:
    path = argument.resolve(strict=True)
    if path.is_dir():
        path = path / RECEIPT_NAME
    return path


def validate_receipt_payload(
    receipt_path: Path,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    receipt = load_json(receipt_path, RECEIPT_SCHEMA, "reçu")
    if receipt.get("status") not in KNOWN_STATUSES:
        raise TransactionError(f"statut de reçu invalide : {receipt.get('status')}")
    managed = receipt.get("managed_files")
    raw_files = receipt.get("files")
    expected_managed = [f"{OVERRIDE_DIRECTORY}/{name}" for name in TARGET_SHADERS]
    if (
        not isinstance(managed, list)
        or not isinstance(raw_files, list)
        or managed != expected_managed
        or len(raw_files) != len(TARGET_SHADERS)
    ):
        raise TransactionError("inventaire du reçu invalide")
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    root = receipt_path.parent
    for raw in raw_files:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise TransactionError("entrée de reçu invalide")
        name = raw["name"]
        target = f"{OVERRIDE_DIRECTORY}/{name}"
        if name not in TARGET_SHADERS or target in seen or raw.get("target") != target:
            raise TransactionError(f"cible de reçu invalide : {name}")
        if target not in managed:
            raise TransactionError(f"cible non gérée dans le reçu : {target}")
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        before = state_from_json(raw.get("before"), f"{name}.before")
        if installed is None:
            raise TransactionError(f"état installé absent : {name}")
        expected_payload = f"{PAYLOAD_DIRECTORY}/{OVERRIDE_DIRECTORY}/{name}"
        expected_backup = (
            f"{BACKUP_DIRECTORY}/{OVERRIDE_DIRECTORY}/{name}" if before else None
        )
        if raw.get("payload") != expected_payload or raw.get("backup") != expected_backup:
            raise TransactionError(f"chemins de reçu invalides : {name}")
        if snapshot_file(root / expected_payload) != installed:
            raise TransactionError(f"payload candidat corrompu : {name}")
        if before is not None and snapshot_file(root / expected_backup) != before:
            raise TransactionError(f"sauvegarde corrompue : {name}")
        seen.add(target)
        rows.append(raw)
    if set(managed) != seen:
        raise TransactionError("liste de fichiers gérés incohérente")
    before_hash = aggregate_hash(
        (str(raw["target"]), state_from_json(raw["before"], str(raw["target"])))
        for raw in rows
    )
    installed_hash = aggregate_hash(
        (str(raw["target"]), state_from_json(raw["installed"], str(raw["target"])))
        for raw in rows
    )
    if before_hash != receipt.get("before_aggregate_sha256") or installed_hash != receipt.get(
        "installed_aggregate_sha256"
    ):
        raise TransactionError("empreinte agrégée du reçu invalide")
    return receipt, rows


def verify_target_state(game: Path, rows: list[dict[str, object]], state: str) -> None:
    for raw in rows:
        expected = state_from_json(raw[state], f"{raw['name']}.{state}")
        if optional_snapshot(game / str(raw["target"])) != expected:
            raise TransactionError(f"état {state} divergent : {raw['target']}")


def rollback_rows(
    game: Path, receipt_path: Path, receipt: dict[str, object], rows: list[dict[str, object]]
) -> bool:
    root = receipt_path.parent
    try:
        for raw in reversed(rows):
            target = game / str(raw["target"])
            before = state_from_json(raw["before"], f"{raw['name']}.before")
            installed = state_from_json(raw["installed"], f"{raw['name']}.installed")
            current = optional_snapshot(target)
            if current == before:
                continue
            if current != installed:
                raise TransactionError(f"récupération refusée, fichier divergent : {target}")
            if before is None:
                safe_unlink(target, installed)
            else:
                atomic_copy(root / str(raw["backup"]), target, before)
        verify_target_state(game, rows, "before")
        set_receipt_status(receipt_path, receipt, "rolled-back")
        return True
    except (OSError, TransactionError):
        set_receipt_status(receipt_path, receipt, "recovery-required")
        return False


def install_candidate(
    candidate_root: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
) -> OperationResult:
    ensure_game_stopped(process_checker)
    source_root, files = validate_candidate(candidate_root)
    game = validate_game_root(game_root)
    targets = resolve_game_targets(game, files)
    for file in files:
        if optional_snapshot(targets[file.name]) != file.expected_before:
            raise TransactionError(
                f"collision ou état initial inattendu : {OVERRIDE_DIRECTORY}/{file.name}"
            )
    if verify_only:
        return OperationResult("verified", None, tuple(f.name for f in files))

    backup = validate_backup_root(backup_root, game, create=True)
    transaction_root = backup / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    transaction_root.mkdir(parents=False)
    receipt_path = transaction_root / RECEIPT_NAME
    try:
        receipt = create_receipt(transaction_root, game, source_root, files)
        write_json_atomic(receipt_path, receipt)
        receipt, rows = validate_receipt_payload(receipt_path)
        set_receipt_status(receipt_path, receipt, "installing")
        for raw in rows:
            installed = state_from_json(raw["installed"], f"{raw['name']}.installed")
            assert installed is not None
            atomic_copy(
                transaction_root / str(raw["payload"]),
                game / str(raw["target"]),
                installed,
            )
        verify_target_state(game, rows, "installed")
        set_receipt_status(receipt_path, receipt, "installed")
        return OperationResult("installed", receipt_path, tuple(f.name for f in files))
    except (OSError, TransactionError) as exc:
        if receipt_path.exists():
            receipt, rows = validate_receipt_payload(receipt_path)
            if rollback_rows(game, receipt_path, receipt, rows):
                raise TransactionError(
                    f"installation échouée ; état initial restauré : {exc}"
                ) from exc
            raise TransactionError(
                f"installation échouée ; récupération manuelle requise : {receipt_path}"
            ) from exc
        shutil.rmtree(transaction_root, ignore_errors=True)
        raise


def verify_transaction(receipt_argument: Path, game_root: Path = DEFAULT_GAME_ROOT) -> dict[str, object]:
    receipt_path = receipt_path_from(receipt_argument)
    receipt, rows = validate_receipt_payload(receipt_path)
    game = validate_game_root(game_root)
    if Path(str(receipt.get("game_root"))).resolve() != game:
        raise TransactionError("reçu créé pour une autre racine de jeu")
    status = str(receipt["status"])
    if status == "installed":
        verify_target_state(game, rows, "installed")
    elif status in {"restored", "rolled-back"}:
        verify_target_state(game, rows, "before")
    else:
        for raw in rows:
            current = optional_snapshot(game / str(raw["target"]))
            before = state_from_json(raw["before"], f"{raw['name']}.before")
            installed = state_from_json(raw["installed"], f"{raw['name']}.installed")
            if current not in {before, installed}:
                raise TransactionError(f"état de récupération divergent : {raw['target']}")
    return receipt


def restore_from_receipt(
    receipt_argument: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
) -> dict[str, object]:
    ensure_game_stopped(process_checker)
    receipt_path = receipt_path_from(receipt_argument)
    receipt, rows = validate_receipt_payload(receipt_path)
    game = validate_game_root(game_root)
    if Path(str(receipt.get("game_root"))).resolve() != game:
        raise TransactionError("reçu créé pour une autre racine de jeu")
    for raw in rows:
        current = optional_snapshot(game / str(raw["target"]))
        before = state_from_json(raw["before"], f"{raw['name']}.before")
        installed = state_from_json(raw["installed"], f"{raw['name']}.installed")
        if current not in {before, installed}:
            raise TransactionError(f"récupération refusée, fichier divergent : {raw['target']}")
    if verify_only:
        return receipt
    if receipt["status"] in {"restored", "rolled-back"}:
        verify_target_state(game, rows, "before")
        return receipt

    set_receipt_status(receipt_path, receipt, "restoring")
    root = receipt_path.parent
    try:
        for raw in reversed(rows):
            target = game / str(raw["target"])
            before = state_from_json(raw["before"], f"{raw['name']}.before")
            installed = state_from_json(raw["installed"], f"{raw['name']}.installed")
            current = optional_snapshot(target)
            if current == before:
                continue
            if installed is None or current != installed:
                raise TransactionError(f"récupération refusée : {raw['target']}")
            if before is None:
                safe_unlink(target, installed)
            else:
                atomic_copy(root / str(raw["backup"]), target, before)
        verify_target_state(game, rows, "before")
        set_receipt_status(receipt_path, receipt, "restored")
        return receipt
    except (OSError, TransactionError) as exc:
        set_receipt_status(receipt_path, receipt, "recovery-required")
        raise TransactionError(
            f"restauration interrompue ; reprendre avec le même reçu : {receipt_path}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prépare ou gère une transaction de shaders expérimentaux."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="créer un candidat scellé")
    prepare.add_argument("source_override", type=Path)
    prepare.add_argument("candidate_root", type=Path)
    prepare.add_argument("--baseline-override", type=Path)
    install = commands.add_parser("install", help="installer un candidat")
    install.add_argument("candidate_root", type=Path)
    install.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    install.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    install.add_argument("--verify-only", action="store_true")
    restore = commands.add_parser("restore", help="restaurer depuis un reçu")
    restore.add_argument("receipt", type=Path)
    restore.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    restore.add_argument("--verify-only", action="store_true")
    verify = commands.add_parser("verify", help="vérifier reçu, payload et état")
    verify.add_argument("receipt", type=Path)
    verify.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "prepare":
        manifest = prepare_candidate(
            args.source_override,
            args.candidate_root,
            baseline_override=args.baseline_override,
        )
        print(f"candidat préparé : {manifest}")
        return
    if args.command == "install":
        result = install_candidate(
            args.candidate_root,
            game_root=args.game_root,
            backup_root=args.backup_root,
            verify_only=args.verify_only,
        )
        if result.receipt_path is None:
            print(f"prévalidation réussie ; {len(result.files)} shaders ; aucune écriture")
        else:
            print(f"installation vérifiée ; reçu : {result.receipt_path}")
        return
    if args.command == "restore":
        receipt = restore_from_receipt(
            args.receipt,
            game_root=args.game_root,
            verify_only=args.verify_only,
        )
        print(f"reçu et état {receipt['status']} vérifiés")
        return
    receipt = verify_transaction(args.receipt, args.game_root)
    print(f"reçu, payload, sauvegardes et état {receipt['status']} vérifiés")


if __name__ == "__main__":
    try:
        main()
    except (OSError, TransactionError) as exc:
        raise SystemExit(f"ERREUR : {exc}") from exc
