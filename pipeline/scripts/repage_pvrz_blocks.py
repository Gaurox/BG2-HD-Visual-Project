"""Repage a TIS/PVRZ atlas without decoding or re-encoding its DXT blocks.

Each TIS tile is copied together with its replicated atlas padding.  The DXT
block bytes therefore remain exact while page dimensions, page numbers and TIS
coordinates change.  The source is read-only and the output directory must not
exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import zlib


PVR_MAGIC = 0x03525650
TIS_SIGNATURE = b"TIS V1  "
MANIFEST_NAME = "repage-manifest.json"
MANIFEST_SCHEMA = "bg2-upscale-pvrz-block-repage-v1"
RESREF_MAX = 8
SUPPORTED_TILE_DIMENSIONS = {64, 128, 256, 512}
BLOCK_BYTES = {7: 8, 9: 16, 11: 16}


@dataclass(frozen=True)
class PvrPage:
    name: str
    decoded: bytes
    width: int
    height: int
    pixel_format: int
    block_bytes: int
    data_offset: int


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def decode_pvrz(path: Path) -> tuple[bytes, bytes]:
    blob = path.read_bytes()
    if len(blob) < 5:
        raise ValueError(f"{path.name}: PVRZ tronquée")
    expected_size = struct.unpack_from("<I", blob)[0]
    try:
        decoded = zlib.decompress(blob[4:])
    except zlib.error as exc:
        raise ValueError(f"{path.name}: flux zlib invalide") from exc
    if len(decoded) != expected_size:
        raise ValueError(
            f"{path.name}: taille PVR décodée {len(decoded)} au lieu de {expected_size}"
        )
    return blob, decoded


def parse_pvr(path: Path) -> tuple[PvrPage, bytes]:
    blob, decoded = decode_pvrz(path)
    if len(decoded) < 52:
        raise ValueError(f"{path.name}: en-tête PVR V3 tronqué")
    fields = struct.unpack_from("<13I", decoded)
    (
        magic,
        _flags,
        pixel_format,
        pixel_format_high,
        _colour_space,
        _channel_type,
        height,
        width,
        depth,
        surfaces,
        faces,
        mipmaps,
        metadata_bytes,
    ) = fields
    if magic != PVR_MAGIC:
        raise ValueError(f"{path.name}: signature PVR V3 invalide")
    if pixel_format_high != 0 or pixel_format not in BLOCK_BYTES:
        raise ValueError(f"{path.name}: format DXT/BC non pris en charge : {pixel_format}")
    if (depth, surfaces, faces, mipmaps) != (1, 1, 1, 1):
        raise ValueError(f"{path.name}: texture PVR complexe non prise en charge")
    if width <= 0 or height <= 0 or width % 4 or height % 4:
        raise ValueError(f"{path.name}: dimensions incompatibles DXT : {width}x{height}")
    data_offset = 52 + metadata_bytes
    expected_payload = (width // 4) * (height // 4) * BLOCK_BYTES[pixel_format]
    if data_offset + expected_payload != len(decoded):
        raise ValueError(f"{path.name}: taille du payload DXT incohérente")
    return (
        PvrPage(
            name=path.name.upper(),
            decoded=decoded,
            width=width,
            height=height,
            pixel_format=pixel_format,
            block_bytes=BLOCK_BYTES[pixel_format],
            data_offset=data_offset,
        ),
        blob,
    )


def parse_tis(path: Path) -> tuple[bytes, int, list[tuple[int, int, int]]]:
    payload = path.read_bytes()
    if len(payload) < 24 or payload[:8] != TIS_SIGNATURE:
        raise ValueError(f"{path.name}: TIS V1 invalide")
    tile_count, entry_size, header_size, tile_dimension = struct.unpack_from(
        "<IIII", payload, 8
    )
    if entry_size != 12 or header_size != 24:
        raise ValueError(f"{path.name}: layout TIS PVRZ inattendu")
    if tile_dimension not in SUPPORTED_TILE_DIMENSIONS:
        raise ValueError(f"{path.name}: dimension de tuile non prise en charge")
    if len(payload) != header_size + tile_count * entry_size:
        raise ValueError(f"{path.name}: taille TIS incohérente")
    entries = [
        struct.unpack_from("<III", payload, header_size + index * entry_size)
        for index in range(tile_count)
    ]
    return payload, tile_dimension, entries


def page_name(resref: str, page: int) -> str:
    prefix = resref[0] + resref[2:]
    name = f"{prefix}{page:02d}".upper()
    if len(name) > RESREF_MAX:
        raise ValueError(f"resref PVRZ trop long : {name}")
    return f"{name}.PVRZ"


def extract_cell(
    page: PvrPage,
    u: int,
    v: int,
    tile_dimension: int,
    padding: int,
) -> bytes:
    cell_pixels = tile_dimension + 2 * padding
    left = u - padding
    top = v - padding
    if min(left, top) < 0 or any(
        value % 4 for value in (left, top, cell_pixels)
    ):
        raise ValueError(
            f"{page.name}: cellule DXT non alignée à ({u}, {v}), padding {padding}"
        )
    if left + cell_pixels > page.width or top + cell_pixels > page.height:
        raise ValueError(f"{page.name}: cellule hors page à ({u}, {v})")
    source_blocks_per_row = page.width // 4
    cell_blocks = cell_pixels // 4
    left_block = left // 4
    top_block = top // 4
    rows = []
    for row in range(cell_blocks):
        start = page.data_offset + (
            (top_block + row) * source_blocks_per_row + left_block
        ) * page.block_bytes
        end = start + cell_blocks * page.block_bytes
        rows.append(page.decoded[start:end])
    return b"".join(rows)


def paste_cell(
    target: bytearray,
    cell: bytes,
    *,
    target_size: int,
    block_bytes: int,
    cell_pixels: int,
    column: int,
    row: int,
) -> None:
    target_blocks_per_row = target_size // 4
    cell_blocks = cell_pixels // 4
    left_block = column * cell_blocks
    top_block = row * cell_blocks
    row_bytes = cell_blocks * block_bytes
    for block_row in range(cell_blocks):
        source_start = block_row * row_bytes
        target_start = (
            (top_block + block_row) * target_blocks_per_row + left_block
        ) * block_bytes
        target[target_start : target_start + row_bytes] = cell[
            source_start : source_start + row_bytes
        ]


def build_pvr(template: PvrPage, target_size: int, dxt_payload: bytes) -> bytes:
    header = bytearray(template.decoded[: template.data_offset])
    struct.pack_into("<II", header, 24, target_size, target_size)
    expected = (target_size // 4) ** 2 * template.block_bytes
    if len(dxt_payload) != expected:
        raise RuntimeError("taille du nouvel atlas DXT incohérente")
    return bytes(header) + dxt_payload


def validate_resref(raw: str) -> str:
    resref = raw.upper()
    if not re.fullmatch(r"[A-Z0-9_]{3,8}", resref):
        raise ValueError(f"resref TIS invalide : {raw}")
    return resref


def repage_directory(
    source_root: Path,
    output_root: Path,
    *,
    target_size: int,
    padding: int,
    max_pages: int,
    compression_level: int,
) -> dict[str, object]:
    source = source_root.resolve()
    output = output_root.resolve()
    if not source.is_dir() or source.is_symlink():
        raise ValueError(f"dossier source absent ou non sûr : {source}")
    if source == output or output.exists():
        raise ValueError("la sortie doit être distincte et inexistante")
    if padding < 0 or padding % 4:
        raise ValueError("le padding doit être positif ou nul et aligné sur quatre pixels")
    if target_size <= 0 or target_size % 4:
        raise ValueError("la taille cible doit être positive et alignée sur quatre pixels")
    if max_pages < 1 or max_pages > 1000:
        raise ValueError("le plafond de pages est invalide")
    if compression_level not in range(10):
        raise ValueError("le niveau zlib doit être compris entre 0 et 9")

    tis_files = [
        path for path in source.iterdir() if path.is_file() and path.suffix.upper() == ".TIS"
    ]
    if len(tis_files) != 1:
        raise ValueError(f"la source doit contenir exactement un TIS, trouvé : {len(tis_files)}")
    tis_path = tis_files[0]
    resref = validate_resref(tis_path.stem)
    tis_payload, tile_dimension, entries = parse_tis(tis_path)
    cell_pixels = tile_dimension + 2 * padding
    if target_size % cell_pixels:
        raise ValueError(
            f"la page {target_size} doit être un multiple exact de la cellule {cell_pixels}"
        )
    cells_per_row = target_size // cell_pixels
    cells_per_page = cells_per_row * cells_per_row
    valid_entries = [entry for entry in entries if entry[0] != 0xFFFFFFFF]
    target_page_count = (len(valid_entries) + cells_per_page - 1) // cells_per_page
    naming_cap = 10 ** (RESREF_MAX - len(resref[0] + resref[2:]))
    effective_cap = min(max_pages, naming_cap)
    if target_page_count > effective_cap:
        raise ValueError(
            f"{len(valid_entries)} tuiles exigent {target_page_count} pages, plafond {effective_cap}"
        )

    referenced_pages = sorted({entry[0] for entry in valid_entries})
    expected_source_names = {page_name(resref, page) for page in referenced_pages}
    actual_source_paths = {
        path.name.upper(): path
        for path in source.iterdir()
        if path.is_file() and path.suffix.upper() == ".PVRZ"
    }
    if set(actual_source_paths) != expected_source_names:
        raise ValueError(
            "inventaire PVRZ source divergent ; "
            f"manquants={sorted(expected_source_names - set(actual_source_paths))}, "
            f"supplémentaires={sorted(set(actual_source_paths) - expected_source_names)}"
        )

    pages: dict[int, PvrPage] = {}
    source_records = []
    template: PvrPage | None = None
    for page_index in referenced_pages:
        name = page_name(resref, page_index)
        page, blob = parse_pvr(actual_source_paths[name])
        if template is None:
            template = page
        elif (
            page.pixel_format,
            page.block_bytes,
            page.decoded[: page.data_offset],
        ) != (
            template.pixel_format,
            template.block_bytes,
            template.decoded[: template.data_offset],
        ):
            # Width and height are the only allowed header differences.
            left = bytearray(page.decoded[: page.data_offset])
            right = bytearray(template.decoded[: template.data_offset])
            struct.pack_into("<II", left, 24, 0, 0)
            struct.pack_into("<II", right, 24, 0, 0)
            if left != right:
                raise ValueError(f"{name}: en-tête PVR incompatible avec les autres pages")
        pages[page_index] = page
        source_records.append(
            {
                "name": name,
                "bytes": len(blob),
                "sha256": sha256_bytes(blob),
                "decoded_bytes": len(page.decoded),
                "decoded_sha256": sha256_bytes(page.decoded),
                "width": page.width,
                "height": page.height,
            }
        )
    if template is None:
        raise ValueError("le TIS ne référence aucune page PVRZ")

    cells: list[bytes | None] = []
    source_cells_hash = hashlib.sha256()
    for tile_index, (page_index, u, v) in enumerate(entries):
        if page_index == 0xFFFFFFFF:
            cells.append(None)
            continue
        cell = extract_cell(pages[page_index], u, v, tile_dimension, padding)
        cells.append(cell)
        source_cells_hash.update(struct.pack("<I", tile_index))
        source_cells_hash.update(cell)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        target_payload_bytes = (target_size // 4) ** 2 * template.block_bytes
        target_payloads = [bytearray(target_payload_bytes) for _ in range(target_page_count)]
        new_entries: list[tuple[int, int, int]] = []
        valid_slot = 0
        for cell in cells:
            if cell is None:
                new_entries.append((0xFFFFFFFF, 0, 0))
                continue
            target_page, within = divmod(valid_slot, cells_per_page)
            row, column = divmod(within, cells_per_row)
            paste_cell(
                target_payloads[target_page],
                cell,
                target_size=target_size,
                block_bytes=template.block_bytes,
                cell_pixels=cell_pixels,
                column=column,
                row=row,
            )
            new_entries.append(
                (
                    target_page,
                    column * cell_pixels + padding,
                    row * cell_pixels + padding,
                )
            )
            valid_slot += 1

        new_tis = bytearray(tis_payload[:24])
        for entry in new_entries:
            new_tis.extend(struct.pack("<III", *entry))
        (temporary / tis_path.name.upper()).write_bytes(new_tis)

        output_records = []
        for page_index, dxt_payload in enumerate(target_payloads):
            decoded = build_pvr(template, target_size, bytes(dxt_payload))
            blob = struct.pack("<I", len(decoded)) + zlib.compress(
                decoded, compression_level
            )
            name = page_name(resref, page_index)
            (temporary / name).write_bytes(blob)
            output_records.append(
                {
                    "name": name,
                    "bytes": len(blob),
                    "sha256": sha256_bytes(blob),
                    "decoded_bytes": len(decoded),
                    "decoded_sha256": sha256_bytes(decoded),
                    "width": target_size,
                    "height": target_size,
                }
            )

        # Re-read the staged output and prove every copied DXT cell byte-exact.
        staged_pages = {
            page_index: parse_pvr(temporary / page_name(resref, page_index))[0]
            for page_index in range(target_page_count)
        }
        target_cells_hash = hashlib.sha256()
        for tile_index, ((page_index, u, v), source_cell) in enumerate(
            zip(new_entries, cells, strict=True)
        ):
            if source_cell is None:
                if page_index != 0xFFFFFFFF:
                    raise RuntimeError("sentinelle TIS modifiée pendant le repack")
                continue
            target_cell = extract_cell(
                staged_pages[page_index], u, v, tile_dimension, padding
            )
            if target_cell != source_cell:
                raise RuntimeError(f"tuile DXT divergente après repack : {tile_index}")
            target_cells_hash.update(struct.pack("<I", tile_index))
            target_cells_hash.update(target_cell)
        if target_cells_hash.digest() != source_cells_hash.digest():
            raise RuntimeError("empreinte agrégée des cellules DXT divergente")

        manifest: dict[str, object] = {
            "schema": MANIFEST_SCHEMA,
            "status": "completed-pending-ingame",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "method": "byte-exact DXT block cells with replicated padding",
            "source_root": str(source),
            "output_root": str(output),
            "resref": resref,
            "pixel_format": template.pixel_format,
            "tile_dimension": tile_dimension,
            "padding": padding,
            "cell_pixels": cell_pixels,
            "target_page_size": target_size,
            "cells_per_row": cells_per_row,
            "cells_per_page": cells_per_page,
            "source_pages": len(source_records),
            "target_pages": target_page_count,
            "max_pages": max_pages,
            "naming_cap": naming_cap,
            "compression": {"codec": "zlib", "level": compression_level},
            "source_tis": {
                "name": tis_path.name.upper(),
                "bytes": len(tis_payload),
                "sha256": sha256_bytes(tis_payload),
            },
            "output_tis": {
                "name": tis_path.name.upper(),
                "bytes": len(new_tis),
                "sha256": sha256_bytes(new_tis),
            },
            "valid_tiles": len(valid_entries),
            "sentinel_tiles": len(entries) - len(valid_entries),
            "dxt_cells_byte_exact": True,
            "dxt_cells_sha256": source_cells_hash.hexdigest().upper(),
            "source_pvrz_bytes": sum(int(record["bytes"]) for record in source_records),
            "output_pvrz_bytes": sum(int(record["bytes"]) for record in output_records),
            "source_files": source_records,
            "output_files": output_records,
        }
        (temporary / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repagine un atlas TIS/PVRZ en conservant exactement ses blocs DXT."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target-size", type=int, required=True)
    parser.add_argument("--padding", type=int, default=4)
    parser.add_argument("--max-pages", type=int, default=96)
    parser.add_argument("--level", type=int, choices=range(10), default=9)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = repage_directory(
        args.source,
        args.output,
        target_size=args.target_size,
        padding=args.padding,
        max_pages=args.max_pages,
        compression_level=args.level,
    )
    print(
        f"Pages PVRZ : {manifest['source_pages']} -> {manifest['target_pages']} "
        f"({manifest['target_page_size']}x{manifest['target_page_size']})"
    )
    print(f"Cellules DXT identiques : {manifest['dxt_cells_byte_exact']}")
    print(
        "Taille PVRZ : "
        f"{int(manifest['source_pvrz_bytes']) / 1024 / 1024:.2f} -> "
        f"{int(manifest['output_pvrz_bytes']) / 1024 / 1024:.2f} MiB"
    )
    print(f"Manifeste : {Path(args.output).resolve() / MANIFEST_NAME}")


if __name__ == "__main__":
    main()
