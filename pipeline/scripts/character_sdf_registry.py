"""V10: append SDF to an acquired V6 Character leaf; keep compressed I/F bytes."""
import hashlib
import struct
import zlib
from pathlib import Path
import numpy as np
import palette_registry as v6
from sprite_sdf_registry import validate


def derive(source, destination, fields):
    source, destination = Path(source), Path(destination)
    assert not destination.exists()
    parsed = v6.inspect(source, include_frames=True)
    assert parsed['scale'] == 2 and parsed['class_profile_id'] == parsed['decode_rule_id'] == 1
    assert parsed['resource_count'] == 1
    resource = parsed['frame_data'][0]
    assert len(fields) == len(resource['frames'])
    raw = source.read_bytes()
    result = bytearray(raw[:32]);struct.pack_into('<I', result, 8, 10)
    result.extend(raw[32:80]);pos = 80;sdf_bytes = 0
    with v6._Codec(compress=True) as codec:
        for frame, (sdf, material) in zip(resource['frames'], fields):
            w,h,*_=frame['geometry']
            validate(np.frombuffer(frame['I'],np.uint8).reshape(h*2,w*2), sdf, material)
            header = bytearray(raw[pos:pos + v6.FRAME_BYTES]);pos += v6.FRAME_BYTES
            stored_i = struct.unpack_from('<I', header, 12)[0]
            stored_f = struct.unpack_from('<I', header, 560)[0]
            header[11] = 2
            result.extend(header)
            auxiliary = []
            for plane in (sdf.tobytes(), material.tobytes()):
                compressed = codec.encode(plane)
                packed = compressed if len(compressed) < len(plane) else plane
                result.extend(struct.pack('<IB3x', len(packed), int(len(packed) < len(plane))))
                auxiliary.append(packed);sdf_bytes += len(plane)
            result.extend(raw[pos:pos + stored_i + stored_f]);pos += stored_i + stored_f
            for packed in auxiliary:result.extend(packed)
    result.extend(raw[pos:])
    assert sdf_bytes <= 128 * 1024 * 1024
    # Prove stripping only the auxiliary data yields the original leaf exactly.
    restored = bytearray(result[:80]);struct.pack_into('<I', restored, 8, 6);pos = 80
    for frame in resource['frames']:
        header = bytearray(result[pos:pos + 568]);pos += 568
        sizes = [struct.unpack_from('<I', result, pos + k * 8)[0] for k in range(2)];pos += 16
        count = struct.unpack_from('<I', header, 12)[0] + struct.unpack_from('<I', header, 560)[0]
        header[11] = 0;restored.extend(header);restored.extend(result[pos:pos + count]);pos += count + sum(sizes)
    restored.extend(result[pos:]);assert restored == raw
    destination.write_bytes(result)
    return dict(version=10, scale=2, sha256=hashlib.sha256(result).hexdigest().upper(),
                crc32=zlib.crc32(result) & 0xffffffff, resource_count=1,
                frame_count=parsed['frame_count'], index_bytes=parsed['index_bytes'],
                registry_bytes=len(result), class_profile_id=1, decode_rule_id=1,
                sdf_bytes=sdf_bytes, original_colour_leaf_byte_identical=True)
