"""Build the immutable runtime registry for the sealed item xBR2x+AA batch."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
from bam_export import decode_bam  # noqa: E402

PACK_NAME = "ItemIcons-X2.registry"
MAGIC = b"IEEICX2\0"
VERSION = 2
SCALE = 2
HEADER_BYTES = 40
RECORD_BYTES = 40


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def inventory_assets() -> list[dict[str, str]]:
    with (ROOT / "icons" / "index" / "resources.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        resources = {row["asset_key"]: row for row in csv.DictReader(stream)}
    with (ROOT / "icons" / "index" / "families.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        keys = [
            row["asset_key"]
            for row in csv.DictReader(stream)
            if row["family"] == "item-inventory"
        ]
    if len(keys) != len(set(keys)):
        raise RuntimeError("item-inventory contains duplicate asset identities")
    return sorted((resources[key] for key in keys), key=lambda row: row["resref"])


def decode_source(asset: dict[str, str]) -> tuple[list[tuple[np.ndarray, int]], list[list[int]]]:
    source = ROOT / asset["extracted_path"]
    if not source.is_file() or sha256(source) != asset["source_sha256"].upper():
        raise RuntimeError(f"{asset['resref']}: source BAM is absent or differs from resources.csv")
    payload = source.read_bytes()
    if payload[:4] == b"BAMC":
        payload = zlib.decompress(payload[12:])
    frame_count, cycle_count, _ = struct.unpack_from("<HBB", payload, 8)
    off_frames, _off_palette, off_lookup = struct.unpack_from("<III", payload, 0x0C)
    frames, palette, _ = decode_bam(payload)
    decoded: list[tuple[np.ndarray, int]] = []
    for indices, _center_x, _center_y, transparent in frames:
        height, width = indices.shape
        rgba = np.empty((height, width, 4), dtype=np.uint8)
        rgba[:, :, :3] = palette[indices]
        rgba[:, :, 3] = np.where(indices == transparent, 0, 255).astype(np.uint8)
        decoded.append((rgba, transparent))
    cycle_table = off_frames + frame_count * 12
    cycles: list[list[int]] = []
    for sequence in range(cycle_count):
        slot_count, lookup_start = struct.unpack_from("<HH", payload, cycle_table + sequence * 4)
        cycle = list(struct.unpack_from(f"<{slot_count}H", payload, off_lookup + lookup_start * 2))
        if any(frame >= frame_count for frame in cycle):
            raise RuntimeError(f"{asset['resref']}: cycle lookup references an invalid frame")
        cycles.append(cycle)
    if not cycles or any(not cycle for cycle in cycles):
        raise RuntimeError(f"{asset['resref']}: empty BAM cycle is not supported")
    return decoded, cycles


def collect_records(
    source_run: Path, frame_suffix: str
) -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    source_manifest = json.loads((source_run / "run.json").read_text(encoding="utf-8"))
    if source_manifest.get("result", {}).get("status") != "completed" or not source_manifest.get(
        "result", {}
    ).get("sealed"):
        raise RuntimeError("source xBR2x+AA batch is not completed and sealed")

    assets = inventory_assets()
    expected_ids = {f"icons:icon-{asset['resref'].lower()}" for asset in assets}
    if set(source_manifest.get("asset_ids", [])) != expected_ids:
        raise RuntimeError("source batch asset_ids differ from current item-inventory authority")

    records: list[dict[str, object]] = []
    source_evidence: list[dict[str, str]] = []
    for asset in assets:
        resref = asset["resref"].upper()
        frames, cycles = decode_source(asset)
        if len(frames) != int(asset["frame_count"]):
            raise RuntimeError(f"{resref}: decoded frame count differs from resources.csv")
        source_evidence.append(
            {"resref": resref, "path": asset["extracted_path"], "sha256": asset["source_sha256"]}
        )
        replacements: list[tuple[bytes, int, int, str, str]] = []
        for frame_index, (rgba, _transparent) in enumerate(frames):
            height, width = rgba.shape[:2]
            png = (
                source_run
                / "assets"
                / resref
                / "frames"
                / f"frame-{frame_index:03d}-{frame_suffix}.png"
            )
            if not png.is_file():
                raise RuntimeError(f"{resref}:{frame_index}: xBR2x+AA PNG is absent")
            with Image.open(png) as image:
                replacement_image = image.convert("RGBA")
                if replacement_image.size != (width * SCALE, height * SCALE):
                    raise RuntimeError(f"{resref}:{frame_index}: replacement dimensions are not x2")
                replacement = replacement_image.tobytes()
            replacements.append(
                (replacement, width, height, png.relative_to(ROOT).as_posix(), sha256(png))
            )
        for sequence, cycle in enumerate(cycles):
            for slot, frame_index in enumerate(cycle):
                replacement, width, height, png_path, png_sha256 = replacements[frame_index]
                records.append(
                    {
                        "resref": resref,
                        "sequence": sequence,
                        "slot": slot,
                        "global_frame": frame_index,
                        "source_width": width,
                        "source_height": height,
                        "replacement_width": width * SCALE,
                        "replacement_height": height * SCALE,
                        "replacement": replacement,
                        "png_path": png_path,
                        "png_sha256": png_sha256,
                    }
                )
    return records, source_evidence


def write_pack(records: list[dict[str, object]], path: Path) -> None:
    data_offset = HEADER_BYTES + len(records) * RECORD_BYTES
    payload_bytes = sum(len(record["replacement"]) for record in records)  # type: ignore[arg-type]
    file_bytes = data_offset + payload_bytes
    output = bytearray(
        struct.pack(
            "<8sIIIIQQ", MAGIC, VERSION, SCALE, len(records), RECORD_BYTES, data_offset, file_bytes
        )
    )
    next_offset = data_offset
    for record in records:
        replacement = record["replacement"]
        resref = str(record["resref"]).encode("ascii")
        if not 1 <= len(resref) <= 8:
            raise RuntimeError(f"invalid resref {record['resref']}")
        output.extend(resref.ljust(8, b"\0"))
        output.extend(
            struct.pack(
                "<HHHHHHIQII",
                int(record["sequence"]),
                int(record["slot"]),
                int(record["source_width"]),
                int(record["source_height"]),
                int(record["replacement_width"]),
                int(record["replacement_height"]),
                int(record["global_frame"]),
                next_offset,
                len(replacement),  # type: ignore[arg-type]
                0,
            )
        )
        next_offset += len(replacement)  # type: ignore[arg-type]
    if len(output) != data_offset:
        raise AssertionError(f"record table size mismatch: {len(output)} != {data_offset}")
    for record in records:
        output.extend(record["replacement"])  # type: ignore[arg-type]
    if len(output) != file_bytes:
        raise AssertionError("pack byte count mismatch")
    path.write_bytes(output)


def build(
    *, run: bool, source_run_id: str, output_run_id: str, frame_suffix: str,
    method: str, alpha_contract: str
) -> dict[str, object]:
    source_run = ROOT / "icons" / "batches" / source_run_id
    output_run = ROOT / "icons" / "batches" / output_run_id
    records, sources = collect_records(source_run, frame_suffix)
    summary = {
        "source_run": source_run_id,
        "output_run": output_run_id,
        "asset_count": len({str(record["resref"]) for record in records}),
        "frame_count": len({(str(record["resref"]), int(record["global_frame"])) for record in records}),
        "mapping_count": len(records),
        "decoded_rgba_bytes": sum(len(record["replacement"]) for record in records),  # type: ignore[arg-type]
    }
    if not run:
        return summary
    if output_run.exists():
        raise FileExistsError(f"refusing to rewrite runtime batch: {output_run}")
    output_run.mkdir(parents=True)
    pack = output_run / PACK_NAME
    write_pack(records, pack)
    aggregate = hashlib.sha256()
    for record in records:
        aggregate.update(str(record["png_path"]).encode("utf-8"))
        aggregate.update(bytes.fromhex(str(record["png_sha256"])))
    manifest = {
        "schema": "bg2-upscale-item-icon-x2-runtime-pack-v2",
        **summary,
        "scale": SCALE,
        "method": method,
        "source_run_manifest": (source_run / "run.json").relative_to(ROOT).as_posix(),
        "source_run_sha256": sha256(source_run / "run.json"),
        "source_png_set_sha256": aggregate.hexdigest().upper(),
        "source_bams": sources,
        "registry": PACK_NAME,
        "registry_sha256": sha256(pack),
        "registry_bytes": pack.stat().st_size,
        "runtime_contract": {
            "logical_geometry": "stock-x1",
            "physical_texture_scale": 2,
            "alpha": alpha_contract,
            "identity": "CVidCell resref + normalized BAM sequence slot",
            "fallback": "stock CVidCell texture on unknown identity or unsafe runtime state",
        },
    }
    manifest_path = output_run / "build-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    recipe = {
        "schema": "bg2-upscale-item-icon-x2-runtime-recipe-v2",
        "source_run": source_run_id,
        "scale": SCALE,
        "identity": "CVidCell resref + BAM sequence + normalized cycle slot",
        "payload": "raw RGBA",
    }
    recipe_path = output_run / "recipe.json"
    recipe_path.write_text(json.dumps(recipe, indent=2) + "\n", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    run_manifest = {
        "$schema": "docs/workspace-run.schema.json",
        "schema_version": 1,
        "run_id": output_run_id,
        "domain": "icons",
        "asset_ids": [f"icons:icon-{resref.lower()}" for resref in sorted({str(record['resref']) for record in records})],
        "pipeline": {
            "id": "item-icon-x2-runtime-registry",
            "recipe_path": recipe_path.relative_to(ROOT).as_posix(),
            "recipe_sha256": sha256(recipe_path),
        },
        "inputs": [
            {
                "role": "sealed-xbr2x-aa-run",
                "path": (source_run / "run.json").relative_to(ROOT).as_posix(),
                "sha256": manifest["source_run_sha256"],
                "bytes": (source_run / "run.json").stat().st_size,
            }
        ],
        "outputs": [
            {
                "role": "runtime-registry",
                "path": pack.relative_to(ROOT).as_posix(),
                "sha256": manifest["registry_sha256"],
                "bytes": pack.stat().st_size,
            },
            {
                "role": "build-manifest",
                "path": manifest_path.relative_to(ROOT).as_posix(),
                "sha256": sha256(manifest_path),
                "bytes": manifest_path.stat().st_size,
            },
        ],
        "provenance": {
            "created_at_utc": now,
            "generator": "pipeline/scripts/build_item_icon_x2_registry.py",
            "command": ["python", "pipeline/scripts/build_item_icon_x2_registry.py", "--run"],
        },
        "result": {
            "status": "completed",
            "sealed": True,
            "completed_at_utc": now,
            "notes": "Runtime artifact only; QA, installation, and release remain separate.",
        },
    }
    (output_run / "run.json").write_text(
        json.dumps(run_manifest, indent=2) + "\n", encoding="utf-8"
    )
    return {**summary, "registry": str(pack), "registry_sha256": manifest["registry_sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="write the immutable runtime batch")
    parser.add_argument("--source-run-id", default="item-inventory-xbr2x-aa-v1")
    parser.add_argument("--output-run-id", default="item-inventory-xbr2x-aa-runtime-v2")
    parser.add_argument("--frame-suffix", default="xbr2x-aa")
    parser.add_argument("--method", default="XBR/xbr2X; x2; antialias on; RGBA")
    parser.add_argument("--alpha-contract", default="RGBA retained")
    args = parser.parse_args()
    result = build(
        run=args.run,
        source_run_id=args.source_run_id,
        output_run_id=args.output_run_id,
        frame_suffix=args.frame_suffix,
        method=args.method,
        alpha_contract=args.alpha_contract,
    )
    print(json.dumps(result, indent=2))
    if not args.run:
        print("Plan only; add --run to write the runtime batch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
