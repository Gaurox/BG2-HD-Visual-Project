"""Repack PVRZ Deflate streams without changing their decoded PVR payload.

This is an opt-in performance experiment for large atlas pages.  It copies the
TIS byte-for-byte and rewrites only the zlib stream that follows the four-byte
decoded-size prefix of each PVRZ.  The source directory is never modified and
the output directory must not already exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import zlib


MANIFEST_NAME = "repack-manifest.json"
MANIFEST_SCHEMA = "bg2-upscale-pvrz-repack-v1"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def decode_pvrz(blob: bytes, name: str) -> bytes:
    if len(blob) < 5:
        raise ValueError(f"{name}: PVRZ tronquée")
    expected_size = struct.unpack_from("<I", blob)[0]
    try:
        decoded = zlib.decompress(blob[4:])
    except zlib.error as exc:
        raise ValueError(f"{name}: flux zlib invalide") from exc
    if len(decoded) != expected_size:
        raise ValueError(
            f"{name}: taille décodée {len(decoded)} différente du préfixe {expected_size}"
        )
    return decoded


def repack_directory(source_root: Path, output_root: Path, level: int) -> dict[str, object]:
    if level < 0 or level > 9:
        raise ValueError("le niveau zlib doit être compris entre 0 et 9")

    source = source_root.resolve()
    output = output_root.resolve()
    if not source.is_dir():
        raise ValueError(f"dossier source absent : {source}")
    if source == output:
        raise ValueError("la sortie doit être distincte de la source")
    if output.exists():
        raise ValueError(f"la sortie existe déjà : {output}")

    tis_files = sorted(path for path in source.iterdir() if path.is_file() and path.suffix.upper() == ".TIS")
    pvrz_files = sorted(
        path for path in source.iterdir() if path.is_file() and path.suffix.upper() == ".PVRZ"
    )
    if len(tis_files) != 1:
        raise ValueError(f"la source doit contenir exactement un TIS, trouvé : {len(tis_files)}")
    if not pvrz_files:
        raise ValueError("la source ne contient aucune page PVRZ")

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        tis_source = tis_files[0]
        tis_payload = tis_source.read_bytes()
        (temporary / tis_source.name).write_bytes(tis_payload)

        file_records: list[dict[str, object]] = []
        source_total = 0
        output_total = 0
        for path in pvrz_files:
            source_blob = path.read_bytes()
            decoded = decode_pvrz(source_blob, path.name)
            output_blob = struct.pack("<I", len(decoded)) + zlib.compress(decoded, level)
            if decode_pvrz(output_blob, path.name) != decoded:
                raise RuntimeError(f"{path.name}: divergence après repack")
            (temporary / path.name).write_bytes(output_blob)
            source_total += len(source_blob)
            output_total += len(output_blob)
            file_records.append(
                {
                    "name": path.name,
                    "source_sha256": sha256_bytes(source_blob),
                    "output_sha256": sha256_bytes(output_blob),
                    "decoded_pvr_sha256": sha256_bytes(decoded),
                    "decoded_bytes": len(decoded),
                    "source_bytes": len(source_blob),
                    "output_bytes": len(output_blob),
                }
            )

        manifest: dict[str, object] = {
            "schema": MANIFEST_SCHEMA,
            "status": "completed",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_root": str(source),
            "output_root": str(output),
            "compression": {"codec": "zlib", "level": level},
            "tis": {
                "name": tis_source.name,
                "sha256": sha256_bytes(tis_payload),
                "bytes": len(tis_payload),
                "copied_byte_exact": True,
            },
            "pvrz_pages": len(file_records),
            "source_pvrz_bytes": source_total,
            "output_pvrz_bytes": output_total,
            "decoded_payloads_byte_exact": True,
            "files": file_records,
        }
        (temporary / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(temporary, output)
        return manifest
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recompresse les PVRZ dans un nouveau dossier en préservant le PVR décodé."
    )
    parser.add_argument("source", type=Path, help="build TIS/PVRZ source")
    parser.add_argument("output", type=Path, help="nouveau dossier de sortie, obligatoirement absent")
    parser.add_argument("--level", type=int, choices=range(10), required=True, help="niveau zlib 0..9")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = repack_directory(args.source, args.output, args.level)
    source_mib = int(manifest["source_pvrz_bytes"]) / 1024 / 1024
    output_mib = int(manifest["output_pvrz_bytes"]) / 1024 / 1024
    print(f"PVRZ repackées : {manifest['pvrz_pages']}")
    print(f"PVR décodés identiques : {manifest['decoded_payloads_byte_exact']}")
    print(f"TIS copié à l'identique : {manifest['tis']['copied_byte_exact']}")
    print(f"Taille PVRZ : {source_mib:.2f} -> {output_mib:.2f} MiB")
    print(f"Manifeste : {Path(args.output).resolve() / MANIFEST_NAME}")


if __name__ == "__main__":
    main()
