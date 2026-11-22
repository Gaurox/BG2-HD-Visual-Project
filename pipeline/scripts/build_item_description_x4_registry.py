"""Package the verified description PNGs for the BG2 test renderer."""

import argparse
import hashlib
import io
import json
import struct
import zlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
HEADER = struct.Struct("<8sI")
RECORD = struct.Struct("<8sHHHIQ")


def build(manifest_path: Path, destination: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = {}
    for entry in manifest["outputs"]:
        role = entry["role"].split(":")
        if len(role) == 3 and role[2] == "seedvr2-7b-x4-rgba":
            key = (role[0], int(role[1]))
            if key in outputs:
                raise ValueError(f"Duplicate frame {key}")
            outputs[key] = entry
    expected = {(asset, slot) for asset in manifest["asset_ids"]
                for slot in range(4 if asset == "CSHLD20" else 1)}
    if len(manifest["asset_ids"]) != 976 or outputs.keys() != expected or len(outputs) != 979:
        raise ValueError("Expected 976 illustrations and 979 frames")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    temporary = destination.with_suffix(".tmp")
    try:
        with temporary.open("xb") as target:
            target.write(HEADER.pack(b"IEEIDX4\0", len(outputs)))
            target.seek(RECORD.size * len(outputs), 1)
            index = []
            for (asset, slot), entry in sorted(outputs.items()):
                data = (ROOT / entry["path"]).read_bytes()
                if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
                    raise ValueError(f"Production hash mismatch: {asset} frame {slot}")
                with Image.open(io.BytesIO(data)) as image:
                    width, height = image.size
                    if (image.mode != "RGBA" or width % 4 or height % 4
                            or not (4 <= width <= 2048 and 4 <= height <= 2048)):
                        raise ValueError(f"Invalid frame: {asset} frame {slot}, {image.size}")
                    pixels = image.tobytes()
                compressed = zlib.compress(pixels, 4)
                if zlib.decompress(compressed) != pixels:
                    raise ValueError(f"Compression round-trip failed: {asset} frame {slot}")
                index.append(RECORD.pack(asset.encode("ascii"), slot, width // 4, height // 4,
                                         len(compressed), target.tell()))
                target.write(compressed)
            target.seek(HEADER.size)
            target.writelines(index)
        temporary.rename(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"{len(manifest['asset_ids'])} illustrations, {len(outputs)} frames, "
          f"{destination.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build(args.manifest, args.destination)
