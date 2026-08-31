"""Run the validated SeedVR2 video upscale stage only.

Scope: canonical 1280x720 cinematics -> 1920x1080 technical video.
Excluded: interpolation, delivery encoding, in-game integration, QA and release selection.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

import requests

from workspace_paths import get_service


ROOT = Path(__file__).resolve().parents[2]
VIDEO_ROOT = ROOT / "video"
INVENTORY = VIDEO_ROOT / "index" / "resources.csv"
DEFAULT_WORKFLOW = (
    ROOT
    / "pipeline"
    / "comfyui"
    / "workflows"
    / "SeedVR-Video-BG2-3B-INT8-1080p-LAB-v2.api.json"
)
PIPELINE_ID = "seedvr2-video-3b-int8-1080p-lab-v2"
WORKFLOW_SHA256 = "b379615afd78660dce7c9283daafb0b91e40acf4832e9cfd88d2e58a0a296f4a"
TARGET_SIZE = (1920, 1080)
SOURCE_SIZE = (1280, 720)
REQUIRED_NODES = {
    "LoadVideo",
    "SaveVideo",
    "VAEEncodeTiled",
    "VAEDecodeTiled",
    "VAELoader",
    "UNETLoader",
    "KSampler",
    "SeedVR2Preprocess",
    "SeedVR2PostProcessing",
    "SeedVR2Conditioning",
    "SeedVR2TemporalChunk",
    "SeedVR2TemporalMerge",
    "GetVideoComponents",
    "CreateVideo",
    "ResizeImageMaskNode",
    "PrimitiveBoolean",
}


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
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def find_single_node(prompt: dict[str, Any], class_type: str) -> str:
    matches = [node_id for node_id, node in prompt.items() if node.get("class_type") == class_type]
    if len(matches) != 1:
        raise RuntimeError(f"workflow: un unique nœud {class_type} est requis")
    return matches[0]


def workflow_summary(prompt: dict[str, Any]) -> dict[str, Any]:
    ids = {
        kind: find_single_node(prompt, kind)
        for kind in (
            "LoadVideo",
            "SaveVideo",
            "VAEEncodeTiled",
            "VAEDecodeTiled",
            "VAELoader",
            "UNETLoader",
            "KSampler",
            "SeedVR2PostProcessing",
            "SeedVR2TemporalChunk",
            "ResizeImageMaskNode",
            "PrimitiveBoolean",
        )
    }
    encode = prompt[ids["VAEEncodeTiled"]]["inputs"]
    decode = prompt[ids["VAEDecodeTiled"]]["inputs"]
    sampler = prompt[ids["KSampler"]]["inputs"]
    resize = prompt[ids["ResizeImageMaskNode"]]["inputs"]
    chunk = prompt[ids["SeedVR2TemporalChunk"]]["inputs"]
    save = prompt[ids["SaveVideo"]]["inputs"]
    return {
        "node_ids": ids,
        "model": prompt[ids["UNETLoader"]]["inputs"]["unet_name"],
        "weight_dtype": prompt[ids["UNETLoader"]]["inputs"]["weight_dtype"],
        "vae": prompt[ids["VAELoader"]]["inputs"]["vae_name"],
        "target_width": resize["resize_type.width"],
        "target_height": resize["resize_type.height"],
        "resize_type": resize["resize_type"],
        "crop": resize["resize_type.crop"],
        "scale_method": resize["scale_method"],
        "seed": sampler["seed"],
        "steps": sampler["steps"],
        "cfg": sampler["cfg"],
        "sampler": sampler["sampler_name"],
        "scheduler": sampler["scheduler"],
        "denoise": sampler["denoise"],
        "color_correction": prompt[ids["SeedVR2PostProcessing"]]["inputs"][
            "color_correction_method"
        ],
        "vae_encode": {
            key: encode[key]
            for key in ("tile_size", "overlap", "temporal_size", "temporal_overlap")
        },
        "vae_decode": {
            key: decode[key]
            for key in ("tile_size", "overlap", "temporal_size", "temporal_overlap")
        },
        "temporal_chunking": {
            "enabled": prompt[ids["PrimitiveBoolean"]]["inputs"]["value"],
            "mode": chunk["chunking_mode"],
            "overlap": chunk["temporal_overlap"],
        },
        "technical_output": {
            key: save[key] for key in ("format", "format.codec", "codec")
        },
    }


def validate_workflow(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not path.is_file():
        raise RuntimeError(f"workflow absent : {path}")
    actual_hash = sha256_file(path)
    if actual_hash.lower() != WORKFLOW_SHA256:
        raise RuntimeError(
            f"workflow non approuvé : SHA-256 {actual_hash}, attendu {WORKFLOW_SHA256}"
        )
    prompt = json.loads(path.read_text(encoding="utf-8"))
    summary = workflow_summary(prompt)
    expected = {
        "model": "seedvr2_3b_int8_convrot.safetensors",
        "weight_dtype": "default",
        "vae": "seedvr2_ema_vae_fp16.safetensors",
        "target_width": 1920,
        "target_height": 1080,
        "resize_type": "scale dimensions",
        "crop": "center",
        "scale_method": "lanczos",
        "seed": 959948902156062,
        "steps": 1,
        "cfg": 1,
        "sampler": "euler",
        "scheduler": "simple",
        "denoise": 1,
        "color_correction": "lab",
        "vae_encode": {
            "tile_size": 512,
            "overlap": 128,
            "temporal_size": 64,
            "temporal_overlap": 8,
        },
        "vae_decode": {
            "tile_size": 512,
            "overlap": 128,
            "temporal_size": 64,
            "temporal_overlap": 8,
        },
        "temporal_chunking": {"enabled": True, "mode": "auto", "overlap": 0},
        "technical_output": {"format": "auto", "format.codec": "auto", "codec": "auto"},
    }
    differences = {
        key: {"expected": value, "actual": summary.get(key)}
        for key, value in expected.items()
        if summary.get(key) != value
    }
    if differences:
        raise RuntimeError(
            "workflow incompatible avec la recette validée : "
            + json.dumps(differences, ensure_ascii=False)
        )
    return prompt, summary


def load_asset(asset_key: str) -> dict[str, str]:
    with INVENTORY.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["asset_key"] == asset_key]
    if len(rows) != 1:
        raise RuntimeError(f"asset_key absent ou ambigu dans {repo_path(INVENTORY)} : {asset_key}")
    row = rows[0]
    if row["role"] != "cinematic":
        raise RuntimeError("recette v1 limitée aux cinématiques; tutoriels exclus")
    actual_size = (int(row["width"]), int(row["height"]))
    if actual_size != SOURCE_SIZE:
        raise RuntimeError(f"recette v1 limitée aux sources {SOURCE_SIZE[0]}x{SOURCE_SIZE[1]}")
    source = ROOT / row["extracted_path"]
    if not source.is_file():
        raise RuntimeError(f"source extraite absente : {row['extracted_path']}")
    if source.stat().st_size != int(row["source_size"]):
        raise RuntimeError(f"taille source différente de l'inventaire : {row['extracted_path']}")
    if sha256_file(source).upper() != row["source_sha256"].upper():
        raise RuntimeError(f"hash source différent de l'inventaire : {row['extracted_path']}")
    row["resolved_source"] = str(source.resolve())
    return row


def stable_video_asset_id(asset_key: str) -> str:
    token = re.sub(r"[^a-z0-9]+", "-", asset_key.lower()).strip("-")
    return f"videos:{token}"


def asset_directory(asset: dict[str, str]) -> Path:
    source = (ROOT / asset["extracted_path"]).resolve()
    directory = source.parent
    if directory.parent != VIDEO_ROOT.resolve():
        raise RuntimeError("source vidéo hors d'un dossier asset direct de video/")
    return directory


def run_ffprobe(path: Path, executable: str) -> dict[str, Any]:
    command = [
        executable,
        "-v",
        "error",
        "-count_frames",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ]
    process = subprocess.run(command, capture_output=True, text=True, check=False)
    if process.returncode:
        raise RuntimeError(f"ffprobe a échoué pour {path}: {process.stderr.strip()}")
    payload = json.loads(process.stdout)
    video = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"),
        None,
    )
    if not video:
        raise RuntimeError(f"flux vidéo absent : {path}")
    audio = next(
        (stream for stream in payload.get("streams", []) if stream.get("codec_type") == "audio"),
        None,
    )
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "frame_rate": video["avg_frame_rate"],
        "frame_count": int(video["nb_read_frames"]),
        "field_order": video.get("field_order", "unknown"),
        "video_codec": video.get("codec_name", ""),
        "audio_codec": audio.get("codec_name", "") if audio else "",
        "duration": float(payload.get("format", {}).get("duration", 0.0)),
    }


def validate_source_probe(asset: dict[str, str], probe: dict[str, Any]) -> None:
    if (probe["width"], probe["height"]) != SOURCE_SIZE:
        raise RuntimeError("dimensions réelles de la source incompatibles avec la recette v1")
    if Fraction(probe["frame_rate"]) != Fraction(asset["frame_rate"]):
        raise RuntimeError("cadence réelle différente de l'inventaire")
    if probe["field_order"] not in {"progressive", "unknown"}:
        raise RuntimeError("source entrelacée non prise en charge")


def validate_output_probe(source: dict[str, Any], output: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "resolution_1920x1080": (output["width"], output["height"]) == TARGET_SIZE,
        "frame_rate_preserved": Fraction(output["frame_rate"]) == Fraction(source["frame_rate"]),
        "frame_count_preserved": output["frame_count"] == source["frame_count"],
        "progressive": output["field_order"] == "progressive",
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError("sortie upscale invalide : " + ", ".join(failed))
    return {
        **checks,
        "interpolation": "absent: cadence et nombre d'images conservés",
        "audio": "non-authoritative: traité par une étape ultérieure",
        "delivery_encoding": "not-assessed",
    }


class ComfyClient:
    def __init__(self, server: str, poll_seconds: float, timeout_seconds: float) -> None:
        self.server = server.rstrip("/")
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.client_id = str(uuid.uuid4())

    def get_json(self, endpoint: str) -> Any:
        response = self.session.get(f"{self.server}{endpoint}", timeout=30)
        response.raise_for_status()
        return response.json()

    def preflight(self) -> dict[str, Any]:
        stats = self.get_json("/system_stats")
        queue = self.get_json("/queue")
        if queue.get("queue_running") or queue.get("queue_pending"):
            raise RuntimeError("file ComfyUI non vide; aucun job envoyé")
        info = self.get_json("/object_info")
        missing = sorted(REQUIRED_NODES - set(info))
        if missing:
            raise RuntimeError("nœuds ComfyUI absents : " + ", ".join(missing))
        return stats

    def upload_video(self, source: Path, run_id: str, asset_key: str) -> str:
        filename = re.sub(r"[^A-Za-z0-9._-]+", "-", asset_key) + ".webm"
        subfolder = f"bg2-video-upscale/{run_id}"
        with source.open("rb") as handle:
            response = self.session.post(
                f"{self.server}/upload/image",
                files={"image": (filename, handle, "video/webm")},
                data={"type": "input", "subfolder": subfolder, "overwrite": "true"},
                timeout=300,
            )
        response.raise_for_status()
        payload = response.json()
        return "/".join(part for part in (payload.get("subfolder", ""), payload["name"]) if part)

    def queue(self, prompt: dict[str, Any]) -> str:
        response = self.session.post(
            f"{self.server}/prompt",
            json={"prompt": prompt, "client_id": self.client_id},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("node_errors"):
            raise RuntimeError("prompt refusé : " + json.dumps(payload["node_errors"], ensure_ascii=False))
        return payload["prompt_id"]

    def wait(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            history = self.get_json(f"/history/{prompt_id}")
            if prompt_id in history:
                item = history[prompt_id]
                status = item.get("status", {})
                if status.get("status_str") != "success" or not status.get("completed"):
                    raise RuntimeError("échec ComfyUI : " + json.dumps(status, ensure_ascii=False))
                return item
            time.sleep(self.poll_seconds)
        raise TimeoutError(f"délai ComfyUI dépassé : {prompt_id}")

    def download(self, info: dict[str, Any], destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        with self.session.get(
            f"{self.server}/view",
            params={
                "filename": info["filename"],
                "subfolder": info.get("subfolder", ""),
                "type": info.get("type", "output"),
            },
            timeout=600,
            stream=True,
        ) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        temporary.replace(destination)


def output_info(item: dict[str, Any], save_node_id: str) -> dict[str, Any]:
    node = item.get("outputs", {}).get(save_node_id, {})
    candidates: list[dict[str, Any]] = []
    for key in ("images", "videos", "gifs"):
        candidates.extend(node.get(key) or [])
    if len(candidates) != 1:
        raise RuntimeError(f"une sortie SaveVideo attendue, trouvé : {len(candidates)}")
    return candidates[0]


def file_evidence(role: str, path: Path) -> dict[str, Any]:
    return {
        "role": role,
        "path": repo_path(path),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def run_descriptor(
    *,
    run_id: str,
    asset_id: str,
    source: Path,
    workflow: Path,
    status: str,
    sealed: bool,
    created_at: str | None = None,
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
            "recipe_path": repo_path(workflow),
            "recipe_sha256": WORKFLOW_SHA256,
            "version": "1",
        },
        "inputs": [file_evidence("canonical-source-video", source)],
        "outputs": outputs or [],
        "provenance": {
            "created_at_utc": created_at or utc_now(),
            "generator": "pipeline/scripts/run_video_upscale.py",
            "command": ["python", "pipeline/scripts/run_video_upscale.py", *sys.argv[1:]],
        },
        "result": result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-key", required=True, help="clé exacte de video/index/resources.csv")
    parser.add_argument(
        "--run", required=True, help="nouvel identifiant sous video/<asset>/runs/"
    )
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--server", default=get_service("comfyui_url"))
    parser.add_argument("--ffprobe", default=shutil.which("ffprobe") or "ffprobe")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=float, default=7200.0)
    parser.add_argument("--plan", action="store_true", help="valide et affiche sans écrire ni appeler ComfyUI")
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in {".", ".."}:
        parser.error("--run doit être un nom de dossier simple")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.run):
        parser.error("--run contient des caractères interdits")
    if args.poll_seconds <= 0 or args.timeout_seconds <= 0:
        parser.error("les délais doivent être strictement positifs")
    return args


def main() -> int:
    args = parse_args()
    workflow = args.workflow.resolve()
    prompt, summary = validate_workflow(workflow)
    asset = load_asset(args.asset_key)
    source = Path(asset["resolved_source"])
    asset_dir = asset_directory(asset)
    source_probe = run_ffprobe(source, args.ffprobe)
    validate_source_probe(asset, source_probe)
    asset_id = stable_video_asset_id(args.asset_key)
    plan = {
        "pipeline": PIPELINE_ID,
        "workflow": repo_path(workflow),
        "workflow_sha256": WORKFLOW_SHA256,
        "asset_id": asset_id,
        "source": file_evidence("canonical-source-video", source),
        "source_probe": source_probe,
        "recipe": summary,
        "scope": {
            "upscale": True,
            "interpolation": False,
            "delivery_encoding": False,
            "in_game_integration": False,
            "qa": False,
            "release": False,
        },
    }
    if args.plan:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    run_dir = asset_dir / "runs" / args.run
    if run_dir.exists():
        raise RuntimeError(f"run déjà présent; créer une nouvelle version : {repo_path(run_dir)}")
    run_dir.mkdir(parents=True)
    request_path = run_dir / "request.json"
    descriptor_path = run_dir / "run.json"
    write_json_atomic(request_path, {"schema": "bg2-video-upscale-request-v1", "run_id": args.run, **plan})
    created_at = utc_now()
    descriptor = run_descriptor(
        run_id=args.run,
        asset_id=asset_id,
        source=source,
        workflow=workflow,
        status="running",
        sealed=False,
        created_at=created_at,
        notes="upscale spatial uniquement",
    )
    write_json_atomic(descriptor_path, descriptor)

    try:
        client = ComfyClient(args.server, args.poll_seconds, args.timeout_seconds)
        system_stats = client.preflight()
        uploaded = client.upload_video(source, args.run, args.asset_key)
        runtime_prompt = copy.deepcopy(prompt)
        load_node = summary["node_ids"]["LoadVideo"]
        save_node = summary["node_ids"]["SaveVideo"]
        runtime_prompt[load_node]["inputs"]["file"] = uploaded
        runtime_prompt[save_node]["inputs"]["filename_prefix"] = (
            f"BG2_video_upscale/{args.run}/{asset['resref']}-1080p-seedvr2-3b-int8-lab"
        )
        prompt_id = client.queue(runtime_prompt)
        history = client.wait(prompt_id)
        remote_output = output_info(history, save_node)
        suffix = Path(remote_output["filename"]).suffix.lower() or ".mp4"
        output_path = (
            run_dir
            / "02_upscale"
            / f"{asset['resref']}-1080p-seedvr2-3b-int8-lab{suffix}"
        )
        client.download(remote_output, output_path)
        output_probe = run_ffprobe(output_path, args.ffprobe)
        checks = validate_output_probe(source_probe, output_probe)
        report_path = run_dir / "upscale-report.json"
        report = {
            "schema": "bg2-video-upscale-report-v1",
            "run_id": args.run,
            "asset_id": asset_id,
            "prompt_id": prompt_id,
            "workflow_sha256": WORKFLOW_SHA256,
            "source_probe": source_probe,
            "output_probe": output_probe,
            "checks": checks,
            "comfyui": {
                "version": system_stats.get("system", {}).get("comfyui_version"),
                "device_count": len(system_stats.get("devices", [])),
                "remote_output": remote_output,
            },
            "scope": plan["scope"],
        }
        write_json_atomic(report_path, report)
        outputs = [
            file_evidence("upscale-technical-video", output_path),
            file_evidence("upscale-technical-report", report_path),
        ]
        descriptor = run_descriptor(
            run_id=args.run,
            asset_id=asset_id,
            source=source,
            workflow=workflow,
            status="completed",
            sealed=True,
            created_at=created_at,
            outputs=outputs,
            completed_at=utc_now(),
            notes="upscale vérifié; QA, interpolation, encodage final et intégration non évalués",
        )
        write_json_atomic(descriptor_path, descriptor)
        print(str(output_path.resolve()))
        return 0
    except Exception as exc:
        failed = run_descriptor(
            run_id=args.run,
            asset_id=asset_id,
            source=source,
            workflow=workflow,
            status="failed",
            sealed=True,
            created_at=created_at,
            completed_at=utc_now(),
            notes=str(exc)[:1000],
        )
        write_json_atomic(descriptor_path, failed)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
