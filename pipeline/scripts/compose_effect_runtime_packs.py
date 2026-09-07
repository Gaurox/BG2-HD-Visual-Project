"""Compose immutable effect packs without rebuilding their source runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_SCHEMA = "bg2-upscale-effect-animation-runtime-pack-v1"
REGISTRY_MAGIC = b"IEEEFX4\0"
REGISTRY_NAME = "EffectAnimations-X4.registry"
REGISTRY_HEADER = struct.Struct("<8sIIII")
FRAME_NAME = re.compile(r"EFX4-([A-Z0-9_]{1,8})-frame([0-9]{3})\.rgba$")
MAX_RESOURCES = 512


class PackError(RuntimeError):
    pass


@dataclass(frozen=True)
class InputPack:
    root: Path
    manifest: dict[str, Any]
    manifest_sha256: str
    registry_version: int
    resource_count: int
    registry_records: bytes
    resources: tuple[dict[str, Any], ...]
    frames: tuple[dict[str, Any], ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def require_relative(value: str, label: str) -> Path:
    target = (REPO_ROOT / value).resolve()
    try:
        target.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise PackError(f"{label} hors workspace : {value}") from exc
    return target


def relative_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError as exc:
        raise PackError(f"chemin hors workspace : {path}") from exc


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackError(f"manifest illisible : {path}") from exc
    if not isinstance(payload, dict):
        raise PackError(f"manifest invalide : {path}")
    return payload


def normalize_resources(
    manifest: dict[str, Any], asset_resrefs: set[str], resource_count: int
) -> tuple[dict[str, Any], ...]:
    declared = manifest.get("resources")
    if declared is None:
        resref = manifest.get("resref")
        if not isinstance(resref, str) or asset_resrefs != {resref} or resource_count != 1:
            raise PackError("ressource du pack unitaire incohérente")
        resource: dict[str, Any] = {
            "resref": resref,
            "frame_count": manifest.get("frame_count"),
            "cycles": manifest.get("cycles"),
            "source": manifest.get("source"),
        }
        if "timeline" in manifest:
            resource["timeline"] = manifest["timeline"]
        return (resource,)
    if not isinstance(declared, list) or len(declared) != resource_count:
        raise PackError("inventaire des ressources du pack incohérent")
    resources: list[dict[str, Any]] = []
    names: set[str] = set()
    for item in declared:
        if not isinstance(item, dict) or not isinstance(item.get("resref"), str):
            raise PackError("descripteur de ressource invalide")
        name = item["resref"]
        if name in names:
            raise PackError(f"resref dupliqué dans le pack : {name}")
        names.add(name)
        resources.append(dict(item))
    if names != asset_resrefs:
        raise PackError("ressources et frames du pack divergent")
    return tuple(resources)


def validate_pack(root: Path) -> InputPack:
    if root.is_symlink() or not root.is_dir():
        raise PackError(f"pack absent ou non sûr : {root}")
    entries = list(root.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in entries):
        raise PackError(f"pack non plat ou non régulier : {root}")
    by_name = {path.name: path for path in entries}
    if len(by_name) != len(entries):
        raise PackError(f"collision de noms dans le pack : {root}")
    manifest_path = by_name.get("manifest.json")
    registry_path = by_name.get(REGISTRY_NAME)
    if manifest_path is None or registry_path is None:
        raise PackError(f"manifest ou registre absent : {root}")
    manifest = load_manifest(manifest_path)
    if (
        manifest.get("schema") != PACK_SCHEMA
        or manifest.get("status") != "completed"
        or manifest.get("scale") != 4
        or manifest.get("registry") != REGISTRY_NAME
        or manifest.get("registry_magic") != "IEEEFX4"
        or manifest.get("registry_version") not in {1, 2}
    ):
        raise PackError(f"manifest incompatible : {root}")
    registry = registry_path.read_bytes()
    if len(registry) < REGISTRY_HEADER.size:
        raise PackError(f"registre tronqué : {registry_path}")
    magic, version, scale, resource_count, reserved = REGISTRY_HEADER.unpack_from(registry)
    if (
        magic != REGISTRY_MAGIC
        or version != manifest["registry_version"]
        or scale != 4
        or resource_count < 1
        or resource_count > MAX_RESOURCES
        or reserved != 0
        or manifest.get("registry_bytes") != len(registry)
        or str(manifest.get("registry_sha256", "")).upper() != sha256_file(registry_path)
    ):
        raise PackError(f"registre incohérent : {registry_path}")
    frames = manifest.get("frames")
    if (
        not isinstance(frames, list)
        or not frames
        or manifest.get("frame_count") != len(frames)
    ):
        raise PackError(f"inventaire de frames invalide : {root}")
    expected_names = {"manifest.json", REGISTRY_NAME, "README.md"}
    normalized_frames: list[dict[str, Any]] = []
    asset_resrefs: set[str] = set()
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict) or frame.get("frame") != index:
            raise PackError(f"index de frame invalide : {root}")
        asset = frame.get("asset")
        match = FRAME_NAME.fullmatch(asset) if isinstance(asset, str) else None
        if match is None or asset in expected_names or asset not in by_name:
            raise PackError(f"asset de frame invalide : {asset}")
        asset_path = by_name[asset]
        if (
            frame.get("bytes") != asset_path.stat().st_size
            or str(frame.get("sha256", "")).upper() != sha256_file(asset_path)
        ):
            raise PackError(f"asset de frame incohérent : {asset}")
        expected_names.add(asset)
        asset_resrefs.add(match.group(1))
        normalized = dict(frame)
        normalized["resref"] = match.group(1)
        normalized["resource_frame"] = int(match.group(2))
        normalized_frames.append(normalized)
    unexpected = set(by_name) - expected_names
    if unexpected:
        raise PackError(f"inventaire divergent : {sorted(unexpected)}")
    resources = normalize_resources(manifest, asset_resrefs, resource_count)
    counts = {
        resref: sum(frame["resref"] == resref for frame in normalized_frames)
        for resref in asset_resrefs
    }
    if any(
        type(resource.get("frame_count")) is not int
        or resource["frame_count"] != counts.get(resource["resref"])
        for resource in resources
    ):
        raise PackError("nombre de frames par ressource incohérent")
    return InputPack(
        root=root,
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        registry_version=version,
        resource_count=resource_count,
        registry_records=registry[REGISTRY_HEADER.size :],
        resources=resources,
        frames=tuple(normalized_frames),
    )


def compose(packs: list[InputPack]) -> tuple[bytes, dict[str, Any], list[tuple[Path, str]]]:
    if not packs:
        raise PackError("au moins un pack source est requis")
    versions = {pack.registry_version for pack in packs}
    if len(versions) != 1:
        raise PackError("les packs natifs v1 et 30 FPS v2 ne peuvent pas être mélangés")
    resource_count = sum(pack.resource_count for pack in packs)
    if resource_count > MAX_RESOURCES:
        raise PackError(f"trop de ressources : {resource_count}")
    resources: list[dict[str, Any]] = []
    frames: list[dict[str, Any]] = []
    copies: list[tuple[Path, str]] = []
    seen_resrefs: set[str] = set()
    seen_assets: set[str] = set()
    sources: list[dict[str, Any]] = []
    for pack in packs:
        source_path = relative_to_repo(pack.root)
        sources.append(
            {
                "path": source_path,
                "manifest_sha256": pack.manifest_sha256,
                "registry_sha256": str(pack.manifest["registry_sha256"]).upper(),
                "resource_count": pack.resource_count,
            }
        )
        for resource in pack.resources:
            resref = resource["resref"]
            if resref in seen_resrefs:
                raise PackError(f"resref présent dans plusieurs packs : {resref}")
            seen_resrefs.add(resref)
            resources.append(dict(resource))
        for frame in pack.frames:
            asset = frame["asset"]
            if asset in seen_assets:
                raise PackError(f"asset présent dans plusieurs packs : {asset}")
            seen_assets.add(asset)
            record = dict(frame)
            record["frame"] = len(frames)
            record["source_pack"] = source_path
            frames.append(record)
            copies.append((pack.root / asset, asset))
    version = versions.pop()
    registry = REGISTRY_HEADER.pack(REGISTRY_MAGIC, version, 4, resource_count, 0) + b"".join(
        pack.registry_records for pack in packs
    )
    manifest = {
        "schema": PACK_SCHEMA,
        "status": "completed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scale": 4,
        "registry": REGISTRY_NAME,
        "registry_magic": "IEEEFX4",
        "registry_version": version,
        "registry_bytes": len(registry),
        "registry_sha256": hashlib.sha256(registry).hexdigest().upper(),
        "resource_count": resource_count,
        "resources": resources,
        "frame_count": len(frames),
        "frames": frames,
        "source_packs": sources,
    }
    return registry, manifest, copies


def require_empty_output(path: Path) -> None:
    if path.is_symlink():
        raise PackError(f"sortie liée interdite : {path}")
    if path.exists():
        if not path.is_dir():
            raise PackError(f"sortie non répertoire : {path}")
        residual = {item.name for item in path.iterdir()} - {"README.md"}
        if residual:
            raise PackError(f"sortie déjà occupée : {path}")


def write_pack(
    output: Path,
    registry: bytes,
    manifest: dict[str, Any],
    copies: list[tuple[Path, str]],
) -> None:
    require_empty_output(output)
    output.mkdir(parents=True, exist_ok=True)
    registry_path = output / REGISTRY_NAME
    registry_path.write_bytes(registry)
    for source, name in copies:
        shutil.copyfile(source, output / name)
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", action="append", required=True, help="pack source relatif au workspace")
    parser.add_argument("--output", required=True, help="nouveau pack composé relatif au workspace")
    parser.add_argument("--run", action="store_true", help="écrire le pack composé")
    args = parser.parse_args(argv)
    try:
        roots = [require_relative(value, "pack source") for value in args.pack]
        output = require_relative(args.output, "sortie")
        packs = [validate_pack(root) for root in roots]
        registry, manifest, copies = compose(packs)
        plan = {
            "source_packs": [relative_to_repo(root) for root in roots],
            "output": relative_to_repo(output),
            "registry_version": manifest["registry_version"],
            "resource_count": manifest["resource_count"],
            "frame_count": manifest["frame_count"],
            "registry_bytes": len(registry),
            "frame_bytes": sum(source.stat().st_size for source, _ in copies),
            "write": bool(args.run),
        }
        if args.run:
            write_pack(output, registry, manifest, copies)
            plan["manifest_sha256"] = sha256_file(output / "manifest.json")
            plan["registry_sha256"] = sha256_file(output / REGISTRY_NAME)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, OSError, PackError, TypeError, ValueError) as error:
        print(f"erreur: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
