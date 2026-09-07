"""Produce one spatial x4 effect run from ``source.bam``.

Default mode is a non-writing plan. With ``--run``, the command reserves the
effect run, exports aligned x1 BAM frames, invokes the approved frame upscaler,
then seals a generic ``run.json``. It deliberately does not update
``effects/index/processing.csv``: use ``effect_workflow.py register-run`` only
after independently reviewing the completed run.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence

import effect_workflow as workflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_SCRIPT = PROJECT_ROOT / "pipeline/scripts/export_bam_frames.py"
UPSCALE_SCRIPT = PROJECT_ROOT / "pipeline/scripts/upscale_animation_frames.py"
PIPELINE_ID = workflow.STAGES["spatial"]
FRAME_SCHEMA = "bg2-upscale-animation-frames-x1-v1"
SPATIAL_SCHEMA = "bg2-upscale-animation-frames-v1"
RECIPE_SCHEMA = "bg2-upscale-effect-spatial-recipe-v1"


class SpatialRunError(RuntimeError):
    """The spatial producer cannot safely create or resume a run."""


@dataclass(frozen=True)
class SpatialPlan:
    root: Path
    resref: str
    asset: Mapping[str, str]
    run_id: str
    run_root: Path
    source: Path
    workflow_path: Path
    workflow_relative: str
    recipe_id: str
    server: str
    pad: int
    poll_seconds: float
    timeout_seconds: float
    upload_folder: str
    color_correction_method: str

    @property
    def frame_root(self) -> Path:
        return self.run_root / "00-frames-x1"

    @property
    def spatial_root(self) -> Path:
        return self.run_root / "01-spatial-x4"

    @property
    def descriptor_path(self) -> Path:
        return self.run_root / "run.json"

    @property
    def recipe_path(self) -> Path:
        return self.run_root / "recipe.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise SpatialRunError(f"JSON illisible: {path}: {error}") from error
    if not isinstance(value, dict):
        raise SpatialRunError(f"objet JSON requis: {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    workflow.atomic_write(path, workflow.json_bytes(value))


def file_evidence(root: Path, role: str, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SpatialRunError(f"preuve absente: {path}")
    return {
        "role": role,
        "path": workflow.relative_path(root, path),
        "sha256": workflow.sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _normalize_workspace_paths(value: Any, root: Path) -> Any:
    """Keep stage manifests portable without changing external runtime values."""

    if isinstance(value, str):
        root_text = root.resolve().as_posix().rstrip("/")
        text = value.replace("\\", "/")
        if text.casefold().startswith((root_text + "/").casefold()):
            return text[len(root_text) + 1 :]
        return value
    if isinstance(value, list):
        return [_normalize_workspace_paths(item, root) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_workspace_paths(item, root) for key, item in value.items()}
    return value


def normalize_manifest_paths(root: Path, path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    portable = _normalize_workspace_paths(manifest, root)
    if portable != manifest:
        write_json(path, portable)
    return portable


def validate_frame_stage(root: Path, stage: Path, source_evidence: Mapping[str, Any]) -> dict[str, Any]:
    manifest_path = stage / "manifest.json"
    manifest = load_json(manifest_path)
    if manifest.get("schema") != FRAME_SCHEMA:
        raise SpatialRunError(f"schéma d'export invalide: {manifest.get('schema')!r}")
    if str(manifest.get("source_sha256", "")).upper() != source_evidence["sha256"]:
        raise SpatialRunError("export x1 lié à une autre source BAM")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or not frames or manifest.get("frame_count") != len(frames):
        raise SpatialRunError("frames x1 absentes ou incohérentes")
    canvas = manifest.get("aligned_canvas_size")
    if not isinstance(canvas, list) or len(canvas) != 2 or not all(isinstance(value, int) and value > 0 for value in canvas):
        raise SpatialRunError("canvas x1 invalide")
    for index, frame in enumerate(frames):
        if not isinstance(frame, Mapping) or frame.get("frame") != index or frame.get("file") != f"frame_{index:03d}.png":
            raise SpatialRunError("ordre de frames x1 invalide")
        for kind in ("rgb", "alpha", "rgba"):
            path = stage / kind / str(frame["file"])
            expected = str(frame.get(f"{kind}_sha256", "")).upper()
            if not path.is_file() or workflow.sha256_file(path) != expected:
                raise SpatialRunError(f"frame x1 absente ou modifiée: {path}")
    return manifest


def validate_spatial_stage(root: Path, stage: Path, frame_manifest: Mapping[str, Any]) -> dict[str, Any]:
    manifest = load_json(stage / "manifest.json")
    if manifest.get("schema") != SPATIAL_SCHEMA or manifest.get("status") != "completed" or manifest.get("scale") != 4:
        raise SpatialRunError("run spatial x4 incomplet ou à mauvaise échelle")
    source = manifest.get("source")
    if not isinstance(source, Mapping) or str(source.get("frame_manifest_sha256", "")).upper() != workflow.sha256_file(stage.parent / "00-frames-x1/manifest.json"):
        raise SpatialRunError("run spatial x4 non lié au manifeste x1 courant")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or len(frames) != int(frame_manifest["frame_count"]):
        raise SpatialRunError("nombre de frames x4 incohérent")
    for index, frame in enumerate(frames):
        if not isinstance(frame, Mapping) or frame.get("frame") != index:
            raise SpatialRunError("ordre de frames x4 invalide")
        for key in ("rgba_xn", "raw_rgba_xn"):
            relative = frame.get(key)
            expected = str(frame.get(f"{key}_sha256", "")).upper()
            if not isinstance(relative, str) or not expected:
                raise SpatialRunError(f"preuve {key} absente pour frame {index}")
            path = stage / relative
            if not path.is_file() or workflow.sha256_file(path) != expected:
                raise SpatialRunError(f"sortie x4 absente ou modifiée: {path}")
    preview = manifest.get("preview")
    preview_hash = str(manifest.get("preview_sha256", "")).upper()
    if not isinstance(preview, str) or not preview_hash:
        raise SpatialRunError("aperçu x4 absent")
    preview_path = stage / preview
    if not preview_path.is_file() or workflow.sha256_file(preview_path) != preview_hash:
        raise SpatialRunError("aperçu x4 absent ou modifié")
    return manifest


def recipe_snapshot(plan: SpatialPlan) -> dict[str, Any]:
    return {
        "schema": RECIPE_SCHEMA,
        "recipe_id": plan.recipe_id,
        "pipeline_id": PIPELINE_ID,
        "scale": 4,
        "alpha_policy": "source alpha enlarged with nearest-neighbour; never generated by SeedVR",
        "transparent_rgb_policy": "export_bam_frames fill_transparent model input; original alpha remains authoritative",
        "workflow": {
            "path": plan.workflow_relative,
            "sha256": workflow.sha256_file(plan.workflow_path),
        },
        "tools": [
            {
                "path": workflow.relative_path(plan.root, EXPORT_SCRIPT),
                "sha256": workflow.sha256_file(EXPORT_SCRIPT),
            },
            {
                "path": workflow.relative_path(plan.root, UPSCALE_SCRIPT),
                "sha256": workflow.sha256_file(UPSCALE_SCRIPT),
            },
            {
                "path": workflow.relative_path(plan.root, Path(__file__)),
                "sha256": workflow.sha256_file(Path(__file__)),
            },
        ],
        "parameters": {
            "pad_x1": plan.pad,
            "poll_seconds": plan.poll_seconds,
            "timeout_seconds": plan.timeout_seconds,
            "upload_folder": plan.upload_folder,
            "color_correction_method": plan.color_correction_method,
        },
    }


def build_descriptor(
    plan: SpatialPlan,
    recipe: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    status: str,
    sealed: bool,
    created_at_utc: str,
    outputs: Sequence[Mapping[str, Any]] = (),
    notes: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "sealed": sealed}
    if status == "completed":
        result["completed_at_utc"] = workflow.utc_now()
    if notes:
        result["notes"] = notes
    return {
        "$schema": "docs/workspace-run.schema.json",
        "schema_version": 1,
        "run_id": plan.run_id,
        "domain": "effects",
        "asset_ids": [f"effects:bam:{plan.resref}"],
        "pipeline": {
            "id": PIPELINE_ID,
            "version": "effect-spatial-runner.v1",
            "recipe_path": workflow.relative_path(plan.root, plan.recipe_path),
            "recipe_sha256": workflow.sha256_file(plan.recipe_path),
        },
        "inputs": [dict(source)],
        "outputs": [dict(item) for item in outputs],
        "provenance": {
            "created_at_utc": created_at_utc,
            "generator": "pipeline/scripts/run_effect_spatial.py",
            "command": ["run_effect_spatial.py", "--resref", plan.resref, "--run-id", plan.run_id],
        },
        "result": result,
    }


def _ensure_source(plan: SpatialPlan) -> dict[str, Any]:
    source = file_evidence(plan.root, "source-bam", plan.source)
    try:
        workflow.assert_source_matches_inventory(plan.source.parent, plan.asset, {"inputs": [source]})
    except workflow.WorkflowError as error:
        raise SpatialRunError(str(error)) from error
    return source


def build_plan(
    root: Path,
    raw_resref: str,
    raw_run_id: str | None,
    recipe_id: str,
    raw_workflow: Path,
    *,
    server: str,
    pad: int,
    poll_seconds: float,
    timeout_seconds: float,
    upload_folder: str,
    color_correction_method: str = "lab",
) -> SpatialPlan:
    if pad < 0 or poll_seconds <= 0 or timeout_seconds <= 0:
        raise SpatialRunError("pad et délais doivent être strictement valides")
    if color_correction_method not in {"lab", "wavelet", "adain", "none"}:
        raise SpatialRunError(f"mode couleur SeedVR invalide: {color_correction_method}")
    try:
        resref, asset, _processing, resource_root = workflow.load_asset(root, raw_resref)
    except workflow.WorkflowError as error:
        raise SpatialRunError(str(error)) from error
    source = resource_root / "source.bam"
    try:
        workflow.assert_source_matches_inventory(source.parent, asset, {"inputs": []})
    except workflow.WorkflowError as error:
        raise SpatialRunError(str(error)) from error
    workflow_path = (
        raw_workflow if raw_workflow.is_absolute() else root / raw_workflow
    ).resolve()
    if not workflow_path.is_file():
        raise SpatialRunError(f"workflow SeedVR absent: {raw_workflow}")
    try:
        workflow_relative = workflow.relative_path(root, workflow_path)
    except workflow.WorkflowError as error:
        raise SpatialRunError("workflow SeedVR doit rester dans le workspace") from error
    if not recipe_id.strip():
        raise SpatialRunError("recipe_id vide")
    run_id = workflow.validate_run_id(raw_run_id) if raw_run_id else workflow.next_run_id(resource_root, resref, "spatial", recipe_id)
    return SpatialPlan(
        root=root, resref=resref, asset=asset, run_id=run_id,
        run_root=resource_root / "runs" / run_id, source=source,
        workflow_path=workflow_path, workflow_relative=workflow_relative,
        recipe_id=recipe_id.strip(), server=server, pad=pad,
        poll_seconds=poll_seconds, timeout_seconds=timeout_seconds,
        upload_folder=upload_folder, color_correction_method=color_correction_method,
    )


def _validate_reservation(plan: SpatialPlan) -> None:
    reservation = workflow.reservation_path(plan.run_root.parent.parent, plan.run_id)
    if not reservation.is_file():
        return
    try:
        payload = load_json(reservation)
    except SpatialRunError as error:
        raise SpatialRunError(f"réservation illisible: {reservation}") from error
    expected = {"asset_id": f"effects:bam:{plan.resref}", "stage": "spatial", "run_id": plan.run_id}
    if any(payload.get(key) != value for key, value in expected.items()):
        raise SpatialRunError("réservation détenue par un autre asset ou une autre étape")


def reserve_plan(plan: SpatialPlan) -> None:
    if plan.descriptor_path.exists():
        return
    if workflow.reservation_path(plan.run_root.parent.parent, plan.run_id).exists():
        _validate_reservation(plan)
        return
    try:
        workflow.new_run(plan.root, plan.resref, "spatial", plan.recipe_id, plan.run_id, write=True)
    except workflow.WorkflowError as error:
        raise SpatialRunError(str(error)) from error


def _run(command: list[str], root: Path) -> None:
    subprocess.run(command, cwd=root, check=True)


def export_frames(plan: SpatialPlan, source: Mapping[str, Any], resume: bool) -> dict[str, Any]:
    if plan.frame_root.exists():
        if not resume:
            raise SpatialRunError(f"frames x1 déjà présentes: {plan.frame_root}; utiliser --resume")
        normalize_manifest_paths(plan.root, plan.frame_root / "manifest.json")
        return validate_frame_stage(plan.root, plan.frame_root, source)
    partial = plan.frame_root.with_name(plan.frame_root.name + ".partial")
    if partial.exists():
        raise SpatialRunError(f"frames x1 partielles présentes: {partial}; intervention explicite requise")
    _run([sys.executable, str(EXPORT_SCRIPT), str(plan.source), str(partial)], plan.root)
    normalize_manifest_paths(plan.root, partial / "manifest.json")
    validate_frame_stage(plan.root, partial, source)
    partial.replace(plan.frame_root)
    return validate_frame_stage(plan.root, plan.frame_root, source)


def upscale_frames(plan: SpatialPlan, frame_manifest: Mapping[str, Any], resume: bool) -> dict[str, Any]:
    command = [
        sys.executable, str(UPSCALE_SCRIPT), str(plan.frame_root / "rgb"), str(plan.frame_root / "alpha"),
        str(plan.spatial_root), "--frame-manifest", str(plan.frame_root / "manifest.json"),
        "--scale", "4", "--workflow", str(plan.workflow_path), "--server", plan.server,
        "--pad", str(plan.pad), "--poll-seconds", str(plan.poll_seconds),
        "--timeout-seconds", str(plan.timeout_seconds), "--upload-folder", plan.upload_folder,
        "--color-correction-method", plan.color_correction_method,
    ]
    if plan.spatial_root.exists():
        if not resume:
            raise SpatialRunError(f"spatial x4 déjà présent: {plan.spatial_root}; utiliser --resume")
        command.append("--resume")
    _run(command, plan.root)
    normalize_manifest_paths(plan.root, plan.spatial_root / "manifest.json")
    return validate_spatial_stage(plan.root, plan.spatial_root, frame_manifest)


def execute(plan: SpatialPlan, *, resume: bool) -> dict[str, Any]:
    created_at_utc = workflow.utc_now()
    if plan.run_root.exists() and not plan.descriptor_path.is_file():
        raise SpatialRunError(f"run sans run.json: {plan.run_root}")
    if plan.descriptor_path.is_file():
        previous = load_json(plan.descriptor_path)
        if previous.get("result", {}).get("sealed") is True:
            raise SpatialRunError("run déjà scellé; créer un nouveau run_id")
        if not resume:
            raise SpatialRunError("run non scellé existant; utiliser --resume")
        previous_created = previous.get("provenance", {}).get("created_at_utc")
        if isinstance(previous_created, str):
            created_at_utc = previous_created
    else:
        reserve_plan(plan)

    _validate_reservation(plan)
    recipe = recipe_snapshot(plan)
    if plan.recipe_path.exists():
        # A failed/unsealed run keeps the exact recipe that produced its existing
        # frames. A later workflow-wrapper fix must validate and seal those bytes,
        # never rewrite their provenance with the newer wrapper hash.
        recipe = load_json(plan.recipe_path)
        if recipe.get("schema") != RECIPE_SCHEMA or recipe.get("pipeline_id") != PIPELINE_ID:
            raise SpatialRunError("recipe.json existant invalide; créer un nouveau run_id")
    else:
        write_json(plan.recipe_path, recipe)
    source = _ensure_source(plan)
    write_json(
        plan.descriptor_path,
        build_descriptor(
            plan, recipe, source, status="running", sealed=False,
            created_at_utc=created_at_utc,
        ),
    )
    try:
        frames = export_frames(plan, source, resume)
        spatial = upscale_frames(plan, frames, resume)
        outputs = [
            file_evidence(plan.root, "frames-manifest", plan.frame_root / "manifest.json"),
            file_evidence(plan.root, "spatial-manifest", plan.spatial_root / "manifest.json"),
            file_evidence(plan.root, "spatial-preview", plan.spatial_root / str(spatial["preview"])),
        ]
        complete = build_descriptor(
            plan, recipe, source, status="completed", sealed=True, outputs=outputs,
            created_at_utc=created_at_utc,
        )
        write_json(plan.descriptor_path, complete)
        return {
            "command": "run-effect-spatial", "resref": plan.resref, "run_id": plan.run_id,
            "run_descriptor": workflow.relative_path(plan.root, plan.descriptor_path),
            "run_descriptor_sha256": workflow.sha256_file(plan.descriptor_path),
            "next": "effect_workflow.py register-run --stage spatial --run-id " + plan.run_id,
            "release_mutation": False,
        }
    except (OSError, SpatialRunError, subprocess.CalledProcessError) as error:
        write_json(
            plan.descriptor_path,
            build_descriptor(
                plan, recipe, source, status="failed", sealed=False,
                created_at_utc=created_at_utc, notes=str(error),
            ),
        )
        raise SpatialRunError(str(error)) from error


def plan_payload(plan: SpatialPlan) -> dict[str, Any]:
    return {
        "command": "run-effect-spatial", "write": False, "resref": plan.resref,
        "asset_id": f"effects:bam:{plan.resref}", "run_id": plan.run_id,
        "run_directory": workflow.relative_path(plan.root, plan.run_root),
        "pipeline_id": PIPELINE_ID, "recipe_id": plan.recipe_id,
        "color_correction_method": plan.color_correction_method,
        "source": workflow.relative_path(plan.root, plan.source),
        "workflow": plan.workflow_relative,
        "stages": ["00-frames-x1", "01-spatial-x4"],
        "authority_mutation": "none; register-run is separate", "release_mutation": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--workflow", type=Path, required=True, help="workflow SeedVR approuvé dans le workspace")
    parser.add_argument("--recipe-id", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--pad", type=int, default=32)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    parser.add_argument("--upload-folder", default="BG2_Upscale/effect-runs")
    parser.add_argument(
        "--color-correction-method",
        choices=("lab", "wavelet", "adain", "none"),
        default="lab",
    )
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run", action="store_true", help="produit le run; sinon plan seulement")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        plan = build_plan(
            args.workspace_root.resolve(), args.resref, args.run_id, args.recipe_id, args.workflow,
            server=args.server, pad=args.pad, poll_seconds=args.poll_seconds,
            timeout_seconds=args.timeout_seconds, upload_folder=args.upload_folder,
            color_correction_method=args.color_correction_method,
        )
        result = execute(plan, resume=args.resume) if args.run else plan_payload(plan)
    except (SpatialRunError, workflow.WorkflowError) as error:
        print(f"ERROR: {error}")
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
