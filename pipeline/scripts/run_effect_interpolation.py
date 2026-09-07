"""Produce one sealed 30 FPS effect run derived from a sealed spatial x4 run.

Apollo receives only RGB frames on a closed loop.  The original enlarged alpha
is reattached by deterministic nearest temporal phase; no alpha is invented by
the interpolation model.  The command never selects, installs or releases the
result: registration remains an explicit workflow transition.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Mapping, Sequence

from PIL import Image

import effect_workflow as workflow
from workspace_paths import get_path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ID = workflow.STAGES["interpolation"]
SPATIAL_SCHEMA = "bg2-upscale-animation-frames-v1"
INTERPOLATION_SCHEMA = "bg2-upscale-effect-interpolation-30fps-v1"
RECIPE_SCHEMA = "bg2-upscale-effect-interpolation-recipe-v1"
DEFAULT_TVAI_FFMPEG = get_path("topaz_video_ffmpeg")
DEFAULT_TVAI_MODEL_DIR = get_path("topaz_video_models")
DEFAULT_MODEL = "apo-8"
REPLACE_DUPLICATE_THRESHOLD = -0.01


class InterpolationError(RuntimeError):
    """The interpolation producer cannot create a valid immutable run."""


@dataclass(frozen=True)
class InterpolationPlan:
    root: Path
    resref: str
    asset: Mapping[str, str]
    spatial_run: str
    run_id: str
    run_root: Path
    parent_descriptor: Path
    parent_output: Mapping[str, Any]
    spatial_manifest: Path
    recipe_id: str
    native_fps: int
    target_fps: int
    tvai_ffmpeg: Path
    tvai_model_dir: Path
    model: str
    device: str

    @property
    def interpolation_root(self) -> Path:
        return self.run_root / "02-interpolation"

    @property
    def recipe_path(self) -> Path:
        return self.run_root / "recipe.json"

    @property
    def descriptor_path(self) -> Path:
        return self.run_root / "run.json"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InterpolationError(f"JSON illisible : {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InterpolationError(f"objet JSON requis : {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    workflow.atomic_write(path, workflow.json_bytes(value))


def evidence(root: Path, role: str, path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise InterpolationError(f"preuve absente : {path}")
    return {
        "role": role,
        "path": workflow.relative_path(root, path),
        "sha256": workflow.sha256_file(path),
        "bytes": path.stat().st_size,
    }


def parse_numbered_pngs(directory: Path) -> list[Path]:
    files = sorted(path for path in directory.glob("*.png") if path.is_file())
    if not files:
        raise InterpolationError(f"aucune frame Apollo : {directory}")
    numbers: list[int] = []
    for path in files:
        match = re.fullmatch(r"out_(\d+)", path.stem)
        if match is None:
            raise InterpolationError(f"nom de frame Apollo invalide : {path.name}")
        numbers.append(int(match.group(1)))
    if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
        raise InterpolationError("numérotation Apollo non contiguë")
    return files


def rate_text(fps: int) -> str:
    if fps <= 0:
        raise InterpolationError("FPS invalide")
    return str(fps)


def topaz_version(ffmpeg: Path) -> str:
    completed = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-version"], check=True, capture_output=True, text=True
    )
    return next((line.strip() for line in completed.stdout.splitlines() if line.strip()), "")


def validate_spatial_manifest(plan: InterpolationPlan) -> dict[str, Any]:
    manifest = load_json(plan.spatial_manifest)
    if (
        manifest.get("schema") != SPATIAL_SCHEMA
        or manifest.get("status") != "completed"
        or manifest.get("scale") != 4
    ):
        raise InterpolationError("manifeste spatial parent incompatible")
    frames = manifest.get("frames")
    if not isinstance(frames, list) or not frames:
        raise InterpolationError("frames spatiales absentes")
    if [item.get("frame") for item in frames] != list(range(len(frames))):
        raise InterpolationError("ordre des frames spatiales invalide")
    sizes: set[tuple[int, int]] = set()
    aligned_sizes: set[tuple[int, int]] = set()
    aligned_frame_count = 0
    for index, frame in enumerate(frames):
        if not isinstance(frame, Mapping):
            raise InterpolationError(f"frame spatiale invalide : {index}")
        logical = frame.get("logical_size_x1")
        physical = frame.get("physical_size_xn")
        raw = frame.get("raw_rgba_xn")
        alpha = frame.get("alpha_xn")
        if (
            not isinstance(logical, list)
            or not isinstance(physical, list)
            or len(logical) != 2
            or len(physical) != 2
            or physical != [int(logical[0]) * 4, int(logical[1]) * 4]
            or not isinstance(raw, str)
            or not isinstance(alpha, str)
        ):
            raise InterpolationError(f"frame spatiale incomplète : {index}")
        raw_path = plan.spatial_manifest.parent / raw
        alpha_path = plan.spatial_manifest.parent / alpha
        expected_bytes = int(physical[0]) * int(physical[1]) * 4
        if (
            not raw_path.is_file()
            or raw_path.stat().st_size != expected_bytes
            or workflow.sha256_file(raw_path) != str(frame.get("raw_rgba_xn_sha256", "")).upper()
            or not alpha_path.is_file()
            or workflow.sha256_file(alpha_path) != str(frame.get("alpha_xn_sha256", "")).upper()
        ):
            raise InterpolationError(f"frame spatiale modifiée ou absente : {index}")
        sizes.add((int(physical[0]), int(physical[1])))
        aligned_size = frame.get("aligned_size_x1")
        aligned_rgba = frame.get("aligned_rgba_xn")
        aligned_digest = frame.get("aligned_rgba_xn_sha256")
        crop = frame.get("runtime_crop_box_xn")
        if any(value is not None for value in (aligned_size, aligned_rgba, aligned_digest, crop)):
            if (
                not isinstance(aligned_size, list)
                or len(aligned_size) != 2
                or not all(type(value) is int and value > 0 for value in aligned_size)
                or not isinstance(aligned_rgba, str)
                or not isinstance(aligned_digest, str)
                or not isinstance(crop, list)
                or len(crop) != 4
                or not all(type(value) is int for value in crop)
            ):
                raise InterpolationError(f"canevas aligné incomplet : {index}")
            aligned_physical = (int(aligned_size[0]) * 4, int(aligned_size[1]) * 4)
            left, top, right, bottom = crop
            if (
                left < 0 or top < 0 or right > aligned_physical[0] or bottom > aligned_physical[1]
                or right <= left or bottom <= top
                or [right - left, bottom - top] != physical
            ):
                raise InterpolationError(f"crop runtime aligné invalide : {index}")
            aligned_path = plan.spatial_manifest.parent / aligned_rgba
            if (
                not aligned_path.is_file()
                or workflow.sha256_file(aligned_path) != aligned_digest.upper()
            ):
                raise InterpolationError(f"canevas aligné modifié ou absent : {index}")
            try:
                with Image.open(aligned_path) as aligned_image:
                    if aligned_image.size != aligned_physical:
                        raise InterpolationError(
                            f"dimensions du canevas aligné invalides : {index}"
                        )
            except (OSError, ValueError) as exc:
                raise InterpolationError(f"canevas aligné illisible : {index}") from exc
            aligned_sizes.add(aligned_physical)
            aligned_frame_count += 1
    if len(sizes) == 1:
        manifest["_interpolation_input"] = "native"
        manifest["_interpolation_physical"] = next(iter(sizes))
    elif aligned_frame_count == len(frames) and len(aligned_sizes) == 1:
        manifest["_interpolation_input"] = "aligned"
        manifest["_interpolation_physical"] = next(iter(aligned_sizes))
    else:
        raise InterpolationError(
            "interpolation d'effet : géométrie x4 variable sans canevas aligné uniforme"
        )
    source = manifest.get("source")
    if not isinstance(source, Mapping) or not isinstance(source.get("frame_manifest"), str):
        raise InterpolationError("provenance des frames x1 absente")
    frames_manifest = plan.root / str(source["frame_manifest"])
    if (
        not frames_manifest.is_file()
        or workflow.sha256_file(frames_manifest)
        != str(source.get("frame_manifest_sha256", "")).upper()
    ):
        raise InterpolationError("manifeste x1 parent modifié ou absent")
    x1 = load_json(frames_manifest)
    cycles = x1.get("cycles")
    if not isinstance(cycles, list) or len(cycles) != 1:
        raise InterpolationError("interpolation d'effet : un seul cycle BAM est requis")
    slots = cycles[0].get("frame_indices") if isinstance(cycles[0], Mapping) else None
    if (
        not isinstance(slots, list)
        or not slots
        or any(type(slot) is not int or slot < 0 or slot >= len(frames) for slot in slots)
    ):
        raise InterpolationError("cycle BAM source invalide")
    manifest["_source_frames_manifest"] = frames_manifest
    manifest["_source_cycle"] = [int(slot) for slot in slots]
    return manifest


def build_plan(
    root: Path,
    raw_resref: str,
    spatial_run: str,
    raw_run_id: str | None,
    recipe_id: str,
    native_fps: int,
    target_fps: int,
    tvai_ffmpeg: Path,
    tvai_model_dir: Path,
    model: str,
    device: str,
) -> InterpolationPlan:
    if native_fps <= 0 or target_fps <= native_fps or target_fps % native_fps:
        raise InterpolationError("cadences invalides : cible doit être un multiple strict du natif")
    if not recipe_id.strip() or not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", recipe_id.strip()):
        raise InterpolationError("recipe-id invalide")
    try:
        resref, asset, _processing, resource_root = workflow.load_asset(root, raw_resref)
        parent_run = workflow.validate_run_id(spatial_run)
    except workflow.WorkflowError as exc:
        raise InterpolationError(str(exc)) from exc
    verification = workflow.verify_run_descriptor(
        root, resource_root, resref, parent_run, stage="spatial"
    )
    if not verification.get("ok"):
        raise InterpolationError("parent spatial invalide : " + "; ".join(verification["errors"]))
    parent_outputs = [item for item in verification["outputs"] if item.get("role") == "spatial-manifest"]
    if len(parent_outputs) != 1:
        raise InterpolationError("parent spatial sans manifeste unique")
    spatial_manifest = root / str(parent_outputs[0]["path"])
    run_id = (
        workflow.validate_run_id(raw_run_id)
        if raw_run_id
        else workflow.next_run_id(resource_root, resref, "interpolation", recipe_id)
    )
    plan = InterpolationPlan(
        root=root,
        resref=resref,
        asset=asset,
        spatial_run=parent_run,
        run_id=run_id,
        run_root=resource_root / "runs" / run_id,
        parent_descriptor=resource_root / "runs" / parent_run / "run.json",
        parent_output=parent_outputs[0],
        spatial_manifest=spatial_manifest,
        recipe_id=recipe_id.strip(),
        native_fps=native_fps,
        target_fps=target_fps,
        tvai_ffmpeg=tvai_ffmpeg.resolve(),
        tvai_model_dir=tvai_model_dir.resolve(),
        model=model,
        device=device,
    )
    validate_spatial_manifest(plan)
    if not plan.tvai_ffmpeg.is_file() or not plan.tvai_model_dir.is_dir():
        raise InterpolationError("installation Topaz Video AI incomplète")
    if not (plan.tvai_model_dir / f"{model}.json").is_file():
        raise InterpolationError(f"modèle Topaz absent : {model}")
    return plan


def recipe_snapshot(plan: InterpolationPlan) -> dict[str, Any]:
    return {
        "schema": RECIPE_SCHEMA,
        "recipe_id": plan.recipe_id,
        "pipeline_id": PIPELINE_ID,
        "scale": 4,
        "timing": {
            "native_fps": [plan.native_fps, 1],
            "target_fps": [plan.target_fps, 1],
            "loop_closed": True,
        },
        "rgb_policy": "Topaz Apollo receives x4 RGB only; source alpha is never model-generated",
        "alpha_policy": "nearest deterministic temporal phase from enlarged spatial source alpha",
        "topaz": {
            "ffmpeg": workflow.relative_path(plan.root, plan.tvai_ffmpeg)
            if plan.tvai_ffmpeg.is_relative_to(plan.root)
            else str(plan.tvai_ffmpeg),
            "version": topaz_version(plan.tvai_ffmpeg),
            "model": plan.model,
            "device": plan.device,
            "replace_duplicate_threshold": REPLACE_DUPLICATE_THRESHOLD,
        },
        "tools": [
            {
                "path": workflow.relative_path(plan.root, Path(__file__)),
                "sha256": workflow.sha256_file(Path(__file__)),
            }
        ],
    }


def descriptor(
    plan: InterpolationPlan,
    recipe: Mapping[str, Any],
    *,
    status: str,
    sealed: bool,
    created_at: str,
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
            "version": "effect-interpolation-runner.v1",
            "recipe_path": workflow.relative_path(plan.root, plan.recipe_path),
            "recipe_sha256": workflow.sha256_file(plan.recipe_path),
        },
        "inputs": [{**dict(plan.parent_output), "role": "parent-spatial-output"}],
        "outputs": [dict(item) for item in outputs],
        "provenance": {
            "created_at_utc": created_at,
            "generator": "pipeline/scripts/run_effect_interpolation.py",
            "command": [
                "run_effect_interpolation.py",
                "--resref",
                plan.resref,
                "--spatial-run",
                plan.spatial_run,
                "--run-id",
                plan.run_id,
            ],
            "parents": [plan.spatial_run],
        },
        "result": result,
    }


def reserve(plan: InterpolationPlan) -> None:
    try:
        workflow.new_run(
            plan.root, plan.resref, "interpolation", plan.recipe_id, plan.run_id, write=True
        )
    except workflow.WorkflowError as exc:
        raise InterpolationError(str(exc)) from exc


def alpha_source_slot(phase: int, source_slots: int, target_slots: int) -> int:
    return ((2 * phase * source_slots + target_slots) // (2 * target_slots)) % source_slots


def geometry_source_slot(phase: int, multiplier: int, source_slots: int) -> int:
    return min(phase // multiplier, source_slots - 1)


def execute(plan: InterpolationPlan) -> dict[str, Any]:
    if plan.run_root.exists():
        raise InterpolationError(f"run déjà présent : {plan.run_root}")
    reserve(plan)
    created_at = workflow.utc_now()
    recipe = recipe_snapshot(plan)
    write_json(plan.recipe_path, recipe)
    write_json(plan.descriptor_path, descriptor(plan, recipe, status="running", sealed=False, created_at=created_at))
    partial = plan.interpolation_root.with_name(plan.interpolation_root.name + ".partial")
    try:
        spatial = validate_spatial_manifest(plan)
        frames = spatial["frames"]
        source_cycle = spatial["_source_cycle"]
        multiplier = plan.target_fps // plan.native_fps
        target_count = len(source_cycle) * multiplier
        input_physical = tuple(int(value) for value in spatial["_interpolation_physical"])
        input_kind = str(spatial["_interpolation_input"])
        input_root = partial / "input-rgb"
        raw_root = partial / "apollo-raw"
        output_root = partial / "frames-rgba"
        for directory in (input_root, raw_root, output_root):
            directory.mkdir(parents=True)
        for slot, source_index in enumerate(source_cycle):
            source = frames[source_index]
            raw_name = "aligned_rgba_xn" if input_kind == "aligned" else "raw_rgba_xn"
            raw_path = plan.spatial_manifest.parent / str(source[raw_name])
            if input_kind == "aligned":
                with Image.open(raw_path) as aligned_image:
                    rgba = aligned_image.convert("RGBA")
            else:
                rgba = Image.frombytes("RGBA", input_physical, raw_path.read_bytes())
            rgba.convert("RGB").save(input_root / f"in_{slot:03d}.png", format="PNG", compress_level=9)
        shutil.copyfile(input_root / "in_000.png", input_root / f"in_{len(source_cycle):03d}.png")

        command = [
            str(plan.tvai_ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", rate_text(plan.native_fps),
            "-i", str(input_root / "in_%03d.png"),
            "-vf",
            f"tvai_fi=model={plan.model}:fps={rate_text(plan.target_fps)}:rdt={REPLACE_DUPLICATE_THRESHOLD}:device={plan.device}",
            "-pix_fmt", "rgb24", str(raw_root / "out_%04d.png"),
        ]
        environment = dict(os.environ)
        environment["TVAI_MODEL_DIR"] = str(plan.tvai_model_dir)
        environment["TVAI_MODEL_DATA_DIR"] = str(plan.tvai_model_dir)
        completed = subprocess.run(command, capture_output=True, text=True, env=environment)
        if completed.returncode != 0:
            raise InterpolationError(f"Apollo a échoué : {(completed.stderr or '').strip()[:800]}")
        produced = parse_numbered_pngs(raw_root)
        if len(produced) not in {target_count, target_count + 1}:
            raise InterpolationError(
                f"Apollo a produit {len(produced)} frames, attendu {target_count} ou {target_count + 1}"
            )
        records: list[dict[str, Any]] = []
        for phase, rgb_path in enumerate(produced[:target_count]):
            with Image.open(rgb_path) as source_rgb:
                rgb = source_rgb.convert("RGB")
            if rgb.size != input_physical:
                raise InterpolationError(f"Apollo : dimensions inattendues {rgb.size} à la phase {phase}")
            source_slot = alpha_source_slot(phase, len(source_cycle), target_count)
            source_index = source_cycle[source_slot]
            alpha_source = frames[source_index]
            geometry_slot = geometry_source_slot(phase, multiplier, len(source_cycle))
            geometry_index = source_cycle[geometry_slot]
            geometry_source = frames[geometry_index]
            logical = [int(value) for value in geometry_source["logical_size_x1"]]
            physical = tuple(int(value) for value in geometry_source["physical_size_xn"])
            if input_kind == "aligned":
                crop = tuple(int(value) for value in geometry_source["runtime_crop_box_xn"])
                rgb = rgb.crop(crop)
                alpha_path = plan.spatial_manifest.parent / str(alpha_source["aligned_rgba_xn"])
                with Image.open(alpha_path) as aligned_image:
                    alpha = aligned_image.convert("RGBA").getchannel("A").crop(crop)
            else:
                alpha_path = plan.spatial_manifest.parent / str(alpha_source["alpha_xn"])
                with Image.open(alpha_path) as alpha_image:
                    alpha = alpha_image.convert("L")
            if rgb.size != physical or alpha.size != physical:
                raise InterpolationError(f"alpha source : dimensions inattendues à la phase {phase}")
            rgba = Image.merge("RGBA", (*rgb.split(), alpha))
            png = output_root / f"frame_{phase:03d}.png"
            raw = output_root / f"frame_{phase:03d}.rgba"
            rgba.save(png, format="PNG", compress_level=9)
            raw.write_bytes(rgba.tobytes())
            records.append(
                {
                    "frame": phase,
                    "apollo_rgb": f"apollo-raw/{rgb_path.name}",
                    "apollo_rgb_sha256": workflow.sha256_file(rgb_path),
                    "alpha_source_frame": source_index,
                    "alpha_phase_source": "deterministic-nearest-source-slot",
                    "geometry_source_frame": geometry_index,
                    "logical_size_x1": logical,
                    "physical_size_x4": list(physical),
                    "rgba_x4": f"frames-rgba/{png.name}",
                    "rgba_x4_sha256": workflow.sha256_file(png),
                    "raw_rgba_x4": f"frames-rgba/{raw.name}",
                    "raw_rgba_x4_sha256": workflow.sha256_file(raw),
                    "bytes": raw.stat().st_size,
                }
            )
        native_indices = [slot * multiplier for slot in range(len(source_cycle))]
        manifest = {
            "schema": INTERPOLATION_SCHEMA,
            "status": "completed",
            "created_utc": workflow.utc_now(),
            "resref": plan.resref,
            "scale": 4,
            "parent": {
                "spatial_run": plan.spatial_run,
                "run_descriptor": workflow.relative_path(plan.root, plan.parent_descriptor),
                "run_descriptor_sha256": workflow.sha256_file(plan.parent_descriptor),
                "spatial_manifest": workflow.relative_path(plan.root, plan.spatial_manifest),
                "spatial_manifest_sha256": workflow.sha256_file(plan.spatial_manifest),
            },
            "timing": {
                "native_fps": [plan.native_fps, 1],
                "target_fps": [plan.target_fps, 1],
                "native_cycle_slots": len(source_cycle),
                "timeline_phase_count": target_count,
                "native_frame_indices": native_indices,
                "timeline_frame_indices": list(range(target_count)),
                "loop_closed": True,
            },
            "topaz": {
                "ffmpeg": str(plan.tvai_ffmpeg),
                "version": recipe["topaz"]["version"],
                "model": plan.model,
                "device": plan.device,
                "replace_duplicate_threshold": REPLACE_DUPLICATE_THRESHOLD,
                "raw_frame_count": len(produced),
            },
            "frames": records,
        }
        write_json(partial / "manifest.json", manifest)
        partial.replace(plan.interpolation_root)
        outputs = [evidence(plan.root, "interpolation-manifest", plan.interpolation_root / "manifest.json")]
        write_json(
            plan.descriptor_path,
            descriptor(plan, recipe, status="completed", sealed=True, created_at=created_at, outputs=outputs),
        )
        return {
            "command": "run-effect-interpolation",
            "resref": plan.resref,
            "run_id": plan.run_id,
            "frame_count": target_count,
            "run_descriptor": workflow.relative_path(plan.root, plan.descriptor_path),
            "run_descriptor_sha256": workflow.sha256_file(plan.descriptor_path),
            "next": f"effect_workflow.py register-run --resref {plan.resref} --stage interpolation --run-id {plan.run_id}",
        }
    except (OSError, InterpolationError, subprocess.SubprocessError) as exc:
        write_json(
            plan.descriptor_path,
            descriptor(plan, recipe, status="failed", sealed=False, created_at=created_at, notes=str(exc)),
        )
        raise InterpolationError(str(exc)) from exc


def plan_payload(plan: InterpolationPlan) -> dict[str, Any]:
    spatial = validate_spatial_manifest(plan)
    native_slots = len(spatial["_source_cycle"])
    return {
        "command": "run-effect-interpolation",
        "write": False,
        "resref": plan.resref,
        "spatial_run": plan.spatial_run,
        "run_id": plan.run_id,
        "run_directory": workflow.relative_path(plan.root, plan.run_root),
        "pipeline_id": PIPELINE_ID,
        "timing": {
            "native_fps": plan.native_fps,
            "target_fps": plan.target_fps,
            "native_cycle_slots": native_slots,
            "timeline_phase_count": native_slots * plan.target_fps // plan.native_fps,
        },
        "authority_mutation": "none; register-run is separate",
        "release_mutation": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--spatial-run", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--recipe-id", default="apollo8-rgb-nearest-alpha")
    parser.add_argument("--native-fps", type=int, default=15)
    parser.add_argument("--target-fps", type=int, default=30)
    parser.add_argument("--tvai-ffmpeg", type=Path, default=DEFAULT_TVAI_FFMPEG)
    parser.add_argument("--tvai-model-dir", type=Path, default=DEFAULT_TVAI_MODEL_DIR)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", default="-2")
    parser.add_argument("--run", action="store_true", help="produire le run, sinon plan seulement")
    args = parser.parse_args(argv)
    try:
        plan = build_plan(
            args.workspace_root.resolve(), args.resref, args.spatial_run, args.run_id,
            args.recipe_id, args.native_fps, args.target_fps, args.tvai_ffmpeg,
            args.tvai_model_dir, args.model, args.device,
        )
        result = execute(plan) if args.run else plan_payload(plan)
    except (InterpolationError, workflow.WorkflowError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
