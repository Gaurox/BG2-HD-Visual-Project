"""Run an approved SeedVR ComfyUI API workflow on one full x1 map render.

The script requires a passing area preflight, uploads one original x1 render
without cutting it, queues exactly one job, downloads the exact ComfyUI output
and validates its dimensions.
For an oversized 7B image, use the orchestrator's overlap-aware ``--split-rows`` or
``--split-grid`` options. They keep tile-aligned boundaries and the validated x1 margin before
joining.

It never edits the saved ComfyUI workflow: LoadImage and SaveImage are changed
only in an in-memory copy of the API prompt.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from workspace_paths import get_service
import requests
from PIL import Image


Image.MAX_IMAGE_PIXELS = None

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAPS_DIR = PROJECT_ROOT / "maps"
TILE_KINDS = (
    "tuiles-principales", "tuiles-secondaires",
    "tuiles-principales-nuit", "tuiles-secondaires-nuit",
)
DEFAULT_WORKFLOW = (
    PROJECT_ROOT
    / "pipeline"
    / "comfyui"
    / "workflows"
    / "SeedVR-Image-BG2-Pipeline-7B.api.json"
)
APPROVED_WORKFLOW_NAME = "SeedVR-Image-BG2-Pipeline"
APPROVED_7B_SHA256 = "30dec619a4c1a3ecde076c0926a5ed8ee29d5f2ca8b4eb89a75d3b5f7811b61e"
APPROVED_3B_SHA256 = "666f38827b31d3fb9ce04046e362766ef3568fe34b1706179fcc732b53703976"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", required=True, help="code de zone, par exemple AR0602")
    parser.add_argument("--run", required=True, help="nom du run de destination")
    parser.add_argument(
        "--preflight",
        type=Path,
        required=True,
        help="manifeste JSON produit par audit_area_preflight.py pour cette zone",
    )
    parser.add_argument(
        "--tile-kind",
        choices=TILE_KINDS,
        default="tuiles-principales",
        help="rendu technique à traiter (défaut : tuiles principales)",
    )
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--server", default=get_service("comfyui_url"))
    parser.add_argument(
        "--variant",
        default="seedvr2-7b-int8-lab",
        help="libellé sûr utilisé dans les noms de sortie",
    )
    parser.add_argument(
        "--expected-workflow-sha256",
        default=APPROVED_7B_SHA256,
        help="empreinte exigée; chaîne vide pour ne pas imposer d'empreinte",
    )
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--scale",
        type=int,
        help="surcharge le multiplicateur du workflow uniquement en mémoire",
    )
    parser.add_argument(
        "--expected-scale",
        type=int,
        help="facteur déclaré attendu dans l'export API, par exemple 2 ou 4",
    )
    parser.add_argument(
        "--split-rows",
        action="store_true",
        help=(
            "découpe l'entrée en deux bandes horizontales avec recouvrement x1 de 128 px, "
            "les traite séquentiellement puis les raccorde sans fondu (SeedVR 7B haute résolution)"
        ),
    )
    parser.add_argument(
        "--split-grid",
        nargs=2,
        type=int,
        metavar=("COLUMNS", "ROWS"),
        help=(
            "découpe l'entrée en grille avec recouvrement x1 de 128 px, "
            "puis traite les morceaux séquentiellement et les assemble sans fondu"
        ),
    )
    parser.add_argument(
        "--split-margin",
        type=int,
        default=128,
        metavar="PIXELS_X1",
        help=(
            "marge x1 de recouvrement d'une grille (defaut : 128; multiple de 64). "
            "A augmenter si le controle de coutures le justifie."
        ),
    )
    parser.add_argument(
        "--reuse-split-from-run",
        help=(
            "réutilise les morceaux x1 d'une grille existante du même AREA au lieu de les recréer; "
            "leurs dimensions et leurs marges sont vérifiées avant l'inférence"
        ),
    )
    parser.add_argument(
        "--allow-blocked-test",
        action="store_true",
        help=(
            "autorise uniquement une inférence expérimentale malgré les bloqueurs du préflight; "
            "le manifeste conserve les bloqueurs et ce mode ne valide ni build ni intégration"
        ),
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="ajoute cette variante technique à un run déjà créé, sans remplacer son manifeste",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if Path(args.run).name != args.run or args.run in {".", ".."}:
        parser.error("--run doit être un nom de dossier simple")
    if Path(args.variant).name != args.variant or args.variant in {".", ".."}:
        parser.error("--variant doit être un libellé simple")
    if args.poll_seconds <= 0 or args.timeout_seconds <= 0:
        parser.error("les délais doivent être strictement positifs")
    if args.scale is not None and args.scale <= 0:
        parser.error("--scale doit être strictement positif")
    if args.expected_scale is not None and args.expected_scale <= 0:
        parser.error("--expected-scale doit être strictement positif")
    if args.split_rows and args.split_grid:
        parser.error("--split-rows et --split-grid sont exclusifs")
    if args.split_grid and (args.split_grid[0] < 1 or args.split_grid[1] < 1):
        parser.error("--split-grid exige au moins 1 colonne et 1 ligne")
    if args.split_grid and args.split_grid[0] * args.split_grid[1] < 2:
        parser.error("--split-grid exige au moins 2 morceaux au total")
    if args.split_margin < 64 or args.split_margin % 64:
        parser.error("--split-margin exige un multiple de 64, au moins 64")
    if args.split_rows and args.split_margin != 128:
        parser.error("--split-margin est reserve a --split-grid")
    if args.reuse_split_from_run and not args.split_grid:
        parser.error("--reuse-split-from-run exige --split-grid")
    if args.reuse_split_from_run and (
        Path(args.reuse_split_from_run).name != args.reuse_split_from_run
        or args.reuse_split_from_run in {".", ".."}
    ):
        parser.error("--reuse-split-from-run doit être un nom de dossier simple")
    return args


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_area(area_id: str) -> Path:
    area_id = area_id.upper()
    area_dir = MAPS_DIR / area_id
    if not area_dir.is_dir():
        raise RuntimeError(f"zone introuvable : {area_id}")
    return area_dir


def validate_preflight(path: Path, area_id: str, allow_blocked_test: bool = False) -> dict[str, Any]:
    """Refuse an inference unless qualification passed, except explicit source-only tests."""
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"préflight introuvable : {path}")
    with path.open("r", encoding="utf-8") as handle:
        preflight = json.load(handle)
    if preflight.get("schema") != "bg2-upscale-area-preflight":
        raise RuntimeError(f"préflight invalide : {path}")
    if preflight.get("area", "").upper() != area_id:
        raise RuntimeError(f"préflight {path} produit pour {preflight.get('area')}, pas pour {area_id}")
    blockers = preflight.get("blockers") or []
    if blockers and not allow_blocked_test:
        raise RuntimeError("préflight bloquant : " + "; ".join(str(blocker) for blocker in blockers))
    if not any(route.get("id") == "core-upscale" for route in preflight.get("routes", [])):
        raise RuntimeError("préflight incomplet : route core-upscale absente")
    return preflight


def find_single_node(prompt: dict[str, Any], class_type: str) -> str:
    matches = [node_id for node_id, node in prompt.items() if node.get("class_type") == class_type]
    if len(matches) != 1:
        raise RuntimeError(f"le workflow doit contenir exactement un nœud {class_type}")
    return matches[0]


def workflow_summary(prompt: dict[str, Any]) -> dict[str, Any]:
    ids = {
        class_type: find_single_node(prompt, class_type)
        for class_type in (
            "LoadImage",
            "SaveImage",
            "UNETLoader",
            "VAELoader",
            "KSampler",
            "ResizeImageMaskNode",
            "SeedVR2PostProcessing",
            "VAEEncodeTiled",
            "VAEDecodeTiled",
        )
    }
    sampler = prompt[ids["KSampler"]]["inputs"]
    resize = prompt[ids["ResizeImageMaskNode"]]["inputs"]
    post = prompt[ids["SeedVR2PostProcessing"]]["inputs"]
    encode = prompt[ids["VAEEncodeTiled"]]["inputs"]
    decode = prompt[ids["VAEDecodeTiled"]]["inputs"]
    return {
        "node_ids": ids,
        "model": prompt[ids["UNETLoader"]]["inputs"]["unet_name"],
        "weight_dtype": prompt[ids["UNETLoader"]]["inputs"].get("weight_dtype"),
        "vae": prompt[ids["VAELoader"]]["inputs"]["vae_name"],
        "scale": resize["resize_type.multiplier"],
        "scale_method": resize["scale_method"],
        "seed": sampler["seed"],
        "steps": sampler["steps"],
        "cfg": sampler["cfg"],
        "sampler": sampler["sampler_name"],
        "scheduler": sampler["scheduler"],
        "denoise": sampler["denoise"],
        "color_correction_method": post["color_correction_method"],
        "vae_encode_tiling": {
            key: encode[key]
            for key in ("tile_size", "overlap", "temporal_size", "temporal_overlap")
        },
        "vae_decode_tiling": {
            key: decode[key]
            for key in ("tile_size", "overlap", "temporal_size", "temporal_overlap")
        },
    }


def validate_approved_7b_settings(summary: dict[str, Any]) -> None:
    expected = {
        "model": "seedvr2_7b_int8_convrot.safetensors",
        "vae": "seedvr2_ema_vae_fp16.safetensors",
        "steps": 1,
        "cfg": 1,
        "sampler": "euler",
        "scheduler": "simple",
        "denoise": 1,
        "color_correction_method": "lab",
    }
    differences = {
        key: {"expected": value, "actual": summary.get(key)}
        for key, value in expected.items()
        if summary.get(key) != value
    }
    if summary.get("scale") not in (2, 4):
        differences["scale"] = {"expected": "2 ou 4", "actual": summary.get("scale")}
    if differences:
        raise RuntimeError(
            "la référence ne correspond pas aux paramètres 7B approuvés : "
            + json.dumps(differences, ensure_ascii=False)
        )


def validate_seedvr_baseline(summary: dict[str, Any]) -> None:
    expected = {
        "vae": "seedvr2_ema_vae_fp16.safetensors",
        "steps": 1,
        "cfg": 1,
        "sampler": "euler",
        "scheduler": "simple",
        "denoise": 1,
        "color_correction_method": "lab",
    }
    differences = {
        key: {"expected": value, "actual": summary.get(key)}
        for key, value in expected.items()
        if summary.get(key) != value
    }
    if differences:
        raise RuntimeError(
            "la référence ne correspond pas au preset SeedVR validé : "
            + json.dumps(differences, ensure_ascii=False)
        )


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
            raise RuntimeError("la file ComfyUI n'est pas vide; aucun job n'a été envoyé")
        return stats

    def upload(self, source: Path, subfolder: str) -> str:
        with source.open("rb") as handle:
            response = self.session.post(
                f"{self.server}/upload/image",
                files={"image": (source.name, handle, "image/png")},
                data={"type": "input", "subfolder": subfolder, "overwrite": "true"},
                timeout=120,
            )
        response.raise_for_status()
        uploaded = response.json()
        if uploaded.get("type", "input") != "input":
            raise RuntimeError(f"type d'upload inattendu : {uploaded}")
        return "/".join(part for part in (uploaded.get("subfolder", ""), uploaded["name"]) if part)

    def queue(self, prompt: dict[str, Any]) -> str:
        response = self.session.post(
            f"{self.server}/prompt",
            json={"prompt": prompt, "client_id": self.client_id},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("node_errors"):
            raise RuntimeError("ComfyUI a rejeté le prompt : " + json.dumps(payload, ensure_ascii=False))
        return payload["prompt_id"]

    def wait_history(self, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            history = self.get_json(f"/history/{prompt_id}")
            if prompt_id in history:
                item = history[prompt_id]
                status = item.get("status", {})
                if not status.get("completed") or status.get("status_str") != "success":
                    raise RuntimeError(
                        f"échec ComfyUI pour {prompt_id} : "
                        + json.dumps(status, ensure_ascii=False)
                    )
                return item
            time.sleep(self.poll_seconds)
        raise TimeoutError(f"délai dépassé pour le prompt {prompt_id}")

    def download(self, image_info: dict[str, Any], destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        with self.session.get(
            f"{self.server}/view",
            params={
                "filename": image_info["filename"],
                "subfolder": image_info.get("subfolder", ""),
                "type": image_info.get("type", "output"),
            },
            timeout=300,
            stream=True,
        ) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        temporary.replace(destination)


def source_part(run_dir: Path, area_id: str, tile_kind: str, part: int) -> Path:
    return (
        run_dir
        / tile_kind
        / "02_decoupe"
        / f"{area_id}-{tile_kind}-x1-part{part}.png"
    )


def save_png_atomic(image: Image.Image, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    image.save(temporary, format="PNG")
    temporary.replace(destination)


def prepare_row_overlap_parts(
    source: Path, run_dir: Path, tile_kind: str, scale: int, overwrite: bool
) -> tuple[list[Path], dict[str, Any]]:
    """Create the only approved 7B high-resolution split: two overlapping rows."""
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        if height % 128:
            raise RuntimeError(f"hauteur non compatible avec la coupe 7B : {height} n'est pas multiple de 128")
        cut = height // 2
        if cut % 64:
            raise RuntimeError(f"coupe 7B non alignée sur une tuile : y={cut}")
        margin = 128
        boxes = [(0, 0, width, cut + margin), (0, cut - margin, width, height)]
        parts_dir = run_dir / tile_kind / "02_decoupe"
        paths = [parts_dir / f"{source.stem}-part{index}.png" for index in (1, 2)]
        for path, box in zip(paths, boxes):
            if path.exists() and not overwrite:
                raise RuntimeError(f"découpe déjà présente (utiliser --overwrite) : {path}")
            save_png_atomic(image.crop(box), path)
    return paths, {
        "orientation": "horizontal",
        "cut_x1": cut,
        "margin_x1_per_side": 128,
        "total_overlap_x1": 256,
        "discarded_margin_scaled_per_part": margin * scale,
        "part_size_x1": [width, cut + 128],
        "part_size_scaled": [width * scale, (cut + 128) * scale],
        "assembled_size_scaled": [width * scale, height * scale],
        "assembly": "retrait des bords de recouvrement puis juxtaposition verticale, sans fondu",
    }


def assemble_row_overlap(part1: Path, part2: Path, destination: Path, scale: int) -> tuple[int, int]:
    scaled_margin = 128 * scale
    with Image.open(part1) as first_opened, Image.open(part2) as second_opened:
        first = first_opened.convert("RGB")
        second = second_opened.convert("RGB")
        if first.width != second.width:
            raise RuntimeError(f"largeurs incompatibles : {first.width} / {second.width}")
        if first.height <= scaled_margin or second.height <= scaled_margin:
            raise RuntimeError("marge de raccord supérieure à la hauteur d'une partie")
        top = first.crop((0, 0, first.width, first.height - scaled_margin))
        bottom = second.crop((0, scaled_margin, second.width, second.height))
        assembled = Image.new("RGB", (first.width, top.height + bottom.height))
        assembled.paste(top, (0, 0))
        assembled.paste(bottom, (0, top.height))
        save_png_atomic(assembled, destination)
        return assembled.size


def grid_tile_boundaries(length: int, divisions: int) -> list[int]:
    """Return near-equal, 64 px tile-aligned grid boundaries."""
    if length % 64:
        raise RuntimeError(f"dimension non alignee sur les tuiles : {length}")
    tiles, remainder = divmod(length // 64, divisions)
    if tiles == 0:
        raise RuntimeError(f"grille trop fine pour {length}px : {divisions} divisions")
    widths = [tiles + (1 if index < remainder else 0) for index in range(divisions)]
    boundaries = [0]
    for width in widths:
        boundaries.append(boundaries[-1] + width * 64)
    return boundaries


def prepare_grid_overlap_parts(
    source: Path,
    run_dir: Path,
    tile_kind: str,
    scale: int,
    columns: int,
    rows: int,
    margin: int,
    overwrite: bool,
) -> tuple[list[Path], dict[str, Any]]:
    """Create tile-aligned overlapping grid pieces for a high-resolution test."""
    with Image.open(source) as opened:
        image = opened.convert("RGB")
        width, height = image.size
        x_boundaries = grid_tile_boundaries(width, columns)
        y_boundaries = grid_tile_boundaries(height, rows)
        parts_dir = run_dir / tile_kind / "02_decoupe"
        paths: list[Path] = []
        for row in range(rows):
            for column in range(columns):
                left = 0 if column == 0 else x_boundaries[column] - margin
                top = 0 if row == 0 else y_boundaries[row] - margin
                right = width if column == columns - 1 else x_boundaries[column + 1] + margin
                bottom = height if row == rows - 1 else y_boundaries[row + 1] + margin
                path = parts_dir / f"{source.stem}-r{row + 1}c{column + 1}.png"
                if path.exists() and not overwrite:
                    raise RuntimeError(f"découpe déjà présente (utiliser --overwrite) : {path}")
                save_png_atomic(image.crop((left, top, right, bottom)), path)
                paths.append(path)
    return paths, {
        "orientation": f"grid-{columns}x{rows}",
        "core_column_widths_x1": [
            x_boundaries[index + 1] - x_boundaries[index] for index in range(columns)
        ],
        "core_row_heights_x1": [
            y_boundaries[index + 1] - y_boundaries[index] for index in range(rows)
        ],
        "margin_x1_per_internal_side": margin,
        "part_count": columns * rows,
        "discarded_margin_scaled_per_internal_side": margin * scale,
        "assembled_size_scaled": [width * scale, height * scale],
        "assembly": "retrait des marges internes de chaque morceau puis juxtaposition sur la grille, sans fondu",
    }


def reuse_grid_overlap_parts(
    source: Path,
    area_dir: Path,
    source_run: str,
    tile_kind: str,
    scale: int,
    columns: int,
    rows: int,
    margin: int,
) -> tuple[list[Path], dict[str, Any]]:
    """Validate and reuse the x1 pieces from an existing compatible grid run."""
    with Image.open(source) as opened:
        width, height = opened.size
    x_boundaries = grid_tile_boundaries(width, columns)
    y_boundaries = grid_tile_boundaries(height, rows)
    parts_dir = area_dir / "runs" / source_run / tile_kind / "02_decoupe"
    paths: list[Path] = []
    for row in range(rows):
        for column in range(columns):
            left = 0 if column == 0 else x_boundaries[column] - margin
            top = 0 if row == 0 else y_boundaries[row] - margin
            right = width if column == columns - 1 else x_boundaries[column + 1] + margin
            bottom = height if row == rows - 1 else y_boundaries[row + 1] + margin
            path = parts_dir / f"{source.stem}-r{row + 1}c{column + 1}.png"
            if not path.is_file():
                raise RuntimeError(f"morceau x1 réutilisable introuvable : {path}")
            expected_size = (right - left, bottom - top)
            if image_size(path) != expected_size:
                raise RuntimeError(
                    f"morceau x1 incompatible {path.name} : {image_size(path)}, "
                    f"attendu {expected_size[0]}x{expected_size[1]}"
                )
            paths.append(path)
    return paths, {
        "orientation": f"grid-{columns}x{rows}",
        "core_column_widths_x1": [
            x_boundaries[index + 1] - x_boundaries[index] for index in range(columns)
        ],
        "core_row_heights_x1": [
            y_boundaries[index + 1] - y_boundaries[index] for index in range(rows)
        ],
        "margin_x1_per_internal_side": margin,
        "part_count": columns * rows,
        "discarded_margin_scaled_per_internal_side": margin * scale,
        "assembled_size_scaled": [width * scale, height * scale],
        "input_parts": "reused",
        "input_parts_run": source_run,
        "assembly": "retrait des marges internes de chaque morceau puis juxtaposition sur la grille, sans fondu",
    }


def assemble_grid_overlap(
    parts: list[Path],
    destination: Path,
    source_size: tuple[int, int],
    scale: int,
    columns: int,
    rows: int,
    margin_x1: int,
) -> tuple[int, int]:
    """Reassemble overlapping grid pieces after discarding their internal margins."""
    if len(parts) != columns * rows:
        raise RuntimeError(f"grille incomplète : {len(parts)} morceaux au lieu de {columns * rows}")
    source_width, source_height = source_size
    x_boundaries = grid_tile_boundaries(source_width, columns)
    y_boundaries = grid_tile_boundaries(source_height, rows)
    margin = margin_x1 * scale
    assembled = Image.new("RGB", (source_width * scale, source_height * scale))
    for index, path in enumerate(parts):
        row, column = divmod(index, columns)
        with Image.open(path) as opened:
            part = opened.convert("RGB")
        left = 0 if column == 0 else margin
        top = 0 if row == 0 else margin
        right = part.width if column == columns - 1 else part.width - margin
        bottom = part.height if row == rows - 1 else part.height - margin
        core = part.crop((left, top, right, bottom))
        expected_size = (
            (x_boundaries[column + 1] - x_boundaries[column]) * scale,
            (y_boundaries[row + 1] - y_boundaries[row]) * scale,
        )
        if core.size != expected_size:
            raise RuntimeError(
                f"morceau incompatible {path.name} : {core.size}, attendu {expected_size[0]}x{expected_size[1]}"
            )
        assembled.paste(core, (x_boundaries[column] * scale, y_boundaries[row] * scale))
    save_png_atomic(assembled, destination)
    return assembled.size


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def seam_metrics(assembled: Path, source: Path, seam_x2: int) -> dict[str, float | int]:
    with Image.open(assembled) as opened:
        output = np.asarray(opened.convert("L"), dtype=np.float32)
        output_size = opened.size
    gradients = np.abs(np.diff(output, axis=1)).mean(axis=0)
    join = float(gradients[seam_x2 - 1])
    reference = np.concatenate(
        (gradients[seam_x2 - 400 : seam_x2 - 20], gradients[seam_x2 + 20 : seam_x2 + 400])
    )
    reference_mean = float(reference.mean())
    reference_std = float(reference.std())
    z_score = (join - reference_mean) / max(reference_std, 1e-9)

    with Image.open(source) as opened:
        original = np.asarray(opened.convert("L"), dtype=np.float32)
    source_gradients = np.abs(np.diff(original, axis=1)).mean(axis=0)
    seam_x1 = seam_x2 // 2
    source_reference = np.concatenate(
        (
            source_gradients[seam_x1 - 200 : seam_x1 - 10],
            source_gradients[seam_x1 + 10 : seam_x1 + 200],
        )
    )
    return {
        "assembled_width": output_size[0],
        "assembled_height": output_size[1],
        "seam_x2": seam_x2,
        "join_gradient": join,
        "surrounding_gradient_mean": reference_mean,
        "surrounding_gradient_std": reference_std,
        "normalized_difference_sigma": float(z_score),
        "source_join_gradient": float(source_gradients[seam_x1 - 1]),
        "source_surrounding_gradient_mean": float(source_reference.mean()),
    }


def assemble_parts(left: Path, right: Path, destination: Path) -> tuple[int, int]:
    with Image.open(left) as left_opened, Image.open(right) as right_opened:
        left_image = left_opened.convert("RGB")
        right_image = right_opened.convert("RGB")
        if left_image.size != right_image.size:
            raise RuntimeError(
                f"moitiés incompatibles pour l'assemblage : {left_image.size} / {right_image.size}"
            )
        assembled = Image.new("RGB", (left_image.width + right_image.width, left_image.height))
        assembled.paste(left_image, (0, 0))
        assembled.paste(right_image, (left_image.width, 0))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        assembled.save(temporary, format="PNG")
        temporary.replace(destination)
        return assembled.size


def output_record(path: Path) -> dict[str, Any]:
    width, height = image_size(path)
    return {
        "path": path.as_posix(),
        "width": width,
        "height": height,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def main() -> None:
    args = parse_args()
    area_id = args.area.upper()
    area_dir = find_area(area_id)
    preflight_path = args.preflight.resolve()
    preflight = validate_preflight(preflight_path, area_id, args.allow_blocked_test)
    run_dir = area_dir / "runs" / args.run
    run_dir.mkdir(parents=True, exist_ok=True)

    workflow_path = args.workflow.resolve()
    workflow_hash = sha256_file(workflow_path)
    if args.expected_workflow_sha256 and workflow_hash.lower() != args.expected_workflow_sha256.lower():
        raise RuntimeError(
            f"empreinte du workflow non autorisée : {workflow_hash}; "
            f"attendue {args.expected_workflow_sha256}"
        )
    with workflow_path.open("r", encoding="utf-8") as handle:
        reference_prompt = json.load(handle)
    runtime_prompt = copy.deepcopy(reference_prompt)
    if args.scale is not None:
        resize_id = find_single_node(runtime_prompt, "ResizeImageMaskNode")
        runtime_prompt[resize_id]["inputs"]["resize_type.multiplier"] = args.scale
    summary = workflow_summary(runtime_prompt)
    if args.expected_workflow_sha256.lower() == APPROVED_7B_SHA256:
        validate_approved_7b_settings(summary)
    else:
        validate_seedvr_baseline(summary)
    scale = int(summary["scale"])
    if args.expected_scale is not None and scale != args.expected_scale:
        raise RuntimeError(f"facteur inattendu : {scale}; attendu {args.expected_scale}")

    tile_kind = args.tile_kind
    is_night_kind = tile_kind.endswith("-nuit")
    # File stem: the night WED/tileset resref (ARxxxxN) so output filenames carry
    # it, while area_dir / run_dir / the ComfyUI upload path stay keyed on the day
    # area code (rendus-x1/tuiles-*-nuit/ is a sibling folder inside that same
    # area, not a separate area).
    file_stem = f"{area_id}N" if is_night_kind else area_id
    base_tile_kind = tile_kind[: -len("-nuit")] if is_night_kind else tile_kind
    source = area_dir / "rendus-x1" / tile_kind / f"{file_stem}-{base_tile_kind}-x1.png"
    if not source.is_file():
        raise RuntimeError(f"rendu x1 introuvable : {source}")
    is_split = args.split_rows or args.split_grid
    if is_split and scale not in (2, 4, 8):
        raise RuntimeError("les découpes exigent un facteur 2, 4 ou 8")
    if args.split_rows:
        sources, split_manifest = prepare_row_overlap_parts(
            source, run_dir, tile_kind, scale, args.overwrite
        )
    elif args.split_grid:
        if args.reuse_split_from_run:
            sources, split_manifest = reuse_grid_overlap_parts(
                source,
                area_dir,
                args.reuse_split_from_run,
                tile_kind,
                scale,
                args.split_grid[0],
                args.split_grid[1],
                args.split_margin,
            )
        else:
            sources, split_manifest = prepare_grid_overlap_parts(
                source,
                run_dir,
                tile_kind,
                scale,
                args.split_grid[0],
                args.split_grid[1],
                args.split_margin,
                args.overwrite,
            )
    if is_split:
        destinations = [
            run_dir / tile_kind / "01_upscale" / f"{part.stem}-x{scale}-{args.variant}.png"
            for part in sources
        ]
        assembled_destination = (
            run_dir / tile_kind / "03_assemble" / f"{file_stem}-{tile_kind}-x{scale}-{args.variant}-overlap.png"
        )
        for destination in [*destinations, assembled_destination]:
            if destination.exists() and not args.overwrite:
                raise RuntimeError(f"sortie déjà présente (utiliser --overwrite) : {destination}")
    else:
        sources = [source]
        destinations = [
            run_dir / tile_kind / "01_upscale" / f"{file_stem}-{tile_kind}-x{scale}-{args.variant}.png"
        ]
        if destinations[0].exists() and not args.overwrite:
            raise RuntimeError(f"sortie déjà présente (utiliser --overwrite) : {destinations[0]}")
        split_manifest = None
        assembled_destination = None

    client = ComfyClient(args.server, args.poll_seconds, args.timeout_seconds)
    system_stats = client.preflight()
    manifest_path = run_dir / "run.json"
    preflight_record = {
        "path": preflight_path.as_posix(),
        "ruleset_version": preflight.get("ruleset_version"),
        "routes": [route.get("id") for route in preflight.get("routes", [])],
        "blockers": preflight.get("blockers") or [],
        "experimental_blocker_override": bool(
            args.allow_blocked_test and (preflight.get("blockers") or [])
        ),
    }
    if args.append:
        if not manifest_path.is_file():
            raise RuntimeError(f"manifeste absent pour --append : {manifest_path}")
        with manifest_path.open("r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        if manifest.get("run_id") != args.run or manifest.get("area_id") != area_id:
            raise RuntimeError("le manifeste existant ne correspond pas au run demandé")
        if manifest.get("workflow", {}).get("sha256", "").lower() != workflow_hash.lower():
            raise RuntimeError("le workflow du manifeste existant diffère du workflow demandé")
        if manifest.get("parameters", {}).get("scale") != scale:
            raise RuntimeError("l'échelle du manifeste existant diffère de l'échelle demandée")
        manifest["status"] = "running"
        manifest["resumed_at_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["preflight"] = preflight_record
    else:
        if manifest_path.exists() and not args.overwrite:
            raise RuntimeError(f"manifeste déjà présent (utiliser --append ou --overwrite) : {manifest_path}")
        manifest = {
            "run_id": args.run,
            "area_id": area_id,
            "status": "running",
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "workflow": {
                "name": APPROVED_WORKFLOW_NAME,
                "path": workflow_path.as_posix(),
                "sha256": workflow_hash,
            },
            "parameters": {key: value for key, value in summary.items() if key != "node_ids"},
            "runtime_overrides": (
                {"resize_type.multiplier": args.scale}
                if args.scale is not None
                else {}
            ),
            "preflight": preflight_record,
            "comfyui": {
                "server": args.server,
                "version": system_stats.get("system", {}).get("comfyui_version"),
                "frontend_version": system_stats.get("system", {}).get("required_frontend_version"),
                "pytorch_version": system_stats.get("system", {}).get("pytorch_version"),
                "device": (system_stats.get("devices") or [{}])[0].get("name"),
            },
            "split": split_manifest,
            "input_kinds": [],
            "jobs": [],
            "outputs": {},
        }
    if tile_kind not in manifest.setdefault("input_kinds", []):
        manifest["input_kinds"].append(tile_kind)

    started = time.monotonic()
    upload_subfolder = f"BG2_Upscale/{area_id}/{args.run}/{tile_kind}"
    load_id = summary["node_ids"]["LoadImage"]
    save_id = summary["node_ids"]["SaveImage"]
    for part_number, (input_path, destination) in enumerate(zip(sources, destinations), start=1):
        part_started = time.monotonic()
        source_width, source_height = image_size(input_path)
        uploaded_name = client.upload(input_path, upload_subfolder)
        prompt = copy.deepcopy(runtime_prompt)
        prompt[load_id]["inputs"]["image"] = uploaded_name
        prompt[save_id]["inputs"]["filename_prefix"] = (
            f"BG2_Upscale/{area_id}/{args.run}/{tile_kind}/"
            f"{input_path.stem}-x{scale}-{args.variant}"
        )
        prompt_id = client.queue(prompt)
        print(f"{input_path.name}: prompt {prompt_id}", flush=True)
        history = client.wait_history(prompt_id)
        images = history.get("outputs", {}).get(save_id, {}).get("images", [])
        if len(images) != 1:
            raise RuntimeError(f"ComfyUI a produit {len(images)} image(s), une seule attendue")
        client.download(images[0], destination)
        output_width, output_height = image_size(destination)
        expected_size = (source_width * scale, source_height * scale)
        if (output_width, output_height) != expected_size:
            raise RuntimeError(
                f"dimension invalide pour {destination.name} : "
                f"{output_width}x{output_height}, attendu {expected_size[0]}x{expected_size[1]}"
            )
        elapsed = time.monotonic() - part_started
        manifest["jobs"].append({
            "tile_kind": tile_kind,
            "part": part_number if is_split else None,
            "prompt_id": prompt_id,
            "duration_seconds": round(elapsed, 3),
            "input": output_record(input_path),
            "output": output_record(destination),
            "comfyui_output": images[0],
        })
        print(f"OK {output_width}x{output_height}, {elapsed:.1f} s -> {destination}", flush=True)

    if is_split:
        assert assembled_destination is not None
        if args.split_rows:
            assembled_size = assemble_row_overlap(
                destinations[0], destinations[1], assembled_destination, scale
            )
        else:
            assembled_size = assemble_grid_overlap(
                destinations,
                assembled_destination,
                image_size(source),
                scale,
                args.split_grid[0],
                args.split_grid[1],
                args.split_margin,
            )
        expected_assembled = (image_size(source)[0] * scale, image_size(source)[1] * scale)
        if assembled_size != expected_assembled:
            raise RuntimeError(f"assemblage invalide : {assembled_size}, attendu {expected_assembled}")
        manifest["outputs"][tile_kind] = {
            "source_x1": output_record(source),
            "parts": [output_record(destination) for destination in destinations],
            "assembled": output_record(assembled_destination),
        }
        print(f"Assemblage OK {assembled_size[0]}x{assembled_size[1]} -> {assembled_destination}", flush=True)
    else:
        manifest["outputs"][tile_kind] = {
            **output_record(destinations[0]),
            "source_x1": output_record(source),
        }

    manifest["status"] = (
        "completed-experimental"
        if args.allow_blocked_test and (preflight.get("blockers") or [])
        else "completed"
    )
    manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    temporary_manifest = manifest_path.with_suffix(".json.part")
    with temporary_manifest.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary_manifest.replace(manifest_path)
    print(f"Manifest écrit : {manifest_path}")


if __name__ == "__main__":
    main()
