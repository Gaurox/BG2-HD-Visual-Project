import struct, zlib, os

from workspace_paths import get_path

GAME_DIR = str(get_path("bg2ee_game_root"))
KEY_PATH = os.path.join(GAME_DIR, "chitin.key")

_bif_cache = {}


def load_key():
    with open(KEY_PATH, "rb") as f:
        data = f.read()
    assert data[0:4] == b"KEY "
    bif_count, res_count, bif_off, res_off = struct.unpack_from("<IIII", data, 8)

    bif_entries = []
    off = bif_off
    for i in range(bif_count):
        length, name_off, name_len, location = struct.unpack_from("<IIHH", data, off)
        name = data[name_off:name_off + name_len].split(b"\x00")[0].decode("cp1252", errors="replace")
        bif_entries.append(name)
        off += 12

    res_entries = []
    off = res_off
    for i in range(res_count):
        name8, rtype, locator = struct.unpack_from("<8sHI", data, off)
        name = name8.split(b"\x00")[0].decode("cp1252", errors="replace")
        res_entries.append((name, rtype, locator))
        off += 14

    return bif_entries, res_entries


def get_bif_buffer(bif_name):
    if bif_name in _bif_cache:
        return _bif_cache[bif_name]
    path = os.path.join(GAME_DIR, bif_name.replace("/", os.sep).replace("\\", os.sep))
    with open(path, "rb") as f:
        raw = f.read()
    if raw[0:4] == b"BIFC":
        pos = 8
        total_len = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        chunks = []
        while pos < len(raw):
            ulen, clen = struct.unpack_from("<II", raw, pos)
            pos += 8
            comp = raw[pos:pos + clen]
            pos += clen
            chunks.append(zlib.decompress(comp))
        buf = b"".join(chunks)
    else:
        buf = raw
    _bif_cache[bif_name] = buf
    return buf


def resolve_resource(bif_entries, locator):
    bif_index = (locator >> 20) & 0xFFF
    res_index = locator & 0x3FFF
    bif_name = bif_entries[bif_index]
    buf = get_bif_buffer(bif_name)
    assert buf[0:4] == b"BIFF", f"unexpected sig {buf[0:4]} in {bif_name}"
    file_count, tileset_count, files_off = struct.unpack_from("<III", buf, 8)
    found = None
    off = files_off
    for i in range(file_count):
        e_locator, e_offset, e_size, e_type, e_unk = struct.unpack_from("<IIIHH", buf, off)
        if (e_locator & 0x3FFF) == res_index:
            found = (e_offset, e_size, e_type)
            break
        off += 16
    if found is None:
        return None
    e_offset, e_size, e_type = found
    return buf[e_offset:e_offset + e_size], bif_name


def resolve_tileset_resource(bif_entries, locator):
    """For TIS resources, which live in the separate tileset-entries table of the BIF."""
    bif_index = (locator >> 20) & 0xFFF
    tileset_index = (locator >> 14) & 0x3F
    bif_name = bif_entries[bif_index]
    buf = get_bif_buffer(bif_name)
    assert buf[0:4] == b"BIFF", f"unexpected sig {buf[0:4]} in {bif_name}"
    file_count, tileset_count, files_off = struct.unpack_from("<III", buf, 8)
    tileset_off = files_off + file_count * 16
    off = tileset_off
    found = None
    for i in range(tileset_count):
        e_locator, e_offset, e_tile_count, e_tile_size, e_type, e_unk = struct.unpack_from("<IIIIHH", buf, off)
        if ((e_locator >> 14) & 0x3F) == tileset_index:
            found = (e_offset, e_tile_count, e_tile_size)
            break
        off += 20
    if found is None:
        raise KeyError(f"tileset index {tileset_index} not found in {bif_name}")
    e_offset, e_tile_count, e_tile_size = found
    data = buf[e_offset:e_offset + e_tile_count * e_tile_size]
    return data, e_tile_count, e_tile_size, bif_name
