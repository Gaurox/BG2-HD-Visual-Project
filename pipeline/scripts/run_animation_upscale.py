"""Run the reproducible BAM area-animation upscale pipeline.

Select one or more BAM resrefs directly, or expand all BAM resources used by an
area. The run copies immutable sources, exports aligned x1 frames, preserves BAM
geometry, calls SeedVR frame by frame, records resumable SHA-256 manifests, and
builds the generic x4 runtime registry. It never edits the game, DLL, INI,
override or release catalogues.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

import animation_paths
from workspace_paths import get_service

from run_seedvr_comfyui import APPROVED_3B_SHA256, APPROVED_7B_SHA256, sha256_file


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANIMATIONS_DIR = PROJECT_ROOT / "animations"
DEFAULT_WORKFLOW = (
    PROJECT_ROOT / "pipeline" / "comfyui" / "workflows" / "SeedVR-Image-BG2-Pipeline-7B.api.json"
)
EXPORT_SCRIPT = PROJECT_ROOT / "pipeline" / "scripts" / "export_bam_frames.py"
UPSCALE_SCRIPT = PROJECT_ROOT / "pipeline" / "scripts" / "upscale_animation_frames.py"
RUNTIME_PACK_SCRIPT = PROJECT_ROOT / "pipeline" / "scripts" / "build_animation_runtime_pack.py"
RUN_SCHEMA = "bg2-upscale-area-animation-run-v1"
FRAME_SCHEMA = "bg2-upscale-animation-frames-x1-v1"
UPSCALE_SCHEMA = "bg2-upscale-animation-frames-v1"
PACK_SCHEMA = "bg2-upscale-area-animation-runtime-pack-v1"
RESREF_RE = re.compile(r"^[A-Z0-9_]{1,8}$")
SUPPORTED_RESOURCE_KINDS = {"BAM", "WBM", "PVRZ"}


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", action="append", default=[], help="BAM à traiter; répétable")
    parser.add_argument("--area", action="append", default=[], help="zone dont tous les BAM seront traités; répétable")
    parser.add_argument(
        "--run",
        help=(
            "identifiant simple; nouveau run mono-resref sous "
            "animations/ressources/<RESREF>/runs, sinon sous animations/batches"
        ),
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        help="racine explicite; utiliser animations/runs seulement pour un chemin legacy",
    )
    parser.add_argument("--scale", type=int, choices=(2, 4), default=4)
    parser.add_argument("--pad", type=int, default=32)
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--server", default=get_service("comfyui_url"))
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--prepare-only", action="store_true", help="copie et extrait sans contacter ComfyUI")
    parser.add_argument("--resume", action="store_true", help="reprend exactement le même run")
    parser.add_argument("--plan", action="store_true", help="affiche la sélection sans créer de run")
    args = parser.parse_args()

    if not args.resref and not args.area:
        parser.error("au moins un --resref ou --area est requis")
    if not args.plan:
        if not args.run:
            parser.error("--run est requis hors mode --plan")
    if args.run:
        try:
            animation_paths.validate_run_id(args.run)
        except RuntimeError as exc:
            parser.error(str(exc))
    if args.pad < 0:
        parser.error("--pad doit être positif ou nul")
    if args.poll_seconds <= 0 or args.timeout_seconds <= 0:
        parser.error("les délais doivent être strictement positifs")
    return args


def atomic_write_json(payload: dict[str, Any], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"index introuvable : {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def normalise_resref(value: str) -> str:
    value = value.strip().upper()
    if not RESREF_RE.fullmatch(value):
        raise RuntimeError(f"resref BAM invalide : {value!r}")
    return value


def normalise_area(value: str) -> str:
    value = value.strip().upper()
    if not RESREF_RE.fullmatch(value):
        raise RuntimeError(f"zone invalide : {value!r}")
    return value


def occurrence_resref(row: dict[str, str]) -> str:
    """Read the canonical v2 field while accepting legacy occurrence fixtures."""
    return normalise_resref(row.get("resource_resref") or row.get("bam_resref") or "")


def occurrence_kind(row: dict[str, str]) -> str:
    kind = (row.get("resource_kind") or "BAM").strip().upper()
    if kind not in SUPPORTED_RESOURCE_KINDS:
        raise RuntimeError(f"type de ressource ARE invalide : {kind!r}")
    return kind


def exclusion_reason(row: dict[str, str]) -> str | None:
    kind = occurrence_kind(row)
    if kind != "BAM":
        return f"resource-kind-{kind.lower()}"
    palette_mode = (row.get("palette_mode") or "embedded").strip().lower()
    palette_resref = (row.get("palette_resref") or "").strip().upper()
    if palette_mode == "external" or palette_resref:
        return f"external-palette-{palette_resref or 'missing-resref'}"
    return None


def load_selection(
    requested_resrefs: list[str],
    requested_areas: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, str]]]:
    resources = read_csv(ANIMATIONS_DIR / "index" / "ressources.csv")
    occurrences = read_csv(ANIMATIONS_DIR / "index" / "occurrences.csv")
    resources_by_resref = {normalise_resref(row["bam_resref"]): row for row in resources}
    explicit = {normalise_resref(value) for value in requested_resrefs}
    areas = {normalise_area(value) for value in requested_areas}
    for area in areas:
        if not any(row.get("area_id", "").upper() == area for row in occurrences):
            raise RuntimeError(f"zone absente de l'inventaire d'animations : {area}")

    eligible = [row for row in occurrences if exclusion_reason(row) is None]
    expanded = {
        occurrence_resref(row)
        for row in eligible
        if row.get("area_id", "").upper() in areas
    }
    area_exclusions = [
        row for row in occurrences
        if row.get("area_id", "").upper() in areas and exclusion_reason(row) is not None
    ]
    for resref in explicit:
        matching = [row for row in occurrences if occurrence_resref(row) == resref]
        if matching and not any(exclusion_reason(row) is None for row in matching):
            reasons = sorted({str(exclusion_reason(row)) for row in matching})
            raise RuntimeError(
                f"{resref}: aucune occurrence éligible au pipeline BAM ({', '.join(reasons)})"
            )

    selected_resrefs = sorted(explicit | expanded)
    if not selected_resrefs:
        reasons = sorted({str(exclusion_reason(row)) for row in area_exclusions})
        suffix = f"; exclusions : {', '.join(reasons)}" if reasons else ""
        raise RuntimeError(f"aucun BAM éligible dans la sélection{suffix}")
    missing = [resref for resref in selected_resrefs if resref not in resources_by_resref]
    if missing:
        raise RuntimeError("BAM absent de l'inventaire extrait : " + ", ".join(missing))

    selected_occurrences = [
        row for row in eligible if occurrence_resref(row) in selected_resrefs
    ]
    excluded_occurrences = [
        row for row in occurrences
        if exclusion_reason(row) is not None
        and (
            occurrence_resref(row) in selected_resrefs
            or row.get("area_id", "").upper() in areas
        )
    ]
    selected: list[dict[str, Any]] = []
    for resref in selected_resrefs:
        row = resources_by_resref[resref]
        source = ANIMATIONS_DIR / Path(row["relative_path"]) / "source.bam"
        if not source.is_file():
            raise RuntimeError(f"source BAM extraite absente : {source}")
        actual_hash = sha256_file(source)
        indexed_hash = row.get("sha256", "").lower()
        if indexed_hash and actual_hash != indexed_hash:
            raise RuntimeError(f"source {resref} modifiée depuis la génération de l'index")
        eligible_for_resref = [
            occurrence for occurrence in selected_occurrences
            if occurrence_resref(occurrence) == resref
        ]
        selected.append({
            "resref": resref,
            "source": source.resolve(),
            "source_sha256": actual_hash,
            "inventory": {
                "frames": int(row.get("frames") or 0),
                "max_frame_width": int(row.get("max_frame_width") or 0),
                "max_frame_height": int(row.get("max_frame_height") or 0),
                "occurrences": len(eligible_for_resref),
                "areas": sorted({
                    occurrence.get("area_id", "") for occurrence in eligible_for_resref
                    if occurrence.get("area_id", "")
                }),
            },
        })
    return selected, selected_occurrences, excluded_occurrences


def exclusion_summary(rows: list[dict[str, str]]) -> list[str]:
    grouped: dict[tuple[str, str], set[str]] = {}
    counts: dict[tuple[str, str], int] = {}
    for row in rows:
        reason = str(exclusion_reason(row))
        key = (occurrence_resref(row), reason)
        grouped.setdefault(key, set()).add(str(row.get("area_id", "")))
        counts[key] = counts.get(key, 0) + 1
    return [
        f"{resref}: {reason}, {counts[(resref, reason)]} occurrence(s), "
        f"zones={';'.join(sorted(grouped[(resref, reason)]))}"
        for resref, reason in sorted(grouped)
    ]


def signature_for(request: dict[str, Any]) -> str:
    raw = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def display_plan(selected: list[dict[str, Any]], areas: list[str], scale: int,
                 excluded: list[dict[str, str]], proposed_location: Path) -> None:
    print(f"Sélection : {len(selected)} BAM, échelle x{scale}")
    if areas:
        print("Zones demandées : " + ", ".join(sorted(areas)))
    print(f"{'RESREF':<9} {'FRAMES':>6} {'MAX X1':>13} {'OCC.':>6}  ZONES")
    for item in selected:
        inventory = item["inventory"]
        maximum = f"{inventory['max_frame_width']}x{inventory['max_frame_height']}"
        print(
            f"{item['resref']:<9} {inventory['frames']:>6} {maximum:>13} "
            f"{inventory['occurrences']:>6}  {';'.join(inventory['areas'])}"
        )
    if excluded:
        print("Occurrences exclues du pipeline BAM :")
        for summary in exclusion_summary(excluded):
            print(f"- {summary}")
    print("Emplacement de run proposé : " + animation_paths.display_path(proposed_location))


def copy_source(source: Path, destination: Path, expected_hash: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file():
        if sha256_file(destination) != expected_hash:
            raise RuntimeError(f"copie source existante modifiée : {destination}")
        return
    if destination.exists():
        raise RuntimeError(f"destination source invalide : {destination}")
    temporary = destination.with_suffix(destination.suffix + ".part")
    shutil.copyfile(source, temporary)
    if sha256_file(temporary) != expected_hash:
        raise RuntimeError(f"copie source corrompue : {temporary}")
    temporary.replace(destination)


def remove_partial_stage(path: Path, resource_dir: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(resource_dir.resolve())
    except ValueError as exc:
        raise RuntimeError(f"refus de supprimer un dossier partiel hors ressource : {resolved}") from exc
    if resolved.is_dir():
        shutil.rmtree(resolved)
    elif resolved.exists():
        resolved.unlink()


def validate_frame_export(stage: Path, source_hash: str) -> dict[str, Any]:
    manifest_path = stage / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"manifeste d'extraction absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != FRAME_SCHEMA:
        raise RuntimeError(f"schéma d'extraction invalide : {manifest.get('schema')}")
    if manifest.get("source_sha256") != source_hash:
        raise RuntimeError("l'extraction ne correspond pas au BAM copié")
    frames = manifest.get("frames") or []
    if manifest.get("frame_count") != len(frames) or not frames:
        raise RuntimeError("nombre de frames extrait incohérent")
    aligned_size = tuple(manifest.get("aligned_canvas_size") or ())
    if len(aligned_size) != 2 or min(int(value) for value in aligned_size) <= 0:
        raise RuntimeError("dimensions de canvas aligné invalides")
    for index, frame in enumerate(frames):
        if frame.get("frame") != index or frame.get("file") != f"frame_{index:03d}.png":
            raise RuntimeError("ordre ou nom de frames invalide")
        for kind, hash_key in (("rgb", "rgb_sha256"), ("alpha", "alpha_sha256"), ("rgba", "rgba_sha256")):
            path = stage / kind / frame["file"]
            if not path.is_file() or sha256_file(path) != frame.get(hash_key):
                raise RuntimeError(f"frame extraite absente ou modifiée : {path}")
            with Image.open(path) as image:
                if image.size != aligned_size:
                    raise RuntimeError(f"canvas inattendu : {path}")
    return manifest


def export_frames(source_copy: Path, stage: Path, source_hash: str, resume: bool) -> dict[str, Any]:
    if stage.is_dir():
        return validate_frame_export(stage, source_hash)
    if stage.exists():
        raise RuntimeError(f"étape d'extraction invalide : {stage}")
    partial = stage.with_name(stage.name + ".partial")
    if partial.exists():
        if not resume:
            raise RuntimeError(f"étape partielle existante : {partial}")
        remove_partial_stage(partial, stage.parent)
    subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), str(source_copy), str(partial)],
        cwd=PROJECT_ROOT,
        check=True,
    )
    manifest = validate_frame_export(partial, source_hash)
    partial.replace(stage)
    return manifest


def validate_upscale(stage: Path, scale: int, frame_count: int) -> dict[str, Any]:
    manifest_path = stage / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"manifeste d'upscale absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != UPSCALE_SCHEMA or manifest.get("status") != "completed":
        raise RuntimeError(f"upscale incomplet : {manifest.get('status')}")
    if manifest.get("scale") != scale or len(manifest.get("frames") or []) != frame_count:
        raise RuntimeError("échelle ou nombre de frames upscale incohérent")
    return manifest


def run_upscale(
    stage_x1: Path,
    output: Path,
    args: argparse.Namespace,
    resref: str,
    frame_count: int,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(UPSCALE_SCRIPT),
        str(stage_x1 / "rgb"),
        str(stage_x1 / "alpha"),
        str(output),
        "--frame-manifest",
        str(stage_x1 / "manifest.json"),
        "--scale",
        str(args.scale),
        "--pad",
        str(args.pad),
        "--workflow",
        str(args.workflow.resolve()),
        "--server",
        args.server,
        "--poll-seconds",
        str(args.poll_seconds),
        "--timeout-seconds",
        str(args.timeout_seconds),
        "--upload-folder",
        f"BG2_Upscale/animation-runs/{args.run}/{resref}/x{args.scale}",
    ]
    if args.resume:
        command.append("--resume")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    return validate_upscale(output, args.scale, frame_count)


def build_runtime_pack(run_dir: Path, resume: bool) -> dict[str, Any]:
    output = run_dir / "03_runtime_pack"
    command = [sys.executable, str(RUNTIME_PACK_SCRIPT), str(run_dir), str(output)]
    if resume:
        command.append("--resume")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    manifest_path = output / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"manifeste runtime absent : {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest.get("schema") != PACK_SCHEMA
        or manifest.get("status") != "completed"
        or manifest.get("scale") != 4
        or manifest.get("source_run_manifest_sha256") != sha256_file(run_dir / "manifest.json")
    ):
        raise RuntimeError(f"pack runtime invalide : {output}")
    return manifest


def main() -> None:
    args = parse_args()
    selected, occurrences, excluded_occurrences = load_selection(args.resref, args.area)
    areas = sorted({normalise_area(value) for value in args.area})
    selected_resrefs = [item["resref"] for item in selected]
    run_dir = (
        animation_paths.resolve_run_destination(
            args.run,
            selected_resrefs,
            runs_root=args.runs_root,
            animations_root=ANIMATIONS_DIR,
        )
        if args.run
        else (
            args.runs_root.resolve()
            if args.runs_root is not None
            else animation_paths.default_run_root(
                selected_resrefs,
                animations_root=ANIMATIONS_DIR,
            )
        )
    )
    display_plan(selected, areas, args.scale, excluded_occurrences, run_dir)
    if args.plan:
        return

    workflow = args.workflow.resolve()
    if not workflow.is_file():
        raise RuntimeError(f"workflow absent : {workflow}")
    workflow_hash = sha256_file(workflow)
    if workflow_hash not in (APPROVED_7B_SHA256, APPROVED_3B_SHA256):
        raise RuntimeError(f"workflow non approuvé pour les animations : {workflow_hash}")

    request = {
        "requested_resrefs": sorted({normalise_resref(value) for value in args.resref}),
        "requested_areas": areas,
        "resolved_resrefs": [item["resref"] for item in selected],
        "sources": {item["resref"]: item["source_sha256"] for item in selected},
        "scale": args.scale,
        "padding_x1": args.pad,
        "workflow_sha256": workflow_hash,
    }
    signature = signature_for(request)
    manifest_path = run_dir / "manifest.json"

    if run_dir.exists() and any(run_dir.iterdir()) and not args.resume:
        raise RuntimeError(f"run non vide; utiliser --resume : {run_dir}")
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("schema") != RUN_SCHEMA or manifest.get("request_signature") != signature:
            raise RuntimeError("le run existant ne correspond pas à la sélection ou aux paramètres")
    else:
        if run_dir.exists() and any(run_dir.iterdir()):
            raise RuntimeError(f"run sans manifeste, reprise impossible : {run_dir}")
        run_dir.mkdir(parents=True, exist_ok=True)
        occurrence_fields = (
            "area_id", "occurrence_index", "instance_name", "x", "y",
            "sequence", "initial_frame", "flags_hex", "palette_mode", "palette_resref",
        )
        manifest = {
            "schema": RUN_SCHEMA,
            "status": "preparing",
            "created_utc": utc_now(),
            "updated_utc": utc_now(),
            "run": args.run,
            "request_signature": signature,
            "request": request,
            "occurrences": [
                {
                    **{key: row.get(key) for key in occurrence_fields},
                    "bam_resref": occurrence_resref(row),
                    "resource_kind": occurrence_kind(row),
                }
                for row in occurrences
            ],
            "resources": [
                {
                    "resref": item["resref"],
                    "status": "pending",
                    "canonical_source": item["source"].as_posix(),
                    "source_sha256": item["source_sha256"],
                    "inventory": item["inventory"],
                }
                for item in selected
            ],
        }
        atomic_write_json(manifest, manifest_path)

    records = {record["resref"]: record for record in manifest["resources"]}
    if manifest.get("status") == "completed":
        # A completed run is immutable. Revalidate every stage and the runtime
        # pack without touching timestamps or manifests.
        for item in selected:
            resref = item["resref"]
            record = records[resref]
            if record.get("status") != "completed":
                raise RuntimeError(f"run terminé mais ressource incohérente : {resref}")
            source_copy = (run_dir / record["source_copy"]).resolve()
            try:
                source_copy.relative_to(run_dir)
            except ValueError as exc:
                raise RuntimeError(f"copie source hors run : {source_copy}") from exc
            copy_source(item["source"], source_copy, item["source_sha256"])
            stage_x1 = (run_dir / record["frames_x1"]).resolve()
            stage_xn = (run_dir / record["upscale"]).resolve()
            for stage in (stage_x1, stage_xn):
                try:
                    stage.relative_to(run_dir)
                except ValueError as exc:
                    raise RuntimeError(f"étape hors run : {stage}") from exc
            frame_manifest = validate_frame_export(stage_x1, item["source_sha256"])
            run_upscale(stage_x1, stage_xn, args, resref, frame_manifest["frame_count"])
        if args.scale == 4:
            pack = build_runtime_pack(run_dir, True)
            print(
                f"already completed and validated: {len(selected)} BAM, "
                f"{pack['frame_count']} frames, pack runtime intact"
            )
        else:
            print(f"already completed and validated: {len(selected)} BAM dans {run_dir}")
        return

    active_record: dict[str, Any] | None = None
    try:
        for item in selected:
            resref = item["resref"]
            active_record = records[resref]
            previous_status = active_record.get("status")
            resource_dir = run_dir / "resources" / resref
            source_copy = resource_dir / "00_source" / f"{resref}.bam"
            stage_x1 = resource_dir / "01_frames_x1"
            stage_xn = resource_dir / f"02_upscale_x{args.scale}"

            active_record["status"] = "preparing"
            active_record.pop("last_error", None)
            manifest["status"] = "preparing"
            manifest["active_resref"] = resref
            manifest["updated_utc"] = utc_now()
            atomic_write_json(manifest, manifest_path)

            copy_source(item["source"], source_copy, item["source_sha256"])
            frame_manifest = export_frames(source_copy, stage_x1, item["source_sha256"], args.resume)
            active_record["source_copy"] = source_copy.relative_to(run_dir).as_posix()
            active_record["frames_x1"] = stage_x1.relative_to(run_dir).as_posix()
            active_record["frame_count"] = frame_manifest["frame_count"]
            active_record["aligned_canvas_size_x1"] = frame_manifest["aligned_canvas_size"]
            active_record["geometry_mode"] = frame_manifest["geometry_mode"]
            active_record["frame_manifest_sha256"] = sha256_file(stage_x1 / "manifest.json")
            active_record["status"] = "prepared"
            manifest["updated_utc"] = utc_now()
            atomic_write_json(manifest, manifest_path)

            if args.prepare_only:
                if previous_status == "completed":
                    run_upscale(
                        stage_x1,
                        stage_xn,
                        args,
                        resref,
                        frame_manifest["frame_count"],
                    )
                    active_record["status"] = "completed"
                    atomic_write_json(manifest, manifest_path)
                continue

            active_record["status"] = "upscaling"
            manifest["status"] = "upscaling"
            manifest["updated_utc"] = utc_now()
            atomic_write_json(manifest, manifest_path)
            upscale_manifest = run_upscale(
                stage_x1,
                stage_xn,
                args,
                resref,
                frame_manifest["frame_count"],
            )
            active_record["upscale"] = stage_xn.relative_to(run_dir).as_posix()
            active_record["upscale_manifest_sha256"] = sha256_file(stage_xn / "manifest.json")
            active_record["preview"] = (
                stage_xn / upscale_manifest["preview"]
            ).relative_to(run_dir).as_posix()
            active_record["status"] = "completed"
            active_record["completed_utc"] = utc_now()
            manifest["updated_utc"] = utc_now()
            atomic_write_json(manifest, manifest_path)

        statuses = {record["status"] for record in records.values()}
        manifest["status"] = "completed" if statuses == {"completed"} else "prepared"
        manifest["updated_utc"] = utc_now()
        if manifest["status"] == "completed":
            manifest["completed_utc"] = utc_now()
        manifest.pop("active_resref", None)
        manifest.pop("last_error", None)
        atomic_write_json(manifest, manifest_path)
        active_record = None
        if manifest["status"] == "completed" and args.scale == 4:
            pack = build_runtime_pack(run_dir, args.resume)
            print(
                f"completed: {len(selected)} BAM, {pack['frame_count']} frames, "
                f"pack runtime dans {run_dir / '03_runtime_pack'}"
            )
        else:
            print(f"{manifest['status']}: {len(selected)} BAM dans {run_dir}")
            if manifest["status"] == "completed":
                print("runtime non généré : seul le chemin x4 est validé en jeu")
    except Exception as exc:
        if active_record is not None:
            active_record["status"] = "failed"
            active_record["last_error"] = str(exc)
        manifest["status"] = "failed"
        manifest["last_error"] = str(exc)
        manifest["updated_utc"] = utc_now()
        atomic_write_json(manifest, manifest_path)
        raise


if __name__ == "__main__":
    configure_utf8_console()
    main()
