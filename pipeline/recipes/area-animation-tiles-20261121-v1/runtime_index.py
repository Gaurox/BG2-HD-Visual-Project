"""Generate per-area seek tables for the verified stored ZIP."""
import json
from pathlib import Path
import re
import shutil
import struct
import sys
from zipfile import ZIP_STORED, ZipFile
from zlib import crc32

from build import CROP_INDEX, GEOMETRY, HEADER, PACK, RUN, TILE_INDEX, sharing

HEAD = struct.Struct('<8sQII')
ROW = struct.Struct('<6IQQ4I')
LOCAL = struct.Struct('<4s5H3I2H')


def registry_frames(registry):
    magic, version, scale, resources, reserved = struct.unpack_from('<8s4I', registry)
    if magic != b'IEEAAX4\0' or version not in (1, 2, 3) or scale != 4 or reserved:
        raise ValueError('Invalid registry header')
    offset = 24
    for _ in range(resources):
        raw_name, frames, cycles = struct.unpack_from('<8s2I', registry, offset)
        name = raw_name.rstrip(b'\0').decode('ascii')
        offset += 16 + (20 if version >= 2 else 0)
        variant = 0
        if version == 3:
            variant, = struct.unpack_from('<I', registry, offset + 12)
            offset += 16
        stem = f'{name}-v{variant}' if variant else name
        for i in range(frames):
            w, h = struct.unpack_from('<2I', registry, offset)
            offset += 8
            yield f'AAX4-{stem}-frame{i:03}.rgba', w * scale, h * scale
        for _ in range(cycles):
            native, = struct.unpack_from('<I', registry, offset)
            offset += 4 + 4 * native
            if version >= 2:
                timed, = struct.unpack_from('<I', registry, offset)
                offset += 4 + 4 * timed
    if offset != len(registry):
        raise ValueError('Invalid registry size')


def payload_offset(raw, info):
    raw.seek(info.header_offset)
    data = LOCAL.unpack(raw.read(LOCAL.size))
    name_bytes, extra_bytes = data[-2:]
    if (data[0] != b'PK\x03\x04' or info.compress_type != ZIP_STORED
            or info.compress_size != info.file_size or data[3] != ZIP_STORED
            or raw.read(name_bytes).decode('ascii') != info.filename):
        raise ValueError(f'Invalid stored member: {info.filename}')
    return raw.tell() + extra_bytes


def build_runtime(game):
    proof = json.loads((RUN.parent / 'results.json').read_bytes())
    if sharing.file_sha(PACK) != proof['tiled_zip_sha256']:
        raise ValueError('Verified archive SHA-256 differs')
    assets = RUN / 'verify-assets'
    overlay = assets / 'area-animation-pack'
    installed_areas = game / 'iee-assets/areas'
    with ZipFile(PACK) as zip_file, PACK.open('rb') as raw:
        shared_raw = zip_file.read(sharing.INDEX)
        mapping = json.loads(shared_raw)
        digests = sorted(set(mapping['frames'].values()))
        crop_data = zip_file.read(CROP_INDEX)
        tile_data = zip_file.read(TILE_INDEX)
        if HEADER.unpack_from(crop_data) != (b'AAX4CRP1', len(digests), bytes.fromhex(sharing.sha(shared_raw))):
            raise ValueError('Crop index binding differs')
        if HEADER.unpack_from(tile_data) != (b'AAX4TIL1', len(digests), bytes.fromhex(sharing.sha(crop_data))):
            raise ValueError('Tile index binding differs')
        tile_offset = payload_offset(raw, zip_file.getinfo(TILE_INDEX))
        next_mask = HEADER.size + len(digests)
        records = {}
        for i, digest in enumerate(digests):
            geometry = GEOMETRY.unpack_from(crop_data, HEADER.size + i * GEOMETRY.size)
            w, h = geometry[-2:]
            edge = tile_data[HEADER.size + i]
            mask_size = (((w+edge-1)//edge)*((h+edge-1)//edge)+7)//8 if edge else 0
            mask = tile_data[next_mask:next_mask + mask_size]
            member = zip_file.getinfo(sharing.blob_name(digest))
            records[digest] = ROW.pack(*geometry, payload_offset(raw, member), tile_offset + next_mask,
                                       member.file_size, member.CRC, crc32(mask), edge)
            next_mask += mask_size
        if next_mask != len(tile_data):
            raise ValueError('Tile index length differs')

        overlays = {}
        covered = set()
        catalog = []
        archive_size = PACK.stat().st_size
        registries = {}
        for name in mapping['metadata']:
            if not name.endswith('/AreaAnimations-X4.registry'):
                continue
            area = Path(name).parent.name
            if not re.fullmatch(r'(AR|OH)[0-9]{4}', area) or area in overlays:
                raise ValueError(f'Unexpected zone: {area}')
            registry = zip_file.read(name)
            if (installed_areas / area / Path(name).name).read_bytes() != registry:
                raise ValueError(f'Active registry differs: {area}')
            rows = []
            for frame, w, h in registry_frames(registry):
                path = f'iee-assets/areas/{area}/{frame}'
                digest = mapping['frames'][path]
                row = records[digest]
                if struct.unpack_from('<2I', row) != (w, h) or path in covered:
                    raise ValueError(f'Unexpected registry frame: {path}')
                covered.add(path)
                rows.append(row)
                catalog.append(f'{area} {frame} {w} {h}')
            registries[area] = registry
            overlays[area] = HEAD.pack(b'AAX4RUN1', archive_size, crc32(registry), len(rows)) + b''.join(rows)
        if covered != mapping['frames'].keys() or len(overlays) * 2 != len(mapping['metadata']):
            raise ValueError('Seek tables do not cover the archive')

    overlay.mkdir(parents=True, exist_ok=True)
    for area, index in overlays.items():
        (overlay / f'{area}.index').write_bytes(index)
        path = assets / 'areas' / area
        path.mkdir(parents=True, exist_ok=True)
        (path / 'AreaAnimations-X4.registry').write_bytes(registries[area])
    staged_archive = overlay / 'AreaAnimations-X4.zip'
    with PACK.open('rb') as source, staged_archive.open('xb') as target:
        shutil.copyfileobj(source, target, 8 * 1024 * 1024)
    if sharing.file_sha(staged_archive) != proof['tiled_zip_sha256']:
        raise ValueError('Staged archive SHA-256 differs')
    (RUN / 'verification-catalog.txt').write_text('\n'.join(catalog) + '\n', encoding='ascii')
    print(f'{len(covered)} frames, {len(overlays)} zones, {sum(map(len, overlays.values()))} octets d\'index')


if __name__ == '__main__':
    build_runtime(Path(sys.argv[1]))
