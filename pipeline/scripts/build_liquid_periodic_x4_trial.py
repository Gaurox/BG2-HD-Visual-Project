"""Build isolated x4 liquid overlay trials; no WED mutation or installation.

Stages: prepare -> generate -> build. Native tile indices/counts are retained.
Plan: {"groups": [{"id": "lake", "resrefs": ["WTLAKE"],
  "aliases": {"WTLAKE": "XL0001"}, "method": "seedvr",
  "layout": [["WTLAKE"]], "wed": "AR0900", "seam_mode": "preserve"}]}.
--group selects plan group IDs. Without --plan it names one or four stock TIS.
All generated groups remain QA candidates. GPU work occurs only in generate/all.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from typing import Any
import zlib

import numpy as np
from PIL import Image

import bg2lib
from build_water_overlay_30fps_test import write_pvrz
from mos_decode import decode_pvrz_page

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / "pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json"
RUNNER = ROOT / "pipeline/scripts/upscale_animation_frames.py"
SEED = 959948902156062
SCHEMA = "bg2-liquid-periodic-x4-trial-v1"
TILE = 256
PAD = 4
PAGE = 2048
STRIDE = TILE + 2 * PAD


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def name(value: str) -> str:
    value = value.upper()
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", value):
        raise ValueError(f"invalid resource name: {value}")
    return value


def page_name(resref: str) -> str:
    result = resref[0] + resref[2:] + "00"
    return name(result)


def configure_vanilla(root: Path) -> tuple[list[str], dict[tuple[str, int], int]]:
    root = root.resolve()
    if not (root / "chitin.key").is_file():
        raise ValueError(f"missing vanilla chitin.key: {root}")
    # Explicit process-local source; never modifies workspace path configuration.
    bg2lib.GAME_DIR = str(root)
    bg2lib.KEY_PATH = str(root / "chitin.key")
    bg2lib._bif_cache.clear()
    bifs, entries = bg2lib.load_key()
    return bifs, {(n.upper(), kind): loc for n, kind, loc in entries}


def decode_palette(raw: bytes, count: int, size: int) -> tuple[list[Image.Image], list[dict]]:
    if size != 5120 or len(raw) != count * size:
        raise ValueError("trial source must be complete native 64x64 palettized TIS")
    images, stats = [], []
    for i in range(count):
        palette = np.frombuffer(raw, np.uint8, 1024, i * size).reshape(256, 4)
        indices = np.frombuffer(raw, np.uint8, 4096, i * size + 1024).reshape(64, 64)
        rgb = palette[:, [2, 1, 0]][indices].copy()
        # TisV1Decoder.getTilePalette: index 0 is transparent only when green.
        # Palette alpha bytes are unused; colored index 0 is an ordinary texel.
        keyed = bool(np.array_equal(palette[0, :3], [0, 255, 0]))
        alpha = np.where((indices == 0) & keyed, 0, 255).astype(np.uint8)
        rgb[alpha == 0] = 0
        images.append(Image.fromarray(np.dstack((rgb, alpha)), "RGBA"))
        stats.append({"tile": i, "palette0_bgra": palette[0].tolist(),
                      "index0_pixels": int((indices == 0).sum()),
                      "palette0_green_key": keyed, "transparent_pixels": int((alpha == 0).sum())})
    return images, stats


def groups_from_args(args: argparse.Namespace) -> list[dict]:
    if args.plan:
        payload = read_json(args.plan)
        groups = payload["groups"] if isinstance(payload, dict) else payload
        if args.group:
            selected = set(args.group)
            groups = [g for g in groups if g["id"] in selected]
            if {g["id"] for g in groups} != selected:
                raise ValueError("one or more --group IDs are absent from plan")
    else:
        refs = [name(v) for v in (args.group or [])]
        if len(refs) not in (1, 4):
            raise ValueError("without --plan, --group requires one or four stock resource names")
        groups = [{"id": "-".join(refs).lower(), "resrefs": refs,
                   "aliases": {v: v for v in refs}}]
    normalized = []
    used_aliases, used_pages = set(), set()
    for original in groups:
        g = copy.deepcopy(original)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", g["id"]):
            raise ValueError("unsafe group ID")
        refs = g["resrefs"] = [name(v) for v in g["resrefs"]]
        if len(refs) not in (1, 4) or len(set(refs)) != len(refs):
            raise ValueError("each group requires one or four distinct TIS resources")
        g.setdefault("layout", [refs] if len(refs) == 1 else [refs[:2], refs[2:]])
        layout = g["layout"]
        if len(layout) not in (1, 2) or any(len(row) != len(layout) for row in layout):
            raise ValueError("layout must be 1x1 or 2x2")
        if sorted(v for row in layout for v in row) != sorted(refs):
            raise ValueError("layout must contain each resource exactly once")
        g["aliases"] = {r: name(g.get("aliases", {}).get(r, r)) for r in refs}
        for alias in g["aliases"].values():
            page = page_name(alias)
            if alias in used_aliases or page in used_pages:
                raise ValueError("duplicate output TIS alias or derived PVRZ page")
            used_aliases.add(alias)
            used_pages.add(page)
        g.setdefault("method", "bilinear" if all(r.startswith("WTPOOL") for r in refs) else "seedvr")
        g.setdefault("seam_mode", "preserve")
        g.setdefault("seam_width_x4", 8)
        g.setdefault("seed", SEED)
        if g["method"] not in ("seedvr", "bilinear") or g["seam_mode"] not in ("preserve", "compatible"):
            raise ValueError("unsupported spatial method or seam mode")
        if not 1 <= int(g["seam_width_x4"]) <= 16:
            raise ValueError("seam collar must be 1..16 x4 pixels")
        normalized.append(g)
    if len({g["id"] for g in normalized}) != len(normalized):
        raise ValueError("duplicate group IDs")
    return normalized


def collect_topology(g: dict, bifs: list[str], resources: dict) -> dict:
    """Record actual flagged-cell adjacency and native per-slot playback."""
    wedges = g.get("weds", g.get("wed", []))
    if isinstance(wedges, str):
        wedges = [wedges]
    aliases = {ref: ref for ref in g["resrefs"]}
    # Rain TIS are selected by the engine; WED still names their dry resource.
    aliases.update({ref[:-1]: ref for ref in g["resrefs"] if ref.endswith("R")})
    if g.get("source_wed_resrefs"):
        if len(g["source_wed_resrefs"]) != len(g["resrefs"]):
            raise ValueError("source_wed_resrefs must match resrefs length")
        aliases.update(zip(g["source_wed_resrefs"], g["resrefs"]))
    edges: dict[tuple[str, str, str], int] = {}
    records = []
    for wedname in wedges:
        wedname = name(wedname)
        raw, archive = bg2lib.resolve_resource(bifs, resources[(wedname, 0x3E9)])
        layers, _, headers = struct.unpack_from("<3I", raw, 8)
        slot_refs, playback = {}, []
        bw, bh = struct.unpack_from("<HH", raw, headers)
        base_map = struct.unpack_from("<I", raw, headers + 16)[0]
        for slot in range(1, layers):
            h = headers + slot * 24
            w, height, rr, unique, movement, tilemap, lookup = struct.unpack_from("<HH8sHHII", raw, h)
            rr = rr.split(b"\0")[0].decode("ascii").upper()
            if rr not in aliases:
                continue
            ref = aliases[rr]
            slot_refs[slot] = ref
            if (w, height) != (1, 1):
                raise ValueError(f"{wedname}/{rr}: unsupported non-single-cell overlay")
            start, count, secondary, flags, speed, render = struct.unpack_from("<HHHBBH", raw, tilemap)
            sequence = list(struct.unpack_from(f"<{count}H", raw, lookup + start * 2))
            playback.append({"slot": slot, "resref": ref, "wed_resref": rr,
                             "lookup": sequence, "speed_divisor": speed, "movement": movement,
                             "secondary": secondary, "flags": flags, "rendering_flags": render,
                             "nominal_loop_seconds_at_15hz": count * max(1, speed) / 15})
        cells = []
        for cell in range(bw * bh):
            flags = raw[base_map + cell * 10 + 6]
            active = [ref for slot, ref in slot_refs.items() if flags & (1 << slot)]
            cells.append(active)
        for y in range(bh):
            for x in range(bw):
                for dx, dy, axis in ((1, 0, "x"), (0, 1, "y")):
                    if x + dx >= bw or y + dy >= bh:
                        continue
                    for a in cells[y * bw + x]:
                        for b in cells[(y + dy) * bw + x + dx]:
                            key = (a, b, axis)
                            edges[key] = edges.get(key, 0) + 1
        records.append({"wed": wedname, "archive": archive, "sha256": sha(raw),
                        "playback": playback})
    if not wedges:
        layout = g["layout"]
        dim = len(layout)
        for y in range(dim):
            for x in range(dim):
                for dx, dy, axis in ((1, 0, "x"), (0, 1, "y")):
                    key = (layout[y][x], layout[(y + dy) % dim][(x + dx) % dim], axis)
                    edges[key] = edges.get(key, 0) + 1
    return {"source": "native-wed" if wedges else "declared-periodic-layout",
            "weds": records, "adjacencies": [
                {"a": a, "b": b, "axis": axis, "occurrences": count}
                for (a, b, axis), count in sorted(edges.items())]}


def prepare(g: dict, output: Path, vanilla: Path, bifs: list, resources: dict) -> dict:
    out = output / "groups" / g["id"]
    contract = {"group": g, "vanilla_root": str(vanilla.resolve()),
                "key_sha256": sha((vanilla / "chitin.key").read_bytes())}
    manifest_path = out / "prepare.json"
    if manifest_path.is_file():
        saved = read_json(manifest_path)
        if saved["contract"] != contract:
            raise ValueError(f"existing prepared group has a different contract: {out}")
        return saved
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"non-empty unprepared group: {out}")
    frames, provenance = {}, []
    for ref in g["resrefs"]:
        raw, count, size, archive = bg2lib.resolve_tileset_resource(bifs, resources[(ref, 0x3EB)])
        frames[ref], alpha = decode_palette(raw, count, size)
        source_dir = out / "source-native" / ref
        source_dir.mkdir(parents=True)
        original_tis = b"TIS V1  " + struct.pack("<4I", count, size, 24, 64) + raw
        (source_dir / f"{ref}.TIS").write_bytes(original_tis)
        for i, image in enumerate(frames[ref]):
            image.save(source_dir / f"frame_{i:03d}.png")
        provenance.append({"resref": ref, "archive": archive, "tiles_payload_sha256": sha(raw),
                           "export_tis_sha256": sha(original_tis), "count": count,
                           "entry_size": size, "alpha_diagnostics": alpha})
    counts = {len(v) for v in frames.values()}
    if len(counts) != 1:
        raise ValueError("joint spatial conditioning requires equal native tile counts")
    count = counts.pop()
    topology = collect_topology(g, bifs, resources)
    for item in topology["weds"]:
        for slot in item["playback"]:
            if any(i >= count for i in slot["lookup"]):
                raise ValueError("native WED references a missing TIS tile")
    rgb_dir, alpha_dir = out / "inputs/rgb", out / "inputs/alpha"
    rgb_dir.mkdir(parents=True)
    alpha_dir.mkdir(parents=True)
    side = 64 * len(g["layout"])
    for i in range(count):
        motif = Image.new("RGBA", (side, side))
        for y, row in enumerate(g["layout"]):
            for x, ref in enumerate(row):
                motif.paste(frames[ref][i], (x * 64, y * 64))
        context = Image.new("RGBA", (side * 3, side * 3))
        for y in range(3):
            for x in range(3):
                context.paste(motif, (x * side, y * side))
        context.convert("RGB").save(rgb_dir / f"frame_{i:03d}.png")
        context.getchannel("A").save(alpha_dir / f"frame_{i:03d}.png")
    manifest = {"schema": SCHEMA, "contract": contract, "status": "prepared",
                "native_frame_count": count, "context_size_x1": [side * 3, side * 3],
                "central_crop_x4": [side * 4, side * 4, side * 8, side * 8],
                "source": provenance, "topology": topology,
                "alpha_policy": "index0 transparent only for green palette0; source alpha nearest x4",
                "temporal_policy": "all native indices retained; WED lookup/speed untouched",
                "qa": "unvalidated-candidate", "installation": "not-performed"}
    write_json(manifest_path, manifest)
    return manifest


def generate(g: dict, output: Path, args: argparse.Namespace) -> None:
    out = output / "groups" / g["id"]
    manifest = read_json(out / "prepare.json")
    if manifest["contract"]["group"] != g:
        raise ValueError("generation plan differs from prepared contract")
    if g["method"] == "bilinear":
        print(f"{g['id']}: deterministic bilinear generation occurs during build", flush=True)
        return
    command = [sys.executable, "-B", str(RUNNER), str(out / "inputs/rgb"),
               str(out / "inputs/alpha"), str(out / "generated"), "--scale", "4",
               "--pad", "0", "--color-correction-method", "none", "--seed", str(g["seed"]),
               "--workflow", str(WORKFLOW), "--upload-folder",
               f"BG2_Upscale/liquid-trials/{output.parent.name}-{sha(str(output).encode())[:12]}/{g['id']}"]
    if args.server:
        command += ["--server", args.server]
    if args.resume:
        command.append("--resume")
    subprocess.run(command, check=True)


def split_context(image: Image.Image, g: dict) -> dict[str, np.ndarray]:
    side = 64 * len(g["layout"]) * 4
    if image.size != (side * 3, side * 3):
        raise ValueError(f"unexpected generated context size: {image.size}")
    center = image.convert("RGBA").crop((side, side, 2 * side, 2 * side))
    return {ref: np.array(center.crop((x * TILE, y * TILE, (x + 1) * TILE, (y + 1) * TILE)))
            for y, row in enumerate(g["layout"]) for x, ref in enumerate(row)}


def edge(a: np.ndarray, axis: str, first: bool) -> np.ndarray:
    return a[:, -1 if first else 0, :3] if axis == "x" else a[-1 if first else 0, :, :3]


def seam_metrics(frames: dict[str, np.ndarray], pairs: list[dict]) -> list[dict]:
    results = []
    for pair in pairs:
        a, b = frames[pair["a"]], frames[pair["b"]]
        left, right = edge(a, pair["axis"], True), edge(b, pair["axis"], False)
        difference = np.abs(left.astype(float) - right.astype(float))
        axis = 1 if pair["axis"] == "x" else 0
        inner = float(np.mean([np.abs(np.diff(v[:, :, :3].astype(float), axis=axis)).mean() for v in (a, b)]))
        results.append({**pair, "mae": float(difference.mean()), "max": float(difference.max()),
                        "inner_gradient": inner, "ratio": float(difference.mean() / max(inner, 1e-6))})
    return results


def compatible_edges(frames: dict[str, np.ndarray], pairs: list[dict],
                     width: int) -> dict[str, np.ndarray]:
    """Reconstruct a narrow collar from compatible generated interior profiles.

    Only RGB in a narrow inner collar changes. Corners share the same nodes, so
    simultaneous x/y constraints agree. Interior and source alpha are untouched.
    Sampling beyond the collar avoids SeedVR's occasional dark edge strokes.
    Reconstructing color (rather than adding a boundary delta) removes the stroke
    throughout the collar and avoids reinserting a native-vs-generated color bias.
    """
    nodes: dict[tuple[str, int, int], int] = {}
    parents: list[int] = []
    def node(key: tuple[str, int, int]) -> int:
        if key not in nodes:
            nodes[key] = len(parents)
            parents.append(len(parents))
        return nodes[key]
    def find(i: int) -> int:
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for p in pairs:
        for k in range(TILE):
            ka = (p["a"], k, TILE - 1) if p["axis"] == "x" else (p["a"], TILE - 1, k)
            kb = (p["b"], k, 0) if p["axis"] == "x" else (p["b"], 0, k)
            ia, ib = find(node(ka)), find(node(kb))
            parents[ib] = ia
    sums, numbers = {}, {}
    for (ref, y, x), i in nodes.items():
        representative = find(i)
        xs = slice(width, width + 4) if x == 0 else slice(TILE - width - 4, TILE - width) if x == TILE - 1 else slice(x, x + 1)
        ys = slice(width, width + 4) if y == 0 else slice(TILE - width - 4, TILE - width) if y == TILE - 1 else slice(y, y + 1)
        profile = frames[ref][ys, xs, :3].astype(float).mean(axis=(0, 1))
        sums[representative] = sums.get(representative, np.zeros(3)) + profile
        numbers[representative] = numbers.get(representative, 0) + 1
    targets = {key: sums[find(i)] / numbers[find(i)] for key, i in nodes.items()}
    result = {}
    weight = 0.5 * (1 + np.cos(np.pi * np.arange(width) / width))
    for ref, original in frames.items():
        delta = np.zeros((TILE, TILE, 3), float)
        weights = np.zeros((TILE, TILE, 1), float)
        for (r, y, x), target in targets.items():
            if r != ref:
                continue
            for d, w in enumerate(weight):
                positions = []
                if x in (0, TILE - 1):
                    positions.append((y, d if x == 0 else TILE - 1 - d))
                if y in (0, TILE - 1):
                    positions.append((d if y == 0 else TILE - 1 - d, x))
                for py, px in positions:
                    delta[py, px] += w * (target - original[py, px, :3].astype(float))
                    weights[py, px] += w
        revised = original.copy()
        revised[:, :, :3] = np.clip(np.rint(original[:, :, :3] + delta / np.maximum(weights, 1)), 0, 255)
        for (r, y, x), target in targets.items():
            if r == ref:
                revised[y, x, :3] = np.clip(np.rint(target), 0, 255)
        result[ref] = revised
    return result


def export_tiles(frames: list[np.ndarray], alias: str, out: Path) -> dict:
    if not 1 <= len(frames) <= (PAGE // STRIDE) ** 2:
        raise ValueError("native frames exceed the one-page trial atlas capacity")
    out.mkdir(parents=True, exist_ok=True)
    canvas = np.zeros((PAGE, PAGE, 4), np.uint8)
    entries = []
    for i, frame in enumerate(frames):
        if frame.shape != (TILE, TILE, 4):
            raise ValueError("incorrect tile dimensions")
        row, col = divmod(i, PAGE // STRIDE)
        x, y = col * STRIDE + PAD, row * STRIDE + PAD
        canvas[y-PAD:y+TILE+PAD, x-PAD:x+TILE+PAD] = np.pad(frame, ((PAD, PAD), (PAD, PAD), (0, 0)), mode="edge")
        entries.append((0, x, y))
    page = out / f"{page_name(alias)}.PVRZ"
    # Pillow 9 silently ignores pixel_format='DXT5' and writes uncompressed DDS.
    # Validate codec support before the shared writer can create a bad PVRZ.
    probe = io.BytesIO()
    Image.new("RGBA", (4, 4), (1, 2, 3, 255)).save(probe, format="DDS", pixel_format="DXT5")
    if probe.getvalue()[84:88] != b"DXT5" or len(probe.getvalue()) != 144:
        raise RuntimeError(f"Pillow {Image.__version__} cannot encode BC3; use the bundled Python/Pillow 12 runtime for --stage build")
    class Capture:
        payload: bytes
        def write_bytes(self, payload: bytes) -> None:
            self.payload = payload
    encoded = Capture()
    write_pvrz(Image.fromarray(canvas, "RGBA"), encoded)
    raw_pvr = zlib.decompress(encoded.payload[4:])
    if len(raw_pvr) != 52 + PAGE * PAGE or struct.unpack_from("<I", raw_pvr, 8)[0] != 11:
        raise ValueError("unexpected BC3 PVR payload size or format")
    page.write_bytes(encoded.payload)
    tis = b"TIS V1  " + struct.pack("<4I", len(frames), 12, 24, TILE)
    tis += b"".join(struct.pack("<3I", *entry) for entry in entries)
    path = out / f"{alias}.TIS"
    path.write_bytes(tis)
    return {"alias": alias, "tile_count": len(frames), "tile_dimension": TILE,
            "format": "PVRZ/BC3-DXT5", "padding_x4": PAD,
            "files": [{"path": str(p), "sha256": sha(p.read_bytes()), "bytes": p.stat().st_size}
                      for p in (path, page)]}


def build(g: dict, output: Path, build_output: Path | None = None,
          reuse_generated_root: Path | None = None) -> dict:
    source_out = output / "groups" / g["id"]
    out = (build_output or output) / "groups" / g["id"]
    prepared = read_json(source_out / "prepare.json")
    if prepared["contract"]["group"] != g:
        raise ValueError("build plan differs from prepared contract")
    if (out / "build.json").exists():
        raise ValueError(f"build already finalized; choose a new run: {out}")
    pairs = prepared["topology"]["adjacencies"]
    collection = {ref: [] for ref in g["resrefs"]}
    metrics = []
    phases = []
    generation = None
    generated_out = source_out
    if g["method"] == "seedvr":
        reuse = (reuse_generated_root / "groups" / g["id"]
                 if reuse_generated_root else g.get("reuse_generated_from"))
        if reuse:
            generated_out = Path(reuse)
            if not generated_out.is_absolute():
                generated_out = ROOT / generated_out
            generated_out = generated_out.resolve(strict=True)
            for kind in ("rgb", "alpha"):
                for i in range(prepared["native_frame_count"]):
                    own = source_out / f"inputs/{kind}/frame_{i:03d}.png"
                    shared = generated_out / f"inputs/{kind}/frame_{i:03d}.png"
                    if not shared.is_file() or sha(own.read_bytes()) != sha(shared.read_bytes()):
                        raise ValueError(f"reused SeedVR input differs: {g['id']}/{kind}/frame_{i:03d}")
        genpath = generated_out / "generated/manifest.json"
        generation = read_json(genpath)
        if generation.get("status") != "completed":
            raise ValueError("SeedVR generation is not completed")
        if generation.get("parameters", {}).get("color_correction_method") != "none":
            raise ValueError("SeedVR generation must use color correction none")
    for i in range(prepared["native_frame_count"]):
        with Image.open(source_out / f"inputs/rgb/frame_{i:03d}.png") as source:
            native_context = source.convert("RGBA").resize((source.width * 4, source.height * 4), Image.Resampling.BILINEAR)
        with Image.open(source_out / f"inputs/alpha/frame_{i:03d}.png") as alpha:
            native_context.putalpha(alpha.resize(native_context.size, Image.Resampling.NEAREST))
        native = split_context(native_context, g)
        if g["method"] == "seedvr":
            with Image.open(generated_out / f"generated/rgba/frame_{i:03d}.png") as generated:
                frames = split_context(generated, g)
            for ref in frames:
                if not np.array_equal(frames[ref][:, :, 3], native[ref][:, :, 3]):
                    raise ValueError("generated alpha diverged from native nearest x4")
        else:
            frames = {r: a.copy() for r, a in native.items()}
        before = seam_metrics(frames, pairs)
        source_metrics = seam_metrics(native, pairs)
        # An ordinary texture gradient is not itself a broken seam. Correct only
        # amplified discontinuities; save the measured reason in the candidate.
        bad = [p for p, stock in zip(before, source_metrics)
               if p["mae"] > max(2.0, stock["mae"] * 1.5)
               and p["ratio"] > max(2.0, stock["ratio"] * 1.25)]
        phases.append((frames, native, before, source_metrics, bad))
    # One spatial contract for the entire loop: a per-frame on/off correction
    # would create a new temporal discontinuity at the correction boundary.
    correction = g["seam_mode"] == "compatible" and any(p[4] for p in phases)
    for i, (frames, native, before, source_metrics, bad) in enumerate(phases):
        final = compatible_edges(frames, pairs, int(g["seam_width_x4"])) if correction else frames
        for ref, array in final.items():
            folder = out / "tiles-x4" / ref
            folder.mkdir(parents=True, exist_ok=True)
            Image.fromarray(array, "RGBA").save(folder / f"frame_{i:03d}.png")
            collection[ref].append(array)
        metrics.append({"frame": i, "native_bilinear": source_metrics, "before": before,
                        "after": seam_metrics(final, pairs), "correction_applied": correction,
                        "reason": "amplified-stock-seam" if correction else "preserved",
                        "trigger_pairs": bad,
                        "rgb_mae_from_seedvr": {r: float(np.abs(final[r][:, :, :3].astype(float) - frames[r][:, :, :3]).mean()) for r in final}})
    outputs = [{"source_resref": ref, **export_tiles(images, g["aliases"][ref], out / "build")}
               for ref, images in collection.items()]
    # Equal RGB boundaries can be quantized differently by independently encoded
    # BC3 blocks. Report the actual delivered bytes, not just uncompressed PNGs.
    decoded = {}
    for item in outputs:
        ref = item["source_resref"]
        raw_tis = Path(item["files"][0]["path"]).read_bytes()
        with decode_pvrz_page(Path(item["files"][1]["path"]).read_bytes()) as page:
            decoded[ref] = []
            for i in range(item["tile_count"]):
                page_id, x, y = struct.unpack_from("<3I", raw_tis, 24 + i * 12)
                if page_id != 0:
                    raise ValueError("unexpected PVRZ page in trial atlas")
                tile = np.array(page.crop((x, y, x + TILE, y + TILE)))
                if not np.array_equal(tile[:, :, 3], collection[ref][i][:, :, 3]):
                    raise ValueError("BC3 encoding changed the native binary alpha")
                decoded[ref].append(tile)
    for i, metric in enumerate(metrics):
        actual = {ref: images[i] for ref, images in decoded.items()}
        metric["after_bc3"] = seam_metrics(actual, pairs)
        metric["bc3_rgb_mae"] = {
            ref: float(np.abs(actual[ref][:, :, :3].astype(float) - collection[ref][i][:, :, :3]).mean())
            for ref in actual}
    manifest = {"schema": SCHEMA, "status": "built-candidate", "group": g,
                "prepare_path": str(source_out / "prepare.json"),
                "prepare_sha256": sha((source_out / "prepare.json").read_bytes()),
                "generation_manifest_path": str(generated_out / "generated/manifest.json") if generation else None,
                "generation_manifest_sha256": sha((generated_out / "generated/manifest.json").read_bytes()) if generation else None,
                "producer_sha256": sha(Path(__file__).read_bytes()),
                "edge_recipe": "generated-interior-profile-equivalence-collar-v2",
                "metrics": metrics, "outputs": outputs, "topology": prepared["topology"],
                "playback": "native TIS indices/counts preserved; apply only isolated resref WED routing",
                "qa": "unvalidated-candidate", "installation": "not-performed"}
    write_json(out / "build.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vanilla-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--build-output", type=Path, help="separate new build root; read prepared/generated sources from --output")
    parser.add_argument("--reuse-generated-root", type=Path,
                        help="reuse byte-identical generated frames from another prepared output root")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--group", nargs="+")
    parser.add_argument("--stage", choices=("prepare", "generate", "build", "all"), default="prepare")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--server")
    args = parser.parse_args()
    groups = groups_from_args(args)
    output = args.output.resolve()
    build_output = args.build_output.resolve() if args.build_output else None
    reuse_generated_root = args.reuse_generated_root.resolve() if args.reuse_generated_root else None
    try:
        output.relative_to(ROOT / "maps")
        if build_output:
            build_output.relative_to(ROOT / "maps")
        if reuse_generated_root:
            reuse_generated_root.relative_to(ROOT / "maps")
    except ValueError as error:
        raise ValueError("trial output must remain beneath repository maps/") from error
    bifs, resources = configure_vanilla(args.vanilla_root)
    for g in groups:
        print(f"{g['id']}: {args.stage}", flush=True)
        if args.stage in ("prepare", "all"):
            prepare(g, output, args.vanilla_root, bifs, resources)
        if args.stage in ("generate", "all"):
            generate(g, output, args)
        if args.stage in ("build", "all"):
            build(g, output, build_output, reuse_generated_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
