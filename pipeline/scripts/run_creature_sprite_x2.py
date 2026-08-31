"""Reproducible xBR xN pipeline for BG2EE creature and Character sprites.

The pipeline keeps BAM V1 metadata at x1, stores lossless x2 or x4 palette
indices in an external registry, builds the shared runtime, and manages
reversible QA installation. Jobs without an explicit ``upscale`` block retain
the historical x2/V2 contract. The runner never launches the game and never
edits release manifests.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
PATH_MIGRATIONS_FILE = PROJECT_ROOT / "sprite" / "index" / "path-migrations.json"
XBR_ADAPTER = SCRIPT_DIR / "xbr2x_batch.js"
INSTALL_SCRIPT = SCRIPT_DIR / "Install-CreatureSprite-X2-Test.ps1"
RESTORE_SCRIPT = SCRIPT_DIR / "Restore-CreatureSprite-X2-Test.ps1"
XN_INSTALL_SCRIPT = SCRIPT_DIR / "Install-CreatureSprite-XN-Test.ps1"
XN_RESTORE_SCRIPT = SCRIPT_DIR / "Restore-CreatureSprite-XN-Test.ps1"
XN_CATALOG_INSTALL_SCRIPT = (
    SCRIPT_DIR / "Install-CreatureSprite-XN-Catalog-Test.ps1"
)
XN_CATALOG_RESTORE_SCRIPT = (
    SCRIPT_DIR / "Restore-CreatureSprite-XN-Catalog-Test.ps1"
)
JOB_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-job-v1"
ARMOR_SET_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-armor-set-v1"
CATALOG_JOB_SCHEMA = "bg2-upscale-creature-sprite-xn-catalog-job-v1"
SOURCE_SCHEMA = "bg2-upscale-creature-sprite-source-v1"
BUILD_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-pack-v1"
ARMOR_SET_BUILD_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-armor-set-pack-v1"
CATALOG_BUILD_SCHEMA = "bg2-upscale-creature-sprite-xn-catalog-pack-v1"
CATALOG_POINTER_SCHEMA = (
    "bg2-upscale-creature-sprite-xn-catalog-current-generation-v1"
)
RUNTIME_SCHEMA = "bg2-upscale-creature-sprite-runtime-v1"
XN_INSTALL_STATE_SCHEMA = "bg2-upscale-creature-sprite-xn-ingame-test-v2"
XN_CATALOG_INSTALL_STATE_SCHEMA = (
    "bg2-upscale-creature-sprite-xn-catalog-ingame-test-v1"
)
REGISTRY_MAGIC = b"IEECSX2\0"
REGISTRY_VERSION = 2
LEGACY_REGISTRY_VERSION = 1
XN_REGISTRY_MAGIC = b"IEECSXN\0"
XN_REGISTRY_VERSION = 3
# V4 is reserved by the runtime for the experimental antialias recipe format.
# V5 keeps exact NEAREST palette indices but stores each frame independently
# with Windows XPRESS_HUFF when that is smaller than the raw index plane.
XN_COMPRESSED_REGISTRY_VERSION = 5
CATALOG_SHARD_REGISTRY_VERSION = XN_COMPRESSED_REGISTRY_VERSION
REGISTRY_FRAME_CODEC_RAW = 0
REGISTRY_FRAME_CODEC_XPRESS_HUFF = 1
XN_REGISTRY_SET_MAGIC = b"IEECSNS\0"
XN_REGISTRY_SET_VERSION = 1
XN_REGISTRY_CATALOG_MAGIC = b"IEECSNC\0"
LEGACY_XN_REGISTRY_CATALOG_VERSION = 1
XN_REGISTRY_CATALOG_VERSION = 2
LEGACY_SCALE = 2
# Readability zoom for source-only QA sheets; it is not the upscale contract.
SOURCE_PREVIEW_SCALE = 2
REGISTRY_FILENAME = "CreatureSprites-X2.registry"
XN_REGISTRY_FILENAME = "CreatureSprites-XN.registry"
XN_REGISTRY_SET_FILENAME = "CreatureSprites-XN.set"
XN_REGISTRY_SHARD_FILENAME = "CreatureSprites-XN-{index:04d}.registry"
XN_REGISTRY_CATALOG_FILENAME = "CreatureSprites-XN.catalog"
XN_REGISTRY_CATALOG_SHARD_FILENAME = "CreatureSprites-XN-{sha256}.registry"
REGISTRY_HEADER_BYTES = 24
REGISTRY_RESOURCE_HEADER_BYTES = 48
REGISTRY_FRAME_HEADER_BYTES = 528
REGISTRY_SET_HEADER_BYTES = 56
REGISTRY_SET_ENTRY_BYTES = 64
REGISTRY_CATALOG_V1_HEADER_BYTES = 64
REGISTRY_CATALOG_HEADER_BYTES = 104
REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES = 16
REGISTRY_CATALOG_MEMBERSHIP_BYTES = 4
REGISTRY_CATALOG_COMPONENT_ENTRY_BYTES = 72
REGISTRY_CATALOG_SHARD_ENTRY_BYTES = 64
REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES = 24
BAM_TYPE = 0x03E8
ITM_TYPE = 0x03ED
IDS_TYPE = 0x03F0
INI_TYPE = 0x0802
MAX_RESOURCES = 128
MAX_FRAMES_PER_RESOURCE = 4096
MAX_CYCLES_PER_RESOURCE = 256
MAX_CYCLE_SLOTS = 65536
MAX_REGISTRY_BYTES = 128 * 1024 * 1024
MAX_REGISTRY_BYTES_BY_SCALE = {
    2: MAX_REGISTRY_BYTES,
    4: 512 * 1024 * 1024,
}
MAX_LAZY_FRAME_INDEX_BYTES = 128 * 1024 * 1024
MAX_REGISTRY_SET_SHARDS = 64
MAX_REGISTRY_SET_RESOURCES = MAX_RESOURCES * MAX_REGISTRY_SET_SHARDS
MAX_REGISTRY_SET_FRAMES = 1_048_576
MAX_REGISTRY_SET_BYTES = 8 * 1024 * 1024 * 1024
MAX_REGISTRY_CATALOG_ANIMATIONS = 512
MAX_REGISTRY_CATALOG_COMPONENTS = 16_384
MAX_REGISTRY_CATALOG_MEMBERSHIPS = 262_144
MAX_REGISTRY_CATALOG_SHARDS = 16_384
MAX_REGISTRY_CATALOG_RESOURCES = 32_768
MAX_REGISTRY_CATALOG_FRAMES = 4_194_304
MAX_REGISTRY_CATALOG_BYTES = 128 * 1024 * 1024 * 1024
MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES = 1_048_576
# Visual Studio 2019 FileTracker adds long TryCompile/tlog suffixes and still
# fails above MAX_PATH even when Windows long paths are enabled.
MAX_WINDOWS_CMAKE_BUILD_ROOT_CHARS = 120
CATALOG_COMPONENT_DIGEST_DOMAIN = b"IEECSNC-COMPONENT-V1\0"
CATALOG_DIRECTORY_DIGEST_DOMAIN = b"IEECSNC-DIRECTORY-V2\0"
CATALOG_LOGICAL_CONTENT_DIGEST_DOMAIN = b"IEECSNC-LOGICAL-CONTENT-V1\0"
CATALOG_SHARD_ANIMATION_SENTINEL = 0xFFFF
CATALOG_OWNER_CHARACTER = 1
CATALOG_OWNER_MONSTER_ICEWIND = 2
XBR_OUTPUT_BATCH_BUDGET_BYTES = 64 * 1024 * 1024
# The xN adapter retains the baseline adapter's legacy protocol and xBR2x call
# path byte-for-byte. Accepting this audited hash keeps existing x2 builds
# resumable without spending another full xBR pass.
LEGACY_COMPATIBLE_XBR_ADAPTER_SHA256S = frozenset(
    {"11FE3B2F1ACAAA0F141E282D86FFE28D7A8DB0B86AFFCEDB8A16741F141FC1D4"}
)
CHARACTER_BODY_SUFFIXES = (
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    "A6",
    "A7",
    "A8",
    "A9",
    "CA",
    "G1",
    "G11",
    "G12",
    "G13",
    "G14",
    "G15",
    "G16",
    "G17",
    "G18",
    "G19",
    "SA",
    "SS",
    "SX",
)
CHARACTER_EQUIPMENT_SUFFIXES = CHARACTER_BODY_SUFFIXES
CHARACTER_OFFHAND_WEAPON_SUFFIXES = ("OA7", "OA8", "OA9", "OG1")
CHARACTER_EQUIPMENT_SUFFIXES_BY_LAYER = {
    "helmet": CHARACTER_EQUIPMENT_SUFFIXES,
    "shield": CHARACTER_EQUIPMENT_SUFFIXES,
    "weapon": CHARACTER_EQUIPMENT_SUFFIXES + CHARACTER_OFFHAND_WEAPON_SUFFIXES,
}
CHARACTER_LAYER_KINDS = frozenset({"body", "helmet", "shield", "weapon"})
CHARACTER_EQUIPMENT_ITEM_TYPES = {
    "helmet": frozenset({7}),
    "shield": frozenset({12}),
    # Weapons span multiple ITM category values. Their two-byte animation code
    # and the Character height code remain the authoritative resource mapping.
    "weapon": frozenset(),
}
SUPPORTED_RUNTIME_PROFILES = frozenset(
    {
        "monster-icewind-bg2ee-2.7.3.0",
        "character-bg2ee-2.7.3.0",
    }
)


def maximum_registry_bytes(scale: int) -> int:
    if isinstance(scale, bool) or not isinstance(scale, int) or scale not in MAX_REGISTRY_BYTES_BY_SCALE:
        raise RuntimeError("registry scale must be 2 or 4")
    return MAX_REGISTRY_BYTES_BY_SCALE[scale]

sys.path.insert(0, str(SCRIPT_DIR))
from bam_export import decode_bam  # noqa: E402


@dataclass
class SourceFrame:
    resref: str
    index: int
    width: int
    height: int
    center_x: int
    center_y: int
    transparent: int
    indices: np.ndarray
    palette: np.ndarray
    rgba: bytes


@dataclass(frozen=True)
class UpscaleContract:
    scale: int
    algorithm: str
    passes: int
    antialias: bool
    xbr_blend: bool
    explicit: bool

    @property
    def registry_magic(self) -> bytes:
        return XN_REGISTRY_MAGIC if self.explicit else REGISTRY_MAGIC

    @property
    def registry_version(self) -> int:
        return XN_REGISTRY_VERSION if self.explicit else REGISTRY_VERSION

    @property
    def registry_filename(self) -> str:
        return XN_REGISTRY_FILENAME if self.explicit else REGISTRY_FILENAME

    @property
    def adapter_mode(self) -> str:
        return f"xbr{self.scale}x"

    @property
    def method(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm,
            "scale": self.scale,
            "passes": self.passes,
            "antialias": self.antialias,
            "xbr_blend": self.xbr_blend,
        }

    @property
    def identity(self) -> tuple[bytes, int, int]:
        return (self.registry_magic, self.registry_version, self.scale)


LEGACY_UPSCALE = UpscaleContract(
    scale=LEGACY_SCALE,
    algorithm="XBR/xbr2X",
    passes=1,
    antialias=False,
    xbr_blend=False,
    explicit=False,
)


def direct_upscale_contract(scale: int) -> UpscaleContract:
    if isinstance(scale, bool) or not isinstance(scale, int) or scale not in {2, 4}:
        raise RuntimeError("upscale scale must be 2 or 4")
    return UpscaleContract(
        scale=scale,
        algorithm=f"XBR/xbr{scale}X",
        passes=1,
        antialias=False,
        xbr_blend=False,
        explicit=True,
    )


def upscale_contract(work_item: dict[str, Any]) -> UpscaleContract:
    raw = work_item.get("upscale")
    if raw is None:
        return LEGACY_UPSCALE
    if not isinstance(raw, dict):
        raise RuntimeError("upscale must be an object")
    required = {"scale", "algorithm", "passes", "antialias", "xbr_blend"}
    missing = sorted(required - raw.keys())
    unexpected = sorted(raw.keys() - required)
    if missing or unexpected:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unexpected:
            details.append("unexpected " + ", ".join(unexpected))
        raise RuntimeError("invalid upscale contract: " + "; ".join(details))
    scale = raw["scale"]
    passes = raw["passes"]
    antialias = raw["antialias"]
    xbr_blend = raw["xbr_blend"]
    if isinstance(scale, bool) or not isinstance(scale, int) or scale not in {2, 4}:
        raise RuntimeError("upscale.scale must be 2 or 4")
    if isinstance(passes, bool) or not isinstance(passes, int) or passes != 1:
        raise RuntimeError("upscale.passes must be 1 for the direct xBR implementation")
    if not isinstance(antialias, bool) or antialias:
        raise RuntimeError("upscale.antialias must be false for palette-index output")
    if not isinstance(xbr_blend, bool) or xbr_blend:
        raise RuntimeError("upscale.xbr_blend must be false for palette-index output")
    expected_algorithm = f"XBR/xbr{scale}X"
    if raw["algorithm"] != expected_algorithm:
        raise RuntimeError(
            f"upscale.algorithm must be exactly {expected_algorithm} for scale {scale}"
        )
    return direct_upscale_contract(scale)


def creation_upscale_contract(
    template: dict[str, Any], requested_scale: int | None
) -> UpscaleContract:
    if requested_scale is None:
        return upscale_contract(template)
    return direct_upscale_contract(requested_scale)


def upscale_method_description(contract: UpscaleContract) -> str:
    return (
        f"{contract.algorithm} x{contract.scale} one-pass antialias-off; "
        "palette indices; x1 geometry; NEAREST"
    )


def effective_upscale_contract(work_item: dict[str, Any]) -> UpscaleContract:
    return upscale_contract(work_item)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def crc32_file(path: Path) -> int:
    checksum = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum = zlib.crc32(chunk, checksum)
    return checksum & 0xFFFFFFFF


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object expected: {path}")
    return value


def canonical_json_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


_PATH_MIGRATIONS: tuple[tuple[str, str], ...] | None = None


def path_migrations() -> tuple[tuple[str, str], ...]:
    """Return audited legacy workspace redirects, longest prefix first.

    Generated run manifests are immutable: they retain the paths used when a
    build or an installation was made.  A directory-only migration therefore
    records redirects in ``sprite/index/path-migrations.json`` instead of
    editing those manifests and invalidating their hashes.
    """

    global _PATH_MIGRATIONS
    if _PATH_MIGRATIONS is not None:
        return _PATH_MIGRATIONS
    if not PATH_MIGRATIONS_FILE.is_file():
        _PATH_MIGRATIONS = ()
        return _PATH_MIGRATIONS
    payload = json.loads(PATH_MIGRATIONS_FILE.read_text(encoding="utf-8"))
    if payload.get("schema") != "bg2-upscale-sprite-path-migrations-v1":
        raise RuntimeError("sprite path migration index has an unsupported schema")
    entries = payload.get("migrations")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("sprite path migration index requires non-empty migrations")
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("sprite path migration entry must be an object")
        old = str(entry.get("from", "")).replace("\\", "/").strip("/")
        new = str(entry.get("to", "")).replace("\\", "/").strip("/")
        if (
            not old.startswith("sprite/")
            or not new.startswith("sprite/")
            or old == new
            or old in seen
        ):
            raise RuntimeError("sprite path migration entry is invalid or duplicated")
        seen.add(old)
        result.append((old, new))
    _PATH_MIGRATIONS = tuple(sorted(result, key=lambda item: len(item[0]), reverse=True))
    return _PATH_MIGRATIONS


def resolve_path(value: str | Path) -> Path:
    expanded = os.path.expandvars(str(value))
    if expanded.startswith("config://"):
        return resolve_path_reference(expanded)
    path = Path(expanded)
    if path.is_absolute():
        candidate = path.resolve()
        if candidate.exists():
            return candidate
        try:
            normalized = candidate.relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            return candidate
    else:
        normalized = expanded.replace("\\", "/").strip("/")
        candidate = PROJECT_ROOT / normalized
    if candidate.exists():
        return candidate.resolve()
    for old, new in path_migrations():
        if normalized == old or normalized.startswith(f"{old}/"):
            suffix = normalized[len(old) :].lstrip("/")
            redirected = PROJECT_ROOT / new
            if suffix:
                redirected /= suffix
            return redirected.resolve()
    return candidate.resolve()


def relative_project_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def playable_character_workspace_from_job_path(path: Path) -> Path | None:
    """Return the current-layout unit workspace for a Character job path.

    Legacy descriptors remain readable below ``sprite/jobs``. New Character
    descriptors may instead live below one physical sprite unit, where their
    source and run directories must remain siblings of ``jobs``.
    """

    resolved = path.resolve()
    try:
        relative = resolved.relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    parts = relative.parts
    if (
        len(parts) >= 6
        and parts[0:3] == ("sprite", "families", "playable-characters")
        and parts[-2] == "jobs"
        and resolved.suffix.lower() == ".json"
    ):
        return resolved.parent.parent
    return None


def character_workspace_paths(
    workspace: Path, job_id: str, scale: int, animation_id: str
) -> dict[str, str]:
    """Build current-layout output paths for one Character unit descriptor."""

    workspace_path = relative_project_path(workspace)
    cache_key = hashlib.sha256(
        relative_project_path(workspace / "jobs" / f"{job_id}.json").encode("utf-8")
    ).hexdigest()[:16]
    return {
        "source_dir": f"{workspace_path}/source",
        "run_dir": f"{workspace_path}/runs/xbr{scale}x-x{scale}",
        "engine_build": (
            "sprite/.work/cmake/character/"
            f"{animation_id[2:].lower()}-{cache_key}"
        ),
    }


def assert_workspace_child(path: Path, label: str) -> None:
    resolved = path.resolve()
    if resolved == PROJECT_ROOT or PROJECT_ROOT not in resolved.parents:
        raise RuntimeError(f"{label} must stay inside {PROJECT_ROOT}: {resolved}")


def first_reparse_component(root: Path, relative: Path) -> Path | None:
    """Return the first symlink/junction below root without following it."""

    current = root
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    try:
        metadata = current.lstat()
    except FileNotFoundError:
        return None
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    if stat.S_ISLNK(metadata.st_mode) or attributes & reparse_flag:
        return current
    for part in relative.parts:
        current /= part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            break
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & reparse_flag:
            return current
    return None


def load_job(job_file: Path) -> dict[str, Any]:
    job_file = resolve_path(job_file)
    job = read_json(job_file)
    if job.get("schema") != JOB_SCHEMA:
        raise RuntimeError(f"unsupported job schema: {job.get('schema')!r}")
    job_id = str(job.get("job_id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("job_id must match [a-z0-9][a-z0-9-]{1,63}")
    animation = job.get("animation")
    paths = job.get("paths")
    compatibility = job.get("compatibility")
    if not isinstance(animation, dict) or not isinstance(paths, dict) or not isinstance(
        compatibility, dict
    ):
        raise RuntimeError("job requires animation, paths, and compatibility objects")
    prefix = str(animation.get("bam_prefix", "")).upper()
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", prefix):
        raise RuntimeError("animation.bam_prefix must be 1..8 BAM-safe characters")
    animation_id = str(animation.get("id", ""))
    if not re.fullmatch(r"0x[0-9A-Fa-f]{4}", animation_id):
        raise RuntimeError("animation.id must use 0xFFFF notation")
    animation_family = int(animation_id, 16) & 0xF000
    runtime_profile = animation.get("runtime_profile")
    if animation_family in {0x5000, 0x6000} and runtime_profile != "character-bg2ee-2.7.3.0":
        raise RuntimeError("0x5000/0x6000 animations require the Character runtime profile")
    if runtime_profile == "character-bg2ee-2.7.3.0" and animation_family not in {0x5000, 0x6000}:
        raise RuntimeError("Character runtime profile requires a 0x5000/0x6000 animation")
    if runtime_profile == "monster-icewind-bg2ee-2.7.3.0" and animation_family != 0xE000:
        raise RuntimeError("MonsterIcewind runtime profile requires a 0xE000 animation")
    if runtime_profile == "character-bg2ee-2.7.3.0":
        ids_symbol = str(animation.get("ids_symbol", "")).upper()
        if not re.fullmatch(r"[A-Z0-9_]{2,64}", ids_symbol):
            raise RuntimeError("Character jobs require animation.ids_symbol from ANIMATE.IDS")
        layer = animation.get("layer", {"kind": "body"})
        if not isinstance(layer, dict):
            raise RuntimeError("Character animation.layer must be an object")
        layer_kind = str(layer.get("kind", "body")).lower()
        if layer_kind not in CHARACTER_LAYER_KINDS:
            raise RuntimeError(
                "Character animation.layer.kind must be body, helmet, shield, or weapon"
            )
        normalized_layer: dict[str, Any] = {"kind": layer_kind}
        if layer_kind == "body":
            armor_code = animation.get("armor_code")
            if (
                isinstance(armor_code, bool)
                or not isinstance(armor_code, int)
                or not 1 <= armor_code <= 9
            ):
                raise RuntimeError("Character body jobs require animation.armor_code in 1..9")
            if "item_resref" in layer:
                raise RuntimeError("Character body layers cannot declare item_resref")
        else:
            if "armor_code" in animation:
                raise RuntimeError("Character equipment jobs cannot declare animation.armor_code")
            item_resref = str(layer.get("item_resref", "")).upper()
            if not re.fullmatch(r"[A-Z0-9_]{1,8}", item_resref):
                raise RuntimeError(
                    "Character equipment layers require a BAM-safe item_resref"
                )
            normalized_layer["item_resref"] = item_resref
        animation["layer"] = normalized_layer
        animation["ids_symbol"] = ids_symbol
    elif "ids_symbol" in animation or "armor_code" in animation or "layer" in animation:
        raise RuntimeError(
            "animation.ids_symbol, armor_code, and layer are reserved for Character jobs"
        )
    required_paths = ("game_root", "source_dir", "run_dir", "scalepix", "engine_source", "engine_build")
    missing = [key for key in required_paths if not paths.get(key)]
    if missing:
        raise RuntimeError(f"job paths missing: {', '.join(missing)}")
    for key in ("source_dir", "run_dir", "engine_source", "engine_build"):
        assert_workspace_child(resolve_path(paths[key]), f"paths.{key}")
    if resolve_path(paths["source_dir"]) == resolve_path(paths["run_dir"]):
        raise RuntimeError("source_dir and run_dir must differ")
    expected_exe = str(compatibility.get("baldur_real_sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_exe):
        raise RuntimeError("compatibility.baldur_real_sha256 must be a SHA-256")
    contract = upscale_contract(job)
    if contract.explicit:
        job["upscale"] = contract.method
    job["_job_file"] = str(job_file)
    job["animation"]["bam_prefix"] = prefix
    job["animation"]["id"] = animation_id.upper().replace("X", "x")
    return job


def load_armor_set(set_file: Path) -> dict[str, Any]:
    set_file = resolve_path(set_file)
    armor_set = read_json(set_file)
    if armor_set.get("schema") != ARMOR_SET_SCHEMA:
        raise RuntimeError(f"unsupported armor-set schema: {armor_set.get('schema')!r}")
    job_id = str(armor_set.get("job_id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("armor-set job_id must match [a-z0-9][a-z0-9-]{1,63}")
    animation = armor_set.get("animation")
    paths = armor_set.get("paths")
    compatibility = armor_set.get("compatibility")
    members = armor_set.get("members")
    if not isinstance(animation, dict) or not isinstance(paths, dict) or not isinstance(compatibility, dict):
        raise RuntimeError("armor set requires animation, paths, and compatibility objects")
    if not isinstance(members, list) or not members or not all(isinstance(item, str) for item in members):
        raise RuntimeError("armor set requires a non-empty members list")
    animation_id = str(animation.get("id", ""))
    if not re.fullmatch(r"0x[0-9A-Fa-f]{4}", animation_id):
        raise RuntimeError("armor-set animation.id must use 0xFFFF notation")
    if int(animation_id, 16) & 0xF000 not in {0x5000, 0x6000}:
        raise RuntimeError("armor set requires a Character animation id")
    if animation.get("runtime_profile") != "character-bg2ee-2.7.3.0":
        raise RuntimeError("armor set requires the Character runtime profile")
    ids_symbol = str(animation.get("ids_symbol", "")).upper()
    if not re.fullmatch(r"[A-Z0-9_]{2,64}", ids_symbol):
        raise RuntimeError("armor set requires animation.ids_symbol from ANIMATE.IDS")
    required_paths = ("game_root", "run_dir", "engine_source", "engine_build")
    missing = [key for key in required_paths if not paths.get(key)]
    if missing:
        raise RuntimeError(f"armor-set paths missing: {', '.join(missing)}")
    for key in ("run_dir", "engine_source", "engine_build"):
        assert_workspace_child(resolve_path(paths[key]), f"paths.{key}")
    expected_exe = str(compatibility.get("baldur_real_sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_exe):
        raise RuntimeError("compatibility.baldur_real_sha256 must be a SHA-256")
    set_contract = upscale_contract(armor_set)
    if set_contract.explicit:
        armor_set["upscale"] = set_contract.method
    member_jobs: list[dict[str, Any]] = []
    seen_files: set[Path] = set()
    seen_codes: set[int] = set()
    seen_prefixes: set[str] = set()
    expected_game_root = resolve_path(paths["game_root"])
    for member_path in members:
        resolved = resolve_path(member_path)
        if resolved in seen_files:
            raise RuntimeError(f"duplicate armor-set member: {member_path}")
        seen_files.add(resolved)
        member = load_job(resolved)
        member_animation = member["animation"]
        if member_animation["runtime_profile"] != animation["runtime_profile"]:
            raise RuntimeError("armor-set member runtime profile differs from set")
        if member_animation["id"].upper() != animation_id.upper():
            raise RuntimeError("armor-set member animation id differs from set")
        if member_animation.get("ids_symbol") != ids_symbol:
            raise RuntimeError("armor-set member ANIMATE.IDS symbol differs from set")
        if resolve_path(member["paths"]["game_root"]) != expected_game_root:
            raise RuntimeError("armor-set member game root differs from set")
        if member["compatibility"]["baldur_real_sha256"].upper() != expected_exe:
            raise RuntimeError("armor-set member BaldurReal hash differs from set")
        prefix = str(member_animation["bam_prefix"])
        layer = character_layer_config(member)
        if prefix in seen_prefixes:
            raise RuntimeError("Character set must have unique BAM prefixes")
        if layer["kind"] == "body":
            code = int(member_animation["armor_code"])
            if code in seen_codes:
                raise RuntimeError("Character set must have unique body armor codes")
            seen_codes.add(code)
        seen_prefixes.add(prefix)
        member_jobs.append(member)
    member_contracts = [upscale_contract(member) for member in member_jobs]
    if not set_contract.explicit:
        identities = {contract.identity for contract in member_contracts}
        if len(identities) != 1:
            raise RuntimeError("armor-set members mix registry magic/version/scale")
        if set_contract.identity != member_contracts[0].identity:
            raise RuntimeError("armor-set upscale contract differs from member registries")
    elif set_contract.scale == 2:
        # V2/x2 and V3/x2 resource records have the same byte layout.  An
        # explicit x2 aggregate may therefore promote existing audited V2
        # members by rewriting only aggregate/shard headers, without spending
        # another xBR pass.  No other legacy-to-xN promotion is valid.
        allowed = {LEGACY_UPSCALE.identity, direct_upscale_contract(2).identity}
        if any(contract.identity not in allowed for contract in member_contracts):
            raise RuntimeError(
                "explicit x2 armor set accepts only legacy V2/x2 or XN V3/x2 members"
            )
    elif any(contract.identity != set_contract.identity for contract in member_contracts):
        raise RuntimeError("explicit x4 armor set requires XN V3/x4 members")
    armor_set["_job_file"] = str(set_file)
    armor_set["_kind"] = "armor-set"
    armor_set["_members"] = member_jobs
    armor_set["animation"]["id"] = animation_id.upper().replace("X", "x")
    armor_set["animation"]["ids_symbol"] = ids_symbol
    return armor_set


def runtime_profiles_for_work_item(work_item: dict[str, Any]) -> list[str]:
    if work_item.get("_kind") == "catalog":
        return sorted(
            {
                str(member["animation"]["runtime_profile"])
                for member in work_item["_catalog_members"]
            }
        )
    return [str(work_item["animation"].get("runtime_profile", ""))]


def catalog_member_leaf_jobs(member: dict[str, Any]) -> list[dict[str, Any]]:
    if member.get("_kind") == "armor-set":
        return list(member["_members"])
    return [member]


def normalized_catalog_qa_contract(
    catalog: dict[str, Any], members: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    qa = catalog.get("qa")
    scenarios = qa.get("animations") if isinstance(qa, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        raise RuntimeError("catalog requires qa.animations")
    by_animation: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise RuntimeError("catalog QA animation must be an object")
        try:
            animation_id = f"0x{int(str(scenario.get('animation_id', '')), 16):04X}"
        except ValueError as error:
            raise RuntimeError("catalog QA animation id is invalid") from error
        if animation_id in by_animation:
            raise RuntimeError(f"catalog QA animation is duplicated: {animation_id}")
        by_animation[animation_id] = scenario

    result: list[dict[str, Any]] = []
    for member in members:
        animation_id = f"0x{int(str(member['animation']['id']), 16):04X}"
        scenario = by_animation.get(animation_id)
        if scenario is None:
            raise RuntimeError(f"catalog QA scenario is missing: {animation_id}")
        prefixes = [
            str(leaf["animation"]["bam_prefix"]).upper()
            for leaf in catalog_member_leaf_jobs(member)
        ]
        required_value = scenario.get("required_bam_prefixes", prefixes)
        if (
            not isinstance(required_value, list)
            or not required_value
            or any(not isinstance(value, str) for value in required_value)
        ):
            raise RuntimeError(
                f"catalog QA required_bam_prefixes is invalid: {animation_id}"
            )
        required = [value.upper() for value in required_value]
        if len(required) != len(set(required)) or set(required) - set(prefixes):
            raise RuntimeError(
                f"catalog QA required_bam_prefixes differs from members: {animation_id}"
            )
        result.append(
            {
                "animation_id": animation_id,
                "runtime_profile": member["animation"]["runtime_profile"],
                "bam_prefixes": prefixes,
                "required_bam_prefixes": required,
            }
        )
    if set(by_animation) != {
        f"0x{int(str(member['animation']['id']), 16):04X}" for member in members
    }:
        raise RuntimeError("catalog QA scenarios differ from catalog animations")
    return result


def load_catalog_job(catalog_file: Path) -> dict[str, Any]:
    catalog_file = resolve_path(catalog_file)
    catalog = read_json(catalog_file)
    if catalog.get("schema") != CATALOG_JOB_SCHEMA:
        raise RuntimeError(f"unsupported catalog schema: {catalog.get('schema')!r}")
    job_id = str(catalog.get("job_id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("catalog job_id must match [a-z0-9][a-z0-9-]{1,63}")
    paths = catalog.get("paths")
    compatibility = catalog.get("compatibility")
    members = catalog.get("members")
    if not isinstance(paths, dict) or not isinstance(compatibility, dict):
        raise RuntimeError("catalog requires paths and compatibility objects")
    if (
        not isinstance(members, list)
        or not members
        or not all(isinstance(item, str) and item for item in members)
    ):
        raise RuntimeError("catalog requires a non-empty members list")
    required_paths = ("game_root", "run_dir", "engine_source", "engine_build")
    missing = [key for key in required_paths if not paths.get(key)]
    if missing:
        raise RuntimeError(f"catalog paths missing: {', '.join(missing)}")
    for key in ("run_dir", "engine_source", "engine_build"):
        assert_workspace_child(resolve_path(paths[key]), f"paths.{key}")
    expected_exe = str(compatibility.get("baldur_real_sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_exe):
        raise RuntimeError("compatibility.baldur_real_sha256 must be a SHA-256")
    contract = upscale_contract(catalog)
    if not contract.explicit:
        raise RuntimeError("catalog requires an explicit xN upscale contract")
    catalog["upscale"] = contract.method

    loaded_members: list[dict[str, Any]] = []
    seen_files: set[Path] = set()
    seen_animation_ids: set[str] = set()
    expected_game_root = resolve_path(paths["game_root"])
    for member_text in members:
        member_path = resolve_path(member_text)
        if member_path in seen_files:
            raise RuntimeError(f"duplicate catalog member: {member_text}")
        seen_files.add(member_path)
        member_schema = read_json(member_path).get("schema")
        if member_schema == JOB_SCHEMA:
            member = load_job(member_path)
        elif member_schema == ARMOR_SET_SCHEMA:
            member = load_armor_set(member_path)
        else:
            raise RuntimeError(
                "catalog members must be individual or armor-set sprite jobs"
            )
        member_contract = upscale_contract(member)
        if contract.scale == 2:
            allowed = {
                LEGACY_UPSCALE.identity,
                direct_upscale_contract(2).identity,
            }
            leaf_contracts = {
                upscale_contract(leaf).identity
                for leaf in catalog_member_leaf_jobs(member)
            }
            if not leaf_contracts or not leaf_contracts.issubset(allowed):
                raise RuntimeError(
                    "x2 catalog accepts only legacy V2/x2 or XN V3/x2 member payloads"
                )
        elif member_contract.identity != contract.identity or any(
            upscale_contract(leaf).identity != contract.identity
            for leaf in catalog_member_leaf_jobs(member)
        ):
            raise RuntimeError("x4 catalog requires only XN V3/x4 member payloads")
        animation_id = str(member["animation"]["id"]).upper()
        if animation_id in seen_animation_ids:
            raise RuntimeError(f"catalog animation id is duplicated: {animation_id}")
        seen_animation_ids.add(animation_id)
        profile = str(member["animation"].get("runtime_profile", ""))
        if profile not in SUPPORTED_RUNTIME_PROFILES:
            raise RuntimeError(f"unsupported catalog runtime profile: {profile!r}")
        if resolve_path(member["paths"]["game_root"]) != expected_game_root:
            raise RuntimeError("catalog member game root differs from catalog")
        if member["compatibility"]["baldur_real_sha256"].upper() != expected_exe:
            raise RuntimeError("catalog member BaldurReal hash differs from catalog")
        loaded_members.append(member)

    installation = catalog.get("installation", {})
    if not isinstance(installation, dict):
        raise RuntimeError("catalog installation must be an object")
    import_state = installation.get("import_active_state")
    if import_state is not None:
        if not isinstance(import_state, dict):
            raise RuntimeError("installation.import_active_state must be an object")
        if set(import_state) != {"state_path", "job_id"}:
            raise RuntimeError(
                "installation.import_active_state requires exactly state_path and job_id"
            )
        state_path_text = str(import_state.get("state_path", ""))
        imported_job_id = str(import_state.get("job_id", ""))
        if not state_path_text or not imported_job_id:
            raise RuntimeError("catalog import active state is incomplete")
        state_path = resolve_path(state_path_text)
        assert_workspace_child(state_path, "installation.import_active_state.state_path")
        installation["import_active_state"] = {
            "state_path": relative_project_path(state_path),
            "job_id": imported_job_id,
        }
    unexpected_installation = set(installation) - {"import_active_state"}
    if unexpected_installation:
        raise RuntimeError(
            "unsupported catalog installation fields: "
            + ", ".join(sorted(unexpected_installation))
        )

    catalog["installation"] = installation
    catalog["_job_file"] = str(catalog_file)
    catalog["_kind"] = "catalog"
    catalog["_catalog_members"] = loaded_members
    catalog["_qa_contract"] = normalized_catalog_qa_contract(
        catalog, loaded_members
    )
    return catalog


def load_work_item(path: Path) -> dict[str, Any]:
    path = resolve_path(path)
    schema = read_json(path).get("schema")
    if schema == JOB_SCHEMA:
        return load_job(path)
    if schema == ARMOR_SET_SCHEMA:
        return load_armor_set(path)
    if schema == CATALOG_JOB_SCHEMA:
        return load_catalog_job(path)
    raise RuntimeError(f"unsupported job schema: {schema!r}")


def job_path(job: dict[str, Any], key: str) -> Path:
    return resolve_path(job["paths"][key])


def source_manifest_path(job: dict[str, Any]) -> Path:
    return job_path(job, "source_dir") / "manifest.json"


def build_dir(job: dict[str, Any]) -> Path:
    if job.get("_kind") == "catalog":
        return catalog_generation_dir(job) / "build"
    return job_path(job, "run_dir") / "build"


def runtime_dir(job: dict[str, Any]) -> Path:
    if job.get("_kind") == "catalog":
        return catalog_generation_dir(job) / "runtime"
    return job_path(job, "run_dir") / "runtime"


def active_state_path(job: dict[str, Any]) -> Path:
    if job.get("_kind") == "catalog":
        return job_path(job, "run_dir") / "ingame-installation" / "active-test.json"
    return job_path(job, "run_dir") / "ingame-test" / "active-test.json"


def catalog_pointer_path(catalog: dict[str, Any]) -> Path:
    return job_path(catalog, "run_dir") / "current-generation.json"


def catalog_payload_path(
    build_root: Path, relative_value: Any, label: str
) -> Path:
    relative_text = str(relative_value or "").replace("\\", "/")
    relative = Path(relative_text)
    if (
        not relative_text
        or relative.is_absolute()
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise RuntimeError(f"{label} must be a canonical relative path")
    root = Path(os.path.abspath(build_root))
    candidate = Path(os.path.abspath(root / relative))
    try:
        candidate_relative = candidate.relative_to(root)
        project_relative = candidate.relative_to(PROJECT_ROOT)
    except ValueError as error:
        raise RuntimeError(f"{label} leaves its immutable build root") from error
    if candidate_relative != relative:
        raise RuntimeError(f"{label} is not canonical")
    reparse = first_reparse_component(PROJECT_ROOT, project_relative)
    if reparse is not None:
        raise RuntimeError(f"{label} crosses a forbidden reparse point: {reparse}")
    if not candidate.is_file():
        raise RuntimeError(f"{label} is missing: {candidate}")
    return candidate


def catalog_leaf_payload_paths(
    build_root: Path, manifest: dict[str, Any]
) -> list[Path]:
    layout = str(manifest.get("registry_layout", "monolith"))
    if layout == "monolith":
        paths = [
            catalog_payload_path(
                build_root, manifest.get("registry"), "catalog leaf registry"
            )
        ]
    elif layout == "set":
        paths = [
            catalog_payload_path(
                build_root,
                manifest.get("registry_set"),
                "catalog leaf registry-set index",
            )
        ]
        shards = manifest.get("shards")
        if not isinstance(shards, list) or not (
            1 <= len(shards) <= MAX_REGISTRY_SET_SHARDS
        ):
            raise RuntimeError("catalog leaf registry-set shards are invalid")
        for index, shard in enumerate(shards):
            if not isinstance(shard, dict):
                raise RuntimeError("catalog leaf registry-set shard is invalid")
            paths.append(
                catalog_payload_path(
                    build_root,
                    shard.get("registry"),
                    f"catalog leaf registry-set shard {index:04d}",
                )
            )
    else:
        raise RuntimeError(f"unsupported catalog leaf registry layout: {layout}")
    ordered = sorted(paths, key=lambda path: relative_project_path(path).casefold())
    normalized = [os.path.normcase(os.path.abspath(path)) for path in ordered]
    if len(normalized) != len(set(normalized)):
        raise RuntimeError("catalog leaf payload paths are duplicated")
    return ordered


def catalog_payload_fingerprint(path: Path) -> dict[str, Any]:
    """Hash one regular payload from a stable file identity in a single pass."""

    sha256 = hashlib.sha256()
    crc32 = 0
    byte_count = 0
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise RuntimeError(f"catalog payload is not a regular file: {path}")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha256.update(chunk)
            crc32 = zlib.crc32(chunk, crc32)
            byte_count += len(chunk)
        after = os.fstat(stream.fileno())
    path_after = path.stat()
    identity_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if (
        any(getattr(before, name) != getattr(after, name) for name in identity_fields)
        or not os.path.samestat(after, path_after)
        or any(getattr(after, name) != getattr(path_after, name) for name in identity_fields)
        or byte_count != after.st_size
    ):
        raise RuntimeError(f"catalog payload changed while it was hashed: {path}")
    return {
        "path": relative_project_path(path),
        "sha256": sha256.hexdigest().upper(),
        "crc32": crc32 & 0xFFFFFFFF,
        "bytes": byte_count,
    }


def catalog_input_lock(
    catalog: dict[str, Any], *, refresh: bool = False
) -> dict[str, Any]:
    if catalog.get("_kind") != "catalog":
        raise RuntimeError("catalog input lock requires a catalog job")
    cached = catalog.get("_catalog_input_lock")
    if not refresh and isinstance(cached, dict):
        return cached
    game_exe = job_path(catalog, "game_root") / "BaldurReal.exe"
    expected_exe = catalog["compatibility"]["baldur_real_sha256"].upper()
    if not game_exe.is_file() or sha256_file(game_exe) != expected_exe:
        raise RuntimeError("BaldurReal.exe is incompatible with the catalog job")
    source = job_path(catalog, "engine_source")
    members: list[dict[str, Any]] = []
    leaf_jobs: list[dict[str, Any]] = []
    seen_leaf_files: set[str] = set()
    for member in catalog["_catalog_members"]:
        member_file = Path(member["_job_file"])
        member_manifest = build_dir(member) / "build-manifest.json"
        if not member_manifest.is_file():
            raise RuntimeError(
                f"catalog member build manifest is missing: {member_manifest}"
            )
        member_entry = {
            "job_file": relative_project_path(member_file),
            "job_sha256": sha256_file(member_file),
            "job_id": member["job_id"],
            "build_manifest": relative_project_path(member_manifest),
            "build_manifest_sha256": sha256_file(member_manifest),
        }
        members.append(member_entry)
        for leaf in catalog_member_leaf_jobs(member):
            leaf_file = Path(leaf["_job_file"])
            leaf_file_key = str(leaf_file.resolve()).casefold()
            if leaf_file_key in seen_leaf_files:
                raise RuntimeError("catalog repeats a leaf job across members")
            seen_leaf_files.add(leaf_file_key)
            source_manifest = source_manifest_path(leaf)
            leaf_manifest = build_dir(leaf) / "build-manifest.json"
            if not source_manifest.is_file() or not leaf_manifest.is_file():
                raise RuntimeError(
                    f"catalog leaf source/build is incomplete: {leaf['job_id']}"
                )
            leaf_manifest_value = read_json(leaf_manifest)
            leaf_jobs.append(
                {
                    "job_file": relative_project_path(leaf_file),
                    "job_sha256": sha256_file(leaf_file),
                    "job_id": leaf["job_id"],
                    "source_manifest": relative_project_path(source_manifest),
                    "source_manifest_sha256": sha256_file(source_manifest),
                    "build_manifest": relative_project_path(leaf_manifest),
                    "build_manifest_sha256": sha256_file(leaf_manifest),
                    "payloads": [
                        catalog_payload_fingerprint(path)
                        for path in catalog_leaf_payload_paths(
                            build_dir(leaf), leaf_manifest_value
                        )
                    ],
                }
            )
    result = {
        "schema": "bg2-upscale-creature-sprite-xn-catalog-input-lock-v1",
        "job_file": relative_project_path(Path(catalog["_job_file"])),
        "job_sha256": sha256_file(Path(catalog["_job_file"])),
        "method": upscale_contract(catalog).method,
        "baldur_real_sha256": expected_exe,
        "engine_source": relative_project_path(source),
        "engine_source_contract_sha256": source_tree_hash(source),
        "catalog_builder": relative_project_path(Path(__file__)),
        "catalog_builder_sha256": sha256_file(Path(__file__)),
        "members": members,
        "leaf_jobs": leaf_jobs,
    }
    catalog["_catalog_input_lock"] = result
    return result


def catalog_generation_id(
    catalog: dict[str, Any], *, refresh: bool = False
) -> str:
    return canonical_json_sha256(catalog_input_lock(catalog, refresh=refresh))


def catalog_generation_dir(catalog: dict[str, Any]) -> Path:
    generation_id = catalog_generation_id(catalog)
    return job_path(catalog, "run_dir") / "generations" / generation_id.lower()


def catalog_object_store_dir(catalog: dict[str, Any]) -> Path:
    return (
        job_path(catalog, "run_dir")
        / "object-store"
        / "creature-sprites-xn-v5"
    )


def require_runtime_profile(job: dict[str, Any]) -> None:
    profiles = runtime_profiles_for_work_item(job)
    unsupported = sorted(set(profiles) - SUPPORTED_RUNTIME_PROFILES)
    if unsupported:
        raise RuntimeError(
            f"unsupported-runtime-profile: {unsupported!r}; supported: "
            f"{', '.join(sorted(SUPPORTED_RUNTIME_PROFILES))}"
        )


class KeyIndex:
    def __init__(self, game_root: Path):
        self.game_root = game_root.resolve()
        key_path = self.game_root / "chitin.key"
        raw = key_path.read_bytes()
        if raw[:8] != b"KEY V1  ":
            raise RuntimeError(f"unsupported chitin.key: {raw[:8]!r}")
        bif_count, resource_count, bif_offset, resource_offset = struct.unpack_from(
            "<IIII", raw, 8
        )
        self.bifs: list[str] = []
        for index in range(bif_count):
            offset = bif_offset + index * 12
            _, name_offset, name_length, _ = struct.unpack_from("<IIHH", raw, offset)
            name = raw[name_offset : name_offset + name_length].split(b"\0", 1)[0]
            self.bifs.append(name.decode("cp1252", errors="strict"))
        self.resources: list[tuple[str, int, int]] = []
        for index in range(resource_count):
            offset = resource_offset + index * 14
            name_raw, resource_type, locator = struct.unpack_from("<8sHI", raw, offset)
            name = name_raw.split(b"\0", 1)[0].decode("ascii", errors="strict").upper()
            self.resources.append((name, resource_type, locator))
        self._bif_cache: dict[str, bytes] = {}

    def resource_map(self, resource_type: int) -> dict[str, tuple[str, int, int]]:
        return {
            name: (name, kind, locator)
            for name, kind, locator in self.resources
            if kind == resource_type
        }

    def _load_bif(self, bif_name: str) -> bytes:
        cached = self._bif_cache.get(bif_name)
        if cached is not None:
            return cached
        local_name = bif_name.replace("/", os.sep).replace("\\", os.sep)
        raw = (self.game_root / local_name).read_bytes()
        if raw[:4] == b"BIFC":
            position = 8
            expected_length = struct.unpack_from("<I", raw, position)[0]
            position += 4
            chunks = []
            while position < len(raw):
                unpacked, packed = struct.unpack_from("<II", raw, position)
                position += 8
                chunk = zlib.decompress(raw[position : position + packed])
                position += packed
                if len(chunk) != unpacked:
                    raise RuntimeError(f"invalid BIFC chunk in {bif_name}")
                chunks.append(chunk)
            data = b"".join(chunks)
            if len(data) != expected_length:
                raise RuntimeError(f"invalid BIFC size in {bif_name}")
        else:
            data = raw
        if data[:4] != b"BIFF":
            raise RuntimeError(f"unsupported BIF: {bif_name}")
        self._bif_cache[bif_name] = data
        return data

    def resolve(self, entry: tuple[str, int, int]) -> tuple[bytes, str]:
        _, _, locator = entry
        bif_index = (locator >> 20) & 0xFFF
        resource_index = locator & 0x3FFF
        if bif_index >= len(self.bifs):
            raise RuntimeError(f"invalid BIF index in locator 0x{locator:08X}")
        bif_name = self.bifs[bif_index]
        data = self._load_bif(bif_name)
        file_count, _, files_offset = struct.unpack_from("<III", data, 8)
        for index in range(file_count):
            offset = files_offset + index * 16
            item_locator, item_offset, item_size, _, _ = struct.unpack_from(
                "<IIIHH", data, offset
            )
            if (item_locator & 0x3FFF) == resource_index:
                return data[item_offset : item_offset + item_size], bif_name
        raise RuntimeError(f"resource locator 0x{locator:08X} absent from {bif_name}")


def parse_animation_ini(raw: bytes) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for source_line in raw.decode("cp1252", errors="strict").replace("\0", "").splitlines():
        line = source_line.strip()
        if not line or line.startswith(("//", ";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            name = line[1:-1].strip().lower()
            current = sections.setdefault(name, {})
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.split("=", 1)
        current[key.strip().lower()] = value.strip()
    return sections


def parse_ids(raw: bytes) -> dict[int, str]:
    values: dict[int, str] = {}
    for source_line in raw.decode("cp1252", errors="strict").replace("\0", "").splitlines():
        line = source_line.strip()
        if not line or line.startswith(("//", ";", "#")):
            continue
        fields = line.split()
        if len(fields) < 2:
            continue
        try:
            number = int(fields[0], 16 if fields[0].lower().startswith("0x") else 10)
        except ValueError:
            continue
        values[number] = fields[1].upper()
    return values


def animation_id_for_symbol(index: KeyIndex, ids_symbol: str) -> int:
    symbol = ids_symbol.upper()
    if not re.fullmatch(r"[A-Z0-9_]{2,64}", symbol):
        raise RuntimeError("--ids-symbol must be an ANIMATE.IDS symbol")
    animate_entry = index.resource_map(IDS_TYPE).get("ANIMATE")
    if animate_entry is None:
        raise RuntimeError("animation identity: ANIMATE.IDS absent from installed chitin.key")
    animate_raw, _ = index.resolve(animate_entry)
    matches = [number for number, name in parse_ids(animate_raw).items() if name == symbol]
    if len(matches) != 1:
        raise RuntimeError(
            f"animation identity: {symbol} must resolve exactly once in ANIMATE.IDS"
        )
    return matches[0]


def character_layer_config(job: dict[str, Any]) -> dict[str, str]:
    """Return a normalized Character layer while preserving legacy body jobs."""

    animation = job.get("animation", {})
    raw = animation.get("layer", {"kind": "body"})
    if not isinstance(raw, dict):
        raise RuntimeError("Character animation.layer must be an object")
    kind = str(raw.get("kind", "body")).lower()
    if kind not in CHARACTER_LAYER_KINDS:
        raise RuntimeError(f"unsupported Character layer kind: {kind!r}")
    result = {"kind": kind}
    if kind != "body":
        item_resref = str(raw.get("item_resref", "")).upper()
        if not re.fullmatch(r"[A-Z0-9_]{1,8}", item_resref):
            raise RuntimeError("Character equipment layer requires item_resref")
        result["item_resref"] = item_resref
    return result


def character_animation_spec(
    index: KeyIndex, animation_id: int, armor_code: int
) -> dict[str, Any]:
    if not 0 <= animation_id <= 0xFFFF:
        raise RuntimeError("character animation id must fit 0x0000..0xFFFF")
    ini_name = f"{animation_id:04X}"
    entry = index.resource_map(INI_TYPE).get(ini_name)
    if entry is None:
        raise RuntimeError(f"animation identity: {ini_name}.INI absent from installed chitin.key")
    raw, bif_name = index.resolve(entry)
    sections = parse_animation_ini(raw)
    animation_type = sections.get("general", {}).get("animation_type", "").upper()
    expected_type = f"{animation_id & 0xF000:04X}"
    if animation_type != expected_type or animation_type not in {"5000", "6000"}:
        raise RuntimeError(
            f"animation identity: {ini_name}.INI type {animation_type!r} is incompatible "
            f"with character animation 0x{animation_id:04X}"
        )
    character = sections.get("character", {})
    base_resref = character.get("resref", "").upper()
    paperdoll_resref = character.get("resref_paperdoll", "").upper()
    armor_base = character.get("resref_armor_base", "").upper()
    armor_specific = character.get("resref_armor_specific", "").upper()
    height_code = character.get("height_code", "").upper()
    height_code_helmet = character.get("height_code_helmet", "").upper()
    height_code_shield = character.get("height_code_shield", "").upper()
    split_bams = character.get("split_bams", "")
    armor_max_text = character.get("armor_max_code", "")
    if not re.fullmatch(r"[A-Z0-9_]{1,7}", base_resref):
        raise RuntimeError(f"animation identity: invalid body resref in {ini_name}.INI")
    if not armor_max_text.isdigit():
        raise RuntimeError(f"animation identity: invalid armor_max_code in {ini_name}.INI")
    armor_max = int(armor_max_text)
    if armor_code < 1 or armor_code > armor_max:
        raise RuntimeError(
            f"animation identity: armor code {armor_code} outside 1..{armor_max} for "
            f"0x{animation_id:04X}"
        )
    resolved_body_resref = base_resref
    if armor_code == armor_max and armor_specific:
        if not armor_base or not base_resref.endswith(armor_base):
            raise RuntimeError(
                f"animation identity: {base_resref} does not end with armor base "
                f"{armor_base or '<missing>'} in {ini_name}.INI"
            )
        resolved_body_resref = base_resref[: -len(armor_base)] + armor_specific
    prefix = f"{resolved_body_resref}{armor_code}"
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", prefix):
        raise RuntimeError(f"animation identity: derived BAM prefix is invalid: {prefix}")

    animate_entry = index.resource_map(IDS_TYPE).get("ANIMATE")
    if animate_entry is None:
        raise RuntimeError("animation identity: ANIMATE.IDS absent from installed chitin.key")
    animate_raw, animate_bif_name = index.resolve(animate_entry)
    ids_symbol = parse_ids(animate_raw).get(animation_id)
    if not ids_symbol:
        raise RuntimeError(f"animation identity: 0x{animation_id:04X} absent from ANIMATE.IDS")

    if split_bams != "1":
        raise RuntimeError(
            f"animation identity: {ini_name}.INI split_bams={split_bams!r} is unsupported"
        )
    bam_map = index.resource_map(BAM_TYPE)
    resources = [f"{prefix}{suffix}" for suffix in CHARACTER_BODY_SUFFIXES]
    missing = [name for name in resources if name not in bam_map]
    if missing:
        raise RuntimeError(
            f"animation identity: missing Character body BAM for {prefix}: "
            + ", ".join(missing)
        )
    if len(resources) > MAX_RESOURCES:
        raise RuntimeError(
            f"animation identity: {len(resources)} resources exceed runtime limit "
            f"{MAX_RESOURCES}"
        )
    return {
        "animation_id": f"0x{animation_id:04X}",
        "ids_symbol": ids_symbol,
        "animate_ids_source_bif": animate_bif_name.replace("\\", "/"),
        "animate_ids_sha256": hashlib.sha256(animate_raw).hexdigest().upper(),
        "ini": f"{ini_name}.INI",
        "source_bif": bif_name.replace("\\", "/"),
        "ini_sha256": hashlib.sha256(raw).hexdigest().upper(),
        "animation_type": animation_type,
        "base_body_resref": base_resref,
        "body_resref": resolved_body_resref,
        "paperdoll_resref": paperdoll_resref,
        "armor_base": armor_base,
        "armor_specific": armor_specific,
        "height_code": height_code,
        "height_code_helmet": height_code_helmet,
        "height_code_shield": height_code_shield,
        "split_bams": int(split_bams),
        "armor_code": armor_code,
        "armor_max_code": armor_max,
        "layer_kind": "body",
        "bam_prefix": prefix,
        "resources": resources,
        "resource_count": len(resources),
    }


def character_equipment_spec(
    index: KeyIndex, animation_id: int, layer_kind: str, item_resref: str
) -> dict[str, Any]:
    """Resolve an equipment BAM family from the Character INI and stock ITM."""

    kind = layer_kind.lower()
    if kind not in CHARACTER_EQUIPMENT_ITEM_TYPES:
        raise RuntimeError(f"unsupported Character equipment layer: {layer_kind!r}")
    item_name = item_resref.upper()
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", item_name):
        raise RuntimeError(f"invalid equipment item resref: {item_resref!r}")

    # Armor code 1 is used only to resolve the shared Character identity and
    # height codes. Equipment resources themselves are independent of armor.
    identity = character_animation_spec(index, animation_id, 1)
    item_entry = index.resource_map(ITM_TYPE).get(item_name)
    if item_entry is None:
        raise RuntimeError(f"equipment identity: {item_name}.ITM absent from installed chitin.key")
    item_raw, item_bif = index.resolve(item_entry)
    if len(item_raw) < 0x24 or item_raw[:8] != b"ITM V1  ":
        raise RuntimeError(f"equipment identity: unsupported {item_name}.ITM")
    item_type = struct.unpack_from("<H", item_raw, 0x1C)[0]
    expected_types = CHARACTER_EQUIPMENT_ITEM_TYPES[kind]
    if expected_types and item_type not in expected_types:
        raise RuntimeError(
            f"equipment identity: {item_name}.ITM type {item_type} is not a {kind}"
        )
    try:
        animation_code = item_raw[0x22:0x24].decode("ascii").upper()
    except UnicodeDecodeError as error:
        raise RuntimeError(
            f"equipment identity: {item_name}.ITM has a non-ASCII animation code"
        ) from error
    if not re.fullmatch(r"[A-Z0-9]{2}", animation_code):
        raise RuntimeError(
            f"equipment identity: {item_name}.ITM has invalid animation code "
            f"{animation_code!r}"
        )

    height_key = {
        "helmet": "height_code_helmet",
        "shield": "height_code_shield",
        "weapon": "height_code",
    }[kind]
    height_code = str(identity.get(height_key, "") or identity.get("height_code", "")).upper()
    if not re.fullmatch(r"[A-Z0-9_]{1,6}", height_code):
        raise RuntimeError(
            f"equipment identity: Character {height_key} is unavailable for {item_name}"
        )
    prefix = f"{height_code}{animation_code}"
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", prefix):
        raise RuntimeError(f"equipment identity: derived BAM prefix is invalid: {prefix}")

    bam_map = index.resource_map(BAM_TYPE)
    equipment_suffixes = CHARACTER_EQUIPMENT_SUFFIXES_BY_LAYER[kind]
    resources = [
        f"{prefix}{suffix}"
        for suffix in equipment_suffixes
        if f"{prefix}{suffix}" in bam_map
    ]
    if not resources:
        raise RuntimeError(f"equipment identity: no Character BAM belongs to {prefix}")
    ignored_paperdolls = {f"{prefix}INV"}
    unexpected = sorted(
        name
        for name in bam_map
        if name.startswith(prefix)
        and name not in resources
        and name not in ignored_paperdolls
    )
    if unexpected:
        raise RuntimeError(
            f"equipment identity: unsupported BAM suffix for {prefix}: "
            + ", ".join(unexpected)
        )

    return {
        **identity,
        "armor_code": None,
        "armor_max_code": identity["armor_max_code"],
        "body_bam_prefix": identity["bam_prefix"],
        "layer_kind": kind,
        "item_resref": item_name,
        "item_type": item_type,
        "item_source_bif": item_bif.replace("\\", "/"),
        "item_sha256": hashlib.sha256(item_raw).hexdigest().upper(),
        "item_animation_code": animation_code,
        "equipment_height_code": height_code,
        "bam_prefix": prefix,
        "resources": resources,
        "resource_count": len(resources),
    }


def verify_character_animation_identity(
    job: dict[str, Any], index: KeyIndex
) -> dict[str, Any] | None:
    if job["animation"].get("runtime_profile") != "character-bg2ee-2.7.3.0":
        return None
    animation_id = int(job["animation"]["id"], 16)
    prefix = job["animation"]["bam_prefix"]
    layer = character_layer_config(job)
    if layer["kind"] != "body":
        spec = character_equipment_spec(
            index, animation_id, layer["kind"], layer["item_resref"]
        )
        expected_symbol = str(job["animation"].get("ids_symbol", "")).upper()
        if expected_symbol != spec["ids_symbol"]:
            raise RuntimeError(
                f"animation identity mismatch: {job['animation']['id']} is "
                f"{spec['ids_symbol']} in ANIMATE.IDS, not {expected_symbol or '<missing>'}"
            )
        if prefix != spec["bam_prefix"]:
            raise RuntimeError(
                f"equipment identity mismatch: {layer['item_resref']} resolves to BAM prefix "
                f"{spec['bam_prefix']}, not {prefix}"
            )
        return spec
    match = re.fullmatch(r"[A-Z0-9_]{1,7}([1-9])", prefix)
    if not match:
        raise RuntimeError(
            f"animation identity mismatch: Character BAM prefix must end in one armor code: "
            f"{prefix}"
        )
    prefix_armor_code = int(match.group(1))
    expected_armor_code = int(job["animation"].get("armor_code", -1))
    if prefix_armor_code != expected_armor_code:
        raise RuntimeError(
            f"animation identity mismatch: BAM prefix {prefix} carries armor code "
            f"{prefix_armor_code}, job declares {expected_armor_code}"
        )
    spec = character_animation_spec(index, animation_id, expected_armor_code)
    expected_symbol = str(job["animation"].get("ids_symbol", "")).upper()
    if expected_symbol != spec["ids_symbol"]:
        raise RuntimeError(
            f"animation identity mismatch: {job['animation']['id']} is "
            f"{spec['ids_symbol']} in ANIMATE.IDS, not {expected_symbol or '<missing>'}"
        )
    if prefix != spec["bam_prefix"]:
        raise RuntimeError(
            f"animation identity mismatch: {job['animation']['id']} resolves to BAM prefix "
            f"{spec['bam_prefix']}, not {prefix}"
        )
    return spec


def character_override_collisions(job: dict[str, Any], game_root: Path) -> list[str]:
    if job["animation"].get("runtime_profile") != "character-bg2ee-2.7.3.0":
        return []
    override = game_root / "override"
    if not override.is_dir():
        return []
    animation_ini = f"{int(job['animation']['id'], 16):04X}.INI"
    blocked = {animation_ini, "ANIMATE.IDS"}
    layer = character_layer_config(job)
    if layer["kind"] != "body":
        blocked.add(f"{layer['item_resref']}.ITM")
    return sorted(path.name for path in override.iterdir() if path.is_file() and path.name.upper() in blocked)


def require_clean_character_identity_overrides(
    job: dict[str, Any], game_root: Path
) -> None:
    collisions = character_override_collisions(job, game_root)
    if collisions:
        raise RuntimeError(
            "character animation identity is overridden outside KEY/BIF: "
            + ", ".join(collisions)
        )


def create_character_job(
    destination: Path,
    template_file: Path | None,
    ids_symbol_text: str | None,
    animation_id_text: str | None,
    armor_code: int | None,
    display_name: str | None,
    qa_areas: list[str],
    qa_creatures: list[str],
    requested_scale: int | None,
    force: bool,
) -> dict[str, Any]:
    if template_file is None:
        raise RuntimeError("new-character-job requires --template-job")
    if ids_symbol_text is None:
        raise RuntimeError("new-character-job requires --ids-symbol from ANIMATE.IDS")
    if animation_id_text is not None and not re.fullmatch(
        r"0x[0-9A-Fa-f]{4}", animation_id_text
    ):
        raise RuntimeError("--animation-id must use 0xFFFF notation")
    if armor_code is None:
        raise RuntimeError("new-character-job requires --armor-code")

    target = resolve_path(destination)
    jobs_root = (PROJECT_ROOT / "sprite" / "jobs").resolve()
    workspace = playable_character_workspace_from_job_path(target)
    if (target.parent != jobs_root and workspace is None) or target.suffix.lower() != ".json":
        raise RuntimeError(
            "new character job must be a legacy sprite/jobs/<job>.json path or "
            "sprite/families/playable-characters/<family>/<unit>/jobs/<job>.json: "
            f"{target}"
        )
    job_id = target.stem
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("destination filename must be a valid lowercase job id")
    if not re.search(r"-xbr(?:2|4)x$", job_id):
        raise RuntimeError("character job filename must end with -xbr2x.json or -xbr4x.json")
    if target.exists() and not force:
        raise RuntimeError(f"job already exists; use --force to replace exactly {target}")

    template = load_job(resolve_path(template_file))
    contract = creation_upscale_contract(template, requested_scale)
    job_suffix = f"-xbr{contract.scale}x"
    if not job_id.endswith(job_suffix):
        raise RuntimeError(
            f"character job filename must end with {job_suffix}.json for the template"
        )
    game_root = job_path(template, "game_root")
    exe = game_root / "BaldurReal.exe"
    expected_exe = template["compatibility"]["baldur_real_sha256"].upper()
    if not exe.is_file() or sha256_file(exe) != expected_exe:
        raise RuntimeError("template job does not match the installed BaldurReal.exe")
    index = KeyIndex(game_root)
    resolved_animation_id = animation_id_for_symbol(index, ids_symbol_text)
    if (
        animation_id_text is not None
        and int(animation_id_text, 16) != resolved_animation_id
    ):
        raise RuntimeError(
            f"animation identity mismatch: {ids_symbol_text.upper()} resolves to "
            f"0x{resolved_animation_id:04X}, not {animation_id_text}"
        )
    resolved_animation_id_text = f"0x{resolved_animation_id:04X}"
    provisional = {
        "animation": {
            "id": resolved_animation_id_text,
            "runtime_profile": "character-bg2ee-2.7.3.0",
        }
    }
    require_clean_character_identity_overrides(provisional, game_root)
    spec = character_animation_spec(index, resolved_animation_id, armor_code)

    asset_id = job_id[: -len(job_suffix)]
    paths = dict(template["paths"])
    if workspace is None:
        paths["source_dir"] = f"sprite/{asset_id}/source"
        paths["run_dir"] = (
            f"sprite/{asset_id}/runs/xbr{contract.scale}x-x{contract.scale}"
        )
    else:
        paths.update(
            character_workspace_paths(
                workspace, job_id, contract.scale, resolved_animation_id_text
            )
        )
    runtime = dict(template.get("runtime", {}))
    runtime.setdefault("no_filter_comparison", True)
    job: dict[str, Any] = {
        "schema": JOB_SCHEMA,
        "job_id": job_id,
        "animation": {
            "name": display_name or spec["ids_symbol"].replace("_", " ").title(),
            "id": spec["animation_id"],
            "ids_symbol": spec["ids_symbol"],
            "armor_code": spec["armor_code"],
            "bam_prefix": spec["bam_prefix"],
            "runtime_profile": "character-bg2ee-2.7.3.0",
        },
        "paths": paths,
        "compatibility": dict(template["compatibility"]),
        "runtime": runtime,
        "qa": {
            "areas": [value.upper() for value in qa_areas],
            "creatures": [value.upper() for value in qa_creatures],
        },
    }
    if isinstance(template.get("tools"), dict):
        job["tools"] = dict(template["tools"])
    if contract.explicit:
        job["upscale"] = contract.method
    write_json(target, job)
    loaded = load_job(target)
    verified = verify_character_animation_identity(loaded, KeyIndex(game_root))
    return {
        "status": "character-job-created",
        "job_file": relative_project_path(target),
        "job_id": job_id,
        "animation_identity": verified,
        "source_dir": paths["source_dir"],
        "run_dir": paths["run_dir"],
        "next": f"python pipeline/scripts/run_creature_sprite_x2.py plan --job {relative_project_path(target)}",
    }


def create_character_equipment_job(
    destination: Path,
    template_file: Path | None,
    ids_symbol_text: str | None,
    animation_id_text: str | None,
    layer_kind_text: str | None,
    item_resref_text: str | None,
    display_name: str | None,
    qa_areas: list[str],
    qa_creatures: list[str],
    requested_scale: int | None,
    force: bool,
) -> dict[str, Any]:
    if template_file is None:
        raise RuntimeError("new-character-equipment-job requires --template-job")
    if ids_symbol_text is None:
        raise RuntimeError("new-character-equipment-job requires --ids-symbol")
    if animation_id_text is not None and not re.fullmatch(
        r"0x[0-9A-Fa-f]{4}", animation_id_text
    ):
        raise RuntimeError("--animation-id must use 0xFFFF notation")
    layer_kind = str(layer_kind_text or "").lower()
    if layer_kind not in CHARACTER_EQUIPMENT_ITEM_TYPES:
        raise RuntimeError(
            "new-character-equipment-job requires --layer-kind helmet, shield, or weapon"
        )
    item_resref = str(item_resref_text or "").upper()
    if not re.fullmatch(r"[A-Z0-9_]{1,8}", item_resref):
        raise RuntimeError("new-character-equipment-job requires --item-resref")

    target = resolve_path(destination)
    jobs_root = (PROJECT_ROOT / "sprite" / "jobs").resolve()
    workspace = playable_character_workspace_from_job_path(target)
    if (target.parent != jobs_root and workspace is None) or target.suffix.lower() != ".json":
        raise RuntimeError(
            "new Character equipment job must be a legacy sprite/jobs/<job>.json path or "
            "sprite/families/playable-characters/<family>/<unit>/jobs/<job>.json: "
            f"{target}"
        )
    job_id = target.stem
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("destination filename must be a valid lowercase job id")
    if not re.search(r"-xbr(?:2|4)x$", job_id):
        raise RuntimeError(
            "Character equipment job filename must end with -xbr2x.json or -xbr4x.json"
        )
    if target.exists() and not force:
        raise RuntimeError(f"job already exists; use --force to replace exactly {target}")

    template = load_job(resolve_path(template_file))
    contract = creation_upscale_contract(template, requested_scale)
    job_suffix = f"-xbr{contract.scale}x"
    if not job_id.endswith(job_suffix):
        raise RuntimeError(
            f"Character equipment job filename must end with {job_suffix}.json for the template"
        )
    game_root = job_path(template, "game_root")
    exe = game_root / "BaldurReal.exe"
    expected_exe = template["compatibility"]["baldur_real_sha256"].upper()
    if not exe.is_file() or sha256_file(exe) != expected_exe:
        raise RuntimeError("template job does not match the installed BaldurReal.exe")
    index = KeyIndex(game_root)
    resolved_animation_id = animation_id_for_symbol(index, ids_symbol_text)
    if animation_id_text is not None and int(animation_id_text, 16) != resolved_animation_id:
        raise RuntimeError(
            f"animation identity mismatch: {ids_symbol_text.upper()} resolves to "
            f"0x{resolved_animation_id:04X}, not {animation_id_text}"
        )
    resolved_animation_id_text = f"0x{resolved_animation_id:04X}"
    provisional = {
        "animation": {
            "id": resolved_animation_id_text,
            "runtime_profile": "character-bg2ee-2.7.3.0",
            "layer": {"kind": layer_kind, "item_resref": item_resref},
        }
    }
    require_clean_character_identity_overrides(provisional, game_root)
    spec = character_equipment_spec(index, resolved_animation_id, layer_kind, item_resref)

    asset_id = job_id[: -len(job_suffix)]
    paths = dict(template["paths"])
    if workspace is None:
        paths["source_dir"] = f"sprite/{asset_id.replace('-', '_')}/source"
        paths["run_dir"] = (
            f"sprite/{asset_id.replace('-', '_')}/runs/"
            f"xbr{contract.scale}x-x{contract.scale}"
        )
    else:
        paths.update(
            character_workspace_paths(
                workspace, job_id, contract.scale, resolved_animation_id_text
            )
        )
    runtime = dict(template.get("runtime", {}))
    runtime.setdefault("no_filter_comparison", True)
    job: dict[str, Any] = {
        "schema": JOB_SCHEMA,
        "job_id": job_id,
        "animation": {
            "name": display_name
            or f"{spec['ids_symbol'].replace('_', ' ').title()} — {item_resref}",
            "id": spec["animation_id"],
            "ids_symbol": spec["ids_symbol"],
            "layer": {"kind": layer_kind, "item_resref": item_resref},
            "bam_prefix": spec["bam_prefix"],
            "runtime_profile": "character-bg2ee-2.7.3.0",
        },
        "paths": paths,
        "compatibility": dict(template["compatibility"]),
        "runtime": runtime,
        "qa": {
            "areas": [value.upper() for value in qa_areas],
            "creatures": [value.upper() for value in qa_creatures],
            "items": [item_resref],
        },
    }
    if isinstance(template.get("tools"), dict):
        job["tools"] = dict(template["tools"])
    if contract.explicit:
        job["upscale"] = contract.method
    write_json(target, job)
    loaded = load_job(target)
    verified = verify_character_animation_identity(loaded, KeyIndex(game_root))
    return {
        "status": "character-equipment-job-created",
        "job_file": relative_project_path(target),
        "job_id": job_id,
        "animation_identity": verified,
        "source_dir": paths["source_dir"],
        "run_dir": paths["run_dir"],
        "next": f"python pipeline/scripts/run_creature_sprite_x2.py plan --job {relative_project_path(target)}",
    }


def promote_armor_set_job(
    destination: Path,
    template_file: Path | None,
    requested_scale: int | None,
    force: bool,
) -> dict[str, Any]:
    """Create an explicit x2 aggregate job over existing legacy x2 members.

    This operation only writes a new job description.  Member builds and their
    palette-index payloads are reused; the later aggregate build rewrites V3
    headers and shards without dispatching Scalepix.
    """

    if template_file is None:
        raise RuntimeError("promote-armor-set-job requires --template-job")
    if requested_scale != 2:
        raise RuntimeError("promote-armor-set-job requires --scale 2")
    target = resolve_path(destination)
    jobs_root = (PROJECT_ROOT / "sprite" / "jobs").resolve()
    if target.parent != jobs_root or target.suffix.lower() != ".json":
        raise RuntimeError(f"promoted armor-set job must be sprite/jobs/<job>.json: {target}")
    job_id = target.stem
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("destination filename must be a valid lowercase job id")
    if target.exists() and not force:
        raise RuntimeError(f"job already exists; use --force to replace exactly {target}")

    template_path = resolve_path(template_file)
    template = load_armor_set(template_path)
    if upscale_contract(template).explicit:
        raise RuntimeError("promote-armor-set-job requires a legacy armor-set template")
    if target == template_path:
        raise RuntimeError("promoted armor-set job must not overwrite its legacy template")

    promoted = json.loads(json.dumps(read_json(template_path)))
    promoted["job_id"] = job_id
    promoted["upscale"] = direct_upscale_contract(2).method
    promoted_paths = dict(promoted["paths"])
    promoted_paths["run_dir"] = (
        f"sprite/{job_id.replace('-', '_')}/runs/xbr2x-x2-xn"
    )
    promoted["paths"] = promoted_paths
    descriptor, validation_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    os.close(descriptor)
    validation_path = Path(validation_name)
    try:
        write_json(validation_path, promoted)
        loaded = load_armor_set(validation_path)
        os.replace(validation_path, target)
    finally:
        validation_path.unlink(missing_ok=True)
    return {
        "status": "armor-set-job-promoted",
        "job_file": relative_project_path(target),
        "job_id": loaded["job_id"],
        "run_dir": promoted_paths["run_dir"],
        "member_count": len(loaded["_members"]),
        "source_registry_formats": [
            {
                "registry_magic": registry_magic_name(REGISTRY_MAGIC),
                "registry_version": REGISTRY_VERSION,
                "scale": LEGACY_SCALE,
            }
        ],
        "promoted_to_xn": True,
        "xbr_dispatched": False,
        "next": (
            "python pipeline/scripts/run_creature_sprite_x2.py build --resume --job "
            f"{relative_project_path(target)}"
        ),
    }


def canonical_bam(raw: bytes) -> tuple[bytes, bool]:
    if raw[:4] == b"BAMC":
        if len(raw) < 12:
            raise RuntimeError("truncated BAMC")
        data = zlib.decompress(raw[12:])
        packed = True
    else:
        data = raw
        packed = False
    if data[:8] != b"BAM V1  ":
        raise RuntimeError(f"unsupported BAM signature: {data[:8]!r}")
    return data, packed


def bam_cycles(data: bytes) -> list[dict[str, Any]]:
    frame_count, cycle_count = struct.unpack_from("<HB", data, 8)
    frame_offset, _, lookup_offset = struct.unpack_from("<III", data, 0x0C)
    cycle_offset = frame_offset + frame_count * 12
    result = []
    for cycle_index in range(cycle_count):
        count, first = struct.unpack_from("<HH", data, cycle_offset + cycle_index * 4)
        values = list(struct.unpack_from(f"<{count}H", data, lookup_offset + first * 2)) if count else []
        result.append({"index": cycle_index, "lookup_start": first, "frame_indices": values})
    return result


def make_source_sheet(frames: list[Image.Image], destination: Path) -> None:
    positions = sorted(
        {0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1}
    )
    selected = [
        (
            index,
            frames[index].resize(
                (
                    frames[index].width * SOURCE_PREVIEW_SCALE,
                    frames[index].height * SOURCE_PREVIEW_SCALE,
                ),
                Image.Resampling.NEAREST,
            ),
        )
        for index in positions
    ]
    cell_width = max(image.width for _, image in selected) + 16
    cell_height = max(image.height for _, image in selected) + 32
    canvas = Image.new("RGBA", (cell_width * len(selected), cell_height), (40, 40, 40, 255))
    draw = ImageDraw.Draw(canvas)
    for column, (index, image) in enumerate(selected):
        x = column * cell_width + (cell_width - image.width) // 2
        y = 22 + (cell_height - 22 - image.height) // 2
        canvas.alpha_composite(image, (x, y))
        draw.text((column * cell_width + 4, 4), f"frame {index:03}", fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def extract_sources(job: dict[str, Any], force: bool, resume: bool) -> dict[str, Any]:
    destination = job_path(job, "source_dir")
    manifest_path = destination / "manifest.json"
    if manifest_path.is_file() and resume:
        return verify_sources(job, compare_game=True)
    if destination.exists() and not force:
        raise RuntimeError(f"source_dir already exists; use --resume or --force: {destination}")
    assert_workspace_child(destination, "source_dir")
    game_root = job_path(job, "game_root")
    require_clean_character_identity_overrides(job, game_root)
    index = KeyIndex(game_root)
    animation_identity = verify_character_animation_identity(job, index)
    prefix = job["animation"]["bam_prefix"]
    bam_map = index.resource_map(BAM_TYPE)
    if animation_identity is not None:
        resources = [bam_map[name] for name in animation_identity["resources"]]
    else:
        resources = sorted(
            (entry for name, entry in bam_map.items() if name.startswith(prefix)),
            key=lambda item: item[0],
        )
    if not resources:
        raise RuntimeError(f"no BAM resource starts with {prefix}")
    if len(resources) > MAX_RESOURCES:
        raise RuntimeError(f"{len(resources)} resources exceed runtime limit {MAX_RESOURCES}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=destination.name + ".tmp-", dir=destination.parent))
    try:
        report_resources = []
        total_frames = 0
        for entry in resources:
            resref, _, locator = entry
            raw, bif_name = index.resolve(entry)
            data, packed = canonical_bam(raw)
            decoded, palette, transparent = decode_bam(data)
            frame_count, cycle_count = struct.unpack_from("<HB", data, 8)
            if len(decoded) != frame_count or frame_count > MAX_FRAMES_PER_RESOURCE:
                raise RuntimeError(f"{resref}: invalid frame count {len(decoded)}")
            target = temporary / "resources" / resref
            frame_dir = target / "frames"
            frame_dir.mkdir(parents=True)
            source_name = "source.bamc" if packed else "source.bam"
            (target / source_name).write_bytes(raw)
            (target / "source.bam").write_bytes(data)
            images = []
            frame_records = []
            for frame_index, (indices, center_x, center_y, tr) in enumerate(decoded):
                height, width = indices.shape
                rgba = np.dstack(
                    [palette[indices], (indices != tr).astype(np.uint8) * 255]
                ).astype(np.uint8)
                image = Image.fromarray(rgba, "RGBA")
                frame_name = f"frame-{frame_index:04}.png"
                image.save(frame_dir / frame_name)
                images.append(image)
                frame_records.append(
                    {
                        "index": frame_index,
                        "file": f"resources/{resref}/frames/{frame_name}",
                        "width": width,
                        "height": height,
                        "center_x": center_x,
                        "center_y": center_y,
                    }
                )
            make_source_sheet(images, target / "source-samples.png")
            report_resources.append(
                {
                    "name": resref,
                    "source": f"resources/{resref}/{source_name}",
                    "canonical_bam": f"resources/{resref}/source.bam",
                    "source_bif": bif_name.replace("\\", "/"),
                    "locator": f"0x{locator:08X}",
                    "source_sha256": sha256_file(target / source_name),
                    "canonical_bam_sha256": sha256_file(target / "source.bam"),
                    "frame_count": frame_count,
                    "cycle_count": cycle_count,
                    "transparent_palette_index": transparent,
                    "cycles": bam_cycles(data),
                    "frames": frame_records,
                    "source_samples": f"resources/{resref}/source-samples.png",
                }
            )
            total_frames += frame_count
        manifest = {
            "schema": SOURCE_SCHEMA,
            "status": "extracted-native",
            "created_at_utc": utc_now(),
            "job_id": job["job_id"],
            "creature": job["animation"].get("name", job["job_id"]),
            "animation_id": job["animation"]["id"],
            "bam_prefix": prefix,
            "layer": character_layer_config(job)
            if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0"
            else None,
            "runtime_profile": job["animation"].get("runtime_profile"),
            "animation_identity": animation_identity,
            "game_dir": str(game_root),
            "baldur_real_sha256": sha256_file(game_root / "BaldurReal.exe"),
            "bams": report_resources,
            "total_frames": total_frames,
        }
        write_json(temporary / "manifest.json", manifest)
        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)
        return {"source_manifest": str(manifest_path), "resources": len(resources), "frames": total_frames}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_sources(job: dict[str, Any], compare_game: bool) -> dict[str, Any]:
    manifest_path = source_manifest_path(job)
    manifest = read_json(manifest_path)
    if manifest.get("schema") != SOURCE_SCHEMA:
        raise RuntimeError("unsupported source manifest")
    if manifest.get("job_id") != job["job_id"]:
        raise RuntimeError("source manifest job id differs from job")
    if manifest.get("runtime_profile") != job["animation"].get("runtime_profile"):
        raise RuntimeError("source manifest runtime profile differs from job")
    prefix = job["animation"]["bam_prefix"]
    if str(manifest.get("bam_prefix", prefix)).upper() != prefix:
        raise RuntimeError("source manifest BAM prefix differs from job")
    if str(manifest.get("animation_id", job["animation"]["id"])).upper() != job["animation"]["id"].upper():
        raise RuntimeError("source manifest animation id differs from job")
    if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
        if manifest.get("layer", {"kind": "body"}) != character_layer_config(job):
            raise RuntimeError("source manifest Character layer differs from job")
    resources = manifest.get("bams")
    if not isinstance(resources, list) or not resources or len(resources) > MAX_RESOURCES:
        raise RuntimeError("invalid source resource inventory")
    game_map = None
    key_index = None
    animation_identity = None
    if compare_game:
        game_root = job_path(job, "game_root")
        require_clean_character_identity_overrides(job, game_root)
        key_index = KeyIndex(game_root)
        animation_identity = verify_character_animation_identity(job, key_index)
        game_map = key_index.resource_map(BAM_TYPE)
    expected_character_resrefs = None
    if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
        if animation_identity is not None:
            expected_character_resrefs = set(animation_identity["resources"])
        else:
            recorded = manifest.get("animation_identity")
            if isinstance(recorded, dict) and isinstance(recorded.get("resources"), list):
                expected_character_resrefs = {
                    str(value).upper() for value in recorded["resources"]
                }
            elif character_layer_config(job)["kind"] == "body":
                expected_character_resrefs = {
                    f"{prefix}{suffix}" for suffix in CHARACTER_BODY_SUFFIXES
                }
    frame_count = 0
    for resource in resources:
        resref = str(resource["name"]).upper()
        if not resref.startswith(prefix) or len(resref) > 8:
            raise RuntimeError(f"out-of-family resref: {resref}")
        if expected_character_resrefs is not None and resref not in expected_character_resrefs:
            raise RuntimeError(f"out-of-layer Character resref: {resref}")
        source = manifest_path.parent / str(resource["source"])
        canonical = manifest_path.parent / str(resource["canonical_bam"])
        if not source.is_file() or not canonical.is_file():
            raise RuntimeError(f"missing source for {resref}")
        local_raw = source.read_bytes()
        local_bam, _ = canonical_bam(local_raw)
        if local_bam != canonical.read_bytes():
            raise RuntimeError(f"canonical BAM differs from source payload: {resref}")
        decoded, _, _ = decode_bam(local_bam)
        if len(decoded) != int(resource["frame_count"]):
            raise RuntimeError(f"frame count differs for {resref}")
        frame_count += len(decoded)
        if compare_game:
            entry = game_map.get(resref) if game_map else None
            if entry is None:
                raise RuntimeError(f"{resref} absent from installed chitin.key")
            installed, _ = key_index.resolve(entry)  # type: ignore[union-attr]
            if hashlib.sha256(installed).digest() != hashlib.sha256(local_raw).digest():
                raise RuntimeError(f"installed source differs from local extraction: {resref}")
    if int(manifest.get("total_frames", frame_count)) != frame_count:
        raise RuntimeError("source total_frames differs from decoded inventory")
    if expected_character_resrefs is not None and {
        str(resource["name"]).upper() for resource in resources
    } != expected_character_resrefs:
        raise RuntimeError("source Character layer inventory is incomplete")
    recorded_identity = manifest.get("animation_identity")
    if animation_identity is not None and isinstance(recorded_identity, dict):
        identity_keys = [
            "animation_id",
            "ids_symbol",
            "animate_ids_sha256",
            "ini_sha256",
            "bam_prefix",
            "armor_code",
        ]
        if character_layer_config(job)["kind"] != "body":
            identity_keys.extend(
                (
                    "layer_kind",
                    "item_resref",
                    "item_sha256",
                    "item_animation_code",
                    "equipment_height_code",
                    "resources",
                )
            )
        for key in identity_keys:
            if recorded_identity.get(key) != animation_identity.get(key):
                raise RuntimeError(f"source animation identity differs from installed game: {key}")
    result = {
        "source_manifest": str(manifest_path),
        "resources": len(resources),
        "frames": frame_count,
        "game_match": compare_game,
    }
    if animation_identity is not None:
        result["animation_identity"] = animation_identity
    return result


def load_source_frames(manifest_path: Path) -> tuple[list[SourceFrame], list[dict[str, Any]], dict[str, Any]]:
    manifest = read_json(manifest_path)
    all_frames: list[SourceFrame] = []
    resources: list[dict[str, Any]] = []
    for resource in manifest["bams"]:
        resref = str(resource["name"]).upper()
        bam_path = manifest_path.parent / str(resource["canonical_bam"])
        source_path = manifest_path.parent / str(resource["source"])
        data = bam_path.read_bytes()
        decoded, palette, transparent = decode_bam(data)
        metadata = resource.get("frames") or []
        if metadata and len(metadata) != len(decoded):
            raise RuntimeError(f"{resref}: metadata count mismatch")
        frame_records = []
        for frame_index, (indices, center_x, center_y, tr) in enumerate(decoded):
            height, width = indices.shape
            if width * height > 65535:
                raise RuntimeError(f"{resref} frame {frame_index}: frame too large")
            if metadata:
                expected = metadata[frame_index]
                geometry = (int(expected["index"]), int(expected["width"]), int(expected["height"]), int(expected["center_x"]), int(expected["center_y"]))
                actual = (frame_index, width, height, center_x, center_y)
                if actual != geometry:
                    raise RuntimeError(f"{resref} frame {frame_index}: geometry mismatch")
            rgba = np.empty((height, width, 4), dtype=np.uint8)
            rgba[:, :, :3] = palette[indices]
            rgba[:, :, 3] = np.where(indices == tr, 0, 255).astype(np.uint8)
            frame = SourceFrame(resref, frame_index, width, height, center_x, center_y, tr, indices, palette, rgba.tobytes())
            all_frames.append(frame)
            frame_records.append(frame)
        cycles = resource.get("cycles") or bam_cycles(data)
        resources.append({"source": resource, "bam_path": bam_path, "source_path": source_path, "frames": frame_records, "cycles": cycles})
    return all_frames, resources, manifest


def run_xbr(
    frames: list[SourceFrame],
    scalepix: Path,
    node: str,
    contract: UpscaleContract,
) -> list[tuple[int, int, bytes]]:
    if not scalepix.is_file() or not XBR_ADAPTER.is_file():
        raise RuntimeError("scalepix or xBR batch adapter is missing")
    if contract.explicit:
        payload = bytearray(b"XBRNBAT\0")
        payload.extend(struct.pack("<II", contract.scale, len(frames)))
        command = [
            node,
            str(XBR_ADAPTER),
            str(scalepix),
            contract.adapter_mode,
        ]
        expected_magic = b"XBRNOUT\0"
        output_header_bytes = 16
    else:
        # Preserve the original adapter protocol and command line for jobs that
        # predate the explicit xN contract.
        payload = bytearray(b"XBR2BAT\0")
        payload.extend(struct.pack("<I", len(frames)))
        command = [node, str(XBR_ADAPTER), str(scalepix)]
        expected_magic = b"XBR2OUT\0"
        output_header_bytes = 12
    for frame in frames:
        payload.extend(struct.pack("<III", frame.width, frame.height, len(frame.rgba)))
        payload.extend(frame.rgba)
    result = subprocess.run(
        command,
        input=bytes(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"xBR{contract.scale}x batch failed:\n"
            + result.stderr.decode("utf-8", errors="replace")
        )
    raw = result.stdout
    if len(raw) < output_header_bytes or raw[:8] != expected_magic:
        raise RuntimeError(f"invalid xBR{contract.scale}x batch output")
    if contract.explicit:
        output_scale, count = struct.unpack_from("<II", raw, 8)
        if output_scale != contract.scale:
            raise RuntimeError("xBR batch output scale differs from the job contract")
    else:
        count = struct.unpack_from("<I", raw, 8)[0]
    if count != len(frames):
        raise RuntimeError(
            f"xBR{contract.scale}x returned {count} frames, expected {len(frames)}"
        )
    outputs = []
    offset = output_header_bytes
    for frame_index in range(count):
        if offset + 12 > len(raw):
            raise RuntimeError(f"truncated xBR{contract.scale}x output")
        width, height, byte_count = struct.unpack_from("<III", raw, offset)
        offset += 12
        if byte_count != width * height * 4 or offset + byte_count > len(raw):
            raise RuntimeError(f"invalid xBR{contract.scale}x output frame {frame_index}")
        outputs.append((width, height, raw[offset : offset + byte_count]))
        offset += byte_count
    if offset != len(raw):
        raise RuntimeError(f"trailing xBR{contract.scale}x output bytes")
    return outputs


def run_xbr2x(
    frames: list[SourceFrame], scalepix: Path, node: str
) -> list[tuple[int, int, bytes]]:
    return run_xbr(frames, scalepix, node, LEGACY_UPSCALE)


def projected_xbr_output_bytes(frame: SourceFrame, scale: int) -> int:
    index_bytes = int(frame.width) * int(frame.height) * scale * scale
    if index_bytes <= 0 or index_bytes > MAX_LAZY_FRAME_INDEX_BYTES:
        raise RuntimeError(
            f"{frame.resref} frame {frame.index}: projected xBR payload exceeds "
            "the lazy frame-index cache limit"
        )
    return index_bytes * 4


def xbr_output_batch_ranges(
    frames: list[SourceFrame],
    scale: int,
    output_budget_bytes: int = XBR_OUTPUT_BATCH_BUDGET_BYTES,
) -> list[tuple[int, int, int]]:
    """Return deterministic [start, end) batches in canonical frame order.

    A frame larger than the dispatch budget is kept as a singleton. Its
    palette-index payload must still fit ``MAX_LAZY_FRAME_INDEX_BYTES``.
    """

    if not frames:
        raise RuntimeError("xBR batching requires at least one frame")
    if isinstance(output_budget_bytes, bool) or not isinstance(
        output_budget_bytes, int
    ) or output_budget_bytes <= 0:
        raise RuntimeError("xBR output batch budget must be a positive integer")
    ranges: list[tuple[int, int, int]] = []
    start = 0
    current_bytes = 0
    for index, frame in enumerate(frames):
        frame_bytes = projected_xbr_output_bytes(frame, scale)
        if index > start and current_bytes + frame_bytes > output_budget_bytes:
            ranges.append((start, index, current_bytes))
            start = index
            current_bytes = 0
        current_bytes += frame_bytes
    ranges.append((start, len(frames), current_bytes))
    return ranges


def has_duplicate_used_rgba_indices(frame: SourceFrame) -> bool:
    """Return whether a frame needs index provenance after RGBA xBR.

    BAM V1 stores palette indices while xBR receives RGBA pixels.  Distinct
    indices may legitimately have the same RGBA in the source palette, and
    those indices must remain distinct so later engine recolors still address
    their original palette entries.
    """

    seen: set[int] = set()
    for raw_index in np.unique(frame.indices).tolist():
        palette_index = int(raw_index)
        packed = (
            int(frame.palette[palette_index, 0])
            | (int(frame.palette[palette_index, 1]) << 8)
            | (int(frame.palette[palette_index, 2]) << 16)
            | (0 if palette_index == frame.transparent else 255) << 24
        )
        if packed in seen:
            return True
        seen.add(packed)
    return False


def xbr_provenance_indices(frame: SourceFrame, scale: int) -> np.ndarray:
    """Reproduce xBR source selection as palette-index provenance.

    ``xbr2x_batch.js`` uses the upstream xBR implementation with blending
    disabled.  Every output pixel is therefore an unblended source pixel
    selected by the xBR edge tests.  This routine performs those tests over
    the original RGBA values, but writes the selected source *palette index*.
    It is used only when RGBA alone is not injective over the used indices.

    The rendered RGBA is still produced by Scalepix.  ``map_output`` verifies
    the provenance against that output before a registry record is written,
    so a future adapter change fails closed instead of silently changing an
    index choice.  The xBR font inversion is channel-wise and preserves every
    comparison made below; the final RGBA verification covers it as well.
    """

    if scale not in {2, 4}:
        raise RuntimeError("palette-index provenance supports only x2 or x4")
    source_colors = np.frombuffer(frame.rgba, dtype="<u4")
    if source_colors.size != frame.width * frame.height:
        raise RuntimeError(f"{frame.resref} frame {frame.index}: invalid RGBA source")
    source_colors = source_colors.reshape(frame.height, frame.width)
    source_indices = np.asarray(frame.indices, dtype=np.uint8)
    if source_indices.shape != (frame.height, frame.width):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: invalid index source")

    def yuv(value: int) -> tuple[float, float, float]:
        red, green, blue = value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF
        return (
            red * 0.299 + green * 0.587 + blue * 0.114,
            red * -0.168736 + green * -0.331264 + blue * 0.5,
            red * 0.5 + green * -0.418688 + blue * -0.081312,
        )

    def difference(left: int, right: int) -> float:
        alpha_left = (left >> 24) & 0xFF
        alpha_right = (right >> 24) & 0xFF
        if alpha_left == 0 and alpha_right == 0:
            return 0.0
        if alpha_left == 0 or alpha_right == 0:
            return 1_000_000.0
        y_left, u_left, v_left = yuv(left)
        y_right, u_right, v_right = yuv(right)
        return (
            abs(y_left - y_right) * 48
            + abs(u_left - u_right) * 7
            + abs(v_left - v_right) * 6
        )

    def equal(left: int, right: int) -> bool:
        alpha_left = (left >> 24) & 0xFF
        alpha_right = (right >> 24) & 0xFF
        if alpha_left == 0 and alpha_right == 0:
            return True
        if alpha_left == 0 or alpha_right == 0:
            return False
        y_left, u_left, v_left = yuv(left)
        y_right, u_right, v_right = yuv(right)
        return (
            abs(y_left - y_right) <= 48
            and abs(u_left - u_right) <= 7
            and abs(v_left - v_right) <= 6
        )

    def related_points(x: int, y: int) -> tuple[list[int], list[int]]:
        xm1, xm2 = max(0, x - 1), max(0, x - 2)
        xp1, xp2 = min(frame.width - 1, x + 1), min(frame.width - 1, x + 2)
        ym1, ym2 = max(0, y - 1), max(0, y - 2)
        yp1, yp2 = min(frame.height - 1, y + 1), min(frame.height - 1, y + 2)
        coordinates = (
            (xm1, ym2), (x, ym2), (xp1, ym2),
            (xm2, ym1), (xm1, ym1), (x, ym1), (xp1, ym1), (xp2, ym1),
            (xm2, y), (xm1, y), (x, y), (xp1, y), (xp2, y),
            (xm2, yp1), (xm1, yp1), (x, yp1), (xp1, yp1), (xp2, yp1),
            (xm1, yp2), (x, yp2), (xp1, yp2),
        )
        return (
            [int(source_colors[row, column]) for column, row in coordinates],
            [int(source_indices[row, column]) for column, row in coordinates],
        )

    def kernel_2x(colors: list[int], labels: list[int], n1: int, n2: int, n3: int) -> tuple[int, int, int]:
        pe, pi, ph, pf, pg, pc, pd, pb, f4, i4, h5, i5 = colors
        _pe_label, _pi_label, ph_label, pf_label, _pg_label, _pc_label, _pd_label, _pb_label, _f4_label, _i4_label, _h5_label, _i5_label = labels
        if pe == ph or pe == pf:
            return n1, n2, n3
        edge = (
            difference(pe, pc) + difference(pe, pg) + difference(pi, h5)
            + difference(pi, f4) + (int(difference(ph, pf)) << 2)
        )
        inverse = (
            difference(ph, pd) + difference(ph, i5) + difference(pf, i4)
            + difference(pf, pb) + (int(difference(pe, pi)) << 2)
        )
        pixel_label = pf_label if difference(pe, pf) <= difference(pe, ph) else ph_label
        if edge < inverse and (
            (not equal(pf, pb) and not equal(ph, pd))
            or (equal(pe, pi) and (not equal(pf, i4) and not equal(ph, i5)))
            or equal(pe, pg)
            or equal(pe, pc)
        ):
            edge_left = difference(pf, pg)
            edge_up = difference(ph, pc)
            distinct_up = pe != pc and pb != pc
            distinct_left = pe != pg and pd != pg
            if ((int(edge_left) << 1) <= edge_up and distinct_left) or (
                edge_left >= (int(edge_up) << 1) and distinct_up
            ):
                if (int(edge_left) << 1) <= edge_up and distinct_left:
                    n3 = pixel_label
                if edge_left >= (int(edge_up) << 1) and distinct_up:
                    n3 = pixel_label
        return n1, n2, n3

    def kernel_4x(
        colors: list[int], labels: list[int], n15: int, n14: int, n11: int,
        n3: int, n7: int, n10: int, n13: int, n12: int,
    ) -> tuple[int, int, int, int, int, int, int, int]:
        pe, pi, ph, pf, pg, pc, pd, pb, f4, i4, h5, i5 = colors
        _pe_label, _pi_label, ph_label, pf_label, _pg_label, _pc_label, _pd_label, _pb_label, _f4_label, _i4_label, _h5_label, _i5_label = labels
        if pe == ph or pe == pf:
            return n15, n14, n11, n3, n7, n10, n13, n12
        edge = (
            difference(pe, pc) + difference(pe, pg) + difference(pi, h5)
            + difference(pi, f4) + (int(difference(ph, pf)) << 2)
        )
        inverse = (
            difference(ph, pd) + difference(ph, i5) + difference(pf, i4)
            + difference(pf, pb) + (int(difference(pe, pi)) << 2)
        )
        pixel_label = pf_label if difference(pe, pf) <= difference(pe, ph) else ph_label
        if edge < inverse and (
            (not equal(pf, pb) and not equal(ph, pd))
            or (equal(pe, pi) and (not equal(pf, i4) and not equal(ph, i5)))
            or equal(pe, pg)
            or equal(pe, pc)
        ):
            edge_left = difference(pf, pg)
            edge_up = difference(ph, pc)
            distinct_up = pe != pc and pb != pc
            distinct_left = pe != pg and pd != pg
            left = (int(edge_left) << 1) <= edge_up and distinct_left
            up = edge_left >= (int(edge_up) << 1) and distinct_up
            if left or up:
                if left:
                    n15 = n14 = n11 = n13 = pixel_label
                if up:
                    n15 = n14 = n11 = n7 = pixel_label
            else:
                n15 = pixel_label
        return n15, n14, n11, n3, n7, n10, n13, n12

    output = np.empty((frame.height * scale, frame.width * scale), dtype=np.uint8)
    rotations = (
        (10, 16, 15, 11, 14, 6, 9, 5, 12, 17, 19, 20),
        (10, 6, 11, 5, 16, 4, 15, 9, 1, 2, 12, 7),
        (10, 4, 5, 9, 6, 14, 11, 15, 8, 3, 1, 0),
        (10, 14, 9, 15, 4, 16, 5, 11, 19, 18, 8, 13),
    )
    for x in range(frame.width):
        for y in range(frame.height):
            colors, labels = related_points(x, y)
            pe_label = labels[10]
            if scale == 2:
                e0 = e1 = e2 = e3 = pe_label
                e1, e2, e3 = kernel_2x(
                    [colors[index] for index in rotations[0]],
                    [labels[index] for index in rotations[0]], e1, e2, e3,
                )
                e0, e3, e1 = kernel_2x(
                    [colors[index] for index in rotations[1]],
                    [labels[index] for index in rotations[1]], e0, e3, e1,
                )
                e2, e1, e0 = kernel_2x(
                    [colors[index] for index in rotations[2]],
                    [labels[index] for index in rotations[2]], e2, e1, e0,
                )
                e3, e0, e2 = kernel_2x(
                    [colors[index] for index in rotations[3]],
                    [labels[index] for index in rotations[3]], e3, e0, e2,
                )
                output[y * 2, x * 2 : x * 2 + 2] = (e0, e1)
                output[y * 2 + 1, x * 2 : x * 2 + 2] = (e2, e3)
            else:
                e = [pe_label] * 16
                e[15], e[14], e[11], e[3], e[7], e[10], e[13], e[12] = kernel_4x(
                    [colors[index] for index in rotations[0]],
                    [labels[index] for index in rotations[0]],
                    e[15], e[14], e[11], e[3], e[7], e[10], e[13], e[12],
                )
                for order, targets in (
                    (rotations[1], (3, 7, 2, 0, 1, 6, 11, 15)),
                    (rotations[2], (0, 1, 4, 12, 8, 5, 2, 3)),
                    (rotations[3], (12, 8, 13, 15, 14, 9, 4, 0)),
                ):
                    values = kernel_4x(
                        [colors[index] for index in order], [labels[index] for index in order],
                        *(e[index] for index in targets),
                    )
                    for target, value in zip(targets, values, strict=True):
                        e[target] = value
                output[y * 4 : y * 4 + 4, x * 4 : x * 4 + 4] = np.asarray(e, dtype=np.uint8).reshape(4, 4)
    return output.reshape(-1)


def map_output(
    frame: SourceFrame,
    output_rgba: bytes,
    provenance_indices: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    source_flat = frame.indices.reshape(-1)
    representatives = np.full(256, 0xFFFF, dtype=np.uint16)
    for offset, value in enumerate(source_flat.tolist()):
        if representatives[value] == 0xFFFF:
            representatives[value] = offset
    color_to_index: dict[int, int] = {}
    for value in np.unique(source_flat).tolist():
        rgba = bytes([int(frame.palette[value, 0]), int(frame.palette[value, 1]), int(frame.palette[value, 2]), 0 if value == frame.transparent else 255])
        packed = int.from_bytes(rgba, "little")
        previous = color_to_index.get(packed)
        if previous is not None and previous != value and provenance_indices is None:
            raise RuntimeError(f"{frame.resref} frame {frame.index}: duplicate used RGBA indices {previous}/{value}")
        color_to_index[packed] = value
    pixels = np.frombuffer(output_rgba, dtype=np.uint8).reshape(-1, 4)
    if not np.all((pixels[:, 3] == 0) | (pixels[:, 3] == 255)):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: partial alpha")
    if provenance_indices is not None:
        mapped = np.asarray(provenance_indices, dtype=np.uint8).reshape(-1)
        if mapped.size != len(pixels):
            raise RuntimeError(
                f"{frame.resref} frame {frame.index}: provenance dimensions differ from xBR output"
            )
        if np.any(representatives[mapped] == 0xFFFF):
            raise RuntimeError(f"{frame.resref} frame {frame.index}: missing palette representative")
        expected = np.empty_like(pixels)
        expected[:, :3] = frame.palette[mapped]
        expected[:, 3] = np.where(mapped == frame.transparent, 0, 255)
        if not np.array_equal(expected, pixels):
            raise RuntimeError(
                f"{frame.resref} frame {frame.index}: palette-index provenance differs from xBR output"
            )
        return mapped, representatives
    packed_pixels = pixels.copy().view("<u4").reshape(-1)
    unique_colors, inverse = np.unique(packed_pixels, return_inverse=True)
    mapped_unique = np.empty(len(unique_colors), dtype=np.uint8)
    for unique_index, color in enumerate(unique_colors.tolist()):
        palette_index = color_to_index.get(int(color))
        if palette_index is None:
            raise RuntimeError(
                f"{frame.resref} frame {frame.index}: xBR introduced "
                f"{int(color).to_bytes(4, 'little').hex()}"
            )
        mapped_unique[unique_index] = palette_index
    mapped = mapped_unique[inverse]
    if np.any(representatives[mapped] == 0xFFFF):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: missing palette representative")
    return mapped, representatives


def comparison_sample_positions(frame_count: int) -> list[int]:
    if frame_count <= 0:
        raise RuntimeError("comparison sheet requires at least one frame")
    return sorted(
        {
            0,
            frame_count // 4,
            frame_count // 2,
            3 * frame_count // 4,
            frame_count - 1,
        }
    )


def make_comparison_sheet_samples(
    frames: list[SourceFrame],
    outputs: dict[int, tuple[int, int, bytes]],
    destination: Path,
    contract: UpscaleContract = LEGACY_UPSCALE,
) -> None:
    positions = comparison_sample_positions(len(frames))
    if sorted(outputs) != positions:
        raise RuntimeError("comparison sheet samples are incomplete or non-canonical")
    pairs = []
    for position in positions:
        frame = frames[position]
        native = Image.frombytes("RGBA", (frame.width, frame.height), frame.rgba).resize(
            (frame.width * contract.scale, frame.height * contract.scale),
            Image.Resampling.NEAREST,
        )
        width, height, rgba = outputs[position]
        pairs.append((position, native, Image.frombytes("RGBA", (width, height), rgba)))
    cell_width = max(max(native.width, xbr.width) for _, native, xbr in pairs) + 16
    row_height = max(max(native.height, xbr.height) for _, native, xbr in pairs) + 28
    canvas = Image.new("RGBA", (cell_width * 2, row_height * len(pairs) + 20), (40, 40, 40, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((4, 3), f"NATIF x{contract.scale} NEAREST", fill="white")
    draw.text((cell_width + 4, 3), f"xBR{contract.scale}x", fill="white")
    for row, (index, native, xbr) in enumerate(pairs):
        top = 20 + row * row_height
        for column, image in enumerate((native, xbr)):
            x = column * cell_width + (cell_width - image.width) // 2
            y = top + 20 + (row_height - 20 - image.height) // 2
            canvas.alpha_composite(image, (x, y))
        draw.text((4, top + 2), f"frame {index:03}", fill="white")
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def make_comparison_sheet(
    frames: list[SourceFrame],
    outputs: list[tuple[int, int, bytes]],
    destination: Path,
    contract: UpscaleContract = LEGACY_UPSCALE,
) -> None:
    if len(outputs) != len(frames):
        raise RuntimeError("comparison sheet output count differs from source frames")
    make_comparison_sheet_samples(
        frames,
        {
            position: outputs[position]
            for position in comparison_sample_positions(len(frames))
        },
        destination,
        contract,
    )


def preflight_registry_layout(
    resources: list[dict[str, Any]],
    scale: int,
    maximum_bytes: int | None = None,
) -> dict[str, Any]:
    if scale not in {2, 4}:
        raise RuntimeError("registry preflight scale must be 2 or 4")
    if maximum_bytes is None:
        maximum_bytes = maximum_registry_bytes(scale)
    if not resources or len(resources) > MAX_RESOURCES:
        raise RuntimeError("invalid source inventory")
    registry_bytes = REGISTRY_HEADER_BYTES
    index_bytes = 0
    frame_count = 0
    seen_resrefs: set[str] = set()
    resource_records: list[dict[str, Any]] = []
    for resource in resources:
        resource_start = registry_bytes
        source = resource.get("source") or {}
        resref = str(source.get("name", "")).upper()
        if resref:
            if not re.fullmatch(r"[A-Z0-9_]{1,8}", resref) or resref in seen_resrefs:
                raise RuntimeError("invalid or duplicate resref in registry preflight")
            seen_resrefs.add(resref)
        frames = resource.get("frames") or []
        cycles = resource.get("cycles") or []
        if (
            not frames
            or len(frames) > MAX_FRAMES_PER_RESOURCE
            or not cycles
            or len(cycles) > MAX_CYCLES_PER_RESOURCE
        ):
            raise RuntimeError("invalid source inventory for registry preflight")
        registry_bytes += REGISTRY_RESOURCE_HEADER_BYTES
        for frame in frames:
            if not (1 <= int(frame.width) <= 4096 and 1 <= int(frame.height) <= 4096):
                raise RuntimeError("invalid frame dimensions in registry preflight")
            payload_bytes = int(frame.width) * int(frame.height) * scale * scale
            if payload_bytes <= 0 or payload_bytes > MAX_LAZY_FRAME_INDEX_BYTES:
                raise RuntimeError("frame payload exceeds registry record capacity")
            registry_bytes += REGISTRY_FRAME_HEADER_BYTES + payload_bytes
            index_bytes += payload_bytes
            frame_count += 1
        for cycle in cycles:
            slots = cycle.get("frame_indices") or []
            # BAM V1 permits empty cycles; preserve them verbatim instead of
            # silently normalizing a native sequence table.
            if len(slots) > MAX_CYCLE_SLOTS:
                raise RuntimeError("invalid cycle slot count in registry preflight")
            if any(int(value) < 0 or int(value) >= len(frames) for value in slots):
                raise RuntimeError("invalid cycle lookup in registry preflight")
            registry_bytes += 4 + 4 * len(slots)
        resource_records.append(
            {
                "resref": resref,
                "bytes": registry_bytes - resource_start,
                "frame_count": len(frames),
            }
        )
    if registry_bytes > maximum_bytes:
        raise RuntimeError(
            f"registry preflight exceeds {maximum_bytes} bytes before xBR: "
            f"{registry_bytes} bytes at x{scale}"
        )
    return {
        "registry_bytes": registry_bytes,
        "index_bytes": index_bytes,
        "resource_count": len(resources),
        "frame_count": frame_count,
        "resource_records": resource_records,
    }


def registry_magic_name(magic: bytes) -> str:
    return magic.rstrip(b"\0").decode("ascii", errors="strict")


def require_compatible_registry_infos(
    infos: list[dict[str, Any]],
) -> tuple[str, int, int]:
    if not infos:
        raise RuntimeError("registry aggregation requires at least one member")
    identities = {
        (str(info.get("registry_magic", "")), int(info["version"]), int(info["scale"]))
        for info in infos
    }
    if len(identities) != 1:
        raise RuntimeError("registry aggregation refuses mixed magic/version/scale")
    return next(iter(identities))


class WindowsXpressHuffCodec:
    """Bounded wrapper around the Windows Compression API.

    V5 is a Windows-only runtime format. Keeping the native compressor and
    decompressor behind this small wrapper makes all allocation and exact-size
    checks explicit and keeps the binary format independent of Python modules.
    """

    _ALGORITHM_XPRESS_HUFF = 4
    _ERROR_INSUFFICIENT_BUFFER = 122

    def __init__(self, *, compress: bool) -> None:
        if os.name != "nt":
            raise RuntimeError("V5 XPRESS_HUFF registries require Windows")
        import ctypes
        from ctypes import wintypes

        self._ctypes = ctypes
        self._cabinet = ctypes.WinDLL("cabinet", use_last_error=True)
        self._compress = compress
        self._handle = ctypes.c_void_p()
        create_name = "CreateCompressor" if compress else "CreateDecompressor"
        self._create = getattr(self._cabinet, create_name)
        self._create.argtypes = [
            wintypes.DWORD,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._create.restype = wintypes.BOOL
        operation_name = "Compress" if compress else "Decompress"
        self._operation = getattr(self._cabinet, operation_name)
        self._operation.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
        ]
        self._operation.restype = wintypes.BOOL
        close_name = "CloseCompressor" if compress else "CloseDecompressor"
        self._close = getattr(self._cabinet, close_name)
        self._close.argtypes = [ctypes.c_void_p]
        self._close.restype = wintypes.BOOL
        if not self._create(
            self._ALGORITHM_XPRESS_HUFF, None, ctypes.byref(self._handle)
        ):
            raise RuntimeError(
                f"cannot create Windows XPRESS_HUFF codec: {ctypes.get_last_error()}"
            )

    def close(self) -> None:
        if self._handle.value is None:
            return
        handle = self._handle
        self._handle = self._ctypes.c_void_p()
        if not self._close(handle):
            raise RuntimeError(
                "cannot close Windows XPRESS_HUFF codec: "
                f"{self._ctypes.get_last_error()}"
            )

    def __enter__(self) -> "WindowsXpressHuffCodec":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def encode(self, payload: bytes) -> bytes:
        if not self._compress or not payload:
            raise RuntimeError("invalid XPRESS_HUFF compression request")
        ctypes = self._ctypes
        source = ctypes.create_string_buffer(payload)
        required = ctypes.c_size_t()
        if self._operation(
            self._handle,
            source,
            len(payload),
            None,
            0,
            ctypes.byref(required),
        ):
            raise RuntimeError("XPRESS_HUFF size query unexpectedly succeeded")
        if (
            ctypes.get_last_error() != self._ERROR_INSUFFICIENT_BUFFER
            or required.value == 0
        ):
            raise RuntimeError(
                f"XPRESS_HUFF size query failed: {ctypes.get_last_error()}"
            )
        output = ctypes.create_string_buffer(required.value)
        written = ctypes.c_size_t()
        if not self._operation(
            self._handle,
            source,
            len(payload),
            output,
            len(output),
            ctypes.byref(written),
        ):
            raise RuntimeError(
                f"XPRESS_HUFF compression failed: {ctypes.get_last_error()}"
            )
        if not (0 < written.value <= len(output)):
            raise RuntimeError("XPRESS_HUFF returned an invalid compressed size")
        return bytes(output.raw[: written.value])

    def decode(self, payload: bytes, logical_bytes: int) -> bytes:
        if (
            self._compress
            or not payload
            or not (1 <= logical_bytes <= MAX_LAZY_FRAME_INDEX_BYTES)
        ):
            raise RuntimeError("invalid XPRESS_HUFF decompression request")
        ctypes = self._ctypes
        source = ctypes.create_string_buffer(payload)
        output = ctypes.create_string_buffer(logical_bytes)
        written = ctypes.c_size_t()
        if not self._operation(
            self._handle,
            source,
            len(payload),
            output,
            logical_bytes,
            ctypes.byref(written),
        ):
            raise RuntimeError(
                f"XPRESS_HUFF decompression failed: {ctypes.get_last_error()}"
            )
        if written.value != logical_bytes:
            raise RuntimeError("XPRESS_HUFF decompressed size differs")
        return bytes(output.raw[:logical_bytes])


def inspect_registry(
    path: Path, *, include_resource_records: bool = False
) -> dict[str, Any]:
    file_bytes = path.stat().st_size
    if file_bytes < REGISTRY_HEADER_BYTES:
        raise RuntimeError("invalid creature registry header")
    def read_exact(stream: Any, count: int, label: str) -> bytes:
        data = stream.read(count)
        if len(data) != count:
            raise RuntimeError(f"truncated creature registry {label}")
        return data

    with path.open("rb") as stream:
        header = read_exact(stream, REGISTRY_HEADER_BYTES, "header")
        magic = header[:8]
        version, scale, resource_count, metadata = struct.unpack_from(
            "<IIII", header, 8
        )
        legacy_format = magic == REGISTRY_MAGIC and version in (
            LEGACY_REGISTRY_VERSION,
            REGISTRY_VERSION,
        )
        xn_format = magic == XN_REGISTRY_MAGIC and version in {
            XN_REGISTRY_VERSION,
            XN_COMPRESSED_REGISTRY_VERSION,
        }
        compressed_format = (
            magic == XN_REGISTRY_MAGIC
            and version == XN_COMPRESSED_REGISTRY_VERSION
        )
        if (
            not (legacy_format or xn_format)
            or (legacy_format and scale != LEGACY_SCALE)
            or (xn_format and scale not in {2, 4})
            or file_bytes > maximum_registry_bytes(scale)
            or not (1 <= resource_count <= MAX_RESOURCES)
        ):
            raise RuntimeError("unsupported creature registry header")
        if version == LEGACY_REGISTRY_VERSION:
            if metadata != 0:
                raise RuntimeError("invalid legacy creature registry metadata")
            animation_id = 0xE400
        else:
            if (
                metadata == 0
                or metadata > 0xFFFF
                or (
                    compressed_format
                    and metadata != CATALOG_SHARD_ANIMATION_SENTINEL
                )
            ):
                raise RuntimeError("invalid creature registry animation id")
            animation_id = metadata

        resources = []
        seen_resrefs: set[str] = set()
        total_frames = 0
        total_indices = 0
        total_stored_indices = 0
        compressed_frame_count = 0
        raw_frame_count = 0
        resource_records: list[dict[str, Any]] = []
        decoder_context: Any = (
            WindowsXpressHuffCodec(compress=False)
            if compressed_format
            else contextlib.nullcontext(None)
        )
        decoder = decoder_context.__enter__()
        decode_error: BaseException | None = None
        try:
            for _ in range(resource_count):
                resource_offset = stream.tell()
                resource_header = read_exact(stream, 48, "resource")
                resref_bytes = resource_header[:8]
                try:
                    resref = resref_bytes.split(b"\0", 1)[0].decode("ascii")
                except UnicodeDecodeError as error:
                    raise RuntimeError("invalid or duplicate registry resref") from error
                if (
                    not re.fullmatch(r"[A-Z0-9_]{1,8}", resref)
                    or (
                        b"\0" in resref_bytes
                        and resref_bytes[len(resref) :] != b"\0" * (8 - len(resref))
                    )
                    or resref in seen_resrefs
                ):
                    raise RuntimeError("invalid or duplicate registry resref")
                seen_resrefs.add(resref)
                frame_count, cycle_count = struct.unpack_from("<II", resource_header, 40)
                if not (1 <= frame_count <= MAX_FRAMES_PER_RESOURCE) or not (
                    1 <= cycle_count <= MAX_CYCLES_PER_RESOURCE
                ):
                    raise RuntimeError(f"invalid registry counts for {resref}")
                resource_index_bytes = 0
                resource_logical_bytes = REGISTRY_RESOURCE_HEADER_BYTES
                for _ in range(frame_count):
                    frame_header = read_exact(stream, 528, "frame")
                    width, height, _, _, _, stored_bytes = struct.unpack_from(
                        "<HHhhB3xI", frame_header, 0
                    )
                    logical_bytes = width * height * scale * scale
                    codec = frame_header[9]
                    if (
                        width == 0
                        or height == 0
                        or frame_header[10:12] != b"\0\0"
                        or (not compressed_format and codec != REGISTRY_FRAME_CODEC_RAW)
                    ):
                        raise RuntimeError(f"invalid frame header for {resref}")
                    if (
                        logical_bytes <= 0
                        or logical_bytes > MAX_LAZY_FRAME_INDEX_BYTES
                    ):
                        raise RuntimeError(f"invalid x{scale} payload for {resref}")
                    if compressed_format:
                        valid_storage = (
                            codec == REGISTRY_FRAME_CODEC_RAW
                            and stored_bytes == logical_bytes
                        ) or (
                            codec == REGISTRY_FRAME_CODEC_XPRESS_HUFF
                            and 0 < stored_bytes < logical_bytes
                        )
                    else:
                        valid_storage = (
                            codec == REGISTRY_FRAME_CODEC_RAW
                            and stored_bytes == logical_bytes
                        )
                    if not valid_storage:
                        raise RuntimeError(f"invalid x{scale} payload for {resref}")
                    representatives = np.frombuffer(
                        frame_header, dtype="<u2", count=256, offset=16
                    )
                    stored_payload = read_exact(
                        stream, stored_bytes, "frame payload"
                    )
                    if codec == REGISTRY_FRAME_CODEC_XPRESS_HUFF:
                        compressed_frame_count += 1
                        if decoder is None:
                            raise RuntimeError("missing XPRESS_HUFF decoder")
                        indices_payload = decoder.decode(
                            stored_payload, logical_bytes
                        )
                    else:
                        raw_frame_count += 1
                        indices_payload = stored_payload
                    for start in range(0, len(indices_payload), 1024 * 1024):
                        indices = np.frombuffer(
                            indices_payload[start : start + 1024 * 1024],
                            dtype=np.uint8,
                        )
                        if np.any(representatives[indices] == 0xFFFF):
                            raise RuntimeError(f"missing representative in {resref}")
                    total_indices += logical_bytes
                    total_stored_indices += stored_bytes
                    resource_index_bytes += logical_bytes
                    resource_logical_bytes += (
                        REGISTRY_FRAME_HEADER_BYTES + logical_bytes
                    )
                for _ in range(cycle_count):
                    cycle_header = read_exact(stream, 4, "cycle")
                    slots = struct.unpack_from("<I", cycle_header, 0)[0]
                    if slots > MAX_CYCLE_SLOTS:
                        raise RuntimeError(f"invalid cycle slot count in {resref}")
                    remaining_slots = slots
                    while remaining_slots:
                        slot_count = min(16_384, remaining_slots)
                        lookup = read_exact(
                            stream, slot_count * 4, "cycle lookup"
                        )
                        values = np.frombuffer(lookup, dtype="<u4")
                        if np.any(values >= frame_count):
                            raise RuntimeError(f"invalid cycle lookup in {resref}")
                        remaining_slots -= slot_count
                    resource_logical_bytes += 4 + slots * 4
                resource_end = stream.tell()
                if include_resource_records:
                    resource_records.append(
                        {
                            "resref": resref,
                            "path": path,
                            "offset": resource_offset,
                            "bytes": resource_end - resource_offset,
                            "logical_bytes": resource_logical_bytes,
                            "storage_version": version,
                            "scale": scale,
                            "frame_count": frame_count,
                            "index_bytes": resource_index_bytes,
                        }
                    )
                resources.append(resref)
                total_frames += frame_count
        except BaseException as error:
            decode_error = error
            raise
        finally:
            try:
                decoder_context.__exit__(
                    type(decode_error) if decode_error is not None else None,
                    decode_error,
                    decode_error.__traceback__ if decode_error is not None else None,
                )
            except Exception:
                if decode_error is None:
                    raise
        if stream.tell() != file_bytes:
            raise RuntimeError("trailing bytes in creature registry")
    result = {
        "version": version,
        "scale": scale,
        "registry_magic": registry_magic_name(magic),
        "animation_id": f"0x{animation_id:04X}",
        "resources": resources,
        "resource_count": resource_count,
        "frame_count": total_frames,
        "index_bytes": total_indices,
        "stored_index_bytes": total_stored_indices,
        "compressed_frame_count": compressed_frame_count,
        "raw_frame_count": raw_frame_count,
        "index_storage_ratio": total_stored_indices / total_indices,
        "registry_bytes": file_bytes,
        "sha256": sha256_file(path),
    }
    if include_resource_records:
        result["resource_records"] = resource_records
    return result


def partition_registry_resources(
    records: list[dict[str, Any]],
    *,
    maximum_resources: int = MAX_RESOURCES,
    maximum_bytes: int = MAX_REGISTRY_BYTES,
    maximum_shards: int = MAX_REGISTRY_SET_SHARDS,
) -> list[list[dict[str, Any]]]:
    """Greedily partition canonical resource records without splitting one."""

    if not records or len(records) > MAX_REGISTRY_SET_RESOURCES:
        raise RuntimeError("invalid registry-set resource inventory")
    if not (1 <= maximum_resources <= MAX_RESOURCES):
        raise RuntimeError("invalid registry-set resource limit")
    if not (
        REGISTRY_HEADER_BYTES
        < maximum_bytes
        <= max(MAX_REGISTRY_BYTES_BY_SCALE.values())
    ):
        raise RuntimeError("invalid registry-set byte limit")
    if not (1 <= maximum_shards <= MAX_REGISTRY_SET_SHARDS):
        raise RuntimeError("invalid registry-set shard limit")
    seen_resrefs: set[str] = set()
    shards: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_bytes = REGISTRY_HEADER_BYTES
    for record in records:
        resref = str(record.get("resref", ""))
        record_bytes = int(record.get("bytes", 0))
        if (
            not re.fullmatch(r"[A-Z0-9_]{1,8}", resref)
            or resref in seen_resrefs
        ):
            raise RuntimeError("invalid or duplicate registry-set resref")
        if record_bytes <= 0 or REGISTRY_HEADER_BYTES + record_bytes > maximum_bytes:
            raise RuntimeError(f"registry resource {resref} cannot fit in one shard")
        seen_resrefs.add(resref)
        if current and (
            len(current) >= maximum_resources
            or current_bytes + record_bytes > maximum_bytes
        ):
            shards.append(current)
            current = []
            current_bytes = REGISTRY_HEADER_BYTES
        current.append(record)
        current_bytes += record_bytes
    if current:
        shards.append(current)
    if len(shards) > maximum_shards:
        raise RuntimeError(
            f"registry set requires {len(shards)} shards; limit is {maximum_shards}"
        )
    return shards


def _copy_registry_record(output_stream: Any, record: dict[str, Any]) -> None:
    remaining = int(record["bytes"])
    with Path(record["path"]).open("rb") as source_stream:
        source_stream.seek(int(record["offset"]))
        while remaining:
            chunk = source_stream.read(min(1024 * 1024, remaining))
            if not chunk:
                raise RuntimeError(f"truncated source registry record {record['resref']}")
            output_stream.write(chunk)
            remaining -= len(chunk)


def write_registry_records(
    path: Path,
    magic: bytes,
    version: int,
    scale: int,
    animation_id: int,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if (magic, version, scale) not in {
        (REGISTRY_MAGIC, REGISTRY_VERSION, LEGACY_SCALE),
        (XN_REGISTRY_MAGIC, XN_REGISTRY_VERSION, 2),
        (XN_REGISTRY_MAGIC, XN_REGISTRY_VERSION, 4),
    }:
        raise RuntimeError("unsupported output registry identity")
    if not (1 <= len(records) <= MAX_RESOURCES):
        raise RuntimeError("invalid output registry resource count")
    if not (1 <= animation_id <= 0xFFFF):
        raise RuntimeError("invalid output registry animation id")
    projected_bytes = REGISTRY_HEADER_BYTES + sum(int(record["bytes"]) for record in records)
    if projected_bytes > maximum_registry_bytes(scale):
        raise RuntimeError("output registry exceeds shard byte limit")
    with path.open("wb") as output_stream:
        output_stream.write(magic)
        output_stream.write(
            struct.pack("<IIII", version, scale, len(records), animation_id)
        )
        for record in records:
            _copy_registry_record(output_stream, record)
    info = inspect_registry(path)
    if info["registry_bytes"] != projected_bytes:
        raise RuntimeError("output registry size differs from resource projection")
    return info


def write_compressed_catalog_registry_records(
    path: Path,
    scale: int,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Write a catalog-only V5 shard with independently compressed frames."""

    if scale not in {2, 4} or not (1 <= len(records) <= MAX_RESOURCES):
        raise RuntimeError("invalid compressed catalog shard contract")
    logical_projection = REGISTRY_HEADER_BYTES + sum(
        int(record.get("logical_bytes", record["bytes"])) for record in records
    )
    if logical_projection > maximum_registry_bytes(scale):
        raise RuntimeError("compressed catalog shard logical size exceeds limit")
    with WindowsXpressHuffCodec(compress=True) as codec, path.open(
        "wb"
    ) as output_stream:
        output_stream.write(XN_REGISTRY_MAGIC)
        output_stream.write(
            struct.pack(
                "<IIII",
                XN_COMPRESSED_REGISTRY_VERSION,
                scale,
                len(records),
                CATALOG_SHARD_ANIMATION_SENTINEL,
            )
        )
        for record in records:
            record_bytes = int(record["bytes"])
            source_path = Path(record["path"])
            with source_path.open("rb") as source_stream:
                source_stream.seek(int(record["offset"]))
                raw = source_stream.read(record_bytes)
            if len(raw) != record_bytes or record_bytes < REGISTRY_RESOURCE_HEADER_BYTES:
                raise RuntimeError(
                    f"truncated catalog source record: {record['resref']}"
                )
            offset = 0
            resource_header = raw[:REGISTRY_RESOURCE_HEADER_BYTES]
            offset += REGISTRY_RESOURCE_HEADER_BYTES
            resref = resource_header[:8].split(b"\0", 1)[0].decode(
                "ascii", errors="strict"
            )
            if resref != str(record["resref"]):
                raise RuntimeError("catalog source record resref differs")
            frame_count, cycle_count = struct.unpack_from(
                "<II", resource_header, 40
            )
            output_stream.write(resource_header)
            for _ in range(frame_count):
                end_header = offset + REGISTRY_FRAME_HEADER_BYTES
                if end_header > len(raw):
                    raise RuntimeError("truncated catalog source frame header")
                frame_header = bytearray(raw[offset:end_header])
                offset = end_header
                width, height, _, _, _, logical_bytes = struct.unpack_from(
                    "<HHhhB3xI", frame_header, 0
                )
                if (
                    width == 0
                    or height == 0
                    or frame_header[9:12] != b"\0\0\0"
                    or logical_bytes != width * height * scale * scale
                    or logical_bytes > MAX_LAZY_FRAME_INDEX_BYTES
                    or offset + logical_bytes > len(raw)
                ):
                    raise RuntimeError("invalid catalog source frame payload")
                payload = raw[offset : offset + logical_bytes]
                offset += logical_bytes
                compressed = codec.encode(payload)
                if len(compressed) < logical_bytes:
                    frame_header[9] = REGISTRY_FRAME_CODEC_XPRESS_HUFF
                    stored = compressed
                else:
                    frame_header[9] = REGISTRY_FRAME_CODEC_RAW
                    stored = payload
                frame_header[10:12] = b"\0\0"
                struct.pack_into("<I", frame_header, 12, len(stored))
                output_stream.write(frame_header)
                output_stream.write(stored)
            for _ in range(cycle_count):
                if offset + 4 > len(raw):
                    raise RuntimeError("truncated catalog source cycle")
                slots = struct.unpack_from("<I", raw, offset)[0]
                cycle_bytes = 4 + slots * 4
                if slots > MAX_CYCLE_SLOTS or offset + cycle_bytes > len(raw):
                    raise RuntimeError("invalid catalog source cycle")
                output_stream.write(raw[offset : offset + cycle_bytes])
                offset += cycle_bytes
            if offset != len(raw):
                raise RuntimeError("catalog source record has trailing bytes")
    info = inspect_registry(path)
    if (
        info["version"] != XN_COMPRESSED_REGISTRY_VERSION
        or info["scale"] != scale
        or info["animation_id"].upper()
        != f"0X{CATALOG_SHARD_ANIMATION_SENTINEL:04X}"
        or info["resource_count"] != len(records)
        or info["registry_bytes"] > logical_projection
    ):
        raise RuntimeError("compressed catalog shard differs from projection")
    return info


def inspect_registry_set(
    path: Path, *, include_resource_records: bool = False
) -> dict[str, Any]:
    if path.name != XN_REGISTRY_SET_FILENAME:
        raise RuntimeError("registry-set filename must be CreatureSprites-XN.set")
    file_bytes = path.stat().st_size
    if not (
        REGISTRY_SET_HEADER_BYTES + REGISTRY_SET_ENTRY_BYTES
        <= file_bytes
        <= REGISTRY_SET_HEADER_BYTES
        + MAX_REGISTRY_SET_SHARDS * REGISTRY_SET_ENTRY_BYTES
    ):
        raise RuntimeError("invalid creature registry-set header")
    raw = path.read_bytes()
    (
        magic,
        version,
        scale,
        shard_count,
        total_resources,
        animation_id,
        reserved,
        total_frames,
        total_index_bytes,
        total_registry_bytes,
    ) = struct.unpack_from("<8sIIIIIIQQQ", raw, 0)
    expected_bytes = REGISTRY_SET_HEADER_BYTES + shard_count * REGISTRY_SET_ENTRY_BYTES
    if (
        magic != XN_REGISTRY_SET_MAGIC
        or version != XN_REGISTRY_SET_VERSION
        or scale not in {2, 4}
        or not (1 <= shard_count <= MAX_REGISTRY_SET_SHARDS)
        or not (shard_count <= total_resources <= MAX_REGISTRY_SET_RESOURCES)
        or total_resources > shard_count * MAX_RESOURCES
        or not (1 <= total_frames <= MAX_REGISTRY_SET_FRAMES)
        or not (1 <= animation_id <= 0xFFFF)
        or reserved != 0
        or len(raw) != expected_bytes
        or not (1 <= total_index_bytes <= MAX_REGISTRY_SET_BYTES)
        or not (REGISTRY_HEADER_BYTES <= total_registry_bytes <= MAX_REGISTRY_SET_BYTES)
    ):
        raise RuntimeError("unsupported creature registry-set header")

    expected_names = [
        XN_REGISTRY_SHARD_FILENAME.format(index=index)
        for index in range(shard_count)
    ]
    actual_names = sorted(
        candidate.name
        for candidate in path.parent.iterdir()
        if candidate.is_file()
        and re.fullmatch(r"CreatureSprites-XN-[0-9]{4}\.registry", candidate.name)
    )
    if actual_names != expected_names:
        raise RuntimeError("registry-set shard filenames are not contiguous and exact")

    shards: list[dict[str, Any]] = []
    resources: list[str] = []
    resource_records: list[dict[str, Any]] = []
    seen_resrefs: set[str] = set()
    calculated_frames = 0
    calculated_index_bytes = 0
    calculated_registry_bytes = 0
    calculated_resources = 0
    for index, filename in enumerate(expected_names):
        offset = REGISTRY_SET_HEADER_BYTES + index * REGISTRY_SET_ENTRY_BYTES
        (
            expected_sha256,
            expected_crc32,
            expected_resource_count,
            expected_frame_count,
            expected_index_bytes,
            expected_registry_bytes,
        ) = struct.unpack_from("<32sIIQQQ", raw, offset)
        shard_path = path.parent / filename
        info = inspect_registry(
            shard_path,
            include_resource_records=include_resource_records,
        )
        if (
            info["registry_magic"] != registry_magic_name(XN_REGISTRY_MAGIC)
            or info["version"] != XN_REGISTRY_VERSION
            or info["scale"] != scale
            or info["animation_id"].upper() != f"0X{animation_id:04X}"
            or info["resource_count"] != expected_resource_count
            or info["frame_count"] != expected_frame_count
            or info["index_bytes"] != expected_index_bytes
            or info["registry_bytes"] != expected_registry_bytes
            or bytes.fromhex(info["sha256"]) != expected_sha256
            or crc32_file(shard_path) != expected_crc32
        ):
            raise RuntimeError(f"registry-set shard {index:04d} differs from its index entry")
        duplicates = seen_resrefs.intersection(info["resources"])
        if duplicates:
            raise RuntimeError("duplicate resref across registry-set shards")
        seen_resrefs.update(info["resources"])
        resources.extend(info["resources"])
        if include_resource_records:
            resource_records.extend(info["resource_records"])
        calculated_resources += info["resource_count"]
        calculated_frames += info["frame_count"]
        calculated_index_bytes += info["index_bytes"]
        calculated_registry_bytes += info["registry_bytes"]
        shards.append(
            {
                "index": index,
                "registry": filename,
                "sha256": info["sha256"],
                "crc32": expected_crc32,
                "resource_count": info["resource_count"],
                "frame_count": info["frame_count"],
                "index_bytes": info["index_bytes"],
                "registry_bytes": info["registry_bytes"],
            }
        )
    if (
        calculated_resources != total_resources
        or calculated_frames != total_frames
        or calculated_index_bytes != total_index_bytes
        or calculated_registry_bytes != total_registry_bytes
    ):
        raise RuntimeError("registry-set aggregate totals differ from shard entries")
    result = {
        "version": version,
        "scale": scale,
        "registry_magic": registry_magic_name(magic),
        "animation_id": f"0x{animation_id:04X}",
        "resources": resources,
        "resource_count": calculated_resources,
        "frame_count": calculated_frames,
        "index_bytes": calculated_index_bytes,
        "registry_bytes": calculated_registry_bytes,
        "registry_set_bytes": len(raw),
        "sha256": sha256_file(path),
        "shards": shards,
        "total_resources": total_resources,
        "total_frames": total_frames,
        "total_index_bytes": total_index_bytes,
        "total_registry_bytes": total_registry_bytes,
    }
    if include_resource_records:
        result["resource_records"] = resource_records
    return result


def write_registry_set_index(
    path: Path,
    scale: int,
    animation_id: int,
    shard_infos: list[dict[str, Any]],
) -> dict[str, Any]:
    if path.name != XN_REGISTRY_SET_FILENAME:
        raise RuntimeError("registry-set filename must be CreatureSprites-XN.set")
    if scale not in {2, 4} or not (1 <= animation_id <= 0xFFFF):
        raise RuntimeError("invalid registry-set scale or animation id")
    if not (1 <= len(shard_infos) <= MAX_REGISTRY_SET_SHARDS):
        raise RuntimeError("invalid registry-set shard count")
    total_resources = sum(int(info["resource_count"]) for info in shard_infos)
    total_frames = sum(int(info["frame_count"]) for info in shard_infos)
    total_index_bytes = sum(int(info["index_bytes"]) for info in shard_infos)
    total_registry_bytes = sum(int(info["registry_bytes"]) for info in shard_infos)
    if (
        total_resources > MAX_REGISTRY_SET_RESOURCES
        or total_frames > MAX_REGISTRY_SET_FRAMES
        or total_registry_bytes > MAX_REGISTRY_SET_BYTES
    ):
        raise RuntimeError("registry-set aggregate limit exceeded")
    index_bytes = bytearray(
        struct.pack(
            "<8sIIIIIIQQQ",
            XN_REGISTRY_SET_MAGIC,
            XN_REGISTRY_SET_VERSION,
            scale,
            len(shard_infos),
            total_resources,
            animation_id,
            0,
            total_frames,
            total_index_bytes,
            total_registry_bytes,
        )
    )
    for index, info in enumerate(shard_infos):
        shard_path = Path(info["path"])
        expected_name = XN_REGISTRY_SHARD_FILENAME.format(index=index)
        if shard_path.parent != path.parent or shard_path.name != expected_name:
            raise RuntimeError("registry-set shard path is not canonical")
        index_bytes.extend(
            struct.pack(
                "<32sIIQQQ",
                bytes.fromhex(str(info["sha256"])),
                crc32_file(shard_path),
                int(info["resource_count"]),
                int(info["frame_count"]),
                int(info["index_bytes"]),
                int(info["registry_bytes"]),
            )
        )
    path.write_bytes(index_bytes)
    return inspect_registry_set(path)


def inspect_build_payload(
    build_root: Path,
    manifest: dict[str, Any],
    *,
    include_resource_records: bool = False,
) -> dict[str, Any]:
    """Inspect one job build, flattening a registry-set into member records."""

    layout = str(manifest.get("registry_layout", "monolith"))
    if layout == "monolith":
        registry_name = manifest.get("registry")
        if not isinstance(registry_name, str) or not registry_name:
            raise RuntimeError("monolithic build manifest has no registry")
        return inspect_registry(
            build_root / registry_name,
            include_resource_records=include_resource_records,
        )
    if layout != "set":
        raise RuntimeError("unsupported member registry layout")
    registry_set_name = manifest.get("registry_set")
    if not isinstance(registry_set_name, str) or not registry_set_name:
        raise RuntimeError("registry-set build manifest has no set index")
    registry_set = build_root / registry_set_name
    set_info = inspect_registry_set(
        registry_set,
        include_resource_records=include_resource_records,
    )
    info = dict(set_info)
    info["registry_set_magic"] = set_info["registry_magic"]
    info["registry_magic"] = registry_magic_name(XN_REGISTRY_MAGIC)
    info["version"] = XN_REGISTRY_VERSION
    if include_resource_records:
        records = set_info["resource_records"]
        if [str(record["resref"]) for record in records] != set_info["resources"]:
            raise RuntimeError("registry-set resource records differ from its index")
    return info


def catalog_owner_for_profile(profile: str) -> int:
    if profile == "character-bg2ee-2.7.3.0":
        return CATALOG_OWNER_CHARACTER
    if profile == "monster-icewind-bg2ee-2.7.3.0":
        return CATALOG_OWNER_MONSTER_ICEWIND
    raise RuntimeError(f"unsupported catalog runtime profile: {profile!r}")


def catalog_shard_filename(sha256: str) -> str:
    digest = str(sha256).upper()
    if re.fullmatch(r"[0-9A-F]{64}", digest) is None:
        raise RuntimeError("catalog shard SHA-256 is invalid")
    return XN_REGISTRY_CATALOG_SHARD_FILENAME.format(sha256=digest)


def publish_catalog_shard_object(
    catalog: dict[str, Any], scratch: Path, final_path: Path, sha256: str
) -> Path:
    """Publish one immutable shard once and hardlink it into a generation.

    Game installs always copy the generation link; they never hardlink into the
    repository. A hash mismatch in the shared store fails closed and no object
    is ever replaced or garbage-collected by this workflow.
    """

    digest = str(sha256).upper()
    filename = catalog_shard_filename(digest)
    if (
        scratch.name == filename
        or final_path.name != filename
        or final_path.exists()
        or not scratch.is_file()
        or sha256_file(scratch) != digest
    ):
        raise RuntimeError("invalid catalog shard object publication")
    object_dir = catalog_object_store_dir(catalog)
    assert_workspace_child(object_dir, "catalog shard object store")
    object_dir.mkdir(parents=True, exist_ok=True)
    object_path = object_dir / filename
    if object_path.exists():
        if not object_path.is_file() or sha256_file(object_path) != digest:
            raise RuntimeError("catalog shard object store collision")
        scratch.unlink()
    else:
        scratch.replace(object_path)
        if sha256_file(object_path) != digest:
            raise RuntimeError("published catalog shard object differs")
    try:
        os.link(object_path, final_path)
    except OSError as error:
        raise RuntimeError(
            "catalog generations require same-volume hardlink support"
        ) from error
    if (
        not final_path.is_file()
        or not os.path.samefile(object_path, final_path)
        or sha256_file(final_path) != digest
    ):
        raise RuntimeError("catalog generation shard is not the sealed CAS object")
    return object_path


def catalog_component_digest(scale: int, raw_shard_entries: list[bytes]) -> str:
    if scale not in {2, 4} or not raw_shard_entries or any(
        len(entry) != REGISTRY_CATALOG_SHARD_ENTRY_BYTES
        for entry in raw_shard_entries
    ):
        raise RuntimeError("invalid catalog component digest input")
    digest = hashlib.sha256()
    digest.update(CATALOG_COMPONENT_DIGEST_DOMAIN)
    digest.update(struct.pack("<I", scale))
    for entry in raw_shard_entries:
        digest.update(entry)
    return digest.hexdigest().upper()


def catalog_directory_digest(scale: int, raw_directory: bytes) -> str:
    if (
        scale not in {2, 4}
        or not raw_directory
        or len(raw_directory) % REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES != 0
        or len(raw_directory) // REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
        > MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES
    ):
        raise RuntimeError("invalid catalog directory digest input")
    digest = hashlib.sha256()
    digest.update(CATALOG_DIRECTORY_DIGEST_DOMAIN)
    digest.update(struct.pack("<I", scale))
    digest.update(raw_directory)
    return digest.hexdigest().upper()


def catalog_logical_content_digest(
    scale: int,
    animations: list[dict[str, Any]],
    component_source_digests: list[str],
) -> str:
    if (
        scale not in {2, 4}
        or not animations
        or not component_source_digests
        or any(
            re.fullmatch(r"[0-9A-F]{64}", str(value).upper()) is None
            for value in component_source_digests
        )
    ):
        raise RuntimeError("invalid catalog logical content digest input")
    digest = hashlib.sha256()
    digest.update(CATALOG_LOGICAL_CONTENT_DIGEST_DOMAIN)
    digest.update(
        struct.pack("<III", scale, len(animations), len(component_source_digests))
    )
    for value in component_source_digests:
        digest.update(bytes.fromhex(str(value)))
    previous_animation = 0
    for animation in animations:
        animation_id = int(str(animation["animation_id"]), 16)
        owner = int(animation["owner"])
        indices = [int(value) for value in animation["component_indices"]]
        if (
            animation_id <= previous_animation
            or not indices
            or indices != sorted(set(indices))
            or any(index < 0 or index >= len(component_source_digests) for index in indices)
        ):
            raise RuntimeError("invalid catalog logical animation mapping")
        digest.update(struct.pack("<III", animation_id, owner, len(indices)))
        digest.update(struct.pack(f"<{len(indices)}I", *indices))
        previous_animation = animation_id
    return digest.hexdigest().upper()


def catalog_shard_entry_bytes(info: dict[str, Any], path: Path) -> bytes:
    return struct.pack(
        "<32sIIQQQ",
        bytes.fromhex(str(info["sha256"])),
        crc32_file(path),
        int(info["resource_count"]),
        int(info["frame_count"]),
        int(info["index_bytes"]),
        int(info["registry_bytes"]),
    )


def _catalog_index_maximum_bytes() -> int:
    return (
        REGISTRY_CATALOG_HEADER_BYTES
        + MAX_REGISTRY_CATALOG_ANIMATIONS
        * REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES
        + MAX_REGISTRY_CATALOG_MEMBERSHIPS
        * REGISTRY_CATALOG_MEMBERSHIP_BYTES
        + MAX_REGISTRY_CATALOG_COMPONENTS
        * REGISTRY_CATALOG_COMPONENT_ENTRY_BYTES
        + MAX_REGISTRY_CATALOG_SHARDS * REGISTRY_CATALOG_SHARD_ENTRY_BYTES
        + MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES
        * REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
    )


def inspect_registry_catalog(
    path: Path, *, require_exact_shards: bool = True
) -> dict[str, Any]:
    if path.name != XN_REGISTRY_CATALOG_FILENAME:
        raise RuntimeError("catalog filename must be CreatureSprites-XN.catalog")
    file_bytes = path.stat().st_size
    if not (
        REGISTRY_CATALOG_V1_HEADER_BYTES < file_bytes
        <= _catalog_index_maximum_bytes()
    ):
        raise RuntimeError("invalid creature registry catalog size")
    raw = path.read_bytes()
    (
        magic,
        version,
        scale,
        animation_count,
        component_count,
        membership_count,
        shard_count,
        total_resources,
        total_frames,
        total_index_bytes,
        total_registry_bytes,
    ) = struct.unpack_from("<8sIIIIIIQQQQ", raw, 0)
    if version == LEGACY_XN_REGISTRY_CATALOG_VERSION:
        header_bytes = REGISTRY_CATALOG_V1_HEADER_BYTES
        directory_count = 0
        directory_entry_bytes = 0
        directory_sha256 = None
    elif version == XN_REGISTRY_CATALOG_VERSION:
        if len(raw) < REGISTRY_CATALOG_HEADER_BYTES:
            raise RuntimeError("truncated creature registry catalog v2 header")
        directory_count, directory_entry_bytes, directory_digest_bytes = (
            struct.unpack_from("<II32s", raw, REGISTRY_CATALOG_V1_HEADER_BYTES)
        )
        directory_sha256 = directory_digest_bytes.hex().upper()
        header_bytes = REGISTRY_CATALOG_HEADER_BYTES
    else:
        raise RuntimeError("unsupported creature registry catalog version")
    expected_bytes = (
        header_bytes
        + animation_count * REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES
        + membership_count * REGISTRY_CATALOG_MEMBERSHIP_BYTES
        + component_count * REGISTRY_CATALOG_COMPONENT_ENTRY_BYTES
        + shard_count * REGISTRY_CATALOG_SHARD_ENTRY_BYTES
        + directory_count * directory_entry_bytes
    )
    if (
        magic != XN_REGISTRY_CATALOG_MAGIC
        or version
        not in {
            LEGACY_XN_REGISTRY_CATALOG_VERSION,
            XN_REGISTRY_CATALOG_VERSION,
        }
        or scale not in {2, 4}
        or not (1 <= animation_count <= MAX_REGISTRY_CATALOG_ANIMATIONS)
        or not (1 <= component_count <= MAX_REGISTRY_CATALOG_COMPONENTS)
        or not (animation_count <= membership_count <= MAX_REGISTRY_CATALOG_MEMBERSHIPS)
        or not (component_count <= shard_count <= MAX_REGISTRY_CATALOG_SHARDS)
        or not (1 <= total_resources <= MAX_REGISTRY_CATALOG_RESOURCES)
        or not (1 <= total_frames <= MAX_REGISTRY_CATALOG_FRAMES)
        or not (1 <= total_index_bytes <= MAX_REGISTRY_CATALOG_BYTES)
        or not (REGISTRY_HEADER_BYTES <= total_registry_bytes <= MAX_REGISTRY_CATALOG_BYTES)
        or (
            version == LEGACY_XN_REGISTRY_CATALOG_VERSION
            and total_index_bytes > total_registry_bytes
        )
        or len(raw) != expected_bytes
    ):
        raise RuntimeError("unsupported creature registry catalog header")
    if version == XN_REGISTRY_CATALOG_VERSION and (
        not (1 <= directory_count <= MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES)
        or directory_entry_bytes != REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
        or directory_sha256 == "0" * 64
    ):
        raise RuntimeError("unsupported creature registry catalog v2 directory header")

    animation_offset = header_bytes
    membership_offset = (
        animation_offset
        + animation_count * REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES
    )
    component_offset = (
        membership_offset
        + membership_count * REGISTRY_CATALOG_MEMBERSHIP_BYTES
    )
    shard_offset = (
        component_offset
        + component_count * REGISTRY_CATALOG_COMPONENT_ENTRY_BYTES
    )
    directory_offset = (
        shard_offset + shard_count * REGISTRY_CATALOG_SHARD_ENTRY_BYTES
    )
    memberships = list(
        struct.unpack_from(f"<{membership_count}I", raw, membership_offset)
    )

    animations: list[dict[str, Any]] = []
    referenced_components: set[int] = set()
    previous_animation_id = 0
    expected_membership_start = 0
    for index in range(animation_count):
        offset = animation_offset + index * REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES
        animation_id, owner, start, count = struct.unpack_from("<IIII", raw, offset)
        family = animation_id & 0xF000
        owner_matches = (
            owner == CATALOG_OWNER_CHARACTER and family in {0x5000, 0x6000}
        ) or (
            owner == CATALOG_OWNER_MONSTER_ICEWIND and family == 0xE000
        )
        if (
            animation_id in {0, CATALOG_SHARD_ANIMATION_SENTINEL}
            or animation_id > 0xFFFF
            or animation_id <= previous_animation_id
            or not owner_matches
            or count == 0
            or start != expected_membership_start
            or start > membership_count
            or count > membership_count - start
        ):
            raise RuntimeError("invalid creature registry catalog animation entry")
        component_indices = memberships[start : start + count]
        if (
            any(component >= component_count for component in component_indices)
            or component_indices != sorted(set(component_indices))
        ):
            raise RuntimeError("invalid creature registry catalog membership list")
        referenced_components.update(component_indices)
        animations.append(
            {
                "animation_id": f"0x{animation_id:04X}",
                "owner": owner,
                "membership_start": start,
                "membership_count": count,
                "component_indices": component_indices,
            }
        )
        previous_animation_id = animation_id
        expected_membership_start = start + count
    if expected_membership_start != membership_count or referenced_components != set(
        range(component_count)
    ):
        raise RuntimeError("creature registry catalog memberships lack exact coverage")

    raw_shard_entries: list[bytes] = []
    shard_entries: list[dict[str, Any]] = []
    seen_shard_hashes: set[str] = set()
    for index in range(shard_count):
        offset = shard_offset + index * REGISTRY_CATALOG_SHARD_ENTRY_BYTES
        entry_bytes = raw[offset : offset + REGISTRY_CATALOG_SHARD_ENTRY_BYTES]
        (
            digest_bytes,
            crc32,
            resource_count,
            frame_count,
            index_bytes,
            registry_bytes,
        ) = struct.unpack("<32sIIQQQ", entry_bytes)
        digest = digest_bytes.hex().upper()
        if (
            digest == "0" * 64
            or digest in seen_shard_hashes
            or not (1 <= resource_count <= MAX_RESOURCES)
            or not (1 <= frame_count <= resource_count * MAX_FRAMES_PER_RESOURCE)
            or not (1 <= index_bytes <= maximum_registry_bytes(scale))
            or not (REGISTRY_HEADER_BYTES <= registry_bytes <= maximum_registry_bytes(scale))
        ):
            raise RuntimeError("invalid creature registry catalog shard entry")
        seen_shard_hashes.add(digest)
        raw_shard_entries.append(entry_bytes)
        shard_entries.append(
            {
                "index": index,
                "registry": (
                    "iee-assets/creature-sprites/" + catalog_shard_filename(digest)
                ),
                "sha256": digest,
                "crc32": crc32,
                "resource_count": resource_count,
                "frame_count": frame_count,
                "index_bytes": index_bytes,
                "registry_bytes": registry_bytes,
            }
        )

    components: list[dict[str, Any]] = []
    seen_component_digests: set[str] = set()
    expected_shard_start = 0
    component_resources: list[list[str]] = []
    logical_component_digests: list[str] = []
    shard_resources: list[list[str]] = [[] for _ in range(shard_count)]
    calculated_resources = 0
    calculated_frames = 0
    calculated_index_bytes = 0
    calculated_registry_bytes = 0
    calculated_stored_index_bytes = 0
    calculated_compressed_frames = 0
    calculated_raw_frames = 0
    expected_shard_names: set[str] = set()
    shard_registry_versions: set[int] = set()
    for index in range(component_count):
        offset = component_offset + index * REGISTRY_CATALOG_COMPONENT_ENTRY_BYTES
        (
            digest_bytes,
            start,
            count,
            resource_count,
            reserved,
            frame_count,
            index_bytes,
            registry_bytes,
        ) = struct.unpack_from("<32sIIIIQQQ", raw, offset)
        digest = digest_bytes.hex().upper()
        if (
            digest == "0" * 64
            or digest in seen_component_digests
            or count == 0
            or start != expected_shard_start
            or start > shard_count
            or count > shard_count - start
            or reserved != 0
            or not (1 <= resource_count <= MAX_REGISTRY_CATALOG_RESOURCES)
            or not (1 <= frame_count <= MAX_REGISTRY_CATALOG_FRAMES)
            or not (1 <= index_bytes <= MAX_REGISTRY_CATALOG_BYTES)
            or not (REGISTRY_HEADER_BYTES <= registry_bytes <= MAX_REGISTRY_CATALOG_BYTES)
        ):
            raise RuntimeError("invalid creature registry catalog component entry")
        selected_entries = raw_shard_entries[start : start + count]
        if catalog_component_digest(scale, selected_entries) != digest:
            raise RuntimeError("creature registry catalog component digest differs")
        selected_shards = shard_entries[start : start + count]
        if (
            sum(int(shard["resource_count"]) for shard in selected_shards)
            != resource_count
            or sum(int(shard["frame_count"]) for shard in selected_shards)
            != frame_count
            or sum(int(shard["index_bytes"]) for shard in selected_shards)
            != index_bytes
            or sum(int(shard["registry_bytes"]) for shard in selected_shards)
            != registry_bytes
        ):
            raise RuntimeError("creature registry catalog component totals differ")
        resources: list[str] = []
        logical_records: list[dict[str, Any]] = []
        seen_resrefs: set[str] = set()
        for shard in selected_shards:
            shard_path = path.parent / Path(str(shard["registry"])).name
            expected_shard_names.add(shard_path.name)
            info = inspect_registry(shard_path, include_resource_records=True)
            if (
                info["registry_magic"] != registry_magic_name(XN_REGISTRY_MAGIC)
                or info["version"]
                not in {
                    XN_REGISTRY_VERSION,
                    XN_COMPRESSED_REGISTRY_VERSION,
                }
                or info["scale"] != scale
                or info["animation_id"].upper()
                != f"0X{CATALOG_SHARD_ANIMATION_SENTINEL:04X}"
                or info["sha256"] != shard["sha256"]
                or crc32_file(shard_path) != shard["crc32"]
                or info["resource_count"] != shard["resource_count"]
                or info["frame_count"] != shard["frame_count"]
                or info["index_bytes"] != shard["index_bytes"]
                or info["registry_bytes"] != shard["registry_bytes"]
            ):
                raise RuntimeError(
                    f"catalog shard differs from entry: {shard_path.name}"
                )
            shard_registry_versions.add(int(info["version"]))
            calculated_stored_index_bytes += int(info["stored_index_bytes"])
            calculated_compressed_frames += int(info["compressed_frame_count"])
            calculated_raw_frames += int(info["raw_frame_count"])
            duplicates = seen_resrefs.intersection(info["resources"])
            if duplicates:
                raise RuntimeError("duplicate resref inside catalog component")
            seen_resrefs.update(info["resources"])
            resources.extend(info["resources"])
            logical_records.extend(info["resource_records"])
            shard_resources[int(shard["index"])] = list(info["resources"])
        seen_component_digests.add(digest)
        components.append(
            {
                "index": index,
                "digest": digest,
                "shard_start": start,
                "shard_count": count,
                "resource_count": resource_count,
                "frame_count": frame_count,
                "index_bytes": index_bytes,
                "registry_bytes": registry_bytes,
            }
        )
        component_resources.append(resources)
        logical_records.sort(key=lambda item: str(item["resref"]))
        logical_component_digests.append(
            catalog_source_component_sha256(scale, logical_records)
        )
        expected_shard_start = start + count
        calculated_resources += resource_count
        calculated_frames += frame_count
        calculated_index_bytes += index_bytes
        calculated_registry_bytes += registry_bytes
    if expected_shard_start != shard_count:
        raise RuntimeError("creature registry catalog components lack shard coverage")
    if len(shard_registry_versions) != 1:
        raise RuntimeError("creature registry catalog mixes shard storage versions")
    shard_registry_version = next(iter(shard_registry_versions))
    if (
        version == LEGACY_XN_REGISTRY_CATALOG_VERSION
        and shard_registry_version != XN_REGISTRY_VERSION
    ):
        raise RuntimeError("legacy catalog requires V3 shards")
    if (
        shard_registry_version == XN_COMPRESSED_REGISTRY_VERSION
        and version != XN_REGISTRY_CATALOG_VERSION
    ):
        raise RuntimeError("compressed V5 shards require a V2 catalog")
    if (
        calculated_resources != total_resources
        or calculated_frames != total_frames
        or calculated_index_bytes != total_index_bytes
        or calculated_registry_bytes != total_registry_bytes
    ):
        raise RuntimeError("creature registry catalog aggregate totals differ")

    animation_resources: dict[str, list[str]] = {}
    expected_routes: dict[tuple[int, str], tuple[int, int, int]] = {}
    for animation in animations:
        resources: list[str] = []
        seen_resrefs: set[str] = set()
        for component_index in animation["component_indices"]:
            component = components[component_index]
            start = int(component["shard_start"])
            count = int(component["shard_count"])
            for shard_index in range(start, start + count):
                for resource_ordinal, resref in enumerate(
                    shard_resources[shard_index]
                ):
                    if resref in seen_resrefs:
                        raise RuntimeError(
                            "duplicate resref within one catalog animation scope"
                        )
                    seen_resrefs.add(resref)
                    resources.append(resref)
                    expected_routes[
                        (int(animation["animation_id"], 16), resref)
                    ] = (component_index, shard_index, resource_ordinal)
        animation_resources[animation["animation_id"]] = resources
    logical_content_sha256 = catalog_logical_content_digest(
        scale, animations, logical_component_digests
    )

    directory: list[dict[str, Any]] = []
    if version == XN_REGISTRY_CATALOG_VERSION:
        raw_directory = raw[
            directory_offset : directory_offset
            + directory_count * REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
        ]
        if catalog_directory_digest(scale, raw_directory) != directory_sha256:
            raise RuntimeError("creature registry catalog directory digest differs")
        previous_key: tuple[int, bytes] | None = None
        seen_routes: set[tuple[int, str]] = set()
        animation_components = {
            int(animation["animation_id"], 16): set(animation["component_indices"])
            for animation in animations
        }
        for index in range(directory_count):
            offset = (
                directory_offset
                + index * REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
            )
            (
                animation_id,
                resref_bytes,
                component_index,
                shard_index,
                resource_ordinal,
            ) = struct.unpack_from("<I8sIII", raw, offset)
            key = (animation_id, resref_bytes)
            try:
                resref = resref_bytes.split(b"\0", 1)[0].decode("ascii")
            except UnicodeDecodeError as error:
                raise RuntimeError(
                    "invalid creature registry catalog directory resref"
                ) from error
            if (
                (previous_key is not None and key <= previous_key)
                or not re.fullmatch(r"[A-Z0-9_]{1,8}", resref)
                or (
                    b"\0" in resref_bytes
                    and resref_bytes[len(resref) :] != b"\0" * (8 - len(resref))
                )
                or animation_id not in animation_components
                or component_index not in animation_components[animation_id]
                or component_index >= len(components)
                or shard_index >= len(shard_entries)
            ):
                raise RuntimeError("invalid creature registry catalog directory entry")
            component = components[component_index]
            shard_start = int(component["shard_start"])
            shard_count_for_component = int(component["shard_count"])
            if (
                shard_index < shard_start
                or shard_index >= shard_start + shard_count_for_component
                or resource_ordinal >= len(shard_resources[shard_index])
                or shard_resources[shard_index][resource_ordinal] != resref
            ):
                raise RuntimeError("catalog directory route differs from shard payload")
            route_key = (animation_id, resref)
            route = (component_index, shard_index, resource_ordinal)
            if route_key in seen_routes or expected_routes.get(route_key) != route:
                raise RuntimeError("catalog directory lacks an exact resource route")
            seen_routes.add(route_key)
            directory.append(
                {
                    "animation_id": f"0x{animation_id:04X}",
                    "resref": resref,
                    "component_index": component_index,
                    "shard_index": shard_index,
                    "resource_ordinal": resource_ordinal,
                }
            )
            previous_key = key
        if seen_routes != set(expected_routes):
            raise RuntimeError("catalog directory lacks exact animation resource coverage")

    if require_exact_shards:
        actual_shard_names = {
            candidate.name
            for candidate in path.parent.iterdir()
            if candidate.is_file()
            and re.fullmatch(
                r"CreatureSprites-XN-[0-9A-F]{64}\.registry", candidate.name
            )
        }
        if actual_shard_names != expected_shard_names:
            raise RuntimeError("catalog shard filenames are not exact")
    return {
        "version": version,
        "scale": scale,
        "registry_magic": registry_magic_name(magic),
        "registry_catalog_bytes": len(raw),
        "sha256": sha256_file(path),
        "directory_count": directory_count,
        "directory_entry_bytes": directory_entry_bytes,
        "directory_sha256": directory_sha256,
        "animation_count": animation_count,
        "component_count": component_count,
        "membership_count": membership_count,
        "shard_count": shard_count,
        "shard_registry_version": shard_registry_version,
        "total_resources": total_resources,
        "total_frames": total_frames,
        "total_index_bytes": total_index_bytes,
        "total_registry_bytes": total_registry_bytes,
        "stored_index_bytes": calculated_stored_index_bytes,
        "compressed_frame_count": calculated_compressed_frames,
        "raw_frame_count": calculated_raw_frames,
        "index_storage_ratio": calculated_stored_index_bytes
        / total_index_bytes,
        "animations": animations,
        "components": components,
        "logical_component_digests": logical_component_digests,
        "logical_content_sha256": logical_content_sha256,
        "shards": shard_entries,
        "directory": directory,
        "animation_resources": animation_resources,
    }


def write_registry_catalog(
    path: Path,
    scale: int,
    animations: list[dict[str, Any]],
    components: list[dict[str, Any]],
    shards: list[dict[str, Any]],
) -> dict[str, Any]:
    if path.name != XN_REGISTRY_CATALOG_FILENAME or scale not in {2, 4}:
        raise RuntimeError("invalid registry catalog output path or scale")
    animations = sorted(animations, key=lambda entry: int(entry["animation_id"], 16))
    if not (1 <= len(animations) <= MAX_REGISTRY_CATALOG_ANIMATIONS):
        raise RuntimeError("invalid registry catalog animation count")
    if not (1 <= len(components) <= MAX_REGISTRY_CATALOG_COMPONENTS):
        raise RuntimeError("invalid registry catalog component count")
    if not (len(components) <= len(shards) <= MAX_REGISTRY_CATALOG_SHARDS):
        raise RuntimeError("invalid registry catalog shard count")
    memberships: list[int] = []
    animation_bytes = bytearray()
    animation_mappings: list[tuple[int, list[int]]] = []
    seen_animation_ids: set[int] = set()
    for animation in animations:
        animation_id = int(str(animation["animation_id"]), 16)
        owner = int(animation["owner"])
        indices = sorted({int(value) for value in animation["component_indices"]})
        if (
            animation_id in seen_animation_ids
            or animation_id in {0, CATALOG_SHARD_ANIMATION_SENTINEL}
            or not indices
            or any(index < 0 or index >= len(components) for index in indices)
        ):
            raise RuntimeError("invalid registry catalog animation mapping")
        seen_animation_ids.add(animation_id)
        start = len(memberships)
        memberships.extend(indices)
        animation_bytes.extend(struct.pack("<IIII", animation_id, owner, start, len(indices)))
        animation_mappings.append((animation_id, indices))
    if len(memberships) > MAX_REGISTRY_CATALOG_MEMBERSHIPS:
        raise RuntimeError("registry catalog membership limit exceeded")

    shard_bytes: list[bytes] = []
    shard_infos: list[dict[str, Any]] = []
    for index, shard in enumerate(shards):
        path_value = Path(str(shard["path"]))
        if path_value.parent != path.parent:
            raise RuntimeError("catalog shard must be adjacent to catalog")
        info = inspect_registry(path_value)
        expected_name = catalog_shard_filename(info["sha256"])
        if path_value.name != expected_name or int(shard.get("index", -1)) != index:
            raise RuntimeError("catalog shard filename or index is not canonical")
        shard_bytes.append(catalog_shard_entry_bytes(info, path_value))
        shard_infos.append(info)

    component_bytes = bytearray()
    expected_start = 0
    for index, component in enumerate(components):
        start = int(component["shard_start"])
        count = int(component["shard_count"])
        if (
            int(component.get("index", -1)) != index
            or start != expected_start
            or count <= 0
            or start + count > len(shards)
        ):
            raise RuntimeError("catalog component shard range is invalid")
        selected = shard_bytes[start : start + count]
        digest = catalog_component_digest(scale, selected)
        if str(component["digest"]).upper() != digest:
            raise RuntimeError("catalog component digest differs from shards")
        component_bytes.extend(
            struct.pack(
                "<32sIIIIQQQ",
                bytes.fromhex(digest),
                start,
                count,
                int(component["resource_count"]),
                0,
                int(component["frame_count"]),
                int(component["index_bytes"]),
                int(component["registry_bytes"]),
            )
        )
        expected_start += count
    if expected_start != len(shards):
        raise RuntimeError("catalog components do not cover every shard")

    total_resources = sum(int(item["resource_count"]) for item in components)
    total_frames = sum(int(item["frame_count"]) for item in components)
    total_index_bytes = sum(int(item["index_bytes"]) for item in components)
    total_registry_bytes = sum(int(item["registry_bytes"]) for item in components)
    if (
        total_resources > MAX_REGISTRY_CATALOG_RESOURCES
        or total_frames > MAX_REGISTRY_CATALOG_FRAMES
        or total_index_bytes > MAX_REGISTRY_CATALOG_BYTES
        or total_registry_bytes > MAX_REGISTRY_CATALOG_BYTES
    ):
        raise RuntimeError("registry catalog aggregate limit exceeded")

    directory_routes: list[tuple[int, bytes, int, int, int]] = []
    for animation_id, component_indices in animation_mappings:
        seen_resrefs: set[bytes] = set()
        for component_index in component_indices:
            component = components[component_index]
            shard_start = int(component["shard_start"])
            shard_count = int(component["shard_count"])
            for shard_index in range(shard_start, shard_start + shard_count):
                for resource_ordinal, resref in enumerate(
                    shard_infos[shard_index]["resources"]
                ):
                    resref_bytes = str(resref).encode("ascii").ljust(8, b"\0")
                    if len(resref_bytes) != 8 or resref_bytes in seen_resrefs:
                        raise RuntimeError(
                            "duplicate or invalid resref in catalog animation directory"
                        )
                    seen_resrefs.add(resref_bytes)
                    directory_routes.append(
                        (
                            animation_id,
                            resref_bytes,
                            component_index,
                            shard_index,
                            resource_ordinal,
                        )
                    )
    directory_routes.sort(key=lambda entry: (entry[0], entry[1]))
    if not (
        1 <= len(directory_routes) <= MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES
    ):
        raise RuntimeError("registry catalog directory entry limit exceeded")
    directory_bytes = bytearray()
    previous_key: tuple[int, bytes] | None = None
    for animation_id, resref, component_index, shard_index, ordinal in directory_routes:
        key = (animation_id, resref)
        if previous_key is not None and key <= previous_key:
            raise RuntimeError("registry catalog directory order is not strict")
        directory_bytes.extend(
            struct.pack(
                "<I8sIII",
                animation_id,
                resref,
                component_index,
                shard_index,
                ordinal,
            )
        )
        previous_key = key
    directory_sha256 = catalog_directory_digest(scale, bytes(directory_bytes))
    raw = bytearray(
        struct.pack(
            "<8sIIIIIIQQQQ",
            XN_REGISTRY_CATALOG_MAGIC,
            XN_REGISTRY_CATALOG_VERSION,
            scale,
            len(animations),
            len(components),
            len(memberships),
            len(shards),
            total_resources,
            total_frames,
            total_index_bytes,
            total_registry_bytes,
        )
    )
    raw.extend(
        struct.pack(
            "<II32s",
            len(directory_routes),
            REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES,
            bytes.fromhex(directory_sha256),
        )
    )
    raw.extend(animation_bytes)
    if memberships:
        raw.extend(struct.pack(f"<{len(memberships)}I", *memberships))
    raw.extend(component_bytes)
    for entry in shard_bytes:
        raw.extend(entry)
    raw.extend(directory_bytes)
    path.write_bytes(raw)
    return inspect_registry_catalog(path)


def build_adapter_hash_matches(
    manifest: dict[str, Any], contract: UpscaleContract
) -> bool:
    adapter_hash = str(manifest.get("xbr_adapter_sha256", "")).upper()
    return adapter_hash == sha256_file(XBR_ADAPTER) or (
        not contract.explicit
        and adapter_hash in LEGACY_COMPATIBLE_XBR_ADAPTER_SHA256S
    )


def build_is_current(job: dict[str, Any], keep_frames: bool = False) -> bool:
    contract = upscale_contract(job)
    try:
        verify_build(job)
        report = read_json(build_dir(job) / "build-manifest.json")
    except (OSError, RuntimeError, ValueError, KeyError, TypeError):
        return False
    return not keep_frames or report.get(
        f"kept_individual_x{contract.scale}_frames"
    ) is True


def build_pack(job: dict[str, Any], force: bool, resume: bool, keep_frames: bool) -> dict[str, Any]:
    verify_sources(job, compare_game=True)
    output = build_dir(job)
    if resume and output.exists() and build_is_current(job, keep_frames):
        report = read_json(output / "build-manifest.json")
        return {"status": "reused", **inspect_build_payload(output, report)}
    if output.exists() and not (force or resume):
        raise RuntimeError(f"build exists; use --resume or --force: {output}")
    assert_workspace_child(output, "build output")
    manifest_path = source_manifest_path(job)
    frames, resources, source_manifest = load_source_frames(manifest_path)
    if not frames or len(resources) > MAX_RESOURCES:
        raise RuntimeError("invalid source inventory")
    contract = upscale_contract(job)
    preflight = preflight_registry_layout(
        resources,
        contract.scale,
        maximum_bytes=(
            MAX_REGISTRY_SET_BYTES
            if contract.explicit
            else maximum_registry_bytes(contract.scale)
        ),
    )
    if contract.explicit and preflight["frame_count"] > MAX_REGISTRY_SET_FRAMES:
        raise RuntimeError("member frames exceed registry-set format limit")
    use_registry_set = contract.explicit and (
        preflight["resource_count"] > MAX_RESOURCES
        or preflight["registry_bytes"] > maximum_registry_bytes(contract.scale)
    )
    partitions = (
        partition_registry_resources(
            preflight["resource_records"],
            maximum_bytes=maximum_registry_bytes(contract.scale),
        )
        if use_registry_set
        else [preflight["resource_records"]]
    )
    projected_registry_bytes = sum(
        REGISTRY_HEADER_BYTES + sum(int(record["bytes"]) for record in partition)
        for partition in partitions
    )
    if use_registry_set and projected_registry_bytes > MAX_REGISTRY_SET_BYTES:
        raise RuntimeError("member registry-set exceeds aggregate byte limit")
    resource_shards = {
        str(record["resref"]): shard_index
        for shard_index, partition in enumerate(partitions)
        for record in partition
    }
    scalepix = job_path(job, "scalepix")
    node = str(job.get("tools", {}).get("node", "node"))
    batch_ranges = xbr_output_batch_ranges(
        frames, contract.scale, XBR_OUTPUT_BATCH_BUDGET_BYTES
    )
    resource_states: list[dict[str, Any]] = []
    resource_cursor = 0
    for resource in resources:
        source = resource["source"]
        resref = str(source["name"]).upper()
        resource_frames: list[SourceFrame] = resource["frames"]
        cycles = sorted(resource["cycles"], key=lambda item: int(item["index"]))
        if [int(item["index"]) for item in cycles] != list(range(len(cycles))):
            raise RuntimeError(f"{resref}: non-contiguous cycles")
        for cycle in cycles:
            lookup = [int(value) for value in cycle["frame_indices"]]
            if any(value < 0 or value >= len(resource_frames) for value in lookup):
                raise RuntimeError(f"{resref}: invalid cycle lookup")
        resource_end = resource_cursor + len(resource_frames)
        if resource_end > len(frames) or any(
            frames[resource_cursor + index] is not frame
            for index, frame in enumerate(resource_frames)
        ):
            raise RuntimeError("global source frame order differs from resource inventory")
        resource_states.append(
            {
                "resource": resource,
                "resref": resref,
                "frames": resource_frames,
                "cycles": cycles,
                "shard_index": resource_shards[resref],
                "start": resource_cursor,
                "end": resource_end,
                "sample_positions": set(
                    comparison_sample_positions(len(resource_frames))
                ),
                "samples": {},
                "opaque_indices": set(),
            }
        )
        resource_cursor = resource_end
    if resource_cursor != len(frames):
        raise RuntimeError("resource inventory does not consume all source frames")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="build.tmp-", dir=output.parent))
    try:
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True, exist_ok=True)
        registry_path: Path | None = None
        registry_set_path: Path | None = None
        shard_paths = [
            pack_dir / XN_REGISTRY_SHARD_FILENAME.format(index=index)
            for index in range(len(partitions))
        ] if use_registry_set else [pack_dir / contract.registry_filename]
        if not use_registry_set:
            registry_path = shard_paths[0]
        report_resources: list[dict[str, Any]] = []
        total_scaled_pixels = 0
        processed_frames = 0
        current_resource_index = 0
        registry_streams: list[Any] = []
        with contextlib.ExitStack() as stack:
            for shard_path, partition in zip(shard_paths, partitions, strict=True):
                registry_stream = stack.enter_context(shard_path.open("wb"))
                registry_stream.write(contract.registry_magic)
                registry_stream.write(
                    struct.pack(
                        "<IIII",
                        contract.registry_version,
                        contract.scale,
                        len(partition),
                        int(job["animation"]["id"], 16),
                    )
                )
                registry_streams.append(registry_stream)
            for batch_start, batch_end, _ in batch_ranges:
                if batch_start != processed_frames:
                    raise RuntimeError("non-contiguous xBR batch order")
                batch_frames = frames[batch_start:batch_end]
                batch_outputs = run_xbr(
                    batch_frames, scalepix, node, contract
                )
                if len(batch_outputs) != len(batch_frames):
                    raise RuntimeError(
                        f"xBR{contract.scale}x batch output count differs from input"
                    )
                completed_resources: list[int] = []
                for batch_offset, (frame, output_record) in enumerate(
                    zip(batch_frames, batch_outputs, strict=True)
                ):
                    global_index = batch_start + batch_offset
                    if current_resource_index >= len(resource_states):
                        raise RuntimeError("xBR produced frames beyond the resource inventory")
                    state = resource_states[current_resource_index]
                    registry_stream = registry_streams[int(state["shard_index"])]
                    if global_index == int(state["start"]):
                        resource = state["resource"]
                        resource_frames = state["frames"]
                        cycles = state["cycles"]
                        resref = str(state["resref"])
                        registry_stream.write(resref.encode("ascii").ljust(8, b"\0"))
                        registry_stream.write(
                            bytes.fromhex(sha256_file(resource["source_path"]))
                        )
                        registry_stream.write(
                            struct.pack("<II", len(resource_frames), len(cycles))
                        )
                    if not int(state["start"]) <= global_index < int(state["end"]):
                        raise RuntimeError("xBR frame order differs from resource inventory")
                    local_index = global_index - int(state["start"])
                    if state["frames"][local_index] is not frame:
                        raise RuntimeError("xBR batch frame identity differs from inventory")
                    scaled_width, scaled_height, scaled_rgba = output_record
                    if (
                        scaled_width != frame.width * contract.scale
                        or scaled_height != frame.height * contract.scale
                    ):
                        raise RuntimeError(
                            f"{state['resref']} frame {frame.index}: output dimensions "
                            f"are not exact x{contract.scale}"
                        )
                    provenance = (
                        xbr_provenance_indices(frame, contract.scale)
                        if has_duplicate_used_rgba_indices(frame)
                        else None
                    )
                    mapped, representatives = map_output(
                        frame, scaled_rgba, provenance
                    )
                    state["opaque_indices"].update(
                        int(value)
                        for value in np.unique(mapped)
                        if value != frame.transparent
                    )
                    registry_stream.write(
                        struct.pack(
                            "<HHhhB3xI",
                            frame.width,
                            frame.height,
                            frame.center_x,
                            frame.center_y,
                            frame.transparent,
                            mapped.size,
                        )
                    )
                    registry_stream.write(
                        representatives.astype("<u2", copy=False).tobytes()
                    )
                    registry_stream.write(memoryview(mapped))
                    if local_index in state["sample_positions"]:
                        state["samples"][local_index] = output_record
                    if keep_frames:
                        frame_path = (
                            temporary
                            / f"x{contract.scale}"
                            / str(state["resref"])
                            / f"frame-{frame.index:04}.png"
                        )
                        frame_path.parent.mkdir(parents=True, exist_ok=True)
                        Image.frombytes(
                            "RGBA", (scaled_width, scaled_height), scaled_rgba
                        ).save(frame_path)
                    total_scaled_pixels += mapped.size
                    del mapped, representatives, scaled_rgba, output_record
                    processed_frames += 1
                    if global_index + 1 == int(state["end"]):
                        for cycle in state["cycles"]:
                            lookup = [int(value) for value in cycle["frame_indices"]]
                            registry_stream.write(struct.pack("<I", len(lookup)))
                            registry_stream.write(
                                struct.pack(f"<{len(lookup)}I", *lookup)
                            )
                        completed_resources.append(current_resource_index)
                        current_resource_index += 1
                del batch_outputs, batch_frames

                # Render QA only after dropping non-sample batch outputs.
                for completed_index in completed_resources:
                    state = resource_states[completed_index]
                    resource = state["resource"]
                    resref = str(state["resref"])
                    make_comparison_sheet_samples(
                        state["frames"],
                        state["samples"],
                        temporary / "qa" / f"{resref}-comparison.png",
                        contract,
                    )
                    state["samples"].clear()
                    report_resources.append(
                        {
                            "resref": resref,
                            "source": relative_project_path(resource["source_path"]),
                            "source_sha256": sha256_file(resource["source_path"]),
                            "frames": len(state["frames"]),
                            "cycles": len(state["cycles"]),
                            "cycle_slots": sum(
                                len(item["frame_indices"])
                                for item in state["cycles"]
                            ),
                            f"opaque_palette_indices_in_x{contract.scale}": len(
                                state["opaque_indices"]
                            ),
                            "qa_sheet": f"qa/{resref}-comparison.png",
                        }
                    )
            registry_bytes_written = sum(stream.tell() for stream in registry_streams)

        if processed_frames != len(frames) or current_resource_index != len(
            resource_states
        ):
            raise RuntimeError(f"unconsumed xBR{contract.scale}x frames")
        if len(report_resources) != len(resources):
            raise RuntimeError("not all resource QA sheets were finalized")
        if registry_bytes_written != projected_registry_bytes:
            raise RuntimeError(
                "registry size differs from the pre-xBR projection: "
                f"{registry_bytes_written} != {projected_registry_bytes}"
            )
        if use_registry_set:
            shard_infos: list[dict[str, Any]] = []
            for shard_path in shard_paths:
                shard_info = inspect_registry(shard_path)
                shard_info["path"] = shard_path
                shard_infos.append(shard_info)
            registry_set_path = pack_dir / XN_REGISTRY_SET_FILENAME
            registry_info = write_registry_set_index(
                registry_set_path,
                contract.scale,
                int(job["animation"]["id"], 16),
                shard_infos,
            )
        else:
            assert registry_path is not None
            registry_info = inspect_registry(registry_path)
        projected_output_bytes = sum(batch[2] for batch in batch_ranges)
        if (
            total_scaled_pixels != preflight["index_bytes"]
            or projected_output_bytes != preflight["index_bytes"] * 4
        ):
            raise RuntimeError("xBR batching totals differ from registry preflight")
        batching_report = {
            "output_budget_bytes": XBR_OUTPUT_BATCH_BUDGET_BYTES,
            "batch_count": len(batch_ranges),
            "total_projected_output_bytes": projected_output_bytes,
            "maximum_projected_batch_bytes": max(batch[2] for batch in batch_ranges),
            "oversized_singleton_batches": sum(
                1
                for start, end, batch_bytes in batch_ranges
                if end - start == 1
                and batch_bytes > XBR_OUTPUT_BATCH_BUDGET_BYTES
            ),
            "ordering": "source-resource-frame",
        }
        report = {
            "schema": BUILD_SCHEMA,
            "status": "built-pending-ingame-qa",
            "created_at_utc": utc_now(),
            "job_id": job["job_id"],
            "animation_id": job["animation"]["id"],
            "bam_prefix": job["animation"]["bam_prefix"],
            "runtime_profile": job["animation"].get("runtime_profile"),
            "registry_version": contract.registry_version,
            "method": contract.method,
            "source_manifest": relative_project_path(manifest_path),
            "source_manifest_sha256": sha256_file(manifest_path),
            "scalepix": str(scalepix),
            "scalepix_sha256": sha256_file(scalepix),
            "xbr_adapter_sha256": sha256_file(XBR_ADAPTER),
            "resources": report_resources,
            "resource_count": len(resources),
            "frame_count": len(frames),
            f"x{contract.scale}_pixel_count": total_scaled_pixels,
            "xbr_batching": batching_report,
            "registry": (
                f"iee-assets/creature-sprites/{contract.registry_filename}"
                if registry_path is not None
                else None
            ),
            "registry_bytes": registry_info["registry_bytes"],
            "registry_sha256": (
                registry_info["sha256"] if registry_path is not None else None
            ),
            f"kept_individual_x{contract.scale}_frames": keep_frames,
            "validation": {
                f"dimensions_exact_x{contract.scale}": len(frames),
                "frames_exactly_remapped_to_source_palette": len(frames),
                "partial_alpha_pixels": 0,
                "new_colors": 0,
                "xbr_dispatch_batches": len(batch_ranges),
                "qa_samples_retained_max_per_resource": 5,
            },
        }
        if contract.explicit:
            report["registry_magic"] = registry_magic_name(contract.registry_magic)
            report["registry_scale"] = contract.scale
            report["registry_layout"] = "set" if use_registry_set else "monolith"
            report["registry_set"] = (
                f"iee-assets/creature-sprites/{XN_REGISTRY_SET_FILENAME}"
                if registry_set_path is not None
                else None
            )
            report["registry_set_sha256"] = (
                registry_info["sha256"] if registry_set_path is not None else None
            )
            report["registry_set_bytes"] = (
                registry_info["registry_set_bytes"]
                if registry_set_path is not None
                else None
            )
            report["shards"] = (
                registry_set_manifest_shards(registry_info)
                if registry_set_path is not None
                else []
            )
            report["total_resources"] = registry_info["resource_count"]
            report["total_frames"] = registry_info["frame_count"]
            report["total_index_bytes"] = registry_info["index_bytes"]
            report["total_registry_bytes"] = registry_info["registry_bytes"]
            report["validation"].update(
                {
                    "monolithic_registry_bytes_preflight": preflight[
                        "registry_bytes"
                    ],
                    "registry_bytes_preflight": projected_registry_bytes,
                    "shard_count": len(partitions),
                    "maximum_shard_resources": MAX_RESOURCES,
                    "maximum_shard_bytes": maximum_registry_bytes(contract.scale),
                    "maximum_set_shards": MAX_REGISTRY_SET_SHARDS,
                    "maximum_set_resources": MAX_REGISTRY_SET_RESOURCES,
                    "maximum_set_frames": MAX_REGISTRY_SET_FRAMES,
                    "maximum_set_registry_bytes": MAX_REGISTRY_SET_BYTES,
                }
            )
        if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
            report["layer"] = character_layer_config(job)
        write_json(temporary / "build-manifest.json", report)
        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)
        return {
            "status": "built",
            "registry_layout": "set" if use_registry_set else "monolith",
            **registry_info,
        }
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def source_tree_hash(source_root: Path) -> str:
    relative_files = [
        "CMakeLists.txt",
        "src/iee/hooks.cpp",
        "src/iee/native_occlusion_bridge.cpp",
        "src/iee/native_occlusion_bridge.h",
        "src/iee/dll_main.cpp",
        "src/iee/bridge_transition.cpp",
        "src/iee/bridge_transition.h",
        "src/iee/creature_sprite_x2.cpp",
        "src/iee/creature_sprite_x2.h",
        "src/iee/core/config.cpp",
        "src/iee/core/config.h",
        "src/iee/core/native_occlusion_probe.cpp",
        "src/iee/core/native_occlusion_probe.h",
        "src/iee/game/build_manifest.cpp",
        "src/iee/game/build_manifest.h",
        "tests/iee_tests.cpp",
        "tests/bridge_worker_lifecycle_tests.cpp",
    ]
    digest = hashlib.sha256()
    for relative in relative_files:
        path = source_root / relative
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest().upper()


def run_checked(command: list[str], cwd: Path | None = None) -> None:
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def assert_cmake_build_root_supported(build: Path) -> None:
    if os.name == "nt" and len(str(build)) > MAX_WINDOWS_CMAKE_BUILD_ROOT_CHARS:
        raise RuntimeError(
            "catalog CMake build root is too long for Visual Studio 2019 "
            f"FileTracker ({len(str(build))} > "
            f"{MAX_WINDOWS_CMAKE_BUILD_ROOT_CHARS} characters): {build}"
        )


def build_runtime(job: dict[str, Any]) -> dict[str, Any]:
    require_runtime_profile(job)
    if os.name != "nt":
        raise RuntimeError("Windows is required for the BG2EE runtime DLL")
    source = job_path(job, "engine_source")
    catalog_job = job.get("_kind") == "catalog"
    if catalog_job:
        catalog_info = verify_catalog_build(job)
        generation_id = catalog_generation_id(job)
        build = job_path(job, "engine_build") / generation_id.lower()
        assert_cmake_build_root_supported(build)
        destination = runtime_dir(job)
        if destination.exists():
            verify_runtime(job)
            write_catalog_pointer(job)
            return read_json(destination / "runtime-manifest.json")
    else:
        build = job_path(job, "engine_build")
        destination = runtime_dir(job)
    cmake = str(job.get("tools", {}).get("cmake", "cmake"))
    runtime = job.get("runtime", {})
    if not (build / "CMakeCache.txt").is_file():
        generator = str(runtime.get("cmake_generator", "Visual Studio 16 2019"))
        architecture = str(runtime.get("cmake_arch", "x64"))
        build.parent.mkdir(parents=True, exist_ok=True)
        run_checked([cmake, "-S", str(source), "-B", str(build), "-G", generator, "-A", architecture, "-DIEE_BUILD_WINDOWS_DLL=ON", "-DBUILD_TESTING=ON"])
    run_checked([cmake, "--build", str(build), "--config", "Release", "--target", "release_bundle"])
    run_checked([cmake, "--build", str(build), "--config", "Release", "--target", "iee_tests"])
    run_checked(
        [
            cmake,
            "--build",
            str(build),
            "--config",
            "Release",
            "--target",
            "iee_bridge_worker_tests",
        ]
    )
    tests = build / "Release" / "iee_tests.exe"
    if not tests.is_file():
        tests = build / "iee_tests.exe"
    run_checked([str(tests)], cwd=source)
    bridge_worker_tests = build / "Release" / "iee_bridge_worker_tests.exe"
    if not bridge_worker_tests.is_file():
        bridge_worker_tests = build / "iee_bridge_worker_tests.exe"
    if not bridge_worker_tests.is_file():
        raise RuntimeError(f"bridge worker tests missing: {bridge_worker_tests}")
    run_checked([str(bridge_worker_tests)], cwd=source)
    source_dll = build / "release-bundle" / "InfinityEngine-Enhancer.dll"
    if not source_dll.is_file():
        raise RuntimeError(f"release DLL missing: {source_dll}")
    runtime_output = destination
    if catalog_job:
        if catalog_generation_id(job, refresh=True) != generation_id:
            raise RuntimeError("catalog inputs changed while building the runtime")
        runtime_output = Path(
            tempfile.mkdtemp(prefix="runtime-", dir=destination.parent)
        )
    else:
        destination.mkdir(parents=True, exist_ok=True)
    dll = runtime_output / "InfinityEngine-Enhancer.dll"
    shutil.copy2(source_dll, dll)
    manifest = {
        "schema": RUNTIME_SCHEMA,
        "status": "built-tested",
        "created_at_utc": utc_now(),
        "job_id": job["job_id"],
        "engine_source": relative_project_path(source),
        "engine_source_contract_sha256": source_tree_hash(source),
        "engine_build": relative_project_path(build),
        "dll": "InfinityEngine-Enhancer.dll",
        "dll_sha256": sha256_file(dll),
        "tests": str(tests),
        "bridge_worker_tests": str(bridge_worker_tests),
        "bridge_worker_tests_status": "passed",
        "tests_status": "passed",
    }
    if catalog_job:
        contract = upscale_contract(job)
        manifest.update(
            {
                "generation_id": generation_id,
                "job_sha256": sha256_file(Path(job["_job_file"])),
                "method": contract.method,
                "runtime_profiles": runtime_profiles_for_work_item(job),
                "catalog_magic": registry_magic_name(
                    XN_REGISTRY_CATALOG_MAGIC
                ),
                "catalog_version": XN_REGISTRY_CATALOG_VERSION,
                "catalog_directory_count": catalog_info["directory_count"],
                "catalog_directory_entry_bytes": catalog_info[
                    "directory_entry_bytes"
                ],
                "catalog_directory_sha256": catalog_info["directory_sha256"],
                "catalog_logical_content_sha256": catalog_info[
                    "logical_content_sha256"
                ],
                "catalog_shard_registry_magic": registry_magic_name(
                    XN_REGISTRY_MAGIC
                ),
                "catalog_shard_registry_version": (
                    CATALOG_SHARD_REGISTRY_VERSION
                ),
                "catalog_frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                "catalog_shard_animation_id_sentinel": "0xFFFF",
                "catalog_limits": {
                    "maximum_animations": MAX_REGISTRY_CATALOG_ANIMATIONS,
                    "maximum_components": MAX_REGISTRY_CATALOG_COMPONENTS,
                    "maximum_memberships": MAX_REGISTRY_CATALOG_MEMBERSHIPS,
                    "maximum_shards": MAX_REGISTRY_CATALOG_SHARDS,
                    "maximum_physical_resources": MAX_REGISTRY_CATALOG_RESOURCES,
                    "maximum_frames": MAX_REGISTRY_CATALOG_FRAMES,
                    "maximum_registry_bytes": MAX_REGISTRY_CATALOG_BYTES,
                    "maximum_resources_per_shard": MAX_RESOURCES,
                    "maximum_frames_per_resource": MAX_FRAMES_PER_RESOURCE,
                    "maximum_lazy_frame_index_bytes": MAX_LAZY_FRAME_INDEX_BYTES,
                    "maximum_directory_entries": (
                        MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES
                    ),
                    "maximum_x2_shard_bytes": maximum_registry_bytes(2),
                    "maximum_x4_shard_bytes": maximum_registry_bytes(4),
                },
            }
        )
    else:
        manifest["runtime_profile"] = job["animation"]["runtime_profile"]
    write_json(runtime_output / "runtime-manifest.json", manifest)
    if catalog_job:
        try:
            if destination.exists():
                raise RuntimeError("catalog runtime appeared during generation")
            runtime_output.replace(destination)
        except Exception:
            shutil.rmtree(runtime_output, ignore_errors=True)
            raise
        write_catalog_pointer(job)
    return manifest


def verify_xbr_batching_manifest(
    manifest: dict[str, Any], frame_count: int, index_bytes: int
) -> None:
    batching = manifest.get("xbr_batching")
    # Builds made before bounded dispatch remain resumable and verifiable; the
    # adapter, source and registry hashes still prove their payload identity.
    if batching is None:
        return
    if not isinstance(batching, dict):
        raise RuntimeError("build xBR batching metadata must be an object")
    integer_fields = (
        "output_budget_bytes",
        "batch_count",
        "total_projected_output_bytes",
        "maximum_projected_batch_bytes",
        "oversized_singleton_batches",
    )
    values: dict[str, int] = {}
    for name in integer_fields:
        value = batching.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(f"build xBR batching field is invalid: {name}")
        values[name] = value
    if (
        values["output_budget_bytes"] <= 0
        or not (1 <= values["batch_count"] <= frame_count)
        or values["total_projected_output_bytes"] != index_bytes * 4
        or not (
            1
            <= values["maximum_projected_batch_bytes"]
            <= values["total_projected_output_bytes"]
        )
        or not (
            0
            <= values["oversized_singleton_batches"]
            <= values["batch_count"]
        )
        or (
            values["maximum_projected_batch_bytes"]
            > values["output_budget_bytes"]
        )
        != (values["oversized_singleton_batches"] > 0)
        or batching.get("ordering") != "source-resource-frame"
    ):
        raise RuntimeError("build xBR batching metadata is inconsistent")
    validation = manifest.get("validation") or {}
    if (
        validation.get("xbr_dispatch_batches") != values["batch_count"]
        or validation.get("qa_samples_retained_max_per_resource") != 5
    ):
        raise RuntimeError("build xBR batching validation metadata is inconsistent")


def verify_build(job: dict[str, Any]) -> dict[str, Any]:
    manifest_path = build_dir(job) / "build-manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema") != BUILD_SCHEMA:
        raise RuntimeError("unsupported build manifest")
    if manifest.get("status") != "built-pending-ingame-qa":
        raise RuntimeError("build manifest is not pending ingame QA")
    if manifest.get("job_id") != job["job_id"]:
        raise RuntimeError("build manifest job id differs from job")
    if str(manifest.get("animation_id", "")).upper() != job["animation"]["id"].upper():
        raise RuntimeError("build manifest animation id differs from job")
    if str(manifest.get("bam_prefix", "")).upper() != job["animation"]["bam_prefix"]:
        raise RuntimeError("build manifest BAM prefix differs from job")
    if manifest.get("runtime_profile") != job["animation"].get("runtime_profile"):
        raise RuntimeError("build manifest runtime profile differs from job")
    if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
        if manifest.get("layer", {"kind": "body"}) != character_layer_config(job):
            raise RuntimeError("build manifest Character layer differs from job")
    contract = upscale_contract(job)
    if manifest.get("method") != contract.method:
        raise RuntimeError("build manifest upscale method differs from job")
    if manifest.get("source_manifest_sha256") != sha256_file(
        source_manifest_path(job)
    ):
        raise RuntimeError("build source manifest hash differs from current source")
    if manifest.get("scalepix_sha256") != sha256_file(job_path(job, "scalepix")):
        raise RuntimeError("build Scalepix hash differs from current source")
    if not build_adapter_hash_matches(manifest, contract):
        raise RuntimeError("build xBR adapter hash differs from current contract")
    if manifest.get("registry_version") != contract.registry_version:
        raise RuntimeError("build manifest registry version differs from job")
    if contract.explicit and (
        manifest.get("registry_magic") != registry_magic_name(contract.registry_magic)
        or manifest.get("registry_scale") != contract.scale
    ):
        raise RuntimeError("build manifest registry magic/scale differs from job")
    layout = str(manifest.get("registry_layout", "monolith"))
    if layout == "set" and not contract.explicit:
        raise RuntimeError("legacy member builds cannot use registry-set layout")
    info = inspect_build_payload(build_dir(job), manifest)
    if layout == "monolith":
        registry = build_dir(job) / str(manifest.get("registry", ""))
        if info["sha256"] != manifest.get("registry_sha256"):
            raise RuntimeError("registry hash differs from build manifest")
        if registry.name != contract.registry_filename:
            raise RuntimeError("registry filename differs from job")
        if contract.explicit and "registry_layout" in manifest and (
            manifest.get("registry_set") is not None
            or manifest.get("registry_set_sha256") is not None
            or manifest.get("registry_set_bytes") is not None
            or manifest.get("shards") != []
        ):
            raise RuntimeError("build manifest monolithic layout metadata differs from registry")
    elif layout == "set":
        registry_set = build_dir(job) / str(manifest.get("registry_set", ""))
        if (
            manifest.get("registry") is not None
            or manifest.get("registry_sha256") is not None
            or registry_set.name != XN_REGISTRY_SET_FILENAME
            or info["sha256"] != manifest.get("registry_set_sha256")
            or info["registry_set_bytes"] != manifest.get("registry_set_bytes")
            or manifest.get("shards") != registry_set_manifest_shards(info)
        ):
            raise RuntimeError("build manifest registry-set metadata differs from its index")
    else:
        raise RuntimeError("unsupported member registry layout")
    if info["animation_id"].upper() != job["animation"]["id"].upper():
        raise RuntimeError("registry animation id differs from job")
    if (
        info["version"] != contract.registry_version
        or info["scale"] != contract.scale
        or info["registry_magic"] != registry_magic_name(contract.registry_magic)
    ):
        raise RuntimeError("registry magic/version/scale differs from job")
    prefix = job["animation"]["bam_prefix"]
    if any(not name.startswith(prefix) for name in info["resources"]):
        raise RuntimeError("registry contains an out-of-family resref")
    if info["frame_count"] != int(manifest["frame_count"]):
        raise RuntimeError("registry frame count differs from build manifest")
    if (
        manifest.get("resource_count") != info["resource_count"]
        or manifest.get("registry_bytes") != info["registry_bytes"]
    ):
        raise RuntimeError("registry top-level counters differ from build manifest")
    if info["index_bytes"] != int(
        manifest.get(f"x{contract.scale}_pixel_count", -1)
    ):
        raise RuntimeError("registry index bytes differ from build manifest pixel count")
    if contract.explicit and "registry_layout" in manifest and (
        manifest.get("total_resources") != info["resource_count"]
        or manifest.get("total_frames") != info["frame_count"]
        or manifest.get("total_index_bytes") != info["index_bytes"]
        or manifest.get("total_registry_bytes") != info["registry_bytes"]
    ):
        raise RuntimeError("build manifest aggregate layout metadata differs from registry")
    validation = manifest.get("validation") or {}
    if validation.get(f"dimensions_exact_x{contract.scale}") != info["frame_count"]:
        raise RuntimeError("build manifest exact-dimension count differs from registry")
    if contract.explicit and "registry_layout" in manifest:
        shard_count = len(info["shards"]) if layout == "set" else 1
        expected_monolithic_bytes = (
            info["registry_bytes"] - (shard_count - 1) * REGISTRY_HEADER_BYTES
        )
        if (
            validation.get("monolithic_registry_bytes_preflight")
            != expected_monolithic_bytes
            or validation.get("registry_bytes_preflight")
            != info["registry_bytes"]
            or validation.get("shard_count") != shard_count
            or validation.get("maximum_shard_resources") != MAX_RESOURCES
            or validation.get("maximum_shard_bytes")
            != maximum_registry_bytes(contract.scale)
            or validation.get("maximum_set_shards") != MAX_REGISTRY_SET_SHARDS
            or validation.get("maximum_set_resources")
            != MAX_REGISTRY_SET_RESOURCES
            or validation.get("maximum_set_frames") != MAX_REGISTRY_SET_FRAMES
            or validation.get("maximum_set_registry_bytes")
            != MAX_REGISTRY_SET_BYTES
        ):
            raise RuntimeError("build registry layout validation differs from payload")
    verify_xbr_batching_manifest(manifest, info["frame_count"], info["index_bytes"])
    return info


def verify_runtime(job: dict[str, Any]) -> dict[str, Any]:
    require_runtime_profile(job)
    manifest = read_json(runtime_dir(job) / "runtime-manifest.json")
    if (
        manifest.get("schema") != RUNTIME_SCHEMA
        or manifest.get("tests_status") != "passed"
        or manifest.get("bridge_worker_tests_status") != "passed"
    ):
        raise RuntimeError("runtime is not built and tested")
    if manifest.get("job_id") != job["job_id"]:
        raise RuntimeError("runtime manifest job id differs from job")
    if job.get("_kind") == "catalog":
        generation_id = catalog_generation_id(job)
        contract = upscale_contract(job)
        catalog_info = verify_catalog_build(job)
        expected_limits = {
            "maximum_animations": MAX_REGISTRY_CATALOG_ANIMATIONS,
            "maximum_components": MAX_REGISTRY_CATALOG_COMPONENTS,
            "maximum_memberships": MAX_REGISTRY_CATALOG_MEMBERSHIPS,
            "maximum_shards": MAX_REGISTRY_CATALOG_SHARDS,
            "maximum_physical_resources": MAX_REGISTRY_CATALOG_RESOURCES,
            "maximum_frames": MAX_REGISTRY_CATALOG_FRAMES,
            "maximum_registry_bytes": MAX_REGISTRY_CATALOG_BYTES,
            "maximum_resources_per_shard": MAX_RESOURCES,
            "maximum_frames_per_resource": MAX_FRAMES_PER_RESOURCE,
            "maximum_lazy_frame_index_bytes": MAX_LAZY_FRAME_INDEX_BYTES,
            "maximum_directory_entries": MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES,
            "maximum_x2_shard_bytes": maximum_registry_bytes(2),
            "maximum_x4_shard_bytes": maximum_registry_bytes(4),
        }
        if (
            manifest.get("generation_id") != generation_id
            or manifest.get("job_sha256")
            != sha256_file(Path(job["_job_file"]))
            or manifest.get("method") != contract.method
            or manifest.get("runtime_profiles")
            != runtime_profiles_for_work_item(job)
            or manifest.get("catalog_magic")
            != registry_magic_name(XN_REGISTRY_CATALOG_MAGIC)
            or manifest.get("catalog_version") != XN_REGISTRY_CATALOG_VERSION
            or manifest.get("catalog_directory_count")
            != catalog_info["directory_count"]
            or manifest.get("catalog_directory_entry_bytes")
            != catalog_info["directory_entry_bytes"]
            or manifest.get("catalog_directory_sha256")
            != catalog_info["directory_sha256"]
            or manifest.get("catalog_logical_content_sha256")
            != catalog_info["logical_content_sha256"]
            or manifest.get("catalog_shard_registry_magic")
            != registry_magic_name(XN_REGISTRY_MAGIC)
            or manifest.get("catalog_shard_registry_version")
            != catalog_info["shard_registry_version"]
            or manifest.get("catalog_frame_storage")
            != "XPRESS_HUFF-or-raw-per-frame-v1"
            or manifest.get("catalog_shard_animation_id_sentinel") != "0xFFFF"
            or manifest.get("catalog_limits") != expected_limits
        ):
            raise RuntimeError("catalog runtime manifest differs from catalog contract")
    elif manifest.get("runtime_profile") != job["animation"].get(
        "runtime_profile"
    ):
        raise RuntimeError("runtime manifest profile differs from job")
    source_contract_sha256 = source_tree_hash(job_path(job, "engine_source"))
    if manifest.get("engine_source_contract_sha256") != source_contract_sha256:
        raise RuntimeError("runtime engine source contract differs from current source")
    dll = runtime_dir(job) / str(manifest["dll"])
    if sha256_file(dll) != manifest.get("dll_sha256"):
        raise RuntimeError("runtime DLL hash differs from runtime manifest")
    return {"dll": str(dll), "dll_sha256": manifest["dll_sha256"], "tests_status": "passed"}


def plan(job: dict[str, Any]) -> dict[str, Any]:
    game = job_path(job, "game_root")
    source_manifest = source_manifest_path(job)
    build_manifest = build_dir(job) / "build-manifest.json"
    runtime_manifest = runtime_dir(job) / "runtime-manifest.json"
    exe = game / "BaldurReal.exe"
    expected = job["compatibility"]["baldur_real_sha256"].upper()
    contract = upscale_contract(job)
    build_layout = None
    if build_manifest.is_file():
        try:
            build_layout = str(
                read_json(build_manifest).get("registry_layout", "monolith")
            )
        except (OSError, RuntimeError, ValueError, TypeError):
            build_layout = "invalid-manifest"
    identity = None
    identity_compatible = None
    identity_error = None
    if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
        try:
            require_clean_character_identity_overrides(job, game)
            identity = verify_character_animation_identity(job, KeyIndex(game))
            identity_compatible = True
        except (OSError, RuntimeError, ValueError) as error:
            identity_compatible = False
            identity_error = str(error)
    return {
        "job_id": job["job_id"],
        "method": upscale_method_description(contract),
        "runtime_profile": job["animation"].get("runtime_profile"),
        "runtime_profile_supported": job["animation"].get("runtime_profile")
        in SUPPORTED_RUNTIME_PROFILES,
        "animation_identity_compatible": identity_compatible,
        "animation_identity": identity,
        "animation_identity_error": identity_error,
        "game_root": str(game),
        "baldur_real_compatible": exe.is_file() and sha256_file(exe) == expected,
        "scalepix_exists": job_path(job, "scalepix").is_file(),
        "source_manifest_exists": source_manifest.is_file(),
        "build_manifest_exists": build_manifest.is_file(),
        "build_registry_layout": build_layout,
        "registry_layout_policy": (
            "auto-shard-explicit-xn" if contract.explicit else "monolith-only-legacy"
        ),
        "maximum_shard_bytes": maximum_registry_bytes(contract.scale),
        "maximum_set_shards": MAX_REGISTRY_SET_SHARDS if contract.explicit else 1,
        "maximum_set_resources": (
            MAX_REGISTRY_SET_RESOURCES if contract.explicit else MAX_RESOURCES
        ),
        "maximum_set_frames": (
            MAX_REGISTRY_SET_FRAMES if contract.explicit else None
        ),
        "maximum_set_registry_bytes": (
            MAX_REGISTRY_SET_BYTES if contract.explicit else None
        ),
        "runtime_manifest_exists": runtime_manifest.is_file(),
        "install_is_explicit": True,
        "game_launch_is_never_automatic": True,
        "release_manifest_is_out_of_scope": True,
    }


def verify_all(job: dict[str, Any], compare_game_sources: bool) -> dict[str, Any]:
    game = job_path(job, "game_root")
    exe = game / "BaldurReal.exe"
    expected = job["compatibility"]["baldur_real_sha256"].upper()
    if sha256_file(exe) != expected:
        raise RuntimeError("BaldurReal.exe is incompatible with the job")
    source = verify_sources(job, compare_game_sources)
    build = verify_build(job)
    runtime = verify_runtime(job)
    override = game / "override"
    if override.is_dir() and job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
        source_inventory = read_json(source_manifest_path(job)).get("bams", [])
        collisions = sorted(
            path.name
            for resource in source_inventory
            if (path := override / f"{str(resource['name']).upper()}.BAM").is_file()
        )
    else:
        collisions = sorted(path.name for path in override.glob(job["animation"]["bam_prefix"] + "*.BAM")) if override.is_dir() else []
    if collisions:
        raise RuntimeError(f"override collision: {', '.join(collisions)}")
    return {"status": "prepared-verified", "source": source, "build": build, "runtime": runtime, "override_collisions": 0}


def armor_set_prefixes(armor_set: dict[str, Any]) -> list[str]:
    return [str(member["animation"]["bam_prefix"]) for member in armor_set["_members"]]


def armor_set_body_codes(armor_set: dict[str, Any]) -> list[int]:
    return [
        int(member["animation"]["armor_code"])
        for member in armor_set["_members"]
        if character_layer_config(member)["kind"] == "body"
    ]


def armor_set_equipment_layers(armor_set: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "kind": character_layer_config(member)["kind"],
            "item_resref": character_layer_config(member)["item_resref"],
            "bam_prefix": str(member["animation"]["bam_prefix"]),
        }
        for member in armor_set["_members"]
        if character_layer_config(member)["kind"] != "body"
    ]


def armor_set_member_records(armor_set: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for member in armor_set["_members"]:
        source = verify_sources(member, compare_game=True)
        build = verify_build(member)
        manifest_path = build_dir(member) / "build-manifest.json"
        member_manifest = read_json(manifest_path)
        member_layout = str(member_manifest.get("registry_layout", "monolith"))
        layer = character_layer_config(member)
        record: dict[str, Any]
        if layer["kind"] == "body":
            # Preserve the original armor-set record shape byte-for-byte so
            # already-built body-only bundles remain verifiable.
            record = {
                "job_file": relative_project_path(Path(member["_job_file"])),
                "job_id": member["job_id"],
                "armor_code": member["animation"]["armor_code"],
                "bam_prefix": member["animation"]["bam_prefix"],
                "source_manifest_sha256": sha256_file(source_manifest_path(member)),
                "build_manifest_sha256": sha256_file(manifest_path),
                "registry": str(member_manifest["registry"]),
                "registry_sha256": build["sha256"],
                "resource_count": build["resource_count"],
                "frame_count": build["frame_count"],
                "source_resource_count": source["resources"],
            }
        else:
            identity = source.get("animation_identity", {})
            record = {
                "job_file": relative_project_path(Path(member["_job_file"])),
                "job_id": member["job_id"],
                "layer_kind": layer["kind"],
                "item_resref": layer["item_resref"],
                "item_animation_code": identity.get("item_animation_code"),
                "height_code": identity.get("equipment_height_code"),
                "bam_prefix": member["animation"]["bam_prefix"],
                "source_manifest_sha256": sha256_file(source_manifest_path(member)),
                "build_manifest_sha256": sha256_file(manifest_path),
                "registry": str(member_manifest["registry"]),
                "registry_sha256": build["sha256"],
                "resource_count": build["resource_count"],
                "frame_count": build["frame_count"],
                "source_resource_count": source["resources"],
            }
        if member_layout == "set":
            record["registry"] = None
            record["registry_sha256"] = None
            record["registry_layout"] = "set"
            record["registry_set"] = str(member_manifest["registry_set"])
            record["registry_set_sha256"] = build["sha256"]
            record["shards"] = member_manifest["shards"]
        records.append(record)
    return records


def armor_set_member_records_match(
    recorded: Any, current: list[dict[str, Any]]
) -> bool:
    """Compare immutable member records across an audited path migration.

    Every production field remains exact. Only ``job_file`` may differ, and
    the legacy value must resolve through the migration index to the current
    descriptor named by the mutable armor-set job.
    """

    if recorded == current:
        return True
    if not isinstance(recorded, list) or len(recorded) != len(current):
        return False
    for sealed_record, current_record in zip(recorded, current, strict=True):
        if not isinstance(sealed_record, dict):
            return False
        sealed_copy = dict(sealed_record)
        current_copy = dict(current_record)
        sealed_job_file = sealed_copy.pop("job_file", None)
        current_job_file = current_copy.pop("job_file", None)
        if sealed_copy != current_copy or not current_job_file:
            return False
        if not state_path_matches_exact_file(
            sealed_job_file, resolve_path(str(current_job_file))
        ):
            return False
    return True


def armor_set_build_manifest_path(armor_set: dict[str, Any]) -> Path:
    return build_dir(armor_set) / "build-manifest.json"


def armor_set_source_registry_formats(
    infos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for info in infos:
        identity = (
            str(info["registry_magic"]),
            int(info["version"]),
            int(info["scale"]),
        )
        if identity in seen:
            continue
        seen.add(identity)
        result.append(
            {
                "registry_magic": identity[0],
                "registry_version": identity[1],
                "scale": identity[2],
            }
        )
    return result


def armor_set_output_registry_identity(
    armor_set: dict[str, Any], infos: list[dict[str, Any]]
) -> tuple[bytes, int, int]:
    contract = upscale_contract(armor_set)
    identities = {
        (str(info["registry_magic"]), int(info["version"]), int(info["scale"]))
        for info in infos
    }
    legacy_identity = (
        registry_magic_name(REGISTRY_MAGIC),
        REGISTRY_VERSION,
        LEGACY_SCALE,
    )
    xn_x2_identity = (
        registry_magic_name(XN_REGISTRY_MAGIC),
        XN_REGISTRY_VERSION,
        2,
    )
    xn_x4_identity = (
        registry_magic_name(XN_REGISTRY_MAGIC),
        XN_REGISTRY_VERSION,
        4,
    )
    if not contract.explicit:
        if identities != {legacy_identity}:
            raise RuntimeError("legacy armor set requires only V2/x2 member registries")
        return REGISTRY_MAGIC, REGISTRY_VERSION, LEGACY_SCALE
    if contract.scale == 2:
        if not identities or not identities.issubset({legacy_identity, xn_x2_identity}):
            raise RuntimeError(
                "explicit x2 armor set accepts only legacy V2/x2 or XN V3/x2 registries"
            )
        return XN_REGISTRY_MAGIC, XN_REGISTRY_VERSION, 2
    if identities != {xn_x4_identity}:
        raise RuntimeError("explicit x4 armor set requires only XN V3/x4 registries")
    return XN_REGISTRY_MAGIC, XN_REGISTRY_VERSION, 4


def registry_set_manifest_shards(info: dict[str, Any]) -> list[dict[str, Any]]:
    prefix = "iee-assets/creature-sprites/"
    return [
        {
            **shard,
            "registry": prefix + str(shard["registry"]),
        }
        for shard in info["shards"]
    ]


def verify_armor_set_build(armor_set: dict[str, Any]) -> dict[str, Any]:
    manifest_path = armor_set_build_manifest_path(armor_set)
    manifest = read_json(manifest_path)
    if manifest.get("schema") != ARMOR_SET_BUILD_SCHEMA:
        raise RuntimeError("unsupported armor-set build manifest")
    if manifest.get("status") != "built-pending-ingame-qa":
        raise RuntimeError("armor-set build is not pending ingame QA")
    if manifest.get("job_id") != armor_set["job_id"]:
        raise RuntimeError("armor-set build manifest job id differs from set")
    if str(manifest.get("animation_id", "")).upper() != armor_set["animation"]["id"].upper():
        raise RuntimeError("armor-set build manifest animation id differs from set")
    if manifest.get("runtime_profile") != armor_set["animation"]["runtime_profile"]:
        raise RuntimeError("armor-set build manifest runtime profile differs from set")
    expected_members = armor_set_member_records(armor_set)
    if not armor_set_member_records_match(manifest.get("members"), expected_members):
        raise RuntimeError("armor-set build members differ from current member jobs")
    expected_resources: list[str] = []
    expected_frames = 0
    expected_index_bytes = 0
    member_infos: list[dict[str, Any]] = []
    member_methods: list[dict[str, Any]] = []
    for member in armor_set["_members"]:
        member_manifest = read_json(build_dir(member) / "build-manifest.json")
        member_info = inspect_build_payload(build_dir(member), member_manifest)
        member_infos.append(member_info)
        member_methods.append(member_manifest.get("method"))
        expected_resources.extend(member_info["resources"])
        expected_frames += member_info["frame_count"]
        expected_index_bytes += member_info["index_bytes"]
    output_magic, output_version, output_scale = armor_set_output_registry_identity(
        armor_set, member_infos
    )
    if any(method != member_methods[0] for method in member_methods[1:]):
        raise RuntimeError("armor-set members mix upscale methods")
    if manifest.get("method") != upscale_contract(armor_set).method:
        raise RuntimeError("armor-set build method differs from set contract")
    if len(expected_resources) != len(set(expected_resources)):
        raise RuntimeError("armor-set members contain duplicate BAM resources")

    layout = str(manifest.get("registry_layout", "monolith"))
    if layout == "monolith":
        registry = build_dir(armor_set) / str(manifest.get("registry", ""))
        info = inspect_registry(registry)
        if info["sha256"] != manifest.get("registry_sha256"):
            raise RuntimeError("armor-set registry hash differs from build manifest")
        if registry.name != (
            XN_REGISTRY_FILENAME
            if output_magic == XN_REGISTRY_MAGIC
            else REGISTRY_FILENAME
        ):
            raise RuntimeError("armor-set registry filename differs from output format")
        if upscale_contract(armor_set).explicit and (
            manifest.get("registry_set") is not None
            or manifest.get("registry_set_sha256") is not None
            or manifest.get("registry_set_bytes") is not None
            or manifest.get("shards") != []
        ):
            raise RuntimeError("monolithic armor-set manifest has registry-set fields")
    elif layout == "set":
        if not upscale_contract(armor_set).explicit:
            raise RuntimeError("legacy armor sets cannot use registry-set layout")
        registry_set = build_dir(armor_set) / str(manifest.get("registry_set", ""))
        info = inspect_registry_set(registry_set)
        if (
            info["sha256"] != manifest.get("registry_set_sha256")
            or registry_set.name != XN_REGISTRY_SET_FILENAME
            or manifest.get("registry") is not None
            or manifest.get("registry_sha256") is not None
            or manifest.get("registry_set_bytes") != info["registry_set_bytes"]
            or manifest.get("shards") != registry_set_manifest_shards(info)
        ):
            raise RuntimeError("armor-set registry-set manifest differs from indexed shards")
    else:
        raise RuntimeError("unsupported armor-set registry layout")

    if info["animation_id"].upper() != armor_set["animation"]["id"].upper():
        raise RuntimeError("armor-set registry animation id differs from set")
    if info["resources"] != expected_resources:
        raise RuntimeError("armor-set registry resources differ from member registries")
    if info["frame_count"] != expected_frames:
        raise RuntimeError("armor-set registry frame count differs from member registries")
    if info["index_bytes"] != expected_index_bytes or info["index_bytes"] != int(
        manifest.get(f"x{output_scale}_index_bytes", -1)
    ):
        raise RuntimeError("armor-set index bytes differ from build manifest")
    if (
        manifest.get("resource_count") != info["resource_count"]
        or manifest.get("frame_count") != info["frame_count"]
        or manifest.get("registry_bytes") != info["registry_bytes"]
    ):
        raise RuntimeError("armor-set top-level counters differ from registries")
    validation = manifest.get("validation")
    shard_count = len(info["shards"]) if layout == "set" else 1
    expected_monolithic_bytes = (
        info["registry_bytes"] - (shard_count - 1) * REGISTRY_HEADER_BYTES
    )
    if not isinstance(validation, dict) or (
        validation.get("monolithic_registry_bytes_preflight")
        != expected_monolithic_bytes
        or validation.get("registry_bytes_preflight") != info["registry_bytes"]
        or validation.get("shard_count") != shard_count
        or validation.get("maximum_shard_resources") != MAX_RESOURCES
        or validation.get("maximum_shard_bytes")
        != maximum_registry_bytes(output_scale)
        or validation.get("maximum_set_shards") != MAX_REGISTRY_SET_SHARDS
        or validation.get("maximum_set_resources") != MAX_REGISTRY_SET_RESOURCES
        or validation.get("maximum_set_frames") != MAX_REGISTRY_SET_FRAMES
        or validation.get("maximum_set_registry_bytes") != MAX_REGISTRY_SET_BYTES
    ):
        raise RuntimeError("armor-set registry layout validation differs from payload")
    set_contract = upscale_contract(armor_set)
    if layout == "monolith" and (
        info["registry_magic"] != registry_magic_name(output_magic)
        or info["version"] != output_version
        or info["scale"] != output_scale
    ):
        raise RuntimeError("armor-set monolith format differs from set contract")
    if layout == "set" and (
        output_magic != XN_REGISTRY_MAGIC
        or info["registry_magic"] != registry_magic_name(XN_REGISTRY_SET_MAGIC)
        or info["version"] != XN_REGISTRY_SET_VERSION
        or info["scale"] != output_scale
    ):
        raise RuntimeError("armor-set registry-set format differs from set contract")
    if set_contract.explicit:
        source_formats = armor_set_source_registry_formats(member_infos)
        promoted_to_xn = any(
            info["registry_magic"] != registry_magic_name(XN_REGISTRY_MAGIC)
            or info["version"] != XN_REGISTRY_VERSION
            for info in member_infos
        )
        if (
            manifest.get("registry_magic") != registry_magic_name(output_magic)
            or manifest.get("registry_version") != output_version
            or manifest.get("registry_scale") != output_scale
            or manifest.get("source_registry_formats") != source_formats
            or manifest.get("promoted_to_xn") is not promoted_to_xn
            or manifest.get("total_resources") != info["resource_count"]
            or manifest.get("total_frames") != info["frame_count"]
            or manifest.get("total_index_bytes") != info["index_bytes"]
            or manifest.get("total_registry_bytes") != info["registry_bytes"]
        ):
            raise RuntimeError("armor-set xN manifest metadata differs from registries")
    return info


def armor_set_override_collisions(armor_set: dict[str, Any]) -> list[str]:
    override = job_path(armor_set, "game_root") / "override"
    if not override.is_dir():
        return []
    resources = {
        str(resource["name"]).upper()
        for member in armor_set["_members"]
        for resource in read_json(source_manifest_path(member)).get("bams", [])
    }
    return sorted(
        path.name
        for resref in resources
        if (path := override / f"{resref}.BAM").is_file()
    )


def build_armor_set(armor_set: dict[str, Any], force: bool, resume: bool) -> dict[str, Any]:
    output = build_dir(armor_set)
    if resume and output.exists():
        try:
            return {"status": "reused", **verify_armor_set_build(armor_set)}
        except (OSError, RuntimeError, ValueError, KeyError, TypeError):
            pass
    if output.exists() and not (force or resume):
        raise RuntimeError(f"armor-set build exists; use --resume or --force: {output}")
    members = armor_set_member_records(armor_set)
    total_resources = sum(int(member["resource_count"]) for member in members)
    total_frames = sum(int(member["frame_count"]) for member in members)
    set_contract = upscale_contract(armor_set)
    if total_resources > (
        MAX_REGISTRY_SET_RESOURCES if set_contract.explicit else MAX_RESOURCES
    ):
        raise RuntimeError("armor-set resources exceed aggregate format limit")
    if set_contract.explicit and total_frames > MAX_REGISTRY_SET_FRAMES:
        raise RuntimeError("armor-set frames exceed registry-set format limit")
    member_registries: list[dict[str, Any]] = []
    member_methods: list[dict[str, Any]] = []
    for member in armor_set["_members"]:
        member_manifest = read_json(build_dir(member) / "build-manifest.json")
        info = inspect_build_payload(
            build_dir(member),
            member_manifest,
            include_resource_records=True,
        )
        if info["animation_id"].upper() != armor_set["animation"]["id"].upper():
            raise RuntimeError("armor-set member registry animation id differs from set")
        member_registries.append(
            {"info": info, "manifest": member_manifest}
        )
        member_methods.append(member_manifest.get("method"))
    member_infos = [entry["info"] for entry in member_registries]
    registry_magic, registry_version, registry_scale = armor_set_output_registry_identity(
        armor_set, member_infos
    )
    shard_byte_limit = maximum_registry_bytes(registry_scale)
    if any(method != member_methods[0] for method in member_methods[1:]):
        raise RuntimeError("registry aggregation refuses mixed upscale methods")
    if member_methods[0] != set_contract.method:
        raise RuntimeError("armor-set upscale method differs from member registries")
    records = [
        record
        for entry in member_registries
        for record in entry["info"]["resource_records"]
    ]
    if len(records) != total_resources:
        raise RuntimeError("armor-set member record count differs from manifests")
    if len({str(record["resref"]) for record in records}) != len(records):
        raise RuntimeError("armor-set members contain duplicate BAM resources")
    projected_registry_bytes = REGISTRY_HEADER_BYTES + sum(
        int(record["bytes"]) for record in records
    )
    use_registry_set = set_contract.explicit and (
        total_resources > MAX_RESOURCES
        or projected_registry_bytes > shard_byte_limit
    )
    if not set_contract.explicit and (
        total_resources > MAX_RESOURCES or projected_registry_bytes > shard_byte_limit
    ):
        raise RuntimeError(
            "legacy armor-set aggregate exceeds the monolithic registry limits"
        )
    partitions = (
        partition_registry_resources(
            records,
            maximum_resources=MAX_RESOURCES,
            maximum_bytes=shard_byte_limit,
            maximum_shards=MAX_REGISTRY_SET_SHARDS,
        )
        if use_registry_set
        else [records]
    )
    projected_set_registry_bytes = sum(
        REGISTRY_HEADER_BYTES + sum(int(record["bytes"]) for record in partition)
        for partition in partitions
    )
    if use_registry_set and projected_set_registry_bytes > MAX_REGISTRY_SET_BYTES:
        raise RuntimeError(
            "registry-set preflight exceeds the 8 GiB aggregate registry limit"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="armor-set-", dir=output.parent))
    try:
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True)
        animation_id = int(armor_set["animation"]["id"], 16)
        registry_path: Path | None = None
        registry_set_path: Path | None = None
        if use_registry_set:
            shard_infos: list[dict[str, Any]] = []
            for index, shard_records in enumerate(partitions):
                shard_path = pack_dir / XN_REGISTRY_SHARD_FILENAME.format(index=index)
                shard_info = write_registry_records(
                    shard_path,
                    XN_REGISTRY_MAGIC,
                    XN_REGISTRY_VERSION,
                    registry_scale,
                    animation_id,
                    shard_records,
                )
                shard_info["path"] = shard_path
                shard_infos.append(shard_info)
            registry_set_path = pack_dir / XN_REGISTRY_SET_FILENAME
            info = write_registry_set_index(
                registry_set_path, registry_scale, animation_id, shard_infos
            )
            registry_layout = "set"
        else:
            registry_filename = (
                XN_REGISTRY_FILENAME
                if registry_magic == XN_REGISTRY_MAGIC
                else REGISTRY_FILENAME
            )
            registry_path = pack_dir / registry_filename
            info = write_registry_records(
                registry_path,
                registry_magic,
                registry_version,
                registry_scale,
                animation_id,
                records,
            )
            registry_layout = "monolith"
        if info["resource_count"] != total_resources:
            raise RuntimeError("armor-set registry resource count differs from members")
        if not use_registry_set and info["registry_bytes"] != projected_registry_bytes:
            raise RuntimeError("armor-set registry size differs from preflight")
        source_formats = armor_set_source_registry_formats(member_infos)
        promoted_to_xn = set_contract.explicit and any(
            member_info["registry_magic"] != registry_magic_name(XN_REGISTRY_MAGIC)
            or member_info["version"] != XN_REGISTRY_VERSION
            for member_info in member_infos
        )
        report = {
            "schema": ARMOR_SET_BUILD_SCHEMA,
            "status": "built-pending-ingame-qa",
            "created_at_utc": utc_now(),
            "job_id": armor_set["job_id"],
            "animation_id": armor_set["animation"]["id"],
            "ids_symbol": armor_set["animation"]["ids_symbol"],
            "runtime_profile": armor_set["animation"]["runtime_profile"],
            "armor_codes": armor_set_body_codes(armor_set),
            "bam_prefixes": [member["bam_prefix"] for member in members],
            "members": members,
            "registry_version": registry_version,
            "method": set_contract.method,
            "resource_count": info["resource_count"],
            "frame_count": info["frame_count"],
            f"x{registry_scale}_index_bytes": info["index_bytes"],
            "registry_layout": registry_layout,
            "registry": (
                f"iee-assets/creature-sprites/{registry_path.name}"
                if registry_path is not None
                else None
            ),
            "registry_bytes": info["registry_bytes"],
            "registry_sha256": info["sha256"] if registry_path is not None else None,
            "registry_set": (
                f"iee-assets/creature-sprites/{XN_REGISTRY_SET_FILENAME}"
                if registry_set_path is not None
                else None
            ),
            "registry_set_sha256": (
                info["sha256"] if registry_set_path is not None else None
            ),
            "registry_set_bytes": (
                info["registry_set_bytes"] if registry_set_path is not None else None
            ),
            "shards": registry_set_manifest_shards(info) if use_registry_set else [],
            "total_resources": info["resource_count"],
            "total_frames": info["frame_count"],
            "total_index_bytes": info["index_bytes"],
            "total_registry_bytes": info["registry_bytes"],
        }
        if registry_version == XN_REGISTRY_VERSION:
            report["registry_magic"] = registry_magic_name(registry_magic)
            report["registry_scale"] = registry_scale
            report["source_registry_formats"] = source_formats
            report["promoted_to_xn"] = promoted_to_xn
            report["validation"] = {
                "monolithic_registry_bytes_preflight": projected_registry_bytes,
                "registry_bytes_preflight": info["registry_bytes"],
                "shard_count": len(partitions),
                "maximum_shard_resources": MAX_RESOURCES,
                "maximum_shard_bytes": shard_byte_limit,
                "maximum_set_shards": MAX_REGISTRY_SET_SHARDS,
                "maximum_set_resources": MAX_REGISTRY_SET_RESOURCES,
                "maximum_set_frames": MAX_REGISTRY_SET_FRAMES,
                "maximum_set_registry_bytes": MAX_REGISTRY_SET_BYTES,
            }
        equipment_layers = armor_set_equipment_layers(armor_set)
        if equipment_layers:
            report["equipment_layers"] = equipment_layers
        write_json(temporary / "build-manifest.json", report)
        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)
        return {"status": "built", "registry_layout": registry_layout, **info}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def iter_catalog_record_logical_chunks(
    record: dict[str, Any], decoder: WindowsXpressHuffCodec | None
) -> Any:
    physical_bytes = int(record["bytes"])
    storage_version = int(record.get("storage_version", 0))
    if storage_version != XN_COMPRESSED_REGISTRY_VERSION:
        remaining = physical_bytes
        with Path(record["path"]).open("rb") as stream:
            stream.seek(int(record["offset"]))
            while remaining:
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RuntimeError(
                        f"truncated catalog source record: {record['resref']}"
                    )
                yield chunk
                remaining -= len(chunk)
        return
    if decoder is None:
        raise RuntimeError("compressed catalog record requires a decoder")
    with Path(record["path"]).open("rb") as stream:
        stream.seek(int(record["offset"]))
        raw = stream.read(physical_bytes)
    if len(raw) != physical_bytes:
        raise RuntimeError(f"truncated catalog V5 record: {record['resref']}")
    offset = 0
    resource_header = raw[:REGISTRY_RESOURCE_HEADER_BYTES]
    offset += REGISTRY_RESOURCE_HEADER_BYTES
    yield resource_header
    frame_count, cycle_count = struct.unpack_from("<II", resource_header, 40)
    logical_count = REGISTRY_RESOURCE_HEADER_BYTES
    scale = int(record["scale"])
    for _ in range(frame_count):
        end_header = offset + REGISTRY_FRAME_HEADER_BYTES
        if end_header > len(raw):
            raise RuntimeError("truncated catalog V5 frame header")
        frame_header = bytearray(raw[offset:end_header])
        offset = end_header
        width, height, _, _, _, stored_bytes = struct.unpack_from(
            "<HHhhB3xI", frame_header, 0
        )
        logical_bytes = width * height * scale * scale
        codec = frame_header[9]
        if (
            frame_header[10:12] != b"\0\0"
            or logical_bytes <= 0
            or logical_bytes > MAX_LAZY_FRAME_INDEX_BYTES
            or offset + stored_bytes > len(raw)
        ):
            raise RuntimeError("invalid catalog V5 frame")
        stored = raw[offset : offset + stored_bytes]
        offset += stored_bytes
        if codec == REGISTRY_FRAME_CODEC_RAW and stored_bytes == logical_bytes:
            payload = stored
        elif (
            codec == REGISTRY_FRAME_CODEC_XPRESS_HUFF
            and 0 < stored_bytes < logical_bytes
        ):
            payload = decoder.decode(stored, logical_bytes)
        else:
            raise RuntimeError("invalid catalog V5 frame codec")
        frame_header[9:12] = b"\0\0\0"
        struct.pack_into("<I", frame_header, 12, logical_bytes)
        yield bytes(frame_header)
        yield payload
        logical_count += REGISTRY_FRAME_HEADER_BYTES + logical_bytes
    for _ in range(cycle_count):
        if offset + 4 > len(raw):
            raise RuntimeError("truncated catalog V5 cycle")
        slots = struct.unpack_from("<I", raw, offset)[0]
        cycle_bytes = 4 + slots * 4
        if slots > MAX_CYCLE_SLOTS or offset + cycle_bytes > len(raw):
            raise RuntimeError("invalid catalog V5 cycle")
        yield raw[offset : offset + cycle_bytes]
        offset += cycle_bytes
        logical_count += cycle_bytes
    if offset != len(raw) or logical_count != int(record["logical_bytes"]):
        raise RuntimeError("catalog V5 logical record length differs")


def catalog_source_component_sha256(
    scale: int, records: list[dict[str, Any]]
) -> str:
    if scale not in {2, 4} or not records:
        raise RuntimeError("invalid catalog source component")
    digest = hashlib.sha256()
    digest.update(b"IEECSNC-SOURCE-COMPONENT-V1\0")
    digest.update(struct.pack("<II", scale, len(records)))
    previous = ""
    decoder_context: Any = (
        WindowsXpressHuffCodec(compress=False)
        if any(
            int(record.get("storage_version", 0))
            == XN_COMPRESSED_REGISTRY_VERSION
            for record in records
        )
        else contextlib.nullcontext(None)
    )
    with decoder_context as decoder:
        for record in records:
            resref = str(record["resref"])
            if resref <= previous:
                raise RuntimeError("catalog component resrefs must be unique and sorted")
            previous = resref
            record_bytes = int(record.get("logical_bytes", record["bytes"]))
            digest.update(resref.encode("ascii") + b"\0")
            digest.update(struct.pack("<Q", record_bytes))
            logical_bytes = 0
            for chunk in iter_catalog_record_logical_chunks(record, decoder):
                digest.update(chunk)
                logical_bytes += len(chunk)
            if logical_bytes != record_bytes:
                raise RuntimeError(
                    f"catalog logical record length differs: {resref}"
                )
    return digest.hexdigest().upper()


def verify_catalog_component_copy(
    scale: int, expected_source_digest: str, shard_paths: list[Path]
) -> None:
    records: list[dict[str, Any]] = []
    for shard_path in shard_paths:
        info = inspect_registry(shard_path, include_resource_records=True)
        records.extend(info["resource_records"])
    records.sort(key=lambda item: str(item["resref"]))
    actual = catalog_source_component_sha256(scale, records)
    if actual != expected_source_digest:
        raise RuntimeError(
            "catalog component output differs from its locked source records"
        )


def catalog_source_collection(catalog: dict[str, Any]) -> dict[str, Any]:
    generation_id = catalog_generation_id(catalog)
    cached = catalog.get("_catalog_source_collection")
    if isinstance(cached, dict) and cached.get("generation_id") == generation_id:
        return cached
    contract = upscale_contract(catalog)
    components_by_source_digest: dict[str, dict[str, Any]] = {}
    animation_entries: list[dict[str, Any]] = []
    source_members: list[dict[str, Any]] = []
    palette_frames = 0
    record_count = 0

    for member in catalog["_catalog_members"]:
        if member.get("_kind") == "armor-set":
            verify_armor_set_build(member)
        else:
            verify_sources(member, compare_game=True)
            verify_build(member)
        member_manifest_path = build_dir(member) / "build-manifest.json"
        member_manifest = read_json(member_manifest_path)
        if member_manifest.get("method") != contract.method:
            raise RuntimeError("catalog member upscale method differs from catalog")

        animation_id = str(member["animation"]["id"]).upper().replace("X", "x")
        component_source_digests: list[str] = []
        animation_resrefs: set[str] = set()
        bam_prefixes: list[str] = []
        for leaf in catalog_member_leaf_jobs(member):
            leaf_manifest_path = build_dir(leaf) / "build-manifest.json"
            leaf_manifest = read_json(leaf_manifest_path)
            leaf_info = inspect_build_payload(
                build_dir(leaf),
                leaf_manifest,
                include_resource_records=True,
            )
            if (
                leaf_info["scale"] != contract.scale
                or leaf_info["animation_id"].upper() != animation_id.upper()
                or leaf_manifest.get("method") != contract.method
            ):
                raise RuntimeError(
                    f"catalog leaf registry contract differs: {leaf['job_id']}"
                )
            if contract.scale == 4 and (
                leaf_info["registry_magic"]
                != registry_magic_name(XN_REGISTRY_MAGIC)
                or leaf_info["version"] != XN_REGISTRY_VERSION
            ):
                raise RuntimeError("x4 catalog requires only XN V3 leaf registries")
            if contract.scale == 2 and (
                leaf_info["registry_magic"], leaf_info["version"]
            ) not in {
                (registry_magic_name(REGISTRY_MAGIC), REGISTRY_VERSION),
                (registry_magic_name(XN_REGISTRY_MAGIC), XN_REGISTRY_VERSION),
            }:
                raise RuntimeError("x2 catalog leaf registry is not V2 or V3")
            validation = leaf_manifest.get("validation")
            if not isinstance(validation, dict) or (
                validation.get(f"dimensions_exact_x{contract.scale}")
                != leaf_info["frame_count"]
                or validation.get("frames_exactly_remapped_to_source_palette")
                != leaf_info["frame_count"]
                or validation.get("partial_alpha_pixels") != 0
                or validation.get("new_colors") != 0
            ):
                raise RuntimeError(
                    f"catalog leaf palette gates are incomplete: {leaf['job_id']}"
                )
            records = sorted(
                leaf_info["resource_records"], key=lambda item: str(item["resref"])
            )
            resrefs = [str(record["resref"]) for record in records]
            duplicates = animation_resrefs.intersection(resrefs)
            if duplicates:
                raise RuntimeError(
                    "duplicate catalog resref in animation scope: "
                    + ", ".join(sorted(duplicates))
                )
            animation_resrefs.update(resrefs)
            source_digest = catalog_source_component_sha256(contract.scale, records)
            signature = [
                {
                    "resref": str(record["resref"]),
                    "bytes": int(record["bytes"]),
                    "frame_count": int(record["frame_count"]),
                    "index_bytes": int(record["index_bytes"]),
                }
                for record in records
            ]
            component = {
                "source_digest": source_digest,
                "records": records,
                "signature": signature,
                "resource_count": leaf_info["resource_count"],
                "frame_count": leaf_info["frame_count"],
                "index_bytes": leaf_info["index_bytes"],
                "source_registry_bytes": leaf_info["registry_bytes"],
            }
            existing = components_by_source_digest.get(source_digest)
            if existing is None:
                components_by_source_digest[source_digest] = component
            elif existing["signature"] != signature:
                raise RuntimeError("catalog source component digest collision")
            component_source_digests.append(source_digest)
            bam_prefixes.append(str(leaf["animation"]["bam_prefix"]))
            palette_frames += int(leaf_info["frame_count"])
            record_count += int(leaf_info["resource_count"])

        if len(component_source_digests) != len(set(component_source_digests)):
            raise RuntimeError("catalog animation repeats an identical component")
        source_members.append(
            {
                "job_file": relative_project_path(Path(member["_job_file"])),
                "job_sha256": sha256_file(Path(member["_job_file"])),
                "job_id": member["job_id"],
                "animation_id": animation_id,
                "runtime_profile": member["animation"]["runtime_profile"],
                "build_manifest": relative_project_path(member_manifest_path),
                "build_manifest_sha256": sha256_file(member_manifest_path),
                "component_source_digests": component_source_digests,
                "bam_prefixes": bam_prefixes,
            }
        )
        animation_entries.append(
            {
                "animation_id": animation_id,
                "runtime_profile": member["animation"]["runtime_profile"],
                "owner": catalog_owner_for_profile(
                    member["animation"]["runtime_profile"]
                ),
                "component_source_digests": component_source_digests,
                "resources": sorted(animation_resrefs),
            }
        )

    components = [
        components_by_source_digest[digest]
        for digest in sorted(components_by_source_digest)
    ]
    if not (1 <= len(components) <= MAX_REGISTRY_CATALOG_COMPONENTS):
        raise RuntimeError("catalog component count exceeds the format limit")
    if len(animation_entries) > MAX_REGISTRY_CATALOG_ANIMATIONS:
        raise RuntimeError("catalog animation count exceeds the format limit")
    physical_resources = sum(int(item["resource_count"]) for item in components)
    physical_frames = sum(int(item["frame_count"]) for item in components)
    if (
        physical_resources > MAX_REGISTRY_CATALOG_RESOURCES
        or physical_frames > MAX_REGISTRY_CATALOG_FRAMES
    ):
        raise RuntimeError("catalog source inventory exceeds aggregate limits")
    result = {
        "generation_id": generation_id,
        "components": components,
        "animations": sorted(
            animation_entries, key=lambda item: int(item["animation_id"], 16)
        ),
        "source_members": sorted(
            source_members, key=lambda item: int(item["animation_id"], 16)
        ),
        "palette_frames": palette_frames,
        "resource_records_verified": record_count,
        "physical_resources": physical_resources,
        "physical_frames": physical_frames,
    }
    catalog["_catalog_source_collection"] = result
    return result


def catalog_manifest_animations(
    collection: dict[str, Any], source_indices: dict[str, int]
) -> list[dict[str, Any]]:
    owner_names = {
        CATALOG_OWNER_CHARACTER: "Character",
        CATALOG_OWNER_MONSTER_ICEWIND: "MonsterIcewind",
    }
    return [
        {
            "animation_id": animation["animation_id"],
            "runtime_profile": animation["runtime_profile"],
            "owner": owner_names[int(animation["owner"])],
            "component_indices": sorted(
                source_indices[value]
                for value in animation["component_source_digests"]
            ),
        }
        for animation in collection["animations"]
    ]


def catalog_manifest_source_members(
    collection: dict[str, Any], source_indices: dict[str, int]
) -> list[dict[str, Any]]:
    return [
        {
            "job_file": member["job_file"],
            "job_sha256": member["job_sha256"],
            "job_id": member["job_id"],
            "animation_id": member["animation_id"],
            "runtime_profile": member["runtime_profile"],
            "build_manifest": member["build_manifest"],
            "build_manifest_sha256": member["build_manifest_sha256"],
            "component_indices": sorted(
                source_indices[value]
                for value in member["component_source_digests"]
            ),
            "bam_prefixes": member["bam_prefixes"],
        }
        for member in collection["source_members"]
    ]


def catalog_override_collisions(
    catalog: dict[str, Any], resources: set[str] | None = None
) -> list[str]:
    override = job_path(catalog, "game_root") / "override"
    if not override.is_dir():
        return []
    if resources is None:
        resources = {
            str(resource["name"]).upper()
            for member in catalog["_catalog_members"]
            for leaf in catalog_member_leaf_jobs(member)
            for resource in read_json(source_manifest_path(leaf)).get("bams", [])
        }
    return sorted(
        path.name
        for resref in resources
        if (path := override / f"{resref}.BAM").is_file()
    )


def catalog_build_validation(
    collection: dict[str, Any], scale: int
) -> dict[str, Any]:
    return {
        "records_copied_without_xbr": True,
        "logical_records_preserved_after_lossless_storage_repack": True,
        "catalog_shard_registry_version": CATALOG_SHARD_REGISTRY_VERSION,
        "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
        "resource_records_sha256_verified": collection[
            "resource_records_verified"
        ],
        "palette_frames_exactly_remapped": collection["palette_frames"],
        "partial_alpha_pixels": 0,
        "new_colors": 0,
        "override_collisions": 0,
        "maximum_animations": MAX_REGISTRY_CATALOG_ANIMATIONS,
        "maximum_components": MAX_REGISTRY_CATALOG_COMPONENTS,
        "maximum_memberships": MAX_REGISTRY_CATALOG_MEMBERSHIPS,
        "maximum_shards": MAX_REGISTRY_CATALOG_SHARDS,
        "maximum_physical_resources": MAX_REGISTRY_CATALOG_RESOURCES,
        "maximum_frames": MAX_REGISTRY_CATALOG_FRAMES,
        "maximum_registry_bytes": MAX_REGISTRY_CATALOG_BYTES,
        "maximum_resources_per_shard": MAX_RESOURCES,
        "maximum_directory_entries": MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES,
        "maximum_shard_bytes": maximum_registry_bytes(scale),
        "game_launch_is_never_automatic": True,
        "release_manifest_is_out_of_scope": True,
    }


def build_catalog(
    catalog: dict[str, Any], force: bool, resume: bool
) -> dict[str, Any]:
    if force:
        raise RuntimeError(
            "catalog generations are immutable; change inputs or use --resume"
        )
    output = build_dir(catalog)
    if output.exists():
        if not resume:
            raise RuntimeError(f"catalog build exists; use --resume: {output}")
        return {"status": "reused", **verify_catalog_build(catalog)}
    collisions = catalog_override_collisions(catalog)
    if collisions:
        raise RuntimeError(f"override collision: {', '.join(collisions)}")
    collection = catalog_source_collection(catalog)
    generation_id = collection["generation_id"]
    contract = upscale_contract(catalog)
    generation = catalog_generation_dir(catalog)
    assert_workspace_child(generation, "catalog generation")
    generation.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="build-", dir=generation))
    try:
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True)
        shards: list[dict[str, Any]] = []
        output_components: list[dict[str, Any]] = []
        source_indices: dict[str, int] = {}
        seen_shard_hashes: set[str] = set()
        for component_index, component in enumerate(collection["components"]):
            source_indices[component["source_digest"]] = component_index
            partitions = partition_registry_resources(
                component["records"],
                maximum_resources=MAX_RESOURCES,
                maximum_bytes=maximum_registry_bytes(contract.scale),
                maximum_shards=MAX_REGISTRY_SET_SHARDS,
            )
            shard_start = len(shards)
            raw_entries: list[bytes] = []
            for local_index, records in enumerate(partitions):
                scratch = pack_dir / f".component-{component_index:05d}-{local_index:04d}.tmp"
                info = write_compressed_catalog_registry_records(
                    scratch,
                    contract.scale,
                    records,
                )
                if info["sha256"] in seen_shard_hashes:
                    raise RuntimeError(
                        "catalog shard is shared by nonidentical components"
                    )
                seen_shard_hashes.add(info["sha256"])
                final_path = pack_dir / catalog_shard_filename(info["sha256"])
                if final_path.exists():
                    raise RuntimeError("catalog content-addressed shard already exists")
                object_path = publish_catalog_shard_object(
                    catalog, scratch, final_path, info["sha256"]
                )
                shard = {
                    "index": len(shards),
                    "path": final_path,
                    "object_path": object_path,
                    **info,
                }
                shards.append(shard)
                raw_entries.append(catalog_shard_entry_bytes(info, final_path))
            verify_catalog_component_copy(
                contract.scale,
                component["source_digest"],
                [Path(shard["path"]) for shard in shards[shard_start:]],
            )
            output_components.append(
                {
                    "index": component_index,
                    "digest": catalog_component_digest(contract.scale, raw_entries),
                    "shard_start": shard_start,
                    "shard_count": len(partitions),
                    "resource_count": sum(
                        int(shard["resource_count"])
                        for shard in shards[shard_start:]
                    ),
                    "frame_count": sum(
                        int(shard["frame_count"])
                        for shard in shards[shard_start:]
                    ),
                    "index_bytes": sum(
                        int(shard["index_bytes"])
                        for shard in shards[shard_start:]
                    ),
                    "registry_bytes": sum(
                        int(shard["registry_bytes"])
                        for shard in shards[shard_start:]
                    ),
                }
            )
        if len(shards) > MAX_REGISTRY_CATALOG_SHARDS:
            raise RuntimeError("catalog shard count exceeds the format limit")
        manifest_animations = catalog_manifest_animations(
            collection, source_indices
        )
        binary_animations = [
            {
                "animation_id": animation["animation_id"],
                "owner": catalog_owner_for_profile(animation["runtime_profile"]),
                "component_indices": animation["component_indices"],
            }
            for animation in manifest_animations
        ]
        catalog_path = pack_dir / XN_REGISTRY_CATALOG_FILENAME
        info = write_registry_catalog(
            catalog_path,
            contract.scale,
            binary_animations,
            output_components,
            shards,
        )
        input_lock = catalog_input_lock(catalog, refresh=True)
        if canonical_json_sha256(input_lock) != generation_id:
            raise RuntimeError("catalog inputs changed during generation")
        source_members = catalog_manifest_source_members(
            collection, source_indices
        )
        job_file = Path(catalog["_job_file"])
        job_sha256 = sha256_file(job_file)
        job_snapshot_relative = "provenance/job.json"
        job_snapshot_path = temporary / Path(job_snapshot_relative)
        job_snapshot_path.parent.mkdir(parents=True)
        shutil.copyfile(job_file, job_snapshot_path)
        if sha256_file(job_snapshot_path) != job_sha256:
            raise RuntimeError("catalog job snapshot differs from its source")
        report = {
            "schema": CATALOG_BUILD_SCHEMA,
            "status": "built-pending-ingame-qa",
            "created_at_utc": utc_now(),
            "job_file": relative_project_path(Path(catalog["_job_file"])),
            "job_sha256": job_sha256,
            "job_snapshot": job_snapshot_relative,
            "job_snapshot_sha256": job_sha256,
            "job_id": catalog["job_id"],
            "generation_id": generation_id,
            "method": contract.method,
            "registry_layout": "catalog",
            "animation_ids": [
                animation["animation_id"] for animation in manifest_animations
            ],
            "runtime_profiles": runtime_profiles_for_work_item(catalog),
            "registry_catalog": (
                "iee-assets/creature-sprites/" + XN_REGISTRY_CATALOG_FILENAME
            ),
            "registry_catalog_magic": registry_magic_name(
                XN_REGISTRY_CATALOG_MAGIC
            ),
            "registry_catalog_version": XN_REGISTRY_CATALOG_VERSION,
            "registry_catalog_shard_version": info[
                "shard_registry_version"
            ],
            "registry_catalog_frame_storage": (
                "XPRESS_HUFF-or-raw-per-frame-v1"
                if info["shard_registry_version"]
                == XN_COMPRESSED_REGISTRY_VERSION
                else "raw-v3"
            ),
            "shard_object_store": relative_project_path(
                catalog_object_store_dir(catalog)
            ),
            "shards_hardlinked_from_object_store": True,
            "registry_scale": contract.scale,
            "registry_catalog_sha256": info["sha256"],
            "registry_catalog_bytes": info["registry_catalog_bytes"],
            "registry_catalog_directory_count": info["directory_count"],
            "registry_catalog_directory_entry_bytes": info[
                "directory_entry_bytes"
            ],
            "registry_catalog_directory_sha256": info["directory_sha256"],
            "registry_catalog_logical_component_digests": info[
                "logical_component_digests"
            ],
            "registry_catalog_logical_content_sha256": info[
                "logical_content_sha256"
            ],
            "animations": manifest_animations,
            "components": info["components"],
            "shards": info["shards"],
            "totals": {
                "total_resources": info["total_resources"],
                "total_frames": info["total_frames"],
                "total_index_bytes": info["total_index_bytes"],
                "total_registry_bytes": info["total_registry_bytes"],
            },
            "storage": {
                "shard_registry_version": info["shard_registry_version"],
                "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                "stored_index_bytes": info["stored_index_bytes"],
                "compressed_frame_count": info["compressed_frame_count"],
                "raw_frame_count": info["raw_frame_count"],
                "index_storage_ratio": info["index_storage_ratio"],
            },
            "source_members": source_members,
            "locks": {
                "input_lock_sha256": generation_id,
                "engine_source_contract_sha256": input_lock[
                    "engine_source_contract_sha256"
                ],
                "baldur_real_sha256": input_lock["baldur_real_sha256"],
                "member_count": len(source_members),
                "leaf_job_count": len(input_lock["leaf_jobs"]),
                "input_lock": input_lock,
            },
            "validation": catalog_build_validation(collection, contract.scale),
        }
        write_json(temporary / "build-manifest.json", report)
        if output.exists():
            raise RuntimeError("catalog build appeared during generation")
        temporary.replace(output)
        return {"status": "built", "generation_id": generation_id, **info}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_catalog_build(catalog: dict[str, Any]) -> dict[str, Any]:
    collection = catalog_source_collection(catalog)
    generation_id = collection["generation_id"]
    manifest_path = build_dir(catalog) / "build-manifest.json"
    manifest = read_json(manifest_path)
    contract = upscale_contract(catalog)
    job_file = Path(catalog["_job_file"])
    job_sha256 = sha256_file(job_file)
    job_snapshot_relative = manifest.get("job_snapshot")
    job_snapshot_sha256 = manifest.get("job_snapshot_sha256")
    if job_snapshot_relative is not None or job_snapshot_sha256 is not None:
        if (
            job_snapshot_relative != "provenance/job.json"
            or job_snapshot_sha256 != job_sha256
        ):
            raise RuntimeError("catalog job snapshot declaration is invalid")
        job_snapshot_path = manifest_path.parent / Path(job_snapshot_relative)
        if (
            not job_snapshot_path.is_file()
            or sha256_file(job_snapshot_path) != job_sha256
        ):
            raise RuntimeError("catalog job snapshot differs from the catalog job")
        job_snapshot = read_json(job_snapshot_path)
        if (
            job_snapshot.get("schema") != CATALOG_JOB_SCHEMA
            or job_snapshot.get("job_id") != catalog["job_id"]
        ):
            raise RuntimeError("catalog job snapshot identity is invalid")
    if (
        manifest.get("schema") != CATALOG_BUILD_SCHEMA
        or manifest.get("status") != "built-pending-ingame-qa"
        or manifest.get("job_id") != catalog["job_id"]
        or manifest.get("job_file")
        != relative_project_path(Path(catalog["_job_file"]))
        or manifest.get("job_sha256") != job_sha256
        or manifest.get("generation_id") != generation_id
        or manifest.get("method") != contract.method
        or manifest.get("registry_layout") != "catalog"
        or manifest.get("runtime_profiles")
        != runtime_profiles_for_work_item(catalog)
        or manifest.get("registry_catalog")
        != "iee-assets/creature-sprites/" + XN_REGISTRY_CATALOG_FILENAME
        or manifest.get("registry_catalog_magic")
        != registry_magic_name(XN_REGISTRY_CATALOG_MAGIC)
        or manifest.get("registry_catalog_version")
        != XN_REGISTRY_CATALOG_VERSION
        or manifest.get("registry_catalog_shard_version")
        != CATALOG_SHARD_REGISTRY_VERSION
        or manifest.get("registry_catalog_frame_storage")
        != "XPRESS_HUFF-or-raw-per-frame-v1"
        or manifest.get("shard_object_store")
        != relative_project_path(catalog_object_store_dir(catalog))
        or manifest.get("shards_hardlinked_from_object_store") is not True
        or manifest.get("registry_scale") != contract.scale
    ):
        raise RuntimeError("catalog build manifest differs from the catalog job")
    catalog_path = build_dir(catalog) / str(manifest["registry_catalog"])
    info = inspect_registry_catalog(catalog_path)
    object_store = catalog_object_store_dir(catalog)
    for shard in info["shards"]:
        filename = Path(str(shard["registry"])).name
        generation_shard = catalog_path.parent / filename
        object_shard = object_store / filename
        if (
            not object_shard.is_file()
            or not generation_shard.is_file()
            or not os.path.samefile(object_shard, generation_shard)
            or sha256_file(object_shard) != shard["sha256"]
        ):
            raise RuntimeError("catalog generation shard differs from shared CAS")
    if (
        info["sha256"] != manifest.get("registry_catalog_sha256")
        or info["registry_catalog_bytes"]
        != manifest.get("registry_catalog_bytes")
        or info["directory_count"]
        != manifest.get("registry_catalog_directory_count")
        or info["directory_entry_bytes"]
        != manifest.get("registry_catalog_directory_entry_bytes")
        or info["directory_sha256"]
        != manifest.get("registry_catalog_directory_sha256")
        or info["logical_component_digests"]
        != manifest.get("registry_catalog_logical_component_digests")
        or info["logical_content_sha256"]
        != manifest.get("registry_catalog_logical_content_sha256")
        or info["scale"] != contract.scale
        or info["version"] != XN_REGISTRY_CATALOG_VERSION
        or info["shard_registry_version"]
        != manifest.get("registry_catalog_shard_version")
    ):
        raise RuntimeError("catalog index differs from build manifest")
    source_indices = {
        component["source_digest"]: index
        for index, component in enumerate(collection["components"])
    }
    expected_animations = catalog_manifest_animations(collection, source_indices)
    expected_binary_animations = [
        {
            "animation_id": animation["animation_id"],
            "owner": catalog_owner_for_profile(animation["runtime_profile"]),
            "membership_start": info["animations"][index]["membership_start"],
            "membership_count": len(animation["component_indices"]),
            "component_indices": animation["component_indices"],
        }
        for index, animation in enumerate(expected_animations)
    ]
    if (
        manifest.get("animation_ids")
        != [entry["animation_id"] for entry in expected_animations]
        or manifest.get("animations") != expected_animations
        or info["animations"] != expected_binary_animations
        or manifest.get("components") != info["components"]
        or manifest.get("shards") != info["shards"]
        or manifest.get("totals")
        != {
            "total_resources": info["total_resources"],
            "total_frames": info["total_frames"],
            "total_index_bytes": info["total_index_bytes"],
            "total_registry_bytes": info["total_registry_bytes"],
        }
        or manifest.get("storage")
        != {
            "shard_registry_version": info["shard_registry_version"],
            "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
            "stored_index_bytes": info["stored_index_bytes"],
            "compressed_frame_count": info["compressed_frame_count"],
            "raw_frame_count": info["raw_frame_count"],
            "index_storage_ratio": info["index_storage_ratio"],
        }
        or manifest.get("source_members")
        != catalog_manifest_source_members(collection, source_indices)
    ):
        raise RuntimeError("catalog manifest mappings differ from indexed payload")
    input_lock = catalog_input_lock(catalog, refresh=True)
    if canonical_json_sha256(input_lock) != generation_id:
        raise RuntimeError("catalog inputs changed while verifying the generation")
    expected_locks = {
        "input_lock_sha256": generation_id,
        "engine_source_contract_sha256": input_lock[
            "engine_source_contract_sha256"
        ],
        "baldur_real_sha256": input_lock["baldur_real_sha256"],
        "member_count": len(collection["source_members"]),
        "leaf_job_count": len(input_lock["leaf_jobs"]),
        "input_lock": input_lock,
    }
    if manifest.get("locks") != expected_locks or manifest.get(
        "validation"
    ) != catalog_build_validation(collection, contract.scale):
        raise RuntimeError("catalog build locks or validation gates differ")
    resources = {
        resref
        for values in info["animation_resources"].values()
        for resref in values
    }
    collisions = catalog_override_collisions(catalog, resources)
    if collisions:
        raise RuntimeError(f"override collision: {', '.join(collisions)}")
    return {
        "generation_id": generation_id,
        "registry_catalog": str(catalog_path),
        **info,
    }


def catalog_pointer_value(catalog: dict[str, Any]) -> dict[str, Any]:
    generation = catalog_generation_dir(catalog)
    build_manifest = generation / "build" / "build-manifest.json"
    runtime_manifest = generation / "runtime" / "runtime-manifest.json"
    if not build_manifest.is_file() or not runtime_manifest.is_file():
        raise RuntimeError("catalog generation is missing build or runtime manifest")
    return {
        "schema": CATALOG_POINTER_SCHEMA,
        "generation_id": catalog_generation_id(catalog),
        "job_sha256": sha256_file(Path(catalog["_job_file"])),
        "generation_dir": relative_project_path(generation),
        "build_manifest": "build/build-manifest.json",
        "build_manifest_sha256": sha256_file(build_manifest),
        "runtime_manifest": "runtime/runtime-manifest.json",
        "runtime_manifest_sha256": sha256_file(runtime_manifest),
    }


def write_catalog_pointer(catalog: dict[str, Any]) -> dict[str, Any]:
    value = catalog_pointer_value(catalog)
    pointer = catalog_pointer_path(catalog)
    assert_workspace_child(pointer, "catalog generation pointer")
    write_json(pointer, value)
    return value


def verify_catalog_pointer(catalog: dict[str, Any]) -> dict[str, Any]:
    pointer = catalog_pointer_path(catalog)
    value = read_json(pointer)
    expected = catalog_pointer_value(catalog)
    if value != expected:
        raise RuntimeError("catalog current-generation pointer differs from inputs")
    return value


def verify_armor_set(armor_set: dict[str, Any]) -> dict[str, Any]:
    game = job_path(armor_set, "game_root")
    if sha256_file(game / "BaldurReal.exe") != armor_set["compatibility"]["baldur_real_sha256"].upper():
        raise RuntimeError("BaldurReal.exe is incompatible with the armor set")
    build = verify_armor_set_build(armor_set)
    runtime = verify_runtime(armor_set)
    collisions = armor_set_override_collisions(armor_set)
    if collisions:
        raise RuntimeError(f"override collision: {', '.join(collisions)}")
    return {
        "status": "prepared-verified",
        "build": build,
        "runtime": runtime,
        "armor_codes": armor_set_body_codes(armor_set),
        "equipment_layers": armor_set_equipment_layers(armor_set),
        "bam_prefixes": armor_set_prefixes(armor_set),
        "override_collisions": 0,
    }


def prepare_armor_set(armor_set: dict[str, Any], force: bool, resume: bool) -> dict[str, Any]:
    build_armor_set(armor_set, force, resume)
    build_runtime(armor_set)
    return verify_armor_set(armor_set)


def plan_armor_set(armor_set: dict[str, Any]) -> dict[str, Any]:
    game = job_path(armor_set, "game_root")
    expected = armor_set["compatibility"]["baldur_real_sha256"].upper()
    contract = effective_upscale_contract(armor_set)
    build_manifest = armor_set_build_manifest_path(armor_set)
    build_layout = None
    if build_manifest.is_file():
        try:
            build_layout = str(
                read_json(build_manifest).get("registry_layout", "monolith")
            )
        except (OSError, RuntimeError, ValueError, TypeError):
            build_layout = "invalid-manifest"
    return {
        "job_id": armor_set["job_id"],
        "method": upscale_method_description(contract),
        "runtime_profile_supported": True,
        "animation_id": armor_set["animation"]["id"],
        "ids_symbol": armor_set["animation"]["ids_symbol"],
        "armor_codes": armor_set_body_codes(armor_set),
        "equipment_layers": armor_set_equipment_layers(armor_set),
        "bam_prefixes": armor_set_prefixes(armor_set),
        "baldur_real_compatible": (game / "BaldurReal.exe").is_file()
        and sha256_file(game / "BaldurReal.exe") == expected,
        "member_jobs": [member["job_id"] for member in armor_set["_members"]],
        "build_manifest_exists": build_manifest.is_file(),
        "build_registry_layout": build_layout,
        "registry_layout_policy": (
            "auto-shard-explicit-xn" if contract.explicit else "monolith-only-legacy"
        ),
        "maximum_shard_bytes": maximum_registry_bytes(contract.scale),
        "maximum_set_shards": MAX_REGISTRY_SET_SHARDS if contract.explicit else 1,
        "maximum_set_resources": (
            MAX_REGISTRY_SET_RESOURCES if contract.explicit else MAX_RESOURCES
        ),
        "maximum_set_frames": (
            MAX_REGISTRY_SET_FRAMES if contract.explicit else None
        ),
        "maximum_set_registry_bytes": (
            MAX_REGISTRY_SET_BYTES if contract.explicit else None
        ),
        "runtime_manifest_exists": (runtime_dir(armor_set) / "runtime-manifest.json").is_file(),
        "install_is_explicit": True,
        "game_launch_is_never_automatic": True,
        "release_manifest_is_out_of_scope": True,
    }


def plan_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    game = job_path(catalog, "game_root")
    exe = game / "BaldurReal.exe"
    expected = catalog["compatibility"]["baldur_real_sha256"].upper()
    contract = upscale_contract(catalog)
    generation_id: str | None = None
    generation_error: str | None = None
    generation: Path | None = None
    try:
        generation_id = catalog_generation_id(catalog)
        generation = catalog_generation_dir(catalog)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        generation_error = str(error)
    return {
        "job_id": catalog["job_id"],
        "method": upscale_method_description(contract),
        "animation_ids": [
            member["animation"]["id"] for member in catalog["_catalog_members"]
        ],
        "runtime_profiles": runtime_profiles_for_work_item(catalog),
        "member_jobs": [
            member["job_id"] for member in catalog["_catalog_members"]
        ],
        "leaf_job_count": sum(
            len(catalog_member_leaf_jobs(member))
            for member in catalog["_catalog_members"]
        ),
        "baldur_real_compatible": exe.is_file()
        and sha256_file(exe) == expected,
        "generation_id": generation_id,
        "generation_error": generation_error,
        "generation_dir": str(generation) if generation is not None else None,
        "build_manifest_exists": bool(
            generation is not None
            and (generation / "build" / "build-manifest.json").is_file()
        ),
        "runtime_manifest_exists": bool(
            generation is not None
            and (generation / "runtime" / "runtime-manifest.json").is_file()
        ),
        "current_generation_pointer_exists": catalog_pointer_path(
            catalog
        ).is_file(),
        "registry_layout_policy": "content-addressed-multi-animation-catalog",
        "shard_object_store": str(catalog_object_store_dir(catalog)),
        "generation_shards_are_hardlinks": True,
        "game_install_shards_are_independent_copies": True,
        "maximum_animations": MAX_REGISTRY_CATALOG_ANIMATIONS,
        "maximum_components": MAX_REGISTRY_CATALOG_COMPONENTS,
        "maximum_memberships": MAX_REGISTRY_CATALOG_MEMBERSHIPS,
        "maximum_shards": MAX_REGISTRY_CATALOG_SHARDS,
        "maximum_physical_resources": MAX_REGISTRY_CATALOG_RESOURCES,
        "maximum_frames": MAX_REGISTRY_CATALOG_FRAMES,
        "maximum_registry_bytes": MAX_REGISTRY_CATALOG_BYTES,
        "maximum_directory_entries": MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES,
        "maximum_shard_bytes": maximum_registry_bytes(contract.scale),
        "import_active_state": catalog.get("installation", {}).get(
            "import_active_state"
        ),
        "install_is_explicit": True,
        "game_launch_is_never_automatic": True,
        "release_manifest_is_out_of_scope": True,
    }


def verify_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    game = job_path(catalog, "game_root")
    expected = catalog["compatibility"]["baldur_real_sha256"].upper()
    if sha256_file(game / "BaldurReal.exe") != expected:
        raise RuntimeError("BaldurReal.exe is incompatible with the catalog")
    build = verify_catalog_build(catalog)
    runtime = verify_runtime(catalog)
    pointer = verify_catalog_pointer(catalog)
    return {
        "status": "prepared-verified",
        "generation_id": build["generation_id"],
        "animation_ids": [
            animation["animation_id"] for animation in build["animations"]
        ],
        "runtime_profiles": runtime_profiles_for_work_item(catalog),
        "build": build,
        "runtime": runtime,
        "pointer": pointer,
        "override_collisions": 0,
    }


def prepare_catalog(
    catalog: dict[str, Any], force: bool, resume: bool
) -> dict[str, Any]:
    build_catalog(catalog, force=force, resume=resume)
    build_runtime(catalog)
    return verify_catalog(catalog)


def runtime_log_session_after_install(
    text: str, exact_marker: str | tuple[str, ...], installed_at_utc: str
) -> str:
    try:
        installed = datetime.fromisoformat(installed_at_utc.replace("Z", "+00:00"))
        installed_local = installed.astimezone().replace(tzinfo=None)
    except ValueError:
        return ""
    lines = text.splitlines()
    start = -1
    start_timestamp: datetime | None = None
    markers = (exact_marker,) if isinstance(exact_marker, str) else exact_marker
    if not markers:
        return ""
    timestamp_pattern = re.compile(
        r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)\]"
    )
    for index, line in enumerate(lines):
        if not any(marker in line for marker in markers):
            continue
        match = timestamp_pattern.match(line)
        if not match:
            continue
        try:
            timestamp = datetime.fromisoformat(match.group(1))
        except ValueError:
            continue
        if timestamp >= installed_local and (
            start_timestamp is None
            or timestamp > start_timestamp
            or (timestamp == start_timestamp and index > start)
        ):
            start = index
            start_timestamp = timestamp
    return "\n".join(lines[start:]) if start >= 0 else ""


def runtime_owner_labels(profile: str) -> tuple[str, str]:
    if profile == "character-bg2ee-2.7.3.0":
        return "Character::Render", "CGameAnimationTypeCharacter::Render"
    return "MonsterIcewind::Render", "CGameAnimationTypeMonsterIcewind::Render"


def animation_composition_lines(
    session: str, animation_id: str, bam_prefix: str
) -> list[str]:
    canonical_id = f"0x{int(animation_id, 16):04X}"
    prefix_marker = f"Composing creature sprite {bam_prefix}"
    animation_marker = f" animation={canonical_id} "
    return [
        line
        for line in session.splitlines()
        if prefix_marker in line and animation_marker in line
    ]


def runtime_session_health(
    session: str,
    profile: str,
    composition_by_prefix: dict[str, list[str]],
) -> dict[str, Any]:
    character_runtime = profile == "character-bg2ee-2.7.3.0"
    pool_resets = session.count("Engine texture pool reset observed")
    unbound_warnings = session.count("No GL texture is bound")
    transient_failures = session.count("Character transient replacement failed")
    pixel_failures = session.count("Character pixel composition failed")
    backing_rejections = session.count("Character replacement backing rejected")
    unsafe_in_place_uploads = session.count("in-place (NEAREST")
    lazy_payload_failures = session.count(
        "Creature sprite lazy pack disabled after payload failure"
    )
    catalog_component_quarantines = sum(
        1
        for line in session.splitlines()
        if "Creature sprite catalog component " in line and " quarantined:" in line
    )
    transient_by_prefix = {
        prefix: any(
            "transient replacement id" in line
            and "delete-pending after queued draw" in line
            for line in lines
        )
        for prefix, lines in composition_by_prefix.items()
    }
    character_transient = not character_runtime or all(transient_by_prefix.values())
    return {
        "texture_pool_reset_count": pool_resets,
        "unbound_texture_warning_count": unbound_warnings,
        "character_transient_failure_count": transient_failures,
        "character_pixel_failure_count": pixel_failures,
        "character_backing_rejection_count": backing_rejections,
        "character_unsafe_in_place_count": unsafe_in_place_uploads,
        "lazy_payload_failure_count": lazy_payload_failures,
        "catalog_component_quarantine_count": catalog_component_quarantines,
        "character_transient_by_prefix": transient_by_prefix,
        "runtime_health_pass": bool(
            pool_resets == 0
            and unbound_warnings == 0
            and transient_failures == 0
            and pixel_failures == 0
            and backing_rejections == 0
            and unsafe_in_place_uploads == 0
            and lazy_payload_failures == 0
            and catalog_component_quarantines == 0
            and character_transient
        ),
    }


def installed_xn_state_contract_errors(
    state: dict[str, Any],
    targets_by_path: dict[str, dict[str, Any]],
    expected_scale: int | None,
) -> list[str]:
    errors: list[str] = []

    def path_key(value: Any) -> str:
        return str(value).replace("\\", "/").casefold()

    def require_target(relative_path: str, expected_present: bool) -> dict[str, Any] | None:
        target = targets_by_path.get(path_key(relative_path))
        if target is None:
            errors.append(f"required installed target is missing: {relative_path}")
            return None
        if target.get("installed_present") is not expected_present:
            errors.append(f"installed target layout differs: {relative_path}")
        return target

    if state.get("schema") != XN_INSTALL_STATE_SCHEMA:
        errors.append("xN installation state schema is not v2")
    layout = state.get("registry_layout")
    if layout not in {"monolith", "set"}:
        errors.append("xN installation registry layout is invalid")
        return errors
    if (
        state.get("registry_magic") != registry_magic_name(XN_REGISTRY_MAGIC)
        or state.get("registry_version") != XN_REGISTRY_VERSION
        or isinstance(state.get("registry_scale"), bool)
        or state.get("registry_scale") not in MAX_REGISTRY_BYTES_BY_SCALE
        or (
            expected_scale is not None
            and state.get("registry_scale") != expected_scale
        )
    ):
        errors.append("xN installation registry contract is invalid")

    sprite_root = "iee-assets/creature-sprites/"
    monolith_relative = sprite_root + XN_REGISTRY_FILENAME
    legacy_relative = sprite_root + REGISTRY_FILENAME
    set_relative = sprite_root + XN_REGISTRY_SET_FILENAME
    allowed_core = {
        path_key("InfinityEngine-Enhancer.dll"),
        path_key("InfinityEngine-Enhancer.ini"),
        path_key(monolith_relative),
        path_key(legacy_relative),
        path_key(set_relative),
    }
    shard_pattern = re.compile(
        re.escape(path_key(sprite_root))
        + r"creaturesprites-xn-[0-9]{4}\.registry"
    )
    for relative in targets_by_path:
        if relative not in allowed_core and shard_pattern.fullmatch(relative) is None:
            errors.append(f"installed target is outside the xN namespace: {relative}")

    require_target("InfinityEngine-Enhancer.dll", True)
    require_target("InfinityEngine-Enhancer.ini", True)
    if targets_by_path.get(path_key(legacy_relative)) is None:
        errors.append(f"required installed target is missing: {legacy_relative}")
    source_shards = state.get("source_shards")
    if not isinstance(source_shards, list):
        errors.append("xN installation source_shards is invalid")
        source_shards = []

    if layout == "monolith":
        primary_relative = monolith_relative
        primary_target = require_target(monolith_relative, True)
        require_target(set_relative, False)
        if (
            state.get("registry_shard_count") != 0
            or source_shards
            or "registry_set_magic" not in state
            or state.get("registry_set_magic") is not None
            or "registry_set_version" not in state
            or state.get("registry_set_version") is not None
        ):
            errors.append("monolithic xN installation has registry-set metadata")
        for relative, target in targets_by_path.items():
            if shard_pattern.fullmatch(relative) and target.get("installed_present") is not False:
                errors.append(f"monolithic xN installation retains a shard: {relative}")
    else:
        primary_relative = set_relative
        primary_target = require_target(set_relative, True)
        require_target(monolith_relative, False)
        shard_count = state.get("registry_shard_count")
        if (
            state.get("registry_set_magic") != "IEECSNS"
            or state.get("registry_set_version") != XN_REGISTRY_SET_VERSION
            or isinstance(shard_count, bool)
            or not isinstance(shard_count, int)
            or not (1 <= shard_count <= MAX_REGISTRY_SET_SHARDS)
            or len(source_shards) != shard_count
        ):
            errors.append("registry-set installation metadata is invalid")
            shard_count = len(source_shards)
        declared_shards: set[str] = set()
        for index, source_shard in enumerate(source_shards):
            expected_relative = sprite_root + XN_REGISTRY_SHARD_FILENAME.format(
                index=index
            )
            expected_key = path_key(expected_relative)
            declared_shards.add(expected_key)
            if not isinstance(source_shard, dict):
                errors.append(f"registry-set source shard {index} is invalid")
                continue
            source_hash = str(source_shard.get("sha256", "")).upper()
            source_crc32 = source_shard.get("crc32")
            if (
                isinstance(source_shard.get("index"), bool)
                or source_shard.get("index") != index
                or path_key(source_shard.get("relative_path", "")) != expected_key
                or re.fullmatch(r"[0-9A-F]{64}", source_hash) is None
                or isinstance(source_crc32, bool)
                or not isinstance(source_crc32, int)
                or not (0 <= source_crc32 <= 0xFFFFFFFF)
            ):
                errors.append(f"registry-set source shard {index} metadata is invalid")
            target = require_target(expected_relative, True)
            if target is not None and str(
                target.get("installed_sha256", "")
            ).upper() != source_hash:
                errors.append(f"registry-set source shard {index} hash differs from target")
        for relative, target in targets_by_path.items():
            if (
                shard_pattern.fullmatch(relative)
                and relative not in declared_shards
                and target.get("installed_present") is not False
            ):
                errors.append(f"registry-set installation retains an undeclared shard: {relative}")

    if path_key(state.get("registry_relative_path", "")) != path_key(primary_relative):
        errors.append("xN installation primary registry target is invalid")
    source_pack_hash = str(state.get("source_pack_sha256", "")).upper()
    if re.fullmatch(r"[0-9A-F]{64}", source_pack_hash) is None:
        errors.append("xN installation source pack hash is invalid")
    elif primary_target is not None and str(
        primary_target.get("installed_sha256", "")
    ).upper() != source_pack_hash:
        errors.append("xN installation source pack hash differs from primary target")
    return errors


def installed_catalog_state_contract_errors(
    state: dict[str, Any], targets_by_path: dict[str, dict[str, Any]]
) -> list[str]:
    errors: list[str] = []

    def path_key(value: Any) -> str:
        return str(value).replace("\\", "/").casefold()

    def require_role(role: str) -> dict[str, Any] | None:
        matches = [target for target in targets_by_path.values() if target.get("role") == role]
        if len(matches) != 1:
            errors.append(f"catalog installation requires exactly one {role} target")
            return None
        return matches[0]

    if state.get("schema") != XN_CATALOG_INSTALL_STATE_SCHEMA:
        errors.append("catalog installation state schema is invalid")
        return errors
    scale = state.get("catalog_scale")
    catalog_version = state.get("catalog_version")
    if (
        state.get("registry_layout") != "catalog"
        or state.get("catalog_magic")
        != registry_magic_name(XN_REGISTRY_CATALOG_MAGIC)
        or catalog_version
        not in {
            LEGACY_XN_REGISTRY_CATALOG_VERSION,
            XN_REGISTRY_CATALOG_VERSION,
        }
        or isinstance(scale, bool)
        or scale not in {2, 4}
    ):
        errors.append("catalog installation binary contract is invalid")
    if catalog_version == XN_REGISTRY_CATALOG_VERSION:
        directory_count = state.get("directory_count")
        directory_entry_bytes = state.get("directory_entry_bytes")
        directory_sha256 = str(state.get("directory_sha256", "")).upper()
        if (
            isinstance(directory_count, bool)
            or not isinstance(directory_count, int)
            or not 1 <= directory_count <= MAX_REGISTRY_CATALOG_DIRECTORY_ENTRIES
            or directory_entry_bytes != REGISTRY_CATALOG_DIRECTORY_ENTRY_BYTES
            or re.fullmatch(r"[0-9A-F]{64}", directory_sha256) is None
        ):
            errors.append("catalog installation v2 directory contract is invalid")
        if state.get("shard_registry_version") not in {
            XN_REGISTRY_VERSION,
            XN_COMPRESSED_REGISTRY_VERSION,
        }:
            errors.append("catalog installation shard storage version is invalid")
        if (
            re.fullmatch(
                r"[0-9A-F]{64}",
                str(state.get("logical_content_sha256", "")).upper(),
            )
            is None
        ):
            errors.append("catalog installation logical content digest is invalid")
    for integer_field, maximum in (
        ("animation_count", MAX_REGISTRY_CATALOG_ANIMATIONS),
        ("component_count", MAX_REGISTRY_CATALOG_COMPONENTS),
        ("membership_count", MAX_REGISTRY_CATALOG_MEMBERSHIPS),
        ("shard_count", MAX_REGISTRY_CATALOG_SHARDS),
        ("total_resources", MAX_REGISTRY_CATALOG_RESOURCES),
        ("total_frames", MAX_REGISTRY_CATALOG_FRAMES),
        ("total_index_bytes", MAX_REGISTRY_CATALOG_BYTES),
        ("total_registry_bytes", MAX_REGISTRY_CATALOG_BYTES),
    ):
        value = state.get(integer_field)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            errors.append(f"catalog installation counter is invalid: {integer_field}")
    animation_ids = state.get("animation_ids")
    if (
        not isinstance(animation_ids, list)
        or not animation_ids
        or animation_ids != sorted(set(animation_ids))
        or any(re.fullmatch(r"0x[0-9A-F]{4}", str(value)) is None for value in animation_ids)
    ):
        errors.append("catalog installation animation ids are invalid")
    runtime_profiles = state.get("runtime_profiles")
    if (
        not isinstance(runtime_profiles, list)
        or not runtime_profiles
        or runtime_profiles != sorted(set(runtime_profiles))
        or set(runtime_profiles) - SUPPORTED_RUNTIME_PROFILES
    ):
        errors.append("catalog installation runtime profiles are invalid")

    catalog_target = require_role("catalog")
    owner_target = require_role("catalog-owner")
    require_role("runtime-dll")
    require_role("runtime-ini")
    shard_targets = [
        target
        for target in targets_by_path.values()
        if target.get("role") == "content-addressed-shard"
    ]
    retired_shard_targets = [
        target
        for target in targets_by_path.values()
        if target.get("role") == "retired-content-addressed-shard"
    ]
    if len(shard_targets) != state.get("shard_count"):
        errors.append("catalog installation shard target count differs")
    if retired_shard_targets and state.get("installation_mode") != "storage-repack":
        errors.append("retired catalog shards require a storage-repack state")
    allowed_roles = {
        "catalog",
        "catalog-owner",
        "runtime-dll",
        "runtime-ini",
        "content-addressed-shard",
        "retired-content-addressed-shard",
    }
    for relative, target in targets_by_path.items():
        role = target.get("role")
        if role not in allowed_roles:
            errors.append(f"catalog installation target role is invalid: {relative}")
        if not isinstance(target.get("immutable_noop"), bool):
            errors.append(f"catalog immutable target flag is invalid: {relative}")
        if role == "retired-content-addressed-shard":
            retired_match = re.fullmatch(
                r"iee-assets/creature-sprites/creaturesprites-xn-([0-9a-f]{64})\.registry",
                relative,
            )
            original_sha256 = str(target.get("original_sha256", "")).upper()
            restore_sha256 = str(target.get("restore_source_sha256", "")).upper()
            restore_text = str(target.get("restore_source_path", ""))
            restore_path = Path(restore_text.replace("\\", "/"))
            if (
                target.get("immutable_noop") is not False
                or target.get("existed_before") is not True
                or target.get("installed_present") is not False
                or target.get("installed_sha256") is not None
                or retired_match is None
                or original_sha256 != restore_sha256
                or re.fullmatch(r"[0-9A-F]{64}", original_sha256) is None
                or (
                    retired_match is not None
                    and retired_match.group(1).upper() != original_sha256
                )
                or not restore_text
                or restore_path.is_absolute()
                or ".." in restore_path.parts
            ):
                errors.append(f"retired catalog shard contract is invalid: {relative}")
        elif target.get("installed_present") is not True:
            errors.append(f"catalog target is not installed: {relative}")
        if role == "content-addressed-shard" and re.fullmatch(
            r"iee-assets/creature-sprites/creaturesprites-xn-[0-9a-f]{64}\.registry",
            relative,
        ) is None:
            errors.append(f"catalog shard target name is invalid: {relative}")

    catalog_relative = path_key(state.get("catalog_relative_path", ""))
    expected_catalog_relative = path_key(
        "iee-assets/creature-sprites/" + XN_REGISTRY_CATALOG_FILENAME
    )
    catalog_sha = str(state.get("catalog_sha256", "")).upper()
    if (
        catalog_relative != expected_catalog_relative
        or re.fullmatch(r"[0-9A-F]{64}", catalog_sha) is None
        or catalog_target is None
        or path_key(catalog_target.get("relative_path", "")) != catalog_relative
        or str(catalog_target.get("installed_sha256", "")).upper() != catalog_sha
    ):
        errors.append("catalog installation primary target differs")

    game_root = Path(str(state.get("game_root", ""))).resolve()
    catalog_path = game_root / Path(
        str(state.get("catalog_relative_path", "")).replace("\\", "/")
    )
    if catalog_path.is_file():
        try:
            info = inspect_registry_catalog(catalog_path, require_exact_shards=False)
            if (
                info["sha256"] != catalog_sha
                or info["version"] != catalog_version
                or info["shard_registry_version"]
                != state.get("shard_registry_version", XN_REGISTRY_VERSION)
                or (
                    catalog_version == XN_REGISTRY_CATALOG_VERSION
                    and info["logical_content_sha256"]
                    != state.get("logical_content_sha256")
                )
                or info["scale"] != scale
                or info["animation_count"] != state.get("animation_count")
                or info["component_count"] != state.get("component_count")
                or info["membership_count"] != state.get("membership_count")
                or info["shard_count"] != state.get("shard_count")
                or info["total_resources"] != state.get("total_resources")
                or info["total_frames"] != state.get("total_frames")
                or info["total_index_bytes"] != state.get("total_index_bytes")
                or info["total_registry_bytes"] != state.get("total_registry_bytes")
                or (
                    catalog_version == XN_REGISTRY_CATALOG_VERSION
                    and (
                        info["directory_count"] != state.get("directory_count")
                        or info["directory_entry_bytes"]
                        != state.get("directory_entry_bytes")
                        or info["directory_sha256"] != state.get("directory_sha256")
                    )
                )
                or [entry["animation_id"] for entry in info["animations"]]
                != animation_ids
            ):
                errors.append("installed catalog counters or mappings differ")
            indexed_shards = {
                path_key(shard["registry"]): shard["sha256"]
                for shard in info["shards"]
            }
            target_shards = {
                path_key(target["relative_path"]): str(
                    target.get("installed_sha256", "")
                ).upper()
                for target in shard_targets
            }
            if indexed_shards != target_shards:
                errors.append("installed catalog shard targets differ from index")
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            errors.append(f"installed catalog validation failed: {error}")

    owner_relative = path_key(
        "iee-assets/creature-sprites/CreatureSprites-XN.catalog-owner.json"
    )
    if owner_target is None or path_key(
        owner_target.get("relative_path", "")
    ) != owner_relative:
        errors.append("catalog owner target path is invalid")
    else:
        owner_path = game_root / Path(
            str(owner_target["relative_path"]).replace("\\", "/")
        )
        try:
            owner = read_json(owner_path)
            if (
                owner.get("schema")
                != "bg2-upscale-creature-sprite-xn-catalog-owner-v1"
                or owner.get("status") != "active"
                or owner.get("transaction_id") != state.get("transaction_id")
                or owner.get("generation_id") != state.get("generation_id")
                or owner.get("job_id") != state.get("job_id")
                or owner.get("job_sha256") != state.get("job_sha256")
                or path_key(owner.get("catalog_relative_path", ""))
                != catalog_relative
                or owner.get("catalog_sha256") != catalog_sha
                or owner.get("catalog_bytes") != state.get("catalog_bytes")
                or owner.get("animation_ids") != animation_ids
                or owner.get("method") != state.get("method")
                or str(owner.get("game_root", "")).casefold()
                != str(state.get("game_root", "")).casefold()
            ):
                errors.append("catalog owner metadata differs from active state")
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            errors.append(f"catalog owner metadata is invalid: {error}")
    return errors


def first_installed_target_reparse_component(
    game_root: Path, relative: Path
) -> Path | None:
    return first_reparse_component(game_root, relative)


def runtime_ini_owned_contract_errors(path: Path, state: dict[str, Any]) -> list[str]:
    expected = {
        "enablecreaturespriteupscaletest": "true",
        "enablecreaturespritex2test": "false",
    }
    if state.get("schema") == XN_CATALOG_INSTALL_STATE_SCHEMA:
        expected["enablecreaturespritelinearfiltering"] = "false"
    values: dict[str, list[str]] = {key: [] for key in expected}
    section = ""
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="strict").splitlines()
    except (OSError, UnicodeError) as error:
        return [f"runtime INI cannot be read: {error}"]
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith((";", "#")):
            continue
        section_match = re.fullmatch(r"\[([^\]]+)\]", line)
        if section_match:
            section = section_match.group(1).strip().casefold()
            continue
        if section != "shaders" or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        key = key.casefold()
        if key in values:
            values[key].append(value.casefold())
    errors: list[str] = []
    for key, expected_value in expected.items():
        if values[key] != [expected_value]:
            errors.append(
                f"runtime INI owned key differs or is duplicated: Shaders/{key}"
            )
    return errors


def installed_state_integrity(
    state: dict[str, Any], expected_scale: int | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    targets = state.get("targets")
    game_root_text = str(state.get("game_root", ""))
    if not isinstance(targets, list) or not targets or not game_root_text:
        return {
            "installed_files_match": False,
            "installed_targets_checked": 0,
            "installed_integrity_errors": ["installation state is incomplete"],
        }
    game_root_unresolved = Path(game_root_text)
    if not game_root_unresolved.is_absolute():
        return {
            "installed_files_match": False,
            "installed_targets_checked": 0,
            "installed_integrity_errors": ["installation game root is not absolute"],
        }
    game_root: Path | None = None
    checked = 0
    targets_by_path: dict[str, dict[str, Any]] = {}
    seen_target_paths: set[str] = set()
    contract_paths_safe = True
    shared_file_drift: list[str] = []
    for target_state in targets:
        if not isinstance(target_state, dict):
            errors.append("invalid target state")
            continue
        relative_text = str(target_state.get("relative_path", ""))
        relative = Path(relative_text.replace("\\", "/"))
        if (
            not relative_text
            or relative.is_absolute()
            or not relative.parts
            or ".." in relative.parts
        ):
            contract_paths_safe = False
            errors.append(f"invalid installed target path: {relative_text!r}")
            continue
        target_key = relative.as_posix().casefold()
        if target_key in seen_target_paths:
            errors.append(f"duplicate installed target path: {relative_text}")
            continue
        seen_target_paths.add(target_key)
        try:
            reparse_component = first_installed_target_reparse_component(
                game_root_unresolved, relative
            )
        except OSError as error:
            contract_paths_safe = False
            errors.append(
                f"cannot inspect installed target components: {relative_text}: {error}"
            )
            continue
        if reparse_component is not None:
            contract_paths_safe = False
            errors.append(
                "installed target crosses a reparse point: "
                f"{relative_text}: {reparse_component}"
            )
            continue
        if game_root is None:
            game_root = game_root_unresolved.resolve()
        target = (game_root / relative).resolve()
        try:
            target.relative_to(game_root)
        except ValueError:
            errors.append(f"installed target escapes game root: {relative_text}")
            continue
        targets_by_path[target_key] = target_state
        expected_present = target_state.get("installed_present")
        if not isinstance(expected_present, bool):
            errors.append(f"installed presence is missing: {relative_text}")
            continue
        present = target.is_file()
        if present != expected_present:
            errors.append(f"installed presence changed: {relative_text}")
            continue
        if present:
            expected_hash = str(target_state.get("installed_sha256", "")).upper()
            if not re.fullmatch(r"[0-9A-F]{64}", expected_hash):
                errors.append(f"installed hash is missing: {relative_text}")
                continue
            if sha256_file(target) != expected_hash:
                if target_state.get("role") == "runtime-ini":
                    ini_errors = runtime_ini_owned_contract_errors(target, state)
                    if ini_errors:
                        errors.extend(ini_errors)
                        continue
                    shared_file_drift.append(relative_text)
                else:
                    errors.append(f"installed hash changed: {relative_text}")
                    continue
        checked += 1
    if contract_paths_safe:
        if state.get("schema") == XN_CATALOG_INSTALL_STATE_SCHEMA:
            errors.extend(
                installed_catalog_state_contract_errors(state, targets_by_path)
            )
        elif expected_scale is not None or state.get("registry_layout") is not None:
            errors.extend(
                installed_xn_state_contract_errors(
                    state, targets_by_path, expected_scale
                )
            )
    return {
        "installed_files_match": not errors and checked == len(targets),
        "installed_targets_checked": checked,
        "installed_integrity_errors": errors,
        "installed_shared_file_drift": shared_file_drift,
    }


def state_path_matches_exact_file(value: Any, expected: Path) -> bool:
    text = str(value or "")
    if not text:
        return False
    candidate = Path(os.path.expandvars(text.replace("\\", "/")))
    if ".." in candidate.parts:
        return False
    resolved = resolve_path(candidate)
    return os.path.normcase(os.path.abspath(resolved)) == os.path.normcase(
        os.path.abspath(expected.resolve())
    )


def read_sealed_json(
    path: Path, expected_sha256: Any, label: str
) -> dict[str, Any]:
    expected = str(expected_sha256 or "").upper()
    if re.fullmatch(r"[0-9A-F]{64}", expected) is None:
        raise RuntimeError(f"{label} sealed SHA-256 is invalid")
    metadata = path.stat()
    if not (1 <= metadata.st_size <= 64 * 1024 * 1024):
        raise RuntimeError(f"{label} sealed JSON size is invalid")
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != expected:
        raise RuntimeError(f"{label} differs from its sealed SHA-256")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} sealed JSON is invalid: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} sealed JSON must be an object")
    return value


def sealed_catalog_generation_integrity(
    catalog: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    """Verify an installed catalog generation without consulting live inputs.

    The active state selects immutable build/runtime manifests by exact path and
    hash.  Their recorded input lock seals the generation id; catalog shards and
    the DLL are then verified from that generation.  No current engine tree,
    member/leaf build, runner hash, or current-generation pointer participates.
    """

    errors: list[str] = []
    has_live_qa_contract = "_qa_contract" in catalog
    live_qa_by_animation = {
        entry["animation_id"]: entry
        for entry in catalog.get("_qa_contract", [])
        if isinstance(entry, dict) and isinstance(entry.get("animation_id"), str)
    }
    job_file = Path(str(catalog.get("_job_file", "")))
    current_job_sha256 = ""
    current_job_hash_error: OSError | None = None
    try:
        current_job_sha256 = sha256_file(job_file)
    except OSError as error:
        current_job_hash_error = error
    live_job_identity_matches = bool(
        current_job_sha256
        and state.get("job_id") == catalog.get("job_id")
        and str(state.get("job_sha256", "")).upper() == current_job_sha256
    )
    active_identity_matches_job = live_job_identity_matches
    if state.get("schema") != XN_CATALOG_INSTALL_STATE_SCHEMA:
        errors.append("active catalog installation schema is invalid")
    if not state_path_matches_exact_file(state.get("job_file"), job_file):
        errors.append("active state job_file differs from the catalog job")
    sealed_catalog_version = state.get("catalog_version")
    if sealed_catalog_version not in {
        LEGACY_XN_REGISTRY_CATALOG_VERSION,
        XN_REGISTRY_CATALOG_VERSION,
    }:
        errors.append("active catalog binary version is unsupported")

    generation_id = str(state.get("generation_id", ""))
    if re.fullmatch(r"[0-9A-F]{64}", generation_id) is None:
        errors.append("active catalog generation_id is invalid")
        return {
            "active_identity_matches_job": active_identity_matches_job,
            "active_generation_is_sealed": False,
            "active_generation_seal_errors": errors,
        }

    try:
        run_root = job_path(catalog, "run_dir")
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        errors.append(f"catalog run_dir is invalid: {error}")
        return {
            "active_identity_matches_job": active_identity_matches_job,
            "active_generation_is_sealed": False,
            "active_generation_seal_errors": errors,
        }
    generation_relative = Path("generations") / generation_id.lower()
    generation_root = run_root / generation_relative
    build_manifest_path = generation_root / "build" / "build-manifest.json"
    runtime_manifest_path = generation_root / "runtime" / "runtime-manifest.json"

    manifest_specs = (
        (
            "build manifest",
            "build_manifest",
            "build_manifest_sha256",
            build_manifest_path,
        ),
        (
            "runtime manifest",
            "runtime_manifest",
            "runtime_manifest_sha256",
            runtime_manifest_path,
        ),
    )
    manifests: dict[str, dict[str, Any]] = {}
    for label, path_field, hash_field, expected_path in manifest_specs:
        if not state_path_matches_exact_file(state.get(path_field), expected_path):
            errors.append(f"active state {path_field} is outside the sealed generation")
            continue
        try:
            relative = expected_path.relative_to(run_root)
            reparse_component = first_installed_target_reparse_component(
                run_root, relative
            )
            if reparse_component is not None:
                raise RuntimeError(
                    f"path crosses a reparse point: {reparse_component}"
                )
            manifests[path_field] = read_sealed_json(
                expected_path, state.get(hash_field), label
            )
        except (OSError, RuntimeError, ValueError) as error:
            errors.append(f"sealed {label} is invalid: {error}")

    build = manifests.get("build_manifest")
    runtime = manifests.get("runtime_manifest")
    sealed_job_snapshot_matches = False
    if build is not None and (
        build.get("job_snapshot") is not None
        or build.get("job_snapshot_sha256") is not None
    ):
        job_snapshot_relative = build.get("job_snapshot")
        job_snapshot_sha256 = str(
            build.get("job_snapshot_sha256", "")
        ).upper()
        job_snapshot_path = generation_root / "build" / Path(
            str(job_snapshot_relative)
        )
        try:
            if job_snapshot_relative != "provenance/job.json":
                raise RuntimeError("path is not provenance/job.json")
            relative = job_snapshot_path.relative_to(run_root)
            reparse_component = first_installed_target_reparse_component(
                run_root, relative
            )
            if reparse_component is not None:
                raise RuntimeError(
                    f"path crosses a reparse point: {reparse_component}"
                )
            snapshot_sha256 = sha256_file(job_snapshot_path)
            snapshot = read_json(job_snapshot_path)
            sealed_job_snapshot_matches = bool(
                job_snapshot_sha256
                and job_snapshot_sha256 == snapshot_sha256
                and job_snapshot_sha256
                == str(state.get("job_sha256", "")).upper()
                and snapshot.get("schema") == CATALOG_JOB_SCHEMA
                and snapshot.get("job_id") == state.get("job_id")
            )
            if not sealed_job_snapshot_matches:
                raise RuntimeError("identity or SHA-256 differs from active state")
        except (OSError, RuntimeError, ValueError) as error:
            errors.append(f"sealed catalog job snapshot is invalid: {error}")
    active_identity_matches_job = bool(
        live_job_identity_matches or sealed_job_snapshot_matches
    )
    if not active_identity_matches_job:
        if current_job_hash_error is not None:
            errors.append(
                f"current catalog job cannot be hashed: {current_job_hash_error}"
            )
        errors.append(
            "active state job_id/job_sha256 differs from the live job and no sealed job snapshot proves it"
        )
    state_method = state.get("method")
    build_method: dict[str, Any] | None = None
    if not isinstance(state_method, dict) or set(state_method) != {
        "algorithm",
        "scale",
        "passes",
        "antialias",
        "xbr_blend",
        "sampling",
    }:
        errors.append("active state upscale method is invalid")
    elif state_method.get("sampling") != "NEAREST":
        errors.append("active state sampling is not NEAREST")
    else:
        build_method = {
            key: state_method[key]
            for key in ("algorithm", "scale", "passes", "antialias", "xbr_blend")
        }

    catalog_info: dict[str, Any] | None = None
    sealed_animation_qa_contract: list[dict[str, Any]] = []
    if build is not None:
        identity_fields_match = bool(
            build.get("schema") == CATALOG_BUILD_SCHEMA
            and build.get("status") == "built-pending-ingame-qa"
            and build.get("job_id") == state.get("job_id")
            and str(build.get("job_sha256", "")).upper()
            == str(state.get("job_sha256", "")).upper()
            and build.get("generation_id") == generation_id
            and state_path_matches_exact_file(build.get("job_file"), job_file)
            and build.get("registry_layout") == "catalog"
            and build.get("method") == build_method
        )
        if not identity_fields_match:
            errors.append("sealed build manifest identity or method differs")
        locks = build.get("locks")
        input_lock = locks.get("input_lock") if isinstance(locks, dict) else None
        if (
            not isinstance(locks, dict)
            or not isinstance(input_lock, dict)
            or locks.get("input_lock_sha256") != generation_id
            or canonical_json_sha256(input_lock) != generation_id
            or input_lock.get("schema")
            != "bg2-upscale-creature-sprite-xn-catalog-input-lock-v1"
            or str(input_lock.get("job_sha256", "")).upper()
            != str(state.get("job_sha256", "")).upper()
            or not state_path_matches_exact_file(input_lock.get("job_file"), job_file)
            or input_lock.get("method") != build_method
        ):
            errors.append("sealed build input lock does not prove generation_id")

        catalog_relative = str(build.get("registry_catalog", "")).replace(
            "\\", "/"
        )
        expected_catalog_relative = (
            "iee-assets/creature-sprites/" + XN_REGISTRY_CATALOG_FILENAME
        )
        source_catalog = generation_root / "build" / Path(catalog_relative)
        manifest_shards = build.get("shards")
        payload_paths_safe = catalog_relative == expected_catalog_relative
        if not payload_paths_safe:
            errors.append("sealed build catalog path is invalid")
        if not isinstance(manifest_shards, list) or not manifest_shards:
            payload_paths_safe = False
            errors.append("sealed build shard inventory is invalid")
        if payload_paths_safe:
            payload_paths = [source_catalog]
            seen_shard_paths: set[str] = set()
            for shard in manifest_shards:
                registry = (
                    str(shard.get("registry", "")).replace("\\", "/")
                    if isinstance(shard, dict)
                    else ""
                )
                if re.fullmatch(
                    r"iee-assets/creature-sprites/CreatureSprites-XN-[0-9A-F]{64}\.registry",
                    registry,
                ) is None or registry in seen_shard_paths:
                    payload_paths_safe = False
                    errors.append("sealed build shard path inventory is invalid")
                    break
                seen_shard_paths.add(registry)
                payload_paths.append(generation_root / "build" / Path(registry))
            if payload_paths_safe:
                for payload_path in payload_paths:
                    try:
                        relative = payload_path.relative_to(run_root)
                        reparse_component = first_installed_target_reparse_component(
                            run_root, relative
                        )
                    except (OSError, ValueError) as error:
                        payload_paths_safe = False
                        errors.append(f"cannot inspect sealed payload path: {error}")
                        break
                    if reparse_component is not None:
                        payload_paths_safe = False
                        errors.append(
                            "sealed catalog payload crosses a reparse point: "
                            f"{reparse_component}"
                        )
                        break
        if payload_paths_safe:
            try:
                catalog_info = inspect_registry_catalog(source_catalog)
            except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
                errors.append(f"sealed catalog payload is invalid: {error}")

        if catalog_info is not None:
            totals = {
                "total_resources": catalog_info["total_resources"],
                "total_frames": catalog_info["total_frames"],
                "total_index_bytes": catalog_info["total_index_bytes"],
                "total_registry_bytes": catalog_info["total_registry_bytes"],
            }
            state_animation_ids = state.get("animation_ids")
            manifest_animations = build.get("animations")
            manifest_animation_matches = isinstance(manifest_animations, list) and len(
                manifest_animations
            ) == len(catalog_info["animations"])
            if manifest_animation_matches:
                owner_names = {
                    CATALOG_OWNER_CHARACTER: "Character",
                    CATALOG_OWNER_MONSTER_ICEWIND: "MonsterIcewind",
                }
                for manifest_animation, binary_animation in zip(
                    manifest_animations, catalog_info["animations"]
                ):
                    if not isinstance(manifest_animation, dict) or (
                        manifest_animation.get("animation_id")
                        != binary_animation["animation_id"]
                        or manifest_animation.get("owner")
                        != owner_names.get(binary_animation["owner"])
                        or manifest_animation.get("component_indices")
                        != binary_animation["component_indices"]
                        or manifest_animation.get("runtime_profile")
                        not in SUPPORTED_RUNTIME_PROFILES
                        or (
                            manifest_animation.get("runtime_profile")
                            == "character-bg2ee-2.7.3.0"
                        )
                        != (binary_animation["owner"] == CATALOG_OWNER_CHARACTER)
                    ):
                        manifest_animation_matches = False
                        break
            source_members = build.get("source_members")
            source_member_matches = (
                manifest_animation_matches
                and isinstance(source_members, list)
                and len(source_members) == len(manifest_animations)
            )
            if source_member_matches:
                animations_by_id = {
                    entry["animation_id"]: entry for entry in manifest_animations
                }
                previous_animation_id = -1
                for member in source_members:
                    animation_id = (
                        str(member.get("animation_id", ""))
                        if isinstance(member, dict)
                        else ""
                    )
                    animation = animations_by_id.get(animation_id)
                    prefixes = member.get("bam_prefixes") if isinstance(member, dict) else None
                    live_qa = live_qa_by_animation.get(animation_id)
                    try:
                        numeric_animation_id = int(animation_id, 16)
                    except ValueError:
                        numeric_animation_id = -1
                    if (
                        animation is None
                        or numeric_animation_id <= previous_animation_id
                        or member.get("runtime_profile")
                        != animation.get("runtime_profile")
                        or member.get("component_indices")
                        != animation.get("component_indices")
                        or not isinstance(prefixes, list)
                        or not prefixes
                        or any(
                            not isinstance(prefix, str)
                            or re.fullmatch(r"[A-Z0-9_]{1,8}", prefix) is None
                            for prefix in prefixes
                        )
                        or len(prefixes) != len(set(prefixes))
                        or (
                            has_live_qa_contract
                            and (
                                live_qa is None
                                or live_qa.get("runtime_profile")
                                != animation.get("runtime_profile")
                                or live_qa.get("bam_prefixes") != prefixes
                            )
                        )
                    ):
                        source_member_matches = False
                        break
                    sealed_animation_qa_contract.append(
                        {
                            "animation_id": animation_id,
                            "runtime_profile": animation["runtime_profile"],
                            "bam_prefixes": prefixes,
                            "required_bam_prefixes": (
                                live_qa["required_bam_prefixes"]
                                if live_qa is not None
                                else prefixes
                            ),
                        }
                    )
                    previous_animation_id = numeric_animation_id
            if not source_member_matches:
                sealed_animation_qa_contract.clear()
            if (
                catalog_info["sha256"]
                != str(build.get("registry_catalog_sha256", "")).upper()
                or catalog_info["sha256"]
                != str(state.get("catalog_sha256", "")).upper()
                or catalog_info["registry_catalog_bytes"]
                != build.get("registry_catalog_bytes")
                or catalog_info["registry_catalog_bytes"]
                != state.get("catalog_bytes")
                or catalog_info["registry_magic"]
                != registry_magic_name(XN_REGISTRY_CATALOG_MAGIC)
                or catalog_info["version"] != sealed_catalog_version
                or catalog_info["scale"] != state.get("catalog_scale")
                or build.get("registry_scale") != catalog_info["scale"]
                or build.get("registry_catalog_magic")
                != registry_magic_name(XN_REGISTRY_CATALOG_MAGIC)
                or build.get("registry_catalog_version")
                != sealed_catalog_version
                or build.get(
                    "registry_catalog_shard_version", XN_REGISTRY_VERSION
                )
                != catalog_info["shard_registry_version"]
                or (
                    catalog_info["shard_registry_version"]
                    == XN_COMPRESSED_REGISTRY_VERSION
                    and build.get("registry_catalog_frame_storage")
                    != "XPRESS_HUFF-or-raw-per-frame-v1"
                )
                or (
                    catalog_info["shard_registry_version"]
                    == XN_COMPRESSED_REGISTRY_VERSION
                    and (
                        build.get("registry_catalog_logical_component_digests")
                        != catalog_info["logical_component_digests"]
                        or build.get("registry_catalog_logical_content_sha256")
                        != catalog_info["logical_content_sha256"]
                    )
                )
                or (
                    sealed_catalog_version == XN_REGISTRY_CATALOG_VERSION
                    and (
                        catalog_info["directory_count"]
                        != build.get("registry_catalog_directory_count")
                        or catalog_info["directory_entry_bytes"]
                        != build.get("registry_catalog_directory_entry_bytes")
                        or catalog_info["directory_sha256"]
                        != build.get("registry_catalog_directory_sha256")
                        or catalog_info["directory_count"]
                        != state.get("directory_count")
                        or catalog_info["directory_entry_bytes"]
                        != state.get("directory_entry_bytes")
                        or catalog_info["directory_sha256"]
                        != state.get("directory_sha256")
                    )
                )
                or build.get("animation_ids") != state_animation_ids
                or state_animation_ids
                != [entry["animation_id"] for entry in catalog_info["animations"]]
                or build.get("components") != catalog_info["components"]
                or build.get("shards") != catalog_info["shards"]
                or build.get("totals") != totals
                or (
                    catalog_info["shard_registry_version"]
                    == XN_COMPRESSED_REGISTRY_VERSION
                    and build.get("storage")
                    != {
                        "shard_registry_version": catalog_info[
                            "shard_registry_version"
                        ],
                        "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                        "stored_index_bytes": catalog_info["stored_index_bytes"],
                        "compressed_frame_count": catalog_info[
                            "compressed_frame_count"
                        ],
                        "raw_frame_count": catalog_info["raw_frame_count"],
                        "index_storage_ratio": catalog_info[
                            "index_storage_ratio"
                        ],
                    }
                )
                or state.get("animation_count") != catalog_info["animation_count"]
                or state.get("component_count") != catalog_info["component_count"]
                or state.get("membership_count") != catalog_info["membership_count"]
                or state.get("shard_count") != catalog_info["shard_count"]
                or state.get("total_resources") != totals["total_resources"]
                or state.get("total_frames") != totals["total_frames"]
                or state.get("total_index_bytes") != totals["total_index_bytes"]
                or state.get("total_registry_bytes") != totals["total_registry_bytes"]
                or not manifest_animation_matches
                or not source_member_matches
                or build.get("runtime_profiles")
                != sorted(
                    {
                        entry["runtime_profile"]
                        for entry in sealed_animation_qa_contract
                    }
                )
                or build.get("runtime_profiles") != state.get("runtime_profiles")
            ):
                errors.append("sealed build catalog metadata differs from its payload")

    if runtime is not None:
        if (
            runtime.get("schema") != RUNTIME_SCHEMA
            or runtime.get("status") != "built-tested"
            or runtime.get("tests_status") != "passed"
            or (
                sealed_catalog_version == XN_REGISTRY_CATALOG_VERSION
                and runtime.get("bridge_worker_tests_status") != "passed"
            )
            or runtime.get("job_id") != state.get("job_id")
            or str(runtime.get("job_sha256", "")).upper()
            != str(state.get("job_sha256", "")).upper()
            or runtime.get("generation_id") != generation_id
            or runtime.get("method") != build_method
            or runtime.get("runtime_profiles") != state.get("runtime_profiles")
            or (build is not None and runtime.get("runtime_profiles") != build.get("runtime_profiles"))
            or runtime.get("catalog_magic")
            != registry_magic_name(XN_REGISTRY_CATALOG_MAGIC)
            or runtime.get("catalog_version") != sealed_catalog_version
            or (
                sealed_catalog_version == XN_REGISTRY_CATALOG_VERSION
                and build is not None
                and (
                    runtime.get("catalog_directory_count")
                    != build.get("registry_catalog_directory_count")
                    or runtime.get("catalog_directory_entry_bytes")
                    != build.get("registry_catalog_directory_entry_bytes")
                    or runtime.get("catalog_directory_sha256")
                    != build.get("registry_catalog_directory_sha256")
                )
            )
            or runtime.get("catalog_shard_registry_magic")
            != registry_magic_name(XN_REGISTRY_MAGIC)
            or runtime.get("catalog_shard_registry_version")
            != (
                build.get("registry_catalog_shard_version", XN_REGISTRY_VERSION)
                if build is not None
                else XN_REGISTRY_VERSION
            )
            or (
                build is not None
                and build.get("registry_catalog_shard_version")
                == XN_COMPRESSED_REGISTRY_VERSION
                and runtime.get("catalog_frame_storage")
                != build.get("registry_catalog_frame_storage")
            )
            or runtime.get("catalog_shard_animation_id_sentinel") != "0xFFFF"
            or runtime.get("dll") != "InfinityEngine-Enhancer.dll"
        ):
            errors.append("sealed runtime manifest identity or contract differs")
        runtime_dll = generation_root / "runtime" / "InfinityEngine-Enhancer.dll"
        try:
            relative = runtime_dll.relative_to(run_root)
            reparse_component = first_installed_target_reparse_component(
                run_root, relative
            )
            if reparse_component is not None:
                raise RuntimeError(
                    f"path crosses a reparse point: {reparse_component}"
                )
            dll_sha256 = sha256_file(runtime_dll)
            if (
                dll_sha256 != str(runtime.get("dll_sha256", "")).upper()
                or dll_sha256 != str(state.get("source_dll_sha256", "")).upper()
            ):
                raise RuntimeError("DLL differs from its sealed SHA-256")
        except (OSError, RuntimeError, ValueError) as error:
            errors.append(f"sealed runtime DLL is invalid: {error}")

    return {
        "active_identity_matches_job": active_identity_matches_job,
        "active_identity_matches_live_job": live_job_identity_matches,
        "sealed_job_snapshot_matches": sealed_job_snapshot_matches,
        "active_generation_is_sealed": bool(
            active_identity_matches_job
            and build is not None
            and runtime is not None
            and catalog_info is not None
            and not errors
        ),
        "active_generation_seal_errors": errors,
        "sealed_generation_root": str(generation_root),
        "sealed_build_manifest": str(build_manifest_path),
        "sealed_runtime_manifest": str(runtime_manifest_path),
        "sealed_animation_qa_contract": sealed_animation_qa_contract,
    }


def catalog_qa_log_report(
    catalog: dict[str, Any], write_report: bool
) -> dict[str, Any]:
    log_path = job_path(catalog, "game_root") / "InfinityEngine-Enhancer.log"
    text = log_path.read_text(encoding="utf-8", errors="replace")
    state_path = active_state_path(catalog)
    state = read_json(state_path) if state_path.is_file() else {}
    seal = sealed_catalog_generation_integrity(catalog, state)
    contract = upscale_contract(catalog)
    ready_marker = "Creature sprite xBR catalog ready:"
    session = runtime_log_session_after_install(
        text, ready_marker, str(state.get("installed_at_utc", ""))
    )
    session_lower = session.lower()
    animation_reports: list[dict[str, Any]] = []
    all_composition_by_animation_prefix: dict[
        tuple[str, str], list[str]
    ] = {}
    owner_scope_by_profile: dict[str, bool] = {}
    runtime_health_by_profile: dict[str, dict[str, Any]] = {}
    for animation_contract in seal.get("sealed_animation_qa_contract", []):
        animation_id = animation_contract["animation_id"]
        profile = animation_contract["runtime_profile"]
        owner, render_owner = runtime_owner_labels(profile)
        prefixes = animation_contract["bam_prefixes"]
        required_prefixes = animation_contract.get(
            "required_bam_prefixes", prefixes
        )
        composition_by_prefix = {
            prefix: animation_composition_lines(session, animation_id, prefix)
            for prefix in prefixes
        }
        for prefix, lines in composition_by_prefix.items():
            all_composition_by_animation_prefix[(animation_id, prefix)] = lines
        owner_scope = (
            f"owner scope installed: {owner}".lower() in session_lower
        )
        owner_scope_by_profile[profile] = owner_scope
        reached = (
            f"Creature sprite animation {animation_id} reached {render_owner}".lower()
            in session_lower
        )
        materialized = (
            f"Creature sprite catalog animation {animation_id} materialized:".lower()
            in session_lower
        )
        on_demand_pattern = re.compile(
            r"Creature sprite catalog shard \d+ ready on demand for animation "
            + re.escape(animation_id)
            + r", resref ([A-Z0-9_]{1,8}):",
            re.IGNORECASE,
        )
        on_demand_resrefs = sorted(
            {match.upper() for match in on_demand_pattern.findall(session)}
        )
        payload_ready = materialized or bool(on_demand_resrefs)
        animation_reports.append(
            {
                "animation_id": animation_id,
                "runtime_profile": profile,
                "owner_scope": owner_scope,
                "materialized": materialized,
                "on_demand_resrefs": on_demand_resrefs,
                "payload_ready": payload_ready,
                "animation_reached": reached,
                "bam_prefixes": prefixes,
                "required_bam_prefixes": required_prefixes,
                "composition_by_prefix": {
                    prefix: len(lines)
                    for prefix, lines in composition_by_prefix.items()
                },
                "all_prefixes_composed": all(composition_by_prefix.values()),
                "required_prefixes_composed": all(
                    composition_by_prefix[prefix] for prefix in required_prefixes
                ),
            }
        )
    for profile in sorted({report["runtime_profile"] for report in animation_reports}):
        profile_compositions = {
            f"{report['animation_id']}:{prefix}": (
                all_composition_by_animation_prefix[
                    (report["animation_id"], prefix)
                ]
            )
            for report in animation_reports
            if report["runtime_profile"] == profile
            for prefix in report["required_bam_prefixes"]
        }
        runtime_health_by_profile[profile] = runtime_session_health(
            session, profile, profile_compositions
        )
    ready_line = next(
        (line for line in session.splitlines() if ready_marker in line), ""
    )
    pack_ready = bool(
        ready_line
        and f"scale=x{contract.scale}," in ready_line
        and f"{len(animation_reports)} animations," in ready_line
        and f"source={XN_REGISTRY_CATALOG_FILENAME};" in ready_line
        and "filter=NEAREST" in ready_line
    )
    integrity = installed_state_integrity(state)
    report = {
        "schema": "bg2-upscale-creature-sprite-catalog-technical-qa-v1",
        "created_at_utc": utc_now(),
        "job_id": catalog["job_id"],
        "generation_id": state.get("generation_id"),
        "log": str(log_path),
        "session_after_install": bool(session),
        "pack_ready": pack_ready,
        "registry_layout": state.get("registry_layout"),
        "registry_scale": state.get("catalog_scale"),
        "owner_palette_snapshot": (
            "owner-scoped CVidPalette::Realize snapshot" in session
        ),
        "animation_results": animation_reports,
        "owner_scope_by_profile": owner_scope_by_profile,
        "composition_count": sum(
            len(lines)
            for lines in all_composition_by_animation_prefix.values()
        ),
        "runtime_health_by_profile": runtime_health_by_profile,
        "qa_scenarios": catalog.get("qa", {}).get("animations", []),
        **seal,
        **integrity,
    }
    report["technical_pass"] = bool(
        report["session_after_install"]
        and report["pack_ready"]
        and report["active_identity_matches_job"]
        and report["active_generation_is_sealed"]
        and report["owner_palette_snapshot"]
        and report["installed_files_match"]
        and all(owner_scope_by_profile.values())
        and all(
            animation["payload_ready"]
            and animation["animation_reached"]
            and animation["required_prefixes_composed"]
            for animation in animation_reports
        )
        and all(
            health["runtime_health_pass"]
            for health in runtime_health_by_profile.values()
        )
        and "Creature sprite xBR pack disabled:" not in session
    )
    if write_report:
        write_json(
            job_path(catalog, "run_dir") / "qa" / "technical-log.json",
            report,
        )
    return report


def qa_log_report(job: dict[str, Any], write_report: bool) -> dict[str, Any]:
    if job.get("_kind") == "catalog":
        return catalog_qa_log_report(job, write_report)
    log_path = job_path(job, "game_root") / "InfinityEngine-Enhancer.log"
    text = log_path.read_text(encoding="utf-8", errors="replace")
    state_path = active_state_path(job)
    state = read_json(state_path) if state_path.is_file() else {}
    animation_id = job["animation"]["id"]
    contract = effective_upscale_contract(job)
    ready_markers = tuple(
        f"Creature sprite {kind} pack ready: animation {animation_id},"
        for kind in ("xBR", "xBR2x")
    )
    session = runtime_log_session_after_install(
        text, ready_markers, str(state.get("installed_at_utc", ""))
    )
    session_lower = session.lower()
    prefixes = (
        armor_set_prefixes(job)
        if job.get("_kind") == "armor-set"
        else [str(job["animation"]["bam_prefix"])]
    )
    required_prefixes = job.get("qa", {}).get(
        "required_bam_prefixes", prefixes
    )
    if (
        not isinstance(required_prefixes, list)
        or not required_prefixes
        or any(prefix not in prefixes for prefix in required_prefixes)
    ):
        raise RuntimeError("QA required_bam_prefixes differs from the work item")
    composition_by_prefix = {
        prefix: [
            line
            for line in session.splitlines()
            if f"Composing creature sprite {prefix}" in line
        ]
        for prefix in prefixes
    }
    composition_lines = [line for lines in composition_by_prefix.values() for line in lines]
    profile = str(job["animation"].get("runtime_profile", ""))
    owner, render_owner = runtime_owner_labels(profile)
    owner_scope_marker = f"owner scope installed: {owner}".lower()
    reached_marker = f"Creature sprite animation {animation_id} reached {render_owner}".lower()
    legacy_pack_ready = any(
        any(marker in line for marker in ready_markers)
        and "filter=NEAREST" in line
        for line in session.splitlines()
    )
    pack_ready = legacy_pack_ready
    if contract.explicit:
        expected_source = (
            XN_REGISTRY_SET_FILENAME
            if state.get("registry_layout") == "set"
            else XN_REGISTRY_FILENAME
        )
        pack_ready = any(
            any(marker in line for marker in ready_markers)
            and f"scale=x{contract.scale}," in line
            and f"source={expected_source};" in line
            and "filter=NEAREST" in line
            for line in session.splitlines()
        )
    report = {
        "schema": "bg2-upscale-creature-sprite-technical-qa-v1",
        "created_at_utc": utc_now(),
        "job_id": job["job_id"],
        "log": str(log_path),
        "session_after_install": bool(session),
        "pack_ready": pack_ready,
        "owner_scope": owner_scope_marker in session_lower,
        "animation_reached": reached_marker in session_lower,
        "owner_palette_snapshot": "owner-scoped CVidPalette::Realize snapshot" in session,
        "bam_prefixes": prefixes,
        "required_bam_prefixes": required_prefixes,
        "composition_by_prefix": {
            prefix: len(lines) for prefix, lines in composition_by_prefix.items()
        },
        "composition_count": len(composition_lines),
        "first_composition": composition_lines[0] if composition_lines else None,
    }
    if contract.explicit:
        report["registry_scale"] = contract.scale
        report["registry_layout"] = state.get("registry_layout", "monolith")
        report.update(installed_state_integrity(state, contract.scale))
    report.update(
        runtime_session_health(
            session,
            profile,
            {
                prefix: composition_by_prefix[prefix]
                for prefix in required_prefixes
            },
        )
    )
    report["technical_pass"] = bool(
        report["session_after_install"]
        and report["pack_ready"]
        and report["owner_scope"]
        and report["animation_reached"]
        and report["owner_palette_snapshot"]
        and all(composition_by_prefix[prefix] for prefix in required_prefixes)
        and report["runtime_health_pass"]
        and (not contract.explicit or report["installed_files_match"])
    )
    if write_report:
        write_json(job_path(job, "run_dir") / "qa" / "technical-log.json", report)
    return report


def record_qa(job: dict[str, Any], result: str, note: str) -> dict[str, Any]:
    state_path = active_state_path(job)
    state = read_json(state_path)
    if state.get("status") != "installed-pending-qa":
        raise RuntimeError(f"active state is not pending QA: {state.get('status')}")
    if job.get("_kind") == "catalog":
        seal = sealed_catalog_generation_integrity(job, state)
        if not seal["active_identity_matches_job"]:
            raise RuntimeError("active catalog identity differs from the catalog job")
        if not seal["active_generation_is_sealed"]:
            details = "; ".join(seal["active_generation_seal_errors"])
            raise RuntimeError(f"active catalog generation is not sealed: {details}")
    technical = qa_log_report(job, write_report=True)
    if result == "pass" and not technical["technical_pass"]:
        raise RuntimeError("cannot validate: runtime log does not prove sprite composition")
    state["status"] = "validated-installed" if result == "pass" else "qa-failed"
    state["qa_recorded_at_utc"] = utc_now()
    state["qa_note"] = note
    write_json(state_path, state)
    backup_root = state.get("backup_root")
    if backup_root:
        backup_root_path = (
            resolve_path(str(backup_root))
            if job.get("_kind") == "catalog"
            else Path(str(backup_root))
        )
        backup_state = backup_root_path / "install-state.json"
        if backup_state.parent.is_dir():
            write_json(backup_state, state)
    decision = {"schema": "bg2-upscale-creature-sprite-qa-decision-v1", "status": state["status"], "recorded_at_utc": state["qa_recorded_at_utc"], "job_id": job["job_id"], "user_note": note, "technical_qa": technical, "release_manifest_modified": False}
    write_json(job_path(job, "run_dir") / "qa" / "qa-decision.json", decision)
    return decision


def powershell_script(script: Path, job: dict[str, Any]) -> None:
    configured = job.get("tools", {}).get("powershell")
    powershell = str(configured or shutil.which("pwsh.exe") or "powershell.exe")
    run_checked([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-JobFile", str(job["_job_file"])])


def install_restore_script(job: dict[str, Any], restore: bool) -> Path:
    if job.get("_kind") == "catalog":
        return (
            XN_CATALOG_RESTORE_SCRIPT
            if restore
            else XN_CATALOG_INSTALL_SCRIPT
        )
    if effective_upscale_contract(job).explicit:
        return XN_RESTORE_SCRIPT if restore else XN_INSTALL_SCRIPT
    return RESTORE_SCRIPT if restore else INSTALL_SCRIPT


def status(job: dict[str, Any]) -> dict[str, Any]:
    path = active_state_path(job)
    if not path.is_file():
        return {"status": "not-installed", "state": str(path)}
    state = read_json(path)
    result = {
        "status": state.get("status"),
        "state": str(path),
        "installed_at_utc": state.get("installed_at_utc"),
        "backup_root": state.get("backup_root"),
    }
    if job.get("_kind") == "catalog":
        result["job_id"] = state.get("job_id")
        result["generation_id"] = state.get("generation_id")
        result["animation_ids"] = state.get("animation_ids")
        result.update(sealed_catalog_generation_integrity(job, state))
        if state.get("status") in {
            "installed-pending-qa",
            "validated-installed",
            "qa-failed",
        }:
            result.update(installed_state_integrity(state))
    return result


def prepare(job: dict[str, Any], force: bool, resume: bool, keep_frames: bool) -> dict[str, Any]:
    extract_sources(job, force=force, resume=resume)
    build_pack(job, force=force, resume=resume, keep_frames=keep_frames)
    build_runtime(job)
    return verify_all(job, compare_game_sources=True)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "new-character-job",
            "new-character-equipment-job",
            "promote-armor-set-job",
            "plan",
            "extract",
            "verify-sources",
            "build",
            "build-runtime",
            "prepare",
            "verify",
            "install",
            "restore",
            "status",
            "qa-log",
            "record-qa",
        ),
    )
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--template-job", type=Path)
    parser.add_argument("--ids-symbol")
    parser.add_argument("--animation-id")
    parser.add_argument("--armor-code", type=int)
    parser.add_argument("--layer-kind", choices=tuple(sorted(CHARACTER_EQUIPMENT_ITEM_TYPES)))
    parser.add_argument("--item-resref")
    parser.add_argument("--name")
    parser.add_argument("--qa-area", action="append", default=[])
    parser.add_argument("--qa-creature", action="append", default=[])
    parser.add_argument(
        "--scale",
        type=int,
        choices=(2, 4),
        help="create an explicit V3 xN job at the requested physical scale",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--keep-upscaled-frames",
        "--keep-x2-frames",
        dest="keep_upscaled_frames",
        action="store_true",
        help="retain individual upscaled frame PNGs; --keep-x2-frames is a legacy alias",
    )
    parser.add_argument("--no-game-source-check", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--result", choices=("pass", "fail"))
    parser.add_argument("--note")
    return parser


def main() -> None:
    args = make_parser().parse_args()
    if args.scale is not None and args.command not in {
        "new-character-job",
        "new-character-equipment-job",
        "promote-armor-set-job",
    }:
        raise RuntimeError("--scale is only valid when creating or promoting a Character job")
    if args.command == "new-character-job":
        result = create_character_job(
            args.job,
            args.template_job,
            args.ids_symbol,
            args.animation_id,
            args.armor_code,
            args.name,
            args.qa_area,
            args.qa_creature,
            args.scale,
            args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "new-character-equipment-job":
        result = create_character_equipment_job(
            args.job,
            args.template_job,
            args.ids_symbol,
            args.animation_id,
            args.layer_kind,
            args.item_resref,
            args.name,
            args.qa_area,
            args.qa_creature,
            args.scale,
            args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "promote-armor-set-job":
        result = promote_armor_set_job(
            args.job,
            args.template_job,
            args.scale,
            args.force,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    job = load_work_item(args.job)
    armor_set = job.get("_kind") == "armor-set"
    catalog = job.get("_kind") == "catalog"
    if args.command == "plan":
        result = (
            plan_catalog(job)
            if catalog
            else plan_armor_set(job)
            if armor_set
            else plan(job)
        )
    elif args.command == "extract":
        if armor_set or catalog:
            raise RuntimeError(
                "extract is not supported for an aggregate; prepare its member jobs"
            )
        result = extract_sources(job, args.force, args.resume)
    elif args.command == "verify-sources":
        if armor_set or catalog:
            raise RuntimeError(
                "verify-sources is not supported for an aggregate; verify its member jobs"
            )
        result = verify_sources(job, not args.no_game_source_check)
    elif args.command == "build":
        if catalog:
            result = build_catalog(job, args.force, args.resume)
        elif armor_set:
            result = build_armor_set(job, args.force, args.resume)
        else:
            result = build_pack(job, args.force, args.resume, args.keep_upscaled_frames)
    elif args.command == "build-runtime":
        result = build_runtime(job)
    elif args.command == "prepare":
        result = (
            prepare_catalog(job, args.force, args.resume)
            if catalog
            else prepare_armor_set(job, args.force, args.resume)
            if armor_set
            else prepare(job, args.force, args.resume, args.keep_upscaled_frames)
        )
    elif args.command == "verify":
        result = (
            verify_catalog(job)
            if catalog
            else verify_armor_set(job)
            if armor_set
            else verify_all(job, not args.no_game_source_check)
        )
    elif args.command == "install":
        if catalog:
            verify_catalog(job)
        elif armor_set:
            verify_armor_set(job)
        else:
            verify_all(job, compare_game_sources=True)
        powershell_script(install_restore_script(job, restore=False), job)
        result = status(job)
    elif args.command == "restore":
        powershell_script(install_restore_script(job, restore=True), job)
        result = status(job)
    elif args.command == "status":
        result = status(job)
    elif args.command == "qa-log":
        result = qa_log_report(job, args.write_report)
        if not result["technical_pass"]:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            raise SystemExit(2)
    else:
        if args.result is None or not args.note:
            raise RuntimeError("record-qa requires --result and --note")
        result = record_qa(job, args.result, args.note)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
