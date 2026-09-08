"""Patch two animation resrefs in one ARE embedded in a BG2EE BALDUR.SAV.

The command is plan-only unless ``--run`` is supplied. A complete save-directory backup is
mandatory before the archive is replaced atomically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_fused_area_animation_carrier as carrier


SAV_SIGNATURE = b"SAV V1.0"
SCHEMA = "bg2-upscale-save-area-animation-resref-patch-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_sav(payload: bytes) -> list[dict[str, Any]]:
    require(payload[:8] == SAV_SIGNATURE, f"signature SAV invalide : {payload[:8]!r}")
    cursor = 8
    entries: list[dict[str, Any]] = []
    while cursor < len(payload):
        require(len(payload) - cursor >= 12, "en-tête d'entrée SAV tronqué")
        name_length = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        require(1 <= name_length <= 1024 and cursor + name_length + 8 <= len(payload),
                "longueur de nom SAV invalide")
        name_bytes = payload[cursor:cursor + name_length]
        cursor += name_length
        raw_length, compressed_length = struct.unpack_from("<II", payload, cursor)
        cursor += 8
        require(compressed_length <= len(payload) - cursor, "entrée SAV hors limites")
        compressed = payload[cursor:cursor + compressed_length]
        cursor += compressed_length
        raw = zlib.decompress(compressed)
        require(len(raw) == raw_length, "taille décompressée SAV invalide")
        name = name_bytes.rstrip(b"\0").decode("ascii")
        entries.append({"name": name, "name_bytes": name_bytes,
                        "compressed": compressed, "raw": raw})
    return entries


def serialize_sav(entries: list[dict[str, Any]], replacements: dict[str, bytes]) -> bytes:
    output = bytearray(SAV_SIGNATURE)
    for entry in entries:
        name_bytes = entry["name_bytes"]
        raw = replacements.get(entry["name"], entry["raw"])
        compressed = (zlib.compress(raw, level=9) if entry["name"] in replacements
                      else entry["compressed"])
        output.extend(struct.pack("<I", len(name_bytes)))
        output.extend(name_bytes)
        output.extend(struct.pack("<II", len(raw), len(compressed)))
        output.extend(compressed)
    return bytes(output)


def inventory(root: Path) -> list[dict[str, Any]]:
    return [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size,
             "sha256": sha256_file(path)}
            for path in sorted(root.rglob("*")) if path.is_file()]


def patch_save(save_dir: Path, backup_dir: Path, *, area: str,
               carrier_resref: str, null_resref: str,
               carrier_occurrence: int, null_occurrence: int,
               write: bool) -> dict[str, Any]:
    save_dir = save_dir.resolve()
    backup_dir = backup_dir.resolve()
    sav_path = save_dir / "BALDUR.SAV"
    require(save_dir.is_dir() and sav_path.is_file(), f"sauvegarde invalide : {save_dir}")
    require(backup_dir != save_dir and save_dir not in backup_dir.parents,
            "la sauvegarde de sécurité doit être hors de la sauvegarde active")
    before_sav = sav_path.read_bytes()
    entries = parse_sav(before_sav)
    target_name = f"{area.upper()}.ARE"
    targets = [entry for entry in entries if entry["name"].upper() == target_name]
    require(len(targets) == 1, f"{target_name} absent ou ambigu dans BALDUR.SAV")
    patched_area, patches = carrier.patch_area(
        targets[0]["raw"], carrier_index=carrier_occurrence, null_index=null_occurrence,
        carrier_resref=carrier_resref, null_resref=null_resref,
    )
    after_sav = serialize_sav(entries, {targets[0]["name"]: patched_area})
    verified = parse_sav(after_sav)
    require([entry["name"] for entry in verified] == [entry["name"] for entry in entries],
            "la table des entrées SAV a changé")
    for before, after in zip(entries, verified, strict=True):
        expected = patched_area if before["name"] == targets[0]["name"] else before["raw"]
        require(after["raw"] == expected, f"entrée SAV altérée : {before['name']}")
    report = {
        "schema": SCHEMA,
        "status": "planned",
        "save_directory": save_dir.as_posix(),
        "save_archive": sav_path.as_posix(),
        "backup_directory": backup_dir.as_posix(),
        "area_entry": targets[0]["name"],
        "entry_count": len(entries),
        "before_sav_sha256": sha256_bytes(before_sav),
        "after_sav_sha256": sha256_bytes(after_sav),
        "before_area_sha256": sha256_bytes(targets[0]["raw"]),
        "after_area_sha256": sha256_bytes(patched_area),
        "occurrence_patches": patches,
    }
    if not write:
        return report
    require(not backup_dir.exists(), f"sauvegarde de sécurité déjà présente : {backup_dir}")
    incoming = sav_path.with_name("BALDUR.SAV.bg2hd-incoming")
    require(not incoming.exists(), f"fichier transactionnel déjà présent : {incoming}")
    shutil.copytree(save_dir, backup_dir)
    require(sha256_file(backup_dir / "BALDUR.SAV") == report["before_sav_sha256"],
            "la sauvegarde de sécurité ne correspond pas à l'archive source")
    try:
        with incoming.open("xb") as stream:
            stream.write(after_sav)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(incoming, sav_path)
    finally:
        if incoming.exists():
            incoming.unlink()
    require(sha256_file(sav_path) == report["after_sav_sha256"],
            "hash de l'archive SAV installée invalide")
    installed = parse_sav(sav_path.read_bytes())
    installed_target = [entry for entry in installed if entry["name"].upper() == target_name]
    require(len(installed_target) == 1 and installed_target[0]["raw"] == patched_area,
            "ARE patché absent après réouverture de la sauvegarde")
    report.update({"status": "installed", "created_utc": datetime.now(timezone.utc).isoformat(),
                   "backup_inventory": inventory(backup_dir)})
    (backup_dir / "patch-transaction.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--area", default="AR2804")
    parser.add_argument("--carrier-resref", default=carrier.DEFAULT_CARRIER_RESREF)
    parser.add_argument("--null-resref", default=carrier.DEFAULT_NULL_RESREF)
    parser.add_argument("--carrier-occurrence", type=int, default=1)
    parser.add_argument("--null-occurrence", type=int, default=3)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    report = patch_save(
        args.save_dir, args.backup_dir, area=args.area,
        carrier_resref=carrier.runtime.normalise_resref(args.carrier_resref),
        null_resref=carrier.runtime.normalise_resref(args.null_resref),
        carrier_occurrence=args.carrier_occurrence, null_occurrence=args.null_occurrence,
        write=args.run,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
