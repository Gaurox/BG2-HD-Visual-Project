"""Reproducible xBR xN pipeline for BG2EE creature and Character sprites.

The pipeline keeps BAM V1 metadata at x1, stores lossless x2 or x4 palette
indices in an external registry, builds the shared runtime, and manages
reversible QA installation. Jobs without an explicit ``upscale`` block retain
the historical x2/V2 contract. The runner never launches the game and never
edits release manifests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
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


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
XBR_ADAPTER = SCRIPT_DIR / "xbr2x_batch.js"
INSTALL_SCRIPT = SCRIPT_DIR / "Install-CreatureSprite-X2-Test.ps1"
RESTORE_SCRIPT = SCRIPT_DIR / "Restore-CreatureSprite-X2-Test.ps1"
XN_INSTALL_SCRIPT = SCRIPT_DIR / "Install-CreatureSprite-XN-Test.ps1"
XN_RESTORE_SCRIPT = SCRIPT_DIR / "Restore-CreatureSprite-XN-Test.ps1"
JOB_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-job-v1"
ARMOR_SET_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-armor-set-v1"
SOURCE_SCHEMA = "bg2-upscale-creature-sprite-source-v1"
BUILD_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-pack-v1"
ARMOR_SET_BUILD_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-armor-set-pack-v1"
RUNTIME_SCHEMA = "bg2-upscale-creature-sprite-runtime-v1"
REGISTRY_MAGIC = b"IEECSX2\0"
REGISTRY_VERSION = 2
LEGACY_REGISTRY_VERSION = 1
XN_REGISTRY_MAGIC = b"IEECSXN\0"
XN_REGISTRY_VERSION = 3
LEGACY_SCALE = 2
# Readability zoom for source-only QA sheets; it is not the upscale contract.
SOURCE_PREVIEW_SCALE = 2
REGISTRY_FILENAME = "CreatureSprites-X2.registry"
XN_REGISTRY_FILENAME = "CreatureSprites-XN.registry"
REGISTRY_HEADER_BYTES = 24
REGISTRY_RESOURCE_HEADER_BYTES = 48
REGISTRY_FRAME_HEADER_BYTES = 528
BAM_TYPE = 0x03E8
ITM_TYPE = 0x03ED
IDS_TYPE = 0x03F0
INI_TYPE = 0x0802
MAX_RESOURCES = 128
MAX_FRAMES_PER_RESOURCE = 4096
MAX_CYCLES_PER_RESOURCE = 256
MAX_CYCLE_SLOTS = 65536
MAX_REGISTRY_BYTES = 128 * 1024 * 1024
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


def resolve_path(value: str | Path) -> Path:
    path = Path(os.path.expandvars(str(value)))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def relative_project_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def assert_workspace_child(path: Path, label: str) -> None:
    resolved = path.resolve()
    if resolved == PROJECT_ROOT or PROJECT_ROOT not in resolved.parents:
        raise RuntimeError(f"{label} must stay inside {PROJECT_ROOT}: {resolved}")


def load_job(job_file: Path) -> dict[str, Any]:
    job_file = job_file.resolve()
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
    set_file = set_file.resolve()
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
    identities = {contract.identity for contract in member_contracts}
    if len(identities) != 1:
        raise RuntimeError("armor-set members mix registry magic/version/scale")
    if set_contract.identity != member_contracts[0].identity:
        raise RuntimeError("armor-set upscale contract differs from member registries")
    armor_set["_job_file"] = str(set_file)
    armor_set["_kind"] = "armor-set"
    armor_set["_members"] = member_jobs
    armor_set["animation"]["id"] = animation_id.upper().replace("X", "x")
    armor_set["animation"]["ids_symbol"] = ids_symbol
    return armor_set


def load_work_item(path: Path) -> dict[str, Any]:
    schema = read_json(path.resolve()).get("schema")
    if schema == JOB_SCHEMA:
        return load_job(path)
    if schema == ARMOR_SET_SCHEMA:
        return load_armor_set(path)
    raise RuntimeError(f"unsupported job schema: {schema!r}")


def job_path(job: dict[str, Any], key: str) -> Path:
    return resolve_path(job["paths"][key])


def source_manifest_path(job: dict[str, Any]) -> Path:
    return job_path(job, "source_dir") / "manifest.json"


def build_dir(job: dict[str, Any]) -> Path:
    return job_path(job, "run_dir") / "build"


def runtime_dir(job: dict[str, Any]) -> Path:
    return job_path(job, "run_dir") / "runtime"


def active_state_path(job: dict[str, Any]) -> Path:
    return job_path(job, "run_dir") / "ingame-test" / "active-test.json"


def require_runtime_profile(job: dict[str, Any]) -> None:
    profile = str(job["animation"].get("runtime_profile", ""))
    if profile not in SUPPORTED_RUNTIME_PROFILES:
        raise RuntimeError(
            f"unsupported-runtime-profile: {profile!r}; supported: "
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
    resources = [
        f"{prefix}{suffix}"
        for suffix in CHARACTER_EQUIPMENT_SUFFIXES
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
    if target.parent != jobs_root or target.suffix.lower() != ".json":
        raise RuntimeError(f"new character job must be sprite/jobs/<job>.json: {target}")
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
    paths["source_dir"] = f"sprite/{asset_id}/source"
    paths["run_dir"] = (
        f"sprite/{asset_id}/runs/xbr{contract.scale}x-x{contract.scale}"
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
    if target.parent != jobs_root or target.suffix.lower() != ".json":
        raise RuntimeError(f"new Character equipment job must be sprite/jobs/<job>.json: {target}")
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
    paths["source_dir"] = f"sprite/{asset_id.replace('-', '_')}/source"
    paths["run_dir"] = (
        f"sprite/{asset_id.replace('-', '_')}/runs/"
        f"xbr{contract.scale}x-x{contract.scale}"
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


def map_output(frame: SourceFrame, output_rgba: bytes) -> tuple[np.ndarray, np.ndarray]:
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
        if previous is not None and previous != value:
            raise RuntimeError(f"{frame.resref} frame {frame.index}: duplicate used RGBA indices {previous}/{value}")
        color_to_index[packed] = value
    pixels = np.frombuffer(output_rgba, dtype=np.uint8).reshape(-1, 4)
    if not np.all((pixels[:, 3] == 0) | (pixels[:, 3] == 255)):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: partial alpha")
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


def make_comparison_sheet(
    frames: list[SourceFrame],
    outputs: list[tuple[int, int, bytes]],
    destination: Path,
    contract: UpscaleContract = LEGACY_UPSCALE,
) -> None:
    positions = sorted({0, len(frames) // 4, len(frames) // 2, 3 * len(frames) // 4, len(frames) - 1})
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


def preflight_registry_layout(
    resources: list[dict[str, Any]],
    scale: int,
    maximum_bytes: int = MAX_REGISTRY_BYTES,
) -> dict[str, int]:
    if scale not in {2, 4}:
        raise RuntimeError("registry preflight scale must be 2 or 4")
    if not resources or len(resources) > MAX_RESOURCES:
        raise RuntimeError("invalid source inventory")
    registry_bytes = REGISTRY_HEADER_BYTES
    index_bytes = 0
    frame_count = 0
    seen_resrefs: set[str] = set()
    for resource in resources:
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
            if payload_bytes <= 0 or payload_bytes > 0xFFFFFFFF:
                raise RuntimeError("frame payload exceeds registry record capacity")
            registry_bytes += REGISTRY_FRAME_HEADER_BYTES + payload_bytes
            index_bytes += payload_bytes
            frame_count += 1
        for cycle in cycles:
            slots = cycle.get("frame_indices") or []
            if not slots or len(slots) > MAX_CYCLE_SLOTS:
                raise RuntimeError("invalid cycle slot count in registry preflight")
            if any(int(value) < 0 or int(value) >= len(frames) for value in slots):
                raise RuntimeError("invalid cycle lookup in registry preflight")
            registry_bytes += 4 + 4 * len(slots)
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


def inspect_registry(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_REGISTRY_BYTES or len(raw) < REGISTRY_HEADER_BYTES:
        raise RuntimeError("invalid creature registry header")
    magic = raw[:8]
    version, scale, resource_count, metadata = struct.unpack_from("<IIII", raw, 8)
    legacy_format = magic == REGISTRY_MAGIC and version in (
        LEGACY_REGISTRY_VERSION,
        REGISTRY_VERSION,
    )
    xn_format = magic == XN_REGISTRY_MAGIC and version == XN_REGISTRY_VERSION
    if (
        not (legacy_format or xn_format)
        or (legacy_format and scale != LEGACY_SCALE)
        or (xn_format and scale not in {2, 4})
        or not (1 <= resource_count <= MAX_RESOURCES)
    ):
        raise RuntimeError("unsupported creature registry header")
    if version == LEGACY_REGISTRY_VERSION:
        if metadata != 0:
            raise RuntimeError("invalid legacy creature registry metadata")
        animation_id = 0xE400
    else:
        if metadata == 0 or metadata > 0xFFFF:
            raise RuntimeError("invalid creature registry animation id")
        animation_id = metadata
    offset = 24
    resources = []
    seen_resrefs: set[str] = set()
    total_frames = 0
    total_indices = 0
    for _ in range(resource_count):
        if offset + 48 > len(raw):
            raise RuntimeError("truncated creature registry resource")
        resref_bytes = raw[offset : offset + 8]
        resref = resref_bytes.split(b"\0", 1)[0].decode("ascii")
        if (
            not re.fullmatch(r"[A-Z0-9_]{1,8}", resref)
            or (b"\0" in resref_bytes and resref_bytes[len(resref) :] != b"\0" * (8 - len(resref)))
            or resref in seen_resrefs
        ):
            raise RuntimeError("invalid or duplicate registry resref")
        seen_resrefs.add(resref)
        frame_count, cycle_count = struct.unpack_from("<II", raw, offset + 40)
        offset += 48
        if not (1 <= frame_count <= MAX_FRAMES_PER_RESOURCE) or not (
            1 <= cycle_count <= MAX_CYCLES_PER_RESOURCE
        ):
            raise RuntimeError(f"invalid registry counts for {resref}")
        for _ in range(frame_count):
            if offset + 528 > len(raw):
                raise RuntimeError("truncated creature registry frame")
            width, height, _, _, _, index_bytes = struct.unpack_from("<HHhhB3xI", raw, offset)
            if width == 0 or height == 0 or raw[offset + 9 : offset + 12] != b"\0\0\0":
                raise RuntimeError(f"invalid frame header for {resref}")
            representatives = np.frombuffer(raw, dtype="<u2", count=256, offset=offset + 16)
            offset += 528
            if index_bytes != width * height * scale * scale or offset + index_bytes > len(raw):
                raise RuntimeError(f"invalid x{scale} payload for {resref}")
            indices = np.frombuffer(raw, dtype=np.uint8, count=index_bytes, offset=offset)
            if np.any(representatives[indices] == 0xFFFF):
                raise RuntimeError(f"missing representative in {resref}")
            offset += index_bytes
            total_indices += index_bytes
        for _ in range(cycle_count):
            if offset + 4 > len(raw):
                raise RuntimeError("truncated registry cycle")
            slots = struct.unpack_from("<I", raw, offset)[0]
            offset += 4
            if slots == 0 or slots > MAX_CYCLE_SLOTS:
                raise RuntimeError(f"invalid cycle slot count in {resref}")
            if offset + slots * 4 > len(raw):
                raise RuntimeError("truncated registry cycle lookup")
            values = np.frombuffer(raw, dtype="<u4", count=slots, offset=offset)
            if values.size and np.any(values >= frame_count):
                raise RuntimeError(f"invalid cycle lookup in {resref}")
            offset += slots * 4
        resources.append(resref)
        total_frames += frame_count
    if offset != len(raw):
        raise RuntimeError("trailing bytes in creature registry")
    return {
        "version": version,
        "scale": scale,
        "registry_magic": registry_magic_name(magic),
        "animation_id": f"0x{animation_id:04X}",
        "resources": resources,
        "resource_count": resource_count,
        "frame_count": total_frames,
        "index_bytes": total_indices,
        "registry_bytes": len(raw),
        "sha256": sha256_file(path),
    }


def build_is_current(job: dict[str, Any], keep_frames: bool = False) -> bool:
    report_path = build_dir(job) / "build-manifest.json"
    if not report_path.is_file():
        return False
    report = read_json(report_path)
    registry = build_dir(job) / str(report.get("registry", ""))
    contract = upscale_contract(job)
    layer_matches = True
    if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
        layer_matches = report.get("layer", {"kind": "body"}) == character_layer_config(job)
    if not registry.is_file():
        return False
    try:
        registry_info = inspect_registry(registry)
    except (OSError, RuntimeError, ValueError):
        return False
    format_matches = (
        registry_info["version"] == contract.registry_version
        and registry_info["scale"] == contract.scale
        and registry_info["registry_magic"]
        == registry_magic_name(contract.registry_magic)
        and str(report.get("registry", "")).endswith(contract.registry_filename)
    )
    adapter_hash = str(report.get("xbr_adapter_sha256", "")).upper()
    adapter_matches = adapter_hash == sha256_file(XBR_ADAPTER) or (
        not contract.explicit
        and adapter_hash in LEGACY_COMPATIBLE_XBR_ADAPTER_SHA256S
    )
    retention_matches = not keep_frames or report.get(
        f"kept_individual_x{contract.scale}_frames"
    ) is True
    return (
        report.get("schema") == BUILD_SCHEMA
        and report.get("job_id") == job["job_id"]
        and str(report.get("animation_id", "")).upper() == job["animation"]["id"].upper()
        and str(report.get("bam_prefix", "")).upper() == job["animation"]["bam_prefix"]
        and report.get("runtime_profile") == job["animation"].get("runtime_profile")
        and layer_matches
        and report.get("method") == contract.method
        and report.get("registry_version") == contract.registry_version
        and format_matches
        and report.get("source_manifest_sha256") == sha256_file(source_manifest_path(job))
        and report.get("scalepix_sha256") == sha256_file(job_path(job, "scalepix"))
        and adapter_matches
        and retention_matches
        and report.get("registry_sha256") == sha256_file(registry)
    )


def build_pack(job: dict[str, Any], force: bool, resume: bool, keep_frames: bool) -> dict[str, Any]:
    verify_sources(job, compare_game=True)
    output = build_dir(job)
    if resume and output.exists() and build_is_current(job, keep_frames):
        report = read_json(output / "build-manifest.json")
        return {"status": "reused", **inspect_registry(output / report["registry"])}
    if output.exists() and not (force or resume):
        raise RuntimeError(f"build exists; use --resume or --force: {output}")
    assert_workspace_child(output, "build output")
    manifest_path = source_manifest_path(job)
    frames, resources, source_manifest = load_source_frames(manifest_path)
    if not frames or len(resources) > MAX_RESOURCES:
        raise RuntimeError("invalid source inventory")
    contract = upscale_contract(job)
    preflight = preflight_registry_layout(resources, contract.scale)
    scalepix = job_path(job, "scalepix")
    node = str(job.get("tools", {}).get("node", "node"))
    xbr_outputs = run_xbr(frames, scalepix, node, contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="build.tmp-", dir=output.parent))
    try:
        registry = bytearray(contract.registry_magic)
        registry.extend(
            struct.pack(
                "<IIII",
                contract.registry_version,
                contract.scale,
                len(resources),
                int(job["animation"]["id"], 16),
            )
        )
        cursor = 0
        report_resources = []
        total_scaled_pixels = 0
        for resource in resources:
            source = resource["source"]
            resref = str(source["name"]).upper()
            resource_frames: list[SourceFrame] = resource["frames"]
            cycles = sorted(resource["cycles"], key=lambda item: int(item["index"]))
            if [int(item["index"]) for item in cycles] != list(range(len(cycles))):
                raise RuntimeError(f"{resref}: non-contiguous cycles")
            registry.extend(resref.encode("ascii").ljust(8, b"\0"))
            registry.extend(bytes.fromhex(sha256_file(resource["source_path"])))
            registry.extend(struct.pack("<II", len(resource_frames), len(cycles)))
            local_outputs = xbr_outputs[cursor : cursor + len(resource_frames)]
            opaque_indices: set[int] = set()
            for frame, (scaled_width, scaled_height, scaled_rgba) in zip(
                resource_frames, local_outputs, strict=True
            ):
                if (
                    scaled_width != frame.width * contract.scale
                    or scaled_height != frame.height * contract.scale
                ):
                    raise RuntimeError(
                        f"{resref} frame {frame.index}: output dimensions are not exact "
                        f"x{contract.scale}"
                    )
                mapped, representatives = map_output(frame, scaled_rgba)
                opaque_indices.update(int(value) for value in np.unique(mapped) if value != frame.transparent)
                registry.extend(struct.pack("<HHhhB3xI", frame.width, frame.height, frame.center_x, frame.center_y, frame.transparent, mapped.size))
                registry.extend(representatives.astype("<u2", copy=False).tobytes())
                registry.extend(mapped.tobytes())
                if keep_frames:
                    frame_path = (
                        temporary
                        / f"x{contract.scale}"
                        / resref
                        / f"frame-{frame.index:04}.png"
                    )
                    frame_path.parent.mkdir(parents=True, exist_ok=True)
                    Image.frombytes(
                        "RGBA", (scaled_width, scaled_height), scaled_rgba
                    ).save(frame_path)
                total_scaled_pixels += mapped.size
            for cycle in cycles:
                lookup = [int(value) for value in cycle["frame_indices"]]
                if any(value < 0 or value >= len(resource_frames) for value in lookup):
                    raise RuntimeError(f"{resref}: invalid cycle lookup")
                registry.extend(struct.pack("<I", len(lookup)))
                if lookup:
                    registry.extend(struct.pack(f"<{len(lookup)}I", *lookup))
            make_comparison_sheet(
                resource_frames,
                local_outputs,
                temporary / "qa" / f"{resref}-comparison.png",
                contract,
            )
            cursor += len(resource_frames)
            report_resources.append(
                {
                    "resref": resref,
                    "source": relative_project_path(resource["source_path"]),
                    "source_sha256": sha256_file(resource["source_path"]),
                    "frames": len(resource_frames),
                    "cycles": len(cycles),
                    "cycle_slots": sum(len(item["frame_indices"]) for item in cycles),
                    f"opaque_palette_indices_in_x{contract.scale}": len(opaque_indices),
                    "qa_sheet": f"qa/{resref}-comparison.png",
                }
            )
        if cursor != len(xbr_outputs):
            raise RuntimeError(f"unconsumed xBR{contract.scale}x frames")
        if len(registry) != preflight["registry_bytes"]:
            raise RuntimeError(
                "registry size differs from the pre-xBR projection: "
                f"{len(registry)} != {preflight['registry_bytes']}"
            )
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True, exist_ok=True)
        registry_path = pack_dir / contract.registry_filename
        registry_path.write_bytes(registry)
        registry_info = inspect_registry(registry_path)
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
            "registry": f"iee-assets/creature-sprites/{contract.registry_filename}",
            "registry_bytes": len(registry),
            "registry_sha256": registry_info["sha256"],
            f"kept_individual_x{contract.scale}_frames": keep_frames,
            "validation": {
                f"dimensions_exact_x{contract.scale}": len(frames),
                "frames_exactly_remapped_to_source_palette": len(frames),
                "partial_alpha_pixels": 0,
                "new_colors": 0,
            },
        }
        if contract.explicit:
            report["registry_magic"] = registry_info["registry_magic"]
            report["registry_scale"] = registry_info["scale"]
            report["validation"]["registry_bytes_preflight"] = preflight[
                "registry_bytes"
            ]
        if job["animation"].get("runtime_profile") == "character-bg2ee-2.7.3.0":
            report["layer"] = character_layer_config(job)
        write_json(temporary / "build-manifest.json", report)
        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)
        return {"status": "built", **registry_info}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def source_tree_hash(source_root: Path) -> str:
    relative_files = [
        "CMakeLists.txt",
        "src/iee/hooks.cpp",
        "src/iee/dll_main.cpp",
        "src/iee/creature_sprite_x2.cpp",
        "src/iee/creature_sprite_x2.h",
        "src/iee/core/config.cpp",
        "src/iee/core/config.h",
        "src/iee/game/build_manifest.cpp",
        "src/iee/game/build_manifest.h",
        "tests/iee_tests.cpp",
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


def build_runtime(job: dict[str, Any]) -> dict[str, Any]:
    require_runtime_profile(job)
    if os.name != "nt":
        raise RuntimeError("Windows is required for the BG2EE runtime DLL")
    source = job_path(job, "engine_source")
    build = job_path(job, "engine_build")
    cmake = str(job.get("tools", {}).get("cmake", "cmake"))
    runtime = job.get("runtime", {})
    if not (build / "CMakeCache.txt").is_file():
        generator = str(runtime.get("cmake_generator", "Visual Studio 16 2019"))
        architecture = str(runtime.get("cmake_arch", "x64"))
        build.parent.mkdir(parents=True, exist_ok=True)
        run_checked([cmake, "-S", str(source), "-B", str(build), "-G", generator, "-A", architecture, "-DIEE_BUILD_WINDOWS_DLL=ON", "-DBUILD_TESTING=ON"])
    run_checked([cmake, "--build", str(build), "--config", "Release", "--target", "release_bundle"])
    run_checked([cmake, "--build", str(build), "--config", "Release", "--target", "iee_tests"])
    tests = build / "Release" / "iee_tests.exe"
    if not tests.is_file():
        tests = build / "iee_tests.exe"
    run_checked([str(tests)], cwd=source)
    source_dll = build / "release-bundle" / "InfinityEngine-Enhancer.dll"
    if not source_dll.is_file():
        raise RuntimeError(f"release DLL missing: {source_dll}")
    destination = runtime_dir(job)
    destination.mkdir(parents=True, exist_ok=True)
    dll = destination / "InfinityEngine-Enhancer.dll"
    shutil.copy2(source_dll, dll)
    manifest = {
        "schema": RUNTIME_SCHEMA,
        "status": "built-tested",
        "created_at_utc": utc_now(),
        "job_id": job["job_id"],
        "runtime_profile": job["animation"]["runtime_profile"],
        "engine_source": relative_project_path(source),
        "engine_source_contract_sha256": source_tree_hash(source),
        "engine_build": relative_project_path(build),
        "dll": "InfinityEngine-Enhancer.dll",
        "dll_sha256": sha256_file(dll),
        "tests": str(tests),
        "tests_status": "passed",
    }
    write_json(destination / "runtime-manifest.json", manifest)
    return manifest


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
    if manifest.get("registry_version") != contract.registry_version:
        raise RuntimeError("build manifest registry version differs from job")
    if contract.explicit and (
        manifest.get("registry_magic") != registry_magic_name(contract.registry_magic)
        or manifest.get("registry_scale") != contract.scale
    ):
        raise RuntimeError("build manifest registry magic/scale differs from job")
    registry = build_dir(job) / str(manifest["registry"])
    info = inspect_registry(registry)
    if info["sha256"] != manifest.get("registry_sha256"):
        raise RuntimeError("registry hash differs from build manifest")
    if info["animation_id"].upper() != job["animation"]["id"].upper():
        raise RuntimeError("registry animation id differs from job")
    if (
        info["version"] != contract.registry_version
        or info["scale"] != contract.scale
        or info["registry_magic"] != registry_magic_name(contract.registry_magic)
        or registry.name != contract.registry_filename
    ):
        raise RuntimeError("registry magic/version/scale differs from job")
    prefix = job["animation"]["bam_prefix"]
    if any(not name.startswith(prefix) for name in info["resources"]):
        raise RuntimeError("registry contains an out-of-family resref")
    if info["frame_count"] != int(manifest["frame_count"]):
        raise RuntimeError("registry frame count differs from build manifest")
    if info["index_bytes"] != int(
        manifest.get(f"x{contract.scale}_pixel_count", -1)
    ):
        raise RuntimeError("registry index bytes differ from build manifest pixel count")
    validation = manifest.get("validation") or {}
    if validation.get(f"dimensions_exact_x{contract.scale}") != info["frame_count"]:
        raise RuntimeError("build manifest exact-dimension count differs from registry")
    return info


def verify_runtime(job: dict[str, Any]) -> dict[str, Any]:
    require_runtime_profile(job)
    manifest = read_json(runtime_dir(job) / "runtime-manifest.json")
    if manifest.get("schema") != RUNTIME_SCHEMA or manifest.get("tests_status") != "passed":
        raise RuntimeError("runtime is not built and tested")
    if manifest.get("job_id") != job["job_id"]:
        raise RuntimeError("runtime manifest job id differs from job")
    if manifest.get("runtime_profile") != job["animation"].get("runtime_profile"):
        raise RuntimeError("runtime manifest profile differs from job")
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
                "registry": str(read_json(manifest_path)["registry"]),
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
                "registry": str(read_json(manifest_path)["registry"]),
                "registry_sha256": build["sha256"],
                "resource_count": build["resource_count"],
                "frame_count": build["frame_count"],
                "source_resource_count": source["resources"],
            }
        records.append(record)
    return records


def armor_set_build_manifest_path(armor_set: dict[str, Any]) -> Path:
    return build_dir(armor_set) / "build-manifest.json"


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
    if manifest.get("members") != expected_members:
        raise RuntimeError("armor-set build members differ from current member jobs")
    registry = build_dir(armor_set) / str(manifest.get("registry", ""))
    info = inspect_registry(registry)
    if info["sha256"] != manifest.get("registry_sha256"):
        raise RuntimeError("armor-set registry hash differs from build manifest")
    if info["animation_id"].upper() != armor_set["animation"]["id"].upper():
        raise RuntimeError("armor-set registry animation id differs from set")
    expected_resources: list[str] = []
    expected_frames = 0
    member_infos: list[dict[str, Any]] = []
    member_methods: list[dict[str, Any]] = []
    for member in armor_set["_members"]:
        member_manifest = read_json(build_dir(member) / "build-manifest.json")
        member_registry = build_dir(member) / str(member_manifest["registry"])
        member_info = inspect_registry(member_registry)
        member_infos.append(member_info)
        member_methods.append(member_manifest.get("method"))
        expected_resources.extend(member_info["resources"])
        expected_frames += member_info["frame_count"]
    member_magic, member_version, member_scale = require_compatible_registry_infos(
        member_infos
    )
    if (
        info["registry_magic"] != member_magic
        or info["version"] != member_version
        or info["scale"] != member_scale
        or any(method != member_methods[0] for method in member_methods[1:])
        or manifest.get("method") != member_methods[0]
    ):
        raise RuntimeError("armor-set registry format differs from member registries")
    if len(expected_resources) != len(set(expected_resources)):
        raise RuntimeError("armor-set members contain duplicate BAM resources")
    if info["resources"] != expected_resources:
        raise RuntimeError("armor-set registry resources differ from member registries")
    if info["frame_count"] != expected_frames:
        raise RuntimeError("armor-set registry frame count differs from member registries")
    if info["index_bytes"] != int(manifest.get(f"x{info['scale']}_index_bytes", -1)):
        raise RuntimeError("armor-set index bytes differ from build manifest")
    set_contract = upscale_contract(armor_set)
    if set_contract.explicit and (
        manifest.get("registry_magic") != info["registry_magic"]
        or manifest.get("registry_scale") != info["scale"]
    ):
        raise RuntimeError("armor-set manifest registry magic/scale differs from set")
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
    if total_resources > MAX_RESOURCES:
        raise RuntimeError(f"armor-set resources exceed registry limit {MAX_RESOURCES}")
    member_registries: list[dict[str, Any]] = []
    member_methods: list[dict[str, Any]] = []
    for member in armor_set["_members"]:
        member_manifest = read_json(build_dir(member) / "build-manifest.json")
        member_registry = build_dir(member) / str(member_manifest["registry"])
        info = inspect_registry(member_registry)
        if info["animation_id"].upper() != armor_set["animation"]["id"].upper():
            raise RuntimeError("armor-set member registry animation id differs from set")
        member_registries.append(
            {"path": member_registry, "info": info, "manifest": member_manifest}
        )
        member_methods.append(member_manifest.get("method"))
    magic_name, registry_version, registry_scale = require_compatible_registry_infos(
        [entry["info"] for entry in member_registries]
    )
    if any(method != member_methods[0] for method in member_methods[1:]):
        raise RuntimeError("registry aggregation refuses mixed upscale methods")
    set_contract = upscale_contract(armor_set)
    if set_contract.explicit and (
        magic_name != registry_magic_name(set_contract.registry_magic)
        or registry_version != set_contract.registry_version
        or registry_scale != set_contract.scale
        or member_methods[0] != set_contract.method
    ):
        raise RuntimeError("armor-set upscale contract differs from member registries")
    projected_registry_bytes = REGISTRY_HEADER_BYTES + sum(
        int(entry["info"]["registry_bytes"]) - REGISTRY_HEADER_BYTES
        for entry in member_registries
    )
    if projected_registry_bytes > MAX_REGISTRY_BYTES:
        raise RuntimeError(
            f"armor-set registry preflight exceeds {MAX_REGISTRY_BYTES} bytes: "
            f"{projected_registry_bytes}"
        )
    if magic_name == registry_magic_name(REGISTRY_MAGIC):
        registry_magic = REGISTRY_MAGIC
        registry_filename = REGISTRY_FILENAME
    elif magic_name == registry_magic_name(XN_REGISTRY_MAGIC):
        registry_magic = XN_REGISTRY_MAGIC
        registry_filename = XN_REGISTRY_FILENAME
    else:
        raise RuntimeError("unsupported registry magic for aggregation")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="armor-set-", dir=output.parent))
    try:
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True)
        registry_path = pack_dir / registry_filename
        with registry_path.open("wb") as output_stream:
            output_stream.write(registry_magic)
            output_stream.write(
                struct.pack(
                    "<IIII",
                    registry_version,
                    registry_scale,
                    total_resources,
                    int(armor_set["animation"]["id"], 16),
                )
            )
            for entry in member_registries:
                raw = entry["path"].read_bytes()
                output_stream.write(raw[REGISTRY_HEADER_BYTES:])
        info = inspect_registry(registry_path)
        if info["resource_count"] != total_resources:
            raise RuntimeError("armor-set registry resource count differs from members")
        if info["registry_bytes"] != projected_registry_bytes:
            raise RuntimeError("armor-set registry size differs from preflight")
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
            "method": member_methods[0],
            "resource_count": info["resource_count"],
            "frame_count": info["frame_count"],
            f"x{registry_scale}_index_bytes": info["index_bytes"],
            "registry": f"iee-assets/creature-sprites/{registry_filename}",
            "registry_bytes": info["registry_bytes"],
            "registry_sha256": info["sha256"],
        }
        if registry_version == XN_REGISTRY_VERSION:
            report["registry_magic"] = info["registry_magic"]
            report["registry_scale"] = info["scale"]
            report["validation"] = {
                "registry_bytes_preflight": projected_registry_bytes
            }
        equipment_layers = armor_set_equipment_layers(armor_set)
        if equipment_layers:
            report["equipment_layers"] = equipment_layers
        write_json(temporary / "build-manifest.json", report)
        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)
        return {"status": "built", **info}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


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
        "build_manifest_exists": armor_set_build_manifest_path(armor_set).is_file(),
        "runtime_manifest_exists": (runtime_dir(armor_set) / "runtime-manifest.json").is_file(),
        "install_is_explicit": True,
        "game_launch_is_never_automatic": True,
        "release_manifest_is_out_of_scope": True,
    }


def runtime_log_session_after_install(
    text: str, exact_marker: str, installed_at_utc: str
) -> str:
    try:
        installed = datetime.fromisoformat(installed_at_utc.replace("Z", "+00:00"))
        installed_local = installed.astimezone().replace(tzinfo=None)
    except ValueError:
        return ""
    lines = text.splitlines()
    start = -1
    timestamp_pattern = re.compile(
        r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)\]"
    )
    for index, line in enumerate(lines):
        if exact_marker not in line:
            continue
        match = timestamp_pattern.match(line)
        if not match:
            continue
        try:
            timestamp = datetime.fromisoformat(match.group(1))
        except ValueError:
            continue
        if timestamp >= installed_local:
            start = index
    return "\n".join(lines[start:]) if start >= 0 else ""


def runtime_owner_labels(profile: str) -> tuple[str, str]:
    if profile == "character-bg2ee-2.7.3.0":
        return "Character::Render", "CGameAnimationTypeCharacter::Render"
    return "MonsterIcewind::Render", "CGameAnimationTypeMonsterIcewind::Render"


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
        "character_transient_by_prefix": transient_by_prefix,
        "runtime_health_pass": bool(
            pool_resets == 0
            and unbound_warnings == 0
            and transient_failures == 0
            and pixel_failures == 0
            and backing_rejections == 0
            and unsafe_in_place_uploads == 0
            and character_transient
        ),
    }


def installed_state_integrity(state: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    targets = state.get("targets")
    game_root_text = str(state.get("game_root", ""))
    if not isinstance(targets, list) or not targets or not game_root_text:
        return {
            "installed_files_match": False,
            "installed_targets_checked": 0,
            "installed_integrity_errors": ["installation state is incomplete"],
        }
    game_root = Path(game_root_text).resolve()
    checked = 0
    for target_state in targets:
        if not isinstance(target_state, dict):
            errors.append("invalid target state")
            continue
        relative_text = str(target_state.get("relative_path", ""))
        relative = Path(relative_text.replace("\\", "/"))
        if not relative_text or relative.is_absolute():
            errors.append(f"invalid installed target path: {relative_text!r}")
            continue
        target = (game_root / relative).resolve()
        try:
            target.relative_to(game_root)
        except ValueError:
            errors.append(f"installed target escapes game root: {relative_text}")
            continue
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
                errors.append(f"installed hash changed: {relative_text}")
                continue
        checked += 1
    return {
        "installed_files_match": not errors and checked == len(targets),
        "installed_targets_checked": checked,
        "installed_integrity_errors": errors,
    }


def qa_log_report(job: dict[str, Any], write_report: bool) -> dict[str, Any]:
    log_path = job_path(job, "game_root") / "InfinityEngine-Enhancer.log"
    text = log_path.read_text(encoding="utf-8", errors="replace")
    state_path = active_state_path(job)
    state = read_json(state_path) if state_path.is_file() else {}
    animation_id = job["animation"]["id"]
    contract = effective_upscale_contract(job)
    marker = f"Creature sprite xBR2x pack ready: animation {animation_id},"
    session = runtime_log_session_after_install(
        text, marker, str(state.get("installed_at_utc", ""))
    )
    session_lower = session.lower()
    prefixes = (
        armor_set_prefixes(job)
        if job.get("_kind") == "armor-set"
        else [str(job["animation"]["bam_prefix"])]
    )
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
    legacy_pack_ready = marker in session and "filter=NEAREST" in session
    pack_ready = legacy_pack_ready
    if contract.explicit:
        pack_ready = any(
            marker in line
            and f"scale=x{contract.scale}," in line
            and "source=CreatureSprites-XN.registry;" in line
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
        "composition_by_prefix": {
            prefix: len(lines) for prefix, lines in composition_by_prefix.items()
        },
        "composition_count": len(composition_lines),
        "first_composition": composition_lines[0] if composition_lines else None,
    }
    if contract.explicit:
        report["registry_scale"] = contract.scale
        report.update(installed_state_integrity(state))
    report.update(runtime_session_health(session, profile, composition_by_prefix))
    report["technical_pass"] = bool(
        report["session_after_install"]
        and report["pack_ready"]
        and report["owner_scope"]
        and report["animation_reached"]
        and report["owner_palette_snapshot"]
        and all(composition_by_prefix.values())
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
    technical = qa_log_report(job, write_report=True)
    if result == "pass" and not technical["technical_pass"]:
        raise RuntimeError("cannot validate: runtime log does not prove sprite composition")
    state["status"] = "validated-installed" if result == "pass" else "qa-failed"
    state["qa_recorded_at_utc"] = utc_now()
    state["qa_note"] = note
    write_json(state_path, state)
    backup_root = state.get("backup_root")
    if backup_root:
        backup_state = Path(str(backup_root)) / "install-state.json"
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
    if effective_upscale_contract(job).explicit:
        return XN_RESTORE_SCRIPT if restore else XN_INSTALL_SCRIPT
    return RESTORE_SCRIPT if restore else INSTALL_SCRIPT


def status(job: dict[str, Any]) -> dict[str, Any]:
    path = active_state_path(job)
    if not path.is_file():
        return {"status": "not-installed", "state": str(path)}
    state = read_json(path)
    return {"status": state.get("status"), "state": str(path), "installed_at_utc": state.get("installed_at_utc"), "backup_root": state.get("backup_root")}


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
    }:
        raise RuntimeError("--scale is only valid when creating a Character job")
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
    job = load_work_item(args.job)
    armor_set = job.get("_kind") == "armor-set"
    if args.command == "plan":
        result = plan_armor_set(job) if armor_set else plan(job)
    elif args.command == "extract":
        if armor_set:
            raise RuntimeError("extract is not supported for an armor set; prepare its member jobs")
        result = extract_sources(job, args.force, args.resume)
    elif args.command == "verify-sources":
        if armor_set:
            raise RuntimeError("verify-sources is not supported for an armor set; verify its member jobs")
        result = verify_sources(job, not args.no_game_source_check)
    elif args.command == "build":
        if armor_set:
            result = build_armor_set(job, args.force, args.resume)
        else:
            result = build_pack(job, args.force, args.resume, args.keep_upscaled_frames)
    elif args.command == "build-runtime":
        result = build_runtime(job)
    elif args.command == "prepare":
        result = (
            prepare_armor_set(job, args.force, args.resume)
            if armor_set
            else prepare(job, args.force, args.resume, args.keep_upscaled_frames)
        )
    elif args.command == "verify":
        result = verify_armor_set(job) if armor_set else verify_all(job, not args.no_game_source_check)
    elif args.command == "install":
        if armor_set:
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
