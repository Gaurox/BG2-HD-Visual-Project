"""Cœur CPU déterministe du compositing de patch raster.

Le module ne contacte aucun service et n'utilise aucun modèle génératif. Les opérations géométriques
restent une similarité isotrope (échelle + translation). Les fichiers source sont toujours lus, jamais
écrits ; ``compose`` refuse tout dossier de sortie déjà existant.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import sys
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image
from scipy import ndimage, optimize, signal


ROOT = Path(__file__).resolve().parents[2]
COMPOSITOR_SCHEMA = "bg2-upscale-map-patch-compositor-run-v1"
CONFIG_SCHEMA = "bg2-upscale-map-patch-compositor-config-v1"
LOSSLESS_FORMATS = frozenset({"PNG", "BMP", "TIFF"})
SUPPORTED_MODES = frozenset({"RGB", "RGBA"})


class CompositeError(RuntimeError):
    """Entrée, recalage ou invariant de composition invalide."""


@dataclass(frozen=True)
class ImageRecord:
    """Preuve compacte d'une image lue sans mutation."""

    reference: str
    filename: str
    sha256: str
    bytes: int
    format: str
    mode: str
    width: int
    height: int
    pixel_sha256: str


@dataclass(frozen=True)
class LoadedImage:
    record: ImageRecord
    rgba: np.ndarray
    save_info: dict[str, Any]


@dataclass(frozen=True)
class Candidate:
    scale: float
    tx: float
    ty: float
    coarse_score: float


@dataclass(frozen=True)
class Registration:
    scale: float
    tx: float
    ty: float
    coarse_score: float
    peak_ratio: float
    rmse: float
    inlier_fraction: float
    sample_count: int
    accepted: bool
    rejection_reasons: tuple[str, ...]


@dataclass(frozen=True)
class ColorCorrection:
    applied: bool
    luminance_gain: float
    luminance_offset: float
    saturation_gain: float
    a_shift: float
    b_shift: float
    identity_error: float
    corrected_error: float
    clipped_fraction: float


@dataclass(frozen=True)
class WarpedPatch:
    rgb: np.ndarray
    alpha: np.ndarray
    source_u: np.ndarray
    source_v: np.ndarray
    roi: tuple[int, int, int, int]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompositeError(f"JSON illisible : {path}") from exc
    if not isinstance(value, dict):
        raise CompositeError(f"objet JSON requis : {path}")
    return value


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if key not in result:
            raise CompositeError(f"clé de configuration inconnue : {key}")
        if isinstance(result[key], dict) and isinstance(value, Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _number(value: object, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise CompositeError(f"nombre fini requis : {label}")
    result = float(value)
    if minimum is not None and result < minimum:
        raise CompositeError(f"{label} doit être >= {minimum}")
    return result


def _integer(value: object, label: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CompositeError(f"entier requis : {label}")
    if minimum is not None and value < minimum:
        raise CompositeError(f"{label} doit être >= {minimum}")
    return value


def _validate_rectangles(value: object, label: str) -> None:
    if not isinstance(value, list):
        raise CompositeError(f"liste de rectangles requise : {label}")
    for index, rect in enumerate(value):
        if not isinstance(rect, list) or len(rect) != 4:
            raise CompositeError(f"rectangle [x,y,largeur,hauteur] requis : {label}[{index}]")
        _number(rect[0], f"{label}[{index}].x")
        _number(rect[1], f"{label}[{index}].y")
        _number(rect[2], f"{label}[{index}].largeur", minimum=0.0)
        _number(rect[3], f"{label}[{index}].hauteur", minimum=0.0)


def validate_config(config: Mapping[str, Any]) -> None:
    """Valide les bornes nécessaires avant tout calcul lourd."""

    if config.get("schema") != CONFIG_SCHEMA:
        raise CompositeError("schéma de configuration incompatible")
    try:
        registration = config["registration"]
        object_mask = config["object_mask"]
        blend = config["blend"]
        color = config["color"]
        output = config["output"]
    except KeyError as exc:
        raise CompositeError(f"section de configuration absente : {exc.args[0]}") from exc
    if not all(isinstance(section, Mapping) for section in (registration, object_mask, blend, color, output)):
        raise CompositeError("sections de configuration objet requises")

    scale_min = _number(registration.get("scale_min"), "registration.scale_min", minimum=0.001)
    scale_max = _number(registration.get("scale_max"), "registration.scale_max", minimum=0.001)
    if scale_min > scale_max:
        raise CompositeError("registration.scale_min supérieur à scale_max")
    _integer(registration.get("coarse_max_dimension_px"), "registration.coarse_max_dimension_px", minimum=128)
    _integer(registration.get("scale_steps"), "registration.scale_steps", minimum=1)
    _integer(registration.get("candidate_count"), "registration.candidate_count", minimum=1)
    _number(registration.get("border_fraction"), "registration.border_fraction", minimum=0.01)
    if float(registration["border_fraction"]) >= 0.5:
        raise CompositeError("registration.border_fraction doit être < 0.5")
    _number(registration.get("edge_percentile"), "registration.edge_percentile", minimum=0.0)
    if float(registration["edge_percentile"]) > 100.0:
        raise CompositeError("registration.edge_percentile doit être <= 100")
    _integer(registration.get("refine_max_samples"), "registration.refine_max_samples", minimum=128)
    _number(registration.get("refine_translation_px"), "registration.refine_translation_px", minimum=0.0)
    _number(registration.get("robust_loss_scale"), "registration.robust_loss_scale", minimum=0.0001)
    _number(registration.get("min_coarse_score"), "registration.min_coarse_score")
    _number(registration.get("min_peak_ratio"), "registration.min_peak_ratio", minimum=1.0)
    _number(registration.get("min_inlier_fraction"), "registration.min_inlier_fraction", minimum=0.0)
    if float(registration["min_inlier_fraction"]) > 1.0:
        raise CompositeError("registration.min_inlier_fraction doit être <= 1")
    _number(registration.get("max_rmse"), "registration.max_rmse", minimum=0.0)
    roi = registration.get("map_search_roi")
    if roi is not None:
        if not isinstance(roi, list) or len(roi) != 4:
            raise CompositeError("registration.map_search_roi doit être [x,y,largeur,hauteur] ou null")
        for item in roi:
            _integer(item, "registration.map_search_roi")
        if roi[2] <= 0 or roi[3] <= 0:
            raise CompositeError("registration.map_search_roi de taille strictement positive")
    _validate_rectangles(registration.get("patch_exclude_rectangles"), "registration.patch_exclude_rectangles")
    _validate_rectangles(registration.get("map_exclude_rectangles"), "registration.map_exclude_rectangles")

    for key in ("delta_e_floor", "delta_e_mad_factor", "gradient_floor"):
        _number(object_mask.get(key), f"object_mask.{key}", minimum=0.0)
    for key in ("minimum_component_area_px", "closing_radius_px", "opening_radius_px"):
        _integer(object_mask.get(key), f"object_mask.{key}", minimum=0)
    seed = object_mask.get("object_seed_patch")
    if seed is not None:
        if not isinstance(seed, list) or len(seed) != 2:
            raise CompositeError("object_mask.object_seed_patch doit être [x,y] ou null")
        for item in seed:
            _number(item, "object_mask.object_seed_patch")

    _integer(blend.get("dilation_px"), "blend.dilation_px", minimum=0)
    _number(blend.get("fade_width_px"), "blend.fade_width_px", minimum=0.01)
    _number(blend.get("gaussian_sigma_px"), "blend.gaussian_sigma_px", minimum=0.0)
    _integer(blend.get("edge_guard_px"), "blend.edge_guard_px", minimum=0)
    _integer(blend.get("minimum_coverage_px"), "blend.minimum_coverage_px", minimum=1)

    if not isinstance(color.get("enabled"), bool):
        raise CompositeError("color.enabled booléen requis")
    _number(color.get("context_ring_fraction"), "color.context_ring_fraction", minimum=0.01)
    if float(color["context_ring_fraction"]) >= 0.5:
        raise CompositeError("color.context_ring_fraction doit être < 0.5")
    for key in (
        "max_luminance_gain_delta", "max_luminance_offset", "max_chroma_shift",
        "max_saturation_gain_delta", "minimum_relative_improvement", "max_clipped_fraction",
    ):
        _number(color.get(key), f"color.{key}", minimum=0.0)
    if float(color["max_clipped_fraction"]) > 1.0:
        raise CompositeError("color.max_clipped_fraction doit être <= 1")

    if not isinstance(output.get("strict_lossless_format"), bool):
        raise CompositeError("output.strict_lossless_format booléen requis")
    _integer(output.get("preview_padding_px"), "output.preview_padding_px", minimum=0)
    _integer(output.get("preview_max_dimension_px"), "output.preview_max_dimension_px", minimum=64)
    compression = _integer(output.get("png_compress_level"), "output.png_compress_level", minimum=0)
    if compression > 9:
        raise CompositeError("output.png_compress_level doit être <= 9")


def load_config(path: Path | None = None) -> dict[str, Any]:
    defaults = _read_json(Path(__file__).with_name("defaults.json"))
    config = _deep_merge(defaults, _read_json(path)) if path is not None else defaults
    validate_config(config)
    return config


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_pixels(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def _portable_reference(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return f"external:{path.name}"


def _load_image(path: Path, *, label: str) -> LoadedImage:
    path = path.resolve()
    if not path.is_file():
        raise CompositeError(f"{label} absent : {path}")
    try:
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise CompositeError(f"{label} animé/multipage non pris en charge : {path}")
            orientation = image.getexif().get(274, 1)
            if orientation != 1:
                raise CompositeError(f"{label} possède une orientation EXIF non identitaire : {path}")
            image.load()
            image_format = str(image.format or "").upper()
            if image.mode not in SUPPORTED_MODES:
                raise CompositeError(f"{label} doit être RGB ou RGBA, reçu {image.mode} : {path}")
            if image.info.get("icc_profile"):
                raise CompositeError(f"{label} possède un profil ICC ; v1 exige du sRGB sans profil embarqué : {path}")
            rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
            save_info: dict[str, Any] = {}
            for key in ("dpi",):
                if key in image.info:
                    save_info[key] = image.info[key]
            mode = image.mode
            width, height = image.size
    except OSError as exc:
        raise CompositeError(f"{label} illisible : {path}") from exc
    record = ImageRecord(
        reference=_portable_reference(path),
        filename=path.name,
        sha256=sha256_file(path),
        bytes=path.stat().st_size,
        format=image_format,
        mode=mode,
        width=width,
        height=height,
        pixel_sha256=sha256_pixels(rgba),
    )
    return LoadedImage(record=record, rgba=rgba, save_info=save_info)


def inspect_inputs(map_path: Path, patch_path: Path, config_path: Path | None = None) -> dict[str, Any]:
    """Contrôle de lecture seule exploitable dans une commande de préflight."""

    config = load_config(config_path)
    map_image = _load_image(map_path, label="map")
    patch_image = _load_image(patch_path, label="patch")
    if map_path.resolve() == patch_path.resolve():
        raise CompositeError("map et patch doivent être deux fichiers distincts")
    if config["output"]["strict_lossless_format"] and map_image.record.format not in LOSSLESS_FORMATS:
        raise CompositeError(f"format map avec perte refusé en mode strict : {map_image.record.format}")
    return {
        "schema": CONFIG_SCHEMA,
        "map": asdict(map_image.record),
        "patch": asdict(patch_image.record),
        "scale_bounds": [config["registration"]["scale_min"], config["registration"]["scale_max"]],
        "map_search_roi": config["registration"]["map_search_roi"],
    }


def _rectangles_mask(shape: tuple[int, int], rectangles: Sequence[Sequence[float]]) -> np.ndarray:
    height, width = shape
    allowed = np.ones(shape, dtype=bool)
    for raw in rectangles:
        x, y, rect_width, rect_height = (float(item) for item in raw)
        x0 = max(0, int(math.floor(x)))
        y0 = max(0, int(math.floor(y)))
        x1 = min(width, int(math.ceil(x + rect_width)))
        y1 = min(height, int(math.ceil(y + rect_height)))
        if x0 < x1 and y0 < y1:
            allowed[y0:y1, x0:x1] = False
    return allowed


def _to_gray(rgb: np.ndarray) -> np.ndarray:
    value = rgb.astype(np.float32) / 255.0
    return value[:, :, 0] * 0.2126 + value[:, :, 1] * 0.7152 + value[:, :, 2] * 0.0722


def _gradient(gray: np.ndarray) -> np.ndarray:
    gx = ndimage.sobel(gray, axis=1, mode="nearest")
    gy = ndimage.sobel(gray, axis=0, mode="nearest")
    return np.hypot(gx, gy).astype(np.float32)


def _normalized_gradient(rgb: np.ndarray) -> np.ndarray:
    raw = _gradient(_to_gray(rgb))
    reference = float(np.percentile(raw, 99.0))
    if reference <= 1.0e-8:
        return np.zeros_like(raw)
    return np.clip(raw / reference, 0.0, 1.0)


def _resize_rgb(rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    if width <= 0 or height <= 0:
        raise CompositeError("redimensionnement non positif")
    image = Image.fromarray(rgb, mode="RGB")
    return np.asarray(image.resize((width, height), Image.Resampling.BICUBIC), dtype=np.uint8)


def _thumbnail(rgb: np.ndarray, maximum: int) -> tuple[np.ndarray, float]:
    height, width = rgb.shape[:2]
    factor = min(1.0, float(maximum) / float(max(width, height)))
    result_width = max(1, int(round(width * factor)))
    result_height = max(1, int(round(height * factor)))
    return _resize_rgb(rgb, result_width, result_height), factor


def _border_mask(shape: tuple[int, int], fraction: float) -> np.ndarray:
    height, width = shape
    thickness = max(1, int(round(min(height, width) * fraction)))
    mask = np.ones(shape, dtype=bool)
    if height > thickness * 2 and width > thickness * 2:
        mask[thickness:-thickness, thickness:-thickness] = False
    return mask


def _analysis_mask(patch_rgb: np.ndarray, patch_alpha: np.ndarray, registration: Mapping[str, Any]) -> np.ndarray:
    border = _border_mask(patch_rgb.shape[:2], float(registration["border_fraction"]))
    allowed = _rectangles_mask(patch_rgb.shape[:2], registration["patch_exclude_rectangles"])
    gradient = _normalized_gradient(patch_rgb)
    available = border & allowed & (patch_alpha >= 254)
    if int(np.count_nonzero(available)) < 128:
        raise CompositeError("décor périphérique insuffisant dans le patch")
    threshold = float(np.percentile(gradient[available], float(registration["edge_percentile"])))
    selected = available & (gradient >= threshold)
    if int(np.count_nonzero(selected)) < 128:
        selected = available
    return selected


def _masked_ncc(target: np.ndarray, patch: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """ZNCC glissante déterministe pour un patch pondéré binaire."""

    if target.ndim != 2 or patch.ndim != 2 or patch.shape != mask.shape:
        raise CompositeError("formes NCC incompatibles")
    count = float(np.count_nonzero(mask))
    if count < 64:
        raise CompositeError("masque de recalage trop petit")
    if target.shape[0] < patch.shape[0] or target.shape[1] < patch.shape[1]:
        return np.empty((0, 0), dtype=np.float32)
    weights = mask.astype(np.float32)
    patch_weighted = patch.astype(np.float32) * weights
    sum_patch = float(patch_weighted.sum(dtype=np.float64))
    sum_patch_sq = float((patch_weighted * patch_weighted).sum(dtype=np.float64))
    patch_variance = sum_patch_sq - sum_patch * sum_patch / count
    if patch_variance <= 1.0e-10:
        raise CompositeError("décor de patch sans variance pour le recalage")
    flipped_weights = weights[::-1, ::-1]
    product = signal.fftconvolve(target, patch_weighted[::-1, ::-1], mode="valid")
    sum_target = signal.fftconvolve(target, flipped_weights, mode="valid")
    sum_target_sq = signal.fftconvolve(target * target, flipped_weights, mode="valid")
    target_variance = np.maximum(sum_target_sq - sum_target * sum_target / count, 0.0)
    denominator = np.sqrt(target_variance * patch_variance)
    numerator = product - sum_target * sum_patch / count
    response = np.full(numerator.shape, -np.inf, dtype=np.float32)
    valid = denominator > 1.0e-10
    response[valid] = (numerator[valid] / denominator[valid]).astype(np.float32)
    return response


def _candidate_positions(response: np.ndarray, count: int) -> list[tuple[int, int, float]]:
    if response.size == 0:
        return []
    finite = np.isfinite(response)
    available = int(np.count_nonzero(finite))
    if not available:
        return []
    requested = min(available, max(count * 8, count))
    values = np.where(finite, response, -np.inf).ravel()
    indexes = np.argpartition(values, -requested)[-requested:]
    ordered = sorted(indexes.tolist(), key=lambda index: (-float(values[index]), int(index)))
    result: list[tuple[int, int, float]] = []
    width = response.shape[1]
    for index in ordered:
        y, x = divmod(index, width)
        result.append((x, y, float(values[index])))
    return result


def _coarse_candidates(map_rgb: np.ndarray, patch_rgb: np.ndarray, patch_alpha: np.ndarray, config: Mapping[str, Any]) -> tuple[list[Candidate], float]:
    registration = config["registration"]
    map_thumb, factor = _thumbnail(map_rgb, int(registration["coarse_max_dimension_px"]))
    map_gradient = _normalized_gradient(map_thumb)
    roi = registration["map_search_roi"]
    if roi is None:
        roi_x, roi_y, roi_width, roi_height = 0, 0, map_rgb.shape[1], map_rgb.shape[0]
    else:
        roi_x, roi_y, roi_width, roi_height = (int(item) for item in roi)
        if roi_x < 0 or roi_y < 0 or roi_x + roi_width > map_rgb.shape[1] or roi_y + roi_height > map_rgb.shape[0]:
            raise CompositeError("registration.map_search_roi hors map")
    thumb_x0 = int(math.floor(roi_x * factor))
    thumb_y0 = int(math.floor(roi_y * factor))
    thumb_x1 = max(thumb_x0 + 1, int(math.ceil((roi_x + roi_width) * factor)))
    thumb_y1 = max(thumb_y0 + 1, int(math.ceil((roi_y + roi_height) * factor)))
    target = map_gradient[thumb_y0:thumb_y1, thumb_x0:thumb_x1]
    candidates: list[Candidate] = []
    scales = np.linspace(float(registration["scale_min"]), float(registration["scale_max"]), int(registration["scale_steps"]))
    for scale in scales.tolist():
        patch_width = max(1, int(round(patch_rgb.shape[1] * scale * factor)))
        patch_height = max(1, int(round(patch_rgb.shape[0] * scale * factor)))
        if patch_width > target.shape[1] or patch_height > target.shape[0]:
            continue
        scaled = _resize_rgb(patch_rgb, patch_width, patch_height)
        scaled_alpha = _resize_rgb(np.repeat(patch_alpha[:, :, None], 3, axis=2), patch_width, patch_height)[:, :, 0]
        mask = _analysis_mask(scaled, scaled_alpha, registration)
        response = _masked_ncc(target, _normalized_gradient(scaled), mask)
        for x, y, score in _candidate_positions(response, int(registration["candidate_count"])):
            candidates.append(Candidate(
                scale=float(scale),
                tx=(x + thumb_x0) / factor,
                ty=(y + thumb_y0) / factor,
                coarse_score=score,
            ))
    if not candidates:
        raise CompositeError("aucun candidat de recalage compatible avec la ROI")
    candidates.sort(key=lambda candidate: (-candidate.coarse_score, candidate.scale, candidate.ty, candidate.tx))
    peak_ratio = (candidates[0].coarse_score / candidates[1].coarse_score
                  if len(candidates) > 1 and candidates[1].coarse_score > 1.0e-9 else math.inf)
    selected: list[Candidate] = []
    min_distance = max(16.0, min(patch_rgb.shape[:2]) * float(registration["scale_min"]) * 0.20)
    for candidate in candidates:
        if all(math.hypot(candidate.tx - kept.tx, candidate.ty - kept.ty) >= min_distance for kept in selected):
            selected.append(candidate)
        if len(selected) == int(registration["candidate_count"]):
            break
    return selected, peak_ratio


def _evenly_sample(mask: np.ndarray, maximum: int) -> tuple[np.ndarray, np.ndarray]:
    ys, xs = np.nonzero(mask)
    if xs.size < 128:
        raise CompositeError("échantillon de recalage insuffisant")
    if xs.size > maximum:
        indexes = np.linspace(0, xs.size - 1, maximum, dtype=np.int64)
        xs = xs[indexes]
        ys = ys[indexes]
    return xs.astype(np.float64), ys.astype(np.float64)


def _map_exclusion_mask(shape: tuple[int, int], rectangles: Sequence[Sequence[float]]) -> np.ndarray:
    return _rectangles_mask(shape, rectangles).astype(np.float32)


def _refine_candidate(
    map_rgb: np.ndarray,
    patch_rgb: np.ndarray,
    patch_alpha: np.ndarray,
    candidate: Candidate,
    peak_ratio: float,
    config: Mapping[str, Any],
) -> Registration:
    registration = config["registration"]
    analysis = _analysis_mask(patch_rgb, patch_alpha, registration)
    xs, ys = _evenly_sample(analysis, int(registration["refine_max_samples"]))
    patch_gradient = _normalized_gradient(patch_rgb)
    source = patch_gradient[ys.astype(np.intp), xs.astype(np.intp)].astype(np.float64)
    map_gradient = _normalized_gradient(map_rgb)
    map_allowed = _map_exclusion_mask(map_rgb.shape[:2], registration["map_exclude_rectangles"])
    translation = float(registration["refine_translation_px"])
    lower = np.array([float(registration["scale_min"]), candidate.tx - translation, candidate.ty - translation])
    upper = np.array([float(registration["scale_max"]), candidate.tx + translation, candidate.ty + translation])

    def residual(parameters: np.ndarray, selected: np.ndarray | None = None) -> np.ndarray:
        scale, tx, ty = (float(item) for item in parameters)
        use_x = xs if selected is None else xs[selected]
        use_y = ys if selected is None else ys[selected]
        use_source = source if selected is None else source[selected]
        map_x = tx + scale * use_x
        map_y = ty + scale * use_y
        target = ndimage.map_coordinates(map_gradient, [map_y, map_x], order=1, mode="constant", cval=2.0)
        allowed = ndimage.map_coordinates(map_allowed, [map_y, map_x], order=0, mode="constant", cval=0.0)
        return np.where(allowed >= 0.5, target - use_source, 1.0)

    try:
        first = optimize.least_squares(
            residual,
            x0=np.array([candidate.scale, candidate.tx, candidate.ty], dtype=np.float64),
            bounds=(lower, upper),
            loss="soft_l1",
            f_scale=float(registration["robust_loss_scale"]),
            max_nfev=80,
            xtol=1.0e-8,
            ftol=1.0e-8,
            gtol=1.0e-8,
        )
    except (ValueError, RuntimeError) as exc:
        raise CompositeError(f"optimisation de recalage échouée : {exc}") from exc
    first_residual = residual(first.x)
    absolute = np.abs(first_residual)
    median = float(np.median(absolute))
    mad = float(np.median(np.abs(absolute - median)))
    cutoff = max(0.015, median + 3.5 * max(mad, 1.0e-5))
    inliers = absolute <= cutoff
    if int(np.count_nonzero(inliers)) >= 128:
        second = optimize.least_squares(
            lambda parameters: residual(parameters, inliers),
            x0=first.x,
            bounds=(lower, upper),
            loss="soft_l1",
            f_scale=float(registration["robust_loss_scale"]),
            max_nfev=80,
            xtol=1.0e-8,
            ftol=1.0e-8,
            gtol=1.0e-8,
        )
        parameters = second.x
        final_residual = residual(parameters)
        absolute = np.abs(final_residual)
        median = float(np.median(absolute))
        mad = float(np.median(np.abs(absolute - median)))
        cutoff = max(0.015, median + 3.5 * max(mad, 1.0e-5))
        inliers = absolute <= cutoff
    else:
        parameters = first.x
        final_residual = first_residual
    inlier_fraction = float(np.mean(inliers))
    rmse = float(np.sqrt(np.mean(np.square(final_residual[inliers])))) if np.any(inliers) else math.inf
    scale, tx, ty = (float(item) for item in parameters)
    reasons: list[str] = []
    if candidate.coarse_score < float(registration["min_coarse_score"]):
        reasons.append("coarse-score")
    if peak_ratio < float(registration["min_peak_ratio"]):
        reasons.append("ambiguous-peak")
    if inlier_fraction < float(registration["min_inlier_fraction"]):
        reasons.append("inlier-fraction")
    if rmse > float(registration["max_rmse"]):
        reasons.append("rmse")
    if math.isclose(scale, float(registration["scale_min"]), abs_tol=1.0e-7) or math.isclose(scale, float(registration["scale_max"]), abs_tol=1.0e-7):
        reasons.append("scale-bound")
    return Registration(
        scale=scale,
        tx=tx,
        ty=ty,
        coarse_score=candidate.coarse_score,
        peak_ratio=peak_ratio,
        rmse=rmse,
        inlier_fraction=inlier_fraction,
        sample_count=int(xs.size),
        accepted=not reasons,
        rejection_reasons=tuple(reasons),
    )


def register(map_rgba: np.ndarray, patch_rgba: np.ndarray, config: Mapping[str, Any]) -> Registration:
    """Recherche puis affine les meilleurs candidats; refuse une confiance insuffisante."""

    map_rgb = map_rgba[:, :, :3]
    patch_rgb = patch_rgba[:, :, :3]
    patch_alpha = patch_rgba[:, :, 3]
    candidates, peak_ratio = _coarse_candidates(map_rgb, patch_rgb, patch_alpha, config)
    results = [_refine_candidate(map_rgb, patch_rgb, patch_alpha, candidate, peak_ratio, config) for candidate in candidates]
    results.sort(key=lambda item: (not item.accepted, item.rmse, -item.coarse_score, item.ty, item.tx))
    return results[0]


def _transform_roi(registration: Registration, patch_shape: tuple[int, int], map_shape: tuple[int, int]) -> tuple[int, int, int, int]:
    patch_height, patch_width = patch_shape
    map_height, map_width = map_shape
    x0 = int(math.floor(registration.tx))
    y0 = int(math.floor(registration.ty))
    x1 = int(math.ceil(registration.tx + registration.scale * patch_width))
    y1 = int(math.ceil(registration.ty + registration.scale * patch_height))
    if x0 < 0 or y0 < 0 or x1 > map_width or y1 > map_height:
        raise CompositeError("patch recalé partiellement hors de la map")
    return x0, y0, x1, y1


def _warp_patch(patch_rgba: np.ndarray, registration: Registration, map_shape: tuple[int, int]) -> WarpedPatch:
    roi = _transform_roi(registration, patch_rgba.shape[:2], map_shape)
    x0, y0, x1, y1 = roi
    grid_y, grid_x = np.mgrid[y0:y1, x0:x1]
    source_u = (grid_x.astype(np.float64) - registration.tx) / registration.scale
    source_v = (grid_y.astype(np.float64) - registration.ty) / registration.scale
    rgb = np.empty((y1 - y0, x1 - x0, 3), dtype=np.float32)
    for channel in range(3):
        rgb[:, :, channel] = ndimage.map_coordinates(
            patch_rgba[:, :, channel].astype(np.float32) / 255.0,
            [source_v, source_u], order=3, mode="constant", cval=0.0,
        )
    alpha = ndimage.map_coordinates(
        patch_rgba[:, :, 3].astype(np.float32) / 255.0,
        [source_v, source_u], order=1, mode="constant", cval=0.0,
    )
    return WarpedPatch(
        rgb=np.clip(rgb, 0.0, 1.0), alpha=np.clip(alpha, 0.0, 1.0),
        source_u=source_u, source_v=source_v, roi=roi,
    )


def _warp_mask(mask: np.ndarray, warped: WarpedPatch) -> np.ndarray:
    values = ndimage.map_coordinates(
        mask.astype(np.float32), [warped.source_v, warped.source_u], order=0, mode="constant", cval=0.0,
    )
    return values >= 0.5


def _srgb_to_linear(value: np.ndarray) -> np.ndarray:
    return np.where(value <= 0.04045, value / 12.92, ((value + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    return np.where(value <= 0.0031308, value * 12.92, 1.055 * np.power(value, 1.0 / 2.4) - 0.055)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB D65 -> CIE Lab; entrée/sortie float, RGB dans [0,1]."""

    linear = _srgb_to_linear(np.clip(rgb.astype(np.float32), 0.0, 1.0))
    matrix = np.array(((0.4124564, 0.3575761, 0.1804375), (0.2126729, 0.7151522, 0.0721750), (0.0193339, 0.1191920, 0.9503041)), dtype=np.float32)
    xyz = np.einsum("...c,dc->...d", linear, matrix)
    reference = np.array((0.95047, 1.0, 1.08883), dtype=np.float32)
    ratio = xyz / reference
    delta = 6.0 / 29.0
    transformed = np.where(ratio > delta ** 3, np.cbrt(np.maximum(ratio, 0.0)), ratio / (3.0 * delta * delta) + 4.0 / 29.0)
    lab = np.empty_like(transformed)
    lab[..., 0] = 116.0 * transformed[..., 1] - 16.0
    lab[..., 1] = 500.0 * (transformed[..., 0] - transformed[..., 1])
    lab[..., 2] = 200.0 * (transformed[..., 1] - transformed[..., 2])
    return lab


def lab_to_rgb(lab: np.ndarray) -> tuple[np.ndarray, float]:
    """CIE Lab D65 -> sRGB; retourne la fraction de valeurs hors gamut avant clamp."""

    fy = (lab[..., 0] + 16.0) / 116.0
    fx = fy + lab[..., 1] / 500.0
    fz = fy - lab[..., 2] / 200.0
    delta = 6.0 / 29.0

    def inverse(value: np.ndarray) -> np.ndarray:
        return np.where(value > delta, value ** 3, 3.0 * delta * delta * (value - 4.0 / 29.0))

    xyz = np.stack((inverse(fx) * 0.95047, inverse(fy), inverse(fz) * 1.08883), axis=-1)
    matrix = np.array(((3.2404542, -1.5371385, -0.4985314), (-0.9692660, 1.8760108, 0.0415560), (0.0556434, -0.2040259, 1.0572252)), dtype=np.float32)
    linear = np.einsum("...c,dc->...d", xyz, matrix)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(np.maximum(linear, 0.0), 1.0 / 2.4) - 0.055)
    clipped = float(np.mean((srgb < 0.0) | (srgb > 1.0)))
    return np.clip(srgb, 0.0, 1.0), clipped


def _robust_scale(values: np.ndarray) -> float:
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    return max(1.4826 * mad, 1.0e-4)


def _color_context_mask(warped: WarpedPatch, patch_rgba: np.ndarray, config: Mapping[str, Any]) -> np.ndarray:
    registration = config["registration"]
    color = config["color"]
    patch_context = _border_mask(patch_rgba.shape[:2], float(color["context_ring_fraction"]))
    patch_context &= _rectangles_mask(patch_rgba.shape[:2], registration["patch_exclude_rectangles"])
    patch_context &= patch_rgba[:, :, 3] >= 254
    return _warp_mask(patch_context, warped) & (warped.alpha >= 0.99)


def _fit_color(
    patch_rgb: np.ndarray,
    target_rgb: np.ndarray,
    context: np.ndarray,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, ColorCorrection]:
    color = config["color"]
    identity = ColorCorrection(False, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    if not bool(color["enabled"]) or int(np.count_nonzero(context)) < 128:
        return patch_rgb, identity
    source_lab = rgb_to_lab(patch_rgb)
    target_lab = rgb_to_lab(target_rgb)
    indexes = np.flatnonzero(context)
    source_context = source_lab.reshape(-1, 3)[indexes]
    target_context = target_lab.reshape(-1, 3)[indexes]
    initial_error = np.linalg.norm(source_context - target_context, axis=1)
    cutoff = float(np.percentile(initial_error, 80.0))
    stable = initial_error <= cutoff
    if int(np.count_nonzero(stable)) < 64:
        return patch_rgb, identity
    fit_source = source_context[stable]
    fit_target = target_context[stable]
    luminance_gain = np.clip(
        _robust_scale(fit_target[:, 0]) / _robust_scale(fit_source[:, 0]),
        1.0 - float(color["max_luminance_gain_delta"]), 1.0 + float(color["max_luminance_gain_delta"]),
    )
    luminance_offset = np.clip(
        float(np.median(fit_target[:, 0])) - luminance_gain * float(np.median(fit_source[:, 0])),
        -float(color["max_luminance_offset"]), float(color["max_luminance_offset"]),
    )
    source_chroma = np.hypot(fit_source[:, 1], fit_source[:, 2])
    target_chroma = np.hypot(fit_target[:, 1], fit_target[:, 2])
    saturation_gain = np.clip(
        float(np.median(target_chroma)) / max(float(np.median(source_chroma)), 1.0e-4),
        1.0 - float(color["max_saturation_gain_delta"]), 1.0 + float(color["max_saturation_gain_delta"]),
    )
    a_shift = np.clip(
        float(np.median(fit_target[:, 1])) - saturation_gain * float(np.median(fit_source[:, 1])),
        -float(color["max_chroma_shift"]), float(color["max_chroma_shift"]),
    )
    b_shift = np.clip(
        float(np.median(fit_target[:, 2])) - saturation_gain * float(np.median(fit_source[:, 2])),
        -float(color["max_chroma_shift"]), float(color["max_chroma_shift"]),
    )
    corrected_lab = source_lab.copy()
    corrected_lab[..., 0] = corrected_lab[..., 0] * luminance_gain + luminance_offset
    corrected_lab[..., 1] = corrected_lab[..., 1] * saturation_gain + a_shift
    corrected_lab[..., 2] = corrected_lab[..., 2] * saturation_gain + b_shift
    corrected_rgb, clipped_fraction = lab_to_rgb(corrected_lab)
    validation = np.flatnonzero(context).reshape(-1)[1::2]
    if validation.size < 32:
        validation = np.flatnonzero(context)
    identity_error = float(np.mean(np.linalg.norm(source_lab.reshape(-1, 3)[validation] - target_lab.reshape(-1, 3)[validation], axis=1)))
    corrected_error = float(np.mean(np.linalg.norm(corrected_lab.reshape(-1, 3)[validation] - target_lab.reshape(-1, 3)[validation], axis=1)))
    improvement = (identity_error - corrected_error) / max(identity_error, 1.0e-8)
    applied = bool(
        improvement >= float(color["minimum_relative_improvement"])
        and clipped_fraction <= float(color["max_clipped_fraction"])
    )
    correction = ColorCorrection(
        applied=applied,
        luminance_gain=float(luminance_gain),
        luminance_offset=float(luminance_offset),
        saturation_gain=float(saturation_gain),
        a_shift=float(a_shift),
        b_shift=float(b_shift),
        identity_error=identity_error,
        corrected_error=corrected_error,
        clipped_fraction=clipped_fraction,
    )
    return (corrected_rgb if applied else patch_rgb), correction


def _disk(radius: int) -> np.ndarray:
    if radius <= 0:
        return np.ones((1, 1), dtype=bool)
    coordinates = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    return coordinates[0] * coordinates[0] + coordinates[1] * coordinates[1] <= radius * radius


def _smoothstep(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def _support_mask(
    source_rgb: np.ndarray,
    target_rgb: np.ndarray,
    warped: WarpedPatch,
    patch_rgba: np.ndarray,
    config: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, float]:
    """Retourne le noyau binaire, son résidu DeltaE et le seuil appliqué."""

    object_config = config["object_mask"]
    registration = config["registration"]
    allowed_patch = _rectangles_mask(patch_rgba.shape[:2], registration["patch_exclude_rectangles"])
    allowed = _warp_mask(allowed_patch, warped) & (warped.alpha >= 0.99)
    source_lab = rgb_to_lab(source_rgb)
    target_lab = rgb_to_lab(target_rgb)
    delta_e = np.linalg.norm(source_lab - target_lab, axis=2)
    context = _color_context_mask(warped, patch_rgba, config) & allowed
    reference = delta_e[context] if int(np.count_nonzero(context)) >= 64 else delta_e[allowed]
    if reference.size < 64:
        raise CompositeError("pixels comparables insuffisants pour le masque d'objet")
    threshold = max(
        float(object_config["delta_e_floor"]),
        float(np.median(reference)) + float(object_config["delta_e_mad_factor"]) * _robust_scale(reference),
    )
    source_gradient = _normalized_gradient((source_rgb * 255.0).round().astype(np.uint8))
    target_gradient = _normalized_gradient((target_rgb * 255.0).round().astype(np.uint8))
    gradient_difference = np.abs(source_gradient - target_gradient)
    changed = allowed & (
        (delta_e > threshold)
        | ((delta_e > threshold * 0.5) & (gradient_difference > float(object_config["gradient_floor"])))
    )
    opening = int(object_config["opening_radius_px"])
    closing = int(object_config["closing_radius_px"])
    if opening:
        changed = ndimage.binary_opening(changed, structure=_disk(opening))
    if closing:
        changed = ndimage.binary_closing(changed, structure=_disk(closing))
    labels, count = ndimage.label(changed)
    retained = np.zeros_like(changed)
    minimum = int(object_config["minimum_component_area_px"])
    for label in range(1, count + 1):
        component = labels == label
        if int(np.count_nonzero(component)) >= minimum:
            retained |= component
    seed = object_config["object_seed_patch"]
    if seed is not None:
        seed_x = int(round(float(seed[0]) * (retained.shape[1] / patch_rgba.shape[1])))
        seed_y = int(round(float(seed[1]) * (retained.shape[0] / patch_rgba.shape[0])))
        seed_x = min(max(seed_x, 0), retained.shape[1] - 1)
        seed_y = min(max(seed_y, 0), retained.shape[0] - 1)
        selected_label = labels[seed_y, seed_x]
        if selected_label == 0 or int(np.count_nonzero(labels == selected_label)) < minimum:
            raise CompositeError("object_seed_patch ne cible aucune composante retenue")
        retained = labels == selected_label
    if not np.any(retained):
        raise CompositeError("aucune emprise utile détectée ; ajuster les seuils ou object_seed_patch")
    return retained, delta_e, threshold


def _blend_mask(core: np.ndarray, config: Mapping[str, Any]) -> np.ndarray:
    blend = config["blend"]
    dilated = ndimage.binary_dilation(core, structure=_disk(int(blend["dilation_px"])))
    distance = ndimage.distance_transform_edt(~dilated).astype(np.float32)
    fade_width = float(blend["fade_width_px"])
    alpha = np.zeros(core.shape, dtype=np.float32)
    alpha[dilated] = 1.0
    band = (distance > 0.0) & (distance <= fade_width)
    alpha[band] = 1.0 - _smoothstep(distance[band] / fade_width)
    sigma = float(blend["gaussian_sigma_px"])
    if sigma > 0.0:
        blurred = ndimage.gaussian_filter(alpha, sigma=sigma, mode="constant", cval=0.0, truncate=4.0)
        alpha[(distance > fade_width)] = 0.0
        alpha[band] = blurred[band]
        alpha[dilated] = 1.0
    alpha *= 1.0
    if int(np.count_nonzero(alpha > 0.0)) < int(blend["minimum_coverage_px"]):
        raise CompositeError("emprise de fusion sous la couverture minimale")
    guard = int(blend["edge_guard_px"])
    edge = np.empty(0, dtype=np.float32) if guard == 0 else np.concatenate((alpha[:guard, :].ravel(), alpha[-guard:, :].ravel(), alpha[:, :guard].ravel(), alpha[:, -guard:].ravel()))
    if edge.size and float(np.max(edge)) > 1.0e-6:
        raise CompositeError("fade ou dilatation atteint le bord rectangulaire du patch")
    return np.clip(alpha, 0.0, 1.0)


def _compose_rgb(map_rgb: np.ndarray, patch_rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    map_linear = _srgb_to_linear(map_rgb.astype(np.float32) / 255.0)
    patch_linear = _srgb_to_linear(np.clip(patch_rgb, 0.0, 1.0))
    mixed = map_linear * (1.0 - alpha[:, :, None]) + patch_linear * alpha[:, :, None]
    return np.clip(np.rint(_linear_to_srgb(mixed) * 255.0), 0, 255).astype(np.uint8)


def _residual_visual(delta_e: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    scale = max(float(np.percentile(delta_e[alpha > 0.0], 99.0)) if np.any(alpha > 0.0) else 1.0, 1.0)
    return np.clip(np.rint(np.clip(delta_e / scale, 0.0, 1.0) * 255.0), 0, 255).astype(np.uint8)


def _seam_metrics(residual_before: np.ndarray, residual_after: np.ndarray, alpha: np.ndarray) -> dict[str, float | int]:
    seam = (alpha > 0.0) & (alpha < 1.0)
    if not np.any(seam):
        return {
            "seam_pixel_count": 0,
            "delta_e_before_mean": 0.0,
            "delta_e_before_p95": 0.0,
            "delta_e_after_mean": 0.0,
            "delta_e_after_p95": 0.0,
        }
    before_values = residual_before[seam]
    after_values = residual_after[seam]
    return {
        "seam_pixel_count": int(before_values.size),
        "delta_e_before_mean": float(np.mean(before_values)),
        "delta_e_before_p95": float(np.percentile(before_values, 95.0)),
        "delta_e_after_mean": float(np.mean(after_values)),
        "delta_e_after_p95": float(np.percentile(after_values, 95.0)),
    }


def _full_mask(shape: tuple[int, int], roi: tuple[int, int, int, int], local: np.ndarray) -> np.ndarray:
    result = np.zeros(shape, dtype=np.uint8)
    x0, y0, x1, y1 = roi
    result[y0:y1, x0:x1] = np.clip(np.rint(local * 255.0), 0, 255).astype(np.uint8)
    return result


def _full_visual(shape: tuple[int, int], roi: tuple[int, int, int, int], local: np.ndarray) -> np.ndarray:
    result = np.zeros(shape, dtype=np.uint8)
    x0, y0, x1, y1 = roi
    result[y0:y1, x0:x1] = local
    return result


def _preview(before: np.ndarray, after: np.ndarray, roi: tuple[int, int, int, int], config: Mapping[str, Any]) -> Image.Image:
    height, width = before.shape[:2]
    x0, y0, x1, y1 = roi
    padding = int(config["output"]["preview_padding_px"])
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(width, x1 + padding)
    y1 = min(height, y1 + padding)
    left = Image.fromarray(before[y0:y1, x0:x1, :3], mode="RGB")
    right = Image.fromarray(after[y0:y1, x0:x1, :3], mode="RGB")
    canvas = Image.new("RGB", (left.width + right.width, max(left.height, right.height)))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width, 0))
    maximum = int(config["output"]["preview_max_dimension_px"])
    if max(canvas.size) > maximum:
        factor = maximum / max(canvas.size)
        canvas = canvas.resize((max(1, int(round(canvas.width * factor))), max(1, int(round(canvas.height * factor)))), Image.Resampling.LANCZOS)
    return canvas


def _write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _save_png(path: Path, array: np.ndarray, compress_level: int) -> None:
    Image.fromarray(array, mode="L").save(path, format="PNG", compress_level=compress_level, optimize=False)


def _save_result(path: Path, rgba: np.ndarray, source: LoadedImage, config: Mapping[str, Any]) -> None:
    format_name = source.record.format
    mode = source.record.mode
    output = Image.fromarray(rgba if mode == "RGBA" else rgba[:, :, :3], mode=mode)
    options = dict(source.save_info)
    if format_name == "PNG":
        options.update({"compress_level": int(config["output"]["png_compress_level"]), "optimize": False})
    output.save(path, format=format_name, **options)


def _dependency_versions() -> dict[str, str]:
    import PIL
    import scipy

    return {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "Pillow": PIL.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
    }


def _prepare_output_run(output_run: Path) -> tuple[Path, Path]:
    final = output_run.resolve()
    partial = final.with_name(final.name + ".partial")
    if final.exists() or partial.exists():
        raise CompositeError(f"run de sortie déjà présent : {final if final.exists() else partial}")
    final.parent.mkdir(parents=True, exist_ok=True)
    partial.mkdir()
    return final, partial


def _safe_result_relative_path(value: Path) -> Path:
    if value.is_absolute() or not value.parts or any(part in {"", ".", ".."} for part in value.parts):
        raise CompositeError("chemin de résultat relatif et sans .. requis")
    return value


def compose(
    map_path: Path,
    patch_path: Path,
    output_run: Path,
    config_path: Path | None = None,
    *,
    result_relative_path: Path | None = None,
    run_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produit un nouveau run immuable et retourne son manifeste.

    Aucun fichier source n'est écrit. En cas de rejet avant écriture, aucun run n'est créé. En cas
    d'erreur d'écriture, le dossier ``.partial`` reste comme preuve de l'échec.
    """

    config = load_config(config_path)
    map_path = map_path.resolve()
    patch_path = patch_path.resolve()
    if map_path == patch_path:
        raise CompositeError("map et patch doivent être distincts")
    map_image = _load_image(map_path, label="map")
    patch_image = _load_image(patch_path, label="patch")
    if bool(config["output"]["strict_lossless_format"]) and map_image.record.format not in LOSSLESS_FORMATS:
        raise CompositeError(f"format map avec perte refusé en mode strict : {map_image.record.format}")
    initial_map_hash = map_image.record.sha256
    initial_patch_hash = patch_image.record.sha256

    registration = register(map_image.rgba, patch_image.rgba, config)
    if not registration.accepted:
        raise CompositeError("recalage refusé : " + ", ".join(registration.rejection_reasons))
    warped = _warp_patch(patch_image.rgba, registration, map_image.rgba.shape[:2])
    x0, y0, x1, y1 = warped.roi
    map_crop = map_image.rgba[y0:y1, x0:x1]
    color_context = _color_context_mask(warped, patch_image.rgba, config)
    corrected_patch, correction = _fit_color(warped.rgb, map_crop[:, :, :3].astype(np.float32) / 255.0, color_context, config)
    core, residual_before, threshold = _support_mask(corrected_patch, map_crop[:, :, :3].astype(np.float32) / 255.0, warped, patch_image.rgba, config)
    blend = _blend_mask(core, config) * warped.alpha
    result = map_image.rgba.copy()
    composed_rgb = _compose_rgb(map_crop[:, :, :3], corrected_patch, blend)
    write_pixels = blend > 0.0
    roi_result = result[y0:y1, x0:x1]
    roi_result[write_pixels, :3] = composed_rgb[write_pixels]
    result[y0:y1, x0:x1] = roi_result
    outside_local = ~write_pixels
    if not np.array_equal(result[y0:y1, x0:x1][outside_local], map_image.rgba[y0:y1, x0:x1][outside_local]):
        raise CompositeError("invariant : map modifiée hors emprise de fusion")
    if not np.array_equal(result[:y0], map_image.rgba[:y0]) or not np.array_equal(result[y1:], map_image.rgba[y1:]):
        raise CompositeError("invariant : map modifiée hors ROI")
    if not np.array_equal(result[y0:y1, :x0], map_image.rgba[y0:y1, :x0]) or not np.array_equal(result[y0:y1, x1:], map_image.rgba[y0:y1, x1:]):
        raise CompositeError("invariant : map modifiée hors ROI")
    residual_after = np.linalg.norm(rgb_to_lab(composed_rgb.astype(np.float32) / 255.0) - rgb_to_lab(map_crop[:, :, :3].astype(np.float32) / 255.0), axis=2)
    metrics = {
        "registration": asdict(registration),
        "color": asdict(correction),
        "object_mask": {
            "delta_e_threshold": threshold,
            "core_pixel_count": int(np.count_nonzero(core)),
            "blend_pixel_count": int(np.count_nonzero(blend > 0.0)),
            "blend_bbox_map": [x0, y0, x1, y1],
        },
        "output": {
            "changed_pixel_count": int(np.count_nonzero(np.any(result != map_image.rgba, axis=2))),
            "outside_blend_pixel_mismatch_count": 0,
            "width": map_image.record.width,
            "height": map_image.record.height,
            "format": map_image.record.format,
            "mode": map_image.record.mode,
            "pixel_sha256": sha256_pixels(result),
        },
        "seam": _seam_metrics(residual_before, residual_after, blend),
    }

    # Recalcul sans cache : garantit l'absence de mutation concurrente des entrées.
    if sha256_file(map_path) != initial_map_hash or sha256_file(patch_path) != initial_patch_hash:
        raise CompositeError("une entrée a changé pendant le compositing")
    final_run, partial_run = _prepare_output_run(output_run)
    try:
        control_dir = partial_run / "control"
        control_dir.mkdir()
        extension = map_path.suffix.lower() or ".png"
        relative_result = _safe_result_relative_path(
            result_relative_path or Path("result") / f"{map_path.stem}-composited{extension}"
        )
        result_path = partial_run / relative_result
        result_path.parent.mkdir(parents=True, exist_ok=True)
        _save_result(result_path, result, map_image, config)
        object_full = _full_mask(map_image.rgba.shape[:2], warped.roi, core.astype(np.float32))
        blend_full = _full_mask(map_image.rgba.shape[:2], warped.roi, blend)
        before_full = _full_visual(map_image.rgba.shape[:2], warped.roi, _residual_visual(residual_before, blend))
        after_full = _full_visual(map_image.rgba.shape[:2], warped.roi, _residual_visual(residual_after, blend))
        registration_patch = _analysis_mask(patch_image.rgba[:, :, :3], patch_image.rgba[:, :, 3], config["registration"]).astype(np.uint8) * 255
        _save_png(control_dir / "registration-mask-patch.png", registration_patch, int(config["output"]["png_compress_level"]))
        _save_png(control_dir / "object-support-mask-map.png", object_full, int(config["output"]["png_compress_level"]))
        _save_png(control_dir / "blend-mask-map.png", blend_full, int(config["output"]["png_compress_level"]))
        _save_png(control_dir / "residual-before-map.png", before_full, int(config["output"]["png_compress_level"]))
        _save_png(control_dir / "residual-after-map.png", after_full, int(config["output"]["png_compress_level"]))
        _preview(map_image.rgba, result, warped.roi, config).save(control_dir / "before-after-zoom.png", format="PNG", compress_level=int(config["output"]["png_compress_level"]), optimize=False)
        placement = {
            "transform": {
                "map_x_equals": "scale * patch_x + tx",
                "map_y_equals": "scale * patch_y + ty",
                "scale": registration.scale,
                "tx": registration.tx,
                "ty": registration.ty,
                "integer_anchor": [int(round(registration.tx)), int(round(registration.ty))],
                "subpixel_translation": [registration.tx - round(registration.tx), registration.ty - round(registration.ty)],
            },
            "blend_bbox_map": [x0, y0, x1, y1],
        }
        _write_json(control_dir / "placement.json", placement)
        _write_json(control_dir / "metrics.json", metrics)
        _write_json(partial_run / "config.resolved.json", config)
        manifest = {
            "schema": COMPOSITOR_SCHEMA,
            "status": "completed",
            "inputs": {"map": asdict(map_image.record), "patch": asdict(patch_image.record)},
            "configuration": {"schema": CONFIG_SCHEMA, "sha256": sha256_file(partial_run / "config.resolved.json")},
            "algorithm": {
                "registration": "masked-zncc-gradient + robust-similarity-refinement",
                "geometry": "isotropic-scale + translation only",
                "ai_generation": False,
                "dependency_versions": _dependency_versions(),
            },
            "placement": placement,
            "metrics": metrics,
            "outputs": {
                "image": {
                    "path": relative_result.as_posix(),
                    "sha256": sha256_file(result_path),
                    "bytes": result_path.stat().st_size,
                    "pixel_sha256": sha256_pixels(result),
                }
            },
        }
        if run_metadata:
            reserved = set(manifest)
            overlap = reserved.intersection(run_metadata)
            if overlap:
                raise CompositeError("métadonnée de run réservée : " + ", ".join(sorted(overlap)))
            manifest.update(deepcopy(dict(run_metadata)))
        _write_json(partial_run / "run.json", manifest)
        if sha256_file(map_path) != initial_map_hash or sha256_file(patch_path) != initial_patch_hash:
            raise CompositeError("une entrée a changé pendant l'écriture des artefacts")
        os.replace(partial_run, final_run)
        return manifest
    except Exception:
        # La preuve partielle reste volontairement. Aucune source n'est nettoyée/modifiée.
        raise
