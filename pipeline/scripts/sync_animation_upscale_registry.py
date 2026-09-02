"""Synchronise le registre de suivi des animations avec les index extraits.

Les colonnes techniques et la liste de zones sont régénérées depuis les index.
Les colonnes de décision humaine (statut, sélection, QA, correction et notes)
sont conservées par resref. Chaque BAM n'occupe donc qu'une seule ligne, quel
que soit son nombre d'occurrences.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import os
from collections import defaultdict
from pathlib import Path
import uuid


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESOURCES = PROJECT_ROOT / "animations" / "index" / "ressources.csv"
DEFAULT_OCCURRENCES = PROJECT_ROOT / "animations" / "index" / "occurrences.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "animations" / "index" / "animation_upscale_registry.csv"
TRANSACTION_ROOT = PROJECT_ROOT / ".tmp" / "workflow-transactions"
ACTIVE_JOURNALS = (
    TRANSACTION_ROOT / "animation-authority-active.json",
    TRANSACTION_ROOT / "animation-release-active.json",
)
FIELDS = (
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
MANUAL_FIELDS = (
    "status",
    "selected_run",
    "qa_decision",
    "qa_date",
    "correction_id",
    "notes",
)
DEFAULT_STATUS = "non-traité"


def _load_authority_lock_module():
    module_path = Path(__file__).with_name("animation_authority_lock.py")
    spec = importlib.util.spec_from_file_location("bg2_animation_registry_lock", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"module de verrou animation illisible: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANIMATION_AUTHORITY_LOCK = _load_authority_lock_module()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def area_key(area: str) -> tuple[str, int, str]:
    prefix = "".join(character for character in area if not character.isdigit())
    digits = "".join(character for character in area if character.isdigit())
    return prefix, int(digits) if digits else -1, area


def existing_manual_fields(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    manual: dict[str, dict[str, str]] = {}
    for row in read_rows(path):
        resref = row.get("resref", "").strip()
        if not resref:
            raise RuntimeError(f"registre: resref vide dans {path}")
        if resref in manual:
            raise RuntimeError(f"registre: doublon interdit pour {resref}")
        manual[resref] = {field: row.get(field, "").strip() for field in MANUAL_FIELDS}
    return manual


def build_rows(resources: Path, occurrences: Path, current: Path) -> list[dict[str, str]]:
    resource_rows = read_rows(resources)
    occurrences_by_resref: dict[str, list[dict[str, str]]] = defaultdict(list)
    for occurrence in read_rows(occurrences):
        if (occurrence.get("resource_kind") or "BAM").strip().upper() != "BAM":
            continue
        resref = (
            occurrence.get("resource_resref")
            or occurrence.get("bam_resref")
            or ""
        ).strip()
        if resref:
            occurrences_by_resref[resref].append(occurrence)

    manual = existing_manual_fields(current)
    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    for resource in resource_rows:
        resref = resource["bam_resref"].strip()
        if not resref or resref in seen:
            raise RuntimeError(f"index ressources: resref invalide ou duplique: {resref!r}")
        seen.add(resref)
        occurrences_for_resref = occurrences_by_resref.get(resref, [])
        areas = sorted({row["area_id"].strip() for row in occurrences_for_resref if row["area_id"].strip()}, key=area_key)
        if not areas:
            # The resource index remains the fallback for an extracted source no
            # longer present in an occurrence file.
            areas = sorted({area for area in resource.get("area_ids", "").split(";") if area}, key=area_key)
        manual_row = manual.get(resref, {})
        rows.append(
            {
                "resref": resref,
                "status": manual_row.get("status") or DEFAULT_STATUS,
                "areas": ";".join(areas),
                "occurrences": str(len(occurrences_for_resref) or resource.get("occurrences", "0")),
                "frames": resource["frames"].strip(),
                "max_frame_size_x1": f"{resource['max_frame_width'].strip()}x{resource['max_frame_height'].strip()}",
                "format": resource["format"].strip(),
                "selected_run": manual_row.get("selected_run", ""),
                "qa_decision": manual_row.get("qa_decision", ""),
                "qa_date": manual_row.get("qa_date", ""),
                "correction_id": manual_row.get("correction_id", ""),
                "notes": manual_row.get("notes", ""),
            }
        )

    stale = sorted(set(manual) - seen)
    if stale:
        raise RuntimeError("registre: resrefs absents de ressources.csv: " + ", ".join(stale))
    return sorted(rows, key=lambda row: row["resref"].upper())


def render(rows: list[dict[str, str]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_junction = getattr(path, "is_junction", lambda: False)
    if path.is_symlink() or is_junction():
        raise RuntimeError(f"cible registre lien/reparse interdite: {path}")
    if path.exists() and not path.is_file():
        raise RuntimeError(f"cible registre non fichier: {path}")
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    try:
        with temporary.open("w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument("--occurrences", type=Path, default=DEFAULT_OCCURRENCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="echoue si le registre devrait changer")
    args = parser.parse_args()

    resources = args.resources.resolve()
    occurrences = args.occurrences.resolve()
    output = args.output.resolve()
    for path in (resources, occurrences):
        if not path.is_file():
            raise SystemExit(f"index requis absent: {path}")

    try:
        with ANIMATION_AUTHORITY_LOCK.animation_authority_lock(PROJECT_ROOT):
            active = [path for path in ACTIVE_JOURNALS if path.exists()]
            if active:
                raise RuntimeError(
                    "transaction animation interrompue active: "
                    + ", ".join(str(path) for path in active)
                )
            content = render(build_rows(resources, occurrences, output))
            previous = output.read_text(encoding="utf-8") if output.is_file() else ""
            if args.check:
                if previous != content:
                    raise SystemExit(f"registre des animations non synchronise: {output}")
                print(f"OK: {output} ({content.count(chr(10)) - 1} elements)")
                return
            write_atomic(output, content)
            print(f"registre synchronise: {output} ({content.count(chr(10)) - 1} elements)")
    except ANIMATION_AUTHORITY_LOCK.AnimationAuthorityLockError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
