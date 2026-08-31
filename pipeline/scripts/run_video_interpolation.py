"""Run the validated Topaz Apollo 8 video interpolation stage only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
VIDEO_ROOT = ROOT / "video"
DEFAULT_RECIPE = (
    ROOT / "pipeline" / "topaz" / "recipes" / "Video-Interpolation-Apollo8-30fps-v1.json"
)
PIPELINE_ID = "topaz-video-apollo8-30fps-v1"
RECIPE_SHA256 = "e707dd23cb5fe789b2d0ae14de53392ab107c51b54a986771015e106abb47d5e"
SOURCE_SIZE = (1920, 1080)
SOURCE_FPS = Fraction(15, 1)
TARGET_FPS = Fraction(30, 1)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def run_checked(
    command: list[str], *, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command, capture_output=True, text=True, env=environment, check=False
    )
    if completed.returncode:
        raise RuntimeError(
            f"commande échouée ({completed.returncode}): "
            + (completed.stderr or completed.stdout).strip()[:1200]
        )
    return completed


def load_recipe(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"recette absente: {path}")
    actual_hash = sha256_file(path)
    if actual_hash.lower() != RECIPE_SHA256:
        raise RuntimeError(
            f"recette non approuvée: SHA-256 {actual_hash}, attendu {RECIPE_SHA256}"
        )
    recipe = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema": "bg2-video-interpolation-recipe-v1",
        "id": PIPELINE_ID,
        "model": "apo-8",
        "target_fps": "30/1",
        "rdt": -0.01,
        "approximate_duplicate_detection": False,
        "exact_duplicate_postpass": True,
        "audio": "excluded",
        "codec": "prores_ks",
        "profile": 3,
        "pixel_format": "yuv422p10le",
    }
    actual = {
        "schema": recipe.get("schema"),
        "id": recipe.get("id"),
        "model": recipe.get("topaz", {}).get("model"),
        "target_fps": recipe.get("topaz", {}).get("target_fps"),
        "rdt": recipe.get("topaz", {}).get("replace_duplicate_threshold"),
        "approximate_duplicate_detection": recipe.get("topaz", {}).get(
            "approximate_duplicate_detection"
        ),
        "exact_duplicate_postpass": recipe.get("timeline", {})
        .get("exact_duplicate_postpass", {})
        .get("enabled"),
        "audio": recipe.get("timeline", {}).get("audio"),
        "codec": recipe.get("technical_output", {}).get("codec"),
        "profile": recipe.get("technical_output", {}).get("profile"),
        "pixel_format": recipe.get("technical_output", {}).get("pixel_format"),
    }
    differences = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if differences:
        raise RuntimeError(
            "recette incompatible: " + json.dumps(differences, ensure_ascii=False)
        )
    return recipe


def file_evidence(role: str, path: Path) -> dict[str, Any]:
    return {
        "role": role,
        "path": repo_path(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def load_upscale_run(run_id: str) -> dict[str, Any]:
    matches = sorted(VIDEO_ROOT.glob(f"*/runs/{run_id}/run.json"))
    if len(matches) != 1:
        raise RuntimeError(f"run d'upscale absent ou ambigu: {run_id}")
    descriptor_path = matches[0]
    run_dir = descriptor_path.parent
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    result = descriptor.get("result") or {}
    if (
        descriptor.get("domain") != "videos"
        or descriptor.get("run_id") != run_id
        or result.get("status") != "completed"
        or result.get("sealed") is not True
    ):
        raise RuntimeError("run d'upscale non terminé, non scellé ou incompatible")
    outputs = [
        item
        for item in descriptor.get("outputs") or []
        if item.get("role") == "upscale-technical-video"
    ]
    if len(outputs) != 1:
        raise RuntimeError("une unique sortie upscale-technical-video est requise")
    evidence = outputs[0]
    source = (ROOT / str(evidence["path"])).resolve()
    if not source.is_file():
        legacy_prefix = f"video/runs/{run_id}/"
        path_text = str(evidence["path"]).replace("\\", "/")
        if path_text.startswith(legacy_prefix):
            source = (run_dir / path_text[len(legacy_prefix):]).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():
        raise RuntimeError("sortie du run d'upscale absente ou hors workspace")
    if (
        source.stat().st_size != evidence.get("bytes")
        or sha256_file(source).lower() != str(evidence.get("sha256", "")).lower()
    ):
        raise RuntimeError("sortie du run d'upscale différente de sa preuve scellée")
    asset_ids = descriptor.get("asset_ids") or []
    if len(asset_ids) != 1:
        raise RuntimeError("un seul asset vidéo est requis")
    return {
        "descriptor": descriptor,
        "descriptor_path": descriptor_path,
        "descriptor_sha256": sha256_file(descriptor_path),
        "source": source,
        "source_evidence": evidence,
        "asset_id": asset_ids[0],
        "asset_dir": run_dir.parent.parent,
    }


def probe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    completed = run_checked([
        ffprobe,
        "-v",
        "error",
        "-count_frames",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ])
    payload = json.loads(completed.stdout)
    video = next(
        (item for item in payload.get("streams", []) if item.get("codec_type") == "video"),
        None,
    )
    if video is None:
        raise RuntimeError(f"flux vidéo absent: {path}")
    audio = next(
        (item for item in payload.get("streams", []) if item.get("codec_type") == "audio"),
        None,
    )
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "frame_rate": video["avg_frame_rate"],
        "frame_count": int(video["nb_read_frames"]),
        "field_order": video.get("field_order", "unknown"),
        "video_codec": video.get("codec_name", ""),
        "pixel_format": video.get("pix_fmt", ""),
        "audio_codec": audio.get("codec_name", "") if audio else "",
        "duration": float(payload.get("format", {}).get("duration", 0.0)),
    }


def validate_source_probe(probe: dict[str, Any]) -> None:
    if (probe["width"], probe["height"]) != SOURCE_SIZE:
        raise RuntimeError("entrée interpolation différente de 1920x1080")
    if Fraction(probe["frame_rate"]) != SOURCE_FPS:
        raise RuntimeError("entrée interpolation différente de 15 fps")
    if probe["field_order"] not in {"progressive", "unknown"}:
        raise RuntimeError("entrée interpolation entrelacée")


def frame_hashes(path: Path, ffmpeg: Path) -> list[str]:
    completed = run_checked([
        str(ffmpeg),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-f",
        "framemd5",
        "-",
    ])
    return [
        line.rsplit(",", 1)[-1].strip()
        for line in completed.stdout.splitlines()
        if line and not line.startswith("#")
    ]


def exact_duplicate_indices(hashes: list[str]) -> list[int]:
    retained: str | None = None
    duplicates: list[int] = []
    for index, digest in enumerate(hashes):
        if digest == retained:
            duplicates.append(index)
        else:
            retained = digest
    return duplicates


def prores_options(recipe: dict[str, Any]) -> list[str]:
    output = recipe["technical_output"]
    return [
        "-fps_mode",
        "passthrough",
        "-c:v",
        str(output["codec"]),
        "-profile:v",
        str(output["profile"]),
        "-vendor",
        "apl0",
        "-pix_fmt",
        str(output["pixel_format"]),
        "-color_primaries",
        str(output["color_primaries"]),
        "-color_trc",
        str(output["color_transfer"]),
        "-colorspace",
        str(output["color_space"]),
        "-movflags",
        "+faststart",
    ]


def topaz_filter(recipe: dict[str, Any]) -> str:
    topaz = recipe["topaz"]
    return (
        f"tvai_fi=model={topaz['model']}:fps=30"
        f":slowmo={topaz['slowmo']}:rdt={topaz['replace_duplicate_threshold']}"
        f":device={topaz['device']}:instances={topaz['instances']}"
        f":download={int(topaz['download'])}:vram={topaz['vram']}"
        ",setpts=N/(30*TB)"
    )


def run_topaz(
    source: Path,
    destination: Path,
    *,
    recipe: dict[str, Any],
    ffmpeg: Path,
    model_dir: Path,
    log_path: Path,
) -> None:
    environment = dict(os.environ)
    environment["TVAI_MODEL_DIR"] = str(model_dir)
    environment["TVAI_MODEL_DATA_DIR"] = str(model_dir)
    command = [
        str(ffmpeg),
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        topaz_filter(recipe),
        *prores_options(recipe),
        str(destination),
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, env=environment, check=False
    )
    log_path.write_text(
        "$ " + subprocess.list2cmdline(command) + "\n\n"
        + completed.stdout
        + "\n"
        + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode:
        raise RuntimeError(f"Topaz a échoué; voir {repo_path(log_path)}")


def remove_exact_duplicates(
    source: Path,
    destination: Path,
    *,
    duplicate_indices: list[int],
    filter_path: Path,
    recipe: dict[str, Any],
    ffmpeg: Path,
) -> None:
    expression = "+".join(f"eq(n,{index})" for index in duplicate_indices)
    filter_path.write_text(
        f"select='not({expression})',setpts=N/(30*TB)\n", encoding="utf-8"
    )
    run_checked([
        str(ffmpeg),
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-filter_script:v",
        str(filter_path),
        *prores_options(recipe),
        str(destination),
    ])


def validate_output_probe(
    source: dict[str, Any],
    topaz: dict[str, Any],
    output: dict[str, Any],
    duplicates_removed: int,
) -> dict[str, bool]:
    checks = {
        "topaz_resolution_1920x1080": (topaz["width"], topaz["height"]) == SOURCE_SIZE,
        "topaz_frame_rate_30": Fraction(topaz["frame_rate"]) == TARGET_FPS,
        "topaz_interval_complete_frame_count": topaz["frame_count"]
        == source["frame_count"] * 2 - 1,
        "output_resolution_1920x1080": (output["width"], output["height"]) == SOURCE_SIZE,
        "output_frame_rate_30": Fraction(output["frame_rate"]) == TARGET_FPS,
        "output_frame_count": output["frame_count"]
        == topaz["frame_count"] - duplicates_removed,
        "output_progressive": output["field_order"] == "progressive",
        "output_audio_absent": not output["audio_codec"],
        "output_prores": output["video_codec"] == "prores",
    }
    failed = [key for key, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("sortie interpolation invalide: " + ", ".join(failed))
    return checks


def run_descriptor(
    *,
    run_id: str,
    asset_id: str,
    parent_run_id: str,
    source: Path,
    recipe: Path,
    status: str,
    sealed: bool,
    created_at: str,
    outputs: list[dict[str, Any]] | None = None,
    completed_at: str | None = None,
    notes: str = "",
) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "sealed": sealed}
    if completed_at:
        result["completed_at_utc"] = completed_at
    if notes:
        result["notes"] = notes
    return {
        "$schema": "docs/workspace-run.schema.json",
        "schema_version": 1,
        "run_id": run_id,
        "domain": "videos",
        "asset_ids": [asset_id],
        "pipeline": {
            "id": PIPELINE_ID,
            "recipe_path": repo_path(recipe),
            "recipe_sha256": RECIPE_SHA256,
            "version": "1",
        },
        "inputs": [file_evidence("upscale-technical-video", source)],
        "outputs": outputs or [],
        "provenance": {
            "created_at_utc": created_at,
            "generator": "pipeline/scripts/run_video_interpolation.py",
            "command": [
                "python",
                "pipeline/scripts/run_video_interpolation.py",
                *sys.argv[1:],
            ],
            "parents": [f"videos:{parent_run_id}"],
        },
        "result": result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upscale-run", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    parser.add_argument("--topaz-ffmpeg", type=Path, default=get_path("topaz_video_ffmpeg"))
    parser.add_argument("--model-dir", type=Path, default=get_path("topaz_video_models"))
    parser.add_argument("--ffprobe", default=shutil.which("ffprobe") or "ffprobe")
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args()
    for label in ("upscale_run", "run"):
        value = getattr(args, label)
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
            parser.error(f"--{label.replace('_', '-')} invalide")
    return args


def main() -> int:
    args = parse_args()
    recipe_path = args.recipe.resolve()
    recipe = load_recipe(recipe_path)
    parent = load_upscale_run(args.upscale_run)
    source = parent["source"]
    source_probe = probe_video(source, args.ffprobe)
    validate_source_probe(source_probe)
    ffmpeg = args.topaz_ffmpeg.resolve()
    model_dir = args.model_dir.resolve()
    model = recipe["topaz"]["model"]
    if not ffmpeg.is_file() or not (model_dir / f"{model}.json").is_file():
        raise RuntimeError("installation Topaz ou modèle Apollo 8 absent")
    plan = {
        "pipeline": PIPELINE_ID,
        "recipe": repo_path(recipe_path),
        "recipe_sha256": RECIPE_SHA256,
        "parent_run": args.upscale_run,
        "parent_descriptor_sha256": parent["descriptor_sha256"],
        "asset_id": parent["asset_id"],
        "source": file_evidence("upscale-technical-video", source),
        "source_probe": source_probe,
        "filter": topaz_filter(recipe),
        "scope": {
            "interpolation": True,
            "exact_duplicate_removal": True,
            "final_encoding": False,
            "audio_mastering": False,
            "in_game_integration": False,
            "qa": False,
            "release": False,
        },
    }
    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    run_dir = parent["asset_dir"] / "runs" / args.run
    if run_dir.exists():
        raise RuntimeError(f"run déjà présent; créer une nouvelle version: {repo_path(run_dir)}")
    run_dir.mkdir(parents=True)
    created_at = utc_now()
    request_path = run_dir / "request.json"
    descriptor_path = run_dir / "run.json"
    write_json_atomic(
        request_path,
        {"schema": "bg2-video-interpolation-request-v1", "run_id": args.run, **plan},
    )
    write_json_atomic(
        descriptor_path,
        run_descriptor(
            run_id=args.run,
            asset_id=parent["asset_id"],
            parent_run_id=args.upscale_run,
            source=source,
            recipe=recipe_path,
            status="running",
            sealed=False,
            created_at=created_at,
            notes="interpolation Apollo 8 uniquement",
        ),
    )

    output_dir = run_dir / "03_interpolation"
    output_dir.mkdir()
    topaz_output = output_dir / "video-1080p-30fps-apollo8.topaz.partial.mov"
    final_output = output_dir / "video-1080p-30fps-apollo8.mov"
    log_path = run_dir / "topaz.log"
    filter_path = run_dir / "exact-duplicate-filter.txt"
    report_path = run_dir / "interpolation-report.json"
    try:
        run_topaz(
            source,
            topaz_output,
            recipe=recipe,
            ffmpeg=ffmpeg,
            model_dir=model_dir,
            log_path=log_path,
        )
        topaz_probe = probe_video(topaz_output, args.ffprobe)
        hashes = frame_hashes(topaz_output, ffmpeg)
        duplicates = exact_duplicate_indices(hashes)
        if duplicates:
            remove_exact_duplicates(
                topaz_output,
                final_output,
                duplicate_indices=duplicates,
                filter_path=filter_path,
                recipe=recipe,
                ffmpeg=ffmpeg,
            )
            topaz_output.unlink()
        else:
            topaz_output.replace(final_output)
        output_probe = probe_video(final_output, args.ffprobe)
        residual_duplicates = exact_duplicate_indices(frame_hashes(final_output, ffmpeg))
        if residual_duplicates:
            raise RuntimeError(
                f"doublons exacts résiduels après post-traitement: {len(residual_duplicates)}"
            )
        checks = validate_output_probe(
            source_probe, topaz_probe, output_probe, len(duplicates)
        )
        report = {
            "schema": "bg2-video-interpolation-report-v1",
            "run_id": args.run,
            "asset_id": parent["asset_id"],
            "parent_run": args.upscale_run,
            "recipe_sha256": RECIPE_SHA256,
            "filter": topaz_filter(recipe),
            "source_probe": source_probe,
            "topaz_probe_before_exact_deduplication": topaz_probe,
            "exact_duplicate_indices_removed": duplicates,
            "output_probe": output_probe,
            "checks": checks,
            "scope": plan["scope"],
        }
        write_json_atomic(report_path, report)
        outputs = [
            file_evidence("interpolation-technical-video", final_output),
            file_evidence("interpolation-technical-report", report_path),
            file_evidence("topaz-log", log_path),
        ]
        if filter_path.is_file():
            outputs.append(file_evidence("exact-duplicate-filter", filter_path))
        completed_at = utc_now()
        write_json_atomic(
            descriptor_path,
            run_descriptor(
                run_id=args.run,
                asset_id=parent["asset_id"],
                parent_run_id=args.upscale_run,
                source=source,
                recipe=recipe_path,
                status="completed",
                sealed=True,
                created_at=created_at,
                outputs=outputs,
                completed_at=completed_at,
                notes=(
                    "interpolation Apollo 8 vérifiée; encodage final, audio, intégration, "
                    "QA et release non évalués"
                ),
            ),
        )
        print(str(final_output.resolve()))
        return 0
    except Exception as exc:
        write_json_atomic(
            descriptor_path,
            run_descriptor(
                run_id=args.run,
                asset_id=parent["asset_id"],
                parent_run_id=args.upscale_run,
                source=source,
                recipe=recipe_path,
                status="failed",
                sealed=True,
                created_at=created_at,
                completed_at=utc_now(),
                notes=str(exc)[:1000],
            ),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
