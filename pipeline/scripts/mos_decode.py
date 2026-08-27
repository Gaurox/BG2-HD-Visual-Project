import struct, zlib, io
import numpy as np
from PIL import Image

FOURCC = {7: b'DXT1', 9: b'DXT3', 11: b'DXT5', 6: None}


def pvr_to_dds_bytes(pvr_data):
    magic, flags, pf_low, pf_high, colorspace, channeltype, height, width, depth, numsurf, numfaces, mipcount, metasize = struct.unpack_from('<13I', pvr_data, 0)
    tex_data = pvr_data[52 + metasize:]
    if pf_low not in FOURCC or FOURCC[pf_low] is None:
        raise ValueError(f"Unsupported PVR pixel format {pf_low}")
    fourcc = FOURCC[pf_low]
    dwFlags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000
    dds_header = struct.pack('<7I44x', 124, dwFlags, height, width, len(tex_data), 0, 0)
    pixelformat = struct.pack('<2I4s5I', 32, 0x4, fourcc, 0, 0, 0, 0, 0)
    caps = struct.pack('<4I', 0x1000, 0, 0, 0)
    reserved2 = struct.pack('<I', 0)
    return b'DDS ' + dds_header + pixelformat + caps + reserved2 + tex_data, width, height


def decode_pvrz_page(pvrz_raw_resource_bytes):
    dec = zlib.decompress(pvrz_raw_resource_bytes[4:])
    dds_bytes, w, h = pvr_to_dds_bytes(dec)
    img = Image.open(io.BytesIO(dds_bytes))
    img.load()
    return img.convert("RGBA")


def decode_mos_v1(data):
    assert data[0:8] == b'MOS V1  '
    width, height, cols, rows, blocksize, paloff = struct.unpack_from('<HHHHII', data, 8)
    num_blocks = cols * rows
    pal_table_size = num_blocks * 256 * 4
    offsets_start = paloff + pal_table_size
    block_offsets = struct.unpack_from(f'<{num_blocks}I', data, offsets_start)
    pixel_data_base = offsets_start + num_blocks * 4

    canvas = np.zeros((height, width, 3), dtype=np.uint8)

    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            pal_off = paloff + idx * 256 * 4
            pal_bytes = np.frombuffer(data, dtype=np.uint8, count=256 * 4, offset=pal_off).reshape(256, 4)
            palette_rgb = pal_bytes[:, [2, 1, 0]]  # BGRA -> RGB

            bw = min(blocksize, width - c * blocksize)
            bh = min(blocksize, height - r * blocksize)
            px_off = pixel_data_base + block_offsets[idx]
            indices = np.frombuffer(data, dtype=np.uint8, count=bw * bh, offset=px_off).reshape(bh, bw)
            block_rgb = palette_rgb[indices]

            y0, x0 = r * blocksize, c * blocksize
            canvas[y0:y0 + bh, x0:x0 + bw, :] = block_rgb

    return Image.fromarray(canvas, mode="RGB")


def decode_mos_v2(data, pvrz_loader):
    assert data[0:8] == b'MOS V2  '
    width, height, num_blocks, blocks_off = struct.unpack_from('<IIII', data, 8)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    off = blocks_off
    for i in range(num_blocks):
        page, src_x, src_y, w, h, dst_x, dst_y = struct.unpack_from('<7I', data, off)
        off += 28
        page_img = pvrz_loader(page)
        region = page_img.crop((src_x, src_y, src_x + w, src_y + h))
        canvas.paste(region, (dst_x, dst_y))
    return canvas


def decode_mos(data, pvrz_loader=None):
    if data[0:4] == b'MOSC':
        dec_len = struct.unpack_from('<I', data, 8)[0]
        data = zlib.decompress(data[12:])
    if data[0:4] != b'MOS ':
        raise ValueError(f"Not a MOS resource, sig={data[0:4]}")
    ver = data[4:8]
    if ver == b'V1  ':
        return decode_mos_v1(data)
    elif ver == b'V2  ':
        if pvrz_loader is None:
            raise ValueError("MOS V2 requires pvrz_loader")
        return decode_mos_v2(data, pvrz_loader)
    else:
        raise ValueError(f"Unknown MOS version {ver}")
