"""Check one generated map without reconstructing its pixels."""

import argparse
import os
import struct
import zlib

from bg2lib import load_key, resolve_resource


def pvr_dimensions(path):
    with open(path, "rb") as stream:
        declared = struct.unpack("<I", stream.read(4))[0]
        inflater = zlib.decompressobj()
        header = b""
        while len(header) < 52:
            chunk = stream.read(65536)
            assert chunk, f"{path}: truncated PVRZ header"
            header += inflater.decompress(chunk, 52 - len(header))
    assert declared >= 52 and len(header) == 52, f"{path}: invalid PVR header"
    values = struct.unpack("<13I", header)
    assert values[0] == 0x03525650, f"{path}: bad PVR signature"
    return values[7], values[6]


def png_dimensions(path):
    with open(path, "rb") as stream:
        header = stream.read(24)
    assert header[:16] == b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", f"{path}: bad PNG header"
    return struct.unpack(">II", header[16:24])


def verify(area, out_dir, upscaled_png):
    bif_entries, res_entries = load_key()
    wed_by = {row[0].upper(): row for row in res_entries if row[1] == 0x03E9}
    wdata, _ = resolve_resource(bif_entries, wed_by[area][2])
    _, _, overlays_offset = struct.unpack_from("<III", wdata, 8)
    overlay_width, overlay_height = struct.unpack_from("<HH", wdata, overlays_offset)
    tileset = wdata[overlays_offset + 4 : overlays_offset + 12].split(b"\0")[0].decode("ascii")

    with open(os.path.join(out_dir, f"{tileset.upper()}.TIS"), "rb") as stream:
        tis = stream.read()
    assert tis[:8] == b"TIS V1  ", "bad TIS signature"
    tile_count, entry_size, header_size, tile_dim = struct.unpack_from("<IIII", tis, 8)
    assert entry_size == 12 and header_size == 24
    assert len(tis) == header_size + tile_count * entry_size, "bad TIS size"
    assert tile_dim in (64, 128, 256, 512), f"bad tile dimension {tile_dim}"

    source_size = png_dimensions(upscaled_png)
    expected = overlay_width * tile_dim, overlay_height * tile_dim
    assert source_size == expected, f"source {source_size}, expected {expected}"

    prefix = tileset[0] + tileset[2:]
    pages = {}
    for index in range(tile_count):
        page, x, y = struct.unpack_from("<3I", tis, header_size + index * entry_size)
        if page == 0xFFFFFFFF:
            continue
        if page not in pages:
            filename = f"{prefix}{page:02d}.PVRZ".upper()
            pages[page] = pvr_dimensions(os.path.join(out_dir, filename))
        width, height = pages[page]
        assert x + tile_dim <= width and y + tile_dim <= height, (
            f"tile {index} outside page {page}"
        )

    print(f"OK: {tile_count} tiles, {len(pages)} pages, tile {tile_dim}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area")
    parser.add_argument("out_dir")
    parser.add_argument("upscaled_png")
    args = parser.parse_args(argv)
    verify(args.area.upper(), args.out_dir, args.upscaled_png)


if __name__ == "__main__":
    main()
