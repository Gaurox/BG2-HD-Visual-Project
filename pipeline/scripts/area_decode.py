import struct
import numpy as np
from PIL import Image
from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from mos_decode import decode_pvrz_page

TIS_TYPE = 0x03EB
WED_TYPE = 0x03E9
PVRZ_TYPE = 0x0404

_pvrz_page_cache = {}


def get_pvrz_page(bif_entries, pvrz_by_name, prefix, page):
    key = f"{prefix}{page:02d}"
    if key in _pvrz_page_cache:
        return _pvrz_page_cache[key]
    entry = pvrz_by_name.get(key.upper())
    if entry is None:
        # try without upper-casing issues, and 3-digit fallback just in case
        entry = pvrz_by_name.get(key)
    if entry is None:
        raise KeyError(f"PVRZ page not found: {key}")
    data, bif_name = resolve_resource(bif_entries, entry[2])
    img = decode_pvrz_page(data)
    _pvrz_page_cache[key] = img
    return img


def decode_tis_tiles(bif_entries, pvrz_by_name, tis_resref, tis_locator):
    data, tile_count, tile_size, bif_name = resolve_tileset_resource(bif_entries, tis_locator)
    prefix = tis_resref[0] + tis_resref[2:]

    if tile_size == 12:
        def get_tile(idx):
            page, x, y = struct.unpack_from('<3I', data, idx * 12)
            if page == 0xFFFFFFFF:
                return Image.new("RGBA", (64, 64), (0, 0, 0, 255))
            page_img = get_pvrz_page(bif_entries, pvrz_by_name, prefix, page)
            return page_img.crop((x, y, x + 64, y + 64))
        return get_tile, tile_count
    elif tile_size == 5120:
        def get_tile(idx):
            off = idx * 5120
            pal = np.frombuffer(data, dtype=np.uint8, count=1024, offset=off).reshape(256, 4)
            pal_rgb = pal[:, [2, 1, 0]]
            indices = np.frombuffer(data, dtype=np.uint8, count=4096, offset=off + 1024).reshape(64, 64)
            rgb = pal_rgb[indices]
            return Image.fromarray(rgb, mode="RGB").convert("RGBA")
        return get_tile, tile_count
    else:
        raise ValueError(f"Unexpected TIS tile size {tile_size}")


def render_area(bif_entries, res_entries, are_name, night=False):
    tis_by_name = {r[0].upper(): r for r in res_entries if r[1] == TIS_TYPE}
    wed_by_name = {r[0].upper(): r for r in res_entries if r[1] == WED_TYPE}
    pvrz_by_name = {r[0].upper(): r for r in res_entries if r[1] == PVRZ_TYPE}

    wed_resref = (are_name + ("N" if night else "")).upper()
    wr = wed_by_name.get(wed_resref)
    if wr is None:
        if night:
            # Do not silently fall back to the day WED: a caller asking for the
            # night variant must know it does not exist, not receive a day
            # render mislabelled as night.
            raise KeyError(f"night WED not found for {are_name} (expected {wed_resref})")
        raise KeyError(f"WED not found for {are_name}")

    wdata, _ = resolve_resource(bif_entries, wr[2])
    assert wdata[0:4] == b'WED '
    num_overlays, num_doors, off_overlays, off_secondary, off_doors, off_door_idx = struct.unpack_from('<IIIIII', wdata, 8)

    ov_w, ov_h = struct.unpack_from('<HH', wdata, off_overlays)
    tileset_ref = wdata[off_overlays + 4:off_overlays + 12].split(b'\x00')[0].decode('ascii')
    off_tilemap, off_lookup = struct.unpack_from('<II', wdata, off_overlays + 0x10)

    tis_entry = tis_by_name.get(tileset_ref.upper())
    if tis_entry is None:
        raise KeyError(f"TIS not found: {tileset_ref}")

    get_tile, tile_count = decode_tis_tiles(bif_entries, pvrz_by_name, tileset_ref.upper(), tis_entry[2])

    canvas = Image.new("RGBA", (ov_w * 64, ov_h * 64))
    for r in range(ov_h):
        for c in range(ov_w):
            cell_idx = r * ov_w + c
            start_idx, cnt, sec_idx, flags = struct.unpack_from('<HHHB3x', wdata, off_tilemap + cell_idx * 10)
            tile_id = struct.unpack_from('<H', wdata, off_lookup + start_idx * 2)[0]
            tile_img = get_tile(tile_id)
            canvas.paste(tile_img, (c * 64, r * 64))
    return canvas
