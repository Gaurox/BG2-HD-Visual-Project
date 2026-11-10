"""Prototype Topaz 15 -> 30 fps. Non canonique; validation visuelle requise."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "pipeline" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from workspace_paths import get_path  # noqa: E402


SOURCE = (
    ROOT
    / "video"
    / "runs"
    / "flythr03-method-prototype-20260831"
    / "FLYTHR03-1080p-seedvr2-3b-int8-full-temporal.mp4"
)
OUTPUT_ROOT = Path(__file__).resolve().parent
TVAI_FFMPEG = get_path("topaz_video_ffmpeg")
MODEL_DIR = get_path("topaz_video_models")
TARGET_FPS = "30"
VARIANTS = (
    {"id": "01-apollo-v8-rdt001", "model": "apo-8", "rdt": 0.01},
    {"id": "02-apollo-v8-rdt010", "model": "apo-8", "rdt": 0.10},
    {"id": "03-chronos-v2-rdt005", "model": "chr-2", "rdt": 0.05},
    {"id": "04-chronos-fast-v3-rdt005", "model": "chf-3", "rdt": 0.05},
    {"id": "05-aion-v1-rdt005", "model": "aion-1", "rdt": 0.05},
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, env=environment, check=False)


def probe(path: Path) -> dict[str, Any]:
    completed = run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_name,width,height,pix_fmt,avg_frame_rate,nb_read_frames,field_order,color_space,color_transfer,color_primaries:format=duration,size",
        "-of", "json", str(path),
    ])
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip())
    payload = json.loads(completed.stdout)
    stream = payload["streams"][0]
    return {
        "codec": stream.get("codec_name"),
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "pix_fmt": stream.get("pix_fmt"),
        "frame_rate": stream.get("avg_frame_rate"),
        "decoded_frames": int(stream["nb_read_frames"]),
        "field_order": stream.get("field_order"),
        "color_space": stream.get("color_space"),
        "color_transfer": stream.get("color_transfer"),
        "color_primaries": stream.get("color_primaries"),
        "duration_seconds": float(payload["format"]["duration"]),
        "bytes": int(payload["format"]["size"]),
    }


def frame_hashes(path: Path) -> list[str]:
    completed = run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-f", "framemd5", "-",
    ])
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip())
    return [
        line.rsplit(",", 1)[-1].strip()
        for line in completed.stdout.splitlines()
        if line and not line.startswith("#")
    ]


def exact_duplicate_indices(path: Path) -> list[int]:
    hashes = frame_hashes(path)
    retained: str | None = None
    duplicates: list[int] = []
    for index, digest in enumerate(hashes):
        if digest == retained:
            duplicates.append(index)
        else:
            retained = digest
    return duplicates


def exact_adjacent_duplicates(path: Path) -> int:
    return len(exact_duplicate_indices(path))


def prores_options() -> list[str]:
    return [
        "-fps_mode", "passthrough", "-c:v", "prores_ks", "-profile:v", "3",
        "-vendor", "apl0", "-pix_fmt", "yuv422p10le",
        "-color_primaries", "bt709", "-color_trc", "iec61966-2-1",
        "-colorspace", "bt709", "-movflags", "+faststart",
    ]


def remove_exact_duplicates(path: Path) -> int:
    duplicates = exact_duplicate_indices(path)
    if not duplicates:
        return 0
    expression = "+".join(f"eq(n,{index})" for index in duplicates)
    filter_text = f"select='not({expression})',setpts=N/(30*TB)"
    temporary = path.with_suffix(".dedupe.mov")
    completed = run([
        str(TVAI_FFMPEG), "-hide_banner", "-nostdin", "-y", "-i", str(path),
        "-map", "0:v:0", "-an", "-vf", filter_text, *prores_options(), str(temporary),
    ])
    if completed.returncode:
        raise RuntimeError(f"suppression des doublons échouée: {completed.stderr.strip()[:800]}")
    temporary.replace(path)
    remaining = exact_adjacent_duplicates(path)
    if remaining:
        raise RuntimeError(f"doublons exacts résiduels après post-traitement: {remaining}")
    return len(duplicates)


def postprocess_existing() -> int:
    report_path = OUTPUT_ROOT / "trials.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_duration = float(report["source"]["probe"]["duration_seconds"])
    for variant in report["variants"]:
        destination = OUTPUT_ROOT / variant["output"]
        before = probe(destination)
        before_duplicates = exact_adjacent_duplicates(destination)
        removed = remove_exact_duplicates(destination)
        after = probe(destination)
        variant["post_topaz_probe"] = before
        variant["post_topaz_adjacent_exact_duplicates"] = before_duplicates
        variant["exact_duplicates_removed_by_postpass"] = removed
        variant["probe"] = after
        variant["frame_delta_from_nominal_522"] = after["decoded_frames"] - 522
        variant["duration_delta_seconds"] = round(after["duration_seconds"] - source_duration, 6)
        variant["adjacent_exact_duplicates"] = exact_adjacent_duplicates(destination)
        variant["sha256"] = sha256_file(destination)
        print(f"deduped {variant['id']}: {removed} removed", flush=True)
    report["contract"]["exact_duplicate_postpass"] = (
        "decoded-frame hash; remove repeated adjacent frames; setpts CFR 30; ProRes 422 HQ"
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


def main() -> int:
    if not SOURCE.is_file():
        raise RuntimeError(f"source absente: {SOURCE}")
    if not TVAI_FFMPEG.is_file() or not MODEL_DIR.is_dir():
        raise RuntimeError("installation Topaz Video AI incomplète")
    source_probe = probe(SOURCE)
    if (
        source_probe["width"], source_probe["height"], source_probe["frame_rate"]
    ) != (1920, 1080, "15/1"):
        raise RuntimeError(f"source incompatible: {source_probe}")

    environment = dict(os.environ)
    environment["TVAI_MODEL_DIR"] = str(MODEL_DIR)
    environment["TVAI_MODEL_DATA_DIR"] = str(MODEL_DIR)
    results: list[dict[str, Any]] = []
    for variant in VARIANTS:
        model = str(variant["model"])
        if not (MODEL_DIR / f"{model}.json").is_file():
            raise RuntimeError(f"modèle Topaz absent: {model}")
        destination = OUTPUT_ROOT / f"FLYTHR03-30fps-{variant['id']}.mov"
        partial = destination.with_suffix(".partial.mov")
        log_path = OUTPUT_ROOT / f"{variant['id']}.log"
        topaz_filter = (
            f"tvai_fi=model={model}:fps={TARGET_FPS}:rdt={variant['rdt']}"
            ":device=0:instances=0:download=1:vram=0.9"
        )
        filter_text = topaz_filter + ",setpts=N/(30*TB)"
        command = [
            str(TVAI_FFMPEG), "-hide_banner", "-nostdin", "-y",
            "-i", str(SOURCE), "-map", "0:v:0", "-an", "-vf", filter_text,
            *prores_options(), str(partial),
        ]
        started = time.monotonic()
        completed = run(command, environment=environment)
        elapsed = time.monotonic() - started
        log_path.write_text(
            "$ " + subprocess.list2cmdline(command) + "\n\n"
            + completed.stdout + "\n" + completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode:
            raise RuntimeError(f"{variant['id']}: Topaz a échoué; voir {log_path}")
        post_topaz_probe = probe(partial)
        post_topaz_duplicates = exact_adjacent_duplicates(partial)
        partial.replace(destination)
        removed_duplicates = remove_exact_duplicates(destination)
        output_probe = probe(destination)
        if (
            output_probe["width"], output_probe["height"], output_probe["frame_rate"]
        ) != (1920, 1080, "30/1"):
            raise RuntimeError(f"{variant['id']}: sortie incompatible: {output_probe}")
        results.append({
            **variant,
            "replace_duplicate_frames": True,
            "filter": filter_text,
            "output": destination.name,
            "sha256": sha256_file(destination),
            "elapsed_seconds": round(elapsed, 3),
            "post_topaz_probe": post_topaz_probe,
            "post_topaz_adjacent_exact_duplicates": post_topaz_duplicates,
            "exact_duplicates_removed_by_postpass": removed_duplicates,
            "probe": output_probe,
            "frame_delta_from_nominal_522": output_probe["decoded_frames"] - 522,
            "duration_delta_seconds": round(
                output_probe["duration_seconds"] - source_probe["duration_seconds"], 6
            ),
            "adjacent_exact_duplicates": exact_adjacent_duplicates(destination),
            "status": "completed",
        })
        print(f"completed {variant['id']}: {elapsed:.1f}s", flush=True)

    report = {
        "schema": "bg2-video-interpolation-topaz-trials-v1",
        "status": "prototype-pending-visual-selection",
        "source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(SOURCE),
            "probe": source_probe,
            "adjacent_exact_duplicates": exact_adjacent_duplicates(SOURCE),
        },
        "contract": {
            "target_fps": "30/1",
            "nominal_frame_count_without_duplicate_removal": 522,
            "duration": "measured per variant; positive rdt may shorten the Topaz CLI output",
            "replace_duplicate_frames": "Topaz tvai_fi rdt > 0",
            "cfr_normalization": "setpts=N/(30*TB); no frame added or removed after Topaz",
            "exact_duplicate_postpass": (
                "decoded-frame hash; remove repeated adjacent frames; setpts CFR 30; ProRes 422 HQ"
            ),
            "audio": "excluded; stage non-authoritative",
            "encoding": "ProRes 422 HQ test intermédiaire; non final",
            "qa": "pending-user-selection",
        },
        "variants": results,
    }
    (OUTPUT_ROOT / "trials.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--postprocess-existing", action="store_true")
    arguments = parser.parse_args()
    raise SystemExit(postprocess_existing() if arguments.postprocess_existing else main())
