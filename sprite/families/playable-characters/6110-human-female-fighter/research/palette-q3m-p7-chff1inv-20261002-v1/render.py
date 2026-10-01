"""Offline P7 pilot: CHFF1INV body only, existing Q3m K6 x2 math.

UI palette realization/alpha/layout are assumptions, not ingame validation.
No catalog, game, installation, QA, runtime or release writes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

import numpy as np
from PIL import Image, ImageDraw

import palette_frac_encode as encoder
import run_creature_sprite_x2 as registry
from palette_complete import independent_lut, source_frames
from palette_oracle import read_bam_p8
from palette_p2 import P1, GOLDEN_SHA, golden
from reboutcx_multipal import inference_context, infer_targets, save_npz, sha256_file
from workspace_paths import get_path

SOURCE = ROOT / ("sprite/Etudes_Sprite_codex_claude/"
    "CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/vanilla_inventory/CHFF1INV.BAM")
SOURCE_SHA = "7362904ce303b28073f2ecb5eb4384ac0e0f715b84e0f45f715898c14da86d8a"
SCALE = 2
NAMES = ("REF", "DEFAULT", "LATIN1", "LATIN2", "LATIN3", "LATIN4")
CANVAS = (128, 160)
SECOND_OFFSET_Y = 80


def assemble(parts, frames, scale):
    canvas = Image.new("RGBA", (CANVAS[0]*scale, CANVAS[1]*scale))
    placements = []
    for index, (part, frame) in enumerate(zip(parts, frames, strict=True)):
        # Native signed centers retained. Compatible-engine paperdoll assembly
        # uses two body halves, the second half displaced by 80 native pixels.
        x = -frame.center_x
        y = -frame.center_y + SECOND_OFFSET_Y*index
        if part.size != (frame.width*scale, frame.height*scale):
            raise ValueError("Part geometry differs from source/scale")
        if x < 0 or y < 0 or x+frame.width > CANVAS[0] or y+frame.height > CANVAS[1]:
            raise ValueError("Paperdoll part exceeds preview canvas")
        canvas.alpha_composite(part, (x*scale, y*scale))
        placements.append(dict(frame=index, x1=[x, y], x2=[x*scale, y*scale]))
    return canvas, placements


def main():
    started = time.perf_counter()
    output = Path(__file__).resolve().parent
    protected = ("result.json", "part-0-q3m-x2.npz", "part-1-q3m-x2.npz",
                 "paperdoll-default-q3m-x2.png", "preview.png", "comparison.png")
    if any((output/name).exists() for name in protected):
        raise ValueError("Existing render: use a fresh run directory")
    if sha256_file(SOURCE) != SOURCE_SHA:
        raise ValueError("CHFF1INV source changed")
    bam = read_bam_p8(SOURCE.read_bytes())
    frames = source_frames("CHFF1INV", bam)
    cycles = [cycle["frame_indices"] for cycle in bam["cycles"]]
    if len(frames) != 2 or cycles != [[0, 0, 1, 1]]:
        raise ValueError("Unexpected CHFF1INV native body parts")
    palettes, _, _, _ = golden()
    fitting = palettes[:6, :, :3].copy()
    fitting[:, 0] = (0, 255, 0)  # Existing P1/P3 inference identity.
    context = inference_context()
    work = output / "work"
    work.mkdir(exist_ok=True)
    by_key = {f"CHFF1INV_{frame.index:04d}": frame for frame in frames}

    print("CHFF1INV only: 2 body halves, 6 fitting palettes, x2 output", flush=True)
    scalepix = get_path("mmpx_scalepix", required=True)
    guides = []
    rendered = registry.run_xbr(frames, scalepix, "node", registry.direct_upscale_contract(SCALE))
    for frame, (width, height, rgba) in zip(frames, rendered, strict=True):
        provenance = registry.xbr_provenance_indices(frame, SCALE) if registry.has_duplicate_used_rgba_indices(frame) else None
        guide, _ = registry.map_output(frame, rgba, provenance)
        guides.append(guide.reshape(height, width))
    references, timing = infer_targets(by_key, dict(zip(NAMES, fitting, strict=True)), work, context)
    lut = independent_lut(palettes)
    records, q3m_parts, native_parts = [], [], []
    for frame, (key, _), guide in zip(frames, by_key.items(), guides, strict=True):
        targets = []
        for name in NAMES:
            with np.load(work / references[name][key], allow_pickle=False) as data:
                targets.append(data["x2"].copy())
        encoded = encoder.encode_variants(guide, np.stack(targets), fitting, ks=(6,))["Q3m-k6"]
        indices, fractions, dep = encoded["I"], encoded["F"], encoded["dep_mask"]
        decoded = [encoder.decode(indices, fractions, palette) for palette in palettes]
        for pi, rgba in enumerate(decoded):
            if not np.array_equal(rgba, lut[pi, indices, fractions]):
                raise ValueError("Q3m independent byte decoder differs")
        path = output / f"part-{frame.index}-q3m-x2.npz"
        save_npz(path, guide=guide, I=indices, F=fractions, dep_mask=dep,
                 native_geometry=np.asarray((frame.width, frame.height, frame.center_x, frame.center_y, 0), np.int32))
        with np.load(path, allow_pickle=False) as check:
            for label, expected in (("guide", guide), ("I", indices), ("F", fractions), ("dep_mask", dep)):
                if not np.array_equal(check[label], expected):
                    raise ValueError(f"Written {label} plane differs")
        q3m_parts.append(Image.fromarray(decoded[1]))
        native_parts.append(Image.fromarray(palettes[1][frame.indices]).resize(
            (frame.width*SCALE, frame.height*SCALE), Image.Resampling.NEAREST))
        records.append(dict(frame=frame.index, native_geometry=[frame.width, frame.height, frame.center_x, frame.center_y, 0],
            output_geometry=[frame.width*SCALE, frame.height*SCALE], file=path.name, sha256=sha256_file(path),
            **encoded["checks"], independent_decode_palettes=len(palettes)))
        print(f"encoded body half {frame.index}; Q3m contract/18-palette byte decode pass", flush=True)

    q3m, placement = assemble(q3m_parts, frames, SCALE)
    native, native_placement = assemble(native_parts, frames, SCALE)
    if placement != native_placement:
        raise ValueError("Native/Q3m preview placement differs")
    q3m.save(output / "paperdoll-default-q3m-x2.png")
    native.save(output / "paperdoll-default-native-nearest-x2.png")
    background = (26, 29, 34, 255)
    preview = Image.new("RGBA", q3m.size, background)
    preview.alpha_composite(q3m)
    preview.convert("RGB").save(output / "preview.png")
    comparison = Image.new("RGBA", (544, 360), background)
    comparison.alpha_composite(native, (8, 28))
    comparison.alpha_composite(q3m, (280, 28))
    draw = ImageDraw.Draw(comparison)
    draw.text((16, 8), "Natif (pixels x2)", fill=(235, 235, 235, 255))
    draw.text((288, 8), "Q3m K6 x2", fill=(235, 235, 235, 255))
    comparison.convert("RGB").save(output / "comparison.png")
    for name in ("paperdoll-default-q3m-x2.png", "preview.png", "comparison.png"):
        with Image.open(output/name) as check:
            check.load()
            if name == "paperdoll-default-q3m-x2.png" and (check.mode != "RGBA" or check.size != (256, 320)):
                raise ValueError("Unexpected final preview format")

    palette_records = json.loads((P1 / "experiment.json").read_text(encoding="utf-8"))["palettes"]
    report = dict(schema="bg2-upscale-p7-paperdoll-preview-v1", state="working",
        scope=dict(animation_id="0x6110", body="CHFF1INV", equipped_overlays=[], other_bodies=[]),
        source=dict(path=SOURCE.relative_to(ROOT).as_posix(), sha256=SOURCE_SHA, bif="data/GUIIcon.bif", locator="0x004006FB",
            frame_count=2, cycles=cycles, transparency=0),
        method=dict(model="reboutcx", scale=SCALE, x2_target="BOX reduction of model x4 float output before Q3m encoding",
            encoder=encoder.ENCODER_ID, variant="Q3m-k6", class_profile=encoder.CLASS_PROFILE,
            decode_rule=encoder.DECODE_RULE, fitting_palettes=list(NAMES), weights="equal", dithering=False),
        preview=dict(palette=palette_records[1], canvas_x1=list(CANVAS), placement=placement,
            native_comparator="same DEFAULT RGBA palette; nearest x2; identical assembly",
            ui_palette="preparatory reuse of Character palette fixture; native UI realization not verified",
            alpha="P1 diagnostic convention: index0=0, index1=128, other=255; native UI alpha not verified",
            layout="native signed centers plus 80-pixel second-half offset; compatible-engine reference, BG2EE ingame verification pending",
            layout_reference="https://raw.githubusercontent.com/gemrb/gemrb/master/gemrb/core/CharAnimations.cpp"),
        frames=records, inference=context, inference_timing=timing, total_seconds=time.perf_counter()-started,
        provenance=dict(golden_sha256=GOLDEN_SHA, recipe_sha256=sha256_file(Path(__file__)),
            kernels={name: sha256_file(ROOT/"pipeline/scripts"/name) for name in
                ("palette_frac_encode.py", "palette_oracle.py", "palette_complete.py", "reboutcx_multipal.py", "run_creature_sprite_x2.py")},
            scalepix_sha256=sha256_file(scalepix)),
        outputs={name:dict(sha256=sha256_file(output/name), bytes=(output/name).stat().st_size) for name in
            ("paperdoll-default-q3m-x2.png", "paperdoll-default-native-nearest-x2.png", "preview.png", "comparison.png")},
        ingame_qa="pending", installation_modified=False, catalog_modified=False, runtime_modified=False, release_modified=False)
    with (output/"result.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps(dict(output=str(output), total_seconds=report["total_seconds"], inference=timing), indent=2), flush=True)


if __name__ == "__main__":
    main()
