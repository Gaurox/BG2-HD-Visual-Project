"""WED V1.3 timeline relocation; preserve all native geometry and object tables."""
from __future__ import annotations

import struct


def _span(data: bytes, offset: int, size: int) -> None:
    if offset < 0 or size < 0 or offset + size > len(data):
        raise ValueError(f"WED span outside file: {offset}+{size}/{len(data)}")


def pointer_fields(data: bytes) -> list[int]:
    """Return positions of absolute offsets, including zero-count object polygons."""
    _span(data, 0, 32)
    if data[:8] != b"WED V1.3":
        raise ValueError("unsupported WED signature")
    layers, objects, headers, polygons, doors, _ = struct.unpack_from("<6I", data, 8)
    if not 1 <= layers <= 5:
        raise ValueError("unsupported WED layer count")
    _span(data, headers, layers * 24)
    _span(data, polygons, 20)
    _span(data, doors, objects * 26)
    fields = [16, 20, 24, 28]
    fields += [headers + i * 24 + k for i in range(layers) for k in (16, 20)]
    fields += [polygons + k for k in (4, 8, 12, 16)]
    fields += [doors + i * 26 + k for i in range(objects) for k in (18, 22)]
    for field in fields:
        _span(data, struct.unpack_from("<I", data, field)[0], 0)
    return fields


def validate_polygons(data: bytes) -> dict[str, int]:
    pointer_fields(data)
    objects, _, poly, doors, _ = struct.unpack_from("<5I", data, 12)
    count, wall, vertices, _, _ = struct.unpack_from("<5I", data, poly)
    groups = [(wall, count)]
    door_count = 0
    for i in range(objects):
        primary_n, secondary_n, primary, secondary = struct.unpack_from("<HHII", data, doors + i * 26 + 14)
        groups += [(primary, primary_n), (secondary, secondary_n)]
        door_count += primary_n + secondary_n
    for offset, count in groups:
        _span(data, offset, count * 18)
        for i in range(count):
            start, length = struct.unpack_from("<II", data, offset + i * 18)
            _span(data, vertices + start * 4, length * 4)
    return {"objects": objects, "wall_polygons": groups[0][1], "object_polygons": door_count}


def replace_overlay_timeline(data: bytes, slot: int, frames: int, speed: int = 1) -> bytes:
    """Relocate from original bytes, never from offsets already mutated in output."""
    validate_polygons(data)
    fields = pointer_fields(data)
    layers, _, headers = struct.unpack_from("<3I", data, 8)
    if not 0 <= slot < layers or not 1 <= frames <= 65535 or not 0 <= speed <= 255:
        raise ValueError("invalid timeline request")
    header = headers + slot * 24
    width, height = struct.unpack_from("<HH", data, header)
    tilemap, lookup = struct.unpack_from("<II", data, header + 16)
    _span(data, tilemap, 10)
    start, count = struct.unpack_from("<HH", data, tilemap)
    if (width, height, start) != (1, 1, 0) or count == 0:
        raise ValueError("only a single-cell sequential overlay is supported")
    _span(data, lookup, count * 2)
    if struct.unpack_from(f"<{count}H", data, lookup) != tuple(range(count)):
        raise ValueError("non-sequential overlay timeline")
    end = lookup + count * 2
    delta = (frames - count) * 2
    def moved(offset: int) -> int:
        return offset + delta if offset >= end else offset
    for field in fields:
        target = struct.unpack_from("<I", data, field)[0]
        if lookup <= field < end or lookup < target < end:
            raise ValueError("timeline overlaps another WED table")
    output = bytearray(data[:lookup] + struct.pack(f"<{frames}H", *range(frames)) + data[end:])
    for field in fields:
        struct.pack_into("<I", output, moved(field), moved(struct.unpack_from("<I", data, field)[0]))
    struct.pack_into("<H", output, moved(tilemap) + 2, frames)
    output[moved(tilemap) + 7] = speed
    validate_polygons(bytes(output))
    # Inverse relocation must reconstruct every original byte, including geometry.
    restored = bytearray(output[:lookup] + data[lookup:end] + output[lookup + frames * 2:])
    for field in fields:
        restored[field:field + 4] = data[field:field + 4]
    restored[tilemap + 2:tilemap + 4] = data[tilemap + 2:tilemap + 4]
    restored[tilemap + 7] = data[tilemap + 7]
    if restored != data:
        raise ValueError("WED bytes changed outside timeline and relocated pointers")
    return bytes(output)
