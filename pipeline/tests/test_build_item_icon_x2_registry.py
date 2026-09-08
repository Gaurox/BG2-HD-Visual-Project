from __future__ import annotations

import importlib.util
import struct
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "build_item_icon_x2_registry.py"
SPEC = importlib.util.spec_from_file_location("build_item_icon_x2_registry", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_write_pack_emits_cycle_slot_identity(tmp_path: Path) -> None:
    replacement = bytes(range(16))
    record = {
        "resref": "TEST",
        "sequence": 2,
        "slot": 1,
        "global_frame": 3,
        "source_width": 1,
        "source_height": 1,
        "replacement_width": 2,
        "replacement_height": 2,
        "replacement": replacement,
    }
    path = tmp_path / MODULE.PACK_NAME
    MODULE.write_pack([record], path)
    raw = path.read_bytes()
    header = struct.unpack_from("<8sIIIIQQ", raw)
    assert header[:4] == (MODULE.MAGIC, 2, 2, 1)
    assert header[4] == MODULE.RECORD_BYTES
    assert header[5] == MODULE.HEADER_BYTES + MODULE.RECORD_BYTES
    assert header[6] == len(raw)
    assert raw[MODULE.HEADER_BYTES : MODULE.HEADER_BYTES + 8] == b"TEST\0\0\0\0"
    record_values = struct.unpack_from("<HHHHHHIQII", raw, MODULE.HEADER_BYTES + 8)
    assert record_values == (2, 1, 1, 1, 2, 2, 3, header[5], 16, 0)
    assert raw[header[5] :] == replacement
