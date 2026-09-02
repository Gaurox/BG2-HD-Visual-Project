"""Crash-safe advisory lock shared by animation QA and release workflows."""

from __future__ import annotations

from contextlib import contextmanager
import argparse
import errno
import os
from pathlib import Path
import sys
from typing import BinaryIO, Iterator


AUTHORITY_LOCK_REL = Path(".tmp/workflow-locks/animation-authority.lock")
AUTHORITY_LOCK_OWNER_ENV = "BG2HD_ANIMATION_AUTHORITY_LOCK_OWNER_PID"
_BUSY_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}


class AnimationAuthorityLockError(RuntimeError):
    """Raised when the shared animation-authority lock cannot be acquired."""


def _acquire(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _release(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _owner(lock_path: Path) -> str:
    try:
        # Byte 0 is the locked range on Windows; inherited children must not
        # read across it when checking the owner record.
        with lock_path.open("rb") as stream:
            stream.seek(1)
            raw = stream.read()
    except OSError:
        return ""
    return raw.decode("ascii", errors="replace").strip() if raw else ""


def _has_live_inherited_owner(lock_path: Path) -> bool:
    value = os.environ.get(AUTHORITY_LOCK_OWNER_ENV, "")
    if not value.isdigit() or int(value) <= 0:
        return False
    if _owner(lock_path).splitlines()[:1] != [f"pid={value}"]:
        return False
    if os.name == "nt":
        import ctypes

        process = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(value))
        if not process:
            return False
        ctypes.windll.kernel32.CloseHandle(process)
        return True
    try:
        os.kill(int(value), 0)
        return True
    except OSError:
        return False


@contextmanager
def animation_authority_lock(workspace_root: Path) -> Iterator[Path]:
    """Hold the common animation-authority lock until the context exits.

    The lock file is intentionally persistent.  Ownership is the operating
    system lock on the open handle, so an abrupt process exit releases it.
    """

    lock_path = workspace_root.resolve() / AUTHORITY_LOCK_REL
    if _has_live_inherited_owner(lock_path):
        yield lock_path
        return
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b", buffering=0)
    except OSError as error:
        raise AnimationAuthorityLockError(
            f"ouverture du verrou animation impossible: {lock_path}: {error}"
        ) from error

    acquired = False
    try:
        try:
            if os.fstat(handle.fileno()).st_size == 0:
                handle.write(b"\0")
            _acquire(handle)
            acquired = True
        except OSError as error:
            owner = _owner(lock_path)
            if error.errno in _BUSY_ERRNOS or getattr(error, "winerror", None) in {33, 36}:
                detail = "transaction animation déjà verrouillée"
            else:
                detail = "acquisition du verrou animation impossible"
            raise AnimationAuthorityLockError(
                f"{detail}: {AUTHORITY_LOCK_REL.as_posix()}"
                + (f" ({owner})" if owner else "")
            ) from error

        try:
            handle.seek(1)
            handle.truncate()
            handle.write(f"pid={os.getpid()}\n".encode("ascii"))
            os.fsync(handle.fileno())
        except OSError as error:
            raise AnimationAuthorityLockError(
                f"mise à jour du verrou animation impossible: {lock_path}: {error}"
            ) from error

        previous_owner = os.environ.get(AUTHORITY_LOCK_OWNER_ENV)
        os.environ[AUTHORITY_LOCK_OWNER_ENV] = str(os.getpid())
        try:
            yield lock_path
        finally:
            if previous_owner is None:
                os.environ.pop(AUTHORITY_LOCK_OWNER_ENV, None)
            else:
                os.environ[AUTHORITY_LOCK_OWNER_ENV] = previous_owner
        if acquired:
            try:
                _release(handle)
            except OSError as error:
                raise AnimationAuthorityLockError(
                    f"libération du verrou animation impossible: {lock_path}: {error}"
                ) from error
            acquired = False
    finally:
        if acquired:
            try:
                _release(handle)
            except OSError:
                pass
        handle.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Maintenir le verrou d'autorité animation")
    parser.add_argument("--hold", type=Path, metavar="WORKSPACE_ROOT", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        with animation_authority_lock(args.hold):
            print("LOCKED", flush=True)
            sys.stdin.buffer.read()
        return 0
    except (OSError, AnimationAuthorityLockError) as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
