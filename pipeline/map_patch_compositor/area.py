"""Workflow non destructif par zone BG2 au-dessus du compositeur raster."""

from __future__ import annotations

import csv
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from . import core


AREA_PATTERN = re.compile(r"^(?:AR|OH)[0-9]{4}$")
SELECTION_SCHEMA = "bg2-upscale-map-patch-compositor-selection-v1"


@dataclass(frozen=True)
class AreaSource:
    area_id: str
    source_path: Path
    source_sha256: str
    parent_run_id: str
    parent_run_manifest: Path
    source_kind: str
    selection_record: Path | None


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise core.CompositeError(f"JSON illisible : {path}") from exc
    if not isinstance(value, dict):
        raise core.CompositeError(f"objet JSON requis : {path}")
    return value


def _area_id(value: str) -> str:
    area = value.upper()
    if not AREA_PATTERN.fullmatch(area):
        raise core.CompositeError(f"area_id invalide : {value!r}")
    return area


def _safe_relative(value: str, label: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise core.CompositeError(f"chemin relatif sûr requis : {label}")
    return path


def _root_reference(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise core.CompositeError(f"chemin hors workspace : {path}") from exc


def _resolve_run_reference(value: str, root: Path) -> Path:
    """Lit les références relatives et les chemins absolus historiques des run.json."""

    recorded = Path(value)
    candidates = [recorded] if recorded.is_absolute() else [root / recorded]
    if recorded.is_absolute():
        parts = recorded.parts
        for index, part in enumerate(parts):
            if part.casefold() == root.name.casefold():
                candidates.append(root.joinpath(*parts[index + 1:]))
                break
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise core.CompositeError(f"image référencée par le run absente : {value}")


def _selected_base_run(area: str, root: Path) -> str:
    catalog = root / "areas.csv"
    if not catalog.is_file():
        raise core.CompositeError(f"areas.csv absent : {catalog}")
    with catalog.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    matching = [row for row in rows if str(row.get("area_id", "")).upper() == area]
    if len(matching) != 1:
        raise core.CompositeError(f"zone absente ou dupliquée dans areas.csv : {area}")
    runs = [item.strip() for item in str(matching[0].get("runs", "")).split(";") if item.strip()]
    if len(runs) != 1:
        raise core.CompositeError(f"run primaire actif ambigu pour {area} dans areas.csv : {runs}")
    return runs[0]


def _run_primary_assembled(area: str, run_id: str, root: Path) -> tuple[Path, Path]:
    manifest_path = root / "maps" / area / "runs" / run_id / "run.json"
    if not manifest_path.is_file():
        raise core.CompositeError(f"run primaire sélectionné sans manifeste : {manifest_path}")
    manifest = _read_json(manifest_path)
    outputs = manifest.get("outputs")
    if not isinstance(outputs, Mapping):
        raise core.CompositeError(f"outputs absents du run primaire : {manifest_path}")
    primary = outputs.get("tuiles-principales")
    if not isinstance(primary, Mapping):
        raise core.CompositeError(f"sortie tuiles-principales absente : {manifest_path}")
    assembled = primary.get("assembled")
    if not isinstance(assembled, Mapping) or not isinstance(assembled.get("path"), str):
        raise core.CompositeError(f"assemblage primaire absent : {manifest_path}")
    return _resolve_run_reference(str(assembled["path"]), root), manifest_path


def _selection_paths(area: str, root: Path) -> tuple[Path, Path]:
    area_root = root / "maps" / area
    return (
        area_root / "patch-compositor-primary-current.json",
        area_root / "patch-compositor-primary-selections",
    )


def _read_current_selection(area: str, root: Path) -> AreaSource | None:
    current_path, _history = _selection_paths(area, root)
    if not current_path.is_file():
        return None
    current = _read_json(current_path)
    if current.get("schema") != SELECTION_SCHEMA or current.get("area_id") != area:
        raise core.CompositeError(f"sélection de patch incompatible : {current_path}")
    record_ref = current.get("selection_record")
    if not isinstance(record_ref, str):
        raise core.CompositeError(f"selection_record absent : {current_path}")
    record_path = root / _safe_relative(record_ref, "selection_record")
    record = _read_json(record_path)
    if record.get("schema") != SELECTION_SCHEMA or record.get("area_id") != area:
        raise core.CompositeError(f"enregistrement de sélection incompatible : {record_path}")
    selected = record.get("selected")
    if not isinstance(selected, Mapping):
        raise core.CompositeError(f"sortie sélectionnée absente : {record_path}")
    run_id = selected.get("run_id")
    output_ref = selected.get("output_path")
    expected_hash = selected.get("sha256")
    if not isinstance(run_id, str) or not isinstance(output_ref, str) or not isinstance(expected_hash, str):
        raise core.CompositeError(f"sortie sélectionnée invalide : {record_path}")
    output_path = root / _safe_relative(output_ref, "selected.output_path")
    if not output_path.is_file() or core.sha256_file(output_path) != expected_hash:
        raise core.CompositeError(f"sortie sélectionnée absente ou divergente : {output_path}")
    manifest_path = root / "maps" / area / "runs" / run_id / "run.json"
    if not manifest_path.is_file():
        raise core.CompositeError(f"run sélectionné absent : {manifest_path}")
    return AreaSource(
        area_id=area,
        source_path=output_path,
        source_sha256=expected_hash,
        parent_run_id=run_id,
        parent_run_manifest=manifest_path,
        source_kind="current-patch-selection",
        selection_record=record_path,
    )


def resolve_area_source(area_id: str, *, base: str = "current", root: Path = core.ROOT) -> AreaSource:
    """Résout le raster primaire x4 sélectionné, sans modifier d'autorité."""

    area = _area_id(area_id)
    if base not in {"base", "current"}:
        raise core.CompositeError("base doit être base ou current")
    if base == "current":
        selection = _read_current_selection(area, root)
        if selection is not None:
            return selection
    run_id = _selected_base_run(area, root)
    source_path, manifest_path = _run_primary_assembled(area, run_id, root)
    return AreaSource(
        area_id=area,
        source_path=source_path,
        source_sha256=core.sha256_file(source_path),
        parent_run_id=run_id,
        parent_run_manifest=manifest_path,
        source_kind="areas-csv-base",
        selection_record=None,
    )


def _safe_run_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,119}", value):
        raise core.CompositeError(f"run_id invalide : {value!r}")
    return value


def propose_run_id(source: AreaSource, patch_path: Path) -> str:
    digest = core.sha256_file(patch_path.resolve())[:10]
    return _safe_run_id(f"{source.parent_run_id}-patch-{digest}-v1".lower())


def area_plan(
    area_id: str,
    patch_path: Path,
    config_path: Path | None = None,
    *,
    base: str = "current",
    run_id: str | None = None,
    root: Path = core.ROOT,
) -> dict[str, Any]:
    """Prépare une application par zone sans créer de fichier."""

    source = resolve_area_source(area_id, base=base, root=root)
    patch_path = patch_path.resolve()
    input_report = core.inspect_inputs(source.source_path, patch_path, config_path)
    identifier = _safe_run_id(run_id) if run_id else propose_run_id(source, patch_path)
    run_root = root / "maps" / source.area_id / "runs" / identifier
    output_name = f"{source.source_path.stem}--patch-{core.sha256_file(patch_path)[:10]}{source.source_path.suffix.lower() or '.png'}"
    output_relative = Path("tuiles-principales") / "03_assemble" / output_name
    return {
        "schema": "bg2-upscale-map-patch-compositor-area-plan-v1",
        "area_id": source.area_id,
        "layer": "tuiles-principales",
        "base": {
            "kind": source.source_kind,
            "path": _root_reference(source.source_path, root),
            "sha256": source.source_sha256,
            "parent_run_id": source.parent_run_id,
            "parent_run_manifest": _root_reference(source.parent_run_manifest, root),
            "selection_record": _root_reference(source.selection_record, root) if source.selection_record else None,
        },
        "patch": input_report["patch"],
        "proposed_run_id": identifier,
        "proposed_run_root": _root_reference(run_root, root),
        "proposed_output": _root_reference(run_root / output_relative, root),
        "output_run_available": not run_root.exists() and not run_root.with_name(run_root.name + ".partial").exists(),
        "registration": {
            "scale_bounds": input_report["scale_bounds"],
            "map_search_roi": input_report["map_search_roi"],
        },
    }


def apply_area_patch(
    area_id: str,
    patch_path: Path,
    config_path: Path | None = None,
    *,
    base: str = "current",
    run_id: str | None = None,
    root: Path = core.ROOT,
) -> dict[str, Any]:
    """Crée un nouveau run dérivé; ne touche ni le parent ni la sélection courante."""

    plan = area_plan(area_id, patch_path, config_path, base=base, run_id=run_id, root=root)
    if not plan["output_run_available"]:
        raise core.CompositeError(f"run de patch déjà présent : {plan['proposed_run_root']}")
    source = resolve_area_source(area_id, base=base, root=root)
    target_run = root / _safe_relative(str(plan["proposed_run_root"]), "proposed_run_root")
    target_output = _safe_relative(str(plan["proposed_output"]), "proposed_output").relative_to(target_run.relative_to(root))
    metadata = {
        "run_id": str(plan["proposed_run_id"]),
        "area_id": source.area_id,
        "run_kind": "map-patch-composite",
        "layer": "tuiles-principales",
        "parents": [{
            "kind": source.source_kind,
            "run_id": source.parent_run_id,
            "run_manifest": _root_reference(source.parent_run_manifest, root),
            "image": _root_reference(source.source_path, root),
            "sha256": source.source_sha256,
            "selection_record": _root_reference(source.selection_record, root) if source.selection_record else None,
        }],
        "selection_state": "unselected",
    }
    return core.compose(
        source.source_path,
        patch_path,
        target_run,
        config_path,
        result_relative_path=target_output,
        run_metadata=metadata,
    )


def _atomic_json(path: Path, data: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.partial")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def select_area_patch(area_id: str, run_id: str, *, root: Path = core.ROOT) -> dict[str, Any]:
    """Désigne un run de patch validé comme raster courant, sans modifier la map de base."""

    area = _area_id(area_id)
    run = _safe_run_id(run_id)
    run_root = root / "maps" / area / "runs" / run
    manifest_path = run_root / "run.json"
    manifest = _read_json(manifest_path)
    if manifest.get("schema") != core.COMPOSITOR_SCHEMA or manifest.get("status") != "completed":
        raise core.CompositeError(f"run de patch non terminé ou incompatible : {manifest_path}")
    if manifest.get("area_id") != area or manifest.get("run_id") != run:
        raise core.CompositeError(f"identité de run de patch incohérente : {manifest_path}")
    outputs = manifest.get("outputs")
    image = outputs.get("image") if isinstance(outputs, Mapping) else None
    if not isinstance(image, Mapping) or not isinstance(image.get("path"), str) or not isinstance(image.get("sha256"), str):
        raise core.CompositeError(f"sortie de run de patch invalide : {manifest_path}")
    output_relative = _safe_relative(str(image["path"]), "outputs.image.path")
    output_path = run_root / output_relative
    expected_hash = str(image["sha256"])
    if not output_path.is_file() or core.sha256_file(output_path) != expected_hash:
        raise core.CompositeError(f"sortie de patch absente ou divergente : {output_path}")
    current_path, history_root = _selection_paths(area, root)
    history_root.mkdir(parents=True, exist_ok=True)
    history_path = history_root / f"{run}.json"
    if history_path.exists():
        raise core.CompositeError(f"sélection immuable déjà existante : {history_path}")
    previous: str | None = None
    if current_path.is_file():
        previous_payload = _read_json(current_path)
        previous_value = previous_payload.get("selection_record")
        if isinstance(previous_value, str):
            previous = previous_value
    record = {
        "schema": SELECTION_SCHEMA,
        "area_id": area,
        "layer": "tuiles-principales",
        "selected_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected": {
            "run_id": run,
            "run_manifest": _root_reference(manifest_path, root),
            "output_path": _root_reference(output_path, root),
            "sha256": expected_hash,
            "pixel_sha256": image.get("pixel_sha256", ""),
        },
        "previous_selection_record": previous,
        "scope": "derived-raster-selection-only; does-not-change-areas-csv-build-installation-or-release",
    }
    _atomic_json(history_path, record)
    current = {
        "schema": SELECTION_SCHEMA,
        "area_id": area,
        "layer": "tuiles-principales",
        "selection_record": _root_reference(history_path, root),
    }
    _atomic_json(current_path, current)
    return record
