"""Build canonical inventories for previously uncovered BG2EE graphics.

The scanner reads the installed stock game in place, writes only versioned
catalogues under the workspace, and can materialise immutable source copies in
ignored data-plane directories with explicit extraction options. It never writes the game.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
from typing import Any, Iterable, Mapping, Sequence
import zlib

from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME_DIR = get_path("bg2ee_game_root")
GENERATOR = "pipeline/scripts/build_graphics_inventory.py"

TYPE_BMP = 0x0001
TYPE_PLT = 0x0006
TYPE_BAM = 0x03E8
TYPE_MOS = 0x03EC
TYPE_ITM = 0x03ED
TYPE_SPL = 0x03EE
TYPE_VVC = 0x03FB
TYPE_VEF = 0x03FC
TYPE_PRO = 0x03FD
TYPE_WBM = 0x03FF
TYPE_FNT = 0x0400
TYPE_PVRZ = 0x0404
TYPE_TTF = 0x040A
TYPE_PNG = 0x040B

TYPE_NAMES = {
    TYPE_BMP: "BMP",
    TYPE_PLT: "PLT",
    TYPE_BAM: "BAM",
    TYPE_MOS: "MOS",
    TYPE_ITM: "ITM",
    TYPE_SPL: "SPL",
    TYPE_VVC: "VVC",
    TYPE_VEF: "VEF",
    TYPE_PRO: "PRO",
    TYPE_WBM: "WBM",
    TYPE_FNT: "FNT",
    TYPE_PVRZ: "PVRZ",
    TYPE_TTF: "TTF",
    TYPE_PNG: "PNG",
}
TYPE_EXTENSIONS = {resource_type: name.lower() for resource_type, name in TYPE_NAMES.items()}
GRAPHICAL_TYPES = {
    TYPE_BMP,
    TYPE_PLT,
    TYPE_BAM,
    TYPE_MOS,
    TYPE_VVC,
    TYPE_VEF,
    TYPE_PRO,
    TYPE_WBM,
    TYPE_FNT,
    TYPE_PVRZ,
    TYPE_TTF,
    TYPE_PNG,
}

OUTPUT_PATHS = {
    "video_manifest": "video/index/manifest.json",
    "video_resources": "video/index/resources.csv",
    "hud_manifest": "interface/gameplay-hud-bg2ee/index/manifest.json",
    "hud_resources": "interface/gameplay-hud-bg2ee/index/resources.csv",
    "hud_dependencies": "interface/gameplay-hud-bg2ee/index/dependencies.csv",
    "icon_manifest": "icons/index/manifest.json",
    "icon_resources": "icons/index/resources.csv",
    "icon_families": "icons/index/families.csv",
    "icon_usages": "icons/index/usages.csv",
    "icon_frames": "icons/index/frames.csv",
    "icon_dependencies": "icons/index/dependencies.csv",
    "icon_missing_resources": "icons/index/missing-resources.csv",
    "cursor_manifest": "cursors/index/manifest.json",
    "cursor_resources": "cursors/index/resources.csv",
    "effect_manifest": "effects/index/manifest.json",
    "effect_resources": "effects/index/resources.csv",
    "effect_dependencies": "effects/index/dependencies.csv",
    "effect_bam_assets": "effects/index/bam-assets.csv",
    "projectile_manifest": "projectiles/index/manifest.json",
    "projectile_resources": "projectiles/index/resources.csv",
    "projectile_dependencies": "projectiles/index/dependencies.csv",
    "font_manifest": "interface/fonts/index/manifest.json",
    "font_resources": "interface/fonts/index/resources.csv",
    "ui_manifest": "interface/index/manifest.json",
    "ui_resources": "interface/index/resources.csv",
    "ui_dependencies": "interface/index/dependencies.csv",
    "supplemental_manifest": "graphics/index/supplemental-manifest.json",
    "supplemental_resources": "graphics/index/supplemental-assets.csv",
    "graphics_coverage": "graphics/index/coverage.json",
    "graphics_unclassified": "graphics/index/unclassified-resources.csv",
}

HUD_RESOURCES = {
    "GUIW12_1": "bottom-panel",
    "GUIW12_2": "bottom-panel",
    "GUIW12_3": "bottom-panel",
    "GUIW12_4": "bottom-panel",
    "GUIW12_5": "bottom-panel",
    "GUIW12_6": "bottom-panel",
    "GUIW12_7": "bottom-panel",
    "GUIW12_8": "bottom-panel",
    "GUIWLS20": "left-panel",
    "GUIWRS20": "right-panel",
    "GUIVERB": "shared-bottom-panel",
    "GUILS10": "left-toolbar",
    "GUILS20": "alternate-left-toolbar",
    "GUIBTACT": "action-buttons",
    "GUIWDB10": "action-slots",
    "GUIWDBUT": "action-slots",
    "GUICTRL": "world-controls",
    "GUIWCTLC": "world-controls",
    "GUIWSBR": "world-controls",
    "GUIWSMB": "world-controls",
    "GUIWPKPC": "world-controls",
    "GUPORTC": "portrait-frame",
    "GUIJRNLC": "journal-control",
    "GUIPFC": "portrait-control",
}

SUPPLEMENTAL_BIF_RULES = {
    "PAPERDOL.BIF": ("sprites", "paperdoll-animation-bam"),
    "OBJANIM.BIF": ("sprites", "object-animation-bam"),
    "25CREANI.BIF": ("sprites", "creature-animation-bam"),
    "CHAANIM.BIF": ("sprites", "character-animation-bam"),
    "SPELANIM.BIF": ("effects", "spell-animation-bam"),
    "25SPELAN.BIF": ("effects", "spell-animation-bam"),
    "MISCANIM.BIF": ("effects", "misc-animation-bam"),
    "25MISCAN.BIF": ("effects", "misc-animation-bam"),
    "SPELLS.BIF": ("effects", "spell-animation-bam"),
    "25GUIBAM.BIF": ("ui", "ui-bam"),
    "25GUIDES.BIF": ("ui", "ui-bam"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def csv_bytes(fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(
        stream,
        fieldnames=fieldnames,
        extrasaction="raise",
        lineterminator="\r\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def read_resref(data: bytes, offset: int) -> str:
    if offset + 8 > len(data):
        return ""
    return data[offset : offset + 8].split(b"\0", 1)[0].decode(
        "ascii", errors="replace"
    ).upper()


@dataclass(frozen=True)
class KeyResource:
    resref: str
    resource_type: int
    locator: int
    bif_name: str

    @property
    def key(self) -> tuple[str, int]:
        return self.resref, self.resource_type


class KeyIndex:
    def __init__(self, game_dir: Path) -> None:
        self.game_dir = game_dir.resolve()
        key_path = self.game_dir / "chitin.key"
        data = key_path.read_bytes()
        if data[:8] != b"KEY V1  ":
            raise RuntimeError(f"chitin.key non supporté: {data[:8]!r}")
        bif_count, resource_count, bif_offset, resource_offset = struct.unpack_from(
            "<IIII", data, 8
        )
        self.bifs: list[str] = []
        for index in range(bif_count):
            offset = bif_offset + index * 12
            _length, name_offset, name_length, _location = struct.unpack_from(
                "<IIHH", data, offset
            )
            name = data[name_offset : name_offset + name_length].split(b"\0", 1)[0]
            self.bifs.append(name.decode("cp1252", errors="strict").replace("\\", "/"))
        resources: list[KeyResource] = []
        for index in range(resource_count):
            offset = resource_offset + index * 14
            raw_name, resource_type, locator = struct.unpack_from("<8sHI", data, offset)
            resref = raw_name.split(b"\0", 1)[0].decode("cp1252", errors="strict").upper()
            bif_index = (locator >> 20) & 0xFFF
            if bif_index >= len(self.bifs):
                raise RuntimeError(f"locator BIF invalide pour {resref}")
            resources.append(
                KeyResource(resref, resource_type, locator, self.bifs[bif_index])
            )
        self.resources = resources
        self.by_key: dict[tuple[str, int], KeyResource] = {}
        self.duplicates: list[tuple[str, int]] = []
        for resource in resources:
            if resource.key in self.by_key:
                self.duplicates.append(resource.key)
            else:
                self.by_key[resource.key] = resource
        self.key_sha256 = sha256_bytes(data)
        self._bif_tables: dict[str, dict[int, tuple[int, int, int]]] = {}
        self._bif_buffers: dict[str, bytes] = {}

    def entries(self, resource_type: int) -> list[KeyResource]:
        return [item for item in self.resources if item.resource_type == resource_type]

    def get(self, resref: str, resource_type: int) -> KeyResource | None:
        return self.by_key.get((resref.upper(), resource_type))

    def resolve(self, resource: KeyResource) -> bytes:
        table = self._load_bif_table(resource.bif_name)
        file_index = resource.locator & 0x3FFF
        try:
            offset, size, actual_type = table[file_index]
        except KeyError as error:
            raise RuntimeError(
                f"locator {resource.locator:#x} absent de {resource.bif_name}"
            ) from error
        if actual_type != resource.resource_type:
            raise RuntimeError(
                f"type BIF divergent pour {resource.resref}: {actual_type:#x}"
            )
        buffer = self._bif_buffers.get(resource.bif_name)
        if buffer is not None:
            return buffer[offset : offset + size]
        path = self.game_dir / Path(resource.bif_name)
        with path.open("rb") as stream:
            stream.seek(offset)
            data = stream.read(size)
        if len(data) != size:
            raise RuntimeError(f"lecture tronquée: {resource.bif_name}:{offset}+{size}")
        return data

    def _load_bif_table(self, bif_name: str) -> dict[int, tuple[int, int, int]]:
        cached = self._bif_tables.get(bif_name)
        if cached is not None:
            return cached
        path = self.game_dir / Path(bif_name)
        with path.open("rb") as stream:
            signature = stream.read(4)
            stream.seek(0)
            raw = stream.read() if signature == b"BIFC" else b""
        if signature == b"BIFC":
            position = 8
            expected_size = struct.unpack_from("<I", raw, position)[0]
            position += 4
            chunks = []
            while position < len(raw):
                uncompressed_size, compressed_size = struct.unpack_from(
                    "<II", raw, position
                )
                position += 8
                chunk = zlib.decompress(raw[position : position + compressed_size])
                position += compressed_size
                if len(chunk) != uncompressed_size:
                    raise RuntimeError(f"bloc BIFC invalide: {bif_name}")
                chunks.append(chunk)
            buffer = b"".join(chunks)
            if len(buffer) != expected_size:
                raise RuntimeError(f"taille BIFC invalide: {bif_name}")
            self._bif_buffers[bif_name] = buffer
            header = buffer[:20]
            file_count, _tileset_count, files_offset = struct.unpack_from(
                "<III", header, 8
            )
            entries_raw = buffer[files_offset : files_offset + file_count * 16]
        elif signature == b"BIFF":
            with path.open("rb") as stream:
                header = stream.read(20)
                file_count, _tileset_count, files_offset = struct.unpack_from(
                    "<III", header, 8
                )
                stream.seek(files_offset)
                entries_raw = stream.read(file_count * 16)
        else:
            raise RuntimeError(f"BIF non supporté {bif_name}: {signature!r}")
        table: dict[int, tuple[int, int, int]] = {}
        for index in range(file_count):
            locator, offset, size, resource_type, _unknown = struct.unpack_from(
                "<IIIHH", entries_raw, index * 16
            )
            table[locator & 0x3FFF] = (offset, size, resource_type)
        self._bif_tables[bif_name] = table
        return table


def bam_metadata(data: bytes) -> dict[str, Any]:
    container = "BAM"
    if data[:4] == b"BAMC":
        data = zlib.decompress(data[12:])
        container = "BAMC"
    if data[:8] == b"BAM V1  ":
        frame_count, cycle_count = struct.unpack_from("<HB", data, 8)
        return {
            "container": container,
            "version": "V1",
            "frame_count": frame_count,
            "cycle_count": cycle_count,
            "block_count": "",
            "pvrz_pages": [],
        }
    if data[:8] == b"BAM V2  ":
        _signature, frame_count, cycle_count, block_count, _frames, _cycles, blocks, _ = struct.unpack_from(
            "<8s7I", data, 0
        )
        pages = sorted(
            {
                struct.unpack_from("<I", data, blocks + index * 28)[0]
                for index in range(block_count)
            }
        )
        return {
            "container": container,
            "version": "V2",
            "frame_count": frame_count,
            "cycle_count": cycle_count,
            "block_count": block_count,
            "pvrz_pages": pages,
        }
    raise ValueError(f"BAM non supporté: {data[:8]!r}")


def bam_frame_metadata(data: bytes) -> list[dict[str, int | str]]:
    if data[:4] == b"BAMC":
        data = zlib.decompress(data[12:])
    if data[:8] == b"BAM V1  ":
        frame_count = struct.unpack_from("<H", data, 8)[0]
        frames_offset = struct.unpack_from("<I", data, 0x0C)[0]
        version = "V1"
    elif data[:8] == b"BAM V2  ":
        _signature, frame_count, _cycles, _blocks, frames_offset, _, _, _ = (
            struct.unpack_from("<8s7I", data, 0)
        )
        version = "V2"
    else:
        raise ValueError(f"BAM non supporté: {data[:8]!r}")

    rows: list[dict[str, int | str]] = []
    for frame_index in range(frame_count):
        width, height, center_x, center_y, packed = struct.unpack_from(
            "<HHhhI", data, frames_offset + frame_index * 12
        )
        rows.append(
            {
                "frame_index": frame_index,
                "width": width,
                "height": height,
                "center_x": center_x,
                "center_y": center_y,
                "block_count": packed >> 16 if version == "V2" else "",
            }
        )
    return rows


def mos_metadata(data: bytes) -> dict[str, Any]:
    if data[:4] == b"MOSC":
        data = zlib.decompress(data[12:])
    if data[:8] == b"MOS V1  ":
        width, height = struct.unpack_from("<HH", data, 8)
        return {"version": "V1", "width": width, "height": height, "pvrz_pages": []}
    if data[:8] == b"MOS V2  ":
        width, height, block_count, blocks_offset = struct.unpack_from("<IIII", data, 8)
        pages = sorted(
            {
                struct.unpack_from("<I", data, blocks_offset + index * 28)[0]
                for index in range(block_count)
            }
        )
        return {"version": "V2", "width": width, "height": height, "pvrz_pages": pages}
    raise ValueError(f"MOS non supporté: {data[:8]!r}")


def ffprobe_metadata(payload: bytes, ffprobe: str) -> dict[str, Any]:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate",
        "-of",
        "json",
        "-i",
        "pipe:0",
    ]
    result = subprocess.run(command, input=payload, capture_output=True, check=True)
    document = json.loads(result.stdout.decode("utf-8"))
    video = next(
        (stream for stream in document.get("streams", []) if stream.get("codec_type") == "video"),
        {},
    )
    audio = next(
        (stream for stream in document.get("streams", []) if stream.get("codec_type") == "audio"),
        {},
    )
    duration = document.get("format", {}).get("duration")
    duration_ms = round(float(duration) * 1000) if duration not in (None, "N/A") else ""
    return {
        "width": video.get("width", ""),
        "height": video.get("height", ""),
        "frame_rate": video.get("avg_frame_rate", ""),
        "duration_ms": duration_ms,
        "video_codec": video.get("codec_name", ""),
        "audio_codec": audio.get("codec_name", ""),
    }


def resource_row(index: KeyIndex, resource: KeyResource, raw: bytes) -> dict[str, Any]:
    return {
        "resref": resource.resref,
        "resource_type": TYPE_NAMES.get(resource.resource_type, f"0x{resource.resource_type:04X}"),
        "source_bif": resource.bif_name,
        "locator": f"0x{resource.locator:08X}",
        "source_size": len(raw),
        "source_sha256": sha256_bytes(raw),
    }


def find_dependency(
    index: KeyIndex, resref: str, allowed_types: Sequence[int]
) -> KeyResource | None:
    for resource_type in allowed_types:
        found = index.get(resref, resource_type)
        if found is not None:
            return found
    return None


def extract_payload(path: Path, payload: bytes) -> None:
    if path.is_file():
        if sha256_file(path) != sha256_bytes(payload):
            raise RuntimeError(f"extraction existante divergente: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def manifest_base(index: KeyIndex, domain: str, asset_count: int) -> dict[str, Any]:
    return {
        "schema": f"bg2-upscale-{domain}-inventory-v1",
        "generated_by": GENERATOR,
        "source_policy": "stock BG2EE installation; KEY/BIF or loose movie files only",
        "chitin_key_sha256": index.key_sha256,
        "asset_count": asset_count,
    }


def build_videos(
    index: KeyIndex, ffprobe: str, extract: bool
) -> tuple[dict[str, Any], list[dict[str, Any]], set[tuple[str, int]]]:
    rows: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    movie_paths = sorted(
        [*(index.game_dir / "movies").glob("*.wbm"), *index.game_dir.glob("lang/*/movies/*.wbm")],
        key=lambda path: path.as_posix().casefold(),
    )
    for path in movie_paths:
        relative = path.relative_to(index.game_dir).as_posix()
        parts = relative.split("/")
        locale = parts[1] if parts[0].lower() == "lang" else "default"
        resref = path.stem.upper()
        payload = path.read_bytes()
        extracted_relative = (
            Path("video")
            / (resref.lower() if locale == "default" else f"{locale}_{resref.lower()}")
            / (path.name if locale == "default" else f"{locale}_{path.name}")
        )
        if extract:
            extract_payload(ROOT / extracted_relative, payload)
        rows.append(
            {
                "asset_key": f"movie:{locale}:{resref}",
                "resref": resref,
                "role": "cinematic",
                "locale": locale,
                "source_kind": "loose-file",
                "source_path": relative,
                "source_bif": "",
                "locator": "",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                **ffprobe_metadata(payload, ffprobe),
                "extracted_path": extracted_relative.as_posix(),
            }
        )

    area_wbm = {
        row["resource_resref"].upper()
        for row in read_csv(ROOT / "animations/index/occurrences.csv")
        if row.get("resource_kind") == "WBM"
    }
    for resource in sorted(index.entries(TYPE_WBM), key=lambda item: item.resref):
        if resource.resref in area_wbm:
            continue
        payload = index.resolve(resource)
        owned.add(resource.key)
        extracted_relative = Path("video/tutorials") / resource.resref.lower() / (
            resource.resref.lower() + ".wbm"
        )
        if extract:
            extract_payload(ROOT / extracted_relative, payload)
        rows.append(
            {
                "asset_key": f"tutorial:engine:{resource.resref}",
                "resref": resource.resref,
                "role": "tutorial-clip",
                "locale": "engine",
                "source_kind": "key-bif",
                "source_path": "",
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                **ffprobe_metadata(payload, ffprobe),
                "extracted_path": extracted_relative.as_posix(),
            }
        )
    rows.sort(key=lambda row: row["asset_key"])
    manifest = {
        **manifest_base(index, "video", len(rows)),
        "loose_movie_count": sum(row["source_kind"] == "loose-file" for row in rows),
        "key_tutorial_count": sum(row["source_kind"] == "key-bif" for row in rows),
        "area_wbm_excluded_count": len(area_wbm),
        "area_wbm_authority": "animations/index/occurrences.csv",
        "resources_csv": "video/index/resources.csv",
    }
    return manifest, rows, owned


def build_hud(
    index: KeyIndex, extract: bool
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[tuple[str, int]],
]:
    rows: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resref, role in sorted(HUD_RESOURCES.items()):
        resource = find_dependency(index, resref, (TYPE_BAM, TYPE_MOS))
        if resource is None:
            raise RuntimeError(f"ressource HUD absente: {resref}")
        payload = index.resolve(resource)
        owned.add(resource.key)
        if resource.resource_type == TYPE_BAM:
            metadata = bam_metadata(payload)
            width = height = ""
        else:
            metadata = mos_metadata(payload)
            width, height = metadata["width"], metadata["height"]
        extension = TYPE_EXTENSIONS[resource.resource_type]
        extracted_relative = (
            Path("interface/gameplay-hud-bg2ee/source")
            / extension
            / f"{resref}.{extension.lower()}"
        )
        if extract:
            extract_payload(ROOT / extracted_relative, payload)
        rows.append(
            {
                "asset_key": f"hud:{resref}",
                "resref": resref,
                "role": role,
                "format": TYPE_NAMES[resource.resource_type],
                "container_version": metadata["version"],
                "frame_count": metadata.get("frame_count", ""),
                "cycle_count": metadata.get("cycle_count", ""),
                "width": width,
                "height": height,
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                "extracted_path": extracted_relative.as_posix(),
            }
        )
        for page in metadata.get("pvrz_pages", []):
            page_resref = f"MOS{page:04d}"
            page_resource = index.get(page_resref, TYPE_PVRZ)
            dependencies.append(
                {
                    "asset_key": f"hud:{resref}",
                    "relation": "texture-page",
                    "dependency_resref": page_resref,
                    "dependency_format": "PVRZ",
                    "present": "yes" if page_resource else "no",
                    "source_bif": page_resource.bif_name if page_resource else "",
                    "locator": f"0x{page_resource.locator:08X}" if page_resource else "",
                }
            )
            if page_resource:
                owned.add(page_resource.key)
    dependencies.sort(
        key=lambda row: (row["asset_key"], row["dependency_resref"])
    )
    manifest = {
        **manifest_base(index, "hud", len(rows)),
        "granularity": "one logical BAM or MOS composition; PVRZ pages are dependencies",
        "resources_csv": "interface/gameplay-hud-bg2ee/index/resources.csv",
        "dependencies_csv": "interface/gameplay-hud-bg2ee/index/dependencies.csv",
        "missing_dependency_count": sum(row["present"] == "no" for row in dependencies),
        "excluded_existing_animation_resrefs": ["PORTL1A", "PORTL1B", "PORTL2A"],
    }
    return manifest, rows, dependencies, owned


def icon_references(kind: str, resref: str, data: bytes) -> list[dict[str, str]]:
    if kind == "ITM":
        if len(data) < 0x60 or data[:4] != b"ITM ":
            raise ValueError(f"{resref}: ITM invalide")
        fields = (
            ("item-inventory", 0x3A),
            ("item-ground", 0x44),
            ("item-description", 0x58),
        )
    elif kind == "SPL":
        if len(data) < 0x60 or data[:4] != b"SPL ":
            raise ValueError(f"{resref}: SPL invalide")
        fields = (("spellbook", 0x3A),)
    else:
        raise ValueError(f"type d'usage icône inconnu: {kind}")
    return [
        {"owner_format": kind, "owner_resref": resref, "role": role, "icon_resref": value}
        for role, offset in fields
        if (value := read_resref(data, offset))
    ]


def build_icons(
    index: KeyIndex, extract: bool
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[tuple[str, int]],
]:
    usages: list[dict[str, Any]] = []
    for resource_type, kind in ((TYPE_ITM, "ITM"), (TYPE_SPL, "SPL")):
        for owner in sorted(index.entries(resource_type), key=lambda item: item.resref):
            usages.extend(icon_references(kind, owner.resref, index.resolve(owner)))
    usages.sort(
        key=lambda row: (
            row["icon_resref"],
            row["role"],
            row["owner_format"],
            row["owner_resref"],
        )
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for usage in usages:
        grouped[usage["icon_resref"]].append(usage)
    rows: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    frames: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resref, resource_usages in sorted(grouped.items()):
        resource = index.get(resref, TYPE_BAM)
        if resource is None:
            roles = sorted({usage["role"] for usage in resource_usages})
            missing_rows.append(
                {
                    "icon_resref": resref,
                    "roles": ";".join(roles),
                    "usage_count": len(resource_usages),
                    "owner_count": len(
                        {
                            (usage["owner_format"], usage["owner_resref"])
                            for usage in resource_usages
                        }
                    ),
                }
            )
            continue
        payload = index.resolve(resource)
        metadata = bam_metadata(payload)
        owned.add(resource.key)
        asset_key = f"icon:{resref}"
        extracted_relative = Path("icons/ressources") / resref / "source.bam"
        if extract:
            extract_payload(ROOT / extracted_relative, payload)
        roles = sorted({usage["role"] for usage in resource_usages})
        for role in roles:
            role_usages = [usage for usage in resource_usages if usage["role"] == role]
            families.append(
                {
                    "asset_key": asset_key,
                    "resref": resref,
                    "family": role,
                    "usage_count": len(role_usages),
                    "owner_count": len(
                        {
                            (usage["owner_format"], usage["owner_resref"])
                            for usage in role_usages
                        }
                    ),
                }
            )
        for frame in bam_frame_metadata(payload):
            frames.append({"asset_key": asset_key, "resref": resref, **frame})

        dependency_count = 0
        for page in metadata["pvrz_pages"]:
            page_resref = f"MOS{page:04d}"
            dependency = index.get(page_resref, TYPE_PVRZ)
            dependency_payload = index.resolve(dependency) if dependency else None
            dependency_path = (
                Path("icons/dependencies/pvrz") / f"{page_resref}.pvrz"
                if dependency_payload is not None
                else None
            )
            if dependency is not None:
                owned.add(dependency.key)
            if extract and dependency_payload is not None and dependency_path is not None:
                extract_payload(ROOT / dependency_path, dependency_payload)
            dependencies.append(
                {
                    "asset_key": asset_key,
                    "relation": "texture-page",
                    "dependency_resref": page_resref,
                    "dependency_format": "PVRZ",
                    "present": "yes" if dependency_payload is not None else "no",
                    "source_bif": dependency.bif_name if dependency else "",
                    "locator": f"0x{dependency.locator:08X}" if dependency else "",
                    "source_size": len(dependency_payload) if dependency_payload is not None else "",
                    "source_sha256": (
                        sha256_bytes(dependency_payload)
                        if dependency_payload is not None
                        else ""
                    ),
                    "extracted_path": dependency_path.as_posix() if dependency_path else "",
                }
            )
            dependency_count += 1
        rows.append(
            {
                "asset_key": asset_key,
                "resref": resref,
                "roles": ";".join(roles),
                "usage_count": len(resource_usages),
                "owner_count": len(
                    {
                        (usage["owner_format"], usage["owner_resref"])
                        for usage in resource_usages
                    }
                ),
                "bam_container": metadata["container"],
                "bam_version": metadata["version"],
                "frame_count": metadata["frame_count"],
                "cycle_count": metadata["cycle_count"],
                "block_count": metadata["block_count"],
                "pvrz_dependency_count": dependency_count,
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                "extracted_path": extracted_relative.as_posix(),
            }
        )
    families.sort(key=lambda row: (row["asset_key"], row["family"]))
    frames.sort(key=lambda row: (row["asset_key"], row["frame_index"]))
    dependencies.sort(
        key=lambda row: (row["asset_key"], row["dependency_resref"])
    )
    manifest = {
        **manifest_base(index, "icons", len(rows)),
        "schema": "bg2-upscale-icons-inventory-v2",
        "granularity": "one BAM icon set shared by all referencing ITM/SPL resources",
        "resources_csv": "icons/index/resources.csv",
        "families_csv": "icons/index/families.csv",
        "usages_csv": "icons/index/usages.csv",
        "frames_csv": "icons/index/frames.csv",
        "dependencies_csv": "icons/index/dependencies.csv",
        "missing_resources_csv": "icons/index/missing-resources.csv",
        "usage_count": len(usages),
        "family_membership_count": len(families),
        "frame_record_count": len(frames),
        "dependency_count": len(dependencies),
        "dependency_resource_count": len(
            {row["dependency_resref"] for row in dependencies}
        ),
        "missing_dependency_count": sum(
            row["present"] == "no" for row in dependencies
        ),
        "missing_resource_count": len(missing_rows),
        "missing_icon_resrefs": [row["icon_resref"] for row in missing_rows],
        "extraction_layout": {
            "bam": "icons/ressources/<RESREF>/source.bam",
            "pvrz": "icons/dependencies/pvrz/<RESREF>.pvrz",
        },
    }
    return (
        manifest,
        rows,
        families,
        usages,
        frames,
        dependencies,
        missing_rows,
        owned,
    )


def build_cursors(
    index: KeyIndex, extract: bool
) -> tuple[dict[str, Any], list[dict[str, Any]], set[tuple[str, int]]]:
    resource = index.get("CURSORS", TYPE_BAM)
    if resource is None:
        raise RuntimeError("CURSORS.BAM absent du chitin.key")
    payload = index.resolve(resource)
    metadata = bam_metadata(payload)
    extracted_relative = Path("cursors/source/CURSORS.bam")
    if extract:
        extract_payload(ROOT / extracted_relative, payload)
    rows = [
        {
            "asset_key": "cursor-set:CURSORS",
            "resref": "CURSORS",
            "granularity": "single-engine-cursor-set",
            "bam_container": metadata["container"],
            "bam_version": metadata["version"],
            "frame_count": metadata["frame_count"],
            "cycle_count": metadata["cycle_count"],
            "source_bif": resource.bif_name,
            "locator": f"0x{resource.locator:08X}",
            "source_size": len(payload),
            "source_sha256": sha256_bytes(payload),
            "extracted_path": extracted_relative.as_posix(),
        }
    ]
    manifest = {
        **manifest_base(index, "cursors", 1),
        "granularity": "one CURSORS.BAM set; cycles are unnamed members, not invented assets",
        "resources_csv": "cursors/index/resources.csv",
    }
    return manifest, rows, {resource.key}


def parse_vvc_dependencies(data: bytes) -> list[tuple[str, str, tuple[int, ...]]]:
    if len(data) < 0x90 or data[:8] != b"VVC V1.0":
        raise ValueError(f"VVC invalide: {data[:8]!r}")
    dependencies = []
    animation = read_resref(data, 0x08)
    if animation:
        dependencies.append(("animation", animation, (TYPE_BAM,)))
    palette = read_resref(data, 0x44)
    if palette:
        dependencies.append(("palette", palette, (TYPE_BMP,)))
    alpha = read_resref(data, 0x88)
    if alpha:
        dependencies.append(("alpha-animation", alpha, (TYPE_BAM,)))
    return dependencies


def parse_vef_dependencies(data: bytes) -> list[tuple[str, str, tuple[int, ...]]]:
    if len(data) < 0x18 or data[:4] != b"VEF ":
        raise ValueError(f"VEF invalide: {data[:8]!r}")
    dependencies = []
    for table_index, (offset_pos, count_pos) in enumerate(((0x08, 0x0C), (0x10, 0x14)), 1):
        offset = struct.unpack_from("<I", data, offset_pos)[0]
        count = struct.unpack_from("<I", data, count_pos)[0]
        if offset + count * 0xE0 > len(data):
            raise ValueError("table VEF hors limites")
        for component_index in range(count):
            position = offset + component_index * 0xE0
            resource_kind = struct.unpack_from("<I", data, position + 0x0C)[0]
            resref = read_resref(data, position + 0x10)
            if not resref:
                continue
            allowed = {
                0: (),
                1: (TYPE_VVC, TYPE_BAM),
                2: (TYPE_VEF, TYPE_VVC, TYPE_BAM),
            }.get(resource_kind, ())
            if allowed:
                dependencies.append(
                    (f"component-{table_index}-{component_index}", resref, allowed)
                )
    return dependencies


def build_effects(
    index: KeyIndex, extract: bool
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[tuple[str, int]],
]:
    rows: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resource_type in (TYPE_VVC, TYPE_VEF):
        for resource in sorted(index.entries(resource_type), key=lambda item: item.resref):
            payload = index.resolve(resource)
            format_name = TYPE_NAMES[resource_type]
            owned.add(resource.key)
            extracted_relative = (
                Path("effects/source")
                / format_name.lower()
                / f"{resource.resref}.{format_name.lower()}"
            )
            if extract:
                extract_payload(ROOT / extracted_relative, payload)
            parsed = (
                parse_vvc_dependencies(payload)
                if resource_type == TYPE_VVC
                else parse_vef_dependencies(payload)
            )
            rows.append(
                {
                    "asset_key": f"effect:{format_name.lower()}:{resource.resref}",
                    "resref": resource.resref,
                    "format": format_name,
                    "dependency_count": len(parsed),
                    "source_bif": resource.bif_name,
                    "locator": f"0x{resource.locator:08X}",
                    "source_size": len(payload),
                    "source_sha256": sha256_bytes(payload),
                    "extracted_path": extracted_relative.as_posix(),
                }
            )
            for relation, dependency_resref, allowed_types in parsed:
                dependency = find_dependency(index, dependency_resref, allowed_types)
                dependencies.append(
                    {
                        "asset_key": f"effect:{format_name.lower()}:{resource.resref}",
                        "relation": relation,
                        "dependency_resref": dependency_resref,
                        "allowed_formats": ";".join(TYPE_NAMES[value] for value in allowed_types),
                        "resolved_format": TYPE_NAMES[dependency.resource_type]
                        if dependency
                        else "",
                        "present": "yes" if dependency else "no",
                        "source_bif": dependency.bif_name if dependency else "",
                    }
                )
                if dependency:
                    owned.add(dependency.key)
    dependencies.sort(
        key=lambda row: (row["asset_key"], row["relation"], row["dependency_resref"])
    )
    manifest = {
        **manifest_base(index, "effects", len(rows)),
        "granularity": "one VVC/VEF controller; BAM/BMP members are dependencies",
        "resources_csv": "effects/index/resources.csv",
        "dependencies_csv": "effects/index/dependencies.csv",
        "missing_dependency_count": sum(row["present"] == "no" for row in dependencies),
        "format_counts": dict(sorted(Counter(row["format"] for row in rows).items())),
    }
    return manifest, rows, dependencies, owned


def build_effect_bam_assets(
    index: KeyIndex,
    effect_dependencies: Sequence[Mapping[str, Any]],
    projectile_dependencies: Sequence[Mapping[str, Any]],
    supplemental_rows: Sequence[Mapping[str, Any]],
    extract: bool,
) -> list[dict[str, Any]]:
    """Build one work asset per visual BAM, without duplicating VVC/VEF controllers.

    ``effects/index/resources.csv`` remains the controller inventory. This table is the
    production-facing leaf inventory: a shared BAM has one row and records every known
    controller/projectile consumer. Missing stock members stay explicit rows so the
    processing authority can block them without inventing a source file.
    """

    controllers_by_bam: dict[str, set[str]] = defaultdict(set)
    nested_controllers: dict[str, set[str]] = defaultdict(set)
    for dependency in effect_dependencies:
        controller = str(dependency["asset_key"])
        resref = str(dependency["dependency_resref"]).upper()
        resolved = str(dependency.get("resolved_format", "")).upper()
        if resolved == "BAM" or (
            dependency.get("present") == "no"
            and dependency.get("relation") in {"animation", "alpha-animation"}
        ):
            controllers_by_bam[resref].add(controller)
        elif resolved in {"VVC", "VEF"}:
            nested_controllers[controller].add(f"effect:{resolved.lower()}:{resref}")

    members_by_controller: dict[str, set[str]] = defaultdict(set)

    def controller_members(controller: str, seen: set[str] | None = None) -> set[str]:
        if controller in members_by_controller:
            return members_by_controller[controller]
        active = set() if seen is None else set(seen)
        if controller in active:
            return set()
        active.add(controller)
        members = {
            resref
            for resref, owners in controllers_by_bam.items()
            if controller in owners
        }
        for child in nested_controllers.get(controller, set()):
            members.update(controller_members(child, active))
        members_by_controller[controller] = members
        return members

    projectiles_by_bam: dict[str, set[str]] = defaultdict(set)
    for dependency in projectile_dependencies:
        projectile = str(dependency["asset_key"])
        resref = str(dependency["dependency_resref"]).upper()
        resolved = str(dependency.get("resolved_format", "")).upper()
        if resolved == "BAM":
            projectiles_by_bam[resref].add(projectile)
        elif resolved in {"VVC", "VEF"}:
            controller = f"effect:{resolved.lower()}:{resref}"
            for member in controller_members(controller):
                projectiles_by_bam[member].add(projectile)

    supplemental_by_resref = {
        str(row["resref"]).upper(): row
        for row in supplemental_rows
        if row.get("domain") == "effects"
    }
    # A PRO may reference a visual BAM directly, without an intermediate VVC/VEF
    # controller and without the BAM being in a dedicated effects BIF.  It is
    # nevertheless an ``effects:bam`` work unit: omitting this source silently
    # removes projectile-only effects from the production authority.
    resrefs = sorted(
        set(controllers_by_bam)
        | set(projectiles_by_bam)
        | set(supplemental_by_resref),
        key=str.casefold,
    )
    rows: list[dict[str, Any]] = []
    for resref in resrefs:
        controller_keys = sorted(controllers_by_bam.get(resref, set()), key=str.casefold)
        projectile_keys = sorted(projectiles_by_bam.get(resref, set()), key=str.casefold)
        supplemental = supplemental_by_resref.get(resref)
        source_path = Path("effects/ressources") / resref / "source.bam"
        origins = []
        if controller_keys:
            origins.append("controller-member")
        if projectile_keys:
            origins.append("projectile-member")
        if supplemental:
            origins.append("dedicated-effect-bif")

        resource = index.get(resref, TYPE_BAM)
        if resource is None:
            rows.append(
                {
                    "asset_key": f"effects:bam:{resref}",
                    "resref": resref,
                    "origin": ";".join(origins),
                    "controller_count": len(controller_keys),
                    "controller_keys": ";".join(controller_keys),
                    "projectile_count": len(projectile_keys),
                    "projectile_keys": ";".join(projectile_keys),
                    "bam_container": "",
                    "bam_version": "",
                    "frame_count": "",
                    "cycle_count": "",
                    "source_bif": "",
                    "locator": "",
                    "source_size": "",
                    "source_sha256": "",
                    "source_state": "missing",
                    "extracted_path": source_path.as_posix(),
                }
            )
            continue

        payload = index.resolve(resource)
        metadata = bam_metadata(payload)
        if extract:
            extract_payload(ROOT / source_path, payload)
            (ROOT / source_path.parent / "runs").mkdir(parents=True, exist_ok=True)
        rows.append(
            {
                "asset_key": f"effects:bam:{resref}",
                "resref": resref,
                "origin": ";".join(origins),
                "controller_count": len(controller_keys),
                "controller_keys": ";".join(controller_keys),
                "projectile_count": len(projectile_keys),
                "projectile_keys": ";".join(projectile_keys),
                "bam_container": metadata["container"],
                "bam_version": metadata["version"],
                "frame_count": metadata["frame_count"],
                "cycle_count": metadata["cycle_count"],
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                "source_state": "available",
                "extracted_path": source_path.as_posix(),
            }
        )
    return rows


def parse_projectile_dependencies(data: bytes) -> list[tuple[str, str, tuple[int, ...]]]:
    if len(data) < 0x100 or data[:8] != b"PRO V1.0":
        raise ValueError(f"PRO invalide: {data[:8]!r}")
    fields: list[tuple[str, int, tuple[int, ...]]] = [
        ("source-animation", 0x20, (TYPE_VEF, TYPE_VVC, TYPE_BAM)),
    ]
    if len(data) >= 0x200:
        fields.extend(
            [
                ("travel-animation", 0x104, (TYPE_BAM,)),
                ("shadow-animation", 0x10C, (TYPE_BAM,)),
                ("palette", 0x11C, (TYPE_BMP,)),
                ("trailing-animation-1", 0x136, (TYPE_BAM,)),
                ("trailing-animation-2", 0x13E, (TYPE_BAM,)),
                ("trailing-animation-3", 0x146, (TYPE_BAM,)),
            ]
        )
    if len(data) >= 0x300:
        fields.extend(
            [
                ("explosion-animation", 0x21C, (TYPE_VEF, TYPE_VVC, TYPE_BAM)),
                ("spread-animation", 0x228, (TYPE_VEF, TYPE_VVC, TYPE_BAM)),
                ("ring-animation", 0x230, (TYPE_VEF, TYPE_VVC, TYPE_BAM)),
            ]
        )
    return [
        (relation, resref, allowed)
        for relation, offset, allowed in fields
        if (resref := read_resref(data, offset))
    ]


def build_projectiles(
    index: KeyIndex, extract: bool
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[tuple[str, int]],
]:
    rows: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resource in sorted(index.entries(TYPE_PRO), key=lambda item: item.resref):
        payload = index.resolve(resource)
        parsed = parse_projectile_dependencies(payload)
        owned.add(resource.key)
        extracted_relative = Path("projectiles/source") / f"{resource.resref}.pro"
        if extract:
            extract_payload(ROOT / extracted_relative, payload)
        projectile_type = struct.unpack_from("<H", payload, 8)[0]
        rows.append(
            {
                "asset_key": f"projectile:{resource.resref}",
                "resref": resource.resref,
                "projectile_type": projectile_type,
                "dependency_count": len(parsed),
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                "extracted_path": extracted_relative.as_posix(),
            }
        )
        for relation, dependency_resref, allowed_types in parsed:
            dependency = find_dependency(index, dependency_resref, allowed_types)
            dependencies.append(
                {
                    "asset_key": f"projectile:{resource.resref}",
                    "relation": relation,
                    "dependency_resref": dependency_resref,
                    "allowed_formats": ";".join(TYPE_NAMES[value] for value in allowed_types),
                    "resolved_format": TYPE_NAMES[dependency.resource_type]
                    if dependency
                    else "",
                    "present": "yes" if dependency else "no",
                    "source_bif": dependency.bif_name if dependency else "",
                }
            )
            if dependency:
                owned.add(dependency.key)
    dependencies.sort(
        key=lambda row: (row["asset_key"], row["relation"], row["dependency_resref"])
    )
    manifest = {
        **manifest_base(index, "projectiles", len(rows)),
        "granularity": "one PRO controller; animations, palettes and nested effects are dependencies",
        "resources_csv": "projectiles/index/resources.csv",
        "dependencies_csv": "projectiles/index/dependencies.csv",
        "missing_dependency_count": sum(row["present"] == "no" for row in dependencies),
        "projectile_type_counts": dict(
            sorted(Counter(str(row["projectile_type"]) for row in rows).items())
        ),
    }
    return manifest, rows, dependencies, owned


def build_fonts(
    index: KeyIndex, extract: bool
) -> tuple[dict[str, Any], list[dict[str, Any]], set[tuple[str, int]]]:
    grouped: dict[str, list[KeyResource]] = defaultdict(list)
    for resource_type in (TYPE_FNT, TYPE_TTF):
        for resource in index.entries(resource_type):
            grouped[resource.resref].append(resource)
    rows: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resref, members in sorted(grouped.items()):
        member_data = []
        for resource in sorted(members, key=lambda item: item.resource_type):
            payload = index.resolve(resource)
            owned.add(resource.key)
            extension = TYPE_EXTENSIONS[resource.resource_type]
            extracted_relative = Path("interface/fonts/source") / f"{resref}.{extension}"
            if extract:
                extract_payload(ROOT / extracted_relative, payload)
            member_data.append(
                {
                    "format": TYPE_NAMES[resource.resource_type],
                    "source_bif": resource.bif_name,
                    "locator": f"0x{resource.locator:08X}",
                    "size": len(payload),
                    "sha256": sha256_bytes(payload),
                    "extracted_path": extracted_relative.as_posix(),
                }
            )
        rows.append(
            {
                "asset_key": f"font:{resref}",
                "resref": resref,
                "formats": ";".join(item["format"] for item in member_data),
                "member_count": len(member_data),
                "members_json": json.dumps(member_data, ensure_ascii=False, sort_keys=True),
                "source_sha256": sha256_bytes(json_bytes(member_data)),
            }
        )
    manifest = {
        **manifest_base(index, "fonts", len(rows)),
        "granularity": "one font resref; FNT and TTF variants are members",
        "resources_csv": "interface/fonts/index/resources.csv",
        "format_counts": dict(
            sorted(
                Counter(
                    TYPE_NAMES[resource.resource_type]
                    for members in grouped.values()
                    for resource in members
                ).items()
            )
        ),
    }
    return manifest, rows, owned


def existing_ui_keys(index: KeyIndex) -> set[tuple[str, int]]:
    kind_types = {"BAM": TYPE_BAM, "MOS": TYPE_MOS, "PVRZ": TYPE_PVRZ}
    document = json.loads(
        (ROOT / "interface/menus-options-bg2ee/reference/extraction-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    result = set()
    for row in document.get("resources", []):
        resource_type = kind_types.get(str(row.get("kind", "")).upper())
        if resource_type is None:
            continue
        resref = Path(str(row.get("resource", ""))).stem.upper()
        if index.get(resref, resource_type):
            result.add((resref, resource_type))
    return result


def map_mos_keys(index: KeyIndex) -> set[tuple[str, int]]:
    area_like = {
        resource.resref
        for resource_type in (0x03E9, 0x03F2)
        for resource in index.entries(resource_type)
    }
    return {
        resource.key
        for resource in index.entries(TYPE_MOS)
        if resource.resref in area_like
    }


def is_ui_bam(resource: KeyResource) -> bool:
    bif_name = Path(resource.bif_name).name.upper()
    return (
        bif_name.startswith(("GUI", "HD0G"))
        or resource.resref.startswith(
            ("GUI", "GU", "START", "TITLE", "LOGO", "BIGLOGO", "CAROT")
        )
    )


def build_ui_supplement(
    index: KeyIndex,
    excluded: set[tuple[str, int]],
    extract: bool,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    set[tuple[str, int]],
]:
    existing = existing_ui_keys(index)
    map_mos = map_mos_keys(index)
    candidates = [
        resource
        for resource in index.resources
        if (
            resource.resource_type == TYPE_MOS
            and resource.key not in map_mos
            or resource.resource_type == TYPE_BAM
            and is_ui_bam(resource)
        )
        and resource.key not in existing
        and resource.key not in excluded
    ]
    rows: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resource in sorted(candidates, key=lambda item: (item.resource_type, item.resref)):
        payload = index.resolve(resource)
        owned.add(resource.key)
        if resource.resource_type == TYPE_BAM:
            metadata = bam_metadata(payload)
            row = {
                "container_version": metadata["version"],
                "frame_count": metadata["frame_count"],
                "cycle_count": metadata["cycle_count"],
                "width": "",
                "height": "",
            }
        else:
            metadata = mos_metadata(payload)
            row = {
                "container_version": metadata["version"],
                "frame_count": "",
                "cycle_count": "",
                "width": metadata["width"],
                "height": metadata["height"],
            }
        format_name = TYPE_NAMES[resource.resource_type]
        extracted_relative = (
            Path("interface/source")
            / format_name.lower()
            / f"{resource.resref}.{format_name.lower()}"
        )
        if extract:
            extract_payload(ROOT / extracted_relative, payload)
        asset_key = f"ui-resource:{format_name.lower()}:{resource.resref}"
        rows.append(
            {
                "asset_key": asset_key,
                "resref": resource.resref,
                "format": format_name,
                **row,
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                "extracted_path": extracted_relative.as_posix(),
            }
        )
        for page in metadata.get("pvrz_pages", []):
            page_resref = f"MOS{page:04d}"
            page_resource = index.get(page_resref, TYPE_PVRZ)
            dependencies.append(
                {
                    "asset_key": asset_key,
                    "relation": "texture-page",
                    "dependency_resref": page_resref,
                    "dependency_format": "PVRZ",
                    "present": "yes" if page_resource else "no",
                    "source_bif": page_resource.bif_name if page_resource else "",
                }
            )
            if page_resource:
                owned.add(page_resource.key)
    dependencies.sort(
        key=lambda row: (row["asset_key"], row["dependency_resref"])
    )
    manifest = {
        **manifest_base(index, "ui-supplement", len(rows)),
        "granularity": "one non-map MOS composition or clearly UI-owned BAM; PVRZ are dependencies",
        "resources_csv": "interface/index/resources.csv",
        "dependencies_csv": "interface/index/dependencies.csv",
        "excluded_existing_manifest_count": len(existing),
        "excluded_map_mos_count": len(map_mos),
        "missing_dependency_count": sum(row["present"] == "no" for row in dependencies),
        "format_counts": dict(sorted(Counter(row["format"] for row in rows).items())),
    }
    return manifest, rows, dependencies, owned


def existing_owned_keys(index: KeyIndex) -> set[tuple[str, int]]:
    owned = existing_ui_keys(index) | map_mos_keys(index)
    for row in read_csv(ROOT / "sprite/index/sprite_resources.csv"):
        owned.add((row["bam_resref"].upper(), TYPE_BAM))
    for row in read_csv(ROOT / "animations/index/occurrences.csv"):
        resource_type = {"BAM": TYPE_BAM, "WBM": TYPE_WBM, "PVRZ": TYPE_PVRZ}.get(
            row.get("resource_kind", "")
        )
        if resource_type:
            owned.add((row["resource_resref"].upper(), resource_type))
    return {key for key in owned if index.get(*key) is not None}


def build_supplemental_graphics(
    index: KeyIndex,
    already_owned: set[tuple[str, int]],
    extract: bool,
    extract_effects: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], set[tuple[str, int]]]:
    rows: list[dict[str, Any]] = []
    owned: set[tuple[str, int]] = set()
    for resource in sorted(index.entries(TYPE_BAM), key=lambda item: item.resref):
        if resource.key in already_owned:
            continue
        rule = SUPPLEMENTAL_BIF_RULES.get(Path(resource.bif_name).name.upper())
        if rule is None:
            continue
        domain, asset_type = rule
        payload = index.resolve(resource)
        metadata = bam_metadata(payload)
        extracted_relative = (
            Path("effects/ressources") / resource.resref / "source.bam"
            if domain == "effects"
            else Path("graphics/source") / domain / f"{resource.resref}.bam"
        )
        if extract or (extract_effects and domain == "effects"):
            extract_payload(ROOT / extracted_relative, payload)
            if domain == "effects":
                (ROOT / extracted_relative.parent / "runs").mkdir(parents=True, exist_ok=True)
        rows.append(
            {
                "asset_key": f"supplemental:{domain}:{asset_type}:{resource.resref}",
                "domain": domain,
                "asset_type": asset_type,
                "resref": resource.resref,
                "bam_container": metadata["container"],
                "bam_version": metadata["version"],
                "frame_count": metadata["frame_count"],
                "cycle_count": metadata["cycle_count"],
                "source_bif": resource.bif_name,
                "locator": f"0x{resource.locator:08X}",
                "source_size": len(payload),
                "source_sha256": sha256_bytes(payload),
                "extracted_path": extracted_relative.as_posix(),
            }
        )
        owned.add(resource.key)
    domain_counts = Counter(row["domain"] for row in rows)
    type_counts = Counter(row["asset_type"] for row in rows)
    manifest = {
        **manifest_base(index, "supplemental-graphics", len(rows)),
        "granularity": (
            "one engine BAM animation set; frames and cycles remain members; "
            "classification requires an unambiguous stock BIF family"
        ),
        "resources_csv": "graphics/index/supplemental-assets.csv",
        "domain_counts": dict(sorted(domain_counts.items())),
        "asset_type_counts": dict(sorted(type_counts.items())),
        "classification_rules": {
            bif_name: {"domain": value[0], "asset_type": value[1]}
            for bif_name, value in sorted(SUPPLEMENTAL_BIF_RULES.items())
        },
    }
    return manifest, rows, owned


def build_graphics_coverage(
    index: KeyIndex,
    owned: set[tuple[str, int]],
    ownership_sets: Mapping[str, set[tuple[str, int]]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_graphics = [
        resource for resource in index.resources if resource.resource_type in GRAPHICAL_TYPES
    ]
    dependency_only_types = {TYPE_BMP, TYPE_PLT, TYPE_PVRZ}
    unclassified = [
        resource
        for resource in raw_graphics
        if resource.key not in owned and resource.resource_type not in dependency_only_types
    ]
    rows = [
        {
            "resref": resource.resref,
            "format": TYPE_NAMES[resource.resource_type],
            "source_bif": resource.bif_name,
            "locator": f"0x{resource.locator:08X}",
            "reason": "logical-owner-not-demonstrated",
        }
        for resource in sorted(
            unclassified, key=lambda item: (item.resource_type, item.bif_name, item.resref)
        )
    ]
    by_type = Counter(TYPE_NAMES[item.resource_type] for item in raw_graphics)
    owned_by_type = Counter(TYPE_NAMES[item[1]] for item in owned if item[1] in TYPE_NAMES)
    unclassified_by_type = Counter(row["format"] for row in rows)
    dependency_only_count = sum(
        resource.resource_type in dependency_only_types for resource in raw_graphics
    )
    top_unclassified_bifs = Counter(resource.bif_name for resource in unclassified).most_common(20)
    overlapping_resources = []
    for key in sorted(set().union(*ownership_sets.values())):
        owners = sorted(name for name, keys in ownership_sets.items() if key in keys)
        if len(owners) > 1:
            overlapping_resources.append(
                {
                    "resref": key[0],
                    "format": TYPE_NAMES.get(key[1], f"0x{key[1]:04X}"),
                    "owners": owners,
                }
            )
    coverage = {
        "schema": "bg2-upscale-graphics-inventory-coverage-v1",
        "generated_by": GENERATOR,
        "chitin_key_sha256": index.key_sha256,
        "key_resource_count": len(index.resources),
        "raw_graphical_resource_count": len(raw_graphics),
        "owned_raw_resource_count": len(
            {resource.key for resource in raw_graphics} & owned
        ),
        "dependency_only_resource_count": dependency_only_count,
        "unclassified_resource_count": len(rows),
        "raw_format_counts": dict(sorted(by_type.items())),
        "owned_format_counts": dict(sorted(owned_by_type.items())),
        "unclassified_format_counts": dict(sorted(unclassified_by_type.items())),
        "top_unclassified_source_bifs": [
            {"source_bif": bif, "resource_count": count}
            for bif, count in top_unclassified_bifs
        ],
        "raw_cross_domain_overlap_count": len(overlapping_resources),
        "raw_cross_domain_overlaps": overlapping_resources,
        "raw_cross_domain_overlap_policy": (
            "reported raw dependency reuse; logical registry assets remain unique"
        ),
        "limitations": [
            "BMP, PLT et PVRZ sont des membres dépendants et ne sont pas comptés comme assets autonomes",
            "les BAM restants ne sont pas projetés tant que leur propriétaire logique n'est pas démontré",
        ],
        "unclassified_csv": "graphics/index/unclassified-resources.csv",
    }
    return coverage, rows


CSV_FIELDS = {
    "video_resources": (
        "asset_key", "resref", "role", "locale", "source_kind", "source_path",
        "source_bif", "locator", "source_size", "source_sha256", "width", "height",
        "frame_rate", "duration_ms", "video_codec", "audio_codec", "extracted_path",
    ),
    "hud_resources": (
        "asset_key", "resref", "role", "format", "container_version", "frame_count",
        "cycle_count", "width", "height", "source_bif", "locator", "source_size",
        "source_sha256", "extracted_path",
    ),
    "hud_dependencies": (
        "asset_key", "relation", "dependency_resref", "dependency_format", "present",
        "source_bif", "locator",
    ),
    "icon_resources": (
        "asset_key", "resref", "roles", "usage_count", "owner_count", "bam_container",
        "bam_version", "frame_count", "cycle_count", "block_count",
        "pvrz_dependency_count", "source_bif", "locator", "source_size",
        "source_sha256", "extracted_path",
    ),
    "icon_families": (
        "asset_key", "resref", "family", "usage_count", "owner_count",
    ),
    "icon_usages": ("owner_format", "owner_resref", "role", "icon_resref"),
    "icon_frames": (
        "asset_key", "resref", "frame_index", "width", "height", "center_x",
        "center_y", "block_count",
    ),
    "icon_dependencies": (
        "asset_key", "relation", "dependency_resref", "dependency_format", "present",
        "source_bif", "locator", "source_size", "source_sha256", "extracted_path",
    ),
    "icon_missing_resources": (
        "icon_resref", "roles", "usage_count", "owner_count",
    ),
    "cursor_resources": (
        "asset_key", "resref", "granularity", "bam_container", "bam_version",
        "frame_count", "cycle_count", "source_bif", "locator", "source_size",
        "source_sha256", "extracted_path",
    ),
    "effect_resources": (
        "asset_key", "resref", "format", "dependency_count", "source_bif", "locator",
        "source_size", "source_sha256", "extracted_path",
    ),
    "effect_dependencies": (
        "asset_key", "relation", "dependency_resref", "allowed_formats",
        "resolved_format", "present", "source_bif",
    ),
    "effect_bam_assets": (
        "asset_key", "resref", "origin", "controller_count", "controller_keys",
        "projectile_count", "projectile_keys", "bam_container", "bam_version",
        "frame_count", "cycle_count", "source_bif", "locator", "source_size",
        "source_sha256", "source_state", "extracted_path",
    ),
    "projectile_resources": (
        "asset_key", "resref", "projectile_type", "dependency_count", "source_bif",
        "locator", "source_size", "source_sha256", "extracted_path",
    ),
    "projectile_dependencies": (
        "asset_key", "relation", "dependency_resref", "allowed_formats",
        "resolved_format", "present", "source_bif",
    ),
    "font_resources": (
        "asset_key", "resref", "formats", "member_count", "members_json", "source_sha256",
    ),
    "ui_resources": (
        "asset_key", "resref", "format", "container_version", "frame_count", "cycle_count",
        "width", "height", "source_bif", "locator", "source_size", "source_sha256",
        "extracted_path",
    ),
    "ui_dependencies": (
        "asset_key", "relation", "dependency_resref", "dependency_format", "present",
        "source_bif",
    ),
    "supplemental_resources": (
        "asset_key", "domain", "asset_type", "resref", "bam_container", "bam_version",
        "frame_count", "cycle_count", "source_bif", "locator", "source_size",
        "source_sha256", "extracted_path",
    ),
    "graphics_unclassified": ("resref", "format", "source_bif", "locator", "reason"),
}


def build_outputs(
    root: Path,
    game_dir: Path,
    ffprobe: str,
    extract: bool = False,
    extract_icons: bool = False,
    extract_effects: bool = False,
) -> dict[Path, bytes]:
    global ROOT
    previous_root = ROOT
    ROOT = root.resolve()
    try:
        index = KeyIndex(game_dir)
        if index.duplicates:
            raise RuntimeError(
                f"chitin.key contient {len(index.duplicates)} clés de ressource dupliquées"
            )

        existing_owned = existing_owned_keys(index)
        video_manifest, video_rows, video_owned = build_videos(index, ffprobe, extract)
        hud_manifest, hud_rows, hud_dependencies, hud_owned = build_hud(index, extract)
        (
            icon_manifest,
            icon_rows,
            icon_families,
            icon_usages,
            icon_frames,
            icon_dependencies,
            icon_missing_resources,
            icon_owned,
        ) = build_icons(index, extract or extract_icons)
        cursor_manifest, cursor_rows, cursor_owned = build_cursors(index, extract)
        effect_manifest, effect_rows, effect_dependencies, effect_owned = build_effects(
            index, extract or extract_effects
        )
        projectile_manifest, projectile_rows, projectile_dependencies, projectile_owned = (
            build_projectiles(index, extract)
        )
        font_manifest, font_rows, font_owned = build_fonts(index, extract)
        new_pre_ui = (
            video_owned
            | hud_owned
            | icon_owned
            | cursor_owned
            | effect_owned
            | projectile_owned
            | font_owned
        )
        ui_manifest, ui_rows, ui_dependencies, ui_owned = build_ui_supplement(
            index, existing_owned | new_pre_ui, extract
        )
        supplemental_manifest, supplemental_rows, supplemental_owned = (
            build_supplemental_graphics(
                index,
                existing_owned | new_pre_ui | ui_owned,
                extract,
                extract_effects,
            )
        )
        effect_bam_rows = build_effect_bam_assets(
            index,
            effect_dependencies,
            projectile_dependencies,
            supplemental_rows,
            extract or extract_effects,
        )
        effect_manifest.update(
            {
                "bam_assets_csv": "effects/index/bam-assets.csv",
                "bam_asset_count": len(effect_bam_rows),
                "bam_source_available_count": sum(
                    row["source_state"] == "available" for row in effect_bam_rows
                ),
                "bam_source_missing_count": sum(
                    row["source_state"] == "missing" for row in effect_bam_rows
                ),
                "production_granularity": "one visual BAM; VVC/VEF controllers remain consumers",
            }
        )
        ownership_sets = {
            "existing-domains": existing_owned,
            "videos": video_owned,
            "hud": hud_owned,
            "icons": icon_owned,
            "cursors": cursor_owned,
            "effects": effect_owned,
            "projectiles": projectile_owned,
            "fonts": font_owned,
            "ui-supplement": ui_owned,
            "supplemental-graphics": supplemental_owned,
        }
        graphics_coverage, graphics_unclassified = build_graphics_coverage(
            index,
            set().union(*ownership_sets.values()),
            ownership_sets,
        )

        documents = {
            "video_manifest": video_manifest,
            "hud_manifest": hud_manifest,
            "icon_manifest": icon_manifest,
            "cursor_manifest": cursor_manifest,
            "effect_manifest": effect_manifest,
            "projectile_manifest": projectile_manifest,
            "font_manifest": font_manifest,
            "ui_manifest": ui_manifest,
            "supplemental_manifest": supplemental_manifest,
            "graphics_coverage": graphics_coverage,
        }
        tables = {
            "video_resources": video_rows,
            "hud_resources": hud_rows,
            "hud_dependencies": hud_dependencies,
            "icon_resources": icon_rows,
            "icon_families": icon_families,
            "icon_usages": icon_usages,
            "icon_frames": icon_frames,
            "icon_dependencies": icon_dependencies,
            "icon_missing_resources": icon_missing_resources,
            "cursor_resources": cursor_rows,
            "effect_resources": effect_rows,
            "effect_dependencies": effect_dependencies,
            "effect_bam_assets": effect_bam_rows,
            "projectile_resources": projectile_rows,
            "projectile_dependencies": projectile_dependencies,
            "font_resources": font_rows,
            "ui_resources": ui_rows,
            "ui_dependencies": ui_dependencies,
            "supplemental_resources": supplemental_rows,
            "graphics_unclassified": graphics_unclassified,
        }
        outputs = {
            root / OUTPUT_PATHS[name]: json_bytes(document)
            for name, document in documents.items()
        }
        outputs.update(
            {
                root / OUTPUT_PATHS[name]: csv_bytes(CSV_FIELDS[name], rows)
                for name, rows in tables.items()
            }
        )
        return outputs
    finally:
        ROOT = previous_root


def write_outputs(outputs: Mapping[Path, bytes], check: bool) -> list[Path]:
    divergent = []
    for path, payload in sorted(outputs.items(), key=lambda item: item[0].as_posix()):
        if path.is_file() and path.read_bytes() == payload:
            continue
        divergent.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    return divergent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--extract", action="store_true")
    parser.add_argument(
        "--extract-icons",
        action="store_true",
        help="extrait seulement les BAM d'icônes et leurs PVRZ partagées",
    )
    parser.add_argument(
        "--extract-effects",
        action="store_true",
        help="extrait seulement les contrôleurs VVC/VEF et les BAM d'effets",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="autorise l'extraction ciblée demandée",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "icons"),
        default="all",
        help="limite les catalogues écrits; la construction en mémoire reste globale",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()
    if args.check and (args.extract or args.extract_icons or args.extract_effects):
        parser.error("--check est incompatible avec une extraction")
    if args.extract_effects and not args.run:
        parser.error("--extract-effects exige --run")
    if args.extract_icons and not args.run:
        parser.error("--extract-icons exige --run")

    first = build_outputs(
        ROOT,
        args.game_dir,
        args.ffprobe,
        extract=args.extract,
        extract_icons=args.extract_icons,
        extract_effects=args.extract_effects,
    )
    if args.scope == "icons":
        icon_root = (ROOT / "icons/index").resolve()
        first = {
            path: payload
            for path, payload in first.items()
            if path.resolve().is_relative_to(icon_root)
        }
    if args.verify_determinism:
        second = build_outputs(ROOT, args.game_dir, args.ffprobe, extract=False)
        if args.scope == "icons":
            second = {
                path: payload
                for path, payload in second.items()
                if path.resolve().is_relative_to(icon_root)
            }
        if first != second:
            raise RuntimeError("inventaire non déterministe entre deux générations")
    divergent = write_outputs(first, check=args.check)
    if args.check and divergent:
        for path in divergent:
            print(f"DIVERGENT {path.relative_to(ROOT)}")
        return 1
    action = "verified" if args.check else "generated"
    print(f"{action}: {len(first)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
