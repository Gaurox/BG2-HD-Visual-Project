"""Prepare scoped P3 sessions and check real palette captures independently."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zlib
from pathlib import Path

import numpy as np

import palette_registry as v6
import run_creature_sprite_x2 as registry
from palette_p3_catalog import derive

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / "sprite/families/playable-characters/6110-human-female-fighter/research"
P2 = RESEARCH / "palette-q3m-p2-20260930-v1"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def prepare(output, dll, parent_pointer):
    proof = json.loads((P2 / "verification.json").read_text())
    experiment = json.loads((RESEARCH / "palette-q3m-p1-20260930-v1/experiment.json").read_text())
    canonical_sources = {ref: ROOT / source["canonical_bam"] for ref, source in experiment["sources"].items()}
    if output.exists():
        raise ValueError("Use a new P3 run; existing runs are preserved")
    if not dll.is_file():
        raise ValueError("Candidate DLL absent")
    pointer = json.loads(parent_pointer.read_text())
    parent_manifest_path = ROOT / pointer["generation_dir"] / pointer["build_manifest"]
    if sha(parent_manifest_path).upper() != pointer["build_manifest_sha256"].upper():
        raise ValueError("Complete parent manifest changed")
    parent_manifest = json.loads(parent_manifest_path.read_text())
    parent_catalog = parent_manifest_path.parent / parent_manifest["registry_catalog"]
    if sha(parent_catalog).upper() != pointer["catalog_sha256"].upper():
        raise ValueError("Complete parent catalog changed")
    output.mkdir(parents=True)
    (output / "candidate").mkdir()
    target_dll = output / "candidate/InfinityEngine-Enhancer.dll"
    shutil.copyfile(dll, target_dll)
    manifest = dict(
        schema="bg2-upscale-runtime-capabilities-v1", status="development-candidate",
        runtime_id=output.name, game_profile=dict(
            id="bg2ee-2.7.3.0-windows-x64",
            baldur_real_sha256="B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57"),
        dll=dict(path=relative(target_dll), sha256=sha(target_dll), bytes=target_dll.stat().st_size),
        capabilities=dict(creature_sprite_xn_catalog=dict(
            catalog_versions=[1, 2], shard_registry_versions=[3, 5, 6],
            mixed_v5_v6_components=True,
            frame_storage=["raw-v3", "XPRESS_HUFF-or-raw-per-frame-v1", "q3m-u8-per-plane-v1"])))
    write_json(output / "runtime.json", manifest)
    for label in ("x2-q0", "x2-q3m-k6"):
        record = next(p for p in proof["packs"] if p["label"] == label)
        source = P2 / record["assets"]
        generation = output / label / "generation"
        destination = generation / "iee-assets/creature-sprites"
        for file in source.iterdir():
            expected = record["sha256"][file.relative_to(P2).as_posix()]
            if sha(file).lower() != expected.lower():
                raise ValueError(f"P2 asset changed: {file}")
        info, preservation = derive(parent_catalog, parent_manifest, next(source.glob("*.registry")), destination,
                                    canonical_sources=canonical_sources)
        write_json(generation / "preservation.json", preservation)
        build = dict(schema="bg2-upscale-creature-sprite-xn-catalog-pack-v1",
            generation_id=label, registry_layout="catalog", registry_catalog_version=2,
            registry_catalog_shard_version=0, registry_catalog_shard_versions=[5, 6],
            registry_catalog_frame_storages=["XPRESS_HUFF-or-raw-per-frame-v1", "q3m-u8-per-plane-v1"],
            registry_catalog_frame_storage="mixed-v5-v6-components-v1",
            registry_catalog="iee-assets/creature-sprites/CreatureSprites-XN.catalog",
            registry_catalog_sha256=sha(destination / "CreatureSprites-XN.catalog"),
            registry_catalog_bytes=(destination / "CreatureSprites-XN.catalog").stat().st_size,
            animation_ids=[a["animation_id"] for a in info["animations"]], shards=info["shards"],
            registry_catalog_logical_component_digests=info["logical_component_digests"],
            registry_catalog_logical_content_sha256=info["logical_content_sha256"],
            storage={key: info[key] for key in ("shard_registry_versions", "frame_storage", "stored_index_bytes",
                "compressed_frame_count", "raw_frame_count")},
            preservation="preservation.json")
        write_json(generation / "build-manifest.json", build)
        write_json(output / label / "current-generation.json", dict(
            schema="bg2-upscale-creature-sprite-xn-catalog-current-generation-v1",
            generation_id=label, generation_dir=relative(generation), build_manifest="build-manifest.json"))
        write_json(output / f"{label}.job.json", dict(
            schema="bg2-upscale-creature-sprite-xn-catalog-job-v1", job_id=f"{output.name}-{label}",
            paths=dict(game_root="config://bg2ee_game_root", run_dir=relative(output / label)),
            compatibility=dict(baldur_real_sha256=manifest["game_profile"]["baldur_real_sha256"])))
    write_json(output / "p1-palette-plan.json", experiment)
    write_json(output / "session.json", dict(
        schema="bg2-upscale-character-palette-p3-session-v1", status="prepared",
        animation_id="0x6110", scale=2, filter="Nearest", p2_source=relative(P2),
        scope="Complete parent coverage; five BAM replaced only for 0x6110; 84 P1 samples Q3m",
        parent_pointer=relative(parent_pointer), parent_catalog_sha256=sha(parent_catalog),
        x1_shader_profiles="disabled-during-test; restored-with-INI",
        runtime_dll_sha256=sha(target_dll), ingame_validated=False, visual_qa_accepted=False,
        source_sha256={relative(ROOT / name): sha(ROOT / name) for name in (
            "engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp",
            "engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/config.cpp",
            "engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/config.h",
            "engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp",
            "pipeline/scripts/run_creature_sprite_x2.py", "pipeline/scripts/palette_p3_catalog.py",
            "pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1",
            "pipeline/scripts/Start-Palette-Q3m-P3.ps1", "pipeline/scripts/palette_p3.py")}))
    print(json.dumps(dict(status="prepared", run=relative(output)), indent=2))


def independent_decode(frame, colors):
    """Explicit class intervals; no production successor, LUT or decode helper."""
    successor = np.arange(256, dtype=np.uint32)
    classes = [(n, n) for n in range(4)]
    classes += [(n, n + 11) for n in range(4, 88, 12)]
    classes += [(n, n + 7) for n in range(88, 256, 8)]
    for first, last in classes:
        successor[first:last] = np.arange(first + 1, last + 1)
    indices = np.frombuffer(frame["I"], np.uint8)
    fractions = np.frombuffer(frame["F"], np.uint8) if frame["F"] else np.zeros_like(indices)
    palette = np.asarray(colors, dtype="<u4").copy()
    palette[0] = 0  # CVidCell clears this after Realize, as does the decoder.
    primary = palette[indices]
    secondary = palette[successor[indices]]
    f = fractions.astype(np.uint32)
    pixels = primary & np.uint32(0xff000000)
    for shift in (0, 8, 16):
        a = (primary >> shift) & 255
        b = (secondary >> shift) & 255
        pixels |= ((a * (8 - f) + b * f + 4) // 8) << shift
    # Keep the runtime's historical FNV seed, which differs from the standard seed.
    fingerprint = 1469598103934665603
    def append(data):
        nonlocal fingerprint
        for byte in data:
            fingerprint = ((fingerprint ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return palette, pixels.astype("<u4"), append, lambda: fingerprint


def verify_capture(assets, log, output, *, require_hd=True):
    if output.exists():
        raise ValueError("Capture reports are immutable; choose a new path")
    catalog = assets / registry.XN_REGISTRY_CATALOG_FILENAME
    sealed = registry.read_sealed_catalog_index(catalog, sha(catalog))
    resources = {}
    for row in sealed["directory"]:
        if row["animation_id"] != "0x6110":
            continue
        shard = sealed["shards"][row["shard_index"]]
        leaf = assets / Path(shard["registry"]).name
        # Only V6 palette traces are emitted by the corrected DLL.
        with leaf.open("rb") as stream:
            stream.seek(8); version = int.from_bytes(stream.read(4), "little")
        if version == 6 and row["resref"] not in resources:
            checked = v6.inspect(leaf, include_frames=True)
            if checked["sha256"].upper() != shard["sha256"].upper():
                raise ValueError("Captured V6 shard identity differs from catalog")
            for resource in checked["frame_data"]:
                if any(r["animation_id"] == "0x6110" and r["resref"] == resource["resref"] and
                       r["shard_index"] == row["shard_index"] for r in sealed["directory"]):
                    resources[resource["resref"]] = resource
    captures, errors, fractional, actors, encodings, alphas = 0, [], 0, set(), set(), set()
    slots, generations, fractional_generations, bound_generations = set(), set(), set(), set()
    lines = log.read_text(errors="replace").splitlines()
    for line in lines:
        if "Q3M_P3_DRAW " in line:
            fields = dict(re.findall(r"(\w+)=([^\s]+)", line.split("Q3M_P3_DRAW ", 1)[1]))
            if fields.get("animation") == "6110" and fields.get("replacementBound") == "true":
                bound_generations.add(fields["generation"])
    for line_number, line in enumerate(lines, 1):
        if "Q3M_P3_PALETTE animation=" not in line:
            continue
        captures += 1
        try:
            fields = dict(re.findall(r"(\w+)=([^\s]+)", line.split("Q3M_P3_PALETTE ", 1)[1]))
            if fields["decoded"] != "true" or fields["animation"] != "6110":
                raise ValueError("Native capture failed to decode")
            resource = resources[fields["resref"]]
            index, sequence, slot = (int(fields[k]) for k in ("frame", "sequence", "slot"))
            if index < 0 or index >= len(resource["frames"]):
                raise ValueError("Invalid native frame index")
            if sequence < 0 or sequence >= len(resource["cycles"]) or slot < 0 or slot >= len(resource["cycles"][sequence]):
                raise ValueError("Invalid native cycle/slot bounds")
            if resource["cycles"][sequence][slot] != index:
                raise ValueError("Native cycle/slot differs from source table")
            frame = resource["frames"][index]
            raw = fields["colors"]
            if len(raw) != 2048:
                raise ValueError("Palette is not 256 DWORDs")
            colors = [int(raw[n:n + 8], 16) for n in range(0, 2048, 8)]
            palette, pixels, append, fingerprint = independent_decode(frame, colors)
            encoding = tuple(int(fields[k], 16) for k in ("format", "type"))
            if encoding not in ((0x1908, 0x1401), (0x80e1, 0x1401), (0x80e1, 0x8367)):
                raise ValueError("Unsupported native packing")
            if len(pixels) != int(fields["pixels"]) or zlib.crc32(pixels.tobytes()) != int(fields["crc32"], 16):
                raise ValueError("Independent decode differs from native pixel CRC/size")
            for word in (*encoding, 1, 1):
                append(word.to_bytes(4, "little"))
            for n in range(256):
                if frame["dep"][n // 8] & (1 << (n % 8)):
                    append(bytes([n])); append(int(palette[n]).to_bytes(4, "little"))
            if fingerprint() != int(fields["fingerprint"], 16):
                raise ValueError("Native dependency fingerprint differs")
            fractional += int(bool(frame["F"] and any(frame["F"])))
            generations.add(fields["generation"])
            if frame["F"] and any(frame["F"]):
                fractional_generations.add(fields["generation"])
            actors.add(fields["cell"]); encodings.add(encoding)
            alphas.update(c >> 24 for c in colors)
            slots.add((fields["resref"], index))
        except (KeyError, IndexError, ValueError) as error:
            errors.append(dict(line=line_number, error=str(error)))
    cpu_passed = bool(captures and not errors)
    hd_observed = bool(generations & bound_generations)
    report = dict(schema="bg2-upscale-character-palette-p3-capture-v2",
        status="passed-cpu-and-hd-substitution" if cpu_passed and hd_observed else
               "passed-cpu-only" if cpu_passed else "failed-or-empty",
        cpu_decode_passed=cpu_passed, require_hd_substitution=require_hd,
        capture_log=str(log), capture_log_sha256=sha(log), records=captures,
        records_with_nonzero_F=fractional, distinct_frames=len(slots), distinct_cells=len(actors),
        captured_generations_with_hd_substitution=len(generations & bound_generations),
        fractional_generations_with_hd_substitution=len(fractional_generations & bound_generations),
        hd_substitution_observed=bool(generations & bound_generations),
        native_encodings=[list(e) for e in sorted(encodings)], raw_alpha_values=sorted(alphas),
        errors=errors, visual_qa_accepted=False,
        limitations=["CRC identity, not archived per-pixel native buffers", "CPU decoded data; no GPU readback",
                    "Captured samples only; effects require labeled scene evidence"])
    write_json(output, report)
    print(json.dumps(report, indent=2))
    if errors or not captures or (require_hd and not hd_observed):
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--output", type=Path, required=True)
    prepare_parser.add_argument("--dll", type=Path, required=True)
    prepare_parser.add_argument("--parent-pointer", type=Path, default=ROOT / "sprite/catalogs/creature-x2-reboutcx/runs/catalog-reboutcx-playable-characters-p13-v1/current-generation.json")
    capture_parser = commands.add_parser("verify-capture")
    capture_parser.add_argument("--cpu-only", action="store_true", help="Diagnostic only; does not prove HD substitution")
    for name in ("assets", "log", "output"):
        capture_parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.output.resolve(), args.dll.resolve(), args.parent_pointer.resolve())
    else:
        verify_capture(args.assets, args.log, args.output, require_hd=not args.cpu_only)


if __name__ == "__main__":
    main()
