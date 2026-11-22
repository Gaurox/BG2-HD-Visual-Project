"""Pack the visually accepted ground-item body and cyan layers for the game."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
QA = ROOT / "icons/index/qa-decisions/batches/20261122-item-ground-x2-cyan-visual-accepted-v1.json"
RUN = ROOT / "icons/batches/item-ground-x2-runtime-20261122-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_verified(path, expected):
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError(f"{path}: evidence hash mismatch")
    return data


def read_rgba(record):
    from io import BytesIO

    data = read_verified(ROOT / record["path"], record["sha256"])
    with Image.open(BytesIO(data)) as image:
        if image.mode != "RGBA":
            raise ValueError(f"{record['path']}: an RGBA PNG is required")
        return image.size, image.tobytes()


def build(dll):
    qa = json.loads(QA.read_bytes())
    asset_ids = sorted(qa["asset_ids"])
    if len(set(asset_ids)) != len(asset_ids) or qa["qa_state"] != "visual-accepted":
        raise ValueError("An accepted ground-item batch is required")
    evidence = {}
    for run in qa["evidence"]:
        descriptor = json.loads(read_verified(ROOT / run["descriptor"], run["descriptor_sha256"]))
        evidence.update({row["role"]: row for row in descriptor["outputs"]})
    payload = bytearray(struct.pack("<8sI", b"IEEGIX2\0", len(asset_ids)))
    for asset in asset_ids:
        size, body = read_rgba(evidence[f"{asset}:reboutcx-x2-rgba"])
        outline_size, outline = read_rgba(evidence[f"{asset}:cyan-overlay-x2"])
        width, height = size
        if size != outline_size or width % 2 or height % 2 or not (2 <= width <= 256 and 2 <= height <= 256):
            raise ValueError(f"{asset}: invalid x2 geometry")
        payload.extend(struct.pack("<8sHH", asset.encode("ascii"), width // 2, height // 2))
        payload.extend(body)
        payload.extend(outline)
    dll = dll.resolve()
    dll_hash = digest(dll.read_bytes())
    dll_relative = dll.relative_to(ROOT).as_posix()
    RUN.mkdir(parents=True, exist_ok=True)
    pack = RUN / "GroundItems-X2.registry"
    if pack.exists():
        read_verified(pack, digest(payload))
    else:
        pack.write_bytes(payload)
    manifest = RUN / "runtime.json"
    manifest.write_text(json.dumps({
        "schema": "bg2-ground-items-x2-runtime-v1",
        "asset_ids": asset_ids,
        "sampler": "nearest",
        "qa_decision": QA.relative_to(ROOT).as_posix(),
        "registry": pack.relative_to(ROOT).as_posix(),
        "registry_sha256": digest(payload),
        "dll": dll_relative,
        "dll_sha256": dll_hash,
        "baldur_real_sha256": "B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"{len(asset_ids)} assets, {len(payload)} bytes: {manifest.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    build(parser.parse_args().dll)


if __name__ == "__main__":
    main()
