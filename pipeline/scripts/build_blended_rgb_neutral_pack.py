"""Derive a split-root whose targeted resources carry no colour under a zero alpha.

Why this exists: an area animation whose ARE flags set bit 1 ("Blended") is not composited
with strict alpha. In that mode black is the transparent value and the RGB channels are added
to the scene, so a texel with `alpha == 0` still contributes its colour. The x1 BAM never
suffered from this because the engine's CPU compositor skips the palette's transparent index
outright; our replacement is a full RGBA GL texture, so every texel reaches the blend.

That turns SeedVR's behaviour into a visible defect. The model only ever sees the RGB plane,
where the transparent region is the palette's flat chroma green, and it hallucinates structure
into it. On `AM0900DM` (AR0900) the result was a translucent 249x185 rectangle of grey-blue
streaks drawn around the ring. The alpha plane was provably correct — strictly binary, right
dimensions — so no alpha-side correction could have removed it, which is why
`ANIMATION_ALPHA_CORRECTIONS.md` (RGB preserved byte for byte) does not cover this class.

Forcing `RGB = 0` wherever `alpha == 0` restores the engine's own "black is transparent"
semantics. It is the neutral element of the blended path and a no-op for the strict-alpha path,
where those texels are discarded anyway, so it is safe for every resource regardless of flags.
It also removes the colour that GL_LINEAR would otherwise bleed inwards across the alpha edge.

This never touches the game, the DLL, INI, override, the input split-root or any catalogue: it
writes a new split-root beside the old one. The alpha plane is asserted unchanged byte for byte.

Two rules are available, because a soft alpha needs more than the binary one:

  - ``--mode zero`` sets `RGB = 0` where `alpha == 0`. Correct and sufficient while the alpha
    plane is strictly binary, which is what a nearest-neighbour upscale of a BAM mask yields.
  - ``--mode premultiply`` sets `RGB = RGB * alpha / 255` everywhere. Once a feather introduces
    intermediate alpha, zeroing is no longer enough: on the blended path a half-transparent
    texel would still add its full colour, so the ramp would read as a bright halo instead of a
    fade. Premultiplication is the general form and subsumes the zero rule at `alpha == 0`.

``--mask-png`` applies a hand-painted foreground mask anchored in world space. The engine's own
occlusion for these resources comes from WED polygons rasterised during the CPU FX composition,
which our replacement texture bypasses entirely — so a map element that should pass in front of
the animation is simply drawn under it. Baking the occluder into the alpha reproduces the effect
without touching the engine. The PNG's alpha channel is read as foreground coverage (painted =
occluded = animation removed), and it is re-projected onto every frame from that frame's own BAM
centre, because the frames differ in both size and anchor. The same ``--mask-anchor-x1`` value is
written into registry v3 as the exact position of the occurrence for which these pixels are valid.

``--feather-proto`` additionally swaps in the alpha plane of a completed `build_alpha_feather.py`
prototype before the rule is applied. The prototype's `source_runtime_sha256` must match the
asset it claims to derive from, so a feather computed against different pixels cannot be grafted
onto this pack unnoticed.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402
from build_alpha_feather import inner_feather_ramp  # noqa: E402

RULES = {"zero": "rgb=0 where alpha==0", "premultiply": "rgb=rgb*alpha/255"}
FEATHER_SCHEMA = "bg2-upscale-animation-alpha-feather-test-v1"
OCCLUSION_MASK_STORAGE = "split-root-relative-v1"
OCCLUSION_MASK_ROOT_PATH = "provenance/occlusion-mask.png"
OCCLUSION_MASK_AREA_PATH = "../provenance/occlusion-mask.png"


def load_feather_proto(proto_dir: Path, resref: str) -> dict[int, dict[str, Any]]:
    """Index a completed alpha-feather prototype by frame, after checking it is one."""
    manifest = v2.load_json(proto_dir / "manifest.json")
    v2.require(manifest.get("schema") == FEATHER_SCHEMA
               and manifest.get("status") == "completed"
               and int(manifest.get("scale", 0)) == 4
               and v2.normalise_resref(str(manifest.get("resref", ""))) == resref,
               f"prototype de fondu alpha incompatible : {proto_dir}")
    frames = {int(frame["frame"]): frame for frame in manifest.get("frames") or []}
    v2.require(len(frames) == int(manifest.get("frame_count", -1)),
               f"inventaire de frames incohérent : {proto_dir}")
    return frames


def read_feather_buffer(proto_dir: Path, frame: dict[str, Any], source_digest: str,
                        expected_bytes: int) -> bytes:
    """Return the prototype's buffer for one frame, refusing a foreign lineage."""
    v2.require(str(frame.get("source_runtime_sha256", "")).lower() == source_digest,
               f"le fondu ne dérive pas de ce buffer (frame {frame.get('frame')})")
    name = str(frame.get("runtime_asset", ""))
    path = (proto_dir / name).resolve()
    try:
        path.relative_to(proto_dir.resolve())
    except ValueError as exc:
        raise RuntimeError(f"asset de fondu hors prototype : {name}") from exc
    v2.require(path.is_file() and path.stat().st_size == expected_bytes
               and int(frame.get("runtime_bytes", -1)) == expected_bytes
               and v2.sha256_file(path) == str(frame.get("runtime_sha256", "")).lower(),
               f"asset de fondu incohérent : {path}")
    return path.read_bytes()


def decode_occlusion_mask(data: bytes, source: object) -> np.ndarray:
    """Decode a hand-painted PNG as occlusion coverage in [0,1].

    Project convention (`ANIMATION_ALPHA_CORRECTIONS.md`): white keeps, black removes, grey
    is a transition. The signal is therefore the luminance, and the file must be flattened —
    a mask whose shape lives in its alpha channel is refused rather than silently inverted,
    because the two encodings mean the exact opposite of one another.
    """
    with Image.open(io.BytesIO(data)) as image:
        v2.require(image.format == "PNG", f"masque d'occlusion non PNG : {source}")
        pixels = np.asarray(image.convert("RGBA"), dtype=np.float32)
    v2.require(bool((pixels[..., 3] == 255).all()),
               f"masque non aplati : le tracé doit être en niveaux de gris opaques, "
               f"blanc = conserver, noir = retirer ({source})")
    return 1.0 - pixels[..., :3].mean(axis=2) / 255.0


def load_occlusion_mask(path: Path) -> np.ndarray:
    """Read a hand-painted foreground mask as occlusion coverage in [0,1]."""
    return decode_occlusion_mask(path.read_bytes(), path)


def occlusion_mask_record(source: str, digest: str, mask_origin_x4: tuple[int, int],
                          mask_anchor_x1: tuple[int, int]) -> dict[str, Any]:
    """Return the portable provenance record used by new split-root outputs."""
    return {
        "storage": OCCLUSION_MASK_STORAGE,
        "source": source,
        "sha256": digest,
        "origin_x4": [int(mask_origin_x4[0]), int(mask_origin_x4[1])],
        "anchor_x1": [int(mask_anchor_x1[0]), int(mask_anchor_x1[1])],
        "semantics": "flattened grayscale; white keeps, black removes",
    }


def validate_sealed_occlusion_mask(record: object, manifest_dir: Path, split_root: Path,
                                   expected_source: str) -> str | None:
    """Validate new embedded-mask records; leave unversioned legacy records readable."""
    if not isinstance(record, dict) or "storage" not in record:
        return None
    v2.require(record.get("storage") == OCCLUSION_MASK_STORAGE,
               f"stockage de masque d'occlusion inconnu : {record.get('storage')}")
    source = str(record.get("source", ""))
    v2.require(source == expected_source,
               f"chemin de masque d'occlusion non canonique : {source}")
    source_path = (manifest_dir / source).resolve()
    try:
        source_path.relative_to(split_root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"masque d'occlusion hors split-root : {source}") from exc
    v2.require(source_path.is_file(), f"masque d'occlusion scellé absent : {source_path}")
    digest = v2.sha256_file(source_path)
    v2.require(str(record.get("sha256", "")).lower() == digest,
               f"hash du masque d'occlusion incohérent : {source_path}")
    return digest


def validate_embedded_mask_provenance(split_root: Path, index: dict[str, Any]) -> None:
    """Validate every versioned mask link while accepting legacy absolute-source records."""
    root_record = (index.get("rgb_neutralisation") or {}).get("occlusion_mask")
    root_digest = validate_sealed_occlusion_mask(
        root_record, split_root, split_root, OCCLUSION_MASK_ROOT_PATH)
    area_digests: list[str] = []
    for entry in index.get("areas") or []:
        area_dir = split_root / str(entry["directory"])
        manifest, _resources = v2.validate_v2_pack(area_dir)
        area_record = (manifest.get("rgb_neutralisation") or {}).get("occlusion_mask")
        digest = validate_sealed_occlusion_mask(
            area_record, area_dir, split_root, OCCLUSION_MASK_AREA_PATH)
        if digest is not None:
            area_digests.append(digest)
    if root_digest is None:
        v2.require(not area_digests,
                   "provenance de masque scellée présente dans une zone mais absente de l'index")
    else:
        v2.require(bool(area_digests) and all(digest == root_digest for digest in area_digests),
                   "provenance de masque scellée incohérente entre index et zones")


def frame_occlusion(mask: np.ndarray, mask_origin_x4: tuple[int, int],
                    frame_origin_x4: tuple[int, int], width: int, height: int) -> np.ndarray:
    """Cut this frame's window out of the world-anchored mask; outside it nothing is occluded."""
    window = np.zeros((height, width), dtype=np.float32)
    dx = frame_origin_x4[0] - mask_origin_x4[0]
    dy = frame_origin_x4[1] - mask_origin_x4[1]
    sx0, sy0 = max(0, dx), max(0, dy)
    sx1 = min(mask.shape[1], dx + width)
    sy1 = min(mask.shape[0], dy + height)
    if sx1 > sx0 and sy1 > sy0:
        window[sy0 - dy:sy1 - dy, sx0 - dx:sx1 - dx] = mask[sy0:sy1, sx0:sx1]
    return window


def write_blend_safe_asset(path: Path, width: int, height: int, mode: str,
                           replacement: bytes | None, feather_radius: float = 0.0,
                           occlusion: np.ndarray | None = None) -> int:
    """Rewrite one raw RGBA8 buffer so its colour is safe for the blended path.

    `replacement`, when given, supplies the buffer (feathered alpha + untouched RGB) instead
    of the file's current contents. Returns the number of texels whose colour changed. The
    alpha plane of whatever buffer is used is asserted to survive the rule untouched: this
    correction owns the colour channels only.
    """
    expected = width * height * 4
    raw = replacement if replacement is not None else path.read_bytes()
    v2.require(len(raw) == expected,
               f"taille de buffer inattendue ({len(raw)} != {expected}) : {path}")

    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4).copy()
    alpha = pixels[..., 3].copy()
    rgb_before = pixels[..., :3].copy()

    if feather_radius > 0:
        # Reuse build_alpha_feather's ramp rather than restating it: the visual result must
        # stay the one validated through that tool, and its `final <= source` rule with it.
        source_alpha = alpha
        alpha = np.rint(source_alpha.astype(np.float32)
                        * inner_feather_ramp(source_alpha, feather_radius)).astype(np.uint8)
        v2.require(bool(np.all(alpha <= source_alpha)),
                   f"alpha étendu hors du masque source : {path}")
        pixels[..., 3] = alpha

    if occlusion is not None:
        source_alpha = alpha
        alpha = np.rint(source_alpha.astype(np.float32) * (1.0 - occlusion)).astype(np.uint8)
        v2.require(bool(np.all(alpha <= source_alpha)),
                   f"le masque a augmenté l'alpha : {path}")
        pixels[..., 3] = alpha

    if mode == "zero":
        pixels[(alpha == 0) & (rgb_before.max(axis=2) > 0), 0:3] = 0
    else:
        scaled = np.rint(rgb_before.astype(np.float32) * (alpha[..., None] / 255.0))
        pixels[..., :3] = np.clip(scaled, 0, 255).astype(np.uint8)

    v2.require(np.array_equal(pixels[..., 3], alpha),
               f"le canal alpha a été modifié, ce qui est interdit : {path}")
    path.write_bytes(pixels.tobytes())
    return int((pixels[..., :3] != rgb_before).any(axis=2).sum())


def neutralise_area(area_dir: Path, targets: set[str], mode: str,
                    proto_dir: Path | None, feather_radius: float = 0.0,
                    mask: np.ndarray | None = None,
                    mask_origin_x4: tuple[int, int] = (0, 0),
                    mask_anchor_x1: tuple[int, int] = (0, 0)) -> dict[str, Any]:
    """Rewrite one area pack's targeted assets and re-hash its manifest."""
    manifest = v2.load_json(area_dir / "manifest.json")
    frames_changed = 0
    pixels_changed = 0
    touched: list[str] = []

    for resource in manifest.get("resources") or []:
        resref = v2.normalise_resref(str(resource["resref"]))
        if resref not in targets:
            continue
        touched.append(resref)
        if mask is not None:
            resource["position"] = [int(mask_anchor_x1[0]), int(mask_anchor_x1[1])]
            resource["variant_index"] = 0
        proto_frames = load_feather_proto(proto_dir, resref) if proto_dir else None
        if proto_frames is not None:
            v2.require(len(proto_frames) == int(resource["frame_count"]),
                       f"{resref}: le fondu ne couvre pas les {resource['frame_count']} frames")
        assets_by_name = {str(asset["name"]): asset for asset in resource["assets"]}
        for frame in sorted(resource["frames"], key=lambda item: int(item["frame"])):
            width, height = (int(value) for value in frame["physical_size_x4"])
            asset_path = area_dir / str(frame["asset"])
            replacement = None
            if proto_frames is not None:
                index = int(frame["frame"])
                v2.require(index in proto_frames, f"{resref}: frame {index} absente du fondu")
                replacement = read_feather_buffer(proto_dir, proto_frames[index],
                                                  str(frame["sha256"]).lower(), int(frame["bytes"]))
            occlusion = None
            if mask is not None:
                cx, cy = (int(value) for value in frame["centre_x1"])
                origin = ((mask_anchor_x1[0] - cx) * 4, (mask_anchor_x1[1] - cy) * 4)
                occlusion = frame_occlusion(mask, mask_origin_x4, origin, width, height)
            changed = write_blend_safe_asset(asset_path, width, height, mode, replacement,
                                             feather_radius, occlusion)
            if changed:
                frames_changed += 1
                pixels_changed += changed
            digest = v2.sha256_file(asset_path)
            size = asset_path.stat().st_size
            # frames[] and assets[] carry the same hash for a frame; both are validated.
            frame["sha256"] = digest
            frame["bytes"] = size
            asset = assets_by_name[str(frame["asset"])]
            asset["sha256"] = digest
            asset["bytes"] = size

    return {"manifest": manifest, "resrefs": sorted(touched),
            "frames_changed": frames_changed, "pixels_changed": pixels_changed}


def build(split_root: Path, output: Path, resrefs: set[str], resume: bool,
          mode: str, proto_dir: Path | None, feather_radius: float = 0.0,
          mask: np.ndarray | None = None, mask_origin_x4: tuple[int, int] = (0, 0),
          mask_anchor_x1: tuple[int, int] = (0, 0),
          mask_source: Path | None = None) -> dict[str, Any]:
    split_root = split_root.resolve()
    output = output.resolve()
    index = v2.load_json(split_root / "manifest.json")
    v2.require(index.get("schema") == splitter.INDEX_SCHEMA and index.get("status") == "completed",
               f"index de découpage incompatible : {split_root}")

    # The source must be intact before anything is copied: a defect inherited silently here
    # would be indistinguishable from one this correction introduced.
    for entry in index.get("areas") or []:
        v2.validate_v2_pack(split_root / str(entry["directory"]))

    available = {v2.normalise_resref(str(resref))
                 for entry in index.get("areas") or [] for resref in entry.get("resrefs") or []}
    missing = sorted(resrefs - available)
    v2.require(not missing, f"resref absent du split-root source : {', '.join(missing)}")
    if mask is not None:
        matching_areas = [str(entry["area_id"]) for entry in index.get("areas") or []
                          if resrefs & {v2.normalise_resref(str(value))
                                       for value in entry.get("resrefs") or []}]
        v2.require(len(matching_areas) == 1,
                   "un masque ancré ne peut cibler qu'une zone par dérivation : "
                   f"{matching_areas}")

    if output.exists():
        v2.require(resume, f"sortie déjà présente sans --resume : {output}")
        existing = v2.load_json(output / "manifest.json")
        validate_embedded_mask_provenance(output, existing)
        return existing

    mask_bytes: bytes | None = None
    mask_digest: str | None = None
    if mask is not None:
        v2.require(mask_source is not None, "un masque d'occlusion exige sa source à sceller")
        source_path = mask_source.resolve()
        v2.require(source_path.is_file(), f"masque d'occlusion source absent : {source_path}")
        mask_bytes = source_path.read_bytes()
        source_mask = decode_occlusion_mask(mask_bytes, source_path)
        v2.require(mask.shape == source_mask.shape and np.array_equal(mask, source_mask),
                   "le masque appliqué ne correspond pas à la source à sceller")
        mask_digest = hashlib.sha256(mask_bytes).hexdigest()
    else:
        v2.require(mask_source is None, "source de masque fournie sans masque d'occlusion")

    shutil.copytree(split_root, output, ignore=shutil.ignore_patterns("install-backups"))
    if mask_bytes is not None and mask_digest is not None:
        embedded_mask = output / OCCLUSION_MASK_ROOT_PATH
        embedded_mask.parent.mkdir(parents=True, exist_ok=True)
        embedded_mask.write_bytes(mask_bytes)
        v2.require(v2.sha256_file(embedded_mask) == mask_digest,
                   f"copie scellée du masque incohérente : {embedded_mask}")

    entries = []
    total_frames = 0
    total_pixels = 0
    for entry in sorted(index.get("areas") or [], key=lambda item: str(item["area_id"])):
        area_dir = output / str(entry["directory"])
        result = neutralise_area(area_dir, resrefs, mode, proto_dir, feather_radius,
                                 mask, mask_origin_x4, mask_anchor_x1)
        manifest = result["manifest"]
        if result["resrefs"]:
            manifest["rgb_neutralisation"] = {
                "rule": RULES[mode],
                "alpha_source": (proto_dir.as_posix() if proto_dir
                                 else (f"fondu intérieur {feather_radius} px x4" if feather_radius
                                       else "pack source (inchangé)")),
                "reason": "blended area animations add RGB regardless of alpha",
                "resrefs": result["resrefs"],
                "frames_changed": result["frames_changed"],
                "pixels_changed": result["pixels_changed"],
                "applied_utc": v2.utc_now(),
                "source_pack": (split_root / str(entry["directory"])).as_posix(),
                "source_manifest_sha256": str(entry["manifest_sha256"]).lower(),
            }
            if mask is not None:
                manifest["rgb_neutralisation"]["occurrence_position"] = [
                    int(mask_anchor_x1[0]), int(mask_anchor_x1[1])]
                if mask_digest is not None:
                    manifest["rgb_neutralisation"]["occlusion_mask"] = occlusion_mask_record(
                        OCCLUSION_MASK_AREA_PATH, mask_digest, mask_origin_x4, mask_anchor_x1)
                manifest["registry_version"] = v2.REGISTRY_VERSION
                manifest["runtime_contract"]["registry_version"] = v2.REGISTRY_VERSION
                registry = v2.registry_v2_from_resources(manifest["resources"])
                registry_path = area_dir / v2.REGISTRY_NAME
                registry_path.write_bytes(registry)
                manifest["registry_sha256"] = v2.sha256_file(registry_path)
                manifest["registry_bytes"] = registry_path.stat().st_size
        v2.write_json(area_dir / "manifest.json", manifest)
        v2.validate_v2_pack(area_dir)

        total_frames += result["frames_changed"]
        total_pixels += result["pixels_changed"]
        entry = dict(entry)
        entry["manifest_sha256"] = v2.sha256_file(area_dir / "manifest.json")
        entry["rgb_neutralised_resrefs"] = result["resrefs"]
        entries.append(entry)

    new_index = dict(index)
    new_index["created_utc"] = v2.utc_now()
    new_index["areas"] = entries
    new_index["rgb_neutralisation"] = {
        "rule": RULES[mode],
        "alpha_source": (proto_dir.as_posix() if proto_dir
                         else (f"fondu intérieur {feather_radius} px x4" if feather_radius
                               else "pack source (inchangé)")),
        "requested_resrefs": sorted(resrefs),
        "frames_changed": total_frames,
        "pixels_changed": total_pixels,
        "source_split_root": split_root.as_posix(),
    }
    if mask_digest is not None:
        new_index["rgb_neutralisation"]["occlusion_mask"] = occlusion_mask_record(
            OCCLUSION_MASK_ROOT_PATH, mask_digest, mask_origin_x4, mask_anchor_x1)
    v2.write_json(output / "manifest.json", new_index)
    validate_embedded_mask_provenance(output, new_index)
    return new_index


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split-root", type=Path, required=True,
                        help="split-root produit par split_animation_pack_by_area.py")
    parser.add_argument("--output", type=Path, required=True,
                        help="nouveau split-root ; le source n'est jamais modifié")
    parser.add_argument("--resref", action="append", required=True, dest="resrefs",
                        help="resref à neutraliser ; répétable")
    parser.add_argument("--mode", choices=sorted(RULES), default="zero",
                        help="zero : rgb=0 sous alpha nul (alpha binaire) ; "
                             "premultiply : rgb*=alpha/255 (obligatoire si l'alpha est dégradé)")
    parser.add_argument("--feather-proto", type=Path, default=None,
                        help="prototype build_alpha_feather.py dont l'alpha remplace celui du pack")
    parser.add_argument("--inner-feather-x4", type=float, default=0.0,
                        help="applique le fondu de silhouette de build_alpha_feather.py à chaque "
                             "frame, rayon en px x4 ; impose --mode premultiply")
    parser.add_argument("--mask-png", type=Path, default=None,
                        help="masque aplati ; blanc conserve, noir retire l'animation")
    parser.add_argument("--mask-origin-x4", type=int, nargs=2, metavar=("X", "Y"),
                        help="coin haut-gauche du masque en pixels monde x4")
    parser.add_argument("--mask-anchor-x1", type=int, nargs=2, metavar=("X", "Y"),
                        help="position monde x1 de l'occurrence sur laquelle le masque a été peint")
    parser.add_argument("--resume", action="store_true",
                        help="revalider une sortie existante sans réécrire")
    args = parser.parse_args(argv)

    resrefs = {v2.normalise_resref(str(value)) for value in args.resrefs}
    if (args.feather_proto is not None or args.inner_feather_x4 > 0) and args.mode != "premultiply":
        raise SystemExit("un alpha dégradé impose --mode premultiply")
    if args.feather_proto is not None and args.inner_feather_x4 > 0:
        raise SystemExit("--feather-proto et --inner-feather-x4 s'excluent")
    mask = None
    if args.mask_png is not None:
        if args.mask_origin_x4 is None or args.mask_anchor_x1 is None:
            raise SystemExit("--mask-png exige --mask-origin-x4 et --mask-anchor-x1")
        if args.mode != "premultiply":
            raise SystemExit("un masque impose --mode premultiply")
        mask = load_occlusion_mask(args.mask_png)
    index = build(args.split_root, args.output, resrefs, args.resume,
                  args.mode, args.feather_proto, args.inner_feather_x4,
                  mask, tuple(args.mask_origin_x4 or (0, 0)), tuple(args.mask_anchor_x1 or (0, 0)),
                  args.mask_png)
    summary = {key: value for key, value in index.items() if key != "areas"}
    summary["areas_list"] = [item["area_id"] for item in index["areas"]]
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
