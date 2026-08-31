"""Install or restore an experimental renderer candidate transactionally.

The transaction owns exactly ``InfinityEngine-Enhancer.dll`` and
``InfinityEngine-Enhancer.ini`` in the selected game root.  It stages verified
copies of both the candidate and the previous state before publishing a receipt
or mutating the game.  Restore therefore remains possible when the original
build directory no longer exists.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import struct
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
DEFAULT_BACKUP_ROOT = PROJECT_ROOT / "backups" / "renderer"
RECEIPT_NAME = "renderer-install-receipt.json"
RECEIPT_SCHEMA = "bg2-upscale-renderer-install-backup-v1"
MANAGED_FILES = (
    "InfinityEngine-Enhancer.dll",
    "InfinityEngine-Enhancer.ini",
)
GAME_EXECUTABLES = ("BaldurReal.exe", "Baldur.exe")
PROCESS_NAMES = {"baldur.exe", "baldurreal.exe", "infinityloader.exe"}
PAYLOAD_DIRECTORY = "candidate"
BACKUP_DIRECTORY = "before"
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
    """A precondition or transactional integrity check failed."""


@dataclass(frozen=True)
class FileSnapshot:
    bytes: int
    sha256: str


@dataclass(frozen=True)
class CandidateFile:
    name: str
    path: Path
    snapshot: FileSnapshot


@dataclass(frozen=True)
class InstallResult:
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


def running_game_processes() -> list[str]:
    """Return relevant Windows processes, failing closed when tasklist fails."""

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
        if row and row[0].strip().lower() in PROCESS_NAMES:
            found.append(row[0].strip())
    return sorted(set(found), key=str.lower)


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
    executables = [game / name for name in GAME_EXECUTABLES]
    if not any(path.is_file() and not path.is_symlink() for path in executables):
        raise TransactionError(
            "racine de jeu sans BaldurReal.exe ni Baldur.exe : " + str(game)
        )
    for name in MANAGED_FILES:
        optional_snapshot(game / name)
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


def validate_dll(path: Path) -> FileSnapshot:
    snapshot = snapshot_file(path)
    payload = path.read_bytes()
    if len(payload) < 0x40 or payload[:2] != b"MZ":
        raise TransactionError(f"DLL sans en-tête DOS valide : {path}")
    pe_offset = struct.unpack_from("<I", payload, 0x3C)[0]
    if pe_offset < 0x40 or pe_offset + 24 > len(payload):
        raise TransactionError(f"offset PE invalide : {path}")
    if payload[pe_offset : pe_offset + 4] != b"PE\0\0":
        raise TransactionError(f"signature PE invalide : {path}")
    machine, section_count = struct.unpack_from("<HH", payload, pe_offset + 4)
    optional_size, characteristics = struct.unpack_from(
        "<HH", payload, pe_offset + 20
    )
    optional_offset = pe_offset + 24
    if machine != 0x8664 or section_count < 1:
        raise TransactionError(f"DLL renderer non x64 : {path}")
    if not characteristics & 0x2000:
        raise TransactionError(f"image PE non marquée DLL : {path}")
    if optional_size < 2 or optional_offset + optional_size > len(payload):
        raise TransactionError(f"en-tête optionnel PE tronqué : {path}")
    if struct.unpack_from("<H", payload, optional_offset)[0] != 0x20B:
        raise TransactionError(f"DLL renderer non PE32+ : {path}")
    return snapshot


def validate_ini(path: Path) -> FileSnapshot:
    snapshot = snapshot_file(path)
    payload = path.read_bytes()
    if not payload or b"\0" in payload:
        raise TransactionError(f"INI renderer vide ou binaire : {path}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise TransactionError(f"INI renderer non UTF-8 : {path}") from exc
    if not re.search(r"(?m)^\s*\[[^\]\r\n]+\]\s*$", text):
        raise TransactionError(f"INI renderer sans section : {path}")
    return snapshot


def collect_candidate_files(candidate_root: Path) -> tuple[list[CandidateFile], Path]:
    if candidate_root.is_symlink():
        raise TransactionError(f"dossier candidat lié interdit : {candidate_root}")
    source = candidate_root.resolve(strict=True)
    if not source.is_dir() or source.is_symlink():
        raise TransactionError(f"dossier candidat invalide : {source}")
    entries = list(source.iterdir())
    by_lower: dict[str, Path] = {}
    for path in entries:
        key = path.name.lower()
        if key in by_lower:
            raise TransactionError(f"collision de casse dans le candidat : {path.name}")
        by_lower[key] = path
    expected = {name.lower() for name in MANAGED_FILES}
    if set(by_lower) != expected:
        missing = sorted(expected - set(by_lower))
        extra = sorted(set(by_lower) - expected)
        raise TransactionError(
            f"inventaire candidat divergent ; manquants={missing}, supplémentaires={extra}"
        )
    files: list[CandidateFile] = []
    for name in MANAGED_FILES:
        path = by_lower[name.lower()]
        if path.name != name or path.is_symlink() or not path.is_file():
            raise TransactionError(f"source candidate non canonique : {path}")
        snapshot = validate_dll(path) if name.endswith(".dll") else validate_ini(path)
        files.append(CandidateFile(name, path, snapshot))
    return files, source


def state_to_json(snapshot: FileSnapshot | None) -> dict[str, object]:
    return {
        "present": snapshot is not None,
        "bytes": snapshot.bytes if snapshot else None,
        "sha256": snapshot.sha256 if snapshot else None,
    }


def state_from_json(raw: object, label: str) -> FileSnapshot | None:
    if not isinstance(raw, dict) or not isinstance(raw.get("present"), bool):
        raise TransactionError(f"état invalide dans le reçu : {label}")
    if not raw["present"]:
        if raw.get("bytes") is not None or raw.get("sha256") is not None:
            raise TransactionError(f"état absent incohérent dans le reçu : {label}")
        return None
    byte_count = raw.get("bytes")
    digest = raw.get("sha256")
    if not isinstance(byte_count, int) or byte_count < 0:
        raise TransactionError(f"taille invalide dans le reçu : {label}")
    if not isinstance(digest, str) or not re.fullmatch(r"[A-F0-9]{64}", digest.upper()):
        raise TransactionError(f"SHA-256 invalide dans le reçu : {label}")
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


def load_receipt(receipt_path: Path) -> dict[str, object]:
    if receipt_path.is_symlink():
        raise TransactionError(f"reçu lié interdit : {receipt_path}")
    path = receipt_path.resolve(strict=True)
    if path.is_dir():
        path = path / RECEIPT_NAME
    if path.is_symlink() or not path.is_file():
        raise TransactionError(f"reçu absent ou non sûr : {path}")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TransactionError(f"reçu JSON illisible : {path}") from exc
    if not isinstance(receipt, dict) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise TransactionError(f"schéma de reçu incompatible : {path}")
    if receipt.get("status") not in KNOWN_STATUSES:
        raise TransactionError(f"statut de reçu invalide : {receipt.get('status')}")
    receipt["_receipt_path"] = str(path)
    return receipt


def receipt_files(receipt: dict[str, object]) -> list[dict[str, object]]:
    if receipt.get("managed_files") != list(MANAGED_FILES):
        raise TransactionError("liste des fichiers gérés incohérente dans le reçu")
    raw_files = receipt.get("files")
    if not isinstance(raw_files, list) or len(raw_files) != len(MANAGED_FILES):
        raise TransactionError("inventaire invalide dans le reçu")
    files: list[dict[str, object]] = []
    names: set[str] = set()
    for raw in raw_files:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise TransactionError("entrée de fichier invalide dans le reçu")
        name = raw["name"]
        if name not in MANAGED_FILES or name in names:
            raise TransactionError(f"nom dupliqué ou non géré dans le reçu : {name}")
        before = state_from_json(raw.get("before"), f"{name}.before")
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        if installed is None:
            raise TransactionError(f"état installé absent dans le reçu : {name}")
        if raw.get("payload") != f"{PAYLOAD_DIRECTORY}/{name}":
            raise TransactionError(f"chemin candidat incohérent dans le reçu : {name}")
        expected_backup = f"{BACKUP_DIRECTORY}/{name}" if before else None
        if raw.get("backup") != expected_backup:
            raise TransactionError(f"chemin de sauvegarde incohérent dans le reçu : {name}")
        names.add(name)
        files.append(raw)
    if names != set(MANAGED_FILES):
        raise TransactionError("inventaire incomplet dans le reçu")
    before_hash = aggregate_hash(
        (
            str(raw["name"]),
            state_from_json(raw.get("before"), f"{raw['name']}.before"),
        )
        for raw in files
    )
    installed_hash = aggregate_hash(
        (
            str(raw["name"]),
            state_from_json(raw.get("installed"), f"{raw['name']}.installed"),
        )
        for raw in files
    )
    if receipt.get("before_set_sha256") != before_hash:
        raise TransactionError("empreinte de l'état initial incohérente dans le reçu")
    if receipt.get("installed_set_sha256") != installed_hash:
        raise TransactionError("empreinte du candidat incohérente dans le reçu")
    return files


def validate_receipt(
    receipt: dict[str, object], game_root: Path
) -> tuple[Path, Path, list[dict[str, object]]]:
    game = validate_game_root(game_root)
    recorded_game = receipt.get("game_root")
    transaction_root = receipt.get("transaction_root")
    if not isinstance(recorded_game, str) or not isinstance(transaction_root, str):
        raise TransactionError("chemins absents du reçu")
    if os.path.normcase(str(game)) != os.path.normcase(str(Path(recorded_game).resolve())):
        raise TransactionError("le reçu appartient à une autre racine de jeu")
    receipt_path = Path(str(receipt["_receipt_path"]))
    root = receipt_path.parent.resolve(strict=True)
    if root.is_symlink() or os.path.normcase(str(root)) != os.path.normcase(
        str(Path(transaction_root).resolve())
    ):
        raise TransactionError("racine de transaction incohérente dans le reçu")
    transaction_id = receipt.get("transaction_id")
    if not isinstance(transaction_id, str) or transaction_id != root.name:
        raise TransactionError("identifiant de transaction incohérent dans le reçu")
    if root == game or game in root.parents:
        raise TransactionError("la transaction ne peut pas résider dans le jeu")
    files = receipt_files(receipt)
    payload_root = root / PAYLOAD_DIRECTORY
    backup_root = root / BACKUP_DIRECTORY
    if not payload_root.is_dir() or payload_root.is_symlink():
        raise TransactionError("payload candidat absent ou non sûr")
    if not backup_root.is_dir() or backup_root.is_symlink():
        raise TransactionError("dossier de sauvegarde absent ou non sûr")
    expected_payload = set(MANAGED_FILES)
    actual_payload = {path.name for path in payload_root.iterdir()}
    expected_backup = {
        str(raw["name"])
        for raw in files
        if state_from_json(raw.get("before"), f"{raw['name']}.before") is not None
    }
    actual_backup = {path.name for path in backup_root.iterdir()}
    if actual_payload != expected_payload or actual_backup != expected_backup:
        raise TransactionError("inventaire de transaction divergent")
    for raw in files:
        name = str(raw["name"])
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        if optional_snapshot(payload_root / name) != installed:
            raise TransactionError(f"payload candidat corrompu : {name}")
        validated = (
            validate_dll(payload_root / name)
            if name.endswith(".dll")
            else validate_ini(payload_root / name)
        )
        if validated != installed:
            raise TransactionError(f"payload candidat divergent : {name}")
        before = state_from_json(raw.get("before"), f"{name}.before")
        if before is not None and optional_snapshot(backup_root / name) != before:
            raise TransactionError(f"sauvegarde corrompue : {name}")
    return game, root, files


def update_status(
    receipt: dict[str, object], status: str, *, error: str | None = None
) -> None:
    if status not in KNOWN_STATUSES:
        raise ValueError(status)
    receipt["status"] = status
    receipt["updated_at_utc"] = utc_now()
    if error is None:
        receipt.pop("last_error", None)
    else:
        receipt["last_error"] = error
    path = Path(str(receipt["_receipt_path"]))
    clean = {key: value for key, value in receipt.items() if not key.startswith("_")}
    write_json_atomic(path, clean)


def require_recovery_state(game: Path, files: list[dict[str, object]]) -> None:
    for raw in files:
        name = str(raw["name"])
        actual = optional_snapshot(game / name)
        before = state_from_json(raw.get("before"), f"{name}.before")
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        if actual not in {before, installed}:
            raise TransactionError(
                f"état ni initial ni candidat, récupération refusée : {game / name}"
            )


def verify_target_state(
    game: Path, files: list[dict[str, object]], expected_key: str
) -> None:
    for raw in files:
        name = str(raw["name"])
        expected = state_from_json(raw.get(expected_key), f"{name}.{expected_key}")
        if optional_snapshot(game / name) != expected:
            raise TransactionError(f"état {expected_key} divergent pour {game / name}")


def restore_files(
    game: Path, root: Path, files: list[dict[str, object]]
) -> None:
    require_recovery_state(game, files)
    for raw in reversed(files):
        name = str(raw["name"])
        target = game / name
        before = state_from_json(raw.get("before"), f"{name}.before")
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        actual = optional_snapshot(target)
        if actual == before:
            continue
        if actual != installed:
            raise TransactionError(f"cible divergente pendant la restauration : {target}")
        if before is None:
            safe_unlink(target, installed)
        else:
            atomic_copy(root / BACKUP_DIRECTORY / name, target, before)
    verify_target_state(game, files, "before")


def install_files(
    receipt: dict[str, object], game: Path, root: Path, files: list[dict[str, object]]
) -> None:
    require_recovery_state(game, files)
    update_status(receipt, "installing")
    for raw in files:
        name = str(raw["name"])
        target = game / name
        before = state_from_json(raw.get("before"), f"{name}.before")
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        actual = optional_snapshot(target)
        if actual == installed:
            continue
        if actual != before:
            raise TransactionError(f"cible divergente pendant l'installation : {target}")
        atomic_copy(root / PAYLOAD_DIRECTORY / name, target, installed)
    verify_target_state(game, files, "installed")
    update_status(receipt, "installed")


def prepare_transaction(
    candidate_files: list[CandidateFile],
    candidate_root: Path,
    game: Path,
    backup_root: Path,
) -> tuple[dict[str, object], Path]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    transaction_id = f"{stamp}-{uuid.uuid4().hex[:8]}"
    root = backup_root / transaction_id
    root.mkdir()
    payload_root = root / PAYLOAD_DIRECTORY
    before_root = root / BACKUP_DIRECTORY
    payload_root.mkdir()
    before_root.mkdir()
    records: list[dict[str, object]] = []
    try:
        for candidate in candidate_files:
            before = optional_snapshot(game / candidate.name)
            atomic_copy(candidate.path, payload_root / candidate.name, candidate.snapshot)
            if before is not None:
                atomic_copy(game / candidate.name, before_root / candidate.name, before)
            records.append(
                {
                    "name": candidate.name,
                    "before": state_to_json(before),
                    "installed": state_to_json(candidate.snapshot),
                    "backup": f"{BACKUP_DIRECTORY}/{candidate.name}" if before else None,
                    "payload": f"{PAYLOAD_DIRECTORY}/{candidate.name}",
                }
            )
        receipt: dict[str, object] = {
            "schema": RECEIPT_SCHEMA,
            "status": "prepared",
            "transaction_id": transaction_id,
            "created_at_utc": utc_now(),
            "updated_at_utc": utc_now(),
            "game_root": str(game),
            "candidate_root": str(candidate_root),
            "transaction_root": str(root),
            "managed_files": list(MANAGED_FILES),
            "before_set_sha256": aggregate_hash(
                (
                    str(raw["name"]),
                    state_from_json(raw["before"], f"{raw['name']}.before"),
                )
                for raw in records
            ),
            "installed_set_sha256": aggregate_hash(
                (
                    str(raw["name"]),
                    state_from_json(raw["installed"], f"{raw['name']}.installed"),
                )
                for raw in records
            ),
            "files": records,
        }
        receipt_path = root / RECEIPT_NAME
        write_json_atomic(receipt_path, receipt)
        receipt["_receipt_path"] = str(receipt_path)
        return receipt, root
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def install_candidate(
    candidate_root: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
) -> InstallResult:
    ensure_game_stopped(process_checker)
    game = validate_game_root(game_root)
    candidates, source = collect_candidate_files(candidate_root)
    backup = validate_backup_root(backup_root, game, create=not verify_only)
    if verify_only:
        return InstallResult("verified", None, MANAGED_FILES)
    receipt, root = prepare_transaction(candidates, source, game, backup)
    files = receipt_files(receipt)
    try:
        install_files(receipt, game, root, files)
    except Exception as exc:
        try:
            restore_files(game, root, files)
            update_status(receipt, "rolled-back", error=str(exc))
        except Exception as rollback_exc:
            update_status(
                receipt,
                "recovery-required",
                error=f"installation: {exc}; rollback: {rollback_exc}",
            )
            raise TransactionError(
                f"installation interrompue ; récupération requise via {root}"
            ) from exc
        raise TransactionError("installation échouée ; état initial restauré") from exc
    return InstallResult("installed", root / RECEIPT_NAME, MANAGED_FILES)


def restore_from_receipt(
    receipt_path: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
) -> dict[str, object]:
    receipt = load_receipt(receipt_path)
    game, root, files = validate_receipt(receipt, game_root)
    if verify_only:
        verify_transaction(receipt_path, game_root)
        return receipt
    ensure_game_stopped(process_checker)
    status = str(receipt["status"])
    if status in {"restored", "rolled-back"}:
        verify_target_state(game, files, "before")
        return receipt
    if status not in {
        "prepared",
        "installing",
        "installed",
        "restoring",
        "recovery-required",
    }:
        raise TransactionError(f"statut non restaurable : {status}")
    require_recovery_state(game, files)
    update_status(receipt, "restoring")
    try:
        restore_files(game, root, files)
    except Exception as exc:
        update_status(receipt, "recovery-required", error=str(exc))
        raise TransactionError(f"restauration interrompue ; reprendre via {root}") from exc
    update_status(receipt, "restored")
    return receipt


def verify_transaction(
    receipt_path: Path, game_root: Path = DEFAULT_GAME_ROOT
) -> dict[str, object]:
    receipt = load_receipt(receipt_path)
    game, _root, files = validate_receipt(receipt, game_root)
    status = str(receipt["status"])
    if status == "installed":
        verify_target_state(game, files, "installed")
    elif status in {"restored", "rolled-back"}:
        verify_target_state(game, files, "before")
    else:
        require_recovery_state(game, files)
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Installe ou restaure transactionnellement un candidat renderer."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    install = subparsers.add_parser("install", help="installer DLL et INI candidates")
    install.add_argument("candidate_root", type=Path)
    install.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    install.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    install.add_argument("--verify-only", action="store_true")
    restore = subparsers.add_parser("restore", help="restaurer depuis un reçu")
    restore.add_argument("backup_path", type=Path)
    restore.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    restore.add_argument("--verify-only", action="store_true")
    verify = subparsers.add_parser("verify", help="vérifier un reçu et son état")
    verify.add_argument("backup_path", type=Path)
    verify.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "install":
        result = install_candidate(
            args.candidate_root,
            game_root=args.game_root,
            backup_root=args.backup_root,
            verify_only=args.verify_only,
        )
        print(f"fichiers gérés : {len(result.files)}")
        if result.receipt_path is None:
            print("VerifyOnly : prévalidation réussie, aucune écriture.")
        else:
            print(f"installation vérifiée ; reçu : {result.receipt_path}")
        return
    if args.command == "restore":
        receipt = restore_from_receipt(
            args.backup_path,
            game_root=args.game_root,
            verify_only=args.verify_only,
        )
        if args.verify_only:
            print(f"reçu et état {receipt['status']} vérifiés ; aucune écriture")
        else:
            print(f"restauration vérifiée ; statut : {receipt['status']}")
        return
    receipt = verify_transaction(args.backup_path, args.game_root)
    print(f"reçu, payload, sauvegardes et état {receipt['status']} vérifiés")


if __name__ == "__main__":
    try:
        main()
    except (OSError, TransactionError) as exc:
        raise SystemExit(f"ERREUR : {exc}") from exc
