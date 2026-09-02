"""Resolve current and legacy animation run locations without moving data."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIMATIONS_ROOT = PROJECT_ROOT / "animations"
LEGACY_RUNS_ROOT = ANIMATIONS_ROOT / "runs"
BATCH_RUNS_ROOT = ANIMATIONS_ROOT / "batches"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
RESREF_RE = re.compile(r"^[A-Z0-9_]{1,8}$")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_run_id(value: str) -> str:
    run_id = value.strip()
    windows_stem = run_id.split(".", 1)[0].upper()
    if (
        run_id != value
        or not RUN_ID_RE.fullmatch(run_id)
        or len(run_id) > 128
        or run_id in {".", ".."}
        or run_id.endswith(".")
        or run_id.casefold().endswith(".partial")
        or windows_stem in WINDOWS_RESERVED_NAMES
    ):
        raise RuntimeError(f"identifiant de run invalide : {value!r}")
    return run_id


def normalise_resrefs(values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(sorted({str(value).strip().upper() for value in values}))
    if not result:
        raise RuntimeError("un run animation doit cibler au moins un resref")
    invalid = [
        value
        for value in result
        if not RESREF_RE.fullmatch(value) or not any(character.isalnum() for character in value)
    ]
    if invalid:
        raise RuntimeError("resref animation invalide : " + ", ".join(invalid))
    return result


def default_run_root(
    resrefs: Iterable[str], *, animations_root: Path = ANIMATIONS_ROOT
) -> Path:
    selected = normalise_resrefs(resrefs)
    root = Path(animations_root).resolve()
    if len(selected) == 1:
        return root / "ressources" / selected[0] / "runs"
    return root / "batches"


def preferred_run_path(
    run_id: str,
    resrefs: Iterable[str],
    *,
    animations_root: Path = ANIMATIONS_ROOT,
) -> Path:
    return default_run_root(resrefs, animations_root=animations_root) / validate_run_id(run_id)


def validate_run_location(
    path: Path,
    resrefs: Iterable[str],
    *,
    animations_root: Path = ANIMATIONS_ROOT,
) -> Path:
    """Accept only one canonical or legacy run root, never an arbitrary subdirectory."""

    selected = normalise_resrefs(resrefs)
    root = Path(animations_root).resolve()
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"run animation hors du workspace animations : {resolved}") from error
    parts = relative.parts
    lowered = tuple(part.casefold() for part in parts)
    valid = (
        len(parts) == 2
        and lowered[0] in {"runs", "batches"}
        and bool(parts[1])
    ) or (
        len(parts) == 4
        and lowered[0] == "ressources"
        and len(selected) == 1
        and parts[1].upper() == selected[0]
        and lowered[2] == "runs"
        and bool(parts[3])
    )
    if not valid:
        raise RuntimeError(f"emplacement de run animation non canonique : {resolved.as_posix()}")
    validate_run_id(parts[-1])
    return resolved


def _candidate_paths(
    run_id: str,
    resrefs: Iterable[str],
    *,
    animations_root: Path,
) -> tuple[Path, ...]:
    selected = normalise_resrefs(resrefs)
    root = Path(animations_root).resolve()
    candidates = [preferred_run_path(run_id, selected, animations_root=root)]
    candidates.append(root / "batches" / run_id)
    candidates.append(root / "runs" / run_id)
    if len(selected) == 1:
        candidates.append(root / "ressources" / selected[0] / "runs" / run_id)

    unique: list[Path] = []
    keys: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()).casefold()
        if key not in keys:
            keys.add(key)
            unique.append(candidate.resolve())
    return tuple(unique)


def _has_run_or_partial(path: Path) -> bool:
    return path.exists() or path.with_name(path.name + ".partial").exists()


def _unique_existing(candidates: Iterable[Path], run_id: str) -> Path | None:
    existing = [path.resolve() for path in candidates if _has_run_or_partial(path)]
    if len(existing) > 1:
        rendered = ", ".join(path.as_posix() for path in existing)
        raise RuntimeError(f"run animation ambigu {run_id!r} : {rendered}")
    return existing[0] if existing else None


def resolve_run_destination(
    run_id: str,
    resrefs: Iterable[str],
    *,
    runs_root: Path | None = None,
    animations_root: Path = ANIMATIONS_ROOT,
) -> Path:
    """Return an existing compatible run, or the preferred path for a new run."""

    run_id = validate_run_id(run_id)
    selected = normalise_resrefs(resrefs)
    if runs_root is not None:
        return validate_run_location(
            Path(runs_root).resolve() / run_id,
            selected,
            animations_root=animations_root,
        )
    candidates = _candidate_paths(run_id, selected, animations_root=animations_root)
    return _unique_existing(candidates, run_id) or candidates[0]


def resolve_existing_run(
    reference: str | Path,
    resrefs: Iterable[str],
    *,
    animations_root: Path = ANIMATIONS_ROOT,
) -> Path:
    """Resolve an explicit path or a run id across current and legacy layouts."""

    value = Path(reference)
    is_simple_name = value.parent == Path(".") and not value.is_absolute()
    if not is_simple_name:
        return validate_run_location(value, resrefs, animations_root=animations_root)

    run_id = validate_run_id(value.name)
    candidates = list(_candidate_paths(run_id, resrefs, animations_root=animations_root))
    resolved = _unique_existing(candidates, run_id)
    if resolved is None:
        searched = ", ".join(path.as_posix() for path in candidates)
        raise RuntimeError(f"run animation introuvable {run_id!r}; chemins testés : {searched}")
    return resolved


def display_path(path: Path, *, project_root: Path = PROJECT_ROOT) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path(project_root).resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()
