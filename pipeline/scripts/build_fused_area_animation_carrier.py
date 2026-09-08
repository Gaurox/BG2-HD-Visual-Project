"""Build one runtime carrier for two already-repaired, world-aligned area animations.

The carrier is intended for areas where separate ARE occurrences use incompatible blend modes.
It composites the x4 textures once off-line, premultiplies the resulting RGB for the ARE Blended
path, patches one Blended occurrence to the new carrier resref, and redirects the superseded
Blended occurrence to a black transparent BAM. A separate strict-alpha occurrence may remain on
its original resref.

The command is plan-only unless ``--run`` is supplied.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bg2lib import load_key, resolve_resource  # noqa: E402
import build_joint_animation_rgb_seam as joint  # noqa: E402
import run_animation_upscale_30fps_v2 as runtime  # noqa: E402


SCHEMA = "bg2-upscale-fused-area-animation-carrier-v1"
AREA_TYPE = 0x03F2
ARE_ANIMATION_SIZE = 76
DEFAULT_CARRIER_RESREF = "AM28ADD"
DEFAULT_NULL_RESREF = "AM28NUL"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_over(bottom: np.ndarray, top: np.ndarray) -> np.ndarray:
    """Composite straight-alpha ``top`` over straight-alpha ``bottom``."""
    require(bottom.shape == top.shape and bottom.ndim == 3 and bottom.shape[2] == 4,
            "canvases RGBA incompatibles")
    lower_alpha = bottom[:, :, 3:4].astype(np.float32) / 255.0
    upper_alpha = top[:, :, 3:4].astype(np.float32) / 255.0
    output_alpha = upper_alpha + lower_alpha * (1.0 - upper_alpha)
    premultiplied = (top[:, :, :3].astype(np.float32) * upper_alpha +
                     bottom[:, :, :3].astype(np.float32) * lower_alpha *
                     (1.0 - upper_alpha))
    straight = np.divide(premultiplied, output_alpha,
                         out=np.zeros_like(premultiplied), where=output_alpha > 1e-7)
    return np.dstack([
        np.clip(np.rint(straight), 0, 255).astype(np.uint8),
        np.clip(np.rint(output_alpha[:, :, 0] * 255.0), 0, 255).astype(np.uint8),
    ])


def premultiply_for_blended(pixels: np.ndarray) -> np.ndarray:
    output = pixels.copy()
    alpha = output[:, :, 3:4].astype(np.float32) / 255.0
    output[:, :, :3] = np.clip(
        np.rint(output[:, :, :3].astype(np.float32) * alpha), 0, 255
    ).astype(np.uint8)
    return output


def place(canvas: np.ndarray, pixels: np.ndarray, layout: joint.FrameLayout,
          left: int, top: int) -> None:
    y = layout.origin_y - top
    x = layout.origin_x - left
    target = canvas[y:y + layout.height, x:x + layout.width]
    canvas[y:y + layout.height, x:x + layout.width] = source_over(target, pixels)


def fuse_frame(top_pixels: np.ndarray, bottom_pixels: np.ndarray, *,
               top_layout: joint.FrameLayout,
               bottom_layout: joint.FrameLayout) -> tuple[np.ndarray, np.ndarray,
                                                           joint.FrameLayout]:
    left = min(top_layout.origin_x, bottom_layout.origin_x)
    upper = min(top_layout.origin_y, bottom_layout.origin_y)
    right = max(top_layout.origin_x + top_layout.width,
                bottom_layout.origin_x + bottom_layout.width)
    lower = max(top_layout.origin_y + top_layout.height,
                bottom_layout.origin_y + bottom_layout.height)
    straight = np.zeros((lower - upper, right - left, 4), dtype=np.uint8)
    place(straight, top_pixels, top_layout, left, upper)
    place(straight, bottom_pixels, bottom_layout, left, upper)
    blended = premultiply_for_blended(straight)
    return straight, blended, joint.FrameLayout(right - left, lower - upper, left, upper)


def extract_area(area: str) -> bytes:
    bif_entries, resources = load_key()
    matches = [(name, locator) for name, resource_type, locator in resources
               if name.upper() == area and resource_type == AREA_TYPE]
    require(len(matches) == 1, f"ressource {area}.ARE absente ou ambiguë")
    resolved = resolve_resource(bif_entries, matches[0][1])
    require(resolved is not None, f"ressource {area}.ARE introuvable dans le BIF")
    payload, _bif = resolved
    require(payload[:8] == b"AREAV1.0", f"format ARE incompatible : {payload[:8]!r}")
    return payload


def are_occurrence(payload: bytes, index: int) -> dict[str, Any]:
    count = struct.unpack_from("<I", payload, 0xAC)[0]
    offset = struct.unpack_from("<I", payload, 0xB0)[0]
    require(0 <= index < count and offset + count * ARE_ANIMATION_SIZE <= len(payload),
            f"occurrence ARE hors limites : {index}")
    entry = offset + index * ARE_ANIMATION_SIZE
    return {
        "offset": entry,
        "name": payload[entry:entry + 32].split(b"\0")[0].decode("cp1252", "replace"),
        "position": list(struct.unpack_from("<hh", payload, entry + 0x20)),
        "resref": payload[entry + 0x28:entry + 0x30].split(b"\0")[0].decode("ascii").upper(),
        "sequence": struct.unpack_from("<H", payload, entry + 0x30)[0],
        "flags": struct.unpack_from("<I", payload, entry + 0x34)[0],
    }


def patch_area(payload: bytes, *, carrier_index: int, null_index: int,
               carrier_resref: str, null_resref: str) -> tuple[bytes, list[dict[str, Any]]]:
    before_carrier = are_occurrence(payload, carrier_index)
    before_null = are_occurrence(payload, null_index)
    require(before_carrier["resref"] == "AM2805B" and
            before_carrier["position"] == [483, 368] and
            before_carrier["flags"] & 1,
            "l'occurrence porteuse Blended AM2805B attendue est absente")
    require(before_null["resref"] == "AM2805C" and
            before_null["position"] == [483, 553] and
            before_null["flags"] & 1,
            "l'occurrence Blended AM2805C attendue est absente")
    output = bytearray(payload)
    for occurrence, resref in ((before_carrier, carrier_resref), (before_null, null_resref)):
        encoded = runtime.normalise_resref(resref).encode("ascii").ljust(8, b"\0")
        output[occurrence["offset"] + 0x28:occurrence["offset"] + 0x30] = encoded
    patched = bytes(output)
    after_carrier = are_occurrence(patched, carrier_index)
    after_null = are_occurrence(patched, null_index)
    for before, after in ((before_carrier, after_carrier), (before_null, after_null)):
        require(before["name"] == after["name"] and
                before["position"] == after["position"] and
                before["sequence"] == after["sequence"] and
                before["flags"] == after["flags"],
                "le patch ARE a modifié un champ autre que le resref BAM")
    changed = np.flatnonzero(np.frombuffer(payload, dtype=np.uint8) !=
                             np.frombuffer(patched, dtype=np.uint8))
    allowed = set(range(before_carrier["offset"] + 0x28,
                        before_carrier["offset"] + 0x30)) | set(
        range(before_null["offset"] + 0x28, before_null["offset"] + 0x30)
    )
    require(set(int(value) for value in changed) <= allowed,
            "octets ARE modifiés hors des deux resrefs")
    return patched, [
        {"index": carrier_index, "before": before_carrier, "after": after_carrier},
        {"index": null_index, "before": before_null, "after": after_null},
    ]


def source_cycles(source_bam: bytes) -> tuple[int, list[tuple[int, int]], bytes]:
    frame_count, cycle_count, transparent = struct.unpack_from("<HBB", source_bam, 8)
    off_frames, _off_palette, off_lookup = struct.unpack_from("<III", source_bam, 0x0C)
    cycle_offset = off_frames + frame_count * 12
    cycles: list[tuple[int, int]] = []
    lookup_count = 0
    for index in range(cycle_count):
        count, start = struct.unpack_from("<HH", source_bam, cycle_offset + index * 4)
        cycles.append((count, start))
        lookup_count = max(lookup_count, start + count)
    lookup = source_bam[off_lookup:off_lookup + lookup_count * 2]
    require(len(lookup) == lookup_count * 2, "lookup BAM source tronqué")
    return transparent, cycles, lookup


def encode_bam(frames: list[np.ndarray], palette_rgb: np.ndarray, *,
               centre: tuple[int, int], cycles: list[tuple[int, int]],
               lookup: bytes, transparent: int = 0) -> bytes:
    require(frames and palette_rgb.shape == (256, 3), "frames ou palette BAM invalides")
    frame_count = len(frames)
    cycle_count = len(cycles)
    off_frames = 24
    cycle_offset = off_frames + frame_count * 12
    off_palette = cycle_offset + cycle_count * 4
    off_lookup = off_palette + 256 * 4
    cursor = off_lookup + len(lookup)
    palette_bgra = np.zeros((256, 4), dtype=np.uint8)
    palette_bgra[:, :3] = palette_rgb[:, ::-1]
    table = bytearray()
    payloads: list[bytes] = []
    for indices in frames:
        height, width = indices.shape
        require(0 < width <= 0xFFFF and 0 < height <= 0xFFFF,
                "dimensions BAM hors limites")
        table.extend(struct.pack("<HHhhI", width, height, centre[0], centre[1],
                                 cursor | 0x80000000))
        raw = indices.astype(np.uint8, copy=False).tobytes(order="C")
        payloads.append(raw)
        cursor += len(raw)
    cycle_table = b"".join(struct.pack("<HH", count, start) for count, start in cycles)
    header = struct.pack("<8sHBBIII", b"BAM V1  ", frame_count, cycle_count, transparent,
                         off_frames, off_palette, off_lookup)
    return b"".join([header, bytes(table), cycle_table, palette_bgra.tobytes(),
                     lookup, *payloads])


def quantized_native_bam(straight_frames: list[np.ndarray], logical_size: tuple[int, int],
                         centre: tuple[int, int], source_bam: bytes) -> bytes:
    native_rgba = [np.asarray(Image.fromarray(frame, "RGBA").resize(
        logical_size, Image.Resampling.LANCZOS), dtype=np.uint8) for frame in straight_frames[:7]]
    sheet_rgb = np.concatenate([frame[:, :, :3] for frame in native_rgba], axis=1)
    quantized = Image.fromarray(sheet_rgb, "RGB").quantize(
        colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
    )
    indices_sheet = np.asarray(quantized, dtype=np.uint8)
    palette_values = np.asarray(quantized.getpalette()[:255 * 3], dtype=np.uint8).reshape(255, 3)
    palette = np.zeros((256, 3), dtype=np.uint8)
    palette[1:] = palette_values
    width, height = logical_size
    frames: list[np.ndarray] = []
    for index, rgba in enumerate(native_rgba):
        indices = indices_sheet[:, index * width:(index + 1) * width].astype(np.uint16) + 1
        indices[rgba[:, :, 3] < 128] = 0
        frames.append(indices.astype(np.uint8))
    _source_transparent, cycles, lookup = source_cycles(source_bam)
    require(sum(count for count, _start in cycles) == 7,
            "le BAM source doit exposer les sept frames natives")
    return encode_bam(frames, palette, centre=centre, cycles=cycles, lookup=lookup)


def null_bam(source_bam: bytes) -> bytes:
    _source_transparent, cycles, lookup = source_cycles(source_bam)
    frame_count = sum(count for count, _start in cycles)
    frames = [np.zeros((1, 1), dtype=np.uint8) for _ in range(frame_count)]
    return encode_bam(frames, np.zeros((256, 3), dtype=np.uint8), centre=(0, 0),
                      cycles=cycles, lookup=lookup)


def carrier_resource(source: joint.PackInput, pixels: list[np.ndarray], *,
                     resref: str, position: tuple[int, int],
                     logical_size: tuple[int, int], centre: tuple[int, int]) -> dict[str, Any]:
    resource = copy.deepcopy(source.resource)
    resource["resref"] = runtime.normalise_resref(resref)
    resource["position"] = list(position)
    resource["variant_index"] = 0
    frames = joint.sorted_frames(resource)
    assets = []
    for frame, frame_pixels in zip(frames, pixels, strict=True):
        name = runtime.asset_name(resref, int(frame["frame"]), 0)
        payload = frame_pixels.tobytes(order="C")
        frame["logical_size_x1"] = list(logical_size)
        frame["physical_size_x4"] = [logical_size[0] * 4, logical_size[1] * 4]
        frame["centre_x1"] = list(centre)
        frame["asset"] = name
        frame["sha256"] = sha256_bytes(payload)
        frame["bytes"] = len(payload)
        assets.append({"name": name, "sha256": frame["sha256"], "bytes": len(payload)})
    resource["frames"] = frames
    resource["assets"] = assets
    return resource


def write_runtime_pack(destination: Path, source: joint.PackInput,
                       resource: dict[str, Any], pixels: list[np.ndarray],
                       provenance: dict[str, Any]) -> dict[str, Any]:
    destination.mkdir(parents=True)
    registry = runtime.registry_v2_from_resources([resource], runtime.REGISTRY_VERSION)
    registry_path = destination / runtime.REGISTRY_NAME
    registry_path.write_bytes(registry)
    for frame, frame_pixels in zip(joint.sorted_frames(resource), pixels, strict=True):
        (destination / str(frame["asset"])).write_bytes(frame_pixels.tobytes(order="C"))
    manifest = copy.deepcopy(source.manifest)
    manifest.update({
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "registry_version": runtime.REGISTRY_VERSION,
        "registry": runtime.REGISTRY_NAME,
        "registry_sha256": runtime.sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": 1,
        "frame_count": int(resource["frame_count"]),
        "timed_resources": [str(resource["resref"])],
        "timed_resource_variants": [runtime.resource_identity(resource)],
        "raw_bytes": sum(int(asset["bytes"]) for asset in resource["assets"]),
        "runtime_budget_enforced": True,
        "authoring_pack_for_area_split": True,
        "base_assets": [],
        "new_assets": copy.deepcopy(resource["assets"]),
        "resources": [resource],
        "fused_carrier": provenance,
    })
    runtime.write_json(destination / "manifest.json", manifest)
    runtime.validate_v2_pack(destination)
    return manifest


def write_review(path: Path, straight_frames: list[np.ndarray]) -> None:
    previews = []
    for frame in straight_frames:
        image = Image.new("RGB", (frame.shape[1], frame.shape[0]), (45, 55, 55))
        rgba = Image.fromarray(frame, "RGBA")
        image.paste(rgba, mask=rgba.getchannel("A"))
        scale = min(1.0, 420.0 / image.width)
        previews.append(image.resize((round(image.width * scale), round(image.height * scale)),
                                     Image.Resampling.LANCZOS))
    columns = 7
    gap, label = 8, 18
    width = columns * previews[0].width + (columns + 1) * gap
    height = 2 * (previews[0].height + label) + 3 * gap
    sheet = Image.new("RGB", (width, height), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)
    for index, preview in enumerate(previews):
        x = gap + (index % columns) * (preview.width + gap)
        y = gap + (index // columns) * (preview.height + label + gap)
        draw.text((x, y), f"phase {index:02d}", fill=(235, 235, 235))
        sheet.paste(preview, (x, y + label))
    path.parent.mkdir(parents=True)
    sheet.save(path, format="PNG", optimize=True)


def build(top_pack: Path, bottom_pack: Path, output: Path, *,
          top_position: tuple[int, int], bottom_position: tuple[int, int],
          top_source_bam: Path, bottom_source_bam: Path, area: str,
          carrier_resref: str, null_resref: str,
          carrier_occurrence: int, null_occurrence: int, write: bool) -> dict[str, Any]:
    top = joint.load_single_resource_pack(top_pack, top_position)
    bottom = joint.load_single_resource_pack(bottom_pack, bottom_position)
    joint.compatible_timeline(top.resource, bottom.resource)
    top_frames = joint.sorted_frames(top.resource)
    bottom_frames = joint.sorted_frames(bottom.resource)
    require(len(top_frames) == len(bottom_frames) == 14, "quatorze phases B/C requises")
    area_payload = extract_area(area)
    patched_area, patches = patch_area(
        area_payload, carrier_index=carrier_occurrence, null_index=null_occurrence,
        carrier_resref=carrier_resref, null_resref=null_resref,
    )
    top_bam = joint.read_bam(top_source_bam)
    bottom_bam = joint.read_bam(bottom_source_bam)
    plan = {
        "schema": SCHEMA,
        "status": "planned",
        "area": area,
        "carrier_resref": carrier_resref,
        "null_resref": null_resref,
        "inputs": {
            "top_pack": top.root.as_posix(),
            "top_pack_manifest_sha256": runtime.sha256_file(top.root / "manifest.json"),
            "bottom_pack": bottom.root.as_posix(),
            "bottom_pack_manifest_sha256": runtime.sha256_file(bottom.root / "manifest.json"),
            "top_source_bam": top_source_bam.resolve().as_posix(),
            "top_source_bam_sha256": sha256_bytes(top_bam),
            "bottom_source_bam": bottom_source_bam.resolve().as_posix(),
            "bottom_source_bam_sha256": sha256_bytes(bottom_bam),
            "area_source_sha256": sha256_bytes(area_payload),
        },
        "occurrence_patches": patches,
        "policy": {
            "carrier_occurrence": "existing-Blended-AM2805B",
            "strict_AM2805B_occurrence": "unchanged",
            "superseded_AM2805C_occurrence": "black-transparent-native-BAM",
            "fusion": "offline-source-over-on-shared-world-canvas",
            "carrier_rgb": "premultiplied-by-final-alpha-for-Blended-path",
            "runtime_overlap": "none-single-carrier-draw",
        },
        "output": output.resolve().as_posix(),
    }
    if not write:
        return plan
    require(not output.exists(), f"sortie déjà présente : {output}")
    partial = output.with_name(output.name + ".partial")
    require(not partial.exists(), f"sortie partielle présente : {partial}")
    straight_frames: list[np.ndarray] = []
    blended_frames: list[np.ndarray] = []
    layouts: list[joint.FrameLayout] = []
    for top_frame, bottom_frame in zip(top_frames, bottom_frames, strict=True):
        top_layout = joint.frame_layout(top_frame, top.position_x1)
        bottom_layout = joint.frame_layout(bottom_frame, bottom.position_x1)
        top_pixels = joint.read_rgba(top.root / str(top_frame["asset"]), top_layout)
        bottom_pixels = joint.read_rgba(bottom.root / str(bottom_frame["asset"]), bottom_layout)
        straight, blended, layout = fuse_frame(
            top_pixels, bottom_pixels, top_layout=top_layout, bottom_layout=bottom_layout
        )
        straight_frames.append(straight)
        blended_frames.append(blended)
        layouts.append(layout)
    require(len(set(layouts)) == 1, "géométrie fusionnée non uniforme")
    layout = layouts[0]
    require(layout.width % 4 == layout.height % 4 == layout.origin_x % 4 == layout.origin_y % 4 == 0,
            "canvas fusionné non aligné sur la grille x1")
    logical_size = (layout.width // 4, layout.height // 4)
    centre = (top_position[0] - layout.origin_x // 4,
              top_position[1] - layout.origin_y // 4)
    resource = carrier_resource(top, blended_frames, resref=carrier_resref,
                                position=top_position, logical_size=logical_size, centre=centre)
    carrier_bam = quantized_native_bam(straight_frames, logical_size, centre, top_bam)
    black_bam = null_bam(bottom_bam)
    partial.mkdir(parents=True)
    runtime_manifest = write_runtime_pack(
        partial / carrier_resref / "03_runtime_pack", top, resource, blended_frames,
        {"schema": SCHEMA, "area": area, "world_rect_x4": [layout.origin_x, layout.origin_y,
                                                              layout.origin_x + layout.width,
                                                              layout.origin_y + layout.height],
         "source_packs": [top.root.as_posix(), bottom.root.as_posix()]},
    )
    override = partial / "override-assets"
    override.mkdir()
    files = {
        f"{area}.ARE": patched_area,
        f"{carrier_resref}.BAM": carrier_bam,
        f"{null_resref}.BAM": black_bam,
        "AM2805B.BAM": top_bam,
        "AM2805C.BAM": bottom_bam,
    }
    for name, payload in files.items():
        (override / name).write_bytes(payload)
    override_manifest = {
        "schema": "bg2-upscale-area-animation-override-assets-v1",
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "area": area,
        "files": {name: {"bytes": len(payload), "sha256": sha256_bytes(payload)}
                  for name, payload in files.items()},
        "occurrence_patches": patches,
        "invariants": {
            "ARE_changes_limited_to_resrefs": True,
            "strict_AM2805B_occurrence_unchanged": True,
            "original_AM2805B_and_AM2805C_BAMs_restored": True,
        },
    }
    runtime.write_json(override / "manifest.json", override_manifest)
    write_review(partial / "review" / "fused-carrier-contact-sheet.png", straight_frames)
    completed = copy.deepcopy(plan)
    completed.update({
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "geometry": {
            "logical_size_x1": list(logical_size),
            "physical_size_x4": [layout.width, layout.height],
            "centre_x1": list(centre),
            "world_rect_x4": [layout.origin_x, layout.origin_y,
                               layout.origin_x + layout.width,
                               layout.origin_y + layout.height],
        },
        "runtime_pack": f"{carrier_resref}/03_runtime_pack",
        "runtime_pack_manifest_sha256": runtime.sha256_file(
            partial / carrier_resref / "03_runtime_pack" / "manifest.json"
        ),
        "override_manifest_sha256": runtime.sha256_file(override / "manifest.json"),
        "native_carrier_bam_sha256": sha256_bytes(carrier_bam),
        "native_null_bam_sha256": sha256_bytes(black_bam),
        "area_override_sha256": sha256_bytes(patched_area),
        "qa_status": "pending-explicit-user-approval",
    })
    runtime.write_json(partial / "manifest.json", completed)
    partial.replace(output)
    return completed


def parse_position(value: str) -> tuple[int, int]:
    return joint.parse_position(value)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-pack", type=Path, required=True)
    parser.add_argument("--bottom-pack", type=Path, required=True)
    parser.add_argument("--top-position", type=parse_position, required=True)
    parser.add_argument("--bottom-position", type=parse_position, required=True)
    parser.add_argument("--top-source-bam", type=Path, required=True)
    parser.add_argument("--bottom-source-bam", type=Path, required=True)
    parser.add_argument("--area", default="AR2804")
    parser.add_argument("--carrier-resref", default=DEFAULT_CARRIER_RESREF)
    parser.add_argument("--null-resref", default=DEFAULT_NULL_RESREF)
    parser.add_argument("--carrier-occurrence", type=int, default=1)
    parser.add_argument("--null-occurrence", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    report = build(
        args.top_pack, args.bottom_pack, args.output,
        top_position=args.top_position, bottom_position=args.bottom_position,
        top_source_bam=args.top_source_bam, bottom_source_bam=args.bottom_source_bam,
        area=args.area.upper(), carrier_resref=runtime.normalise_resref(args.carrier_resref),
        null_resref=runtime.normalise_resref(args.null_resref),
        carrier_occurrence=args.carrier_occurrence, null_occurrence=args.null_occurrence,
        write=args.run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
