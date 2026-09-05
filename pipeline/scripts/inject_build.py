"""Install and restore one map build with a fail-closed hash receipt.

The installer owns only the area's TIS and the PVRZ namespace referenced by
that TIS. It validates the complete source inventory before writing, saves the
previous target state, publishes ``install-backup.json``, replaces every file
atomically and verifies the resulting inventory. Restore is independent from
the build source and refuses any target that no longer matches the recorded
installed state.

The historical two-argument invocation remains supported::

    python pipeline/scripts/inject_build.py AR2015 <build-dir>

Explicit commands are preferred::

    python pipeline/scripts/inject_build.py install AR2015 <build-dir>
    python pipeline/scripts/inject_build.py restore <backup-dir>
    python pipeline/scripts/inject_build.py verify <backup-dir>
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
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from workspace_paths import get_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME_ROOT = get_path("bg2ee_game_root")
DEFAULT_BACKUP_ROOT = PROJECT_ROOT / "backups" / "maps"
RECEIPT_NAME = "install-backup.json"
RECEIPT_SCHEMA = "bg2-upscale-map-install-backup-v1"
RESREF_PATTERN = re.compile(r"^[A-Z0-9_]{1,8}$")
PROCESS_NAMES = {"baldur.exe", "baldurreal.exe", "infinityloader.exe"}


class TransactionError(RuntimeError):
    """A precondition or transactional integrity check failed."""


@dataclass(frozen=True)
class FileSnapshot:
    bytes: int
    sha256: str


@dataclass(frozen=True)
class SourceFile:
    name: str
    path: Path
    snapshot: FileSnapshot


@dataclass(frozen=True)
class InstallResult:
    status: str
    receipt_path: Path | None
    installed_files: tuple[str, ...]
    retired_files: tuple[str, ...]


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
    return FileSnapshot(bytes=path.stat().st_size, sha256=sha256_file(path))


def optional_snapshot(path: Path) -> FileSnapshot | None:
    if path.is_symlink():
        raise TransactionError(f"lien symbolique interdit : {path}")
    if not path.exists():
        return None
    return snapshot_file(path)


def running_game_processes() -> list[str]:
    """Return relevant Windows process image names, failing closed on errors."""

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


def validate_resref(raw: str) -> str:
    resref = raw.strip().upper()
    if not RESREF_PATTERN.fullmatch(resref) or not any(char.isalnum() for char in resref):
        raise TransactionError(f"resref invalide : {raw!r}")
    if len(resref) < 3:
        raise TransactionError(f"resref de tileset trop court : {resref}")
    return resref


def safe_file_name(raw: str) -> str:
    if Path(raw).name != raw or raw in {"", ".", ".."}:
        raise TransactionError(f"nom de fichier non sécurisé : {raw!r}")
    return raw


def validate_game_root(game_root: Path) -> tuple[Path, Path]:
    game = game_root.resolve(strict=True)
    if not game.is_dir() or game.is_symlink():
        raise TransactionError(f"racine de jeu invalide : {game}")
    override = game / "override"
    if not override.is_dir() or override.is_symlink():
        raise TransactionError(f"dossier override absent ou non sûr : {override}")
    if override.resolve(strict=True).parent != game:
        raise TransactionError(f"dossier override hors racine de jeu : {override}")
    return game, override.resolve(strict=True)


def validate_tis(path: Path) -> tuple[FileSnapshot, set[int]]:
    payload = path.read_bytes()
    if payload[:8] != b"TIS V1  " or len(payload) < 24:
        raise TransactionError(f"TIS V1 invalide : {path}")
    tile_count, entry_size, header_size, tile_dimension = struct.unpack_from("<IIII", payload, 8)
    if entry_size != 12 or header_size != 24:
        raise TransactionError(f"layout TIS PVRZ inattendu : {path}")
    if tile_dimension // 64 not in {1, 2, 4, 8} or tile_dimension % 64:
        raise TransactionError(f"dimension de tuile TIS invalide : {tile_dimension}")
    expected_size = header_size + tile_count * entry_size
    if len(payload) != expected_size:
        raise TransactionError(
            f"taille TIS incohérente : {len(payload)} au lieu de {expected_size}"
        )
    pages = {
        struct.unpack_from("<I", payload, header_size + index * entry_size)[0]
        for index in range(tile_count)
    }
    pages.discard(0xFFFFFFFF)
    if not pages:
        raise TransactionError(f"aucune page PVRZ référencée par {path.name}")
    return (
        FileSnapshot(len(payload), hashlib.sha256(payload).hexdigest().upper()),
        pages,
    )


def validate_pvrz(path: Path) -> FileSnapshot:
    digest = hashlib.sha256()
    decoded_bytes = 0
    compressed_bytes = 0
    inflater = zlib.decompressobj()
    with path.open("rb") as handle:
        prefix = handle.read(4)
        if len(prefix) != 4:
            raise TransactionError(f"PVRZ tronquée : {path}")
        digest.update(prefix)
        compressed_bytes += len(prefix)
        expected_decoded = struct.unpack("<I", prefix)[0]
        try:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                compressed_bytes += len(chunk)
                decoded_bytes += len(inflater.decompress(chunk))
            decoded_bytes += len(inflater.flush())
        except zlib.error as exc:
            raise TransactionError(f"flux zlib invalide : {path}") from exc
    if not inflater.eof or inflater.unused_data:
        raise TransactionError(f"flux zlib incomplet ou données finales inattendues : {path}")
    if decoded_bytes != expected_decoded:
        raise TransactionError(
            f"taille PVR décodée incohérente pour {path.name} : "
            f"{decoded_bytes} au lieu de {expected_decoded}"
        )
    return FileSnapshot(compressed_bytes, digest.hexdigest().upper())


def expected_page_name(resref: str, page: int) -> str:
    prefix = resref[0] + resref[2:]
    name = f"{prefix}{page:02d}.PVRZ".upper()
    if len(Path(name).stem) > 8:
        raise TransactionError(f"resref PVRZ supérieur à huit caractères : {name}")
    return name


def collect_source_files(resref: str, build_dir: Path) -> tuple[list[SourceFile], str]:
    source = build_dir.resolve(strict=True)
    if not source.is_dir() or source.is_symlink():
        raise TransactionError(f"dossier build invalide : {source}")
    content = [
        path
        for path in source.iterdir()
        if path.is_file() and path.suffix.upper() in {".TIS", ".PVRZ"}
    ]
    tis_files = [path for path in content if path.suffix.upper() == ".TIS"]
    expected_tis_name = f"{resref}.TIS"
    if len(tis_files) != 1 or tis_files[0].name.upper() != expected_tis_name:
        found = ", ".join(sorted(path.name for path in tis_files)) or "aucun"
        raise TransactionError(
            f"le build doit contenir uniquement {expected_tis_name} comme TIS ; trouvé : {found}"
        )
    tis_path = tis_files[0]
    if tis_path.is_symlink():
        raise TransactionError(f"source liée interdite : {tis_path}")
    tis_snapshot, pages = validate_tis(tis_path)
    page_names = {expected_page_name(resref, page) for page in pages}
    pvrz_by_name: dict[str, Path] = {}
    for path in content:
        if path.suffix.upper() != ".PVRZ":
            continue
        if path.is_symlink():
            raise TransactionError(f"source liée interdite : {path}")
        upper_name = path.name.upper()
        if upper_name in pvrz_by_name:
            raise TransactionError(f"collision de casse dans le build : {path.name}")
        pvrz_by_name[upper_name] = path
    actual_names = set(pvrz_by_name)
    if actual_names != page_names:
        missing = sorted(page_names - actual_names)
        extra = sorted(actual_names - page_names)
        raise TransactionError(
            f"inventaire PVRZ divergent ; manquants={missing}, supplémentaires={extra}"
        )
    files = [SourceFile(expected_tis_name, tis_path, tis_snapshot)]
    for name in sorted(page_names):
        path = pvrz_by_name[name]
        files.append(SourceFile(name, path, validate_pvrz(path)))
    return files, resref[0] + resref[2:]


def namespace_files(override: Path, prefix: str) -> dict[str, Path]:
    pattern = re.compile(rf"^{re.escape(prefix)}[0-9]+\.PVRZ$", re.IGNORECASE)
    found: dict[str, Path] = {}
    for path in override.iterdir():
        if pattern.fullmatch(path.name):
            if path.is_symlink() or not path.is_file():
                raise TransactionError(f"entrée override non ordinaire : {path}")
            upper_name = path.name.upper()
            if upper_name in found:
                raise TransactionError(f"collision de casse dans override : {path.name}")
            found[upper_name] = path
    return found


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


def same_state(left: FileSnapshot | None, right: FileSnapshot | None) -> bool:
    return left == right


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
        actual = snapshot_file(temporary)
        if actual != expected:
            raise TransactionError(f"copie temporaire divergente : {source}")
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_receipt(receipt_path: Path) -> dict[str, object]:
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
    receipt["_receipt_path"] = str(path)
    return receipt


def receipt_files(receipt: dict[str, object]) -> list[dict[str, object]]:
    raw_files = receipt.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise TransactionError("inventaire vide ou invalide dans le reçu")
    files: list[dict[str, object]] = []
    names: set[str] = set()
    for raw in raw_files:
        if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
            raise TransactionError("entrée de fichier invalide dans le reçu")
        name = safe_file_name(raw["name"])
        if name != name.upper() or name in names:
            raise TransactionError(f"nom dupliqué ou non canonique dans le reçu : {name}")
        state_from_json(raw.get("before"), f"{name}.before")
        state_from_json(raw.get("installed"), f"{name}.installed")
        names.add(name)
        files.append(raw)
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
        raise TransactionError("empreinte de l’état initial incohérente dans le reçu")
    if receipt.get("installed_set_sha256") != installed_hash:
        raise TransactionError("empreinte de l’état installé incohérente dans le reçu")

    installed_inventory = receipt.get("installed_inventory")
    retired_inventory = receipt.get("retired_inventory")
    if not isinstance(installed_inventory, list) or not all(
        isinstance(name, str) for name in installed_inventory
    ):
        raise TransactionError("inventaire installé invalide dans le reçu")
    if not isinstance(retired_inventory, list) or not all(
        isinstance(name, str) for name in retired_inventory
    ):
        raise TransactionError("inventaire retiré invalide dans le reçu")
    expected_installed = {
        str(raw["name"])
        for raw in files
        if state_from_json(
            raw.get("installed"), f"{raw['name']}.installed"
        ) is not None
    }
    expected_retired = set(names) - expected_installed
    if (
        len(installed_inventory) != len(set(installed_inventory))
        or set(installed_inventory) != expected_installed
    ):
        raise TransactionError("inventaire installé incohérent dans le reçu")
    if (
        len(retired_inventory) != len(set(retired_inventory))
        or set(retired_inventory) != expected_retired
    ):
        raise TransactionError("inventaire retiré incohérent dans le reçu")
    return files


def validate_receipt_game(
    receipt: dict[str, object], game_root: Path
) -> tuple[Path, Path, Path]:
    game, override = validate_game_root(game_root)
    recorded_game = receipt.get("game_root")
    recorded_override = receipt.get("override_root")
    if not isinstance(recorded_game, str) or not isinstance(recorded_override, str):
        raise TransactionError("chemins absents du reçu")
    if os.path.normcase(str(game)) != os.path.normcase(str(Path(recorded_game).resolve())):
        raise TransactionError("le reçu appartient à une autre racine de jeu")
    if os.path.normcase(str(override)) != os.path.normcase(
        str(Path(recorded_override).resolve())
    ):
        raise TransactionError("le reçu appartient à un autre override")
    receipt_path = Path(str(receipt["_receipt_path"]))
    return game, override, receipt_path


def verify_target_state(
    override: Path,
    files: list[dict[str, object]],
    expected_key: str,
) -> None:
    for raw in files:
        name = str(raw["name"])
        actual = optional_snapshot(override / name)
        expected = state_from_json(raw.get(expected_key), f"{name}.{expected_key}")
        if not same_state(actual, expected):
            raise TransactionError(
                f"état {expected_key} divergent pour {override / name}"
            )


def verify_recovery_state(override: Path, files: list[dict[str, object]]) -> None:
    for raw in files:
        name = str(raw["name"])
        actual = optional_snapshot(override / name)
        before = state_from_json(raw.get("before"), f"{name}.before")
        installed = state_from_json(raw.get("installed"), f"{name}.installed")
        if not same_state(actual, before) and not same_state(actual, installed):
            raise TransactionError(
                f"état ni initial ni installé, récupération refusée : {override / name}"
            )


def verify_receipt_namespace(
    receipt: dict[str, object],
    override: Path,
    files: list[dict[str, object]],
    expected_key: str | None,
) -> None:
    resref_raw = receipt.get("resref")
    prefix = receipt.get("pvrz_prefix")
    if not isinstance(resref_raw, str) or not isinstance(prefix, str):
        raise TransactionError("namespace PVRZ absent du reçu")
    resref = validate_resref(resref_raw)
    if prefix != (resref[0] + resref[2:]).upper():
        raise TransactionError("namespace PVRZ incohérent dans le reçu")
    actual = set(namespace_files(override, prefix))
    managed = {
        str(raw["name"])
        for raw in files
        if str(raw["name"]).endswith(".PVRZ")
    }
    if expected_key is None:
        unexpected = actual - managed
        if unexpected:
            raise TransactionError(
                f"pages PVRZ hors reçu dans le namespace : {sorted(unexpected)}"
            )
        return
    expected = {
        str(raw["name"])
        for raw in files
        if str(raw["name"]).endswith(".PVRZ")
        and state_from_json(
            raw.get(expected_key), f"{raw['name']}.{expected_key}"
        ) is not None
    }
    if actual != expected:
        raise TransactionError(
            f"inventaire PVRZ {expected_key} divergent : {sorted(actual)}"
        )


def require_target_state(
    target: Path,
    allowed: Iterable[FileSnapshot | None],
    operation: str,
) -> None:
    actual = optional_snapshot(target)
    if not any(same_state(actual, expected) for expected in allowed):
        raise TransactionError(
            f"cible modifiée pendant {operation}, opération interrompue : {target}"
        )


def verify_backup_files(receipt_path: Path, files: list[dict[str, object]]) -> None:
    backup_files = receipt_path.parent / "files"
    if (
        not backup_files.is_dir()
        or backup_files.is_symlink()
        or backup_files.resolve(strict=True).parent != receipt_path.parent.resolve(strict=True)
    ):
        raise TransactionError(f"dossier de sauvegarde absent ou non sûr : {backup_files}")
    for raw in files:
        name = str(raw["name"])
        before = state_from_json(raw.get("before"), f"{name}.before")
        saved = backup_files / name
        if before is None:
            if saved.exists():
                raise TransactionError(f"sauvegarde inattendue pour un fichier absent : {saved}")
            continue
        if optional_snapshot(saved) != before:
            raise TransactionError(f"sauvegarde absente ou corrompue : {saved}")


def restore_from_receipt(
    receipt_path: Path,
    game_root: Path,
    *,
    process_checker: ProcessChecker = running_game_processes,
    final_status: str = "restored",
) -> dict[str, object]:
    ensure_game_stopped(process_checker)
    receipt = load_receipt(receipt_path)
    _, override, receipt_file = validate_receipt_game(receipt, game_root)
    files = receipt_files(receipt)
    status = receipt.get("status")
    if status in {"restored", "rolled-back"}:
        verify_target_state(override, files, "before")
        verify_receipt_namespace(receipt, override, files, "before")
        return receipt
    if status == "installed":
        verify_target_state(override, files, "installed")
        verify_receipt_namespace(receipt, override, files, "installed")
    elif status in {"prepared", "restoring", "recovery-required"}:
        verify_recovery_state(override, files)
        verify_receipt_namespace(receipt, override, files, None)
    else:
        raise TransactionError(f"statut de reçu non restaurable : {status!r}")
    verify_backup_files(receipt_file, files)
    receipt.pop("_receipt_path", None)
    receipt["status"] = "restoring"
    receipt["restoration_started_at_utc"] = utc_now()
    write_json_atomic(receipt_file, receipt)
    try:
        for raw in files:
            name = str(raw["name"])
            target = override / name
            before = state_from_json(raw.get("before"), f"{name}.before")
            installed = state_from_json(raw.get("installed"), f"{name}.installed")
            require_target_state(target, (before, installed), "la restauration")
            if before is None:
                if target.exists():
                    if target.is_symlink() or not target.is_file():
                        raise TransactionError(f"cible non ordinaire à supprimer : {target}")
                    target.unlink()
            else:
                atomic_copy(receipt_file.parent / "files" / name, target, before)
        verify_target_state(override, files, "before")
        verify_receipt_namespace(receipt, override, files, "before")
    except Exception as restore_error:
        try:
            failed_receipt = load_receipt(receipt_file)
            failed_receipt.pop("_receipt_path", None)
            failed_receipt["status"] = "recovery-required"
            failed_receipt["restoration_failure_at_utc"] = utc_now()
            failed_receipt["restoration_failure"] = str(restore_error)
            write_json_atomic(receipt_file, failed_receipt)
        except Exception:
            pass
        raise
    receipt["status"] = final_status
    receipt["restored_at_utc"] = utc_now()
    write_json_atomic(receipt_file, receipt)
    receipt["_receipt_path"] = str(receipt_file)
    return receipt


def install_build(
    resref_raw: str,
    build_dir: Path,
    *,
    game_root: Path = DEFAULT_GAME_ROOT,
    backup_root: Path = DEFAULT_BACKUP_ROOT,
    verify_only: bool = False,
    process_checker: ProcessChecker = running_game_processes,
) -> InstallResult:
    ensure_game_stopped(process_checker)
    resref = validate_resref(resref_raw)
    game, override = validate_game_root(game_root)
    source_files, prefix = collect_source_files(resref, build_dir)
    source_by_name = {entry.name: entry for entry in source_files}
    existing_namespace = namespace_files(override, prefix)
    expected_names = set(source_by_name)
    retired_names = sorted(set(existing_namespace) - expected_names)
    managed_names = sorted(expected_names | set(retired_names))

    before_states: dict[str, FileSnapshot | None] = {}
    installed_states: dict[str, FileSnapshot | None] = {}
    for name in managed_names:
        before_states[name] = optional_snapshot(override / name)
        installed_states[name] = (
            source_by_name[name].snapshot if name in source_by_name else None
        )

    if verify_only:
        return InstallResult(
            status="verified-only",
            receipt_path=None,
            installed_files=tuple(sorted(expected_names)),
            retired_files=tuple(retired_names),
        )

    backup = backup_root.resolve()
    if backup.exists() and (not backup.is_dir() or backup.is_symlink()):
        raise TransactionError(f"racine de sauvegarde invalide : {backup}")
    backup.mkdir(parents=True, exist_ok=True)
    transaction_id = (
        f"{resref}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-"
        f"{uuid.uuid4().hex[:8]}"
    )
    final_backup = backup / transaction_id
    staging_backup = backup / f".{transaction_id}.installing"
    if final_backup.exists() or staging_backup.exists():
        raise TransactionError(f"collision de transaction : {transaction_id}")
    staging_files = staging_backup / "files"
    staging_files.mkdir(parents=True)

    file_records: list[dict[str, object]] = []
    try:
        for name in managed_names:
            before = before_states[name]
            if before is not None:
                atomic_copy(override / name, staging_files / name, before)
            file_records.append(
                {
                    "name": name,
                    "before": state_to_json(before),
                    "installed": state_to_json(installed_states[name]),
                }
            )
        receipt: dict[str, object] = {
            "schema": RECEIPT_SCHEMA,
            "status": "prepared",
            "transaction_id": transaction_id,
            "created_at_utc": utc_now(),
            "resref": resref,
            "game_root": str(game),
            "override_root": str(override),
            "source_root": str(build_dir.resolve(strict=True)),
            "tis": f"{resref}.TIS",
            "pvrz_prefix": prefix,
            "installed_inventory": sorted(expected_names),
            "retired_inventory": retired_names,
            "before_set_sha256": aggregate_hash(before_states.items()),
            "installed_set_sha256": aggregate_hash(installed_states.items()),
            "files": file_records,
        }
        write_json_atomic(staging_backup / RECEIPT_NAME, receipt)
        os.replace(staging_backup, final_backup)
    except Exception:
        if staging_backup.exists():
            shutil.rmtree(staging_backup, ignore_errors=True)
        raise

    receipt_path = final_backup / RECEIPT_NAME
    try:
        verify_target_state(override, file_records, "before")
        for name in managed_names:
            target = override / name
            expected = installed_states[name]
            require_target_state(target, (before_states[name],), "l’installation")
            if expected is None:
                if target.exists():
                    target.unlink()
            else:
                atomic_copy(source_by_name[name].path, target, expected)
        verify_target_state(override, file_records, "installed")
        actual_namespace = set(namespace_files(override, prefix))
        expected_pages = {
            name for name in expected_names if name.upper().endswith(".PVRZ")
        }
        if actual_namespace != expected_pages:
            raise TransactionError(
                "inventaire override divergent après installation : "
                f"{sorted(actual_namespace)}"
            )
        receipt = load_receipt(receipt_path)
        receipt.pop("_receipt_path", None)
        receipt["status"] = "installed"
        receipt["installed_at_utc"] = utc_now()
        write_json_atomic(receipt_path, receipt)
    except Exception as install_error:
        try:
            restore_from_receipt(
                receipt_path,
                game,
                process_checker=lambda: [],
                final_status="rolled-back",
            )
        except Exception as rollback_error:
            receipt = load_receipt(receipt_path)
            receipt.pop("_receipt_path", None)
            receipt["status"] = "recovery-required"
            receipt["failure_at_utc"] = utc_now()
            receipt["failure"] = str(install_error)
            receipt["rollback_failure"] = str(rollback_error)
            write_json_atomic(receipt_path, receipt)
            raise TransactionError(
                f"installation échouée ; récupération manuelle requise avec {receipt_path}"
            ) from install_error
        raise TransactionError(
            f"installation échouée ; état initial restauré, reçu {receipt_path}"
        ) from install_error

    return InstallResult(
        status="installed",
        receipt_path=receipt_path,
        installed_files=tuple(sorted(expected_names)),
        retired_files=tuple(retired_names),
    )


def verify_transaction(receipt_path: Path, game_root: Path) -> dict[str, object]:
    receipt = load_receipt(receipt_path)
    _, override, receipt_file = validate_receipt_game(receipt, game_root)
    files = receipt_files(receipt)
    verify_backup_files(receipt_file, files)
    status = receipt.get("status")
    if status == "installed":
        verify_target_state(override, files, "installed")
        verify_receipt_namespace(receipt, override, files, "installed")
    elif status in {"restored", "rolled-back"}:
        verify_target_state(override, files, "before")
        verify_receipt_namespace(receipt, override, files, "before")
    elif status in {"prepared", "restoring", "recovery-required"}:
        verify_recovery_state(override, files)
        verify_receipt_namespace(receipt, override, files, None)
    else:
        raise TransactionError(f"statut de reçu inconnu : {status!r}")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Installe ou restaure transactionnellement un build TIS/PVRZ."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install = subparsers.add_parser("install", help="installer un build de map")
    install.add_argument("resref")
    install.add_argument("build_dir", type=Path)
    install.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    install.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    install.add_argument("--verify-only", action="store_true")

    restore = subparsers.add_parser("restore", help="restaurer depuis un reçu")
    restore.add_argument("backup_path", type=Path)
    restore.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    restore.add_argument("--verify-only", action="store_true")

    verify = subparsers.add_parser("verify", help="vérifier l'état décrit par un reçu")
    verify.add_argument("backup_path", type=Path)
    verify.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    return parser


def normalized_argv(argv: list[str]) -> list[str]:
    if len(argv) == 2 and argv[0].lower() not in {"install", "restore", "verify"}:
        return ["install", *argv]
    return argv


def main(argv: list[str] | None = None) -> None:
    raw_argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(normalized_argv(raw_argv))
    if args.command == "install":
        result = install_build(
            args.resref,
            args.build_dir,
            game_root=args.game_root,
            backup_root=args.backup_root,
            verify_only=args.verify_only,
        )
        print(f"RESREF : {validate_resref(args.resref)}")
        print(f"fichiers à installer : {len(result.installed_files)}")
        print(f"anciennes pages à retirer : {len(result.retired_files)}")
        if result.receipt_path:
            print(f"installation vérifiée ; reçu : {result.receipt_path}")
        else:
            print("VerifyOnly : prévalidation réussie, aucune écriture.")
        return
    if args.command == "restore":
        if args.verify_only:
            receipt = verify_transaction(args.backup_path, args.game_root)
            print(f"reçu et état {receipt['status']} vérifiés ; aucune écriture")
        else:
            receipt = restore_from_receipt(args.backup_path, args.game_root)
            print(f"restauration vérifiée ; statut : {receipt['status']}")
        return
    receipt = verify_transaction(args.backup_path, args.game_root)
    print(f"reçu, sauvegardes et état {receipt['status']} vérifiés")


if __name__ == "__main__":
    try:
        main()
    except (OSError, TransactionError) as exc:
        raise SystemExit(f"ERREUR : {exc}") from exc
