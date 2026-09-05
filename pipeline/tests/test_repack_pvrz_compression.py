from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from repack_pvrz_compression import decode_pvrz, repack_directory  # noqa: E402


class RepackPvrzCompressionTests(unittest.TestCase):
    def test_level_zero_preserves_tis_and_decoded_pvr(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            tis = b"TIS V1  " + bytes(range(64))
            decoded = b"PVR\x03" + bytes(range(256)) * 1024
            source_pvrz = struct.pack("<I", len(decoded)) + zlib.compress(decoded, 9)
            (source / "ARTEST.TIS").write_bytes(tis)
            (source / "ATEST00.PVRZ").write_bytes(source_pvrz)
            (source / "_preview.png").write_bytes(b"ignored")

            manifest = repack_directory(source, output, level=0)

            self.assertEqual((output / "ARTEST.TIS").read_bytes(), tis)
            output_pvrz = (output / "ATEST00.PVRZ").read_bytes()
            self.assertEqual(decode_pvrz(output_pvrz, "ATEST00.PVRZ"), decoded)
            self.assertNotEqual(output_pvrz, source_pvrz)
            self.assertFalse((output / "_preview.png").exists())
            self.assertEqual(manifest["schema"], "bg2-upscale-pvrz-repack-v1")
            self.assertTrue(manifest["decoded_payloads_byte_exact"])
            self.assertTrue(manifest["tis"]["copied_byte_exact"])
            written = json.loads((output / "repack-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(written["files"][0]["decoded_pvr_sha256"], manifest["files"][0]["decoded_pvr_sha256"])

    def test_existing_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            output.mkdir()
            (source / "ARTEST.TIS").write_bytes(b"TIS")
            (source / "ATEST00.PVRZ").write_bytes(struct.pack("<I", 1) + zlib.compress(b"x"))
            with self.assertRaisesRegex(ValueError, "sortie existe déjà"):
                repack_directory(source, output, level=0)

    def test_invalid_decoded_size_is_rejected_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            (source / "ARTEST.TIS").write_bytes(b"TIS")
            (source / "ATEST00.PVRZ").write_bytes(struct.pack("<I", 2) + zlib.compress(b"x"))
            with self.assertRaisesRegex(ValueError, "taille décodée"):
                repack_directory(source, output, level=0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
