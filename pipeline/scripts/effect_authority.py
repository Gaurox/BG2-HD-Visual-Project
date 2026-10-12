"""Small effects-only lock and recoverable authority transaction.

Read-only commands never create a lock. Writers serialize read/modify/write and
finish an interrupted commit before starting another one. No game/release paths.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from functools import wraps
import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Iterator, Mapping
import uuid

LOCK = Path(".tmp/workflow-locks/effects-authority.lock")
JOURNAL = Path(".tmp/workflow-transactions/effects-authority.json")


class AuthorityError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    try:
        with partial.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def authority_target(root: Path, relative: str) -> Path:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise AuthorityError("chemin de transaction non relatif")
    try:
        path.resolve().relative_to((root / "effects/index").resolve())
    except ValueError as error:
        raise AuthorityError("transaction hors effects/index") from error
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in [path, *path.parents]):
        raise AuthorityError("lien dans un chemin d'autorité")
    if path.is_symlink():
        raise AuthorityError("lien d'autorité interdit")
    return path


def require_stable(root: Path) -> None:
    if (root / JOURNAL).exists():
        raise AuthorityError("transaction effects interrompue : effect_workflow.py recover --run")


def recover(root: Path) -> None:
    journal = root / JOURNAL
    if not journal.exists():
        return
    try:
        data = json.loads(journal.read_text(encoding="utf-8"))
        if data.get("schema") != "bg2-effects-authority-transaction-v1" or not data.get("files"):
            raise AuthorityError("journal effects invalide")
        pending = []
        for record in data["files"]:
            target = authority_target(root, record["path"])
            content = base64.b64decode(record["content"], validate=True)
            if digest(content) != record["after"]:
                raise AuthorityError("contenu de transaction corrompu")
            current = digest(target.read_bytes()) if target.is_file() else None
            if current not in (record["before"], record["after"]):
                raise AuthorityError(f"autorité modifiée pendant une transaction : {record['path']}")
            if record.get("immutable") and record["before"] is not None and record["before"] != record["after"]:
                raise AuthorityError("remplacement d'une preuve immuable interdit")
            pending.append((target, content, current != record["after"]))
        # Validate every target before replaying any write.
        for target, content, changed in pending:
            if changed:
                atomic_write(target, content)
        journal.unlink()
    except (OSError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, AuthorityError):
            raise
        raise AuthorityError(f"journal effects illisible : {error}") from error


@contextmanager
def guard(root: Path, write: bool) -> Iterator[None]:
    if not write:
        require_stable(root)
        yield
        require_stable(root)
        return
    lock = root / LOCK
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b", buffering=0) as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b"\0")
        stream.seek(0)
        acquired = False
        try:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as error:
                raise AuthorityError("une écriture effects est déjà en cours ; relancer la commande") from error
            recover(root)
            yield
        finally:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def guarded(function):
    signature = inspect.signature(function)

    @wraps(function)
    def call(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        with guard(bound.arguments["root"], bound.arguments.get("write", False)):
            return function(*args, **kwargs)
    return call


def commit(root: Path, changes: Mapping[str, bytes], *, immutable: tuple[str, ...] = ()) -> None:
    """Called with guard(write=True) held; replay is safe after process failure."""
    require_stable(root)
    files = []
    for relative, content in changes.items():
        target = authority_target(root, relative)
        before = digest(target.read_bytes()) if target.is_file() else None
        after = digest(content)
        if relative in immutable and before is not None and before != after:
            raise AuthorityError(f"preuve immuable déjà présente : {relative}")
        if before != after:
            files.append({"path": relative, "before": before, "after": after,
                          "immutable": relative in immutable,
                          "content": base64.b64encode(content).decode("ascii")})
    if files:
        atomic_write(root / JOURNAL, (json.dumps({"schema": "bg2-effects-authority-transaction-v1", "files": files}) + "\n").encode())
        recover(root)
