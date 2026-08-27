"""Build a validated runtime pack from a completed area-animation upscale run.

The compact binary registry contains resrefs, native frame dimensions and BAM
cycle lookup tables. Raw RGBA assets are copied with deterministic names. The
output is immutable and suitable for the reversible IEE runtime installer.
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_seedvr_comfyui import sha256_file


RUN_SCHEMA = "bg2-upscale-area-animation-run-v1"
FRAME_SCHEMA = "bg2-upscale-animation-frames-x1-v1"
UPSCALE_SCHEMA = "bg2-upscale-animation-frames-v1"
PACK_SCHEMA = "bg2-upscale-area-animation-runtime-pack-v1"
REGISTRY_MAGIC = b"IEEAAX4\0"
REGISTRY_VERSION = 1
REGISTRY_NAME = "AreaAnimations-X4.registry"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"manifeste absent : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def asset_name(resref: str, frame_index: int) -> str:
    return f"AAX4-{resref}-frame{frame_index:03d}.rgba"


def registry_header(resource_count: int) -> bytearray:
    registry = bytearray(REGISTRY_MAGIC)
    registry.extend(struct.pack("<IIII", REGISTRY_VERSION, 4, resource_count, 0))
    return registry


def drop_trailing_empty_cycles(
    cycles: list[dict[str, Any]], resref: str
) -> list[dict[str, Any]]:
    """Stock BAM V1 resources carry padding cycles with an empty lookup table
    (FIRE_1: cycle 0 is [0..14], cycles 1-4 are empty). The engine registry
    parser rejects a zero-length cycle (``area_animation_x4_registry.cpp``), so
    trailing empty cycles are dropped here. Every project occurrence of such a
    resource uses ``sequence == 0``, so nothing references the dropped cycles; an
    occurrence pointing past the trimmed list simply falls back to the native
    render, matching vanilla where the empty cycle drew nothing. A non-trailing
    empty cycle is left in place and rejected by the lookup check downstream."""
    trimmed = list(cycles)
    while trimmed and not (trimmed[-1].get("frame_indices") or []):
        trimmed.pop()
    if not trimmed:
        raise RuntimeError(f"{resref}: aucun cycle non vide")
    return trimmed


def relative_from_run(run_dir: Path, value: str) -> Path:
    path = (run_dir / value).resolve()
    try:
        path.relative_to(run_dir)
    except ValueError as exc:
        raise RuntimeError(f"chemin hors run : {value}") from exc
    return path


def build_resource(
    run_dir: Path,
    record: dict[str, Any],
    output: Path | None,
) -> tuple[bytes, dict[str, Any]]:
    resref = str(record.get("resref", "")).upper()
    try:
        encoded_resref = resref.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeError(f"resref non ASCII : {resref}") from exc
    if not encoded_resref or len(encoded_resref) > 8:
        raise RuntimeError(f"resref invalide : {resref}")
    if record.get("status") != "completed":
        raise RuntimeError(f"ressource non terminée : {resref}")

    frames_dir = relative_from_run(run_dir, record["frames_x1"])
    upscale_dir = relative_from_run(run_dir, record["upscale"])
    frame_manifest = load_json(frames_dir / "manifest.json")
    upscale_manifest = load_json(upscale_dir / "manifest.json")
    if frame_manifest.get("schema") != FRAME_SCHEMA:
        raise RuntimeError(f"{resref}: schéma x1 invalide")
    if upscale_manifest.get("schema") != UPSCALE_SCHEMA or upscale_manifest.get("status") != "completed":
        raise RuntimeError(f"{resref}: upscale incomplet")
    if upscale_manifest.get("scale") != 4:
        raise RuntimeError(f"{resref}: seul le runtime x4 est pris en charge")

    frame_count = int(frame_manifest.get("frame_count", 0))
    frame_records = sorted(upscale_manifest.get("frames") or [], key=lambda item: int(item["frame"]))
    if frame_count <= 0 or len(frame_records) != frame_count:
        raise RuntimeError(f"{resref}: nombre de frames incohérent")

    binary = bytearray()
    binary.extend(encoded_resref.ljust(8, b"\0"))
    cycles = sorted(frame_manifest.get("cycles") or [], key=lambda item: int(item["cycle"]))
    cycles = drop_trailing_empty_cycles(cycles, resref)
    if [int(item["cycle"]) for item in cycles] != list(range(len(cycles))):
        raise RuntimeError(f"{resref}: cycles non contigus")
    binary.extend(struct.pack("<II", frame_count, len(cycles)))

    assets: list[dict[str, Any]] = []
    frames: list[dict[str, Any]] = []
    for expected_index, frame in enumerate(frame_records):
        if int(frame.get("frame", -1)) != expected_index:
            raise RuntimeError(f"{resref}: frames upscale non contiguës")
        logical_width, logical_height = (int(value) for value in frame["logical_size_x1"])
        physical_width, physical_height = (int(value) for value in frame["physical_size_xn"])
        if logical_width <= 0 or logical_height <= 0:
            raise RuntimeError(f"{resref} frame {expected_index}: taille logique invalide")
        if (physical_width, physical_height) != (logical_width * 4, logical_height * 4):
            raise RuntimeError(f"{resref} frame {expected_index}: taille physique invalide")
        raw_source = (upscale_dir / frame["raw_rgba_xn"]).resolve()
        try:
            raw_source.relative_to(upscale_dir)
        except ValueError as exc:
            raise RuntimeError(f"{resref}: asset brut hors upscale") from exc
        expected_hash = frame.get("raw_rgba_xn_sha256")
        expected_size = physical_width * physical_height * 4
        if not raw_source.is_file() or raw_source.stat().st_size != expected_size:
            raise RuntimeError(f"{resref} frame {expected_index}: asset brut absent ou tronqué")
        actual_hash = sha256_file(raw_source)
        if actual_hash != expected_hash:
            raise RuntimeError(f"{resref} frame {expected_index}: hash brut incohérent")

        destination_name = asset_name(resref, expected_index)
        if output is not None:
            destination = output / destination_name
            shutil.copyfile(raw_source, destination)
            if sha256_file(destination) != actual_hash:
                raise RuntimeError(f"{resref} frame {expected_index}: copie runtime corrompue")
        binary.extend(struct.pack("<II", logical_width, logical_height))
        frames.append({
            "frame": expected_index,
            "logical_size_x1": [logical_width, logical_height],
            "physical_size_x4": [physical_width, physical_height],
            "centre_x1": frame.get("centre_x1"),
            "asset": destination_name,
            "sha256": actual_hash,
            "bytes": expected_size,
        })
        assets.append({"name": destination_name, "sha256": actual_hash, "bytes": expected_size})

    cycle_manifest: list[dict[str, Any]] = []
    for expected_cycle, cycle in enumerate(cycles):
        lookup = [int(value) for value in cycle.get("frame_indices") or []]
        if not lookup or any(value < 0 or value >= frame_count for value in lookup):
            raise RuntimeError(f"{resref} cycle {expected_cycle}: lookup invalide")
        binary.extend(struct.pack("<I", len(lookup)))
        binary.extend(struct.pack(f"<{len(lookup)}I", *lookup))
        cycle_manifest.append({"cycle": expected_cycle, "frame_indices": lookup})

    return bytes(binary), {
        "resref": resref,
        "frame_count": frame_count,
        "cycle_count": len(cycles),
        "geometry_mode": frame_manifest.get("geometry_mode"),
        "frames": frames,
        "cycles": cycle_manifest,
        "assets": assets,
    }


def resource_binary_from_manifest(resource: dict[str, Any]) -> bytes:
    """Validate one runtime-manifest resource and encode its registry record."""
    resref = str(resource.get("resref", "")).upper()
    try:
        encoded_resref = resref.encode("ascii")
    except UnicodeEncodeError as exc:
        raise RuntimeError(f"resref non ASCII : {resref}") from exc
    if not encoded_resref or len(encoded_resref) > 8:
        raise RuntimeError(f"resref invalide : {resref}")

    frame_count = int(resource.get("frame_count", 0))
    frames = sorted(resource.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    if frame_count <= 0 or len(frames) != frame_count:
        raise RuntimeError(f"{resref}: nombre de frames runtime incoherent")

    cycles = sorted(resource.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    cycles = drop_trailing_empty_cycles(cycles, resref)
    if int(resource.get("cycle_count", -1)) != len(cycles):
        raise RuntimeError(f"{resref}: nombre de cycles runtime incoherent")
    if [int(item.get("cycle", -1)) for item in cycles] != list(range(len(cycles))):
        raise RuntimeError(f"{resref}: cycles runtime non contigus")

    binary = bytearray(encoded_resref.ljust(8, b"\0"))
    binary.extend(struct.pack("<II", frame_count, len(cycles)))
    expected_assets: list[tuple[str, str, int]] = []
    for expected_index, frame in enumerate(frames):
        if int(frame.get("frame", -1)) != expected_index:
            raise RuntimeError(f"{resref}: frames runtime non contigues")
        logical_width, logical_height = (int(value) for value in frame.get("logical_size_x1") or [])
        physical_width, physical_height = (int(value) for value in frame.get("physical_size_x4") or [])
        if logical_width <= 0 or logical_height <= 0:
            raise RuntimeError(f"{resref} frame {expected_index}: taille logique runtime invalide")
        if (physical_width, physical_height) != (logical_width * 4, logical_height * 4):
            raise RuntimeError(f"{resref} frame {expected_index}: taille physique runtime invalide")
        name = str(frame.get("asset", ""))
        expected_name = asset_name(resref, expected_index)
        if name != expected_name:
            raise RuntimeError(f"{resref} frame {expected_index}: nom runtime invalide")
        expected_bytes = physical_width * physical_height * 4
        if int(frame.get("bytes", -1)) != expected_bytes:
            raise RuntimeError(f"{resref} frame {expected_index}: taille asset runtime invalide")
        digest = str(frame.get("sha256", "")).lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise RuntimeError(f"{resref} frame {expected_index}: hash runtime invalide")
        binary.extend(struct.pack("<II", logical_width, logical_height))
        expected_assets.append((name, digest, expected_bytes))

    assets = sorted(resource.get("assets") or [], key=lambda item: str(item.get("name", "")))
    if len(assets) != frame_count:
        raise RuntimeError(f"{resref}: inventaire runtime incomplet")
    actual_assets = [
        (str(asset.get("name", "")), str(asset.get("sha256", "")).lower(), int(asset.get("bytes", -1)))
        for asset in assets
    ]
    if sorted(expected_assets) != actual_assets:
        raise RuntimeError(f"{resref}: inventaire frames/assets runtime divergent")

    for expected_cycle, cycle in enumerate(cycles):
        lookup = [int(value) for value in cycle.get("frame_indices") or []]
        if not lookup or any(value < 0 or value >= frame_count for value in lookup):
            raise RuntimeError(f"{resref} cycle {expected_cycle}: lookup runtime invalide")
        binary.extend(struct.pack("<I", len(lookup)))
        binary.extend(struct.pack(f"<{len(lookup)}I", *lookup))
    return bytes(binary)


def registry_from_resources(resources: list[dict[str, Any]]) -> bytes:
    ordered = sorted(resources, key=lambda item: str(item.get("resref", "")).upper())
    resrefs = [str(resource.get("resref", "")).upper() for resource in ordered]
    if len(set(resrefs)) != len(resrefs):
        raise RuntimeError("resref duplique dans un pack runtime")
    registry = registry_header(len(ordered))
    for resource in ordered:
        registry.extend(resource_binary_from_manifest(resource))
    return bytes(registry)


def validate_pack_contents(pack_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate a completed runtime pack without trusting its registry blindly."""
    manifest = load_json(pack_root / "manifest.json")
    if (
        manifest.get("schema") != PACK_SCHEMA
        or manifest.get("status") != "completed"
        or manifest.get("scale") != 4
    ):
        raise RuntimeError(f"pack runtime incomplet ou incompatible : {pack_root}")
    resources = sorted(manifest.get("resources") or [], key=lambda item: str(item.get("resref", "")).upper())
    if (
        not resources
        or manifest.get("resource_count") != len(resources)
        or manifest.get("frame_count") != sum(int(resource.get("frame_count", 0)) for resource in resources)
    ):
        raise RuntimeError(f"inventaire runtime invalide : {pack_root}")

    expected_registry = registry_from_resources(resources)
    registry_name = str(manifest.get("registry", ""))
    if registry_name != REGISTRY_NAME or Path(registry_name).name != registry_name:
        raise RuntimeError(f"nom de registre runtime invalide : {pack_root}")
    registry_path = pack_root / registry_name
    if (
        not registry_path.is_file()
        or registry_path.read_bytes() != expected_registry
        or manifest.get("registry_sha256") != sha256_file(registry_path)
        or manifest.get("registry_bytes") != registry_path.stat().st_size
    ):
        raise RuntimeError(f"registre runtime incoherent : {registry_path}")

    expected_names = {"manifest.json", REGISTRY_NAME}
    for resource in resources:
        resource_binary_from_manifest(resource)
        for asset in resource["assets"]:
            name = str(asset["name"])
            if Path(name).name != name or name in expected_names:
                raise RuntimeError(f"nom d'asset runtime invalide : {name}")
            expected_names.add(name)
            path = pack_root / name
            if (
                not path.is_file()
                or path.stat().st_size != int(asset["bytes"])
                or sha256_file(path) != str(asset["sha256"]).lower()
            ):
                raise RuntimeError(f"asset runtime incoherent : {path}")
    actual_names = {path.name for path in pack_root.iterdir() if path.is_file()}
    if actual_names != expected_names or any(path.is_dir() for path in pack_root.iterdir()):
        raise RuntimeError(f"contenu supplementaire ou manquant dans le pack runtime : {pack_root}")
    return manifest, resources


def compile_registry(
    run_dir: Path,
    run_manifest: dict[str, Any],
    asset_output: Path | None,
) -> tuple[bytes, list[dict[str, Any]]]:
    resource_records = sorted(run_manifest.get("resources") or [], key=lambda item: item["resref"])
    if not resource_records:
        raise RuntimeError("aucune ressource dans le run")
    registry = bytearray(REGISTRY_MAGIC)
    registry.extend(struct.pack("<IIII", REGISTRY_VERSION, 4, len(resource_records), 0))
    resources: list[dict[str, Any]] = []
    for record in resource_records:
        binary, resource = build_resource(run_dir, record, asset_output)
        registry.extend(binary)
        resources.append(resource)
    return bytes(registry), resources


def alpha_override_from_manifest(
    manifest_path: Path,
    resources: list[dict[str, Any]],
) -> tuple[dict[str, Path], dict[str, Any]]:
    """Load the narrowly scoped alpha-correction manifest used by validated prototypes."""
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    if (
        manifest.get("schema") != "bg2-upscale-animation-alpha-feather-test-v1"
        or manifest.get("status") != "completed"
        or manifest.get("scale") != 4
    ):
        raise RuntimeError(f"override alpha incompatible : {manifest_path}")
    resref = str(manifest.get("resref", "")).upper()
    matching = [resource for resource in resources if str(resource.get("resref", "")).upper() == resref]
    if len(matching) != 1:
        raise RuntimeError(f"override alpha sans ressource cible unique : {resref}")
    resource = matching[0]
    frames = sorted(manifest.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    if len(frames) != int(resource["frame_count"]):
        raise RuntimeError(f"{resref}: nombre de frames override incoherent")

    source_root = manifest_path.parent
    assets_by_name: dict[str, Path] = {}
    resource_frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    for expected_index, (override, frame) in enumerate(zip(frames, resource_frames)):
        if int(override.get("frame", -1)) != expected_index:
            raise RuntimeError(f"{resref}: frames override non contigues")
        expected_name = asset_name(resref, expected_index)
        source_name = str(override.get("runtime_asset", ""))
        if Path(source_name).name != expected_name:
            raise RuntimeError(f"{resref} frame {expected_index}: nom override invalide")
        source_path = (source_root / source_name).resolve()
        try:
            source_path.relative_to(source_root)
        except ValueError as exc:
            raise RuntimeError(f"{resref}: asset override hors prototype") from exc
        expected_bytes = int(frame["bytes"])
        expected_hash = str(override.get("runtime_sha256", "")).lower()
        if (
            not source_path.is_file()
            or source_path.stat().st_size != expected_bytes
            or int(override.get("runtime_bytes", -1)) != expected_bytes
            or sha256_file(source_path) != expected_hash
        ):
            raise RuntimeError(f"{resref} frame {expected_index}: asset override incoherent")
        frame["sha256"] = expected_hash
        frame["bytes"] = expected_bytes
        assets_by_name[expected_name] = source_path
    resource["assets"] = [
        {
            "name": str(frame["asset"]),
            "sha256": str(frame["sha256"]),
            "bytes": int(frame["bytes"]),
        }
        for frame in resource_frames
    ]
    resource_binary_from_manifest(resource)
    return assets_by_name, {
        "manifest": manifest_path.as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "resref": resref,
    }


def compose_runtime_packs(
    pack_roots: list[Path],
    override_manifests: list[Path],
) -> tuple[
    list[dict[str, Any]],
    dict[str, Path],
    list[dict[str, str]],
    list[dict[str, str]],
]:
    """Compose immutable completed packs into one registry/asset inventory."""
    resources: list[dict[str, Any]] = []
    sources: dict[str, Path] = {}
    provenance: list[dict[str, str]] = []
    for requested_root in pack_roots:
        pack_root = requested_root.resolve()
        manifest, pack_resources = validate_pack_contents(pack_root)
        provenance.append({
            "pack": pack_root.as_posix(),
            "manifest_sha256": sha256_file(pack_root / "manifest.json"),
        })
        for source_resource in pack_resources:
            resource = copy.deepcopy(source_resource)
            resref = str(resource["resref"]).upper()
            if any(str(existing["resref"]).upper() == resref for existing in resources):
                raise RuntimeError(f"resref duplique entre packs source : {resref}")
            resources.append(resource)
            for asset in resource["assets"]:
                name = str(asset["name"])
                if name in sources:
                    raise RuntimeError(f"asset duplique entre packs source : {name}")
                sources[name] = pack_root / name

    if not resources:
        raise RuntimeError("aucun pack source a composer")
    override_provenance: list[dict[str, str]] = []
    for override_manifest in override_manifests:
        assets, override = alpha_override_from_manifest(override_manifest, resources)
        for name, path in assets.items():
            sources[name] = path
        override_provenance.append(override)
    ordered_resources = sorted(resources, key=lambda item: str(item["resref"]).upper())
    registry_from_resources(ordered_resources)
    return ordered_resources, sources, provenance, override_provenance


def write_composed_pack(
    output: Path,
    resources: list[dict[str, Any]],
    sources: dict[str, Path],
    provenance: list[dict[str, str]],
    override_provenance: list[dict[str, str]],
) -> dict[str, Any]:
    registry = registry_from_resources(resources)
    registry_path = output / REGISTRY_NAME
    registry_path.write_bytes(registry)
    for resource in resources:
        for asset in resource["assets"]:
            name = str(asset["name"])
            source = sources.get(name)
            if source is None:
                raise RuntimeError(f"source manquante pour l'asset compose : {name}")
            destination = output / name
            shutil.copyfile(source, destination)
            if (
                destination.stat().st_size != int(asset["bytes"])
                or sha256_file(destination) != str(asset["sha256"]).lower()
            ):
                raise RuntimeError(f"copie composee corrompue : {destination}")
    manifest = {
        "schema": PACK_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "composition": {
            "source_packs": provenance,
            "asset_overrides": override_provenance,
        },
        "scale": 4,
        "registry": REGISTRY_NAME,
        "registry_sha256": sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": len(resources),
        "frame_count": sum(int(resource["frame_count"]) for resource in resources),
        "resources": resources,
    }
    atomic_write_json(manifest, output / "manifest.json")
    validate_pack_contents(output)
    return manifest


def validate_existing_pack(
    run_dir: Path,
    run_manifest: dict[str, Any],
    output: Path,
) -> dict[str, Any]:
    validate_pack_contents(output)
    pack_manifest = load_json(output / "manifest.json")
    expected_registry, expected_resources = compile_registry(run_dir, run_manifest, None)
    registry_path = output / REGISTRY_NAME
    if (
        pack_manifest.get("schema") != PACK_SCHEMA
        or pack_manifest.get("status") != "completed"
        or pack_manifest.get("scale") != 4
        or Path(str(pack_manifest.get("source_run", ""))).resolve() != run_dir
        or pack_manifest.get("source_run_manifest_sha256")
        != sha256_file(run_dir / "manifest.json")
        or pack_manifest.get("resources") != expected_resources
        or pack_manifest.get("resource_count") != len(expected_resources)
        or pack_manifest.get("frame_count")
        != sum(resource["frame_count"] for resource in expected_resources)
    ):
        raise RuntimeError(f"pack runtime existant incohérent : {output}")
    if not registry_path.is_file() or registry_path.read_bytes() != expected_registry:
        raise RuntimeError(f"registre runtime existant incohérent : {registry_path}")
    if (
        pack_manifest.get("registry_sha256") != sha256_file(registry_path)
        or pack_manifest.get("registry_bytes") != registry_path.stat().st_size
    ):
        raise RuntimeError(f"empreinte du registre runtime incohérente : {registry_path}")

    expected_names = {"manifest.json", REGISTRY_NAME}
    for resource in expected_resources:
        for asset in resource["assets"]:
            expected_names.add(asset["name"])
            path = output / asset["name"]
            if (
                not path.is_file()
                or path.stat().st_size != asset["bytes"]
                or sha256_file(path) != asset["sha256"]
            ):
                raise RuntimeError(f"asset runtime existant incohérent : {path}")
    actual_names = {path.name for path in output.iterdir() if path.is_file()}
    if actual_names != expected_names or any(path.is_dir() for path in output.iterdir()):
        raise RuntimeError(f"contenu supplémentaire ou manquant dans le pack runtime : {output}")
    return pack_manifest


def validate_existing_composed_pack(
    output: Path,
    resources: list[dict[str, Any]],
    provenance: list[dict[str, str]],
    override_provenance: list[dict[str, str]],
) -> dict[str, Any]:
    manifest, actual_resources = validate_pack_contents(output)
    expected_composition = {
        "source_packs": provenance,
        "asset_overrides": override_provenance,
    }
    if (
        manifest.get("composition") != expected_composition
        or actual_resources != resources
        or manifest.get("resource_count") != len(resources)
        or manifest.get("frame_count") != sum(int(resource["frame_count"]) for resource in resources)
    ):
        raise RuntimeError(f"pack runtime compose existant incoherent : {output}")
    return manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="dossier de run terminé")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="dossier runtime à créer (défaut : <run>/03_runtime_pack)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="valide et réutilise un pack terminé sans le réécrire",
    )
    parser.add_argument(
        "--include-pack",
        type=Path,
        action="append",
        default=[],
        help="pack runtime x4 terminé supplémentaire à composer ; répétable",
    )
    parser.add_argument(
        "--alpha-override-manifest",
        type=Path,
        action="append",
        default=[],
        help="manifest d'un correctif alpha validé à conserver dans la composition ; répétable",
    )
    args = parser.parse_args(argv)

    run_dir = args.run.resolve()
    output = args.output.resolve() if args.output else run_dir / "03_runtime_pack"
    run_manifest = load_json(run_dir / "manifest.json")
    if run_manifest.get("schema") != RUN_SCHEMA or run_manifest.get("status") != "completed":
        raise RuntimeError("le run source n'est pas terminé")
    if run_manifest.get("request", {}).get("scale") != 4:
        raise RuntimeError("le run source n'est pas x4")

    composing = bool(args.include_pack or args.alpha_override_manifest)
    if composing:
        primary_pack = run_dir / "03_runtime_pack"
        if not primary_pack.is_dir():
            raise RuntimeError("le pack runtime primaire doit etre construit avant une composition")
        if output == primary_pack:
            raise RuntimeError("une composition doit viser un dossier runtime distinct du pack primaire")
        resources, sources, provenance, override_provenance = compose_runtime_packs(
            [primary_pack, *args.include_pack],
            args.alpha_override_manifest,
        )
    if output.exists() and any(output.iterdir()):
        if not args.resume:
            raise RuntimeError(f"destination runtime non vide : {output}")
        if composing:
            manifest = validate_existing_composed_pack(
                output,
                resources,
                provenance,
                override_provenance,
            )
            print(
                f"already completed and validated composed runtime pack: "
                f"{manifest['resource_count']} BAM, {manifest['frame_count']} frames in {output}"
            )
            return
        manifest = validate_existing_pack(run_dir, run_manifest, output)
        print(
            f"already completed and validated runtime pack: "
            f"{manifest['resource_count']} BAM, {manifest['frame_count']} frames in {output}"
        )
        return
    if output.exists():
        output.rmdir()

    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise RuntimeError(f"dossier partiel existant : {partial}")
    partial.mkdir(parents=True)
    try:
        if composing:
            manifest = write_composed_pack(
                partial,
                resources,
                sources,
                provenance,
                override_provenance,
            )
            partial.replace(output)
            print(
                f"completed composed runtime pack: {manifest['resource_count']} BAM, "
                f"{manifest['frame_count']} frames in {output}"
            )
            return
        registry, resources = compile_registry(run_dir, run_manifest, partial)

        registry_path = partial / REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest = {
            "schema": PACK_SCHEMA,
            "status": "completed",
            "created_utc": utc_now(),
            "source_run": run_dir.as_posix(),
            "source_run_manifest_sha256": sha256_file(run_dir / "manifest.json"),
            "scale": 4,
            "registry": REGISTRY_NAME,
            "registry_sha256": sha256_file(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "resource_count": len(resources),
            "frame_count": sum(resource["frame_count"] for resource in resources),
            "resources": resources,
        }
        atomic_write_json(manifest, partial / "manifest.json")
        partial.replace(output)
        print(
            f"completed runtime pack: {manifest['resource_count']} BAM, "
            f"{manifest['frame_count']} frames in {output}"
        )
    except Exception:
        # Keep the partial directory for forensic inspection. A new build must
        # use an empty destination and never overwrite ambiguous output.
        raise


if __name__ == "__main__":
    main()
